"""Real loopback HTTP/restart smoke check, using only isolated temporary stores."""
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, ProxyHandler, build_opener
from urllib.request import HTTPCookieProcessor
from http.cookiejar import CookieJar

ROOT = Path(__file__).resolve().parents[1]


def check_local_api(include_drawings=False):
    """Start/stop only our subprocess; no exchange keys, account or external network."""
    with tempfile.TemporaryDirectory(prefix='agentrader-web-check-') as folder:
        store = Path(folder) / 'application.db'
        execution = Path(folder) / 'execution.db'
        token = secrets.token_urlsafe(32)
        env = dict(os.environ, AGENTRADER_WEB_DATABASE=str(store),
                   AGENTRADER_EXECUTION_DATABASE=str(execution), AGENTRADER_WEB_TOKEN=token)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = 'http://127.0.0.1:' + str(port)
        opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))
        process = None

        def request(path, *, body=None, authenticated=False, extra_headers=None, method=None):
            headers = {'Content-Type': 'application/json'} if body is not None else {}
            if authenticated:
                headers['Authorization'] = 'Bearer ' + token
            headers.update(extra_headers or {})
            req = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
            try:
                with opener.open(req, timeout=2) as response:
                    return response.status, json.load(response)
            except HTTPError as exc:
                with exc:
                    return exc.code, json.load(exc)

        def start():
            nonlocal process
            process = subprocess.Popen([sys.executable, '-m', 'agentrader', 'web', 'serve', '--port', str(port)],
                                       cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('Local API exited before readiness')
                try:
                    status, body = request('/api/health')
                    if status == 200 and body['mode'] == 'LOCAL_READ_ONLY':
                        return
                except (URLError, TimeoutError, OSError):
                    pass
                time.sleep(0.05)
            raise RuntimeError('Local API readiness timed out')

        def stop():
            nonlocal process
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                process.communicate(timeout=5)
                process = None

        checks = {}
        try:
            start()
            checks['keyless_loopback_start'] = request('/api/health')[0] == 200
            checks['private_status_requires_auth'] = request('/api/status')[0] == 401
            checks['foreign_origin_rejected'] = request('/api/commands', body={}, authenticated=True,
                                                        extra_headers={'Origin': 'http://foreign.invalid'})[0] == 403
            checks['financial_action_rejected'] = request('/api/commands', authenticated=True,
                body={'request_id': 'forbidden', 'action': 'plans.run', 'payload': {}})[0] == 422
            command = {'request_id': 'smoke-inspect', 'action': 'runtime.inspect', 'payload': {}}
            status, result = request('/api/commands', body=command, authenticated=True)
            checks['http_only_queues'] = status == 202 and result['state'] == 'QUEUED' and result['attempts'] == 0
            worker = subprocess.run([sys.executable, '-m', 'agentrader', 'web', 'worker', '--once'],
                                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=10,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if worker.returncode != 0:
                raise RuntimeError('Read-only worker failed')
            result = request('/api/commands/smoke-inspect', authenticated=True)[1]
            checks['explicit_worker_completes'] = result['state'] == 'SUCCEEDED' and result['attempts'] == 1
            if include_drawings:
                geometry = {'kind': 'horizontal', 'symbol': 'BTCUSDT', 'price_source': 'LAST_PRICE',
                            'label': 'Isolated smoke level', 'anchors': [{'time': 1800000000, 'price': '100.10'}]}
                create = {'request_id': 'drawing-create', 'geometry': geometry}
                code, drawing = request('/api/workspaces/main/drawings', body=create, authenticated=True)
                checks['drawing_created'] = code == 201 and drawing['revision'] == 1
                code, duplicate = request('/api/workspaces/main/drawings', body=create, authenticated=True)
                checks['drawing_duplicate_is_single'] = duplicate['drawing_id'] == drawing['drawing_id'] and duplicate['duplicate']
                drawing_id = drawing['drawing_id']
                moved = {**geometry, 'anchors': [{'time': 1800000000, 'price': '101.10'}]}
                edit = {'request_id': 'drawing-edit', 'expected_revision': 1, 'geometry': moved}
                code, edited = request('/api/drawings/' + drawing_id, body=edit, authenticated=True, method='PATCH')
                checks['drawing_revision_update'] = code == 200 and edited['revision'] == 2
                code, _ = request('/api/drawings/' + drawing_id, body={**edit, 'request_id': 'stale-edit'},
                                  authenticated=True, method='PATCH')
                checks['stale_drawing_write_rejected'] = code == 409
                code, _ = request('/api/workspaces/main', method='PUT', authenticated=True,
                                  body={'request_id': 'workspace-save', 'expected_revision': 0,
                                        'preferences': {'symbol': 'ETHUSDT', 'interval': '4h'}})
                checks['workspace_saved'] = code == 200
                checks['browser_session_paired'] = request('/api/session', method='POST', authenticated=True)[0] == 200
            stop()
            start()
            status, repeated = request('/api/commands', body=command, authenticated=True)
            checks['restart_preserves_single_command'] = (status == 200 and repeated['duplicate'] is True
                                                         and repeated['state'] == 'SUCCEEDED' and repeated['attempts'] == 1)
            status, snapshot = request('/api/status', authenticated=True)
            checks['local_observation_not_exchange_proof'] = status == 200 and snapshot['execution']['exchange_access'] == 'NOT_CHECKED'
            checks['no_execution_store_created'] = not execution.exists()
            if include_drawings:
                code, restored = request('/api/drawings/' + drawing_id)
                checks['cookie_and_drawing_survive_restart'] = code == 200 and restored['revision'] == 2 and restored['geometry'] == moved
                code, workspace = request('/api/workspaces/main')
                checks['workspace_survives_restart'] = code == 200 and workspace['preferences'] == {'symbol': 'ETHUSDT', 'interval': '4h'}
                code, deleted = request('/api/drawings/' + drawing_id, method='DELETE',
                                        body={'request_id': 'drawing-delete', 'expected_revision': 2})
                checks['drawing_delete_is_versioned'] = code == 200 and deleted['deleted'] and deleted['revision'] == 3
                code, restored = request('/api/drawings/' + drawing_id, method='PATCH',
                                         body={'request_id': 'drawing-undo', 'expected_revision': 3, 'geometry': moved})
                checks['drawing_restore_is_new_revision'] = code == 200 and restored['revision'] == 4 and not restored['deleted']
            with closing(sqlite3.connect(store)) as db:
                checks['one_durable_command'] = db.execute('SELECT COUNT(*) FROM app_commands').fetchone()[0] == 1
        finally:
            stop()
        if not all(checks.values()):
            raise RuntimeError('Local API checks failed: ' + ', '.join(k for k, v in checks.items() if not v))
        return {'result': 'PASSED', 'checks': checks, 'uses_isolated_temporary_stores': True,
                'exchange_requests': 0, 'server_left_running': False}


if __name__ == '__main__':
    try:
        print(json.dumps(check_local_api(), indent=2))
    except Exception:
        print(json.dumps({'result': 'FAILED', 'error': 'LOCAL_API_CHECK_FAILED'}))
        raise SystemExit(1)
