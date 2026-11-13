import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentrader.batch_cancel import OwnedBatchCancel
from agentrader.exchange import ExchangeError
from agentrader.state import StateStore
from test_grid_runner import GridExchange


class BatchExchange(GridExchange):
    def __init__(self):super().__init__();self.reject_ids=set();self.lost=False
    def request(self,method,path,params):
        if method=='DELETE'and path=='/fapi/v1/batchOrders':
            self.calls.append((method,path,dict(params)));reply=[]
            for cid in json.loads(params['origClientOrderIdList']):
                reply.append({'code':-2011}if cid in self.reject_ids else
                             super().request('DELETE','/fapi/v1/order',{'symbol':params['symbol'],'origClientOrderId':cid}))
            if self.lost:raise ExchangeError('lost batch response',delivery_status='UNKNOWN')
            return reply
        return super().request(method,path,params)


class BatchCancelTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=StateStore(Path(self.temp.name)/'state.db')
        self.x=BatchExchange();self.ids=['batch-0','batch-1'];self.helper=OwnedBatchCancel(self.x,self.store)
        for cid in self.ids:
            p={'symbol':'BTCUSDT','side':'BUY','positionSide':'BOTH','type':'LIMIT','price':'75000',
               'quantity':'.001','timeInForce':'GTC','newClientOrderId':cid}
            self.store.reserve(cid,'/fapi/v1/order',p)
            reply=self.x.request('POST','/fapi/v1/order',p);self.store.update(cid,reply['status'],reply)
        self.x.calls.clear()
    def tearDown(self):self.store.close();self.temp.cleanup()
    def cancel(self):return self.helper.cancel('BTCUSDT',self.ids,owned_client_ids=set(self.ids))
    def batches(self):return [c for c in self.x.calls if c[1]=='/fapi/v1/batchOrders']

    def test_native_batch_is_sent_once_and_every_order_is_verified(self):
        r=self.cancel();self.assertEqual(r['state'],'RECONCILED')
        self.assertEqual(r['submitted_count'],2);self.assertEqual(len(self.batches()),1)
        self.assertTrue(all(o['status']=='CANCELED'for o in r['orders']))
        self.cancel();self.assertEqual(len(self.batches()),1)
    def test_partial_errors_do_not_mean_whole_batch_succeeded(self):
        self.x.reject_ids={'batch-1'}
        r=self.cancel();self.assertEqual(r['state'],'PARTIAL');self.assertEqual(r['unresolved'],['batch-1'])
        self.assertEqual(self.cancel()['state'],'PARTIAL');self.assertEqual(len(self.batches()),1)
        self.x.fill('batch-1')
        self.assertEqual(self.cancel()['state'],'RECONCILED')
        self.assertEqual(self.store.db.execute('SELECT state FROM batch_cancellations').fetchone()[0],'RECONCILED')
    def test_lost_response_is_read_only_reconciled_without_another_delete(self):
        self.x.lost=True
        with self.assertRaises(ExchangeError):self.cancel()
        self.assertEqual(self.cancel()['state'],'RECONCILED');self.assertEqual(len(self.batches()),1)
    def test_cancel_fill_race_reports_actual_cumulative_fill(self):
        self.x.late_fill='batch-0';r=self.cancel()
        row=next(o for o in r['orders']if o['client_id']=='batch-0')
        self.assertEqual(row['executed_quantity'],'0.001');self.assertEqual(r['state'],'RECONCILED')
    def test_unowned_duplicate_and_oversized_selections_never_write(self):
        for ids,owned in [(['foreign'],set()),(self.ids*2,set(self.ids)),(['x'+str(i)for i in range(11)],set())]:
            with self.assertRaises(ValueError):self.helper.cancel('BTCUSDT',ids,owned_client_ids=owned)
        self.assertEqual(self.x.calls,[])
    def test_wrong_order_identity_is_rejected_before_batch_delivery(self):
        original=self.x.get
        def get(path,params=None):
            r=original(path,params)
            if path=='/fapi/v1/order':r['side']='SELL'
            return r
        with patch.object(self.x,'get',side_effect=get):
            with self.assertRaises(ValueError):self.cancel()
        self.assertEqual(self.x.calls,[])
    def test_previously_uncertain_single_cancel_is_not_resent_in_batch(self):
        key,body=self.helper._single('BTCUSDT','batch-0')
        with self.store.db:self.store.db.execute('INSERT INTO v2_cancellations VALUES (?,?,?)',(key,body,'UNKNOWN'))
        r=self.cancel();self.assertEqual(r['unresolved'],['batch-0'])
        self.assertEqual(json.loads(self.batches()[0][2]['origClientOrderIdList']),['batch-1'])
    def test_already_filled_order_is_not_canceled(self):
        self.x.fill('batch-0');r=self.cancel()
        self.assertEqual(r['state'],'RECONCILED')
        self.assertEqual(json.loads(self.batches()[0][2]['origClientOrderIdList']),['batch-1'])
    def test_restart_preserves_no_resend_guarantee(self):
        self.x.lost=True
        with self.assertRaises(ExchangeError):self.cancel()
        restarted=OwnedBatchCancel(self.x,self.store)
        self.assertEqual(restarted.cancel('BTCUSDT',self.ids,owned_client_ids=self.ids)['state'],'RECONCILED')
        self.assertEqual(len(self.batches()),1)
