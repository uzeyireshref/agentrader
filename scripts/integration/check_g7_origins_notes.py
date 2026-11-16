"""G7 verified actors and linked notes; production browser, isolated synthetic data."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import secrets
import json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from agentrader.api.session import COOKIE
import httpx
from playwright.sync_api import sync_playwright
from scripts.integration.chart_tool_matrix_cases import drawing_cases,candles
from scripts.chart.measure_chart_interactions import INSPECT,ROOT
from agentrader.chart.chart_evidence import snapshot
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT

OUT=ROOT/'reports/chart-interface-g7-20261115'


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
        human_token=secrets.token_hex(24);bot_token=secrets.token_hex(24)
        env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(folder/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(folder/'execution.db'),AGENTRADER_CHART_DATABASE=str(folder/'market.db'),AGENTRADER_WEB_TOKEN=human_token,AGENTRADER_CHART_BOT_TOKEN=bot_token,AGENTRADER_CHART_BOT_ID='alpha',AGENTRADER_CHART_STRATEGY_ID='synth')
        server=subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            with httpx.Client(base_url=base,timeout=10,headers={'Authorization':'Bearer '+human_token}) as client:
                for _ in range(100):
                    try:
                        response=client.get('/api/workspaces/main/ui-sessions?policy_only=true')
                        if response.status_code==200:break
                    except httpx.HTTPError:pass
                    time.sleep(.1)
                assert client.post('/api/session').status_code==200
                bot=httpx.Client(base_url=base,timeout=10,headers={'Authorization':'Bearer '+bot_token})
                policy=response.json()['policy'];identity=dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE')
                market=dict(symbol='BTCUSDT',base_asset='BTC',quote_asset='USDT',tick_size='.25',contract_type='PERPETUAL')
                geometry=drawing_cases()[0]['geometry']
                created=client.post('/api/workspaces/main/drawings?format_version=9',json=dict(request_id='g7-sentinel',geometry=geometry));assert created.status_code==201,created.text
                did=created.json()['drawing_id'];rows=candles()
                proof=snapshot(rows,market,dict(state='OK',missing_bars=0),symbol='BTCUSDT',interval='15m',epoch='d'*32,generation=1,revision=1).view()
                packet=dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=1,stream_epoch='d'*32,data_proof=proof,status='LIVE',received_at=int(time.time()*1000),market=market,quality=dict(state='OK',missing_bars=0),candles=rows,**identity)
                with sync_playwright() as pw:
                    browser=pw.chromium.launch(headless=True);result['browser']=browser.version
                    contexts=[]
                    def new_page():
                        context=browser.new_context(viewport=dict(width=1536,height=950));contexts.append(context)
                        context.add_cookies([dict(name=COOKIE,value=client.cookies.get(COOKIE),url=base+'/api',httpOnly=True,sameSite='Strict')])
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

                    a,ca=new_page();a.locator('[data-drawing="'+did+'"]').press('Enter')
                    a.get_by_label('Çizimleri göster veya gizle',exact=True).click();panel=a.locator('#drawing-panel')
                    panel.get_by_label('Çizim adı',exact=True).fill('Manuel düzenleme')
                    panel.locator('form').get_by_role('button',name='Kaydet',exact=True).click()
                    eventually(a,lambda:not a.get_by_label('Geri al',exact=True).is_disabled())
                    before=client.get('/api/drawings/'+did+'?format_version=9').json()
                    text='Uzun not 🧭\nİstanbul 日本語\n<script>literal</script>\n'+('Satır açıklaması. '*20)
                    panel.get_by_label('Çizimin uzun notu',exact=True).fill(text);panel.get_by_role('button',name='Notu kaydet',exact=True).click()
                    eventually(a,lambda:client.get('/api/drawings/'+did+'/notes').json()['revision']==1)
                    check('unicode_multiline_roundtrip',client.get('/api/drawings/'+did+'/notes').json()['text']==text)
                    check('selection_history_preserved',panel.get_by_label('Çizimin uzun notu').is_visible() and not a.get_by_label('Geri al',exact=True).is_disabled())
                    check('html_literal',panel.locator('script').count()==0 and panel.get_by_label('Çizimin uzun notu').input_value()==text)
                    after=client.get('/api/drawings/'+did+'?format_version=9').json()
                    check('geometry_revision_origin_unchanged',all(after[k]==before[k] for k in ('geometry','revision','origin')))
                    raw=bot.get('/api/drawings/'+did+'?format_version=9').json()
                    check('bot_reads_manual_notes',raw['linked_note']['text']==text and raw['origin']['kind']=='manual')
                    check('bot_manual_edit_denied',bot.patch('/api/drawings/'+did+'?format_version=9',json=dict(request_id='denied-edit',expected_revision=after['revision'],geometry={**after['geometry'],'label':'no'})).status_code==403)
                    check('bot_manual_delete_denied',bot.request('DELETE','/api/drawings/'+did+'?format_version=9',json=dict(request_id='denied-del',expected_revision=after['revision'])).status_code==403)
                    check('bot_manual_note_denied',bot.put('/api/drawings/'+did+'/notes',json=dict(request_id='denied-note',expected_revision=1,expected_drawing_revision=after['revision'],text='no')).status_code==403)
                    check('bot_import_denied',bot.post('/api/workspaces/main/template-restore',json={}).status_code==403)
                    a.get_by_label('Geri al',exact=True).click()
                    eventually(a,lambda:client.get('/api/drawings/'+did+'?format_version=9').json()['revision']==3)
                    check('undo_retains_note',client.get('/api/drawings/'+did+'/notes').json()['text']==text)
                    a.close();a,ca=new_page();a.locator('[data-drawing="'+did+'"]').press('Enter');a.get_by_label('Çizimleri göster veya gizle',exact=True).click()
                    check('reload_persists_note',a.locator('#drawing-panel').get_by_label('Çizimin uzun notu').input_value()==text)
                    current=client.get('/api/drawings/'+did+'?format_version=9').json()
                    client.post('/api/workspaces/main/drawing-operations?format_version=9',json=dict(request_id='lock',operations=[dict(drawing_id=did,expected_revision=current['revision'],geometry=current['geometry'],management={**current['management'],'locked':True},deleted=False)]))
                    a.close();a,ca=new_page();a.locator('[data-drawing="'+did+'"]').press('Enter');a.get_by_label('Çizimleri göster veya gizle',exact=True).click()
                    check('locked_note_editor',a.locator('#drawing-panel').get_by_label('Çizimin uzun notu').is_disabled())
                    response=bot.post('/api/workspaces/main/drawings?format_version=9',json=dict(request_id='verified-bot',geometry={**geometry,'label':'Alpha proof'}));assert response.status_code==201,response.text
                    bd=response.json();bid=bd['drawing_id']
                    check('verified_bot_origin',bd['origin']['kind']=='bot' and bd['origin']['bot_id']=='alpha' and bd['origin']['strategy_id']=='synth')
                    check('bot_owned_note_allowed',bot.put('/api/drawings/'+bid+'/notes',json=dict(request_id='owned-note',expected_revision=0,expected_drawing_revision=1,text='Bot notu 🧭')).status_code==200)
                    check('origin_spoof_rejected',bot.post('/api/workspaces/main/drawings?format_version=9',json=dict(request_id='spoof',geometry=geometry,origin='manual')).status_code==422)
                    latest=client.get('/api/drawings/'+did+'?format_version=9').json()
                    check('manual_origin_remains',latest['origin']==before['origin'] and latest['linked_note']['text']==text)
                    context=bot.get('/api/workspaces/main/chart-context?symbol=BTCUSDT&interval=15m').json()
                    check('snapshot_origin_notes',all('origin'in d and 'linked_note'in d for d in context['objects']) and any(d['drawing_id']==bid and d['linked_note']['text']=='Bot notu 🧭' for d in context['objects']))
                    result['sample_context']=context;result['manual_history']=bot.get('/api/drawings/'+did+'/history').json()
                    check('no_browser_errors',not result['page_errors'])
                    check('no_financial_external_requests',not result['unexpected_requests'] and not (folder/'execution.db').exists())
                    a.locator('#drawing-panel').get_by_label('Çizimin uzun notu').scroll_into_view_if_needed();a.screenshot(path=str(OUT/'linked-note-browser.png'));bot.close();browser.close();result['passed']=True
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (OUT/'browser.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(passed=result['passed'],checks=len(result['checks']),error=result.get('error')),ensure_ascii=True))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
