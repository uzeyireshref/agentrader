import { steps } from './evidence';
import { MAX_DISPLAY_AGE_MS } from './freshness';
import { validTiming } from './timing';
import { validCandle, type ChartState } from './types';

export type CountdownClock={mono:number;wall:number};
export type CandleCountdownResult={state:'APPROXIMATE'|'UNAVAILABLE';label:string;reason:string;minRemainingMs:number|null;maxRemainingMs:number|null};
export const COUNTDOWN_EXPLANATION='Son alınan saat kanıtına göre yaklaşık kalan süre. Borsa saatinin belirsizliği aralığa dahildir; sunucudan tarayıcıya aktarım gecikmesi ölçülmediğinden kesin kapanış saati değildir.';
export function countdownDuration(ms:number):string {
 const seconds=Math.max(0,Math.ceil(ms/1000)),days=Math.floor(seconds/86400),hours=Math.floor(seconds%86400/3600),minutes=Math.floor(seconds%3600/60),s=seconds%60;
 const hms=[hours,minutes,s].map(v=>String(v).padStart(2,'0')).join(':');
 return days?days+' gün '+hms:hours?hms:[minutes,s].map(v=>String(v).padStart(2,'0')).join(':');
}
const unavailable=(reason:string,label='Saat doğrulanamadı'):CandleCountdownResult=>({state:'UNAVAILABLE',label,reason,minRemainingMs:null,maxRemainingMs:null});
/** Approximation anchored to producer evidence; never substitute the browser wall epoch for exchange time. */
export function candleCountdown(state:ChartState,clock:CountdownClock):CandleCountdownResult {
 if(state.status!=='LIVE'||state.consumer_clock_untrusted||state.snapshot_required||state.data_proof?.state!=='VERIFIED'||state.quality!=='OK')return unavailable('MARKET_NOT_READY');
 const candle=state.candles.at(-1),step=steps[state.interval]*1000,anchor=state.interval==='1w'?345600000:0;
 if(!candle||!validCandle(candle)||candle.closed)return unavailable('NO_OPEN_CANDLE','Açık mum bekleniyor');
 const open=candle.time*1000,close=candle.close_time+1;
 if(!Number.isFinite(step)||(open-anchor)%step!==0||close!==open+step)return unavailable('INVALID_CANDLE_BOUNDARY');
 const p=state.timing;
 if(!validTiming(p)||p.state!=='FRESH'||p.upstream_event_time===null||p.uncertainty_ms===null||p.upstream_age_upper_ms===null||p.data_age_ms===null)return unavailable('TIMING_UNAVAILABLE');
 const elapsed=state.timing_received_mono===undefined?NaN:clock.mono-state.timing_received_mono;
 if(!Number.isFinite(clock.wall)||!Number.isFinite(elapsed)||elapsed<0||state.timing_received_wall===undefined||Math.abs((clock.wall-state.timing_received_wall)-elapsed)>250)return unavailable('CLOCK_UNTRUSTED');
 if(p.uncertainty_ms>1000||elapsed>MAX_DISPLAY_AGE_MS||p.data_age_ms+elapsed>MAX_DISPLAY_AGE_MS||p.upstream_age_upper_ms+elapsed>MAX_DISPLAY_AGE_MS)return unavailable('TIMING_STALE');
 if(p.upstream_event_time<open||p.upstream_event_time>=close)return unavailable('EVENT_OUTSIDE_CANDLE');
 // upper age includes one uncertainty radius. Subtracting twice that radius yields
 // a broad producer-clock interval, not an exact point estimate of exchange time.
 const upperNow=p.upstream_event_time+p.upstream_age_upper_ms+elapsed;
 const lowerNow=p.upstream_event_time+p.upstream_age_upper_ms-2*p.uncertainty_ms+elapsed;
 if(upperNow>=close)return unavailable('CLOSE_BOUNDARY_PENDING','Kapanış doğrulanıyor');
 const minRemainingMs=close-upperNow,maxRemainingMs=close-lowerNow;
 const low=countdownDuration(minRemainingMs),high=countdownDuration(maxRemainingMs);
 return {state:'APPROXIMATE',reason:'PRODUCER_CLOCK_APPROXIMATION',label:'Yaklaşık kapanış · '+(low===high?low:low+'–'+high),minRemainingMs,maxRemainingMs};
}
