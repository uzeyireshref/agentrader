import {vwapSeries} from './vwap';
import {isVwap,indicatorName} from './indicatorConfig';
import {steps} from './evidence';
import type {PriceSource,IndicatorConfig} from './indicatorConfig';
import {validCandle,type Candle,type Interval} from './types';
export type IndicatorPoint={time:number;value:number;color?:string};
export function sourceValue(row:Candle,source:PriceSource):number {switch(source){case 'hl2':return (row.high+row.low)/2;case 'hlc3':return (row.high+row.low+row.close)/3;case 'ohlc4':return (row.open+row.high+row.low+row.close)/4;default:return row[source];}}
export function ema(rows:Candle[],period:number,source:PriceSource='close'):IndicatorPoint[]{
 if(!Number.isInteger(period)||period<1)throw new Error('Invalid period');
 const result:IndicatorPoint[]=[];let value=0;const alpha=2/(period+1);
 for(let i=0;i<rows.length;i++){if(i<period)value+=sourceValue(rows[i],source);if(i===period-1)value/=period;else if(i>=period)value=sourceValue(rows[i],source)*alpha+value*(1-alpha);if(i>=period-1)result.push({time:rows[i].time,value});}return result;
}
export function rsi(rows:Candle[],period=14,source:PriceSource='close',version:1|2=1):IndicatorPoint[]{
 if(!Number.isInteger(period)||period<1)throw new Error('Invalid period');
 const result:IndicatorPoint[]=[];let gain=0,loss=0;
 for(let i=1;i<rows.length;i++){const delta=sourceValue(rows[i],source)-sourceValue(rows[i-1],source),g=Math.max(0,delta),l=Math.max(0,-delta);if(i<=period){gain+=g;loss+=l;if(i===period){gain/=period;loss/=period;}}else{gain=(gain*(period-1)+g)/period;loss=(loss*(period-1)+l)/period;}if(i>=period)result.push({time:rows[i].time,value:loss===0?(gain===0&&version===1?50:100):100-100/(1+gain/loss)});}return result;
}
export function magnetPrice(row:Candle|undefined,price:number,toCoordinate:(p:number)=>number|null,y:number,threshold=10):number{
 if(!row)return price;let best=threshold,result=price;for(const p of [row.open,row.high,row.low,row.close]){const coordinate=toCoordinate(p);if(coordinate===null)continue;const distance=Math.abs(coordinate-y);if(distance<best){best=distance;result=p;}}return result;
}

export function sma(rows:Candle[],period:number,source:PriceSource='close'):IndicatorPoint[]{
 if(!Number.isInteger(period)||period<1)throw Error('Invalid period');const out:IndicatorPoint[]=[];for(let i=period-1;i<rows.length;i++){let total=0;for(let j=i-period+1;j<=i;j++)total+=sourceValue(rows[j],source);out.push({time:rows[i].time,value:total/period});}return out;
}
export function atr(rows:Candle[],period=14):IndicatorPoint[]{
 if(!Number.isInteger(period)||period<1)throw Error('Invalid period');let value=0;const out:IndicatorPoint[]=[];for(let i=0;i<rows.length;i++){const r=rows[i],previous=rows[i-1],tr=previous?Math.max(r.high-r.low,Math.abs(r.high-previous.close),Math.abs(r.low-previous.close)):r.high-r.low;if(i<period)value+=tr;if(i===period-1)value/=period;else if(i>=period)value=(value*(period-1)+tr)/period;if(i>=period-1)out.push({time:r.time,value});}return out;
}
export function indicatorGrid(rows:Candle[],interval:Interval):boolean{const step=steps[interval],anchor=interval==='1w'?345600:0;return rows.every((r,i)=>validCandle(r)&&(r.time-anchor)%step===0&&r.close_time===(r.time+step)*1000-1&&(!i||r.time-rows[i-1].time===step));}
export function indicatorSeries(rows:Candle[],c:IndicatorConfig,interval:Interval,symbol=''):IndicatorPoint[]{if(isVwap(c))return vwapSeries(rows,c,interval,symbol).points;if(!indicatorGrid(rows,interval))return [];const source=c.source as PriceSource;switch(c.kind){case 'EMA':return ema(rows,c.period,source);case 'RSI':return rsi(rows,c.period,source,c.calculation_version);case 'SMA':return sma(rows,c.period,source);case 'ATR':return atr(rows,c.period);case 'MACD':return multiIndicator(rows,c,interval).macd;case 'BB':return multiIndicator(rows,c,interval).basis;case 'SESSION_VWAP':case 'ANCHORED_VWAP':return [];}}

