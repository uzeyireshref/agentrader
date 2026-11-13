import copy
import tempfile
import time
import unittest
from decimal import ROUND_FLOOR
from pathlib import Path
from unittest.mock import patch

from agentrader.config import Config
from agentrader.exchange import ExchangeError
from agentrader.plans import PlanService
from agentrader.risk import RiskLimits, number
from agentrader.state import StateStore
from agentrader.v2_runner import V2Runner
from test_plan_v2 import plan_v2
from test_v2_preflight import snapshot


class ExecutionExchange:
    config = Config('demo-key', 'secret-never-output')
    offset_ms = 0

    def __init__(self, short=False, hedge=False):
        self.short, self.hedge = short, hedge
        self.orders, self.algos, self.trades, self.calls = {}, {}, [], []
        self.amount, self.price = number(0), '80000'
        self.timeout = False
        self.partial = False
        self.algo_timeout = False
        self.cancel_timeout = False
        self.limit_pending = False

    def sync_time(self): pass

    def get(self, path, params=None):
        if path == '/fapi/v1/order':
            if params['origClientOrderId'] not in self.orders:
                raise ExchangeError('missing', -2013)
            return copy.deepcopy(self.orders[params['origClientOrderId']])
        if path == '/fapi/v1/algoOrder':
            return copy.deepcopy(self.algos[params['clientAlgoId']])
        if path == '/fapi/v1/positionSide/dual':
            return {'dualSidePosition':self.hedge}
        if path == '/fapi/v1/symbolConfig':
            return [snapshot()['settings']]
        if path == '/fapi/v1/userTrades':
            return [dict(row, symbol=params['symbol'], id=i+1, time=params['endTime']) for i,row in enumerate(self.trades) if float(row['qty']) > 0]
        if path == '/fapi/v3/positionRisk':
            return [{'symbol':'BTCUSDT','positionSide':('SHORT' if self.short else 'LONG') if self.hedge else 'BOTH',
                     'positionAmt':str(self.amount)}]
        if path == '/fapi/v1/openOrders':
            return [copy.deepcopy(o) for o in self.orders.values() if o['status'] not in ('FILLED','CANCELED')]
        if path == '/fapi/v1/openAlgoOrders':
            return [copy.deepcopy(o) for o in self.algos.values() if o['algoStatus']=='NEW']
        if path == '/fapi/v1/premiumIndex':
            return {'symbol':'BTCUSDT','markPrice':self.price,'time':int(time.time()*1000)}
        if path == '/fapi/v1/exchangeInfo':
            return {'symbols':[snapshot()['symbol_info']]}
        raise AssertionError(path)

    def request(self, method, path, params):
        self.calls.append((method,path,copy.deepcopy(params)))
        if method == 'DELETE':
            if path.endswith('algoOrder'):
                self.algos[params['clientAlgoId']]['algoStatus']='CANCELED'
            else:
                self.orders[params['origClientOrderId']]['status']='CANCELED'
            if self.cancel_timeout:
                self.cancel_timeout=False
                raise ExchangeError('cancel timeout', delivery_status='UNKNOWN')
            return {}
        if path.endswith('algoOrder'):
            self.algos[params['clientAlgoId']] = params | {'algoStatus':'NEW','orderType':params['type']}
            if self.algo_timeout:
                self.algo_timeout=False
                raise ExchangeError('algo timeout', delivery_status='UNKNOWN')
            return copy.deepcopy(self.algos[params['clientAlgoId']])
        cid=params['newClientOrderId']
        q=number(params['quantity'])
        fill=(q/2/number('.0001')).to_integral_value(rounding=ROUND_FLOOR)*number('.0001') if self.partial else q
        pending = params['type'] == 'LIMIT' and self.limit_pending
        if pending: fill=number(0)
        order=params | {'clientOrderId':cid,'orderId':len(self.orders)+1,'origQty':str(q),
                        'avgPrice':'80000',
                        'executedQty':str(fill),'status':'NEW' if pending else ('PARTIALLY_FILLED' if self.partial else 'FILLED'),
                        'updateTime':int(time.time()*1000)}
        self.orders[cid]=order
        self.amount += fill*(1 if params['side']=='BUY' else -1)
        self.trades.append({'orderId':order['orderId'],'qty':str(fill),'side':params['side']})
        if self.timeout:
            self.timeout=False
            raise ExchangeError('timeout', delivery_status='UNKNOWN')
        return copy.deepcopy(order)


