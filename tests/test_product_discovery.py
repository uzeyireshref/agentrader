import copy
import hashlib
import io
import json
import os
from contextlib import closing,redirect_stdout
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs

from agentrader.bot.account_commands import AccountCommands
from agentrader.bot.account_discovery import probe,lookup_order
from agentrader.bot.exchange_commands import ExchangeCommands
from agentrader.shared.config import Config,DiscoveryCredentials
from agentrader.shared.discovery_exchange import DiscoveryExchange
from agentrader.shared.discovery_store import DiscoveryStore
from agentrader.shared.exchange import DemoExchange,ExchangeError
from agentrader.shared.market_data import CandleStore
from agentrader.shared.product_registry import PROFILES,profile,scoped_identity,inventory,EXECUTION_CONTEXT
from agentrader.shared.state import StateStore


KEY='G11_KEY_CANARY';SECRET='G11_SECRET_CANARY'


class DiscoveryTransport:
    def __init__(self):self.calls=[];self.responses={};self.errors={};self.clock_offset=3000
    def perform(self,opener,factory,method,base):
        req=factory();path=urlparse(req.full_url).path;self.calls.append((req,method,base))
        if path in self.errors:raise self.errors[path]
        if path in self.responses:return copy.deepcopy(self.responses[path])
        if path.endswith('/time'):return {'serverTime':int(time.time()*1000)+self.clock_offset}
        if path.endswith('/ping'):return {}
        if path.endswith('/exchangeInfo'):
            return {'optionSymbols':[]} if path.startswith('/eapi/') else {'symbols':[]}
        if path.endswith('/positionSide/dual'):return {'dualSidePosition':False}
        if path.endswith('/accountConfig'):return {'canTrade':True,'multiAssetsMargin':False,'api_key':KEY}
        if path=='/api/v3/account':return {'accountType':'SPOT','canTrade':True,'balances':[],'permissions':['SPOT'],'apiKey':KEY,'secret':SECRET}
        if path=='/eapi/v1/marginAccount':return {'asset':[],'greek':[],'canTrade':True,'reduceOnly':False,'apiKey':KEY}
        if path=='/sapi/v1/margin/account':return {'marginLevel':'2','userAssets':[{'asset':'BTC','borrowed':'1','interest':'.01'}]}
        if path=='/sapi/v1/margin/isolated/account':return {'assets':[]}
        if path.startswith('/sapi/v') and path.endswith('/portfolio/account'):
            return {'accountStatus':'NORMAL','uniMMR':'100','accountType':'PM_3' if path.startswith('/sapi/v2') else 'PM_1'}
        if path=='/papi/v1/account':return {'accountStatus':'NORMAL','uniMMR':'100'}
        if path.endswith('/account'):return {'assets':[],'positions':[],'canTrade':True,'apiSecret':SECRET}
        if path.endswith('/order'):
            p=parse_qs(urlparse(req.full_url).query)
            return {'symbol':p['symbol'][0],'orderId':int(p.get('orderId',['1'])[0]),'clientOrderId':p.get('origClientOrderId',['legacy-order'])[0],
                    'status':'FILLED','origQty':'1','executedQty':'1','apiKey':KEY}
        raise AssertionError(path)


def client(id='usdm-demo',private=True,transport=None):
    return DiscoveryExchange(id,DiscoveryCredentials(id,KEY if private else '',SECRET if private else ''),transport=transport or DiscoveryTransport())


