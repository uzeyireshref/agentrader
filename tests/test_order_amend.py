import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agentrader.exchange import ExchangeError
from agentrader.grid_runner import GridRunner
from agentrader.order_amend import OrderAmendments
from agentrader.order_revisions import effective_params
from agentrader.plans import PlanService
from agentrader.risk import RiskLimits,number
from agentrader.state import StateStore
from agentrader.v2_runner import V2Runner
from test_grid_plan import grid_plan,grid_snapshot,limits
from test_grid_runner import GridExchange
from test_plan_v2 import plan_v2
from test_v2_preflight import snapshot


class AmendExchange(GridExchange):
    def __init__(self):
        super().__init__();self.history=[];self.amend_lost=False;self.amend_rejected=False
        self.hide_history=False;self.fill_before_amend=False
        self.batch_reject=set();self.batch_lost=False
    def get(self,path,params=None):
        if path=='/fapi/v1/orderAmendment':
            return []if self.hide_history else copy.deepcopy([h for h in self.history if h['clientOrderId']==params['origClientOrderId']])
        return super().get(path,params)
    def request(self,method,path,p):
        if method=='PUT'and path=='/fapi/v1/batchOrders':
            self.calls.append((method,path,copy.deepcopy(p)))
            result=[{'code':-1111}if x['origClientOrderId']in self.batch_reject else self.request('PUT','/fapi/v1/order',x)
                    for x in json.loads(p['batchOrders'])]
            if self.batch_lost:raise ExchangeError('lost batch',delivery_status='UNKNOWN')
            return result
        if method=='PUT'and path=='/fapi/v1/order':
            self.calls.append((method,path,copy.deepcopy(p)))
            if self.amend_rejected:raise ExchangeError('rejected',-1111,400,delivery_status='REJECTED')
            a=self.orders[p['origClientOrderId']]
            if self.fill_before_amend:self.fill(p['origClientOrderId'])
            if number(p['quantity'])<=number(a['executedQty']):a['status']='CANCELED';return copy.deepcopy(a)
            self.history.append({'amendmentId':len(self.history)+1,'symbol':a['symbol'],'clientOrderId':a['clientOrderId'],
                'orderId':a['orderId'],'time':int(time.time()*1000),'amendment':{'modifyId':p['modifyId'],
                'price':{'before':a['price'],'after':p['price']},'origQty':{'before':a['origQty'],'after':p['quantity']}}})
            a.update(origQty=p['quantity'],price=p['price'],modifyId=p['modifyId'],updateTime=int(time.time()*1000))
            if self.amend_lost:raise ExchangeError('lost',delivery_status='UNKNOWN')
            return copy.deepcopy(a)
        return super().request(method,path,p)


class OrderAmendTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.db'
        self.store=StateStore(self.path);self.service=PlanService(self.store,'owner');self.x=AmendExchange()
        self.plan=plan_v2();self.plan['entry'].update(condition='LIMIT',trigger_price='79900')
        self.plan['sizing']['amount']='90';self.snap=snapshot();self.x.price='80000'
        self.snap.update(observed_at=time.time(),finished_at=time.time(),now_ms=int(time.time()*1000))
        self.mock=patch('agentrader.v2_runner.collect_flat_snapshot',side_effect=lambda*a:copy.deepcopy(self.snap));self.mock.start()
        self.runner=V2Runner(self.service,self.x,RiskLimits());self.amend=OrderAmendments(self.service,self.x,RiskLimits())
    def tearDown(self):self.mock.stop();self.store.close();self.temp.cleanup()
    def start(self):
        p=self.service.create(self.plan,'owner')
        self.service.authorize(self.plan['plan_id'],1,p['authorization_token'],'approve','owner')
        sid=self.runner.open(self.plan['plan_id'],1,True)['session_id']
        return sid,self.store.sessions()[0]['entry_id']
    def prepared(self):
        sid,cid=self.start();return sid,cid,self.amend.prepare(sid,cid,'.001','79800')
    def apply(self,p):return self.amend.apply(p['command_id'],p['digest'])

    def test_native_amend_commits_verified_revision_without_changing_plan(self):
        sid,cid,p=self.prepared();before=self.service.show(self.plan['plan_id'],1)['digest']
        self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.assertEqual(effective_params(self.store,cid)['quantity'],'0.001')
        self.assertEqual(effective_params(self.store,cid)['price'],'79800')
        self.assertEqual(self.service.show(self.plan['plan_id'],1)['digest'],before)
        self.assertEqual(self.runner.manage(sid,False)['state'],'ENTRY_PENDING')
        self.apply(p);self.assertEqual(len([c for c in self.x.calls if c[0]=='PUT']),1)
    def test_wrong_digest_does_not_put(self):
        _,_,p=self.prepared()
        with self.assertRaises(ValueError):self.amend.apply(p['command_id'],'wrong')
        self.assertFalse(any(c[0]=='PUT'for c in self.x.calls))
    def test_size_increase_and_worse_price_are_rejected(self):
        sid,cid=self.start()
        for q,price in [('.002','79900'),('.001','80000'),('.001','78000')]:
            with self.assertRaises(ValueError):self.amend.prepare(sid,cid,q,price)
        self.assertFalse(any(c[0]=='PUT'for c in self.x.calls))
    def test_lost_put_response_resolves_from_modify_history_without_retry(self):
        sid,cid,p=self.prepared();self.x.amend_lost=True
        self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.apply(p);self.assertEqual(len([c for c in self.x.calls if c[0]=='PUT']),1)
    def test_delayed_history_is_not_applied_from_price_alone(self):
        sid,cid,p=self.prepared();self.x.hide_history=True
        self.assertEqual(self.apply(p)['state'],'ACKNOWLEDGED')
        self.assertTrue(self.store.unresolved_account_command())
        self.assertEqual(effective_params(self.store,cid)['price'],'79900')
        self.x.hide_history=False
        self.assertEqual(self.amend.reconcile(p['command_id'])['state'],'APPLIED')
        self.assertFalse(self.store.unresolved_account_command())
    def test_cancel_prepared_command_never_puts(self):
        _,_,p=self.prepared()
        self.assertEqual(self.amend.cancel(p['command_id'],p['digest'])['state'],'CANCELED')
        self.assertEqual(self.apply(p)['state'],'CANCELED')
        self.assertFalse(any(c[0]=='PUT'for c in self.x.calls))
    def test_partial_fill_before_apply_is_kept_in_cumulative_inventory(self):
        sid,cid,p=self.prepared();self.x.fill(cid,'.0003')
        self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.assertEqual(number(self.runner.journal.get(cid)['filled']),number('.0003'))
        self.assertEqual(number(self.runner.journal.get(cid)['quantity']),number('.001'))
    def test_fill_during_put_cancels_without_false_revision(self):
        sid,cid,p=self.prepared();self.x.fill_before_amend=True
        self.assertEqual(self.apply(p)['state'],'SUPERSEDED')
        self.assertEqual(effective_params(self.store,cid)['price'],'79900')
        self.assertEqual(self.runner.manage(sid,True)['state'],'MANAGING')
    def test_restart_keeps_revision_and_no_resend(self):
        sid,cid,p=self.prepared();self.apply(p)
        self.store.close();self.store=StateStore(self.path);self.service=PlanService(self.store,'owner')
        self.amend=OrderAmendments(self.service,self.x,RiskLimits())
        self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='PUT']),1)
    def test_expired_and_rejected_commands_do_not_reissue(self):
        sid,cid,p=self.prepared();self.amend.clock=lambda:p['expires_at']+1
        self.assertEqual(self.apply(p)['state'],'EXPIRED')
        self.amend.clock=time.time
        p=self.amend.prepare(sid,cid,'.001','79800');self.x.amend_rejected=True
        self.assertEqual(self.apply(p)['state'],'REJECTED')
        self.apply(p);self.assertEqual(len([c for c in self.x.calls if c[0]=='PUT']),1)
    def test_short_improved_price_cannot_expand_nominal_budget(self):
        self.plan.update(direction='SHORT',stop='81600',targets=[{'price':'78400','fraction':'1'}])
        self.plan['entry']['trigger_price']='80100';self.x.short=True
        sid,cid=self.start();old=effective_params(self.store,cid)['quantity']
        with self.assertRaises(ValueError):self.amend.prepare(sid,cid,old,'80200')
        p=self.amend.prepare(sid,cid,'.001','80200');self.assertEqual(self.apply(p)['state'],'APPLIED')
    def test_grid_quantity_amend_keeps_levels_and_next_refill_cap(self):
        self.plan=grid_plan();self.snap=grid_snapshot();self.x.price='75725'
        self.snap.update(observed_at=time.time(),finished_at=time.time(),now_ms=int(time.time()*1000))
        with patch('agentrader.grid_runner.collect_flat_snapshot',side_effect=lambda*a:copy.deepcopy(self.snap)):
            self.runner=GridRunner(self.service,self.x,limits());self.amend=OrderAmendments(self.service,self.x,limits())
            p=self.service.create(self.plan,'owner');self.service.authorize(self.plan['plan_id'],1,p['authorization_token'],'approve','owner')
            sid=self.runner.open(self.plan['plan_id'],1,True)['session_id']
        record=next(r for r in self.store.sessions()[0]['orders']if r['kind']=='OPEN')
        cid=record['proposal']['params']['newClientOrderId'];price=record['proposal']['params']['price']
        with self.assertRaises(ValueError):self.amend.prepare(sid,cid,'.0008',str(number(price)+100))
        p=self.amend.prepare(sid,cid,'.0008',price);self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.x.fill(cid)
        r=self.runner.manage(sid,True)
        self.assertIn(r['state'],('GRID_ORDER_SUBMITTED','GRID_RUNNING'))
        self.assertLessEqual(abs(self.x.amount),number('.0036'))

    def grid_for_batch(self):
        self.plan=grid_plan();self.snap=grid_snapshot();self.x.price='75725'
        self.snap.update(observed_at=time.time(),finished_at=time.time(),now_ms=int(time.time()*1000))
        self.runner=GridRunner(self.service,self.x,limits());self.amend=OrderAmendments(self.service,self.x,limits())
        with patch('agentrader.grid_runner.collect_flat_snapshot',side_effect=lambda*a:copy.deepcopy(self.snap)):
            p=self.service.create(self.plan,'owner');self.service.authorize(self.plan['plan_id'],1,p['authorization_token'],'approve','owner')
            sid=self.runner.open(self.plan['plan_id'],1,True)['session_id']
        for _ in range(5):self.runner.manage(sid,True)
        orders=[r['proposal']['params']for r in self.store.sessions()[0]['orders']if r['kind']=='OPEN'][:2]
        return sid,[{'client_id':p['newClientOrderId'],'quantity':'.0008','price':p['price']}for p in orders]

    def test_native_batch_modify_has_independent_verified_revisions(self):
        sid,changes=self.grid_for_batch();p=self.amend.prepare_batch(sid,changes)
        self.assertEqual(self.amend.apply_batch(p['batch_id'],p['digest'])['state'],'APPLIED')
        for c in changes:self.assertEqual(effective_params(self.store,c['client_id'])['quantity'],'0.0008')
        self.amend.apply_batch(p['batch_id'],p['digest'])
        self.assertEqual(len([c for c in self.x.calls if c[0]=='PUT'and c[1]=='/fapi/v1/batchOrders']),1)
    def test_partial_batch_rejection_does_not_change_other_order_revision(self):
        sid,changes=self.grid_for_batch();p=self.amend.prepare_batch(sid,changes)
        self.x.batch_reject={changes[1]['client_id']}
        result=self.amend.apply_batch(p['batch_id'],p['digest'])
        self.assertEqual(result['state'],'FINAL_WITH_ERRORS')
        self.assertEqual([c['state']for c in result['commands']],['APPLIED','REJECTED'])
        self.assertEqual(effective_params(self.store,changes[1]['client_id'])['quantity'],'0.0009')
    def test_lost_batch_modify_is_reconciled_without_second_put(self):
        sid,changes=self.grid_for_batch();p=self.amend.prepare_batch(sid,changes);self.x.batch_lost=True
        self.assertEqual(self.amend.apply_batch(p['batch_id'],p['digest'])['state'],'APPLIED')
        self.amend.apply_batch(p['batch_id'],p['digest'])
        self.assertEqual(len([c for c in self.x.calls if c[0]=='PUT'and c[1]=='/fapi/v1/batchOrders']),1)
    def test_batch_member_cannot_be_sent_individually_or_repeated(self):
        sid,changes=self.grid_for_batch();p=self.amend.prepare_batch(sid,changes)
        child=p['commands'][0]
        with self.assertRaises(ValueError):self.amend.apply(child['command_id'],child['digest'])
        with self.assertRaises(ValueError):self.amend.prepare_batch(sid,[changes[0],changes[0]])
        self.assertEqual(self.amend.cancel_batch(p['batch_id'],p['digest'])['state'],'CANCELED')
        self.assertFalse(any(c[0]=='PUT'for c in self.x.calls))
    def test_history_without_matching_modify_id_does_not_apply_revision(self):
        sid,cid,p=self.prepared();self.x.hide_history=True
        self.assertEqual(self.apply(p)['state'],'ACKNOWLEDGED');self.x.hide_history=False
        self.x.history[-1]['amendment']['modifyId']=0
        self.assertEqual(self.amend.reconcile(p['command_id'])['state'],'ACKNOWLEDGED')
        self.assertEqual(effective_params(self.store,cid)['price'],'79900')

    def test_manual_price_change_is_not_accepted_as_a_verified_revision(self):
        sid,cid=self.start();self.x.orders[cid]['price']='80000'
        before=len(self.x.calls)
        with self.assertRaises(ValueError):self.runner.manage(sid,True)
        self.assertEqual(len(self.x.calls),before)

    def test_reused_client_identity_with_different_broker_order_is_rejected(self):
        sid,cid=self.start();self.x.orders[cid]['orderId']=999
        with self.assertRaises(ValueError):self.runner.manage(sid,False)

    def test_applied_command_remains_idempotent_after_session_closed(self):
        sid,cid,p=self.prepared();self.apply(p);self.x.price='78000'
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='PUT']),1)

    def test_last_authorization_guard_can_block_put_after_local_reservation(self):
        _,_,p=self.prepared()
        with patch.object(self.amend,'_final_guard',return_value=False):self.assertEqual(self.apply(p)['state'],'NOT_SENT')
        self.assertFalse(any(c[0]=='PUT'for c in self.x.calls))
        self.assertFalse(self.store.unresolved_account_command())

    def test_malformed_matching_history_keeps_revision_uncommitted(self):
        _,cid,p=self.prepared();self.x.hide_history=True;self.apply(p);self.x.hide_history=False
        del self.x.history[0]['amendment']['price']
        with self.assertRaises(ValueError):self.amend.reconcile(p['command_id'])
        self.assertEqual(effective_params(self.store,cid)['price'],'79900')
        self.assertTrue(self.store.unresolved_account_command())
