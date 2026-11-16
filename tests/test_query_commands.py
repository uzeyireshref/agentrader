import copy
import io
import json
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock,patch
from urllib.parse import urlparse,parse_qs

from agentrader.bot.exchange_commands import ExchangeCommands,validate_command
from agentrader.bot.query_history import collect,POLICIES,DAY
from agentrader.shared.config import Config
from agentrader.shared.exchange import DemoExchange,ExchangeError,allowed_requests
from agentrader.shared.market_data import PublicMarket
from agentrader.shared.query_routes import QUERIES,HISTORY_PATHS,EXPORT_PATHS
from agentrader.shared.state import StateStore
from agentrader.shared.transport import JsonTransport


class QueryExchange:
    config=Config('g10-test-key','g10-test-secret');offset_ms=0
    def __init__(self):
        self.calls=[];self.fail=None;self.responses={};self.rows=[];self.hook=None;self.lost_export=False
        self.export_status='processing';self.export_expiry=int(time.time()*1000)+60000;self.export_url='https://files.example.test/export.csv?token=owned-result'
    def sync_time(self):pass
    def get(self,path,params=None):
        params=copy.deepcopy(params or {});self.calls.append(('GET',path,params))
        if self.hook:self.hook(path,params)
        if path==self.fail:raise ExchangeError('SECRET_CANARY',-2013,400)
        if path in self.responses:return copy.deepcopy(self.responses[path])
        if path in EXPORT_PATHS.values():
            if self.lost_export:raise ExchangeError('SECRET_CANARY lost',delivery_status='READ_FAILED')
            return {'downloadId':'same-id','avgCostTimestampOfLast30d':10}
        if path.endswith('/asyn/id'):return {'downloadId':params['downloadId'],'status':self.export_status,'url':self.export_url,'expirationTimestamp':self.export_expiry}
        if path in HISTORY_PATHS.values():
            kind=next(k for k,v in HISTORY_PATHS.items() if v==path);policy=POLICIES[kind];rows=self.rows
            if 'symbol' in params:rows=[r for r in rows if r.get('symbol')==params['symbol']]
            if 'fromId' in params:rows=[r for r in rows if r['id']>=params['fromId']]
            else:rows=[r for r in rows if params['startTime']<=r[policy['time']]<=params['endTime']]
            cursor=policy.get('cursor')
            if cursor and cursor in params:rows=sorted((r for r in rows if r[policy['id']]>=params[cursor]),key=lambda r:r[policy['id']])
            elif kind in ('ORDERS','ALGO_ORDERS'):rows=rows[-params['limit']:]
            return copy.deepcopy(rows[:params['limit']])
        spec=next(s for s in QUERIES.values() if s['path']==path)
        if spec['shape'] in ('list','candles'):return []
        if path.endswith('/ping'):return {}
        if path.endswith('/account'):return {'assets':[],'positions':[]}
        if path.endswith('/exchangeInfo'):return {'symbols':[],'assets':[]}
        if path.endswith('/apiTradingStatus'):return {'indicators':{}}
        if path.endswith('/accountConfig'):return {'canTrade':True,'multiAssetsMargin':False}
        if path.endswith('/leverageBracket'):return {'symbol':params.get('symbol','BTCUSDT'),'brackets':[{'notionalFloor':0,'notionalCap':10000,'initialLeverage':50,'maintMarginRatio':'.004','cum':0}]}
        if path.endswith(('/depth','/rpiDepth')):return {'lastUpdateId':1,'bids':[['100','.5']],'asks':[['101','.4']]}
        if path.endswith('/positionSide/dual'):return {'dualSidePosition':False}
        if path.endswith('/multiAssetsMargin'):return {'multiAssetsMargin':False}
        if path.endswith('/feeBurn'):return {'feeBurn':False}
        if path.endswith('/openOrder'):return {'symbol':params['symbol'],'orderId':params.get('orderId',1),'clientOrderId':params.get('origClientOrderId','manual')}
        if path.endswith('/algoOrder'):return {'symbol':params['symbol'],'algoId':params.get('algoId',1),'clientAlgoId':params.get('clientAlgoId','manual-algo')}
        field=next(iter(sorted(spec['fields'])))
        return {field:1,'symbol':params.get('symbol','BTCUSDT')}
    def request(self,*a):raise AssertionError('No financial mutation is allowed')


