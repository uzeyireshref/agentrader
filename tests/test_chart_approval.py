import copy
from contextlib import closing
import json
import unittest
from unittest.mock import Mock, patch

import test_chart_execution as bridge_tests
from agentrader.application.settings import WebSettings
from agentrader.integration.chart_approval import ApprovalInbox, ApprovalError, plan_view, process_once, pulse, run_approval_worker
from agentrader.migrations import connect
from agentrader.integration.preview_preflight import ReadOnlyDemoAccount


class ChartApprovalTests(unittest.TestCase):
    def setUp(self):
        self.f=bridge_tests.ChartExecutionTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.clock=lambda:self.f.f.clock[1]
        self.report=dict(preview_hash=self.f.body['content_hash'],plan_digest=self.f.body['plan_digest'],
                         checked_at=1000,expires_at=1120,account_preflight=dict(state='READY',execution_authorized=False,quantity='0.59'))
        self.f.preflight.side_effect=None;self.f.preflight.return_value=self.report
        created=self.f.review();self.plan=created['plan'];self.plan_id=self.plan['plan_id']
        self.settings=WebSettings(application_database=self.f.f.h.db,execution_database=self.f.path,
                                  market_database=self.f.path.parent/'market.db',owner='fixture',token='t'*40)
        from agentrader.application.environment import CONTEXT
        with closing(connect(self.settings.application_database)) as db,db:
            db.execute('CREATE TABLE app_market_context (id INTEGER PRIMARY KEY,body TEXT NOT NULL)')
            db.execute('INSERT INTO app_market_context VALUES (1,?)',(json.dumps(CONTEXT),))
        self.inbox=ApprovalInbox(self.settings,clock=self.clock)
        pulse(self.settings,clock=self.clock)
        self.view=plan_view(self.settings,self.plan_id,clock=self.clock)
        self.command=dict(request_id='explicit-consent',review_hash=self.view['review_hash'],plan_digest=self.view['plan_digest'],
                          preview_hash=self.view['preview_hash'],account_ref=self.view['account_ref'],ttl_seconds=60)

    def process(self,**kwargs):
        return process_once(self.settings,ReadOnlyDemoAccount(self.f.x),self.f.limits,clock=self.clock,
                            guard=lambda *a,**k:self.f.guard(*a),preflight=self.f.preflight,
                            provider_factory=lambda *a:self.f.provider,**kwargs)

    def test_acceptance_only_queues_and_worker_approves_without_any_exchange_write(self):
        self.assertEqual(self.inbox.accept(self.plan_id,self.command)['state'],'PENDING')
        self.assertEqual(self.f.service.show(self.plan_id,1,now=1000)['state'],'PENDING_APPROVAL')
        result=self.process()
        self.assertEqual(result['state'],'APPROVED')
        self.assertEqual(result['result']['approval_until'],1060)
        self.assertFalse(result['result']['executed'])
        self.assertEqual(self.f.store.intents(),[]);self.assertEqual(self.f.x.calls,[])
        self.assertEqual(self.f.service.show(self.plan_id,1,now=1000)['state'],'AUTHORIZED')

    def test_duplicate_acceptance_never_extends_authorization(self):
        self.inbox.accept(self.plan_id,self.command);self.process()
        self.f.f.clock[1]=1010
        duplicate=self.inbox.accept(self.plan_id,self.command)
        self.assertEqual(duplicate['state'],'APPROVED')
        self.assertEqual(duplicate['result']['approval_until'],1060)
        self.assertIsNone(self.process())

    def test_mismatched_scope_or_reused_request_identifier_is_rejected(self):
        for field in ('review_hash','plan_digest','preview_hash','account_ref'):
            with self.assertRaises(ApprovalError):self.inbox.accept(self.plan_id,{**self.command,field:'b'*64})
        self.inbox.accept(self.plan_id,self.command)
        with self.assertRaises(ApprovalError):self.inbox.accept(self.plan_id,{**self.command,'ttl_seconds':120})

    def test_offline_worker_cannot_accept_new_consent(self):
        pulse(self.settings,'STOPPED',clock=self.clock)
        with self.assertRaisesRegex(ApprovalError,'WORKER_OFFLINE'):self.inbox.accept(self.plan_id,self.command)

    def test_changed_account_or_failed_preflight_never_authorizes(self):
        self.inbox.accept(self.plan_id,self.command)
        self.f.preflight.side_effect=ValueError('signed-url-and-secret-must-not-escape')
        result=self.process()
        self.assertEqual(result['state'],'FAILED');self.assertNotIn('secret',json.dumps(result))
        self.assertEqual(self.f.service.show(self.plan_id,1,now=1000)['state'],'PENDING_APPROVAL')
        self.assertEqual(self.f.x.calls,[])

    def test_preview_expiry_during_revalidation_blocks_approval(self):
        self.inbox.accept(self.plan_id,self.command)
        def expire(*a,**k):self.f.f.clock[1]=1121;return self.report
        self.f.preflight.side_effect=expire
        self.assertEqual(self.process()['state'],'FAILED')
        self.assertEqual(self.f.store.db.execute('SELECT state FROM plan_versions').fetchone()[0],'PENDING_APPROVAL')

    def test_queued_consent_expiry_is_not_an_approval_extension(self):
        self.inbox.accept(self.plan_id,self.command);self.f.f.clock[1]=1061
        self.assertIsNone(self.process());self.assertEqual(self.inbox.show(self.command['request_id'])['state'],'EXPIRED')

    def test_scope_tampering_in_queue_fails_closed(self):
        self.inbox.accept(self.plan_id,self.command)
        with closing(connect(self.settings.application_database)) as db,db:
            db.execute("UPDATE app_chart_approvals SET payload='{}'")
        self.assertEqual(self.process()['state'],'FAILED')

    def test_account_key_change_blocks_preflight_and_authorization(self):
        from agentrader.shared.config import Config
        self.inbox.accept(self.plan_id,self.command)
        self.f.x.config=Config('another-account','never-expose')
        self.f.preflight.reset_mock()
        self.assertEqual(self.process()['state'],'FAILED')
        self.f.preflight.assert_not_called()

    def test_worker_adapter_rejects_mutation_even_if_preflight_regresses(self):
        self.inbox.accept(self.plan_id,self.command)
        self.f.preflight.side_effect=lambda provider,x,*a,**k:x.request('POST','/fapi/v1/order',{})
        self.assertEqual(self.process()['state'],'FAILED')
        self.assertEqual(self.f.x.calls,[])

    def test_other_owner_cannot_read_plan_or_consent(self):
        from dataclasses import replace
        self.inbox.accept(self.plan_id,self.command)
        foreign=replace(self.settings,owner='someone-else')
        self.assertIsNone(plan_view(foreign,self.plan_id,clock=self.clock))
        with self.assertRaises(ApprovalError):ApprovalInbox(foreign,clock=self.clock).show('explicit-consent')

    def test_crashed_worker_is_not_replayed_and_idle_worker_never_loads_credentials(self):
        self.inbox.accept(self.plan_id,self.command)
        with closing(connect(self.settings.application_database)) as db,db:
            db.execute("UPDATE app_chart_approvals SET state='RUNNING'")
        with patch('agentrader.shared.config.Config.load',side_effect=AssertionError('no account I/O')):
            run_approval_worker(self.settings,once=True)
        self.assertEqual(self.inbox.show(self.command['request_id'])['state'],'NEEDS_REVIEW')
        self.assertEqual(self.f.x.calls,[])

    def client(self,settings=None):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        self.enterContext(patch('agentrader.api.chart_approvals.ApprovalInbox',return_value=self.inbox))
        real_view=plan_view
        self.enterContext(patch('agentrader.api.chart_approvals.plan_view',side_effect=lambda s,p:real_view(s,p,clock=self.clock)))
        hub=Mock();hub.binding_context.return_value=None
        return self.enterContext(TestClient(create_app(settings or self.settings,market=Mock(),hub=hub),base_url='http://127.0.0.1'))

    def test_private_routes_require_session_and_reject_foreign_origin(self):
        c=self.client();url='/api/chart-plans?workspace=main&event_id='+self.f.f.event
        self.assertEqual(c.get(url).status_code,401)
        self.assertEqual(c.get(url,headers={'Authorization':'Bearer '+'t'*40,'Origin':'https://other.example'}).status_code,403)
        self.assertEqual(c.post('/api/session',headers={'Authorization':'Bearer '+'t'*40}).status_code,200)
        response=c.get(url);self.assertEqual(response.status_code,200)
        self.assertNotIn('authorization_token',response.text);self.assertNotIn('token_hash',response.text)
        self.assertNotIn('secret',response.text)

    def test_disabled_private_api_has_no_approval_surface(self):
        from dataclasses import replace
        c=self.client(replace(self.settings,token=''))
        self.assertEqual(c.get('/api/chart-plans?workspace=main&event_id='+self.f.f.event).status_code,503)
        self.assertEqual(c.post('/api/chart-plans/'+self.plan_id+'/approval-requests',json=self.command).status_code,503)

    def test_authenticated_http_only_enqueues_never_opens_execution_writer(self):
        c=self.client();headers={'Authorization':'Bearer '+'t'*40}
        with patch('agentrader.shared.state.StateStore',side_effect=AssertionError('HTTP must remain read-only')):
            response=c.post('/api/chart-plans/'+self.plan_id+'/approval-requests',json=self.command,headers=headers)
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['state'],'PENDING')
        self.assertEqual(self.f.service.show(self.plan_id,1,now=1000)['state'],'PENDING_APPROVAL')
        self.assertEqual(self.f.x.calls,[])

