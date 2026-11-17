import {decimalRational,add,rational,subtract} from './exactGeometry';
// Browser-only design model. Never an exchange validation or executable plan.
export type GridDraft={lower:string;upper:string;intervals:string;spacing:'ARITHMETIC'|'GEOMETRIC';budget:string;sizing:'NOTIONAL'|'MARGIN'|'MAX_LOSS';upperStop:string;longPercent:string};
export const priceMatches=['OPPONENT','OPPONENT_5','OPPONENT_10','OPPONENT_20','QUEUE','QUEUE_5','QUEUE_10','QUEUE_20'] as const;
export type LimitOptions={tif:'GTC'|'IOC'|'FOK'|'GTX'|'GTD';stp:''|'EXPIRE_MAKER'|'EXPIRE_TAKER'|'EXPIRE_BOTH';expires:string;priceMatch?:typeof priceMatches[number]|''};
export type ExecutionDraft={leverage:string;margin:'ISOLATED'|'CROSSED';positionMode:'one-way'|'hedge';condition:'IMMEDIATE'|'MARK_AT_OR_BELOW'|'MARK_AT_OR_ABOVE';trigger:string;driftBps:string};
export const defaultExecution:ExecutionDraft={leverage:'3',margin:'ISOLATED',positionMode:'hedge',condition:'IMMEDIATE',trigger:'90000',driftBps:'50'};
export type BotDraft={symbol:string;side:'Long'|'Short';kind:'SINGLE'|'GRID'|'NEUTRAL';entry:string;stop:string;target:string;amount:string;grid?:GridDraft;options?:LimitOptions;execution?:ExecutionDraft;orderType?:'LIMIT'|'MARKET';sizing?:'NOTIONAL'|'MARGIN'|'MAX_LOSS';targets?:{price:string;percent:string}[];breakEven?:string;response?:'ACK'|'RESULT';trailing?:{activation:string;distance:string;step:string;nativeStop:boolean};source?:{drawingId:string;revision:number;workspace:string}};
export const defaultGrid:GridDraft={lower:'89000',upper:'91000',intervals:'10',spacing:'ARITHMETIC',budget:'100',sizing:'MARGIN',upperStop:'92000',longPercent:'50'};
export const initialBotDraft:BotDraft={symbol:'BTCUSDT',side:'Long',kind:'SINGLE',entry:'90000',stop:'88000',target:'94000',amount:'100'};
export function draftError(d:BotDraft){
 const executionError=validateExecution(d);if(executionError)return executionError;
 if(d.trailing){const t=d.trailing;
 if(d.kind==='NEUTRAL')return 'NEUTRAL takip stopu desteklenmiyor.';
 if([t.activation,t.distance,t.step].some(v=>!/^\d+(\.\d+)?$/.test(v)||!Number.isFinite(Number(v))||Number(v)<=0)||Number(t.distance)<1||Number(t.distance)>5000||Number(t.step)<1||Number(t.step)>Number(t.distance))return 'Takip mesafesi 1–5000 bps, güncelleme 1–mesafe arasında olmalı.';
 const sign=d.side==='Long'?1:-1,last=d.kind==='SINGLE'&&d.targets?.length?d.targets.at(-1)!.price:d.target;
 if(sign*(Number(t.activation)-Number(d.entry))<0||sign*(Number(last)-Number(t.activation))<=0)return 'Takip aktivasyonu referans ile son hedef arasında olmalı.';
 if(t.nativeStop&&d.kind!=='GRID')return 'Borsada stop yenileme yalnız yönlü GRID içindir.';
 }
 if(d.kind!=='SINGLE')return gridError(d);
 const o=d.options;
 if(d.orderType==='MARKET'&&o)return 'Market emrinde Limit seçenekleri bulunamaz.';
 if(o?.priceMatch&&!priceMatches.includes(o.priceMatch))return 'priceMatch seçimi desteklenmiyor.';
 if(o?.stp&& !['GTC','IOC','GTD'].includes(o.tif))return 'STP yalnız GTC, IOC ve GTD ile kullanılabilir.';
 if(o?.tif==='GTD'&&(!o.expires||!Number.isFinite(Date.parse(o.expires))||Date.parse(o.expires)<=Date.now()+600000))return 'GTD için en az 10 dakika ileride bir son geçerlilik zamanı seçin.';
 const values=[d.entry,d.stop,d.target,d.amount];
 if(values.some(v=>!/^\d+(\.\d+)?$/.test(v)||!Number.isFinite(Number(v))||Number(v)<=0))return 'Fiyat ve miktar alanlarına sıfırdan büyük sayılar girin.';
 const targets=d.targets??[{price:d.target,percent:'100'}];
 if(targets.length<1||targets.length>8)return '1–8 hedef girin.';
 let total=rational(0n),previous=Number(d.entry);
 for(const t of targets){
  if(!/^\d+(\.\d+)?$/.test(t.price)||!Number.isFinite(Number(t.price))||Number(t.price)<=0||!/^\d+(\.\d+)?$/.test(t.percent)||t.percent.length>40||Number(t.percent)<=0)return 'Hedef fiyatları ve payları pozitif olmalı.';
  if(d.side==='Long'?Number(t.price)<=previous:Number(t.price)>=previous)return 'Hedefler işlem yönünde sıralanmalı.';
  previous=Number(t.price);total=add(total,decimalRational(t.percent));
 }
 if(subtract(total,rational(100n)).n!==0n)return 'Hedef payları toplamı tam %100 olmalı.';
 if(d.breakEven&&(!/^\d+$/.test(d.breakEven)||Number(d.breakEven)<1||Number(d.breakEven)>=targets.length))return 'Girişe stop için son hedeften önce geçerli bir hedef seçin.';
 const [entry,stop,target]=values.map(Number);
 if(d.side==='Long'?(stop>=entry||target<=entry):(stop<=entry||target>=entry))return 'Stop ve hedef fiyatlarını seçtiğiniz yöne göre düzenleyin.';
 return '';
}