def order(i,stamp=10,algo=False):
    if algo:return dict(symbol='BTCUSDT',algoId=i+1,clientAlgoId='algo-'+str(i),side='SELL',createTime=stamp,algoStatus='FINISHED',actualOrderId=i+10000)
    return dict(symbol='BTCUSDT',orderId=i+1,clientOrderId='order-'+str(i),side='BUY',time=stamp,origQty='.001',executedQty='.001',status='FILLED')


class HistoryCollectorTests(unittest.TestCase):
    def test_dense_single_millisecond_normal_orders_use_identity_cursor_from_zero(self):
        x=QueryExchange();x.rows=[order(i) for i in range(2501)]
        r=collect(x,'ORDERS','BTCUSDT',10,10,now_ms=20,page_size=1000,max_requests=20)
        self.assertTrue(r['complete'],r);self.assertEqual(r['record_count'],2501)
        self.assertTrue(any(p.get('orderId')==0 for _,_,p in x.calls))
    def test_algo_parent_and_normal_child_namespace_are_not_collapsed(self):
        x=QueryExchange();x.rows=[order(i,algo=True) for i in range(1001)]
        r=collect(x,'ALGO_ORDERS','BTCUSDT',10,10,now_ms=20,page_size=1000,max_requests=20)
        self.assertTrue(r['pagination_complete']);self.assertFalse(r['complete']);self.assertEqual(r['namespace'],'ALGO')
        self.assertEqual(r['record_count'],1001);self.assertIn('actualOrderId',r['records'][0])
    def test_force_order_saturated_millisecond_is_not_claimed_complete(self):
        x=QueryExchange();x.rows=[order(i) for i in range(101)]
        r=collect(x,'FORCE_ORDERS','BTCUSDT',10,10,now_ms=20,page_size=100,max_requests=20)
        self.assertFalse(r['complete']);self.assertEqual(r['reason'],'SATURATED_MILLISECOND_WITHOUT_CURSOR')
    def test_income_time_bisection_preserves_boundaries_and_type_scoped_ids(self):
        x=QueryExchange();x.rows=[dict(tranId=i,time=i//2,incomeType='COMMISSION',asset='USDT',income='-.1') for i in range(21)]
        x.rows.append(dict(tranId=1,time=1,incomeType='REALIZED_PNL',asset='USDT',income='1'))
        r=collect(x,'INCOME',None,0,10,now_ms=20,page_size=5,max_requests=100)
        self.assertTrue(r['complete'],r);self.assertEqual(r['record_count'],22)
    def test_history_inserted_between_sweeps_invalidates_completeness(self):
        x=QueryExchange();x.rows=[order(1)];calls=[0]
        def change(path,p):
            calls[0]+=1
            if calls[0]==2:x.rows.append(order(2))
        x.hook=change;r=collect(x,'ORDERS','BTCUSDT',0,20,now_ms=20,page_size=10,max_requests=10)
        self.assertFalse(r['complete']);self.assertEqual(r['reason'],'HISTORY_CHANGED_DURING_COLLECTION')
    def test_request_budget_is_global_and_never_returns_complete_prefix(self):
        x=QueryExchange();x.rows=[order(i,i) for i in range(50)]
        r=collect(x,'ORDERS','BTCUSDT',0,49,now_ms=50,page_size=5,max_requests=2)
        self.assertFalse(r['complete']);self.assertEqual(r['requests'],2);self.assertEqual(r['reason'],'REQUEST_BUDGET_EXHAUSTED')
    def test_old_normal_order_window_cannot_prove_deleted_zero_fill_orders(self):
        x=QueryExchange();r=collect(x,'ORDERS','BTCUSDT',0,1,now_ms=3*DAY,page_size=1000,max_requests=10)
        self.assertFalse(r['complete']);self.assertEqual(r['reason'],'RETENTION_GAP');self.assertEqual(x.calls,[])
    def test_trade_history_chunks_keep_id_continuation_and_frozen_end(self):
        x=QueryExchange();x.rows=[dict(symbol='BTCUSDT',id=i,orderId=1,side='BUY',qty='.001',time=10) for i in range(1001)]
        x.rows.extend([dict(symbol='BTCUSDT',id=1001,orderId=2,side='BUY',qty='.001',time=7*DAY+1),dict(symbol='BTCUSDT',id=1002,orderId=3,side='BUY',qty='.001',time=8*DAY+1)])
        r=collect(x,'TRADES','BTCUSDT',0,8*DAY,now_ms=8*DAY,page_size=1000,max_requests=20)
        self.assertTrue(r['complete'],r);self.assertEqual(r['record_count'],1002)
        self.assertTrue(all('fromId' not in p or not {'startTime','endTime'}&p.keys() for _,_,p in x.calls))
    def test_identical_margin_events_are_preserved_as_multiplicity_not_deduplicated(self):
        x=QueryExchange();row=dict(symbol='BTCUSDT',positionSide='BOTH',type=1,time=10,amount='10',asset='USDT')
        x.rows=[row,dict(row)]
        r=collect(x,'POSITION_MARGIN','BTCUSDT',0,20,now_ms=20,page_size=10,max_requests=10)
        self.assertEqual(r['record_count'],2);self.assertFalse(r['complete']);self.assertTrue(r['pagination_complete'])
    def test_trade_record_budget_stops_inside_id_pagination(self):
        x=QueryExchange();x.rows=[dict(symbol='BTCUSDT',id=i,orderId=1,side='BUY',qty='.001',time=10) for i in range(10)]
        with patch('agentrader.bot.query_history.MAX_RECORDS',3):
            r=collect(x,'TRADES','BTCUSDT',0,20,now_ms=20,page_size=2,max_requests=10)
        self.assertFalse(r['complete']);self.assertEqual(r['reason'],'HISTORY_RECORD_BUDGET_EXHAUSTED');self.assertEqual(r['requests'],2)
    def test_inclusive_amendment_windows_handle_more_than_one_page(self):
        x=QueryExchange();x.rows=[dict(symbol='BTCUSDT',orderId=1,clientOrderId='manual',amendmentId=i,time=i,
            amendment={'modifyId':i,'price':{'before':'100','after':'99'},'origQty':{'before':'1','after':'.9'}}) for i in range(250)]
        r=collect(x,'AMENDMENTS','BTCUSDT',0,249,now_ms=250,page_size=100,max_requests=50,selector={'orderId':1})
        self.assertTrue(r['complete'],r);self.assertEqual(r['record_count'],250)
    def test_conflicting_identity_and_bad_timestamp_do_not_complete(self):
        x=QueryExchange();x.rows=[order(1),order(1)|{'executedQty':'0'}]
        self.assertFalse(collect(x,'ORDERS','BTCUSDT',0,20,now_ms=20,page_size=10,max_requests=10)['complete'])
        x.responses[HISTORY_PATHS['ORDERS']]=[order(1,99)]
        self.assertFalse(collect(x,'ORDERS','BTCUSDT',0,20,now_ms=20,page_size=10,max_requests=10)['complete'])


class QueryCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.db';self.store=StateStore(self.path)
        self.x=QueryExchange();self.owner='local:g10';self.commands=ExchangeCommands(self.x,self.store,self.owner)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def request(self,operation='PRIVATE_QUERY',key='query',parameters=None,scope=None):
        return dict(schema_version=1,client_command_id=key,environment='demo',exchange='binance',product='USD-M',account_ref=self.commands.account_ref,
                    operation=operation,scope=scope or {'account_wide':True},parameters=parameters or {'query':'BALANCE_V3','arguments':{}})
    def execute(self,r):
        p=self.commands.prepare(r);return p,self.commands.apply(p['command_id'],p['digest'],execute=r['operation']=='CREATE_HISTORY_EXPORT')
    def export(self,kind='ORDERS',key='export'):
        now=int(time.time()*1000);return self.request('CREATE_HISTORY_EXPORT',key,dict(kind=kind,start_ms=now-10000,end_ms=now-1000))
    def test_prepare_is_local_read_results_are_projected_and_duplicates_are_not_refetched(self):
        self.x.responses['/fapi/v3/balance']=[{'asset':'USDT','availableBalance':'10.000000000000001','api_key':'SECRET_CANARY','secret':'SECRET_CANARY'}]
        p=self.commands.prepare(self.request());self.assertEqual(self.x.calls,[])
        r=self.commands.apply(p['command_id'],p['digest']);self.assertEqual(r['state'],'APPLIED');self.assertNotIn('SECRET_CANARY',json.dumps(r))
        self.assertEqual(r['result']['data'][0]['availableBalance'],'10.000000000000001')
        self.commands.apply(p['command_id'],p['digest']);self.assertEqual(len(self.x.calls),1)
    def test_all_named_contracts_have_normal_command_entry_and_only_allowed_get_routes(self):
        self.assertEqual(len(QUERIES),53)
        for name,spec in QUERIES.items():
            values={k:('1m' if k=='interval' else '5m' if k=='period' else 'PERPETUAL') for k in spec['required']}
            if name=='OPEN_ORDER':values={'orderId':1}
            if name=='ALGO_ORDER':values={'algoId':1}
            scope={'symbol':'BTCUSDT'} if spec['scope'] in ('SYMBOL','PAIR') else {'account_wide':True} if spec['private'] else {'market_wide':True}
            with self.subTest(name=name):
                self.assertIn(('GET',spec['path']),allowed_requests())
                _,r=self.execute(self.request('PRIVATE_QUERY' if spec['private'] else 'PUBLIC_QUERY',name,{'query':name,'arguments':values},scope))
                self.assertEqual(r['state'],'APPLIED',r)
        self.assertEqual(self.store.intents(),[])
    def test_arbitrary_path_signing_fields_and_scope_escape_are_rejected(self):
        for args in ({'url':'https://evil.test'},{'timestamp':1},{'recvWindow':999999},{'symbol':'ETHUSDT'},{'signature':'secret'}):
            r=self.request(parameters={'query':'BALANCE_V3','arguments':args})
            with self.subTest(args=args),self.assertRaises(ValueError):self.commands.prepare(r)
        r=self.request('PUBLIC_QUERY',parameters={'query':'BALANCE_V3','arguments':{}})
        with self.assertRaises(ValueError):self.commands.prepare(r)
        self.assertEqual(self.x.calls,[])
    def test_absent_order_read_does_not_reject_existing_intent_or_release_halt(self):
        self.store.reserve('manual','/fapi/v1/order',{'symbol':'BTCUSDT'});self.store.halt('keep')
        self.x.fail='/fapi/v1/openOrder';_,r=self.execute(self.request(parameters={'query':'OPEN_ORDER','arguments':{'orderId':1}},scope={'symbol':'BTCUSDT'}))
        self.assertEqual(r['state'],'READ_FAILED');self.assertFalse(r['result']['absence_is_rejection'])
        self.assertEqual(self.store.intent('manual')['state'],'SUBMITTING');self.assertEqual(self.store.halt_reason(),'keep');self.assertNotIn('SECRET_CANARY',json.dumps(r))
    def test_wrong_normal_or_algo_identity_is_not_a_successful_read(self):
        for name,path,idfield in [('OPEN_ORDER','/fapi/v1/openOrder','orderId'),('ALGO_ORDER','/fapi/v1/algoOrder','algoId')]:
            self.x.responses[path]={'symbol':'BTCUSDT',idfield:2}
            _,r=self.execute(self.request(key=name,parameters={'query':name,'arguments':{idfield:1}},scope={'symbol':'BTCUSDT'}))
            self.assertEqual(r['state'],'READ_FAILED')
    def test_account_wide_positions_and_open_orders_preserve_multiple_symbols(self):
        self.x.responses['/fapi/v3/positionRisk']=[{'symbol':s,'positionAmt':'.001','positionSide':'BOTH'} for s in ('BTCUSDT','ETHUSDT')]
        _,r=self.execute(self.request(parameters={'query':'POSITIONS_V3','arguments':{}}));self.assertEqual(r['state'],'APPLIED')
        self.assertEqual(len(r['result']['data']),2);self.assertNotIn('symbol',self.x.calls[-1][2])
        self.x.responses['/fapi/v1/openOrders']=[dict(order(i),symbol=s) for i,s in enumerate(('BTCUSDT','ETHUSDT'))]
        _,r=self.execute(self.request(key='all-orders',parameters={'query':'OPEN_ORDERS','arguments':{}}));self.assertEqual(r['state'],'APPLIED')
        self.assertEqual(len(r['result']['data']),2);self.assertEqual(self.store.intents(),[])
    def test_optional_symbol_scope_cannot_be_widened_by_arguments(self):
        request=self.request(parameters={'query':'POSITIONS_V3','arguments':{'symbol':'ETHUSDT'}},scope={'symbol':'BTCUSDT'})
        with self.assertRaises(ValueError):self.commands.prepare(request)
    def test_history_reports_completeness_and_durable_page_hashes(self):
        now=int(time.time()*1000);self.x.rows=[order(1,now-100)]
        p,r=self.execute(self.request('QUERY_HISTORY',parameters=dict(kind='ORDERS',start_ms=now-1000,end_ms=now-1,page_size=1000,max_requests=10),scope={'symbol':'BTCUSDT'}))
        self.assertEqual(r['state'],'APPLIED',r);self.assertTrue(r['result']['complete']);self.assertFalse(r['result']['accounting_adopted'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM exchange_read_pages').fetchone()[0],2)
        self.assertEqual(self.store.intents(),[])
    def test_old_missing_history_remains_incomplete_even_when_empty(self):
        now=int(time.time()*1000)
        _,r=self.execute(self.request('QUERY_HISTORY',parameters=dict(kind='ORDERS',start_ms=now-4*DAY,end_ms=now-3*DAY,page_size=1000,max_requests=10),scope={'symbol':'BTCUSDT'}))
        self.assertEqual(r['state'],'READ_FAILED');self.assertEqual(r['result']['reason'],'RETENTION_GAP');self.assertFalse(r['result']['complete']);self.assertEqual(self.x.calls,[])
    def test_each_history_family_through_common_command_preserves_values_and_namespace(self):
        now=int(time.time()*1000);stamp=now-100
        samples={'ORDERS':order(1,stamp),'ALGO_ORDERS':order(1,stamp,True),
            'TRADES':dict(symbol='BTCUSDT',id=1,orderId=2,side='BUY',qty='.001',time=stamp),
            'INCOME':dict(incomeType='COMMISSION',tranId=1,asset='USDT',income='-.01',time=stamp),
            'AMENDMENTS':dict(symbol='BTCUSDT',orderId=1,clientOrderId='manual',amendmentId=1,time=stamp,
                amendment={'modifyId':1,'price':{'before':'100','after':'99'},'origQty':{'before':'1','after':'.9'}}),
            'FORCE_ORDERS':order(1,stamp),
            'POSITION_MARGIN':dict(symbol='BTCUSDT',positionSide='BOTH',type=1,amount='10',asset='USDT',time=stamp)}
        for kind,row in samples.items():
            self.x.rows=[row];p=dict(kind=kind,start_ms=now-1000,end_ms=now-1,page_size=POLICIES[kind]['limit'],max_requests=10)
            if kind=='AMENDMENTS':p['order_id']=1
            scope={'account_wide':True} if kind=='INCOME' else {'symbol':'BTCUSDT'}
            with self.subTest(kind=kind):
                _,r=self.execute(self.request('QUERY_HISTORY',kind,p,scope))
                self.assertEqual(r['state'],'READ_FAILED' if kind in ('ALGO_ORDERS','POSITION_MARGIN') else 'APPLIED',r)
                self.assertEqual(r['result']['namespace'],POLICIES[kind]['namespace']);self.assertEqual(r['result']['record_count'],1)
                if kind=='AMENDMENTS':self.assertEqual(r['result']['records'][0]['amendment']['origQty'],{'before':'1','after':'.9'})
    def test_explicit_reconcile_can_retry_failed_read_without_any_financial_mutation(self):
        self.x.fail='/fapi/v3/balance';p,r=self.execute(self.request());self.assertEqual(r['state'],'READ_FAILED')
        self.x.fail=None;self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'APPLIED')
        self.assertTrue(all(m=='GET' for m,_,_ in self.x.calls))
    def test_export_job_creation_requires_explicit_gate_and_stable_duplicate_identity(self):
        p=self.commands.prepare(self.export())
        with self.assertRaises(ValueError):self.commands.apply(p['command_id'],p['digest'])
        r=self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(r['state'],'APPLIED');self.assertFalse(r['result']['complete'])
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(len(self.x.calls),1)
    def test_export_lost_response_never_creates_second_job_after_restart(self):
        self.x.lost_export=True;p,r=self.execute(self.export());self.assertEqual(r['state'],'UNKNOWN')
        self.store.close();self.store=StateStore(self.path);self.commands=ExchangeCommands(self.x,self.store,self.owner)
        self.commands.reconcile(p['command_id']);self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(len(self.x.calls),1)
    def test_export_processing_ready_expiry_are_separate_from_file_completeness(self):
        p,_=self.execute(self.export());request=self.request('QUERY_HISTORY_EXPORT','poll',{'source_command_id':p['command_id']})
        _,r=self.execute(request);self.assertEqual(r['result']['status'],'PROCESSING');self.assertNotIn('download_url',r['result'])
        self.x.export_status='completed';request['client_command_id']='ready';_,r=self.execute(request)
        self.assertEqual(r['result']['status'],'READY');self.assertFalse(r['result']['file_downloaded']);self.assertFalse(r['result']['complete'])
        self.x.export_expiry=1;request['client_command_id']='expired';_,r=self.execute(request);self.assertEqual(r['state'],'READ_FAILED');self.assertEqual(r['result']['status'],'EXPIRED')
        self.assertTrue(all(not path.startswith('https:') for _,path,_ in self.x.calls))
    def test_export_family_is_bound_even_when_broker_ids_collide(self):
        a,_=self.execute(self.export('ORDERS','a'));b,_=self.execute(self.export('TRADES','b'))
        self.execute(self.request('QUERY_HISTORY_EXPORT','pa',{'source_command_id':a['command_id']}));self.execute(self.request('QUERY_HISTORY_EXPORT','pb',{'source_command_id':b['command_id']}))
        self.assertEqual(self.x.calls[-2][1],'/fapi/v1/order/asyn/id');self.assertEqual(self.x.calls[-1][1],'/fapi/v1/trade/asyn/id')
    def test_export_link_is_not_followed_or_accepted_with_unsafe_scheme(self):
        p,_=self.execute(self.export());self.x.export_status='completed';self.x.export_url='http://127.0.0.1/private'
        _,r=self.execute(self.request('QUERY_HISTORY_EXPORT','poll',{'source_command_id':p['command_id']}));self.assertEqual(r['state'],'READ_FAILED')
        self.assertEqual(len(self.x.calls),2)
    def test_corrupt_export_record_is_not_polled_as_another_family(self):
        p,_=self.execute(self.export())
        with self.store.db:self.store.db.execute("UPDATE exchange_history_exports SET digest='bad'")
        _,r=self.execute(self.request('QUERY_HISTORY_EXPORT','poll',{'source_command_id':p['command_id']}));self.assertEqual(r['state'],'READ_FAILED');self.assertEqual(len(self.x.calls),1)
    def test_crash_after_export_id_persisted_recovers_without_another_get(self):
        p=self.commands.prepare(self.export())
        with patch.object(self.commands,'_finish',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.store.close();self.store=StateStore(self.path);self.commands=ExchangeCommands(self.x,self.store,self.owner)
        self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'APPLIED');self.assertEqual(len(self.x.calls),1)
    def test_public_queries_need_no_private_credentials(self):
        self.x.config=Config();self.commands=ExchangeCommands(self.x,self.store,self.owner)
        _,r=self.execute(self.request('PUBLIC_QUERY','public',{'query':'OPEN_INTEREST','arguments':{}},{'symbol':'BTCUSDT'}))
        self.assertEqual(r['state'],'APPLIED',r)
        with self.assertRaises(ValueError):self.commands.prepare(self.request())
    def test_malformed_parameters_and_unknown_export_kind_are_rejected_locally(self):
        for op,parameters,scope in [('CREATE_HISTORY_EXPORT',{'kind':[],'start_ms':0,'end_ms':1},{'account_wide':True}),
                ('QUERY_HISTORY',{'kind':[],'start_ms':0,'end_ms':1,'page_size':10,'max_requests':2},{'symbol':'BTCUSDT'}),
                ('PRIVATE_QUERY',[],{'account_wide':True})]:
            r=self.request(op,parameters=parameters,scope=scope);r['parameters']=parameters
            with self.subTest(op=op),self.assertRaises(ValueError):self.commands.prepare(r)
        self.assertEqual(self.x.calls,[])
    def test_cli_prepare_apply_show_and_reconcile_read(self):
        from agentrader.cli.exchange_command_cli import main
        file=Path(self.temp.name)/'read.json';file.write_text(json.dumps(self.request()),encoding='utf-8')
        def call(args):
            out=io.StringIO()
            with redirect_stdout(out):code=main(['--database',str(self.path)]+args)
            self.assertEqual(code,0,out.getvalue());return json.loads(out.getvalue())
        with patch('agentrader.cli.exchange_command_cli.Config.load',return_value=self.x.config),patch('agentrader.cli.exchange_command_cli.DemoExchange',return_value=self.x),patch('agentrader.cli.exchange_command_cli.getpass.getuser',return_value='g10'):
            p=call(['prepare',str(file)]);call(['show',p['command_id']]);call(['apply',p['command_id'],'--digest',p['digest']]);call(['reconcile',p['command_id']])
        self.assertEqual(len(self.x.calls),1)


class QueryTransportTests(unittest.TestCase):
    def test_job_creating_get_never_retries_but_ordinary_get_can(self):
        governor=Mock();governor.record.return_value=None;sleep=Mock();transport=JsonTransport(governor,sleep=sleep)
        x=DemoExchange(Config('key','secret'),transport=transport);x.opener=Mock();x.opener.open.side_effect=TimeoutError('SECRET_CANARY')
        with self.assertRaises(ExchangeError):x.get('/fapi/v1/order/asyn',{'startTime':0,'endTime':1})
        self.assertEqual(x.opener.open.call_count,1);sleep.assert_not_called()
        x.opener.open.reset_mock()
        with self.assertRaises(ExchangeError):x.get('/fapi/v3/balance')
        self.assertEqual(x.opener.open.call_count,2)
    def test_historical_trades_use_key_header_without_signing_and_public_market_refuses_them(self):
        x=DemoExchange(Config('key','secret'));req=x._signed_request('GET','/fapi/v1/historicalTrades',{'symbol':'BTCUSDT','limit':2})
        self.assertEqual(req.get_header('X-mbx-apikey'),'key');self.assertNotIn('signature',parse_qs(urlparse(req.full_url).query))
        with self.assertRaises(ValueError):PublicMarket().query('HISTORICAL_TRADES',{'symbol':'BTCUSDT'},{'limit':2})
    def test_new_public_market_queries_are_keyless_and_pinned_to_demo_host(self):
        requests=[]
        class Transport:
            def perform(self,opener,factory,method,base):requests.append((factory(),base));return {'symbol':'BTCUSDT','openInterest':'1','time':1}
        market=PublicMarket(transport=Transport());market.query('OPEN_INTEREST',{'symbol':'BTCUSDT'},{})
        req,base=requests[0];self.assertEqual(urlparse(req.full_url).netloc,'demo-fapi.binance.com');self.assertEqual(req.headers,{});self.assertEqual(req.method,'GET')
