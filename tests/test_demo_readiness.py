from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentrader.shared.config import Config
from agentrader.bot.demo_readiness import audit,AuditExchange
from agentrader.cli.service_cli import main
from test_v2_preflight import SnapshotExchange


class AuditFake(SnapshotExchange):
    config=Config('isolated-key','never-expose-secret')
    def request(self,method,path,params=None):
        if method!='GET':raise AssertionError('financial mutation attempted')
        return self.get(path,params)


class DemoReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.settings=SimpleNamespace(execution_database=Path(self.tmp.name)/'execution.db',owner='fixture')
        self.x=AuditFake()
        self.local=dict(storage='AVAILABLE',entry_halted=False,active_sessions=[],intent_counts={})

    def check(self,**kw):
        return audit(self.settings,self.x,clock=kw.pop('clock',lambda:1000),continuity=kw.pop('continuity',lambda:True),
                     local_observer=lambda *a:self.local,guardian_observer=lambda *a:dict(state='NOT_RUNNING',entry_ready=False),**kw)

    def test_flat_audit_only_permits_review_never_authorizes_execution(self):
        r=self.check();self.assertTrue(r['plan_review_ready']);self.assertFalse(r['execution_ready'])
        self.assertFalse(r['execution_authorized']);self.assertFalse(r['order_authority'])
        self.assertIn('EXPLICIT_FRESH_PLAN_AND_APPROVAL_REQUIRED',r['execution_blockers'])
        self.assertIn('INDEPENDENT_DEMO_GUARDIAN_REQUIRED',r['execution_blockers'])
        self.assertTrue(all(c['method']=='GET' for c in r['requests']));self.assertEqual(r['private_get_requests'],6)

    def test_existing_external_positions_block_without_adoption_or_closing(self):
        rows=[dict(symbol='AAVEUSDT',positionSide='BOTH',positionAmt='29.8'),dict(symbol='TRUMPUSDT',positionSide='BOTH',positionAmt='1000')]
        self.x.data['/fapi/v3/account']['positions']=copy.deepcopy(rows);self.x.data['/fapi/v3/positionRisk']=copy.deepcopy(rows)
        before=copy.deepcopy(self.x.data);r=self.check()
        self.assertEqual(r['position_count'],2);self.assertFalse(r['plan_review_ready'])
        self.assertIn('EXISTING_ACCOUNT_POSITIONS',r['review_blockers'])
        self.assertTrue(all(v['automatic_management_authority'] is False for v in r['positions']))
        self.assertEqual(self.x.data,before);self.assertFalse(self.settings.execution_database.exists())

    def test_disagreeing_endpoint_cannot_hide_a_position(self):
        self.x.data['/fapi/v3/positionRisk']=[dict(symbol='BTCUSDT',positionSide='BOTH',positionAmt='0.1')]
        r=self.check();self.assertIn('ACCOUNT_POSITION_SNAPSHOTS_DISAGREE',r['review_blockers'])
        self.assertEqual(r['position_count'],1);self.assertFalse(r['plan_review_ready'])

    def test_failed_private_read_is_not_reported_as_empty_account_or_secret_text(self):
        self.x.get=lambda *a:(_ for _ in ()).throw(ValueError('https://signed-url/secret'))
        r=self.check();self.assertIn('DEMO_ACCOUNT_AUDIT_FAILED',r['review_blockers'])
        self.assertIsNone(r['position_count']);self.assertFalse(r['account_verified'])
        self.assertNotIn('signed-url',json.dumps(r));self.assertNotIn('never-expose-secret',json.dumps(r))

    def test_local_halt_history_and_open_orders_all_remain_blockers(self):
        self.local.update(entry_halted=True,intent_counts={'NEW':3,'FILLED':7})
        self.x.data['/fapi/v1/openOrders']=[dict(symbol='BTCUSDT',clientOrderId='existing')]
        self.x.data['/fapi/v1/openAlgoOrders']=[dict(symbol='BTCUSDT',clientAlgoId='protection')]
        r=self.check()
        for reason in ('LOCAL_ENTRY_HALT_ACTIVE','LOCAL_INTENTS_NEED_RECONCILIATION','EXISTING_NORMAL_ORDERS','EXISTING_ALGO_ORDERS'):
            self.assertIn(reason,r['review_blockers'])
        self.assertTrue(self.local['entry_halted']);self.assertEqual(len(self.x.data['/fapi/v1/openAlgoOrders']),1)

    def test_expired_snapshot_and_failed_continuity_never_become_ready(self):
        times=iter([1000,1016,1016]);r=self.check(clock=lambda:next(times),continuity=lambda:False)
        self.assertIn('ACCOUNT_AUDIT_EXPIRED',r['review_blockers'])
        self.assertIn('DEMO_CONTINUITY_ACCEPTANCE_REQUIRED',r['review_blockers'])

    def test_readonly_wrapper_denies_all_mutating_methods(self):
        x=AuditExchange(self.x)
        for method in ('POST','PUT','DELETE'):
            with self.assertRaises(ValueError):x.request(method,'/fapi/v1/order',{})
        self.assertEqual(x.calls,[])

    def test_cli_returns_nonzero_for_blocked_report_and_has_no_execute_flag(self):
        with patch('agentrader.bot.demo_readiness.local_audit',return_value=dict(state='BLOCKED',plan_review_ready=False,order_requests=0)),redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['acceptance-check']),1)
        self.assertEqual(json.loads(output.getvalue())['order_requests'],0)
        with redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):main(['acceptance-check','--execute-demo'])
