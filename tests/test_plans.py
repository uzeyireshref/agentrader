import copy
import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from agentrader.execution import DurableExchange
from agentrader.plans import PlanService, example_plan, validate_plan, timestamp
from agentrader.plan_execution import run_plan, prepare
from agentrader.risk import RiskLimits
from agentrader.state import StateStore
from agentrader.watchdog import Watchdog
from test_watchdog import WatchExchange
from test_orders import SYMBOL


class PlanExchange(WatchExchange):
    def __init__(self):
        super().__init__()
        self.price = '80000'
        self.fill_price = '80000'

    def get(self, path, params=None):
        if path.endswith('premiumIndex'):
            return {'markPrice': self.price, 'time': int(time.time() * 1000)}
        return super().get(path, params)

    def request(self, method, path, params):
        result = super().request(method, path, params)
        if path.endswith('/order') and method == 'POST':
            result['avgPrice'] = self.fill_price
        return result


class PlansTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.path = Path(self.folder.name) / 'state.sqlite3'
        self.store = StateStore(self.path)
        self.service = PlanService(self.store, 'owner')
        self.plan = example_plan()
        self.x = PlanExchange()

    def tearDown(self):
        self.store.close()
        self.folder.cleanup()

    def create(self, mode='A', name=None):
        plan = copy.deepcopy(self.plan)
        plan['mode'] = mode
        if name:
            plan['plan_id'] = name
        return self.service.create(plan, 'owner')

    def authorize(self, mode='A'):
        request = self.create(mode)
        self.service.authorize(self.plan['plan_id'], 1, request['authorization_token'],
                               'approve' if mode == 'A' else 'activate', 'owner')
        return request

    def run_plan(self, execute=True):
        return run_plan(self.service, self.x, RiskLimits(), self.plan['plan_id'], 1, execute)

    def test_no_authorization_no_entry(self):
        self.create()
        with self.assertRaisesRegex(ValueError, 'yetkili'):
            self.run_plan()
        self.assertEqual(self.x.calls, [])

    def test_mode_a_exact_authorization_then_single_execution(self):
        request = self.authorize()
        duplicate = self.service.authorize(self.plan['plan_id'], 1, request['authorization_token'], 'approve', 'owner')
        self.assertTrue(duplicate['duplicate'])
        result = self.run_plan()
        self.assertEqual(result['state'], 'MANAGING')
        self.assertTrue(result['executed'])
        with self.assertRaises(ValueError):
            self.run_plan()
        entries = [p for m, path, p in self.x.calls if path.endswith('/order') and p.get('reduceOnly') != 'true']
        self.assertEqual(len(entries), 1)
        self.assertEqual(Decimal(entries[0]['quantity']), Decimal('.0007'))

    def test_mode_b_requires_activation_not_approval(self):
        request = self.create('B')
        with self.assertRaisesRegex(ValueError, 'moduyla'):
            self.service.authorize(self.plan['plan_id'], 1, request['authorization_token'], 'approve', 'owner')
        self.service.authorize(self.plan['plan_id'], 1, request['authorization_token'], 'activate', 'owner')
        self.assertEqual(self.run_plan()['state'], 'MANAGING')

    def test_wrong_actor_and_wrong_token(self):
        request = self.create()
        for actor, token in [('intruder', request['authorization_token']), ('owner', 'wrong')]:
            with self.assertRaises(ValueError):
                self.service.authorize(self.plan['plan_id'], 1, token, 'approve', actor)
        self.assertEqual(self.x.calls, [])

    def test_expired_approval_cannot_be_refreshed_by_duplicate_click(self):
        request = self.authorize()
        until = self.service.show(self.plan['plan_id'], 1)['approval_until']
        with self.assertRaisesRegex(ValueError, 'EXPIRED'):
            self.service.authorize(self.plan['plan_id'], 1, request['authorization_token'], 'approve', 'owner', now=until + 1)
        self.assertEqual(self.service.show(self.plan['plan_id'], 1)['state'], 'EXPIRED')

    def test_revision_revokes_old_authorization(self):
        first = self.authorize()
        second = copy.deepcopy(self.plan)
        second['version'] = 2
        second['stop'] = '78500'
        self.service.create(second, 'owner')
        with self.assertRaises(ValueError):
            self.service.authorize(self.plan['plan_id'], 2, first['authorization_token'], 'approve', 'owner')
        self.assertEqual(self.service.show(self.plan['plan_id'], 1)['state'], 'SUPERSEDED')
        self.assertEqual(self.service.show(self.plan['plan_id'], 2)['state'], 'PENDING_APPROVAL')

    def test_conflicting_authorized_plans_rejected(self):
        self.authorize()
        request = self.create(name='conflict')
        with self.assertRaisesRegex(ValueError, 'başka etkin'):
            self.service.authorize('conflict', 1, request['authorization_token'], 'approve', 'owner')

    def test_condition_not_met_does_not_consume_authorization(self):
        self.plan['entry']['trigger_price'] = '79900'
        self.authorize()
        result = self.run_plan()
        self.assertEqual(result['state'], 'WAITING_CONDITION')
        self.assertEqual(result['observation']['mark_price'], '80000')
        self.assertEqual(result['observation']['trigger_distance'], '100')
        import json
        audit = self.store.db.execute("SELECT payload FROM events WHERE event='plan_price_check'").fetchone()
        self.assertEqual(json.loads(audit[0]), result['observation'])
        self.assertEqual(self.service.show(self.plan['plan_id'], 1)['state'], 'AUTHORIZED')
        self.assertEqual(self.x.calls, [])

    def test_price_drift_requires_new_plan(self):
        self.authorize()
        self.x.price = '79000'
        with self.assertRaisesRegex(ValueError, 'tolerans'):
            self.run_plan()
        self.assertEqual(self.x.calls, [])
        import json
        audit = json.loads(self.store.db.execute("SELECT payload FROM events WHERE event='plan_price_check'").fetchone()[0])
        self.assertEqual(audit['decision'], 'BLOCKED')
        self.assertEqual(audit['mark_price'], '79000')
        self.assertIn('tolerans', audit['reason'])

    def test_preview_does_not_consume_or_submit(self):
        self.authorize()
        self.assertEqual(self.run_plan(False)['state'], 'READY')
        self.assertEqual(self.service.show(self.plan['plan_id'], 1)['state'], 'AUTHORIZED')
        self.assertEqual(self.x.calls, [])

    def test_cancel_open_plan_preserves_position_and_protection(self):
        self.authorize()
        self.run_plan()
        count = len(self.x.calls)
        result = self.service.cancel(self.plan['plan_id'], 1, 'owner')
        self.assertTrue(result['entry_revoked'])
        self.assertEqual(len(self.x.calls), count)
        self.assertGreater(self.x.qty, 0)
        self.assertTrue(all(a['algoStatus'] == 'NEW' for a in self.x.algos.values()))

    def test_reject_and_cancel_prevent_execution(self):
        for reject in (False, True):
            plan = copy.deepcopy(self.plan)
            plan['plan_id'] = 'reject' if reject else 'cancel'
            self.service.create(plan, 'owner')
            self.service.cancel(plan['plan_id'], 1, 'owner', reject)
            with self.assertRaises(ValueError):
                run_plan(self.service, self.x, RiskLimits(), plan['plan_id'], 1, True)
        self.assertEqual(self.x.calls, [])

    def test_close_syncs_plan_and_releases_symbol_slot(self):
        self.authorize()
        self.run_plan()
        Watchdog(self.x, self.store).tick(True, close=True)
        self.assertEqual(self.service.show(self.plan['plan_id'], 1)['state'], 'CLOSED')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM plan_slots').fetchone()[0], 0)

    def test_claim_survives_restart_and_cannot_be_claimed_twice(self):
        self.authorize()
        action = self.service.claim(self.plan['plan_id'], 1, 'session-crash')
        self.store.close()
        self.store = StateStore(self.path)
        self.service = PlanService(self.store, 'owner')
        with self.assertRaises(ValueError):
            self.service.claim(self.plan['plan_id'], 1, 'other')
        self.assertEqual(self.service.show(self.plan['plan_id'], 1)['action_id'], action)
        self.assertEqual(self.x.calls, [])

    def test_raw_entry_cannot_bypass_new_plan_gate(self):
        engine = DurableExchange(self.x, self.store)
        engine.configure_entry('80000', '78400')
        with self.assertRaisesRegex(ValueError, 'yetki denetimi'):
            engine.request('POST', '/fapi/v1/order', {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': '.0007', 'newClientOrderId': 'bypass'})
        self.assertEqual(self.x.calls, [])

    def test_risk_violation_rejects_authorized_plan_without_submission(self):
        self.plan['sizing']['amount'] = '1000'
        self.authorize()
        with self.assertRaisesRegex(ValueError, 'sınır'):
            self.run_plan()
        self.assertEqual(self.x.calls, [])

    def test_fill_slippage_outside_authorized_scope_closes_owned_position(self):
        self.authorize()
        self.x.fill_price = '82000'
        result = self.run_plan()
        self.assertEqual(result['state'], 'CLOSED')
        self.assertEqual(self.x.qty, 0)
        self.assertIsNotNone(self.store.halt_reason())

    def test_schema_rejects_unsupported_and_invalid_plans(self):
        variants = []
        for field, value in [('environment', 'live'), ('direction', 'SHORT'), ('version', True), ('mode', 'C'), ('max_runs', 2), ('stop', 'NaN')]:
            p = copy.deepcopy(self.plan)
            p[field] = value
            variants.append(p)
        for change in ('margin', 'scale', 'break_even', 'sum', 'unknown'):
            p = copy.deepcopy(self.plan)
            if change == 'margin': p['sizing']['kind'] = 'MARGIN'
            elif change == 'scale': p['management']['allow_scale_in'] = True
            elif change == 'break_even': p['management']['break_even_after_target'] = 1
            elif change == 'sum': p['targets'][0]['fraction'] = '.5'
            else: p['mystery'] = 1
            variants.append(p)
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                validate_plan(variant)

    def test_symbol_steps_minimum_and_max_loss_sizing(self):
        plan = copy.deepcopy(self.plan)
        plan['sizing'] = {'kind': 'MAX_LOSS', 'amount': '1.12', 'currency': 'USDT'}
        self.assertEqual(Decimal(prepare(plan, SYMBOL, {'markPrice': '80000'}, RiskLimits())['quantity']), Decimal('.0007'))
        plan['stop'] = '78400.03'
        with self.assertRaisesRegex(ValueError, 'fiyat adım'):
            prepare(plan, SYMBOL, {'markPrice': '80000'}, RiskLimits())

    def test_existing_database_tables_preserved(self):
        self.store.event('legacy', {'preserved': True})
        self.create()
        self.assertIsNotNone(self.store.db.execute("SELECT 1 FROM events WHERE event='legacy'").fetchone())
        self.assertEqual(self.store.db.execute('PRAGMA user_version').fetchone()[0], 1)

    def test_unreached_trigger_far_from_reference_still_waits(self):
        self.authorize('B')
        self.x.price = '85000'
        self.assertEqual(self.run_plan()['state'], 'WAITING_CONDITION')
        self.assertEqual(self.x.calls, [])

    def test_authorization_expiring_after_intent_reservation_prevents_post(self):
        self.authorize()
        original = self.store.reserve
        def expire_after_reserve(*args):
            saved = original(*args)
            with self.store.db:
                self.store.db.execute('UPDATE plan_versions SET approval_until=0')
            return saved
        with patch.object(self.store, 'reserve', side_effect=expire_after_reserve):
            with self.assertRaisesRegex(ValueError, 'süresi doldu'):
                self.run_plan()
        self.assertEqual(self.x.calls, [])
        self.assertEqual(self.store.intents()[0]['state'], 'REJECTED')

    def test_unsubmitted_claim_can_be_explicitly_canceled_after_restart(self):
        self.authorize()
        self.service.claim(self.plan['plan_id'], 1, 'never-submitted')
        self.assertEqual(self.service.cancel(self.plan['plan_id'], 1, 'owner')['state'], 'CANCELED')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM plan_slots').fetchone()[0], 0)
        with self.assertRaises(ValueError):
            self.run_plan()

    def test_plan_owner_cannot_be_replaced(self):
        with self.assertRaisesRegex(ValueError, 'başka'):
            PlanService(self.store, 'intruder')

    def test_sqlite_plan_tampering_is_rejected(self):
        self.create()
        changed = copy.deepcopy(self.plan)
        changed['stop'] = '78500'
        import json
        with self.store.db:
            self.store.db.execute('UPDATE plan_versions SET body=?', (json.dumps(changed),))
        with self.assertRaisesRegex(ValueError, 'özeti'):
            self.service.show(self.plan['plan_id'], 1)
