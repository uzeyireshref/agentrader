import {steps} from './evidence';
import {validCandle,type Candle,type Interval} from './types';
import {sourceValue,type IndicatorPoint} from './indicators';
import type {IndicatorConfig,PriceSource} from './indicatorConfig';
import {decimalRational,rational,add,divide,displayNumber,type Rational} from './exactGeometry';
export type VwapPlotPoint={time:number;value?:number;color?:string};
export type VwapResult={points:(IndicatorPoint&{exact_ratio?:{numerator:string;denominator:string}})[];plot:VwapPlotPoint[];states:{time:number;state:string}[];provenance:{computation_mode:string;price_source:string;volume_source:string;session:string|null;anchor_time:number|null;anchor_symbol:string|null;display_interval:Interval;trade_vwap_claim:false;order_authority:false}};
export const vwapReasons:Record<string,string>={ANCHOR_UNSET:'Önce bir çapa mumu seç',ANCHOR_SYMBOL_MISMATCH:'Çapa başka bir sembole ait',ANCHOR_NOT_ON_GRID:'Çapa bu zaman diliminin mum başlangıcında değil',ANCHOR_HISTORY_MISSING:'Çapaya kadar eski mumları yükle',BEFORE_ANCHOR:'Çapadan önce',SESSION_START_MISSING:'UTC seans başlangıcına kadar eski mumları yükle',SESSION_INTERVAL_UNSUPPORTED:'Günlük seans bu zaman diliminde uygulanamaz',ZERO_CUMULATIVE_VOLUME:'Birikimli hacim sıfır',EXACT_VOLUME_UNPROVEN:'Exact quote/base hacmi doğrulanamadı',INVALID_VOLUME_SOURCE:'Ham hacim/fiyat kaynağı geçersiz',GRID_GAP:'Birikimde mum boşluğu var',INVALID_GRID:'Geçersiz mum/zaman gridi'};
export function vwapSeries(rows:Candle[],config:IndicatorConfig,interval:Interval,symbol:string):VwapResult{
 const step=steps[interval],session=config.kind==='SESSION_VWAP',p=config.params!,exact=p.computation_mode==='EXACT_QUOTE_BASE',anchor=Number(p.anchor_time??0);
 const result:VwapResult={points:[],plot:[],states:[],provenance:{computation_mode:String(p.computation_mode),price_source:config.source,volume_source:exact?'NATIVE_DECIMAL_QUOTE_BASE':'RAW_KLINE_BASE_VOLUME',session:session?'UTC_00:00':null,anchor_time:session?null:anchor,anchor_symbol:session?null:String(p.anchor_symbol),display_interval:interval,trade_vwap_claim:false,order_authority:false}};
 const blocked=(reason:string)=>{result.plot=reason==='INVALID_GRID'?[]:rows.map(r=>({time:r.time}));result.states=rows.map(r=>({time:r.time,state:reason}));return result;};
 const gridAnchor=interval==='1w'?345600:0;
 if(rows.some((r,i)=>!validCandle(r)||(r.time-gridAnchor)%step!==0||r.close_time!==(r.time+step)*1000-1||i>0&&r.time<=rows[i-1].time))return blocked('INVALID_GRID');
 if(session&&(step>86400||86400%step!==0))return blocked('SESSION_INTERVAL_UNSUPPORTED');
 if(!session){if(!anchor)return blocked('ANCHOR_UNSET');if(p.anchor_symbol!==symbol)return blocked('ANCHOR_SYMBOL_MISMATCH');if((anchor-gridAnchor)%step!==0)return blocked('ANCHOR_NOT_ON_GRID');if(rows.length&&anchor<rows[0].time)return blocked('ANCHOR_HISTORY_MISSING');}
 let total=0,weighted=0,exactTotal=rational(0n),exactWeighted=rational(0n),current:number|null=null,complete=false,reason=session?'SESSION_START_MISSING':'BEFORE_ANCHOR';
 for(let i=0;i<rows.length;i++){
  const r=rows[i],t=r.time,day=Math.floor(t/86400)*86400,reset=(session&&current!==day)||(!session&&t===anchor);
  if(reset){current=day;total=0;weighted=0;exactTotal=rational(0n);exactWeighted=rational(0n);complete=session?t===day:true;reason=session?'SESSION_START_MISSING':'ANCHOR_HISTORY_MISSING';}
  else if(i>0&&t-rows[i-1].time!==step){complete=false;reason='GRID_GAP';}
  let state:string;
  if(!session&&t<anchor)state='BEFORE_ANCHOR';else if(!complete)state=reason;else{
   try{
    let value:number,ratio:Rational|undefined;
    if(exact){const e=r.exact;if(!e||e.schema!=='chart-exact-decimal/1'||e.state!=='VERIFIED'||e.provenance!=='UPSTREAM_DECIMAL_TEXT')throw Error();const v=decimalRational(e.volume as string),q=decimalRational(e.quote_volume as string);if(v.n<0n||q.n<0n||Number(e.volume)!==r.volume||Number(e.quote_volume)!==r.quote_volume||!((v.n===0n&&q.n===0n)||(v.n>0n&&q.n>0n)))throw Error();exactTotal=add(exactTotal,v);exactWeighted=add(exactWeighted,q);if(exactTotal.n===0n){state='ZERO_CUMULATIVE_VOLUME';result.plot.push({time:t});result.states.push({time:t,state});continue;}ratio=divide(exactWeighted,exactTotal);value=displayNumber(ratio);}
    else{total+=r.volume;weighted+=sourceValue(r,config.source as PriceSource)*r.volume;if(total===0){state='ZERO_CUMULATIVE_VOLUME';result.plot.push({time:t});result.states.push({time:t,state});continue;}value=weighted/total;}
    if(!Number.isFinite(value))throw Error();result.points.push({time:t,value,...(ratio?{exact_ratio:{numerator:ratio.n.toString(),denominator:ratio.d.toString()}}:{})});result.plot.push({time:t,value});state='READY';
   }catch{complete=false;reason=exact?'EXACT_VOLUME_UNPROVEN':'INVALID_VOLUME_SOURCE';state=reason;}
  }
  if(state!=='READY')result.plot.push({time:t});result.states.push({time:t,state});
 }
 return result;
}

/** Engine 5.2 omits whitespace plot rows and otherwise bridges them. Color belongs to outgoing segment. */
export function vwapRenderPlot(plot:VwapPlotPoint[]):VwapPlotPoint[]{return plot.map((p,i)=>p.value!==undefined&&i+1<plot.length&&plot[i+1].value===undefined?{...p,color:'rgba(0, 0, 0, 0)'}:p);}
