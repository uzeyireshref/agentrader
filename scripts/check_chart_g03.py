"""G03 real App: pinned data, independently delayed reads, stale/race/paint recovery."""
import json,math,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
from measure_chart_interactions import INSPECT,ROOT

def main():
    result={'task':'G03','passed':False,'checks':[],'page_errors':[],'unexpected_requests':[], 'scope':'Real production App, controlled stream/read order and isolated SQLite; no live exchange parity'}
    with tempfile.TemporaryDirectory(prefix='agentrader-g03-') as folder:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}';opener=build_opener(ProxyHandler({}));env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(Path(folder)/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(Path(folder)/'execution.db'),AGENTRADER_CHART_DATABASE=str(Path(folder)/'market.db'),AGENTRADER_WEB_TOKEN='')
        server=subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def api(path,body=None):
            req=Request(base+path,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json'})
            with opener.open(req,timeout=5) as r:return json.load(r)
        def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
        try:
            for _ in range(100):
                try:api('/api/health');break
                except Exception:time.sleep(.1)
            markets=[dict(symbol=b+'USDT',base_asset=b,quote_asset='USDT',contract_type='PERPETUAL',tick_size='0.25') for b in ['BTC','ETH']]
            seeds={m['symbol']:api('/api/workspaces/main/drawings',{'request_id':'g03-'+m['symbol'],'geometry':{'kind':'horizontal','symbol':m['symbol'],'price_source':'LAST_PRICE','anchors':[{'time':1794283200,'price':'74100.00' if m['base_asset']=='BTC' else '2100.00'}],'label':m['base_asset']+' kayıtlı'}}) for m in markets}
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True);context=browser.new_context(viewport={'width':1536,'height':776},device_scale_factor=1.25);p=context.new_page();p.set_default_timeout(6000);sockets=[];pending=[];control={'hold':True,'fail':False,'history_fail':False}
                p.on('pageerror',lambda e:result['page_errors'].append(str(e)))
                def guard(r):
                    if not r.request.url.startswith(base+'/'):result['unexpected_requests'].append(r.request.url);r.abort()
                    else:r.continue_()
                def drawings(r):
                    if control['hold']:pending.append((parse_qs(urlparse(r.request.url).query)['symbol'][0],r))
                    elif control['fail']:r.fulfill(status=503,json={'error':{'message':'Controlled read failure'}})
                    else:r.continue_()
                p.route('**/*',guard);p.route('**/api/markets',lambda r:r.fulfill(json={'markets':markets}));p.route('**/api/workspaces/main/drawings?*',drawings);p.route('**/api/candles*',lambda r:r.fulfill(status=503,json={}) if control['history_fail'] else r.fulfill(json={'candles':[],'has_more':False}));p.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
                sequences={}
                def wait_socket(symbol='BTCUSDT',interval='15m'):
                    for _ in range(80):
                        if sockets and parse_qs(urlparse(sockets[-1].url).query).get('symbol')==[symbol] and parse_qs(urlparse(sockets[-1].url).query).get('interval')==[interval]:return sockets[-1]
                        p.wait_for_timeout(60)
                    raise AssertionError('Missing stream')
                def rows_for(symbol='BTCUSDT',interval='15m',count=300):
                    step=900 if interval=='15m' else 3600;start=1794085200 if interval=='15m' else 1794081600;out=[]
                    for i in range(count):
                        o=(71000 if symbol=='BTCUSDT' else 2000)+i*(11 if symbol=='BTCUSDT' else .5)+math.sin(i*.17)*20;c=o+math.sin(i)*3;t=start+i*step
                        out.append(dict(time=t,open=o,close=c,high=max(o,c)+10,low=min(o,c)-10,volume=0 if i==count-1 else 150+i,quote_volume=0 if i==count-1 else 10000,close_time=(t+step)*1000-1,closed=i<count-1))
                    return out
                def feed(symbol='BTCUSDT',interval='15m',status='LIVE',count=300,payload_symbol=None):
                    ws=wait_socket(symbol,interval);key=id(ws);sequences[key]=sequences.get(key,0)+1;rows=rows_for(symbol,interval,count);ws.send(json.dumps(dict(type='snapshot',symbol=payload_symbol or symbol,interval=interval,generation=1,sequence=sequences[key],status=status,received_at=int(time.time()*1000),market=next(m for m in markets if m['symbol']==symbol),quality={'state':'OK','missing_bars':0},candles=rows)));p.wait_for_timeout(160);return rows
                def release(symbol):
                    for _ in range(60):
                        hit=next(((i,r) for i,(s,r) in enumerate(pending) if s==symbol),None)
                        if hit:break
                        p.wait_for_timeout(50)
                    assert hit,'No held drawing read';pending.pop(hit[0]);hit[1].continue_();p.wait_for_timeout(160)
                def read(expr):return p.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');'+'}')
                def data():return p.get_by_role('region',name='Mum veri penceresi',exact=True)
                def value(label):return data().get_by_text(label+' · CLOSE' if label in ('EMA 20','EMA 50','RSI 14') else label,exact=True).locator('..').locator('dd').inner_text()
                p.goto(base);feed();p.get_by_label('Veri penceresini göster veya gizle').click();data().wait_for();assert value('Hacim')=='0,000';assert data().locator('[data-readiness="drawings"] dd').inner_text()=='Yükleniyor';assert p.get_by_label('Fiyat-zaman cetveli',exact=True).is_disabled();assert '0 çizim hazır' not in data().inner_text();record('market_ready_drawing_pending_is_not_empty_or_editable')
                release('BTCUSDT');assert data().locator('[data-readiness="drawings"] dd').inner_text()=='1 çizim hazır';assert not p.get_by_label('Fiyat-zaman cetveli',exact=True).is_disabled();record('independent_drawing_barrier_releases_after_current_read')
                assert 'Son mum' in data().locator('.data-selection').inner_text();assert 'Açık mum' in data().locator('.data-selection').inner_text();record('latest_candle_open_state_and_zero_volume_are_explicit')
                data().get_by_role('button',name='İmleci izle',exact=True).click();sample=rows_for()[250];point=read('({x:chart.timeScale().timeToCoordinate('+str(sample['time'])+'),y:series.priceToCoordinate('+str(sample['close'])+')})');box=p.locator('.chart-host').bounding_box();p.mouse.move(box['x']+point['x'],box['y']+point['y']);p.wait_for_timeout(120);assert 'Kapanmış mum' in data().locator('.data-selection').inner_text();stamp=data().locator('time').inner_text();data().get_by_role('button',name='Sabitle',exact=True).click();old=value('Kapanış');p.mouse.move(box['x']+point['x']+30,box['y']+point['y']);assert data().locator('time').inner_text()==stamp;assert value('Kapanış')==old;record('crosshair_pin_retains_timestamp_and_closed_state_across_pointer_exit')
                data().get_by_role('button',name='Son mum',exact=True).click();assert value('Kapanış')!=old;record('return_to_latest_is_explicit')
                p.get_by_label('Göstergeler',exact=True).click();p.get_by_role('button',name='EMA 20 / 50',exact=False).click();p.wait_for_timeout(200);assert value('EMA 20') not in ['Kapalı','—','Yetersiz geçmiş'];record('indicator_output_follows_same_selected_source_context')
                feed(status='STALE');assert data().locator('[data-readiness="market"] dd').inner_text()=='Veri gecikiyor';assert 'güncel olduğu doğrulanmadı' in data().inner_text();assert value('Kapanış')!='—';assert not p.locator('.shell-state').evaluate("e=>e.classList.contains('is-live')");record('stale_keeps_last_values_with_warning_not_live');feed()
                p.get_by_label('Sözleşme seç').select_option('ETHUSDT');wait_socket('ETHUSDT');assert value('Kapanış')=='—';assert data().locator('[data-selection-mode]').get_attribute('data-selection-mode')=='latest';feed('ETHUSDT',payload_symbol='BTCUSDT');assert value('Kapanış')=='—';feed('ETHUSDT');assert float(value('Kapanış').replace('.','').replace(',','.'))<10000;record('market_switch_and_wrong_source_packet_cannot_show_old_btc_values')
                p.get_by_label('Sözleşme seç').select_option('BTCUSDT');feed();release('ETHUSDT');assert 'ETH kayıtlı' not in p.locator('.drawings-overlay').text_content();assert data().locator('[data-readiness="drawings"] dd').inner_text()=='Yükleniyor';release('BTCUSDT');assert data().locator('[data-readiness="drawings"] dd').inner_text()=='1 çizim hazır';record('a_b_a_late_drawing_response_is_ignored')
                control.update(hold=False,fail=True);p.get_by_role('button',name='Çizimler',exact=True).click();p.get_by_role('button',name='Sunucudan yenile',exact=True).click();p.wait_for_timeout(200);p.get_by_role('button',name='Veri',exact=True).click();assert data().locator('[data-readiness="drawings"] dd').inner_text()=='Yüklenemedi';assert '0 çizim hazır' not in data().inner_text();control['fail']=False;data().get_by_role('button',name='Çizimleri yeniden yükle').click();p.wait_for_timeout(200);assert data().locator('[data-readiness="drawings"] dd').inner_text()=='1 çizim hazır';record('drawing_error_is_not_empty_and_explicit_reload_recovers')
                control['history_fail']=True;p.get_by_role('button',name='Eski mumları yükle',exact=True).click();p.wait_for_timeout(200);assert data().get_by_text('Geçmiş',exact=True).locator('..').locator('dd').inner_text()=='Yüklenemedi';assert value('Kapanış')!='—';record('history_failure_does_not_erase_current_candle')
                read("(window.__g03Paint={setData:series.setData.bind(series),update:series.update.bind(series)},series.setData=()=>{throw Error('Controlled paint failure')},series.update=()=>{throw Error('Controlled paint failure')},true)");feed();assert data().locator('[data-readiness="market"] dd').inner_text()=='Grafik güncellenemedi';assert value('Kapanış')=='—';assert value('EMA 20')=='Kullanılamıyor';read('(series.setData=window.__g03Paint.setData,series.update=window.__g03Paint.update,true)');feed();assert value('Kapanış')!='—';record('actual_series_paint_failure_blocks_readout_until_successful_repaint')
                p.get_by_role('button',name='1 sa',exact=True).click();feed(interval='1h',count=0);assert value('Kapanış')=='—';assert data().locator('[data-readiness="market"] dd').inner_text()!='Canlı';feed(interval='1h',count=10);assert value('EMA 20')=='Yetersiz geçmiş';record('empty_snapshot_and_indicator_warmup_are_not_numeric_zero');feed(interval='1h')
                for width,theme in [(1536,'dark'),(1024,'light')]:
                    p.set_viewport_size({'width':width,'height':776})
                    if p.locator('.terminal').get_attribute('data-theme')!=theme:p.get_by_label('Açık temaya geç' if theme=='light' else 'Koyu temaya geç').click()
                    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');p.locator('.shell-data').evaluate('(e)=>e.scrollTop=0');p.screenshot(path=str(ROOT/f'reports/chart-g03-{width}-{theme}.png'))
                record('data_panel_fits_two_desktop_widths_and_themes')
                assert api('/api/drawings/'+seeds['BTCUSDT']['drawing_id'])['revision']==1;assert api('/api/drawings/'+seeds['ETHUSDT']['drawing_id'])['revision']==1;assert not result['page_errors'];assert not result['unexpected_requests'];result['passed']=True;browser.close()
        except Exception:result['error']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-g03-validation-20261111.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
