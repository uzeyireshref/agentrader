"""B1 current interaction baseline; real mouse/wheel in isolated App/Chromium."""
import json
from pathlib import Path
import socket
import subprocess
import time
import traceback
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from check_chart_connection import OBSERVE

ROOT=Path(__file__).resolve().parents[1]
INSPECT=OBSERVE.replace("f.type?.name==='App'","(()=>{let h=f.memoizedState;while(h){if(h.memoizedState&&Array.isArray(h.memoizedState.candles))return true;h=h.next;}return false;})()").replace('view,candles,volume;', 'view,candles,volume,chart,series;').replace(
    'const ref=v?.current;', "const ref=v?.current;if(ref?.timeScale)chart=ref;if(ref?.seriesType?.()==='Candlestick')series=ref;").replace(
    'return view?{view,candles,volume}:null;', "return view?{range:chart.timeScale().getVisibleLogicalRange(),options:chart.options(),price:series.priceScale().options(),priceY:series.priceToCoordinate(135),pane:chart.paneSize(0),barCount:view.candles.length}:null;")


def main(extra_checks=None, report_name='chart-interaction-baseline-20261109.json', production=False):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=subprocess.Popen(['node','node_modules/vite/bin/vite.js',*(['preview'] if production else []),'--host','127.0.0.1','--port',str(port),'--strictPort'],cwd=ROOT/'frontend',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    result={'date':'2026-11-09','passed':False,'observations':[],'page_errors':[],'unexpected_requests':[],
            'scope':'Current App/headless Chromium mouse and wheel baseline; no physical trackpad/touch or raster acceptance',
            'account_requests':0,'user_workspace_writes':0}
    try:
        for _ in range(100):
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1',port))==0:break
            time.sleep(.1)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True);result['browser']=browser.version
            page=browser.new_page(viewport={'width':1400,'height':1000});sockets=[]
            page.on('pageerror',lambda e:result['page_errors'].append(str(e)))
            page.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
            def route(r):
                path=urlparse(r.request.url).path
                if not r.request.url.startswith(f'http://127.0.0.1:{port}/'):
                    result['unexpected_requests'].append(r.request.url);return r.abort()
                responses={'/api/markets':{'markets':[{'symbol':'BTCUSDT','base_asset':'BTC','quote_asset':'USDT','tick_size':'0.1','contract_type':'PERPETUAL'}]},'/api/workspaces/main':{'revision':0,'preferences':{'symbol':'BTCUSDT','interval':'15m'}},'/api/workspaces/main/drawings':{'drawings':[]},'/api/candles':{'candles':[],'has_more':False}}
                if path in responses:return r.fulfill(json=responses[path])
                if path.startswith('/api/'):
                    result['unexpected_requests'].append(path);return r.abort()
                return r.continue_()
            page.route('**/*',route);page.goto(f'http://127.0.0.1:{port}/')
            page.wait_for_function("document.querySelector('.connection')!==null")
            page.wait_for_timeout(250);assert sockets
            rows=[{'time':1800000000+i*900,'open':100+i*.1,'high':110+i*.1,'low':90+i*.1,'close':105+i*.1,'volume':10+i,'quote_volume':1000,'close_time':(1800000000+(i+1)*900)*1000-1,'closed':i<299} for i in range(300)]
            sockets[-1].send(json.dumps({'type':'snapshot','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'candles':rows}))
            page.wait_for_timeout(200)
            def snap(name):
                data=page.evaluate(INSPECT);assert data and data['range']
                result['observations'].append({'name':name,'range':data['range'],'auto_scale':data['price']['autoScale'],'price_135_y':data['priceY'],'bars':data['barCount']})
                return data
            initial=snap('initial');result['engine_interaction_options']={k:initial['options'][k] for k in ['handleScroll','handleScale','kineticScroll','timeScale']}
            box=page.locator('.chart-host').bounding_box();assert box
            x=box['x']+initial['pane']['width']*.55;y=box['y']+initial['pane']['height']*.5
            page.mouse.move(x,y);page.mouse.wheel(0,-360);page.wait_for_timeout(200)
            zoom=snap('vertical_wheel_zoom');assert zoom['range']['to']-zoom['range']['from']<initial['range']['to']-initial['range']['from']
            page.get_by_label('Güncel mumlara dön',exact=True).click();page.wait_for_timeout(100)
            snap('go_live_after_zoom')
            page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+180,y,steps=12);page.mouse.up();page.wait_for_timeout(200)
            pan=snap('mouse_drag_into_history');assert pan['range']['from']<initial['range']['from']
            newer={**rows[-1],'time':rows[-1]['time']+900,'close_time':rows[-1]['close_time']+900000,'volume':1}
            sockets[-1].send(json.dumps({'type':'update','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':2,'status':'LIVE','received_at':int(time.time()*1000),'tail':[{**rows[-1],'closed':True},newer]}))
            page.wait_for_timeout(100);snap('new_bar_while_viewing_history')
            page.mouse.move(x,y);page.mouse.wheel(200,0);page.wait_for_timeout(200);snap('horizontal_wheel')
            page.get_by_label('Güncel mumlara dön',exact=True).click();page.wait_for_timeout(100)
            axis_x=box['x']+box['width']-30
            page.mouse.move(axis_x,y);page.mouse.down();page.mouse.move(axis_x,y+80,steps=12);page.mouse.up();page.wait_for_timeout(150)
            manual=snap('price_axis_drag');assert manual['price']['autoScale'] is False
            page.get_by_label('Güncel mumlara dön',exact=True).click();page.wait_for_timeout(100);snap('go_live_after_manual_price_scale')
            page.mouse.dblclick(axis_x,y);page.wait_for_timeout(150)
            reset=snap('price_axis_double_click');assert reset['price']['autoScale'] is True
            page.mouse.move(x,y);page.mouse.wheel(0,-360);page.wait_for_timeout(150);snap('zoom_before_time_axis_reset')
            page.mouse.dblclick(x,box['y']+box['height']-12);page.wait_for_timeout(150);snap('time_axis_double_click')
            page.get_by_label('Trend çizgisi',exact=True).click();page.wait_for_timeout(100)
            page.mouse.move(x,y);page.mouse.wheel(0,-240);page.wait_for_timeout(150);snap('wheel_during_drawing_creation')
            page.keyboard.press('Escape');assert page.locator('.tool-hint').count()==0
            result['observations'].append({'name':'escape_drawing_creation','draft_closed':True,'writes':0})
            if extra_checks is not None:extra_checks(page,sockets,rows,result)
            result['passed']=not result['page_errors'] and not result['unexpected_requests'];browser.close()
    except Exception as error:result['error']=str(error);result['traceback']=traceback.format_exc()
    finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports'/report_name).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2));return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
