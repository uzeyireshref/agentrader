import json
import sqlite3
import tempfile
import time
import unittest
import copy
from contextlib import contextmanager,closing
from pathlib import Path
from unittest.mock import patch

from agentrader.application.settings import WebSettings
from agentrader.application.service import ApplicationService
from agentrader.application.bot_inbox import BotInbox,BotError
from agentrader.application.bot_engine import BotEngine,make_plan,verified_store
from agentrader.application.bot_worker import process_bot_once
from agentrader.bot.risk import RiskLimits
from agentrader.shared.state import StateStore
from test_exchange_commands import CommandExchange


class BotTerminalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.settings=WebSettings(application_database=self.root/'app.db',execution_database=self.root/'exec.db',market_database=self.root/'market.db',token='a'*40,owner='owner',bot_enabled=True)
        ApplicationService(self.settings).initialize();self.inbox=BotInbox(self.settings)
        self.store=StateStore(self.settings.execution_database);self.addCleanup(self.store.close)
        self.x=CommandExchange();self.engine=BotEngine(self.settings,self.x,self.store,RiskLimits())

    @contextmanager
    def factory(self,settings):yield self.engine

    def job(self,action,payload,rid='one'):
        return self.inbox.accept(dict(request_id=rid,action=action,payload=payload))

    def process(self,execute=False):return process_bot_once(self.inbox,execute=execute,factory=self.factory)

    def preview(self):
        self.job('PREVIEW_COMMAND',dict(operation='SET_LEVERAGE',scope={'symbol':'BTCUSDT'},parameters={'leverage':20}))
        result=self.process();self.assertEqual(result['state'],'SUCCEEDED');return result

    def consent(self,p,rid='consent',**changes):
        r=p['result'];payload=dict(review_id=p['job_id'],review_digest=r['review_digest'],account_ref=r['account_ref'],execute_demo=True);payload.update(changes)
        return self.job('CONFIRM',payload,rid)

    def test_prepare_and_context_never_mutate_exchange(self):
        self.preview();self.assertEqual(self.x.calls,[])
        self.job('CONTEXT',{},'context');result=self.process()['result'];self.assertEqual(result['environment'],'demo');self.assertNotIn('EXECUTE_V1_PLAN',result['operations'])

    def test_same_request_id_changed_payload_conflicts(self):
        self.job('CONTEXT',{})
        with self.assertRaisesRegex(BotError,'CONFLICT'):self.job('SNAPSHOT',{'symbol':'BTCUSDT'})

    def test_consent_is_unique_per_review_across_browser_request_ids(self):
        p=self.preview();first=self.consent(p);result=self.process(True)
        self.assertEqual(result['state'],'SUCCEEDED');self.assertEqual(result['result']['state'],'APPLIED')
        second=self.consent(p,'second-tab');self.assertEqual(first['job_id'],second['job_id']);self.assertTrue(second['duplicate']);self.assertEqual(len(self.x.calls),1)

    def test_read_only_worker_cannot_execute_even_authenticated_consent(self):
        p=self.preview();self.consent(p);r=self.process();self.assertEqual(r['error_code'],'BOT_WORKER_READ_ONLY');self.assertEqual(self.x.calls,[])

    def test_wrong_digest_or_account_scope_cannot_execute(self):
        p=self.preview();self.consent(p,review_digest='b'*64);self.assertEqual(self.process(True)['error_code'],'REVIEW_SCOPE_CHANGED');self.assertEqual(self.x.calls,[])

    def test_expired_review_does_not_execute(self):
        p=self.preview();self.consent(p);self.engine.clock=lambda:p['result']['expires_at']+1
        self.assertEqual(self.process(True)['error_code'],'REVIEW_EXPIRED_OR_RISK_CHANGED');self.assertEqual(self.x.calls,[])

    def test_restart_never_replays_a_running_confirmation(self):
        p=self.preview();c=self.consent(p);self.inbox.claim();self.inbox.recover()
        self.assertEqual(self.inbox.show(c['job_id'])['state'],'NEEDS_REVIEW');self.assertIsNone(self.process(True));self.assertEqual(self.x.calls,[])

    def test_read_command_rejects_write_operation(self):
        self.job('READ_COMMAND',dict(operation='SET_LEVERAGE',scope={'symbol':'BTCUSDT'},parameters={'leverage':20}))
        self.assertEqual(self.process()['error_code'],'READ_ONLY_OPERATION_REQUIRED');self.assertEqual(self.x.calls,[])

    def plan_fixture(self):
        from test_v2_runner import ExecutionExchange
        from test_v2_preflight import snapshot
        self.x=ExecutionExchange();self.engine=BotEngine(self.settings,self.x,self.store,RiskLimits())
        snap=snapshot();snap.update(observed_at=time.time(),finished_at=time.time(),now_ms=int(time.time()*1000))
        mock=patch('agentrader.bot.v2_runner.collect_flat_snapshot',side_effect=lambda *a,**kw:copy.deepcopy(snap));mock.start();self.addCleanup(mock.stop)
        return dict(symbol='BTCUSDT',kind='SINGLE',side='Long',entry='80000',stop='78000',target='84000',amount='80',orderType='MARKET',execution=dict(leverage='20',margin='CROSSED',positionMode='one-way',condition='IMMEDIATE',trigger='80000',driftBps='50')),snap

    def test_plan_preview_consent_opens_existing_runner_once(self):
        draft,_=self.plan_fixture();self.job('PREVIEW_PLAN',{'draft':draft});p=self.process()
        self.assertEqual(p['state'],'SUCCEEDED',p);self.assertEqual(self.x.calls,[])
        self.assertNotIn('authorization_token',json.dumps(p));self.assertNotIn('token_hash',json.dumps(p))
        self.consent(p);result=self.process(True);self.assertEqual(result['state'],'SUCCEEDED',result)
        self.assertTrue(self.store.sessions());count=len(self.x.calls)
        self.consent(p,'other-tab');self.assertIsNone(self.process(True));self.assertEqual(len(self.x.calls),count)

    def test_plan_price_change_invalidates_review_before_any_post(self):
        draft,snap=self.plan_fixture();self.job('PREVIEW_PLAN',{'draft':draft});p=self.process();self.assertEqual(p['state'],'SUCCEEDED',p)
        snap['mark']['markPrice']='80100';self.consent(p)
        self.assertEqual(self.process(True)['error_code'],'PLAN_PREFLIGHT_CHANGED');self.assertEqual(self.x.calls,[])

    def test_saved_plan_is_pending_without_account_reads_or_authority(self):
        draft,_=self.plan_fixture();self.job('SAVE_PLAN',{'draft':draft});r=self.process()
        self.assertEqual(r['state'],'SUCCEEDED',r);self.assertEqual(r['result']['state'],'PENDING_APPROVAL')
        self.assertEqual(self.x.calls,[]);self.assertEqual(self.store.sessions(),[])
        self.assertNotIn('authorization_token',json.dumps(r))

    def test_batch_plan_authorization_does_not_open_or_send(self):
        draft,_=self.plan_fixture();self.job('PREVIEW_PLAN_AUTHORIZATION',{'draft':draft});p=self.process()
        self.assertEqual(p['state'],'SUCCEEDED',p);self.assertTrue(p['result']['payload']['authorize_only'])
        self.consent(p);r=self.process(True)
        self.assertEqual(r['state'],'SUCCEEDED',r);self.assertEqual(r['result']['state'],'AUTHORIZED')
        self.assertFalse(r['result']['order_sent']);self.assertEqual(self.x.calls,[]);self.assertEqual(self.store.sessions(),[])

    def test_worker_once_marks_itself_stopped_and_does_not_execute_by_default(self):
        from agentrader.application.bot_worker import run_bot_worker
        from agentrader.shared.locking import execution_lock
        self.job('CONTEXT',{})
        with patch('agentrader.application.bot_worker.execution_lock',side_effect=lambda path=None:execution_lock(path or self.root/'runtime.lock')):
            result=run_bot_worker(self.settings,once=True,factory=self.factory)
        self.assertEqual(result['state'],'SUCCEEDED');self.assertFalse(self.inbox.status()['execution_enabled'])
        self.assertEqual(self.inbox.status()['worker'],'NOT_READY');self.assertEqual(self.x.calls,[])

    def test_snapshot_returns_projected_account_and_never_places_orders(self):
        from test_v2_preflight import SnapshotExchange
        x=SnapshotExchange();x.config=self.x.config
        x.data['/fapi/v3/account']['apiKey']='must-not-leak'
        self.engine=BotEngine(self.settings,x,self.store,RiskLimits())
        self.job('SNAPSHOT',{'symbol':'BTCUSDT'});r=self.process()
        self.assertEqual(r['state'],'SUCCEEDED',r);self.assertNotIn('must-not-leak',json.dumps(r))
        self.assertEqual(r['result']['positions'],[]);self.assertFalse(r['result']['atomic_snapshot'])

    def test_inbox_rejects_bad_schema_or_non_explicit_consent(self):
        for action,p in [('POST',{}),('SNAPSHOT',{'symbol':'BTCUSDT','url':'https://bad'}),('CONFIRM',{'review_id':'job-'+'a'*40,'review_digest':'b'*64,'account_ref':'c'*64,'execute_demo':False})]:
            with self.subTest(action=action),self.assertRaises(BotError):self.job(action,p)

    def test_legacy_store_is_not_silently_rebound(self):
        path=self.root/'legacy.db'
        with closing(sqlite3.connect(path)) as db,db:db.execute('CREATE TABLE control(name TEXT,value TEXT)')
        before=path.read_bytes()
        with self.assertRaisesRegex(BotError,'UNVERIFIED'):verified_store(path)
        self.assertEqual(path.read_bytes(),before)

    def test_result_integrity_is_checked_before_show_or_consent(self):
        p=self.preview()
        with closing(sqlite3.connect(self.settings.application_database)) as db,db:db.execute("UPDATE app_bot_jobs SET result='{}' WHERE job_id=?",(p['job_id'],))
        with self.assertRaisesRegex(BotError,'INTEGRITY'):self.inbox.show(p['job_id'])

    def test_http_requires_user_auth_and_only_queues_without_loading_credentials(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        with patch('agentrader.shared.config.Config.load',side_effect=AssertionError('HTTP credential load')):
            with TestClient(create_app(self.settings),base_url='http://127.0.0.1') as client:
                self.assertEqual(client.get('/api/bot/status').status_code,401)
                headers={'Authorization':'Bearer '+'a'*40}
                self.assertEqual(client.get('/api/bot/status',headers=headers).status_code,200)
                r=client.post('/api/bot/jobs',headers=headers,json=dict(request_id='http-one',action='CONTEXT',payload={}))
                self.assertEqual(r.status_code,202);self.assertEqual(r.json()['state'],'PENDING')
                self.assertEqual(client.post('/api/bot/jobs',headers=headers|{'Origin':'http://evil.invalid'},json={}).status_code,403)

    def test_local_auto_login_requires_explicit_mode_loopback_and_same_origin(self):
        from dataclasses import replace
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        settings=replace(self.settings,local_auto_login=True)
        with TestClient(create_app(settings),base_url='http://127.0.0.1',client=('127.0.0.1',50123)) as client:
            self.assertTrue(client.get('/api/session').json()['local_auto_login'])
            self.assertEqual(client.post('/api/session').status_code,401)
            headers={'Sec-Fetch-Site':'same-origin','X-Agentrader-Local-Session':'1'}
            self.assertEqual(client.post('/api/session',headers=headers|{'Origin':'http://evil.invalid'}).status_code,403)
            self.assertEqual(client.post('/api/session',headers=headers).status_code,200)
            self.assertEqual(client.get('/api/bot/status').status_code,200)


class TerminalPlanCompilerTests(unittest.TestCase):
    def draft(self):return dict(symbol='BTCUSDT',side='Long',kind='SINGLE',entry='90000',stop='88000',target='94000',amount='100')

    def test_budget_and_target_shares_remain_decimal(self):
        d=self.draft();d['targets']=[dict(price='94000',percent='33.3'),dict(price='95000',percent='66.7')]
        p=make_plan(d,'id',time.time());self.assertEqual(p['sizing'],dict(kind='NOTIONAL',amount='100',currency='USDT'));self.assertEqual(p['targets'][0]['fraction'],'0.333')

    def test_created_time_never_rounds_into_the_future_on_an_unchanged_clock(self):
        from datetime import datetime
        now=2000000000.1234567
        p=make_plan(self.draft(),'fixed-clock',now)
        self.assertLessEqual(datetime.fromisoformat(p['created_at']).timestamp(),now)
        self.assertGreater(datetime.fromisoformat(p['expires_at']).timestamp(),now+299)

    def test_price_match_retains_reference_but_is_an_explicit_order_option(self):
        d=self.draft();d['options']=dict(tif='IOC',stp='',priceMatch='QUEUE',expires='')
        p=make_plan(d,'id',time.time());self.assertEqual(p['entry']['order_options']['price_match'],'QUEUE')

    def test_gtd_requires_utc_epoch_not_server_local_time(self):
        d=self.draft();d['options']=dict(tif='GTD',stp='',expires='2099-01-01T00:00')
        with self.assertRaisesRegex(BotError,'GTD_UTC'):make_plan(d,'id',time.time())
