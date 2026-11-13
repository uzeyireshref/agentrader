"""A4: App/native-series lifecycle, Decimal reference and SVG coordinate checks."""
import json
from pathlib import Path
import socket
import subprocess
import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from check_chart_connection import OBSERVE

ROOT = Path(__file__).resolve().parents[1]
INSPECT = OBSERVE.replace('view,candles,volume;', 'view,candles,volume,chart,lines=[],stored=[];').replace(
    'const ref=v?.current;', "if(Array.isArray(v)&&v.length&&v.every(d=>d?.geometry&&d?.drawing_id))stored=v;const ref=v?.current;if(ref?.panes)chart=ref;if(Array.isArray(ref)&&ref.length&&ref.every(s=>typeof s?.seriesType==='function'&&s.seriesType()==='Line'))lines=ref;").replace(
    'return view?{view,candles,volume}:null;', 'return view?{view,candles,volume,stored,panes:chart?.panes().length,lines:lines.map(s=>s.data())}:null;')


def main(report_name='chart-lifecycle-browser-20261109.json'):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    server = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', str(port), '--strictPort'], cwd=ROOT/'frontend', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    result = {'date': '2026-11-09', 'passed': False, 'cases': [], 'page_errors': [], 'unexpected_requests': [],
              'scope': 'Full App with controlled data; native indicator values and SVG coordinates, not raster or native-touch acceptance',
              'account_requests': 0, 'user_workspace_writes': 0}
    try:
        for _ in range(100):
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1', port)) == 0:
                    break
            time.sleep(.1)
        fixture = next(c for c in json.loads((ROOT/'reports/indicator-reference-20261109.json').read_text())['cases'] if c['name']=='time_gap')
        rows = [{'time': t, 'open': float(c), 'high': float(c)+1, 'low': float(c)-1, 'close': float(c), 'volume': i+1, 'quote_volume': float(c)*(i+1), 'close_time': t*1000+899999, 'closed': i<299} for i, (t,c) in enumerate(zip(fixture['times'], fixture['closes']))]
        price = float(fixture['closes'][133])
        drawings = []
        for kind in ['horizontal', 'zone', 'trend', 'fibonacci']:
            anchors = [{'time': fixture['times'][133], 'price': str(price)}] if kind=='horizontal' else [{'time': fixture['times'][131], 'price': str(price-2)}, {'time': fixture['times'][135], 'price': str(price+2)}]
            if kind=='trend':
                anchors[0]['time'] = (fixture['times'][132]+fixture['times'][133])/2
            if kind=='fibonacci':
                anchors.reverse()
            drawings.append({'drawing_id': kind, 'revision': 1, 'workspace_id': 'main', 'deleted': False, 'updated_at': 0,
                             'geometry': {'kind': kind, 'symbol': 'FIXTUREUSDT', 'price_source': 'LAST_PRICE', 'label': kind, 'anchors': anchors}})
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            result['browser'] = browser.version
            page = browser.new_page(viewport={'width': 1400, 'height': 1000})
            page.on('pageerror', lambda e: result['page_errors'].append(str(e)))
            sockets, history_calls = [], []
            page.route_web_socket('**/api/market-stream*', lambda ws: sockets.append(ws))
            market = {'symbol': 'FIXTUREUSDT', 'base_asset': 'FIXTURE', 'quote_asset': 'USDT', 'tick_size': '0.01', 'contract_type': 'PERPETUAL'}

            def route(r):
                path = urlparse(r.request.url).path
                if not r.request.url.startswith(f'http://127.0.0.1:{port}/'):
                    result['unexpected_requests'].append(r.request.url)
                    return r.abort()
                if path=='/api/markets':
                    return r.fulfill(json={'markets': [market]})
                if path=='/api/workspaces/main':
                    return r.fulfill(json={'revision': 0, 'preferences': {'symbol': 'FIXTUREUSDT', 'interval': '15m'}})
                if path=='/api/workspaces/main/drawings':
                    return r.fulfill(json={'drawings': drawings})
                if path=='/api/candles':
                    history_calls.append(r.request.url)
                    return r.fulfill(json={'candles': rows[:100] if len(history_calls)==1 else [], 'has_more': len(history_calls)==1})
                if path.startswith('/api/'):
                    result['unexpected_requests'].append(path)
                    return r.abort()
                return r.continue_()

            page.route('**/*', route)
            page.goto(f'http://127.0.0.1:{port}/?diagnostics=1')
            page.wait_for_function("document.querySelector('select[aria-label=\"Sözleşme seç\"]')?.value==='FIXTUREUSDT'")
            page.wait_for_timeout(200)
            assert sockets
            sockets[-1].send(json.dumps({'type': 'snapshot', 'symbol': 'FIXTUREUSDT', 'interval': '15m', 'generation': 1, 'sequence': 1, 'status': 'LIVE', 'received_at': int(time.time()*1000), 'candles': rows[100:]}))
            page.wait_for_timeout(150)
            assert page.evaluate(INSPECT)['view']['candles']==rows[100:]
            ema = page.get_by_role('button', name='EMA 20/50', exact=True)
            rsi = page.get_by_role('button', name='RSI 14', exact=True)
            ema.click();rsi.click()
            page.wait_for_timeout(100)
            assert len(page.evaluate(INSPECT)['lines'])==3
            page.locator('.chart-bottom button.text-button').click()
            page.wait_for_timeout(180)
            assert page.evaluate(INSPECT)['view']['candles']==rows
            result['cases'].append({'name': 'history_prepend_with_three_active_indicators', 'passed': True, 'candles': 300})
            page.locator('.chart-bottom button.text-button').click()
            page.wait_for_timeout(150)
            assert page.locator('.chart-bottom button.text-button').is_disabled()
            assert page.locator('.chart-bottom button.text-button').inner_text()=='Geçmiş sınırına ulaşıldı'
            assert page.locator('.history-error').count()==0
            assert page.evaluate(INSPECT)['view']['candles']==rows
            result['cases'].append({'name': 'valid_empty_older_page_shows_boundary_without_error_or_data_loss', 'passed': True})

            def reference_check(label, reference=fixture):
                data = page.evaluate(INSPECT)
                assert len(data['lines'])==3 and data['panes']==3, label+' series/pane count'
                compared, worst = 0, 0.0
                for line, key, warmup in zip(data['lines'], ['ema20', 'ema50', 'rsi14'], [19,49,14]):
                    expected = reference[key]
                    assert len(line)==len(expected), label+' warmup/length'
                    for i, (point,value) in enumerate(zip(line, expected)):
                        assert point['time']==reference['times'][i+warmup], label+' time'
                        error=abs(point['value']-float(value));worst=max(worst,error)
                        assert error<=1e-8, label+' Decimal mismatch'
                        compared+=1
                result['cases'].append({'name': label, 'passed': True, 'numeric_values': compared, 'max_error': worst, 'panes': data['panes']})

            reference_check('independent_decimal_values_after_prepend')
            def align(label):
                # Exercise public native time-scale API through test-only React observation.
                page.evaluate(INSPECT.replace('return view?', 'chart.timeScale().setVisibleLogicalRange({from:115,to:153});return view?'))
                page.wait_for_timeout(100)
                page.get_by_role('button', name='Hizalamayı ölç', exact=True).click()
                page.wait_for_timeout(150)
                data = json.loads(page.get_by_label('Çizim hizalama kontrolü').locator('pre').inner_text())
                assert data['result']=='CHECKED_POINTS_PASSED' and data['unchecked_drawings']==0, data
                assert page.locator('[data-drawing]').count()==4
                stored=page.evaluate(INSPECT)['stored']
                assert [d['geometry'] for d in stored]==[d['geometry'] for d in original_drawings], 'stored drawing coordinates changed'
                result['cases'].append({'name': label, 'passed': True, 'checked_points': data['checked_points'], 'failed_drawings': data['failed_drawings']})

            original_drawings = json.loads(json.dumps(drawings))
            align('four_drawings_gap_fractional_and_reverse_fibonacci_after_prepend')
            page.get_by_label('Grafiği tam ekran aç',exact=True).click();page.wait_for_timeout(200)
            align('diagnostic_alignment_accessible_in_fullscreen')
            page.get_by_label('Tam ekrandan çık',exact=True).click();page.wait_for_timeout(150)
            # Start ON; 50 OFF/ON cycles for each indicator control.
            for i in range(50):
                ema.click();rsi.click()
                page.wait_for_timeout(20)
                off=page.evaluate(INSPECT)
                assert off['lines']==[] and off['panes']==2, f'cycle {i}: abandoned pane/series'
                ema.click();rsi.click()
                page.wait_for_timeout(20)
                on=page.evaluate(INSPECT)
                assert len(on['lines'])==3 and on['panes']==3, f'cycle {i}: duplicate/missing pane/series'
            result['cases'].append({'name': '50_indicator_off_on_cycles', 'passed': True, 'cycles': 50, 'control_clicks': 200, 'off_series': 0, 'off_panes': 2, 'on_series': 3, 'on_panes': 3})
            reference_check('independent_decimal_values_after_50_cycles')
            align('four_drawings_alignment_after_50_pane_cycles')
            # Close changes must travel through the App update path, not just a fixture switch.
            changed = next(c for c in json.loads((ROOT/'reports/indicator-reference-20261109.json').read_text())['cases'] if c['name']=='changed_live_close')
            changed = {**changed, 'times': fixture['times']}
            changed_close = float(changed['closes'][-1])
            updated = {**rows[-1], 'close': changed_close, 'high': max(rows[-1]['high'], changed_close+1)}
            def live_update(sequence, last):
                sockets[-1].send(json.dumps({'type': 'update', 'symbol': 'FIXTUREUSDT', 'interval': '15m', 'generation': 1, 'sequence': sequence, 'status': 'LIVE', 'received_at': int(time.time()*1000), 'candle': last}))
                page.wait_for_timeout(150)
                assert page.evaluate(INSPECT)['view']['candles'][-1]==last
            live_update(2, updated)
            reference_check('independent_decimal_values_after_live_close_change', changed)
            live_update(3, {**updated, 'closed': True})
            reference_check('independent_decimal_values_after_candle_finalization', changed)
            # Native drawing geometry observations are in the DOM attributes checked above.
            result['passed']=not result['page_errors'] and not result['unexpected_requests']
            browser.close()
    except Exception as error:
        result['error']=str(error)
    finally:
        server.terminate();server.wait(timeout=10)
    (ROOT/'reports'/report_name).write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
