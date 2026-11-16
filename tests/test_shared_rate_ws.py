import copy
import hashlib
import hmac
import io
import json
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout, nullcontext
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import urlencode
from urllib.request import Request

from agentrader.shared.config import Config
from agentrader.shared.errors import ExchangeError
from agentrader.shared.exchange import DemoExchange
from agentrader.shared.rate_budget import charges, reserve, observe, rest_charges
from agentrader.shared.state import StateStore
from agentrader.shared.transport import JsonTransport, RequestGovernor
from agentrader.shared.ws_orders import WS_URL


class SharedBudgetTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)/'rate.db';self.now=120.0
        self.g=RequestGovernor(self.path,lambda:self.now)

    def test_two_hosts_share_atomic_rest_weight(self):
        a=rest_charges(Request('https://demo-fapi.binance.com/fapi/v1/time'))
        b=rest_charges(Request('https://demo-dapi.binance.com/dapi/v1/time'))
        self.assertEqual(a,b)
        reserve(self.g,charges('demo','REST',2400))
        with self.assertRaises(ExchangeError):reserve(RequestGovernor(self.path,lambda:self.now),b)
        reserve(self.g,charges('production','REST',2400))

    def test_concurrent_process_connections_cannot_overspend(self):
        barrier=threading.Barrier(8)
        def attempt(_):
            g=RequestGovernor(self.path,lambda:self.now);barrier.wait()
            try:reserve(g,[('pool','REQUEST_WEIGHT',60,3,1)]);return True
            except ExchangeError:return False
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(attempt,range(8)))
        self.assertEqual(sum(results),3)

    def test_all_dimensions_rollback_when_order_window_full(self):
        reserve(self.g,charges('demo','REST',1,300))
        with self.assertRaises(ExchangeError):reserve(self.g,charges('demo','REST',2000,1))
        reserve(self.g,charges('demo','REST',2399))

    def test_ws_weight_separate_order_count_shared_across_all_keys(self):
        reserve(self.g,charges('demo','REST',2400,300))
        reserve(self.g,charges('demo','WS',5))
        with self.assertRaises(ExchangeError):reserve(self.g,charges('demo','WS',1,1))

    def test_rest_trade_overlap_consumes_ws_pool(self):
        request=Request('https://demo-fapi.binance.com/fapi/v1/order?newClientOrderId=x',method='POST')
        reserve(self.g,charges('demo','WS',2400))
        with self.assertRaises(ExchangeError):reserve(self.g,rest_charges(request))

    def test_cooldown_restarts_and_crosses_hosts_and_transports(self):
        self.g.record('demo-dapi.binance.com',{'Retry-After':'90'},418)
        g=RequestGovernor(self.path,lambda:self.now)
        for channel in ('REST','WS'):
            with self.subTest(channel=channel),self.assertRaises(ExchangeError):reserve(g,charges('demo',channel,1))
        reserve(g,charges('production','REST',1))
        self.now+=91;reserve(g,charges('demo','REST',1))

    def test_header_count_never_refunds_local_or_out_of_order_observations(self):
        reserve(self.g,charges('demo','REST',10))
        self.g.record('demo-dapi.binance.com',{'X-MBX-USED-WEIGHT-1M':'2390'})
        self.g.record('demo-fapi.binance.com',{'X-MBX-USED-WEIGHT-1M':'1'})
        with self.assertRaises(ExchangeError):reserve(self.g,charges('demo','REST',1))

    def test_server_lower_limit_and_new_interval_are_enforced(self):
        observe(self.g,'testnet.binancefuture.com',[dict(rateLimitType='ORDERS',interval='SECOND',intervalNum=5,limit=2,count=1)])
        reserve(self.g,charges('demo','REST',1,1))
        with self.assertRaises(ExchangeError):reserve(self.g,charges('demo','WS',1,1))

    def test_time_window_reset_and_backwards_clock_fail_closed(self):
        reserve(self.g,charges('demo','REST',2400))
        self.now=180;reserve(self.g,charges('demo','REST',1))
        self.now=179
        with self.assertRaises(ExchangeError) as caught:reserve(self.g,charges('demo','REST',1))
        self.assertEqual(caught.exception.delivery_status,'NOT_SENT')

    def test_reported_lower_dimensions_survive_window_cleanup_and_restart(self):
        observe(self.g,'demo-fapi.binance.com',[dict(rateLimitType='ORDERS',interval='SECOND',intervalNum=5,limit=1,count=0)])
        self.now+=300
        reserve(self.g,charges('demo','REST',1,1))
        with self.assertRaises(ExchangeError):reserve(RequestGovernor(self.path,lambda:self.now),charges('demo','WS',1,1))

    def test_rest_reserves_before_network_and_keeps_unknown_debit(self):
        opener=Mock();opener.open.side_effect=TimeoutError('secret-canary')
        t=JsonTransport(self.g)
        factory=lambda:Request('https://demo-fapi.binance.com/fapi/v1/order?newClientOrderId=x',method='POST')
        with self.assertRaises(ExchangeError) as caught:t.perform(opener,factory,'POST','https://demo-fapi.binance.com')
        self.assertEqual(caught.exception.delivery_status,'UNKNOWN');self.assertEqual(opener.open.call_count,1)
        with self.assertRaises(ExchangeError):reserve(self.g,charges('demo','REST',1,300))

    def test_rate_storage_failure_prevents_network(self):
        self.path.write_text('invalid-db',encoding='utf-8');opener=Mock()
        with self.assertRaises(ExchangeError) as caught:
            JsonTransport(self.g).perform(opener,lambda:Request('https://demo-fapi.binance.com/fapi/v1/time'),'GET','https://demo-fapi.binance.com')
        self.assertEqual(caught.exception.delivery_status,'NOT_SENT');opener.open.assert_not_called()

    def test_observation_clock_failure_after_rest_send_never_claims_unsent(self):
        response=io.BytesIO(b'{}');response.headers={'X-MBX-USED-WEIGHT-1M':'1'}
        opener=Mock();opener.open.return_value=response
        with patch('agentrader.shared.rate_budget.observe',side_effect=ExchangeError('clock',delivery_status='NOT_SENT')):
            with self.assertRaises(ExchangeError) as caught:
                JsonTransport(self.g).perform(opener,lambda:Request('https://demo-fapi.binance.com/fapi/v1/order',method='POST'),'POST','https://demo-fapi.binance.com')
        self.assertEqual(caught.exception.delivery_status,'UNKNOWN');self.assertEqual(opener.open.call_count,1)

    def test_costs_bound_variable_reads_and_batch_members(self):
        rows=rest_charges(Request('https://demo-fapi.binance.com/fapi/v1/openOrders'))
        self.assertEqual(rows[0][-1],40)
        rows=rest_charges(Request('https://demo-fapi.binance.com/fapi/v1/batchOrders?'+urlencode({'batchOrders':json.dumps([{}, {}, {}])}),method='POST'))
        self.assertEqual([r[-1] for r in rows if r[1]=='ORDERS'],[3,3])
        self.assertEqual(rest_charges(Request('https://demo-fapi.binance.com/fapi/v1/income/asyn'))[0][-1],1000)

    def test_funding_and_statistics_have_separate_five_minute_quotas(self):
        for path,limit in (('/futures/data/openInterestHist',1000),('/fapi/v1/fundingInfo',500)):
            rows=rest_charges(Request('https://demo-fapi.binance.com'+path))
            self.assertEqual(rows[-1][2:4],(300,limit))
            reserve(self.g,[(*rows[-1][:-1],limit)])
            with self.assertRaises(ExchangeError):reserve(self.g,rows)