class V2RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'state.db'
        self.store=StateStore(self.path)
        self.service=PlanService(self.store,'local:test')
        self.plan=plan_v2()
        self.plan['entry'].update(condition='IMMEDIATE',trigger_price=None)
        self.x=ExecutionExchange()
        self.runner=V2Runner(self.service,self.x,RiskLimits())
        self.snap=snapshot()
        self.snap.update(observed_at=time.time(),finished_at=time.time(),now_ms=int(time.time()*1000))
        self.mock=patch('agentrader.v2_runner.collect_flat_snapshot',side_effect=lambda *a:copy.deepcopy(self.snap))
        self.mock.start()

    def tearDown(self):
        self.mock.stop()
        self.store.close()
        self.temp.cleanup()

    def authorize(self):
        created=self.service.create(self.plan,'local:test')
        self.service.authorize(self.plan['plan_id'],1,created['authorization_token'],'approve','local:test')

    def open(self, execute=True):
        return self.runner.open(self.plan['plan_id'],1,execute)

    def test_preview_does_not_claim_or_send(self):
        self.authorize()
        self.assertEqual(self.open(False)['state'],'READY')
        self.assertEqual(self.x.calls,[])
        self.assertEqual(self.service.show(self.plan['plan_id'],1)['state'],'AUTHORIZED')

    def test_dense_trade_history_reconciles_and_foreign_fill_on_later_page_halts(self):
        from test_history import TradeExchange, trade
        self.authorize()
        opened = self.open()
        order = next(iter(self.x.orders.values()))
        timestamp = int(time.time()*1000)
        quantity = str(number(order['executedQty'])/2000)
        rows = [dict(trade(i, timestamp), orderId=order['orderId'], qty=quantity)
                for i in range(2000)]
        history = TradeExchange(rows)
        original_get = self.x.get
        def get(path, params=None):
            return history.get(path, params) if path.endswith('/userTrades') else original_get(path, params)
        self.x.get = get
        self.assertEqual(self.runner.manage(opened['session_id'], True)['state'], 'MANAGING')
        self.assertEqual(len(history.calls), 3)
        count = len(self.x.calls)
        rows.append(dict(trade(2000, timestamp), orderId=99999))
        with self.assertRaises(ValueError):
            self.runner.manage(opened['session_id'], True)
        self.assertEqual(len(self.x.calls), count)
        self.assertIsNotNone(self.store.halt_reason())

    def test_authorized_long_protects_and_restart_never_reenters(self):
        self.authorize()
        result=self.open()
        self.assertEqual(result['state'],'MANAGING')
        self.assertEqual(result['protections_verified'],2)
        self.assertEqual(len(self.x.calls),3)
        sid=result['session_id']
        self.store.close();self.store=StateStore(self.path)
        self.service=PlanService(self.store,'local:test')
        self.runner=V2Runner(self.service,self.x,RiskLimits())
        self.assertEqual(self.runner.manage(sid,True)['state'],'MANAGING')
        self.assertEqual(len(self.x.calls),3)
        with self.assertRaises(ValueError):self.open()

    def test_short_hedge_uses_correct_entry_and_protection_sides(self):
        self.plan.update(direction='SHORT',position_mode='hedge',stop='81600',targets=[{'price':'78400','fraction':'1'}])
        self.snap['position_mode']='hedge'
        self.x.short=True;self.x.hedge=True
        self.authorize();self.open()
        self.assertEqual(self.x.calls[0][2]['side'],'SELL')
        self.assertEqual(self.x.calls[1][2]['side'],'BUY')
        self.assertEqual(self.x.calls[1][2]['positionSide'],'SHORT')

    def test_lost_entry_response_is_recovered_without_second_entry(self):
        self.authorize();self.x.timeout=True
        with self.assertRaises(ExchangeError):self.open()
        sid=self.store.sessions()[0]['id']
        self.assertEqual(self.runner.manage(sid,True)['state'],'MANAGING')
        entries=[c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order']
        self.assertEqual(len(entries),1)

    def test_partial_entry_is_canceled_before_protection(self):
        self.authorize();self.x.partial=True
        result=self.open()
        self.assertEqual(result['state'],'MANAGING')
        self.assertEqual(self.x.calls[1][0],'DELETE')
        self.assertEqual(self.x.calls[2][1],'/fapi/v1/algoOrder')

    def test_foreign_trade_prevents_automatic_management(self):
        self.authorize();result=self.open()
        self.x.trades.append({'orderId':999,'qty':'.001','side':'BUY'})
        before=len(self.x.calls)
        with self.assertRaises(ValueError):self.runner.manage(result['session_id'],True)
        self.assertEqual(len(self.x.calls),before)

    def test_crossed_stop_closes_reduce_only_then_cleans_protections(self):
        self.authorize();result=self.open();sid=result['session_id']
        self.x.price='78000'
        self.assertEqual(self.runner.manage(sid,True)['state'],'EXIT_SUBMITTED')
        self.assertEqual(self.x.calls[-1][2]['reduceOnly'],'true')
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(self.store.sessions(),[])
        self.assertEqual(self.x.amount,0)
        self.assertTrue(all(a['algoStatus']=='CANCELED' for a in self.x.algos.values()))

    def test_read_only_manage_never_submits_missing_protection(self):
        self.authorize();self.x.timeout=True
        with self.assertRaises(ExchangeError):self.open()
        sid=self.store.sessions()[0]['id'];before=len(self.x.calls)
        self.assertEqual(self.runner.manage(sid,False)['state'],'PROTECTION_REQUIRED')
        self.assertEqual(len(self.x.calls),before)

    def test_wrong_key_cannot_resume_session(self):
        self.authorize();result=self.open()
        self.x.config=Config('another-key','secret')
        runner=V2Runner(self.service,self.x,RiskLimits())
        with self.assertRaises(ValueError):runner.manage(result['session_id'],True)

    def test_unapproved_and_unsupported_scope_never_submit(self):
        self.service.create(self.plan,'local:test')
        with self.assertRaises(ValueError):self.open()
        self.assertEqual(self.x.calls,[])

    def test_price_or_budget_change_after_claim_blocks_entry(self):
        self.authorize()
        changed=copy.deepcopy(self.snap);changed['mark']['markPrice']='81000'
        with patch('agentrader.v2_runner.collect_flat_snapshot',side_effect=[self.snap,changed]):
            with self.assertRaises(ValueError):self.open()
        self.assertEqual(self.x.calls,[])

    def test_partial_close_is_canceled_before_residual_close(self):
        self.authorize();sid=self.open()['session_id']
        self.x.price='78000';self.x.partial=True
        self.runner.manage(sid,True)
        self.x.partial=False
        self.runner.manage(sid,True)
        self.assertEqual(self.x.calls[-2][0],'DELETE')
        self.assertEqual(self.x.calls[-1][2]['reduceOnly'],'true')
        self.assertEqual(self.x.amount,0)
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')

    def test_revocation_after_claim_blocks_post(self):
        self.authorize()
        def revoke(*args):
            if self.store.sessions():
                self.service.cancel(self.plan['plan_id'],1,'local:test')
            return copy.deepcopy(self.snap)
        with patch('agentrader.v2_runner.collect_flat_snapshot',side_effect=revoke):
            # The second scope check immediately before sending must see revocation.
            with self.assertRaises(ValueError):self.open()
        self.assertEqual(self.x.calls,[])

    def test_lost_stop_response_is_queried_and_not_resubmitted(self):
        self.authorize();self.x.algo_timeout=True
        with self.assertRaises(ExchangeError):self.open()
        sid=self.store.sessions()[0]['id']
        self.assertEqual(self.runner.manage(sid,True)['state'],'MANAGING')
        stop_posts=[c for c in self.x.calls if c[0]=='POST' and c[2].get('type')=='STOP_MARKET']
        self.assertEqual(len(stop_posts),1)

    def test_modified_saved_protection_is_rejected_before_mutation(self):
        self.authorize();sid=self.open()['session_id']
        s=self.store.sessions()[0]
        s['protections'][0]['params']['triggerPrice']='70000'
        self.store.save_session(s)
        before=len(self.x.calls)
        with self.assertRaises(ValueError):self.runner.manage(sid,True)
        self.assertEqual(len(self.x.calls),before)

    def test_definite_unsent_entry_can_retire_after_flat_read(self):
        self.authorize()
        changed=copy.deepcopy(self.snap);changed['mark']['markPrice']='81000'
        with patch('agentrader.v2_runner.collect_flat_snapshot',side_effect=[self.snap,changed]):
            with self.assertRaises(ValueError):self.open()
        sid=self.store.sessions()[0]['id']
        self.assertEqual(self.runner.manage(sid,False)['state'],'CLOSED')
        self.assertEqual(self.x.calls,[])

    def test_lost_cancel_response_is_reconciled_without_second_delete(self):
        self.authorize();self.x.partial=True;self.x.cancel_timeout=True
        with self.assertRaises(ExchangeError):self.open()
        sid=self.store.sessions()[0]['id']
        self.assertEqual(self.runner.manage(sid,True)['state'],'MANAGING')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='DELETE']),1)

    def test_unknown_missing_entry_is_not_retired_as_unsent(self):
        self.authorize();self.x.timeout=True
        with self.assertRaises(ExchangeError):self.open()
        sid=self.store.sessions()[0]['id']
        self.x.orders.clear()
        with self.assertRaises(ExchangeError):self.runner.manage(sid,False)
        self.assertEqual(len(self.store.sessions()),1)

    def limit_plan(self):
        self.plan['entry'].update(condition='LIMIT',trigger_price='79900')
        self.x.limit_pending=True
        self.authorize()

    def test_limit_pending_restart_does_not_cancel_or_reenter(self):
        self.limit_plan();sid=self.open()['session_id']
        self.assertEqual(len(self.x.calls),1)
        self.assertEqual(self.runner.manage(sid,True)['state'],'ENTRY_PENDING')
        self.assertEqual(len(self.x.calls),1)

    def test_limit_expiry_cancels_without_opening_position(self):
        self.limit_plan();sid=self.open()['session_id']
        with self.store.db:
            self.store.db.execute('UPDATE plan_versions SET approval_until=?',(time.time()-1,))
        self.assertEqual(self.runner.manage(sid,False)['state'],'ENTRY_CANCEL_REQUIRED')
        self.assertEqual(len(self.x.calls),1)
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(self.x.amount,0)
        self.assertEqual(self.x.calls[-1][0],'DELETE')

    def test_limit_partial_fill_cancels_remainder_and_protects(self):
        self.plan['entry'].update(condition='LIMIT',trigger_price='79900')
        self.x.partial=True
        self.authorize();r=self.open()
        self.assertEqual(r['state'],'MANAGING')
        self.assertEqual(self.x.calls[1][0],'DELETE')
        self.assertEqual(len(self.x.algos),2)

    def test_limit_stop_crossing_cancels_pending_buy(self):
        self.limit_plan();sid=self.open()['session_id']
        self.x.price='78000'
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST']),1)

    def staged_plan(self, short=False):
        self.plan['targets']=[{'price':'81000','fraction':'.5'}, {'price':'82000','fraction':'.5'}]
        if short:
            self.plan.update(direction='SHORT',stop='81600',targets=[{'price':'79000','fraction':'.5'}, {'price':'78000','fraction':'.5'}])
            self.x.short=True
        self.authorize()

    def test_staged_long_exit_leaves_residual_and_keeps_final_target(self):
        self.staged_plan();sid=self.open()['session_id']
        self.x.price='81000'
        self.assertEqual(self.runner.manage(sid,True)['state'],'TARGET_EXIT_SUBMITTED')
        self.assertGreater(self.x.amount,0)
        self.assertEqual(self.x.calls[-1][2]['quantity'],'0.0003')
        self.assertEqual(self.runner.manage(sid,True)['state'],'MANAGING')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order']),2)
        targets=[a for a in self.x.algos.values() if a['type']=='TAKE_PROFIT_MARKET']
        self.assertEqual(targets[0]['triggerPrice'],'82000')

    def test_staged_short_exit_buys_only_the_target_share(self):
        self.staged_plan(short=True);sid=self.open()['session_id']
        self.x.price='79000'
        self.assertEqual(self.runner.manage(sid,True)['stage'],1)
        self.assertEqual(self.x.calls[-1][2]['side'],'BUY')
        self.assertLess(self.x.amount,0)

    def test_staged_partial_exit_cancels_before_residual_retry(self):
        self.staged_plan();sid=self.open()['session_id']
        self.x.price='81000';self.x.partial=True
        self.runner.manage(sid,True)
        self.x.partial=False
        self.runner.manage(sid,True)
        self.assertEqual(self.x.calls[-2][0],'DELETE')
        self.assertEqual(self.x.calls[-1][2]['quantity'],'0.0002')

    def test_lost_stage_response_is_counted_without_duplicate_exit(self):
        self.staged_plan();sid=self.open()['session_id']
        self.x.price='81000';self.x.timeout=True
        with self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        count=len(self.x.calls)
        self.assertEqual(self.runner.manage(sid,True)['state'],'MANAGING')
        self.assertEqual(len(self.x.calls),count)

    def break_even_plan(self, short=False):
        self.plan['management']['break_even_after_target']=1
        self.staged_plan(short=short)
        sid=self.open()['session_id']
        self.x.price='79000' if short else '81000'
        self.runner.manage(sid,True)
        return sid

    def test_break_even_verifies_new_quantity_stop_before_canceling_old(self):
        sid=self.break_even_plan()
        self.assertEqual(self.runner.manage(sid,True)['state'],'STOP_MOVED')
        old=self.store.sessions()[0]['protections'][0]['params']['clientAlgoId']
        self.assertEqual(self.x.algos[old]['algoStatus'],'CANCELED')
        new=self.x.calls[-2]
        self.assertEqual(new[0],'POST')
        self.assertEqual(new[2]['triggerPrice'],'80000')
        self.assertEqual(new[2]['quantity'],'0.0004')
        self.assertEqual(new[2]['reduceOnly'],'true')
        before=len(self.x.calls)
        self.assertEqual(self.runner.manage(sid,True)['state'],'MANAGING')
        self.assertEqual(len(self.x.calls),before)

    def test_lost_break_even_response_keeps_old_stop_until_read_verified(self):
        sid=self.break_even_plan();self.x.algo_timeout=True
        old=self.store.sessions()[0]['protections'][0]['params']['clientAlgoId']
        with self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        self.assertEqual(self.x.algos[old]['algoStatus'],'NEW')
        posts=len([c for c in self.x.calls if c[0]=='POST' and c[2].get('quantity')=='0.0004'])
        self.assertEqual(self.runner.manage(sid,True)['state'],'STOP_MOVED')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST' and c[2].get('quantity')=='0.0004']),posts)

    def test_short_break_even_stop_has_buy_direction(self):
        sid=self.break_even_plan(short=True)
        self.runner.manage(sid,True)
        new=self.x.calls[-2][2]
        self.assertEqual(new['side'],'BUY')
        self.assertEqual(new['triggerPrice'],'80000')

    def test_break_even_crossing_closes_using_effective_stop(self):
        sid=self.break_even_plan();self.runner.manage(sid,True)
        self.x.price='79900'
        self.assertEqual(self.runner.manage(sid,True)['state'],'EXIT_SUBMITTED')
        self.assertEqual(self.x.amount,0)
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')

    def test_break_even_old_stop_cancel_timeout_does_not_repeat_delete(self):
        sid=self.break_even_plan();self.x.cancel_timeout=True
        with self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        deletes=len([c for c in self.x.calls if c[0]=='DELETE'])
        self.assertEqual(self.runner.manage(sid,True)['state'],'STOP_MOVED')
        self.assertEqual(len([c for c in self.x.calls if c[0]=='DELETE']),deletes)

    def test_unverified_replacement_stop_does_not_retire_existing_stop(self):
        sid=self.break_even_plan()
        original_get=self.x.get
        old=self.store.sessions()[0]['protections'][0]['params']['clientAlgoId']
        def get(path, params=None):
            result=original_get(path,params)
            if path.endswith('algoOrder') and result.get('reduceOnly')=='true':
                result['quantity']='0'
            return result
        with patch.object(self.x,'get',side_effect=get):
            with self.assertRaises(ValueError):self.runner.manage(sid,True)
        self.assertEqual(self.x.algos[old]['algoStatus'],'NEW')
        self.assertFalse(any(c[0]=='DELETE' for c in self.x.calls))

    def test_unknown_conditional_cleanup_status_is_not_closed_proof(self):
        self.authorize();sid=self.open()['session_id']
        self.x.price='78000';self.runner.manage(sid,True)
        original_get=self.x.get
        def get(path,params=None):
            result=original_get(path,params)
            if path.endswith('algoOrder'):result['algoStatus']='TRIGGERING'
            return result
        with patch.object(self.x,'get',side_effect=get):
            with self.assertRaises(ValueError):self.runner.manage(sid,True)
        self.assertEqual(len(self.store.sessions()),1)

    def test_hedge_break_even_has_position_side_without_reduce_only(self):
        self.plan['position_mode']='hedge';self.snap['position_mode']='hedge';self.x.hedge=True
        sid=self.break_even_plan(short=True)
        self.runner.manage(sid,True)
        new=self.x.calls[-2][2]
        self.assertEqual(new['positionSide'],'SHORT')
        self.assertNotIn('reduceOnly',new)

    def test_later_target_resizes_break_even_stop_before_retiring_previous(self):
        self.plan['targets']=[{'price':'81000','fraction':'.3'}, {'price':'82000','fraction':'.3'}, {'price':'83000','fraction':'.4'}]
        self.plan['management']['break_even_after_target']=1
        self.authorize();sid=self.open()['session_id']
        self.x.price='81000';self.runner.manage(sid,True);self.runner.manage(sid,True)
        self.x.price='82000'
        self.assertEqual(self.runner.manage(sid,True)['state'],'TARGET_EXIT_SUBMITTED')
        self.assertEqual(self.runner.manage(sid,True)['state'],'STOP_MOVED')
        transitions=self.store.sessions()[0]['stop_transitions']
        self.assertEqual(len(transitions),2)
        self.assertEqual(transitions[-1]['proposal']['params']['quantity'],'0.0003')
        old=transitions[0]['proposal']['params']['clientAlgoId']
        self.assertEqual(self.x.algos[old]['algoStatus'],'CANCELED')