export function updateBotDraft(draft:BotDraft,patch:Partial<BotDraft>):BotDraft{
 const next={...draft,...patch};
 if(['entry','stop','target','targets','symbol','side','kind'].some(k=>k in patch))next.source=undefined;
 if(patch.targets&&next.breakEven&&Number(next.breakEven)>=patch.targets.length)next.breakEven='';
 if(patch.target&&!patch.targets&&next.targets)next.targets=next.targets.map((t,i)=>i===0?{...t,price:patch.target!}:t);
 if(patch.kind){next.execution={...(draft.execution??defaultExecution),positionMode:patch.kind==='NEUTRAL'?'hedge':(draft.execution??defaultExecution).positionMode,condition:patch.kind==='SINGLE'?'IMMEDIATE':(draft.execution??defaultExecution).condition};}
 if(next.kind!=='SINGLE'){next.targets=undefined;next.breakEven='';next.response=undefined;}
 if(next.kind==='NEUTRAL')next.trailing=undefined;
 if(next.kind==='SINGLE'&&next.trailing)next.trailing={...next.trailing,nativeStop:false};
 if(patch.orderType==='LIMIT'&&next.execution)next.execution={...next.execution,condition:'IMMEDIATE'};
 if(next.kind!=='SINGLE'||next.orderType==='MARKET')next.options=undefined;
 return next;
}

function validateExecution(d:BotDraft){
 const e=d.execution??defaultExecution;
 if(!/^\d+$/.test(e.leverage)||!Number.isSafeInteger(Number(e.leverage))||Number(e.leverage)<1)return 'Kaldıraç pozitif tamsayı olmalı. Hesaba uygun üst sınır preflight ile belirlenir.';
 if(!/^\d+(\.\d+)?$/.test(e.driftBps)||!Number.isFinite(Number(e.driftBps))||Number(e.driftBps)<=0||Number(e.driftBps)>100)return 'Fiyat sapma toleransı 0’dan büyük ve en fazla 100 bps olmalı.';
 if(d.kind==='NEUTRAL'&&e.positionMode!=='hedge')return 'NEUTRAL için hedge modu gerekir; hesap modu otomatik değiştirilmez.';
 if(d.kind==='SINGLE'&&d.orderType!=='MARKET'&&e.condition!=='IMMEDIATE')return 'Koşullu başlatma yalnız Market girişinde desteklenir.';
 if(e.condition!=='IMMEDIATE'){
  if(!/^\d+(\.\d+)?$/.test(e.trigger)||!Number.isFinite(Number(e.trigger))||Number(e.trigger)<=0)return 'Koşullu başlatma için pozitif tetik fiyatı gerekli.';
  const t=Number(e.trigger),stop=Number(d.stop);
  if(d.kind==='NEUTRAL'){
   if(!(stop<t&&t<Number(d.grid?.upperStop)))return 'NEUTRAL tetik fiyatı iki global stop arasında olmalı.';
  }else if(d.side==='Long'?!(stop<t&&t<Number(d.target)):!(Number(d.target)<t&&t<stop))return 'Tetik fiyatı stop ve son hedef arasında olmalı.';
 }
 return '';
}

function gridError(d:BotDraft){
 const g=d.grid;if(!g)return 'Grid parametrelerini doldurun.';
 const fields=[g.lower,g.upper,g.budget,d.entry,d.stop,...(d.kind==='NEUTRAL'?[g.upperStop,g.longPercent]:[d.target])];
 if(fields.some(v=>!/^\d+(\.\d+)?$/.test(v)||!Number.isFinite(Number(v))||Number(v)<=0))return 'Grid fiyatları ve bütçesi pozitif sayılar olmalı.';
 const lo=Number(g.lower),hi=Number(g.upper),ref=Number(d.entry),stop=Number(d.stop),count=Number(g.intervals);
 if(!/^\d+$/.test(g.intervals)||count<2||count>(d.kind==='NEUTRAL'?20:100))return d.kind==='NEUTRAL'?'NEUTRAL 2–20 aralık destekler.':'GRID 2–100 aralık destekler.';
 if(!(lo<=ref&&ref<hi))return 'Referans fiyatı alt sınır dahil, üst sınır hariç grid bandında olmalı.';
 if(d.kind==='NEUTRAL'){
  if(!(stop<lo&&lo<ref&&ref<hi&&hi<Number(g.upperStop)))return 'NEUTRAL stopları bandın dışında, merkez bandın içinde olmalı.';
  if(Number(g.longPercent)>=100)return 'LONG payı %0 ile %100 arasında olmalı; kalan pay SHORT içindir.';
  const step=g.spacing==='ARITHMETIC'?(hi-lo)/count:Math.log(hi/lo)/count;
  const index=g.spacing==='ARITHMETIC'?(ref-lo)/step:Math.log(ref/lo)/step;
  if(!Number.isFinite(index)||Math.abs(index-Math.round(index))>1e-7)return 'Merkez bir iç grid seviyesine denk gelmeli. Kesin tick uyumu backend tarafından doğrulanacak.';
 }else if(d.side==='Long'?!(stop<ref&&Number(d.target)>=hi):!(stop>ref&&Number(d.target)<=lo))return 'GRID stopu yönle uyumlu, son hedefi çıkış bandında veya dışında olmalı.';
 return '';
}
