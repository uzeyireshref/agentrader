import copy
import json
import tempfile
import time
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from agentrader.account_ownership import AccountOwnership
from agentrader.account_runtime import prepare_many,start_many,monitor_account,supervise_account
from agentrader.config import Config
from agentrader.exchange import ExchangeError
from agentrader.grid_runner import GridRunner
from agentrader.plans import PlanService
from agentrader.risk import RiskLimits,number
from agentrader.state import StateStore
from agentrader.v2_runner import V2Runner
from test_orders import SYMBOL
from test_plan_v2 import plan_v2


class MultiExchange:
    config=Config('multi-demo-key','not-a-real-secret')
    offset_ms=0
    def __init__(self):
        self.orders={};self.algos={};self.trades=[];self.calls=[]
        self.prices={'BTCUSDT':'80000','ETHUSDT':'80000'}
        self.amounts={s:number(0) for s in self.prices}
        self.available='5000';self.unrealized='0';self.limit_pending=False;self.lost=False
        self.caps={s:50 for s in self.prices}
        self.incomes=[]
    def sync_time(self):pass
    def get(self,path,params=None):
        params=params or {};symbol=params.get('symbol')
        if path.endswith('/accountConfig'):return {'canTrade':True,'multiAssetsMargin':False}
        if path.endswith('/dual'):return {'dualSidePosition':False}
        if path.endswith('/account'):
            return {'availableBalance':self.available,'assets':[{'asset':'USDT','availableBalance':self.available,'unrealizedProfit':self.unrealized}],
                    'positions':[{'symbol':s,'positionSide':'BOTH','positionAmt':str(q)} for s,q in self.amounts.items()]}
        if path.endswith('/positionRisk'):
            return [{'symbol':s,'positionSide':'BOTH','positionAmt':str(q)} for s,q in self.amounts.items() if symbol is None or s==symbol]
        if path.endswith('/symbolConfig'):return [{'symbol':symbol,'leverage':20,'marginType':'CROSSED'}]
        if path.endswith('/leverageBracket'):
            return [{'symbol':symbol,'brackets':[{'notionalFloor':0,'notionalCap':100000,'initialLeverage':self.caps[symbol],'maintMarginRatio':'.004','cum':'0'}]}]
        if path.endswith('/exchangeInfo'):return {'symbols':[dict(copy.deepcopy(SYMBOL),symbol=s) for s in self.prices]}
        if path.endswith('/premiumIndex'):return {'symbol':symbol,'markPrice':self.prices[symbol],'time':int(time.time()*1000)}
        if path.endswith('/income'):
            return [dict(r,time=params['endTime'],tranId=i+1) for i,r in enumerate(self.incomes)]
        if path.endswith('/userTrades'):
            rows=[copy.deepcopy(t) for t in self.trades if t['symbol']==symbol]
            if 'fromId' in params:rows=[t for t in rows if t['id']>=params['fromId']]
            else:rows=[t for t in rows if params['startTime']<=t['time']<=params['endTime']]
            return rows[:params['limit']]
        if path.endswith('/openOrders'):
            return [copy.deepcopy(o) for o in self.orders.values() if o['status'] in ('NEW','PARTIALLY_FILLED') and (not symbol or o['symbol']==symbol)]
        if path.endswith('/openAlgoOrders'):
            return [copy.deepcopy(o) for o in self.algos.values() if o['algoStatus']=='NEW' and (not symbol or o['symbol']==symbol)]
        if path.endswith('/algoOrder'):return copy.deepcopy(self.algos[params['clientAlgoId']])
        if path.endswith('/order'):
            cid=params['origClientOrderId']
            if cid not in self.orders or self.orders[cid]['symbol']!=symbol:raise ExchangeError('missing',-2013)
            return copy.deepcopy(self.orders[cid])
        raise AssertionError(path)
    def request(self,method,path,params):
        self.calls.append((method,path,copy.deepcopy(params)))
        if path.endswith('/batchOrders'):
            if method=='POST':return [self.request(method,'/fapi/v1/order',p) for p in json.loads(params['batchOrders'])]
            if method=='DELETE':return [self.request(method,'/fapi/v1/order',{'symbol':params['symbol'],'origClientOrderId':cid}) for cid in json.loads(params['origClientOrderIdList'])]
        if method=='DELETE':
            if path.endswith('/algoOrder'):self.algos[params['clientAlgoId']]['algoStatus']='CANCELED'
            else:self.orders[params['origClientOrderId']]['status']='CANCELED'
            return {}
        if path.endswith('/algoOrder'):
            self.algos[params['clientAlgoId']]=params|{'algoStatus':'NEW','orderType':params['type'],'algoId':len(self.algos)+1}
            return copy.deepcopy(self.algos[params['clientAlgoId']])
        cid=params['newClientOrderId'];symbol=params['symbol']
        ident=1+sum(o['symbol']==symbol for o in self.orders.values())
        self.orders[cid]=params|{'clientOrderId':cid,'orderId':ident,'origQty':params['quantity'],
            'executedQty':'0','status':'NEW','avgPrice':'0','updateTime':int(time.time()*1000)}
        if params['type']=='MARKET' or not self.limit_pending:self.fill(cid)
        if self.lost:
            self.lost=False
            raise ExchangeError('lost',delivery_status='UNKNOWN')
        return copy.deepcopy(self.orders[cid])
    def fill(self,cid):
        o=self.orders[cid];delta=number(o['origQty'])-number(o['executedQty']);symbol=o['symbol']
        o.update(status='FILLED',executedQty=o['origQty'],avgPrice=self.prices[symbol],updateTime=int(time.time()*1000))
        self.amounts[symbol]+=delta*(1 if o['side']=='BUY' else -1)
        if delta:self.trades.append({'symbol':symbol,'id':1+sum(t['symbol']==symbol for t in self.trades),
            'orderId':o['orderId'],'time':int(time.time()*1000),'side':o['side'],'qty':str(delta)})


class MultiSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.db'
        self.store=StateStore(self.path);self.service=PlanService(self.store,'local:test');self.x=MultiExchange()
        self.limits=replace(RiskLimits(),max_positions=2,max_notional=Decimal('150'))
        self.runner=V2Runner(self.service,self.x,self.limits)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def plan(self,symbol,grid=False):
        p=plan_v2();p.update(plan_id=symbol.lower(),symbol=symbol)
        p['entry'].update(condition='IMMEDIATE',trigger_price=None)
        if grid:
            p['execution']['strategy']='GRID';p['grid']=dict(lower='78000',upper='82000',intervals=2,spacing='ARITHMETIC')
            p['stop']='77000';p['targets']=[{'price':'84000','fraction':'1'}]
            p['management'].update(allow_scale_in=True,allow_reentry=True)
            p['sizing']['amount']='120'
        return p
    def authorize(self,symbol,grid=False):
        p=self.plan(symbol,grid);created=self.service.create(p,'local:test')
        self.service.authorize(p['plan_id'],1,created['authorization_token'],'approve','local:test')
        return p
    def open(self,symbol):
        p=self.authorize(symbol)
        return self.runner.open(p['plan_id'],1,True)['session_id']

    def test_two_symbols_open_and_manage_without_adopting_each_others_orders(self):
        btc=self.open('BTCUSDT');eth=self.open('ETHUSDT')
        self.assertEqual(self.runner.manage(btc,True)['state'],'MANAGING')
        self.assertEqual(self.runner.manage(eth,True)['state'],'MANAGING')
        self.assertEqual(len(self.store.sessions()),2)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST']),6)
        proof=AccountOwnership(self.runner).verify()
        self.assertEqual(len(proof['sessions']),2)
        # Order IDs are scoped by symbol, not globally unique.
        self.assertEqual({o['orderId'] for o in self.x.orders.values()},{1})

    def test_default_position_limit_still_blocks_second_before_post(self):
        self.open('BTCUSDT');p=self.authorize('ETHUSDT');count=len(self.x.calls)
        other=V2Runner(self.service,self.x,RiskLimits())
        with self.assertRaises(ValueError):other.open(p['plan_id'],1,True)
        self.assertEqual(len(self.x.calls),count)
        self.assertEqual(self.service.show(p['plan_id'],1)['state'],'AUTHORIZED')

    def test_individually_valid_plans_cannot_exceed_shared_notional(self):
        self.runner=V2Runner(self.service,self.x,replace(self.limits,max_notional=Decimal('100')))
        self.open('BTCUSDT');p=self.authorize('ETHUSDT');count=len(self.x.calls)
        with self.assertRaises(ValueError):self.runner.open(p['plan_id'],1,True)
        self.assertEqual(len(self.x.calls),count)

    def test_closing_one_session_preserves_peer_protections_and_reservation(self):
        btc=self.open('BTCUSDT');eth=self.open('ETHUSDT')
        peer={cid:copy.deepcopy(a) for cid,a in self.x.algos.items() if a['symbol']=='ETHUSDT'}
        self.x.prices['BTCUSDT']='82000'
        self.assertEqual(self.runner.manage(btc,True)['state'],'EXIT_SUBMITTED')
        self.assertEqual(self.runner.manage(btc,True)['state'],'CLOSED')
        self.assertEqual(self.runner.book.state(btc),'RELEASED')
        self.assertEqual(self.runner.book.state(eth),'COMMITTED')
        self.assertEqual({cid:a for cid,a in self.x.algos.items() if a['symbol']=='ETHUSDT'},peer)
        self.assertEqual(self.runner.manage(eth,True)['state'],'MANAGING')

    def test_foreign_open_order_cannot_reuse_other_symbols_broker_id(self):
        self.open('BTCUSDT');eth=self.open('ETHUSDT');count=len(self.x.calls)
        self.x.orders['manual']=dict(symbol='XRPUSDT',clientOrderId='manual',orderId=1,status='NEW',
                                    side='BUY',positionSide='BOTH',type='LIMIT',origQty='1',executedQty='0',price='1')
        with self.assertRaises(ValueError):self.runner.manage(eth,True)
        self.assertEqual(len(self.x.calls),count)

    def test_foreign_position_or_mismatched_peer_fill_blocks_management(self):
        self.open('BTCUSDT');eth=self.open('ETHUSDT');count=len(self.x.calls)
        self.x.amounts['BTCUSDT']+=number('.001')
        with self.assertRaises(ValueError):self.runner.manage(eth,True)
        self.assertEqual(len(self.x.calls),count)

    def test_restart_preserves_ownership_and_full_reservations(self):
        btc=self.open('BTCUSDT');eth=self.open('ETHUSDT');count=len(self.x.calls)
        self.store.close();self.store=StateStore(self.path);self.service=PlanService(self.store,'local:test')
        self.runner=V2Runner(self.service,self.x,self.limits)
        self.assertEqual(self.runner.manage(btc,True)['state'],'MANAGING')
        self.assertEqual(self.runner.manage(eth,True)['state'],'MANAGING')
        self.assertEqual(len(self.x.calls),count)

    def test_unprotected_peer_cannot_admit_new_entry(self):
        self.open('BTCUSDT');p=self.authorize('ETHUSDT');count=len(self.x.calls)
        for a in self.x.algos.values():
            if a['type']=='STOP_MARKET':a['algoStatus']='CANCELED'
        with self.assertRaises(ValueError):self.runner.open(p['plan_id'],1,True)
        self.assertEqual(len(self.x.calls),count)

    def test_two_pending_entries_reserve_capacity_even_with_no_fills(self):
        self.x.limit_pending=True
        for symbol in ('BTCUSDT','ETHUSDT'):
            p=self.plan(symbol);p['entry'].update(condition='LIMIT',trigger_price='79900')
            created=self.service.create(p,'local:test')
            self.service.authorize(p['plan_id'],1,created['authorization_token'],'approve','local:test')
            self.runner.open(p['plan_id'],1,True)
        self.assertTrue(all(q==0 for q in self.x.amounts.values()))
        self.assertEqual(len(self.store.sessions()),2)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM risk_reservations WHERE state='COMMITTED'").fetchone()[0],2)

    def test_changed_api_account_is_not_allowed_to_adopt_active_sessions(self):
        self.open('BTCUSDT');p=self.authorize('ETHUSDT');count=len(self.x.calls)
        self.x.config=Config('other-key','other-secret')
        other=V2Runner(self.service,self.x,self.limits)
        with self.assertRaises(ValueError):other.open(p['plan_id'],1,True)
        self.assertEqual(len(self.x.calls),count)

    def wide_limits(self):
        self.limits=replace(self.limits,max_notional=Decimal('400'),max_trade_loss=Decimal('100'),
                            max_total_loss=Decimal('100'),max_daily_loss=Decimal('100'))
        self.runner=V2Runner(self.service,self.x,self.limits)

    def open_grid(self,symbol):
        p=self.authorize(symbol,grid=True);runner=GridRunner(self.service,self.x,self.limits)
        sid=runner.open(p['plan_id'],1,True)['session_id']
        for _ in range(4):
            if runner.manage(sid,True)['state']=='GRID_RUNNING':break
        return runner,sid

    def test_single_and_grid_coexist_and_stop_only_cancels_grid_symbol(self):
        self.wide_limits();btc=self.open('BTCUSDT');self.x.limit_pending=True
        grid,eth=self.open_grid('ETHUSDT')
        self.assertEqual(self.runner.manage(btc,True)['state'],'MANAGING')
        protected={cid:copy.deepcopy(a) for cid,a in self.x.algos.items() if a['symbol']=='BTCUSDT'}
        start=len(self.x.calls)
        grid.stop(eth,close_position=False,execute=True)
        changed=self.x.calls[start:]
        self.assertTrue(all(c[2].get('symbol','ETHUSDT')!='BTCUSDT' for c in changed))
        self.assertEqual({cid:a for cid,a in self.x.algos.items() if a['symbol']=='BTCUSDT'},protected)
        self.assertGreater(self.x.amounts['BTCUSDT'],0)
        self.assertEqual(self.runner.manage(btc,True)['state'],'MANAGING')

    def test_two_grids_manage_and_close_independently(self):
        self.wide_limits();self.x.limit_pending=True
        btc,bid=self.open_grid('BTCUSDT');eth,eid=self.open_grid('ETHUSDT')
        self.assertEqual(btc.manage(bid,True)['state'],'GRID_RUNNING')
        self.assertEqual(eth.manage(eid,True)['state'],'GRID_RUNNING')
        peer_orders={cid:copy.deepcopy(o) for cid,o in self.x.orders.items() if o['symbol']=='ETHUSDT'}
        btc.stop(bid,close_position=True,execute=True)
        for _ in range(4):
            if btc.manage(bid,True)['state']=='CLOSED':break
        self.assertEqual(btc.book.state(bid),'RELEASED')
        self.assertEqual(eth.book.state(eid),'COMMITTED')
        self.assertEqual({cid:o for cid,o in self.x.orders.items() if o['symbol']=='ETHUSDT'},peer_orders)
        self.assertEqual(eth.manage(eid,True)['state'],'GRID_RUNNING')

    def test_peer_leverage_tier_change_blocks_joint_refill(self):
        self.wide_limits();self.open('BTCUSDT');self.x.limit_pending=True
        grid,sid=self.open_grid('ETHUSDT')
        session=next(s for s in self.store.sessions() if s['id']==sid)
        opening=next(r for r in session['orders'] if r['kind']=='OPEN')
        self.x.fill(opening['proposal']['params']['newClientOrderId'])
        grid.manage(sid,True)
        session=next(s for s in self.store.sessions() if s['id']==sid)
        reducing=[r for r in session['orders'] if r['cell']==opening['cell'] and r['kind']=='REDUCE'][-1]
        self.x.fill(reducing['proposal']['params']['newClientOrderId'])
        self.x.caps['BTCUSDT']=10
        count=len([c for c in self.x.calls if c[0]=='POST' and c[2].get('symbol')=='ETHUSDT' and c[2].get('side')=='BUY'])
        grid.manage(sid,True)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST' and c[2].get('symbol')=='ETHUSDT' and c[2].get('side')=='BUY']),count)

    def test_multi_preflight_checks_shared_budget_before_any_entry(self):
        self.authorize('BTCUSDT');self.authorize('ETHUSDT')
        with self.assertRaises(ValueError):
            start_many(self.service,self.x,RiskLimits(),[('btcusdt',1),('ethusdt',1)],execute=True)
        self.assertEqual(self.x.calls,[])
        self.assertEqual(self.store.sessions(),[])

    def test_multi_preview_does_not_claim_or_reserve_then_explicit_start_works(self):
        self.authorize('BTCUSDT');self.authorize('ETHUSDT');refs=[('btcusdt',1),('ethusdt',1)]
        result=prepare_many(self.service,self.x,self.limits,refs)
        self.assertEqual(result['state'],'READY');self.assertEqual(self.x.calls,[])
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM risk_reservations').fetchone()[0],0)
        result=start_many(self.service,self.x,self.limits,refs,execute=True)
        self.assertEqual(result['state'],'STARTED');self.assertEqual(len(self.store.sessions()),2)

    def test_account_scheduler_manages_both_without_reopening(self):
        self.open('BTCUSDT');self.open('ETHUSDT');before=len(self.x.calls)
        rows=list(monitor_account(self.service,self.x,self.limits,execute=True,iterations=2,sleep=lambda _:None))
        self.assertEqual(len(rows),4)
        self.assertEqual(len({r['session_id'] for r in rows}),2)
        self.assertEqual(len(self.x.calls),before)

    def test_one_service_stop_does_not_resume_or_stop_peer(self):
        from agentrader.service_cli import request_stop
        btc=self.open('BTCUSDT');eth=self.open('ETHUSDT');before=len(self.x.calls)
        request_stop(self.store,btc,'local:test')
        rows=list(monitor_account(self.service,self.x,self.limits,execute=True,iterations=2,sleep=lambda _:None))
        self.assertEqual(sum(r['session_id']==btc for r in rows),1)
        self.assertEqual(sum(r['session_id']==eth for r in rows),2)
        self.assertTrue(rows[0]['service_stopped'])
        self.assertEqual(len(self.x.calls),before)

    def test_partial_start_does_not_repeat_unknown_second_entry(self):
        self.authorize('BTCUSDT');self.authorize('ETHUSDT')
        original=self.x.request
        def request(method,path,params):
            if method=='POST' and path=='/fapi/v1/order' and params.get('symbol')=='ETHUSDT':self.x.lost=True
            return original(method,path,params)
        self.x.request=request
        result=start_many(self.service,self.x,self.limits,[('btcusdt',1),('ethusdt',1)],execute=True)
        self.assertEqual(result['state'],'PARTIAL_START_REVIEW_REQUIRED')
        self.assertEqual(len(result['opened']),1)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order' and c[2]['symbol']=='ETHUSDT']),1)
        self.assertTrue(any(a['symbol']=='BTCUSDT' and a['type']=='STOP_MARKET' and a['algoStatus']=='NEW' for a in self.x.algos.values()))

    def test_finite_account_monitor_drains_each_grid_without_flattening(self):
        self.wide_limits();self.x.limit_pending=True
        self.open_grid('BTCUSDT');self.open_grid('ETHUSDT')
        amounts=dict(self.x.amounts);rows=[]
        self.assertTrue(supervise_account(self.service,self.x,self.limits,execute=True,iterations=1,emit=rows.append))
        self.assertTrue(all(s['phase']=='DRAINING' for s in self.store.sessions()))
        self.assertEqual(self.x.amounts,amounts)

    def test_corrupted_peer_risk_envelope_cannot_reduce_shared_budget(self):
        from agentrader.plans import canonical,digest
        btc=self.open('BTCUSDT');eth=self.open('ETHUSDT');before=len(self.x.calls)
        row=self.store.db.execute('SELECT body FROM risk_reservations WHERE reservation_id=?',(btc,)).fetchone()
        body=json.loads(row['body']);body['exposures'][0]['quantity']='0.0001'
        with self.store.db:self.store.db.execute('UPDATE risk_reservations SET body=?,digest=? WHERE reservation_id=?',(canonical(body),digest(body),btc))
        with self.assertRaises(ValueError):self.runner.manage(eth,True)
        self.assertEqual(len(self.x.calls),before)

    def test_joint_stop_loss_and_daily_loss_are_account_wide(self):
        self.runner=V2Runner(self.service,self.x,replace(self.limits,max_total_loss=Decimal('2')))
        self.open('BTCUSDT');p=self.authorize('ETHUSDT');count=len(self.x.calls)
        with self.assertRaises(ValueError):self.runner.open(p['plan_id'],1,True)
        self.assertEqual(len(self.x.calls),count)

    def test_daily_income_is_counted_once_against_combined_exposure(self):
        self.x.incomes=[{'asset':'USDT','incomeType':'REALIZED_PNL','income':'-23'}]
        self.open('BTCUSDT');p=self.authorize('ETHUSDT');count=len(self.x.calls)
        with self.assertRaises(ValueError):self.runner.open(p['plan_id'],1,True)
        self.assertEqual(len(self.x.calls),count)

    def test_pre_claim_crash_can_release_unused_budget_and_cancel_plan_atomically(self):
        from agentrader.v2_preflight import prepare_single
        from agentrader.portfolio import Exposure
        p=self.authorize('BTCUSDT');row=self.service.show(p['plan_id'],1)
        snap=self.runner._snapshot(p['symbol']);prepared=prepare_single(p,snap,self.limits)
        self.runner.book.reserve('unused',self.service.owner,row['digest'],[Exposure(**e) for e in prepared['exposures']],snap,self.limits)
        listed=self.runner.book.list_reservations(self.service.owner)
        self.assertEqual(len(listed),1);self.assertFalse(listed[0]['has_session'])
        self.assertEqual(self.runner.book.list_reservations('foreign'),[])
        result=self.runner.book.release_unused('unused',self.service.owner,AccountOwnership(self.runner))
        self.assertEqual(result['state'],'UNUSED_RESERVATION_RELEASED')
        self.assertEqual(self.service.show(p['plan_id'],1)['state'],'CANCELED')
        self.assertEqual(self.runner.book.state('unused'),'RELEASED')
        with self.assertRaises(ValueError):self.service.claim(p['plan_id'],1,'unused')
        self.assertEqual(self.x.calls,[])

    def test_submitted_or_uncertain_budget_is_never_released_as_unused(self):
        sid=self.open('BTCUSDT');before=len(self.x.calls)
        with self.assertRaises(ValueError):self.runner.book.release_unused(sid,self.service.owner,AccountOwnership(self.runner))
        self.assertEqual(self.runner.book.state(sid),'COMMITTED');self.assertEqual(len(self.x.calls),before)

    def test_modified_peer_stop_is_not_accepted_as_protection(self):
        self.open('BTCUSDT');eth=self.open('ETHUSDT');before=len(self.x.calls)
        for a in self.x.algos.values():
            if a['symbol']=='BTCUSDT' and a['type']=='STOP_MARKET':a['triggerPrice']='70000'
        with self.assertRaises(ValueError):self.runner.manage(eth,True)
        self.assertEqual(len(self.x.calls),before)

    def test_hedge_long_and_short_on_distinct_symbols_reconcile_by_position_side(self):
        original=self.x.get
        def get(path,params=None):
            if path.endswith('/dual'):return {'dualSidePosition':True}
            result=original(path,params)
            if path.endswith('/positionRisk'):
                for p in result:p['positionSide']='LONG' if p['symbol']=='BTCUSDT' else 'SHORT'
            if path.endswith('/account'):
                for p in result['positions']:p['positionSide']='LONG' if p['symbol']=='BTCUSDT' else 'SHORT'
            return result
        self.x.get=get
        sessions=[]
        for symbol in ('BTCUSDT','ETHUSDT'):
            p=self.plan(symbol);p['position_mode']='hedge'
            if symbol=='ETHUSDT':p.update(direction='SHORT',stop='81600',targets=[{'price':'78400','fraction':'1'}])
            created=self.service.create(p,'local:test')
            self.service.authorize(p['plan_id'],1,created['authorization_token'],'approve','local:test')
            sessions.append(self.runner.open(p['plan_id'],1,True)['session_id'])
        self.assertGreater(self.x.amounts['BTCUSDT'],0);self.assertLess(self.x.amounts['ETHUSDT'],0)
        for sid in sessions:self.assertEqual(self.runner.manage(sid,True)['state'],'MANAGING')

    def test_unresolved_peer_read_stops_scheduler_without_financial_retry(self):
        self.open('BTCUSDT');self.open('ETHUSDT');before=len(self.x.calls)
        original=self.x.get
        def get(path,params=None):
            if path=='/fapi/v1/order' and params['symbol']=='BTCUSDT':raise ExchangeError('offline',delivery_status='READ_FAILED')
            return original(path,params)
        self.x.get=get
        rows=list(monitor_account(self.service,self.x,self.limits,execute=True,iterations=0))
        self.assertEqual(rows[-1]['state'],'ACCOUNT_REVIEW_REQUIRED')
        self.assertEqual(len(self.x.calls),before)
        self.assertEqual(len(self.store.sessions()),2)
        self.assertTrue(all(a['algoStatus']=='NEW' for a in self.x.algos.values()))

    def test_missing_legacy_envelope_is_not_silently_adopted_for_multi_entry(self):
        btc=self.open('BTCUSDT');p=self.authorize('ETHUSDT');before=len(self.x.calls)
        s=self.store.sessions()[0];s['prepared'].pop('exposures');self.store.save_session(s)
        with self.store.db:self.store.db.execute('DELETE FROM risk_reservations WHERE reservation_id=?',(btc,))
        with self.assertRaises(ValueError):self.runner.open(p['plan_id'],1,True)
        self.assertEqual(len(self.x.calls),before)

    def test_peer_unrealized_loss_blocks_new_entry_without_touching_peer(self):
        self.open('BTCUSDT');p=self.authorize('ETHUSDT');before=len(self.x.calls)
        self.x.unrealized='-24'
        with self.assertRaises(ValueError):self.runner.open(p['plan_id'],1,True)
        self.assertEqual(len(self.x.calls),before)

    def test_isolated_peers_require_real_wallet_coverage(self):
        original=self.x.get;wallet={'BTCUSDT':'20','ETHUSDT':'20'}
        def get(path,params=None):
            result=original(path,params)
            if path.endswith('/symbolConfig'):
                for r in result:r['marginType']='ISOLATED'
            if path.endswith('/positionRisk'):
                for r in result:r.update(entryPrice='80000',isolatedWallet=wallet[r['symbol']])
            return result
        self.x.get=get
        sessions=[]
        for symbol in ('BTCUSDT','ETHUSDT'):
            p=self.plan(symbol);p['execution']['margin_mode']='ISOLATED'
            created=self.service.create(p,'local:test')
            self.service.authorize(p['plan_id'],1,created['authorization_token'],'approve','local:test')
            sessions.append(self.runner.open(p['plan_id'],1,True)['session_id'])
        before=len(self.x.calls);wallet['BTCUSDT']='0.01'
        with self.assertRaises(ValueError):self.runner.manage(sessions[1],True)
        self.assertEqual(len(self.x.calls),before)

    def test_condition_change_after_bundle_preflight_does_not_start_later_plan(self):
        p=self.plan('BTCUSDT');p['entry'].update(condition='MARK_AT_OR_BELOW',trigger_price='80000')
        created=self.service.create(p,'local:test')
        self.service.authorize(p['plan_id'],1,created['authorization_token'],'approve','local:test')
        self.authorize('ETHUSDT');original=self.x.get;reads=0
        def get(path,params=None):
            nonlocal reads
            if path.endswith('/premiumIndex') and params['symbol']=='BTCUSDT':
                reads+=1
                if reads>1:self.x.prices['BTCUSDT']='80010'
            return original(path,params)
        self.x.get=get
        result=start_many(self.service,self.x,self.limits,[('btcusdt',1),('ethusdt',1)],execute=True)
        self.assertEqual(result['state'],'PARTIAL_START_REVIEW_REQUIRED')
        self.assertEqual(result['failure']['kind'],'CONDITION_CHANGED')
        self.assertEqual(self.x.calls,[])
