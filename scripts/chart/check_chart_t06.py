"""T06 current toolbar channel-family creation, persistence and restart."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from scripts.chart.demo_browser_fixture import fixture_packet,fixture_response
import json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
from scripts.chart.measure_chart_interactions import INSPECT,ROOT

def main():
    result={'task':'T06','passed':False,'checks':[],'page_errors':[],'unexpected_requests':[],'private_requests':[],'scope':'Production App, synthetic market and isolated SQLite; no account/order access'}
    with tempfile.TemporaryDirectory(prefix='agentrader-t06-') as folder:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}';opener=build_opener(ProxyHandler({}));env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(Path(folder)/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(Path(folder)/'execution.db'),AGENTRADER_CHART_DATABASE=str(Path(folder)/'market.db'),AGENTRADER_WEB_TOKEN='')
        def start():return subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        server=start()
        def api(path,body=None):
            req=Request(base+path,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json'})
            with opener.open(req,timeout=5) as r:return json.load(r)
        def wait_server():
            for _ in range(100):
                try:api('/api/health');return
                except Exception:time.sleep(.1)
            raise AssertionError('Server not ready')
        def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
        try:
            wait_server();market=dict(symbol='BTCUSDT',base_asset='BTC',quote_asset='USDT',contract_type='PERPETUAL',tick_size='0.25');rows=[dict(time=1800000000+i*900,open=100+i*.1,high=110+i*.1,low=90+i*.1,close=105+i*.1,volume=10+i,quote_volume=1000,close_time=(1800000000+(i+1)*900)*1000-1,closed=i<299) for i in range(300)]
            old=api('/api/workspaces/main/drawings',{'request_id':'old','geometry':dict(kind='trend',symbol='BTCUSDT',price_source='LAST_PRICE',label='Eski segment',anchors=[{'time':rows[210]['time'],'price':'105'},{'time':rows[215]['time'],'price':'110'}])})
            zone=api('/api/workspaces/main/drawings',{'request_id':'zone','geometry':dict(kind='zone',symbol='BTCUSDT',price_source='LAST_PRICE',label='Eski bölge',anchors=[{'time':rows[205]['time'],'price':'108'},{'time':rows[212]['time'],'price':'118'}])})
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True);context=browser.new_context(viewport={'width':1536,'height':900},device_scale_factor=1.25);p=context.new_page();p.set_default_timeout(6000);sockets=[]
                p.on('pageerror',lambda e:result['page_errors'].append(str(e)))
                def guard(r):
                    if any(path in r.request.url for path in ['/api/commands','/api/account','/api/orders','/api/execution','/api/session']):result['private_requests'].append(r.request.url);r.abort()
                    elif not r.request.url.startswith(base+'/'):result['unexpected_requests'].append(r.request.url);r.abort()
                    else:r.continue_()
                p.route('**/*',guard);p.route('**/api/markets',lambda r:r.fulfill(json=fixture_response(r.request.url,{'markets':[market]})));p.route('**/api/candles*',lambda r:r.fulfill(json=fixture_response(r.request.url,{'candles':[],'has_more':False})));p.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
                seq=0
                def feed(data=rows):
                    nonlocal seq
                    for _ in range(80):
                        if sockets:break
                        p.wait_for_timeout(80)
                    seq+=1;sockets[-1].send(json.dumps(fixture_packet(dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=seq,status='LIVE',received_at=int(time.time()*1000),market=market,quality={'state':'OK','missing_bars':0},candles=data))));p.wait_for_timeout(200)
                def read(expr):return p.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');'+'}')
                def frame():read('(chart.timeScale().setVisibleLogicalRange({from:200,to:280}),series.priceScale().setVisibleRange({from:100,to:150}),true)');p.wait_for_timeout(150)
                def point(index,price):
                    q=read('({x:chart.timeScale().logicalToCoordinate('+str(index)+'),y:series.priceToCoordinate('+str(price)+')})');b=p.locator('.chart-host').bounding_box();return (b['x']+q['x'],b['y']+q['y'])
                def listing(version=9):return api('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version='+str(version))['drawings']
                def head(key):return api('/api/drawings/'+key+'?format_version=9')
                def create(label,points):
                    before={x['drawing_id'] for x in listing()};p.get_by_label('Çizgi araçları',exact=True).click();p.get_by_label('Çizgi araçları',exact=True).locator('..').get_by_role('button',name=label,exact=True).click()
                    for i,price in points:p.mouse.click(*point(i,price));p.wait_for_timeout(550)
                    added=[x for x in listing() if x['drawing_id'] not in before];assert len(added)==1;return added[0]
                def pick(label):p.locator('.drawing-list button').filter(has=p.get_by_text(label,exact=True)).click()
                def save():
                    with p.expect_response(lambda r:r.request.method=='PATCH' and '/api/drawings/' in r.url) as response:p.get_by_role('button',name='Kaydet',exact=True).click()
                    assert response.value.status==200;p.wait_for_timeout(120)
                def create_channel(points,label):
                    before={d['drawing_id'] for d in listing()};p.get_by_label('Çizgi araçları',exact=True).click();p.get_by_label('Çizgi araçları',exact=True).locator('..').get_by_role('button',name='Paralel kanal',exact=True).click()
                    for index,price in points:p.mouse.click(*point(index,price));p.wait_for_timeout(550)
                    added=[d for d in listing() if d['drawing_id'] not in before];assert len(added)==1;d=added[0]
                    if label!='Paralel kanal':
                        # Rename through the actual editor so each scenario is selectable.
                        p.get_by_label('Çizim adı',exact=True).fill(label);save();d=head(d['drawing_id'])
                    return d
                p.goto(base);feed();p.get_by_text('300 mum',exact=True).wait_for();p.get_by_label('Çizimleri göster veya gizle').click();frame()
                forward=create_channel([(220,120),(260,130),(240,140)],'Paralel kanal')
                assert forward['geometry']['schema']=='chart-channel-family/1'
                assert forward['geometry']['kind']=='parallel_channel'
                assert len(forward['geometry']['anchors'])==3
                group=p.locator('[data-drawing="'+forward['drawing_id']+'"]')
                assert group.locator('.family-line').count()>0
                assert p.locator('[data-drawing-handles="'+forward['drawing_id']+'"] circle').count()==4
                record('current_toolbar_creates_family_schema_with_three_raw_anchors_and_four_handles')
                p.get_by_label('Seçili çizimin tüm ayarları',exact=True).click()
                popup=p.get_by_role('region',name='Seçili çizim ayarları',exact=True)
                popup.get_by_label('Kanal ve pitchfork metni',exact=True).fill('G0 güncel kanal\nSentetik kabul')
                popup.get_by_role('button',name='Kaydet',exact=True).click();p.wait_for_timeout(200)
                p.get_by_label('Çizim ayarlarını kapat',exact=True).click()
                saved=head(forward['drawing_id'])
                assert saved['geometry']['text']=='G0 güncel kanal\nSentetik kabul'
                assert saved['revision']>forward['revision']
                record('current_family_settings_persist_text_with_new_revision')
                expected={d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()}
                server.terminate();server.wait(timeout=10);server=start();wait_server();sockets.clear();seq=0;p.reload();feed()
                assert {d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()}==expected
                frame();assert p.locator('[data-drawing="'+forward['drawing_id']+'"] .family-line').count()>0
                assert not api('/api/health')['trading_commands_enabled']
                record('restart_preserves_current_family_and_legacy_sentinel_objects')
                assert not result['page_errors'];assert not result['unexpected_requests'];assert not result['private_requests']
                result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-t06-validation-20261115.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
