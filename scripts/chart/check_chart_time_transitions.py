"""Isolated production UI regression for time transitions; no user stores."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import json,time
from datetime import datetime,timezone
from urllib.parse import parse_qs,urlparse
from playwright.sync_api import sync_playwright,expect
from scripts.chart.qa_chart_fixture import Fixture
from scripts.chart.demo_browser_fixture import fixture_response
ROOT=Path(__file__).resolve().parents[2]
STEPS={'1m':60,'5m':300,'15m':900,'30m':1800,'1h':3600,'4h':14400,'1d':86400,'1w':604800}
def main():
 f=Fixture();result=dict(passed=False,checks=[],page_errors=[],unexpected_requests=[]);pages=[]
 def dataset(iv):
  step=STEPS[iv];anchor=345600 if iv=='1w' else 0;end=(1800900000-anchor)//step*step+anchor;out=[]
  for i in range(4000):
   t=end-(3999-i)*step;c=100+i*.01
   r=dict(time=t,close_time=(t+step)*1000-1,open=c,high=c+2,low=c-1,close=c+1,volume=10,quote_volume=10*(c+1),closed=i<3999)
   r['exact']=dict(schema='chart-exact-decimal/1',state='VERIFIED',provenance='UPSTREAM_DECIMAL_TEXT',**{k:str(r[k]) for k in ('open','high','low','close','volume','quote_volume')});out.append(r)
  return out
 data={iv:dataset(iv) for iv in STEPS};timing_control={'enabled':False}
 def packet(symbol,iv,gen,initial):
  p=dict(type='snapshot' if initial else 'update',symbol=symbol,interval=iv,generation=gen,sequence=1,status='LIVE',received_at=int(time.time()*1000))
  if initial:p.update(candles=data[iv][-300:],market=next(m for m in f.markets if m['symbol']==symbol),quality=dict(state='OK',missing_bars=0))
  if timing_control['enabled']:
   p['timing']=dict(schema='chart-time-proof/1',policy=dict(schema='chart-time-policy/1'),state='FRESH',reason=None,data_age_ms=0,upstream_age_upper_ms=200,uncertainty_ms=100,upstream_event_time=data[iv][-1]['time']*1000+1000)
  return p
 f.packet_provider=packet
 settings=f.api('/api/workspaces/main/indicators?format_version=4')
 for indicator in settings['indicators']:
  if indicator['kind']=='BB':indicator['enabled']=True;indicator['params']['offset']=-30
 f.api('/api/workspaces/main/indicators?format_version=4',dict(request_id='time-audit-bb',expected_revision=settings['revision'],indicators=settings['indicators']),'PUT')
 target=data['15m'][-300:]
 trend=f.trend
 geometry={**trend['geometry'],'anchors':[dict(time=target[35]['time'],price='138'),dict(time=target[65]['time'],price='139')]}
 f.api('/api/workspaces/main/drawing-operations?format_version=10',dict(request_id='time-audit-trend',operations=[dict(drawing_id=trend['drawing_id'],expected_revision=trend['revision'],geometry=geometry,management=trend['management'],deleted=False)]),'POST')
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);p=browser.new_page(viewport=dict(width=1536,height=900),timezone_id='Asia/Baku');p.set_default_timeout(10000)
   f.setup(p,result,wait=False)
   def history(route):
    q=parse_qs(urlparse(route.request.url).query);iv=q['interval'][0];end=int(q['end_time'][0])//1000
    rows=[r for r in data[iv] if r['time']<=end][-300:];pages.append(dict(interval=iv,count=len(rows)))
    route.fulfill(json=fixture_response(route.request.url,dict(candles=rows,has_more=len(rows)==300,quality=dict(state='OK',missing_bars=0))))
   p.route('**/api/candles*',history)
   expect(p.get_by_text('300 mum',exact=True)).to_be_visible()
   f.read(p,'chart.timeScale().setVisibleLogicalRange({from:30,to:100})');p.wait_for_timeout(150)
   line=p.locator('[data-drawing="'+trend['drawing_id']+'"] .shape-trend')
   for attr,index in [('x1',35),('x2',65)]:
    expected=f.read(p,'chart.timeScale().timeToCoordinate(view.candles['+str(index)+'].time)')
    actual=float(line.get_attribute(attr));assert abs(actual-expected)<0.01,(attr,actual,expected)
   result['checks'].append(dict(name='negative_BB_drawings_match_native_candle_pixels'))
   hidden_labels=p.locator('text[data-label-collision="hidden"]').count()
   assert hidden_labels>0,'dense fixture must suppress overlapping decorative labels'
   result['checks'].append(dict(name='dense_drawing_labels_suppress_overlap',hidden=hidden_labels))
   p.screenshot(path=str(ROOT/'reports/tradingview-comparison-20261117/priorities-labels.png'))
   f.read(p,'chart.timeScale().setVisibleLogicalRange({from:40,to:140})');p.wait_for_timeout(150)
   def middle():
    return f.read(p,"(()=>{const s=chart.timeScale(),x=s.width()/2;const rows=view.candles;let a=0,b=rows.length-1;while(a+1<b){const m=(a+b)>>1;if(s.timeToCoordinate(rows[m].time)<x)a=m;else b=m;}const left=s.timeToCoordinate(rows[a].time),right=s.timeToCoordinate(rows[b].time);return rows[a].time+(x-left)/(right-left)*(rows[b].time-rows[a].time);})()")
   original=middle();assert original
   # Preserve UTC through real settings save and indicator effect cleanup/recreation.
   for offset in (30,0,-30):
    p.locator('summary').filter(has_text='Göstergeler').click()
    p.get_by_role('button',name='Gösterge ayarları',exact=True).click()
    p.get_by_label('bb-main offset',exact=True).fill(str(offset))
    p.get_by_role('button',name='Gösterge ayarlarını kaydet',exact=True).click()
    expect(p.get_by_role('dialog',name='Gösterge ayarları',exact=True)).not_to_be_visible()
    p.wait_for_timeout(180)
    current=middle()
    assert abs(current-original)<1,(offset,original,current)
    result['checks'].append(dict(name='indicator_offset_preserves_UTC_'+str(offset),error_seconds=abs(current-original)))
   for iv,label in [('1h','1 sa'),('5m','5 dk'),('15m','15 dk')]:
    p.get_by_role('button',name=label,exact=True).click()
    p.wait_for_function("iv=>{const node=document.querySelector('.shell-instrument');return node&&node.textContent.includes(iv)}",arg=label)
    p.wait_for_timeout(800)
    # Wait for target-driven history to settle by watching its visible middle.
    for _ in range(30):
     current=middle()
     if current and abs(current-original)<1:break
     p.wait_for_timeout(200)
    assert current and abs(current-original)<1,(iv,original,current)
    result['checks'].append(dict(name='preserve_middle_'+iv,original=original,actual=current,error_seconds=abs(current-original)))
   assert pages, 'smaller timeframe should load older pages'
   result['checks'].append(dict(name='automatic_history_for_reference',pages=pages))
   held=[]
   def delayed_history(route):
    if parse_qs(urlparse(route.request.url).query)['interval'][0]=='5m':held.append(route)
    else:history(route)
   p.route('**/api/candles*',delayed_history)
   p.get_by_role('button',name='1 sa',exact=True).click();p.wait_for_timeout(500)
   p.get_by_role('button',name='5 dk',exact=True).click()
   for _ in range(25):
    if held:break
    p.wait_for_timeout(100)
   assert held,'expected delayed history request'
   # A real wheel gesture is new user intent and must cancel the old restore target.
   box=p.locator('.chart-host').bounding_box()
   p.mouse.move(box['x']+box['width']*.5,box['y']+100)
   p.mouse.wheel(0,120);p.wait_for_timeout(200)
   user_middle=middle()
   history(held.pop(0));p.wait_for_timeout(500)
   assert abs(middle()-user_middle)<1,(user_middle,middle())
   result['checks'].append(dict(name='wheel_cancels_pending_history_restore',error_seconds=abs(middle()-user_middle)))
   p.unroute('**/api/candles*',delayed_history)
   p.get_by_role('button',name='Güncel',exact=True).click();p.wait_for_timeout(150)
   tail=f.read(p,'view.candles.at(-1).time');visible=f.read(p,'chart.timeScale().getVisibleRange()');assert visible['to']==tail,(visible,tail)
   result['checks'].append(dict(name='latest_returns_to_market_tail',tail=tail))
   footer=p.locator('.chart-footer').inner_text() if p.locator('.chart-footer').count() else p.locator('footer').inner_text()
   receipt=f.read(p,'view.received_at');expected_time=datetime.fromtimestamp(receipt/1000,timezone.utc).strftime('%H:%M:%S')+' UTC'
   assert expected_time in footer,(expected_time,footer)
   result['checks'].append(dict(name='receipt_explicit_UTC_in_Baku_browser'))
   def navigate_date(target):
    p.get_by_role('button',name='Tarihe git',exact=True).click()
    dialog=p.get_by_role('dialog',name='Tarihe git',exact=True)
    dialog.get_by_label('Gitmek istediğin tarih ve saat (UTC)').fill(datetime.fromtimestamp(target,timezone.utc).strftime('%Y-%m-%dT%H:%M'))
    p.screenshot(path=str(ROOT/'reports/tradingview-comparison-20261117/priorities-date-dialog.png'))
    dialog.get_by_role('button',name='Tarihe git',exact=True).click()
   # Direct navigation centers an unloaded UTC candle after bounded pagination.
   target=data['5m'][-2200]['time'];navigate_date(target)
   for _ in range(100):
    if abs(middle()-target)<1:break
    p.wait_for_timeout(100)
   assert abs(middle()-target)<1,(target,middle())
   result['checks'].append(dict(name='go_to_unloaded_UTC_date',error_seconds=abs(middle()-target)))
   future=data['5m'][-1]['time']+86400;navigate_date(future)
   expect(p.get_by_text('Bu tarihin mumu henüz yok. Son mevcut mum için Güncel seç.',exact=True)).to_be_visible()
   result['checks'].append(dict(name='future_date_reports_missing_candle'))
   def broken(route):route.abort()
   p.route('**/api/candles*',broken);navigate_date(data['5m'][-3500]['time'])
   expect(p.get_by_role('button',name='Geçmişi yeniden dene',exact=True)).to_be_visible()
   assert f.read(p,'view.candles[0].time')>data['5m'][-3500]['time']
   p.unroute('**/api/candles*',broken)
   result['checks'].append(dict(name='date_network_failure_is_retryable'))
   # An empty provider page and a full memory window have distinct visible outcomes.
   def boundary(route):route.fulfill(json=fixture_response(route.request.url,dict(candles=[],has_more=False)))
   p.route('**/api/candles*',boundary)
   p.get_by_role('button',name='Geçmişi yeniden dene',exact=True).click()
   expect(p.get_by_text('Sağlayıcının sunduğu geçmişin başlangıcına ulaşıldı.',exact=True)).to_be_visible()
   p.unroute('**/api/candles*',boundary)
   result['checks'].append(dict(name='provider_boundary_is_distinct'))
   p.get_by_role('button',name='30 dk',exact=True).click();p.wait_for_timeout(500)
   navigate_date(data['30m'][0]['time']-1800)
   expect(p.get_by_text('4000 mumluk görünüm sınırına ulaşıldı. Daha eski tarih bu oturumda yüklenemiyor.',exact=True).first).to_be_visible(timeout=20000)
   result['checks'].append(dict(name='date_history_cap_reports_4000_limit'))
   # No producer timing in this fixture: the UI must refuse a precise countdown.
   expect(p.get_by_label('Mum kapanış süresi')).to_have_attribute('data-countdown-state','UNAVAILABLE')
   result['checks'].append(dict(name='countdown_without_clock_proof_is_unavailable'))
   timing_control['enabled']=True
   p.get_by_role('button',name='1 dk',exact=True).click()
   expect(p.get_by_label('Mum kapanış süresi')).to_have_attribute('data-countdown-state','APPROXIMATE')
   assert 'Yaklaşık kapanış' in p.get_by_label('Mum kapanış süresi').inner_text()
   p.evaluate('window.__originalDateNow=Date.now;Date.now=()=>window.__originalDateNow()+10000')
   expect(p.get_by_label('Mum kapanış süresi')).to_have_attribute('data-countdown-state','UNAVAILABLE')
   p.evaluate('Date.now=window.__originalDateNow')
   result['checks'].append(dict(name='countdown_proof_range_and_clock_jump'))
   assert not result['page_errors'],result['page_errors'];assert not result['unexpected_requests'],result['unexpected_requests']
   p.screenshot(path=str(ROOT/'reports/chart-time-audit-20261117/fixed-browser.png'))
   result['passed']=True;browser.close()
 finally:
  f.close();(ROOT/'reports/chart-time-audit-20261117/browser-fix-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':main()
