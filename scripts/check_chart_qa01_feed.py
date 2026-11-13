"""Existing native socket blackout/stale heartbeat/resync using real FeedState/P2/P3."""
import json,time,traceback,hashlib
from playwright.sync_api import sync_playwright
from qa_chart_fixture import Fixture,ROOT
from agentrader.chart_clock import measure_time
from agentrader.chart_market import candle
from agentrader.chart_precision import exact_tick
from agentrader.market_feed import FeedState

def main():
 result=dict(task='QA01_FEED',passed=False,checks=[],page_errors=[],unexpected_requests=[],scope='Controlled real loopback WebSocket using production clock/reducer/evidence; no real Binance outage claim')
 def record(name,**kw):result['checks'].append(dict(name=name,passed=True,**kw))
 result['assets']={str(x.relative_to(ROOT/'agentrader/web_assets')):hashlib.sha256(x.read_bytes()).hexdigest() for x in (ROOT/'agentrader/web_assets').rglob('*') if x.is_file()}
 f=Fixture();state=FeedState('BTCUSDT','15m');offset=(int(time.time()*1000)//900000+1)*900000-int(time.time()*1000)-2000
 base_upstream=int(time.time()*1000)+offset;base_mono=time.monotonic()
 def upstream_now():return base_upstream+int((time.monotonic()-base_mono)*1000)
 class Clock:
  def get(self,path):assert path=='/fapi/v1/time';return {'serverTime':upstream_now()}
 market={**f.markets[0],'exact':exact_tick('0.25')};connections={}
 def seed():
  server,sample=measure_time(Clock());current=server//900000*900000;rows=[]
  for i in range(499):
   t=current-(498-i)*900000;rows.append(candle([t,'100','110','90','105','10',t+900000-1,'1050',5,'5','525','0'],server))
  state.seed(dict(candles=rows,market=market,quality={'state':'OK','missing_bars':0},server_time=server,clock_sample=sample))
 def apply():
  t=state.rows[-1]['time']*1000;stamp=upstream_now()
  return state.apply(dict(e='kline',E=stamp,s='BTCUSDT',k=dict(s='BTCUSDT',i='15m',t=t,T=t+900000-1,x=False,o='100',h='110',l='90',c='105',v='11',q='1155',n=6,V='5',Q='525')))
 def packet(symbol,interval,connection,initial):
  assert symbol=='BTCUSDT' and interval=='15m'
  generation,epoch=connections.get(connection,(-1,None));value=state.packet(generation,epoch);connections[connection]=(value['generation'],value['stream_epoch']);f.receipts.append({k:value.get(k) for k in ('type','status','generation','stream_epoch','sequence','data_proof','timing')});return value
 try:
  seed();apply();f.packet_provider=packet
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);p=browser.new_page(viewport={'width':1536,'height':900});p.set_default_timeout(8000);p.route('**/api/workspaces/main/drawings*',lambda r:r.fulfill(json={'drawings':[]}));f.setup(p,result,wait=False);p.get_by_text('499 mum',exact=True).wait_for();p.wait_for_function("document.querySelector('.connection')?.textContent.includes('Canlı')")
   initial=f.read(p,'view.data_proof');assert initial['state']=='VERIFIED' and f.read(p,'view.timing.state')=='FRESH';opened=f.counts['opened'];initial_last=state.rows[-1]['time'];record('native_initial_P2_P3_evidence_verified',hash=initial['snapshot_hash'])
   f.pause_stream.set();start=time.monotonic()
   p.wait_for_function("document.querySelector('.connection')?.textContent.includes('Veri gecikiyor')",timeout=16000);assert f.counts['opened']==opened==1 and f.counts['active']==1;record('same_open_socket_blackout_marks_stale_without_reconnect',seconds=time.monotonic()-start)
   f.pause_stream.clear();p.wait_for_timeout(800);assert f.read(p,'view.status')=='STALE';assert f.read(p,'view.timing.state')=='BLOCKED';record('fresh_delivery_of_stale_heartbeat_does_not_restore_live')
   seed();state.last_close=dict(event_id='historical-fixture-close',time=initial_last,event_time=state.last_event);p.wait_for_timeout(750);assert f.read(p,'view.stream_epoch')!=initial['stream_epoch'];assert f.read(p,'view.status')!='LIVE';record('resync_seed_is_snapshot_with_new_epoch_and_no_fresh_upstream',status=f.read(p,'view.status'))
   apply();p.wait_for_function("document.querySelector('.connection')?.textContent.includes('Canlı')");proof=f.read(p,'view.data_proof');assert proof['state']=='VERIFIED' and proof['snapshot_hash']!=initial['snapshot_hash'];assert f.read(p,'view.candles.length')==500 and f.read(p,'series.data().length')==500 and f.read(p,'new Set(series.data().map(x=>x.time)).size')==500;assert state.rows[-1]['time']-initial_last==900;record('fresh_event_after_catchup_restores_same_socket_without_duplicate_bar',hash=proof['snapshot_hash'],bar_advance_seconds=900,server_proof_bars=499,preserved_history_prefix=1,unique_native_bars=500)
   sequence=state.sequence;revision=state.data_revision;assert apply() is not None or state.sequence==sequence
   # Replaying an identical old event must be ignored by the producer reducer.
   t=state.rows[-1]['time']*1000;raw=dict(e='kline',E=state.last_event,s='BTCUSDT',k=dict(s='BTCUSDT',i='15m',t=t,T=t+900000-1,x=False,o='100',h='110',l='90',c='105',v='11',q='1155',n=6,V='5',Q='525'));sequence=state.sequence;revision=state.data_revision;assert state.apply(raw) is None;assert (state.sequence,state.data_revision)==(sequence,revision);p.wait_for_timeout(600);assert f.read(p,'series.data().length')==500;record('repeated_source_event_does_not_mutate_proof_or_duplicate_native_data')
   assert f.api('/api/workspaces/main/local-events')['events']==[];assert f.counts['opened']==1;record('history_close_metadata_creates_no_event_intent_or_external_action')
   p.screenshot(path=str(ROOT/'reports/chart-qa01-feed-20261113.png'));assert not result['page_errors'] and not result['unexpected_requests'] and not result.get('console_errors');browser.close();result['passed']=True
 except Exception:result['error']=traceback.format_exc()
 finally:result['packets']=f.receipts;f.close()
 (ROOT/'reports/chart-qa01-feed-20261113.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='packets'},ensure_ascii=True,indent=2));return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
