"""A2: real App/Chromium, controlled WebSocket, packets from production FeedState."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agentrader.market_feed import FeedState, FeedUnavailable

# Read-only observation of this pinned React version; no production debug API.
OBSERVE = """() => {
 const root=document.getElementById('root');
 const key=Object.keys(root).find(k=>k.startsWith('__reactContainer$'));
 if(!key) return null;
 const walk=f=>{if(!f)return null;if(f.type?.name==='App')return f;return walk(f.child)||walk(f.sibling);};
 const app=walk(root[key].stateNode.current);if(!app)return null;
 let h=app.memoizedState,view,candles,volume;
 while(h){const v=h.memoizedState;if(v&&Array.isArray(v.candles))view=v;
 const ref=v?.current;
 if(ref&&typeof ref.seriesType==='function'){
 if(ref.seriesType()==='Candlestick')candles=ref.data();
 if(ref.seriesType()==='Histogram')volume=ref.data();}h=h.next;}
 return view?{view,candles,volume}:null;
}"""


def main():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    server = subprocess.Popen(
        ['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', str(port), '--strictPort'],
        cwd=ROOT/'frontend', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    result = {'date': '2026-11-09', 'passed': False, 'cases': [], 'page_errors': [], 'unexpected_requests': [],
              'mode': 'HEADLESS_CHROMIUM_FULL_APP_CONTROLLED_WEBSOCKET_PRODUCTION_FEEDSTATE',
              'scope': 'App event handlers and native series; intercepted transport, not live exchange/TCP outage or raster acceptance',
              'account_requests': 0, 'user_workspace_writes': 0}
    try:
        for _ in range(100):
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1', port)) == 0:
                    break
            if server.poll() is not None:
                raise RuntimeError('Vite exited')
            time.sleep(.1)
        now = [time.time()]
        step = 900
        start = int(now[0]) // step * step
        market = {'symbol': 'BTCUSDT', 'base_asset': 'BTC', 'quote_asset': 'USDT', 'tick_size': '0.1', 'contract_type': 'PERPETUAL'}

        def candle(t, closed=False, close=105, volume=10):
            return {'time': t, 'open': 100, 'high': 120, 'low': 90, 'close': close,
                    'volume': volume, 'quote_volume': 1000, 'close_time': (t+step)*1000-1, 'closed': closed}

        rows = [candle(start-(119-i)*step, i<119) for i in range(120)]
        history = {'server_time': int(now[0]*1000), 'market': market,
                   'quality': {'state': 'OK', 'missing_bars': 0}, 'candles': rows}
        feed = FeedState('BTCUSDT', '15m', clock=lambda: now[0])
        feed.seed(copy.deepcopy(history))

        def event(t=start, closed=False, close=106, volume=11):
            return {'e': 'kline', 'E': int(now[0]*1000), 's': 'BTCUSDT', 'k': {
                's': 'BTCUSDT', 'i': '15m', 't': t*1000, 'T': (t+step)*1000-1,
                'x': closed, 'o': '100', 'h': '120', 'l': '90', 'c': str(close),
                'v': str(volume), 'q': '1100', 'n': 1, 'V': '0', 'Q': '0'}}

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            result['browser'] = browser.version
            page = browser.new_page(viewport={'width': 1400, 'height': 950})
            page.on('pageerror', lambda e: result['page_errors'].append(str(e)))
            page.clock.install(time=datetime.fromtimestamp(now[0], timezone.utc))
            sockets = []
            page.route_web_socket('**/api/market-stream*', lambda ws: sockets.append(ws))
            workspace = {'revision': 0, 'preferences': {'symbol': 'BTCUSDT', 'interval': '15m'}}

            def route(r):
                path = urlparse(r.request.url).path
                if not r.request.url.startswith(f'http://127.0.0.1:{port}/'):
                    result['unexpected_requests'].append(r.request.url)
                    return r.abort()
                if path == '/api/markets':
                    return r.fulfill(json={'markets': [market]})
                if path == '/api/workspaces/main':
                    return r.fulfill(json=workspace)
                if path == '/api/workspaces/main/drawings':
                    return r.fulfill(json={'drawings': []})
                if path == '/api/candles':
                    return r.fulfill(json={'candles': [], 'has_more': False})
                if path.startswith('/api/'):
                    result['unexpected_requests'].append(path)
                    return r.abort()
                return r.continue_()

            page.route('**/*', route)
            page.goto(f'http://127.0.0.1:{port}/')
            page.wait_for_function('document.querySelector(".connection") !== null')
            for _ in range(100):
                if sockets:
                    break
                page.wait_for_timeout(50)
            assert sockets, 'No WebSocket'
            status = page.locator('.connection')

            def send(packet):
                sockets[-1].send(json.dumps(packet))
                page.wait_for_timeout(80)

            def verify(name, expected_status, expected_rows=None):
                assert status.inner_text().strip() == expected_status, name+': '+status.inner_text().strip()
                observed = page.evaluate(OBSERVE)
                assert observed is not None, 'React observation unavailable'
                actual = observed['view']['candles']
                if expected_rows is not None:
                    assert actual == expected_rows, name+' state mismatch'
                assert len(observed['candles']) == len(actual) == len(observed['volume'])
                for c, v, expected in zip(observed['candles'], observed['volume'], actual):
                    assert all(c[k] == expected[k] for k in ('time', 'open', 'high', 'low', 'close'))
                    assert v['time'] == expected['time'] and v['value'] == expected['volume']
                result['cases'].append({'name': name, 'passed': True, 'status': observed['view']['status'], 'candles': len(actual)})
                return observed

            send(feed.packet())
            verify('initial_snapshot_syncing', 'Mumlar eşitleniyor', feed.rows)
            now[0] += 1
            feed.apply(event())
            first = feed.packet(feed.generation)
            send(first)
            verify('fresh_update_live', 'Canlı', feed.rows)
            duplicate = copy.deepcopy(first)
            duplicate['tail'][-1]['close'] = 119
            send(duplicate)
            verify('same_sequence_cannot_change_price', 'Canlı', feed.rows)
            stale = copy.deepcopy(first)
            stale['sequence'] -= 1
            stale['tail'][-1]['close'] = 118
            send(stale)
            verify('older_sequence_rejected', 'Canlı', feed.rows)
            # Silence uses the actual App interval watchdog, with virtual browser time.
            page.clock.fast_forward(13000)
            verify('silent_transport_becomes_stale', 'Veri gecikiyor', feed.rows)
            # An old LIVE heartbeat must not temporarily resurrect stale data.
            send(first)
            verify('delayed_live_heartbeat_stays_stale', 'Veri gecikiyor', feed.rows)
            sockets[-1].close(code=1011, reason='A2 controlled disconnect')
            verify('socket_close_marks_reconnecting', 'Yeniden bağlanıyor', feed.rows)
            old_count = len(sockets)
            page.clock.fast_forward(2000)
            for _ in range(100):
                if len(sockets) > old_count:
                    break
                page.wait_for_timeout(30)
            assert len(sockets) > old_count, 'Reconnect did not open a new WebSocket'
            # Recover a missing bar by REST seed, not by synthesizing a candle.
            now[0] += 15
            resync = copy.deepcopy(history)
            resync['server_time'] = int(now[0]*1000)
            resync['candles'][-1] = candle(start, False, 108, 12)
            feed.seed(resync)
            send(feed.packet())
            verify('reconnected_snapshot_syncing', 'Mumlar eşitleniyor', feed.rows)
            send(first)
            verify('old_generation_rejected_after_resync', 'Mumlar eşitleniyor', feed.rows)
            now[0] = max(now[0]+1, start+step)
            page.clock.set_system_time(datetime.fromtimestamp(now[0], timezone.utc))
            feed.apply(event(closed=True, close=109, volume=13))
            closed = copy.deepcopy(feed.rows[-1])
            # Deliberately withhold the close packet: next tail must contain both bars.
            now[0] += 1
            feed.apply(event(t=start+step, close=102, volume=1))
            tail = feed.packet(feed.generation)
            send(tail)
            verify('close_and_next_open_in_one_tail', 'Canlı', feed.rows)
            assert feed.rows[-2] == closed and feed.rows[-2]['closed']
            reopen = copy.deepcopy(tail)
            reopen['sequence'] += 1
            reopen['tail'][0]['closed'] = False
            send(reopen)
            verify('closed_candle_cannot_reopen', 'Canlı', feed.rows)
            # FeedState must refuse gaps and demand a resync before publishing.
            now[0] = max(now[0]+1, start+3*step)
            page.clock.set_system_time(datetime.fromtimestamp(now[0], timezone.utc))
            try:
                feed.apply(event(t=start+3*step))
                raise AssertionError('Missing close/gap accepted')
            except FeedUnavailable:
                feed.status('RECONNECTING')
            send(feed.packet(feed.generation))
            verify('gap_requires_resync_not_fake_live', 'Yeniden bağlanıyor', feed.rows)
            resync['candles'] = [*feed.rows[:-1], candle(start+step, True), candle(start+2*step, True), candle(start+3*step)]
            resync['server_time'] = int(now[0]*1000)
            feed.seed(resync)
            send(feed.packet())
            verify('rest_resync_restores_missing_bars', 'Mumlar eşitleniyor', feed.rows)
            now[0] += 1
            feed.apply(event(t=start+3*step, close=107))
            send(feed.packet(feed.generation))
            verify('fresh_after_gap_returns_live', 'Canlı', feed.rows)
            result['passed'] = not result['page_errors'] and not result['unexpected_requests']
            browser.close()
    except Exception as error:
        result['error'] = str(error)
    finally:
        server.terminate()
        server.wait(timeout=10)
    (ROOT/'reports/chart-connection-browser-20261109.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
