import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import test_v2_runner as fixtures
from agentrader.shared.config import Config
from agentrader.shared.locking import ExecutionBusy
from agentrader.bot.recovery_guardian import paths,require_guardian,status,recover_once,RecoveryExchange,profile_hash,run_guardian,lease_signature,replace_lease
from agentrader.bot.risk import RiskLimits,number


class GuardianLeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/'execution.db';self.runtime=Path(self.temp.name)/'runtime.lock'
        self.x=fixtures.ExecutionExchange();self.limits=RiskLimits()
        database,lock,lease=paths(self.db);self.lease=lease
        body=dict(schema='demo-recovery-guardian/1',instance='a'*32,owner='owner',database=str(database),
                  runtime_lock=str(self.runtime.resolve()),account_ref=hashlib.sha256(self.x.config.api_key.encode()).hexdigest(),
                  risk_profile_hash=profile_hash(self.limits),execute_demo=True,state='ARMED')
        code="""import json,os,sys,time
from pathlib import Path
from agentrader.shared.locking import execution_lock
from agentrader.bot.recovery_guardian import lease_signature,process_token
from agentrader.shared.config import Config
body=json.loads(sys.argv[3]);body.update(pid=os.getpid(),observed_at=time.time())
body['process_token']=process_token(os.getpid())
body['signature']=lease_signature(body,type('X',(),{'config':Config('demo-key','secret-never-output')})())
with execution_lock(Path(sys.argv[1])):
 Path(sys.argv[2]).write_text(json.dumps(body))
 time.sleep(120)
"""
        self.child=subprocess.Popen([sys.executable,'-c',code,str(lock),str(lease),json.dumps(body)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.addCleanup(self.stop_child)
        for _ in range(100):
            if lease.exists():break
            time.sleep(.02)
        self.assertTrue(lease.exists())
        self.body=json.loads(lease.read_text());self.clock=lambda:self.body['observed_at']+1

    def stop_child(self):
        if self.child.poll() is None:self.child.kill()
        self.child.wait(timeout=10)

    def check(self):return require_guardian(self.db,'owner',self.x,self.limits,runtime_lock=self.runtime,clock=self.clock)

    def test_independent_live_lock_and_matching_scope_are_required(self):
        self.assertEqual(self.check(),'a'*32)
        for key,value in [('owner','foreign'),('account_ref','b'*64),('risk_profile_hash','b'*64),('state','OBSERVING'),
                          ('execute_demo',False),('pid',os.getpid()),('observed_at',self.body['observed_at']-10),
                          ('observed_at',self.body['observed_at']+10),('database','wrong'),('runtime_lock','wrong'),('process_token','wrong')]:
            changed={**self.body,key:value};changed['signature']=lease_signature(changed,self.x)
            self.lease.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'GUARDIAN_REQUIRED'):self.check()
        self.lease.write_text(json.dumps(self.body))
        self.assertTrue(status(self.db,clock=self.clock)['entry_ready'])

    def test_killed_guardian_cannot_authorize_entry_even_with_fresh_heartbeat(self):
        self.assertEqual(self.check(),'a'*32)
        self.stop_child()
        with self.assertRaisesRegex(ValueError,'GUARDIAN_REQUIRED'):self.check()
        self.assertFalse(status(self.db,clock=self.clock)['entry_ready'])

    def test_second_guardian_never_loads_credentials_or_mutates(self):
        factory=Mock(side_effect=AssertionError('must not load credentials'))
        with self.assertRaises(ExecutionBusy):run_guardian(self.db,'owner',factory,self.limits,iterations=1,runtime_lock=self.runtime)
        factory.assert_not_called()

    def test_same_key_with_rotated_or_wrong_secret_cannot_use_lease(self):
        self.x.config=Config('demo-key','different-secret')
        with self.assertRaisesRegex(ValueError,'GUARDIAN_REQUIRED'):self.check()


class GuardianRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.V2RunnerTests();self.f.setUp();self.addCleanup(self.f.tearDown)
        self.f.plan['analysis_ref']='shadow-event:'+'a'*64
        self.f.plan['entry'].update(condition='LIMIT',trigger_price='79900')
        self.enterContext(patch('agentrader.bot.v2_runner.guard_chart_entry',return_value=True))
        self.enterContext(patch('agentrader.bot.v2_runner.require_guardian',return_value='fixture'))

    def opened(self,*,pending=False,partial=False):
        self.f.x.limit_pending=pending;self.f.x.partial=partial
        self.f.authorize();return self.f.open()['session_id']

    def recover(self,execute=True):return recover_once(self.f.store,'local:test',self.f.x,RiskLimits(),execute=execute)

    def test_pending_limit_is_revoked_cancelled_and_never_reentered(self):
        sid=self.opened(pending=True);result=self.recover()
        self.assertEqual(result['sessions'][0]['state'],'CLOSED')
        self.assertEqual(self.f.x.amount,0);self.assertEqual(self.f.store.sessions(),[])
        self.assertEqual(len([c for c in self.f.x.calls if c[0]=='POST']),1)
        self.assertEqual(len([c for c in self.f.x.calls if c[0]=='DELETE']),1)
        self.assertIsNotNone(self.f.store.halt_reason())
        self.assertEqual(self.recover()['state'],'IDLE')

    def test_readonly_guardian_cannot_mutate_or_arm(self):
        sid=self.opened(pending=True);before=copy.deepcopy(self.f.x.calls)
        self.recover(False)
        self.assertEqual(self.f.x.calls,before)
        wrapped=RecoveryExchange(self.f.x,self.f.store,sid,False)
        with self.assertRaises(ValueError):wrapped.request('DELETE','/fapi/v1/order',{'symbol':'BTCUSDT','origClientOrderId':'x'})

    def test_native_protections_survive_repeated_takeover(self):
        self.opened();before=copy.deepcopy(self.f.x.calls)
        for _ in range(3):self.assertEqual(self.recover()['sessions'][0]['state'],'MANAGING')
        self.assertEqual(self.f.x.calls,before);self.assertEqual(len(self.f.x.algos),2)

    def test_fill_during_cancel_is_reconciled_and_protected(self):
        self.opened(pending=True)
        original=self.f.x.request
        def fill(method,path,params):
            if method=='DELETE' and path.endswith('/order'):
                order=self.f.x.orders[params['origClientOrderId']]
                order['executedQty']=order['origQty'];order['avgPrice']='80000'
                self.f.x.amount=number(order['origQty'])
                self.f.x.trades.append(dict(orderId=order['orderId'],qty=order['origQty'],side=order['side']))
            return original(method,path,params)
        self.f.x.request=fill
        self.assertEqual(self.recover()['sessions'][0]['state'],'MANAGING')
        self.assertEqual(len(self.f.x.algos),2)
        self.assertEqual(len([c for c in self.f.x.calls if c[0]=='POST' and c[1].endswith('/order')]),1)

    def test_lost_entry_response_queries_then_protects_without_second_entry(self):
        self.f.authorize();self.f.x.timeout=True
        with self.assertRaises(Exception):self.f.open()
        self.assertEqual(self.recover()['sessions'][0]['state'],'MANAGING')
        self.assertEqual(len([c for c in self.f.x.calls if c[0]=='POST' and c[1].endswith('/order')]),1)
        self.assertEqual(len(self.f.x.algos),2)

    def test_foreign_position_blocks_all_exchange_mutations(self):
        self.opened();before=copy.deepcopy(self.f.x.calls);self.f.x.amount+=number(1)
        self.assertEqual(self.recover()['state'],'NEEDS_REVIEW')
        self.assertEqual(self.f.x.calls,before)

    def test_adapter_denies_entries_settings_and_unowned_cancellations(self):
        sid=self.opened(pending=True);wrapped=RecoveryExchange(self.f.x,self.f.store,sid,True)
        s=self.f.store.sessions()[0]
        for method,path,params in [('POST','/fapi/v1/order',s['prepared']['entry']['params']),('POST','/fapi/v1/leverage',{'symbol':'BTCUSDT','leverage':50}),
                                   ('DELETE','/fapi/v1/order',{'symbol':'BTCUSDT','origClientOrderId':'foreign'}),('DELETE','/fapi/v1/algoOrder',{'clientAlgoId':'foreign'})]:
            with self.assertRaises(ValueError):wrapped.request(method,path,params)

    def test_stop_crossing_allows_only_owned_reduce_market(self):
        self.opened();self.f.x.price='78000'
        result=self.recover()
        self.assertEqual(result['sessions'][0]['state'],'EXIT_SUBMITTED')
        params=self.f.x.calls[-1][2];self.assertEqual(params['reduceOnly'],'true');self.assertEqual(params['side'],'SELL')
        self.assertEqual(self.f.x.amount,0)

    def test_orphan_claim_keeps_risk_and_blocks_instead_of_inventing_session(self):
        self.opened(pending=True)
        with self.f.store.db:self.f.store.db.execute('DELETE FROM managed_sessions')
        before=copy.deepcopy(self.f.x.calls)
        self.assertEqual(self.recover()['state'],'ORPHAN_PLAN_REVIEW_REQUIRED')
        self.assertEqual(self.f.x.calls,before)

    def test_new_chart_entry_cannot_start_without_live_guardian(self):
        self.f.authorize()
        with patch('agentrader.bot.v2_runner.require_guardian',side_effect=ValueError('INDEPENDENT_DEMO_GUARDIAN_REQUIRED')):
            with self.assertRaises(ValueError):self.f.open()
        self.assertEqual(self.f.x.calls,[]);self.assertEqual(self.f.store.intents(),[])
        self.assertEqual(self.f.store.sessions(),[])

    def test_guardian_loss_during_last_account_read_blocks_first_post(self):
        self.f.authorize()
        with patch('agentrader.bot.v2_runner.require_guardian',side_effect=['lease','lease',ValueError('lost guardian')]):
            with self.assertRaises(ValueError):self.f.open()
        self.assertEqual(self.f.x.calls,[]);self.assertEqual(self.f.store.intents()[0]['state'],'REJECTED')

    def test_pending_entry_cancels_when_guardian_disappears(self):
        sid=self.opened(pending=True)
        with patch('agentrader.bot.v2_runner.require_guardian',side_effect=ValueError('lost guardian')):
            self.f.runner.manage(sid,True)
        self.assertEqual(self.f.x.amount,0)
        self.assertEqual(len([c for c in self.f.x.calls if c[0]=='POST']),1)
        self.assertEqual(next(iter(self.f.x.orders.values()))['status'],'CANCELED')


class GuardianStartupTests(unittest.TestCase):
    def test_failed_account_probe_never_arms_or_initializes_execution_store(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'execution.db';x=Mock(config=Config('key','secret'));x.get.return_value={'canTrade':False}
            with self.assertRaises(ValueError):run_guardian(db,'owner',lambda:x,RiskLimits(),iterations=1,runtime_lock=Path(folder)/'runtime.lock')
            self.assertEqual(status(db)['state'],'STOPPED');self.assertFalse(db.exists())
            x.request.assert_not_called()

    def test_windows_read_share_conflict_retries_atomic_replace_without_truncation(self):
        with tempfile.TemporaryDirectory() as folder:
            old=Path(folder)/'lease.json';new=Path(folder)/'new.tmp';old.write_text('old');new.write_text('complete new lease')
            original=os.replace;count=[]
            def replace(a,b):
                count.append(1)
                if len(count)==1:raise PermissionError('read sharing conflict')
                original(a,b)
            with patch('agentrader.bot.recovery_guardian.os.replace',side_effect=replace),patch('agentrader.bot.recovery_guardian.time.sleep') as sleep:
                replace_lease(new,old)
            self.assertEqual(old.read_text(),'complete new lease');self.assertEqual(len(count),2)
            sleep.assert_called_once_with(.01)

