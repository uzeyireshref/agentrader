"""Cold startup latency regressions using gates, not external network timing."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock

from agentrader.chart.chart_market import ChartMarket
from agentrader.shared.market_data import INTERVALS, bucket
from agentrader.shared.market_feed import SharedFeed

STAMP = 1800000002000


class ChartStartupTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.client = Mock()
        self.client.get.side_effect = self.get
        self.market = ChartMarket(Path(self.folder.name)/'market.db',
                                  client_factory=lambda: self.client, clock=lambda: STAMP/1000)

    def get(self, path, params=None):
        if path.endswith('exchangeInfo'):
            return {'symbols': [dict(symbol='BTCUSDT', status='TRADING', contractType='PERPETUAL',
                baseAsset='BTC', quoteAsset='USDT', filters=[dict(filterType='PRICE_FILTER',tickSize='0.10')])]}
        if path.endswith('/time'):
            return {'serverTime': STAMP}
        step = INTERVALS[params['interval']]
        t = bucket(params['endTime'], params['interval'])
        return [[t-step,'100','110','90','105','10',t-1,'1050',5,'5','525','0'],
                [t,'100','110','90','105','10',t+step-1,'1050',5,'5','525','0']]

    def test_slow_history_interval_does_not_serialize_another_interval(self):
        self.market.catalog()
        entered, release = threading.Event(), threading.Event()
        def get(path, params=None):
            if path.endswith('klines') and params['interval']=='5m':
                entered.set()
                if not release.wait(3):
                    raise TimeoutError()
            return self.get(path, params)
        self.client.get.side_effect = get
        with ThreadPoolExecutor(max_workers=2) as pool:
            slow = pool.submit(self.market.history, 'BTCUSDT','5m',limit=2)
            try:
                self.assertTrue(entered.wait(1))
                fast = pool.submit(self.market.history, 'BTCUSDT','15m',limit=2)
                self.assertEqual(fast.result(timeout=1)['interval'],'15m')
            finally:
                release.set()
            self.assertEqual(slow.result(timeout=2)['interval'],'5m')

    def test_duplicate_concurrent_history_still_uses_one_upstream_read(self):
        self.market.catalog()
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(self.market.history,'BTCUSDT','15m',limit=2) for _ in range(2)]
            self.assertEqual(jobs[0].result(), jobs[1].result())
        calls = [c for c in self.client.get.call_args_list if c.args[0].endswith('klines')]
        self.assertEqual(len(calls),1)

    def test_rest_seed_publishes_while_public_socket_is_still_opening(self):
        history = self.market.history('BTCUSDT','15m',limit=2)
        market = Mock(database=self.market.database)
        socket_started, open_socket, seeded, stopped = (threading.Event() for _ in range(4))
        socket = Mock()
        socket.receive.side_effect = lambda: (stopped.wait(.01) and None)
        socket.close.side_effect = stopped.set
        def opening(*args):
            socket_started.set()
            if not open_socket.wait(3):
                raise TimeoutError()
            return socket
        def read(*args, **kwargs):
            if not socket_started.wait(1):
                raise TimeoutError('Socket must start independently of history')
            return history
        market.history.side_effect = read
        feed = SharedFeed(market,'BTCUSDT','15m',socket_factory=opening,clock=lambda: STAMP/1000)
        seed = feed.state.seed
        def publish(value):
            seed(value)
            seeded.set()
        feed.state.seed = publish
        feed.references = 1
        feed.thread.start()
        try:
            self.assertTrue(seeded.wait(1),'REST candles should not wait for socket handshake')
            self.assertEqual(feed.state.state,'SYNCING')
            self.assertTrue(feed.state.rows)
        finally:
            feed.stop()
            open_socket.set()
            feed.thread.join(timeout=3)
        self.assertFalse(feed.thread.is_alive())
        socket.close.assert_called()

    def test_failed_rest_still_closes_socket_opened_in_parallel(self):
        market = Mock(database=self.market.database)
        market.history.side_effect = OSError('history failed')
        closed = threading.Event()
        socket = Mock()
        socket.close.side_effect = closed.set
        feed = SharedFeed(market,'BTCUSDT','15m',socket_factory=lambda *args: socket)
        feed.references = 1
        feed.thread.start()
        try:
            self.assertTrue(closed.wait(1))
        finally:
            feed.stop()
            feed.thread.join(timeout=3)
        self.assertFalse(feed.thread.is_alive())

    def test_switch_burst_reuses_original_clock_evidence_without_resetting_age(self):
        self.market.catalog()
        first=self.market.history('BTCUSDT','5m',limit=2)
        second=self.market.history('BTCUSDT','15m',limit=2)
        calls=[c for c in self.client.get.call_args_list if c.args[0].endswith('/time')]
        self.assertEqual(len(calls),1)
        self.assertEqual(first['clock_sample']['sample_id'],second['clock_sample']['sample_id'])

    def test_wall_jump_or_reuse_ttl_requires_another_measured_clock(self):
        wall,mono=[STAMP/1000],[100.]
        self.market.clock=lambda:wall[0]
        self.market.monotonic=lambda:mono[0]
        self.market.history('BTCUSDT','5m',limit=2)
        wall[0]+=11;mono[0]+=11
        self.market.history('BTCUSDT','15m',limit=2)
        wall[0]+=1
        self.market.history('BTCUSDT','1h',limit=2)
        calls=[c for c in self.client.get.call_args_list if c.args[0].endswith('/time')]
        self.assertEqual(len(calls),3)


if __name__ == '__main__':
    unittest.main()
