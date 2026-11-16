import copy
import io
import json
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from unittest.mock import patch

from agentrader.bot.account_commands import AccountCommands
from agentrader.bot.brackets import leverage_constraints,select_bracket
from agentrader.bot.exchange_commands import ExchangeCommands,validate_command
from agentrader.bot.plan_v2 import validate_v2
from agentrader.shared.config import Config
from agentrader.shared.exchange import DemoExchange,ExchangeError,COIN_BASE_URL,allowed_requests
from agentrader.shared.state import StateStore
from test_account_commands import SettingsExchange
from test_plan_v2 import plan_v2


class DynamicSettingsExchange(SettingsExchange):
    def __init__(self):
        super().__init__();self.reads=[];self.cap=200;self.second_cap=None;self.bracket_reads=0
        self.coin_dual=None;self.fail_path=None;self.override={};self.before_post=None;self.on_read=None
    def get(self,path,params=None):
        self.reads.append((path,copy.deepcopy(params)))
        if self.on_read:self.on_read(path)
        if path==self.fail_path:raise ExchangeError('SECRET_CANARY unavailable',-2015,400,delivery_status='REJECTED')
        if path in self.override:return copy.deepcopy(self.override[path])
        if path=='/dapi/v1/positionSide/dual' and self.coin_dual is not None:return {'dualSidePosition':self.coin_dual}
        if path.endswith('leverageBracket'):
            self.bracket_reads+=1;cap=self.second_cap if self.second_cap is not None and self.bracket_reads>1 else self.cap
            return [{'symbol':'BTCUSDT','brackets':[{'notionalFloor':0,'notionalCap':10000,'initialLeverage':cap,'maintMarginRatio':'.004','cum':0},
                    {'notionalFloor':10000,'notionalCap':1000000,'initialLeverage':min(cap,50),'maintMarginRatio':'.005','cum':10}]}]
        return super().get(path,params)
    def request(self,method,path,params):
        if self.before_post:self.before_post(method,path,params)
        return super().request(method,path,params)


