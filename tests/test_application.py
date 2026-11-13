from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agentrader.application.commands import CommandConflict, CommandNotFound, InvalidCommand
from agentrader.application.queries import StorageUnavailable
from agentrader.application.service import ApplicationService
from agentrader.application.settings import WebSettings
from agentrader.application.worker import run_worker
from agentrader.locking import execution_lock
from agentrader.state import StateStore


COMMAND = {'request_id': 'inspect-1', 'action': 'runtime.inspect', 'payload': {}}


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.settings = WebSettings(self.folder / 'app.db', self.folder / 'execution.db', 'x' * 40, 'local:test')
        self.service = ApplicationService(self.settings, clock=lambda: 100)
        self.service.initialize()

    def make_execution(self):
        store = StateStore(self.settings.execution_database)
        with store.db:
            store.db.execute("INSERT INTO control VALUES ('plan_owner','local:test')")
        store.halt('private-halt-secret')
        store.save_session({'id': 's', 'symbol': 'BTCUSDT', 'engine': 'v2', 'status': 'PROTECTED',
                            'active': True, 'plan': {'token': 'private-plan-secret'}, 'account_ref': 'private-account'})
        store.reserve('intent', '/private', {'secret': 'private-intent-secret'})
        store.runtime_health('s', {'state': 'MANAGING'}, 99)
        store.close()

    def test_settings_reject_short_secret_and_aliasing_databases(self):
        with self.assertRaises(ValueError):
            WebSettings(self.folder / 'same.db', self.folder / 'same.db')
        with self.assertRaises(ValueError):
            WebSettings(token='short')
        self.assertNotIn('x' * 40, repr(self.settings))

    def test_public_queries_do_not_load_credentials_or_create_execution_store(self):
        with patch('agentrader.config.Config.load', side_effect=AssertionError('credential load')):
            self.assertFalse(self.service.health()['trading_commands_enabled'])
            self.assertEqual(self.service.capabilities()['count'], 95)
            self.assertEqual(self.service.status()['execution']['storage'], 'NOT_INITIALIZED')
        self.assertFalse(self.settings.execution_database.exists())

    def test_status_is_sanitized_local_observation_and_does_not_write_execution_store(self):
        self.make_execution()
        before = hashlib.sha256(self.settings.execution_database.read_bytes()).hexdigest()
        status = self.service.status()
        self.assertTrue(status['execution']['entry_halted'])
        self.assertEqual(status['execution']['exchange_access'], 'NOT_CHECKED')
        self.assertEqual(status['execution']['active_sessions'][0]['monitor']['health'], 'FRESH')
        self.assertNotIn('private-', json.dumps(status))
        self.assertEqual(hashlib.sha256(self.settings.execution_database.read_bytes()).hexdigest(), before)
        other = ApplicationService(self.settings, clock=lambda: 200)
        self.assertEqual(other.status()['execution']['active_sessions'][0]['monitor']['health'], 'STALE')

    def test_incomplete_execution_schema_is_not_reported_as_ready(self):
        with closing(sqlite3.connect(self.settings.execution_database)) as db, db:
            db.execute('CREATE TABLE unrelated (id INTEGER)')
        result = self.service.status()['execution']
        self.assertEqual(result['storage'], 'INCOMPLETE_SCHEMA')
        self.assertIsNone(result['entry_halted'])

    def test_foreign_execution_owner_does_not_expose_sessions(self):
        self.make_execution()
        with closing(sqlite3.connect(self.settings.execution_database)) as db, db:
            db.execute("UPDATE control SET value='foreign' WHERE name='plan_owner'")
        status = self.service.status()['execution']
        self.assertEqual(status['storage'], 'OWNER_MISMATCH')
        self.assertEqual(status['active_sessions'], [])

    def test_invalid_local_store_is_reported_without_exception_payload(self):
        self.settings.execution_database.write_text('private-secret-not-sqlite')
        with self.assertRaises(StorageUnavailable) as caught:
            self.service.status()
        self.assertNotIn('private-secret', str(caught.exception))

    def test_command_acceptance_is_durable_and_duplicate_does_not_execute(self):
        first = self.service.accept_command(COMMAND)
        self.assertEqual(first['state'], 'QUEUED')
        restarted = ApplicationService(self.settings, clock=lambda: 101)
        restarted.initialize()
        duplicate = restarted.accept_command(COMMAND)
        self.assertTrue(duplicate['duplicate'])
        self.assertEqual(duplicate['attempts'], 0)
        self.assertIsNone(duplicate['result'])
        self.assertEqual(restarted.status()['command_worker']['state'], 'NOT_OBSERVED')

    def test_unsupported_financial_commands_and_forged_actor_are_rejected(self):
        for command in [dict(COMMAND, action='plans.run'), dict(COMMAND, payload={'execute': True}),
                        dict(COMMAND, actor='other'), dict(COMMAND, request_id='../file'), []]:
            with self.assertRaises(InvalidCommand):
                self.service.accept_command(command)
        with closing(sqlite3.connect(self.settings.application_database)) as db, db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM app_commands').fetchone()[0], 0)

    def test_actor_scope_hides_other_commands(self):
        self.service.accept_command(COMMAND)
        with self.assertRaises(CommandNotFound):
            self.service.queue.show('other', 'inspect-1')
        self.service.queue.accept('other', COMMAND)
        self.assertEqual(self.service.queue.show('other', 'inspect-1')['state'], 'QUEUED')

    def test_conflicting_stored_digest_cannot_reuse_identity(self):
        self.service.accept_command(COMMAND)
        with closing(sqlite3.connect(self.settings.application_database)) as db, db:
            db.execute("UPDATE app_commands SET digest='different'")
        with self.assertRaises(CommandConflict):
            self.service.accept_command(COMMAND)

    def test_explicit_worker_completes_command_and_restart_does_not_repeat_it(self):
        self.service.accept_command(COMMAND)
        result = run_worker(self.service, once=True)
        self.assertEqual(result['state'], 'SUCCEEDED')
        self.assertEqual(result['result']['execution']['storage'], 'NOT_INITIALIZED')
        self.assertEqual(run_worker(self.service, once=True)['state'], 'IDLE')
        self.assertEqual(self.service.command('inspect-1')['attempts'], 1)
        self.assertEqual(self.service.queue.worker_status()['health'], 'STOPPED')

    def test_crashed_read_only_claim_is_recovered_by_next_worker(self):
        self.service.accept_command(COMMAND)
        self.service.queue.claim(self.settings.owner)
        self.assertEqual(self.service.command('inspect-1')['state'], 'RUNNING')
        result = run_worker(ApplicationService(self.settings), once=True)
        self.assertEqual(result['state'], 'SUCCEEDED')
        self.assertEqual(result['attempts'], 2)

    def test_tampered_queued_financial_action_is_never_executed(self):
        self.service.accept_command(COMMAND)
        with closing(sqlite3.connect(self.settings.application_database)) as db, db:
            db.execute("UPDATE app_commands SET action='plans.run'")
        with patch.object(self.service, 'status', side_effect=AssertionError('executed')):
            self.assertEqual(run_worker(self.service, once=True)['state'], 'FAILED')
        self.assertEqual(self.service.command('inspect-1')['error_code'], 'INVALID_STORED_COMMAND')

    def test_worker_failure_stores_only_safe_error_code(self):
        self.service.accept_command(COMMAND)
        with patch.object(self.service, 'status', side_effect=StorageUnavailable('private-secret')):
            result = run_worker(self.service, once=True)
        self.assertEqual(result['state'], 'FAILED')
        self.assertNotIn('private-secret', json.dumps(result))

    def test_read_only_worker_can_coexist_with_existing_financial_execution_lock(self):
        self.service.accept_command(COMMAND)
        with execution_lock(self.folder / 'runtime.lock'):
            self.assertEqual(run_worker(self.service, once=True)['state'], 'SUCCEEDED')

    def test_second_application_worker_is_blocked(self):
        with execution_lock(self.settings.worker_lock):
            with self.assertRaises(ValueError):
                run_worker(self.service, once=True)

    def test_execution_lock_blocks_another_process(self):
        script = """from pathlib import Path
import sys
from agentrader.locking import execution_lock
try:
    with execution_lock(Path(sys.argv[1])):
        sys.exit(73)
except ValueError:
    print('BLOCKED')
"""
        lock = self.folder / 'financial.lock'
        with execution_lock(lock):
            result = subprocess.run([sys.executable, '-c', script, str(lock)], capture_output=True,
                                    text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'BLOCKED')
