"""T10: production UI, native chart, real configuration HTTP/SQLite, isolated market."""
import json,math,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from urllib.parse import urlparse,parse_qs
from playwright.sync_api import sync_playwright
from measure_chart_interactions import INSPECT,ROOT
from agentrader.indicator_config import series as reference

def main():
 result=dict(task='T10',passed=False,checks=[],page_errors=[],unexpected_requests=[],scope='Production App, synthetic market, isolated SQLite; no account/order access')
 def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
 with tempfile.TemporaryDirectory(prefix='agentrader-t10-') as folder:
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  base=f'http://127.0.0.1:{port}';opener=build_opener(ProxyHandler({}));env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(Path(folder)/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(Path(folder)/'execution.db'),AGENTRADER_CHART_DATABASE=str(Path(folder)/'market.db'),AGENTRADER_WEB_TOKEN='')
  def start():return subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  server=start()
  def api(path,body=None):
   if path.endswith('/indicators'):path+='?format_version=2'
   req=Request(base+path,data=json.dumps(body).encode() if body else None,method='PUT' if body else 'GET',headers={'Content-Type':'application/json'})
   with opener.open(req,timeout=5) as r:return json.load(r)
  def wait_server():
   for _ in range(100):
    try:api('/api/health');return
    except Exception:time.sleep(.1)
   raise AssertionError('server unavailable')
  try:
   wait_server();markets=[dict(symbol=s,base_asset=s[:-4],quote_asset='USDT',contract_type='PERPETUAL',tick_size='0.25') for s in ['BTCUSDT','ETHUSDT']]
   def rows(interval):
    step={'15m':900,'5m':300}[interval];end=1800000000//step*step;out=[]
    for i in range(300):
     o=100+i*.1+math.sin(i*.17)*5;c=o+math.sin(i*1.8)*2;t=end-(299-i)*step;out.append(dict(time=t,open=o,close=c,high=max(o,c)+1,low=min(o,c)-1,volume=15+abs(math.sin(i))*65,quote_volume=1000,close_time=(t+step)*1000-1,closed=i<299))
    return out
   with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True);p=browser.new_page(viewport={'width':1536,'height':900});p.set_default_timeout(7000);sockets=[];requests=[];sequence=[0]
    p.on('pageerror',lambda e:result['page_errors'].append(str(e)))
    def guard(route):
     if not route.request.url.startswith(base+'/') or any(x in route.request.url for x in ['/api/orders','/api/account','/api/commands','/api/execution']):result['unexpected_requests'].append(route.request.url);route.abort()
     else:route.continue_()
    p.route('**/*',guard);p.route('**/api/markets',lambda r:r.fulfill(json={'markets':markets}));p.route('**/api/candles*',lambda r:r.fulfill(json={'candles':[],'has_more':False}));p.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws));p.on('request',lambda r:requests.append((r.method,r.url)))
    def read(expr):return p.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');'+'}')
    def feed(symbol='BTCUSDT',interval='15m',data=None):
     data=rows(interval) if data is None else data
     for _ in range(100):
      matching=[w for w in sockets if parse_qs(urlparse(w.url).query).get('symbol')==[symbol] and parse_qs(urlparse(w.url).query).get('interval')==[interval]]
      if matching:break
      p.wait_for_timeout(50)
     assert matching
     market=next(m for m in markets if m['symbol']==symbol);sequence[0]+=1;matching[-1].send(json.dumps(dict(type='snapshot',symbol=symbol,interval=interval,generation=1,sequence=sequence[0],status='LIVE',received_at=int(time.time()*1000),market=market,quality={'state':'OK','missing_bars':0},candles=data)));p.get_by_text(str(len(data))+' mum',exact=True).wait_for();p.wait_for_timeout(100)
    def menu(label,button):
     toggle=p.get_by_label(label,exact=True)
     if toggle.locator('..').get_attribute('open') is None:toggle.click()
     toggle.locator('..').get_by_role('button',name=button,exact=True).click()
    def settings():menu('Göstergeler','Gösterge ayarları');p.get_by_role('dialog').wait_for()
    def save():
     with p.expect_response(lambda r:r.request.method=='PUT' and urlparse(r.url).path.endswith('/indicators')) as response:p.get_by_role('button',name='Gösterge ayarlarını kaydet',exact=True).click()
     p.wait_for_timeout(100);return response.value
    def verify(interval='15m',data=None):
     data=rows(interval) if data is None else data
     all_series=read("chart.panes().flatMap(p=>p.getSeries()).filter(s=>s.seriesType()==='Line').map(s=>({title:s.options().title,data:s.data()}))");items=api('/api/workspaces/main/indicators')['indicators'];enabled=[c for c in items if c['enabled']];assert len(all_series)==len(enabled),(len(all_series),len(enabled))
     for c in enabled:
      a=next(s for s in all_series if s['title']==c['kind']+' '+str(c['period']));expected=reference(data,c,interval);assert len(a['data'])==len(expected)
      for observed,wanted in zip(a['data'],expected):assert observed['time']==wanted['time'] and abs(observed['value']-wanted['value'])<1e-9
    p.goto(base);feed();settings();assert [p.get_by_label(i+' periyot',exact=True).input_value() for i in ['ema-fast','ema-slow','rsi-main']]==['20','50','14'];record('default_ids_periods_and_explicit_v1_seed_policy')
    for key,period,source in [('ema-fast','9','hlc3'),('ema-slow','34','hl2'),('rsi-main','7','ohlc4')]:p.get_by_label(key+' periyot',exact=True).fill(period);p.get_by_label(key+' kaynak',exact=True).select_option(source)
    for checkbox in p.get_by_role('dialog').get_by_role('checkbox').all():checkbox.check()
    assert save().status==200;verify();assert read('chart.panes().length')==4;record('three_persistent_instances_render_every_point_equal_to_python_reference')
    p.get_by_label('Veri penceresini göster veya gizle',exact=True).click();assert 'EMA 9 · HLC3' in p.locator('.data-window').inner_text();assert 'RSI 7 · OHLC4' in p.locator('.data-window').inner_text();record('data_window_uses_saved_period_source_and_live_values')
    settings();p.get_by_label('ema-fast periyot',exact=True).fill('501');before=len(requests);p.get_by_role('button',name='Gösterge ayarlarını kaydet',exact=True).click();p.wait_for_timeout(100);assert not any(method=='PUT' for method,url in requests[before:]);p.keyboard.press('Escape');verify();record('invalid_period_and_cancel_do_not_change_persisted_or_rendered_data')
    settings();p.get_by_label('ema-fast periyot',exact=True).fill('10')
    def lost(route):
     response=route.fetch();assert response.status==200;route.fulfill(status=503,json={'error':{'code':'SIMULATED_LOST_ACK'}})
    p.route('**/api/workspaces/main/indicators*',lost);assert save().status==503;assert p.get_by_role('dialog').is_visible();assert read("chart.panes()[0].getSeries().some(s=>s.options().title==='EMA 9')");revision=api('/api/workspaces/main/indicators')['revision'];p.unroute('**/api/workspaces/main/indicators*',lost);response=save();assert response.status==200 and response.json()['duplicate'];assert api('/api/workspaces/main/indicators')['revision']==revision;verify();record('lost_save_ack_retries_same_request_without_duplicate_revision')
    settings();p.get_by_label('ema-fast periyot',exact=True).fill('11');head=api('/api/workspaces/main/indicators');head['indicators'][0]['period']=12;api('/api/workspaces/main/indicators',dict(request_id='other-screen',expected_revision=head['revision'],indicators=head['indicators']));assert save().status==409;assert 'başka bir ekranda' in p.get_by_role('dialog').inner_text();p.get_by_label('Gösterge ayarlarını kapat',exact=True).click();p.locator('.chart-data-notice').get_by_role('button',name='Gösterge ayarlarını yeniden yükle',exact=True).click();p.wait_for_timeout(150);verify();record('concurrent_revision_conflict_requires_explicit_reload')
    settings();p.get_by_label('ema-fast periyot',exact=True).fill('500');p.get_by_role('dialog').get_by_role('checkbox').nth(1).uncheck();assert save().status==200;verify();assert p.locator('.data-window').get_by_text('EMA 500 · HLC3',exact=True).locator('..').locator('dd').inner_text()=='Yetersiz geçmiş';assert not read("chart.panes().flatMap(p=>p.getSeries()).some(s=>s.options().title==='EMA 34')");record('individual_visibility_and_long_period_warmup_never_publish_zero')
    settings();p.get_by_label('ema-fast periyot',exact=True).fill('12');p.get_by_role('dialog').get_by_role('checkbox').nth(1).check();assert save().status==200;verify();record('restoring_period_and_instance_rebuilds_full_series_without_residue')
    # Native RSI pane is created and removed 50 times, each via real persisted UI action.
    for cycle in range(50):
     with p.expect_response(lambda r:r.request.method=='PUT' and urlparse(r.url).path.endswith('/indicators')):menu('Paneller','RSI paneli')
     p.wait_for_timeout(35);assert read('chart.panes().length')==3
     with p.expect_response(lambda r:r.request.method=='PUT' and urlparse(r.url).path.endswith('/indicators')):menu('Paneller','RSI paneli')
     p.wait_for_timeout(35);assert read('chart.panes().length')==4
    verify();assert len(sockets)==1;record('fifty_persisted_rsi_pane_cycles_have_no_duplicate_series_or_streams',cycles=50)
    p.get_by_role('group',name='Zaman dilimi',exact=True).get_by_role('button',name='5 dk',exact=True).click();feed(interval='5m');verify('5m');record('interval_change_recomputes_same_saved_config_on_new_grid')
    p.get_by_label('Sözleşme seç',exact=True).select_option('ETHUSDT');feed('ETHUSDT','5m');verify('5m');record('symbol_change_preserves_workspace_indicator_instances')
    assert 'Açık mumdaki gösterge değerleri güncellenebilir.' in p.locator('.data-window').inner_text();record('open_candle_indicator_outputs_are_explicitly_provisional')
    damaged=rows('5m');damaged.pop(100);feed('ETHUSDT','5m',damaged);assert p.locator('.data-window').get_by_text('SMA 20 · CLOSE',exact=True).locator('..').locator('dd').inner_text()=='Veri boşluğu / geçersiz grid';assert read("chart.panes().flatMap(p=>p.getSeries()).filter(s=>s.seriesType()==='Line').every(s=>s.data().length===0)");record('missing_bar_clears_all_plot_values_and_explains_unavailable_state')
    feed('ETHUSDT','5m');verify('5m');record('repaired_grid_restores_all_configured_calculations')
    revised=rows('5m');revised[-1].update(open=125,high=180,low=60,close=150);feed('ETHUSDT','5m',revised);verify('5m',revised);record('live_open_candle_revision_recalculates_sma_ema_rsi_atr')
    flat=rows('5m')
    for item in flat:item.update(open=10,high=10,low=10,close=10)
    feed('ETHUSDT','5m',flat);assert read("chart.panes().flatMap(p=>p.getSeries()).find(s=>s.options().title==='RSI 7').data().at(-1).value")==100
    settings();p.get_by_label('RSI hesap sürümü',exact=True).select_option('1');assert save().status==200;assert read("chart.panes().flatMap(p=>p.getSeries()).find(s=>s.options().title==='RSI 7').data().at(-1).value")==50
    settings();p.get_by_label('RSI hesap sürümü',exact=True).select_option('2');assert save().status==200;assert read("chart.panes().flatMap(p=>p.getSeries()).find(s=>s.options().title==='RSI 7').data().at(-1).value")==100;record('explicit_rsi_v1_v2_selection_changes_flat_result_50_to_100')
    feed('ETHUSDT','5m');verify('5m')
    p.wait_for_timeout(1000);assert api('/api/workspaces/main')['preferences']==dict(symbol='ETHUSDT',interval='5m');expected=api('/api/workspaces/main/indicators');sockets.clear();p.reload();feed('ETHUSDT','5m');verify('5m');assert api('/api/workspaces/main/indicators')==expected;record('page_reload_restores_period_source_enabled_and_instance_revisions')
    p.screenshot(path=str(ROOT/'reports/chart-t10-dark-20261112.png'));settings();p.set_viewport_size({'width':1024,'height':768});assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');assert p.get_by_role('dialog').bounding_box()['width']<1024;p.screenshot(path=str(ROOT/'reports/chart-t10-settings-dark-20261112.png'));p.keyboard.press('Escape');p.get_by_label('Açık temaya geç').click();settings();p.screenshot(path=str(ROOT/'reports/chart-t10-settings-light-20261112.png'));p.keyboard.press('Escape');record('modal_keyboard_cancel_and_light_dark_1024_layout')
    server.terminate();server.wait(timeout=10);server=start();wait_server();assert api('/api/workspaces/main/indicators')==expected;record('server_restart_restores_saved_configuration_without_exchange_execution')
    assert not result['page_errors'];assert not result['unexpected_requests'];assert not api('/api/health')['trading_commands_enabled'];result['passed']=True;browser.close()
  except Exception:result['error']=traceback.format_exc()
  finally:server.terminate();server.wait(timeout=10)
 (ROOT/'reports/chart-t10-validation-20261112.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
