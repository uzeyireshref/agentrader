import hashlib
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sqlite3
import subprocess
import sys
import os
import tempfile
import unittest
from unittest.mock import patch

from agentrader.application.operations import operation_status,prometheus
from agentrader.application.queries import StorageUnavailable
from agentrader.bot.exchange_commands import ExchangeCommands
from agentrader.bot.plans import PlanService
from agentrader.shared.operation_telemetry import schema,command_state
from agentrader.shared.state import StateStore
from agentrader.shared.transport import RequestGovernor
from test_exchange_commands import CommandExchange


class OperationStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'execution.db';self.gov=self.root/'rate.db'
        self.store=StateStore(self.path);self.addCleanup(self.store.close)
        PlanService(self.store,'local:test');self.service=ExchangeCommands(CommandExchange(),self.store,'local:test')
        self.now=1000.

    def report(self,owner='local:test'):
        return operation_status(self.path,owner,governor_database=self.gov,clock=lambda:self.now)

    def command(self,key='one'):
        req=dict(schema_version=1,client_command_id=key,environment='demo',exchange='binance',product='USD-M',account_ref=self.service.account_ref,operation='QUERY_ORDER',scope=dict(symbol='BTCUSDT'),parameters=dict(order_id=7))
        with patch('agentrader.bot.exchange_commands.time.time',return_value=900.):return self.service.prepare(req)

    def unresolved(self,key='one'):
        p=self.command(key)
        with self.store.db:self.store.db.execute("UPDATE exchange_commands SET state='UNKNOWN' WHERE command_id=?",(p['command_id'],))
        return p

    def test_missing_store_does_not_create_files_or_claim_readiness(self):
        p=self.root/'absent.db';r=operation_status(p,'local:test',governor_database=self.gov)
        self.assertFalse(p.exists());self.assertEqual(r['health'],'NOT_OBSERVED');self.assertEqual(r['trading_readiness'],'UNPROVEN')

    def test_readonly_snapshot_hash_and_credentials_never_loaded(self):
        self.store.reserve('owned','/fapi/v1/order',dict(secret='secret-canary'));self.store.halt('secret-canary')
        self.store.db.execute('PRAGMA wal_checkpoint(FULL)');before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with patch('agentrader.shared.config.Config.load',side_effect=AssertionError('credential access')),patch('agentrader.shared.exchange.DemoExchange.request',side_effect=AssertionError('network')):r=self.report()
        self.assertEqual(before,hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertNotIn('canary',json.dumps(r));self.assertTrue(r['entry_halted']);self.assertEqual(r['health'],'ATTENTION_REQUIRED')

    def test_wrong_owner_no_counts_or_path_leak(self):
        self.unresolved();r=self.report('foreign')
        self.assertEqual(r['storage'],'OWNER_MISMATCH');self.assertNotIn('commands',r);self.assertNotIn(str(self.path),json.dumps(r))

    def test_legacy_fill_rejection_conflict_requires_attention_without_rewriting(self):
        from agentrader.bot.order_journal import OrderJournal
        journal=OrderJournal(self.store);journal.register('owned','local:test','BTCUSDT','BUY','1')
        with self.store.db:self.store.db.execute("UPDATE order_projection SET status='REJECTED',filled='0.5'")
        r=self.report();self.assertEqual(r['projection_conflicts'],1);self.assertEqual(r['health'],'ATTENTION_REQUIRED')
        self.assertEqual(journal.get('owned')['status'],'REJECTED')

    def test_corrupt_projection_decimal_is_a_safe_storage_error(self):
        from agentrader.bot.order_journal import OrderJournal
        journal=OrderJournal(self.store);journal.register('owned','local:test','BTCUSDT','BUY','1')
        with self.store.db:self.store.db.execute("UPDATE order_projection SET filled='secret-canary'")
        with self.assertRaises(StorageUnavailable) as caught:self.report()
        self.assertNotIn('canary',str(caught.exception))

    def test_owner_unverified_no_counts(self):
        with self.store.db:self.store.db.execute("DELETE FROM control WHERE name='plan_owner'")
        self.assertEqual(self.report()['storage'],'OWNER_UNVERIFIED')

    def test_foreign_namespace_is_rejected_without_migration(self):
        with self.store.db:self.store.db.execute('UPDATE execution_namespace SET body=?',(json.dumps(dict(environment='production')),))
        self.assertEqual(self.report()['storage'],'CONTEXT_MISMATCH')

    def test_unknown_counts_age_and_partial_batch_are_distinct(self):
        self.unresolved();p=self.command('partial')
        with self.store.db:self.store.db.execute("UPDATE exchange_commands SET state='FINAL_WITH_ERRORS' WHERE command_id=?",(p['command_id'],))
        r=self.report();self.assertEqual(r['commands']['UNKNOWN'],1);self.assertEqual(r['oldest_unresolved_command_age_seconds'],100)
        self.assertEqual(r['partial_batch_commands'],1);self.assertEqual(r['health'],'ATTENTION_REQUIRED')

    def test_unknown_state_is_sanitized_and_not_healthy(self):
        self.store.reserve('owned','/fapi/v1/order',{})
        self.store.update('owned','secret-canary')
        r=self.report();self.assertEqual(r['intents'],{'UNRECOGNIZED':1});self.assertNotIn('canary',json.dumps(r));self.assertEqual(r['health'],'ATTENTION_REQUIRED')

    def test_active_monitor_missing_stale_fresh_and_stopped(self):
        with self.store.db:self.store.db.execute('INSERT INTO managed_sessions VALUES (?,?,1)',('session','{}'))
        self.assertEqual(self.report()['monitors']['NOT_OBSERVED'],1)
        self.store.runtime_health('session',dict(state='MANAGING'),800)
        self.assertEqual(self.report()['monitors']['STALE'],1)
        self.store.runtime_health('session',dict(state='MANAGING'),999)
        self.assertEqual(self.report()['monitors']['FRESH'],1)
        self.store.runtime_health('session',dict(state='CLOSED'),999)
        self.assertEqual(self.report()['monitors']['STOPPED'],1)

    def test_future_health_stamp_never_looks_fresh(self):
        with self.store.db:self.store.db.execute('INSERT INTO managed_sessions VALUES (?,?,1)',('session','{}'))
        self.store.runtime_health('session',dict(state='MANAGING'),1001)
        self.assertEqual(self.report()['monitors']['STALE'],1)

    def test_pending_stream_and_bounded_reconnect_counter_survive_reopen(self):
        self.store.save_stream_observation('s',dict(event_id='secret-canary'))
        self.store.runtime_health('s',dict(state='STREAM_RECONNECTING',secret='secret-canary'),999)
        self.store.runtime_health('s',dict(state='STREAM_RECONNECTING'),1000)
        r=self.report();self.assertEqual(r['pending_stream_barriers'],1);self.assertEqual(r['stream_counters_since_instrumentation']['STREAM_RECONNECTING'],2)
        self.assertNotIn('canary',json.dumps(r))

    def test_shared_cooldown_survives_new_governor(self):
        RequestGovernor(self.gov,lambda:self.now).record('demo-dapi.binance.com',{'Retry-After':'90'},418)
        r=self.report();self.assertEqual(r['rate_budget']['max_wait_seconds'],90);self.assertEqual(r['health'],'ATTENTION_REQUIRED')

    def test_recovery_latency_tracks_only_measured_transition_and_is_not_recounted(self):
        p=self.unresolved()
        with patch('agentrader.bot.exchange_commands.time.time',return_value=950.):self.service._finish(p['command_id'],'UNKNOWN',{})
        with patch('agentrader.bot.exchange_commands.time.time',return_value=970.):self.service._finish(p['command_id'],'APPLIED',{})
        with patch('agentrader.bot.exchange_commands.time.time',return_value=999.):self.service._finish(p['command_id'],'APPLIED',{})
        r=self.report();self.assertEqual(r['recovery']['samples'],1);self.assertEqual(r['recovery']['max_seconds'],20)

    def test_missing_historical_timestamps_are_not_fabricated_zero(self):
        self.unresolved();r=self.report();self.assertIsNone(r['recovery']['max_seconds']);self.assertEqual(r['recovery']['samples'],0)
        self.assertIsNone(r['ws_transport_faults_since_instrumentation'])

    def test_backward_recovery_clock_is_untimed(self):
        p=self.unresolved()
        with self.store.db:command_state(self.store.db,p['command_id'],'UNKNOWN',990);command_state(self.store.db,p['command_id'],'APPLIED',980)
        r=self.report();self.assertEqual(r['recovery']['untimed_samples'],1);self.assertIsNone(r['recovery']['max_seconds'])

    def test_corrupt_storage_returns_safe_error(self):
        p=self.root/'bad.db';p.write_text('secret-canary',encoding='utf-8')
        with self.assertRaises(StorageUnavailable) as caught:operation_status(p,'local:test',governor_database=self.gov)
        self.assertNotIn('canary',str(caught.exception));self.assertNotIn(str(p),str(caught.exception))

    def test_fixed_prometheus_names_no_raw_labels(self):
        self.unresolved();text=prometheus(self.report())
        self.assertIn('agentrader_operations_unresolved_records 1',text)
        self.assertNotIn('local:test',text);self.assertNotIn(self.service.account_ref,text);self.assertNotIn('{',text)
        self.assertNotIn('max_recovery_seconds',text)

    def test_service_cli_is_readonly_and_uses_same_report(self):
        from agentrader.cli.service_cli import main
        self.unresolved();out=io.StringIO()
        with patch('getpass.getuser',return_value='test'),patch('agentrader.shared.config.Config.load',side_effect=AssertionError('credentials')),redirect_stdout(out):
            code=main(['operations','--database',str(self.path),'--governor-database',str(self.gov)])
        self.assertEqual(code,1);self.assertEqual(json.loads(out.getvalue())['commands'],self.report()['commands'])

    def test_legacy_ws_ledger_migration_preserves_identity_and_unknown_age(self):
        from agentrader.shared.ws_orders import schema as ws_schema
        with self.store.db:
            self.store.db.execute('CREATE TABLE ws_deliveries (identity TEXT PRIMARY KEY,account_ref TEXT,method TEXT,path TEXT,request_id TEXT,state TEXT,delivery_status TEXT)')
            self.store.db.execute('INSERT INTO ws_deliveries VALUES (?,?,?,?,?,?,?)',('identity','a'*64,'POST','/fapi/v1/order','request','UNKNOWN','UNKNOWN'))
        ws_schema(self.store)
        row=self.store.db.execute('SELECT * FROM ws_deliveries').fetchone()
        self.assertEqual(row['identity'],'identity');self.assertEqual(row['request_id'],'request');self.assertEqual(row['state'],'UNKNOWN')
        self.assertIsNone(row['created_at']);self.assertIsNone(row['updated_at'])
        self.assertEqual(self.report()['ws_delivery_history']['UNKNOWN'],1)
        self.assertEqual(self.report()['health'],'ATTENTION_REQUIRED')

    def test_lost_ws_receipt_needs_exact_business_identity_before_healthy_report(self):
        from agentrader.shared.ws_orders import schema as ws_schema,identity
        ws_schema(self.store);p=dict(symbol='BTCUSDT',newClientOrderId='owned')
        wire=identity(self.service.account_ref,'POST','/fapi/v1/order',p)
        with self.store.db:self.store.db.execute('INSERT INTO ws_deliveries (identity,account_ref,method,path,request_id,state) VALUES (?,?,?,?,?,?)',(wire,self.service.account_ref,'POST','/fapi/v1/order','rid','UNKNOWN'))
        self.assertEqual(self.report()['ws_unknown_without_business_resolution'],1)
        self.store.reserve('other','/fapi/v1/order',dict(symbol='BTCUSDT',newClientOrderId='other'));self.store.update('other','FILLED')
        self.assertEqual(self.report()['ws_unknown_without_business_resolution'],1)
        self.store.reserve('owned','/fapi/v1/order',p);self.store.update('owned','FILLED')
        self.assertEqual(self.report()['ws_unknown_without_business_resolution'],1)
        session=dict(id='s',entry_id='owned',symbol='BTCUSDT',account_ref='b'*64)
        with self.store.db:self.store.db.execute('INSERT INTO managed_sessions VALUES (?,?,0)',('s',json.dumps(session)))
        self.assertEqual(self.report()['ws_unknown_without_business_resolution'],1)
        session['account_ref']=self.service.account_ref
        with self.store.db:self.store.db.execute('UPDATE managed_sessions SET body=?',(json.dumps(session),))
        r=self.report();self.assertEqual(r['ws_unknown_without_business_resolution'],0);self.assertEqual(r['ws_delivery_history']['UNKNOWN'],1)
        self.assertEqual(r['health'],'NO_LOCAL_BLOCKER_OBSERVED')

    def test_cli_help_handles_non_utf8_windows_output(self):
        env=dict(os.environ,PYTHONIOENCODING='cp1252')
        result=subprocess.run([sys.executable,'-m','agentrader','commands','--help'],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
        self.assertIn('--order-transport',result.stdout.decode('utf-8'))

    @unittest.skipUnless(all(importlib.util.find_spec(m) is not None for m in ('fastapi','httpx')),'Optional web dependencies missing')
    def test_api_operations_and_metrics_require_auth_and_share_service(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.service import ApplicationService
        from agentrader.application.settings import WebSettings
        settings=WebSettings(self.root/'app.db',self.path,'x'*40,'local:test')
        service=ApplicationService(settings,clock=lambda:self.now)
        service.operations=self.report
        self.unresolved()
        with TestClient(create_app(settings,service=service),base_url='http://127.0.0.1') as client:
            for url in ('/api/operations','/api/operations/metrics'):
                self.assertEqual(client.get(url).status_code,401)
                self.assertEqual(client.get(url,headers={'Authorization':'Bearer wrong'}).status_code,401)
            headers={'Authorization':'Bearer '+'x'*40}
            r=client.get('/api/operations',headers=headers);self.assertEqual(r.status_code,200);self.assertEqual(r.json(),self.report())
            metrics=client.get('/api/operations/metrics',headers=headers)
            self.assertEqual(metrics.status_code,200);self.assertEqual(metrics.text,prometheus(self.report()))
            self.assertEqual(r.headers['Cache-Control'],'no-store')
