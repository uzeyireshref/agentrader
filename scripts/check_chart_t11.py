"""T11: production UI, native chart, real configuration HTTP/SQLite, isolated market."""
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
 result=dict(task='T11',passed=False,checks=[],page_errors=[],unexpected_requests=[],scope='Production App, synthetic market, isolated SQLite; no account/order access')
 def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
 with tempfile.TemporaryDirectory(prefix='agentrader-t11-') as folder:
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  base=f'http://127.0.0.1:{port}';opener=build_opener(ProxyHandler({}));env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(Path(folder)/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(Path(folder)/'execution.db'),AGENTRADER_CHART_DATABASE=str(Path(folder)/'market.db'),AGENTRADER_WEB_TOKEN='')
  def start():return subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  server=start()
  def api(path,body=None):
   if path.endswith('/indicators'):path+='?format_version=4'
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
    def verify(interval='15m',data=None):
     data=rows(interval) if data is None else data
     all_series=read("chart.panes().flatMap(p=>p.getSeries()).filter(s=>s.seriesType()==='Line'||s.options().title==='MACD Histogram').map(s=>({title:s.options().title,data:s.data(),type:s.seriesType()}))");items=api('/api/workspaces/main/indicators')['indicators'];enabled=[c for c in items if c['enabled']];expected=[]
     for c in enabled:
      if c['kind'] in ('SESSION_VWAP','ANCHORED_VWAP'):
       expected.append(('Seans VWAP' if c['kind']=='SESSION_VWAP' else 'Anchored VWAP',vwap_series(data,c,interval,active_symbol[0])['points'],c))
      elif c['kind'] in ('MACD','BB'):
       multi=multi_series(data,c,interval)
       titles={'macd':'MACD','signal':'MACD Sinyal','histogram':'MACD Histogram'} if c['kind']=='MACD' else {'basis':'BB Orta','upper':'BB Üst','lower':'BB Alt'}
       expected.extend((titles[key],points,c) for key,points in multi.items())
      else:expected.append((c['kind']+' '+str(c['period']),reference(data,c,interval),c))
     assert len(all_series)==len(expected),(len(all_series),len(expected))
     for title,points,c in expected:
      a=next(x for x in all_series if x['title']==title);assert len(a['data'])==len(points),(title,len(a['data']),len(points))
      for i,(actual,wanted) in enumerate(zip(a['data'],points)):
       assert actual['time']==wanted['time'],(title,actual,wanted)
       if 'value' not in wanted:assert 'value' not in actual,(title,actual,wanted)
       else:assert abs(actual['value']-wanted['value'])<1e-9,(title,actual,wanted)
       if title=='MACD Histogram':
        value=wanted['value'];previous=points[i-1]['value'] if i else 0;key=('positive_' if value>=0 else 'negative_')+('rising' if value>=previous else 'falling');assert actual['color']==c['style']['colors'][key]
    def value(output):return p.locator('[data-output-id="'+output+'"] dd').inner_text()
    def anchor_action():
     with p.expect_response(lambda r:r.request.method=='PUT' and urlparse(r.url).path.endswith('/indicators')):p.get_by_role('button',name='Seçili mumdan Anchored VWAP',exact=True).click()
     p.wait_for_timeout(120)
    def utc(t):return datetime.fromtimestamp(t,timezone.utc).strftime('%Y-%m-%dT%H:%M')
    def switch(symbol,interval,data):
     p.get_by_label('Sözleşme seç',exact=True).select_option(symbol)
     label={'15m':'15 dk','5m':'5 dk','1w':'1 hf'}[interval];p.get_by_role('group',name='Zaman dilimi',exact=True).get_by_role('button',name=label,exact=True).click();feed(symbol,interval,data)
    p.goto(base);feed();settings();assert p.get_by_label('session-vwap hesap kaynağı',exact=True).input_value()=='BAR_PRICE_VOLUME';assert p.get_by_label('anchored-vwap UTC çapa',exact=True).input_value()=='';record('nine_config_defaults_keep_vwap_disabled_and_anchor_unset')
    checks=p.get_by_role('dialog').get_by_role('checkbox');checks.nth(0).check();checks.nth(1).check();checks.nth(2).check();checks.nth(7).check();checks.nth(8).check();assert save().status==200;verify();p.get_by_label('Veri penceresini göster veya gizle',exact=True).click();assert value('anchored-vwap:value')=='Önce bir çapa mumu seç';assert 'ham base hacmi' in p.locator('.data-window').inner_text();record('native_plot_whitespace_and_data_window_explain_unset_anchor_and_raw_source')
    anchor_action();head=api('/api/workspaces/main/indicators');assert head['indicators'][8]['params']['anchor_time']==rows('15m')[-1]['time'];assert head['indicators'][8]['params']['anchor_symbol']=='BTCUSDT';verify();record('selected_candle_action_persists_symbol_and_exact_utc_bar_anchor')
    chosen=rows('15m')[100]['time'];settings();p.get_by_label('anchored-vwap UTC çapa',exact=True).fill(utc(chosen));assert save().status==200;assert api('/api/workspaces/main/indicators')['indicators'][8]['params']['anchor_time']==chosen;verify();assert p.evaluate('Intl.DateTimeFormat().resolvedOptions().timeZone')=='America/New_York';record('utc_anchor_form_roundtrips_independently_of_browser_dst_timezone')
    settings();p.get_by_label('anchored-vwap UTC çapa',exact=True).fill(utc(chosen+60));assert save().status==200;assert value('anchored-vwap:value')=='Çapa bu zaman diliminin mum başlangıcında değil';record('unaligned_anchor_is_explicitly_unavailable_without_silent_snapping')
    settings();p.get_by_label('anchored-vwap UTC çapa',exact=True).fill(utc(chosen));assert save().status==200
    session_start=(rows('5m')[-1]['time']//86400+1)*86400
    def session_rows(count=20):
     out=[]
     for i in range(count):
      price=100+math.sin(i*.5)*5+i*.1;v=0 if i<3 else 10+i;t=session_start+i*300;q=price*v
      out.append(dict(time=t,close_time=(t+300)*1000-1,closed=i<count-1,open=price,high=price+2,low=price-1,close=price,volume=v,quote_volume=q,exact=dict(schema='chart-exact-decimal/1',state='VERIFIED',provenance='UPSTREAM_DECIMAL_TEXT',volume=str(v),quote_volume=str(q))))
     return out
    initial=session_rows(3);switch('ETHUSDT','5m',initial);assert value('session-vwap:value')=='Birikimli hacim sıfır';assert value('anchored-vwap:value')=='Çapa başka bir sembole ait';verify('5m',initial);record('new_utc_session_zero_volume_and_other_symbol_anchor_never_publish_zero')
    current=session_rows(20);feed('ETHUSDT','5m',current);verify('5m',current);assert value('session-vwap:value') not in ['Birikimli hacim sıfır','—'];anchor_action();assert api('/api/workspaces/main/indicators')['indicators'][8]['params']['anchor_symbol']=='ETHUSDT';verify('5m',current);record('positive_volume_starts_session_and_explicit_anchor_rebinds_new_symbol')
    settings();p.get_by_label('anchored-vwap UTC çapa',exact=True).fill(utc(session_start));assert save().status==200;verify('5m',current)
    extra={**current[-1],'time':session_start+20*300,'close_time':(session_start+21*300)*1000-1,'volume':0,'quote_volume':0,'exact':dict(schema='chart-exact-decimal/1',state='VERIFIED',provenance='UPSTREAM_DECIMAL_TEXT',volume='0',quote_volume='0')};current[-1]['closed']=True;current.append(extra);before=value('session-vwap:value');feed('ETHUSDT','5m',current);verify('5m',current);assert value('session-vwap:value')==before;record('zero_volume_after_positive_total_preserves_both_weighted_means')
    settings();p.get_by_label('session-vwap hesap kaynağı',exact=True).select_option('EXACT_QUOTE_BASE');p.get_by_label('anchored-vwap hesap kaynağı',exact=True).select_option('EXACT_QUOTE_BASE');assert save().status==200;verify('5m',current);assert 'Doğrulanmış ham decimal quote/base oranı' in p.locator('.data-window').inner_text();assert 'gerçek trade VWAP iddiası yok' in p.locator('.data-window').inner_text();record('exact_quote_base_selection_uses_native_decimal_provenance_without_trade_claim')
    bad=json.loads(json.dumps(current));bad[5]['exact']['state']='UNPROVEN';feed('ETHUSDT','5m',bad);verify('5m',bad);assert value('session-vwap:value')=='Exact quote/base hacmi doğrulanamadı';assert value('anchored-vwap:value')=='Exact quote/base hacmi doğrulanamadı';assert read("chart.panes()[0].getSeries().find(s=>s.options().title==='Seans VWAP').data().at(-1).color")=='rgba(0, 0, 0, 0)';record('unproven_native_volume_clears_plot_tail_without_hlc3_fallback')
    feed('ETHUSDT','5m',current);verify('5m',current);record('repaired_decimal_evidence_restores_exact_outputs')
    settings();p.get_by_label('anchored-vwap UTC çapa',exact=True).fill(utc(session_start-300));assert save().status==200;assert value('anchored-vwap:value')=='Çapaya kadar eski mumları yükle';record('saved_anchor_before_loaded_history_is_unavailable_until_history_arrives')
    older={**current[3],'time':session_start-300,'close_time':session_start*1000-1,'closed':True};history_route=lambda r:r.fulfill(json={'candles':[older],'has_more':False});p.route('**/api/candles*',history_route)
    pending=[r for r in history_wait if parse_qs(urlparse(r.request.url).query).get('symbol')==['ETHUSDT'] and parse_qs(urlparse(r.request.url).query).get('end_time')==[str(session_start*1000-1)]]
    if pending:
     with p.expect_response(lambda r:r.url==pending[-1].request.url):pending[-1].fulfill(json={'candles':[older],'has_more':False})
    else:
     with p.expect_response(lambda r:'/api/candles?' in r.url):p.get_by_role('button',name='Eski mumları yükle',exact=True).click()
    current=[older]+current;p.get_by_text(str(len(current))+' mum',exact=True).wait_for();p.wait_for_timeout(150);verify('5m',current);assert value('anchored-vwap:value')!='Çapaya kadar eski mumları yükle';record('real_history_pagination_restores_anchor_accumulation_from_saved_start')
    count=len(sockets);sockets[-1].close(code=1012,reason='T11 controlled reconnect')
    for _ in range(100):
     if len(sockets)>count:break
     p.wait_for_timeout(50)
    assert len(sockets)==count+1;feed('ETHUSDT','5m',current);verify('5m',current);record('same_page_websocket_reconnect_reseeds_without_double_counting_volume')
    for cycle in range(20):
     for kind in ['SESSION_VWAP','ANCHORED_VWAP']:
      with p.expect_response(lambda r:r.request.method=='PUT' and urlparse(r.url).path.endswith('/indicators')):menu('Göstergeler',kind+' göstergesi')
      p.wait_for_timeout(30)
     assert read("chart.panes().flatMap(p=>p.getSeries()).filter(s=>s.options().title.includes('VWAP')).length")==0
     for kind in ['SESSION_VWAP','ANCHORED_VWAP']:
      with p.expect_response(lambda r:r.request.method=='PUT' and urlparse(r.url).path.endswith('/indicators')):menu('Göstergeler',kind+' göstergesi')
      p.wait_for_timeout(30)
     assert read("chart.panes()[0].getSeries().filter(s=>s.options().title.includes('VWAP')).length")==2
    verify('5m',current);record('twenty_dual_vwap_visibility_cycles_keep_two_price_owned_series_without_volume_drift')
    settings();p.get_by_label('session-vwap value renk',exact=True).fill('#ddaa55');p.get_by_label('anchored-vwap çizgi kalınlığı',exact=True).select_option('3');assert save().status==200;assert read("chart.panes()[0].getSeries().find(s=>s.options().title==='Seans VWAP').options().color")=='#ddaa55';record('vwap_color_and_width_style_persist_and_apply_to_native_series')
    p.wait_for_timeout(600);expected=api('/api/workspaces/main/indicators');sockets.clear();p.reload();feed('ETHUSDT','5m',current);verify('5m',current);assert api('/api/workspaces/main/indicators')==expected;record('page_reload_restores_anchor_symbol_sources_styles_and_revisions')
    p.get_by_label('Veri penceresini göster veya gizle',exact=True).click();read('(chart.timeScale().fitContent(),true)');p.screenshot(path=str(ROOT/'reports/chart-t11-dark-20261112.png'));settings();p.set_viewport_size({'width':1024,'height':768});p.get_by_label('anchored-vwap UTC çapa',exact=True).scroll_into_view_if_needed();assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');p.screenshot(path=str(ROOT/'reports/chart-t11-settings-dark-20261112.png'));p.keyboard.press('Escape');p.get_by_label('Açık temaya geç').click();settings();p.get_by_label('session-vwap hesap kaynağı',exact=True).scroll_into_view_if_needed();p.screenshot(path=str(ROOT/'reports/chart-t11-settings-light-20261112.png'));p.keyboard.press('Escape');record('utc_anchor_and_source_forms_are_keyboard_accessible_at_1024_in_both_themes')
    server.terminate();server.wait(timeout=10);server=start();wait_server();assert api('/api/workspaces/main/indicators')==expected;record('server_restart_preserves_vwap_configuration_without_exchange_execution')
    assert not result['page_errors'];assert not result['unexpected_requests'];assert not api('/api/health')['trading_commands_enabled'];result['passed']=True;browser.close()
  except Exception:result['error']=traceback.format_exc()
  finally:server.terminate();server.wait(timeout=10)
 (ROOT/'reports/chart-t11-validation-20261112.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
