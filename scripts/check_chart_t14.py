"""T14: production UI, native chart, real configuration HTTP/SQLite, isolated market."""
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
 result=dict(task='T14',passed=False,checks=[],page_errors=[],unexpected_requests=[],scope='Production App, synthetic market, isolated SQLite; no account/order access')
 def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
 with tempfile.TemporaryDirectory(prefix='agentrader-t14-') as folder:
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
    def head(key):return api('/api/drawings/'+key+'?format_version=8')
    def create(label,symbol='BTCUSDT',price='120'):
     return api('/api/workspaces/main/drawings?format_version=8',dict(request_id='seed-'+label.encode('utf-8').hex(),geometry=dict(kind='horizontal',symbol=symbol,price_source='LAST_PRICE',label=label,anchors=[dict(time=rows('15m')[220]['time'],price=price)])),'POST')
    def style(item,color=None,width=1,locked=False):
     m={**item['management'],'color':color,'line_width':width,'line_style':'dashed' if width==3 else 'default','locked':locked}
     return api('/api/workspaces/main/drawing-operations?format_version=8',dict(request_id='style-'+item['drawing_id'],operations=[dict(drawing_id=item['drawing_id'],expected_revision=item['revision'],geometry=item['geometry'],management=m,deleted=False)]),'POST')['drawings'][0]
    a=style(create('Örnek stil'),'#9b6ed6',3);b=create('Toplu hedef');locked=style(create('Kilitli hedef'),locked=True);other=create('ETH hedef','ETHUSDT','250')
    indicator=api('/api/workspaces/main/indicators');indicator['indicators'][8]['params'].update(anchor_time=rows('15m')[200]['time'],anchor_symbol='BTCUSDT');api('/api/workspaces/main/indicators',dict(request_id='seed-anchor',expected_revision=0,indicators=indicator['indicators']))
    def templates():p.get_by_label('Çalışma alanı şablonları',exact=True).click();p.get_by_role('dialog').wait_for()
    def close():p.get_by_label('Şablonları kapat',exact=True).click()
    def action(name,path,method='PUT'):
     with p.expect_response(lambda r:r.request.method==method and path in r.url) as response:p.get_by_role('dialog').get_by_role('button',name=name,exact=True).click()
     p.wait_for_timeout(180);return response.value
    def choose(key,version):
     p.get_by_label('Kayıtlı şablon',exact=True).select_option(key);p.get_by_role('button',name='Seçili sürümü uygula',exact=True).wait_for();p.wait_for_timeout(100)
     p.get_by_label('Şablon sürümü',exact=True).select_option(str(version));p.wait_for_timeout(160);p.get_by_role('button',name='Seçili sürümü uygula',exact=True).wait_for()
    def pick(label):p.locator('.drawing-list button').filter(has=p.get_by_text(label,exact=True)).click()
    def weights():return read("({price:series.getPane().getStretchFactor(),volume:chart.panes().flatMap(p=>p.getSeries()).find(s=>s.seriesType()==='Histogram').getPane().getStretchFactor(),rsi:chart.panes().flatMap(p=>p.getSeries()).find(s=>s.options().title.startsWith('RSI')).getPane().getStretchFactor()})")
    p.goto(base);feed();settings();p.get_by_label('ema-fast periyot',exact=True).fill('9');p.get_by_label('rsi-main periyot',exact=True).fill('7')
    for index in [0,1,2]:p.get_by_role('dialog').get_by_role('checkbox').nth(index).check()
    assert save().status==200
    box=p.locator('.chart-host').bounding_box();height=read('chart.panes()[0].getHeight()');p.mouse.move(box['x']+140,box['y']+height+1);p.mouse.down();p.mouse.move(box['x']+140,box['y']+height-45,steps=8);p.mouse.up();p.wait_for_timeout(180);assert abs(read('chart.panes()[0].getHeight()')-height)>20;original_weights=weights()
    p.get_by_label('Çizimleri göster veya gizle',exact=True).click();pick('Örnek stil');templates();assert action('Seçili aracı varsayılan yap','/profile').status==200;assert action('Çalışma alanını kaydet','/profile').status==200;profile=api('/api/workspaces/main/profile');assert profile['body']['drawing_defaults']['horizontal']['style']['line_width']==3
    for key,value in original_weights.items():assert abs(profile['body']['view']['pane_weights'][key]-value)<1e-8
    record('workspace_profile_saves_real_separator_ratios_and_safe_tool_defaults')
    p.get_by_label('Şablon adı',exact=True).fill('Araştırma düzeni');response=action('Yeni şablon kaydet','/templates/');assert response.status==200;template_id=response.json()['template_id'];one=api('/api/workspaces/main/templates/'+template_id+'?revision=1');assert one['body']['indicators'][8]['params']['anchor_time']==0;assert all(c['revision']==0 for c in one['body']['indicators']);record('portable_named_version_captures_settings_without_anchor_or_revision_transfer');close()
    before_ids={d['drawing_id'] for d in listing()};p.get_by_label('Çizgi araçları',exact=True).click();p.get_by_label('Çizgi araçları',exact=True).locator('..').get_by_role('button',name='Yatay çizgi',exact=True).click();point=read('({x:chart.timeScale().logicalToCoordinate(220),y:series.priceToCoordinate(124)})');box=p.locator('.chart-host').bounding_box()
    with p.expect_response(lambda r:r.request.method=='POST' and '/drawing-operations' in r.url):p.mouse.click(box['x']+point['x'],box['y']+point['y'])
    p.wait_for_timeout(180);added=[d for d in listing() if d['drawing_id'] not in before_ids];assert len(added)==1;assert added[0]['management']['color']=='#9b6ed6' and added[0]['management']['line_width']==3;assert not added[0]['management']['locked'];assert added[0]['management']['intervals']==[];record('actual_new_pointer_drawing_uses_saved_style_without_lock_visibility_or_anchor_copy')
    pick('Örnek stil')
    with p.expect_response(lambda r:r.request.method=='POST' and '/drawing-operations' in r.url):p.get_by_label('Çizgi rengi',exact=True).select_option('#d95656')
    p.wait_for_timeout(160);p.get_by_label('Açık temaya geç',exact=True).click();menu('Paneller','Hacim paneli');settings();p.get_by_label('ema-fast periyot',exact=True).fill('14');assert save().status==200;templates();assert action('Seçili aracı varsayılan yap','/profile').status==200;choose(template_id,1);p.get_by_label('Şablon adı',exact=True).fill('İkinci düzen');assert action('Yeni sürüm kaydet','/templates/').status==200;assert api('/api/workspaces/main/templates/'+template_id)['revision']==2;assert api('/api/workspaces/main/templates/'+template_id+'?revision=1')==one;record('second_version_is_immutable_and_first_version_remains_selectable')
    choose(template_id,1);p.get_by_role('checkbox',name='Mevcut görünür çizimlere stilleri uygula',exact=True).check();before_geometry={d['drawing_id']:d['geometry'] for d in listing()};response=action('Seçili sürümü uygula','/template-restore','POST');assert response.status==200;restored=response.json();assert b['drawing_id'] in restored['changed_drawings'];assert locked['drawing_id'] in restored['skipped_drawings'];assert not restored['order_authority'];assert api('/api/workspaces/main/indicators')['indicators'][0]['period']==9;assert api('/api/workspaces/main/indicators')['indicators'][8]['params']['anchor_time']==indicator['indicators'][8]['params']['anchor_time'];assert p.locator('.terminal').get_attribute('data-theme')=='dark';assert read('chart.panes().length')==3
    for key,value in original_weights.items():assert abs(weights()[key]-value)<1e-6,(key,weights(),original_weights)
    assert {d['drawing_id']:d['geometry'] for d in listing()}==before_geometry;assert head(locked['drawing_id'])['revision']==locked['revision'];assert head(other['drawing_id'])['revision']==other['revision'];assert head(b['drawing_id'])['management']['color']=='#9b6ed6';record('atomic_bulk_restore_reinstates_indicators_theme_ratios_and_unlocked_styles_preserving_geometry_and_lock')
    for cycle in range(3):
     choose(template_id,2);assert action('Seçili sürümü uygula','/template-restore','POST').status==200;assert p.locator('.terminal').get_attribute('data-theme')=='light'
     choose(template_id,1);assert action('Seçili sürümü uygula','/template-restore','POST').status==200
     for key,value in original_weights.items():assert abs(weights()[key]-value)<1e-6,(key,weights(),original_weights)
    record('repeated_alternating_versions_restore_saved_native_pane_ratios_without_async_reset');close()
    btc_before={d['drawing_id']:d['revision'] for d in listing()};p.get_by_label('Sözleşme seç',exact=True).select_option('ETHUSDT');p.get_by_role('group',name='Zaman dilimi',exact=True).get_by_role('button',name='5 dk',exact=True).click();feed('ETHUSDT','5m');templates();choose(template_id,1);p.get_by_role('checkbox',name='Mevcut görünür çizimlere stilleri uygula',exact=True).check();response=action('Seçili sürümü uygula','/template-restore','POST');assert response.status==200 and response.json()['symbol']=='ETHUSDT' and response.json()['interval']=='5m';assert p.get_by_label('Sözleşme seç',exact=True).input_value()=='ETHUSDT';assert {d['drawing_id']:d['revision'] for d in listing()}==btc_before;assert head(other['drawing_id'])['geometry']==other['geometry'];record('restoring_btc_captured_settings_on_eth_changes_only_current_symbol_styles_and_keeps_market_interval')
    concurrent=api('/api/workspaces/main/indicators');concurrent['indicators'][0]['period']=33;api('/api/workspaces/main/indicators',dict(request_id='other-screen',expected_revision=concurrent['revision'],indicators=concurrent['indicators']));before_profile=api('/api/workspaces/main/profile');before_drawing=head(other['drawing_id']);assert action('Seçili sürümü uygula','/template-restore','POST').status==409;assert 'başka bir ekranda' in p.get_by_role('dialog').inner_text();assert api('/api/workspaces/main/profile')==before_profile;assert head(other['drawing_id'])==before_drawing;record('concurrent_indicator_revision_conflict_leaves_profile_and_drawings_unchanged');p.get_by_role('button',name='Son kayıtları yükle',exact=True).click();p.get_by_text('Son kayıtlar yüklendi.',exact=True).wait_for()
    def lost_restore(route):
     response=route.fetch();assert response.status==200;route.fulfill(status=503,json={'error':{'code':'SIMULATED_LOST_ACK'}})
    p.route('**/template-restore',lost_restore);assert action('Seçili sürümü uygula','/template-restore','POST').status==503;committed=api('/api/workspaces/main/profile')['revision'];p.unroute('**/template-restore',lost_restore);response=action('Seçili sürümü uygula','/template-restore','POST');assert response.status==200 and response.json()['duplicate'];assert api('/api/workspaces/main/profile')['revision']==committed;record('lost_atomic_restore_ack_retries_same_request_without_duplicate_revision')
    p.get_by_label('Şablon adı',exact=True).fill('Kayıp yanıt denemesi')
    def lost_template(route):
     if route.request.method=='PUT':
      response=route.fetch();assert response.status==200;route.fulfill(status=503,json={'error':{'code':'SIMULATED_LOST_ACK'}})
     else:route.continue_()
    p.route('**/templates/*',lost_template);assert action('Yeni şablon kaydet','/templates/').status==503;count=len(api('/api/workspaces/main/templates')['templates']);p.unroute('**/templates/*',lost_template);response=action('Yeni şablon kaydet','/templates/');assert response.status==200 and response.json()['duplicate'];assert len(api('/api/workspaces/main/templates')['templates'])==count;record('lost_new_template_ack_reuses_template_identity_and_request_id')
    choose(template_id,1);held=[]
    def delay_restore(route):held.append((route,route.fetch()))
    p.route('**/template-restore',delay_restore);p.get_by_role('button',name='Seçili sürümü uygula',exact=True).click()
    for _ in range(50):
     if held:break
     p.wait_for_timeout(50)
    assert held;p.get_by_label('Sözleşme seç',exact=True).select_option('BTCUSDT',force=True);feed('BTCUSDT','5m');held[0][0].fulfill(response=held[0][1]);p.get_by_text('Grafik bağlamı değişti. Son çalışma alanı kaydını yükle.',exact=True).wait_for();assert p.get_by_label('Sözleşme seç',exact=True).input_value()=='BTCUSDT';assert {d['drawing_id']:d['revision'] for d in listing()}==btc_before;assert p.locator('.drawing-tools button[aria-label="Yatay çizgi"]').is_disabled();p.unroute('**/template-restore',delay_restore);record('late_restore_response_cannot_publish_into_changed_market_and_blocks_unverified_creation');p.get_by_role('button',name='Son kayıtları yükle',exact=True).click();p.get_by_text('Son kayıtlar yüklendi.',exact=True).wait_for();close()
    p.wait_for_timeout(600);expected_profile=api('/api/workspaces/main/profile');expected_indicators=api('/api/workspaces/main/indicators');sockets.clear();p.reload();feed('BTCUSDT','5m');assert api('/api/workspaces/main/profile')==expected_profile;assert api('/api/workspaces/main/indicators')==expected_indicators;assert read('chart.panes().length')==3;record('page_reload_bootstraps_saved_profile_indicators_and_legacy_symbol_interval_preferences')
    read('(series.getPane().setStretchFactor(8),true)');p.get_by_label('Açık temaya geç',exact=True).click();templates();p.get_by_role('button',name='Son kayıtları yükle',exact=True).click();p.get_by_text('Son kayıtlar yüklendi.',exact=True).wait_for();p.wait_for_timeout(160);assert p.locator('.terminal').get_attribute('data-theme')=='dark'
    for key,value in expected_profile['body']['view']['pane_weights'].items():
     if key in weights():assert abs(weights()[key]-value)<1e-6
    record('explicit_reload_reapplies_saved_view_even_when_profile_revision_is_unchanged');close()
    templates();choose(template_id,1);p.screenshot(path=str(ROOT/'reports/chart-t14-dark-20261112.png'));close();p.get_by_label('Açık temaya geç',exact=True).click();p.set_viewport_size({'width':1024,'height':768});assert p.get_by_label('Çalışma alanı şablonları',exact=True).is_visible();templates();choose(template_id,1);assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');p.screenshot(path=str(ROOT/'reports/chart-t14-light-20261112.png'));close();record('template_access_preview_and_version_controls_work_in_both_themes_and_1024_layout')
    server.terminate();server.wait(timeout=10);server=start();wait_server();assert api('/api/workspaces/main/profile')==expected_profile;assert api('/api/workspaces/main/indicators')==expected_indicators;assert api('/api/workspaces/main/templates/'+template_id+'?revision=1')==one;record('server_restart_keeps_template_versions_profile_and_settings')
    assert not result['page_errors'];assert not result['unexpected_requests'];assert not api('/api/health')['trading_commands_enabled'];result['passed']=True;browser.close()
  except Exception:result['error']=traceback.format_exc()
  finally:server.terminate();server.wait(timeout=10)
 (ROOT/'reports/chart-t14-validation-20261112.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
