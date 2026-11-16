import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_signal_previews as preview_tests
from test_v2_preflight import snapshot
from test_v2_runner import ExecutionExchange
from agentrader.chart.chart_bindings import binding_hash
from agentrader.integration.chart_execution import review_preview, guard_chart_entry, require_demo_acceptance
from agentrader.shared.config import Config
from agentrader.bot.plans import PlanService
from agentrader.bot.risk import RiskLimits
from agentrader.shared.state import StateStore
from agentrader.bot.v2_runner import V2Runner
from agentrader.integration.preview_preflight import local_preview_provider


class ChartExecutionTests(unittest.TestCase):
    def setUp(self):
        self.f = preview_tests.PreviewTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.body = self.f.create()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'execution.sqlite3'
        self.store = StateStore(self.path)
        self.addCleanup(lambda: self.store.close())
        self.service = PlanService(self.store, 'fixture')
        self.x = ExecutionExchange()
        self.x.price = '100'
        self.limits = RiskLimits()
        self.provider = lambda: self.f.service.show('main', self.f.event)
        self.preflight = Mock(side_effect=lambda *a, **k: dict(preview_hash=self.body['content_hash'],
                                       account_preflight={'state': 'READY', 'execution_authorized': False}))

    def review(self):
        return review_preview(self.service, self.provider, self.x, self.limits,
                              workspace='main', event_id=self.f.event, version=self.body['version'],
                              clock=lambda: self.f.clock[1], preflight=self.preflight, acceptance=lambda: True)

    def guard(self, service=None, exchange=None, limits=None, plan=None):
        return guard_chart_entry(service or self.service, exchange or self.x, limits or self.limits,
                                 plan or self.plan, provider_factory=lambda *a: self.provider,
                                 clock=lambda: self.f.clock[1], acceptance=lambda: True)

    def authorize(self):
        reviewed = self.review()
        self.plan = reviewed['plan']
        self.service.authorize(self.plan['plan_id'], 1, reviewed['authorization_token'],
                               'approve', 'fixture', now=1000)
        return reviewed

    def runner(self):
        self.addCleanup(patch.stopall)
        patch('time.time', return_value=1000).start()
        patch('agentrader.bot.v2_runner.guard_chart_entry', side_effect=self.guard).start()
        patch('agentrader.bot.v2_runner.require_guardian', return_value='isolated-guardian-fixture').start()
        snap = snapshot()
        snap['mark']['markPrice'] = '100'
        snap['settings'].update(leverage=2, marginType='ISOLATED')
        snap.update(observed_at=1000, finished_at=1000, now_ms=1000000)
        patch('agentrader.bot.v2_runner.collect_flat_snapshot', side_effect=lambda *a: copy.deepcopy(snap)).start()
        original_get = self.x.get
        self.x.get = lambda path, params=None: [snap['settings']] if path.endswith('symbolConfig') else original_get(path, params)
        original_request = self.x.request
        def request(method, path, params):
            result = original_request(method, path, params)
            if method == 'POST' and path.endswith('/order'):
                result['avgPrice'] = '100'
                self.x.orders[params['newClientOrderId']]['avgPrice'] = '100'
            return result
        self.x.request = request
        return self.new_runner()

    def new_runner(self):
        runner = V2Runner(self.service, self.x, self.limits)
        runner.book.clock = lambda: 1000
        return runner

    def test_review_is_pending_and_duplicate_never_rotates_token_or_sends(self):
        first = self.review()
        self.assertEqual(first['state'], 'PENDING_APPROVAL')
        self.assertTrue(first['authorization_token'])
        duplicate = self.review()
        self.assertTrue(duplicate['duplicate'])
        self.assertIsNone(duplicate['authorization_token'])
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM plan_versions').fetchone()[0], 1)
        self.assertEqual(self.x.calls, [])
        self.assertEqual(self.store.intents(), [])

    def test_guard_rejects_different_account_risk_and_content(self):
        self.authorize()
        self.assertTrue(self.guard())
        other = ExecutionExchange()
        other.config = Config('another-key', 'another-secret')
        with self.assertRaisesRegex(ValueError, 'SOURCE_NOT_CURRENT'):
            self.guard(exchange=other)
        with self.assertRaises(ValueError):
            self.guard(limits=RiskLimits(max_notional='90'))
        changed = copy.deepcopy(self.plan)
        changed['stop'] = '97'
        with self.assertRaises(ValueError):
            self.guard(plan=changed)

    def test_source_change_after_account_preflight_creates_no_plan(self):
        def changed(*a, **k):
            self.f.clock[1] = self.body['expires_at'] + 1
            return dict(preview_hash=self.body['content_hash'], account_preflight={'state':'READY'})
        self.preflight.side_effect = changed
        with self.assertRaises(ValueError):
            self.review()
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM plan_versions').fetchone()[0], 0)

    def test_preview_revision_two_imports_as_execution_one_and_binds_exact_revision(self):
        self.body = self.f.create({**preview_tests.inputs(), 'target':'105'}, version=1)
        first = self.review()
        self.assertEqual(first['plan']['version'], 1)
        self.assertEqual(first['source_binding']['preview_version'], 2)
        self.plan = first['plan']
        self.assertTrue(self.guard())

    def test_changed_parameters_cannot_create_second_execution_for_same_event(self):
        self.review()
        self.body = self.f.create({**preview_tests.inputs(), 'target':'105'}, version=1)
        with self.assertRaisesRegex(ValueError, 'ALREADY_REVIEWED'):
            self.review()

    def test_lost_binding_fails_closed_even_with_valid_plan_approval(self):
        self.authorize()
        with self.store.db:
            self.store.db.execute("DELETE FROM control WHERE name LIKE 'chart_entry:%'")
        with self.assertRaises(ValueError):
            self.guard()

    def test_runner_uses_existing_intent_journal_and_restart_never_reenters(self):
        self.authorize()
        runner = self.runner()
        opened = runner.open(self.plan['plan_id'], 1, True)
        self.assertEqual(opened['state'], 'MANAGING')
        self.assertEqual(len([c for c in self.x.calls if c[0] == 'POST' and c[1].endswith('/order')]), 1)
        self.store.close()
        self.store = StateStore(self.path)
        self.service = PlanService(self.store, 'fixture')
        runner = self.new_runner()
        runner.manage(opened['session_id'], True)
        with self.assertRaises(ValueError):
            runner.open(self.plan['plan_id'], 1, True)
        self.assertEqual(len([c for c in self.x.calls if c[0] == 'POST' and c[1].endswith('/order')]), 1)

    def test_pending_limit_cancels_when_source_is_revoked(self):
        self.authorize()
        self.x.limit_pending = True
        runner = self.runner()
        opened = runner.open(self.plan['plan_id'], 1, True)
        self.assertEqual(opened['state'], 'ENTRY_PENDING')
        self.f.clock[1] = self.body['expires_at'] + 1
        runner.manage(opened['session_id'], True)
        self.assertEqual(next(iter(self.x.orders.values()))['status'], 'CANCELED')
        self.assertEqual(len([c for c in self.x.calls if c[0] == 'POST']), 1)

    def test_filled_position_protection_continues_when_preview_expires(self):
        self.authorize()
        runner = self.runner()
        opened = runner.open(self.plan['plan_id'], 1, True)
        self.f.clock[1] = self.body['expires_at'] + 1
        self.assertEqual(runner.manage(opened['session_id'], True)['state'], 'MANAGING')
        self.assertEqual(len(self.x.algos), 2)

    def test_unknown_entry_response_is_not_resent_on_restart(self):
        self.authorize()
        self.x.timeout = True
        runner = self.runner()
        with self.assertRaises(Exception):
            runner.open(self.plan['plan_id'], 1, True)
        sid = self.store.sessions()[0]['id']
        self.store.close()
        self.store = StateStore(self.path)
        self.service = PlanService(self.store, 'fixture')
        self.new_runner().manage(sid, True)
        self.assertEqual(len([c for c in self.x.calls if c[0] == 'POST' and c[1].endswith('/order')]), 1)

    def test_source_expires_during_last_account_read_before_post(self):
        self.authorize()
        runner = self.runner()
        original = runner._snapshot
        calls = []
        def snapshot_then_expire(*args):
            snap = original(*args)
            calls.append(1)
            if len(calls) == 2:
                self.f.clock[1] = self.body['expires_at'] + 1
            return snap
        runner._snapshot = snapshot_then_expire
        with self.assertRaisesRegex(ValueError, 'SOURCE_NOT_CURRENT'):
            runner.open(self.plan['plan_id'], 1, True)
        self.assertEqual(self.x.calls, [])
        self.assertEqual(self.store.intents()[0]['state'], 'REJECTED')
        sid = self.store.sessions()[0]['id']
        runner.manage(sid, True)
        self.assertEqual(self.x.calls, [])

    def test_source_service_unavailable_cancels_pending_limit_without_reentry(self):
        self.authorize()
        self.x.limit_pending = True
        runner = self.runner()
        opened = runner.open(self.plan['plan_id'], 1, True)
        self.provider = Mock(side_effect=OSError('unavailable'))
        runner.manage(opened['session_id'], True)
        self.assertEqual(next(iter(self.x.orders.values()))['status'], 'CANCELED')
        self.assertEqual(len([c for c in self.x.calls if c[0] == 'POST']), 1)

    def test_bounded_monitor_drains_pending_entry_before_exit(self):
        from agentrader.shared.runtime import supervise_session
        self.authorize()
        self.x.limit_pending = True
        runner = self.runner()
        opened = runner.open(self.plan['plan_id'], 1, True)
        supervise_session(runner, opened['session_id'], emit=lambda _: None,
                          execute=True, iterations=1, drain_on_exit=True)
        self.assertEqual(next(iter(self.x.orders.values()))['status'], 'CANCELED')
        self.assertEqual(self.store.sessions(), [])

    def test_stopping_monitor_preserves_filled_position_protection(self):
        self.authorize()
        runner = self.runner()
        opened = runner.open(self.plan['plan_id'], 1, True)
        self.assertEqual(runner.stop(opened['session_id'], execute=True)['state'], 'MANAGING')
        self.assertEqual(len(self.x.algos), 2)
        self.assertTrue(all(a['algoStatus'] == 'NEW' for a in self.x.algos.values()))
        self.assertFalse(any(c[0] == 'DELETE' for c in self.x.calls))

    def test_fill_during_source_revocation_cancel_is_protected(self):
        self.authorize()
        self.x.limit_pending = True
        runner = self.runner()
        opened = runner.open(self.plan['plan_id'], 1, True)
        original_request = self.x.request
        def request(method, path, params):
            if method == 'DELETE' and path.endswith('/order'):
                from agentrader.bot.risk import number
                order = self.x.orders[params['origClientOrderId']]
                order['executedQty'] = order['origQty']
                self.x.amount = number(order['origQty'])
                self.x.trades.append(dict(orderId=order['orderId'], qty=order['origQty'], side=order['side']))
            return original_request(method, path, params)
        self.x.request = request
        self.f.clock[1] = self.body['expires_at'] + 1
        result = runner.manage(opened['session_id'], True)
        self.assertEqual(result['state'], 'MANAGING')
        self.assertEqual(len(self.x.algos), 2)
        self.assertEqual(len([c for c in self.x.calls if c[0] == 'POST' and c[1].endswith('/order')]), 1)


