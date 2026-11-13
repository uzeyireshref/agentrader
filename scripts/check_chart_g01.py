"""G01 real production App with isolated SQLite and deterministic market input."""
import json, math, os, socket, subprocess, sys, tempfile, time, traceback
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def main():
    result={'task':'G01','passed':False,'checks':[],'page_errors':[],'unexpected_requests':[],
            'scope':'Production App, synthetic stream, isolated SQLite; desktop browser acceptance, not physical GPU/touch'}
    with tempfile.TemporaryDirectory(prefix='agentrader-g01-') as folder:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}';opener=build_opener(ProxyHandler({}))
        env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(Path(folder)/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(Path(folder)/'execution.db'),AGENTRADER_CHART_DATABASE=str(Path(folder)/'market.db'),AGENTRADER_WEB_TOKEN='')
        server=subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def api(path,body=None,method=None):
            req=Request(base+path,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json'},method=method)
            with opener.open(req,timeout=5) as r:return json.load(r)
        def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
        try:
            for _ in range(100):
                try:api('/api/health');break
                except Exception:time.sleep(.1)
            markets=[{'symbol':s,'base_asset':s[:-4],'quote_asset':'USDT','contract_type':'PERPETUAL','tick_size':'0.25'} for s in ('BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','AVAXUSDT','LINKUSDT','ADAUSDT')]
            rows=[]
            for i in range(300):
                o=71000+i*11+math.sin(i*.17)*520;c=o+math.sin(i*1.8)*150
                rows.append(dict(time=1794085200+i*900,open=o,close=c,high=max(o,c)+90,low=min(o,c)-100,volume=150+abs(math.sin(i))*650,quote_volume=10000,close_time=(1794085200+(i+1)*900)*1000-1,closed=i<299))
            seed=api('/api/workspaces/main/drawings',{'request_id':'g01-seed','geometry':{'kind':'horizontal','symbol':'BTCUSDT','price_source':'LAST_PRICE','anchors':[{'time':rows[240]['time'],'price':'74100.00'}],'label':'Referans seviye'}},'POST')
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True);context=browser.new_context(viewport={'width':1536,'height':776},device_scale_factor=1.25)
                p=context.new_page();sockets=[]
                p.on('pageerror',lambda e:result['page_errors'].append(str(e)))
                def guard(route):
                    if not route.request.url.startswith(base+'/'):
                        result['unexpected_requests'].append(route.request.url);route.abort()
                    else:route.continue_()
                p.route('**/*',guard);p.route('**/api/markets',lambda r:r.fulfill(json={'markets':markets}));p.route('**/api/candles*',lambda r:r.fulfill(json={'candles':[],'has_more':False}));p.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
                def feed():
                    p.wait_for_function("document.querySelector('.chart-host canvas') !== null")
                    for _ in range(80):
                        if sockets:break
                        p.wait_for_timeout(100)
                    sockets[-1].send(json.dumps(dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=1,status='LIVE',received_at=int(time.time()*1000),market=markets[0],quality={'state':'OK','missing_bars':0},candles=rows)))
                    p.get_by_text('300 mum',exact=True).wait_for();p.wait_for_timeout(250)
                p.goto(base);p.get_by_role('heading',name='Grafik hazırlanıyor',exact=True).wait_for();record('loading_state_remains_visible');feed();assert p.locator('.shell-diagnostics').count()==0
                record('real_app_stream_and_diagnostics_opt_in')
                for width in [1536,1280,1024]:
                    p.set_viewport_size({'width':width,'height':776});p.wait_for_timeout(200)
                    shape=p.locator('.chart-stage').bounding_box();assert shape['height']>600
                    assert p.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    for theme in ['dark','light']:
                        if p.locator('.terminal').get_attribute('data-theme')!=theme:p.get_by_role('button',name='Açık temaya geç' if theme=='light' else 'Koyu temaya geç',exact=True).click()
                        p.screenshot(path=str(ROOT/f'reports/chart-g01-{width}-{theme}.png'))
                    record('desktop_two_themes_no_horizontal_overflow',width=width,chart_height=shape['height'])
                assert len(sockets)==1;record('theme_and_resize_preserve_market_connection')
                before=p.locator('.chart-host').bounding_box()['width'];p.get_by_label('Yan paneli kapat',exact=True).click();p.wait_for_timeout(200)
                after=p.locator('.chart-host').bounding_box()['width'];assert after-before>250
                p.keyboard.press('/');p.get_by_label('Coin ara',exact=True).wait_for(state='visible');assert p.get_by_label('Coin ara',exact=True).evaluate('(e)=>e===document.activeElement')
                p.get_by_label('Coin ara',exact=True).fill('SOL');assert p.locator('.market-row:visible').count()==1
                p.get_by_label('Coin ara',exact=True).fill('');record('panel_resize_search_shortcut_and_filter',gained_css_px=after-before)
                p.get_by_label('Çizimleri göster veya gizle',exact=True).click();p.locator('.drawing-list button').filter(has_text='Referans seviye').click()
                p.get_by_label('Çizim fiyatı',exact=True).fill('74125.25');p.get_by_role('button',name='Kaydet',exact=True).click();p.wait_for_timeout(300)
                current=api('/api/drawings/'+seed['drawing_id']);assert current['geometry']['anchors'][0]['price']=='74125.25';record('relocated_editor_persists_exact_price_in_isolated_sqlite')
                p.get_by_label('Çizim değişikliğini geri al',exact=True).click();p.wait_for_timeout(250);assert api('/api/drawings/'+seed['drawing_id'])['geometry']['anchors'][0]['price']=='74100.00'
                p.get_by_label('Çizim değişikliğini yinele',exact=True).click();p.wait_for_timeout(250);assert api('/api/drawings/'+seed['drawing_id'])['geometry']['anchors'][0]['price']=='74125.25';record('existing_undo_redo_survives_shell')
                p.get_by_label('Çizgi araçları',exact=True).click();p.get_by_label('Trend çizgisi',exact=True).click();assert p.locator('.tool-hint').is_visible();p.get_by_role('region',name='Fiyat grafiği',exact=True).focus();p.keyboard.press('Escape');assert p.get_by_label('İmleç',exact=True).get_attribute('aria-pressed')=='true';record('grouped_tool_selection_and_escape_cancel')
                p.get_by_label('Göstergeler',exact=True).focus();p.keyboard.press('Enter');p.keyboard.press('Escape');assert not p.get_by_label('Göstergeler',exact=True).locator('..').evaluate('(e)=>e.open');assert p.get_by_label('Göstergeler',exact=True).evaluate('(e)=>e===document.activeElement');record('disclosure_escape_returns_focus')
                p.get_by_label('Grafiği tam ekran aç',exact=True).click();p.wait_for_timeout(200);assert p.evaluate('!!document.fullscreenElement');p.get_by_label('Tam ekrandan çık',exact=True).click();record('fullscreen_preserves_shell')
                sockets[-1].send(json.dumps(dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=2,status='STALE',received_at=int(time.time()*1000),market=markets[0],quality={'state':'OK','missing_bars':0},candles=rows)))
                p.locator('.connection').filter(has_text='Veri gecikiyor').wait_for();assert not p.locator('.shell-state').evaluate("e=>e.classList.contains('is-live')");record('stale_state_not_presented_as_live')
                sockets.clear();p.reload();feed();assert p.locator('.terminal').get_attribute('data-theme')=='light';p.get_by_label('Çizimleri göster veya gizle',exact=True).click();assert p.locator('.drawing-list button').filter(has_text='Referans seviye').count()==1;record('theme_persists_and_saved_drawing_reload')
                p.set_viewport_size({'width':1536,'height':776});p.screenshot(path=str(ROOT/'reports/chart-g01-final.png'))
                assert not result['page_errors'];assert not result['unexpected_requests'];result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-g01-validation-20261111.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
