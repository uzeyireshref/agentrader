import copy
import unittest
from unittest.mock import patch

from agentrader.exchange import ExchangeError
from agentrader.grid_runner import GridRunner
from agentrader.plan_v2 import validate_v2
from agentrader.plans import PlanService
from agentrader.risk import number
from agentrader.state import StateStore
import test_grid_runner as fixtures
import test_multi_session as multi
from agentrader.account_ownership import AccountOwnership


class GridNativeStopTests(unittest.TestCase):
    setUp=fixtures.GridRunnerTests.setUp
    tearDown=fixtures.GridRunnerTests.tearDown
    authorize=fixtures.GridRunnerTests.authorize
    start=fixtures.GridRunnerTests.start
    cell=fixtures.GridRunnerTests.cell
    def enable(self):
        self.plan['management']['trailing']=dict(activation_price='77000',distance_bps='100',min_step_bps='10',native_stop=True)
    def first(self):
        self.enable();sid=self.start();self.x.price='78000'
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_STOP_MOVED')
        return sid
    def transitions(self):return self.store.sessions()[0]['stop_transitions']
    def test_first_move_preserves_original_fallback_and_has_no_quantity(self):
        sid=self.first();t=self.transitions()[0];p=t['proposal']['params']
        self.assertEqual(number(p['triggerPrice']),77220);self.assertEqual(p['closePosition'],'true')
        self.assertNotIn('quantity',p);self.assertNotIn('reduceOnly',p)
        self.assertEqual(len(self.x.algos),3);self.assertTrue(all(a['algoStatus']=='NEW' for a in self.x.algos.values()))
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_RUNNING')
    def test_second_move_verifies_new_before_canceling_previous(self):
        sid=self.first();previous=self.transitions()[0]['proposal']['params']['clientAlgoId'];original=self.x.request
        def request(method,path,params):
            if method=='DELETE' and params.get('clientAlgoId')==previous:
                newest=self.transitions()[-1]['proposal']['params']['clientAlgoId']
                self.assertEqual(self.x.algos[newest]['algoStatus'],'NEW')
                self.assertEqual(self.transitions()[-1]['state'],'VERIFIED')
            return original(method,path,params)
        self.x.price='79000'
        with patch.object(self.x,'request',side_effect=request):
            self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_STOP_MOVED')
        self.assertEqual(self.x.algos[previous]['algoStatus'],'CANCELED')
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_RUNNING')
    def test_read_only_requires_move_without_post(self):
        self.enable();sid=self.start();self.x.price='78000';before=len(self.x.calls)
        self.assertEqual(self.runner.manage(sid,False)['state'],'GRID_STOP_MOVE_REQUIRED')
        self.assertEqual(len(self.x.calls),before);self.assertNotIn('stop_transitions',self.store.sessions()[0])
    def test_lost_post_only_queries_same_client_id(self):
        self.enable();sid=self.start();self.x.price='78000';self.x.algo_timeout=True
        with self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        before=len([c for c in self.x.calls if c[0]=='POST' and c[1].endswith('algoOrder')])
        # Halt keeps entries stopped; stop cleanup queries the already accepted protection.
        for _ in range(4):
            if self.runner.manage(sid,True)['state']=='CLOSED':break
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST' and c[1].endswith('algoOrder')]),before)
    def test_lost_cancel_is_not_sent_twice_after_restart(self):
        sid=self.first();self.x.price='79000';self.x.cancel_timeout=True
        with self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        previous=self.transitions()[-1]['previous'];before=len([c for c in self.x.calls if c[0]=='DELETE' and c[2].get('clientAlgoId')==previous])
        self.store.close();self.store=StateStore(self.path);self.service=PlanService(self.store,'local:test')
        self.runner=GridRunner(self.service,self.x,self.runner.limits)
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_CLOSE_SUBMITTED')
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='DELETE' and c[2].get('clientAlgoId')==previous]),before)
    def test_retired_stop_with_native_child_is_not_ignored(self):
        sid=self.first();self.x.price='79000';self.runner.manage(sid,True)
        old=self.transitions()[0]['proposal']['params']['clientAlgoId']
        self.x.algos[old]['actualOrderId']='999'
        self.runner.manage(sid,False)
        self.assertEqual(self.store.sessions()[0]['phase'],'STOPPING')
    def test_triggered_without_child_waits_instead_of_market_close(self):
        sid=self.first();cid=self.transitions()[0]['proposal']['params']['clientAlgoId']
        self.x.algos[cid]['algoStatus']='TRIGGERING';before=len([c for c in self.x.calls if c[0]=='POST'])
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_NATIVE_CHILD_PENDING')
        self.assertEqual(before,len([c for c in self.x.calls if c[0]=='POST']))
    def test_malformed_new_stop_cannot_retire_previous(self):
        sid=self.first();previous=self.transitions()[0]['proposal']['params']['clientAlgoId'];original=self.x.request
        def request(method,path,params):
            reply=original(method,path,params)
            if method=='POST' and path.endswith('algoOrder'):
                self.x.algos[params['clientAlgoId']]['triggerPrice']='1'
            return reply
        self.x.price='79000'
        with patch.object(self.x,'request',side_effect=request),self.assertRaises(ValueError):self.runner.manage(sid,True)
        self.assertEqual(self.x.algos[previous]['algoStatus'],'NEW')
    def test_definitive_reject_never_reposts_replacement(self):
        self.enable();sid=self.start();self.x.price='78000';original=self.x.request
        def request(method,path,params):
            if method=='POST' and path.endswith('algoOrder'):raise ExchangeError('rejected',delivery_status='REJECTED')
            return original(method,path,params)
        with patch.object(self.x,'request',side_effect=request),self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        self.assertEqual(self.store.sessions()[0]['phase'],'STOPPING')
        for _ in range(4):
            if self.runner.manage(sid,True)['state']=='CLOSED':break
        self.assertEqual(self.x.amount,0)
    def test_short_hedge_move_uses_buy_close_all(self):
        self.enable();self.plan.update(direction='SHORT',position_mode='hedge',stop='79000',targets=[{'price':'72000','fraction':'1'}])
        self.plan['management']['trailing']['activation_price']='75000'
        self.snap['position_mode']='hedge';self.x.short=True;self.x.hedge=True
        sid=self.start();self.x.price='74000'
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_STOP_MOVED')
        p=self.transitions()[0]['proposal']['params'];self.assertEqual((p['side'],p['positionSide']),('BUY','SHORT'))
        self.assertEqual(number(p['triggerPrice']),74740)
    def test_tampered_transition_or_unapproved_native_mode_blocks(self):
        sid=self.first();s=self.store.sessions()[0];s['stop_transitions'][0]['proposal']['params']['side']='BUY';self.store.save_session(s)
        before=len(self.x.calls)
        with self.assertRaises(ValueError):self.runner.manage(sid,True)
        self.assertEqual(before,len(self.x.calls))
    def test_native_flag_requires_boolean(self):
        self.enable();self.plan['management']['trailing']['native_stop']='true'
        with self.assertRaises(ValueError):validate_v2(self.plan)
    def test_non_object_trailing_is_rejected_as_invalid_plan(self):
        self.plan['management']['trailing']=[]
        with self.assertRaises(ValueError):validate_v2(self.plan)
    def test_amend_cannot_bypass_the_advanced_stop(self):
        from agentrader.order_amend import OrderAmendments
        sid=self.first();cid=self.cell(1,'OPEN');p=self.x.orders[cid]
        self.x.price='77000';before=len(self.x.calls)
        with self.assertRaisesRegex(ValueError,'Amend öncesi stop'):
            OrderAmendments(self.service,self.x,self.runner.limits).prepare(sid,cid,p['origQty'],p['price'])
        self.assertEqual(len(self.x.calls),before)
    def test_higher_watermark_during_pending_post_does_not_change_reserved_params(self):
        self.enable();sid=self.start();self.x.price='78000';original=self.x.request
        def request(method,path,params):
            result=original(method,path,params)
            if method=='POST' and path.endswith('algoOrder'):self.x.price='79000'
            return result
        with patch.object(self.x,'request',side_effect=request):self.runner.manage(sid,True)
        first=copy.deepcopy(self.transitions()[0]['proposal'])
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_STOP_MOVED')
        self.assertEqual(first,self.transitions()[0]['proposal'])
        self.assertEqual(len(self.transitions()),2)
    def test_unexpected_manual_cancel_of_latest_stop_stops_grid(self):
        sid=self.first();cid=self.transitions()[0]['proposal']['params']['clientAlgoId']
        self.x.algos[cid]['algoStatus']='CANCELED'
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_CLOSE_SUBMITTED')
    def test_gap_below_stop_before_replacement_post_cleans_without_new_algo(self):
        sid=self.first();self.x.price='79000';original=self.x.get;calls=0
        def get(path,params=None):
            nonlocal calls
            if path.endswith('/premiumIndex'):
                calls+=1
                if calls>=2:self.x.price='78000'
            return original(path,params)
        before=len([c for c in self.x.calls if c[0]=='POST' and c[1].endswith('algoOrder')])
        with patch.object(self.x,'get',side_effect=get):
            self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_CLOSE_SUBMITTED')
        self.assertEqual(before,len([c for c in self.x.calls if c[0]=='POST' and c[1].endswith('algoOrder')]))
    def fire_child(self,quantity):
        cid=self.transitions()[-1]['proposal']['params']['clientAlgoId']
        self.x.algos[cid].update(algoStatus='TRIGGERED',actualOrderId='900')
        self.x.orders['native-900']=dict(symbol='BTCUSDT',positionSide='BOTH',side='SELL',type='MARKET',
            clientOrderId='native-900',orderId=900,origQty=str(abs(self.x.amount)),executedQty='0',status='NEW')
        self.x.fill('native-900',quantity)
        if not self.x.amount:self.x.algos[cid]['algoStatus']='FINISHED'
    def test_native_child_full_fill_does_not_send_second_market_close(self):
        sid=self.first();self.fire_child(abs(self.x.amount))
        before=len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order' and c[2]['type']=='MARKET'])
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(before,len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order' and c[2]['type']=='MARKET']))
    def test_partial_native_child_is_cancelled_before_residual_close(self):
        sid=self.first();self.fire_child(number('.0004'));remaining=abs(self.x.amount)
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_CLOSE_SUBMITTED')
        self.assertEqual(self.x.orders['native-900']['status'],'CANCELED')
        close=[c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order' and c[2]['type']=='MARKET'][-1]
        self.assertEqual(number(close[2]['quantity']),remaining)


class MultiGridNativeStopTests(unittest.TestCase):
    setUp=multi.MultiSessionTests.setUp
    tearDown=multi.MultiSessionTests.tearDown
    authorize=multi.MultiSessionTests.authorize
    open=multi.MultiSessionTests.open
    open_grid=multi.MultiSessionTests.open_grid
    wide_limits=multi.MultiSessionTests.wide_limits
    def plan(self,symbol,grid=False):
        p=multi.MultiSessionTests.plan(self,symbol,grid)
        if grid:p['management']['trailing']=dict(activation_price='81000',distance_bps='100',min_step_bps='10',native_stop=True)
        return p
    def test_peer_ownership_includes_active_and_retired_stop_generations(self):
        self.wide_limits();btc=self.open('BTCUSDT');self.x.limit_pending=True
        grid,sid=self.open_grid('ETHUSDT');peer=copy.deepcopy({k:a for k,a in self.x.algos.items() if a['symbol']=='BTCUSDT'})
        for price in ('82000','83000'):
            self.x.prices['ETHUSDT']=price
            self.assertEqual(grid.manage(sid,True)['state'],'GRID_STOP_MOVED')
        proof=AccountOwnership(grid).verify();self.assertTrue(all(s['protected'] for s in proof['sessions']))
        self.assertEqual(self.runner.manage(btc,True)['state'],'MANAGING')
        self.assertEqual(peer,{k:a for k,a in self.x.algos.items() if a['symbol']=='BTCUSDT'})
        self.assertEqual(grid.manage(sid,True)['state'],'GRID_RUNNING')
    def test_native_grid_close_preserves_peer_orders_and_reservation(self):
        self.wide_limits();btc=self.open('BTCUSDT');self.x.limit_pending=True;grid,sid=self.open_grid('ETHUSDT')
        self.x.prices['ETHUSDT']='82000';grid.manage(sid,True)
        self.x.prices['ETHUSDT']='81000'
        self.assertEqual(grid.manage(sid,True)['state'],'GRID_CLOSE_SUBMITTED')
        self.assertEqual(grid.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(self.runner.book.state(btc),'COMMITTED')
        self.assertEqual(self.runner.manage(btc,True)['state'],'MANAGING')