class ContinuityGateTests(unittest.TestCase):
    def fixture(self, root):
        sources = ['agentrader/chart/chart_clock.py', 'agentrader/chart/chart_market.py', 'agentrader/shared/market_feed.py',
                   'agentrader/integration/shadow_tracking.py', 'scripts/chart/build_binding_evidence.py',
                   'scripts/chart/observe_demo_continuity.py', 'tests/test_clock_renewal.py']
        for name in sources:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'observed candidate')
        (root / 'reports').mkdir()
        (root / 'reports/continuity-delivery-20261113.json').write_text(json.dumps(dict(
            sources={name:hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sources})))
        from agentrader.shared.market_environment import SOURCE, ENVIRONMENT
        report = dict(state='COMPLETED', passed=True, source=SOURCE, environment=ENVIRONMENT,
                      elapsed_seconds=1801, closed_events=[dict(time=i*60) for i in range(30)],
                      violations=[], outages=[], account_requests=0, order_requests=0)
        path = root / 'reports/demo-continuity-observation-20261113.json'
        path.write_text(json.dumps(report))
        return path, report

    def test_passed_observation_rejects_changed_source_gap_or_long_outage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, report = self.fixture(root)
            self.assertTrue(require_demo_acceptance(root))
            report['closed_events'][15]['time'] += 60
            path.write_text(json.dumps(report))
            with self.assertRaises(ValueError):require_demo_acceptance(root)
            report['closed_events'][15]['time'] -= 60
            report['outages'] = [dict(seconds=31, end=50)]
            path.write_text(json.dumps(report))
            with self.assertRaises(ValueError):require_demo_acceptance(root)
            report['outages'] = []
            path.write_text(json.dumps(report))
            (root / 'agentrader/shared/market_feed.py').write_text('changed after observation')
            with self.assertRaises(ValueError):require_demo_acceptance(root)

    def test_missing_or_failed_observation_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, 'ACCEPTANCE_REQUIRED'):
                require_demo_acceptance(root)


