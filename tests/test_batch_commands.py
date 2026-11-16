import copy
import io
import json
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from agentrader.bot.batch_commands import CREATE,AMEND,CANCEL
from agentrader.bot.exchange_commands import ExchangeCommands
from agentrader.bot.plans import PlanService
from agentrader.bot.risk import RiskLimits,number
from agentrader.bot.v2_runner import V2Runner
from agentrader.shared.exchange import ExchangeError
from agentrader.shared.state import StateStore
from test_cancel_scope_commands import CancelExchange
from test_plan_v2 import plan_v2


class BatchExchange(CancelExchange):
    def __init__(self):
        super().__init__();self.batch_lost=False;self.missing=set();self.reject=set();self.history=[];self.hide_history=False;self.before_batch=None
    def get(self,path,params=None):
        if path.endswith('/orderAmendment'):
            return [] if self.hide_history else copy.deepcopy([h for h in self.history if h['clientOrderId']==params['origClientOrderId']])
        return super().get(path,params)
    def request(self,method,path,p):
        if path.endswith('/batchOrders'):
            self.calls.append((method,path,copy.deepcopy(p)))
            if self.before_batch:self.before_batch(method,p)
            result=[]
            if method=='DELETE':
                for oid in json.loads(p['orderIdList']):
                    order=next(o for o in self.orders.values() if o['symbol']==p['symbol'] and o['orderId']==oid)
                    if order['clientOrderId'] in self.reject:result.append({'code':-2011});continue
                    self.request('DELETE','/fapi/v1/order',{'symbol':p['symbol'],'orderId':oid});result.append({})
            else:
                for item in json.loads(p['batchOrders']):
                    cid=item['newClientOrderId' if method=='POST' else 'origClientOrderId']
                    if cid in self.missing:continue
                    result.append({'code':-2019} if cid in self.reject else self.request(method,'/fapi/v1/order',item))
            if self.batch_lost:raise ExchangeError('lost',delivery_status='UNKNOWN')
            return result
        if method=='PUT':
            self.calls.append((method,path,copy.deepcopy(p)));a=self.orders[p['origClientOrderId']]
            if a['status']=='FILLED':return {'code':-2011}
            self.history.append({'symbol':a['symbol'],'clientOrderId':a['clientOrderId'],'orderId':a['orderId'],'time':int(time.time()*1000),
                'amendment':{'modifyId':p['modifyId'],'price':{'before':a['price'],'after':p['price']},'origQty':{'before':a['origQty'],'after':p['quantity']}}})
            a.update(origQty=p['quantity'],price=p['price'],updateTime=int(time.time()*1000));return copy.deepcopy(a)
        result=super().request(method,path,p)
        if method=='POST' and path.endswith('/order') and 'priceMatch' in p:
            self.orders[p['newClientOrderId']]['price']='80000';result=copy.deepcopy(self.orders[p['newClientOrderId']])
        return result


class BatchCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.db';self.store=StateStore(self.path)
        self.x=BatchExchange();self.owner='local:g08';self.commands=ExchangeCommands(self.x,self.store,self.owner);self.service=PlanService(self.store,self.owner)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def request(self,op=CREATE,key='group',symbols=('BTCUSDT','ETHUSDT'),parameters=None):
        return dict(schema_version=1,client_command_id=key,environment='demo',exchange='binance',product='USD-M',account_ref=self.commands.account_ref,
                    operation=op,scope={'symbols':list(symbols)} if op==CREATE else {'symbol':symbols[0]},parameters=parameters)
    def plans(self,types=('MARKET','LIMIT'),options=None):
        refs=[]
        for symbol,kind in zip(('BTCUSDT','ETHUSDT'),types):
            p=plan_v2();p.update(plan_id=symbol.lower(),symbol=symbol);p['sizing']['amount']='60'
            p['entry'].update(condition='LIMIT' if kind=='LIMIT' else 'IMMEDIATE',trigger_price='79900' if kind=='LIMIT' else None)
            if kind=='LIMIT' and options:p['entry']['order_options']=options
            row=self.service.create(p,self.owner);self.service.authorize(p['plan_id'],1,row['authorization_token'],'approve',self.owner)
            refs.append(dict(plan_id=p['plan_id'],version=1,plan_digest=row['digest'],entry_options=p['entry'].get('order_options',{})))
        limits={k:str(v) if k not in ('max_positions','max_age_seconds') else v for k,v in asdict(RiskLimits()).items()}
        limits.update(max_positions=2,max_notional='200')
        return self.request(symbols=('BTCUSDT','ETHUSDT')[:len(refs)],parameters={'plans':refs,'risk_limits':limits})
    def execute(self,r):
        p=self.commands.prepare(r);return p,self.commands.apply(p['command_id'],p['digest'],execute=True)
    def batches(self,method):return [p for m,path,p in self.x.calls if m==method and path.endswith('/batchOrders')]
    def cancel_request(self,key='cancel'):
        return self.request(CANCEL,key,parameters={'targets':[{'namespace':'NORMAL','client_id':c} for c in ('manual','second')],'include_foreign':True})
    def amend_request(self,options=None):
        r=self.plans(types=('LIMIT',),options=options);self.x.limit_pending=True;p,result=self.execute(r)
        self.assertEqual(result['state'],'APPLIED',result)
        s=self.store.sessions()[0]
        return self.request(AMEND,'amend',parameters={'session_id':s['id'],'changes':[{'client_id':s['entry_id'],'quantity':'.0007','price':'79800'}]})
    def test_create_preview_is_read_only_and_digest_covers_all_members(self):
        r=self.plans();p=self.commands.prepare(r)
        self.assertEqual(len(p['prepared_details']['batch']['members']),2);self.assertEqual(self.x.calls,[])
        with patch.object(self.x,'get',side_effect=AssertionError('duplicate local')):self.assertTrue(self.commands.prepare(r)['duplicate'])
        r['parameters']['risk_limits']['max_notional']='250'
        with self.assertRaises(ValueError):self.commands.prepare(r)
    def test_mixed_market_limit_create_each_session_gets_owned_journal_and_protection(self):
        self.x.limit_pending=True;p,r=self.execute(self.plans())
        self.assertEqual(r['state'],'APPLIED',r);self.assertEqual(len(self.batches('POST')),1)
        self.assertEqual({p['type'] for p in json.loads(self.batches('POST')[0]['batchOrders'])},{'MARKET','LIMIT'})
        self.assertEqual(len(self.store.sessions()),2);self.assertEqual(len(self.x.algos),2)
        for s in self.store.sessions():self.assertEqual(self.store.db.execute('SELECT owner FROM order_projection WHERE client_id=?',(s['entry_id'],)).fetchone()[0],s['id'])
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(len(self.batches('POST')),1)
    def test_lost_create_reply_queries_all_members_without_repost(self):
        self.x.batch_lost=True;p,r=self.execute(self.plans(types=('MARKET','MARKET')))
        self.assertEqual(r['state'],'APPLIED',r);self.commands.reconcile(p['command_id']);self.assertEqual(len(self.batches('POST')),1)
    def test_missing_member_keeps_unknown_and_protects_proven_other_fill(self):
        r=self.plans(types=('MARKET','MARKET'));missing='agt-'+__import__('hashlib').sha256(b'ethusdt:1:entry').hexdigest()[:28]
        self.x.missing={missing};self.x.batch_lost=True;p,result=self.execute(r)
        self.assertEqual(result['state'],'UNKNOWN',result);self.assertTrue(self.store.halt_reason())
        self.assertEqual(len(self.x.algos),2);self.assertTrue(all(p['symbol']=='BTCUSDT' for p in self.x.algos.values()))
        self.store.close();self.store=StateStore(self.path);self.commands=ExchangeCommands(self.x,self.store,self.owner)
        self.commands.reconcile(p['command_id']);self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(len(self.batches('POST')),1)
    def test_partial_reject_is_not_whole_group_success(self):
        r=self.plans(types=('MARKET','MARKET'));self.x.reject={'agt-'+__import__('hashlib').sha256(b'ethusdt:1:entry').hexdigest()[:28]}
        _,result=self.execute(r);self.assertEqual(result['state'],'FINAL_WITH_ERRORS',result)
        self.assertEqual(len(self.batches('POST')),1);self.assertEqual(len(self.x.algos),2)
    def test_group_risk_limit_cannot_be_bypassed_by_small_members(self):
        r=self.plans();r['parameters']['risk_limits']['max_notional']='100'
        with self.assertRaises(ValueError):self.commands.prepare(r)
        self.assertEqual(self.batches('POST'),[]);self.assertEqual(self.store.sessions(),[])
    def test_duplicate_plan_or_symbol_is_rejected(self):
        r=self.plans();r['parameters']['plans'][1]=r['parameters']['plans'][0]
        with self.assertRaises(ValueError):self.commands.prepare(r)
        r=self.request(parameters={'plans':[],'risk_limits':{}})
        with self.assertRaises(ValueError):self.commands.prepare(r)
    def test_explicit_execute_and_digest_gates(self):
        p=self.commands.prepare(self.plans())
        with self.assertRaises(ValueError):self.commands.apply(p['command_id'],p['digest'])
        with self.assertRaises(ValueError):self.commands.apply(p['command_id'],'wrong',execute=True)
        self.assertEqual(self.x.calls,[])
    def test_create_records_all_intents_before_batch_delivery(self):
        observed=[]
        def hook(method,p):observed.extend(self.store.intent(o['newClientOrderId'])['state'] for o in json.loads(p['batchOrders']))
        self.x.before_batch=hook;self.execute(self.plans());self.assertEqual(observed,['SUBMITTING','SUBMITTING'])
    def test_second_plan_claim_failure_rolls_back_whole_reservation_and_session_group(self):
        r=self.plans();original=PlanService.claim;count=[0]
        def claim(service,*a,**kw):
            count[0]+=1
            if count[0]==2:raise ValueError('injected second claim failure')
            return original(service,*a,**kw)
        with patch.object(PlanService,'claim',new=claim):_,result=self.execute(r)
        self.assertEqual(result['state'],'NOT_SENT',result);self.assertEqual(self.store.sessions(),[])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM risk_reservations').fetchone()[0],0)
        self.assertEqual({r[0] for r in self.store.db.execute('SELECT state FROM plan_versions')},{'AUTHORIZED'})
        self.assertEqual(self.batches('POST'),[])
    def test_restart_after_intents_before_delivery_never_reposts(self):
        p=self.commands.prepare(self.plans());self.x.before_batch=lambda *a:(_ for _ in ()).throw(KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.store.close();self.store=StateStore(self.path);self.commands=ExchangeCommands(self.x,self.store,self.owner)
        self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'UNKNOWN')
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(len(self.batches('POST')),1)
    def test_restart_after_delivery_existing_manager_recovers_protection_without_reentry(self):
        from agentrader.bot.position_commands import risk_limits
        request=self.plans(types=('MARKET','MARKET'));p=self.commands.prepare(request);original=self.x.request
        def crash(method,path,params):
            result=original(method,path,params)
            if method=='POST' and path.endswith('/batchOrders'):raise KeyboardInterrupt
            return result
        with patch.object(self.x,'request',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.store.close();self.store=StateStore(self.path);self.commands=ExchangeCommands(self.x,self.store,self.owner)
        runner=V2Runner(PlanService(self.store,self.owner),self.x,risk_limits(request['parameters']['risk_limits']))
        for s in self.store.sessions():runner.manage(s['id'],execute=True)
        self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'APPLIED');self.assertEqual(len(self.x.algos),4)
        self.assertEqual(len(self.batches('POST')),1)
    def test_create_ioc(self):
        _,r=self.execute(self.plans(types=('LIMIT',),options={'time_in_force':'IOC'}));self.assertEqual(r['state'],'APPLIED',r)
    def test_create_fok(self):
        _,r=self.execute(self.plans(types=('LIMIT',),options={'time_in_force':'FOK'}));self.assertEqual(r['state'],'APPLIED',r)
    def test_create_gtx(self):
        _,r=self.execute(self.plans(types=('LIMIT',),options={'time_in_force':'GTX'}));self.assertEqual(r['state'],'APPLIED',r)
    def test_create_gtd_and_stp(self):
        _,r=self.execute(self.plans(types=('LIMIT',),options={'time_in_force':'GTD','good_till_date':int(time.time()*1000)+800999,'self_trade_prevention_mode':'EXPIRE_BOTH'}))
        self.assertEqual(r['state'],'APPLIED',r);order=json.loads(self.batches('POST')[0]['batchOrders'])[0]
        self.assertEqual(order['goodTillDate']%1000,0);self.assertEqual(order['selfTradePreventionMode'],'EXPIRE_BOTH')
    def test_create_price_match_uses_returned_price(self):
        _,r=self.execute(self.plans(types=('LIMIT',),options={'price_match':'QUEUE_5'}));self.assertEqual(r['state'],'APPLIED',r)
        order=json.loads(self.batches('POST')[0]['batchOrders'])[0];self.assertNotIn('price',order);self.assertEqual(order['priceMatch'],'QUEUE_5')
    def test_prepare_scope_changed_before_apply_does_not_consume_plans(self):
        p=self.commands.prepare(self.plans());self.x.amounts['BTCUSDT']=number('.001')
        result=self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(result['state'],'NOT_SENT');self.assertEqual(self.store.sessions(),[]);self.assertEqual(self.batches('POST'),[])
    def test_normal_batch_cancel_uses_frozen_broker_ids(self):
        self.x.add_normal('manual');self.x.add_normal('second');p=self.commands.prepare(self.cancel_request());self.x.add_normal('late')
        r=self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(r['state'],'APPLIED',r);self.assertEqual(len(self.batches('DELETE')),1)
        self.assertEqual(self.x.orders['late']['status'],'NEW');self.assertEqual(len(json.loads(self.batches('DELETE')[0]['orderIdList'])),2)
    def test_cancel_partial_rejection_and_lost_reply_are_independent(self):
        self.x.add_normal('manual');self.x.add_normal('second');self.x.reject={'second'};self.x.batch_lost=True
        p,r=self.execute(self.cancel_request());self.assertEqual(r['state'],'UNKNOWN');self.assertEqual(self.x.orders['manual']['status'],'CANCELED')
        self.commands.reconcile(p['command_id']);self.assertEqual(len(self.batches('DELETE')),1)
    def test_g07_unknown_cancel_blocks_native_batch_resend(self):
        self.x.add_normal('manual');self.x.add_normal('second');self.x.no_effect_ids={'manual','second'}
        request=self.cancel_request();request['operation']='CANCEL_SELECTED_ORDERS';self.execute(request)
        _,result=self.execute(self.cancel_request('native-after'));self.assertEqual(result['state'],'UNKNOWN');self.assertEqual(self.batches('DELETE'),[])
    def test_batch_cancel_rejects_algo_and_foreign_scope_omission(self):
        r=self.cancel_request();r['parameters']['targets'][0]['namespace']='ALGO'
        with self.assertRaises(ValueError):self.commands.prepare(r)
        self.x.add_normal('manual');self.x.add_normal('second');r=self.cancel_request();r['parameters']['include_foreign']=False
        with self.assertRaises(ValueError):self.commands.prepare(r)
    def test_amend_through_common_command_verifies_history(self):
        p,r=self.execute(self.amend_request());self.assertEqual(r['state'],'APPLIED',r);self.assertEqual(len(self.batches('PUT')),1)
        self.assertEqual(json.loads(self.batches('PUT')[0]['batchOrders'])[0]['orderId'],next(iter(self.x.orders.values()))['orderId'])
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(len(self.batches('PUT')),1)
    def test_amend_lost_reply_and_delayed_history_do_not_repost(self):
        request=self.amend_request();self.x.batch_lost=True;self.x.hide_history=True
        p,r=self.execute(request);self.assertEqual(r['state'],'UNKNOWN',r);self.assertEqual(len(self.batches('PUT')),1)
        self.x.hide_history=False;self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'APPLIED');self.assertEqual(len(self.batches('PUT')),1)
    def test_cancel_prepared_parent_cancels_all_amend_children(self):
        p=self.commands.prepare(self.amend_request());self.commands.cancel(p['command_id'],p['digest'])
        states=[r[0] for r in self.store.db.execute('SELECT state FROM order_modifications')]
        self.assertEqual(states,['CANCELED']);self.assertEqual(self.batches('PUT'),[])
    def test_amend_gtx_keeps_original_tif(self):
        _,r=self.execute(self.amend_request(options={'time_in_force':'GTX'}));self.assertEqual(r['state'],'APPLIED',r)
        self.assertEqual(next(iter(self.x.orders.values()))['timeInForce'],'GTX')
    def test_amend_gtd_keeps_original_expiry(self):
        expiry=(int(time.time()*1000)+800000)//1000*1000
        _,r=self.execute(self.amend_request(options={'time_in_force':'GTD','good_till_date':expiry}));self.assertEqual(r['state'],'APPLIED',r)
        self.assertEqual(next(iter(self.x.orders.values()))['goodTillDate'],expiry)
    def test_amend_fill_race_sends_no_put(self):
        request=self.amend_request();p=self.commands.prepare(request);self.x.fill(request['parameters']['changes'][0]['client_id'])
        result=self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(result['state'],'NOT_SENT');self.assertEqual(self.batches('PUT'),[])
    def test_expired_parent_retires_amend_children(self):
        request=self.amend_request();p=self.commands.prepare(request,ttl=1)
        with patch('agentrader.bot.exchange_commands.time.time',return_value=p['expires_at']+1):r=self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(r['state'],'EXPIRED');self.assertEqual(self.store.db.execute('SELECT state FROM order_modifications').fetchone()[0],'CANCELED')
    def test_corrupt_amend_member_never_sends(self):
        p=self.commands.prepare(self.amend_request())
        with self.store.db:self.store.db.execute("UPDATE order_modifications SET digest='bad'")
        with self.assertRaises(ValueError):self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(self.batches('PUT'),[])
    def test_parent_cancel_retries_after_child_cancel_crash_without_put(self):
        from agentrader.bot.batch_commands import cancel_prepared
        p=self.commands.prepare(self.amend_request());_,body=self.commands._row(p['command_id'])
        cancel_prepared(self.commands,body)
        self.assertEqual(self.commands.cancel(p['command_id'],p['digest'])['state'],'CANCELED')
        self.assertEqual(self.batches('PUT'),[])
    def test_applying_parent_with_previously_canceled_children_is_not_sent(self):
        from agentrader.bot.batch_commands import cancel_prepared
        p=self.commands.prepare(self.amend_request());_,body=self.commands._row(p['command_id']);cancel_prepared(self.commands,body)
        self.assertEqual(self.commands.apply(p['command_id'],p['digest'],execute=True)['state'],'NOT_SENT')
        self.assertEqual(self.batches('PUT'),[])
    def test_cli_create_prepare_apply_show_reconcile(self):
        from agentrader.cli.exchange_command_cli import main
        request=self.plans();file=Path(self.temp.name)/'batch.json';file.write_text(json.dumps(request),encoding='utf-8')
        def call(args):
            out=io.StringIO()
            with redirect_stdout(out):code=main(['--database',str(self.path)]+args)
            self.assertEqual(code,0,out.getvalue());return json.loads(out.getvalue())
        with patch('agentrader.cli.exchange_command_cli.Config.load',return_value=self.x.config),patch('agentrader.cli.exchange_command_cli.DemoExchange',return_value=self.x),patch('agentrader.cli.exchange_command_cli.getpass.getuser',return_value='g08'):
            p=call(['prepare',str(file)]);call(['show',p['command_id']]);call(['apply',p['command_id'],'--digest',p['digest'],'--execute-demo']);call(['reconcile',p['command_id']])
        self.assertEqual(len(self.batches('POST')),1)
