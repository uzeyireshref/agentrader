import copy
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from agentrader.chart_market import ChartMarket, InvalidMarket, MarketUnavailable, normalize_kline
from agentrader.market_data import INTERVALS
from agentrader.market_feed import FeedState, FeedUnavailable, MarketFeedHub, PublicSocket

STEP = INTERVALS['15m']
START = 1800000000000 // STEP * STEP


def row(t=START):
    return [t, '100', '110', '90', '105', '10', t + STEP - 1, '1050', 5, '5', '525', '0']


def event(t=START, stamp=None, closed=False, volume='11'):
    return {'e': 'kline', 'E': stamp or t + 3000, 's': 'BTCUSDT', 'k': {
        's': 'BTCUSDT', 'i': '15m', 't': t, 'T': t + STEP - 1, 'x': closed,
        'o': '100', 'h': '110', 'l': '90', 'c': '105', 'v': volume,
        'q': '1155', 'n': 6, 'V': '5', 'Q': '525'}}


class ChartFeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.client = Mock()
        self.symbol = {'symbol': 'BTCUSDT', 'status': 'TRADING', 'contractType': 'PERPETUAL',
                       'baseAsset': 'BTC', 'quoteAsset': 'USDT',
                       'filters': [{'filterType': 'PRICE_FILTER', 'tickSize': '0.10'}]}

        def get(path, params=None):
            if path.endswith('exchangeInfo'):
                return {'symbols': [self.symbol, dict(self.symbol, symbol='OLDUSDT', status='BREAK')]}
            if path.endswith('/time'):
                return {'serverTime': START + 2000}
            return [row(START-STEP), row()]
        self.client.get.side_effect = get
        self.market = ChartMarket(Path(self.temp.name)/'chart.db', client_factory=lambda: self.client, clock=lambda: START/1000+2)

    def history(self):
        return self.market.history('BTCUSDT', '15m', limit=2)

    def test_catalog_filters_contracts_and_cache_does_not_duplicate_requests(self):
        self.assertEqual([m['symbol'] for m in self.market.catalog()['markets']], ['BTCUSDT'])
        self.market.catalog()
        self.assertEqual(self.client.get.call_count, 1)

    def test_history_preserves_open_closed_bars_and_source(self):
        h = self.history()
        self.assertTrue(h['candles'][0]['closed'])
        self.assertFalse(h['candles'][1]['closed'])
        self.assertEqual(h['quality']['state'], 'OK')
        self.assertEqual(h['price_type'], 'LAST_PRICE')
        calls = self.client.get.call_count
        self.history()
        self.assertEqual(calls, self.client.get.call_count)

    def test_invalid_selection_rejected_without_network(self):
        for symbol, interval in [('BTCUSDT', '1s'), ('../BTCUSDT', '15m')]:
            with self.assertRaises(InvalidMarket):
                self.market.history(symbol, interval)
        self.client.get.assert_not_called()

    def test_unavailable_data_has_no_fake_live_fallback(self):
        self.client.get.side_effect = OSError('private-network-details')
        with self.assertRaises(MarketUnavailable) as caught:
            self.history()
        self.assertNotIn('private-', str(caught.exception))

    def test_bad_event_types_and_wrong_symbol_are_rejected(self):
        for payload in [dict(event(), s='ETHUSDT'), dict(event(), E='bad'),
                        dict(event(), k=dict(event()['k'], t='bad'))]:
            with self.assertRaises(InvalidMarket):
                normalize_kline(payload, 'BTCUSDT', '15m')

    def test_live_updates_drop_duplicates_and_closed_bar_cannot_reopen(self):
        state = FeedState('BTCUSDT', '15m')
        state.seed(self.history())
        state.apply(event())
        sequence = state.sequence
        self.assertIsNone(state.apply(event()))
        self.assertEqual(sequence, state.sequence)
        state.apply(event(stamp=START+STEP, closed=True))
        close_id = state.last_close['event_id']
        self.assertIsNone(state.apply(event(stamp=START+STEP+1)))
        self.assertEqual(close_id, state.last_close['event_id'])

    def test_missing_close_or_bar_requires_rest_resynchronization(self):
        state = FeedState('BTCUSDT', '15m')
        state.seed(self.history())
        with self.assertRaises(FeedUnavailable):
            state.apply(event(t=START+STEP))
        state.apply(event(stamp=START+STEP, closed=True))
        with self.assertRaises(FeedUnavailable):
            state.apply(event(t=START+STEP*2))

    def test_reconnect_seed_does_not_emit_historical_closes_as_new_signals(self):
        state = FeedState('BTCUSDT', '15m')
        h = self.history()
        state.seed(h)
        self.assertIsNone(state.last_close)
        state.apply(event(stamp=START+STEP, closed=True))
        previous = state.last_close
        h = copy.deepcopy(h)
        h['candles'][-1]['closed'] = True
        state.seed(h)
        self.assertEqual(previous, state.last_close)
        self.assertEqual(state.generation, 2)

    def test_stale_and_tail_packet_are_explicit(self):
        now = [100]
        state = FeedState('BTCUSDT', '15m', lambda: now[0], monotonic=lambda: now[0])
        state.seed(self.history())
        state.apply(event())
        packet = state.packet(state.generation)
        self.assertEqual(len(packet['tail']), 2)
        now[0] += 11
        self.assertEqual(state.packet(state.generation)['status'], 'STALE')

    def test_socket_uses_routed_public_market_endpoint(self):
        with patch('websocket.create_connection') as create:
            socket = PublicSocket('BTCUSDT', '15m')
            self.assertEqual(create.call_args.args[0], 'wss://fstream.binance.com/market/ws/btcusdt@kline_15m')
            socket.close()

    def test_two_clients_share_one_feed_and_shutdown_closes_it(self):
        gate = threading.Event()
        socket = Mock()
        socket.receive.side_effect = lambda: (gate.wait(.02) or None)
        socket.close.side_effect = gate.set
        # Mock receive must return timeout rather than the Event.wait boolean.
        def receive():
            gate.wait(.02)
            return None
        socket.receive.side_effect = receive
        hub = MarketFeedHub(self.market, socket_factory=lambda *args: socket)
        try:
            one = hub.acquire('BTCUSDT', '15m')
            two = hub.acquire('BTCUSDT', '15m')
            self.assertIs(one, two)
            self.assertEqual(one.references, 2)
            hub.release(one)
            hub.release(two)
        finally:
            hub.close()
        self.assertFalse(one.thread.is_alive())