export function smoothPoints(points:IndicatorPoint[],period:number,kind:string):IndicatorPoint[]{let value=0;const out:IndicatorPoint[]=[];for(let i=0;i<points.length;i++){const p=points[i];if(i<period)value+=p.value;if(i===period-1)value/=period;else if(i>=period){if(kind==='EMA')value=p.value*2/(period+1)+value*(1-2/(period+1));else{value=0;for(let j=i-period+1;j<=i;j++)value+=points[j].value;value/=period;}}if(i>=period-1)out.push({time:p.time,value});}return out;}
export function histogramState(value:number,previous=0):string{return value>=0?(value>=previous?'positive_rising':'positive_falling'):(value>=previous?'negative_rising':'negative_falling');}
export function multiIndicator(rows:Candle[],c:IndicatorConfig,interval:Interval):Record<string,IndicatorPoint[]>{
 const names=c.kind==='MACD'?['macd','signal','histogram']:['basis','upper','lower'];const empty=Object.fromEntries(names.map(n=>[n,[]]));if(!indicatorGrid(rows,interval))return empty;
 const p=c.params!,points=rows.map(r=>({time:r.time,value:sourceValue(r,c.source as PriceSource)}));
 if(c.kind==='MACD'){const fast=new Map(smoothPoints(points,Number(p.fast_period),String(p.oscillator_type)).map(r=>[r.time,r.value]));const macd=smoothPoints(points,c.period,String(p.oscillator_type)).map(r=>({time:r.time,value:fast.get(r.time)!-r.value}));const signal=smoothPoints(macd,Number(p.signal_period),String(p.signal_type));const values=new Map(macd.map(r=>[r.time,r.value]));let previous=0;const histogram=signal.map(r=>{const value=values.get(r.time)!-r.value,color=c.style!.colors[histogramState(value,previous)];previous=value;return {time:r.time,value,color};});return {macd,signal,histogram};}
 const means=new Map(smoothPoints(points,c.period,String(p.basis_type)).map(r=>[r.time,r.value]));const result:Record<string,IndicatorPoint[]>={basis:[],upper:[],lower:[]};for(let i=c.period-1;i<rows.length;i++){let mean=0,variance=0;for(let j=i-c.period+1;j<=i;j++)mean+=points[j].value;mean/=c.period;for(let j=i-c.period+1;j<=i;j++)variance+=(points[j].value-mean)**2;const deviation=Math.sqrt(variance/c.period)*Number(p.deviation),basis=means.get(rows[i].time)!,time=rows[i].time+Number(p.offset)*steps[interval];for(const [key,value] of [['basis',basis],['upper',basis+deviation],['lower',basis-deviation]] as const)result[key].push({time,value});}return result;
}
export function indicatorOutputs(rows:Candle[],c:IndicatorConfig,interval:Interval,symbol=''):{id:string;name:string;points:IndicatorPoint[]}[]{const multi=c.kind==='MACD'||c.kind==='BB',data=multi?multiIndicator(rows,c,interval):{value:indicatorSeries(rows,c,interval,symbol)};const labels:Record<string,string>={macd:'Çizgi',signal:'Sinyal',histogram:'Histogram',basis:'Orta',upper:'Üst',lower:'Alt'};return Object.entries(data).map(([key,points])=>({id:c.indicator_id+':'+key,name:multi?c.kind+' '+labels[key]:isVwap(c)?indicatorName(c)+' · '+c.source.toUpperCase():c.kind+' '+c.period+' · '+c.source.toUpperCase(),points}));}
