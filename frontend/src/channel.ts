import {decimalRational as dec,add,subtract,multiply,divide,rational,type Rational} from './exactGeometry';
import {verifiedLineGrid} from './lineGeometry';
import type {Geometry} from './drawings';
import type {Candle,Interval} from './types';
export const isChannel=(g:Geometry)=>g.kind==='parallel_channel'&&g.schema!=='chart-channel-family/1';
export function channelBasis(g:Geometry){
 if(!isChannel(g)||g.schema!=='chart-channel/1'||g.anchors.length!==3)throw Error('Kanal verisi geçersiz.');
 const [a,b,c]=g.anchors;
 if(g.anchors.some(a=>!Number.isSafeInteger(a.time)||a.time<=0||a.time>32503680000))throw Error('Geçerli bir UTC zamanı gir.');
 if(a.time===b.time)throw Error('Temel çizginin iki zamanı farklı olmalı.');
 if(c.time<Math.min(a.time,b.time)||c.time>Math.max(a.time,b.time))throw Error('Üçüncü nokta temel çizginin zaman aralığında olmalı.');
 const [pa,pb,pc]=g.anchors.map(a=>dec(a.price));if([pa,pb,pc].some(p=>p.n<=0n))throw Error('Kanal fiyatları pozitif olmalı.');
 const slope=divide(subtract(pb,pa),rational(BigInt(b.time-a.time))),offset=subtract(pc,add(pa,multiply(slope,rational(BigInt(c.time-a.time)))));
 if(offset.n===0n)throw Error('Kanal genişliği sıfır olamaz.');
 if(add(pa,offset).n<=0n||add(pb,offset).n<=0n)throw Error('Kanalın iki sınırı da pozitif olmalı.');
 return {pa,slope,offset};
}
export function channelValues(g:Geometry,time:number){
 const {pa,slope,offset}=channelBasis(g),base=add(pa,multiply(slope,rational(BigInt(time-g.anchors[0].time)))),other=add(base,offset);
 const [lower,upper]=offset.n>0n?[base,other]:[other,base];
 return {base,other,lower,upper,middle:divide(add(lower,upper),rational(2n)),width:subtract(upper,lower)};
}
export function channelAt(g:Geometry,rows:Candle[],time:number,interval:Interval){
 if(!Number.isSafeInteger(time)||time<=0)throw Error('INVALID_UTC_SECONDS');
 if(!verifiedLineGrid(g,rows,interval))throw Error('GRID_UNAVAILABLE');
 if(time<Math.min(...g.anchors.slice(0,2).map(a=>a.time))||time>Math.max(...g.anchors.slice(0,2).map(a=>a.time)))throw Error('OUT_OF_SCOPE');
 return channelValues(g,time);
}
export function channelDistance(bounds:{lower:Rational;upper:Rational},price:string){const p=dec(price);if(p.n<=0n)throw Error('Fiyat pozitif olmalı.');const low=subtract(bounds.lower,p),high=subtract(p,bounds.upper);return low.n>0n?low:high.n>0n?high:rational(0n);}
