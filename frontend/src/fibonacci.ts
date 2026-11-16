import {decimalRational,fibonacciPrice,rational,subtract,add,multiply,type Rational} from './exactGeometry';
import type {Geometry} from './drawings';
export const legacyFibLevels=['0','0.236','0.382','0.5','0.618','0.786','1'];
export const extensionFibLevels=['0','1','1.272','1.618','2','2.618'];
export const isFibonacci=(g:Geometry)=>g.kind==='fibonacci'||g.kind==='fibonacci_extension'||g.kind==='fibonacci_projection';
export function ratioText(value:string):string{
 if(typeof value!=='string'||value.length>32||!/^[-+]?\d+(?:\.\d{1,12})?$/.test(value))throw Error('Oran en fazla 12 ondalık basamaklı sayı olmalı.');
 const r=decimalRational(value);if(subtract(r,rational(10n)).n>0n||subtract(r,rational(-10n)).n<0n)throw Error('Oranlar −10 ile 10 arasında olmalı.');
 const [whole,fraction='']=value.replace(/^[-+]/,'').split('.'),tail=fraction.replace(/0+$/,'');
 return r.n===0n?'0':(r.n<0n?'-':'')+BigInt(whole).toString()+(tail?'.'+tail:'');
}
export function normalizeFibLevels(values:string[]):string[]{
 if(values.length<2||values.length>24)throw Error('2–24 seviye gir.');const normalized=values.map(ratioText);
 if(new Set(normalized).size!==normalized.length)throw Error('Aynı oran birden fazla kez kullanılamaz.');return normalized;
}
export const parseFibLevels=(text:string)=>normalizeFibLevels(text.split(/[;\n]+/).map(s=>s.trim().replace(',','.')).filter(Boolean));
export const fibLevels=(g:Geometry)=>(g.schema==='chart-fibonacci/1'||g.schema==='chart-fibonacci-projection/1')?g.levels??[]:legacyFibLevels;
export function validateFibonacci(g:Geometry){if(!isFibonacci(g)||!['chart-fibonacci/1','chart-fibonacci-projection/1'].includes(g.schema??''))return;if(!['bounded','right','unbounded'].includes(g.time_scope??''))throw Error('Fibonacci zaman kapsamını seç.');normalizeFibLevels(g.levels??[]);if(g.kind==='fibonacci_projection'){if(g.basis!=='PRICE_DELTA'||g.anchors.length!==3||g.anchors[0].time===g.anchors[1].time||subtract(decimalRational(g.anchors[0].price),decimalRational(g.anchors[1].price)).n===0n||g.time_scope==='bounded'&&g.anchors[2].time+Math.abs(g.anchors[1].time-g.anchors[0].time)>32503680000)throw Error('Projection A/B hareketi ve C tabanını kontrol et.');}}
export function fibValue(g:Geometry,ratio:string):Rational{
 const value=g.kind==='fibonacci_projection'?add(decimalRational(g.anchors[2].price),multiply(subtract(decimalRational(g.anchors[1].price),decimalRational(g.anchors[0].price)),decimalRational(ratio))):fibonacciPrice(g.anchors[0].price,g.anchors[1].price,ratio);return value;
}
export const tryFibValue=(g:Geometry,ratio:string)=>{try{return fibValue(g,ratio);}catch{return null;}};

export function reverseFibAnchors<T>(values:T[],projection:boolean):T[]{return projection?[values[1],values[0],...values.slice(2)]:[...values].reverse();}
