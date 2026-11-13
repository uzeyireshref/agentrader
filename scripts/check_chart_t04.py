"""T04 production App/HTTP/SQLite: real pointer creation, v3 geometry and restart."""
import json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
from measure_chart_interactions import INSPECT,ROOT
from agentrader.drawings.calculations import query,CalculationBlocked

def main():
    result={'task':'T04','passed':False,'checks':[],'page_errors':[],'unexpected_requests':[],'private_requests':[],'scope':'Production App, synthetic market and isolated SQLite; no account/order access'}
    with tempfile.TemporaryDirectory(prefix='agentrader-t04-') as folder:
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
                def listing(version=5):return api('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version='+str(version))['drawings']
                def head(key):return api('/api/drawings/'+key+'?format_version=5')
                def create(label,points):
                    before={x['drawing_id'] for x in listing()};p.get_by_label('Çizgi araçları',exact=True).click();p.get_by_label('Çizgi araçları',exact=True).locator('..').get_by_role('button',name=label,exact=True).click()
                    for i,price in points:p.mouse.click(*point(i,price));p.wait_for_timeout(550)
                    added=[x for x in listing() if x['drawing_id'] not in before];assert len(added)==1;return added[0]
                def pick(label):p.locator('.drawing-list button').filter(has=p.get_by_text(label,exact=True)).click()
                def save():
                    with p.expect_response(lambda r:r.request.method=='PATCH' and '/api/drawings/' in r.url) as resp:p.get_by_role('button',name='Kaydet',exact=True).click()
                    assert resp.value.status==200;p.wait_for_timeout(150)
                def canonical(item):return query(item['geometry'],'riskReward')['value']
                p.goto(base);feed();p.get_by_text('300 mum',exact=True).wait_for();frame()
                # Plan tools have their own rail menu; leave the line helper intact for regression semantics.
                def create_plan(label,points):
                    before={d['drawing_id'] for d in listing()};p.get_by_label('Planlama araçları',exact=True).click();p.get_by_label('Planlama araçları',exact=True).locator('..').get_by_role('button',name=label,exact=True).click()
                    for i,price in points:p.mouse.click(*point(i,price));p.wait_for_timeout(550)
                    added=[d for d in listing() if d['drawing_id'] not in before];assert len(added)==1;return added[0]
                long=create_plan('Long plan',[(220,120),(230,110),(250,140)]);short=create_plan('Short plan',[(255,130),(260,140),(280,110)])
                for item in [long,short]:assert item['geometry']['schema']=='chart-position/1';assert canonical(item)['gross_rr']['decimal']=='2';assert item['tracking']=='NOT_IMPLEMENTED';assert item['geometry']['anchors'][1]['time']==item['geometry']['anchors'][2]['time']
                assert len(listing(4))==2 and len(listing())==4;record('real_three_click_long_and_short_creation_with_v5_old_client_isolation')
                for item in [long,short]:
                    g=item['geometry'];rect=p.locator('[data-drawing="'+item['drawing_id']+'"] .position-risk');r=rect.evaluate('e=>({x:+e.getAttribute("x"),y:+e.getAttribute("y"),w:+e.getAttribute("width"),h:+e.getAttribute("height")})');expected=read('({x:chart.timeScale().timeToCoordinate('+str(g['anchors'][0]['time'])+'),y:series.priceToCoordinate('+str(max(float(a['price']) for a in g['anchors'][:2]))+'),end:chart.timeScale().timeToCoordinate('+str(g['anchors'][2]['time'])+'),h:Math.abs(series.priceToCoordinate('+g['anchors'][0]['price']+')-series.priceToCoordinate('+g['anchors'][1]['price']+'))})');assert abs(r['y']-expected['y'])<1 and abs(r['x']-expected['x'])<1 and abs(r['h']-expected['h'])<1 and abs(r['w']-(expected['end']-expected['x']))<1
                    for index,anchor in enumerate(g['anchors']):
                        line=p.locator('[data-drawing="'+item['drawing_id']+'"] [data-position-line="'+str(index)+'"]');assert abs(float(line.get_attribute('y1'))-read('series.priceToCoordinate('+anchor['price']+')'))<1
                record('risk_rectangle_native_coordinates_match_long_and_short_levels')
                p.get_by_label('Çizimleri göster veya gizle').click();pick('Long plan');assert p.locator('[data-drawing-handles="'+long['drawing_id']+'"] circle').count()==3
                p.get_by_label('Plan risk bütçesi',exact=True).fill('100');p.get_by_label('Plan ücret baz puanı',exact=True).fill('10');p.get_by_label('Plan kayma baz puanı',exact=True).fill('20');save();costed=head(long['drawing_id']);m=canonical(costed);assert m['net_risk']['decimal']=='10.69002';assert m['net_reward']['decimal']=='19.22004';assert m['loss_budget']['decimal']=='100';summary=p.get_by_role('region',name='Plan risk ve getiri özeti');assert '1,797' in summary.inner_text();assert m['quantity']['decimal'] is None;record('independent_cost_reference_and_budget_are_exact_and_nonterminating_qty_is_not_faked')
                p.get_by_label('Stop fiyatı',exact=True).fill('120');revision=head(long['drawing_id'])['revision'];p.get_by_role('button',name='Kaydet',exact=True).click();assert 'stop < giriş < hedef' in p.locator('.drawing-error').inner_text();assert head(long['drawing_id'])['revision']==revision;p.get_by_label('Stop fiyatı',exact=True).fill('110');record('zero_risk_form_edit_is_rejected_without_server_revision')
                p.get_by_label('Hedef fiyatı',exact=True).fill('150');save();saved=head(long['drawing_id']);assert canonical(saved)['gross_rr']['decimal']=='3';record('numeric_target_edit_updates_canonical_and_visual_rr')
                frame();h=p.locator('[data-drawing-handles="'+long['drawing_id']+'"] [data-anchor="1"]');b=h.bounding_box();p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);p.mouse.down();p.mouse.move(*point(252,115),steps=8);p.mouse.up();p.wait_for_timeout(220);moved=head(long['drawing_id']);assert moved['geometry']['anchors'][1]['price']=='115.00';assert moved['geometry']['anchors'][1]['time']==moved['geometry']['anchors'][2]['time']==rows[252]['time'];assert canonical(moved)['gross_rr']['decimal']=='6';record('actual_stop_handle_drag_preserves_shared_horizon_and_exact_rr')
                p.get_by_label('Çizim değişikliğini geri al').click();p.wait_for_timeout(180);assert head(long['drawing_id'])['geometry']==saved['geometry'];p.get_by_label('Çizim değişikliğini yinele').click();p.wait_for_timeout(180);assert head(long['drawing_id'])['geometry']==moved['geometry'];record('undo_redo_preserves_position_geometry_and_cost_assumptions')
                frame();p.mouse.move(*point(235,135));p.mouse.down();p.mouse.move(*point(237,137.5),steps=8);p.mouse.up();p.wait_for_timeout(200);translated=head(long['drawing_id']);assert [a['price'] for a in translated['geometry']['anchors']]==['122.50','117.50','152.50'];assert translated['geometry']['params']==moved['geometry']['params'];record('whole_position_drag_moves_all_levels_with_unchanged_cost_model')
                pick('Short plan');p.get_by_label('Plan risk bütçesi',exact=True).fill('50');p.get_by_label('Plan ücret baz puanı',exact=True).fill('10');p.get_by_label('Plan kayma baz puanı',exact=True).fill('20');save();s=head(short['drawing_id']);assert canonical(s)['net_risk']['decimal']=='10.81002';assert canonical(s)['net_reward']['decimal']=='19.28004';record('short_adverse_fill_signs_and_two_sided_fees_match_independent_reference')
                pick('Long plan');before={d['drawing_id'] for d in listing()};p.get_by_role('button',name='Çoğalt',exact=True).click();p.wait_for_timeout(200);copy=next(d for d in listing() if d['drawing_id'] not in before);assert copy['geometry']['params']==translated['geometry']['params'];assert copy['tracking']=='NOT_IMPLEMENTED';assert copy['drawing_id']!=long['drawing_id'];record('plan_copy_keeps_assumptions_with_new_identity_and_no_execution')
                p.get_by_label('Çizimi kilitle',exact=True).click();p.wait_for_timeout(200);assert p.get_by_label('Giriş fiyatı',exact=True).is_disabled();p.locator('[data-drawing-handles="'+copy['drawing_id']+'"]').wait_for(state='detached');p.get_by_label('Çizimi gizle',exact=True).click();p.wait_for_timeout(200);p.locator('[data-drawing="'+copy['drawing_id']+'"]').wait_for(state='detached');record('plan_inherits_t07_lock_hide_and_handle_policy')
                pick('Long plan');p.screenshot(path=str(ROOT/'reports/chart-t04-dark-20261112.png'));p.get_by_label('Açık temaya geç').click();p.screenshot(path=str(ROOT/'reports/chart-t04-light-20261112.png'));expected={d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()}
                server.terminate();server.wait(timeout=10);server=start();wait_server();sockets.clear();seq=0;p.reload();feed();assert {d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()}==expected;assert api('/api/health')['trading_commands_enabled'] is False;record('restart_restores_plan_costs_levels_and_visibility_without_order_authority')
                assert not result['page_errors'];assert not result['unexpected_requests'];assert not result['private_requests'];result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-t04-validation-20261112.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
