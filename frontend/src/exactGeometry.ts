/** Exact interaction arithmetic. Number conversion is restricted to display boundaries. */
export type Rational={n:bigint;d:bigint};
function gcd(a:bigint,b:bigint):bigint{a=a<0n?-a:a;while(b){const r=a%b;a=b;b=r;}return a;}
export function rational(n:bigint,d=1n):Rational{if(d===0n)throw Error('Zero denominator');if(d<0n){n=-n;d=-d;}const g=gcd(n,d);return {n:n/g,d:d/g};}
export function decimalRational(text:string):Rational{
 if(typeof text!=='string'||text.length>128||!/^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?$/.test(text))throw Error('Invalid decimal');
 const [base,exponent]=text.toLowerCase().split('e');const exp=Number(exponent??0);if(!Number.isInteger(exp)||Math.abs(exp)>160)throw Error('Invalid decimal');
 const sign=base.startsWith('-')?-1n:1n;const clean=base.replace(/^[-+]/,'');const places=(clean.split('.')[1]?.length??0)-exp;const n=sign*BigInt(clean.replace('.',''));
 return places>=0?rational(n,10n**BigInt(places)):rational(n*10n**BigInt(-places));
}
export const add=(a:Rational,b:Rational)=>rational(a.n*b.d+b.n*a.d,a.d*b.d);
export const subtract=(a:Rational,b:Rational)=>rational(a.n*b.d-b.n*a.d,a.d*b.d);
export const multiply=(a:Rational,b:Rational)=>rational(a.n*b.n,a.d*b.d);
export const divide=(a:Rational,b:Rational)=>rational(a.n*b.d,a.d*b.n);
export function exactDecimal(value:Rational):string|null{
 let d=value.d,a=0,b=0;while(d%2n===0n){d/=2n;a++;}while(d%5n===0n){d/=5n;b++;}if(d!==1n)return null;
 const places=Math.max(a,b),units=(value.n<0n?-value.n:value.n)*2n**BigInt(places-a)*5n**BigInt(places-b),digits=units.toString().padStart(places+1,'0');
 const text=places?(digits.slice(0,-places)+'.'+digits.slice(-places)).replace(/0+$/,'').replace(/\.$/,''):digits;
 return (value.n<0n?'-':'')+text;
}
export function onTick(price:string,tick:string):boolean{const p=decimalRational(price),t=decimalRational(tick);return p.n>0n&&t.n>0n&&(p.n*t.d)%(p.d*t.n)===0n;}
export function snapPrice(price:string,tick:string,delta='0'):string{
 const p=add(decimalRational(price),decimalRational(delta)),t=decimalRational(tick);if(p.n<=0n||t.n<=0n)throw Error('Fiyat ve adım pozitif olmalı.');
 const q=divide(p,t),units=(2n*q.n+q.d)/(2n*q.d);const snapped=multiply(rational(units),t);if(snapped.n<=0n)throw Error('Fiyat pozitif olmalı.');
 const text=exactDecimal(snapped)!;const step=exactDecimal(t)!;const places=step.split('.')[1]?.length??0;
 if(!places)return text;const [whole,fraction='']=text.split('.');return whole+'.'+fraction.padEnd(places,'0');
}
export function fibonacciPrice(first:string,second:string,ratio:string):Rational{return add(decimalRational(first),multiply(subtract(decimalRational(second),decimalRational(first)),decimalRational(ratio)));}
export function displayNumber(value:Rational):number{return Number(value.n)/Number(value.d);}
