import {test} from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import CandleCountdown from '../src/CandleCountdown.tsx';
import {candleCountdown,countdownDuration,COUNTDOWN_EXPLANATION} from '../src/closeCountdown';
import {initialState,type ChartState,type Interval} from '../src/types';
import {steps} from '../src/evidence';
function live(interval:Interval='1m',remaining=10000):ChartState {
 const anchor=interval==='1w'?Date.UTC(2026,10,16):Date.UTC(2026,10,17),step=steps[interval]*1000;
 const open=Math.floor(anchor/step)*step+(interval==='1w'?345600000:0);
 const corrected=interval==='1w'?anchor:open,close=corrected+step;
 return {...initialState('BTCUSDT',interval),status:'LIVE',quality:'OK',data_proof:{state:'VERIFIED'} as ChartState['data_proof'],timing_received_mono:1000,timing_received_wall:5000,
  candles:[{time:corrected/1000,close_time:close-1,closed:false,open:100,high:110,low:90,close:105,volume:10,quote_volume:1050}],
  timing:{schema:'chart-time-proof/1',policy:{schema:'chart-time-policy/1'},state:'FRESH',reason:null,data_age_ms:100,upstream_age_upper_ms:600,uncertainty_ms:200,upstream_event_time:close-remaining}};
}
const clock={mono:1000,wall:5000};
test('initial connection waits without claiming that the clock is broken',()=>{
 for(const status of ['CONNECTING','SYNCING']){
  const state=live();state.status=status;
  const result=candleCountdown(state,clock);
  assert.equal(result.state,'UNAVAILABLE');assert.equal(result.reason,'WAITING_FOR_MARKET');
  assert.equal(result.minRemainingMs,null);assert.equal(result.label,'Kapanış süresi bekleniyor');
  state.consumer_clock_untrusted=true;
  assert.notEqual(candleCountdown(state,clock).reason,'WAITING_FOR_MARKET');
 }
});
test('producer age upper bound yields an explicit approximate range, never an exact server timestamp',()=>{
 const result=candleCountdown(live(),clock);assert.equal(result.state,'APPROXIMATE');assert.equal(result.minRemainingMs,9400);assert.equal(result.maxRemainingMs,9800);assert.match(result.label,/Yaklaşık kapanış/);
 const later=candleCountdown(live(),{mono:1500,wall:5500});assert.equal(later.minRemainingMs,8900);assert.equal(later.maxRemainingMs,9300);
});
test('range remains visibly approximate when its endpoints round to the same second',()=>{
 const state=live();const a=candleCountdown(state,clock);assert.equal(a.label,'Yaklaşık kapanış · 00:10');
 state.timing!.uncertainty_ms=1000;assert.equal(candleCountdown(state,clock).label,'Yaklaşık kapanış · 00:10–00:12');
});
test('daily boundary uses close_time plus one at UTC midnight',()=>{
 const state=live('1d',60000),row=state.candles[0];assert.equal(new Date(row.time*1000).toISOString(),'2026-11-17T00:00:00.000Z');assert.equal(new Date(row.close_time+1).toISOString(),'2026-11-18T00:00:00.000Z');
 const result=candleCountdown(state,clock);assert.equal(result.minRemainingMs,59400);assert.equal(result.maxRemainingMs,59800);
});
test('weekly boundary is the next Monday UTC even across month changes',()=>{
 const state=live('1w',3*86400000);const row=state.candles[0];assert.equal(new Date(row.time*1000).toISOString(),'2026-11-16T00:00:00.000Z');assert.equal(new Date(row.close_time+1).toISOString(),'2026-11-23T00:00:00.000Z');assert.match(candleCountdown(state,clock).label,/3 gün 00:00:00/);
 row.time=Date.UTC(2026,10,30)/1000;row.close_time=Date.UTC(2026,11,7)-1;state.timing!.upstream_event_time=row.close_time+1-60000;assert.equal(candleCountdown(state,clock).state,'APPROXIMATE');assert.equal(new Date(row.close_time+1).getUTCDay(),1);
});
test('crossing the uncertain close boundary waits for a new candle instead of counting negative',()=>{
 const state=live('1m',500);const result=candleCountdown(state,clock);assert.equal(result.state,'UNAVAILABLE');assert.equal(result.label,'Kapanış doğrulanıyor');assert.equal(result.minRemainingMs,null);
});
for(const status of ['STALE','BLOCKED','RENDER_ERROR','RECONNECTING','ERROR','STOPPED','GAP'])test('countdown unavailable for '+status,()=>{const state=live();state.status=status;assert.equal(candleCountdown(state,clock).state,'UNAVAILABLE');});
test('blocked/missing proofs, uncertainty and frozen upstream events fail closed despite LIVE transport',()=>{
 const changes:Array<(s:ChartState)=>void>=[s=>{s.timing=undefined},s=>{s.timing!.state='BLOCKED';s.timing!.reason='CLOCK_UNTRUSTED'},s=>{s.timing!.uncertainty_ms=1001},s=>{s.timing!.data_age_ms=10001},s=>{s.timing!.upstream_age_upper_ms=10001},s=>{s.timing!.upstream_event_time=null},s=>{s.consumer_clock_untrusted=true},s=>{s.snapshot_required=true},s=>{s.data_proof=undefined},s=>{s.data_proof!.state='BLOCKED'},s=>{s.quality='GAP'},s=>{s.timing_received_mono=undefined},s=>{s.timing_received_wall=undefined}];
 for(const change of changes){const state=live();change(state);assert.equal(candleCountdown(state,clock).state,'UNAVAILABLE');}
 assert.equal(candleCountdown(live(),{mono:11001,wall:15001}).state,'UNAVAILABLE');
});
test('wall-clock jumps in both directions and monotonic reversal cannot change the countdown',()=>{
 for(const c of [{mono:1000,wall:100000},{mono:1000,wall:-100000},{mono:999,wall:4999},{mono:NaN,wall:5000},{mono:1000,wall:NaN}])assert.equal(candleCountdown(live(),c).reason,'CLOCK_UNTRUSTED');
});
test('consumer wall epoch is irrelevant when elapsed wall and monotonic durations agree',()=>{const state=live();state.timing_received_wall=100;assert.deepEqual(candleCountdown(state,{mono:1500,wall:600}),candleCountdown(live(),{mono:1500,wall:5500}));});
test('closed candles, malformed boundaries, and wrong upstream event window never show a countdown',()=>{
 for(const mutate of [(s:ChartState)=>{s.candles[0].closed=true},(s:ChartState)=>{s.candles=[]},(s:ChartState)=>{s.candles[0].close_time--},(s:ChartState)=>{s.timing!.upstream_event_time=s.candles[0].time*1000-1},(s:ChartState)=>{s.timing!.upstream_event_time=s.candles[0].close_time+1}]){const state=live();mutate(state);assert.equal(candleCountdown(state,clock).state,'UNAVAILABLE');}
});
test('duration formats minutes hours days and clamps negative inputs',()=>{assert.equal(countdownDuration(0),'00:00');assert.equal(countdownDuration(-1),'00:00');assert.equal(countdownDuration(61000),'01:01');assert.equal(countdownDuration(3661000),'01:01:01');assert.equal(countdownDuration(86461000),'1 gün 00:01:01');});
test('component renders approximation and explains transit uncertainty; unavailable clock is explicit',()=>{
 const html=renderToStaticMarkup(<CandleCountdown view={live()} clock={()=>clock}/>);assert.match(html,/data-countdown-state="APPROXIMATE"/);assert.match(html,/Yaklaşık kapanış/);assert.match(html,/aktar[ıi]m gecikmesi/);assert.match(COUNTDOWN_EXPLANATION,/kesin kapanış saati değildir/);
 const state=live();state.timing=undefined;const unavailable=renderToStaticMarkup(<CandleCountdown view={state} clock={()=>clock}/>);assert.match(unavailable,/Saat doğrulanamadı/);assert.match(unavailable,/data-countdown-state="UNAVAILABLE"/);
});


