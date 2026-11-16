import copy
import time
import unittest
from decimal import Decimal
from unittest.mock import Mock,patch
from scripts.bot.run_bounded_demo_acceptance import test_limits as limits_for_test, make_plan, flatten_owned, fresh_snapshot
from agentrader.bot.risk import RiskLimits
from agentrader.bot.v2_preflight import prepare_single
from test_v2_preflight import snapshot


class BoundedDemoAcceptanceTests(unittest.TestCase):
    def test_old_loss_is_preserved_with_only_three_extra_dollars(self):
        limits=limits_for_test('529.69467203')
        self.assertEqual(limits.max_daily_loss,Decimal('532.69467203'))
        self.assertEqual(limits.max_trade_loss,1)
        self.assertEqual(limits.max_total_loss,1)
        self.assertEqual(limits.max_notional,60)
        self.assertEqual(limits.max_positions,1)
        self.assertEqual(RiskLimits().max_daily_loss,25)

    def test_three_cases_pass_real_preflight_with_minimum_lots(self):
        for direction,condition in [('LONG','LIMIT'),('LONG','IMMEDIATE'),('SHORT','IMMEDIATE')]:
            snap=copy.deepcopy(snapshot());snap['observed_at']=time.time();snap['now_ms']=int(time.time()*1000)
            snap['daily_loss']='529.69467203'
            plan=make_plan(snap,direction,condition,'fixture')
            r=prepare_single(plan,snap,limits_for_test(snap['daily_loss']))
            self.assertEqual(r['state'],'READY')
            self.assertLessEqual(Decimal(plan['sizing']['amount']),60)
            self.assertFalse(plan['management']['allow_reentry'])

    def test_budget_exhaustion_is_not_rebased_or_ignored(self):
        snap=copy.deepcopy(snapshot());snap['observed_at']=time.time();snap['now_ms']=int(time.time()*1000)
        limits=limits_for_test('529.69467203');snap['daily_loss']='532.69467203'
        plan=make_plan(snap,'LONG','IMMEDIATE','fixture')
        with self.assertRaisesRegex(ValueError,'Günlük'):prepare_single(plan,snap,limits)

    def test_iso_microsecond_rounding_cannot_date_new_plan_in_future(self):
        from agentrader.bot.plans import timestamp
        frozen=1794622507.9735487
        with patch('scripts.bot.run_bounded_demo_acceptance.time.time',return_value=frozen):
            plan=make_plan(snapshot(),'SHORT','IMMEDIATE','fixture')
        self.assertLessEqual(timestamp(plan['created_at']),frozen)
        self.assertGreater(timestamp(plan['expires_at']),frozen)

    def test_only_expired_read_snapshots_retry_with_same_risk_limits(self):
        limits=limits_for_test('529.69467203');exchange=Mock()
        with patch('scripts.bot.run_bounded_demo_acceptance.collect_flat_snapshot',side_effect=[ValueError('Hesap görünümü toplanırken eskidi.'),{'flat_verified':True}]) as collect:
            self.assertTrue(fresh_snapshot(exchange,'BTCUSDT',limits)['flat_verified'])
        self.assertEqual(collect.call_count,2)
        for call in collect.call_args_list:self.assertIs(call.args[2],limits)
        exchange.request.assert_not_called()

    def test_read_retry_is_bounded_and_does_not_hide_other_failures(self):
        with patch('scripts.bot.run_bounded_demo_acceptance.collect_flat_snapshot',side_effect=ValueError('foreign position')) as collect:
            with self.assertRaisesRegex(ValueError,'foreign'):fresh_snapshot(Mock(),'BTCUSDT',RiskLimits())
            self.assertEqual(collect.call_count,1)
        with patch('scripts.bot.run_bounded_demo_acceptance.collect_flat_snapshot',side_effect=ValueError('Hesap görünümü toplanırken eskidi.')) as collect:
            with self.assertRaises(ValueError):fresh_snapshot(Mock(),'BTCUSDT',RiskLimits())
            self.assertEqual(collect.call_count,3)

    def test_no_reduction_is_sent_if_cancelled_entry_never_filled(self):
        runner=Mock();runner.store.sessions.return_value=[]
        flatten_owned(runner,'owned-session')
        runner.stop.assert_called_once_with('owned-session',execute=True)
        runner._post.assert_not_called()

    def test_unverified_ownership_cannot_send_reduction(self):
        runner=Mock();runner.store.sessions.return_value=[{'id':'owned-session'}]
        runner._session.return_value={'protections':[]}
        runner._owned.side_effect=ValueError('foreign fill')
        with self.assertRaises(ValueError):flatten_owned(runner,'owned-session')
        runner._post.assert_not_called()
