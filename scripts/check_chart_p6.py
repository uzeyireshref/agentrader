"""Production local-event history against isolated P6 SQLite; fixed fake sink only."""
import hashlib,json,os,socket,sqlite3,subprocess,sys,tempfile,time,traceback
from contextlib import closing
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from check_chart_p5 import fixture
from agentrader.local_chart_events import LocalChartEvents
from agentrader.chart_bindings import BindingService
from agentrader.chart_evidence import snapshot
from agentrader.chart_clock import POLICY
from agentrader.drawings.service import DrawingService
from agentrader.migrations import migrate,connect


def seed(db):
    migrate(db);rows,market,quality=fixture();rows[-3].update(close=95);rows[-3]['exact']['close']='95'
    grid=[r['time'] for r in rows];service=BindingService(db,'local:fixture');engine=LocalChartEvents(db,'local:fixture')
    context=dict(transport_state='LIVE',identity=dict(source='binance_usdm_live_trade_price',environment='live_public',product='USD-M',price_type='LAST_PRICE',symbol='BTCUSDT',interval='15m'),rows=rows,market=market,quality=quality,stream_epoch='a'*32,generation=1,data_revision=1,data_proof=snapshot(rows,market,quality,symbol='BTCUSDT',interval='15m',epoch='a'*32,generation=1,revision=1).view(),timing=dict(schema='chart-time-proof/1',policy=dict(POLICY),state='FRESH',reason=None,data_age_ms=1,upstream_age_upper_ms=2,uncertainty_ms=1,upstream_event_time=rows[-1]['time']*1000+3000))
    for state in ('delivered','unknown','inflight','canceled','pending'):
        d=DrawingService(db,'local:fixture').create('main','drawing-'+state,dict(kind='horizontal',symbol='BTCUSDT',price_source='LAST_PRICE',label=state,anchors=[dict(time=grid[2],price='100')]))
        b=service.save_binding('main',state,'binding-'+state,0,dict(type='drawing',object_id=d['drawing_id'],revision=1),'BTCUSDT','15m','LINEAR',grid,None,dict(operation='priceAt',output='value',ratio=None),dict(schema='chart-rule-definition/1',kind='touch',direction='ANY',tolerance='0',closed_candle=True,rearm_policy='EXPLICIT'))
        result=engine.commit(engine.prepare('main',state,'replay:local',context));assert result['created']
        if state=='delivered':assert engine.deliver_one('main','replay:local')['state']=='DELIVERED_FAKE'
        if state=='unknown':
            def fault(stage):
                if stage=='after_fake_send':raise RuntimeError('ack lost')
            assert engine.deliver_one('main','replay:local',_fault=fault)['state']=='DELIVERY_UNKNOWN'
        if state=='inflight':
            def fault(stage):
                if stage=='after_delivery_claim':raise RuntimeError('crash')
            try:engine.deliver_one('main','replay:local',_fault=fault)
            except RuntimeError:pass
        if state=='canceled':
            DrawingService(db,'local:fixture').update(d['drawing_id'],'cancel',1,{**d['geometry'],'label':'changed'});assert engine.deliver_one('main','replay:local')['state']=='CANCELED_SUPERSEDED'
        if state=='pending':
            other=engine.commit(engine.prepare('main',state,'replay:other',context));assert other['domain_event_id']==result['domain_event_id'] and other['event_id']!=result['event_id']
    return rows,market,quality


def serve(folder,port):
    import uvicorn
    from agentrader.api.app import create_app
    from agentrader.application.settings import WebSettings
    class Hub:
        def close(self):pass
    settings=WebSettings(application_database=Path(folder,'app.db'),execution_database=Path(folder,'execution.db'),market_database=Path(folder,'market.db'),owner='local:fixture')
    uvicorn.run(create_app(settings,hub=Hub()),host='127.0.0.1',port=int(port),log_level='error')


