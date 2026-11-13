"""T08 production UI with synthetic public market and isolated workspace."""
import json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from urllib.request import build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
 result=dict(task='T08',passed=False,checks=[],page_errors=[],private_requests=[])
 def record(name):result['checks'].append(dict(name=name,passed=True))
 with tempfile.TemporaryDirectory(prefix='agentrader-t08-') as folder:
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  base=f'http://127.0.0.1:{port}';env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(Path(folder)/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(Path(folder)/'execution.db'),AGENTRADER_CHART_DATABASE=str(Path(folder)/'market.db'),AGENTRADER_WEB_TOKEN='')
  server=subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  try:
   opener=build_opener(ProxyHandler({}))
   for _ in range(100):
    try:
     with opener.open(base+'/api/health',timeout=2) as r:health=json.load(r)
     break
    except Exception:time.sleep(.1)
   assert not health['trading_commands_enabled']
   steps={'1m':60,'5m':300,'15m':900,'30m':1800,'1h':3600,'4h':14400,'1d':86400,'1w':604800};labels={'1m':'1 dk','5m':'5 dk','30m':'30 dk','1w':'1 hf'};sockets=[];calls=[];bad=[False]
   market=dict(symbol='BTCUSDT',base_asset='BTC',quote_asset='USDT',contract_type='PERPETUAL',tick_size='0.25')
   def rows(interval):
    step=steps[interval];anchor=345600 if interval=='1w' else 0;end=(1800000000-anchor)//step*step+anchor
    return [dict(time=end-(299-i)*step,open=100,high=110,low=90,close=105,volume=10,quote_volume=1050,close_time=(end-(298-i)*step)*1000-1,closed=i<299) for i in range(300)]
   with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True);p=browser.new_page(viewport={'width':1536,'height':900});p.set_default_timeout(7000);p.on('pageerror',lambda e:result['page_errors'].append(str(e)))
    def guard(route):
     if not route.request.url.startswith(base+'/') or any(x in route.request.url for x in ['/api/orders','/api/account','/api/commands','/api/execution']):result['private_requests'].append(route.request.url);route.abort()
     else:route.continue_()
    def higher(route):
     q={k:v[0] for k,v in parse_qs(urlparse(route.request.url).query).items()};calls.append(q);ref=int(q['reference_time']);step=steps[q['interval']]*1000;anchor=345600000 if q['interval']=='1w' else 0;t=(ref-anchor)//step*step+anchor-step;c=dict(time=t//1000,close_time=t+step-1,closed=not bad[0],open=200,high=220,low=190,close=210,volume=20,quote_volume=4200,exact={'state':'VERIFIED'})
     route.fulfill(json=dict(schema='chart-higher-context/1',symbol=q['symbol'],base_interval=q['base_interval'],interval=q['interval'],requested_reference_time=ref,effective_reference_time=ref,state='READY',reason=None,candle=c,source='binance_usdm_live_trade_price',environment='live_public',product='USD-M',price_type='LAST_PRICE',provenance='BINANCE_NATIVE_KLINE',resampled=False,server_time=ref+10,clock_state='MEASURED',clock_uncertainty_ms=1,precision={'state':'VERIFIED'},live_eligible=False,order_authority=False))
    p.route('**/*',guard);p.route('**/api/markets',lambda r:r.fulfill(json={'markets':[market]}));p.route('**/api/candles*',lambda r:r.fulfill(json={'candles':[],'has_more':False}));p.route('**/api/higher-context*',higher);p.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
    def feed(interval):
     for _ in range(100):
      matching=[w for w in sockets if parse_qs(urlparse(w.url).query).get('interval')==[interval]]
      if matching:break
      p.wait_for_timeout(50)
     assert matching,interval
     matching[-1].send(json.dumps(dict(type='snapshot',symbol='BTCUSDT',interval=interval,generation=1,sequence=1,status='LIVE',received_at=int(time.time()*1000),market=market,quality={'state':'OK','missing_bars':0},candles=rows(interval))));p.wait_for_timeout(150);p.get_by_text('300 mum',exact=True).wait_for()
    p.goto(base);feed('15m');assert not calls;record('higher_context_is_opt_in_no_background_requests')
    for interval in ['1m','5m','30m']:
     p.get_by_role('group',name='Zaman dilimi',exact=True).get_by_role('button',name=labels[interval],exact=True).click();feed(interval);assert p.locator('.shell-instrument').inner_text().find(labels[interval])>=0;record(interval+'_production_selector_and_stream_context')
    p.get_by_label('Veri penceresini göster veya gizle',exact=True).click();p.locator('.higher-details summary').click();p.locator('.higher-timeframe time').wait_for();assert calls[-1]['reference_time']==str(rows('30m')[-1]['time']*1000);assert 'Yeniden örnekleme yok' in p.locator('.higher-timeframe').inner_text();record('native_upper_context_uses_open_base_start_and_explicit_provenance')
    p.get_by_label('Üst zaman dilimi',exact=True).select_option('4h');p.locator('.higher-timeframe time').wait_for();assert calls[-1]['interval']=='4h';record('higher_selection_reloads_matching_native_context')
    bad[0]=True;p.get_by_role('button',name='Üst zamanı yenile',exact=True).click();p.get_by_text('Üst zaman yanıtının bağlamı doğrulanamadı.',exact=True).wait_for();assert p.locator('.higher-timeframe time').count()==0;record('malformed_open_upper_response_removes_old_values')
    bad[0]=False;p.get_by_role('button',name='Üst zamanı yenile',exact=True).click();p.locator('.higher-timeframe time').wait_for();record('explicit_retry_restores_verified_context')
    p.screenshot(path=str(ROOT/'reports/chart-t08-dark-20261112.png'));p.get_by_label('Açık temaya geç').click();p.screenshot(path=str(ROOT/'reports/chart-t08-light-20261112.png'))
    p.set_viewport_size({'width':1024,'height':768});assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');record('eight_interval_header_has_no_document_overflow_at_1024')
    p.get_by_role('group',name='Zaman dilimi',exact=True).get_by_role('button',name='1 hf',exact=True).click();feed('1w');p.locator('.higher-details summary').click();p.get_by_text('Bu aralığın üzerinde desteklenen bir zaman dilimi yok.',exact=True).wait_for();record('weekly_base_has_explicit_no_higher_interval')
    assert not result['page_errors'];assert not result['private_requests'];result['passed']=True;browser.close()
  except Exception:result['error']=traceback.format_exc()
  finally:server.terminate();server.wait(timeout=10)
 (ROOT/'reports/chart-t08-validation-20261112.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