class Socket:
    def __init__(self, callback=None):self.sent=[];self.closed=False;self.callback=callback
    def send(self, data):self.sent.append(json.loads(data))
    def recv(self):
        request=self.sent[-1]
        if self.callback:return self.callback(request)
        p=request['params'];result=dict(symbol=p.get('symbol','BTCUSDT'),orderId=p.get('orderId',7),
            clientOrderId=p.get('newClientOrderId',p.get('origClientOrderId','owned')),
            status='NEW',origQty=p.get('quantity','1'),executedQty='0')
        if 'modifyId' in p:result['modifyId']=p['modifyId']
        if request['method'].startswith('algoOrder.'):
            result=dict(algoId=p.get('algoId',11),clientAlgoId=p.get('clientAlgoId','algo'),algoStatus='NEW')
            if 'symbol' in p:result['symbol']=p['symbol']
        return json.dumps(dict(id=request['id'],status=200,result=result))
    def close(self):self.closed=True


class WsOrderTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);self.store=StateStore(self.root/'execution.db');self.addCleanup(lambda:self.store.close())
        self.g=RequestGovernor(self.root/'rate.db')
        self.sockets=[]
        def connector(url):
            self.assertEqual(url,WS_URL);s=Socket();self.sockets.append(s);return s
        self.connector=connector
        self.x=self.exchange()
        self.params=dict(symbol='BTCUSDT',side='BUY',type='LIMIT',timeInForce='GTC',quantity='1.00000001',price='100.00000001',newClientOrderId='owned')

    def exchange(self,channel='ws',connector=None):
        x=DemoExchange(Config('key-canary','secret-canary'),transport=JsonTransport(self.g),order_transport=channel,store=self.store,ws_connector=connector or self.connector)
        x.sync_time=Mock(return_value={'clock_offset_ms':0});x.opener=Mock();return x

    def send(self):return self.x.request('POST','/fapi/v1/order',self.params)

    def test_signature_sorted_exact_decimal_and_persistent_correlation(self):
        self.send();p=self.sockets[0].sent[0];values=p['params'].copy();signature=values.pop('signature')
        self.assertEqual(signature,hmac.new(b'secret-canary',urlencode(sorted(values.items())).encode(),hashlib.sha256).hexdigest())
        self.assertEqual(values['quantity'],'1.00000001');self.assertIs(type(values['timestamp']),int)
        row=self.store.db.execute('SELECT * FROM ws_deliveries').fetchone()
        self.assertEqual(row['request_id'],p['id']);self.assertEqual(row['state'],'ACKNOWLEDGED')
        self.assertTrue(self.sockets[0].closed);self.x.opener.open.assert_not_called()
        self.assertNotIn('canary',str(tuple(row)))

    def test_normal_lookup_cancel_modify_and_algo_routes(self):
        requests=[('GET','/fapi/v1/order',dict(symbol='BTCUSDT',orderId=7)),
            ('DELETE','/fapi/v1/order',dict(symbol='BTCUSDT',origClientOrderId='owned')),
            ('PUT','/fapi/v1/order',dict(symbol='BTCUSDT',origClientOrderId='owned',side='BUY',price='99',quantity='1',modifyId=44)),
            ('POST','/fapi/v1/algoOrder',dict(algoType='CONDITIONAL',symbol='BTCUSDT',side='SELL',type='STOP_MARKET',triggerPrice='90',closePosition='true',clientAlgoId='algo')),
            ('DELETE','/fapi/v1/algoOrder',dict(clientAlgoId='algo'))]
        for method,path,p in requests:self.x.request(method,path,p)
        self.assertEqual([s.sent[0]['method'] for s in self.sockets],['order.status','order.cancel','order.modify','algoOrder.place','algoOrder.cancel'])

    def test_lost_response_restart_cannot_send_again_or_fallback_to_rest(self):
        def lost(_):raise TimeoutError('signed-url-secret-canary')
        s=Socket(lost);self.x=self.exchange(connector=lambda _:s)
        with self.assertRaises(ExchangeError) as caught:self.send()
        self.assertEqual(caught.exception.delivery_status,'UNKNOWN');self.assertNotIn('canary',str(caught.exception))
        self.store.close();self.store=StateStore(self.root/'execution.db');self.x=self.exchange()
        with self.assertRaises(ExchangeError):self.send()
        rest=self.exchange('rest')
        with self.assertRaises(ExchangeError):rest.request('POST','/fapi/v1/order',self.params)
        rest.opener.open.assert_not_called();self.assertEqual(len(s.sent),1)

    def test_changed_price_with_same_client_id_cannot_acquire_new_send_right(self):
        self.send();self.params['price']='99'
        with self.assertRaises(ExchangeError):self.send()
        rest=self.exchange('rest')
        with self.assertRaises(ExchangeError):rest.request('POST','/fapi/v1/order',self.params)
        self.assertEqual(len(self.sockets),1);rest.opener.open.assert_not_called()

    def test_partial_send_failure_is_unknown_without_retry(self):
        s=Socket();s.send=Mock(side_effect=OSError('partial-secret-canary'));self.x=self.exchange(connector=lambda _:s)
        with self.assertRaises(ExchangeError) as caught:self.send()
        self.assertEqual(caught.exception.delivery_status,'UNKNOWN');self.assertEqual(s.send.call_count,1);self.assertTrue(s.closed)

    def test_connect_failure_is_proven_not_sent(self):
        self.x=self.exchange(connector=Mock(side_effect=OSError('secret-canary')))
        with self.assertRaises(ExchangeError) as caught:self.send()
        self.assertEqual(caught.exception.delivery_status,'NOT_SENT')
        self.assertEqual(self.store.db.execute('SELECT state FROM ws_deliveries').fetchone()[0],'NOT_SENT')

    def test_connector_exchange_error_message_cannot_echo_credentials(self):
        self.x=self.exchange(connector=Mock(side_effect=ExchangeError('secret-canary',delivery_status='UNKNOWN')))
        with self.assertRaises(ExchangeError) as caught:self.send()
        self.assertEqual(caught.exception.delivery_status,'NOT_SENT');self.assertNotIn('canary',str(caught.exception))

    def test_clock_failure_no_socket_or_claim(self):
        self.x.sync_time.side_effect=TimeoutError('secret-canary')
        with self.assertRaises(ExchangeError) as caught:self.send()
        self.assertEqual(caught.exception.delivery_status,'NOT_SENT');self.assertEqual(self.sockets,[])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM ws_deliveries').fetchone()[0],0)

    def test_mismatched_request_id_or_identity_never_adopted(self):
        for key in ('id','symbol','clientOrderId','orderId'):
            def callback(req):
                body=dict(id=req['id'],status=200,result=dict(symbol='BTCUSDT',orderId=7,clientOrderId=req['params']['newClientOrderId']))
                if key=='id':body['id']='foreign'
                else:body['result'][key]='foreign'
                return json.dumps(body)
            self.params['newClientOrderId']='owned-'+key;self.x=self.exchange(connector=lambda _:Socket(callback))
            with self.subTest(key=key),self.assertRaises(ExchangeError) as caught:self.send()
            self.assertEqual(caught.exception.delivery_status,'UNKNOWN')

    def test_error_classification_and_no_raw_message(self):
        for status,code,expected in ((400,-1111,'REJECTED'),(400,-1007,'UNKNOWN'),(503,-1000,'UNKNOWN'),(429,-1003,'UNKNOWN')):
            self.params['newClientOrderId']=str(status)+str(code)
            self.x=self.exchange(connector=lambda _:Socket(lambda req:json.dumps(dict(id=req['id'],status=status,error=dict(code=code,msg='secret-canary')))))
            with self.subTest(status=status,code=code),self.assertRaises(ExchangeError) as caught:self.send()
            self.assertEqual(caught.exception.delivery_status,expected);self.assertNotIn('canary',str(caught.exception))

    def test_ws_ban_is_persistent_in_rest_pool(self):
        self.x=self.exchange(connector=lambda _:Socket(lambda req:json.dumps(dict(id=req['id'],status=418,error=dict(code=-1003),retryAfter=int(time.time()*1000)+90000))))
        with self.assertRaises(ExchangeError):self.send()
        with self.assertRaises(ExchangeError):reserve(RequestGovernor(self.g.path),charges('demo','REST',1))

    def test_invalid_json_and_oversized_frames_unknown(self):
        for i,raw in enumerate(('invalid','x'*(1024*1024+1),'[]')):
            self.params['newClientOrderId']='owned'+str(i);self.x=self.exchange(connector=lambda _:Socket(lambda _:raw))
            with self.assertRaises(ExchangeError) as caught:self.send()
            self.assertEqual(caught.exception.delivery_status,'UNKNOWN')

    def test_float_signing_override_and_missing_id_rejected_before_connect(self):
        for key,value in (('quantity',.1),('apiKey','foreign'),('timestamp',4),('newClientOrderId',''),('newClientOrderId','special:cid/1')):
            p=self.params|{key:value}
            with self.subTest(key=key),self.assertRaises(ValueError):self.x.request('POST','/fapi/v1/order',p)
        self.assertEqual(self.sockets,[])

    def test_wrong_context_or_missing_journal_rejected(self):
        with self.assertRaises(ValueError):DemoExchange(Config('x','y'),order_transport='ws')
        with self.assertRaises(ValueError):DemoExchange(Config('x','y'),order_transport='ws',store=object())
        self.x.config=Config('other','other')
        with self.assertRaises(ValueError):self.send()
        self.assertEqual(self.sockets,[])

    def test_ws_batch_never_silently_uses_rest(self):
        with self.assertRaises(ExchangeError) as caught:self.x.request('POST','/fapi/v1/batchOrders',{'batchOrders':'[]'})
        self.assertEqual(caught.exception.delivery_status,'NOT_SENT');self.x.opener.open.assert_not_called()

    def test_read_failure_is_not_order_rejection(self):
        self.x=self.exchange(connector=lambda _:Socket(lambda req:json.dumps(dict(id=req['id'],status=400,error=dict(code=-2013)))))
        with self.assertRaises(ExchangeError) as caught:self.x.get('/fapi/v1/order',dict(symbol='BTCUSDT',orderId=7))
        self.assertEqual(caught.exception.delivery_status,'READ_FAILED')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM ws_deliveries').fetchone()[0],0)

    def test_rate_db_failure_before_connect_is_unsent(self):
        self.g.path.write_text('broken',encoding='utf-8')
        with self.assertRaises(ExchangeError) as caught:self.send()
        self.assertEqual(caught.exception.delivery_status,'NOT_SENT');self.assertEqual(self.sockets,[])

    def test_rate_observation_failure_after_send_is_unknown(self):
        with patch('agentrader.shared.ws_orders.observe',side_effect=ExchangeError('clock',delivery_status='NOT_SENT')):
            with self.assertRaises(ExchangeError) as caught:self.send()
        self.assertEqual(caught.exception.delivery_status,'UNKNOWN')

    def test_cli_query_uses_real_ws_dispatch_and_existing_command_projection(self):
        from agentrader.bot.exchange_commands import ExchangeCommands
        from agentrader.cli.exchange_command_cli import main
        service=ExchangeCommands(self.x,self.store,'local:test')
        req=dict(schema_version=1,client_command_id='query',environment='demo',exchange='binance',product='USD-M',account_ref=service.account_ref,operation='QUERY_ORDER',scope=dict(symbol='BTCUSDT'),parameters=dict(order_id=7))
        p=service.prepare(req);out=io.StringIO()
        with patch('agentrader.cli.exchange_command_cli.Config.load',return_value=self.x.config),patch('agentrader.cli.exchange_command_cli.DemoExchange',return_value=self.x) as factory,patch('getpass.getuser',return_value='test'),patch('agentrader.cli.exchange_command_cli.execution_lock',return_value=nullcontext()),redirect_stdout(out):
            code=main(['--database',str(self.store.path),'--order-transport','ws','apply',p['command_id'],'--digest',p['digest']])
        self.assertEqual(code,0);self.assertEqual(json.loads(out.getvalue())['state'],'APPLIED')
        self.assertEqual(factory.call_args.kwargs['order_transport'],'ws');self.assertEqual(self.sockets[0].sent[0]['method'],'order.status')


