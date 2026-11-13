import copy
import unittest
from decimal import Decimal

from agentrader.plan_v2 import validate_v2
from agentrader.trailing import advance_trailing
from agentrader.v2_runner import V2Runner
from agentrader.plans import PlanService
from agentrader.state import StateStore
from agentrader.exchange import ExchangeError
from test_plan_v2 import plan_v2
import test_v2_runner as runner_fixtures


POLICY=dict(activation_price='80800',distance_bps='100',min_step_bps='10')


class TrailingPolicyTests(unittest.TestCase):
    def test_legacy_plan_is_unchanged_and_disabled(self):
        p=plan_v2();before=copy.deepcopy(p)
        validate_v2(p)
        self.assertEqual(p,before)
        self.assertNotIn('trailing',p['management'])

    def test_policy_is_explicit_and_invalid_bounds_are_rejected(self):
        for change in ({'distance_bps':'0'},{'min_step_bps':'101'},
                       {'activation_price':'70000'},{'activation_price':'90000'}, {'distance_bps':'NaN'}):
            p=plan_v2();p['management']['trailing']=POLICY|change
            with self.subTest(change=change),self.assertRaises(ValueError):validate_v2(p)

    def test_watermark_is_monotonic_and_tick_rounding_is_conservative(self):
        state,trigger=advance_trailing(POLICY,'LONG','81200.17','.1','78400')
        self.assertEqual(trigger,Decimal('80388.1'))
        state2,trigger2=advance_trailing(POLICY,'LONG','81000','.1',str(trigger),state)
        self.assertEqual(state2['watermark'],state['watermark'])
        self.assertIsNone(trigger2)

    def test_before_activation_and_small_steps_do_not_replace_stop(self):
        state,trigger=advance_trailing(POLICY,'LONG','80700','.1','78400')
        self.assertFalse(state['active']);self.assertIsNone(trigger)
        state,trigger=advance_trailing(POLICY,'LONG','81200','.1','80380')
        self.assertTrue(state['active']);self.assertIsNone(trigger)

    def test_short_watermark_and_rounding_are_mirrored(self):
        policy=POLICY|{'activation_price':'79200'}
        state,trigger=advance_trailing(policy,'SHORT','78800.13','.1','81600')
        self.assertEqual(trigger,Decimal('79588.2'))
        state2,next_trigger=advance_trailing(policy,'SHORT','79000','.1',str(trigger),state)
        self.assertEqual(state2['watermark'],state['watermark']);self.assertIsNone(next_trigger)


class TrailingRunnerTests(unittest.TestCase):
    setUp=runner_fixtures.V2RunnerTests.setUp
    tearDown=runner_fixtures.V2RunnerTests.tearDown
    authorize=runner_fixtures.V2RunnerTests.authorize
    open=runner_fixtures.V2RunnerTests.open

    def start(self,short=False,staged=False):
        self.plan['management']['trailing']=dict(POLICY)
        self.plan['targets']=[{'price':'84000','fraction':'1'}]
        if staged:
            self.plan['targets']=[{'price':'81000','fraction':'.5'},{'price':'84000','fraction':'.5'}]
            self.plan['management']['break_even_after_target']=1
        if short:
            self.x.short=True
            self.plan.update(direction='SHORT',stop='81600',targets=[{'price':'76000','fraction':'1'}])
            self.plan['management']['trailing']['activation_price']='79200'
        self.authorize()
        return self.open()['session_id']

    def test_long_tightens_once_and_never_moves_back(self):
        sid=self.start();self.x.price='81200'
        result=self.runner.manage(sid,True)
        self.assertEqual(Decimal(result['trigger_price']),Decimal('80388'))
        count=len(self.x.calls);self.x.price='81000'
        self.assertEqual(self.runner.manage(sid,True)['state'],'MANAGING')
        self.assertEqual(len(self.x.calls),count)

    def test_short_uses_buy_stop_and_lower_watermark(self):
        sid=self.start(short=True);self.x.price='78800'
        result=self.runner.manage(sid,True)
        self.assertEqual(Decimal(result['trigger_price']),Decimal('79588'))
        self.assertEqual(self.x.calls[-2][2]['side'],'BUY')

    def test_read_only_tracking_does_not_send_orders(self):
        sid=self.start();self.x.price='81200';count=len(self.x.calls)
        self.assertEqual(self.runner.manage(sid,False)['state'],'STOP_MOVE_REQUIRED')
        self.assertEqual(len(self.x.calls),count)

    def test_restart_preserves_watermark_and_replaces_only_on_new_high(self):
        sid=self.start();self.x.price='81200';self.runner.manage(sid,True)
        self.store.close();self.store=StateStore(self.path)
        self.service=PlanService(self.store,'local:test');self.runner=V2Runner(self.service,self.x,self.runner.limits)
        self.x.price='81000';count=len(self.x.calls)
        self.assertEqual(self.runner.manage(sid,True)['state'],'MANAGING')
        self.assertEqual(len(self.x.calls),count)
        self.x.price='82000'
        self.assertEqual(Decimal(self.runner.manage(sid,True)['trigger_price']),Decimal('81180'))

    def test_lost_post_and_lost_cancel_are_never_repeated(self):
        sid=self.start();self.x.price='81200';self.x.algo_timeout=True
        with self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        posts=len([c for c in self.x.calls if c[0]=='POST'])
        self.x.cancel_timeout=True
        with self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        cancels=len([c for c in self.x.calls if c[0]=='DELETE'])
        self.assertEqual(self.runner.manage(sid,True)['state'],'STOP_MOVED')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST']),posts)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='DELETE']),cancels)

    def test_staged_exit_resizes_without_break_even_loosening_trailing(self):
        sid=self.start(staged=True);self.x.price='81000'
        self.assertEqual(self.runner.manage(sid,True)['state'],'STOP_MOVED')
        self.assertEqual(self.runner.manage(sid,True)['state'],'TARGET_EXIT_SUBMITTED')
        self.assertEqual(self.runner.manage(sid,True)['state'],'STOP_MOVED')
        transition=self.store.sessions()[0]['stop_transitions'][-1]['proposal']['params']
        self.assertEqual(Decimal(transition['quantity']),abs(self.x.amount))
        self.assertEqual(Decimal(transition['triggerPrice']),Decimal('80190'))

    def test_retrace_below_effective_stop_closes_residual_only(self):
        sid=self.start();self.x.price='81200';self.runner.manage(sid,True)
        self.x.price='80300'
        self.assertEqual(self.runner.manage(sid,True)['state'],'EXIT_SUBMITTED')
        self.assertEqual(self.x.amount,0)
        self.assertEqual(self.x.calls[-1][2]['reduceOnly'],'true')

    def test_modified_stop_transition_cannot_change_side_or_increase_quantity(self):
        sid=self.start();self.x.price='81200';self.runner.manage(sid,True)
        saved=self.store.sessions()[0];before=len(self.x.calls)
        for change in ({'side':'BUY'},{'quantity':'1'},{'triggerPrice':'70000'}):
            altered=copy.deepcopy(saved);altered['stop_transitions'][-1]['proposal']['params'].update(change)
            self.store.save_session(altered)
            with self.subTest(change=change),self.assertRaises(ValueError):self.runner.manage(sid,True)
            self.assertEqual(len(self.x.calls),before)
        self.store.save_session(saved)
