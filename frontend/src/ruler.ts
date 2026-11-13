import {decimalRational,subtract,divide,multiply,rational,exactDecimal,type Rational} from './exactGeometry';
import type {Geometry} from './drawings';
import {steps} from './evidence';
import type {Interval} from './types';
export type ExactValue={numerator:string;denominator:string;decimal:string|null};
export type Measurement={schema:'chart-ruler-measurement/1';price_change:ExactValue;percent_change:ExactValue;tick_change:ExactValue;elapsed_seconds:number;duration_seconds:number;bars:{state:'UNAVAILABLE'|'COMPLETE'|'GAPPED';reason:string|null;count:number|null;intervals:ExactValue|null;missing_bars:number|null};live_eligible:false;order_authority:false};
function price(text:string):Rational{const p=decimalRational(text);if(p.n<=0n||p.n*10n**30n<p.d||p.n>=p.d*10n**31n)throw Error('INVALID_DECIMAL_PRICE');return p;}
function timestamp(t:number){if(!Number.isSafeInteger(t)||t<=0||t>32503680000)throw Error('INVALID_UTC_SECONDS');}
export function exactValue(p:Rational):ExactValue{return {numerator:p.n.toString(),denominator:p.d.toString(),decimal:exactDecimal(p)};}
function logical(times:number[],t:number):Rational{
 if(times.length===1)return rational(0n);let low=0,high=times.length-1;while(low+1<high){const mid=(low+high)>>>1;if(times[mid]<=t)low=mid;else high=mid;}
 const i=Math.min(low,times.length-2);return rational(BigInt(i)*BigInt(times[i+1]-times[i])+BigInt(t-times[i]),BigInt(times[i+1]-times[i]));
}
export function measureRuler(value:Geometry,tick:string,times:number[]|null,interval:Interval):Measurement{
 if(value.kind!=='ruler'||value.schema!=='chart-ruler/1'||value.anchors.length!==2||typeof value.label!=='string'||value.label.length>64||!/^[A-Z0-9]{2,20}USDT$/.test(value.symbol)||value.price_source!=='LAST_PRICE')throw Error('INVALID_GEOMETRY');
 if(!Object.hasOwn(steps,interval))throw Error('UNSUPPORTED_INTERVAL');
 const [a,b]=value.anchors;if([a,b].some(v=>typeof v.price!=='string'||v.price.length>64))throw Error('INVALID_GEOMETRY');timestamp(a.time);timestamp(b.time);const p0=price(a.price),p1=price(b.price),stepPrice=price(tick),delta=subtract(p1,p0);
 let bars:Measurement['bars']={state:'UNAVAILABLE',reason:'GRID_UNAVAILABLE',count:null,intervals:null,missing_bars:null};
 if(times!==null){
  if(!Array.isArray(times)||times.length<1||times.length>4000||times.some(t=>!Number.isSafeInteger(t)||t<=0||t>32503680000)||times.some((t,i)=>i>0&&t<=times[i-1]))throw Error('INVALID_GRID');
  const step=steps[interval],anchor=interval==='1w'?345600:0;
  if(times.some(t=>((t-anchor)%step+step)%step!==0))throw Error('GRID_BUCKET_MISMATCH');
  const low=Math.min(a.time,b.time),high=Math.max(a.time,b.time);
  if(low<times[0]||high>times.at(-1)!)bars.reason='GRID_OUT_OF_RANGE';
  else{
   const distance=subtract(logical(times,b.time),logical(times,a.time));const count=times.filter(t=>low<=t&&t<=high).length,first=Math.ceil((low-anchor)/step)*step+anchor,last=Math.floor((high-anchor)/step)*step+anchor,missing=Math.max(0,(last-first)/step+1)-count;
   bars={state:missing?'GAPPED':'COMPLETE',reason:missing?'GRID_GAP':null,count,intervals:exactValue(rational(distance.n<0n?-distance.n:distance.n,distance.d)),missing_bars:missing};
  }
 }
 return {schema:'chart-ruler-measurement/1',price_change:exactValue(delta),percent_change:exactValue(multiply(divide(delta,p0),rational(100n))),tick_change:exactValue(divide(delta,stepPrice)),elapsed_seconds:b.time-a.time,duration_seconds:Math.abs(b.time-a.time),bars,live_eligible:false,order_authority:false};
}
export function exactText(value:ExactValue):string{return value.decimal??value.numerator+'/'+value.denominator;}
export function durationText(seconds:number):string{const d=Math.floor(seconds/86400),h=Math.floor(seconds%86400/3600),m=Math.floor(seconds%3600/60),s=seconds%60;return [d?d+'g':'',h?h+'sa':'',m?m+'dk':'',s||!seconds?s+'sn':''].filter(Boolean).join(' ');}
function compact(value:ExactValue):string{const text=exactText(value);return text.length>19?text.slice(0,18)+'…':text;}
export function rulerSummary(m:Measurement):[string,string]{return ['Δ '+compact(m.price_change)+' · '+compact(m.percent_change)+'% · '+compact(m.tick_change)+' tick',(m.elapsed_seconds<0?'Geri · ':'')+durationText(m.duration_seconds)+' · '+(m.bars.count===null?'Mum: geçmiş gerekli':m.bars.count+' mum'+(m.bars.state==='GAPPED'?' · boşluk var':''))];}
