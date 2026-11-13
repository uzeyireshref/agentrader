"""A3: full App/native Chromium with delayed HTTP responses and controlled WS."""
import copy
import json
from pathlib import Path
import socket
import subprocess
import time
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
from check_chart_connection import OBSERVE

ROOT = Path(__file__).resolve().parents[1]


def main():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    server = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', str(port), '--strictPort'], cwd=ROOT/'frontend', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    result = {'date': '2026-11-09', 'passed': False, 'cases': [], 'page_errors': [], 'unexpected_requests': [],
              'scope': 'Full App/native series; controlled delayed HTTP and intercepted WebSocket; not live exchange or real multi-tab persistence',
              'account_requests': 0, 'user_workspace_writes': 0}
    try:
        for _ in range(100):
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1', port)) == 0:
                    break
            time.sleep(.1)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            result['browser'] = browser.version
            page = browser.new_page(viewport={'width': 1400, 'height': 950})
            page.on('pageerror', lambda e: result['page_errors'].append(str(e)))
            sockets, pending_history, pending_drawings, bootstrap = [], [], [], []
            delay_drawings = [None]
            workspace = {'revision': 0, 'preferences': {'symbol': 'BTCUSDT', 'interval': '15m'}}
            markets = [{'symbol': s, 'base_asset': s[:-4], 'quote_asset': 'USDT', 'tick_size': '0.1', 'contract_type': 'PERPETUAL'} for s in ['BTCUSDT', 'ETHUSDT']]
            page.route_web_socket('**/api/market-stream*', lambda ws: sockets.append(ws))

            def drawing(symbol):
                return {'drawing_id': symbol+'-test', 'revision': 1, 'deleted': False, 'geometry': {
                    'kind': 'horizontal', 'symbol': symbol, 'price_source': 'LAST_PRICE',
                    'anchors': [{'time': 1800000000, 'price': 100}], 'label': symbol+' çizimi'}}

            def route(r):
                path = urlparse(r.request.url).path
                query = parse_qs(urlparse(r.request.url).query)
                if not r.request.url.startswith(f'http://127.0.0.1:{port}/'):
                    result['unexpected_requests'].append(r.request.url)
                    return r.abort()
                if path == '/api/markets':
                    return r.fulfill(json={'markets': markets})
                if path == '/api/workspaces/main':
                    if r.request.method == 'GET' and not bootstrap:
                        bootstrap.append(r)
                        return
                    return r.fulfill(json=workspace)
                if path == '/api/workspaces/main/drawings':
                    symbol = query['symbol'][0]
                    if symbol == delay_drawings[0]:
                        pending_drawings.append((r, symbol))
                        return
                    return r.fulfill(json={'drawings': [drawing(symbol)]})
                if path == '/api/candles':
                    pending_history.append(r)
                    return
                if path.startswith('/api/'):
                    result['unexpected_requests'].append(path)
                    return r.abort()
                return r.continue_()

            page.route('**/*', route)
            page.goto(f'http://127.0.0.1:{port}/')

            def settle():
                page.wait_for_timeout(120)

            def wait_for(predicate):
                for _ in range(150):
                    if predicate():
                        return
                    page.wait_for_timeout(30)
                raise AssertionError('Expected test request/socket did not arrive')

            wait_for(lambda: bootstrap and sockets)
            select = page.get_by_label('Sözleşme seç')
            select.select_option('ETHUSDT')
            settle()
            bootstrap[0].fulfill(json=workspace)
            settle()
            assert select.input_value() == 'ETHUSDT', 'Delayed bootstrap overrode user market selection'
            result['cases'].append({'name': 'delayed_workspace_cannot_override_user_market', 'passed': True})

            def rows(symbol='ETHUSDT', interval='15m', count=150):
                step = {'15m': 900, '1h': 3600, '4h': 14400}[interval]
                base = 100 if symbol == 'ETHUSDT' else 1000
                return [{'time': 1800000000+i*step, 'open': base+i, 'high': base+i+10, 'low': base+i-10, 'close': base+i+5, 'volume': i+10, 'quote_volume': 1000, 'close_time': (1800000000+(i+1)*step)*1000-1, 'closed': i<count-1} for i in range(count)]

            def packet(symbol, interval, candles, sequence=1, kind='snapshot', **extra):
                return dict(type=kind, symbol=symbol, interval=interval, generation=1, sequence=sequence, status='LIVE', received_at=int(time.time()*1000), **({'candles': candles} if kind=='snapshot' else {}), **extra)

            def send(p):
                sockets[-1].send(json.dumps(p))
                settle()

            def verify(name, symbol, interval, expected):
                data = page.evaluate(OBSERVE)
                assert data and data['view']['symbol'] == symbol and data['view']['interval'] == interval, name+' wrong context'
                assert data['view']['candles'] == expected, name+' state mismatch'
                assert len(data['candles']) == len(expected) == len(data['volume']), name+' series lengths'
                for c, v, e in zip(data['candles'], data['volume'], expected):
                    assert all(c[k] == e[k] for k in ['time', 'open', 'high', 'low', 'close']), name+' OHLC mismatch'
                    assert v['time'] == e['time'] and v['value'] == e['volume'], name+' volume mismatch'
                result['cases'].append({'name': name, 'passed': True, 'symbol': symbol, 'interval': interval, 'candles': len(expected)})

            current = rows()
            send(packet('ETHUSDT', '15m', current))
            verify('selected_market_after_delayed_bootstrap', 'ETHUSDT', '15m', current)
            # A delayed BTC drawing read cannot overwrite ETH drawings.
            delay_drawings[0] = 'BTCUSDT'
            select.select_option('BTCUSDT')
            wait_for(lambda: pending_drawings)
            select.select_option('ETHUSDT')
            settle()
            pending_drawings.pop()[0].fulfill(json={'drawings': [drawing('BTCUSDT')]})
            settle()
            assert page.locator('.drawing-list b').all_text_contents() == ['ETHUSDT çizimi']
            send(packet('ETHUSDT', '15m', current))
            verify('rapid_market_return_and_delayed_drawing_read', 'ETHUSDT', '15m', current)
            # Rapid timeframe changes; wrong-context packets arrive on the active socket.
            page.get_by_role('button', name='1 sa', exact=True).click()
            settle()
            page.get_by_role('button', name='4 sa', exact=True).click()
            settle()
            four = rows(interval='4h')
            send(packet('ETHUSDT', '4h', four))
            send(packet('ETHUSDT', '1h', rows(interval='1h'), sequence=99))
            send(packet('BTCUSDT', '4h', rows('BTCUSDT', '4h'), sequence=99))
            verify('rapid_timeframes_and_wrong_context_packets', 'ETHUSDT', '4h', four)
            # Request history, then revise the current candle and append a new one.
            older_button = page.locator('.chart-bottom button.text-button')
            older_button.click()
            wait_for(lambda: pending_history)
            history_route = pending_history.pop(0)
            assert older_button.is_disabled(), 'Parallel history fetch allowed'
            result['cases'].append({'name': 'pending_history_blocks_duplicate_clicks', 'passed': True})
            revised = {**four[-1], 'close': four[-1]['close']+1, 'closed': True, 'volume': 999}
            new = {**four[-1], 'time': four[-1]['time']+14400, 'close_time': four[-1]['close_time']+14400000, 'volume': 1}
            current = four[:-1]+[revised, new]
            send(packet('ETHUSDT', '4h', None, sequence=2, kind='update', tail=[revised, new]))
            verify('live_rollover_while_history_pending', 'ETHUSDT', '4h', current)
            older = [{**four[0], 'time': four[0]['time']-(3-i)*14400, 'close_time': four[0]['close_time']-(3-i)*14400000, 'closed': True} for i in range(3)]
            history_route.fulfill(json={'candles': older+four, 'has_more': True})
            settle()
            current = older+current
            verify('history_merge_preserves_live_close_and_new_bar', 'ETHUSDT', '4h', current)
            # Failed request must leave data intact and allow retry.
            older_button.click()
            wait_for(lambda: pending_history)
            pending_history.pop(0).fulfill(status=503, json={'error': 'A3 controlled failure'})
            settle()
            assert page.locator('.history-error').count() == 1 and older_button.is_enabled()
            verify('history_failure_preserves_data_and_allows_retry', 'ETHUSDT', '4h', current)
            older_button.click()
            wait_for(lambda: pending_history)
            extra = {**older[0], 'time': older[0]['time']-14400, 'close_time': older[0]['close_time']-14400000}
            pending_history.pop(0).fulfill(json={'candles': [extra], 'has_more': True})
            settle()
            current = [extra]+current
            assert page.locator('.history-error').count() == 0
            verify('history_retry_succeeds_without_duplicates', 'ETHUSDT', '4h', current)
            # Late old-market history is delivered after active context changed.
            older_button.click()
            wait_for(lambda: pending_history)
            old_request = pending_history.pop(0)
            delay_drawings[0] = None
            select.select_option('BTCUSDT')
            settle()
            btc = rows('BTCUSDT', '4h')
            send(packet('BTCUSDT', '4h', btc))
            old_request.fulfill(json={'candles': older, 'has_more': True})
            settle()
            assert page.locator('.history-error').count() == 0 and older_button.is_enabled()
            verify('late_old_market_history_cannot_replace_new_market', 'BTCUSDT', '4h', btc)
            # The same cancellation isolation must hold for timeframe changes.
            older_button.click()
            wait_for(lambda: pending_history)
            old_request = pending_history.pop(0)
            page.get_by_role('button', name='15 dk', exact=True).click()
            settle()
            btc = rows('BTCUSDT', '15m')
            send(packet('BTCUSDT', '15m', btc))
            old_request.fulfill(status=500, json={'error': 'old timeframe failure'})
            settle()
            assert page.locator('.history-error').count() == 0 and older_button.is_enabled()
            verify('late_old_timeframe_failure_cannot_mark_new_view', 'BTCUSDT', '15m', btc)
            result['passed'] = not result['page_errors'] and not result['unexpected_requests']
            browser.close()
    except Exception as error:
        result['error'] = str(error)
    finally:
        server.terminate()
        server.wait(timeout=10)
    (ROOT/'reports/chart-context-races-browser-20261109.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
