"""T06 production App/HTTP/SQLite: real pointer creation, v3 geometry and restart."""
import json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
from measure_chart_interactions import INSPECT,ROOT
from agentrader.drawings.calculations import query,CalculationBlocked

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
                def listing(version=6):return api('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version='+str(version))['drawings']
                def head(key):return api('/api/drawings/'+key+'?format_version=6')
                def create(label,points):
                    before={x['drawing_id'] for x in listing()};p.get_by_label('Çizgi araçları',exact=True).click();p.get_by_label('Çizgi araçları',exact=True).locator('..').get_by_role('button',name=label,exact=True).click()
                    for i,price in points:p.mouse.click(*point(i,price));p.wait_for_timeout(550)
                    added=[x for x in listing() if x['drawing_id'] not in before];assert len(added)==1;return added[0]
                def pick(label):p.locator('.drawing-list button').filter(has=p.get_by_text(label,exact=True)).click()
                def save():
                    with p.expect_response(lambda r:r.request.method=='PATCH' and '/api/drawings/' in r.url) as response:p.get_by_role('button',name='Kaydet',exact=True).click()
                    assert response.value.status==200;p.wait_for_timeout(120)
                def bounds(g,time):return query(g,'boundsAt',time=time,times=[r['time'] for r in rows],interval='15m')['value']
                def create_channel(points,label):
                    before={d['drawing_id'] for d in listing()};p.get_by_label('Çizgi araçları',exact=True).click();p.get_by_label('Çizgi araçları',exact=True).locator('..').get_by_role('button',name='Paralel kanal',exact=True).click()
                    for index,price in points:p.mouse.click(*point(index,price));p.wait_for_timeout(550)
                    added=[d for d in listing() if d['drawing_id'] not in before];assert len(added)==1;d=added[0]
                    if label!='Paralel kanal':
                        # Rename through the actual editor so each scenario is selectable.
                        p.get_by_label('Çizim adı',exact=True).fill(label);save();d=head(d['drawing_id'])
                    return d
                p.goto(base);feed();p.get_by_text('300 mum',exact=True).wait_for();p.get_by_label('Çizimleri göster veya gizle').click();frame()
                forward=create_channel([(220,120),(260,130),(240,140)],'Paralel kanal');assert forward['geometry']['schema']=='chart-channel/1';assert bounds(forward['geometry'],rows[260]['time'])['width']['decimal']=='15';assert p.locator('[data-drawing-handles="'+forward['drawing_id']+'"] circle').count()==3;record('three_real_pointer_anchors_create_bounded_channel_and_three_handles')
                reverse=create_channel([(260,130),(220,120),(240,140)],'Ters kanal');assert bounds(reverse['geometry'],rows[250]['time'])==bounds(forward['geometry'],rows[250]['time']);record('reversed_baseline_has_identical_bounds_and_midline')
                negative=create_channel([(225,135),(265,140),(245,125)],'Alt kanal');flat=create_channel([(225,125),(265,125),(245,130)],'Yatay kanal');assert bounds(negative['geometry'],rows[265]['time'])['width']['decimal']=='12.5';assert bounds(flat['geometry'],rows[265]['time'])['middle']['decimal']=='127.5';assert len(listing(5))==2 and len(listing())==6;record('negative_offset_and_horizontal_baseline_work_with_v6_isolation')
                for item in [forward,reverse,negative,flat]:
                    g=item['geometry'];group=p.locator('[data-drawing="'+item['drawing_id']+'"]');native=[]
                    for anchor in g['anchors'][:2]:
                        v=bounds(g,anchor['time']);native.append(read('({x:chart.timeScale().timeToCoordinate('+str(anchor['time'])+'),lo:series.priceToCoordinate('+v['lower']['decimal']+'),hi:series.priceToCoordinate('+v['upper']['decimal']+'),mid:series.priceToCoordinate('+v['middle']['decimal']+')})'))
                    mid=group.locator('[data-channel="middle"]');assert abs(float(mid.get_attribute('y1'))-native[0]['mid'])<1 and abs(float(mid.get_attribute('y2'))-native[1]['mid'])<1
                    baseline=group.locator('[data-channel="base"]');other=group.locator('[data-channel="offset"]');dx=float(baseline.get_attribute('x2'))-float(baseline.get_attribute('x1'));assert abs((float(baseline.get_attribute('y2'))-float(baseline.get_attribute('y1')))/dx-(float(other.get_attribute('y2'))-float(other.get_attribute('y1')))/dx)<1e-8
                record('all_four_channels_are_parallel_and_midlines_match_native_exact_prices')
                pick('Paralel kanal');summary=p.get_by_role('region',name='Paralel kanal özeti');assert '137,5' in summary.inner_text();p.get_by_label('Kanal kontrol fiyatı',exact=True).fill('137.5');assert 'İçeride' in summary.inner_text();p.get_by_label('Kanal kontrol fiyatı',exact=True).fill('150');assert 'Dışarıda' in summary.inner_text() and '5' in summary.inner_text();assert query(forward['geometry'],'distance',time=rows[260]['time'],query_price='150',times=[r['time'] for r in rows],interval='15m')['value']['decimal']=='5';record('inside_outside_and_price_distance_panel_match_canonical_boundary_queries')
                p.get_by_label('Nokta 3 fiyatı',exact=True).fill('125');revision=head(forward['drawing_id'])['revision'];p.get_by_role('button',name='Kaydet',exact=True).click();assert 'genişliği sıfır' in p.locator('.drawing-error').inner_text();assert head(forward['drawing_id'])['revision']==revision;p.get_by_label('Nokta 3 fiyatı',exact=True).fill('145');save();saved=head(forward['drawing_id']);assert bounds(saved['geometry'],rows[260]['time'])['width']['decimal']=='20';record('zero_width_is_rejected_and_numeric_offset_edit_changes_exact_width')
                # Other overlapping channels are temporarily hidden through their persisted properties.
                for item,label in [(reverse,'Ters kanal'),(negative,'Alt kanal'),(flat,'Yatay kanal')]:
                    pick(label);p.get_by_label('Çizimi gizle',exact=True).click();p.locator('[data-drawing="'+item['drawing_id']+'"]').wait_for(state='detached')
                pick('Paralel kanal');frame();h=p.locator('[data-drawing-handles="'+forward['drawing_id']+'"] [data-anchor="2"]');b=h.bounding_box();p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);p.mouse.down();p.mouse.move(*point(242,147.5),steps=8);p.mouse.up();p.wait_for_timeout(220);moved=head(forward['drawing_id']);assert moved['geometry']['anchors'][2]==dict(time=rows[242]['time'],price='147.50');assert bounds(moved['geometry'],rows[260]['time'])['width']['decimal']=='22';record('actual_third_handle_drag_keeps_parallel_boundaries_and_exact_offset')
                p.get_by_label('Çizim değişikliğini geri al').click();p.wait_for_timeout(180);assert head(forward['drawing_id'])['geometry']==saved['geometry'];p.get_by_label('Çizim değişikliğini yinele').click();p.wait_for_timeout(180);assert head(forward['drawing_id'])['geometry']==moved['geometry'];record('one_undo_redo_restores_all_three_channel_anchors')
                frame();p.mouse.move(*point(235,130));p.mouse.down();p.mouse.move(*point(237,132.5),steps=8);p.mouse.up();p.wait_for_timeout(220);translated=head(forward['drawing_id']);assert [a['price'] for a in translated['geometry']['anchors']]==['122.50','132.50','150.00'];assert bounds(translated['geometry'],rows[262]['time'])['width']['decimal']=='22';record('whole_channel_drag_translates_all_anchors_without_changing_width')
                # A gap after every anchor leaves their pixel coordinates unchanged: validity must still repaint.
                feed(rows[:295]+rows[296:]);p.locator('[data-drawing="'+forward['drawing_id']+'"]').wait_for(state='hidden');assert 'kullanılamıyor' in p.locator('.channel-unavailable').inner_text()
                try:query(translated['geometry'],'boundsAt',time=rows[250]['time'],times=[r['time'] for i,r in enumerate(rows) if i!=295],interval='15m');raise AssertionError('Gap accepted')
                except CalculationBlocked as e:assert e.code=='GRID_GAP'
                feed();frame();p.locator('[data-drawing="'+forward['drawing_id']+'"]').wait_for(state='visible');record('gap_outside_anchor_span_hides_stale_projection_and_recovery_restores_it')
                p.get_by_label('Çizimi kilitle',exact=True).click();p.locator('[data-drawing-handles="'+forward['drawing_id']+'"]').wait_for(state='detached');assert p.get_by_label('Nokta 3 fiyatı',exact=True).is_disabled();p.get_by_label('Çizimi kilitle',exact=True).click();p.locator('[data-drawing-handles="'+forward['drawing_id']+'"]').wait_for(state='visible');record('channel_uses_t07_lock_and_handle_policy')
                p.screenshot(path=str(ROOT/'reports/chart-t06-dark-20261112.png'));p.get_by_label('Açık temaya geç').click();p.screenshot(path=str(ROOT/'reports/chart-t06-light-20261112.png'));expected={d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()}
                server.terminate();server.wait(timeout=10);server=start();wait_server();sockets.clear();seq=0;p.reload();feed();assert {d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()}==expected;assert not api('/api/health')['trading_commands_enabled'];record('server_page_restart_preserves_channel_geometry_and_management')
                assert not result['page_errors'];assert not result['unexpected_requests'];assert not result['private_requests'];result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-t06-validation-20261112.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
