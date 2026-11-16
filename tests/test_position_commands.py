import copy
import tempfile
import time
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from agentrader.bot.exchange_commands import ExchangeCommands,validate_command
from agentrader.bot.position_commands import INCREASE,REDUCE,CLOSE,REVERSE
from agentrader.bot.plans import PlanService
from agentrader.bot.risk import RiskLimits,number
from agentrader.bot.v2_runner import V2Runner
from agentrader.shared.exchange import ExchangeError
from agentrader.shared.state import StateStore
from test_plan_v2 import plan_v2
from test_multi_session import MultiExchange


def limits_json(cap='200'):
    return dict(max_trade_loss='5',max_total_loss='10',max_daily_loss='25',max_notional=cap,max_positions=1,max_age_seconds=15)


class PositionExchange(MultiExchange):
    def __init__(self):
        super().__init__();self.partial_change=False;self.partial_next=False;self.reject_change=False;self.reject_next=False
    def request(self,method,path,params):
        cid=params.get('newClientOrderId','');change=method=='POST' and path.endswith('/order') and cid.startswith('agt-pos-')
        if change and self.reject_change or method=='POST' and self.reject_next and cid.startswith('agt-') and not change and params.get('reduceOnly')!='true':
            self.calls.append((method,path,copy.deepcopy(params)));raise ExchangeError('rejected',-2019,400,delivery_status='REJECTED')
        if change and self.partial_change or method=='POST' and self.partial_next and cid.startswith('agt-') and not change and params.get('reduceOnly')!='true':
            q=number(params['quantity']);filled=(q/2/number('.0001')).to_integral_value(rounding='ROUND_FLOOR')*number('.0001')
            self.calls.append((method,path,copy.deepcopy(params)));symbol=params['symbol'];ident=1+sum(o['symbol']==symbol for o in self.orders.values())
            self.orders[cid]=params|dict(clientOrderId=cid,orderId=ident,origQty=str(filled),executedQty='0',status='NEW',avgPrice='0',updateTime=int(time.time()*1000))
            self.fill(cid);self.orders[cid].update(origQty=str(q),status='EXPIRED');return copy.deepcopy(self.orders[cid])
        return super().request(method,path,params)


class HedgePositionExchange(PositionExchange):
    def __init__(self):super().__init__();self.leg='SHORT'
    def get(self,path,params=None):
        if path.endswith('/dual'):return {'dualSidePosition':True}
        result=super().get(path,params)
        if path.endswith('/account'):
            for p in result['positions']:p['positionSide']=self.leg
        if path.endswith('/positionRisk'):
            for p in result:p['positionSide']=self.leg
        return result
    def request(self,method,path,params):
        if method=='POST' and path.endswith('/order') and params['side']==('BUY' if params['positionSide']=='LONG' else 'SELL'):
            self.leg=params['positionSide']
        return super().request(method,path,params)


class PositionCommandTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.path=Path(self.folder.name)/'state.db';self.store=StateStore(self.path)
        self.owner='local:position';self.service=PlanService(self.store,self.owner);self.x=PositionExchange()
        self.plan=plan_v2();self.plan['entry'].update(condition='IMMEDIATE',trigger_price=None)
        created=self.service.create(self.plan,self.owner);self.service.authorize(self.plan['plan_id'],1,created['authorization_token'],'approve',self.owner)
        self.limits=replace(RiskLimits(),max_notional=Decimal('200'));self.runner=V2Runner(self.service,self.x,self.limits)
        self.sid=self.runner.open(self.plan['plan_id'],1,True)['session_id'];self.commands=ExchangeCommands(self.x,self.store,self.owner)
    def tearDown(self):self.store.close();self.folder.cleanup()
    def request(self,op=REDUCE,key='change'):
        p={'session_id':self.sid}
        if op==REDUCE:p['reduction']={'kind':'PERCENT','value':'25'}
        if op==INCREASE:p.update(quantity='0.0007',price_floor='79900',price_ceiling='80100',risk_limits=limits_json())
        if op==REVERSE:
            row=self.service.show('reverse-plan',1);p.update(next_plan_id='reverse-plan',next_version=1,next_digest=row['digest'],risk_limits=limits_json())
        return dict(schema_version=1,client_command_id=key,environment='demo',exchange='binance',product='USD-M',account_ref=self.commands.account_ref,
                    operation=op,scope={'symbol':'BTCUSDT'},parameters=p)
    def execute(self,op=REDUCE,key='change',request=None):
        p=self.commands.prepare(request or self.request(op,key));return p,self.commands.apply(p['command_id'],p['digest'],execute=True)
    def changes(self):return [p for m,path,p in self.x.calls if m=='POST' and path.endswith('/order') and p['newClientOrderId'].startswith('agt-pos-')]
    def next_plan(self):
        plan=copy.deepcopy(self.plan);plan.update(plan_id='reverse-plan',direction='SHORT',stop='81600',targets=[{'price':'78400','fraction':'1'}])
        return self.service.create(plan,self.owner)
    def test_percentage_reduction_is_quantized_and_preserves_protection(self):
        p,r=self.execute();self.assertEqual(r['state'],'APPLIED');self.assertEqual(number(r['result']['filled_quantity']),number('.0001'))
        self.assertEqual(number(r['result']['remaining_quantity']),number('.0006'));self.assertEqual(self.runner.book.state(self.sid),'COMMITTED')
        self.assertEqual(self.runner.manage(self.sid,True)['state'],'MANAGING')
        self.assertEqual(sum(a['algoStatus']=='NEW' for a in self.x.algos.values()),2)
    def test_exact_reduce_and_duplicate_never_repeat(self):
        req=self.request();req['parameters']['reduction']={'kind':'QUANTITY','value':'.0002'};p,r=self.execute(request=req)
        self.assertEqual(r['state'],'APPLIED');self.assertEqual(self.x.amounts['BTCUSDT'],number('.0005'))
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.commands.reconcile(p['command_id']);self.assertEqual(len(self.changes()),1)
    def test_close_releases_only_after_flat_and_terminal_protection(self):
        _,r=self.execute(CLOSE);self.assertEqual(r['state'],'APPLIED');self.assertEqual(r['result']['source_plan_state'],'CLOSED')
        self.assertEqual(self.x.amounts['BTCUSDT'],0);self.assertEqual(self.runner.book.state(self.sid),'RELEASED')
        self.assertTrue(all(a['algoStatus']=='CANCELED' for a in self.x.algos.values()))
    def test_increase_uses_separate_authority_and_risk_envelope(self):
        before=self.service.show(self.plan['plan_id'],1)['digest'];_,r=self.execute(INCREASE)
        self.assertEqual(r['state'],'APPLIED');self.assertEqual(self.x.amounts['BTCUSDT'],number('.0014'))
        self.assertEqual(self.service.show(self.plan['plan_id'],1)['digest'],before)
        self.assertFalse(self.service.show(self.plan['plan_id'],1)['plan']['management']['allow_scale_in'])
        self.assertEqual(self.runner.manage(self.sid,True)['state'],'MANAGING')
        import json
        row=self.store.db.execute('SELECT * FROM risk_reservations WHERE reservation_id=?',(self.sid,)).fetchone()
        self.assertEqual(len(self.runner.book._effective_exposures(self.store.db,row,json.loads(row['body']))),2)
    def test_insufficient_added_risk_budget_sends_nothing(self):
        req=self.request(INCREASE);req['parameters']['risk_limits']=limits_json('100');_,r=self.execute(request=req)
        self.assertEqual(r['state'],'NOT_SENT');self.assertEqual(self.changes(),[])
    def test_increase_reject_keeps_original_risk_and_does_not_retry(self):
        self.x.reject_change=True;p,r=self.execute(INCREASE);self.assertEqual(r['state'],'REJECTED')
        self.assertEqual(self.x.amounts['BTCUSDT'],number('.0007'));self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(len(self.changes()),1);self.assertEqual(self.runner.manage(self.sid,True)['state'],'MANAGING')
    def test_lost_increase_response_queries_without_new_post(self):
        self.x.lost=True;p,r=self.execute(INCREASE);self.assertEqual(r['state'],'APPLIED')
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(len(self.changes()),1)
        self.assertEqual(self.runner.manage(self.sid,True)['state'],'MANAGING')
    def test_partial_increase_is_explicit_and_reservation_is_retained(self):
        self.x.partial_change=True;_,r=self.execute(INCREASE);self.assertEqual(r['state'],'APPLIED');self.assertEqual(r['result']['phase'],'PARTIAL_FILL')
        self.assertEqual(self.x.amounts['BTCUSDT'],number('.0010'));self.assertEqual(self.runner.book.state(self.sid),'COMMITTED')
    def test_partial_close_is_not_reported_as_closed(self):
        self.x.partial_change=True;_,r=self.execute(CLOSE);self.assertEqual(r['result']['source_plan_state'],'MANAGING')
        self.assertGreater(number(r['result']['remaining_quantity']),0);self.assertEqual(self.runner.book.state(self.sid),'COMMITTED')
    def test_reverse_closes_before_authorizing_new_direction(self):
        self.next_plan();_,r=self.execute(REVERSE);self.assertEqual(r['state'],'APPLIED',r)
        self.assertEqual(r['result']['source_plan_state'],'CLOSED');self.assertEqual(r['result']['next_plan_state'],'MANAGING')
        self.assertEqual(number(r['result']['remaining_quantity']),0)
        self.assertLess(self.x.amounts['BTCUSDT'],0);self.assertEqual(self.runner.book.state(self.sid),'RELEASED')
    def test_reverse_partial_close_does_not_open_second_leg(self):
        self.next_plan();self.x.partial_change=True;_,r=self.execute(REVERSE)
        self.assertEqual(r['state'],'UNKNOWN');self.assertEqual(r['result']['next_plan_state'],'PENDING_APPROVAL')
        self.assertGreater(self.x.amounts['BTCUSDT'],0);self.assertEqual(len(self.changes()),1)
    def test_reverse_second_leg_rejection_is_visible_and_old_position_stays_closed(self):
        self.next_plan();self.x.reject_next=True;p,r=self.execute(REVERSE)
        self.assertEqual(r['state'],'UNKNOWN');self.assertEqual(r['result']['phase'],'OPEN_REJECTED')
        self.assertEqual(self.x.amounts['BTCUSDT'],0)
        n=len(self.x.calls);self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(len(self.x.calls),n)
    def test_lost_close_response_does_not_implicitly_open_reverse(self):
        self.next_plan();self.x.lost=True;p,r=self.execute(REVERSE)
        self.assertEqual(r['state'],'UNKNOWN');self.assertEqual(self.service.show('reverse-plan',1)['state'],'PENDING_APPROVAL')
        self.runner.manage(self.sid,True);self.commands.reconcile(p['command_id'])
        self.assertEqual(self.service.show('reverse-plan',1)['state'],'PENDING_APPROVAL');self.assertEqual(self.x.amounts['BTCUSDT'],0)
    def test_manual_position_mix_blocks_without_reducing_it(self):
        self.x.amounts['BTCUSDT']+=number('.0001');_,r=self.execute(CLOSE)
        self.assertEqual(r['state'],'NOT_SENT');self.assertEqual(self.changes(),[])
    def test_excess_reduction_and_too_small_percentage_send_nothing(self):
        for value,kind,key in (('1','QUANTITY','large'),('0.01','PERCENT','tiny')):
            req=self.request(key=key);req['parameters']['reduction']={'kind':kind,'value':value};_,r=self.execute(request=req)
            self.assertEqual(r['state'],'NOT_SENT')
        self.assertEqual(self.changes(),[])
    def test_unsupported_schema_and_execute_gate(self):
        req=self.request();req['parameters']['reduction']['value']='101'
        with self.assertRaises(ValueError):validate_command(req)
        p=self.commands.prepare(self.request())
        with self.assertRaises(ValueError):self.commands.apply(p['command_id'],p['digest'])
        self.assertEqual(self.changes(),[])
    def test_crash_after_child_intent_never_reposts(self):
        p=self.commands.prepare(self.request(CLOSE));original=self.x.request
        def crash(method,path,params):
            if params.get('newClientOrderId','').startswith('agt-pos-'):raise KeyboardInterrupt
            return original(method,path,params)
        with patch.object(self.x,'request',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'UNKNOWN')
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(self.changes(),[])
    def test_action_and_intent_are_atomic_on_storage_failure(self):
        import sqlite3
        p=self.commands.prepare(self.request(CLOSE))
        self.store.db.execute("CREATE TRIGGER fail_position_intent BEFORE INSERT ON intents WHEN NEW.client_id LIKE 'agt-pos-%' BEGIN SELECT RAISE(ABORT,'disk failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM position_actions').fetchone()[0],0)
        self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'NOT_SENT');self.assertEqual(self.changes(),[])
    def test_corrupt_action_stops_management_without_freeing_risk(self):
        self.execute(INCREASE)
        with self.store.db:self.store.db.execute("UPDATE position_actions SET digest='bad'")
        with self.assertRaises(ValueError):self.runner.manage(self.sid,True)
        self.assertEqual(self.runner.book.state(self.sid),'COMMITTED')
    def test_partial_reverse_open_reports_actual_quantity(self):
        self.next_plan();self.x.partial_next=True;_,r=self.execute(REVERSE)
        self.assertEqual(r['state'],'APPLIED',r);self.assertEqual(r['result']['phase'],'REVERSED_PARTIAL')
        self.assertLess(number(r['result']['next_filled_quantity']),number(r['result']['next_requested_quantity']))
    def test_rejected_reverse_does_not_become_success_after_empty_cleanup(self):
        self.next_plan();self.x.reject_next=True;p,r=self.execute(REVERSE)
        self.runner.manage(r['result']['next_session_id'],True)
        result=self.commands.reconcile(p['command_id']);self.assertEqual(result['state'],'UNKNOWN')
        self.assertEqual(result['result']['phase'],'OPEN_REJECTED');self.assertEqual(result['result']['next_filled_quantity'],'0')
    def test_cli_position_prepare_apply_show_and_reconcile(self):
        import io,json
        from contextlib import redirect_stdout
        from agentrader.cli.exchange_command_cli import main
        file=Path(self.folder.name)/'position.json';file.write_text(json.dumps(self.request()),encoding='utf-8')
        def call(args):
            out=io.StringIO()
            with redirect_stdout(out):code=main(['--database',str(self.path)]+args)
            self.assertEqual(code,0,out.getvalue());return json.loads(out.getvalue())
        with patch('agentrader.cli.exchange_command_cli.DemoExchange',return_value=self.x),patch('agentrader.cli.exchange_command_cli.Config.load',return_value=self.x.config),patch('agentrader.cli.exchange_command_cli.getpass.getuser',return_value='position'):
            p=call(['prepare',str(file)]);self.assertEqual(self.changes(),[])
            r=call(['apply',p['command_id'],'--digest',p['digest'],'--execute-demo']);self.assertEqual(r['result']['phase'],'FULL_FILL')
            call(['show',p['command_id']]);call(['reconcile',p['command_id']]);self.assertEqual(len(self.changes()),1)
    def test_short_hedge_reduce_and_reverse_keep_correct_legs(self):
        store=StateStore(Path(self.folder.name)/'hedge.db')
        try:
            x=HedgePositionExchange();service=PlanService(store,self.owner)
            plan=copy.deepcopy(self.plan);plan.update(plan_id='hedge-short',direction='SHORT',position_mode='hedge',stop='81600',targets=[{'price':'78400','fraction':'1'}])
            created=service.create(plan,self.owner);service.authorize(plan['plan_id'],1,created['authorization_token'],'approve',self.owner)
            runner=V2Runner(service,x,self.limits);sid=runner.open(plan['plan_id'],1,True)['session_id'];commands=ExchangeCommands(x,store,self.owner)
            increase=self.request(INCREASE,key='hedge-increase');increase['parameters']['session_id']=sid
            inc=commands.prepare(increase);result=commands.apply(inc['command_id'],inc['digest'],execute=True)
            self.assertEqual(result['state'],'APPLIED',result);self.assertEqual(x.amounts['BTCUSDT'],number('-.0014'))
            opening=next(p for m,path,p in x.calls if m=='POST' and p.get('newClientOrderId','').startswith('agt-pos-'))
            self.assertEqual((opening['side'],opening['positionSide']),('SELL','SHORT'));self.assertNotIn('reduceOnly',opening)
            request=self.request();request['parameters']['session_id']=sid;p=commands.prepare(request)
            r=commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(r['state'],'APPLIED')
            change=next(p for m,path,p in x.calls if m=='POST' and p.get('newClientOrderId','').startswith('agt-pos-') and p['type']=='MARKET')
            self.assertEqual((change['side'],change['positionSide']),('BUY','SHORT'));self.assertNotIn('reduceOnly',change)
            opposite=copy.deepcopy(self.plan);opposite.update(plan_id='hedge-long',position_mode='hedge');created=service.create(opposite,self.owner)
            request=self.request(CLOSE,key='reverse-hedge');request['operation']=REVERSE
            request['parameters'].update(session_id=sid,next_plan_id=opposite['plan_id'],next_version=1,
                next_digest=service.show(opposite['plan_id'],1)['digest'],risk_limits=limits_json())
            p=commands.prepare(request);r=commands.apply(p['command_id'],p['digest'],execute=True)
            self.assertEqual(r['state'],'APPLIED',r);self.assertGreater(x.amounts['BTCUSDT'],0)
            self.assertEqual(x.leg,'LONG')
        finally:store.close()
    def test_increased_owned_position_can_receive_full_size_native_trailing(self):
        self.execute(INCREASE)
        request=self.request(CLOSE,key='native-after-increase');request['operation']='CREATE_NATIVE_TRAILING'
        request['parameters'].update(quantity=str(self.x.amounts['BTCUSDT']),activate_price='80500',callback_rate='1',working_type='MARK_PRICE')
        p=self.commands.prepare(request);r=self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(r['state'],'APPLIED',r)
        self.assertEqual(number(next(a for a in self.x.algos.values() if a['orderType']=='TRAILING_STOP_MARKET')['quantity']),number('.0014'))
    def test_out_of_range_fill_is_reviewed_and_actual_notional_stays_reserved(self):
        import json
        original=self.x.request
        def inconsistent_fill(method,path,params):
            response=original(method,path,params)
            if params.get('newClientOrderId','').startswith('agt-pos-'):
                self.x.orders[params['newClientOrderId']]['avgPrice']='80200'
            return response
        with patch.object(self.x,'request',side_effect=inconsistent_fill):_,result=self.execute(INCREASE)
        self.assertEqual(result['state'],'UNKNOWN');self.assertEqual(result['result']['phase'],'PRICE_BOUND_REVIEW')
        self.assertTrue(self.store.halt_reason())
        row=self.store.db.execute('SELECT * FROM risk_reservations WHERE reservation_id=?',(self.sid,)).fetchone()
        exposures=self.runner.book._effective_exposures(self.store.db,row,json.loads(row['body']))
        self.assertEqual(number(exposures[-1].notional_price),number('80200'))
    def test_revoked_reverse_target_does_not_close_original_position(self):
        self.next_plan();p=self.commands.prepare(self.request(REVERSE))
        self.service.cancel('reverse-plan',1,self.owner)
        result=self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(result['state'],'NOT_SENT');self.assertEqual(self.changes(),[])
        self.assertGreater(self.x.amounts['BTCUSDT'],0)
    def test_lost_fill_with_manual_position_mix_is_not_declared_applied(self):
        original=self.x.request;self.x.lost=True
        def lose_and_mix(method,path,params):
            try:return original(method,path,params)
            except ExchangeError:
                self.x.amounts['BTCUSDT']+=number('.0001');raise
        with patch.object(self.x,'request',side_effect=lose_and_mix):_,result=self.execute(REDUCE)
        self.assertEqual(result['state'],'UNKNOWN');self.assertEqual(self.runner.book.state(self.sid),'COMMITTED')
    def test_new_increase_price_authority_does_not_reuse_old_entry_drift_limit(self):
        before=self.service.show(self.plan['plan_id'],1)['digest'];self.x.prices['BTCUSDT']='79200'
        request=self.request(INCREASE);request['parameters'].update(price_floor='79100',price_ceiling='79300')
        _,result=self.execute(request=request);self.assertEqual(result['state'],'APPLIED',result)
        self.assertEqual(self.service.show(self.plan['plan_id'],1)['digest'],before)
        self.assertEqual(self.service.show(self.plan['plan_id'],1)['plan']['entry']['reference_price'],'80000')
