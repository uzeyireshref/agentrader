import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from scripts.bot.close_approved_demo_positions import ReductionScope,params_for,verified_inventory
from agentrader.bot.execution import DurableExchange
from agentrader.shared.exchange import ExchangeError
from agentrader.shared.state import StateStore


class Fake:
    def __init__(self):self.amounts={'AAVEUSDT':'29.8','TRUMPUSDT':'1000.00'};self.orders={};self.posts=[];self.lost=False
    def get(self,path,params=None):
        rows=[dict(symbol=s,positionSide='BOTH',positionAmt=q) for s,q in self.amounts.items()]
        if path.endswith('positionSide/dual'):return {'dualSidePosition':False}
        if path.endswith('/account'):return {'positions':rows}
        if path.endswith('positionRisk'):return rows
        if path.endswith('openOrders') or path.endswith('openAlgoOrders'):return []
        if path.endswith('/order'):return copy.deepcopy(self.orders[params['origClientOrderId']])
        raise AssertionError(path)
    def request(self,method,path,params):
        self.posts.append(copy.deepcopy(params));self.amounts[params['symbol']]='0'
        value={**params,'clientOrderId':params['newClientOrderId'],'status':'FILLED','executedQty':params['quantity']}
        self.orders[params['newClientOrderId']]=value
        if self.lost:raise ExchangeError('isolated lost response',delivery_status='UNKNOWN')
        return value


class ApprovedReductionTests(unittest.TestCase):
    def test_scope_denies_wrong_side_quantity_identity_and_endpoint(self):
        x=Fake();guard=ReductionScope(x);p=params_for('AAVEUSDT')
        for changed in ({**p,'side':'BUY'},{**p,'quantity':'29.9'},{**p,'reduceOnly':'false'},{**p,'newClientOrderId':'different'}):
            with self.assertRaises(ValueError):guard.request('POST','/fapi/v1/order',changed)
        with self.assertRaises(ValueError):guard.request('DELETE','/fapi/v1/order',p)
        self.assertEqual(x.posts,[])

    def test_changed_or_unrelated_exposure_blocks_before_delivery(self):
        for symbol,qty in [('AAVEUSDT','30'),('BTCUSDT','1')]:
            x=Fake();x.amounts[symbol]=qty
            with self.assertRaises(ValueError):ReductionScope(x).request('POST','/fapi/v1/order',params_for('AAVEUSDT'))
            self.assertEqual(x.posts,[])

    def test_durable_retry_queries_same_id_without_second_post(self):
        with tempfile.TemporaryDirectory() as folder:
            store=StateStore(Path(folder)/'execution.db')
            try:
                x=Fake();durable=DurableExchange(ReductionScope(x),store);p=params_for('AAVEUSDT')
                durable.request('POST','/fapi/v1/order',p);durable.request('POST','/fapi/v1/order',p)
                self.assertEqual(len(x.posts),1);self.assertEqual(x.amounts['AAVEUSDT'],'0')
                self.assertEqual(x.amounts['TRUMPUSDT'],'1000.00')
            finally:store.close()

    def test_lost_response_reconciles_without_resending_reduction(self):
        with tempfile.TemporaryDirectory() as folder:
            store=StateStore(Path(folder)/'execution.db')
            try:
                x=Fake();x.lost=True;durable=DurableExchange(ReductionScope(x),store);p=params_for('AAVEUSDT')
                with self.assertRaises(ExchangeError):durable.request('POST','/fapi/v1/order',p)
                self.assertEqual(store.intent(p['newClientOrderId'])['state'],'UNKNOWN')
                self.assertEqual(durable.request('POST','/fapi/v1/order',p)['status'],'FILLED')
                self.assertEqual(len(x.posts),1);self.assertIsNotNone(store.halt_reason())
            finally:store.close()
