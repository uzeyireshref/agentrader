import {isDemoMarket} from './marketEnvironment';
import type {Geometry,Management} from './drawings';
export type DrawingPackage={schema:'chart-drawing-package/1';market:Record<string,string>;items:{geometry:Geometry;management:Management;linked_note:{text:string}|null}[]};
const keys=(x:object)=>Object.keys(x).sort().join(',');
export function parseDrawingPackage(text:string,symbol:string,interval:string):DrawingPackage{
 if(new TextEncoder().encode(text).length>524288)throw Error('Paket en fazla 512 KiB olabilir.');
 let value:DrawingPackage;try{value=JSON.parse(text);}catch{throw Error('Geçerli bir çizim paketi JSON metni yapıştır.');}
 if(!value||keys(value)!=='items,market,schema'||value.schema!=='chart-drawing-package/1'||!isDemoMarket(value.market)||keys(value.market)!=='environment,interval,price_type,product,source,symbol')throw Error('Çizim paketi şeması veya kaynak kimliği geçersiz.');
 if(value.market.symbol!==symbol||value.market.interval!==interval)throw Error('Paket '+value.market.symbol+' / '+value.market.interval+' için. Önce bu sembol ve zaman dilimine geç. Fiyatlar otomatik ölçeklenmez.');
 if(!Array.isArray(value.items)||value.items.length<1||value.items.length>20)throw Error('Paket 1–20 çizim içermeli.');
 for(const item of value.items){
  if(!item||keys(item)!=='geometry,linked_note,management'||!item.geometry||item.geometry.symbol!==symbol||item.geometry.price_source!=='LAST_PRICE'||!item.management||keys(item.management)!=='color,hidden,intervals,line_style,line_width,locked,schema')throw Error('Paket geometri/stil alanlarını kontrol et; kimlik, revizyon ve köken aktarılamaz.');
  const note=item.linked_note;if(note!==null&&(!note||keys(note)!=='text'||typeof note.text!=='string'||Array.from(note.text).length>4000||new TextEncoder().encode(note.text).length>16000))throw Error('Bağlı not en fazla 4000 karakter / 16000 UTF-8 bayt olabilir.');
 }
 return value;
}