def main():
    from playwright.sync_api import sync_playwright
    result=dict(task='P6',passed=False,checks=[],page_errors=[],unexpected_requests=[],scope='Production App/API, isolated application DB, fixed SQLite fake sink, no external side effects')
    def record(name):result['checks'].append(dict(name=name,passed=True))
    with tempfile.TemporaryDirectory(prefix='agentrader-p6-') as folder:
        db=Path(folder,'app.db');rows,market,quality=seed(db)
        execution=Path(folder,'execution.db')
        with closing(sqlite3.connect(execution)) as c:
            c.execute('CREATE TABLE sentinel(value TEXT)');c.execute("INSERT INTO sentinel VALUES ('unchanged')");c.commit()
        execution_hash=hashlib.sha256(execution.read_bytes()).hexdigest()
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        base=f'http://127.0.0.1:{port}';opener=build_opener(ProxyHandler({}))
        def api(path):
            with opener.open(base+path,timeout=5) as r:return json.load(r)
        def start():return subprocess.Popen([sys.executable,__file__,'--server',folder,str(port)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def wait_server():
            for _ in range(100):
                try:api('/api/health');return
                except Exception:time.sleep(.1)
            raise AssertionError('server unavailable')
        server=start()
        try:
            wait_server();before=api('/api/workspaces/main/local-events');assert len(before['events'])==5
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True);p=browser.new_page(viewport={'width':1536,'height':900});p.set_default_timeout(7000);sockets=[];requests=[]
                p.on('pageerror',lambda e:result['page_errors'].append(str(e)))
                def guard(route):
                    u=route.request.url
                    if not u.startswith(base+'/') or any(x in u for x in ['/api/orders','/api/account','/api/execution','/api/commands']):result['unexpected_requests'].append(u);route.abort()
                    else:route.continue_()
                p.route('**/*',guard);p.route('**/api/markets',lambda r:r.fulfill(json={'markets':[market]}));p.route('**/api/candles*',lambda r:r.fulfill(json=dict(symbol='BTCUSDT',interval='15m',market=market,quality=quality,candles=rows)));p.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws));p.on('request',lambda r:requests.append((r.method,r.url)))
                p.goto(base)
                def open_dialog():p.get_by_label('Paneller',exact=True).click();p.get_by_role('button',name='Yerel olay geçmişi',exact=True).click();p.get_by_role('dialog').wait_for();p.locator('[data-local-event]').first.wait_for()
                open_dialog();assert p.locator('[data-local-event]').count()==5;record('production_readonly_panel_lists_five_durable_intent_states')
                for label in ('Sahte alıcı için bekliyor','Sahte teslim işlemi sürüyor','Sahte alıcıya kaydedildi','Teslim sonucu bilinmiyor','Hedef değişti; teslim iptal edildi'):assert label in p.get_by_role('dialog').inner_text()
                record('unknown_and_canceled_are_not_rendered_as_delivered')
                unknown=p.locator('[data-intent-state="DELIVERY_UNKNOWN"]');unknown.locator('summary').click();unknown.locator('details').scroll_into_view_if_needed();assert 'tam bir kez teslim edildiği varsayılmaz' in unknown.inner_text();record('ambiguous_delivery_and_hash_audit_are_explicit')
                p.screenshot(path=str(ROOT/'reports/chart-p6-dark-20261113.png'))
                run=p.get_by_label('Deneme kimliği',exact=True);run.fill('other');p.get_by_role('button',name='Kayıtları yükle',exact=True).click();p.get_by_text('Alan: replay:other',exact=False).wait_for();assert p.locator('[data-local-event]').count()==1;record('replay_namespaces_do_not_mix_records')
                run.fill('empty');p.get_by_role('button',name='Kayıtları yükle',exact=True).click();p.get_by_text('Bu deneme alanında yerel olay yok.',exact=False).wait_for();assert p.locator('[data-local-event]').count()==0;record('empty_namespace_shows_no_stale_records')
                run.fill('bad space');p.get_by_role('button',name='Kayıtları yükle',exact=True).click();p.get_by_role('alert').wait_for();assert p.locator('[data-local-event]').count()==0;record('invalid_namespace_rejected_without_mutation')
                run.fill('local');p.get_by_role('button',name='Kayıtları yükle',exact=True).click();p.locator('[data-local-event]').first.wait_for()
                p.route('**/api/workspaces/main/local-events*',lambda r:r.fulfill(status=503,json={'error':{'code':'UNAVAILABLE'}}));p.get_by_role('button',name='Kayıtları yükle',exact=True).click();p.get_by_role('alert').wait_for();assert p.locator('[data-local-event]').count()==0;p.unroute('**/api/workspaces/main/local-events*');record('failed_reload_clears_previous_success')
                # A late response cannot replace a newly selected run.
                held=[];p.route('**/api/workspaces/main/local-events*',lambda r:held.append(r));p.get_by_role('button',name='Kayıtları yükle',exact=True).click();p.wait_for_timeout(100);run.fill('other')
                for r in held:
                    try:r.fulfill(json=before)
                    except Exception:pass
                p.wait_for_timeout(100);assert p.locator('[data-local-event]').count()==0;p.unroute('**/api/workspaces/main/local-events*');record('late_old_run_response_cannot_relabel_new_namespace')
                run.fill('local');p.get_by_role('button',name='Kayıtları yükle',exact=True).click();p.locator('[data-local-event]').first.wait_for();p.get_by_role('button',name='Olay geçmişini kapat',exact=True).click();p.get_by_label('Açık temaya geç',exact=True).click();p.set_viewport_size({'width':1024,'height':768});open_dialog();unknown=p.locator('[data-intent-state="DELIVERY_UNKNOWN"]');unknown.locator('summary').click();p.get_by_role('dialog').evaluate('(d)=>{d.scrollTop=d.scrollHeight}');p.screenshot(path=str(ROOT/'reports/chart-p6-light-20261113.png'));assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');record('light1024_dark1536_audit_layout_and_scroll')
                assert all(method=='GET' for method,url in requests if '/local-events' in url);assert api('/api/workspaces/main/local-events')==before;record('history_has_no_write_dispatch_retry_or_activation_request')
                server.terminate();server.wait(timeout=10);server=start();wait_server();assert api('/api/workspaces/main/local-events')==before;record('restart_preserves_events_phase_and_ambiguous_delivery_state')
                assert hashlib.sha256(execution.read_bytes()).hexdigest()==execution_hash;record('execution_database_byte_hash_unchanged')
                assert not result['page_errors'] and not result['unexpected_requests'];result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    Path(ROOT/'reports/chart-p6-validation-20261113.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=True,indent=2));return 0 if result['passed'] else 1

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--server':serve(sys.argv[2],sys.argv[3])
    else:sys.exit(main())
