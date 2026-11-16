"""G2: real SQLite + FeedState, synthetic data, no subscription/network/order access."""
import copy
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agentrader.chart.chart_clock import measure_time
from agentrader.chart.chart_context import ChartContext, ContextChanged, ContextReadLimit, ContextSourceMismatch
from agentrader.chart.chart_precision import exact_tick
from agentrader.chart.chart_profiles import ProfileService
from agentrader.chart.drawings.service import DrawingService, DrawingError
from agentrader.chart.indicator_config import IndicatorService
from agentrader.shared.market_feed import FeedState, MarketFeedHub
from agentrader.migrations import migrate
from scripts.integration.chart_tool_matrix_cases import drawing_cases, candles

HAS_WEB = all(importlib.util.find_spec(module) is not None for module in ('fastapi', 'httpx'))


class ChartContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name)/'app.db'
        migrate(self.database)
        self.drawings = DrawingService(self.database, 'owner')
        self.indicators = IndicatorService(self.database, 'owner')
        self.profiles = ProfileService(self.database, 'owner')
        self.rows = candles(10)
        self.now = [self.rows[-1]['time']+2.]
        self.mono = [1000.]
        self.state = FeedState('BTCUSDT', '15m', clock=lambda: self.now[0], monotonic=lambda: self.mono[0])
        self.market = dict(symbol='BTCUSDT', tick_size='0.25', exact=exact_tick('0.25'))
        client = SimpleNamespace(get=lambda *_: dict(serverTime=int(self.now[0]*1000)))
        sample = measure_time(client, lambda: self.now[0], lambda: self.mono[0])[1]
        self.state.seed(dict(clock_sample=sample, server_time=int(self.now[0]*1000),
                             market=self.market, quality=dict(state='OK', missing_bars=0), candles=self.rows))
        self.state.timing.observe(int(self.now[0]*1000))
        self.state.state = 'LIVE'
        self.hub = MarketFeedHub(None)
        self.feed = SimpleNamespace(state=self.state, references=1)
        self.hub.feeds[('BTCUSDT', '15m')] = self.feed
        self.service = ChartContext(self.database, 'owner', self.hub, clock=lambda: self.now[0])

    def create(self, request='drawing', **changes):
        geometry = {**drawing_cases()[0]['geometry'], **changes}
        return self.drawings.create('main', request, geometry)

    def test_ready_snapshot_is_readonly_bounded_and_keeps_raw_decimal_objects(self):
        item = self.create()
        before = self.database.read_bytes()
        with patch.object(self.hub, 'acquire', side_effect=AssertionError('subscription created')):
            result = self.service.read('main')
        self.assertEqual(before, self.database.read_bytes())
        self.assertEqual(result['objects'][0]['geometry'], item['geometry'])
        self.assertIsInstance(result['objects'][0]['geometry']['anchors'][0]['price'], str)
        self.assertEqual(len(result['indicators']['indicators']), 9)
        ready = result['derived']['readiness']
        self.assertEqual(ready['state'], 'READY')
        self.assertEqual(ready['available_closed_count'], 9)
        self.assertEqual(ready['consumed_range']['count'], 9)
        self.assertFalse(ready['open_candle_used'])
        self.assertTrue(ready['open_candle_present'])
        self.assertNotIn('candles', result)
        self.assertFalse(result['order_authority'])
        self.assertEqual(result['ui']['state'], 'UI_UNAVAILABLE')
        self.assertEqual(result['data_identity']['data_revision'], self.state.data_revision)
        self.assertEqual(result['data_identity']['sequence'], self.state.sequence)
        self.assertEqual(result['context_id'], self.service.read('main')['context_id'])
        included = self.service.read('main', include_open=True)
        self.assertEqual(included['derived']['readiness']['consumed_range']['count'], 10)
        self.assertTrue(included['derived']['readiness']['open_candle_used'])
        self.assertNotEqual(result['context_id'], included['context_id'])
        self.assertNotEqual(ready['consumed_data_hash'], included['derived']['readiness']['consumed_data_hash'])

    def test_no_feed_retains_objects_and_persistent_preferences_without_browser(self):
        self.create()
        self.hub.feeds.clear()
        result = self.service.read('main')
        self.assertEqual(len(result['objects']), 1)
        self.assertEqual(result['derived']['readiness']['state'], 'WAITING_FOR_DATA')
        self.assertIsNone(result['data_identity'])
        self.assertEqual(result['persistent_view']['body']['schema'], 'chart-profile/1')

    def test_stale_disconnect_and_untrusted_clock_never_report_ready(self):
        before = self.service.read('main')
        self.now[0] += 11
        self.mono[0] += 11
        result = self.service.read('main')
        self.assertEqual(result['derived']['readiness']['state'], 'STALE')
        self.assertNotEqual(before['context_id'], result['context_id'])
        self.state.state = 'RECONNECTING'
        self.assertEqual(self.service.read('main')['derived']['readiness']['state'], 'STALE')
        self.state.state = 'LIVE'
        self.state.timing.sample = None
        result = self.service.read('main')['derived']['readiness']
        self.assertEqual(result['state'], 'STALE')
        self.assertEqual(result['source_clock']['reason'], 'CLOCK_UNTRUSTED')
        self.feed.references = 0
        self.assertEqual(self.service.read('main')['derived']['readiness']['state'], 'WAITING_FOR_DATA')

    def test_warmup_gap_and_corrupt_proof_are_distinct_and_not_zero_success(self):
        result = self.service.read('main', required_closed_bars=10)['derived']['readiness']
        self.assertEqual(result['state'], 'WARMUP')
        self.assertEqual(result['required_closed_bars'], 10)
        self.state.rows.pop(5)
        self.state.quality = dict(state='GAP', missing_bars=1)
        self.state._capture_evidence()
        result = self.service.read('main')['derived']['readiness']
        self.assertEqual(result['state'], 'WAITING_FOR_DATA')
        self.assertEqual(result['missing_ranges'], [dict(start=self.rows[5]['time'], end=self.rows[5]['time'], missing_count=1)])
        self.state.rows[-1]['close'] += .1
        self.assertEqual(self.service.read('main')['derived']['readiness']['reasons'], ['DATA_PROOF_MISMATCH'])

    def test_owner_workspace_symbol_interval_and_source_boundaries(self):
        self.create()
        self.create('eth', symbol='ETHUSDT')
        other = DrawingService(self.database, 'other')
        other.create('main', 'other-owner', drawing_cases()[0]['geometry'])
        self.drawings.create('elsewhere', 'other-workspace', drawing_cases()[0]['geometry'])
        self.assertEqual(len(self.service.read('main')['objects']), 1)
        self.assertEqual(len(self.service.read('main', symbol='ETHUSDT')['objects']), 1)
        self.assertEqual(self.service.read('main', interval='1m')['derived']['readiness']['state'], 'WAITING_FOR_DATA')
        self.drawings.save_workspace('main', 'select-eth', 0, dict(symbol='ETHUSDT', interval='1m'))
        self.assertEqual(self.service.read('main')['market']['symbol'], 'ETHUSDT')
        with self.assertRaises(ContextSourceMismatch):
            self.service.read('main', environment='live_public')
        data = self.hub.binding_context('BTCUSDT', '15m')
        for field, value in [('symbol', 'ETHUSDT'), ('interval', '1m'), ('source', 'foreign'), ('price_type', 'MARK_PRICE')]:
            wrong = copy.deepcopy(data)
            wrong['identity'][field] = value
            with patch.object(self.service, '_data', return_value=wrong):
                result = self.service.read('main', symbol='BTCUSDT', interval='15m')
                self.assertEqual(result['derived']['readiness']['state'], 'SOURCE_MISMATCH')
                self.assertIsNone(result['derived']['readiness']['proof'])

    def test_pages_require_same_context_and_edits_deletes_configs_profiles_invalidate_it(self):
        for i in range(3):
            self.create(str(i))
        first = self.service.read('main', limit=1)
        self.assertEqual(first['pagination']['next_offset'], 1)
        with self.assertRaises(DrawingError):
            self.service.read('main', offset=1)
        second = self.service.read('main', limit=1, offset=1, expected_context_id=first['context_id'])
        self.assertNotEqual(first['objects'][0]['drawing_id'], second['objects'][0]['drawing_id'])
        self.assertEqual(first['context_id'], second['context_id'])
        item = first['objects'][0]
        self.drawings.update(item['drawing_id'], 'edit', 1, {**item['geometry'], 'label': 'edited'})
        with self.assertRaises(ContextChanged):
            self.service.read('main', expected_context_id=first['context_id'])
        before = self.service.read('main')
        self.drawings.update(item['drawing_id'], 'delete', 2, deleted=True)
        self.assertNotEqual(before['context_id'], self.service.read('main')['context_id'])
        before = self.service.read('main')
        config = before['indicators']['indicators']
        config[0]['period'] = 19
        self.indicators.save('main', 'config', 0, config, format_version=4)
        self.assertNotEqual(before['context_id'], self.service.read('main')['context_id'])
        before = self.service.read('main')
        profile = before['persistent_view']['body']
        profile['view']['theme'] = 'light'
        self.profiles.save_profile('main', 'profile', 0, profile)
        self.assertNotEqual(before['context_id'], self.service.read('main')['context_id'])

    def test_concurrent_edit_retries_and_continuous_change_returns_conflict(self):
        item = self.create()
        original = self.service._persistent
        calls = [0]
        def changing(*args):
            result = original(*args)
            calls[0] += 1
            if calls[0] == 1:
                self.drawings.update(item['drawing_id'], 'race', 1, {**item['geometry'], 'label': 'raced'})
            return result
        with patch.object(self.service, '_persistent', side_effect=changing):
            result = self.service.read('main')
        self.assertEqual(result['consistency']['attempts'], 2)
        self.assertEqual(result['objects'][0]['geometry']['label'], 'raced')
        original_data = self.service._data
        def changing_data(*args):
            result = original_data(*args)
            self.state.sequence += 1
            return result
        with patch.object(self.service, '_data', side_effect=changing_data):
            with self.assertRaises(ContextChanged):
                self.service.read('main')

    def test_invalid_bounds_and_read_deadline(self):
        for arguments in [dict(limit=201), dict(offset=-1), dict(required_closed_bars=0), dict(include_open=1)]:
            with self.assertRaises(DrawingError):
                self.service.read('main', **arguments)
        with patch.object(self.service, 'monotonic', side_effect=[0, 3]):
            with self.assertRaises(ContextReadLimit):
                self.service.read('main')

    def test_reload_epoch_generation_sequence_and_new_bar_invalidate_old_snapshot(self):
        before = self.service.read('main')
        self.state.stream_epoch = 'e'*32
        self.state.generation += 1
        self.state._capture_evidence()
        after = self.service.read('main')
        self.assertEqual(after['derived']['readiness']['state'], 'READY')
        self.assertNotEqual(before['context_id'], after['context_id'])
        self.assertEqual(after['data_identity']['stream_epoch'], 'e'*32)
        self.state.sequence += 1
        with self.assertRaises(ContextChanged):
            self.service.read('main', expected_context_id=after['context_id'])

    def test_all_25_raw_geometries_and_existing_text_survive_context_reads(self):
        expected = {}
        for case in drawing_cases():
            item = self.drawings.create('main', case['case_id'], case['geometry'])
            expected[item['drawing_id']] = item['geometry']
        before = self.database.read_bytes()
        result = self.service.read('main')
        self.assertEqual({item['drawing_id']: item['geometry'] for item in result['objects']}, expected)
        self.assertEqual(before, self.database.read_bytes())
        with patch.object(self.service, '_data', return_value={**self.hub.binding_context('BTCUSDT', '15m'), 'rows': [{'bad': 'row'}]}):
            invalid = self.service.read('main')
            self.assertEqual(invalid['derived']['readiness']['state'], 'INVALID_INPUT')
            self.assertIsNone(invalid['data_identity'])

    @unittest.skipUnless(HAS_WEB, 'Optional web dependencies not installed')
    def test_http_context_contract_conflict_and_existing_local_boundary(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        settings = WebSettings(self.database, Path(self.temp.name)/'execution.db', '', 'owner',
                               market_database=Path(self.temp.name)/'market.db')
        proxy = SimpleNamespace(binding_context=self.hub.binding_context, close=lambda: None)
        app = create_app(settings, hub=proxy)
        with TestClient(app, base_url='http://127.0.0.1') as client:
            # Stop unrelated lifecycle writers before measuring the GET's byte-level effect.
            app.state.shadow_worker.close()
            app.state.alert_worker.close()
            self.create()
            before = hashlib.sha256(self.database.read_bytes()).hexdigest()
            response = client.get('/api/workspaces/main/chart-context')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.headers['cache-control'], 'no-store')
            result = response.json()
            self.assertTrue(client.get('/api/chart-tools').json()['chart_context']['implemented'])
            self.assertEqual(result['derived']['readiness']['state'], 'READY')
            self.assertEqual(hashlib.sha256(self.database.read_bytes()).hexdigest(), before)
            self.assertEqual(client.get('/api/workspaces/main/chart-context', params={'expected_context_id': 'a'*64}).status_code, 409)
            for parameters in [dict(limit=201), dict(offset=1), dict(environment='live_public'), dict(symbol='BTC/USDT')]:
                self.assertEqual(client.get('/api/workspaces/main/chart-context', params=parameters).status_code, 422)
            self.assertEqual(client.get('/api/workspaces/main/chart-context', headers={'Origin': 'http://foreign.invalid'}).status_code, 403)
            self.assertEqual(client.get('/api/workspaces/main/chart-context', headers={'Host': 'foreign.invalid'}).status_code, 400)
        self.assertFalse(settings.execution_database.exists())
        self.assertFalse(settings.market_database.exists())
