import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agentrader.exchange import ExchangeError
from agentrader.grid_runner import GridRunner
from agentrader.plans import PlanService
from agentrader.risk import number
from agentrader.state import StateStore
from test_grid_plan import grid_plan, grid_snapshot, limits
from test_v2_runner import ExecutionExchange


class GridExchange(ExecutionExchange):
    def __init__(self):
        super().__init__()
        self.price='75725';self.limit_pending=True
        self.late_fill=None
        self.brackets=copy.deepcopy(grid_snapshot()['brackets'])

    def get(self,path,params=None):
        if path=='/fapi/v1/leverageBracket':return [{'symbol':'BTCUSDT','brackets':copy.deepcopy(self.brackets)}]
        if path=='/fapi/v3/account':
            return {'availableBalance':'5000','assets':[{'asset':'USDT','availableBalance':'5000',
                     'marginAvailable':True,'unrealizedProfit':'0'}],'positions':[]}
        if path=='/fapi/v1/accountConfig':return {'canTrade':True,'multiAssetsMargin':True}
        if path=='/fapi/v1/assetIndex':return {'symbol':'USDTUSD','index':'1','askRate':'1','time':int(time.time()*1000)}
        if path=='/fapi/v1/income':return []
        return super().get(path,params)

    def request(self,method,path,params):
        if method=='POST'and path=='/fapi/v1/batchOrders':
            self.calls.append((method,path,dict(params)))
            return [self.request('POST','/fapi/v1/order',p)for p in json.loads(params['batchOrders'])]
        if method=='DELETE'and path=='/fapi/v1/batchOrders':
            self.calls.append((method,path,dict(params)))
            return [self.request('DELETE','/fapi/v1/order',{'symbol':params['symbol'],'origClientOrderId':c})
                    for c in json.loads(params['origClientOrderIdList'])]
        if method=='DELETE'and path=='/fapi/v1/order'and params['origClientOrderId']==self.late_fill:
            self.fill(self.late_fill);self.late_fill=None
        result=super().request(method,path,params)
        if method=='POST'and path=='/fapi/v1/order':
            cid=params['newClientOrderId']
            self.orders[cid]['avgPrice']=params.get('price',self.price)
            result=copy.deepcopy(self.orders[cid])
        return result

    def fill(self,cid,quantity=None):
        order=self.orders[cid]
        target=number(quantity)if quantity is not None else number(order['origQty'])
        delta=target-number(order['executedQty'])
        assert delta>=0
        order.update(executedQty=str(target),status='FILLED'if target==number(order['origQty'])else'PARTIALLY_FILLED',
                     updateTime=int(time.time()*1000),avgPrice=order.get('price',self.price))
        self.amount+=delta*(1 if order['side']=='BUY'else -1)
        if delta:self.trades.append({'orderId':order['orderId'],'qty':str(delta),'side':order['side']})


class GridRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.db'
        self.store=StateStore(self.path);self.service=PlanService(self.store,'local:test')
        self.plan=grid_plan();self.snap=grid_snapshot()
        self.snap.update(observed_at=time.time(),finished_at=time.time(),now_ms=int(time.time()*1000))
        self.x=GridExchange();self.runner=GridRunner(self.service,self.x,limits())
        self.mock=patch('agentrader.grid_runner.collect_flat_snapshot',side_effect=lambda *a:copy.deepcopy(self.snap));self.mock.start()

    def tearDown(self):self.mock.stop();self.store.close();self.temp.cleanup()

    def authorize(self):
        created=self.service.create(self.plan,'local:test')
        self.service.authorize(self.plan['plan_id'],1,created['authorization_token'],'approve','local:test')

    def start(self):
        self.authorize()
        sid=self.runner.open(self.plan['plan_id'],1,True)['session_id']
        for _ in range(6):
            if self.runner.manage(sid,True)['state']=='GRID_RUNNING':break
        return sid

    def cell(self,index,kind):
        return [r['proposal']['params']['newClientOrderId']for r in self.store.sessions()[0]['orders']
                if r['cell']==index and r['kind']==kind][-1]

    def test_preview_does_not_consume_authorization_or_reserve(self):
        self.authorize();r=self.runner.open(self.plan['plan_id'],1,False)
        self.assertEqual(r['state'],'READY');self.assertEqual(self.x.calls,[])
        self.assertEqual(self.service.show(self.plan['plan_id'],1)['state'],'AUTHORIZED')

    def test_grid_initializes_four_slots_and_protects_seed(self):
        sid=self.start()
        s=self.store.sessions()[0]
        self.assertEqual(len(s['orders']),5)
        self.assertEqual(len(self.x.algos),2)
        self.assertEqual(self.runner.book.state(sid),'COMMITTED')
        self.assertEqual(self.x.amount,number('.0009'))
        self.assertEqual(self.x.orders[self.cell(3,'REDUCE')]['reduceOnly'],'true')

    def test_stream_restart_reconciles_durable_fill_before_submitting_partner(self):
        from unittest.mock import Mock
        from agentrader.runtime import stream_monitor_session
        sid=self.start();cid=self.cell(1,'OPEN');self.x.fill(cid)
        order=self.x.orders[cid]
        event=dict(kind='ORDER_TRADE_UPDATE', event_id='durable-fill', symbol='BTCUSDT',
                   client_id=cid, order_id=order['orderId'], side='BUY', status='FILLED',
                   cumulative_filled=order['executedQty'])
        self.store.save_stream_observation(sid,event)
        self.assertTrue(self.store.unresolved_account_command())
        self.store.close();self.store=StateStore(self.path)
        self.service=PlanService(self.store,'local:test');self.runner=GridRunner(self.service,self.x,limits())
        stream=Mock(generation=1);stream.connect.return_value={'state':'STREAM_CONNECTED','generation':1}
        before=len(self.x.calls)
        rows=list(stream_monitor_session(self.runner,sid,stream=stream,execute=True,iterations=1))
        self.assertEqual(rows[-1]['state'],'GRID_ORDER_SUBMITTED')
        self.assertEqual(rows[-1]['kind'],'REDUCE')
        self.assertEqual(len(self.x.calls),before+1)
        self.assertIsNone(self.store.pending_stream_observation(sid))
        self.assertFalse(self.store.unresolved_account_command())

    def test_fill_sell_refill_cycle_preserves_slot_capacity(self):
        sid=self.start();buy=self.cell(1,'OPEN');self.x.fill(buy)
        r=self.runner.manage(sid,True);self.assertEqual(r['kind'],'REDUCE')
        sell=self.cell(1,'REDUCE');self.x.fill(sell)
        self.assertEqual(self.runner.manage(sid,True)['kind'],'OPEN')
        self.assertNotEqual(self.cell(1,'OPEN'),buy)
        self.assertLessEqual(abs(self.x.amount),number('.0036'))

    def test_lowered_exchange_leverage_cap_blocks_refill_before_new_open(self):
        sid=self.start();buy=self.cell(1,'OPEN');self.x.fill(buy)
        self.runner.manage(sid,True);sell=self.cell(1,'REDUCE');self.x.fill(sell)
        self.x.brackets[0]['initialLeverage']=10
        before=len([c for c in self.x.calls if c[0]=='POST' and c[2].get('side')=='BUY'])
        self.runner.manage(sid,True)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST' and c[2].get('side')=='BUY']),before)
        sessions=self.store.sessions()+self.store.sessions(active=False)
        self.assertIn(sessions[0]['phase'],('STOPPING','CLOSED'))

    def test_partial_buy_cancels_remaining_then_sells_actual_fill(self):
        sid=self.start();self.x.fill(self.cell(1,'OPEN'),'.0004')
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_PARTIAL_CANCELED')
        self.assertEqual(self.runner.manage(sid,True)['kind'],'REDUCE')
        self.assertEqual(self.x.orders[self.cell(1,'REDUCE')]['origQty'],'0.0004')

    def test_partial_sell_never_refills_before_residual_is_sold(self):
        sid=self.start();cid=self.cell(3,'REDUCE');self.x.fill(cid,'.0004')
        self.runner.manage(sid,True)
        self.assertEqual(self.runner.manage(sid,True)['kind'],'REDUCE')
        self.assertEqual(self.x.orders[self.cell(3,'REDUCE')]['origQty'],'0.0005')

    def test_stop_inside_band_cancels_lower_buys_and_closes_late_fill(self):
        sid=self.start();self.x.late_fill=self.cell(0,'OPEN');self.x.price='73900'
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_CLOSE_SUBMITTED')
        self.assertEqual(self.x.calls[-1][2]['quantity'],'0.0018')
        self.assertEqual(self.x.calls[-1][2]['reduceOnly'],'true')
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(self.runner.book.state(sid),'RELEASED')
        self.assertEqual(self.x.amount,0)
        self.assertEqual(self.x.get('/fapi/v1/openOrders'),[])
        self.assertEqual(self.x.get('/fapi/v1/openAlgoOrders'),[])

    def test_restart_queries_existing_orders_without_duplicate_posts(self):
        sid=self.start();before=len(self.x.calls)
        self.store.close();self.store=StateStore(self.path);self.service=PlanService(self.store,'local:test')
        self.runner=GridRunner(self.service,self.x,limits())
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_RUNNING')
        self.assertEqual(len(self.x.calls),before)

    def test_lost_seed_response_never_sends_another_seed(self):
        self.authorize();self.x.timeout=True
        with self.assertRaises(ExchangeError):self.runner.open(self.plan['plan_id'],1,True)
        sid=self.store.sessions()[0]['id']
        self.runner.manage(sid,True);self.runner.manage(sid,True)
        entries=[c for c in self.x.calls if c[0]=='POST'and c[1]=='/fapi/v1/order'and c[2]['side']=='BUY']
        self.assertEqual(len(entries),1)
        self.assertEqual(self.x.amount,0)

    def test_foreign_trade_halts_without_touching_account(self):
        sid=self.start();self.x.trades.append({'orderId':999,'qty':'.001','side':'BUY'})
        before=len(self.x.calls)
        with self.assertRaises(ValueError):self.runner.manage(sid,True)
        self.assertEqual(len(self.x.calls),before)

    def test_short_hedge_and_geometric_grid_use_inverse_sides(self):
        self.plan.update(direction='SHORT',position_mode='hedge',stop='79000',targets=[{'price':'72000','fraction':'1'}])
        self.plan['grid']['spacing']='GEOMETRIC';self.snap['position_mode']='hedge'
        self.x.short=True;self.x.hedge=True
        sid=self.start()
        self.assertLess(self.x.amount,0)
        p=self.x.orders[self.cell(0,'REDUCE')]
        self.assertEqual(p['side'],'BUY');self.assertEqual(p['positionSide'],'SHORT');self.assertNotIn('reduceOnly',p)
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_RUNNING')

    def test_cancel_authority_drains_entries_without_forcing_position_close(self):
        sid=self.start();before=self.x.amount
        self.service.cancel(self.plan['plan_id'],1,'local:test')
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_DRAINING')
        self.assertEqual(self.x.amount,before)
        self.assertTrue(all(o['side']=='SELL'for o in self.x.get('/fapi/v1/openOrders')))
        self.assertEqual(self.runner.book.state(sid),'COMMITTED')
        self.x.fill(self.cell(3,'REDUCE'))
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(self.runner.book.state(sid),'RELEASED')

    def test_explicit_stop_preview_does_not_cancel_or_close(self):
        sid=self.start();before=len(self.x.calls)
        self.assertEqual(self.runner.stop(sid,close_position=True)['next_phase'],'STOPPING')
        self.assertEqual(len(self.x.calls),before)
        self.assertEqual(self.store.sessions()[0]['phase'],'ACTIVE')

    def test_explicit_close_grid_cleans_orders_and_releases_envelope(self):
        sid=self.start()
        self.assertEqual(self.runner.stop(sid,close_position=True,execute=True)['state'],'GRID_CLOSE_SUBMITTED')
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(self.x.amount,0)

    def test_external_cancel_does_not_silently_recreate_order(self):
        sid=self.start();cid=self.cell(1,'OPEN');self.x.orders[cid]['status']='CANCELED'
        count=len([c for c in self.x.calls if c[0]=='POST'and c[2].get('side')=='BUY'])
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_DRAINING')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST'and c[2].get('side')=='BUY']),count)

    def test_external_target_cancel_is_not_recreated_or_forced_closed(self):
        sid=self.start();cid=self.cell(3,'REDUCE');self.x.orders[cid]['status']='CANCELED'
        before=len([c for c in self.x.calls if c[0]=='POST'])
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_DRAINING')
        self.assertEqual(self.x.amount,number('.0009'))
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST']),before)
        self.assertEqual(len(self.x.get('/fapi/v1/openAlgoOrders')),2)

    def test_spent_exchange_stop_after_price_bounce_prevents_refill(self):
        sid=self.start();self.x.fill(self.cell(1,'OPEN'))
        self.runner.manage(sid,True);self.x.fill(self.cell(1,'REDUCE'))
        before=len(self.x.calls)
        def spend(*args):
            cid=self.store.sessions()[0]['protections'][0]['params']['clientAlgoId']
            self.x.algos[cid]['algoStatus']='FINISHED'
        with patch.object(self.runner,'_refill_risk',side_effect=spend):
            with self.assertRaises(ValueError):self.runner.manage(sid,True)
        self.assertEqual(len(self.x.calls),before)
        self.assertEqual(self.store.sessions()[0]['phase'],'STOPPING')

    def test_modified_grid_protection_is_rejected_before_write(self):
        sid=self.start();s=self.store.sessions()[0]
        s['protections'][0]['params']['triggerPrice']='70000';self.store.save_session(s)
        count=len(self.x.calls)
        with self.assertRaises(ValueError):self.runner.manage(sid,True)
        self.assertEqual(len(self.x.calls),count)

    def test_no_seed_grid_waits_with_bounded_pending_buys(self):
        self.plan['entry']['reference_price']='77750';self.snap['mark']['markPrice']='77750';self.x.price='77750'
        sid=self.start()
        self.assertEqual(self.x.amount,0)
        self.assertEqual(len(self.x.algos),0)
        self.assertEqual(len(self.x.get('/fapi/v1/openOrders')),4)
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_RUNNING')

    def test_partial_seed_stops_instead_of_overallocating_cells(self):
        self.authorize();self.x.partial=True
        sid=self.runner.open(self.plan['plan_id'],1,True)['session_id']
        self.x.partial=False
        for _ in range(4):
            if self.runner.manage(sid,True)['state']=='CLOSED':break
        self.assertEqual(self.x.amount,0)
        self.assertEqual(self.store.sessions(),[])
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST'and c[2].get('side')=='BUY']),1)

    def test_lost_refill_response_is_canceled_without_another_open(self):
        sid=self.start();self.x.fill(self.cell(1,'OPEN'));self.runner.manage(sid,True)
        self.x.fill(self.cell(1,'REDUCE'));self.x.timeout=True
        with self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        before=len([c for c in self.x.calls if c[0]=='POST'and c[2].get('side')=='BUY'])
        self.runner.manage(sid,True);self.runner.manage(sid,True)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST'and c[2].get('side')=='BUY']),before)
        self.assertEqual(self.x.amount,0)

    def native_stop(self,filled,status):
        s=self.store.sessions()[0];cid=s['protections'][0]['params']['clientAlgoId']
        self.x.algos[cid].update(algoStatus=status,actualOrderId='900')
        self.x.orders['native-900']={'symbol':'BTCUSDT','positionSide':'BOTH','side':'SELL','type':'MARKET',
                 'clientOrderId':'native-900','orderId':900,'origQty':'0.0009','executedQty':'0',
                 'status':'NEW','updateTime':int(time.time()*1000)}
        self.x.fill('native-900',filled)

    def test_native_stop_fill_closes_grid_without_another_market_exit(self):
        sid=self.start();self.native_stop('.0009','FINISHED')
        before=len([c for c in self.x.calls if c[0]=='POST'and c[1]=='/fapi/v1/order'and c[2]['type']=='MARKET'])
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST'and c[1]=='/fapi/v1/order'and c[2]['type']=='MARKET']),before)

    def test_partial_native_child_is_canceled_before_residual_close(self):
        sid=self.start();self.native_stop('.0004','TRIGGERED')
        self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_CLOSE_SUBMITTED')
        self.assertEqual(self.x.orders['native-900']['status'],'CANCELED')
        self.assertEqual(self.x.calls[-1][2]['quantity'],'0.0005')
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')

    def test_read_only_grid_stop_reports_cleanup_without_account_mutation(self):
        sid=self.start();self.x.price='73900';before=len(self.x.calls)
        self.assertEqual(self.runner.manage(sid,False)['state'],'GRID_CANCEL_REQUIRED')
        self.assertEqual(len(self.x.calls),before)
        self.assertEqual(self.runner.book.state(sid),'COMMITTED')

    def test_refill_risk_rejection_stops_pending_entries_before_closing(self):
        sid=self.start();self.x.fill(self.cell(1,'OPEN'));self.runner.manage(sid,True)
        self.x.fill(self.cell(1,'REDUCE'))
        before=len([c for c in self.x.calls if c[0]=='POST'and c[2].get('side')=='BUY'])
        with patch.object(self.runner,'_refill_risk',side_effect=ValueError('daily limit')):
            self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_CLOSE_SUBMITTED')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST'and c[2].get('side')=='BUY']),before)
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')

    def test_confirmed_full_fills_do_not_need_repeated_historical_order_queries(self):
        sid=self.start();buy=self.cell(1,'OPEN');self.x.fill(buy)
        self.runner.manage(sid,True);sell=self.cell(1,'REDUCE');self.x.fill(sell)
        self.runner.manage(sid,True)
        original=self.x.get
        def get(path,params=None):
            if path=='/fapi/v1/order'and self.x.orders[params['origClientOrderId']]['status']=='FILLED':
                raise ExchangeError('old order unavailable',-2013)
            return original(path,params)
        before=len(self.x.calls)
        with patch.object(self.x,'get',side_effect=get):
            self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_RUNNING')
        self.assertEqual(len(self.x.calls),before)

    def test_initial_grid_batch_keeps_open_risk_within_reserved_slots(self):
        sid=self.start();batches=[c for c in self.x.calls if c[0]=='POST'and c[1]=='/fapi/v1/batchOrders']
        self.assertEqual(len(batches),1)
        orders=json.loads(batches[0][2]['batchOrders'])
        self.assertEqual(len(orders),4)
        self.assertEqual(len({p['newClientOrderId']for p in orders}),4)
        pending=sum((number(p['quantity'])for p in orders if p['side']=='BUY'),number(0))
        capacity=sum(number(p['quantity'])for p in self.store.sessions()[0]['compiled']['slots'])
        self.assertEqual(pending+abs(self.x.amount),capacity)
