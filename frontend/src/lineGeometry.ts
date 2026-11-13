import {add,subtract,multiply,divide,decimalRational,rational,type Rational} from './exactGeometry';
import type {Geometry} from './drawings';
import type {Candle,Interval} from './types';
import {steps} from './evidence';
export const isExtendedLine=(g:Geometry)=>['ray','extended_line','horizontal_ray'].includes(g.kind);
export function verifiedLineGrid(g:Geometry,rows:Candle[],interval:Interval):boolean{
 const step=steps[interval],base=interval==='1w'?345600:0;
 return rows.length>=2&&rows.every((r,i)=>(r.time-base)%step===0&&(!i||r.time-rows[i-1].time===step))&&g.anchors.every(a=>a.time>=rows[0].time&&a.time<=rows.at(-1)!.time);
}
export function linePriceAt(g:Geometry,rows:Candle[],time:number,interval:Interval):Rational{
 const [a,b]=g.anchors;if(!Number.isSafeInteger(time)||time<=0)throw Error('INVALID_UTC_SECONDS');
 if(g.kind==='horizontal_ray'){if(time<a.time)throw Error('OUT_OF_SCOPE');return decimalRational(a.price);}
 if(!verifiedLineGrid(g,rows,interval))throw Error('GRID_UNAVAILABLE');
 if(time<rows[0].time||time>rows.at(-1)!.time)throw Error('GRID_OUT_OF_RANGE');
 if(g.kind==='ray'&&(time-a.time)*(b.time-a.time)<0||g.kind==='trend'&&(time<Math.min(a.time,b.time)||time>Math.max(a.time,b.time)))throw Error('OUT_OF_SCOPE');
 const value=add(decimalRational(a.price),multiply(subtract(decimalRational(b.price),decimalRational(a.price)),divide(rational(BigInt(time-a.time)),rational(BigInt(b.time-a.time)))));
 if(value.n<=0n)throw Error('NON_POSITIVE_PROJECTION');return value;
}
type Point={x:number;y:number};
/** Clip in screen space, bounded also by the known loaded grid, never fabricate bars. */
export function clipExtendedLine(a:Point,b:Point,width:number,height:number,left:number,right:number,kind:Geometry['kind']):[Point,Point]|null{
 if(![a.x,a.y,b.x,b.y,width,height,left,right].every(Number.isFinite))return null;
 let low=kind==='extended_line'?-Infinity:0,high=Infinity;const dx=b.x-a.x,dy=b.y-a.y;
 for(const [origin,delta,min,max] of [[a.x,dx,Math.max(0,left),Math.min(width,right)],[a.y,dy,0,height]]){
  if(min>max)return null;if(delta===0){if(origin<min||origin>max)return null;continue;}
  const u=(min-origin)/delta,v=(max-origin)/delta;low=Math.max(low,Math.min(u,v));high=Math.min(high,Math.max(u,v));
 }
 if(low>high||!Number.isFinite(low)||!Number.isFinite(high))return null;return [{x:a.x+dx*low,y:a.y+dy*low},{x:a.x+dx*high,y:a.y+dy*high}];
}
