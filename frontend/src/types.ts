import {verifyEvidence,type DataProof} from './evidence';
import {validTiming,type TimeProof} from './timing';
export type Interval = '1m' | '5m' | '30m' | '15m' | '1h' | '4h' | '1d' | '1w';
export type Candle = {exact?:Record<string,unknown>;time:number; open:number; high:number; low:number; close:number; volume:number; quote_volume:number; close_time:number; closed:boolean};
export type Market = {exact?:Record<string,unknown>;symbol:string; base_asset:string; quote_asset:string; tick_size:string; contract_type:string};
export type Packet = {stream_epoch?:string;data_proof?:DataProof|null;source?:string;environment?:string;product?:string;price_type?:string;timing?:TimeProof;type:'snapshot'|'update'|'error'; symbol:string; interval:Interval; status:string; sequence:number; generation:number; received_at:number|null; candles?:Candle[]; candle?:Candle|null; tail?:Candle[]; quality?:{state:string;missing_bars:number;[key:string]:unknown}; market?:Market|null; code?:string};
export type ChartState = {stream_epoch?:string;retired_epochs?:string[];snapshot_required?:boolean;data_proof?:DataProof;data_quality?:Record<string,unknown>;timing?:TimeProof;timing_received_mono?:number;timing_received_wall?:number;consumer_clock_untrusted?:boolean;symbol:string;interval:Interval;generation:number;sequence:number;status:string;received_at:number|null;candles:Candle[];quality:string;market:Market|null};
export const intervals:Interval[] = ['1m','5m','15m','30m','1h','4h','1d','1w'];
export const labels:Record<Interval,string> = {'1m':'1 dk','5m':'5 dk','30m':'30 dk','15m':'15 dk','1h':'1 sa','4h':'4 sa','1d':'1 gün','1w':'1 hf'};
export function initialState(symbol:string, interval:Interval):ChartState { return {symbol,interval,generation:-1,sequence:-1,status:'CONNECTING',received_at:null,candles:[],quality:'UNKNOWN',market:null}; }
export function beginStream(state:ChartState):ChartState{return {...state,status:'RECONNECTING',snapshot_required:true,...(!state.stream_epoch?{generation:-1,sequence:-1}:{})};}
export function validCandle(c:Candle):boolean { return Boolean(c && typeof c==='object') && Number.isSafeInteger(c.time) && c.time>0 && c.time<=32503680000 && typeof c.closed==='boolean' && Number.isSafeInteger(c.close_time) && c.close_time>=c.time*1000 && [c.open,c.high,c.low,c.close,c.volume,c.quote_volume].every(Number.isFinite) && Math.min(c.open,c.high,c.low,c.close)>0 && c.low<=Math.min(c.open,c.close) && c.high>=Math.max(c.open,c.close) && c.volume>=0 && c.quote_volume>=0; }
export function mergeHistory(current:Candle[], incoming:Candle[]):Candle[] { const byTime = new Map<number,Candle>(); for (const c of incoming) if(validCandle(c)) byTime.set(c.time,c); for(const c of current) byTime.set(c.time,c); return [...byTime.values()].sort((a,b)=>a.time-b.time).slice(-4000); }
export function applyPacket(state:ChartState,p:Packet,mono=performance.now(),wall=Date.now()):ChartState {
  if(!p||typeof p!=='object'||!['snapshot','update'].includes(p.type))return state;
  if(!['CONNECTING','SYNCING','LIVE','RECONNECTING','STALE','GAP','STOPPED','ERROR'].includes(p.status))return state;
  if(p.received_at!==null&&(!Number.isSafeInteger(p.received_at)||p.received_at<0))return state;
  if(p.status==='LIVE'&&p.received_at===null)return state;
  if((p.candles!==undefined&&!Array.isArray(p.candles))||(p.tail!==undefined&&!Array.isArray(p.tail)))return state;
  if(p.symbol!==state.symbol || p.interval!==state.interval || p.type==='error') return state;
  const strict=p.stream_epoch!==undefined||state.stream_epoch!==undefined;
  const sameEpoch=p.stream_epoch===state.stream_epoch;
  if(!Number.isSafeInteger(p.sequence)||p.sequence<0||!Number.isSafeInteger(p.generation)||p.generation<0)return state;
  if(strict){
    if(typeof p.stream_epoch!=='string'||!/^[a-f0-9]{32}$/.test(p.stream_epoch)||!p.data_proof)return state;
    if(p.source!=='binance_usdm_live_trade_price'||p.environment!=='live_public'||p.product!=='USD-M'||p.price_type!=='LAST_PRICE')return state;
    if(!sameEpoch&&(p.type!=='snapshot'||state.retired_epochs?.includes(p.stream_epoch)||!state.snapshot_required&&state.stream_epoch!==undefined&&p.generation<=state.generation))return state;
    if(state.snapshot_required&&p.type!=='snapshot'||sameEpoch&&p.generation!==state.generation&&p.type!=='snapshot')return state;
  }
  if((!strict||sameEpoch)&&(p.generation<state.generation||p.generation===state.generation&&p.sequence<state.sequence))return state;
  if(p.timing!==undefined&&!validTiming(p.timing))return {...state,status:'STALE'};
  const elapsed=state.timing_received_mono===undefined?0:mono-state.timing_received_mono;
  const snapshot=p.type==='snapshot'&&(!sameEpoch||state.snapshot_required||p.generation!==state.generation);
  const clockBad=!Number.isFinite(mono)||elapsed<0||state.timing_received_wall!==undefined&&Math.abs((wall-state.timing_received_wall)-elapsed)>250;
  let timing=p.timing;
  if(sameEpoch&&timing&&state.timing&&p.generation===state.generation&&p.sequence===state.sequence&&timing.upstream_event_time!==state.timing.upstream_event_time)return {...state,status:'STALE'};
  if(sameEpoch&&timing&&state.timing&&timing.upstream_event_time===state.timing.upstream_event_time){
   const carry=(a:number|null,b:number|null)=>a===null?b:b===null?a:Math.max(a,b+Math.max(0,elapsed));
   timing={...timing,data_age_ms:carry(timing.data_age_ms,state.timing.data_age_ms),upstream_age_upper_ms:carry(timing.upstream_age_upper_ms,state.timing.upstream_age_upper_ms)};
  }
  const clockFields=timing?{timing,timing_received_mono:mono,timing_received_wall:wall,consumer_clock_untrusted:snapshot?false:Boolean(state.consumer_clock_untrusted||clockBad)}:{};
  // Repeated sequence is a heartbeat: update status without replacing candle identity.
  const heartbeat=sameEpoch&&p.generation===state.generation&&p.sequence===state.sequence&&!snapshot;
  if(heartbeat&&!strict)return {...state,...clockFields,status:p.status,received_at:p.received_at,quality:p.quality?.state??state.quality,market:p.market??state.market};
  let candles=state.candles;
  if(!heartbeat&&p.type==='snapshot' && p.candles?.length) {
    if(!p.candles.every(validCandle) || p.candles.some((c,i,a)=>i>0 && c.time<=a[i-1].time)) return state;
    const closed=new Set(state.candles.filter(c=>c.closed).map(c=>c.time));
    if(p.candles.some(c=>closed.has(c.time)&&!c.closed))return state;
    const older=state.candles.filter(c=>c.time<p.candles![0].time);
    candles=[...older,...p.candles].slice(-4000);
  } else if(!heartbeat&&(p.tail?.length || p.candle)) {
    const tail=p.tail?.length?p.tail:[p.candle!];
    if(!tail.every(validCandle) || tail.some((c,i)=>i>0&&c.time<=tail[i-1].time))return state;
    const byTime=new Map(state.candles.map(c=>[c.time,c]));
    for(const c of tail){const previous=byTime.get(c.time);if(previous?.closed&&!c.closed)return state;byTime.set(c.time,c);}
    candles=[...byTime.values()].sort((a,b)=>a.time-b.time).slice(-4000);
  }
  let evidenceFields={};
  if(strict){
    const proof=p.data_proof!;
    if(sameEpoch&&state.data_proof&&(proof.data_revision<state.data_proof.data_revision||(proof.data_revision===state.data_proof.data_revision&&proof.snapshot_hash!==state.data_proof.snapshot_hash)||heartbeat&&proof.data_revision!==state.data_proof.data_revision))return state;
    if(!p.quality||!verifyEvidence(candles,p.market??state.market,p.quality,p.symbol,p.interval,p.stream_epoch!,p.generation,proof))return state;
    evidenceFields={stream_epoch:p.stream_epoch,retired_epochs:!sameEpoch&&state.stream_epoch?[...(state.retired_epochs??[]),state.stream_epoch]:state.retired_epochs??[],snapshot_required:false,data_proof:proof,data_quality:p.quality};
  }
  return {...state,...clockFields,...evidenceFields,candles,generation:p.generation,sequence:p.sequence,status:p.status,received_at:p.received_at,quality:p.quality?.state??state.quality,market:p.market??state.market};
}
