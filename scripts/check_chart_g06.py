"""G06 real production App, deterministic catalog/streams, isolated SQLite."""
import json, math, os, socket, subprocess, sys, tempfile, time, traceback
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def main():
    result={'task':'G06','passed':False,'checks':[],'page_errors':[],'unexpected_requests':[], 'scope':'Real production App; synthetic public catalog/stream; isolated SQLite, no user DB writes'}
    with tempfile.TemporaryDirectory(prefix='agentrader-g06-') as folder:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}';opener=build_opener(ProxyHandler({}))
        env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(Path(folder)/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(Path(folder)/'execution.db'),AGENTRADER_CHART_DATABASE=str(Path(folder)/'market.db'),AGENTRADER_WEB_TOKEN='')
        server=subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def api(path,body=None):
            req=Request(base+path,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json'})
            with opener.open(req,timeout=5) as r:return json.load(r)
        def record(name,**extra):result['checks'].append(dict(name=name,passed=True,**extra))
        try:
            for _ in range(100):
                try:api('/api/health');break
                except Exception:time.sleep(.1)
            markets=[dict(symbol=b+'USDT',base_asset=b,quote_asset='USDT',contract_type='PERPETUAL',tick_size='0.25') for b in ['BTC','ETH','SOL']+[f'COIN{i:03}' for i in range(100)]]
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True);context=browser.new_context(viewport={'width':1536,'height':776},device_scale_factor=1.25);p=context.new_page();sockets=[]
                p.on('pageerror',lambda e:result['page_errors'].append(str(e)))
                def guard(route):
                    if not route.request.url.startswith(base+'/'):result['unexpected_requests'].append(route.request.url);route.abort()
                    else:route.continue_()
                p.route('**/*',guard);p.route('**/api/markets',lambda r:r.fulfill(json={'markets':markets}));p.route('**/api/candles*',lambda r:r.fulfill(json={'candles':[],'has_more':False}));p.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
                def feed(expected_symbol='BTCUSDT',expected_interval='15m'):
                    for _ in range(80):
                        if sockets:
                            q=parse_qs(urlparse(sockets[-1].url).query)
                            if q.get('symbol')==[expected_symbol] and q.get('interval')==[expected_interval]:break
                        p.wait_for_timeout(100)
                    else:raise AssertionError('Expected stream not opened')
                    step={'15m':900,'1h':3600}[expected_interval];rows=[]
                    for i in range(300):
                        o=71000+i*11+math.sin(i*.17)*520;c=o+math.sin(i*1.8)*150;t=1790002800+i*step
                        rows.append(dict(time=t,open=o,close=c,high=max(o,c)+90,low=min(o,c)-100,volume=150+i,quote_volume=10000,close_time=(t+step)*1000-1,closed=i<299))
                    sockets[-1].send(json.dumps(dict(type='snapshot',symbol=expected_symbol,interval=expected_interval,generation=1,sequence=1,status='LIVE',received_at=int(time.time()*1000),market=next(m for m in markets if m['symbol']==expected_symbol),quality={'state':'OK','missing_bars':0},candles=rows)))
                    p.get_by_text('300 mum',exact=True).wait_for();p.wait_for_timeout(200)
                def command(mode=None):
                    p.get_by_label('Hızlı erişimi aç',exact=True).click()
                    if mode:p.get_by_role('button',name=mode,exact=True).click()
                    return p.get_by_role('combobox',name='Hızlı erişimde ara',exact=True)
                p.goto(base);feed();p.wait_for_timeout(150)
                assert p.locator('.market-row').count()==80;p.get_by_role('button',name='80 sözleşme daha göster').click();assert p.locator('.market-row').count()==103;record('all_catalog_accessible_beyond_first80')
                before=len(sockets);p.get_by_label('ETHUSDT favorisi',exact=True).click();p.get_by_role('button',name='Favoriler',exact=True).click();assert p.locator('.market-row').count()==1;assert p.get_by_label('Sözleşme seç').input_value()=='BTCUSDT';assert len(sockets)==before
                assert json.loads(p.evaluate("localStorage.getItem('agentrader.favorites')"))==['ETHUSDT'];record('favorites_filter_persists_without_changing_market')
                p.get_by_role('button',name='Tümü',exact=True).click();p.get_by_label('Coin ara').fill(' COIN099 / USDT ');assert p.locator('.market-row').count()==1;p.get_by_label('Coin ara').fill('');record('normalized_search_finds_late_catalog_symbol')
                p.get_by_label('Yan paneli kapat').click();p.get_by_role('region',name='Fiyat grafiği').focus();p.keyboard.press('Control+k');search=p.get_by_role('combobox',name='Hızlı erişimde ara');assert search.evaluate('(e)=>e===document.activeElement')
                search.fill('ETH / USDT');assert p.locator('dialog[open]').get_by_role('option').count()==1;search.press('Enter');feed('ETHUSDT');assert p.get_by_label('Sözleşme seç').input_value()=='ETHUSDT';record('keyboard_palette_selects_correct_market_from_closed_panel')
                search=command();search.fill('not-a-symbol');assert p.locator('dialog[open]').get_by_role('option').count()==0;search.press('Enter');assert p.get_by_role('dialog').is_visible();search.press('Escape');assert p.get_by_label('Hızlı erişimi aç').evaluate('(e)=>e===document.activeElement');record('empty_result_enter_is_safe_and_escape_restores_opener')
                search=command('Araçlar');search.fill('cetvel');search.press('Enter');assert p.get_by_label('Fiyat-zaman cetveli').get_attribute('aria-pressed')=='true'
                p.get_by_role('region',name='Fiyat grafiği').focus();p.keyboard.press('Escape');p.keyboard.press('t');assert p.get_by_label('Trend çizgisi',exact=True).get_attribute('aria-pressed')=='true';record('tool_palette_and_chart_scoped_tool_hotkeys')
                p.get_by_label('Piyasaları göster veya gizle').click();box=p.get_by_label('Coin ara');box.fill('');box.press('r');box.press(',');box.press('Control+k');assert not p.locator('dialog[open]').count();assert p.get_by_label('Trend çizgisi',exact=True).get_attribute('aria-pressed')=='true';box.press('Escape');assert p.get_by_label('Trend çizgisi',exact=True).get_attribute('aria-pressed')=='true';box.fill('');record('typing_and_escape_in_form_do_not_change_tools_or_open_commands')
                p.get_by_role('region',name='Fiyat grafiği').focus();p.keyboard.press('Escape');p.keyboard.press(',');search=p.get_by_role('combobox',name='Hızlı erişimde ara');search.fill('7m');assert p.locator('dialog[open]').get_by_role('option').count()==0;search.fill('1h');search.press('Enter');feed('ETHUSDT','1h');assert p.get_by_role('button',name='1 sa',exact=True).get_attribute('aria-pressed')=='true';record('interval_palette_lists_only_supported_intervals_and_selects1h')
                search=command();search.press('Control+k');assert p.locator('dialog[open]').count()==1;search.press('Escape');record('shortcut_cannot_nest_modal')
                for width,theme in [(1536,'dark'),(1280,'light'),(1024,'light')]:
                    p.set_viewport_size({'width':width,'height':776})
                    if p.locator('.terminal').get_attribute('data-theme')!=theme:p.get_by_label('Açık temaya geç' if theme=='light' else 'Koyu temaya geç').click()
                    search=command('Araçlar');p.wait_for_timeout(100);bounds=p.get_by_role('dialog').bounding_box();assert bounds['x']>=0 and bounds['x']+bounds['width']<=width;assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');p.screenshot(path=str(ROOT/f'reports/chart-g06-{width}-{theme}.png'));search.press('Escape')
                record('palette_fits_three_desktop_widths_and_two_themes')
                p.get_by_label('Grafiği tam ekran aç').click();search=command();assert p.get_by_role('dialog').is_visible();search.press('Escape');p.get_by_label('Tam ekrandan çık').click();record('palette_works_inside_fullscreen')
                sockets.clear();p.reload();feed('ETHUSDT','1h');p.get_by_role('button',name='Favoriler',exact=True).click();assert p.get_by_label('ETHUSDT favorisi').get_attribute('aria-pressed')=='true';p.get_by_role('button',name='Tümü',exact=True).click();assert p.get_by_label('ETHUSDT sözleşmesine dön').count()==1;record('favorites_recents_and_workspace_market_survive_reload')
                assert not result['page_errors'];assert not result['unexpected_requests'];result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-g06-validation-20261111.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
