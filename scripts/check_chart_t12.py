"""T12 production App/HTTP/SQLite: real pointer creation, v3 geometry and restart."""
import json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
from measure_chart_interactions import INSPECT,ROOT
from agentrader.drawings.calculations import query,CalculationBlocked

def main():
    result={'task':'T12','passed':False,'checks':[],'page_errors':[],'unexpected_requests':[],'private_requests':[],'scope':'Production App, synthetic market and isolated SQLite; no account/order access'}
    with tempfile.TemporaryDirectory(prefix='agentrader-t12-') as folder:
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
            zone=api('/api/workspaces/main/drawings',{'request_id':'zone','geometry':dict(kind='fibonacci',symbol='BTCUSDT',price_source='LAST_PRICE',label='Eski Fibonacci',anchors=[{'time':rows[205]['time'],'price':'108'},{'time':rows[212]['time'],'price':'118'}])})
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
                def listing(version=7):return api('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version='+str(version))['drawings']
                def head(key):return api('/api/drawings/'+key+'?format_version=7')
                def create(label,points):
                    before={x['drawing_id'] for x in listing()};p.get_by_label('Çizgi araçları',exact=True).click();p.get_by_label('Çizgi araçları',exact=True).locator('..').get_by_role('button',name=label,exact=True).click()
                    for i,price in points:p.mouse.click(*point(i,price));p.wait_for_timeout(550)
                    added=[x for x in listing() if x['drawing_id'] not in before];assert len(added)==1;return added[0]
                def pick(label):p.locator('.drawing-list button').filter(has=p.get_by_text(label,exact=True)).click()
                def save():
                    with p.expect_response(lambda r:r.request.method=='PATCH' and '/api/drawings/' in r.url) as response:p.get_by_role('button',name='Kaydet',exact=True).click()
                    assert response.value.status==200;p.wait_for_timeout(120)
                def level(g,ratio,time=None):return query(g,'level',ratio=ratio,time=rows[240]['time'] if time is None else time)['value']['decimal']
                def create_fib(label,points):
                    before={d['drawing_id'] for d in listing()};p.get_by_label('Fibonacci araçları',exact=True).click();p.get_by_label('Fibonacci araçları',exact=True).locator('..').get_by_role('button',name=label,exact=True).click()
                    for index,price in points:p.mouse.click(*point(index,price));p.wait_for_timeout(550)
                    added=[d for d in listing() if d['drawing_id'] not in before];assert len(added)==1;return added[0]
                p.goto(base);feed();p.get_by_text('300 mum',exact=True).wait_for();p.get_by_label('Çizimleri göster veya gizle').click();frame()
                legacy=head(zone['drawing_id']);assert 'schema' not in legacy['geometry'];assert p.locator('[data-drawing="'+legacy['drawing_id']+'"] .shape-line[data-fib]').count()==7;assert legacy['revision']==1;record('existing_legacy_record_keeps_seven_lines_geometry_and_revision')
                fib=create_fib('Fibonacci',[(220,120),(260,130)]);extension=create_fib('Fibonacci extension',[(230,115),(250,125)]);assert fib['geometry']['schema']=='chart-fibonacci/1';assert extension['geometry']['kind']=='fibonacci_extension';assert level(extension['geometry'],'1.618')=='131.18';assert len(listing(6))==2;record('real_two_point_retracement_and_extension_are_versioned_and_old_client_isolated')
                pick('Fibonacci');p.get_by_label('Fibonacci oran listesi',exact=True).fill('0; 0.236; 1; 1.272; 1.618; 2.618; 0.236000000001');save();configured=head(fib['drawing_id']);assert configured['geometry']['levels'][-1]=='0.236000000001';assert level(configured['geometry'],'1.618')=='136.18';assert level(configured['geometry'],'0.236')=='122.36';line=p.locator('[data-drawing="'+fib['drawing_id']+'"] .shape-line[data-fib="1.618"]');assert abs(float(line.get_attribute('y1'))-read('series.priceToCoordinate(136.18)'))<1;record('custom_decimal_and_extension_levels_render_exact_prices_without_tick_rounding')
                p.get_by_label('Fibonacci oran listesi',exact=True).fill('0; 0.00');revision=head(fib['drawing_id'])['revision'];p.get_by_role('button',name='Kaydet',exact=True).click();assert 'birden fazla' in p.locator('.drawing-error').inner_text();assert head(fib['drawing_id'])['revision']==revision;p.get_by_label('Fibonacci oran listesi',exact=True).fill('; '.join(configured['geometry']['levels']));record('duplicate_numeric_ratios_rejected_without_any_server_write')
                p.get_by_label('Fibonacci zaman kapsamı',exact=True).select_option('right');save();right=head(fib['drawing_id']);assert level(right['geometry'],'1.618',rows[-1]['time']+90000)=='136.18';assert abs(float(line.get_attribute('x2'))-read('chart.paneSize(0).width'))<1;p.get_by_label('Fibonacci zaman kapsamı',exact=True).select_option('unbounded');save();assert float(line.get_attribute('x1'))==0;p.get_by_label('Fibonacci zaman kapsamı',exact=True).select_option('bounded');save();record('bounded_right_and_unbounded_scope_agree_between_svg_and_canonical_queries')
                p.get_by_role('button',name='Noktaların yönünü ters çevir',exact=True).click();save();reversed=head(fib['drawing_id']);assert reversed['geometry']['anchors']==configured['geometry']['anchors'][::-1];assert level(reversed['geometry'],'1.618')=='113.82';record('explicit_anchor_reverse_keeps_ratio_configuration_and_correct_direction')
                frame();h=p.locator('[data-drawing-handles="'+fib['drawing_id']+'"] [data-anchor="1"]');b=h.bounding_box();p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);p.mouse.down();p.mouse.move(*point(225,122.5),steps=8);p.mouse.up();p.wait_for_timeout(220);moved=head(fib['drawing_id']);assert moved['geometry']['anchors'][1]==dict(time=rows[225]['time'],price='122.50');assert moved['geometry']['levels']==configured['geometry']['levels'];assert level(moved['geometry'],'1.618')=='117.865';record('actual_endpoint_drag_preserves_ratios_and_keeps_off_tick_computed_level')
                p.get_by_label('Çizim değişikliğini geri al').click();p.wait_for_timeout(180);assert head(fib['drawing_id'])['geometry']==reversed['geometry'];p.get_by_label('Çizim değişikliğini yinele').click();p.wait_for_timeout(180);assert head(fib['drawing_id'])['geometry']==moved['geometry'];record('undo_redo_restore_full_ratio_and_scope_configuration')
                frame();p.mouse.move(*point(240,122.5));p.mouse.down();p.mouse.move(*point(242,125),steps=8);p.mouse.up();p.wait_for_timeout(200);translated=head(fib['drawing_id']);assert [a['price'] for a in translated['geometry']['anchors']]==['132.50','125.00'];assert translated['geometry']['levels']==configured['geometry']['levels'];record('whole_object_drag_moves_anchors_without_rounding_or_resetting_levels')
                group=p.locator('[data-drawing="'+fib['drawing_id']+'"]');assert group.locator('.shape-line[data-fib]').count()==7;visible=group.locator('[data-fib-label]').evaluate_all('es=>es.filter(e=>+e.getAttribute("opacity")>0).length');assert visible<7;assert group.locator('.hit-line[data-fib]').count()==7;record('dense_labels_are_suppressed_while_all_price_lines_and_hit_areas_remain')
                pick('Eski Fibonacci');p.get_by_role('button',name='Oranları özelleştir',exact=True).wait_for();assert p.get_by_label('Fibonacci oran listesi',exact=True).count()==0;p.get_by_label('Çizim adı',exact=True).fill('Eski Fibonacci adı');save();renamed=head(legacy['drawing_id']);assert 'schema' not in renamed['geometry'];assert renamed['geometry']['anchors']==legacy['geometry']['anchors'];p.get_by_role('button',name='Oranları özelleştir',exact=True).click();p.get_by_label('Fibonacci oran listesi',exact=True).fill('-1; 0; 1; 1.618');save();promoted=head(legacy['drawing_id']);assert promoted['geometry']['schema']=='chart-fibonacci/1';assert promoted['geometry']['levels']==['-1','0','1','1.618'];p.get_by_label('Çizim değişikliğini geri al').click();p.wait_for_timeout(180);assert head(legacy['drawing_id'])['geometry']==renamed['geometry'];assert p.locator('[data-drawing="'+legacy['drawing_id']+'"] .shape-line[data-fib]').count()==7;p.get_by_label('Çizim değişikliğini yinele').click();p.wait_for_timeout(180);assert head(legacy['drawing_id'])['geometry']==promoted['geometry'];record('legacy_rename_stays_legacy_explicit_promotion_and_undo_restore_original_seven_levels')
                pick('Fibonacci extension');p.get_by_label('Fibonacci oran listesi',exact=True).fill('0; 10');p.get_by_role('button',name='Noktaların yönünü ters çevir',exact=True).click();p.get_by_label('Nokta 2 fiyatı',exact=True).fill('100');save();nonpositive=head(extension['drawing_id']);assert p.locator('[data-drawing="'+extension['drawing_id']+'"] [data-fib-group="10"]').evaluate('e=>e.style.display')=='none';assert 'Pozitif fiyat üretmiyor' in p.get_by_role('region',name='Fibonacci seviye fiyatları').inner_text()
                try:level(nonpositive['geometry'],'10');raise AssertionError('Nonpositive price fabricated')
                except CalculationBlocked as error:assert error.code=='NON_POSITIVE_LEVEL'
                record('nonpositive_extension_level_is_explicitly_unavailable_and_not_drawn_at_zero')
                pick('Fibonacci');p.screenshot(path=str(ROOT/'reports/chart-t12-dark-20261112.png'));p.get_by_label('Açık temaya geç').click();p.screenshot(path=str(ROOT/'reports/chart-t12-light-20261112.png'));expected={d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()}
                server.terminate();server.wait(timeout=10);server=start();wait_server();sockets.clear();seq=0;p.reload();feed();assert {d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()}==expected;assert not api('/api/health')['trading_commands_enabled'];record('server_page_restart_restores_all_custom_levels_scopes_and_legacy_history')
                assert not result['page_errors'];assert not result['unexpected_requests'];assert not result['private_requests'];result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-t12-validation-20261112.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
