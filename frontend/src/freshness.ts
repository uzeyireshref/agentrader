import type {ChartState} from './types';
export const MAX_DISPLAY_AGE_MS=10_000;
/** Heartbeat receipt cannot reset upstream age. Wall jumps remain blocked until snapshot. */
export function checkFreshness(state:ChartState,now:number,mono=performance.now()):ChartState{
 if(state.status!=='LIVE')return state;
 if(state.data_proof?.state==='BLOCKED')return {...state,status:state.data_proof.blocked_reasons.some(r=>r==='GRID_GAP'||r==='INVALID_GRID')?'GAP':'UNVERIFIED'};
 if(state.timing){
  const elapsed=state.timing_received_mono===undefined?NaN:mono-state.timing_received_mono;
  const jumped=state.timing_received_wall===undefined||Math.abs((now-state.timing_received_wall)-elapsed)>250;
  const badClock=state.consumer_clock_untrusted||!Number.isFinite(elapsed)||elapsed<0||jumped;
  const p=state.timing;
  const stale=badClock||p.state!=='FRESH'||p.data_age_ms===null||p.upstream_age_upper_ms===null||p.uncertainty_ms===null||p.uncertainty_ms>1000||elapsed>MAX_DISPLAY_AGE_MS||p.data_age_ms+elapsed>MAX_DISPLAY_AGE_MS||p.upstream_age_upper_ms+elapsed>MAX_DISPLAY_AGE_MS;
  return stale?{...state,status:'STALE',consumer_clock_untrusted:Boolean(badClock)}:state;
 }
 // Legacy display packets provide no clock eligibility proof.
 return state.received_at===null||!Number.isFinite(now)||now-state.received_at>MAX_DISPLAY_AGE_MS||state.received_at-now>250?{...state,status:'STALE'}:state;
}
