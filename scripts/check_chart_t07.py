"""T07 production App/HTTP/SQLite: real pointer creation, v3 geometry and restart."""
import json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
from measure_chart_interactions import INSPECT,ROOT
from agentrader.drawings.calculations import query,CalculationBlocked

def main():
    result={'task':'T07','passed':False,'checks':[],'page_errors':[],'unexpected_requests':[],'scope':'Production App, synthetic market and isolated SQLite; no account/order access'}
    with tempfile.TemporaryDirectory(prefix='agentrader-t07-') as folder:
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
            def seed(label,price,symbol='BTCUSDT'):
                return api('/api/workspaces/main/drawings',{'request_id':label.replace(' ','-'),'geometry':dict(kind='horizontal',symbol=symbol,price_source='LAST_PRICE',label=label,anchors=[{'time':rows[220]['time'],'price':str(price)}])})
            first=seed('Free-A',120);locked=seed('Locked',130);second=seed('Free-B',110);eth=seed('ETH-line',120,'ETHUSDT')
            markets=[market,{**market,'symbol':'ETHUSDT','base_asset':'ETH'}]
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True);context=browser.new_context(viewport={'width':1536,'height':900},device_scale_factor=1.25);p=context.new_page();p.set_default_timeout(6000);sockets=[];control={'lose':False};writes=[]
                p.on('pageerror',lambda e:result['page_errors'].append(str(e)))
                def guard(r):
                    if not r.request.url.startswith(base+'/'):result['unexpected_requests'].append(r.request.url);r.abort()
                    else:r.continue_()
                p.route('**/*',guard);p.route('**/api/markets',lambda r:r.fulfill(json={'markets':markets}));p.route('**/api/candles*',lambda r:r.fulfill(json={'candles':[],'has_more':False}));p.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
                def mutate(r):
                    writes.append(r.request.post_data)
                    if control['lose']:
                        control['lose']=False;r.fetch();r.abort('failed')
                    else:r.continue_()
                p.route('**/api/workspaces/main/drawing-operations?*',mutate)
                sequences={}
                def feed(symbol='BTCUSDT',interval='15m'):
                    for _ in range(80):
                        if sockets and parse_qs(urlparse(sockets[-1].url).query).get('symbol')==[symbol] and parse_qs(urlparse(sockets[-1].url).query).get('interval')==[interval]:break
                        p.wait_for_timeout(60)
                    else:raise AssertionError('Missing current socket')
                    ws=sockets[-1];key=id(ws);sequences[key]=sequences.get(key,0)+1;step=900 if interval=='15m' else 3600
                    data=[{**r,'time':1800000000+i*step,'close_time':(1800000000+(i+1)*step)*1000-1} for i,r in enumerate(rows)]
                    ws.send(json.dumps(dict(type='snapshot',symbol=symbol,interval=interval,generation=1,sequence=sequences[key],status='LIVE',received_at=int(time.time()*1000),market=next(m for m in markets if m['symbol']==symbol),quality={'state':'OK','missing_bars':0},candles=data)));p.wait_for_timeout(200)
                def read(expr):return p.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');'+'}')
                def frame():read('(chart.timeScale().setVisibleLogicalRange({from:200,to:280}),series.priceScale().setVisibleRange({from:100,to:150}),true)');p.wait_for_timeout(150)
                def point(index,price):
                    q=read('({x:chart.timeScale().logicalToCoordinate('+str(index)+'),y:series.priceToCoordinate('+str(price)+')})');b=p.locator('.chart-host').bounding_box();return (b['x']+q['x'],b['y']+q['y'])
                def listing(version=4):return api('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version='+str(version))['drawings']
                def head(key):return api('/api/drawings/'+key+'?format_version=4')
                def select(label):p.locator('.drawing-list button').filter(has_text=label).click()
                def save_action(action):
                    with p.expect_response(lambda r:'/drawing-operations?' in r.url) as response:action()
                    assert response.value.status==200
                    p.wait_for_timeout(120)
                def drag(price,delta):
                    frame();p.mouse.move(*point(230,price));p.mouse.down();p.mouse.move(*point(230,price+delta),steps=8);p.mouse.up();p.wait_for_timeout(250)
                p.goto(base);feed();p.get_by_text('300 mum',exact=True).wait_for();p.get_by_label('Çizimleri göster veya gizle').click();frame()
                select('Locked');save_action(lambda:p.get_by_label('Çizimi kilitle',exact=True).click());assert p.get_by_label('Çizim fiyatı',exact=True).is_disabled();assert p.get_by_label('Çizgi rengi',exact=True).is_disabled();lock_head=head(locked['drawing_id']);drag(130,5);assert head(locked['drawing_id'])==lock_head;record('real_lock_disables_form_and_prevents_pointer_geometry_write')
                select('Free-A');save_action(lambda:p.get_by_label('Çizgi rengi',exact=True).select_option('#9b6ed6'));save_action(lambda:p.get_by_label('Çizgi kalınlığı',exact=True).select_option('3'));save_action(lambda:p.get_by_label('Çizgi stili',exact=True).select_option('dashed'));style=p.locator('[data-drawing="'+first['drawing_id']+'"] .shape-line').evaluate('e=>({color:getComputedStyle(e).stroke,width:getComputedStyle(e).strokeWidth,dash:getComputedStyle(e).strokeDasharray})');assert style['width']=='3px' and style['color']=='rgb(155, 110, 214)' and '6' in style['dash'];record('persistent_color_width_and_dash_apply_to_actual_svg')
                save_action(lambda:p.get_by_label('Çizimi gizle',exact=True).click());assert p.locator('[data-drawing="'+first['drawing_id']+'"]').count()==0;assert p.locator('.drawing-list button').filter(has_text='Free-A').count()==1;hidden=head(first['drawing_id']);assert hidden['tracking']=='NOT_IMPLEMENTED';assert hidden['geometry']==first['geometry'];save_action(lambda:p.get_by_label('Çizimi gizle',exact=True).click());record('hide_preserves_geometry_and_tracking_and_remains_selectable_in_list')
                save_action(lambda:p.get_by_label('Çizimin zaman dilimi kapsamı',exact=True).select_option('custom'));assert head(first['drawing_id'])['management']['intervals']==['15m'];p.get_by_role('button',name='1 sa',exact=True).click();feed(interval='1h');assert p.locator('[data-drawing="'+first['drawing_id']+'"]').count()==0;assert p.locator('.drawing-list button').filter(has_text='Free-A').count()==1;p.get_by_role('button',name='15 dk',exact=True).click();feed();frame();assert p.locator('[data-drawing="'+first['drawing_id']+'"]').count()==1;record('timeframe_visibility_filters_canvas_without_losing_saved_object')
                select('Locked');before_ids={d['drawing_id'] for d in listing()};save_action(lambda:p.get_by_role('button',name='Çoğalt',exact=True).click());copy=next(d for d in listing() if d['drawing_id'] not in before_ids);assert copy['drawing_id']!=locked['drawing_id'];assert not copy['management']['locked'];assert copy['tracking']=='NOT_IMPLEMENTED';assert copy['geometry']['anchors']==locked['geometry']['anchors'];record('duplicate_uses_new_identity_and_does_not_inherit_lock_or_bot_activation')
                save_action(lambda:p.get_by_label('Çizim değişikliğini geri al').click());assert head(copy['drawing_id'])['deleted'];save_action(lambda:p.get_by_label('Çizim değişikliğini yinele').click());assert not head(copy['drawing_id'])['deleted'];p.get_by_role('button',name='Sil',exact=True).click();p.wait_for_timeout(180);record('duplicate_undo_redo_restores_same_new_identity')
                p.get_by_role('button',name='Seçimi temizle',exact=True).click() if p.get_by_role('button',name='Seçimi temizle',exact=True).is_enabled() else None
                for name in ['Free-A','Locked','Free-B']:p.get_by_label(name+' seçimi',exact=True).check()
                assert '3 çizim seçili' in p.locator('.drawing-editor').inner_text();assert p.get_by_label('Çizim fiyatı',exact=True).count()==0
                pre=[head(d['drawing_id']) for d in [first,locked,second]];write_count=len(writes);drag(120,5);post=[head(d['drawing_id']) for d in [first,locked,second]];assert [d['geometry']['anchors'][0]['price'] for d in post]==['125.00','130','115.00'];assert len(writes)==write_count+1;assert len(json.loads(writes[-1])['operations'])==2;assert post[1]['revision']==pre[1]['revision'];p.screenshot(path=str(ROOT/'reports/chart-t07-multiselect-20261112.png'));record('mixed_three_selection_moves_two_free_drawings_in_one_atomic_write')
                save_action(lambda:p.get_by_label('Çizim değişikliğini geri al').click());assert [head(d['drawing_id'])['geometry'] for d in [first,locked,second]]==[d['geometry'] for d in pre];save_action(lambda:p.get_by_label('Çizim değişikliğini yinele').click());assert [head(d['drawing_id'])['geometry'] for d in [first,locked,second]]==[d['geometry'] for d in post];record('one_undo_and_redo_restore_entire_free_group_without_touching_locked_revision')
                p.get_by_role('button',name='Seçimi temizle',exact=True).click();select('Free-A');control['lose']=True;p.get_by_label('Çizimi gizle',exact=True).click();p.get_by_role('button',name='Aynı kaydı tekrar dene',exact=True).wait_for();committed=head(first['drawing_id']);assert committed['management']['hidden'];prior=writes[-1];save_action(lambda:p.get_by_role('button',name='Aynı kaydı tekrar dene',exact=True).click());assert writes[-1]==prior;assert head(first['drawing_id'])['revision']==committed['revision'];assert p.locator('[data-drawing="'+first['drawing_id']+'"]').count()==0;record('lost_committed_response_retries_identical_identity_without_second_revision')
                save_action(lambda:p.get_by_label('Çizimi gizle',exact=True).click());p.get_by_role('button',name='Seçimi temizle',exact=True).click();p.get_by_label('Free-A seçimi',exact=True).check();p.get_by_label('Free-B seçimi',exact=True).check()
                now=head(second['drawing_id']);api('/api/workspaces/main/drawing-operations?format_version=4',dict(request_id='external',operations=[dict(drawing_id=now['drawing_id'],expected_revision=now['revision'],geometry={**now['geometry'],'label':'Free-B external'},management=now['management'],deleted=False)]));before_first=head(first['drawing_id']);drag(125,5);p.get_by_role('button',name='Son kaydı yükle',exact=True).wait_for();assert head(first['drawing_id'])==before_first;assert 'başka bir ekranda' in p.locator('.drawing-error').inner_text();p.get_by_role('button',name='Son kaydı yükle',exact=True).click();p.get_by_role('button',name='Son kaydı yükle',exact=True).wait_for(state='hidden');assert p.locator('.drawing-list button').filter(has_text='Free-B external').count()==1;record('actual_group_409_rolls_back_other_object_and_refresh_recovers_latest_heads')
                p.get_by_label('Sözleşme seç').select_option('ETHUSDT');feed('ETHUSDT');assert p.locator('.drawing-list button').filter(has_text='ETH-line').count()==1;assert p.locator('.drawing-list button').filter(has_text='Free-A').count()==0;p.get_by_label('Sözleşme seç').select_option('BTCUSDT');feed();assert p.locator('.drawing-list button').filter(has_text='Free-A').count()==1;assert p.locator('.selection-caption').inner_text().startswith('0 seçili');record('market_roundtrip_isolates_objects_and_clears_selection')
                select('Free-A');expected={d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()};p.screenshot(path=str(ROOT/'reports/chart-t07-dark-20261112.png'));p.get_by_label('Açık temaya geç').click();p.screenshot(path=str(ROOT/'reports/chart-t07-light-20261112.png'))
                server.terminate();server.wait(timeout=10);server=start();wait_server();sockets.clear();p.reload();feed();assert {d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()}==expected;assert all(d['tracking']=='NOT_IMPLEMENTED' for d in listing());record('server_and_page_restart_preserve_properties_geometries_and_revisions')
                assert not result['page_errors'];assert not result['unexpected_requests'];result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-t07-validation-20261112.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