class RegistryAndTransportTests(unittest.TestCase):
    def test_registry_has_explicit_boundaries_and_only_legacy_execution_context(self):
        data=inventory();self.assertEqual(len(data['profiles']),16);self.assertEqual(data['execution_contexts'],['usdm-demo'])
        self.assertFalse(data['production_execution_enabled']);self.assertTrue(all(p['discovery_read_only'] for p in data['profiles']))
        with self.assertRaises(ValueError):profile('margin-demo')
        with self.assertRaises(ValueError):profile('https://other.test')
    def test_same_options_um_demo_host_is_not_same_api_or_identity(self):
        a=scoped_identity('usdm-demo',KEY);b=scoped_identity('options-demo',KEY)
        self.assertEqual(a['base_url'],b['base_url']);self.assertNotEqual(a['context_ref'],b['context_ref']);self.assertNotEqual(a['api_family'],b['api_family'])
        self.assertEqual(a['account_ref'],hashlib.sha256(KEY.encode()).hexdigest())
    def test_legacy_credentials_cannot_be_implicitly_used_for_another_product(self):
        with self.assertRaises(ValueError):DiscoveryExchange('spot-testnet',Config(KEY,SECRET))
        with self.assertRaises(ValueError):DiscoveryExchange('options-demo',DiscoveryCredentials('usdm-demo',KEY,SECRET))
        self.assertEqual(DiscoveryExchange('usdm-demo',Config(KEY,SECRET)).identity['account_ref'],hashlib.sha256(KEY.encode()).hexdigest())
    def test_production_or_options_profile_cannot_enter_legacy_execution_adapter(self):
        for id in ('usdm-production','options-demo','coinm-demo','spot-testnet'):
            with self.subTest(id=id),self.assertRaises(ValueError):DemoExchange(DiscoveryCredentials(id,KEY,SECRET))
    def test_all_registered_discovery_adapters_reject_every_write_before_transport(self):
        for id in PROFILES:
            transport=DiscoveryTransport();x=client(id,transport=transport);p=x.profile
            route=next(iter(p.private_reads or p.public_reads),'/sapi/v1/anything')
            for method in ('POST','PUT','DELETE'):
                with self.subTest(id=id,method=method),self.assertRaises(ValueError):x.request(method,route)
            self.assertEqual(transport.calls,[])
    def test_spot_testnet_sapi_and_cross_product_routes_are_forbidden(self):
        transport=DiscoveryTransport();x=client('spot-testnet',transport=transport)
        for path in ('/sapi/v1/margin/account','/sapi/v1/portfolio/account','/fapi/v3/account','https://api.binance.com/api/v3/account'):
            with self.subTest(path=path),self.assertRaises(ValueError):x.get(path)
        self.assertEqual(transport.calls,[])
    def test_binding_is_rechecked_if_credentials_are_replaced(self):
        transport=DiscoveryTransport();x=client(transport=transport);x.credentials=DiscoveryCredentials('options-demo',KEY,SECRET)
        with self.assertRaises(ValueError):x.get('/fapi/v1/time')
        self.assertEqual(transport.calls,[])
    def test_private_signing_uses_own_context_clock_and_fixed_host(self):
        transport=DiscoveryTransport();x=client('spot-testnet',transport=transport)
        with patch('time.time',return_value=1000):x.get('/api/v3/account')
        self.assertEqual(len(transport.calls),2)
        req,method,base=transport.calls[-1];p=parse_qs(urlparse(req.full_url).query)
        self.assertEqual(base,'https://testnet.binance.vision');self.assertEqual(p['timestamp'],['1003000']);self.assertIn('signature',p)
        self.assertEqual(req.get_header('X-mbx-apikey'),KEY);self.assertEqual(method,'GET')
        self.assertEqual(transport.calls[0][0].headers,{})
    def test_no_arbitrary_signing_parameter_override(self):
        transport=DiscoveryTransport();x=client(transport=transport)
        for params in ({'timestamp':1},{'recvWindow':1},{'signature':'x'},{'symbol':'BTCUSDT'}):
            with self.subTest(params=params),self.assertRaises(ValueError):x.get('/fapi/v3/account',params)
        self.assertEqual(transport.calls,[])
    def test_missing_private_credentials_do_not_send_or_try_other_profile(self):
        transport=DiscoveryTransport();x=client('coinm-demo',False,transport)
        with self.assertRaises(ExchangeError):x.get('/dapi/v1/account')
        self.assertEqual(transport.calls,[])
    def test_pm_does_not_guess_a_server_time_endpoint(self):
        transport=DiscoveryTransport();x=client('portfolio-margin-production',transport=transport);x.get('/papi/v1/account')
        self.assertEqual(len(transport.calls),1);self.assertEqual(x.sync_time()['clock_source'],'LOCAL_UNVERIFIED')


class CredentialProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.file=Path(self.temp.name)/'profiles.env'
    def test_legacy_config_loading_stays_demo_and_never_exposes_secret_repr(self):
        self.file.write_text('BINANCE_DEMO_API_KEY='+KEY+'\nBINANCE_DEMO_API_SECRET='+SECRET+'\n',encoding='utf-8')
        with patch.dict(os.environ,{},clear=True):
            old=Config.load(self.file);new=Config.load_for_discovery('usdm-demo',self.file)
        self.assertEqual(old.api_key,new.api_key);self.assertNotIn(KEY,repr(old));self.assertNotIn(SECRET,repr(new));self.assertNotIn(KEY,repr(new))
    def test_product_profile_never_falls_back_to_legacy_or_other_environment_key(self):
        self.file.write_text('BINANCE_DEMO_API_KEY='+KEY+'\nBINANCE_DEMO_API_SECRET='+SECRET+'\n',encoding='utf-8')
        with patch.dict(os.environ,{},clear=True):x=Config.load_for_discovery('spot-testnet',self.file)
        self.assertEqual(x.api_key,'');self.assertEqual(x.api_secret,'')
    def test_explicit_production_read_profile_does_not_enable_default_live_config(self):
        env={'AGENTRADER_ENV':'live','BINANCE_USDM_PRODUCTION_API_KEY':KEY,'BINANCE_USDM_PRODUCTION_API_SECRET':SECRET}
        with patch.dict(os.environ,env,clear=True):
            with self.assertRaises(ValueError):Config.load(self.file)
            bound=Config.load_for_discovery('usdm-production',self.file)
        self.assertEqual(bound.context_id,'usdm-production')
        with self.assertRaises(ValueError):DemoExchange(bound)
    def test_key_secret_pair_is_context_specific_and_mandatory(self):
        with patch.dict(os.environ,{'BINANCE_SPOT_TESTNET_API_KEY':KEY},clear=True),self.assertRaises(ValueError):Config.load_for_discovery('spot-testnet',self.file)


