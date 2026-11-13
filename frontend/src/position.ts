import {decimalRational as dec,add,subtract,multiply,divide,rational,displayNumber,type Rational} from './exactGeometry';
import type {Geometry} from './drawings';
export const isPosition=(g:Geometry)=>g.kind==='long_plan'||g.kind==='short_plan';
export const defaultPositionParams=()=>({risk_budget:null as string|null,fee_bps:'0',slippage_bps:'0'});
const read=(s:string,positive=false)=>{if(typeof s!=='string'||s.length>128)throw Error('Geçerli bir ondalık sayı gir.');const n=dec(s);if(n.n<0n||(positive&&n.n===0n)||subtract(n,rational(10n**31n)).n>=0n||n.n!==0n&&subtract(n,rational(1n,10n**30n)).n<0n)throw Error('Geçerli pozitif bir sayı gir.');return n;};
export function positionMetrics(g:Geometry){
 if(!isPosition(g)||g.schema!=='chart-position/1'||g.anchors.length!==3||!g.params)throw Error('Plan verisi geçersiz.');
 const [a,b,c]=g.anchors;if(g.anchors.some(a=>!Number.isSafeInteger(a.time)||a.time<=0||a.time>32503680000))throw Error('Geçerli bir UTC zamanı gir.');if(a.time>=b.time||b.time!==c.time)throw Error('Plan bitiş zamanı başlangıçtan sonra olmalı.');
 const [entry,stop,target]=g.anchors.map(a=>read(a.price,true)),direction=rational(g.kind==='long_plan'?1n:-1n),one=rational(1n);
 const gross_risk=multiply(direction,subtract(entry,stop)),gross_reward=multiply(direction,subtract(target,entry));
 if(gross_risk.n<=0n||gross_reward.n<=0n)throw Error(g.kind==='long_plan'?'Long için stop < giriş < hedef olmalı.':'Short için hedef < giriş < stop olmalı.');
 const feeBps=read(g.params.fee_bps),slipBps=read(g.params.slippage_bps);
 if(subtract(feeBps,rational(1000n)).n>0n||subtract(slipBps,rational(1000n)).n>0n)throw Error('Ücret ve kayma 0–1000 baz puan aralığında olmalı.');
 const fee=divide(feeBps,rational(10000n)),slip=divide(slipBps,rational(10000n));
 const entry_fill=multiply(entry,add(one,multiply(direction,slip))),stop_fill=multiply(stop,subtract(one,multiply(direction,slip))),target_fill=multiply(target,subtract(one,multiply(direction,slip)));
 const net_risk=add(multiply(direction,subtract(entry_fill,stop_fill)),multiply(fee,add(entry_fill,stop_fill)));
 const net_reward=subtract(multiply(direction,subtract(target_fill,entry_fill)),multiply(fee,add(entry_fill,target_fill)));
 const loss_budget=g.params.risk_budget===null?null:read(g.params.risk_budget,true),quantity=loss_budget===null?null:divide(loss_budget,net_risk);
 return {gross_risk,gross_reward,gross_rr:divide(gross_reward,gross_risk),risk_percent:multiply(divide(gross_risk,entry),rational(100n)),reward_percent:multiply(divide(gross_reward,entry),rational(100n)),net_risk,net_reward,net_rr:divide(net_reward,net_risk),entry_fill,stop_fill,target_fill,quantity,notional:quantity===null?null:multiply(quantity,entry_fill),loss_budget,target_pnl:quantity===null?null:multiply(quantity,net_reward)};
}
export const positionText=(v:Rational|null)=>{if(v===null)return '—';const text=displayNumber(v).toLocaleString('tr-TR',{maximumFractionDigits:6});const shown=dec(text.replace(/\./g,'').replace(',','.'));return (subtract(shown,v).n!==0n?'≈ ':'')+text;};
