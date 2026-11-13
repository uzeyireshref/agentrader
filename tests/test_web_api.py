from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from agentrader.application.service import ApplicationService
from agentrader.application.settings import WebSettings
from agentrader.application.worker import run_worker

HAS_WEB = all(importlib.util.find_spec(m) is not None for m in ('fastapi', 'httpx'))
if HAS_WEB:
    from fastapi.testclient import TestClient
    from agentrader.api.app import create_app


@unittest.skipUnless(HAS_WEB, 'Optional web/web-test dependencies not installed')
class WebAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        self.token = 'token-' + 'x' * 40
        self.settings = WebSettings(folder / 'app.db', folder / 'execution.db', self.token, 'local:test')
        self.service = ApplicationService(self.settings)
        self.client = self.enterContext(TestClient(create_app(self.settings, service=self.service), base_url='http://127.0.0.1'))
        self.auth = {'Authorization': 'Bearer ' + self.token}
        self.command = {'request_id': 'r1', 'action': 'runtime.inspect', 'payload': {}}

    def count(self):
        with closing(sqlite3.connect(self.settings.application_database)) as db, db:
            return db.execute('SELECT COUNT(*) FROM app_commands').fetchone()[0]

    def test_public_startup_and_catalog_do_not_load_binance_credentials_or_connect(self):
        with patch('agentrader.config.Config.load', side_effect=AssertionError('credentials')), \
             patch('agentrader.exchange.DemoExchange.request', side_effect=AssertionError('network')):
            response = self.client.get('/api/health')
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()['trading_commands_enabled'])
            self.assertEqual(self.client.get('/api/capabilities').json()['count'], 95)
        self.assertFalse(self.settings.execution_database.exists())
        self.assertNotIn(self.token, response.text)

    def test_private_reads_and_writes_require_authentication(self):
        for method, url in [('get', '/api/status'), ('post', '/api/commands'), ('get', '/api/commands/r1')]:
            response = getattr(self.client, method)(url)
            self.assertEqual(response.status_code, 401)
        self.assertEqual(self.count(), 0)
        self.assertEqual(self.client.get('/api/status', headers={'Authorization': 'Bearer wrong'}).status_code, 401)

    def test_without_token_only_public_routes_are_available(self):
        settings = WebSettings(self.settings.application_database, self.settings.execution_database, owner='local:test')
        with TestClient(create_app(settings), base_url='http://127.0.0.1') as client:
            self.assertFalse(client.get('/api/health').json()['private_api_enabled'])
            self.assertEqual(client.post('/api/commands', json=self.command, headers=self.auth).status_code, 503)
        self.assertEqual(self.count(), 0)

    def test_status_is_local_only_and_no_execution_db_is_created(self):
        response = self.client.get('/api/status', headers=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['execution']['exchange_access'], 'NOT_CHECKED')
        self.assertFalse(self.settings.execution_database.exists())

    def test_command_acceptance_never_executes_and_duplicate_survives_api_restart(self):
        first = self.client.post('/api/commands', json=self.command, headers=self.auth)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.json()['state'], 'QUEUED')
        with TestClient(create_app(self.settings), base_url='http://127.0.0.1') as restarted:
            repeat = restarted.post('/api/commands', json=self.command, headers=self.auth)
            self.assertEqual(repeat.status_code, 200)
            self.assertTrue(repeat.json()['duplicate'])
            self.assertEqual(repeat.json()['attempts'], 0)
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.service.queue.worker_status()['state'], 'NOT_OBSERVED')

    def test_explicit_worker_result_can_be_read_over_api(self):
        self.client.post('/api/commands', json=self.command, headers=self.auth)
        run_worker(self.service, once=True)
        result = self.client.get('/api/commands/r1', headers=self.auth)
        self.assertEqual(result.json()['state'], 'SUCCEEDED')
        self.assertEqual(result.json()['result']['execution']['storage'], 'NOT_INITIALIZED')

    def test_financial_actions_actor_spoof_and_extra_fields_are_rejected(self):
        for body in [dict(self.command, action='plans.run'), dict(self.command, actor='local:admin'),
                     dict(self.command, payload={'token': 'private-secret'}), dict(self.command, request_id='../data')]:
            response = self.client.post('/api/commands', json=body, headers=self.auth)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn('private-secret', response.text)
        self.assertEqual(self.count(), 0)

    def test_invalid_json_duplicate_fields_and_oversized_input_are_bounded(self):
        headers = self.auth | {'Content-Type': 'application/json'}
        for body in ['{broken', '{"action":"runtime.inspect","action":"plans.run","request_id":"r1","payload":{}}',
                     '{"action":"runtime.inspect","request_id":"r1","payload":NaN}', '[]']:
            self.assertEqual(self.client.post('/api/commands', content=body, headers=headers).status_code, 422)
        self.assertEqual(self.client.post('/api/commands', content='x' * 8193, headers=headers).status_code, 413)
        self.assertEqual(self.client.post('/api/commands', content='{}', headers=self.auth).status_code, 415)
        self.assertEqual(self.count(), 0)

    def test_host_and_cross_origin_requests_cannot_enqueue(self):
        for extra, status in [({'Host': 'attacker.example'}, 400), ({'Origin': 'http://attacker.example'}, 403),
                              ({'Origin': 'null'}, 403), ({'Origin': 'http://127.0.0.1:5173'}, 403)]:
            response = self.client.post('/api/commands', json=self.command, headers=self.auth | extra)
            self.assertEqual(response.status_code, status)
        self.assertEqual(self.count(), 0)
        same = self.client.post('/api/commands', json=self.command,
                                headers=self.auth | {'Origin': 'http://127.0.0.1'})
        self.assertEqual(same.status_code, 202)

    def test_storage_errors_do_not_echo_private_data_or_paths(self):
        self.settings.execution_database.write_text('private-db-content')
        response = self.client.get('/api/status', headers=self.auth)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'LOCAL_STORAGE_UNAVAILABLE')
        self.assertNotIn('private-db-content', response.text)
        self.assertNotIn(str(self.settings.execution_database), response.text)

    def test_no_trade_routes_or_private_automatic_docs(self):
        self.assertEqual(self.client.post('/api/orders', json={}, headers=self.auth).status_code, 404)
        self.assertEqual(self.client.get('/docs').status_code, 404)
        self.assertEqual(self.client.get('/openapi.json').status_code, 404)
        self.assertEqual(self.client.get('/api/commands/missing', headers=self.auth).status_code, 404)

    def test_successful_responses_are_not_cached_or_cors_enabled(self):
        response = self.client.get('/api/status', headers=self.auth)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertNotIn('access-control-allow-origin', response.headers)
