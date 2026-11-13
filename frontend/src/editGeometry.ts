import {isAnnotation,annotationText} from './annotations';
import {validateFibonacci} from './fibonacci';
import {isFamily,validateFamily} from './channelFamily';
import {isChannel,channelBasis} from './channel';
import {isPosition,positionMetrics} from './position';
import {onTick} from './exactGeometry';
import type {Geometry} from './drawings';
function decimal(value:string):{units:bigint;places:number}{
 if(value.length>64||!/^\d+(?:\.\d+)?$/.test(value)||!Number.isFinite(Number(value))||Number(value)<=0)throw Error('Fiyat pozitif bir ondalık sayı olmalı.');
 return {units:BigInt(value.replace('.','')),places:value.split('.')[1]?.length??0};
}
function equal(a:ReturnType<typeof decimal>,b:ReturnType<typeof decimal>):boolean{
 const places=Math.max(a.places,b.places);return a.units*10n**BigInt(places-a.places)===b.units*10n**BigInt(places-b.places);
}
export function editGeometry(original:Geometry,label:string,prices:string[],times:string[],tick:string):Geometry{
 if(prices.length!==original.anchors.length||times.length!==prices.length)throw Error('Çizim noktaları yüklenemedi.');
 const values:ReturnType<typeof decimal>[]=[];
 const anchors=original.anchors.map((anchor,i)=>{
  const price=prices[i].trim().replace(',','.');const value=decimal(price);values.push(value);
  // Existing stored levels may predate tick rules; renaming must not change them.
  if(price!==anchor.price){
   try{decimal(tick);}catch{throw Error('Piyasanın fiyat adımı henüz yüklenmedi.');}
   if(!onTick(price,tick))throw Error('Fiyat '+tick+' adımına uymalı.');
  }
  const date=times[i].length===16?times[i]+':00':times[i];
  if(!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$/.test(date))throw Error('Geçerli bir UTC zamanı gir.');
  const ms=Date.parse(date+'Z'),time=ms/1000;
  if(!Number.isSafeInteger(time)||time<=0||time>32503680000||new Date(ms).toISOString().slice(0,19)!==date)throw Error('Geçerli bir UTC zamanı gir.');
  return {...anchor,price,time};
 });
 if(!isFamily(original)&&original.kind!=='ruler'&&anchors.length===2&&(anchors[0].time===anchors[1].time||(!['ray','extended_line'].includes(original.kind)&&equal(values[0],values[1]))))throw Error('İki nokta farklı zaman ve fiyatta olmalı.');
 const result={...original,label,anchors};if(isPosition(result))positionMetrics(result);if(isChannel(result))channelBasis(result);validateFibonacci(result);validateFamily(result);if(isAnnotation(result))result.text=annotationText(result.kind,result.text??'');return result;
}