class G09SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.db';self.store=StateStore(self.path)
        self.owner='local:g09';self.x=DynamicSettingsExchange();self.service=AccountCommands(self.x,self.store,self.owner)
        self.commands=ExchangeCommands(self.x,self.store,self.owner)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def prepared(self,kind='LEVERAGE',value=150):return self.service.prepare(kind,value,'BTCUSDT' if kind in ('LEVERAGE','MARGIN_TYPE') else None)
    def apply(self,p,**kw):return self.service.apply(p['command_id'],p['digest'],**kw)
    def request(self,operation='SET_POSITION_MODE',key='setting'):
        if operation=='SET_POSITION_MODE':scope={'affected_products':['USD-M','COIN-M']};params={'enabled':True}
        elif operation in ('SET_MULTI_ASSETS_MODE','SET_FEE_BURN'):scope={'account_wide':True};params={'enabled':True}
        else:scope={'symbol':'BTCUSDT'};params={'margin_type':'ISOLATED'} if operation=='SET_MARGIN_TYPE' else {'leverage':150}
        return dict(schema_version=1,client_command_id=key,environment='demo',exchange='binance',product='USD-M',account_ref=self.commands.account_ref,
                    operation=operation,scope=scope,parameters=params)
    def execute(self,request):
        p=self.commands.prepare(request);return p,self.commands.apply(p['command_id'],p['digest'],execute=True)
    def test_above_125_uses_current_account_symbol_cap_and_records_full_constraint(self):
        p=self.prepared();r=self.apply(p);self.assertEqual(r['state'],'APPLIED');self.assertEqual(self.x.leverage,150)
        proof=self.service.show(p['command_id'])['result']['preflight']
        self.assertEqual(proof['constraints']['maximum_leverage'],200);self.assertEqual(proof['constraints']['max_notional_for_requested'],'10000')
        self.assertEqual(len(self.x.calls),1)
    def test_symbol_with_lower_cap_is_rejected_without_clamping(self):
        self.x.cap=75;p=self.prepared()
        with self.assertRaises(ValueError):self.apply(p)
        self.assertEqual(self.x.calls,[]);self.assertEqual(self.x.leverage,10)
    def test_bracket_changes_at_last_boundary_do_not_post(self):
        self.x.second_cap=50;p=self.prepared()
        with self.assertRaises(ValueError):self.apply(p)
        self.assertEqual(self.x.bracket_reads,2);self.assertEqual(self.x.calls,[])
    def test_noop_still_requires_supported_current_ladder(self):
        self.x.cap=50;self.x.leverage=150;p=self.prepared()
        with self.assertRaises(ValueError):self.apply(p)
        self.assertEqual(self.x.calls,[])
    def test_broken_ladder_or_account_coefficient_is_not_accepted(self):
        payload=self.x.get('/fapi/v1/leverageBracket');payload[0]['brackets'][1]['notionalFloor']=9999
        with self.assertRaises(ValueError):leverage_constraints(payload,'BTCUSDT',20)
        payload=self.x.get('/fapi/v1/leverageBracket');payload[0]['notionalCoef']='2'
        with self.assertRaises(ValueError):leverage_constraints(payload,'BTCUSDT',20)
        with self.assertRaises(ValueError):leverage_constraints(payload,'OTHERUSDT',20)
    def test_actual_notional_tier_still_limits_accepted_high_leverage(self):
        rows=self.x.get('/fapi/v1/leverageBracket')[0]['brackets']
        self.assertEqual(select_bracket(rows,5000,150)['initialLeverage'],200)
        with self.assertRaises(ValueError):select_bracket(rows,10000,150)
    def test_plan_syntax_defers_upper_bound_to_runtime_brackets(self):
        plan=plan_v2();plan['execution']['leverage']=150;self.assertEqual(validate_v2(plan)['execution']['leverage'],150)
        for value in (True,0,-1,1.5,'150'):
            plan['execution']['leverage']=value
            with self.subTest(value=value),self.assertRaises(ValueError):validate_v2(plan)
    def test_setting_check_is_durable_before_post(self):
        def before(*a):
            row=self.store.db.execute('SELECT body FROM account_command_checks').fetchone();self.assertIsNotNone(row)
            self.assertTrue(json.loads(row['body'])['flat_verified'])
        self.x.before_post=before;self.apply(self.prepared())
    def test_coin_position_blocks_shared_mode_even_when_um_flat(self):
        self.x.coin_positions=[{'symbol':'BTCUSD_PERP','positionAmt':'1'},{'symbol':'BTCUSD_PERP','positionAmt':'-1'}]
        p=self.prepared('POSITION_MODE',True)
        with self.assertRaises(ValueError):self.apply(p,cross_product_flat_verified=True)
        self.assertEqual(self.x.calls,[])
    def test_coin_normal_or_algo_order_blocks_shared_mode(self):
        p=self.prepared('POSITION_MODE',True)
        for field in ('coin_orders','coin_algos'):
            with self.subTest(field=field):
                setattr(self.x,field,[{'symbol':'BTCUSD_PERP'}])
                with self.assertRaises(ValueError):self.apply(p)
                setattr(self.x,field,[])
        self.assertEqual(self.x.calls,[])
    def test_coin_auth_failure_cannot_be_overridden_by_legacy_boolean(self):
        self.x.fail_path='/dapi/v1/positionRisk';p=self.prepared('POSITION_MODE',True)
        with self.assertRaises(ExchangeError):self.apply(p,cross_product_flat_verified=True)
        self.assertEqual(self.x.calls,[])
    def test_malformed_empty_looking_coin_payload_is_not_flat(self):
        p=self.prepared('POSITION_MODE',True)
        for value in ({},None,{'orders':[]},[{}]):
            self.x.override['/dapi/v1/positionRisk']=value
            with self.subTest(value=value),self.assertRaises(ValueError):self.apply(p)
        self.assertEqual(self.x.calls,[])
    def test_shared_mode_records_both_products_and_sends_only_um_post(self):
        p,r=self.execute(self.request());self.assertEqual(r['state'],'APPLIED',r)
        observation=r['result']['observation'];self.assertEqual(observation['observed_products'],{'USD-M':True,'COIN-M':True})
        self.assertEqual(set(observation['preflight']['flat_products']),{'USD-M','COIN-M'})
        self.assertEqual(self.x.calls,[('POST','/fapi/v1/positionSide/dual',{'dualSidePosition':'true'})])
    def test_scope_requires_explicit_both_product_acknowledgement(self):
        for scope in ({'symbol':'BTCUSDT'},{'account_wide':True},{'affected_products':['USD-M']},{'affected_products':['USD-M','COIN-M','SPOT']}):
            r=self.request();r['scope']=scope
            with self.subTest(scope=scope),self.assertRaises(ValueError):validate_command(r)
    def test_coin_order_appearing_at_second_snapshot_blocks_post(self):
        reads=[0]
        def on_read(path):
            if path=='/dapi/v1/positionRisk':
                reads[0]+=1
                if reads[0]==2:self.x.coin_algos=[{'symbol':'BTCUSD_PERP'}]
        self.x.on_read=on_read;p=self.prepared('POSITION_MODE',True)
        with self.assertRaises(ValueError):self.apply(p)
        self.assertEqual(self.x.calls,[])
    def test_mismatched_product_mode_after_lost_ack_remains_unknown_without_repost(self):
        self.x.coin_dual=False;self.x.lose_response=True;p,r=self.execute(self.request())
        self.assertEqual(r['state'],'UNKNOWN',r);self.assertTrue(self.store.unresolved_account_command())
        self.store.close();self.store=StateStore(self.path);self.commands=ExchangeCommands(self.x,self.store,self.owner)
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.commands.reconcile(p['command_id']);self.assertEqual(len(self.x.calls),1)
        self.x.coin_dual=True;self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'APPLIED')
        self.assertEqual(len(self.x.calls),1)
    def test_lost_shared_mode_ack_resolves_only_when_both_reads_match(self):
        self.x.lose_response=True;_,r=self.execute(self.request());self.assertEqual(r['state'],'APPLIED',r)
        self.assertEqual(len(self.x.calls),1)
    def test_all_new_settings_use_common_command_digest_and_delegate(self):
        for operation in ('SET_LEVERAGE','SET_MARGIN_TYPE','SET_MULTI_ASSETS_MODE','SET_FEE_BURN'):
            with self.subTest(operation=operation):
                p,r=self.execute(self.request(operation,operation));self.assertEqual(r['state'],'APPLIED',r)
                self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(len(self.x.calls),4)
    def test_active_session_prevents_all_configuration_changes(self):
        self.store.save_session({'id':'dummy','active':True})
        p=self.prepared('POSITION_MODE',True)
        with self.assertRaises(ValueError):self.apply(p)
        self.assertEqual(self.x.calls,[])
    def test_mutation_execution_gate_is_explicit(self):
        p=self.commands.prepare(self.request())
        with self.assertRaises(ValueError):self.commands.apply(p['command_id'],p['digest'])
        with self.assertRaises(ValueError):self.commands.apply(p['command_id'],'wrong',execute=True)
        self.assertEqual(self.x.reads+self.x.calls,[])
    def test_settings_cli_prepare_show_apply_and_reconcile(self):
        from agentrader.cli.settings_cli import main
        def call(args):
            out=io.StringIO()
            with redirect_stdout(out):code=main(['--database',str(self.path)]+args)
            self.assertEqual(code,0,out.getvalue());return json.loads(out.getvalue())
        with patch('agentrader.cli.settings_cli.Config.load',return_value=self.x.config),patch('agentrader.cli.settings_cli.DemoExchange',return_value=self.x),patch('agentrader.cli.settings_cli.getpass.getuser',return_value='g09'):
            p=call(['prepare','--kind','POSITION_MODE','--value','true']);self.assertEqual(p['affected_products'],['USD-M','COIN-M'])
            call(['show',p['command_id']]);call(['apply',p['command_id'],'--digest',p['digest'],'--execute-demo']);call(['reconcile',p['command_id']])
        self.assertEqual(len(self.x.calls),1)
    def test_common_cli_shared_scope_prepare_apply_show_reconcile(self):
        from agentrader.cli.exchange_command_cli import main
        file=Path(self.temp.name)/'mode.json';file.write_text(json.dumps(self.request()),encoding='utf-8')
        def call(args):
            out=io.StringIO()
            with redirect_stdout(out):code=main(['--database',str(self.path)]+args)
            self.assertEqual(code,0,out.getvalue());return json.loads(out.getvalue())
        with patch('agentrader.cli.exchange_command_cli.Config.load',return_value=self.x.config),patch('agentrader.cli.exchange_command_cli.DemoExchange',return_value=self.x),patch('agentrader.cli.exchange_command_cli.getpass.getuser',return_value='g09'):
            p=call(['prepare',str(file)]);call(['show',p['command_id']]);call(['apply',p['command_id'],'--digest',p['digest'],'--execute-demo']);call(['reconcile',p['command_id']])
        self.assertEqual(len(self.x.calls),1)
    def test_corrupt_setting_proof_does_not_prove_success_or_resend(self):
        self.x.coin_dual=False;p,r=self.execute(self.request());self.assertEqual(r['state'],'UNKNOWN')
        with self.store.db:self.store.db.execute("UPDATE account_command_checks SET digest='bad'")
        self.x.coin_dual=True
        self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'UNKNOWN')
        self.assertEqual(len(self.x.calls),1)
    def test_lost_isolated_margin_is_not_repeated_after_store_restart(self):
        from agentrader.bot.isolated_margin import IsolatedMarginCommands
        from test_isolated_margin import MarginExchange
        x=MarginExchange();service=IsolatedMarginCommands(x,self.store,self.owner,clock=lambda:1000)
        p=service.prepare('BTCUSDT','BOTH','ADD','10');x.lost=True
        self.assertEqual(service.apply(p['command_id'],p['digest'])['state'],'UNKNOWN');self.assertEqual(x.wallet,'30')
        self.store.close();self.store=StateStore(self.path);service=IsolatedMarginCommands(x,self.store,self.owner,clock=lambda:1000)
        self.assertEqual(service.apply(p['command_id'],p['digest'])['state'],'UNKNOWN');service.reconcile(p['command_id'])
        self.assertEqual(len(x.calls),1)


