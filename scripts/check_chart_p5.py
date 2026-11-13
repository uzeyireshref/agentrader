"""P5 production App + real eligibility API; isolated DB and synthetic server feed."""
import copy,json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agentrader.chart_evidence import snapshot
from agentrader.chart_clock import POLICY
from agentrader.chart_precision import exact_tick


def fixture():
    step=900;end=1800000000;rows=[]
    for i in range(100):
        t=end-(99-i)*step
        exact=dict(schema='chart-exact-decimal/1',state='VERIFIED',provenance='UPSTREAM_DECIMAL_TEXT',open='100',high='110',low='90',close='105',volume='10',quote_volume='1050')
        rows.append(dict(time=t,close_time=(t+step)*1000-1,closed=i<99,**{k:float(exact[k]) for k in ('open','high','low','close','volume','quote_volume')},exact=exact))
    market=dict(symbol='BTCUSDT',base_asset='BTC',quote_asset='USDT',contract_type='PERPETUAL',tick_size='0.1',exact=exact_tick('0.1'))
    return rows,market,dict(state='OK',missing_bars=0)


def serve(folder,port):
    import uvicorn
    from agentrader.api.app import create_app
    from agentrader.application.settings import WebSettings
    class Hub:
        def binding_context(self,symbol,interval):
            mode=Path(folder,'mode').read_text()
            if mode=='missing':return None
            rows,market,quality=fixture()
            proof=snapshot(rows,market,quality,symbol=symbol,interval=interval,epoch='a'*32,generation=1,revision=1).view()
            c=dict(transport_state='LIVE',identity=dict(source='binance_usdm_live_trade_price',environment='live_public',product='USD-M',price_type='LAST_PRICE',symbol=symbol,interval=interval),rows=rows,market=market,quality=quality,stream_epoch='a'*32,generation=1,data_revision=1,data_proof=proof,timing=dict(schema='chart-time-proof/1',policy=dict(POLICY),state='FRESH',reason=None,data_age_ms=1,upstream_age_upper_ms=2,uncertainty_ms=1,upstream_event_time=rows[-1]['time']*1000+3000))
            if mode=='stale':c['timing']['upstream_age_upper_ms']=10001
            if mode=='clock':c['timing']['state']='BLOCKED';c['timing']['reason']='CLOCK_UNTRUSTED'
            if mode=='tamper':c['rows'][0]['exact']['close']='999'
            return c
        def close(self):pass
    settings=WebSettings(application_database=Path(folder,'app.db'),execution_database=Path(folder,'execution.db'),market_database=Path(folder,'market.db'),owner='p5-fixture')
    uvicorn.run(create_app(settings,hub=Hub()),host='127.0.0.1',port=int(port),log_level='error')


