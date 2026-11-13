import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from agentrader.batch_create import NativeBatchCreate
from agentrader.exchange import ExchangeError
from agentrader.state import StateStore
from test_grid_runner import GridExchange


class CreateExchange(GridExchange):
    def __init__(self):super().__init__();self.reject=set();self.lost=False;self.partial_delivery=False
    def request(self,method,path,p):
        if method=='POST'and path=='/fapi/v1/batchOrders':
            self.calls.append((method,path,copy.deepcopy(p)));reply=[]
            for i,order in enumerate(json.loads(p['batchOrders'])):
                if self.partial_delivery and i:continue
                reply.append({'code':-2019}if order['newClientOrderId']in self.reject else self.request('POST','/fapi/v1/order',order))
            if self.lost:raise ExchangeError('lost',delivery_status='UNKNOWN')
            return reply
        return super().request(method,path,p)


class NativeBatchCreateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.db'
        self.store=StateStore(self.path);self.x=CreateExchange();self.helper=NativeBatchCreate(self.x,self.store,'owned-session')
        self.proposals=[{'method':'POST','path':'/fapi/v1/order','operation':'OPEN',
                         'params':{'symbol':'BTCUSDT','side':'BUY','positionSide':'BOTH','type':'LIMIT','timeInForce':'GTC',
                                   'quantity':'.001','price':str(74000+i*100),'newClientOrderId':'create-'+str(i)}}for i in range(2)]
    def tearDown(self):self.store.close();self.temp.cleanup()
    def submit(self,authorize=lambda*p:True):return self.helper.submit(self.proposals,authorize)
    def batches(self):return [c for c in self.x.calls if c[0]=='POST'and c[1]=='/fapi/v1/batchOrders']
    def test_native_batch_reserves_and_reconciles_each_identity(self):
        auth=Mock(return_value=True);r=self.submit(auth)
        self.assertEqual(r['state'],'RECONCILED');self.assertEqual(len(r['orders']),2)
        self.assertEqual(auth.call_count,2);self.assertEqual(len(self.batches()),1)
        self.submit();self.assertEqual(len(self.batches()),1)
    def test_whole_group_is_reserved_before_any_post(self):
        observed=[];original=self.x.request
        def request(method,path,p):
            if path=='/fapi/v1/batchOrders':observed.extend(r['state']for r in self.store.intents())
            return original(method,path,p)
        self.x.request=request;self.submit()
        self.assertEqual(observed,['SUBMITTING','SUBMITTING'])
    def test_rejected_member_is_not_credited_or_resubmitted(self):
        self.x.reject={'create-1'};r=self.submit()
        self.assertEqual(r['state'],'FINAL_WITH_ERRORS')
        self.assertEqual(self.store.intent('create-1')['state'],'REJECTED')
        self.assertEqual(self.helper.journal.get('create-1')['filled'],'0')
        self.submit();self.assertEqual(len(self.batches()),1)
    def test_lost_reply_queries_without_second_post(self):
        self.x.lost=True;self.assertEqual(self.submit()['state'],'RECONCILED')
        self.submit();self.assertEqual(len(self.batches()),1)
    def test_missing_member_remains_unknown_and_stops_new_entries(self):
        self.x.partial_delivery=True;self.x.lost=True
        r=self.submit();self.assertEqual(r['state'],'UNKNOWN')
        self.assertEqual(self.store.intent('create-1')['state'],'UNKNOWN')
        self.assertTrue(self.store.halt_reason())
        self.submit();self.assertEqual(len(self.batches()),1)
    def test_failed_final_authorization_does_not_post_any_member(self):
        def authorize(params,phase):return phase=='before_reserve'
        with self.assertRaises(ValueError):self.submit(authorize)
        self.assertEqual(self.x.calls,[])
        self.assertTrue(all(r['state']=='REJECTED'for r in self.store.intents()))
    def test_restart_never_resends_batch(self):
        self.submit();self.store.close();self.store=StateStore(self.path)
        self.helper=NativeBatchCreate(self.x,self.store,'owned-session')
        self.assertEqual(self.submit()['state'],'RECONCILED');self.assertEqual(len(self.batches()),1)
    def test_duplicate_mixed_existing_and_new_identity_is_not_sent(self):
        self.submit();self.proposals[1]['params']['newClientOrderId']='new-extra'
        with self.assertRaises(ValueError):self.submit()
        self.assertEqual(len(self.batches()),1)
    def test_scope_mutation_by_authorizer_is_rejected(self):
        def authorize(p,phase):p[0]['quantity']='100';return True
        with self.assertRaises(ValueError):self.submit(authorize)
        self.assertEqual(self.x.calls,[])
