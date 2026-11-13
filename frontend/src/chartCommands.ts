import {familyKinds,familyNames} from './channelFamily';
import type {Market} from './types';
export type ToolKind=typeof familyKinds[number]|'text'|'note'|'price_label'|'fibonacci_extension'|'parallel_channel'|'long_plan'|'short_plan'|'cursor'|'line'|'zone'|'trend'|'fibonacci'|'ruler'|'ray'|'extended_line'|'horizontal_ray';
export const chartTools:{id:ToolKind;label:string;icon:string;key:string;search:string}[]=[
 ...familyKinds.filter(id=>id!=='parallel_channel').map(id=>({id,label:familyNames[id],icon:'channel',key:'',search:id.replaceAll('_',' ')+' '+familyNames[id]})),
 {id:'text',label:'Metin',icon:'text',key:'A',search:'text yazı açıklama annotation'},
 {id:'note',label:'Not',icon:'note',key:'N',search:'note çok satırlı not annotation'},
 {id:'price_label',label:'Fiyat etiketi',icon:'price-label',key:'P',search:'price label etiket fiyat'},
 {id:'fibonacci_extension',label:'Fibonacci extension',icon:'fibonacci',key:'',search:'fib extension uzatma iki nokta'},
 {id:'parallel_channel',label:'Paralel kanal',icon:'channel',key:'',search:'parallel channel kanal orta çizgi'},
 {id:'long_plan',label:'Long plan',icon:'position',key:'',search:'long position risk getiri hedef stop'},
 {id:'short_plan',label:'Short plan',icon:'position',key:'',search:'short position risk reward'},
 {id:'ray',label:'Işın',icon:'trend',key:'',search:'ray ışın isin'},
 {id:'extended_line',label:'Uzatılmış çizgi',icon:'trend',key:'',search:'extended iki yön sonsuz'},
 {id:'horizontal_ray',label:'Yatay ışın',icon:'line',key:'',search:'horizontal ray yatay isin'},
 {id:'cursor',label:'İmleç',icon:'cursor',key:'V',search:'cursor seç seçim'},
 {id:'trend',label:'Trend çizgisi',icon:'trend',key:'T',search:'trend line çizgi'},
 {id:'line',label:'Yatay çizgi',icon:'line',key:'H',search:'horizontal seviye'},
 {id:'zone',label:'Fiyat bölgesi',icon:'zone',key:'B',search:'zone rectangle dikdörtgen'},
 {id:'fibonacci',label:'Fibonacci',icon:'fibonacci',key:'F',search:'fib retracement'},
 {id:'ruler',label:'Fiyat-zaman cetveli',icon:'ruler',key:'R',search:'ruler ölçüm cetvel'}
];
export const normalizeSearch=(s:string)=>s.toLocaleLowerCase('tr-TR').replace(/ı/g,'i').replace(/[\s/_-]+/g,'');
/** Search only the supported catalog; exact base/symbol matches rank before substrings. */
export function searchMarkets(markets:Market[],query:string):Market[]{
 const q=normalizeSearch(query);if(!q)return markets;
 const score=(m:Market)=>normalizeSearch(m.symbol)===q||normalizeSearch(m.base_asset)===q?0:normalizeSearch(m.symbol).startsWith(q)?1:2;
 return markets.filter(m=>normalizeSearch(m.symbol).includes(q)).sort((a,b)=>score(a)-score(b)||a.symbol.localeCompare(b.symbol));
}
export function readSymbolList(key:string,limit:number):string[]{
 try{const value:unknown=JSON.parse(localStorage.getItem(key)??'[]');return Array.isArray(value)?[...new Set(value.filter((s):s is string=>typeof s==='string'&&/^[A-Z0-9]{2,30}USDT$/.test(s)))].slice(0,limit):[];}catch{return [];}
}
export function installShellShortcuts(actions:{markets:()=>void;commands:()=>void;intervals:()=>void;tool:(kind:ToolKind)=>void}):()=>void{
 const key=(e:KeyboardEvent)=>{
  if(e.defaultPrevented||e.isComposing)return;
  const target=e.target instanceof Element?e.target:null;
  if(target?.closest('input,textarea,select,[contenteditable]:not([contenteditable="false"]),[role="textbox"],[role="combobox"]')||document.querySelector('dialog[open], [role="dialog"][aria-modal="true"]'))return;
  if((e.ctrlKey||e.metaKey)&&!e.altKey&&!e.shiftKey&&e.key.toLowerCase()==='k'){e.preventDefault();actions.commands();return;}
  if(e.ctrlKey||e.metaKey||e.altKey)return;
  if(e.key==='/'){e.preventDefault();actions.markets();return;}
  if(e.key===','){e.preventDefault();actions.intervals();return;}
  if(e.key==='Escape'){actions.tool('cursor');return;}
  if(!target?.matches('.chart-stage'))return;
  const tool=chartTools.find(t=>t.key.toLowerCase()===e.key.toLowerCase());if(tool&&!e.shiftKey){e.preventDefault();actions.tool(tool.id);}
 };
 window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);
}
