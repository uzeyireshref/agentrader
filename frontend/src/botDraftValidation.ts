import {draftError,type BotDraft} from './botPrototype';
export function draftFieldErrors(d:BotDraft):Record<string,string>{
 const errors:Record<string,string>={};
 const positive=(key:string,value:string|undefined)=>{
  if(!value||!/^\d+(\.\d+)?$/.test(value)||!Number.isFinite(Number(value))||Number(value)<=0)
   errors[key]='Sıfırdan büyük bir sayı girin. Ondalık ayırıcı olarak nokta kullanın.';
 };
 positive('entry',d.entry);positive('stop',d.stop);if(d.kind!=='NEUTRAL')positive('target',d.target);
 if(d.kind==='SINGLE')positive('amount',d.amount);
 else {
  for(const key of ['lower','upper','budget'] as const)positive('grid.'+key,d.grid?.[key]);
  if(d.kind==='NEUTRAL'){positive('grid.upperStop',d.grid?.upperStop);positive('grid.longPercent',d.grid?.longPercent);}
  const count=d.grid?.intervals??'';
  if(!/^\d+$/.test(count)||Number(count)<2||Number(count)>(d.kind==='NEUTRAL'?20:100))errors['grid.intervals']=`2–${d.kind==='NEUTRAL'?20:100} arasında tam sayı girin.`;
  if(!errors['grid.lower']&&!errors['grid.upper']&&Number(d.grid?.upper)<=Number(d.grid?.lower))errors['grid.upper']='Üst bant alt banttan büyük olmalı.';
  if(!errors.entry&&!errors['grid.lower']&&!errors['grid.upper']&&!(Number(d.grid?.lower)<=Number(d.entry)&&Number(d.entry)<Number(d.grid?.upper)))errors.entry='Referans fiyatı grid bandında olmalı; üst sınır dahil değildir.';
  if(!errors.stop&&!errors.entry&&!errors['grid.lower']){
   if(d.kind==='NEUTRAL'){if(Number(d.stop)>=Number(d.grid?.lower))errors.stop='Alt stop fiyatı alt bandın altında olmalı.';}
   else if(d.side==='Long'?Number(d.stop)>=Number(d.entry):Number(d.stop)<=Number(d.entry))errors.stop=d.side==='Long'?'Long stop fiyatı referansın altında olmalı.':'Short stop fiyatı referansın üstünde olmalı.';
  }
  if(d.kind==='NEUTRAL'){
   if(!errors['grid.upperStop']&&!errors['grid.upper']&&Number(d.grid?.upperStop)<=Number(d.grid?.upper))errors['grid.upperStop']='Üst stop fiyatı üst bandın üstünde olmalı.';
   if(!errors['grid.longPercent']&&Number(d.grid?.longPercent)>=100)errors['grid.longPercent']='LONG payı 0 ile 100 arasında olmalı; iki yöne de pay ayrılmalı.';
  }else if(!errors.target&&!errors['grid.lower']&&!errors['grid.upper']){
   if(d.side==='Long'?Number(d.target)<Number(d.grid?.upper):Number(d.target)>Number(d.grid?.lower))errors.target=d.side==='Long'?'Son hedef üst bantta veya üstünde olmalı.':'Short son hedef alt bantta veya altında olmalı.';
  }
 }
 if(d.kind==='SINGLE'){
  if(!errors.entry&&!errors.stop&&(d.side==='Long'?Number(d.stop)>=Number(d.entry):Number(d.stop)<=Number(d.entry)))errors.stop=d.side==='Long'?'Long stop fiyatı girişin altında olmalı.':'Short stop fiyatı girişin üstünde olmalı.';
  if(!errors.entry&&!errors.target&&(d.side==='Long'?Number(d.target)<=Number(d.entry):Number(d.target)>=Number(d.entry)))errors.target=d.side==='Long'?'Long hedef fiyatı girişin üstünde olmalı.':'Short hedef fiyatı girişin altında olmalı.';
 }
 return errors;
}
export function draftValidation(d:BotDraft){
 const fields=draftFieldErrors(d);
 return {fields,message:Object.keys(fields).length?'İşaretli alanları düzeltin.':draftError(d)};
}
