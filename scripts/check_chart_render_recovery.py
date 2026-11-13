"""A1: isolated real Chromium + native chart series, no API/account/storage calls."""
import json
import socket
import subprocess
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    server = subprocess.Popen(
        ['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', str(port), '--strictPort'],
        cwd=ROOT / 'frontend', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        for _ in range(100):
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1', port)) == 0:
                    break
            if server.poll() is not None:
                raise RuntimeError('Isolated Vite server exited')
            time.sleep(.1)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1200, 'height': 800})
            errors, blocked = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))

            def route(request_route):
                url = request_route.request.url
                if not url.startswith(f'http://127.0.0.1:{port}/') or '/api/' in url:
                    blocked.append(url)
                    request_route.abort()
                else:
                    request_route.continue_()

            page.route('**/*', route)
            page.goto(f'http://127.0.0.1:{port}/tests/browser/render-recovery.html')
            page.wait_for_function('window.__a1?.done === true', timeout=60000)
            result = page.evaluate('window.__a1')
            result.update(browser=browser.version, mode='HEADLESS_CHROMIUM_NATIVE_SERIES_WITH_CONTROLLED_WRITE_FAULTS',
                          date='2026-11-09', page_errors=errors, blocked_requests=blocked,
                          scope='Shared production recovery/writer and real native series; isolated harness, not full App or screenshot/native-touch acceptance',
                          account_requests=0, user_workspace_writes=0)
            result['passed'] = result['passed'] and not errors and not blocked
            browser.close()
        path = ROOT / 'reports/chart-render-recovery-browser-20261109.json'
        path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, indent=2))
        return 0 if result['passed'] else 1
    finally:
        server.terminate()
        server.wait(timeout=10)


if __name__ == '__main__':
    raise SystemExit(main())
