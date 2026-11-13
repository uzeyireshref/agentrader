import copy
import unittest
from unittest.mock import Mock

from agentrader.chart_clock import measure_time, StreamTiming, POLICY
from agentrader.market_feed import FeedState, FeedUnavailable
from test_chart_feed import START, event
from test_feed_freshness import history


class FakeClock:
    def __init__(self): self.wall = 100.; self.mono = 10.
    def advance(self, seconds): self.wall += seconds; self.mono += seconds


class ChartClockTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.wall = lambda: self.clock.wall
        self.mono = lambda: self.clock.mono
        self.client = Mock()
        self.client.get.return_value = {'serverTime': START + 2000}

    def sample(self): return measure_time(self.client, self.wall, self.mono)[1]

    def state(self):
        state = FeedState('BTCUSDT', '15m', self.wall, self.mono)
        seed = history(); seed['clock_sample'] = self.sample()
        state.seed(seed)
        return state, seed

    def test_server_offset_is_independent_of_local_wall_epoch_and_no_monotonic_wire(self):
        state, _ = self.state()
        self.clock.advance(1)
        state.apply(event(stamp=START+3000))
        timing = state.packet(state.generation)['timing']
        self.assertEqual(timing['state'], 'FRESH')
        self.assertEqual(timing['data_age_ms'], 0)
        self.assertEqual(timing['upstream_event_time'], START+3000)
        self.assertFalse(timing['live_eligible'])
        self.assertNotIn('mono', str(timing))

    def test_measurement_uncertainty_and_roundtrip_wall_jump_are_rejected(self):
        def slow(*_):
            self.clock.advance(3)
            return {'serverTime': START+2000}
        self.client.get.side_effect = slow
        evidence = self.sample()
        self.assertEqual(evidence['state'], 'UNTRUSTED')
        self.assertGreater(evidence['uncertainty_ms'], POLICY['max_uncertainty_ms'])
        self.client.get.side_effect = lambda *_: (setattr(self.clock, 'wall', self.clock.wall+1) or {'serverTime': START+2000})
        self.assertEqual(self.sample()['state'], 'UNTRUSTED')

    def test_wall_jumps_in_both_directions_block_without_changing_candles(self):
        for direction in (-100, 100):
            with self.subTest(direction=direction):
                state, _ = self.state(); before = copy.deepcopy(state.rows)
                self.clock.wall += direction
                with self.assertRaisesRegex(FeedUnavailable, 'CLOCK_UNTRUSTED'):
                    state.apply(event(stamp=START+3000))
                self.assertEqual(state.rows, before)
                self.assertEqual(state.packet()['timing']['reason'], 'CLOCK_UNTRUSTED')

    def test_missing_foreign_and_malformed_samples_are_observation_only(self):
        for proof in (None, {}, {'schema':'chart-clock-sample/1','state':'MEASURED','sample_id':'other-process'},
                      {'schema':'chart-clock-sample/1','state':'MEASURED','sample_id':[]}):
            timing = StreamTiming(self.wall, self.mono); timing.seed(proof)
            self.assertEqual(timing.observe(START+3000), 'CLOCK_UNTRUSTED')
            self.assertEqual(timing.proof()['state'], 'BLOCKED')

    def test_heartbeat_and_duplicate_traffic_do_not_reset_data_age(self):
        state, _ = self.state(); self.clock.advance(1); state.apply(event(stamp=START+3000))
        self.clock.advance(11)
        self.assertIsNone(state.apply(event(stamp=START+3000)))
        first = state.packet(state.generation)
        self.assertEqual(first['status'], 'STALE')
        self.assertEqual(first['timing']['reason'], 'UPSTREAM_STALE')
        self.clock.advance(1)
        second = state.packet(state.generation)
        self.assertEqual(second['sequence'], first['sequence'])
        self.assertGreater(second['timing']['data_age_ms'], first['timing']['data_age_ms'])

    def test_future_and_old_upstream_events_require_snapshot_before_resume(self):
        for stamp, reason in ((START+5000, 'FUTURE_UPSTREAM_TIME'), (START+3000, 'UPSTREAM_STALE')):
            state, _ = self.state()
            if reason == 'UPSTREAM_STALE': self.clock.advance(15)
            with self.assertRaisesRegex(FeedUnavailable, reason): state.apply(event(stamp=stamp))
            self.assertIsNone(state.last_close)
            self.assertTrue(state.timing.needs_snapshot)

    def test_long_outage_catchup_close_cannot_emit_and_fresh_seed_recovers(self):
        state, seed = self.state(); self.clock.advance(1); state.apply(event(stamp=START+3000))
        self.clock.advance(25)
        with self.assertRaises(FeedUnavailable): state.apply(event(stamp=START+28000, closed=True))
        self.assertIsNone(state.last_close)
        self.assertTrue(state.timing.needs_snapshot)
        self.client.get.return_value = {'serverTime': START+28000}
        seed['server_time'] = START+28000; seed['clock_sample'] = self.sample()
        state.seed(seed)
        self.assertEqual(state.packet()['timing']['reason'], 'AWAITING_UPSTREAM')
        self.assertIsNone(state.last_close)
        self.clock.advance(1); state.apply(event(stamp=START+29000))
        self.assertEqual(state.packet()['timing']['state'], 'FRESH')

    def test_sample_expiry_and_monotonic_regression_are_blocked(self):
        state, _ = self.state(); self.clock.advance(301)
        self.assertEqual(state.packet()['timing']['reason'], 'CLOCK_UNTRUSTED')
        state, _ = self.state(); self.clock.mono -= 1
        self.assertEqual(state.packet()['timing']['reason'], 'CLOCK_UNTRUSTED')

    def test_measurement_age_and_uncertainty_count_as_upstream_delay(self):
        timing = StreamTiming(self.wall, self.mono); timing.seed(self.sample())
        self.clock.advance(10)
        self.assertEqual(timing.observe(START+2000), 'UPSTREAM_STALE')

    def test_real_http_and_websocket_transport_timing_without_monotonic_numbers(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        state, seed = self.state(); self.clock.advance(1); state.apply(event(stamp=START+3000))
        hub = Mock(); hub.acquire.return_value = SimpleNamespace(state=state)
        market = Mock(); market.history.return_value = seed
        with tempfile.TemporaryDirectory() as folder:
            settings = WebSettings(Path(folder)/'app.db', Path(folder)/'execution.db', market_database=Path(folder)/'market.db')
            with TestClient(create_app(settings, market=market, hub=hub), base_url='http://127.0.0.1') as client:
                self.assertIn('clock_sample', client.get('/api/candles').json())
                with client.websocket_connect('ws://127.0.0.1/api/market-stream?symbol=BTCUSDT&interval=15m', headers={'origin':'http://127.0.0.1'}) as ws:
                    snapshot = ws.receive_json()
                    self.assertEqual(snapshot['timing']['state'], 'FRESH')
                    self.clock.advance(11)
                    stale = ws.receive_json()
                    self.assertEqual(stale['timing']['state'], 'BLOCKED')
                    self.assertEqual(stale['status'], 'STALE')
            self.assertFalse(settings.execution_database.exists())

    def test_runtime_shared_feed_never_consumes_socket_without_clock_evidence(self):
        import threading
        from types import SimpleNamespace
        from agentrader.market_feed import SharedFeed
        socket = Mock()
        market = SimpleNamespace(history=Mock(return_value=history()))
        feed = SharedFeed(market, 'BTCUSDT', '15m', socket_factory=lambda *_: socket,
                          clock=self.wall, monotonic=self.mono)
        feed.references = 1
        feed.stop_event.wait = lambda _: feed.stop_event.set()
        feed.run()
        socket.receive.assert_not_called()
        self.assertEqual(feed.state.packet()['timing']['reason'], 'CLOCK_UNTRUSTED')
        self.assertIsNone(feed.state.last_close)

    def test_clock_fault_observed_in_packet_stays_blocked_after_wall_restored(self):
        state, _ = self.state(); self.clock.advance(1); state.apply(event(stamp=START+3000))
        self.clock.wall += 100
        self.assertEqual(state.packet()['timing']['reason'], 'CLOCK_UNTRUSTED')
        self.clock.wall -= 100
        self.assertEqual(state.packet()['timing']['reason'], 'SNAPSHOT_REQUIRED')
        with self.assertRaisesRegex(FeedUnavailable, 'SNAPSHOT_REQUIRED'):
            state.apply(event(stamp=START+3001))
