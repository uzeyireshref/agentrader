import copy
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest

from agentrader.shared.config import Config
from agentrader.shared.exchange import ExchangeError
from agentrader.bot.history_reconciliation import HistoryReads,reconcile_terminal_history
from agentrader.bot.plans import PlanService
from agentrader.shared.state import StateStore


class FakeHistory:
    config=Config('fixture-key','secret-do-not-export')
    def __init__(self):self.results={};self.positions=[];self.normal=[];self.algos=[];self.calls=[];self.hook=None
    def sync_time(self):pass
    def request(self,method,path,params=None):
        if method!='GET':raise AssertionError('exchange mutation')
        self.calls.append((method,path))
        if path.endswith('positionSide/dual'):return {'dualSidePosition':False}
        if path.endswith('/account'):return {'positions':copy.deepcopy(self.positions)}
        if path.endswith('positionRisk'):return copy.deepcopy(self.positions)
        if path.endswith('openOrders'):return copy.deepcopy(self.normal)
        if path.endswith('openAlgoOrders'):return copy.deepcopy(self.algos)
        cid=(params or {}).get('clientAlgoId',(params or {}).get('origClientOrderId'))
        value=self.results[cid]
        if self.hook:self.hook(cid)
        if isinstance(value,Exception):raise value
        return copy.deepcopy(value)


class HistoryReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'execution.db';self.backup=Path(self.tmp.name)/'before.db'
        self.store=StateStore(self.path);self.addCleanup(self.store.close);PlanService(self.store,'owner');self.store.halt('preserve-this-halt')
        self.settings=SimpleNamespace(execution_database=self.path,owner='owner');self.x=FakeHistory()
        p=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='MARKET',quantity='0.001',newClientOrderId='entry')
        self.store.reserve('entry','/fapi/v1/order',p)
        self.store.update('entry','NEW',dict(orderId=11,status='NEW',executedQty='0',reduceOnly=False,updateTime=100))
        self.x.results['entry']=dict(orderId=11,clientOrderId='entry',symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='MARKET',
                                    origQty='0.001',executedQty='0.001',status='FILLED',reduceOnly=False,updateTime=101)

    def run_check(self,apply=False):
        return reconcile_terminal_history(self.settings,self.x,apply=apply,backup_path=self.backup,clock=lambda:1000)

    def test_verified_terminal_updates_only_local_history_and_preserves_halt(self):
        r=self.run_check(True);self.assertEqual(r['state'],'APPLIED');self.assertEqual(r['updated_count'],1)
        self.assertEqual(self.store.intent('entry')['state'],'FILLED');self.assertEqual(self.store.halt_reason(),'preserve-this-halt')
        self.assertTrue(all(method=='GET' for method,path in self.x.calls))
        with closing(sqlite3.connect(self.backup)) as db:self.assertEqual(db.execute('SELECT state FROM intents').fetchone()[0],'NEW')

    def test_preview_never_writes_local_ledger_or_backup(self):
        before=self.store.intent('entry');r=self.run_check()
        self.assertEqual(r['state'],'READ_ONLY_VERIFIED');self.assertEqual(self.store.intent('entry'),before);self.assertFalse(self.backup.exists())

    def test_changed_identity_quantity_or_older_broker_id_never_applies(self):
        original=copy.deepcopy(self.x.results['entry'])
        for key,value in [('clientOrderId','foreign'),('symbol','ETHUSDT'),('side','SELL'),('origQty','0.002'),('orderId',12),('reduceOnly',True)]:
            self.x.results['entry']={**original,key:value};self.assertEqual(self.run_check(True)['state'],'BLOCKED')
            self.assertEqual(self.store.intent('entry')['state'],'NEW')

    def test_missing_order_stays_unresolved_even_on_flat_account(self):
        self.x.results['entry']=ExchangeError('signed-url-secret',-2013)
        r=self.run_check(True);self.assertEqual(r['state'],'BLOCKED');self.assertEqual(self.store.intent('entry')['state'],'NEW')
        self.assertNotIn('signed-url-secret',str(r));self.assertNotIn('secret-do-not-export',str(r))

    def test_unfinished_or_unproven_fill_cannot_become_terminal(self):
        for change in ({'status':'NEW'},{'executedQty':'0.0005'},{'updateTime':99}):
            original=copy.deepcopy(self.x.results['entry']);self.x.results['entry'].update(change)
            self.assertEqual(self.run_check(True)['state'],'BLOCKED');self.assertEqual(self.store.intent('entry')['state'],'NEW')
            self.x.results['entry']=original

    def test_account_change_after_lookup_rolls_back_all_local_changes(self):
        self.x.hook=lambda cid:self.x.positions.append(dict(symbol='BTCUSDT',positionSide='BOTH',positionAmt='1'))
        r=self.run_check(True);self.assertEqual(r['state'],'BLOCKED');self.assertEqual(self.store.intent('entry')['state'],'NEW')

    def test_local_change_during_lookup_is_detected_by_snapshot_comparison(self):
        self.x.hook=lambda cid:self.store.update('entry','UNKNOWN',{'changed':True})
        r=self.run_check(True);self.assertEqual(r['state'],'BLOCKED');self.assertEqual(self.store.intent('entry')['state'],'UNKNOWN')
        self.assertFalse(self.backup.exists())

    def test_algorithms_use_order_type_and_preserve_dynamic_close_position_quantity(self):
        p=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='STOP_MARKET',triggerPrice='90',closePosition='true',workingType='MARK_PRICE',algoType='CONDITIONAL',clientAlgoId='stop')
        self.store.reserve('stop','/fapi/v1/algoOrder',p);self.store.update('stop','NEW',dict(algoId=22,quantity='0',updateTime=100))
        self.x.results['stop']=dict(algoId=22,clientAlgoId='stop',symbol='BTCUSDT',side='SELL',positionSide='BOTH',orderType='STOP_MARKET',triggerPrice='90.0',
                                    closePosition=True,workingType='MARK_PRICE',algoType='CONDITIONAL',quantity='0.001',actualQty='0.001',algoStatus='FINISHED',updateTime=101)
        r=self.run_check(True);self.assertEqual(r['state'],'APPLIED');self.assertEqual(r['updated_count'],2)
        self.assertEqual(self.store.intent('stop')['state'],'FINISHED')

    def test_repeat_is_no_change_and_terminal_records_are_not_requeried(self):
        self.run_check(True);self.x.calls.clear();r=self.run_check(True)
        self.assertEqual(r['state'],'NO_CHANGES');self.assertEqual(r['updated_count'],0)
        self.assertFalse(any(path=='/fapi/v1/order' for method,path in self.x.calls))

    def test_transport_blocks_mutations_and_unknown_endpoints(self):
        x=HistoryReads(self.x)
        for method in ('POST','PUT','DELETE'):
            with self.assertRaises(ValueError):x.request(method,'/fapi/v1/order',{})
        with self.assertRaises(ValueError):x.get('/unapproved')
        self.assertEqual(self.x.calls,[])

    def test_one_unproven_member_prevents_entire_batch_from_applying(self):
        p=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='STOP_MARKET',clientAlgoId='missing-stop')
        self.store.reserve('missing-stop','/fapi/v1/algoOrder',p)
        self.x.results['missing-stop']=ExchangeError('missing',-2013)
        r=self.run_check(True)
        self.assertEqual(r['state'],'BLOCKED');self.assertEqual(self.store.intent('entry')['state'],'NEW')
        self.assertEqual(self.store.intent('missing-stop')['state'],'SUBMITTING');self.assertFalse(self.backup.exists())

    def test_existing_backup_is_never_overwritten(self):
        self.backup.write_bytes(b'previous backup')
        self.assertEqual(self.run_check(True)['state'],'BLOCKED')
        self.assertEqual(self.backup.read_bytes(),b'previous backup');self.assertEqual(self.store.intent('entry')['state'],'NEW')

    def test_active_session_blocks_before_any_exchange_request(self):
        self.store.save_session(dict(id='owned-session',active=True))
        self.assertEqual(self.run_check(True)['state'],'BLOCKED');self.assertEqual(self.x.calls,[])
        self.assertEqual(self.store.intent('entry')['state'],'NEW')
