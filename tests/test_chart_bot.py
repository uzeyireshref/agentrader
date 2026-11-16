"""G8 production adapter against a real isolated loopback HTTP process."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import unittest
import uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from agentrader.integration.chart_bot import ChartBot,BotError,BotJournal,LocalHTTP
from agentrader.chart.drawings.service import management
from scripts.integration.chart_bot_fixture import ChartBotFixture,ROOT
from scripts.integration.chart_tool_matrix_cases import drawing_cases,START,STEP


class ChartBotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=ChartBotFixture().start()
    @classmethod
    def tearDownClass(cls):cls.fixture.close()
    def setUp(self):
        self.workspace='test-'+uuid.uuid4().hex[:12];self.journal=self.fixture.folder/(self.workspace+'.db')
        self.bot=self.client();self.geometry=drawing_cases()[0]['geometry']
    def client(self,**kwargs):
        return ChartBot(self.fixture.base,self.fixture.bot_token,bot_id='alpha',strategy_id='synthetic',journal=self.journal,workspace_id=self.workspace,**kwargs)
    def create(self,key='create'):return self.bot.create(key,self.geometry)
    def op(self,item,**changes):return dict(drawing_id=item['drawing_id'],expected_revision=item['revision'],geometry=item['geometry'],management=item['management'],deleted=item['deleted'])|changes
    def error(self,code,call):
        with self.assertRaises(BotError) as caught:call()
        self.assertEqual(caught.exception.code,code);return caught.exception

    def test_identity_catalog_namespace_and_explicit_snapshot(self):
        identity=self.bot.identify();self.assertEqual(identity['actor']['kind'],'bot');self.assertFalse(identity['order_authority'])
        self.assertEqual(self.bot.discover()['access_schema'],'chart-tool-access/1')
        context=self.bot.snapshot('BTCUSDT','15m');self.assertEqual(context['derived']['readiness']['state'],'READY')
        self.assertEqual(context['ui']['reason'],'UI_SESSION_NOT_SELECTED')

    def test_create_cached_replay_changed_payload_conflict_and_restart_discovery(self):
        a=self.create();b=self.create()
        self.assertEqual(a['drawing_id'],b['drawing_id']);self.assertTrue(b['adapter']['replayed'])
        self.error('OPERATION_KEY_CONFLICT',lambda:self.bot.create('create',{**self.geometry,'label':'different'}))
        fresh=self.client();self.assertEqual([x['drawing_id'] for x in fresh.find_own('BTCUSDT','15m')],[a['drawing_id']])
        self.assertEqual(len(fresh.history(a['drawing_id'])['revisions']),1)

    def test_response_lost_after_commit_pending_survives_adapter_restart(self):
        class Drop:
            def __init__(self,http):self.http=http
            def request(self,method,path,body=None):
                result=self.http.request(method,path,body)
                if method=='POST' and '/drawings?' in path:raise BotError('CHART_TRANSPORT_UNAVAILABLE',pending=True)
                return result
        bot=self.client(attempts=1);bot._transport=Drop(bot.http)
        self.assertTrue(self.error('CHART_TRANSPORT_UNAVAILABLE',lambda:bot.create('lost',self.geometry)).pending)
        self.assertEqual(len(bot.journal.pending(bot.scope)),1)
        recovered=self.client();result=recovered.resume_pending()
        self.assertEqual(len(result),1);self.assertTrue(result[0]['duplicate'])
        self.assertEqual(len(recovered.find_own('BTCUSDT','15m')),1);self.assertEqual(recovered.resume_pending(),[])

    def test_dropped_update_and_note_ack_retry_do_not_add_revisions(self):
        item=self.create();real=self.bot.http;dropped=set()
        class Once:
            def request(inner,method,path,body=None):
                result=real.request(method,path,body)
                if method in ('PATCH','PUT') and method not in dropped:
                    dropped.add(method);raise BotError('CHART_TRANSPORT_UNAVAILABLE',pending=True)
                return result
        self.bot._transport=Once()
        updated=self.bot.update('edit',item['drawing_id'],1,{**self.geometry,'label':'updated'})
        self.assertEqual(updated['revision'],2)
        note=self.bot.save_note('note',item['drawing_id'],0,2,'🧭\nNot')
        self.assertEqual(note['revision'],1);self.assertEqual(len(self.bot.history(item['drawing_id'])['revisions']),2)

    def test_manual_object_and_note_preserved_adapter_and_server_protection(self):
        f=self.fixture
        item=f.human.post('/api/workspaces/'+self.workspace+'/drawings?format_version=9',json=dict(request_id='manual-'+uuid.uuid4().hex,geometry=self.geometry)).json();did=item['drawing_id']
        f.human.put('/api/drawings/'+did+'/notes',json=dict(request_id='note-'+uuid.uuid4().hex,expected_revision=0,expected_drawing_revision=1,text='manual 🧭'))
        before=self.bot.get(did)
        self.error('BOT_OBJECT_PROTECTED',lambda:self.bot.delete('manual-delete',did,1))
        self.error('BOT_OBJECT_PROTECTED',lambda:self.bot.save_note('manual-note',did,1,1,'no'))
        result=self.bot.http.request('DELETE','/api/drawings/'+did+'?format_version=9',dict(request_id='bypass-'+uuid.uuid4().hex,expected_revision=1))
        self.assertEqual(result[0],403);self.assertEqual(self.bot.get(did),before)
        self.assertEqual(self.bot.find_own('BTCUSDT','15m'),[])

    def test_explicit_revision_conflict_and_race_do_not_rebase(self):
        item=self.create();did=item['drawing_id']
        self.bot.update('update',did,1,{**self.geometry,'label':'first'})
        self.error('DRAWING_REVISION_CONFLICT',lambda:self.bot.update('stale',did,1,{**self.geometry,'label':'stale'}))
        self.assertEqual(self.bot.get(did)['geometry']['label'],'first')
        def race(n):
            client=self.client()
            try:return client.update('race-'+str(n),did,2,{**self.geometry,'label':'race-'+str(n)})['revision']
            except BotError as error:return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(race,[1,2]))
        self.assertCountEqual(results,[3,'DRAWING_REVISION_CONFLICT'])

    def test_lock_bulk_and_deleted_note_archive(self):
        item=self.create();did=item['drawing_id'];self.bot.save_note('note',did,0,1,'keep')
        locked=self.bot.operations('lock',[self.op(item,management={**management(),'locked':True})])['drawings'][0]
        self.error('DRAWING_LOCKED',lambda:self.bot.delete('locked-delete',did,2))
        self.error('DRAWING_LOCKED',lambda:self.bot.save_note('locked-note',did,1,2,'no'))
        unlocked=self.bot.operations('unlock',[self.op(locked,management=management())])['drawings'][0]
        self.bot.delete('delete',did,unlocked['revision'])
        self.assertEqual(self.bot.notes(did)['state'],'TARGET_ARCHIVED');self.assertEqual(self.bot.find_own('BTCUSDT','15m'),[])

    def test_calculation_structured_blocks_explicit_time_context_and_indicator_reads(self):
        item=self.create();did=item['drawing_id'];context=self.bot.snapshot('BTCUSDT','15m')
        result=self.bot.calculate(did,1,'priceAt',dict(time=START+287*STEP),symbol='BTCUSDT',interval='15m',context_id=context['context_id'])
        self.assertEqual(result['results'][0]['state'],'READY');self.assertEqual(result['results'][0]['result']['value']['decimal'],'110.25')
        wrong=self.bot.calculate(did,1,'priceAt',dict(time=START+287*STEP),symbol='ETHUSDT',interval='15m')
        self.assertEqual(wrong['results'][0]['state'],'SOURCE_MISMATCH')
        missing=self.bot.calculate(did,1,'priceAt',{},symbol='BTCUSDT',interval='15m')
        self.assertEqual(missing['results'][0]['state'],'INVALID_INPUT')
        queries=[dict(query_id=c['indicator_id'],indicator_id=c['indicator_id'],expected_revision=c['revision'],operation='latest',inputs={}) for c in context['indicators']['indicators']]
        self.assertEqual(len(self.bot.indicator_queries('BTCUSDT','15m',queries)['results']),9)

    def test_namespace_identity_mismatch_rejected_before_any_write(self):
        bot=ChartBot(self.fixture.base,self.fixture.bot_token,bot_id='wrong',strategy_id='synthetic',journal=self.journal,workspace_id=self.workspace)
        self.error('BOT_NAMESPACE_MISMATCH',lambda:bot.create('no',self.geometry))
        self.assertEqual(bot.journal.pending(bot.scope),[])
        self.error('SOURCE_MISMATCH',lambda:self.bot.create('null-geometry',None))
        self.error('SOURCE_MISMATCH',lambda:self.bot.create('wrong-source',{**self.geometry,'price_source':'MARK_PRICE'}))
        self.assertEqual(self.bot.find_own('BTCUSDT','15m'),[])

    def test_wrong_database_journal_is_rejected_without_application_changes(self):
        path=self.fixture.folder/'app.db';before=path.read_bytes()
        self.error('NOT_A_BOT_JOURNAL',lambda:BotJournal(path))
        self.assertEqual(path.read_bytes(),before)
        raw=self.journal.read_bytes();self.assertNotIn(self.fixture.bot_token.encode(),raw)

    def test_concurrent_duplicate_operation_has_one_object(self):
        def create(n):return self.client().create('concurrent',self.geometry)['drawing_id']
        with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(create,[1,2]))
        self.assertEqual(ids[0],ids[1]);self.assertEqual(len(self.bot.find_own('BTCUSDT','15m')),1)

    def test_cli_uses_same_durable_adapter_and_no_exchange_config(self):
        request=self.fixture.folder/'task.json';request.write_text(json.dumps(dict(action='create',arguments=dict(key='cli',geometry=self.geometry))),encoding='utf-8')
        command=[sys.executable,'-m','agentrader','chart-bot','--url',self.fixture.base,'--bot-id','alpha','--strategy-id','synthetic','--workspace',self.workspace,'--journal',str(self.journal)]
        first=subprocess.run(command+['run',str(request)],cwd=ROOT,env=self.fixture.env,capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(first.returncode,0,first.stdout+first.stderr)
        again=subprocess.run(command+['run',str(request)],cwd=ROOT,env=self.fixture.env,capture_output=True,text=True,encoding='utf-8',timeout=15)
        a,b=json.loads(first.stdout),json.loads(again.stdout)
        self.assertEqual(a['result']['drawing_id'],b['result']['drawing_id']);self.assertTrue(b['result']['adapter']['replayed'])
        self.assertNotIn(self.fixture.bot_token,first.stdout+first.stderr);self.assertFalse((self.fixture.folder/'execution.db').exists())

    def test_local_transport_rejects_remote_credentials_urls_and_unsafe_paths(self):
        for url in ('https://127.0.0.1','http://example.com','http://127.0.0.1/x','http://user:password@localhost','http://localhost:99999','http://localhost?token=secret'):
            with self.subTest(url=url):self.error('LOCAL_CHART_URL_REQUIRED',lambda:LocalHTTP(url,'b'*40,'namespace'))
        self.error('BOT_PATH_FORBIDDEN',lambda:self.bot.http.request('GET','//remote/api/test'))
        self.error('BOT_CREDENTIAL_REQUIRED',lambda:LocalHTTP('http://localhost','short','namespace'))

    def test_invalid_committed_ack_stays_pending_and_recovers_same_object(self):
        bot=self.client(attempts=1);real=bot.http
        class WrongAck:
            def request(inner,method,path,body=None):
                status,value=real.request(method,path,body)
                if method=='POST' and '/drawings?' in path:value={**value,'origin':None}
                return status,value
        bot._transport=WrongAck()
        self.assertTrue(self.error('INVALID_BOT_WRITE_ACK',lambda:bot.create('bad-ack',self.geometry)).pending)
        recovered=self.client().resume_pending();self.assertEqual(len(recovered),1)
        self.assertTrue(recovered[0]['duplicate']);self.assertEqual(len(self.bot.find_own('BTCUSDT','15m')),1)

    def test_transport_blocks_redirects_and_rejects_html_duplicate_json_nan(self):
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(inner):
                calls.append(inner.path)
                if inner.path=='/api/redirect':
                    inner.send_response(302);inner.send_header('Location','/api/leak');inner.end_headers();return
                content,body=('text/html',b'<html>error</html>') if inner.path=='/api/html' else ('application/json',b'{"a":1,"a":2}' if inner.path=='/api/duplicate' else b'{"a":NaN}')
                inner.send_response(200);inner.send_header('Content-Type',content);inner.end_headers();inner.wfile.write(body)
            def log_message(*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            transport=LocalHTTP('http://127.0.0.1:'+str(server.server_port),'b'*40,'namespace')
            self.error('BOT_REDIRECT_FORBIDDEN',lambda:transport.request('GET','/api/redirect'))
            self.assertNotIn('/api/leak',calls)
            for path in ('/api/html','/api/duplicate','/api/nan'):self.error('INVALID_BOT_RESPONSE',lambda:transport.request('GET',path))
        finally:server.shutdown();server.server_close();thread.join(timeout=2)
