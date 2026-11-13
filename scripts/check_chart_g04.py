"""G04 production App/HTTP/SQLite: real pointer creation, v3 geometry and restart."""
import json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
from measure_chart_interactions import INSPECT,ROOT
from agentrader.drawings.calculations import query,CalculationBlocked

def main():
    result={'task':'G04','passed':False,'checks':[],'page_errors':[],'unexpected_requests':[],'private_requests':[],'scope':'Production App, synthetic market and isolated SQLite; no account/order access'}
    with tempfile.TemporaryDirectory(prefix='agentrader-g04-') as folder:
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
                def listing(version=8):return api('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version='+str(version))['drawings']
                def head(key):return api('/api/drawings/'+key+'?format_version=8')
                def create(label,points):
                    before={x['drawing_id'] for x in listing()};p.get_by_label('Çizgi araçları',exact=True).click();p.get_by_label('Çizgi araçları',exact=True).locator('..').get_by_role('button',name=label,exact=True).click()
                    for i,price in points:p.mouse.click(*point(i,price));p.wait_for_timeout(550)
                    added=[x for x in listing() if x['drawing_id'] not in before];assert len(added)==1;return added[0]
                def pick(label):p.locator('.drawing-list button').filter(has=p.get_by_text(label,exact=True)).click()
                def save():
                    with p.expect_response(lambda r:r.request.method=='PATCH' and '/api/drawings/' in r.url) as response:p.get_by_role('button',name='Kaydet',exact=True).click()
                    assert response.value.status==200;p.wait_for_timeout(120)
                def create(label,index,price):
                    before={d['drawing_id'] for d in listing()};p.get_by_label('Açıklama araçları',exact=True).click();p.get_by_label('Açıklama araçları',exact=True).locator('..').get_by_role('button',name=label,exact=True).click();p.mouse.click(*point(index,price));p.wait_for_timeout(550);added=[d for d in listing() if d['drawing_id'] not in before];assert len(added)==1;return added[0]
                def drag_box(item,dx_price=2.5,dx_bars=2):
                    frame();rect=p.locator('[data-drawing="'+item['drawing_id']+'"] .annotation-hit');b=rect.bounding_box();start=(b['x']+b['width']/2,b['y']+b['height']/2);delta=read('({x:chart.timeScale().logicalToCoordinate(240+'+str(dx_bars)+')-chart.timeScale().logicalToCoordinate(240),y:series.priceToCoordinate(120+'+str(dx_price)+')-series.priceToCoordinate(120)})');p.mouse.move(*start);p.mouse.down();p.mouse.move(start[0]+delta['x'],start[1]+delta['y'],steps=8);p.mouse.up();p.wait_for_timeout(220)
                p.goto(base);feed();p.get_by_text('300 mum',exact=True).wait_for();frame()
                text=create('Metin',215,112);note=create('Not',245,138);label=create('Fiyat etiketi',270,124)
                for item in [text,note,label]:assert item['geometry']['schema']=='chart-annotation/1';assert len(item['geometry']['anchors'])==1;assert item['tracking']=='NOT_IMPLEMENTED'
                assert p.locator('#drawing-panel').is_visible();assert len(listing(7))==2 and len(listing())==5;record('three_real_single_click_annotation_tools_open_editor_and_isolate_v8_records')
                pick('Metin');body='İlk satır\n<script>window.__annotationAttack=1</script>\nBakı İstanbul 😀';p.get_by_label('Açıklama metni',exact=True).fill(body);save();saved_text=head(text['drawing_id']);assert saved_text['geometry']['text']==body;g=p.locator('[data-drawing="'+text['drawing_id']+'"]');assert '<script>' in g.locator('.annotation-body').text_content();assert g.locator('script').count()==0;assert p.evaluate('window.__annotationAttack') is None;record('multiline_unicode_and_markup_are_plain_svg_text_without_script_execution')
                pick('Not');long_body='\n'.join(('Satır '+str(i)+' Bakı İstanbul '+('abcdef '*12)) for i in range(8));p.get_by_label('Açıklama metni',exact=True).fill(long_body);save();assert head(note['drawing_id'])['geometry']['text']==long_body;lines=p.locator('[data-drawing="'+note['drawing_id']+'"] .annotation-body').get_attribute('data-lines');visible=json.loads(lines);assert len(visible)<=12 and visible[-1].endswith('…');assert p.locator('[data-drawing="'+note['drawing_id']+'"] title').text_content()==long_body;record('long_wrapped_note_preserves_full_body_with_explicit_visual_ellipsis')
                p.get_by_label('Açıklama metni',exact=True).fill('\n'.join(['x']*9));revision=head(note['drawing_id'])['revision'];p.get_by_role('button',name='Kaydet',exact=True).click();assert '8 satır' in p.locator('.drawing-error').inner_text();assert head(note['drawing_id'])['revision']==revision;p.get_by_label('Açıklama metni',exact=True).fill('Araştırma notu\nHacmi ve kapanışı izle');save();record('invalid_ninth_line_is_rejected_without_server_revision')
                pick('Fiyat etiketi');p.get_by_label('Açıklama metni',exact=True).fill('Takip seviyesi');p.get_by_label('Çizim fiyatı',exact=True).fill('123.75');save();label_saved=head(label['drawing_id']);assert label_saved['geometry']['text']=='Takip seviyesi';assert p.locator('[data-drawing="'+label['drawing_id']+'"] .annotation-body').text_content()=='Takip seviyesi123.75';record('price_label_caption_and_exact_anchor_price_are_independent_persistent_fields')
                pick('Not');before_note=head(note['drawing_id']);drag_box(note);moved_note=head(note['drawing_id']);assert moved_note['geometry']['anchors']==[dict(time=rows[247]['time'],price='140.50')];assert moved_note['geometry']['text']==before_note['geometry']['text'];assert moved_note['revision']==before_note['revision']+1;record('actual_note_card_hit_area_moves_one_anchor_with_text_unchanged')
                pick('Fiyat etiketi');frame();h=p.locator('[data-drawing-handles="'+label['drawing_id']+'"] [data-anchor="0"]');assert p.locator('[data-drawing-handles="'+label['drawing_id']+'"] circle').count()==1;b=h.bounding_box();p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);p.mouse.down();p.mouse.move(*point(272,126.25),steps=8);p.mouse.up();p.wait_for_timeout(220);moved_label=head(label['drawing_id']);assert moved_label['geometry']['anchors']==[dict(time=rows[272]['time'],price='126.25')];assert '126.25' in p.locator('[data-drawing="'+label['drawing_id']+'"] .annotation-body').text_content();record('single_price_label_handle_updates_native_anchor_and_displayed_exact_price')
                p.get_by_label('Çizim değişikliğini geri al').click();p.wait_for_timeout(180);assert head(label['drawing_id'])['geometry']==label_saved['geometry'];p.get_by_label('Çizim değişikliğini yinele').click();p.wait_for_timeout(180);assert head(label['drawing_id'])['geometry']==moved_label['geometry'];record('one_undo_redo_restores_caption_price_and_anchor_together')
                keyboard=[]
                for key,kind,index,price in [('a','text',230,108),('n','note',240,108),('p','price_label',250,108)]:
                    before={d['drawing_id'] for d in listing()};p.locator('.chart-stage').focus();p.keyboard.press(key);p.mouse.click(*point(index,price));p.wait_for_timeout(550);added=[d for d in listing() if d['drawing_id'] not in before];assert len(added)==1 and added[0]['geometry']['kind']==kind;keyboard.append(added[0]);p.get_by_label('Çizim adı',exact=True).fill('Klavye-'+key.upper());save();p.get_by_label('Açıklama metni',exact=True).focus();p.keyboard.type('ANP');assert p.locator('.drawing-tools button[aria-label="İmleç"]').get_attribute('aria-pressed')=='true'
                record('a_n_p_chart_shortcuts_create_correct_tools_and_typing_cannot_switch_tools')
                pick('Not');p.get_by_label('Çizimi kilitle',exact=True).click();p.locator('[data-drawing-handles="'+note['drawing_id']+'"]').wait_for(state='detached');assert p.get_by_label('Açıklama metni',exact=True).is_disabled();locked=head(note['drawing_id']);drag_box(note);assert head(note['drawing_id'])==locked;p.get_by_label('Çizimi gizle',exact=True).click();p.locator('[data-drawing="'+note['drawing_id']+'"]').wait_for(state='detached');record('lock_prevents_body_and_pointer_changes_while_hide_keeps_list_record')
                before={d['drawing_id'] for d in listing()};p.get_by_role('button',name='Çoğalt',exact=True).click();p.wait_for_timeout(220);copy=next(d for d in listing() if d['drawing_id'] not in before);assert copy['geometry']['text']==locked['geometry']['text'];assert not copy['management']['locked'];assert copy['tracking']=='NOT_IMPLEMENTED';p.get_by_label('Çizimi gizle',exact=True).click();p.locator('[data-drawing="'+copy['drawing_id']+'"]').wait_for(state='visible');record('copy_uses_new_unlocked_identity_preserving_plain_body_without_bot_activation')
                for item in [text,note,label]:
                    contract=api('/api/drawings/'+item['drawing_id']+'/contract');assert contract['category']=='annotation';assert not contract['capabilities']['computable'];assert contract['capabilities']['canonical_queries']==[];assert not contract['capabilities']['order_authority']
                record('all_annotation_contracts_explicitly_exclude_canonical_bot_queries_and_orders')
                pick('Fiyat etiketi');before_log={d['drawing_id']:(d['geometry'],d['revision']) for d in listing()};p.get_by_label('Fiyat ekseni türü',exact=True).select_option('LOG');p.wait_for_timeout(160);assert p.locator('[data-drawing-handles]').count()==0;anchor=p.locator('[data-drawing="'+label['drawing_id']+'"] .annotation-anchor');assert abs(float(anchor.get_attribute('cy'))-read('series.priceToCoordinate(126.25)'))<1;assert {d['drawing_id']:(d['geometry'],d['revision']) for d in listing()}==before_log;p.get_by_label('Fiyat ekseni türü',exact=True).select_option('LINEAR');frame();record('log_view_preserves_annotation_prices_and_native_anchor_without_pointer_edit')
                for item,key in zip(keyboard,['A','N','P']):pick('Klavye-'+key);p.get_by_label('Çizimi gizle',exact=True).click();p.locator('[data-drawing="'+item['drawing_id']+'"]').wait_for(state='detached')
                pick('Metin');p.get_by_label('Açıklama metni',exact=True).fill('Seans açılışı\nReferans bölge');save()
                for seed,label_name in [(old,'Eski segment'),(zone,'Eski Fibonacci')]:
                    pick(label_name);p.get_by_label('Çizimi gizle',exact=True).click();p.locator('[data-drawing="'+seed['drawing_id']+'"]').wait_for(state='detached')
                pick('Not kopya');p.get_by_label('Çizgi rengi',exact=True).select_option('#9b6ed6');p.wait_for_timeout(150);p.locator('.shell-drawings').evaluate('e=>e.scrollTop=0');p.screenshot(path=str(ROOT/'reports/chart-g04-dark-20261112.png'));p.get_by_label('Açık temaya geç').click();p.screenshot(path=str(ROOT/'reports/chart-g04-light-20261112.png'));expected={d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()}
                server.terminate();server.wait(timeout=10);server=start();wait_server();sockets.clear();seq=0;p.reload();feed();assert {d['drawing_id']:(d['geometry'],d['management'],d['revision']) for d in listing()}==expected;assert not api('/api/health')['trading_commands_enabled'];record('server_page_restart_restores_annotation_bodies_prices_and_management')
                assert not result['page_errors'];assert not result['unexpected_requests'];assert not result['private_requests'];result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-g04-validation-20261112.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
