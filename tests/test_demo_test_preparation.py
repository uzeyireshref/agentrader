import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from agentrader.shared.config import Config
from agentrader.bot.demo_test_preparation import candidate,prepare
from agentrader.bot.risk import RiskLimits,number
from test_v2_preflight import snapshot


class DemoTestPreparationTests(unittest.TestCase):
    def setUp(self):
        self.snap=snapshot();self.limits=RiskLimits();self.settings=SimpleNamespace(execution_database=Path('unused'),owner='fixture')
        self.exchange=Mock(config=Config('fixture-key','fixture-secret'))
        self.local=dict(storage='AVAILABLE',active_sessions=[],entry_halted=True,intent_counts={'FILLED':1})

    def prepare(self,**changes):
        return prepare(self.settings,self.exchange,self.limits,'BTCUSDT','LONG',clock=lambda:1001,
                       collector=lambda *a:copy.deepcopy(self.snap),local_observer=lambda *a:self.local,
                       continuity=changes.pop('continuity',lambda:True),guardian_observer=lambda *a:dict(state='NOT_RUNNING',entry_ready=False),**changes)

    def test_both_directions_produce_filter_valid_inputs_without_plan_authority(self):
        for direction in ('LONG','SHORT'):
            r=candidate(self.snap,self.limits,direction,clock=lambda:1001)
            self.assertEqual(r['state'],'DRAFT_ONLY');self.assertLessEqual(number(r['budget_usdt']),100)
            self.assertEqual(r['inputs']['leverage'],20);self.assertEqual(r['inputs']['margin_mode'],'CROSSED')
            self.assertFalse(r['execution_authorized']);self.assertNotIn('plan',r)
            self.assertIn('FRESH_DEMO_SHADOW_EVENT',r['required_flow']);self.assertTrue(r['fill_possible'])

    def test_real_cleanup_day_loss_blocks_without_substituting_zero_or_raising_limits(self):
        self.snap['daily_loss']='529.69467203';r=self.prepare()
        self.assertIn('DAILY_LOSS_LIMIT_EXCEEDED',r['blockers']);self.assertEqual(r['state'],'BLOCKED')
        self.assertEqual(r['candidate']['preflight_state'],'NOT_ELIGIBLE');self.assertIsNone(r['candidate']['quantity'])
        self.assertEqual(r['daily_loss'],'529.69467203');self.assertEqual(r['max_daily_loss'],'25')
        self.assertFalse(r['halt_cleared']);self.assertTrue(self.local['entry_halted'])
        self.exchange.request.assert_not_called()

    def test_minimum_valid_order_over_cap_is_reported_and_not_imported(self):
        self.snap['symbol_info']['filters']=[{**f,'notional':'150'} if f['filterType']=='MIN_NOTIONAL' else f for f in self.snap['symbol_info']['filters']]
        r=candidate(self.snap,self.limits,'LONG',clock=lambda:1001)
        self.assertIn('MINIMUM_VALID_ORDER_EXCEEDS_NOTIONAL_CAP',r['blockers']);self.assertEqual(r['state'],'BLOCKED')

    def test_unreconciled_local_intents_or_failed_data_acceptance_block_preparation(self):
        self.local['intent_counts']['UNKNOWN']=1;r=self.prepare(continuity=lambda:False)
        self.assertIn('LOCAL_HISTORY_RECONCILIATION_REQUIRED',r['blockers']);self.assertIn('DEMO_CONTINUITY_ACCEPTANCE_REQUIRED',r['blockers'])

    def test_wrong_snapshot_symbol_and_implicit_direction_are_rejected(self):
        self.snap['symbol_info']['symbol']='ETHUSDT'
        self.assertIn('ACCOUNT_OR_SYMBOL_PREPARATION_FAILED',self.prepare()['blockers'])
        with self.assertRaises(ValueError):candidate(self.snap,self.limits,'',clock=lambda:1001)

    def test_clean_account_draft_does_not_clear_halt_or_replace_plan_approval(self):
        r=self.prepare();self.assertEqual(r['state'],'DRAFT_READY_FOR_REVIEW')
        self.assertFalse(r['halt_release_eligible']);self.assertFalse(r['execution_authorized']);self.assertFalse(r['halt_cleared'])
        self.assertEqual(r['next_utc_day_check_at'],'1970-01-02T00:00:00+00:00')
