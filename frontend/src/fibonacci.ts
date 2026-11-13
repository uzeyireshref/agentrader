import {decimalRational,fibonacciPrice,rational,subtract,type Rational} from './exactGeometry';
import type {Geometry} from './drawings';
export const legacyFibLevels=['0','0.236','0.382','0.5','0.618','0.786','1'];
export const extensionFibLevels=['0','1','1.272','1.618','2','2.618'];
export const isFibonacci=(g:Geometry)=>g.kind==='fibonacci'||g.kind==='fibonacci_extension';
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
export const fibLevels=(g:Geometry)=>g.schema==='chart-fibonacci/1'?g.levels??[]:legacyFibLevels;
export function validateFibonacci(g:Geometry){if(!isFibonacci(g)||g.schema!=='chart-fibonacci/1')return;if(!['bounded','right','unbounded'].includes(g.time_scope??''))throw Error('Fibonacci zaman kapsamını seç.');normalizeFibLevels(g.levels??[]);}
export function fibValue(g:Geometry,ratio:string):Rational{
 const value=fibonacciPrice(g.anchors[0].price,g.anchors[1].price,ratio);if(value.n<=0n)throw Error('NON_POSITIVE_LEVEL');return value;
}
export const tryFibValue=(g:Geometry,ratio:string)=>{try{return fibValue(g,ratio);}catch{return null;}};
