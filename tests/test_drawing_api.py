import importlib.util
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from agentrader.application.settings import WebSettings
from test_drawings import line

HAS_WEB = all(importlib.util.find_spec(m) is not None for m in ('fastapi', 'httpx'))
if HAS_WEB:
    from fastapi.testclient import TestClient
    from agentrader.api.app import create_app
    from agentrader.api.session import COOKIE, cookie_value


@unittest.skipUnless(HAS_WEB, 'Optional web dependencies not installed')
class DrawingAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        self.settings = WebSettings(folder/'app.db', folder/'execution.db', 'a'*40, 'local:test', market_database=folder/'chart.db')
        self.client = self.enterContext(TestClient(create_app(self.settings), base_url='http://127.0.0.1'))
        self.auth = {'Authorization': 'Bearer '+self.settings.token}

    def create(self):
        return self.client.post('/api/workspaces/main/drawings', headers=self.auth,
                                json={'request_id': 'r1', 'geometry': line()})

    def test_local_drawings_do_not_require_token_or_cookie(self):
        self.assertEqual(self.client.get('/api/workspaces/main/drawings').status_code, 200)
        created = self.client.post('/api/workspaces/main/drawings', json={'request_id': 'no-key', 'geometry': line()})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.get('/api/commands/missing').status_code, 401)

    def test_without_configured_token_local_drawings_work_and_commands_stay_disabled(self):
        settings = WebSettings(self.settings.application_database, self.settings.execution_database, '', 'local:test', market_database=self.settings.market_database)
        with TestClient(create_app(settings), base_url='http://127.0.0.1') as client:
            created = client.post('/api/workspaces/main/drawings', json={'request_id': 'keyless', 'geometry': line()})
            self.assertEqual(created.status_code, 201)
            self.assertEqual(client.get('/api/workspaces/main/drawings').status_code, 200)
            self.assertEqual(client.get('/api/status').status_code, 503)
            self.assertEqual(client.post('/api/commands', json={}).status_code, 503)
            self.assertEqual(client.post('/api/workspaces/main/drawings', headers={'Origin': 'http://foreign.invalid'}, json={'request_id': 'foreign', 'geometry': line()}).status_code, 403)
        self.assertFalse(settings.execution_database.exists())

    def test_browser_pairing_uses_http_only_cookie_without_exposing_token(self):
        result = self.client.post('/api/session', headers=self.auth)
        self.assertEqual(result.status_code, 200)
        self.assertIn('HttpOnly', result.headers['set-cookie'])
        self.assertIn('SameSite=strict', result.headers['set-cookie'])
        self.assertNotIn(self.settings.token, result.text)
        self.assertEqual(self.client.get('/api/workspaces/main').status_code, 200)
        self.client.delete('/api/session')
        self.assertEqual(self.client.get('/api/commands/missing').status_code, 401)

    def test_pairing_cookie_survives_server_restart_and_token_rotation_revokes_it(self):
        self.client.post('/api/session', headers=self.auth)
        cookies = dict(self.client.cookies)
        with TestClient(create_app(self.settings), base_url='http://127.0.0.1', cookies=cookies) as restart:
            self.assertEqual(restart.get('/api/commands/missing').status_code, 404)
        rotated = WebSettings(self.settings.application_database, self.settings.execution_database, 'b'*40,
                              'local:test', market_database=self.settings.market_database)
        with TestClient(create_app(rotated), base_url='http://127.0.0.1', cookies=cookies) as restart:
            self.assertEqual(restart.get('/api/commands/missing').status_code, 401)

    def test_expired_cookie_is_rejected_server_side(self):
        value = cookie_value(self.settings, int(time.time())-1)
        self.client.cookies.set(COOKIE, value, domain='127.0.0.1', path='/api')
        self.assertEqual(self.client.get('/api/commands/missing').status_code, 401)

    def test_create_update_conflict_and_reload(self):
        created = self.create()
        self.assertEqual(created.status_code, 201)
        item = created.json()
        moved = line()
        moved['anchors'][0]['price'] = '81000'
        payload = {'request_id': 'r2', 'expected_revision': 1, 'geometry': moved}
        self.assertEqual(self.client.patch('/api/drawings/'+item['drawing_id'], json=payload, headers=self.auth).status_code, 200)
        payload['request_id'] = 'stale'
        self.assertEqual(self.client.patch('/api/drawings/'+item['drawing_id'], json=payload, headers=self.auth).status_code, 409)
        reloaded = self.client.get('/api/workspaces/main/drawings', headers=self.auth).json()['drawings'][0]
        self.assertEqual(reloaded['geometry']['anchors'][0]['price'], '81000')

    def test_actor_spoof_origin_and_extra_fields_have_no_effect(self):
        for headers, data, code in [
            (self.auth | {'Origin': 'http://foreign.invalid'}, {'request_id': 'r1', 'geometry': line()}, 403),
            (self.auth, {'request_id': 'r1', 'geometry': line(), 'owner': 'other'}, 422)]:
            self.assertEqual(self.client.post('/api/workspaces/main/drawings', json=data, headers=headers).status_code, code)
        self.assertEqual(self.client.get('/api/workspaces/main/drawings', headers=self.auth).json()['drawings'], [])

    def test_metadata_mutations_never_open_execution_or_exchange(self):
        with patch('agentrader.exchange.DemoExchange.request', side_effect=AssertionError('exchange write')):
            self.assertEqual(self.create().status_code, 201)
        self.assertFalse(self.settings.execution_database.exists())

    def test_tool_registry_declares_supported_and_future_capabilities(self):
        result = self.client.get('/api/chart-tools')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['schema'], 'chart-tool-registry/1')
        supported = self.client.get('/api/chart-tools/drawing/horizontal').json()
        self.assertTrue(supported['readable'])
        self.assertTrue(supported['editable'])
        self.assertTrue(supported['computable'])
        self.assertEqual(supported['calculation_state'], 'PURE_OFFLINE_REQUIRES_CONTEXT')
        self.assertFalse(supported['order_authority'])
        ray = self.client.get('/api/chart-tools/drawing/ray').json()
        self.assertTrue(ray['readable'])
        future = self.client.get('/api/chart-tools/drawing/fibonacci_projection').json()
        self.assertFalse(future['readable'])
        self.assertEqual(future['definition']['state'], 'DECLARED_ONLY')

    def test_unknown_tool_or_version_is_structured_blocked_error(self):
        for path in ('drawing/unknown', 'unknown/horizontal',
                     'drawing/horizontal?version=2', 'drawing/horizontal?version=0'):
            result = self.client.get('/api/chart-tools/' + path)
            self.assertEqual(result.status_code, 422)
            self.assertEqual(result.json()['error']['code'], 'BLOCKED_UNSUPPORTED_TOOL')

    def test_contract_read_preserves_legacy_crud_duplicate_and_revision(self):
        from agentrader.drawings.service import DrawingService
        with patch('agentrader.exchange.DemoExchange.request', side_effect=AssertionError('exchange access')):
            saved = self.create().json()
            path = '/api/drawings/' + saved['drawing_id']
            result = self.client.get(path + '/contract')
            self.assertEqual(result.status_code, 200)
            contract = result.json()
            self.assertEqual(contract['anchors'], saved['geometry']['anchors'])
            self.assertEqual(contract['label'], saved['geometry']['label'])
            self.assertEqual(contract['revision'], 1)
            self.assertIsNone(contract['market']['interval'])
            self.assertEqual(contract['evaluation']['state'], 'BLOCKED')
            self.assertEqual(self.client.get(path).json(), {k: v for k, v in saved.items() if k != 'duplicate'})
            repeat = self.create().json()
            self.assertTrue(repeat['duplicate'])
            self.assertEqual(repeat['revision'], 1)
            foreign = DrawingService(self.settings.application_database, 'another-owner').create('main', 'foreign', line())
            self.assertEqual(self.client.get('/api/drawings/' + foreign['drawing_id'] + '/contract').status_code, 404)
            self.assertEqual(self.client.get('/api/drawings/missing/contract').status_code, 404)
        self.assertFalse(self.settings.execution_database.exists())

    def test_contract_is_read_only_and_not_accepted_as_legacy_geometry(self):
        saved = self.create().json()
        path = '/api/drawings/' + saved['drawing_id']
        contract = self.client.get(path + '/contract').json()
        self.assertEqual(self.client.post(path + '/contract', json=contract).status_code, 405)
        result = self.client.patch(path, json={'request_id': 'new-schema', 'expected_revision': 1, 'geometry': contract})
        self.assertEqual(result.status_code, 422)
        self.assertEqual(self.client.get(path).json()['revision'], 1)
        self.assertEqual(self.client.get('/api/chart-tools', headers={'Origin': 'http://foreign.invalid'}).status_code, 403)

    def test_contract_delete_restore_and_workspace_interval_never_infer_binding(self):
        saved = self.create().json()
        path = '/api/drawings/' + saved['drawing_id']
        self.client.put('/api/workspaces/main', json={'request_id': 'workspace', 'expected_revision': 0,
                                                     'preferences': {'symbol': 'BTCUSDT', 'interval': '4h'}})
        removed = self.client.request('DELETE', path, json={'request_id': 'delete', 'expected_revision': 1})
        self.assertEqual(removed.status_code, 200)
        contract = self.client.get(path + '/contract').json()
        self.assertTrue(contract['deleted'])
        self.assertEqual(contract['revision'], 2)
        self.assertIsNone(contract['market']['interval'])
        self.client.patch(path, json={'request_id': 'restore', 'expected_revision': 2, 'geometry': saved['geometry']})
        restored = self.client.get(path + '/contract').json()
        self.assertFalse(restored['deleted'])
        self.assertEqual(restored['revision'], 3)