class G09CoinTransportTests(unittest.TestCase):
    def test_coin_reads_are_signed_to_fixed_demo_host_with_independent_clock(self):
        requests=[]
        class Transport:
            def perform(self,opener,factory,method,base):
                req=factory();requests.append((req,base))
                return {'serverTime':int(time.time()*1000)+3000} if urlparse(req.full_url).path.endswith('/time') else []
        x=DemoExchange(Config('demo-key','demo-secret'),transport=Transport());x.offset_ms=-9000
        with patch('time.time',return_value=1000):x.get('/dapi/v1/positionRisk')
        self.assertEqual(len(requests),2);self.assertEqual(requests[0][0].headers,{})
        req,base=requests[1];self.assertEqual(base,COIN_BASE_URL);self.assertEqual(urlparse(req.full_url).netloc,'demo-dapi.binance.com')
        query=parse_qs(urlparse(req.full_url).query);self.assertEqual(query['timestamp'],['1003000']);self.assertIn('signature',query)
        self.assertEqual(req.get_header('X-mbx-apikey'),'demo-key');self.assertEqual(x.offset_ms,-9000)
    def test_no_coin_financial_route_or_arbitrary_host_is_allowed(self):
        x=DemoExchange(Config('demo-key','demo-secret'))
        for method,path in [('POST','/dapi/v1/positionSide/dual'),('POST','/dapi/v1/order'),('DELETE','/dapi/v1/algoOrder'),('GET','https://dapi.binance.com/dapi/v1/openOrders'),('GET','/dapi/v1/account')]:
            with self.subTest(method=method,path=path),self.assertRaises(ValueError):x.request(method,path)
        self.assertEqual({m for m,p in allowed_requests() if p.startswith('/dapi/')},{'GET'})
