import copy
import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from agentrader.exchange import ExchangeError
from agentrader.management import split_targets
from agentrader.plan_execution import run_plan, prepare
from agentrader.plans import PlanService, example_plan, validate_plan
from agentrader.risk import RiskLimits
from agentrader.state import StateStore
from agentrader.watchdog import Watchdog, OwnershipError
from test_plans import PlanExchange
from test_orders import SYMBOL


class PartialExchange(PlanExchange):
    def __init__(self, partial_entry=False):
        super().__init__()
        self.partial_entry = partial_entry
        self.partial_exit = not partial_entry
        self.reject_exit = False

    def request(self, method, path, params):
        if method == 'POST' and path.endswith('/order'):
            reduce = params.get('reduceOnly') == 'true'
            if reduce and self.reject_exit:
                raise ExchangeError('Invalid amount', -4003)
            if (reduce and self.partial_exit) or (not reduce and self.partial_entry):
                self.partial_exit = False
                self.partial_entry = False
                filled = Decimal(params['quantity']) / 2
                result = super().request(method, path, dict(params, quantity=str(filled)))
                self.calls[-1] = (method, path, dict(params))
                result.update(status='PARTIALLY_FILLED', origQty=params['quantity'])
                return result
        return super().request(method, path, params)


class StagedTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.path = Path(self.folder.name) / 'state.sqlite3'
        self.store = StateStore(self.path)
        self.service = PlanService(self.store, 'owner')
        self.x = PlanExchange()
        self.plan = example_plan()
        self.plan['sizing']['amount'] = '64'
        self.plan['targets'] = [{'price': '81000', 'fraction': '.5'}, {'price': '82000', 'fraction': '.5'}]
        self.plan['management']['break_even_after_target'] = 1

    def tearDown(self):
        self.store.close()
        self.folder.cleanup()

    def open(self):
        request = self.service.create(self.plan, 'owner')
        self.service.authorize(self.plan['plan_id'], 1, request['authorization_token'], 'approve', 'owner')
        return run_plan(self.service, self.x, RiskLimits(), self.plan['plan_id'], 1, True)

    def watcher(self):
        return Watchdog(self.x, self.store)

    def restart(self):
        self.store.close()
        self.store = StateStore(self.path)
        self.service = PlanService(self.store, 'owner')
        return self.watcher()

    def reductions(self):
        return [p for method, path, p in self.x.calls if method == 'POST' and path.endswith('/order') and p.get('reduceOnly') == 'true']

    def test_first_target_partial_close_and_stop_then_final_close(self):
        self.open()
        self.x.price = '81000'
        report = self.watcher().tick(True)
        self.assertEqual(report['position'], '0.0004')
        self.assertEqual(Decimal(report['stop']), 80000)
        s = self.store.sessions()[0]
        self.assertEqual(s['target_management']['targets'][0]['status'], 'COMPLETED')
        self.assertEqual(s['stop_transition']['state'], 'APPLIED')
        stops = [a for a in self.x.algos.values() if a['type'] == 'STOP_MARKET']
        self.assertEqual(sum(a['algoStatus'] == 'NEW' for a in stops), 1)
        self.x.price = '82000'
        self.assertEqual(self.watcher().tick(True)['status'], 'closed')
        self.assertEqual(self.x.qty, 0)
        self.assertEqual([Decimal(p['quantity']) for p in self.reductions()], [Decimal('.0004'), Decimal('.0004')])
        self.assertEqual(self.service.show(self.plan['plan_id'], 1)['state'], 'CLOSED')

    def test_stop_transition_uses_remaining_reduce_only_quantity_before_cancel(self):
        self.open()
        original = self.x.request
        def reject_duplicate_close_all(method, path, params):
            if (method == 'POST' and path.endswith('algoOrder') and params['type'] == 'STOP_MARKET'
                    and params.get('closePosition') == 'true'
                    and any(a['orderType'] == 'STOP_MARKET' and a['algoStatus'] == 'NEW'
                            for a in self.x.algos.values())):
                raise ExchangeError('Duplicate close-all stop', -4130, 400)
            return original(method, path, params)
        self.x.price = '81000'
        with patch.object(self.x, 'request', side_effect=reject_duplicate_close_all):
            self.assertEqual(self.watcher().tick(True)['status'], 'protected')
        s = self.store.sessions()[0]
        self.assertEqual(s['stop_transition']['state'], 'APPLIED')
        replacement = s['protections'][-1]
        self.assertNotIn('closePosition', replacement)
        self.assertEqual(replacement['reduceOnly'], 'true')
        self.assertEqual(Decimal(replacement['quantity']), self.x.qty)
        wrong = dict(replacement, quantity='0.0001')
        response = dict(self.x.algos[replacement['clientAlgoId']], quantity='0.0001')
        self.assertFalse(self.watcher().valid_protection(s, wrong, response))
        self.assertEqual(self.x.algos[s['protections'][0]['clientAlgoId']]['algoStatus'], 'CANCELED')
        count = len(self.x.calls)
        self.restart().tick(True)
        self.assertEqual(len(self.x.calls), count)

    def test_rejected_replacement_does_not_get_masked_by_not_found(self):
        self.open()
        self.x.price = '81000'
        self.x.reject_stop = True
        self.assertEqual(self.watcher().tick(True)['status'], 'closed')
        failures = self.store.db.execute("SELECT payload FROM events WHERE event='order_submission_failed'").fetchall()
        import json
        self.assertEqual(json.loads(failures[0][0])['code'], -2021)
        self.assertFalse(any(r['state'] == 'UNKNOWN' for r in self.store.intents()))

    def test_restart_after_first_target_does_not_repeat_exit_or_stop(self):
        self.open()
        self.x.price = '81000'
        self.watcher().tick(True)
        count = len(self.x.calls)
        restarted = self.restart()
        self.assertEqual(restarted.tick(True)['status'], 'protected')
        self.assertEqual(len(self.x.calls), count)
        self.x.price = '82000'
        restarted.tick(True)
        self.assertEqual(len(self.reductions()), 2)

    def test_immediate_plan_restarts_before_target_without_duplicate_entry(self):
        self.plan['entry']['condition'] = 'IMMEDIATE'
        self.plan['entry']['trigger_price'] = None
        self.open()
        session_id = self.store.sessions()[0]['id']
        entry_id = self.store.sessions()[0]['entry_id']
        before = len(self.x.calls)
        restarted = self.restart()
        self.assertEqual(restarted.tick(True)['status'], 'protected')
        self.assertEqual(self.store.sessions()[0]['id'], session_id)
        self.assertEqual(self.store.sessions()[0]['entry_id'], entry_id)
        self.assertEqual(len(self.x.calls), before)
        self.x.price = '81000'
        restarted.tick(True)
        self.assertEqual(self.x.qty, Decimal('.0004'))
        self.assertEqual(len(self.reductions()), 1)
        self.assertEqual(Decimal(self.store.sessions()[0]['plan']['stop']), Decimal('80000'))

    def test_crash_after_exit_fill_before_local_completion_does_not_repeat(self):
        self.open()
        self.x.price = '81000'
        original = self.x.request
        def crash(method, path, params):
            result = original(method, path, params)
            if method == 'POST' and path.endswith('/order') and params.get('reduceOnly') == 'true':
                raise SystemExit('process terminated after fill')
            return result
        with patch.object(self.x, 'request', side_effect=crash):
            with self.assertRaises(SystemExit):
                self.watcher().tick(True)
        self.assertEqual(self.x.qty, Decimal('.0004'))
        restarted = self.restart()
        self.assertEqual(restarted.tick(True)['status'], 'protected')
        self.assertEqual(len(self.reductions()), 1)
        self.assertEqual(Decimal(self.store.sessions()[0]['plan']['stop']), 80000)

    def test_crash_before_exit_submission_uses_saved_same_id_once(self):
        self.open()
        self.x.price = '81000'
        watcher = self.watcher()
        original = watcher.engine.request
        def crash(method, path, params):
            if method == 'POST' and path.endswith('/order') and params.get('reduceOnly') == 'true':
                raise SystemExit('terminated before durable reservation')
            return original(method, path, params)
        with patch.object(watcher.engine, 'request', side_effect=crash):
            with self.assertRaises(SystemExit):
                watcher.tick(True)
        saved = self.store.sessions()[0]['target_management']['targets'][0]['attempts'][0]
        self.restart().tick(True)
        self.assertEqual([p['newClientOrderId'] for p in self.reductions()], [saved])

    def test_crash_after_new_stop_acceptance_preserves_old_until_restart(self):
        self.open()
        self.x.price = '81000'
        original = self.x.request
        def crash(method, path, params):
            result = original(method, path, params)
            if method == 'POST' and path.endswith('algoOrder') and params.get('triggerPrice') == '80000':
                raise SystemExit('terminated before retiring previous stop')
            return result
        with patch.object(self.x, 'request', side_effect=crash):
            with self.assertRaises(SystemExit):
                self.watcher().tick(True)
        self.assertEqual(sum(a['algoStatus'] == 'NEW' and a['type'] == 'STOP_MARKET' for a in self.x.algos.values()), 2)
        stops_before = len(self.x.algos)
        self.restart().tick(True)
        self.assertEqual(len(self.x.algos), stops_before)
        self.assertEqual(sum(a['algoStatus'] == 'NEW' and a['type'] == 'STOP_MARKET' for a in self.x.algos.values()), 1)
        self.assertEqual(len(self.reductions()), 1)

    def test_partial_exit_is_settled_then_only_remainder_is_sent(self):
        self.x = PartialExchange()
        self.open()
        self.x.price = '81000'
        self.watcher().tick(True)
        self.assertEqual(self.x.qty, Decimal('.0006'))
        self.assertNotIn('stop_transition', self.store.sessions()[0])
        self.restart().tick(True)
        self.assertEqual(self.x.qty, Decimal('.0004'))
        self.assertEqual([Decimal(p['quantity']) for p in self.reductions()], [Decimal('.0004'), Decimal('.0002')])
        self.assertEqual(Decimal(self.store.sessions()[0]['plan']['stop']), 80000)

    def test_lost_exit_response_is_queried_not_repeated(self):
        self.open()
        self.x.price = '81000'
        original = self.x.request
        def lost(method, path, params):
            result = original(method, path, params)
            if method == 'POST' and path.endswith('/order') and params.get('reduceOnly') == 'true':
                raise ExchangeError('response lost after fill')
            return result
        with patch.object(self.x, 'request', side_effect=lost):
            self.watcher().tick(True)
        self.restart().tick(True)
        self.assertEqual(len(self.reductions()), 1)

    def test_unknown_reserved_exit_not_found_never_resubmits(self):
        self.open()
        self.x.price = '81000'
        watcher = self.watcher()
        original = self.store.reserve
        def reserve_then_crash(*args):
            result = original(*args)
            raise SystemExit('crash between reservation and HTTP')
        with patch.object(self.store, 'reserve', side_effect=reserve_then_crash):
            with self.assertRaises(SystemExit):
                watcher.tick(True)
        with self.assertRaises(ExchangeError):
            self.restart().tick(True)
        self.assertEqual(len(self.reductions()), 0)
        self.assertTrue(all(a['algoStatus'] == 'NEW' for a in self.x.algos.values()))

    def test_stop_replacement_rejection_closes_without_dropping_old_first(self):
        self.open()
        self.x.price = '81000'
        self.x.reject_stop = True
        self.assertEqual(self.watcher().tick(True)['status'], 'closed')
        self.assertEqual(self.x.qty, 0)
        self.assertIsNotNone(self.store.halt_reason())
        calls = self.x.calls
        final_sell = max(i for i, (m, path, p) in enumerate(calls) if m == 'POST' and path.endswith('/order'))
        cancellations = [i for i, (m, path, p) in enumerate(calls) if m == 'DELETE' and path.endswith('algoOrder')]
        self.assertTrue(all(i > final_sell for i in cancellations))

    def test_no_permission_no_break_even(self):
        self.plan['management']['break_even_after_target'] = None
        self.open()
        self.x.price = '81000'
        self.watcher().tick(True)
        self.assertEqual(Decimal(self.store.sessions()[0]['plan']['stop']), 78400)

    def test_retracement_to_moved_stop_closes_remaining_position(self):
        self.open()
        self.x.price = '81000'
        self.watcher().tick(True)
        self.x.price = '79999'
        self.assertEqual(self.watcher().tick(True)['status'], 'closed')
        self.assertEqual(self.x.qty, 0)

    def test_readonly_at_target_does_not_trade(self):
        self.open()
        self.x.price = '81000'
        before = len(self.x.calls)
        self.assertEqual(self.watcher().tick(False)['status'], 'observed')
        self.assertEqual(len(self.x.calls), before)

    def test_manual_trade_at_target_blocks_all_mutations(self):
        self.open()
        self.x.price = '81000'
        self.x.trades.append({'orderId': 9999, 'side': 'BUY', 'qty': '.0001'})
        self.x.qty += Decimal('.0001')
        before = len(self.x.calls)
        with self.assertRaises(OwnershipError):
            self.watcher().tick(True)
        self.assertEqual(len(self.x.calls), before)

    def test_target_rounding_preserves_total_and_last_gets_remainder(self):
        self.plan['sizing']['amount'] = '60'
        result = prepare(self.plan, SYMBOL, {'markPrice': '80000'}, RiskLimits())
        parts = split_targets(result['quantity'], self.plan['targets'], result['lot_rules'])
        self.assertEqual([Decimal(p['quantity']) for p in parts], [Decimal('.0003'), Decimal('.0004')])
        self.assertEqual(sum(Decimal(p['quantity']) for p in parts), Decimal(result['quantity']))

    def test_zero_lot_target_is_rejected_before_entry(self):
        self.plan['targets'][0]['fraction'] = '.01'
        self.plan['targets'][1]['fraction'] = '.99'
        with self.assertRaisesRegex(ValueError, 'Hedef payı'):
            prepare(self.plan, SYMBOL, {'markPrice': '80000'}, RiskLimits())
        self.assertEqual(self.x.calls, [])

    def test_invalid_break_even_and_target_definitions(self):
        for value in (0, 2, True, '1', -1):
            p = copy.deepcopy(self.plan)
            p['management']['break_even_after_target'] = value
            with self.assertRaises(ValueError):
                validate_plan(p)
        p = copy.deepcopy(self.plan)
        p['targets'][1]['price'] = '80500'
        with self.assertRaises(ValueError):
            validate_plan(p)

    def test_gap_through_both_targets_exits_only_total_position(self):
        self.open()
        self.x.price = '82500'
        self.assertEqual(self.watcher().tick(True)['status'], 'closed')
        self.assertEqual(sum(Decimal(p['quantity']) for p in self.reductions()), Decimal('.0008'))
        self.assertEqual(self.x.qty, 0)

    def test_partial_entry_allocates_targets_from_actual_fills(self):
        self.x = PartialExchange(partial_entry=True)
        self.open()
        s = self.store.sessions()[0]
        self.assertEqual(self.x.qty, Decimal('.0004'))
        self.assertEqual([Decimal(t['quantity']) for t in s['target_management']['targets']], [Decimal('.0002'), Decimal('.0002')])
        self.x.price = '81000'
        self.watcher().tick(True)
        self.assertEqual(self.x.qty, Decimal('.0002'))

    def test_break_even_rounds_actual_entry_down_to_price_tick(self):
        self.plan['sizing']['amount'] = '66'
        self.x.fill_price = '80000.09'
        self.open()
        self.x.price = '81000'
        self.watcher().tick(True)
        self.assertEqual(Decimal(self.store.sessions()[0]['plan']['stop']), Decimal('80000.0'))

    def test_runtime_management_cannot_expand_original_authorization(self):
        self.plan['management']['break_even_after_target'] = None
        self.open()
        s = self.store.sessions()[0]
        s['plan']['management']['break_even_after_target'] = 1
        self.store.save_session(s)
        self.x.price = '81000'
        before = len(self.x.calls)
        with self.assertRaises(OwnershipError):
            self.watcher().tick(True)
        self.assertEqual(len(self.x.calls), before)

    def test_stale_price_cannot_trigger_exit_or_stop_change(self):
        self.open()
        self.x.price = '81000'
        original = self.x.get
        def stale(path, params=None):
            result = original(path, params)
            if path.endswith('premiumIndex'):
                result['time'] -= 60000
            return result
        before = len(self.x.calls)
        with patch.object(self.x, 'get', side_effect=stale):
            with self.assertRaises(ExchangeError):
                self.watcher().tick(True)
        self.assertEqual(len(self.x.calls), before)

    def test_lost_old_stop_cancel_response_is_queried(self):
        self.open()
        self.x.price = '81000'
        old_id = self.store.sessions()[0]['protections'][0]['clientAlgoId']
        original = self.x.request
        def lost(method, path, params):
            result = original(method, path, params)
            if method == 'DELETE' and path.endswith('algoOrder') and params['clientAlgoId'] == old_id:
                raise ExchangeError('cancel response lost')
            return result
        with patch.object(self.x, 'request', side_effect=lost):
            self.assertEqual(self.watcher().tick(True)['status'], 'protected')
        self.assertEqual(self.x.algos[old_id]['algoStatus'], 'CANCELED')
        self.assertEqual(self.x.qty, Decimal('.0004'))
        self.assertEqual(len(self.reductions()), 1)

    def test_false_completed_record_cannot_advance_management(self):
        self.open()
        s = self.store.sessions()[0]
        s['target_management']['targets'][0]['status'] = 'COMPLETED'
        self.store.save_session(s)
        before = len(self.x.calls)
        with self.assertRaisesRegex(ValueError, 'gerçekleşmesiyle'):
            self.watcher().tick(True)
        self.assertEqual(len(self.x.calls), before)

    def test_runtime_target_quantity_cannot_exceed_approved_fraction(self):
        self.open()
        s = self.store.sessions()[0]
        s['target_management']['targets'][0]['quantity'] = '.0008'
        self.store.save_session(s)
        before = len(self.x.calls)
        self.x.price = '81000'
        with self.assertRaises(OwnershipError):
            self.watcher().tick(True)
        self.assertEqual(len(self.x.calls), before)

    def test_pending_target_cannot_change_into_new_entry(self):
        self.open()
        self.x.price = '81000'
        watcher = self.watcher()
        original = watcher.engine.request
        def crash(method, path, params):
            if method == 'POST' and path.endswith('/order'):
                raise SystemExit('before target submission')
            return original(method, path, params)
        with patch.object(watcher.engine, 'request', side_effect=crash):
            with self.assertRaises(SystemExit):
                watcher.tick(True)
        s = self.store.sessions()[0]
        s['exits'][0]['side'] = 'BUY'
        self.store.save_session(s)
        before = len(self.x.calls)
        with self.assertRaises(OwnershipError):
            self.restart().tick(True)
        self.assertEqual(len(self.x.calls), before)
