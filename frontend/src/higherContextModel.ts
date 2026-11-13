import {intervals,validCandle,type Candle,type Interval} from './types';
import {steps} from './evidence';
export type HigherContext={schema:'chart-higher-context/1';symbol:string;base_interval:Interval;interval:Interval;requested_reference_time:number;effective_reference_time:number|null;state:'READY'|'BLOCKED'|'UNAVAILABLE';reason:string|null;candle:Candle|null;source:string;environment:string;product:string;price_type:string;provenance:string;resampled:boolean;server_time:number;clock_state:string;clock_uncertainty_ms:number;precision:{state:string};live_eligible:false;order_authority:false};
export const higherIntervals=(base:Interval)=>intervals.filter(i=>steps[i]>steps[base]);
export const referenceTime=(row?:Candle)=>row?(row.closed?row.close_time+1:row.time*1000):null;
export function validHigherContext(r:HigherContext,symbol:string,base:Interval,target:Interval,time:number):boolean{
 if(r.schema!=='chart-higher-context/1'||r.symbol!==symbol||r.base_interval!==base||r.interval!==target||r.requested_reference_time!==time||!higherIntervals(base).includes(target)||r.source!=='binance_usdm_live_trade_price'||r.environment!=='live_public'||r.product!=='USD-M'||r.price_type!=='LAST_PRICE'||r.provenance!=='BINANCE_NATIVE_KLINE'||r.resampled!==false||r.live_eligible!==false||r.order_authority!==false||!['READY','BLOCKED','UNAVAILABLE'].includes(r.state))return false;
 if(r.state!=='READY')return r.candle===null;
 const c=r.candle,cutoff=r.effective_reference_time,step=steps[target]*1000,anchor=target==='1w'?345600000:0;
 return !!c&&validCandle(c)&&c.closed&&r.precision?.state==='VERIFIED'&&c.exact?.state==='VERIFIED'&&r.clock_state==='MEASURED'&&Number.isFinite(r.clock_uncertainty_ms)&&r.clock_uncertainty_ms>=0&&r.clock_uncertainty_ms<=1000&&Number.isSafeInteger(cutoff)&&cutoff!==null&&cutoff<=time&&cutoff<=r.server_time-r.clock_uncertainty_ms&&c.close_time<cutoff&&c.close_time===c.time*1000+step-1&&(c.time*1000-anchor)%step===0&&c.time*1000===Math.floor((cutoff-anchor)/step)*step+anchor-step;
}
