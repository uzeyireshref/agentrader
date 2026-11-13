import type {FamilyOptions} from './channelFamily';
import {snapPrice} from './exactGeometry';
import type {Candle,Interval} from './types';
export type Anchor={time:number;price:string};
export type Geometry={options?:FamilyOptions;text?:string;levels?:string[];schema?:'chart-channel-family/1'|'chart-annotation/1'|'chart-fibonacci/1'|'chart-channel/1'|'chart-position/1'|'chart-ruler/1'|'chart-line/1'|'chart-zone/1';params?:{risk_budget:string|null;fee_bps:string;slippage_bps:string};kind:'flat_channel'|'disjoint_channel'|'regression_channel'|'pitchfork'|'schiff_pitchfork'|'modified_schiff_pitchfork'|'inside_pitchfork'|'text'|'note'|'price_label'|'fibonacci_extension'|'parallel_channel'|'long_plan'|'short_plan'|'horizontal'|'zone'|'trend'|'fibonacci'|'ruler'|'ray'|'extended_line'|'horizontal_ray';time_scope?:'bounded'|'right'|'unbounded';symbol:string;price_source:'LAST_PRICE';anchors:Anchor[];label:string};
export type Management={schema:"chart-management/1";locked:boolean;hidden:boolean;intervals:Interval[];color:string|null;line_width:1|2|3;line_style:"default"|"solid"|"dashed"|"dotted"};
export const drawingManagement=(d?:Drawing):Management=>({schema:"chart-management/1",locked:false,hidden:false,intervals:[],color:null,line_width:1,line_style:"default",...d?.management});
export const drawingVisible=(d:Drawing,interval:Interval)=>{const m=drawingManagement(d);return !m.hidden&&(!m.intervals.length||m.intervals.includes(interval));};
export type Drawing={management?:Management;drawing_id:string;revision:number;workspace_id:string;geometry:Geometry;deleted:boolean;updated_at:number};
export type Workspace={revision:number;preferences:{symbol:string;interval:Interval}};
export class DrawingRequestError extends Error {status:number;constructor(status:number){super(status===409?'Çizim başka bir ekranda değişmiş. Son kaydı yükleyip yeniden düzenle.':status===423?'Çizim kilitli. Önce kilidi aç.':status===401?'Yerel erişim oturumu sona ermiş. Yeniden bağlan.':'Kayıt doğrulanamadı. Tekrar dene veya sunucudaki son kaydı yükle.');this.status=status;}}
export async function drawingRequest<T>(path:string,method='GET',data?:unknown,token?:string):Promise<T>{const headers:Record<string,string>={};if(data!==undefined)headers['Content-Type']='application/json';if(token)headers.Authorization='Bearer '+token;const r=await fetch(path,{method,headers,body:data===undefined?undefined:JSON.stringify(data),credentials:'same-origin'});if(!r.ok)throw new DrawingRequestError(r.status);return await r.json() as T;}
export function timeToLogical(rows:Candle[],time:number):number|null{if(!rows.length)return null;if(rows.length===1)return 0;let low=0,high=rows.length-1;while(low+1<high){const mid=(low+high)>>>1;if(rows[mid].time<time)low=mid;else high=mid;}const i=Math.min(low,rows.length-2);const span=rows[i+1].time-rows[i].time;return i+(time-rows[i].time)/span;}
export function pricePrecision(tick:number):number{const [coefficient,exponent]=tick.toString().toLowerCase().split('e');return Math.min(12,Math.max(0,(coefficient.split('.')[1]?.length??0)-Number(exponent??0)));}
export function roundPrice(price:number,tick:number|string):string {return snapPrice(String(price),String(tick));}

/** Engine v5.2 rejects fractional indices; interpolate native integer coordinates. */
export function projectLogical(logical:number,native:(index:number)=>number|null):number|null{
 if(!Number.isFinite(logical))return null;
 const left=Math.floor(logical),fraction=logical-left,a=native(left);
 if(a===null||!Number.isFinite(a))return null;
 if(fraction===0)return a;
 const b=native(left+1);return b===null||!Number.isFinite(b)?null:a+(b-a)*fraction;
}
