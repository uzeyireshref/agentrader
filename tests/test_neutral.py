import copy
import io
import json
from contextlib import redirect_stdout
import tempfile
import time
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from agentrader.account_ownership import AccountOwnership
from agentrader.exchange import ExchangeError
from agentrader.neutral_plan import compile_neutral,validate_neutral
from agentrader.neutral_runner import NeutralGridRunner
from agentrader.plan_execution import run_plan
from agentrader.plans import PlanService
from agentrader.risk import RiskLimits,number
from agentrader.state import StateStore
from agentrader.account_runtime import monitor_account,prepare_many
from agentrader.service_cli import request_stop
from agentrader.runtime import supervise_session
from agentrader.v2_preflight import collect_flat_snapshot
from test_multi_session import MultiExchange
from test_plan_v2 import plan_v2


def neutral_plan():
    p=plan_v2();p.update(plan_id='neutral-test',direction='NEUTRAL',position_mode='hedge',targets=[],
                        stop={'lower':'76000','upper':'84000'})
    p['execution']['strategy']='NEUTRAL_GRID';p['sizing']['amount']='300'
    p['entry'].update(condition='IMMEDIATE',trigger_price=None)
    p['grid']=dict(lower='78000',upper='82000',intervals=4,spacing='ARITHMETIC',anchor_price='80000',
                   long_fraction='.5',short_fraction='.5')
    p['management'].update(allow_scale_in=True,allow_reentry=True)
    return p


def neutral_limits():
    return replace(RiskLimits(),max_positions=2,max_notional=Decimal('400'),max_trade_loss=Decimal('100'),
                   max_total_loss=Decimal('100'),max_daily_loss=Decimal('100'))


class NeutralExchange(MultiExchange):
    def __init__(self):
        super().__init__();self.limit_pending=True
        self.legs={(sym,side):number(0) for sym in self.prices for side in ('LONG','SHORT')}
        self.late_fill=None;self.algo_lost=False;self.cancel_lost=False
    def get(self,path,params=None):
        params=params or {}
        if path.endswith('/dual'):return {'dualSidePosition':True}
        if path.endswith('/positionRisk'):
            return [{'symbol':sym,'positionSide':side,'positionAmt':str(q),'entryPrice':'80000','isolatedWallet':'50'}
                    for (sym,side),q in self.legs.items() if not params.get('symbol') or params['symbol']==sym]
        result=super().get(path,params)
        if path.endswith('/account'):
            result['positions']=[{'symbol':sym,'positionSide':side,'positionAmt':str(q)} for (sym,side),q in self.legs.items()]
        return result
    def fill(self,cid,quantity=None):
        o=self.orders[cid];target=number(o['origQty']) if quantity is None else number(quantity)
        delta=target-number(o['executedQty']);assert delta>=0
        key=o['symbol'],o['positionSide'];amount=self.legs[key]+delta*(1 if o['side']=='BUY' else -1)
        assert amount>=0 if key[1]=='LONG' else amount<=0
        self.legs[key]=amount;self.amounts[key[0]]=sum(q for (sym,_),q in self.legs.items() if sym==key[0])
        o.update(executedQty=str(target),status='FILLED' if target==number(o['origQty']) else 'PARTIALLY_FILLED',
                 updateTime=int(time.time()*1000),avgPrice=o.get('price',self.prices[key[0]]))
        if delta:self.trades.append(dict(symbol=key[0],positionSide=key[1],id=1+sum(t['symbol']==key[0] for t in self.trades),
            orderId=o['orderId'],time=int(time.time()*1000),side=o['side'],qty=str(delta)))
    def request(self,method,path,params):
        if method=='DELETE' and path.endswith('/order') and params['origClientOrderId']==self.late_fill:
            self.fill(self.late_fill);self.late_fill=None
        reply=super().request(method,path,params)
        if method=='POST' and path.endswith('/algoOrder') and self.algo_lost:
            self.algo_lost=False;raise ExchangeError('lost',delivery_status='UNKNOWN')
        if method=='DELETE' and self.cancel_lost:
            self.cancel_lost=False;raise ExchangeError('lost',delivery_status='UNKNOWN')
        return reply
    def fire(self,side,kind='STOP_MARKET'):
        a=next(a for a in self.algos.values() if a['positionSide']==side and a['type']==kind and a['algoStatus']=='NEW')
        symbol=a['symbol'];q=abs(self.legs[symbol,side]);oid=1+sum(o['symbol']==symbol for o in self.orders.values())
        cid='native-child-'+str(oid)
        self.orders[cid]=dict(symbol=symbol,positionSide=side,side=a['side'],type='MARKET',clientOrderId=cid,
                              orderId=oid,origQty=str(q),executedQty='0',status='NEW',updateTime=int(time.time()*1000))
        self.fill(cid);a.update(algoStatus='FINISHED',actualOrderId=str(oid),actualQty=str(q))


class NeutralTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.db'
        self.store=StateStore(self.path);self.service=PlanService(self.store,'local:test')
        self.x=NeutralExchange();self.limits=neutral_limits();self.plan=neutral_plan()
        self.runner=NeutralGridRunner(self.service,self.x,self.limits)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def snapshot(self):return collect_flat_snapshot(self.x,self.plan['symbol'],self.limits)
    def authorize(self):
        created=self.service.create(self.plan,'local:test')
        self.service.authorize(self.plan['plan_id'],1,created['authorization_token'],'approve','local:test')
    def start(self):
        self.authorize();sid=self.runner.open(self.plan['plan_id'],1,True)['session_id']
        for _ in range(10):
            result=self.runner.manage(sid,True)
            if result['state']=='NEUTRAL_RUNNING':break
        return sid
    def order(self,cell,kind='OPEN'):
        s=self.store.sessions()[0]
        return [r['proposal']['params']['newClientOrderId'] for r in s['orders'] if r['cell']==cell and r['kind']==kind][-1]

    def until_order(self,sid,cell,kind='REDUCE'):
        for _ in range(8):
            self.runner.manage(sid,True)
            matches=[r for r in self.store.sessions()[0]['orders'] if r['cell']==cell and r['kind']==kind]
            if matches:return matches[-1]['proposal']['params']['newClientOrderId']
        self.fail('Beklenen hücre emri oluşmadı.')

    def test_compiler_splits_one_budget_and_counts_both_legs_without_netting(self):
        compiled=compile_neutral(self.plan,self.snapshot(),self.limits)
        self.assertEqual(compiled['budgets'],{'LONG':'150.0','SHORT':'150.0'})
        self.assertEqual([c['position_side'] for c in compiled['slots']],['LONG','LONG','SHORT','SHORT'])
        self.assertLessEqual(number(compiled['notional_ceiling']),300)
        self.assertEqual(len(compiled['exposures']),2)
        self.assertGreater(number(compiled['risk']['risk_with_fee_reserve']),0)

    def test_200_nominal_does_not_invent_more_budget_to_meet_cell_minimum(self):
        self.plan['sizing']['amount']='200'
        with self.assertRaises(ValueError):compile_neutral(self.plan,self.snapshot(),self.limits)
        self.assertEqual(self.x.calls,[])

    def test_hedge_anchor_and_explicit_fraction_rules(self):
        for mutate in (lambda p:p.update(position_mode='one-way'),lambda p:p['grid'].update(long_fraction='.7'),
                       lambda p:p['grid'].update(anchor_price='80100'),lambda p:p['stop'].update(lower='79000')):
            p=copy.deepcopy(self.plan);mutate(p)
            with self.assertRaises(ValueError):compile_neutral(p,self.snapshot(),self.limits)

    def test_default_position_limit_rejects_two_sides_before_claim_or_orders(self):
        self.authorize();runner=NeutralGridRunner(self.service,self.x,replace(self.limits,max_positions=RiskLimits().max_positions))
        with self.assertRaisesRegex(ValueError,'Pozisyon'):runner.open(self.plan['plan_id'],1,True)
        self.assertEqual(self.x.calls,[])
        self.assertEqual(self.service.show(self.plan['plan_id'],1)['state'],'AUTHORIZED')

    def test_preview_and_existing_run_plan_routing(self):
        self.authorize();result=run_plan(self.service,self.x,self.limits,self.plan['plan_id'],1,False)
        self.assertEqual(result['state'],'READY');self.assertFalse(result['executed'])
        self.assertEqual(self.x.calls,[]);self.assertEqual(self.store.sessions(),[])

    def test_initial_limits_have_correct_sides_no_market_seed_and_one_reservation(self):
        sid=self.start();self.assertEqual(len(self.store.sessions()),1)
        self.assertEqual(self.runner.book.state(sid),'COMMITTED')
        self.assertEqual(len(self.x.orders),4)
        self.assertTrue(all(o['type']=='LIMIT' for o in self.x.orders.values()))
        self.assertTrue(all(o['side']==('BUY' if o['positionSide']=='LONG' else 'SELL') for o in self.x.orders.values()))
        self.assertTrue(all(o['selfTradePreventionMode']=='EXPIRE_BOTH' for o in self.x.orders.values()))
        self.assertTrue(all(q==0 for q in self.x.legs.values()))

    def test_long_fill_gets_native_protection_then_profit_order_and_refill(self):
        sid=self.start();original=self.order(0);self.x.fill(original)
        self.assertEqual(self.runner.manage(sid,True)['state'],'NEUTRAL_CONFLICT_CANCELED')
        self.assertEqual(len([a for a in self.x.algos.values() if a['positionSide']=='LONG' and a['algoStatus']=='NEW']),2)
        reduce=self.until_order(sid,0);self.assertEqual(self.x.orders[reduce]['side'],'SELL')
        self.x.fill(reduce)
        for _ in range(8):
            self.runner.manage(sid,True)
            if self.order(0)!=original:break
        self.assertEqual(self.x.legs['BTCUSDT','LONG'],0)
        self.assertNotEqual(self.order(0),original)

    def test_short_fill_reduces_with_buy_on_short_position_side(self):
        sid=self.start();self.x.fill(self.order(3));reduction=self.x.orders[self.until_order(sid,3)]
        self.assertEqual((reduction['side'],reduction['positionSide']),('BUY','SHORT'))
        self.assertLess(self.x.legs['BTCUSDT','SHORT'],0)

    def test_partial_open_cancels_remaining_before_reducing_actual_fill(self):
        sid=self.start();cid=self.order(0);self.x.fill(cid,'.0003')
        self.assertEqual(self.runner.manage(sid,True)['state'],'NEUTRAL_PARTIAL_CANCELED')
        self.assertEqual(number(self.x.orders[self.until_order(sid,0)]['origQty']),number('.0003'))

    def test_stop_cancels_both_side_entries_and_closes_gross_legs_even_if_net_zero(self):
        sid=self.start();self.x.fill(self.order(0));self.x.fill(self.order(3));self.runner.manage(sid,True)
        self.assertEqual(self.x.amounts['BTCUSDT'],0)
        self.x.prices['BTCUSDT']='75000'
        self.runner.manage(sid,True)
        for _ in range(8):
            if self.runner.manage(sid,True)['state']=='CLOSED':break
        self.assertTrue(all(q==0 for q in self.x.legs.values()))
        self.assertEqual(self.runner.book.state(sid),'RELEASED')
        self.assertEqual(self.store.sessions(),[])

    def test_restart_never_reposts_existing_cell_orders(self):
        sid=self.start();before=len(self.x.calls)
        self.store.close();self.store=StateStore(self.path);self.service=PlanService(self.store,'local:test')
        self.runner=NeutralGridRunner(self.service,self.x,self.limits)
        self.assertEqual(self.runner.manage(sid,True)['state'],'NEUTRAL_RUNNING')
        self.assertEqual(len(self.x.calls),before)

    def test_native_trigger_latches_global_stop_and_reconciles_child_fill(self):
        sid=self.start();self.x.fill(self.order(0));self.runner.manage(sid,True)
        self.x.fire('LONG')
        for _ in range(8):
            if self.runner.manage(sid,True)['state']=='CLOSED':break
        self.assertEqual(self.store.sessions(),[])
        self.assertEqual(self.runner.book.state(sid),'RELEASED')

    def close_until_flat(self,sid):
        for _ in range(12):
            if self.runner.manage(sid,True)['state']=='CLOSED':return
        self.fail('Neutral güvenli kapanış tamamlanmadı.')

    def test_geometric_grid_keeps_exact_center_and_uses_one_gross_budget(self):
        self.plan['grid'].update(lower='64000',upper='100000',spacing='GEOMETRIC')
        self.plan['stop'].update(lower='60000',upper='104000');self.plan['sizing']['amount']='500'
        limits=replace(self.limits,max_notional=Decimal('600'),max_trade_loss=Decimal('300'),max_total_loss=Decimal('300'),max_daily_loss=Decimal('300'))
        result=compile_neutral(self.plan,self.snapshot(),limits)
        self.assertEqual(number(result['slots'][1]['upper']),80000)
        self.assertLessEqual(number(result['notional_ceiling']),500)

    def test_asymmetric_shares_do_not_double_total_nominal(self):
        self.plan['grid'].update(long_fraction='.7',short_fraction='.3');self.plan['sizing']['amount']='500'
        result=compile_neutral(self.plan,self.snapshot(),replace(self.limits,max_notional=Decimal('600')))
        self.assertEqual(number(result['budgets']['LONG']),350);self.assertEqual(number(result['budgets']['SHORT']),150)
        self.assertLessEqual(number(result['notional_ceiling']),500)
        self.assertGreater(number(result['exposures'][0]['quantity']),number(result['exposures'][1]['quantity']))

    def test_isolated_liquidation_before_global_stop_is_rejected(self):
        self.plan['execution']['margin_mode']='ISOLATED';snap=self.snapshot();snap['settings']['marginType']='ISOLATED'
        with self.assertRaises(ValueError):compile_neutral(self.plan,snap,self.limits)
        self.assertEqual(self.x.calls,[])

    def test_partial_reduce_cancels_remainder_and_places_only_residual(self):
        sid=self.start();self.x.fill(self.order(0));first=self.until_order(sid,0)
        self.x.fill(first,'.0003')
        self.assertEqual(self.runner.manage(sid,True)['state'],'NEUTRAL_PARTIAL_CANCELED')
        second=self.until_order(sid,0)
        if second==first:self.runner.manage(sid,True);second=self.order(0,'REDUCE')
        self.assertNotEqual(first,second)
        self.assertEqual(number(self.x.orders[second]['origQty']),number('.0005'))

    def test_flat_native_expiry_allows_a_new_distinct_generation(self):
        sid=self.start();self.x.fill(self.order(0));reduction=self.until_order(sid,0);self.x.fill(reduction)
        old={cid for cid,a in self.x.algos.items() if a['positionSide']=='LONG'}
        for cid in old:self.x.algos[cid]['algoStatus']='EXPIRED'
        original=self.order(0)
        for _ in range(8):
            self.runner.manage(sid,True)
            if self.order(0)!=original:break
        self.x.fill(self.order(0));self.runner.manage(sid,True)
        new={cid for cid,a in self.x.algos.items() if a['positionSide']=='LONG' and a['algoStatus']=='NEW'}
        self.assertEqual(len(new),2);self.assertFalse(old&new)
        self.assertTrue(all(p['generation']==1 for p in self.store.sessions()[0]['protections'] if p['params']['clientAlgoId'] in new))

    def test_live_native_expiry_stops_whole_plan_without_recreating_protection(self):
        sid=self.start();self.x.fill(self.order(0));self.runner.manage(sid,True)
        before=len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/algoOrder'])
        next(a for a in self.x.algos.values() if a['type']=='STOP_MARKET')['algoStatus']='EXPIRED'
        self.close_until_flat(sid)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/algoOrder']),before)

    def test_lost_entry_response_never_reposts_entry(self):
        self.authorize();self.x.lost=True
        with self.assertRaises(ExchangeError):self.runner.open(self.plan['plan_id'],1,True)
        sid=self.store.sessions()[0]['id'];posts=len([c for c in self.x.calls if c[0]=='POST'])
        self.close_until_flat(sid)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST']),posts)

    def test_lost_native_response_does_not_duplicate_native_post(self):
        sid=self.start();self.x.fill(self.order(0));self.x.algo_lost=True
        with self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        before=len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/algoOrder'])
        self.close_until_flat(sid)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/algoOrder']),before)

    def test_cancel_race_closes_late_fill_instead_of_releasing_inventory(self):
        sid=self.start();self.x.late_fill=self.order(0)
        self.runner.stop(sid,close_position=True,execute=True);self.close_until_flat(sid)
        self.assertEqual(self.x.legs['BTCUSDT','LONG'],0);self.assertEqual(self.runner.book.state(sid),'RELEASED')
        self.assertTrue(any(c[0]=='POST' and c[2].get('type')=='MARKET' and c[2].get('side')=='SELL' for c in self.x.calls))

    def test_net_zero_but_wrong_gross_legs_is_not_owned(self):
        sid=self.start();self.x.fill(self.order(0));self.x.fill(self.order(3))
        self.x.legs['BTCUSDT','LONG']=number('.0001');self.x.legs['BTCUSDT','SHORT']=number('-.0001')
        before=len(self.x.calls)
        with self.assertRaises(ValueError):self.runner.manage(sid,True)
        self.assertEqual(len(self.x.calls),before)

    def test_read_only_management_does_not_create_protection_or_close_orders(self):
        sid=self.start();self.x.fill(self.order(0));before=len(self.x.calls)
        self.assertEqual(self.runner.manage(sid,False)['state'],'NEUTRAL_PROTECTION_REQUIRED')
        self.assertEqual(len(self.x.calls),before)

    def test_last_moment_entry_revocation_prevents_initial_post(self):
        self.authorize();original=self.x.get
        def get(path,params=None):
            if path.endswith('/premiumIndex') and self.store.sessions():
                s=self.store.sessions()[0]
                if any(r['state']=='SUBMITTING' for r in self.store.intents()):
                    with self.store.db:self.store.db.execute('INSERT OR REPLACE INTO control VALUES (?,?)',('entry_revoked:'+s['entry_id'],'true'))
            return original(path,params)
        self.x.get=get
        self.assertEqual(self.runner.open(self.plan['plan_id'],1,True)['state'],'CLOSED')
        self.assertEqual(self.x.calls,[])

    def test_trade_leg_metadata_is_required_even_when_net_matches(self):
        sid=self.start();self.x.fill(self.order(0));self.x.trades[-1]['positionSide']='SHORT';before=len(self.x.calls)
        with self.assertRaises(ValueError):self.runner.manage(sid,True)
        self.assertEqual(len(self.x.calls),before)

    def test_margin_and_max_loss_budgets_include_both_leg_costs(self):
        for kind in ('MARGIN','MAX_LOSS'):
            p=copy.deepcopy(self.plan);p['sizing'].update(kind=kind,amount='20')
            compiled=compile_neutral(p,self.snapshot(),self.limits)
            key='risk_with_fee_reserve' if kind=='MAX_LOSS' else 'initial_margin'
            cost=number(compiled['risk'][key])
            if kind=='MARGIN':cost+=number(compiled['risk']['fee_reserve'])
            self.assertLessEqual(cost,20)

    def test_initial_send_consumes_only_initial_approval_ttl_not_cycle_authority(self):
        self.authorize();sid=self.runner.open(self.plan['plan_id'],1,True)['session_id']
        with self.store.db:self.store.db.execute('UPDATE plan_versions SET approval_until=?',(time.time()-1,))
        self.assertEqual(self.runner.manage(sid,True)['state'],'NEUTRAL_ORDER_SUBMITTED')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order']),2)

    def test_native_change_at_send_time_latches_stop_without_new_normal_post(self):
        sid=self.start();self.x.fill(self.order(0));self.runner.manage(sid,True)
        before=len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order']);original=self.x.get
        def get(path,params=None):
            if path.endswith('/algoOrder') and any(i['state']=='SUBMITTING' and i['path']=='/fapi/v1/order' for i in self.store.intents()):
                self.x.algos[params['clientAlgoId']]['algoStatus']='TRIGGERED'
            return original(path,params)
        self.x.get=get
        self.assertEqual(self.runner.manage(sid,True)['state'],'NEUTRAL_NATIVE_PENDING')
        self.assertEqual(self.store.sessions()[0]['phase'],'STOPPING')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order']),before)

    def test_malformed_normal_reply_stays_unknown_without_resending(self):
        self.authorize();original=self.x.request
        def request(method,path,params):
            reply=original(method,path,params)
            return [] if method=='POST' and path=='/fapi/v1/order' else reply
        self.x.request=request
        with self.assertRaises(ExchangeError):self.runner.open(self.plan['plan_id'],1,True)
        self.assertEqual(self.store.intents()[0]['state'],'UNKNOWN')
        self.x.request=original;sid=self.store.sessions()[0]['id'];self.close_until_flat(sid)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST']),1)

    def test_malformed_native_reply_does_not_repeat_native_post(self):
        sid=self.start();self.x.fill(self.order(0));original=self.x.request
        def request(method,path,params):
            reply=original(method,path,params)
            return [] if method=='POST' and path=='/fapi/v1/algoOrder' else reply
        self.x.request=request
        with self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        self.x.request=original;before=len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/algoOrder'])
        self.close_until_flat(sid)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/algoOrder']),before)

    def test_definitely_rejected_protection_cleans_up_actual_inventory(self):
        sid=self.start();self.x.fill(self.order(0));original=self.x.request
        def request(method,path,params):
            if method=='POST' and path=='/fapi/v1/algoOrder':raise ExchangeError('reject',-2019,400,delivery_status='REJECTED')
            return original(method,path,params)
        self.x.request=request
        self.runner.manage(sid,True);self.close_until_flat(sid)
        self.assertTrue(all(q==0 for q in self.x.legs.values()))

    def test_stop_service_preserves_both_native_protections_and_disables_openers(self):
        sid=self.start();self.x.fill(self.order(0));self.x.fill(self.order(3));self.runner.manage(sid,True)
        amounts=dict(self.x.legs);request_stop(self.store,sid,'local:test');reports=[]
        supervise_session(self.runner,sid,emit=reports.append,execute=True,iterations=0,drain_on_exit=True)
        self.assertTrue(reports[-1]['service_stopped']);self.assertEqual(self.x.legs,amounts)
        self.assertEqual(self.store.sessions()[0]['phase'],'DRAINING')
        self.assertEqual(len([a for a in self.x.algos.values() if a['algoStatus']=='NEW']),4)

    def test_own_normal_stop_and_read_only_account_scheduler_routing(self):
        sid=self.start();before=len(self.x.calls)
        reports=list(monitor_account(self.service,self.x,self.limits,iterations=1,execute=False))
        self.assertEqual(reports[0]['state'],'NEUTRAL_RUNNING')
        self.assertEqual(reports[0]['session_id'],sid);self.assertEqual(len(self.x.calls),before)

    def test_parent_plan_owns_one_symbol_and_cannot_split_into_second_same_symbol_plan(self):
        self.start();p=plan_v2();p['plan_id']='conflicting-plan';p['position_mode']='hedge'
        created=self.service.create(p,'local:test')
        with self.assertRaises(ValueError):self.service.authorize(p['plan_id'],1,created['authorization_token'],'approve','local:test')

    def test_common_bundle_preview_includes_two_neutral_exposures(self):
        self.authorize();result=prepare_many(self.service,self.x,self.limits,[(self.plan['plan_id'],1)])
        self.assertEqual(result['state'],'READY');self.assertEqual(len(result['portfolio_risk']['positions']),2)
        self.assertEqual(self.x.calls,[])

    def test_newly_filled_side_is_protected_before_flat_side_retirement(self):
        sid=self.start();self.x.fill(self.order(0));reduction=self.until_order(sid,0);self.x.fill(reduction)
        self.x.fill(self.order(3))
        self.assertEqual(self.runner.manage(sid,True)['state'],'NEUTRAL_PROTECTION_RETIRED')
        self.assertEqual(len([a for a in self.x.algos.values() if a['positionSide']=='SHORT' and a['algoStatus']=='NEW']),2)

    def test_lost_cancel_response_is_not_repeated_on_resume(self):
        sid=self.start();self.x.fill(self.order(0));conflict=self.order(1);self.x.cancel_lost=True
        with self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        self.close_until_flat(sid)
        calls=[c for c in self.x.calls if c[0]=='DELETE' and c[1]=='/fapi/v1/order' and c[2]['origClientOrderId']==conflict]
        self.assertEqual(len(calls),1)

    def test_stp_or_manual_expiry_does_not_silently_recreate_open_cell(self):
        sid=self.start();cid=self.order(0);self.x.orders[cid]['status']='EXPIRED_IN_MATCH'
        before=len([c for c in self.x.calls if c[0]=='POST'])
        self.close_until_flat(sid)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST']),before)

    def test_changed_record_side_or_quantity_cannot_submit_or_close_foreign_inventory(self):
        sid=self.start();original=self.store.sessions()[0];before=len(self.x.calls)
        for change in ({'position_side':'SHORT'},{'quantity':'1'}):
            s=copy.deepcopy(original)
            if 'position_side' in change:s['orders'][0]['position_side']=change['position_side']
            else:s['orders'][0]['proposal']['params']['quantity']=change['quantity']
            self.store.save_session(s)
            with self.assertRaises(ValueError):self.runner.manage(sid,True)
        self.assertEqual(len(self.x.calls),before);self.store.save_session(original)

    def test_same_account_peer_single_remains_untouched_on_neutral_close(self):
        from agentrader.v2_runner import V2Runner
        self.limits=replace(self.limits,max_positions=3,max_notional=Decimal('600'))
        self.runner=NeutralGridRunner(self.service,self.x,self.limits);sid=self.start()
        p=plan_v2();p.update(plan_id='eth-peer',symbol='ETHUSDT',position_mode='hedge')
        p['entry'].update(condition='IMMEDIATE',trigger_price=None)
        created=self.service.create(p,'local:test');self.service.authorize(p['plan_id'],1,created['authorization_token'],'approve','local:test')
        peer=V2Runner(self.service,self.x,self.limits);peer_id=peer.open(p['plan_id'],1,True)['session_id']
        protected={cid:copy.deepcopy(a) for cid,a in self.x.algos.items() if a['symbol']=='ETHUSDT'}
        self.x.fill(self.order(0));self.runner.manage(sid,True)
        self.runner.stop(sid,close_position=True,execute=True);self.close_until_flat(sid)
        self.assertEqual(peer.manage(peer_id,True)['state'],'MANAGING')
        self.assertEqual({cid:a for cid,a in self.x.algos.items() if a['symbol']=='ETHUSDT'},protected)
        self.assertEqual(peer.book.state(peer_id),'COMMITTED')

    def test_two_sides_still_share_one_trade_loss_limit_after_restart(self):
        sid=self.start();self.x.fill(self.order(0));reduction=self.until_order(sid,0);self.x.fill(reduction)
        before=len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order'])
        self.runner=NeutralGridRunner(self.service,self.x,replace(self.limits,max_trade_loss=Decimal('10')))
        self.close_until_flat(sid)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order']),before)

    def test_neutral_example_prints_requested_budget_without_account_or_authorization(self):
        from agentrader.plan_cli import main
        stream=io.StringIO()
        with patch('agentrader.plan_cli.Config.load') as load,redirect_stdout(stream):
            self.assertEqual(main(['neutral-example','--amount','200']),0)
        data=json.loads(stream.getvalue())
        self.assertEqual(data['sizing']['amount'],'200');self.assertEqual(data['execution']['strategy'],'NEUTRAL_GRID')
        load.assert_not_called();self.assertEqual(self.x.calls,[])

    def test_actual_one_way_account_is_not_automatically_switched_to_hedge(self):
        self.authorize();original=self.x.get
        self.x.get=lambda path,params=None: {'dualSidePosition':False} if path.endswith('/dual') else original(path,params)
        with self.assertRaises(ValueError):self.runner.open(self.plan['plan_id'],1,True)
        self.assertEqual(self.x.calls,[]);self.assertEqual(self.store.sessions(),[])

    def test_stopping_flat_neutral_releases_one_reservation_without_creating_market_orders(self):
        sid=self.start();result=self.runner.stop(sid,close_position=False,execute=True)
        self.assertEqual(result['state'],'CLOSED');self.assertEqual(self.runner.book.state(sid),'RELEASED')
        self.assertFalse(any(c[0]=='POST' and c[2].get('type')=='MARKET' for c in self.x.calls))