class WsExecutionIntegrationTests(unittest.TestCase):
    def setUp(self):
        from agentrader.bot.plans import PlanService
        from agentrader.bot.risk import RiskLimits
        from agentrader.bot.v2_runner import V2Runner
        from test_plan_v2 import plan_v2
        from test_v2_preflight import snapshot
        from test_order_amend import AmendExchange
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.store=StateStore(self.root/'execution.db');self.addCleanup(lambda:self.store.close())
        self.service=PlanService(self.store,'owner');self.backend=AmendExchange();self.backend.price='80000'
        self.x=self.exchange()
        self.plan=plan_v2();self.plan['entry'].update(condition='IMMEDIATE',trigger_price=None)
        self.snap=snapshot();self.snap.update(observed_at=time.time(),finished_at=time.time(),now_ms=int(time.time()*1000))
        mock=patch('agentrader.bot.v2_runner.collect_flat_snapshot',side_effect=lambda *a:copy.deepcopy(self.snap));mock.start();self.addCleanup(mock.stop)
        self.runner=V2Runner(self.service,self.x,RiskLimits())

    def exchange(self, channel='ws'):
        x=DemoExchange(self.backend.config,transport=JsonTransport(RequestGovernor(self.root/'rate.db')),order_transport=channel,store=self.store,ws_connector=lambda _:Socket(self.dispatch))
        x.get=self.backend.get;x.sync_time=self.backend.sync_time;x.opener=Mock();return x

    def dispatch(self, req):
        from agentrader.shared.ws_orders import ROUTES
        method,path=next(k for k,v in ROUTES.items() if v[0]==req['method'])
        p={k:v for k,v in req['params'].items() if k not in ('apiKey','signature','timestamp','recvWindow')}
        result=self.backend.request(method,path,p)
        if req['method']=='algoOrder.place':
            result['algoId']=list(self.backend.algos).index(p['clientAlgoId'])+1
        if method=='DELETE':
            if path.endswith('algoOrder'):
                result=self.backend.algos[p['clientAlgoId']]|{'algoId':1}
            else:result=self.backend.orders[p['origClientOrderId']]
        return json.dumps(dict(id=req['id'],status=200,result=result))

    def authorize(self):
        p=self.service.create(self.plan,'owner');self.service.authorize(self.plan['plan_id'],1,p['authorization_token'],'approve','owner')

    def test_normal_generic_single_command_enters_and_protects_via_ws(self):
        from agentrader.bot.exchange_commands import ExchangeCommands
        self.authorize();service=ExchangeCommands(self.x,self.store,'owner');plan=self.service.show(self.plan['plan_id'],1)
        req=dict(schema_version=1,client_command_id='single',environment='demo',exchange='binance',product='USD-M',account_ref=service.account_ref,operation='RUN_SINGLE_PLAN',scope=dict(symbol='BTCUSDT'),parameters=dict(plan_id=self.plan['plan_id'],version=1,plan_digest=plan['digest'],entry_options={}))
        p=service.prepare(req);result=service.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(result['state'],'APPLIED');self.assertEqual(len(self.backend.orders),1);self.assertEqual(len(self.backend.algos),2)
        service.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(len(self.backend.calls),3);self.assertEqual(self.store.db.execute('SELECT count(*) FROM ws_deliveries').fetchone()[0],3)
        self.x.opener.open.assert_not_called()

    def test_lost_ws_entry_restart_management_and_rest_guard_never_repost(self):
        from agentrader.bot.plans import PlanService
        from agentrader.bot.risk import RiskLimits
        from agentrader.bot.v2_runner import V2Runner
        self.authorize();self.backend.timeout=True
        with self.assertRaises(ExchangeError):self.runner.open(self.plan['plan_id'],1,True)
        s=self.store.sessions()[0];self.assertEqual(self.store.intent(s['entry_id'])['state'],'UNKNOWN')
        self.store.close();self.store=StateStore(self.root/'execution.db');self.service=PlanService(self.store,'owner')
        self.x=self.exchange();runner=V2Runner(self.service,self.x,RiskLimits())
        result=runner.manage(s['id'],True)
        self.assertEqual(result['state'],'MANAGING')
        self.assertEqual(len([c for c in self.backend.calls if c[:2]==('POST','/fapi/v1/order')]),1)
        rest=self.exchange('rest');intent=self.store.intent(s['entry_id'])
        with self.assertRaises(ExchangeError):rest.request('POST','/fapi/v1/order',json.loads(intent['params']))
        rest.opener.open.assert_not_called()

    def test_lost_ws_amend_uses_existing_modify_history_without_second_put(self):
        from agentrader.bot.order_amend import OrderAmendments
        from agentrader.bot.risk import RiskLimits
        self.plan['entry'].update(condition='LIMIT',trigger_price='79900');self.plan['sizing']['amount']='90'
        self.authorize();sid=self.runner.open(self.plan['plan_id'],1,True)['session_id'];cid=self.store.sessions()[0]['entry_id']
        amendments=OrderAmendments(self.service,self.x,RiskLimits());p=amendments.prepare(sid,cid,'.001','79800')
        self.backend.amend_lost=True
        self.assertEqual(amendments.apply(p['command_id'],p['digest'])['state'],'APPLIED')
        amendments.apply(p['command_id'],p['digest'])
        self.assertEqual(len([c for c in self.backend.calls if c[0]=='PUT']),1)
