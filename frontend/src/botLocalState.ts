import {useSyncExternalStore} from 'react';

export type LocalRecord={id:string;at:string;kind:'command'|'feedback';label:string;detail:string};
type State={records:LocalRecord[];error:string};
const key='agentrader.bot-prototype.records.v1';
const listeners=new Set<()=>void>();
let current:State={records:[],error:''};let initialized=false;
export function parseLocalRecords(raw:string|null):LocalRecord[]{
 if(!raw)return [];if(raw.length>1500000)throw Error('Record storage too large');const rows:unknown=JSON.parse(raw);
 if(!Array.isArray(rows)||rows.length>200)throw Error('Invalid records');
 return rows.map(r=>{if(!r||typeof r!=='object'||!['command','feedback'].includes(r.kind)||typeof r.id!=='string'||r.id.length>80||typeof r.at!=='string'||!Number.isFinite(Date.parse(r.at))||typeof r.label!=='string'||r.label.length>300||typeof r.detail!=='string'||r.detail.length>5000)throw Error('Invalid record');return r as LocalRecord;});
}
function emit(){for(const listener of listeners)listener();}
function initialize(){if(initialized)return;initialized=true;try{current={records:parseLocalRecords(localStorage.getItem(key)),error:''};}catch{current={records:[],error:'Yerel kayıtlar okunamadı. Yeni kayıt yazmadan önce tarayıcı depolamasını kontrol edin.'};}if(typeof window!=='undefined')window.addEventListener('storage',event=>{if(event.key!==key)return;try{current={records:parseLocalRecords(event.newValue),error:''};}catch{current={...current,error:'Başka sekmeden gelen kayıtlar geçersiz; otomatik yazma durduruldu.'};}emit();});}
export function addLocalRecord(kind:LocalRecord['kind'],label:string,detail=''){
 initialize();if(current.error)return false;
 try{const record:LocalRecord={id:crypto.randomUUID(),at:new Date().toISOString(),kind,label:label.slice(0,300),detail:detail.slice(0,5000)};const records=[record,...parseLocalRecords(localStorage.getItem(key))].slice(0,200);localStorage.setItem(key,JSON.stringify(records));current={records,error:''};emit();return true;}catch{current={...current,error:'Kayıt saklanamadı; işlem başarılı gösterilmedi. Tarayıcı depolama alanını kontrol edin.'};emit();return false;}
}
export function useBotRecords(){initialize();return useSyncExternalStore(callback=>{listeners.add(callback);return()=>listeners.delete(callback);},()=>current,()=>current);}
export function retryLocalRecords(){try{current={records:parseLocalRecords(localStorage.getItem(key)),error:''};}catch{current={...current,error:'Yerel kayıtlar hâlâ okunamıyor. Tarayıcı depolamasını kontrol edin.'};}emit();}
export function downloadLocalRecords(records:LocalRecord[]){const blob=new Blob([JSON.stringify({schema_version:1,source:'agentrader-ui-prototype',records},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='agentrader-prototip-kayitlari.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
