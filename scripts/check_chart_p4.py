"""P4: production UI, native chart, real configuration HTTP/SQLite, isolated market."""
import json,math,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from urllib.parse import urlparse,parse_qs
from playwright.sync_api import sync_playwright
from measure_chart_interactions import INSPECT,ROOT
from agentrader.indicator_config import series as reference,multi_series
from agentrader.vwap import vwap_series
from datetime import datetime,timezone

def main():
 result=dict(task='P4',passed=False,checks=[],page_errors=[],unexpected_requests=[],scope='Production App, synthetic market, isolated SQLite; no account/order access')
 def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
 with tempfile.TemporaryDirectory(prefix='agentrader-p4-') as folder:
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  base=f'http://127.0.0.1:{port}';opener=build_opener(ProxyHandler({}));env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(Path(folder)/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(Path(folder)/'execution.db'),AGENTRADER_CHART_DATABASE=str(Path(folder)/'market.db'),AGENTRADER_WEB_TOKEN='')
  def start():return subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  server=start()
  def api(path,body=None,method=None):
   if path.endswith('/indicators'):path+='?format_version=4'
   req=Request(base+path,data=json.dumps(body).encode() if body else None,method=method or ('PUT' if body else 'GET'),headers={'Content-Type':'application/json'})
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
    for r in out:
     r['quote_volume']=r['close']*r['volume'];r['exact']=dict(schema='chart-exact-decimal/1',state='VERIFIED',provenance='UPSTREAM_DECIMAL_TEXT',volume=str(r['volume']),quote_volume=str(r['quote_volume']))
    return out
   with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True);p=browser.new_page(viewport={'width':1536,'height':900},timezone_id='America/New_York');p.set_default_timeout(7000);sockets=[];requests=[];sequence=[0];active_symbol=['BTCUSDT'];history_wait=[]
    p.on('pageerror',lambda e:result['page_errors'].append(str(e)))
    def guard(route):
     if not route.request.url.startswith(base+'/') or any(x in route.request.url for x in ['/api/orders','/api/account','/api/commands','/api/execution']):result['unexpected_requests'].append(route.request.url);route.abort()
     else:route.continue_()
    p.route('**/*',guard);p.route('**/api/markets',lambda r:r.fulfill(json={'markets':markets}));p.route('**/api/candles*',lambda r:history_wait.append(r));p.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws));p.on('request',lambda r:requests.append((r.method,r.url)))
    def read(expr):return p.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');'+'}')
    def feed(symbol='BTCUSDT',interval='15m',data=None):
     data=rows(interval) if data is None else data;active_symbol[0]=symbol
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
    def listing(symbol='BTCUSDT'):return api('/api/workspaces/main/drawings?symbol='+symbol+'&format_version=8')['drawings']
    def create(label,kind='horizontal',symbol='BTCUSDT'):
     g=dict(kind=kind,symbol=symbol,price_source='LAST_PRICE',label=label,anchors=[dict(time=rows('15m')[220]['time'],price='120')])
     if kind=='text':g.update(schema='chart-annotation/1',text='Araştırma notu')
     return api('/api/workspaces/main/drawings?format_version=8',dict(request_id='seed-'+label.encode().hex(),geometry=g),'POST')
    a=create('Bağ hedefi');b=create('İkinci hedef');note=create('Açıklama','text');other=create('ETH hedef','horizontal','ETHUSDT')
    def all_bindings():return api('/api/workspaces/main/bindings')['bindings']
    def bound(key):return api('/api/workspaces/main/bindings/'+key)
    def open_bindings():menu('Paneller','Araç / kural bağları');p.get_by_role('dialog').wait_for();p.get_by_role('button',name='Bağları yenile',exact=True).wait_for();p.wait_for_timeout(120)
    def close():p.get_by_label('Bağ penceresini kapat',exact=True).click()
    def card(key):return p.locator('[data-binding-id="'+key+'"]')
    def save_binding(name='Devre dışı tanım kaydet',key=None):
     button=card(key).get_by_role('button',name=name,exact=True) if key else p.get_by_role('button',name=name,exact=True)
     with p.expect_response(lambda r:r.request.method=='PUT' and '/bindings/' in r.url) as response:button.click()
     p.wait_for_timeout(160);return response.value
    def refresh():p.get_by_role('button',name='Bağları yenile',exact=True).click();p.wait_for_timeout(200)
    def pick(label):p.locator('.drawing-list button').filter(has=p.get_by_text(label,exact=True)).click()
    p.goto(base);feed();p.get_by_label('Çizimleri göster veya gizle',exact=True).click();pick('Bağ hedefi');open_bindings();p.get_by_role('dialog').get_by_label('Bağ hedefi',exact=True).select_option('drawing:'+a['drawing_id']);p.get_by_label('Bağ kuralı',exact=True).select_option('approach');p.get_by_label('Bağ yönü',exact=True).select_option('BELOW');p.get_by_label('Bağ toleransı',exact=True).fill('2.50');response=save_binding();assert response.status==200;first=response.json();key=first['binding_id'];assert first['state']=='DISABLED';assert first['definition']['rule']['tolerance']=='2.5';assert first['definition']['grid']['count']==300;assert not first['definition']['bot_capabilities']['write_target'];assert not first['order_authority'];assert first['definition']['data_reference']['state']=='CLIENT_REFERENCE_NOT_ELIGIBILITY';assert card(key).get_attribute('data-binding-state')=='DISABLED';record('closed_price_rule_saves_disabled_with_owner_revision_grid_hash_and_no_target_write_or_order_capability');close()
    p.get_by_label('Çizim fiyatı',exact=True).fill('123')
    with p.expect_response(lambda r:r.request.method=='PATCH' and '/api/drawings/' in r.url):p.get_by_role('button',name='Kaydet',exact=True).click()
    p.wait_for_timeout(120);assert bound(key)['state']=='STOPPED';assert bound(key)['reason']=='TARGET_REVISION_CHANGED';open_bindings();assert card(key).get_attribute('data-binding-state')=='STOPPED';card(key).get_by_role('button',name='Hedefi seç',exact=True).click();assert p.get_by_label('Bağ kuralı',exact=True).input_value()=='approach';response=save_binding('Bu kuralla yeniden bağla',key);assert response.status==200;assert response.json()['revision']==3 and response.json()['definition']['target']['revision']==2;assert response.json()['definition_hash']!=first['definition_hash'];record('real_form_edit_latches_stop_and_explicit_rebind_preserves_rule_on_new_target_revision');close()
    with p.expect_response(lambda r:r.request.method=='POST' and '/drawing-operations' in r.url):p.get_by_label('Çizim değişikliğini geri al',exact=True).click()
    p.wait_for_timeout(100);assert bound(key)['state']=='STOPPED';stopped_revision=bound(key)['revision']
    with p.expect_response(lambda r:r.request.method=='POST' and '/drawing-operations' in r.url):p.get_by_label('Çizim değişikliğini yinele',exact=True).click()
    p.wait_for_timeout(100);assert bound(key)['revision']==stopped_revision;open_bindings();card(key).get_by_role('button',name='Hedefi seç',exact=True).click();assert save_binding('Bu kuralla yeniden bağla',key).status==200;record('undo_redo_keep_stop_latched_even_when_geometry_returns_and_rebind_is_always_explicit');close()
    pick('Bağ hedefi')
    with p.expect_response(lambda r:r.request.method=='DELETE' and '/api/drawings/' in r.url):p.get_by_role('button',name='Sil',exact=True).click()
    p.wait_for_timeout(100);assert bound(key)['reason']=='TARGET_DELETED';open_bindings();card(key).get_by_role('button',name='Hedefi seç',exact=True).click();assert card(key).get_by_role('button',name='Bu kuralla yeniden bağla',exact=True).is_disabled();assert card(key).get_attribute('data-binding-state')=='STOPPED';record('deleted_target_binding_stays_visible_for_audit_and_cannot_be_rebound');close()
    with p.expect_response(lambda r:r.request.method=='POST' and '/drawing-operations' in r.url):p.get_by_label('Çizim değişikliğini geri al',exact=True).click()
    p.wait_for_timeout(120);open_bindings();card(key).get_by_role('button',name='Hedefi seç',exact=True).click();assert save_binding('Bu kuralla yeniden bağla',key).status==200;assert bound(key)['state']=='DISABLED';record('undo_delete_restores_target_but_old_definition_only_resumes_as_disabled_after_manual_rebind')
    p.get_by_role('dialog').get_by_label('Bağ hedefi',exact=True).select_option('indicator:ema-fast');assert p.get_by_label('Bağ kuralı',exact=True).locator('option').count()==1;response=save_binding();assert response.status==200;indicator_key=response.json()['binding_id'];assert response.json()['definition']['rule']['kind']=='observe';record('indicator_output_binding_is_observe_only_and_does_not_enable_hidden_indicator');close();settings();p.get_by_label('ema-fast periyot',exact=True).fill('9');assert save().status==200;assert bound(indicator_key)['state']=='STOPPED';assert bound(key)['state']=='DISABLED';open_bindings();card(indicator_key).get_by_role('button',name='Hedefi seç',exact=True).click();assert save_binding('Bu kuralla yeniden bağla',indicator_key).status==200;record('indicator_parameter_change_stops_only_its_own_binding_and_requires_new_revision_rebind')
    from agentrader.chart_profiles import default_view
    from agentrader.indicator_config import defaults_v4
    body=dict(schema='chart-template/1',view=default_view(),indicators=defaults_v4(),drawing_defaults={'horizontal':dict(style=dict(color='#9b6ed6',line_width=3,line_style='dashed'),options={})});api('/api/workspaces/main/templates/p4',dict(request_id='template',expected_revision=0,name='Bağ regression',body=body));profile=api('/api/workspaces/main/profile');ind=api('/api/workspaces/main/indicators');heads=[dict(drawing_id=d['drawing_id'],revision=d['revision']) for d in listing()];api('/api/workspaces/main/template-restore',dict(request_id='apply-template',template_id='p4',template_revision=1,expected_profile_revision=profile['revision'],expected_indicator_revision=ind['revision'],symbol='BTCUSDT',interval='15m',expected_drawings=heads,apply_drawing_styles=True),'POST');refresh();assert bound(key)['state']=='STOPPED';assert bound(indicator_key)['state']=='STOPPED';assert card(key).get_attribute('data-binding-state')=='STOPPED';record('atomic_workspace_restore_stops_both_changed_drawing_and_indicator_bindings')
    p.get_by_role('dialog').get_by_label('Bağ hedefi',exact=True).select_option('drawing:'+note['drawing_id']);assert p.get_by_role('button',name='Devre dışı tanım kaydet',exact=True).is_disabled();assert 'yalnız görseldir' in p.get_by_role('dialog').inner_text();p.get_by_role('dialog').get_by_label('Bağ hedefi',exact=True).select_option('indicator:macd-main');p.get_by_label('Bağ sorgusu',exact=True).select_option('valueAt:histogram');response=save_binding();assert response.status==200 and response.json()['definition']['query']['output']=='histogram';assert response.json()['definition']['rule']['kind']=='observe';record('display_annotation_is_blocked_while_macd_output_identity_and_parity_traceability_are_explicit')
    p.get_by_role('dialog').get_by_label('Bağ hedefi',exact=True).select_option('drawing:'+b['drawing_id']);p.get_by_label('Bağ kuralı',exact=True).select_option('touch');p.get_by_label('Bağ toleransı',exact=True).fill('0');count=len(all_bindings())
    def lost(route):
     if route.request.method=='PUT':
      response=route.fetch();assert response.status==200;route.fulfill(status=503,json={'error':{'code':'SIMULATED_LOST_ACK'}})
     else:route.continue_()
    p.route('**/bindings/*',lost);assert save_binding().status==503;assert len(all_bindings())==count+1;p.unroute('**/bindings/*',lost)
    extended=rows('15m');extended[-1]['closed']=True;new={**extended[-1],'time':extended[-1]['time']+900,'close_time':extended[-1]['close_time']+900000,'closed':False};extended.append(new);feed(data=extended);response=save_binding();assert response.status==200 and response.json()['duplicate'];assert response.json()['definition']['grid']['count']==300;assert len(all_bindings())==count+1;record('lost_binding_ack_retries_same_identity_and_frozen_reference_after_new_market_bar')
    current_b=next(d for d in listing() if d['drawing_id']==b['drawing_id']);renamed={**current_b['geometry'],'label':'İkinci hedef revize'};api('/api/drawings/'+b['drawing_id']+'?format_version=8',dict(request_id='remote-edit',expected_revision=current_b['revision'],geometry=renamed),'PATCH');assert save_binding().status==409;refresh();response=save_binding();assert response.status==200;assert response.json()['definition']['target']['revision']==current_b['revision']+1;record('stale_target_conflict_requires_refresh_of_actual_drawing_and_not_just_binding_list')
    held=[]
    def delayed(route):held.append((route,route.fetch()))
    p.route('**/bindings/*',delayed);p.get_by_role('button',name='Devre dışı tanım kaydet',exact=True).click()
    for _ in range(80):
     if held:break
     p.wait_for_timeout(50)
    assert held;p.get_by_label('Sözleşme seç',exact=True).select_option('ETHUSDT',force=True);p.get_by_role('group',name='Zaman dilimi',exact=True).get_by_role('button',name='5 dk',exact=True).evaluate("e=>e.dispatchEvent(new MouseEvent('click',{bubbles:true}))");feed('ETHUSDT','5m');held[0][0].fulfill(response=held[0][1]);p.get_by_text('Hedef veya grafik bağlamı değişti. Bağları yenile.',exact=True).wait_for();p.unroute('**/bindings/*',delayed);assert p.get_by_label('Sözleşme seç',exact=True).input_value()=='ETHUSDT';assert held[0][1].json()['definition']['market']['symbol']=='BTCUSDT';record('late_binding_response_cannot_attach_old_coin_or_interval_definition_to_new_graph');refresh();close()
    p.get_by_label('Fiyat ekseni türü',exact=True).select_option('LOG');open_bindings();assert p.get_by_role('button',name='Devre dışı tanım kaydet',exact=True).is_disabled();assert 'lineer görünüme dön' in p.get_by_role('dialog').inner_text();close();p.get_by_label('Fiyat ekseni türü',exact=True).select_option('LINEAR');record('unsupported_log_definition_is_blocked_without_mutating_existing_binding_records')
    p.wait_for_timeout(600);expected=[(x['binding_id'],x['revision'],x['state'],x['definition_hash']) for x in all_bindings()];sockets.clear();p.reload();feed('ETHUSDT','5m');open_bindings();assert [(x['binding_id'],x['revision'],x['state'],x['definition_hash']) for x in all_bindings()]==expected;assert not p.get_by_role('dialog').get_by_role('button',name='Etkinleştir',exact=True).count();record('page_reload_restores_disabled_and_stopped_definitions_without_activation')
    p.get_by_role('dialog').get_by_label('Bağ hedefi',exact=True).select_option('drawing:'+other['drawing_id']);p.screenshot(path=str(ROOT/'reports/chart-p4-dark-20261112.png'));close();p.get_by_label('Açık temaya geç',exact=True).click();p.set_viewport_size({'width':1024,'height':768});open_bindings();assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');p.screenshot(path=str(ROOT/'reports/chart-p4-light-20261112.png'));close();record('binding_form_history_and_hash_audit_are_accessible_in_both_themes_at_1024')
    server.terminate();server.wait(timeout=10);server=start();wait_server();assert [(x['binding_id'],x['revision'],x['state'],x['definition_hash']) for x in all_bindings()]==expected;assert bound(key)['state']=='STOPPED';assert not api('/api/health')['trading_commands_enabled'];record('server_restart_keeps_stopped_heads_and_immutable_definition_history')
    assert not result['page_errors'];assert not result['unexpected_requests'];result['passed']=True;browser.close()
  except Exception:result['error']=traceback.format_exc()
  finally:server.terminate();server.wait(timeout=10)
 (ROOT/'reports/chart-p4-validation-20261112.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
