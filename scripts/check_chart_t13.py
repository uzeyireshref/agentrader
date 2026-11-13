"""T13 production App/HTTP/SQLite: real pointer creation, v3 geometry and restart."""
import json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from PIL import Image
import math
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
from measure_chart_interactions import INSPECT,ROOT
from agentrader.drawings.calculations import query,CalculationBlocked

def main():
    result={'task':'T13','passed':False,'checks':[],'page_errors':[],'unexpected_requests':[],'private_requests':[],'scope':'Production App, synthetic market and isolated SQLite; no account/order access'}
    with tempfile.TemporaryDirectory(prefix='agentrader-t13-') as folder:
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
            wait_server();market=dict(symbol='BTCUSDT',base_asset='BTC',quote_asset='USDT',contract_type='PERPETUAL',tick_size='0.25');rows=[dict(time=1800000000+i*900,open=100+(i%60)*15,high=110+(i%60)*15,low=90+(i%60)*15,close=105+(i%60)*15,volume=10+i,quote_volume=1000,close_time=(1800000000+(i+1)*900)*1000-1,closed=i<299) for i in range(300)]
            def seed(kind,label,anchors,**extra):return api('/api/workspaces/main/drawings?format_version=7',dict(request_id=label,geometry=dict(kind=kind,label=label,symbol='BTCUSDT',price_source='LAST_PRICE',anchors=[dict(time=rows[i]['time'],price=str(price)) for i,price in anchors],**extra)))
            trend=seed('trend','Trend',[(210,100),(260,400)])
            zone=seed('zone','Zone',[(210,100),(260,400)])
            ray=seed('ray','Ray',[(210,100),(260,400)],schema='chart-line/1')
            extended=seed('extended_line','Extended',[(210,100),(260,400)],schema='chart-line/1')
            channel=seed('parallel_channel','Channel',[(210,100),(260,400),(235,350)],schema='chart-channel/1')
            horizontal=seed('horizontal','Horizontal',[(220,600)])
            fib=seed('fibonacci','Fib',[(210,100),(260,400)],schema='chart-fibonacci/1',levels=['0','0.5','1','1.618'],time_scope='bounded')
            ruler=seed('ruler','Ruler',[(210,100),(260,400)],schema='chart-ruler/1')
            plan=seed('long_plan','Plan',[(220,300),(260,200),(260,600)],schema='chart-position/1',params=dict(risk_budget='100',fee_bps='10',slippage_bps='20'))
            api('/api/workspaces/main/drawing-operations?format_version=7',dict(request_id='purple',operations=[dict(drawing_id=fib['drawing_id'],expected_revision=1,geometry=fib['geometry'],management=dict(schema='chart-management/1',locked=False,hidden=False,intervals=[],color='#9b6ed6',line_width=2,line_style='solid'),deleted=False)]))
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
                def frame():read('(chart.timeScale().setVisibleLogicalRange({from:200,to:280}),series.priceScale().setVisibleRange({from:100,to:1000}),true)');p.wait_for_timeout(150)
                def point(index,price):
                    q=read('({x:chart.timeScale().logicalToCoordinate('+str(index)+'),y:series.priceToCoordinate('+str(price)+')})');b=p.locator('.chart-host').bounding_box();return (b['x']+q['x'],b['y']+q['y'])
                def listing(version=7):return api('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version='+str(version))['drawings']
                def head(key):return api('/api/drawings/'+key+'?format_version=7')
                def create(label,points):
                    before={x['drawing_id'] for x in listing()};p.get_by_label('Çizgi araçları',exact=True).click();p.get_by_label('Çizgi araçları',exact=True).locator('..').get_by_role('button',name=label,exact=True).click()
                    for i,price in points:p.mouse.click(*point(i,price));p.wait_for_timeout(550)
                    added=[x for x in listing() if x['drawing_id'] not in before];assert len(added)==1;return added[0]
                def pick(label):p.locator('.drawing-list button').filter(has=p.get_by_text(label,exact=True)).click()
                def snapshot():return {d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()}
                def mode(value):p.get_by_label('Fiyat ekseni türü',exact=True).select_option(value);p.wait_for_timeout(180)
                def raster(name):
                    p.mouse.move(20,20);filename=ROOT/('reports/chart-t13-'+name+'-20261112.png');p.screenshot(path=str(filename));im=Image.open(filename).convert('RGB');ratio=im.width/1536;host=p.locator('.chart-host').bounding_box();native=read('({y:series.priceToCoordinate(250),left:chart.timeScale().timeToCoordinate('+str(rows[210]['time'])+'),right:chart.timeScale().timeToCoordinate('+str(rows[260]['time'])+')})');expected=(host['y']+native['y'])*ratio;left=max(0,int((host['x']+min(native['left'],native['right'])+15)*ratio));right=min(im.width,int((host['x']+max(native['left'],native['right'])-15)*ratio));hits=[]
                    for y in range(max(0,int(expected)-5),min(im.height,int(expected)+6)):
                        count=sum(sum((a-b)**2 for a,b in zip(im.getpixel((x,y)),(155,110,214)))<65**2 for x in range(left,right))
                        hits.append((count,y))
                    count,row=max(hits);assert count>60,(name,count);assert abs(row-expected)<=3;return dict(expected_y=expected,observed_y=row,matching_pixels=count,dpr=ratio)
                p.goto(base);feed();p.get_by_text('300 mum',exact=True).wait_for();frame();before=snapshot();assert read('series.priceScale().options().mode')==0
                linear_px=raster('linear-dark');assert query(fib['geometry'],'level',ratio='0.5',time=rows[235]['time'])['value']['decimal']=='250';record('linear_exact_fib250_matches_native_coordinate_and_actual_raster',**linear_px)
                p.get_by_label('Çizimleri göster veya gizle').click();pick('Trend');mode('LOG');assert read('series.priceScale().options().mode')==1;assert snapshot()==before;record('native_log_switch_preserves_all_anchor_prices_metadata_and_revisions')
                for item in [trend,ray,extended,channel]:p.locator('[data-drawing="'+item['drawing_id']+'"]').wait_for(state='hidden')
                assert 'BLOCKED' in p.locator('.scale-semantics').inner_text();assert p.get_by_label('Nokta 1 fiyatı',exact=True).is_disabled();assert p.locator('[data-drawing-handles]').count()==0;record('all_unsupported_straight_slopes_are_hidden_with_explicit_blocked_edit_policy')
                p.get_by_label('Çizgi araçları',exact=True).click()
                for label in ['Trend çizgisi','Işın','Uzatılmış çizgi','Paralel kanal']:assert p.get_by_role('button',name=label,exact=True).is_disabled()
                assert p.get_by_role('button',name='Yatay çizgi',exact=True).is_enabled();p.get_by_label('Çizgi araçları',exact=True).click();p.get_by_label('Araç ara',exact=True).click();p.get_by_role('combobox',name='Hızlı erişimde ara').fill('Trend çizgisi');option=p.get_by_role('option').filter(has_text='Trend çizgisi');assert option.get_attribute('aria-disabled')=='true';assert 'Log görünümde engelli' in option.inner_text();p.keyboard.press('Escape');record('rail_and_keyboard_command_search_cannot_activate_blocked_log_tools')
                pick('Fib');assert 'aritmetik' in p.locator('.scale-semantics').inner_text();line=p.locator('[data-drawing="'+fib['drawing_id']+'"] .shape-line[data-fib="0.5"]');assert abs(float(line.get_attribute('y1'))-read('series.priceToCoordinate(250)'))<1;assert abs(float(line.get_attribute('y1'))-read('series.priceToCoordinate(200)'))>20;log_px=raster('log-dark');assert abs(log_px['expected_y']-linear_px['expected_y'])>30;record('log_fib_retains_arithmetic250_not_geometric200_and_raster_matches',**log_px)
                # A log view never injects a fake logarithmic geometry scale into pure queries.
                try:query(fib['geometry'],'level',ratio='0.5',time=rows[235]['time'],scale='LOG');raise AssertionError('Unsupported log math accepted')
                except CalculationBlocked as error:assert error.code=='UNSUPPORTED_SCALE'
                assert query(trend['geometry'],'priceAt',time=rows[235]['time'],times=[r['time'] for r in rows],interval='15m')['value']['decimal']=='250';record('unsupported_log_canonical_query_blocks_while_original_linear_geometry_remains_exact')
                for item in [zone,horizontal,fib,ruler,plan]:p.locator('[data-drawing="'+item['drawing_id']+'"]').wait_for(state='visible')
                for item,selector,price in [(horizontal,'.shape-line',600),(ruler,'.shape-trend',100),(plan,'[data-position-line="0"]',300)]:
                    assert abs(float(p.locator('[data-drawing="'+item['drawing_id']+'"] '+selector).get_attribute('y1'))-read('series.priceToCoordinate('+str(price)+')'))<1
                zr=p.locator('[data-drawing="'+zone['drawing_id']+'"] .shape-zone');assert abs(float(zr.get_attribute('y'))-read('series.priceToCoordinate(400)'))<1;record('horizontal_zone_ruler_endpoints_and_plan_levels_follow_native_log_prices')
                revision=snapshot();p.mouse.move(*point(235,250));p.mouse.down();p.mouse.move(*point(237,275),steps=8);p.mouse.up();p.wait_for_timeout(120);assert snapshot()==revision;assert p.locator('[data-drawing-handles]').count()==0;record('log_pointer_selection_cannot_move_or_save_any_geometry')
                read('(chart.timeScale().setVisibleLogicalRange({from:205,to:270}),true)');p.wait_for_timeout(150);assert abs(float(line.get_attribute('y1'))-read('series.priceToCoordinate(250)'))<1;record('time_zoom_keeps_log_price_projection_aligned')
                p.get_by_label('Göstergeler',exact=True).click();p.get_by_role('button',name='EMA 20 / 50',exact=False).click();p.get_by_label('Paneller',exact=True).click();p.get_by_label('RSI paneli',exact=True).click();assert read('chart.panes().every((p,i)=>i===0||p.priceScale("right").options().mode===0)');assert read('series.priceScale().options().mode')==1;record('log_mode_isolated_to_price_pane_without_rewriting_volume_rsi_or_ema_data')
                # Native mode transitions explicitly refit; no raw manual-range reuse in log mode.
                manual=read('series.priceScale().getVisibleRange()');assert 0<manual['from']<manual['to']<1e10;mode('LINEAR');assert read('series.priceScale().options().autoScale') is True;mode('LOG');assert snapshot()==before;record('mode_transitions_refit_safely_without_reusing_custom_native_log_range')
                p.get_by_label('Açık temaya geç').click();light_px=raster('log-light');record('light_theme_log_raster_matches_native_level',**light_px)
                stored=p.evaluate('JSON.parse(localStorage.getItem("agentrader.chartView"))');assert stored==dict(schema='chart-view/1',price_scale='LOG');sockets.clear();seq=0;p.reload();feed();assert p.get_by_label('Fiyat ekseni türü',exact=True).input_value()=='LOG';assert read('series.priceScale().options().mode')==1;assert snapshot()==before;record('page_reload_restores_versioned_view_preference_without_drawing_migration')
                mode('LINEAR');frame()
                for item in [trend,ray,extended,channel]:p.locator('[data-drawing="'+item['drawing_id']+'"]').wait_for(state='visible')
                assert snapshot()==before;record('return_to_linear_restores_every_blocked_drawing_unchanged')
                assert not result['page_errors'];assert not result['unexpected_requests'];assert not result['private_requests'];result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-t13-validation-20261112.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
