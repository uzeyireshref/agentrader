import {familyKinds,familyGeometry,validateFamily,isFamily,familyModel,type FamilyKind} from './channelFamily';
import type {Candle} from './types';
import type {ToolKind} from './chartCommands';
import {roundPrice,type Anchor,type Geometry} from './drawings';
import {legacyFibLevels,extensionFibLevels} from './fibonacci';
import {channelBasis,channelValues,isChannel} from './channel';
import {defaultPositionParams,positionMetrics} from './position';
import {displayNumber} from './exactGeometry';

/** A manually panned scale can put zero/negative prices under the pointer. */
export function cursorPrice(price:number|null,tick:string):string|null{
 if(price===null||!Number.isFinite(price)||price<=0)return null;
 try{return roundPrice(price,tick);}catch{return null;}
}

/** Transient geometry only. Never passed to the persistence or history API. */
export function creationPreview(tool:ToolKind,symbol:string,first:Anchor|null,second:Anchor|null,cursor:Anchor|null):Geometry|null{
 if(tool==='cursor'||!cursor)return null;
 const base={symbol,price_source:'LAST_PRICE' as const,label:''};
 if(tool==='line'||tool==='horizontal_ray')return {...base,kind:tool==='line'?'horizontal':'horizontal_ray',...(tool==='horizontal_ray'?{schema:'chart-line/1' as const}:{}),anchors:[cursor]};
 if(['text','note','price_label'].includes(tool))return {...base,kind:tool as 'text'|'note'|'price_label',schema:'chart-annotation/1',text:tool==='text'?'Metin':tool==='note'?'Not':'',anchors:[cursor]};
 if(!first)return null;
 const baseline:Geometry={...base,kind:'trend',anchors:[first,second??cursor]};
 if(familyKinds.includes(tool as FamilyKind)){
  if(tool==='regression_channel'){try{const g=familyGeometry(tool,symbol,[first,cursor]);validateFamily(g);return g;}catch{return baseline;}}
  if(!second)return baseline;
  try{const g=familyGeometry(tool as FamilyKind,symbol,[first,second,cursor]);validateFamily(g);return g;}catch{return baseline;}
 }
 if(tool==='long_plan'||tool==='short_plan'){
  if(!second)return baseline;
  const g:Geometry={...base,kind:tool,schema:'chart-position/1',anchors:[first,{...second,time:cursor.time},cursor],params:defaultPositionParams()};
  try{positionMetrics(g);return g;}catch{return {...baseline,anchors:[first,cursor]};}
 }
 if(tool==='fibonacci'||tool==='fibonacci_extension')return {...base,kind:tool,schema:'chart-fibonacci/1',levels:tool==='fibonacci'?legacyFibLevels:extensionFibLevels,time_scope:tool==='fibonacci'?'bounded':'right',anchors:[first,cursor]};
 return {...base,kind:tool as Geometry['kind'],...(['ray','extended_line'].includes(tool)?{schema:'chart-line/1' as const}:tool==='ruler'?{schema:'chart-ruler/1' as const}:{}),anchors:[first,cursor]};
}

/** Price extent of the finite drawing, including a channel's unanchored corners. */
export function drawingPriceExtent(g:Geometry,rows:Candle[]=[],axis?:import('./channelFamily').FamilyAxis):[number,number]|null{
 try{
  const prices=isFamily(g)?familyModel(g,rows,axis).handles.map(p=>p.y):g.anchors.map(a=>Number(a.price));
  if(isChannel(g))for(const a of g.anchors.slice(0,2))prices.push(displayNumber(channelValues(g,a.time).other));
  if(!prices.length||prices.some(p=>!Number.isFinite(p)||p<=0))return null;
  return [Math.min(...prices),Math.max(...prices)];
 }catch{return null;}
}
