"""Outcome, bounded reads and recovery invariants over temporary stores only."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import Mock, patch

import test_bot_terminal as terminal
from agentrader.application.bot_worker import monitor, process_bot_once, uncertain_financial
from agentrader.application.bot_inbox import BotError
from agentrader.application.queries import execution_status
from agentrader.application.operations import operation_status
from agentrader.migrations import connect, migrate, MIGRATIONS
from agentrader.shared.state import StateStore
from agentrader.shared.exchange import ExchangeError
from agentrader.shared.legacy_execution import attest


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.f=terminal.BotTerminalTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.store,self.inbox,self.engine=self.f.store,self.f.inbox,self.f.engine

    def test_summary_is_one_query_and_never_reads_payload_or_result(self):
        self.f.preview()
        count=[0,0]
        def connection(path):
            db=connect(path);count[0]+=1
            db.set_trace_callback(lambda sql:count.__setitem__(1,count[1]+1) if sql.startswith('SELECT') else None)
            def authorize(action,table,column,*rest):
                return sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_READ and column in ('payload','result') else sqlite3.SQLITE_OK
            db.set_authorizer(authorize);return db
        with patch('agentrader.application.bot_inbox.connect',side_effect=connection):rows=self.inbox.recent(summary=True)
        self.assertEqual(count,[1,1]);self.assertFalse(rows[0]['result_loaded']);self.assertIsNone(rows[0]['result'])
        self.assertEqual(self.inbox.recent()[0]['result'],self.inbox.show(rows[0]['job_id'])['result'])

    def test_detail_still_rejects_tampered_result(self):
        review=self.f.preview()
        with closing(connect(self.f.settings.application_database)) as db,db:db.execute("UPDATE app_bot_jobs SET result='{}' WHERE job_id=?",(review['job_id'],))
        self.assertFalse(self.inbox.recent(summary=True)[0]['result_loaded'])
        with self.assertRaisesRegex(BotError,'INTEGRITY'):self.inbox.show(review['job_id'])

    def test_operation_history_filter_precedes_limit_and_never_removes_snapshots(self):
        review=self.f.preview()
        for i in range(105):
            job=self.f.job('SNAPSHOT',{'symbol':'BTCUSDT'},'background-'+str(i))
            self.inbox.claim();self.inbox.finish(job['job_id'],result={'observed_at':i})
        self.assertEqual(len(self.inbox.recent(summary=True)),100)
        for summary in (False,True):
            rows=self.inbox.recent(summary=summary,include_snapshots=False)
            self.assertEqual([r['job_id'] for r in rows],[review['job_id']])
        self.assertEqual(self.inbox.show(job['job_id'])['result'],{'observed_at':104})
        self.assertEqual(self.inbox.show(review['job_id'])['result'],review['result'])

    def test_worker_queue_status_counts_only_current_owner_pending_and_running(self):
        from dataclasses import replace
        from agentrader.application.bot_inbox import BotInbox
        self.f.job('CONTEXT',{},'running');self.inbox.claim()
        self.f.job('SNAPSHOT',{'symbol':'BTCUSDT'},'pending')
        other=BotInbox(replace(self.f.settings,owner='another-owner'))
        other.accept(dict(request_id='other-pending',action='CONTEXT',payload={}))
        self.inbox.pulse(False,'EXECUTION_BUSY');status=self.inbox.status()
        self.assertEqual(status['queue']['pending'],1);self.assertEqual(status['queue']['running'],1)
        self.assertGreaterEqual(status['queue']['oldest_pending_age_seconds'],0)
        self.assertEqual(status['error_code'],'EXECUTION_BUSY');self.assertFalse(status['execution_enabled'])

    def test_migration_preserves_queue_and_rejects_malformed_legacy_schema(self):
        job=self.f.job('CONTEXT',{});migrate(self.f.settings.application_database)
        self.assertEqual(self.inbox.show(job['job_id'])['state'],'PENDING')
        path=self.f.root/'malformed.db'
        with closing(connect(path)) as db,db:db.execute('CREATE TABLE app_bot_jobs(job_id TEXT)')
        with self.assertRaisesRegex(ValueError,'SCHEMA_MISMATCH'):migrate(path)
        with closing(connect(path)) as db:self.assertEqual(db.execute('PRAGMA table_info(app_bot_jobs)').fetchone()['name'],'job_id')

    def test_all_entrypoints_reject_unverified_context_without_relabelling(self):
        path=self.f.root/'legacy.db'
        store=StateStore(path)
        with store.db:
            store.db.execute("INSERT INTO control VALUES('plan_owner','owner')")
            store.db.execute('DROP TABLE execution_namespace')
        store.close();before=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'CONTEXT_UNVERIFIED'):StateStore(path)
        self.assertEqual(execution_status(path,'owner')['storage'],'CONTEXT_UNVERIFIED')
        self.assertEqual(operation_status(path,'owner')['storage'],'CONTEXT_UNVERIFIED')
        self.assertEqual(path.read_bytes(),before)
        review=attest(path,'owner','a'*64,context='usdm-demo');self.assertFalse(review['applied'])
        self.assertEqual(path.read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'OWNER_MISMATCH'):attest(path,'other','a'*64,context='usdm-demo',apply=True)
        applied=attest(path,'owner','a'*64,context='usdm-demo',apply=True)
        self.assertTrue(Path(applied['backup']).exists())
        with closing(sqlite3.connect(applied['backup'])) as db:
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='execution_namespace'").fetchone())
        opened=StateStore(path);opened.close()

    def setup_monitor(self, error):
        self.store.save_session(dict(id='session',active=True,symbol='BTCUSDT'))
        self.engine.owned_session=Mock()
        runner=Mock();runner.manage.side_effect=error
        return runner

    def test_read_timeout_retries_only_after_readonly_barrier(self):
        runner=self.setup_monitor([ExchangeError('do not expose',delivery_status='READ_FAILED',retryable=True),{'state':'MANAGING'},{'state':'MANAGING'}])
        with patch('agentrader.bot.account_runtime.runner_for',return_value=runner):
            monitor(self.engine,{});monitor(self.engine,{})
        self.assertEqual([c.kwargs['execute'] for c in runner.manage.call_args_list],[True,False,True])
        self.assertIsNone(self.store.db.execute("SELECT 1 FROM control WHERE name='bot_monitor_paused:session'").fetchone())

    def test_unknown_mutation_and_exhausted_read_retries_stay_paused(self):
        runner=self.setup_monitor(ExchangeError('hidden',delivery_status='READ_FAILED',retryable=True))
        with patch('agentrader.bot.account_runtime.runner_for',return_value=runner):
            for _ in range(4):monitor(self.engine,{})
            count=runner.manage.call_count;monitor(self.engine,{})
            self.assertEqual(runner.manage.call_count,count)
        pause=self.store.db.execute("SELECT value FROM control WHERE name='bot_monitor_paused:session'").fetchone()
        self.assertEqual(json.loads(pause[0])['reason'],'READ_RETRIES_EXHAUSTED')

    def test_unknown_cancel_prevents_read_retry(self):
        runner=self.setup_monitor(ExchangeError('hidden',delivery_status='READ_FAILED',retryable=True))
        with self.store.db:
            self.store.db.execute('CREATE TABLE IF NOT EXISTS v2_cancellations(command_id TEXT,body TEXT,state TEXT)')
            self.store.db.execute("INSERT INTO v2_cancellations VALUES('cancel','{}','UNKNOWN')")
        self.assertTrue(uncertain_financial(self.store))
        with patch('agentrader.bot.account_runtime.runner_for',return_value=runner):monitor(self.engine,{})
        self.assertIsNotNone(self.store.db.execute("SELECT 1 FROM control WHERE name='bot_monitor_paused:session'").fetchone())

    def test_errors_have_safe_correlation_and_do_not_export_exception_text(self):
        job=self.f.job('CONTEXT',{})
        with patch.object(self.engine,'perform',side_effect=ExchangeError('SECRET_CANARY',-1007,delivery_status='UNKNOWN')):
            result=process_bot_once(self.inbox,factory=self.f.factory)
        self.assertEqual(result['state'],'FAILED');self.assertEqual(result['result']['diagnostic']['correlation_id'],job['job_id'])
        self.assertNotIn('SECRET_CANARY',json.dumps(result))

    def test_v2_management_does_not_scan_all_intents(self):
        with patch.object(self.store,'intents',side_effect=AssertionError('full scan')):
            self.f.test_plan_preview_consent_opens_existing_runner_once()

    def test_history_page_checkpoint_is_after_durable_page_and_never_reposts(self):
        from test_query_commands import QueryExchange
        from agentrader.bot.exchange_commands import ExchangeCommands
        x=QueryExchange();commands=ExchangeCommands(x,self.store,'owner');seen=[]
        commands.read_checkpoint=lambda:seen.append(self.store.db.execute('SELECT count(*) FROM exchange_read_pages').fetchone()[0])
        request=dict(schema_version=1,client_command_id='history-checkpoint',environment='demo',exchange='binance',product='USD-M',account_ref=commands.account_ref,operation='QUERY_HISTORY',scope={'symbol':'BTCUSDT'},parameters=dict(kind='ORDERS',start_ms=int(__import__('time').time()*1000)-1000,end_ms=int(__import__('time').time()*1000)-1,page_size=10,max_requests=5))
        prepared=commands.prepare(request);result=commands.apply(prepared['command_id'],prepared['digest'])
        self.assertEqual(result['state'],'APPLIED');self.assertEqual(seen,[1,2])
        count=len(x.calls);commands.apply(prepared['command_id'],prepared['digest']);self.assertEqual(len(x.calls),count)

    def test_frontend_operations_match_backend_mutation_contract(self):
        import re
        from agentrader.bot.exchange_commands import OPERATIONS
        source=(Path(__file__).resolve().parents[1]/'frontend/src/BotLiveCommands.tsx').read_text(encoding='utf-8')
        choices=re.search(r'const\s+choices\s*=\s*(.*?);',source,re.S).group(1)
        operations=re.findall(r'''\[\s*["']([A-Z_]+)["']''',choices)
        self.assertEqual(len(operations),len(set(operations)))
        self.assertTrue(set(operations)<=set(OPERATIONS))
        reads=re.search(r'const\s+readOnly\s*=\s*new Set\((.*?)\);',source,re.S).group(1)
        readonly=set(re.findall(r'''["']([A-Z_]+)["']''',reads))
        self.assertEqual(readonly,{op for op in operations if not OPERATIONS[op]['mutates']})

    def test_resume_monitor_uses_readonly_barrier_and_keeps_halt(self):
        self.engine.owned_session=Mock(return_value=dict(id='session',engine='v2',symbol='BTCUSDT',status='PROTECTED'))
        runner=Mock();runner.manage.return_value={'state':'MANAGING'}
        with self.store.db:
            self.store.db.execute("INSERT INTO control VALUES('bot_monitor_paused:session','true')")
        self.store.halt('existing halt')
        review=self.engine.review('CONTROL',dict(kind='RESUME_MONITOR',session_id='session',close_position=False),dict(session_id='session',symbol='BTCUSDT',engine='v2',state='PROTECTED'))
        job=self.f.job('PREVIEW_CONTROL',dict(kind='RESUME_MONITOR',session_id='session',close_position=False))
        self.inbox.claim();self.inbox.finish(job['job_id'],result=review)
        with patch('agentrader.bot.account_runtime.V2Runner',return_value=runner):
            result=self.engine.confirm(self.inbox,dict(review_id=job['job_id'],review_digest=review['review_digest'],account_ref=self.engine.account_ref),True)
        self.assertEqual(result['state'],'MONITOR_RESUMED');self.assertFalse(runner.manage.call_args.kwargs['execute'])
        self.assertEqual(self.store.halt_reason(),'existing halt')
        self.assertIsNone(self.store.db.execute("SELECT 1 FROM control WHERE name='bot_monitor_paused:session'").fetchone())

    def test_worker_runs_management_before_and_after_a_user_job(self):
        from agentrader.application.bot_worker import run_bot_worker
        from agentrader.shared.locking import execution_lock
        sequence=[]
        with patch('agentrader.application.bot_worker.execution_lock',side_effect=lambda path=None:execution_lock(path or self.f.root/'runtime.lock')):
            with patch('agentrader.application.bot_worker.monitor',side_effect=lambda *args:sequence.append('monitor')):
                with patch('agentrader.application.bot_worker.process_bot_once',side_effect=lambda *args,**kwargs:sequence.append('job')):
                    run_bot_worker(self.f.settings,execute=True,once=True,factory=self.f.factory)
        self.assertEqual(sequence,['monitor','job','monitor'])

    def test_outcome_summary_survives_restart_without_loading_large_result(self):
        job=self.f.job('CONTEXT',{});self.inbox.claim()
        self.inbox.finish(job['job_id'],result={'state':'UNKNOWN','data':'x'*100000})
        from agentrader.application.bot_inbox import BotInbox
        row=BotInbox(self.f.settings).recent(summary=True)[0]
        self.assertEqual(row['result_state'],'UNKNOWN');self.assertIsNone(row['result'])
        self.assertLess(len(json.dumps(row)),1000)

    def test_outcome_migration_backfills_old_jobs_without_touching_result(self):
        import agentrader.migrations as migrations
        from agentrader.application.bot_inbox import checksum,encoded
        path=self.f.root/'pre-outcomes.db'
        with patch.object(migrations,'MIGRATIONS',migrations.MIGRATIONS[:-1]):migrations.migrate(path)
        body=encoded({'state':'FINAL_WITH_ERRORS','data':'keep'})
        with closing(connect(path)) as db,db:
            db.execute('INSERT INTO app_bot_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',('old','owner','CONTEXT','{}',checksum(['owner','CONTEXT',{}]),'SUCCEEDED',1,1,body,checksum(json.loads(body)),None))
        migrations.migrate(path)
        with closing(connect(path)) as db:
            self.assertEqual(db.execute('SELECT result FROM app_bot_jobs').fetchone()[0],body)
            self.assertEqual(db.execute('SELECT result_state FROM app_bot_job_outcomes').fetchone()[0],'FINAL_WITH_ERRORS')