def main():
    from playwright.sync_api import sync_playwright
    result=dict(task='P5',passed=False,checks=[],page_errors=[],unexpected_requests=[],scope='Production App/API; isolated SQLite and synthetic server feed; no account/order access')
    def record(name):result['checks'].append(dict(name=name,passed=True))
    with tempfile.TemporaryDirectory(prefix='agentrader-p5-') as folder:
        mode=Path(folder,'mode');mode.write_text('fresh')
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        base=f'http://127.0.0.1:{port}';opener=build_opener(ProxyHandler({}))
        server=subprocess.Popen([sys.executable,__file__,'--server',folder,str(port)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def api(path,body=None,method=None):
            with opener.open(Request(base+path,data=json.dumps(body).encode() if body is not None else None,method=method or ('PUT' if body else 'GET'),headers={'Content-Type':'application/json'}),timeout=5) as r:return json.load(r)
        try:
            for _ in range(100):
                try:api('/api/health');break
                except Exception:time.sleep(.1)
            else:raise AssertionError('server unavailable')
            rows,market,quality=fixture();grid=[r['time'] for r in rows]
            d=api('/api/workspaces/main/drawings',dict(request_id='drawing',geometry=dict(kind='horizontal',symbol='BTCUSDT',price_source='LAST_PRICE',label='P5 hedef',anchors=[dict(time=grid[2],price='100')])),method='POST')
            payload=dict(request_id='binding',expected_binding_revision=0,target=dict(type='drawing',object_id=d['drawing_id'],revision=d['revision']),symbol='BTCUSDT',interval='15m',scale='LINEAR',grid_times=grid,data_snapshot_hash=None,query=dict(operation='priceAt',output='value',ratio=None),rule=dict(schema='chart-rule-definition/1',kind='touch',direction='ANY',tolerance='0',closed_candle=True,rearm_policy='EXPLICIT'))
            b=api('/api/workspaces/main/bindings/p5-price',payload)
            c=api('/api/workspaces/main/indicators?format_version=4')['indicators'][0]
            ib=api('/api/workspaces/main/bindings/p5-indicator',{**payload,'request_id':'indicator','target':dict(type='indicator',object_id=c['indicator_id'],revision=c['revision']),'query':dict(operation='valueAt',output='value',ratio=None),'rule':{**payload['rule'],'kind':'observe'}})
            before=api('/api/workspaces/main/bindings')
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True);p=browser.new_page(viewport={'width':1536,'height':900});p.set_default_timeout(7000);sockets=[]
                p.on('pageerror',lambda e:result['page_errors'].append(str(e)))
                def guard(route):
                    if not route.request.url.startswith(base+'/') or any(x in route.request.url for x in ['/api/commands','/api/account','/api/orders','/api/execution']):result['unexpected_requests'].append(route.request.url);route.abort()
                    else:route.continue_()
                p.route('**/*',guard);p.route('**/api/markets',lambda r:r.fulfill(json={'markets':[market]}));p.route('**/api/candles*',lambda r:r.fulfill(json=dict(symbol='BTCUSDT',interval='15m',market=market,quality=quality,candles=rows)));p.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
                p.goto(base)
                for _ in range(100):
                    if sockets:break
                    p.wait_for_timeout(50)
                sockets[-1].send(json.dumps(dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=1,status='LIVE',received_at=int(time.time()*1000),market=market,quality=quality,candles=rows)))
                p.get_by_text('100 mum',exact=True).wait_for()
                def open_dialog():
                    p.get_by_label('Paneller',exact=True).click();p.get_by_role('button',name='Araç / kural bağları',exact=True).click();p.get_by_role('dialog').wait_for()
                open_dialog();card=p.locator('[data-binding-id="p5-price"]');indicator=p.locator('[data-binding-id="p5-indicator"]')
                def inspect(state):
                    card.get_by_role('button',name='Uygunluğu kontrol et',exact=True).click();card.locator('[data-eligibility-state="'+state+'"]').wait_for()
                inspect('EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY');assert 'Bağ devre dışı' in card.inner_text();assert api('/api/workspaces/main/bindings/p5-price')['state']=='DISABLED';record('server_verified_price_is_suitable_without_activation_or_execution')
                indicator.get_by_role('button',name='Uygunluğu kontrol et').click();indicator.locator('[data-eligibility-state="OBSERVE_ONLY"]').wait_for();record('display_indicator_remains_observe_only')
                for value,text,name in [('clock','Sunucu saati güvenilir değil','clock_failure_has_explicit_reason'),('stale','Kaynak verinin yaşı eski','stale_upstream_blocks'),('tamper','ondalık','native_sidecar_tamper_blocks'),('missing','sunucuda açık veri aboneliği yok','ui_live_does_not_supply_server_proof')]:
                    mode.write_text(value);inspect('BLOCKED');assert text in card.inner_text();record(name)
                mode.write_text('fresh');inspect('EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY')
                card.locator('[data-eligibility-state]').scroll_into_view_if_needed();p.screenshot(path=str(ROOT/'reports/chart-p5-dark-20261113.png'));record('dark_theme_reason_and_proof_layout')
                p.wait_for_timeout(10100);assert card.locator('[data-eligibility-state]').count()==0;assert 'süresi doldu' in card.inner_text();record('point_in_time_result_expires_without_poll_or_activation')
                assert api('/api/workspaces/main/bindings')==before;record('all_inspections_leave_binding_history_unchanged')
                p.get_by_role('button',name='Bağ penceresini kapat').click()
                # Edit through actual API, then refresh target heads in the UI.
                api('/api/drawings/'+d['drawing_id'],dict(request_id='edit',expected_revision=1,geometry={**d['geometry'],'label':'P5 değişti'}),'PATCH')
                open_dialog();inspect('BLOCKED');assert 'durdurulmuş' in card.inner_text();record('changed_target_stopped_binding_cannot_gain_suitability')
                p.get_by_role('button',name='Bağ penceresini kapat').click();p.get_by_label('Açık temaya geç',exact=True).click();p.set_viewport_size({'width':1024,'height':768});open_dialog();inspect('BLOCKED');p.get_by_role('dialog').evaluate('(d)=>{d.scrollTop=d.scrollHeight}');p.wait_for_timeout(100);assert card.get_by_text('Bağ durdurulmuş; açık yeniden bağlama gerekiyor.',exact=True).is_visible();reason_box=card.get_by_text('Bağ durdurulmuş; açık yeniden bağlama gerekiyor.',exact=True).bounding_box();footer_box=p.get_by_role('dialog').locator('footer').bounding_box();assert reason_box['y']+reason_box['height']<=footer_box['y'];p.screenshot(path=str(ROOT/'reports/chart-p5-light-20261113.png'));record('light1024_blocked_reason_dialog_and_scroll_accessible')
                assert not result['page_errors'] and not result['unexpected_requests'];browser.close();result['passed']=True
        except Exception:
            result['error']=traceback.format_exc()
        finally:
            server.terminate();server.wait(timeout=10)
    Path(ROOT/'reports/chart-p5-validation-20261113.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=True,indent=2));return 0 if result['passed'] else 1

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--server':serve(sys.argv[2],sys.argv[3])
    else:sys.exit(main())