class LocalPreviewTransportTests(unittest.TestCase):
    def server(self, status, payload):
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading
        calls = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                calls.append(self.path)
                self.send_response(status)
                if status == 302:
                    self.send_header('Location', 'https://fapi.binance.com/never-follow-this')
                self.end_headers()
                self.wfile.write(payload)
            def log_message(self, *args):pass
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def close():
            server.shutdown()
            server.server_close()
            thread.join(2)
        self.addCleanup(close)
        return server.server_port, calls

    def test_loopback_get_has_exact_reference_and_ignores_proxy(self):
        event = 'a'*64
        payload = dict(event_id=event, version=2, workspace_id='main')
        port, calls = self.server(200, json.dumps(payload).encode())
        with patch.dict('os.environ', {'HTTP_PROXY':'http://127.0.0.1:1'}):
            self.assertEqual(local_preview_provider('main', event, 2, port)(), payload)
        self.assertEqual(calls, [f'/api/workspaces/main/shadow-events/{event}/preview?version=2'])

    def test_redirect_is_never_followed(self):
        from urllib.error import HTTPError
        port, calls = self.server(302, b'')
        with self.assertRaises(HTTPError) as context:
            local_preview_provider('main', 'a'*64, 1, port)()
        self.assertEqual(context.exception.code, 302)
        self.assertEqual(len(calls), 1)

    def test_wrong_version_response_is_rejected(self):
        port, _ = self.server(200, json.dumps(dict(event_id='a'*64, version=2, workspace_id='main')).encode())
        with self.assertRaisesRegex(ValueError, 'REFERENCE_MISMATCH'):
            local_preview_provider('main', 'a'*64, 1, port)()