class AccountDiscoveryTests(unittest.TestCase):
    def test_all_implemented_models_have_read_only_probe_outcomes_without_secret_data(self):
        for id,p in PROFILES.items():
            with self.subTest(id=id):
                transport=DiscoveryTransport();report=probe(client(id,transport=transport),include_private=True)
                self.assertEqual(report['status'],'READ_COMPLETE' if p.private_reads else 'DISCOVERY_NOT_IMPLEMENTED',report)
                self.assertEqual(report['write_permission'],'NOT_VERIFIED');self.assertFalse(report['financial_execution_authorized'])
                self.assertNotIn(KEY,json.dumps(report));self.assertNotIn(SECRET,json.dumps(report))
                self.assertTrue(all(m=='GET' and b==p.base_url for _,m,b in transport.calls))
    def test_can_trade_flag_does_not_become_write_permission_or_execution_authority(self):
        report=probe(client(),include_private=True)
        self.assertTrue(report['permissions']['can_trade_flag']);self.assertEqual(report['permissions']['write_permission'],'NOT_VERIFIED')
        self.assertFalse(report['financial_execution_authorized']);self.assertEqual(report['product_eligibility'],'SCHEMA_OBSERVED_ONLY')
    def test_options_403_remains_unknown_access_not_unsupported_product(self):
        t=DiscoveryTransport();t.errors['/eapi/v1/time']=ExchangeError('SECRET_CANARY',http_status=403)
        report=probe(client('options-demo',transport=t),include_private=True)
        self.assertEqual(report['status'],'INCOMPLETE');self.assertEqual(report['product_eligibility'],'UNPROVEN')
        self.assertEqual(report['checks'][0]['status'],'ACCESS_BLOCKED');self.assertNotIn('SECRET_CANARY',json.dumps(report));self.assertEqual(len(t.calls),1)
    def test_wrong_product_api_key_error_does_not_fall_back_to_another_host(self):
        t=DiscoveryTransport();t.errors['/dapi/v1/account']=ExchangeError('SECRET_CANARY',-2015,401)
        report=probe(client('coinm-demo',transport=t),include_private=True)
        self.assertEqual(report['permissions']['private_read'],'UNPROVEN');self.assertEqual(report['checks'][-1]['status'],'SKIPPED_AFTER_PRIVATE_ERROR')
        self.assertTrue(all(b=='https://demo-dapi.binance.com' for _,_,b in t.calls))
    def test_pm_pro_and_span_preserve_versioned_labels_without_linear_risk_claim(self):
        pro=probe(client('portfolio-margin-pro-production'),include_private=True)
        span=probe(client('portfolio-margin-span-production'),include_private=True)
        self.assertEqual(pro['checks'][-1]['summary']['account_model_match'],'VERSIONED_LABEL_UNPROVEN')
        self.assertEqual(span['checks'][-1]['summary']['reported_account_type'],'PM_3')
        self.assertNotEqual(pro['identity']['context_ref'],span['identity']['context_ref']);self.assertFalse(span['financial_execution_authorized'])
    def test_model_mismatch_or_malformed_flag_never_proves_eligibility(self):
        t=DiscoveryTransport();t.responses['/api/v3/account']={'accountType':'MARGIN','canTrade':True,'balances':[]}
        report=probe(client('spot-testnet',transport=t),include_private=True);self.assertEqual(report['status'],'INCOMPLETE');self.assertEqual(report['checks'][-1]['status'],'MODEL_MISMATCH')
        t.responses['/api/v3/account']={'accountType':'SPOT','canTrade':'true','balances':[]}
        report=probe(client('spot-testnet',transport=t),include_private=True);self.assertEqual(report['checks'][-1]['status'],'SCHEMA_OR_CONTEXT_UNPROVEN')
    def test_readable_but_restricted_account_is_not_declared_tradeable(self):
        t=DiscoveryTransport();t.responses['/api/v3/account']={'accountType':'SPOT','canTrade':False,'balances':[]}
        report=probe(client('spot-testnet',transport=t),include_private=True)
        self.assertEqual(report['status'],'READ_COMPLETE');self.assertFalse(report['permissions']['can_trade_flag']);self.assertEqual(report['product_eligibility'],'ACCOUNT_FLAG_RESTRICTED')
    def test_testnet_reset_missing_order_is_not_rejection_or_ledger_mutation(self):
        t=DiscoveryTransport();t.errors['/api/v3/order']=ExchangeError('missing',-2013,400)
        report=lookup_order(client('spot-testnet',transport=t),'BTCUSDT',order_id=42)
        self.assertEqual(report['status'],'ORDER_NOT_OBSERVED');self.assertFalse(report['absence_is_rejection']);self.assertTrue(report['reset_possible']);self.assertFalse(report['accounting_adopted'])
    def test_lookup_normal_namespace_and_identity_are_verified(self):
        report=lookup_order(client('usdm-demo'),'BTCUSDT',client_order_id='legacy-order')
        self.assertEqual(report['status'],'ORDER_OBSERVED');self.assertEqual(report['namespace'],'NORMAL')
        t=DiscoveryTransport();t.responses['/fapi/v1/order']={'symbol':'ETHUSDT','orderId':42,'status':'FILLED'}
        self.assertEqual(lookup_order(client(transport=t),'BTCUSDT',order_id=42)['status'],'ORDER_IDENTITY_UNPROVEN')
    def test_inconsistent_futures_can_trade_flags_are_not_combined_as_success(self):
        t=DiscoveryTransport();t.responses['/fapi/v1/accountConfig']={'canTrade':False,'multiAssetsMargin':False}
        report=probe(client(transport=t),include_private=True)
        self.assertEqual(report['status'],'INCOMPLETE');self.assertIsNone(report['permissions']['can_trade_flag']);self.assertEqual(report['product_eligibility'],'UNPROVEN')
    def test_unrecognized_account_labels_do_not_echo_credentials(self):
        t=DiscoveryTransport();t.responses['/api/v3/account']={'accountType':KEY,'canTrade':True,'balances':[],'permissions':['SPOT',SECRET]}
        report=probe(client('spot-testnet',transport=t),include_private=True)
        self.assertNotIn(KEY,json.dumps(report));self.assertNotIn(SECRET,json.dumps(report))
        self.assertEqual(report['checks'][-1]['summary']['unrecognized_permission_count'],1)


class DiscoveryStorageAndCliTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.cache=DiscoveryStore(self.root/'discovery.db')
    def tearDown(self):self.cache.close();self.temp.cleanup()
    def test_cache_partitions_demo_production_account_and_same_host_products(self):
        x=client();r=probe(x,include_private=True);self.cache.save(r)
        self.assertEqual(self.cache.latest(x.evidence_identity(True))['evidence_status'],'FRESH')
        for context,key in [('usdm-production',KEY),('options-demo',KEY),('usdm-demo','OTHER_KEY')]:
            other=scoped_identity(context,key,access='PRIVATE')
            self.assertEqual(self.cache.latest(other)['evidence_status'],'NOT_FOUND')
        self.assertEqual(self.cache.latest(x.evidence_identity(False))['evidence_status'],'NOT_FOUND')
    def test_private_missing_credentials_and_public_evidence_have_separate_scopes(self):
        x=client(private=False);r=probe(x,include_private=True);self.cache.save(r)
        self.assertNotEqual(x.evidence_identity(True)['context_ref'],x.evidence_identity(False)['context_ref'])
        self.assertEqual(self.cache.latest(x.evidence_identity(False))['evidence_status'],'NOT_FOUND')
    def test_cache_is_an_immutable_observation_not_a_trading_permission(self):
        x=client();r=probe(x,include_private=True);self.assertTrue(self.cache.save(r));self.assertFalse(self.cache.save(r))
        modified=copy.deepcopy(r);modified['status']='INCOMPLETE'
        with self.assertRaises(ValueError):self.cache.save(modified)
        modified['financial_execution_authorized']=True
        with self.assertRaises(ValueError):self.cache.save(modified)
        old=self.cache.latest(x.evidence_identity(True),now_ms=r['observed_ms']+301000)
        self.assertEqual(old['evidence_status'],'STALE');self.assertFalse(old['financial_execution_authorized'])
    def test_corrupt_cache_cannot_be_loaded_as_fresh_evidence(self):
        x=client();self.cache.save(probe(x,include_private=True))
        with self.cache.db:self.cache.db.execute("UPDATE discovery_runs SET digest='bad'")
        self.assertEqual(self.cache.latest(x.evidence_identity(True))['evidence_status'],'CORRUPT')
    def test_discovery_database_cannot_be_used_for_execution_or_candles(self):
        file=self.cache.path
        for opener in (StateStore,CandleStore):
            with self.subTest(opener=opener),self.assertRaises(ValueError):opener(file)
        self.assertNotIn('intents',{r[0] for r in self.cache.db.execute("SELECT name FROM sqlite_master WHERE type='table'")})
    def test_execution_market_and_application_databases_are_not_discovery_caches(self):
        execution=StateStore(self.root/'execution.db');execution.close()
        market=CandleStore(self.root/'market.db');market.close()
        app=self.root/'app.db'
        with closing(sqlite3.connect(app)) as db,db:db.execute('CREATE TABLE app_market_context (body TEXT)')
        for path in (self.root/'execution.db',self.root/'market.db',app):
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.subTest(path=path),self.assertRaises(ValueError):DiscoveryStore(path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
    def test_legacy_execution_migration_preserves_account_refs_commands_and_owner(self):
        path=self.root/'legacy.db';store=StateStore(path)
        cfg=Config(KEY,SECRET);service=AccountCommands(DemoExchange(cfg),store,'owner');prepared=service.prepare('LEVERAGE',20,'BTCUSDT')
        store.reserve('legacy-order','/fapi/v1/order',{'symbol':'BTCUSDT','quantity':'.001'})
        store.save_session({'id':'old-session','active':False,'account_ref':hashlib.sha256(KEY.encode()).hexdigest()})
        def snapshot(s):return {name:[tuple(row) for row in s.db.execute('SELECT * FROM '+name)] for name in ('intents','control','account_commands','managed_sessions')}
        before=snapshot(store)
        with store.db:store.db.execute('DROP TABLE execution_namespace')
        store.close()
        with self.assertRaisesRegex(ValueError, 'CONTEXT_UNVERIFIED'):
            StateStore(path)
        from agentrader.shared.legacy_execution import attest
        review = attest(path, 'owner', hashlib.sha256(KEY.encode()).hexdigest(), context='usdm-demo')
        self.assertFalse(review['applied'])
        applied = attest(path, 'owner', hashlib.sha256(KEY.encode()).hexdigest(), context='usdm-demo', apply=True)
        self.assertTrue(Path(applied['backup']).is_file())
        store=StateStore(path)
        try:
            self.assertEqual(snapshot(store),before);self.assertEqual(json.loads(store.db.execute('SELECT body FROM execution_namespace').fetchone()[0]),EXECUTION_CONTEXT)
            row=AccountCommands(DemoExchange(cfg),store,'owner').row(prepared['command_id'])[0]
            self.assertEqual(row['digest'],prepared['digest'])
            self.assertEqual(ExchangeCommands(DemoExchange(cfg),store,'owner').account_ref,hashlib.sha256(KEY.encode()).hexdigest())
        finally:store.close()
    def test_production_marker_in_execution_journal_is_rejected_unchanged(self):
        path=self.root/'wrong.db';store=StateStore(path)
        with store.db:store.db.execute('UPDATE execution_namespace SET body=?',(json.dumps(EXECUTION_CONTEXT|{'environment':'production'}),))
        store.close();before=hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):StateStore(path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
    def test_cli_list_and_public_probe_do_not_load_credentials(self):
        from agentrader.cli.discovery_cli import main
        t=DiscoveryTransport();factory=lambda context,credentials:DiscoveryExchange(context,credentials,transport=t)
        with patch('agentrader.cli.discovery_cli.Config.load_for_discovery',side_effect=AssertionError('No credentials')),patch('agentrader.cli.discovery_cli.DiscoveryExchange',side_effect=factory):
            out=io.StringIO()
            with redirect_stdout(out):self.assertEqual(main(['list']),0)
            self.assertEqual(t.calls,[])
            with redirect_stdout(io.StringIO()):self.assertEqual(main(['probe','--context','spot-testnet','--database',str(self.root/'cli.db')]),0)
        self.assertTrue(all(not req.headers for req,_,_ in t.calls))
    def test_cli_private_probe_latest_and_missing_order_are_read_only(self):
        from agentrader.cli.discovery_cli import main
        t=DiscoveryTransport();factory=lambda context,credentials:DiscoveryExchange(context,credentials,transport=t)
        file=str(self.root/'cli.db')
        with patch('agentrader.cli.discovery_cli.Config.load_for_discovery',return_value=DiscoveryCredentials('spot-testnet',KEY,SECRET)),patch('agentrader.cli.discovery_cli.DiscoveryExchange',side_effect=factory):
            out=io.StringIO()
            with redirect_stdout(out):self.assertEqual(main(['probe','--context','spot-testnet','--private','--database',file]),0)
            before=len(t.calls)
            with redirect_stdout(io.StringIO()):self.assertEqual(main(['latest','--context','spot-testnet','--private','--database',file]),0)
            self.assertEqual(len(t.calls),before)
            t.errors['/api/v3/order']=ExchangeError('SECRET_CANARY',-2013,400)
            with redirect_stdout(out):self.assertEqual(main(['lookup-order','--context','spot-testnet','--private','--symbol','BTCUSDT','--order-id','1','--database',file]),1)
        self.assertNotIn(KEY,out.getvalue());self.assertNotIn(SECRET,out.getvalue());self.assertNotIn('SECRET_CANARY',out.getvalue())
        self.assertTrue(all(method=='GET' for _,method,_ in t.calls))
    def test_fresh_cached_access_failure_is_not_cli_success(self):
        from agentrader.cli.discovery_cli import main
        x=client('options-demo');x.transport.errors['/eapi/v1/time']=ExchangeError('blocked',http_status=403)
        self.cache.save(probe(x,include_private=True))
        with patch('agentrader.cli.discovery_cli.Config.load_for_discovery',return_value=x.credentials),patch('agentrader.cli.discovery_cli.DiscoveryExchange',return_value=x),redirect_stdout(io.StringIO()):
            self.assertEqual(main(['latest','--context','options-demo','--private','--database',str(self.cache.path)]),1)
