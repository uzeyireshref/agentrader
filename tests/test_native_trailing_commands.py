import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agentrader.bot.exchange_commands import ExchangeCommands,validate_command
from agentrader.bot.native_trailing import CREATE,QUERY,CANCEL
from agentrader.bot.plans import PlanService
from agentrader.bot.risk import RiskLimits,number
from agentrader.bot.v2_runner import V2Runner
from agentrader.shared.exchange import ExchangeError
from agentrader.shared.state import StateStore
from test_plan_v2 import plan_v2
from test_v2_preflight import snapshot
from test_v2_runner import ExecutionExchange


class NativeExchange(ExecutionExchange):
    def __init__(self):
        super().__init__();self.cancel_race=False;self.reject_native=False;self.contract='79000'
    def get(self,path,params=None):
        if path=='/fapi/v2/ticker/price':return {'symbol':'BTCUSDT','price':self.contract,'time':int(time.time()*1000)}
        if path=='/fapi/v1/order' and 'orderId' in params:
            matches=[o for o in self.orders.values() if o['orderId']==params['orderId']]
            if not matches:raise ExchangeError('missing child',-2013)
            return copy.deepcopy(matches[0])
        if path=='/fapi/v1/algoOrder' and params['clientAlgoId'] not in self.algos:raise ExchangeError('missing algo',-2013)
        return super().get(path,params)
    def request(self,method,path,params):
        if method=='POST' and params.get('type')=='TRAILING_STOP_MARKET':
            if self.reject_native:
                self.calls.append((method,path,copy.deepcopy(params)));raise ExchangeError('rejected',-2021,400,delivery_status='REJECTED')
            try:super().request(method,path,params)
            finally:
                if params['clientAlgoId'] in self.algos:
                    self.algos[params['clientAlgoId']].update(algoId=100+len(self.algos),actualOrderId='')
            return copy.deepcopy(self.algos[params['clientAlgoId']])
        if method=='DELETE' and path.endswith('algoOrder') and self.cancel_race and params['clientAlgoId'].startswith('agt-nt-'):
            self.cancel_race=False;self.calls.append((method,path,copy.deepcopy(params)));self.trigger(params['clientAlgoId']);return {}
        if method=='DELETE' and path.endswith('/order') and 'orderId' in params:
            self.calls.append((method,path,copy.deepcopy(params)))
            for row in self.orders.values():
                if row['orderId']==params['orderId']:row['status']='CANCELED';return {}
        return super().request(method,path,params)
    def trigger(self,cid,filled=None,child_status='FILLED',parent_status='FINISHED'):
        algo=self.algos[cid];q=number(algo['quantity']);filled=q if filled is None else number(filled)
        oid=1000+len(self.orders);client='native-child-'+str(oid)
        child={'symbol':algo['symbol'],'orderId':oid,'clientOrderId':client,'side':algo['side'],
               'positionSide':algo['positionSide'],'type':'MARKET','origQty':str(q),'executedQty':str(filled),
               'status':child_status,'updateTime':int(time.time()*1000),'reduceOnly':algo.get('reduceOnly','false')}
        self.orders[client]=child;algo.update(actualOrderId=str(oid),algoStatus=parent_status)
        self.amount+=filled*(1 if algo['side']=='BUY' else -1)
        self.trades.append({'orderId':oid,'qty':str(filled),'side':algo['side']})


class NativeTrailingTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.path=Path(self.folder.name)/'state.db';self.store=StateStore(self.path)
        self.service=PlanService(self.store,'local:native');self.x=NativeExchange();self.plan=plan_v2()
        self.plan['entry'].update(condition='IMMEDIATE',trigger_price=None)
        self.snap=snapshot();self.snap.update(observed_at=time.time(),finished_at=time.time(),now_ms=int(time.time()*1000))
        self.mock=patch('agentrader.bot.v2_runner.collect_flat_snapshot',side_effect=lambda *a,**kw:copy.deepcopy(self.snap));self.mock.start()
        created=self.service.create(self.plan,'local:native');self.service.authorize(self.plan['plan_id'],1,created['authorization_token'],'approve','local:native')
        self.runner=V2Runner(self.service,self.x,RiskLimits());self.sid=self.runner.open(self.plan['plan_id'],1,True)['session_id']
        self.commands=ExchangeCommands(self.x,self.store,'local:native')
    def tearDown(self):self.mock.stop();self.store.close();self.folder.cleanup()
    def request(self,op=CREATE,key='native',ref=None):
        return {'schema_version':1,'client_command_id':key,'environment':'demo','exchange':'binance','product':'USD-M',
                'account_ref':self.commands.account_ref,'operation':op,'scope':{'symbol':'BTCUSDT'},
                'parameters':{'session_id':self.sid,'quantity':str(abs(self.x.amount)),'activate_price':'80500','callback_rate':'1','working_type':'MARK_PRICE'} if op==CREATE else {'create_command_id':ref}}
    def create(self):
        p=self.commands.prepare(self.request());return p,self.commands.apply(p['command_id'],p['digest'],execute=True)
    def command(self,op,ref,key):
        p=self.commands.prepare(self.request(op,key,ref));return p,self.commands.apply(p['command_id'],p['digest'],execute=True)
    def native_posts(self):return [p for m,path,p in self.x.calls if m=='POST' and p.get('type')=='TRAILING_STOP_MARKET']
    def test_prepare_no_network_or_intent_and_existing_protections_kept(self):
        n=len(self.x.calls)
        with patch.object(self.x,'get',side_effect=AssertionError('prepare must be local')):p=self.commands.prepare(self.request())
        self.assertEqual(p['state'],'PREPARED');self.assertEqual(len(self.x.calls),n);self.assertEqual(len(self.x.algos),2)
    def test_create_query_duplicate_and_existing_management(self):
        p,r=self.create();self.assertEqual(r['state'],'APPLIED');self.assertEqual(r['result']['algo_status'],'NEW')
        self.commands.apply(p['command_id'],p['digest'],execute=True)
        _,q=self.command(QUERY,p['command_id'],'query');self.assertEqual(q['state'],'APPLIED');self.assertIsNone(q['result']['filled_quantity'])
        self.assertEqual(len(self.native_posts()),1);self.assertEqual(len(self.x.algos),3)
        self.assertEqual(self.runner.manage(self.sid,True)['state'],'MANAGING')
    def test_callback_boundaries_and_invalid_fields(self):
        for rate in ('.1','20'):
            r=self.request(key=rate.replace('.','x'));r['parameters']['callback_rate']=rate;validate_command(r)
        for field,value in (('callback_rate','0.09'),('callback_rate','20.1'),('quantity',True),('activate_price','0'),('working_type','INDEX_PRICE')):
            r=self.request();r['parameters'][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):validate_command(r)
    def test_wrong_activation_side_blocks_send(self):
        r=self.request();r['parameters']['activate_price']='80000';p=self.commands.prepare(r)
        self.assertEqual(self.commands.apply(p['command_id'],p['digest'],execute=True)['state'],'NOT_SENT');self.assertEqual(self.native_posts(),[])
    def test_contract_reference_is_distinct_from_mark(self):
        r=self.request();r['parameters'].update(working_type='CONTRACT_PRICE',activate_price='79500');p=self.commands.prepare(r)
        self.assertEqual(self.commands.apply(p['command_id'],p['digest'],execute=True)['state'],'APPLIED')
    def test_excess_quantity_and_missing_execute_rejected(self):
        r=self.request();r['parameters']['quantity']='1'
        with self.assertRaises(ValueError):self.commands.prepare(r)
        p=self.commands.prepare(self.request())
        with self.assertRaises(ValueError):self.commands.apply(p['command_id'],p['digest'])
        self.assertEqual(self.native_posts(),[])
    def test_lost_response_restart_does_not_repost(self):
        self.x.algo_timeout=True;p,r=self.create();self.assertEqual(r['state'],'APPLIED')
        self.store.close();self.store=StateStore(self.path);self.service=PlanService(self.store,'local:native')
        self.commands=ExchangeCommands(self.x,self.store,'local:native');self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(len(self.native_posts()),1)
    def test_cancel_only_trailing_retains_fixed_protections_and_risk(self):
        p,r=self.create();_,c=self.command(CANCEL,p['command_id'],'cancel')
        self.assertEqual(c['state'],'APPLIED');self.assertEqual(c['result']['algo_status'],'CANCELED')
        self.assertEqual(sum(a['algoStatus']=='NEW' for a in self.x.algos.values()),2)
        self.assertEqual(self.runner.book.state(self.sid),'COMMITTED');self.assertEqual(self.runner.manage(self.sid,True)['state'],'MANAGING')
    def test_fill_cancel_race_reports_child_and_management_cleans_up(self):
        p,r=self.create();self.x.cancel_race=True;_,c=self.command(CANCEL,p['command_id'],'cancel-race')
        self.assertEqual(c['state'],'APPLIED');self.assertEqual(c['result']['child']['status'],'FILLED')
        self.assertNotEqual(c['result']['cancel_outcome'],'CANCELED')
        self.assertEqual(self.runner.manage(self.sid,True)['state'],'CLOSED');self.assertEqual(self.runner.book.state(self.sid),'RELEASED')
    def test_partial_trigger_keeps_remaining_owned_and_protected(self):
        p,r=self.create();self.x.trigger(r['result']['client_algo_id'],'.0003','CANCELED','CANCELED')
        _,q=self.command(QUERY,p['command_id'],'partial');self.assertEqual(q['result']['filled_quantity'],'0.0003')
        self.assertEqual(self.runner.manage(self.sid,True)['state'],'MANAGING');self.assertEqual(self.runner.book.state(self.sid),'COMMITTED')
        child=self.store.db.execute("SELECT * FROM order_projection WHERE client_id LIKE 'native-child:%'").fetchone()
        self.assertEqual(number(child['filled']),number('.0003'))
    def test_finished_parent_without_child_is_not_a_fill(self):
        p,r=self.create();self.x.algos[r['result']['client_algo_id']]['algoStatus']='FINISHED'
        _,q=self.command(QUERY,p['command_id'],'no-child');self.assertEqual(q['state'],'UNKNOWN');self.assertIsNone(q['result']['filled_quantity'])
    def test_child_identity_mismatch_blocks_observation(self):
        p,r=self.create();self.x.trigger(r['result']['client_algo_id']);child=next(o for o in self.x.orders.values() if o['orderId']>=1000)
        child['side']='BUY';_,q=self.command(QUERY,p['command_id'],'bad-child');self.assertEqual(q['state'],'READ_FAILED')
    def test_second_active_trailing_not_created(self):
        self.create();p=self.commands.prepare(self.request(key='other'))
        self.assertEqual(self.commands.apply(p['command_id'],p['digest'],execute=True)['state'],'NOT_SENT');self.assertEqual(len(self.native_posts()),1)
    def test_create_crash_after_reserved_intent_remains_unknown_without_repost(self):
        p=self.commands.prepare(self.request());original=self.store.reserve
        def crash(*args):original(*args);raise RuntimeError('crash before POST')
        with patch.object(self.store,'reserve',side_effect=crash):
            with self.assertRaises(RuntimeError):self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'UNKNOWN')
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(self.native_posts(),[])
    def test_definitive_rejection_never_resubmitted(self):
        self.x.reject_native=True;p,r=self.create();self.assertEqual(r['state'],'REJECTED')
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(len(self.native_posts()),1)
        self.assertEqual(self.runner.manage(self.sid,True)['state'],'MANAGING')
    def test_foreign_create_reference_rejected(self):
        p,_=self.create();r=self.request(QUERY,'wrong',p['command_id']);r['scope']['symbol']='ETHUSDT'
        with self.assertRaises(ValueError):self.commands.prepare(r)
    def test_active_child_blocks_flat_cleanup_until_child_terminal(self):
        p,r=self.create();self.x.trigger(r['result']['client_algo_id'],'0','NEW','FINISHED')
        # Another owned exit makes the position flat while the child is pending.
        from agentrader.bot.order_rules import validate_order
        s=self.runner._session(self.sid);params={'symbol':'BTCUSDT','side':'SELL','positionSide':'BOTH','type':'MARKET',
            'quantity':str(self.x.amount),'reduceOnly':'true','newClientOrderId':self.runner._id(s,'test-flat')}
        proposal=validate_order(params,self.snap['symbol_info'],'one-way','REDUCE','80000',int(time.time()*1000))
        s['exits'].append(proposal);self.runner._save(s);self.runner._post(s,proposal)
        self.assertEqual(self.runner.manage(self.sid,False)['state'],'CLEANUP_REQUIRED')
        self.assertEqual(self.runner.book.state(self.sid),'COMMITTED')
        self.assertEqual(self.runner.manage(self.sid,True)['state'],'CLOSED')
        deletes=[params for m,path,params in self.x.calls if m=='DELETE' and path.endswith('/order')]
        self.assertTrue(any('orderId' in params for params in deletes))
    def test_lost_cancel_response_resolves_without_another_delete(self):
        p,r=self.create();self.x.cancel_timeout=True;c,q=self.command(CANCEL,p['command_id'],'lost-cancel')
        self.assertEqual(q['state'],'APPLIED');n=len(self.x.calls)
        self.commands.apply(c['command_id'],c['digest'],execute=True);self.assertEqual(len(self.x.calls),n)
    def test_uncertain_cancel_is_never_resent_even_under_new_command_key(self):
        p,r=self.create();original=self.x.request
        def lose(method,path,params):
            if method=='DELETE':self.x.calls.append((method,path,copy.deepcopy(params)));raise ExchangeError('unknown cancel',delivery_status='UNKNOWN')
            return original(method,path,params)
        with patch.object(self.x,'request',side_effect=lose):
            _,q=self.command(CANCEL,p['command_id'],'lost');self.assertEqual(q['state'],'UNKNOWN')
            _,q=self.command(CANCEL,p['command_id'],'again');self.assertEqual(q['state'],'UNKNOWN')
        self.assertEqual(sum(m=='DELETE' for m,_,_ in self.x.calls),1)
    def test_expiry_during_preflight_prevents_native_post(self):
        p=self.commands.prepare(self.request(),ttl=1);clock=[time.time()]
        def expire(*args,**kwargs):clock[0]=p['expires_at']+1
        with patch('time.time',side_effect=lambda:clock[0]),patch('agentrader.bot.order_send_guard.validate_before_send',side_effect=expire):
            self.assertEqual(self.commands.apply(p['command_id'],p['digest'],execute=True)['state'],'EXPIRED')
        self.assertEqual(self.native_posts(),[])
    def test_real_cli_create_query_cancel_without_extra_permissions(self):
        import io,json
        from contextlib import redirect_stdout
        from agentrader.cli.exchange_command_cli import main
        file=Path(self.folder.name)/'native.json'
        def call(args):
            output=io.StringIO()
            with redirect_stdout(output):code=main(['--database',str(self.path)]+args)
            self.assertEqual(code,0,output.getvalue());return json.loads(output.getvalue())
        with patch('agentrader.cli.exchange_command_cli.DemoExchange',return_value=self.x),patch('agentrader.cli.exchange_command_cli.Config.load',return_value=self.x.config),patch('agentrader.cli.exchange_command_cli.getpass.getuser',return_value='native'):
            file.write_text(json.dumps(self.request()),encoding='utf-8');p=call(['prepare',str(file)])
            call(['apply',p['command_id'],'--digest',p['digest'],'--execute-demo'])
            for op,key in ((QUERY,'cli-query'),(CANCEL,'cli-cancel')):
                file.write_text(json.dumps(self.request(op,key,p['command_id'])),encoding='utf-8');q=call(['prepare',str(file)])
                call(['apply',q['command_id'],'--digest',q['digest']]+(['--execute-demo'] if op==CANCEL else []))
        self.assertEqual(len(self.native_posts()),1)
    def test_short_hedge_uses_buy_activation_below_reference_without_reduceonly(self):
        path=Path(self.folder.name)/'short.db';store=StateStore(path)
        try:
            service=PlanService(store,'local:native');x=NativeExchange();x.short=True;x.hedge=True
            plan=copy.deepcopy(self.plan);plan.update(direction='SHORT',position_mode='hedge',stop='81600',targets=[{'price':'78400','fraction':'1'}])
            self.snap['position_mode']='hedge';created=service.create(plan,'local:native')
            service.authorize(plan['plan_id'],1,created['authorization_token'],'approve','local:native')
            runner=V2Runner(service,x,RiskLimits());sid=runner.open(plan['plan_id'],1,True)['session_id'];commands=ExchangeCommands(x,store,'local:native')
            r=self.request();r['parameters'].update(session_id=sid,quantity=str(abs(x.amount)),activate_price='80000')
            p=commands.prepare(r);self.assertEqual(commands.apply(p['command_id'],p['digest'],execute=True)['state'],'NOT_SENT')
            r['client_command_id']='short-valid';r['parameters']['activate_price']='79500';p=commands.prepare(r)
            actual=commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(actual['state'],'APPLIED')
            native=next(a for a in x.algos.values() if a['orderType']=='TRAILING_STOP_MARKET')
            self.assertEqual((native['side'],native['positionSide']),('BUY','SHORT'));self.assertNotIn('reduceOnly',native)
        finally:store.close()
    def test_crash_after_successful_post_recovers_without_post(self):
        p=self.commands.prepare(self.request())
        with patch.object(self.commands,'_finish',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(self.commands.show(p['command_id'])['state'],'SUBMITTING')
        self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'APPLIED');self.assertEqual(len(self.native_posts()),1)
    def test_child_trade_total_mismatch_cannot_release_risk_even_if_net_position_matches(self):
        p,r=self.create();self.x.trigger(r['result']['client_algo_id']);oid=self.x.algos[r['result']['client_algo_id']]['actualOrderId']
        self.x.trades.extend([{'orderId':int(oid),'qty':'.0001','side':'BUY'},{'orderId':int(oid),'qty':'.0001','side':'SELL'}])
        self.assertEqual(self.x.amount,0)
        with self.assertRaises(ValueError):self.runner.manage(self.sid,True)
        self.assertEqual(self.runner.book.state(self.sid),'COMMITTED')
    def test_internal_child_projection_keeps_symbol_and_algo_identity_namespaces(self):
        from agentrader.bot.native_trailing import observe_child
        for symbol in ('BTCUSDT','ETHUSDT'):
            child={'orderId':1,'symbol':symbol,'side':'SELL','positionSide':'BOTH','origQty':'.0001',
                   'executedQty':'.0001','status':'FILLED','updateTime':1}
            observe_child(self.store,self.sid,{'algoId':1,'clientAlgoId':'same-number','symbol':symbol,'child':child})
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM order_projection WHERE client_id LIKE 'native-child:%'").fetchone()[0],2)
    def test_pending_child_also_blocks_second_trailing(self):
        p,r=self.create();self.x.trigger(r['result']['client_algo_id'],'0','NEW','FINISHED')
        p=self.commands.prepare(self.request(key='second-with-pending-child'))
        self.assertEqual(self.commands.apply(p['command_id'],p['digest'],execute=True)['state'],'NOT_SENT')
        self.assertEqual(len(self.native_posts()),1)
