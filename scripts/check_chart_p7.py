"""P7 report and replay-history production UI; isolated DB and no external access."""
import hashlib,json,socket,sqlite3,subprocess,sys,time,traceback
from contextlib import closing
from pathlib import Path
from urllib.request import build_opener,ProxyHandler
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from run_chart_p7 import Harness

def serve(folder,port):
 import uvicorn
 from agentrader.api.app import create_app
 from agentrader.application.settings import WebSettings
 class Hub:
  def close(self):pass
 settings=WebSettings(application_database=Path(folder)/'app.db',execution_database=Path(folder)/'execution.db',market_database=Path(folder)/'market.db',owner='fixture')
 uvicorn.run(create_app(settings,hub=Hub()),host='127.0.0.1',port=int(port),log_level='error')

def main():
 from playwright.sync_api import sync_playwright
 result=dict(task='P7',passed=False,checks=[],page_errors=[],unexpected_requests=[],scope='Production App/API, isolated replay DB, source-verified report, no account/order access')
 def record(name):result['checks'].append(dict(name=name,passed=True))
 h=Harness();h.ns='replay:local';h.seed();h.process();folder=h.tmp.name;execution=Path(folder)/'execution.db'
 with closing(sqlite3.connect(execution)) as db:db.execute('CREATE TABLE sentinel(v TEXT)');db.execute("INSERT INTO sentinel VALUES ('unchanged')");db.commit()
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
  wait_server();summary=api('/api/replay-validation');assert summary['state']=='VERIFIED_ISOLATED' and summary['passed_count']==36
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);p=browser.new_page(viewport={'width':1536,'height':900});p.set_default_timeout(7000);requests=[]
   p.on('pageerror',lambda e:result['page_errors'].append(str(e)))
   def guard(route):
    u=route.request.url
    if not u.startswith(base+'/') or any(x in u for x in ('/api/orders','/api/account','/api/execution','/api/commands')):result['unexpected_requests'].append(u);route.abort()
    else:route.continue_()
   p.route('**/*',guard);c=h.context(1);p.route('**/api/markets',lambda r:r.fulfill(json={'markets':[c['market']]}));p.route('**/api/candles*',lambda r:r.fulfill(json=dict(symbol='BTCUSDT',interval='15m',candles=c['rows'],market=c['market'],quality=c['quality'])));p.route_web_socket('**/api/market-stream*',lambda ws:None);p.on('request',lambda r:requests.append((r.method,r.url)))
   p.goto(base)
   def panel(name):p.get_by_label('Paneller',exact=True).click();p.get_by_role('button',name=name,exact=True).click();p.get_by_role('dialog').wait_for()
   def report():panel('Kuru çalışma sonuçları');p.get_by_text('36 / 36 senaryo geçti',exact=True).wait_for()
   report();assert p.locator('[data-replay-case]').count()==36;record('source_verified_report_renders_all36_real_results')
   for id in ('DR02','DR08','DR32'):
    row=p.locator('[data-replay-case="'+id+'"]');row.locator('summary').click();assert 'Beklenen' in row.inner_text() and 'Gözlenen' in row.inner_text()
   record('expected_observed_approach_rearm_unknown_delivery_are_inspectable')
   assert 'Canlı entegrasyon kapalı kalıyor.' in p.get_by_role('dialog').inner_text();assert 'QA01' in p.get_by_role('dialog').inner_text();record('isolated_pass_does_not_enable_live_or_close_physical_acceptance')
   p.get_by_role('dialog').evaluate('(d)=>{d.scrollTop=0}');p.screenshot(path=str(ROOT/'reports/chart-p7-dark-20261113.png'))
   p.get_by_role('button',name='Kuru çalışma sonuçlarını kapat',exact=True).click();panel('Yerel olay geçmişi');p.locator('[data-local-event]').first.wait_for();assert p.locator('[data-local-event]').count()==1;record('replay_episode_event_E3_hash_is_verified_by_typescript_history')
   p.get_by_role('button',name='Olay geçmişini kapat',exact=True).click();report()
   match='**/api/replay-validation'
   p.route(match,lambda r:r.fulfill(json={**summary,'state':'BLOCKED','passed_count':0,'cases':[],'reason':'REPLAY_EVIDENCE_STALE_OR_MISSING'}));p.get_by_role('button',name='Raporu yenile',exact=True).click();p.get_by_role('alert').wait_for();assert p.locator('[data-replay-case]').count()==0;p.unroute(match);record('stale_source_evidence_removes_green_success')
   p.route(match,lambda r:r.fulfill(json={**summary,'runtime_connected':True}));p.get_by_role('button',name='Raporu yenile',exact=True).click();p.get_by_role('alert').wait_for();assert p.locator('[data-replay-case]').count()==0;p.unroute(match);record('authority_tampered_report_rejected')
   p.route(match,lambda r:r.fulfill(status=503,json={}));p.get_by_role('button',name='Raporu yenile',exact=True).click();p.get_by_role('alert').wait_for();assert p.locator('[data-replay-case]').count()==0;p.unroute(match);record('failed_report_reload_leaves_no_old_success')
   held=[];p.route(match,lambda r:held.append(r));p.get_by_role('button',name='Raporu yenile',exact=True).click();p.wait_for_timeout(100);p.get_by_role('button',name='Kuru çalışma sonuçlarını kapat',exact=True).click();p.unroute(match);report()
   for r in held:
    try:r.fulfill(json={**summary,'runtime_connected':True})
    except Exception:pass
   assert p.locator('[data-replay-case]').count()==36;record('unmounted_pending_response_cannot_replace_reopened_report')
   p.get_by_role('button',name='Kuru çalışma sonuçlarını kapat',exact=True).click();p.get_by_label('Açık temaya geç',exact=True).click();p.set_viewport_size({'width':1024,'height':768});report();p.locator('[data-replay-case="DR08"] summary').click();p.locator('[data-replay-case="DR08"]').scroll_into_view_if_needed();p.screenshot(path=str(ROOT/'reports/chart-p7-light-20261113.png'));assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');record('dark1536_light1024_results_and_comparison_layout')
   assert all(method=='GET' for method,url in requests if '/replay-validation' in url);assert h.count()==1;assert hashlib.sha256(execution.read_bytes()).hexdigest()==execution_hash;record('readonly_report_preserves_events_and_execution_database_hash')
   checkpoint=h.engine.checkpoint('main','binding',h.ns);server.terminate();server.wait(timeout=10);server=start();wait_server();assert api('/api/replay-validation')['report_sha256']==summary['report_sha256'];assert h.engine.checkpoint('main','binding',h.ns)==checkpoint;record('server_restart_keeps_report_and_checkpoint_without_worker')
   assert not result['page_errors'] and not result['unexpected_requests'];browser.close();result['passed']=True
 except Exception:result['error']=traceback.format_exc()
 finally:server.terminate();server.wait(timeout=10);h.close()
 Path(ROOT/'reports/chart-p7-validation-20261113.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=True,indent=2));return 0 if result['passed'] else 1

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--server':serve(sys.argv[2],sys.argv[3])
 else:sys.exit(main())
