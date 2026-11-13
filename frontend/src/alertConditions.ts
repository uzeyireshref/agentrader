import type {ChannelPolicy} from './alertChannels';
import type {AlertSchedule} from './alertSchedule';
import type {IndicatorConfig} from './indicatorConfig';
import type {Geometry} from './drawings';
export type Operand={type:'market';field:string}|{type:'value';value:string}|{type:'indicator';config:IndicatorConfig;output:string}|{type:'drawing';geometry:Geometry;output:string;ratio:string|null};
export type Condition={interval?:string;left:Operand;operator:string;right:Operand;upper:Operand|null;bars:number};
export type AlertDefinition={schema:'technical-alert/2'|'technical-alert/3'|'technical-alert/4';evaluation?:'intrabar';notification_schedule?:AlertSchedule;notification_channels?:ChannelPolicy;name:string;symbol:string;interval:string;match:'all'|'any';conditions:Condition[];frequency:'once'|'bar_close'|'bar'|'minute';expires_at:number|null;message:string};
export const operators:Record<string,string>={cross:'Kesişiyor',cross_up:'Yukarı kesiyor',cross_down:'Aşağı kesiyor',above:'Büyüktür',below:'Küçüktür',equal:'Eşittir',not_equal:'Eşit değildir',inside:'Kanal içinde',outside:'Kanal dışında',enter:'Kanala giriyor',exit:'Kanaldan çıkıyor',move_up:'Yükseliyor · değer',move_down:'Düşüyor · değer',move_up_pct:'Yükseliyor · %',move_down_pct:'Düşüyor · %',rising:'Ardışık yükseliyor',falling:'Ardışık düşüyor'};
export const marketNames:Record<string,string>={close:'Fiyat · Kapanış',open:'Açılış',high:'En yüksek',low:'En düşük',hl2:'HL2',hlc3:'HLC3',ohlc4:'OHLC4',volume:'Hacim',quote_volume:'İşlem hacmi · USDT'};
export const defaultCondition=():Condition=>({left:{type:'market',field:'close'},operator:'cross_up',right:{type:'value',value:''},upper:null,bars:1});
export const isBand=(op:string)=>['inside','outside','enter','exit'].includes(op);
export const isMovement=(op:string)=>op.startsWith('move_')||['rising','falling'].includes(op);
export function normalizeDefinition(d:any):AlertDefinition{return ['technical-alert/2','technical-alert/3','technical-alert/4'].includes(d.schema)?structuredClone(d):{schema:'technical-alert/2',name:d.name,symbol:d.symbol,interval:d.interval,match:'all',conditions:[{...defaultCondition(),operator:d.operator,right:{type:'value',value:d.price}}],frequency:d.frequency,expires_at:d.expires_at,message:d.message,...(d.notification_schedule?{notification_schedule:structuredClone(d.notification_schedule)}:{}),...(d.notification_channels?{notification_channels:structuredClone(d.notification_channels)}:{})};}
export const outputNames:Record<string,string>={value:'Değer',basis:'Orta bant',upper:'Üst bant',lower:'Alt bant',middle:'Orta',macd:'MACD',signal:'Sinyal',histogram:'Histogram'};
export function operandName(o:Operand):string{return o.type==='value'?o.value||'Değer':o.type==='market'?marketNames[o.field]:o.type==='indicator'?`${o.config.kind} ${o.config.period} · ${outputNames[o.output]??o.output}`:`${o.geometry.label||o.geometry.kind} · ${o.ratio??outputNames[o.output]??o.output}`;}

export function alarmPayload(draft:AlertDefinition,name:string):AlertDefinition{
 const {evaluation,...base}=draft;
 if(evaluation==='intrabar')return {...base,name,schema:'technical-alert/4',evaluation,conditions:draft.conditions.map(c=>({...c,interval:c.interval??draft.interval}))};
 return draft.conditions.some(c=>c.interval)?{...base,name,schema:'technical-alert/3',conditions:draft.conditions.map(c=>({...c,interval:c.interval??draft.interval}))}:{...base,name,schema:'technical-alert/2'};
}
