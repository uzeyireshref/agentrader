import {validateFibonacci} from './fibonacci';
import {isFamily,isPitchfork,validateFamily} from './channelFamily';
import {isChannel,channelBasis} from './channel';
import {isPosition,positionMetrics} from './position';
import {snapPrice,decimalRational,subtract} from './exactGeometry';
import type {Candle} from './types';
import {timeToLogical,type Geometry} from './drawings.ts';
/** One pointer owns a gesture; all cancellation paths share one cleanup. */
export class DragGuard {
 private owner:number|null=null;
 private cleanup:(()=>void)|null=null;
 begin(pointer:number,cleanup:()=>void):boolean {if(this.owner!==null)return false;this.owner=pointer;this.cleanup=cleanup;return true;}
 owns(pointer:number):boolean{return this.owner===pointer;}
 end(pointer:number):boolean {if(!this.owns(pointer))return false;this.cancel();return true;}
 cancel():void {const cleanup=this.cleanup;this.owner=null;this.cleanup=null;cleanup?.();}
}
/** A hidden document must abandon an uncommitted gesture even without window blur. */
export function installDragCancellation(cancel:()=>void):()=>void{
 const hidden=()=>{if(document.hidden)cancel();};
 const key=(event:KeyboardEvent)=>{if(event.key==='Escape')cancel();};
 window.addEventListener('blur',cancel);window.addEventListener('keydown',key);document.addEventListener('visibilitychange',hidden);
 return()=>{window.removeEventListener('blur',cancel);window.removeEventListener('keydown',key);document.removeEventListener('visibilitychange',hidden);};
}
export function logicalToTime(rows:Candle[],logical:number,step:number):number|null{
 if(!rows.length||!Number.isFinite(logical))return null;
 if(rows.length===1)return Math.round(rows[0].time+logical*step);
 const i=Math.max(0,Math.min(rows.length-2,Math.floor(logical)));
 return Math.round(rows[i].time+(logical-i)*(rows[i+1].time-rows[i].time));
}
export function moveGeometry(geometry:Geometry,rows:Candle[],logicalDelta:number,priceDelta:number,tick:number|string,step:number,anchor:number|null):Geometry|null{
 if(!Number.isFinite(priceDelta)||!Number.isFinite(logicalDelta))return null;
 if(isFamily(geometry)&&anchor!==null){
  try{
   const points=geometry.anchors.map(a=>({...a})),[a,b,c]=points;
   const time=(value:number)=>{const x=timeToLogical(rows,value);if(x===null)throw Error('GRID');const t=logicalToTime(rows,x+Math.round(logicalDelta),step);if(t===null)throw Error('GRID');return t;};
   const price=(value:string,delta=priceDelta)=>snapPrice(value,String(tick),String(delta));
   if(isPitchfork(geometry.kind)){points[anchor]={time:time(points[anchor].time),price:price(points[anchor].price)};}
   else if(geometry.kind==='regression_channel'){points[anchor]={...points[anchor],time:time(points[anchor].time)};}
   else if(anchor===0){points[0]={time:time(a.time),price:price(a.price)};}
   else if(anchor===1){points[1]={time:time(b.time),price:price(b.price)};points[2]={time:points[1].time,price:geometry.kind==='disjoint_channel'?price(c.price,-priceDelta):geometry.kind==='parallel_channel'?price(c.price):c.price};}
   else if(anchor===2){points[1]={...b,time:time(b.time)};points[2]={time:points[1].time,price:price(c.price)};}
   else if(anchor===3){points[0]={time:time(a.time),price:geometry.kind==='disjoint_channel'?price(a.price,-priceDelta):a.price};if(geometry.kind!=='disjoint_channel')points[2]={...c,price:price(c.price)};}
   const result={...geometry,anchors:points};validateFamily(result);return result;
  }catch{return null;}
 }
 let anchors;try{anchors=geometry.anchors.map((a,i)=>{
  if(anchor!==null&&anchor!==i)return a;
  const logical=rows.length===1?(a.time-rows[0].time)/step:timeToLogical(rows,a.time);
  const time=geometry.kind==='horizontal'?a.time:logical===null?null:logicalToTime(rows,logical+Math.round(logicalDelta),step);
  return {time:time??0,price:snapPrice(a.price,String(tick),String(priceDelta))};
 });}catch{return null;}
 if(anchors.some(a=>!Number.isSafeInteger(a.time)||a.time<=0||a.time>32503680000||!Number.isFinite(Number(a.price))||Number(a.price)<=0))return null;
 if(!isFamily(geometry)&&geometry.kind!=='ruler'&&anchors.length===2&&(anchors[0].time===anchors[1].time||(!['ray','extended_line'].includes(geometry.kind)&&subtract(decimalRational(anchors[0].price),decimalRational(anchors[1].price)).n===0n)))return null;
 if(isPosition(geometry)&&anchor!==null){if(anchor===1)anchors[2]={...anchors[2],time:anchors[1].time};if(anchor===2)anchors[1]={...anchors[1],time:anchors[2].time};}
 const result={...geometry,anchors};if(isPosition(result)){try{positionMetrics(result);}catch{return null;}}if(isChannel(result)){try{channelBasis(result);}catch{return null;}}try{validateFibonacci(result);validateFamily(result);}catch{return null;}return result;
}


/** Transform transient prices into the native display axis; persist only tick-snapped real prices. */
export function moveFamilyOnAxis(g:Geometry,rows:Candle[],logicalDelta:number,axisDelta:number,tick:number|string,step:number,anchor:number|null,toAxis:(p:number)=>number,fromAxis:(p:number)=>number):Geometry|null{
 if(!isFamily(g))return null;
 try{const offset=1000000,proxy={...g,anchors:g.anchors.map(a=>({...a,price:String(offset+toAxis(Number(a.price)))}))};
 const moved=moveGeometry(proxy,rows,logicalDelta,axisDelta,'0.000000001',step,anchor);if(!moved)return null;
 const result={...g,anchors:moved.anchors.map((a,i)=>({time:a.time,price:Number(a.price)===Number(proxy.anchors[i].price)?g.anchors[i].price:snapPrice(String(fromAxis(Number(a.price)-offset)),String(tick),'0')}))};validateFamily(result);return result;
 }catch{return null;}
}
