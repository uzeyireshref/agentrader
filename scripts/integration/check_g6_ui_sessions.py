"""G6 production frontend -> real isolated HTTP UI-session bridge acceptance."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import httpx
from playwright.sync_api import sync_playwright
from scripts.integration.chart_tool_matrix_cases import drawing_cases,candles
from scripts.chart.measure_chart_interactions import INSPECT,ROOT
from agentrader.chart.chart_evidence import snapshot
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT

OUT=ROOT/'reports/chart-interface-g6-20261115'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    result=dict(passed=False,checks=[],page_errors=[],unexpected_requests=[],publish_count=0,
                scope='Synthetic public market fixture; production App and real isolated HTTP/SQLite; no trading')
    def check(name,condition):
        result['checks'].append(dict(name=name,passed=bool(condition)));assert condition,name
    with tempfile.TemporaryDirectory(prefix='g6-ui-') as tmp:
        folder=Path(tmp)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(folder/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(folder/'execution.db'),AGENTRADER_CHART_DATABASE=str(folder/'market.db'),AGENTRADER_WEB_TOKEN='')
        server=subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            with httpx.Client(base_url=base,timeout=10) as client:
                for _ in range(100):
                    try:
                        response=client.get('/api/workspaces/main/ui-sessions?policy_only=true')
                        if response.status_code==200:break
                    except httpx.HTTPError:pass
                    time.sleep(.1)
                policy=response.json()['policy'];identity=dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE')
                market=dict(symbol='BTCUSDT',base_asset='BTC',quote_asset='USDT',tick_size='.25',contract_type='PERPETUAL')
                geometry=drawing_cases()[0]['geometry']
                created=client.post('/api/workspaces/main/drawings?format_version=9',json=dict(request_id='g6-sentinel',geometry=geometry));assert created.status_code==201,created.text
                did=created.json()['drawing_id'];rows=candles()
                proof=snapshot(rows,market,dict(state='OK',missing_bars=0),symbol='BTCUSDT',interval='15m',epoch='d'*32,generation=1,revision=1).view()
                packet=dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=1,stream_epoch='d'*32,data_proof=proof,status='LIVE',received_at=int(time.time()*1000),market=market,quality=dict(state='OK',missing_bars=0),candles=rows,**identity)
                with sync_playwright() as pw:
                    browser=pw.chromium.launch(headless=True);result['browser']=browser.version
                    contexts=[]
                    def new_page():
                        context=browser.new_context(viewport=dict(width=1536,height=950));contexts.append(context)
                        page=context.new_page();page.set_default_timeout(10000);sockets=[]
                        page.on('pageerror',lambda error:result['page_errors'].append(str(error)))
                        def boundary(route):
                            url=route.request.url
                            if not url.startswith(base+'/') or any(p in url for p in ('/api/account','/api/orders','/api/commands','/api/execution')):
                                result['unexpected_requests'].append(url);route.abort()
                            else:
                                if '/ui-sessions/' in url and route.request.method=='PUT':result['publish_count']+=1
                                route.continue_()
                        page.route('**/*',boundary)
                        page.route('**/api/markets',lambda r:r.fulfill(json=dict(markets=[market,{**market,'symbol':'ETHUSDT','base_asset':'ETH'}],ui_session_bridge=policy,**identity)))
                        page.route('**/api/candles*',lambda r:r.fulfill(json=dict(candles=[],has_more=False,**identity)))
                        page.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
                        page.goto(base)
                        # The other tab persists ETH/1h. Restore the fixture market
                        # through real UI before publishing the BTC/15m packet.
                        page.get_by_label('Sözleşme seç',exact=True).select_option('BTCUSDT')
                        page.get_by_role('button',name='15 dk',exact=True).click()
                        page.wait_for_timeout(500)
                        until=time.time()+5
                        while not sockets and time.time()<until:page.wait_for_timeout(30)
                        assert sockets;sockets[-1].send(json.dumps(packet))
                        page.get_by_text(str(len(rows))+' mum',exact=True).wait_for()
                        page.wait_for_function("document.documentElement.dataset.uiSessionStatus==='READY'")
                        return page,context
                    def read(page,expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');}')
                    def sid(page):return page.evaluate('document.documentElement.dataset.uiSessionId')
                    def view(session):return client.get('/api/workspaces/main/ui-sessions/'+session).json()
                    def eventually(page,fn):
                        until=time.time()+7
                        while time.time()<until:
                            value=fn()
                            if value:return value
                            page.wait_for_timeout(100)
                        raise AssertionError('UI publication timed out: '+json.dumps(view(sid(page))))
                    a,ca=new_page();aid=sid(a);b,cb=new_page();bid=sid(b)
                    check('distinct_tabs',aid!=bid and view(aid)['state']==view(bid)['state']=='READY')
                    a.get_by_label('Açık temaya geç',exact=True).click()
                    eventually(a,lambda:view(aid).get('snapshot',{}).get('theme')=='light')
                    check('tab_state_not_merged',view(bid)['snapshot']['theme']=='dark')
                    a.get_by_label('BTCUSDT favorisi',exact=True).click();a.get_by_label('Mıknatıs',exact=True).click()
                    a.get_by_label('Fiyat bölgesi',exact=True).click()
                    eventually(a,lambda:view(aid).get('snapshot',{}).get('selection',{}).get('tool')=='zone')
                    check('tool_magnet_favorites',view(aid)['snapshot']['magnet'] and 'BTCUSDT' in view(aid)['snapshot']['favorites'])
                    a.get_by_label('İmleç',exact=True).click()
                    b.get_by_role('button',name='1 sa',exact=True).click()
                    eventually(b,lambda:view(bid).get('snapshot',{}).get('market',{}).get('interval')=='1h')
                    b.get_by_label('Sözleşme seç',exact=True).select_option('ETHUSDT')
                    eventually(b,lambda:view(bid).get('snapshot',{}).get('market',{}).get('symbol')=='ETHUSDT')
                    check('market_switch_resets_hover',view(bid)['snapshot']['crosshair']['hover_candle'] is None and view(aid)['snapshot']['market']['symbol']=='BTCUSDT')
                    # Actual native chart viewport and cursor, read through HTTP.
                    read(a,'(chart.timeScale().setVisibleLogicalRange({from:260,to:299}),true)');a.wait_for_timeout(300)
                    point=read(a,'({x:chart.timeScale().logicalToCoordinate(280),y:series.priceToCoordinate(view.candles[280].close)})')
                    box=a.locator('.chart-host').bounding_box();assert box
                    a.mouse.move(box['x']+point['x'],box['y']+point['y'])
                    eventually(a,lambda:view(aid).get('snapshot',{}).get('crosshair',{}).get('hover_candle'))
                    report=view(aid);hover=report['snapshot']['crosshair']['hover_candle']
                    row=next(r for r in rows if r['time']==hover['time'])
                    check('real_hover_candle_decimals',all(hover[k]==str(row.get('exact',{}).get(k,row[k])) for k in ('open','high','low','close','volume','quote_volume')))
                    check('viewport_logical_time_price',all(report['snapshot']['viewport'][k] is not None for k in ('logical_range','time_range','price_range')))
                    count=result['publish_count'];start=time.monotonic()
                    for n in range(150):a.mouse.move(box['x']+point['x']+(n%20),box['y']+point['y']+(n%10))
                    a.wait_for_timeout(600);elapsed=time.monotonic()-start
                    check('pointer_requests_coalesced',result['publish_count']-count<=int(elapsed*2)+4)
                    result['pointer_burst']=dict(moves=150,seconds=elapsed,publishes=result['publish_count']-count)
                    # Select actual persisted SVG and delete it through API: stale selection is filtered.
                    node=a.locator('[data-drawing="'+did+'"]');node.press('Enter')
                    eventually(a,lambda:did in view(aid).get('snapshot',{}).get('selection',{}).get('drawing_ids',[]))
                    a.get_by_label('Çizimleri göster veya gizle',exact=True).click()
                    a.get_by_label('Çizim adı',exact=True).fill('G6 revision proof')
                    a.locator('.drawing-editor').get_by_role('button',name='Kaydet',exact=True).click()
                    eventually(a,lambda:view(aid).get('snapshot',{}).get('history',{}).get('can_undo'))
                    history=view(aid)['snapshot']['history']
                    check('undo_revision_summary_without_stack',history['undo_targets'][0]['drawing_id']==did and history['undo_targets'][0]['revision_matches'] and set(history)=={'can_undo','can_redo','undo_targets','redo_targets'})
                    a.get_by_label('Geri al',exact=True).click()
                    eventually(a,lambda:view(aid).get('snapshot',{}).get('history',{}).get('can_redo'))
                    check('redo_availability_reported',view(aid)['snapshot']['history']['redo_targets'][0]['drawing_id']==did)
                    revision=client.get('/api/drawings/'+did+'?format_version=9').json()['revision']
                    deleted=client.request('DELETE','/api/drawings/'+did+'?format_version=9',json=dict(request_id='g6-delete',expected_revision=revision));assert deleted.status_code==200
                    check('deleted_selection_reconciled',did not in view(aid)['snapshot']['selection']['drawing_ids'])
                    context=client.get('/api/workspaces/main/chart-context',params=dict(symbol='BTCUSDT',interval='15m',ui_session_id=aid)).json()
                    check('saved_profile_separate_from_screen',context['persistent_view']['body']['view']['theme']=='dark' and context['ui']['snapshot']['theme']=='light')
                    check('ui_client_reported_no_market_authority',context['ui']['authority']=='CLIENT_REPORTED_UI_NOT_MARKET_EVIDENCE' and not context['order_authority'] and not context['ui']['order_authority'])
                    check('bot_must_select_session',client.get('/api/workspaces/main/chart-context').json()['ui']['reason']=='UI_SESSION_NOT_SELECTED')
                    # Browser lifecycle visibility event reaches real API; no session payload is readable.
                    a.evaluate("Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'hidden'});document.dispatchEvent(new Event('visibilitychange'))")
                    eventually(a,lambda:view(aid)['state']=='UI_UNAVAILABLE')
                    check('hidden_session_not_readable','snapshot' not in view(aid) and all(s['ui_session_id']!=aid for s in client.get('/api/workspaces/main/ui-sessions').json()['sessions']))
                    a.evaluate("Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'visible'});document.dispatchEvent(new Event('visibilitychange'))")
                    eventually(a,lambda:view(aid)['state']=='READY')
                    # Connection loss cannot renew the server lease; wait real TTL with browser timers running.
                    ca.set_offline(True);a.wait_for_timeout(31000)
                    check('offline_real_ttl_unavailable',view(aid)['state']=='UI_UNAVAILABLE' and view(aid)['stale'] and 'snapshot' not in view(aid))
                    ca.set_offline(False)
                    eventually(a,lambda:sid(a)!=aid and view(sid(a))['state']=='READY')
                    renewed=sid(a);check('reconnect_new_lease_identity',renewed!=aid)
                    a.goto('about:blank');b.wait_for_timeout(1000)
                    check('closed_tab_unavailable',view(renewed)['state']=='UI_UNAVAILABLE' and 'snapshot' not in view(renewed))
                    c,cc=new_page();check('reopen_new_identity',sid(c) not in (aid,bid,renewed))
                    # Navigation BFCache lifecycle returns with a fresh publisher.
                    old=sid(c);c.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide'));window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
                    eventually(c,lambda:sid(c)!=old and view(sid(c))['state']=='READY')
                    check('bfcache_new_identity',sid(c)!=old)
                    result['sample_context']=context
                    check('no_browser_errors',not result['page_errors'])
                    check('no_financial_or_external_requests',not result['unexpected_requests'] and not (folder/'execution.db').exists())
                    c.screenshot(path=str(OUT/'ui-session-browser.png'));browser.close();result['passed']=True
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (OUT/'browser.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(passed=result['passed'],checks=len(result['checks']),error=result.get('error')),ensure_ascii=True))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
