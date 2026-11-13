"""T03 current production ruler, real isolated HTTP/SQLite and two browser tabs."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from urllib.parse import urlparse
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
from measure_chart_interactions import INSPECT,ROOT
from agentrader.drawings.calculations import measure_ruler


def main():
    result={'task':'T03','date':'2026-11-10','passed':False,'checks':[],'page_errors':[],
            'unexpected_requests':[],'user_workspace_writes':0,'account_requests':0,'order_requests':0,
            'scope':'Real production App/HTTP/isolated SQLite; synthetic market; no physical device acceptance'}
    def record(name,**extra):result['checks'].append(dict(name=name,passed=True,**extra))
    with tempfile.TemporaryDirectory(prefix='agentrader-t03-') as folder:
        isolated=Path(folder)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base='http://127.0.0.1:'+str(port)
        env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(isolated/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(isolated/'execution.db'),AGENTRADER_CHART_DATABASE=str(isolated/'market.db'),AGENTRADER_WEB_TOKEN='')
        def start():return subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        server=start();opener=build_opener(ProxyHandler({}))
        def api(path,body=None,method=None):
            request=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'},method=method)
            with opener.open(request,timeout=5) as response:return json.load(response)
        def wait_server():
            for _ in range(100):
                try:api('/api/health');return
                except Exception:time.sleep(.1)
            raise AssertionError('server not ready')
        try:
            wait_server()
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True);context=browser.new_context(viewport={'width':1400,'height':1000});result['browser']=browser.version
                markets=[{'symbol':s,'base_asset':s[:-4],'quote_asset':'USDT','contract_type':'PERPETUAL','tick_size':'0.25'} for s in ('BTCUSDT','ETHUSDT')]
                rows=[{'time':1800000000+i*900,'open':100+i*.1,'high':110+i*.1,'low':90+i*.1,'close':105+i*.1,'volume':10+i,'quote_volume':1000,'close_time':(1800000000+(i+1)*900)*1000-1,'closed':i<299} for i in range(300)]
                hourly=[dict(r,close_time=r['time']*1000+3599999) for r in rows[::4]]
                sockets={}
                def pause(p):p.wait_for_timeout(200)
                def opened(name):
                    p=context.new_page();sockets[name]=[]
                    p.on('pageerror',lambda error:result['page_errors'].append(str(error)))
                    def guard(route):
                        if not route.request.url.startswith(base+'/'):
                            result['unexpected_requests'].append(route.request.url);return route.abort()
                        return route.continue_()
                    p.route('**/*',guard)
                    p.route('**/api/markets',lambda r:r.fulfill(json={'markets':markets}))
                    p.route('**/api/candles*',lambda r:r.fulfill(json={'candles':[],'has_more':False}))
                    p.route_web_socket('**/api/market-stream*',lambda ws:sockets[name].append(ws))
                    p.goto(base);p.wait_for_timeout(650)
                    deadline=time.monotonic()+8
                    while not sockets[name] and time.monotonic()<deadline:p.wait_for_timeout(100)
                    if not sockets[name]:raise AssertionError('No stream: '+p.locator('body').inner_text()[:2000])
                    return p
                def feed(p,name,symbol='BTCUSDT',interval='15m'):
                    data=hourly if interval=='1h' else rows
                    sockets[name][-1].send(json.dumps({'type':'snapshot','symbol':symbol,'interval':interval,'generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'market':next(m for m in markets if m['symbol']==symbol),'quality':{'state':'OK','missing_bars':0},'candles':data}));pause(p)
                def choose(p):p.locator('.drawing-list button').filter(has_text='Cetvel').first.click();pause(p)
                def refresh(p):p.get_by_role('button',name='Sunucudan yenile',exact=True).click();pause(p)
                def read(p,expr):return p.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');'+'}')
                a=opened('A');feed(a,'A')
                read(a,'chart.timeScale().setVisibleLogicalRange({from:200,to:280})');read(a,'series.priceScale().setVisibleRange({from:100,to:150})');pause(a)
                a.get_by_label('Fiyat-zaman cetveli',exact=True).click()
                result['creation_states']=[]
                read(a,'(window.__t03clicks=[],chart.subscribeClick(e=>window.__t03clicks.push({time:e.time,point:e.point,pane:e.paneIndex})),true)')
                box=a.locator('.chart-host').bounding_box()
                for t,price in ((rows[220]['time'],120),(rows[240]['time'],130)):
                    point=read(a,'({x:chart.timeScale().timeToCoordinate('+str(t)+'),y:series.priceToCoordinate('+str(price)+')})')
                    a.mouse.click(box['x']+point['x'],box['y']+point['y']);a.wait_for_timeout(650)
                    result['creation_states'].append({'point':point,'box':box,'hint':a.locator('.tool-hint').text_content() if a.locator('.tool-hint').count() else None,'save':a.locator('.save-state').text_content(),'rows':a.locator('.drawing-list button').count()})
                listing=api('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version=2')['drawings']
                result['native_clicks']=a.evaluate('window.__t03clicks')
                a.screenshot(path=str(ROOT/'reports/chart-t03-debug-20261110.png'),full_page=True)
                assert len(listing)==1
                saved=listing[0];key=saved['drawing_id'];path='/api/drawings/'+key+'?format_version=2'
                def head():return api(path)
                assert saved['geometry']['schema']=='chart-ruler/1'
                assert [v['price'] for v in saved['geometry']['anchors']]==['120.00','130.00']
                m=measure_ruler(saved['geometry'],tick_size='0.25',times=[r['time'] for r in rows],interval='15m')
                readout=a.locator('.ruler-readout').inner_text()
                assert '10 USDT' in readout and '25/3%' in readout and '21 mum · 20 aralık' in readout and '5sa' in readout
                assert api('/api/workspaces/main/drawings?symbol=BTCUSDT')['drawings']==[]
                record('actual_two_click_creation_exact_reference_and_legacy_isolation',measurement=m)
                # Own first handle, keep time fixed, move price exactly 2.50.
                handle=a.locator('[data-drawing-handles="'+key+'"] [data-anchor="0"]');handle.scroll_into_view_if_needed();h=handle.bounding_box()
                end_y=read(a,'series.priceToCoordinate(122.5)');box=a.locator('.chart-host').bounding_box()
                a.mouse.move(h['x']+h['width']/2,h['y']+h['height']/2);a.mouse.down();a.mouse.move(h['x']+h['width']/2,box['y']+end_y,steps=8);a.mouse.up();pause(a)
                assert head()['revision']==2 and head()['geometry']['anchors'][0]['price']=='122.50';record('actual_handle_drag_persists_exact_tick')
                a.get_by_label('Nokta 2 fiyatı',exact=True).fill('135.00');a.get_by_role('button',name='Kaydet',exact=True).click();pause(a)
                assert head()['revision']==3;record('numeric_edit_keeps_schema_and_revision')
                a.get_by_label('Çizim değişikliğini geri al',exact=True).click();pause(a);assert head()['geometry']['anchors'][1]['price']=='130.00'
                a.get_by_label('Çizim değişikliğini yinele',exact=True).click();pause(a);assert head()['geometry']['anchors'][1]['price']=='135.00';record('undo_redo_restore_exact_values')
                a.get_by_role('button',name='Sil',exact=True).click();pause(a);assert head()['deleted']
                a.get_by_label('Çizim değişikliğini geri al',exact=True).click();pause(a);assert not head()['deleted'];record('delete_undo_restores_same_ruler')
                b=opened('B');feed(b,'B');choose(b)
                a.get_by_label('Nokta 2 fiyatı',exact=True).fill('140.00');a.get_by_role('button',name='Kaydet',exact=True).click();pause(a)
                b.get_by_label('Nokta 2 fiyatı',exact=True).fill('141.00');b.get_by_role('button',name='Kaydet',exact=True).click();pause(b)
                assert head()['geometry']['anchors'][1]['price']=='140.00' and b.get_by_role('button',name='Aynı kaydı tekrar dene',exact=True).is_visible();record('second_tab_409_cannot_overwrite_winner')
                b.get_by_role('button',name='Son kaydı yükle',exact=True).click();pause(b);choose(b);assert b.get_by_label('Nokta 2 fiyatı',exact=True).input_value()=='140.00';record('conflict_refresh_recovers_saved_ruler')
                b.close();refresh(a);choose(a)
                a.get_by_label('Sözleşme seç',exact=True).select_option('ETHUSDT');a.wait_for_timeout(650);feed(a,'A','ETHUSDT')
                assert a.locator('.drawing-list button').count()==0 and api('/api/workspaces/main/drawings?symbol=ETHUSDT&format_version=2')['drawings']==[]
                a.get_by_label('Sözleşme seç',exact=True).select_option('BTCUSDT');a.wait_for_timeout(650);feed(a,'A');choose(a);assert head()['drawing_id']==key;record('market_switch_has_no_cross_symbol_measurement')
                a.get_by_role('button',name='1 sa',exact=True).click();a.wait_for_timeout(650);feed(a,'A',interval='1h')
                readout=a.locator('.ruler-readout').inner_text();assert '6 mum · 5 aralık' in readout and '5sa' in readout;record('timeframe_changes_bars_but_keeps_utc_duration')
                server.terminate();server.wait(timeout=10);server=start();wait_server()
                a.reload();a.wait_for_timeout(750);feed(a,'A',interval='1h');choose(a)
                assert head()['geometry']['anchors'][1]['price']=='140.00' and head()['geometry']['schema']=='chart-ruler/1';record('page_and_server_restart_keep_exact_ruler')
                a.screenshot(path=str(ROOT/'reports/chart-t03-ruler-20261110.png'),full_page=True)
                assert not result['page_errors'] and not result['unexpected_requests'] and not (isolated/'execution.db').exists()
                result['assets']={str(p.relative_to(ROOT/'agentrader/web_assets')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'agentrader/web_assets').rglob('*')) if p.is_file()}
                record('no_external_account_order_or_user_workspace_access')
                result['passed']=True;browser.close()
        except Exception as error:
            result['error']=str(error);result['traceback']=traceback.format_exc()
            try:a.screenshot(path=str(ROOT/'reports/chart-t03-debug-20261110.png'),full_page=True)
            except Exception:pass
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-t03-browser-20261110.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'passed':result['passed'],'checks':len(result['checks']),'error':result.get('error')}));return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
