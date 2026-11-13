"""T05 production App/HTTP/SQLite: real pointer creation, v3 geometry and restart."""
import json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
from measure_chart_interactions import INSPECT,ROOT
from agentrader.drawings.calculations import query,CalculationBlocked

def main():
    result={'task':'T05','passed':False,'checks':[],'page_errors':[],'unexpected_requests':[],'scope':'Production App, synthetic market and isolated SQLite; no account/order access'}
    with tempfile.TemporaryDirectory(prefix='agentrader-t05-') as folder:
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
                    if not r.request.url.startswith(base+'/'):result['unexpected_requests'].append(r.request.url);r.abort()
                    else:r.continue_()
                p.route('**/*',guard);p.route('**/api/markets',lambda r:r.fulfill(json={'markets':[market]}));p.route('**/api/candles*',lambda r:r.fulfill(json={'candles':[],'has_more':False}));p.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
                seq=0
                def feed(data=rows):
                    nonlocal seq
                    for _ in range(80):
                        if sockets:break
                        p.wait_for_timeout(80)
                    seq+=1;sockets[-1].send(json.dumps(dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=seq,status='LIVE',received_at=int(time.time()*1000),market=market,quality={'state':'OK','missing_bars':0},candles=data)));p.wait_for_timeout(200)
                def read(expr):return p.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');'+'}')
                def frame():read('(chart.timeScale().setVisibleLogicalRange({from:200,to:280}),series.priceScale().setVisibleRange({from:100,to:150}),true)');p.wait_for_timeout(150)
                def point(index,price):
                    q=read('({x:chart.timeScale().logicalToCoordinate('+str(index)+'),y:series.priceToCoordinate('+str(price)+')})');b=p.locator('.chart-host').bounding_box();return (b['x']+q['x'],b['y']+q['y'])
                def listing(version=3):return api('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version='+str(version))['drawings']
                def head(key):return api('/api/drawings/'+key+'?format_version=3')
                def create(label,points):
                    before={x['drawing_id'] for x in listing()};p.get_by_label('Çizgi araçları',exact=True).click();p.get_by_label('Çizgi araçları',exact=True).locator('..').get_by_role('button',name=label,exact=True).click()
                    for i,price in points:p.mouse.click(*point(i,price));p.wait_for_timeout(550)
                    added=[x for x in listing() if x['drawing_id'] not in before];assert len(added)==1;return added[0]
                p.goto(base);feed();p.get_by_text('300 mum',exact=True).wait_for();frame()
                forward=create('Işın',[(220,120),(240,130)]);backward=create('Işın',[(260,140),(240,130)]);extended=create('Uzatılmış çizgi',[(230,123),(240,128)]);horizontal=create('Yatay ışın',[(230,117.5)])
                for item in [forward,backward,extended,horizontal]:assert item['geometry']['schema']=='chart-line/1'
                assert len(listing(1))==2 and len(listing(2))==2 and len(listing(3))==6;record('four_real_pointer_creations_and_legacy_list_isolation')
                for item,direction in [(forward,1),(backward,-1)]:
                    el=p.locator('[data-drawing="'+item['drawing_id']+'"] .shape-line');assert (float(el.get_attribute('x2'))-float(el.get_attribute('x1')))*direction>0
                assert query(forward['geometry'],'priceAt',time=rows[260]['time'],times=[r['time'] for r in rows],interval='15m')['value']['decimal']=='140';record('forward_and_backward_scope_matches_exact_offline_price')
                h=p.locator('[data-drawing="'+horizontal['drawing_id']+'"] .shape-line');assert abs(float(h.get_attribute('x2'))-read('chart.paneSize(0).width'))<1;record('horizontal_ray_starts_at_anchor_and_reaches_visible_known_grid_edge')
                p.get_by_label('Çizimleri göster veya gizle').click();p.locator('.drawing-list button').filter(has_text='Uzatılmış çizgi').click();p.get_by_label('Nokta 2 fiyatı',exact=True).fill('135.00');p.get_by_role('button',name='Kaydet',exact=True).click();p.wait_for_timeout(200);saved=head(extended['drawing_id']);assert saved['geometry']['anchors'][1]['price']=='135.00';assert query(saved['geometry'],'priceAt',time=rows[250]['time'],times=[r['time'] for r in rows],interval='15m')['value']['decimal']=='147';record('numeric_endpoint_edit_uses_same_canonical_line')
                handle=p.locator('[data-drawing-handles="'+extended['drawing_id']+'"] [data-anchor="1"]');b=handle.bounding_box();p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);p.mouse.down();p.mouse.move(*point(245,137.5),steps=8);p.mouse.up();p.wait_for_timeout(250);moved=head(extended['drawing_id']);assert moved['geometry']['anchors'][1]=={'time':rows[245]['time'],'price':'137.50'};record('actual_handle_drag_keeps_versioned_geometry_and_exact_tick')
                p.get_by_label('Çizim değişikliğini geri al').click();p.wait_for_timeout(180);assert head(extended['drawing_id'])['geometry']==saved['geometry'];p.get_by_label('Çizim değişikliğini yinele').click();p.wait_for_timeout(180);assert head(extended['drawing_id'])['geometry']==moved['geometry'];record('undo_redo_preserve_extension_schema_and_direction')
                p.locator('.drawing-list button').filter(has_text='Eski bölge').click();p.get_by_label('Bölgenin zaman kapsamı').select_option('unbounded');p.get_by_role('button',name='Kaydet',exact=True).click();p.wait_for_timeout(200);z=head(zone['drawing_id']);assert z['geometry']['schema']=='chart-zone/1';assert z['geometry']['time_scope']=='unbounded';rect=p.locator('[data-drawing="'+zone['drawing_id']+'"] .shape-zone');assert float(rect.get_attribute('x'))==0 and abs(float(rect.get_attribute('width'))-read('chart.paneSize(0).width'))<1;assert query(z['geometry'],'contains',time=rows[290]['time'],query_price='115')['value'];assert len(listing(2))==1;record('zone_explicit_scope_promotion_is_versioned_and_not_leaked_to_v2')
                assert head(old['drawing_id'])['geometry']==old['geometry'];assert head(old['drawing_id'])['revision']==1;record('old_segment_geometry_and_revision_unchanged')
                feed(rows[:235]+rows[236:]);assert p.locator('[data-drawing="'+forward['drawing_id']+'"]').evaluate("e=>e.style.display==='none'");
                try:query(forward['geometry'],'priceAt',time=rows[260]['time'],times=[r['time'] for r in rows if r['time']!=rows[235]['time']],interval='15m');raise AssertionError('Gap accepted')
                except CalculationBlocked as error:assert error.code=='GRID_GAP'
                feed();frame();record('missing_grid_hides_sloped_extension_and_blocks_canonical_query')
                p.screenshot(path=str(ROOT/'reports/chart-t05-dark-20261112.png'));p.get_by_label('Açık temaya geç').click();p.screenshot(path=str(ROOT/'reports/chart-t05-light-20261112.png'))
                server.terminate();server.wait(timeout=10);server=start();wait_server();sockets.clear();seq=0;p.reload();feed();assert len(listing())==6;assert head(extended['drawing_id'])['geometry']==moved['geometry'];assert head(zone['drawing_id'])['geometry']==z['geometry'];record('server_and_page_restart_restore_all_new_and_legacy_geometry')
                assert not result['page_errors'];assert not result['unexpected_requests'];result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-t05-validation-20261112.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())

