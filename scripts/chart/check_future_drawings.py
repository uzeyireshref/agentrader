"""Production browser + isolated SQLite, pointer creation beyond the last real bar."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json, os, socket, subprocess, sys, tempfile, time, traceback
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler
from playwright.sync_api import sync_playwright
from scripts.chart.measure_chart_interactions import INSPECT, ROOT
from agentrader.shared.market_environment import SOURCE, ENVIRONMENT
from agentrader.chart.chart_evidence import snapshot


def main():
    report = dict(passed=False, checks=[], page_errors=[], unexpected_requests=[], account_requests=0, order_requests=0)
    with tempfile.TemporaryDirectory(prefix='future-drawings-') as folder:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        env = dict(os.environ, AGENTRADER_WEB_DATABASE=str(Path(folder)/'app.db'),
                   AGENTRADER_EXECUTION_DATABASE=str(Path(folder)/'execution.db'),
                   AGENTRADER_CHART_DATABASE=str(Path(folder)/'market.db'), AGENTRADER_WEB_TOKEN='')
        server = subprocess.Popen([sys.executable, '-m', 'agentrader', 'web', 'serve', '--port', str(port)],
                                  cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        opener = build_opener(ProxyHandler({}))
        def api(path):
            with opener.open(base+path, timeout=5) as response:return json.load(response)
        try:
            for _ in range(100):
                try:api('/api/health');break
                except Exception:time.sleep(.1)
            market = dict(symbol='BTCUSDT', base_asset='BTC', quote_asset='USDT', tick_size='0.25', contract_type='PERPETUAL')
            rows = [dict(time=1800000000+i*900,open=120,high=140,low=100,close=125,volume=10,
                         quote_volume=1250,close_time=(1800000000+(i+1)*900)*1000-1,closed=i<299) for i in range(300)]
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page(viewport={'width':1536,'height':950})
                page.set_default_timeout(7000)
                page.on('pageerror', lambda e:report['page_errors'].append(str(e)))
                def boundary(route):
                    if not route.request.url.startswith(base+'/') or any(x in route.request.url for x in ['/api/account','/api/orders','/api/commands']):
                        report['unexpected_requests'].append(route.request.url);route.abort()
                    else:route.continue_()
                sockets = []
                page.route('**/*', boundary)
                context=dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE')
                page.route('**/api/markets', lambda r:r.fulfill(json=dict(markets=[market],**context)))
                page.route('**/api/candles*', lambda r:r.fulfill(json=dict(candles=[],has_more=False,**context)))
                page.route_web_socket('**/api/market-stream*', lambda ws:sockets.append(ws))
                def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');}')
                def feed(data, seq):
                    for _ in range(100):
                        if sockets:break
                        page.wait_for_timeout(50)
                    proof=snapshot(data,market,dict(state='OK',missing_bars=0),symbol='BTCUSDT',interval='15m',epoch='a'*32,generation=1,revision=seq).view()
                    sockets[-1].send(json.dumps(dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=seq,stream_epoch='a'*32,data_proof=proof,
                        status='LIVE',received_at=int(time.time()*1000),market=market,quality=dict(state='OK',missing_bars=0),candles=data,**context)))
                    page.wait_for_timeout(200)
                def frame():
                    read('(chart.timeScale().setVisibleLogicalRange({from:275,to:345}),series.priceScale().setVisibleRange({from:80,to:160}),true)')
                    page.wait_for_timeout(100)
                def point(index, price):
                    at=read(f'({{x:chart.timeScale().logicalToCoordinate({index}),y:series.priceToCoordinate({price})}})')
                    box=page.locator('.chart-host').bounding_box()
                    return box['x']+at['x'], box['y']+at['y']
                def listing():return api('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version=9')['drawings']
                page.goto(base);feed(rows,1);page.get_by_text('300 mum',exact=True).wait_for();frame()
                tools=[('Çizgi araçları','Yatay çizgi',[(310,120)]),('Çizgi araçları','Trend çizgisi',[(305,110),(320,130)]),
                       ('Çizgi araçları','Işın',[(305,115),(320,125)]),('Çizgi araçları','Uzatılmış çizgi',[(305,112),(320,127)]),
                       ('Çizgi araçları','Yatay ışın',[(310,122)]),('Fibonacci araçları','Fibonacci',[(305,110),(320,135)]),
                       ('Fibonacci araçları','Fibonacci extension',[(305,112),(320,133)]),
                       ('Çizgi araçları','Paralel kanal',[(305,110),(320,120),(320,135)]),
                       ('Çizgi araçları','Düz üst/alt kanal',[(305,110),(320,120),(320,135)]),
                       ('Çizgi araçları','Ayrışan kanal',[(305,110),(320,120),(320,135)]),
                       *[('Pitchfork araçları',name,[(305,115),(313,135),(323,110)]) for name in ['Pitchfork','Schiff Pitchfork','Modified Schiff Pitchfork','Inside Pitchfork']],
                       (None,'Fiyat bölgesi',[(305,110),(320,130)]),(None,'Fiyat-zaman cetveli',[(305,110),(320,130)]),
                       *[('Açıklama araçları',name,[(312,125)]) for name in ['Metin','Not','Fiyat etiketi']],
                       ('Planlama araçları','Long plan',[(305,120),(310,110),(325,140)]),
                       ('Planlama araçları','Short plan',[(305,120),(310,135),(325,100)])]
                created=[]
                for group,label,points in tools:
                    frame()
                    before={d['drawing_id'] for d in listing()}
                    if group:page.get_by_label(group,exact=True).click()
                    page.get_by_role('button',name=label,exact=True).click()
                    for index,price in points:
                        page.mouse.move(*point(index,price));page.wait_for_timeout(60)
                        page.mouse.click(*point(index,price));page.wait_for_timeout(550)
                    page.wait_for_timeout(200)
                    added=[d for d in listing() if d['drawing_id'] not in before]
                    if len(added)!=1:
                        report['browser_text']=page.locator('body').inner_text()[:4500]
                        report['range']=read('chart.timeScale().getVisibleLogicalRange()')
                        page.screenshot(path=str(ROOT/'reports/future-drawings-failure.png'))
                    assert len(added)==1,(label,added)
                    item=added[0];created.append(item)
                    assert all(a['time']>rows[-1]['time'] for a in item['geometry']['anchors']),label
                    node=page.locator('[data-drawing="'+item['drawing_id']+'"]')
                    assert node.is_visible(),label
                    report['checks'].append(dict(tool=label,kind=item['geometry']['kind'],passed=True))
                    if item['geometry']['kind'] in ('trend','fibonacci','parallel_channel'):
                        handle=page.locator('[data-drawing-handles="'+item['drawing_id']+'"] [data-anchor="1"]')
                        handle.wait_for(state='visible');box=handle.bounding_box()
                        page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2)
                        page.mouse.down();page.mouse.move(*point(330,138),steps=7);page.mouse.up();page.wait_for_timeout(550)
                        saved=next(d for d in listing() if d['drawing_id']==item['drawing_id'])
                        assert saved['revision']==2 and saved['geometry']['anchors'][1]['time']==1800000000+330*900,(label,saved)
                        created[-1]=saved
                        report['checks'].append(dict(tool=label,operation='drag_future_anchor',passed=True))
                horizontal_ray=next(d for d in created if d['geometry']['kind']=='horizontal_ray')
                line=page.locator('[data-drawing="'+horizontal_ray['drawing_id']+'"] .shape-line')
                assert abs(float(line.get_attribute('x2'))-read('chart.paneSize(0).width'))<1
                # The future object stays at its persisted UTC instant when actual bars catch up.
                before=created[1]['geometry']
                more=rows+[dict(rows[-1],time=1800000000+i*900,close_time=(1800000000+(i+1)*900)*1000-1) for i in range(300,330)]
                feed(more,2);frame()
                assert next(d for d in listing() if d['drawing_id']==created[1]['drawing_id'])['geometry']==before
                page.screenshot(path=str(ROOT/'reports/future-drawings-20261113.png'))
                sockets.clear();page.reload();page.wait_for_timeout(100);feed(rows,3);frame()
                assert len(listing())==len(created)
                assert not report['page_errors'],report['page_errors']
                assert not report['unexpected_requests'],report['unexpected_requests']
                assert not Path(folder,'execution.db').exists()
                report.update(passed=True,created=len(created),future_ray_reaches_viewport=True,real_bar_arrival_preserves_utc=True,reload_persistence=True)
                browser.close()
        except Exception:
            report['error']=traceback.format_exc()
            try:report['browser_text']=page.locator('body').inner_text()[:3500];report['view']=read('view')
            except Exception:pass
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/future-drawings-validation-20261113.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
