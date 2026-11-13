import copy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from agentrader.chart_clock import measure_time
from agentrader.market_feed import FeedState, FeedUnavailable, SharedFeed
from test_chart_feed import START, event


def history():
    return {'server_time': START+2000, 'market': {}, 'quality': {'state': 'OK', 'missing_bars': 0},
            'candles': [{'time': START//1000, 'open': 100, 'high': 110, 'low': 90, 'close': 105,
                         'volume': 10, 'quote_volume': 1050, 'close_time': START+899999, 'closed': False}]}


class Stop:
    def __init__(self): self.stopped = False
    def is_set(self): return self.stopped
    def set(self): self.stopped = True
    def wait(self, _): return self.stopped


class FeedFreshnessTests(unittest.TestCase):
    def test_duplicate_flood_requires_reconnect_even_without_socket_timeout(self):
        now = [100.0]
        def fresh_history(*args, **kwargs):
            sample_client = Mock(); sample_client.get.return_value = {'serverTime': START+2000}
            value = copy.deepcopy(history())
            value['clock_sample'] = measure_time(sample_client, lambda: now[0], lambda: now[0])[1]
            return value
        market = SimpleNamespace(history=Mock(side_effect=fresh_history))
        first, second = Mock(), Mock()
        feed = SharedFeed(market, 'BTCUSDT', '15m', clock=lambda: now[0], monotonic=lambda: now[0])
        feed.references = 1
        feed.stop_event = Stop()
        def receive():
            now[0] += 1
            if now[0] >= 135:
                feed.stop_event.set()
            return event(stamp=START+1000)
        first.receive.side_effect = receive
        def connect(*_):
            if factory.call_count == 2:
                feed.stop_event.set()
                return second
            return first
        factory = Mock(side_effect=connect)
        feed.socket_factory = factory
        feed.run()
        self.assertEqual(factory.call_count, 2)
        self.assertEqual(market.history.call_count, 2)
        self.assertTrue(all(call.kwargs['force'] for call in market.history.call_args_list))
        first.close.assert_called_once()
        second.close.assert_called_once()

    def test_monotonic_but_delayed_event_cannot_refresh_live_status(self):
        now = [100.0]
        state = FeedState('BTCUSDT', '15m', clock=lambda: now[0], monotonic=lambda: now[0])
        state.seed(history())
        before = state.packet(state.generation)
        now[0] += 30
        with self.assertRaises(FeedUnavailable):
            state.apply(event(stamp=START+3000))
        self.assertEqual(state.sequence, before['sequence'])
        self.assertEqual(state.received_at, 100)

    def test_current_event_after_short_jitter_still_updates_normally(self):
        now = [100.0]
        state = FeedState('BTCUSDT', '15m', clock=lambda: now[0], monotonic=lambda: now[0])
        state.seed(history())
        now[0] += 5
        self.assertIsNotNone(state.apply(event(stamp=START+6500)))
        self.assertEqual(state.state, 'LIVE')
        self.assertEqual(state.received_at, 105)

    def test_server_clock_anchor_avoids_relying_on_local_epoch_agreement(self):
        now = [10.0]
        state = FeedState('BTCUSDT', '15m', clock=lambda: now[0], monotonic=lambda: now[0])
        state.seed(history())
        now[0] += 1
        self.assertIsNotNone(state.apply(event(stamp=START+3000)))
        self.assertEqual(state.state, 'LIVE')
