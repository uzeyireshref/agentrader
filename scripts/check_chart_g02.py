"""Production App pane ownership, native resize and SVG alignment acceptance."""
import json,math,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
from measure_chart_interactions import INSPECT,ROOT

def main():
    result={'task':'G02','passed':False,'checks':[],'page_errors':[],'unexpected_requests':[], 'scope':'Real App/native engine, synthetic stream and isolated SQLite; not physical GPU/touch'}
    with tempfile.TemporaryDirectory(prefix='agentrader-g02-') as folder:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}';opener=build_opener(ProxyHandler({}));env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(Path(folder)/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(Path(folder)/'execution.db'),AGENTRADER_CHART_DATABASE=str(Path(folder)/'market.db'),AGENTRADER_WEB_TOKEN='')
        server=subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def api(path,body=None):
            req=Request(base+path,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json'})
            with opener.open(req,timeout=5) as r:return json.load(r)
        def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
        try:
            for _ in range(100):
                try:api('/api/health');break
                except Exception:time.sleep(.1)
            market=dict(symbol='BTCUSDT',base_asset='BTC',quote_asset='USDT',contract_type='PERPETUAL',tick_size='0.25');rows=[]
            for i in range(300):
                o=71000+i*11+math.sin(i*.17)*520;c=o+math.sin(i*1.8)*150;t=1794085200+i*900
                rows.append(dict(time=t,open=o,close=c,high=max(o,c)+90,low=min(o,c)-100,volume=150+abs(math.sin(i))*650,quote_volume=10000,close_time=(t+900)*1000-1,closed=i<299))
            seed=api('/api/workspaces/main/drawings',{'request_id':'g02-line','geometry':{'kind':'horizontal','symbol':'BTCUSDT','price_source':'LAST_PRICE','anchors':[{'time':rows[240]['time'],'price':'74100.00'}],'label':'Pane referansı'}})
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True);context=browser.new_context(viewport={'width':1536,'height':776},device_scale_factor=1.25);p=context.new_page();p.set_default_timeout(5000);sockets=[]
                p.on('pageerror',lambda e:result['page_errors'].append(str(e)))
                def guard(r):
                    if not r.request.url.startswith(base+'/'):result['unexpected_requests'].append(r.request.url);r.abort()
                    else:r.continue_()
                p.route('**/*',guard);p.route('**/api/markets',lambda r:r.fulfill(json={'markets':[market]}));p.route('**/api/candles*',lambda r:r.fulfill(json={'candles':[],'has_more':False}));p.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
                p.goto(base)
                for _ in range(80):
                    if sockets:break
                    p.wait_for_timeout(100)
                sockets[-1].send(json.dumps(dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=1,status='LIVE',received_at=int(time.time()*1000),market=market,quality={'state':'OK','missing_bars':0},candles=rows)));p.get_by_text('300 mum',exact=True).wait_for();p.wait_for_timeout(300)
                def read(expr):return p.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');'+'}')
                def panes():return read("chart.panes().map(p=>({height:p.getHeight(),index:p.paneIndex(),series:p.getSeries().map(s=>({type:s.seriesType(),title:s.options().title,visible:s.options().visible,scale:s.options().priceScaleId,auto:s.priceScale().options().autoScale}))}))")
                def menu(name):
                    toggle=p.get_by_label('Paneller',exact=True)
                    details=toggle.locator('..')
                    if details.get_attribute('open') is None:toggle.click()
                    assert details.get_attribute('open') is not None, 'Panel menu did not open'
                    p.get_by_role('button',name=name,exact=True).click();p.wait_for_timeout(180)
                def aligned():
                    observed=p.locator('[data-drawing="'+seed['drawing_id']+'"] .shape-line').get_attribute('y1');expected=read('series.priceToCoordinate(74100)');height=read('chart.paneSize(0).height');svg=p.locator('.drawings-overlay').bounding_box();assert abs(float(observed)-expected)<1;assert abs(svg['height']-height)<1;return height
                initial=panes();assert len(initial)==2;assert initial[1]['series'][0]['scale']=='right';aligned();record('price_and_volume_have_distinct_native_panes_and_scales')
                menu('RSI paneli');p.get_by_label('Otomatik RSI ölçeği').wait_for();assert len(panes())==3
                rsi=read("chart.panes().flatMap(p=>p.getSeries()).find(s=>s.options().title==='RSI 14').data().slice(-1)[0].value")
                assert 0<=rsi<=100;aligned();record('rsi_owns_third_pane_and_bounded_values')
                p.get_by_label('Otomatik RSI ölçeği').click();assert read("chart.panes()[2].getSeries()[0].priceScale().options().autoScale")==False;assert read('series.priceScale().options().autoScale')==True
                p.get_by_label('Otomatik hacim ölçeği').click();assert read("chart.panes()[1].getSeries()[0].priceScale().options().autoScale")==False;assert read('series.priceScale().options().autoScale')==True;record('auxiliary_manual_scale_does_not_change_price_scale')
                p.get_by_label('Göstergeler',exact=True).click();p.get_by_role('button',name='EMA 20 / 50',exact=False).click();p.wait_for_timeout(180);assert read("chart.panes()[2].getSeries()[0].priceScale().options().autoScale")==False;assert len(panes())==3;record('ema_toggle_keeps_rsi_instance_and_manual_scale')
                p.get_by_label('Hacim panelini gizle',exact=True).click();p.wait_for_timeout(180);state=panes();assert len(state)==2;assert any(s['title']=='RSI 14' for s in state[1]['series']);assert not any(s['type']=='Histogram' and s['visible'] for s in state[0]['series']);aligned();record('hiding_volume_compacts_panes_without_rsi_or_price_mix')
                menu('Hacim paneli');state=panes();assert read("chart.panes()[1].getSeries()[0].data().length")==300;assert read("chart.panes()[1].getSeries()[0].priceScale().getVisibleRange()") is not None;assert len(state)==3;assert state[1]['series'][0]['type']=='Histogram';assert state[2]['series'][0]['title']=='RSI 14';aligned();record('restoring_volume_reorders_by_series_owner')
                box=p.locator('.chart-host').bounding_box();before=read('chart.panes()[0].getHeight()');separator_y=box['y']+before+1
                p.mouse.move(box['x']+150,separator_y);p.mouse.down();p.mouse.move(box['x']+150,separator_y-55,steps=8);p.mouse.up();p.wait_for_timeout(200);after=read('chart.panes()[0].getHeight()');result['resize_attempt']={'before':before,'after':after,'y':separator_y};assert abs(after-before)>25;aligned();record('native_separator_drag_resizes_and_reprojects_svg',before=before,after=after)
                menu('Fiyat alanını büyüt');focus=read('chart.panes()[0].getHeight()');assert focus>after;p.mouse.move(box['x']+150,box['y']+focus+1);p.mouse.down();p.mouse.move(box['x']+150,box['y']+focus-30,steps=5);p.mouse.up();p.wait_for_timeout(150);menu('Fiyat alanını büyüt');assert abs(read('chart.panes()[0].getHeight()')-focus)<1;menu('Panel boyutlarını sıfırla');balanced=read('chart.panes()[0].getHeight()');assert balanced<focus;aligned();record('explicit_layout_presets_and_reset')
                assert len(sockets)==1;assert api('/api/drawings/'+seed['drawing_id'])['revision']==1;record('pane_controls_do_not_reconnect_or_write_drawing_geometry')
                box=p.locator('.chart-host').bounding_box();sample=rows[250]
                point=read("(()=>{const r=chart.panes()[2].getSeries()[0],e=r.getPane().getHTMLElement().getBoundingClientRect(),h=chart.chartElement().getBoundingClientRect();return {x:chart.timeScale().timeToCoordinate("+str(sample['time'])+"),y:r.priceToCoordinate(r.data().find(v=>v.time==="+str(sample['time'])+").value)+e.top-h.top};})()")
                p.mouse.move(box['x']+point['x'],box['y']+point['y']);p.wait_for_timeout(100)
                assert 'A ' in p.get_by_label('Seçili mum fiyatları').inner_text();record('crosshair_on_rsi_reads_price_ohlc_at_same_timestamp')
                p.get_by_label('Fiyat-zaman cetveli',exact=True).click();p.mouse.click(box['x']+point['x'],box['y']+point['y']);p.wait_for_timeout(100)
                assert api('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version=2')['drawings'][0]['revision']==1
                assert 'İlk noktayı' in p.locator('.tool-hint').inner_text();p.get_by_role('region',name='Fiyat grafiği').focus();p.keyboard.press('Escape');record('auxiliary_pane_click_cannot_start_price_drawing')
                for width in [1536,1280,1024]:
                    p.set_viewport_size({'width':width,'height':776});p.wait_for_timeout(180);aligned();assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');p.screenshot(path=str(ROOT/f'reports/chart-g02-{width}-dark.png'))
                p.get_by_label('Açık temaya geç').click();p.wait_for_timeout(150);aligned();p.screenshot(path=str(ROOT/'reports/chart-g02-1024-light.png'));record('three_desktop_widths_and_light_theme_preserve_projection')
                session=context.new_cdp_session(p);session.send('Emulation.setDeviceMetricsOverride',{'width':1024,'height':776,'deviceScaleFactor':2,'mobile':False});p.wait_for_timeout(180);assert p.evaluate('devicePixelRatio')==2;aligned();p.screenshot(path=str(ROOT/'reports/chart-g02-dpr2.png'));session.send('Emulation.clearDeviceMetricsOverride');session.detach();p.wait_for_timeout(180);record('dpr2_keeps_native_svg_css_coordinate_alignment')
                p.get_by_label('Grafiği tam ekran aç').click();p.wait_for_timeout(180);aligned();p.get_by_label('Tam ekrandan çık').click();p.set_viewport_size({'width':1536,'height':776});p.wait_for_timeout(250);record('fullscreen_preserves_pane_ownership_and_projection')
                p.get_by_label('RSI panelini gizle').click();p.wait_for_timeout(150);assert len(panes())==2;menu('Hacim paneli');assert len(panes())==1;aligned();menu('RSI paneli');assert len(panes())==2;menu('Hacim paneli');assert len(panes())==3;aligned();record('repeated_remove_readd_has_no_empty_or_duplicate_panes')
                assert not result['page_errors'];assert not result['unexpected_requests'];result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-g02-validation-20261111.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
