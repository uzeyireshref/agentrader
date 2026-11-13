import {drawingWithDefault,type DrawingDefaults} from './chartProfiles';
import {useEffect,useRef,useState} from 'react';
import {drawingRequest,type Drawing,type Geometry,type Workspace,drawingManagement,drawingVisible,type Management} from './drawings';
import {LatestRead} from './latestRead';
import type {Interval} from './types';
type Change={before:Drawing|null;after:Drawing};
export function useDrawings(symbol:string,interval:Interval,restore:(symbol:string,interval:Interval)=>void,defaults?:DrawingDefaults|null){
 const creationDefaults=useRef(defaults);creationDefaults.current=defaults;
 const [items,setItems]=useState<Drawing[]>([]),[selected,setSelectedValue]=useState<string|null>(null),[selectedIds,setSelectedIds]=useState<string[]>([]),[available,setAvailable]=useState(false),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[savedAt,setSavedAt]=useState<number|null>(null),[ready,setReady]=useState(false),[loadedFor,setLoadedFor]=useState<string|null>(null),[historyVersion,setHistoryVersion]=useState(0),[retryable,setRetryable]=useState(false);
 const reads=useRef(new LatestRead()),bootstrap=useRef(new LatestRead());
 const heads=useRef(new Map<string,Drawing>()),undo=useRef<Change[][]>([]),redo=useRef<Change[][]>([]),mutating=useRef(false),pending=useRef<(()=>Promise<void>)|null>(null),workspace=useRef<Workspace>({revision:0,preferences:{symbol:'BTCUSDT',interval:'15m'}}),current=useRef(symbol),onRestore=useRef(restore),prefChain=useRef(Promise.resolve()),prefSerial=useRef(0);current.current=symbol;onRestore.current=restore;
 const setSelected=(id:string|null)=>{setSelectedValue(id);setSelectedIds(id?[id]:[]);};
 const select=(id:string,additive=false,preserve=false)=>{if(additive){setSelectedIds(ids=>{const next=ids.includes(id)?ids.filter(x=>x!==id):ids.length<20?[...ids,id]:ids;setSelectedValue(next.at(-1)??null);return next;});}else if(!preserve||!selectedIds.includes(id))setSelected(id);};
 const selection=useRef({symbol,interval,version:0});
 if(selection.current.symbol!==symbol||selection.current.interval!==interval)selection.current={symbol,interval,version:selection.current.version+1};
 const refresh=async()=>{
  if(mutating.current)return false;
  let refreshed=false;bootstrap.current.invalidate();
  const requested=current.current;setLoadedFor(null);
  await reads.current.run(async()=>{
   await prefChain.current;
   const saved=await drawingRequest<Workspace>('/api/workspaces/main');
   const response=await drawingRequest<{drawings:Drawing[]}>('/api/workspaces/main/drawings?symbol='+encodeURIComponent(requested)+'&format_version=9');
   return {saved,response};
  },({saved,response})=>{
   if(current.current!==requested)return;
   refreshed=true;workspace.current=saved;setAvailable(true);setReady(true);heads.current=new Map(response.drawings.map(d=>[d.drawing_id,d]));setItems(response.drawings);setLoadedFor(requested);setSelected(null);undo.current=[];redo.current=[];pending.current=null;setRetryable(false);setHistoryVersion(v=>v+1);setMessage('');
  },e=>setMessage(e instanceof Error?e.message:'Çizimler yüklenemedi.'));
  return refreshed;
 };
 useEffect(()=>{
  const selectionVersion=selection.current.version;
  void bootstrap.current.run(()=>drawingRequest<Workspace>('/api/workspaces/main'),saved=>{
   workspace.current=saved;if(selection.current.version===selectionVersion)onRestore.current(saved.preferences.symbol,saved.preferences.interval);setAvailable(true);setReady(true);
  },()=>setMessage('Çizim çalışma alanı yüklenemedi. Sunucudan yenileyebilirsin.'));
  return()=>{bootstrap.current.invalidate();reads.current.invalidate();};
 },[]);
 useEffect(()=>{
  reads.current.invalidate();if(!available)return;
  setLoadedFor(null);setItems([]);setSelected(null);undo.current=[];redo.current=[];setHistoryVersion(v=>v+1);
  const requested=symbol;
  void reads.current.run(()=>drawingRequest<{drawings:Drawing[]}>('/api/workspaces/main/drawings?symbol='+encodeURIComponent(requested)+'&format_version=9'),response=>{
   if(current.current!==requested)return;
   heads.current=new Map(response.drawings.map(d=>[d.drawing_id,d]));setItems(response.drawings);setLoadedFor(requested);
  },e=>setMessage(e instanceof Error?e.message:'Çizimler yüklenemedi.'));
  return()=>reads.current.invalidate();
 },[symbol,available]);
 useEffect(()=>{setSelected(null);},[interval]);
 useEffect(()=>{if(!available||!ready)return;const serial=++prefSerial.current;const timer=setTimeout(()=>{prefChain.current=prefChain.current.then(async()=>{if(serial!==prefSerial.current)return;try{workspace.current=await drawingRequest<Workspace>('/api/workspaces/main','PUT',{request_id:crypto.randomUUID(),expected_revision:workspace.current.revision,preferences:{symbol,interval}});}catch(e){setMessage(e instanceof Error?e.message:'Çalışma alanı kaydedilemedi.');setReady(false);}});},450);return()=>clearTimeout(timer);},[symbol,interval,available,ready]);
 const commit=(results:Drawing[],before:(Drawing|null)[],mode:'normal'|'undo'|'redo')=>{
  const staleReadPending=reads.current.pending&&results.some(d=>d.geometry.symbol===current.current);
  for(const result of results)heads.current.set(result.drawing_id,result);
  const relevant=results.filter(d=>d.geometry.symbol===current.current);
  if(relevant.length){setItems(list=>[...list.filter(d=>!relevant.some(r=>r.drawing_id===d.drawing_id)),...relevant.filter(d=>!d.deleted)]);const changedIds=relevant.filter(d=>!d.deleted).map(d=>d.drawing_id);const ids=before.every(Boolean)&&selectedIds.length>1?Array.from(new Set([...selectedIds.filter(id=>!relevant.some(d=>d.drawing_id===id&&d.deleted)),...changedIds])):changedIds;setSelectedIds(ids);setSelectedValue(ids.at(-1)??null);
   if(mode==='normal'){undo.current.push(results.map((after,i)=>({before:before[i],after})));redo.current=[];}
   else if(mode==='undo'){const entry=undo.current.pop();if(entry)redo.current.push(entry);}
   else{const entry=redo.current.pop();if(entry)undo.current.push(entry);}
   setHistoryVersion(v=>v+1);
  }
  setSavedAt(Date.now());setMessage('');
  if(staleReadPending){reads.current.invalidate();setLoadedFor(null);queueMicrotask(()=>{if(relevant.length)void refresh();});}
 };
 const perform=async(operation:()=>Promise<Drawing|{drawings:Drawing[]}>,before:(Drawing|null)[],mode:'normal'|'undo'|'redo')=>{if(mutating.current)return;const run=async()=>{mutating.current=true;setBusy(true);try{const result=await operation();commit("drawings" in result?result.drawings:[result],before,mode);pending.current=null;setRetryable(false);}catch(e){setMessage(e instanceof Error?e.message:'Kayıt doğrulanamadı.');pending.current=run;setRetryable(true);}finally{mutating.current=false;setBusy(false);}};await run();};
 const create=async(geometry:Geometry)=>{if(!available||!ready||loadedFor!==symbol||pending.current||mutating.current||creationDefaults.current===null)return;const request_id=crypto.randomUUID(),template=creationDefaults.current?.[geometry.kind];if(template){const item=drawingWithDefault(geometry,template);await perform(()=>drawingRequest<{drawings:Drawing[]}>('/api/workspaces/main/drawing-operations?format_version=9','POST',{request_id,operations:[{drawing_id:null,expected_revision:0,geometry:item.geometry,management:item.management,deleted:false}]}),[null],'normal');}else await perform(()=>drawingRequest<Drawing>('/api/workspaces/main/drawings?format_version=9','POST',{request_id,geometry}),[null],'normal');};

 const change=async(id:string,geometry:Geometry|null,mode:'normal'|'undo'|'redo'='normal')=>{if(!available||!ready||loadedFor!==symbol||mutating.current||(pending.current&&mode==='normal'))return;const previous=heads.current.get(id);if(!previous||drawingManagement(previous).locked)return;const request_id=crypto.randomUUID();await perform(()=>drawingRequest<Drawing>('/api/drawings/'+id+'?format_version=9',geometry===null?'DELETE':'PATCH',{request_id,expected_revision:previous.revision,...(geometry?{geometry}:{})}),[previous],mode);};
 const transact=async(targets:{before:Drawing|null;geometry:Geometry;management:Management;deleted:boolean}[],mode:'normal'|'undo'|'redo'='normal')=>{
  if(!available||!ready||loadedFor!==symbol||mutating.current||pending.current||!targets.length||targets.some(t=>t.geometry.symbol!==symbol))return;
  const request_id=crypto.randomUUID();const operations=targets.map(t=>({drawing_id:t.before?.drawing_id??null,expected_revision:t.before?.revision??0,geometry:t.geometry,management:t.management,deleted:t.deleted}));
  await perform(()=>drawingRequest<{drawings:Drawing[]}>('/api/workspaces/main/drawing-operations?format_version=9','POST',{request_id,operations}),targets.map(t=>t.before),mode);
 };
 const properties=async(id:string,management:Management)=>{const d=heads.current.get(id);if(d)await transact([{before:d,geometry:d.geometry,management,deleted:d.deleted}]);};
 const duplicate=async(id:string)=>{const d=heads.current.get(id);if(d)await transact([{before:null,geometry:{...d.geometry,label:(d.geometry.label||'Çizim').slice(0,56)+' kopya'},management:{...drawingManagement(d),locked:false},deleted:false}]);};
 const changeMany=async(changes:{id:string;geometry:Geometry}[])=>{const targets=changes.flatMap(c=>{const d=heads.current.get(c.id);return d&&!drawingManagement(d).locked&&drawingVisible(d,interval)?[{before:d,geometry:c.geometry,management:drawingManagement(d),deleted:false}]:[];});await transact(targets);};
 const removeSelected=async()=>{const targets=selectedIds.flatMap(id=>{const d=heads.current.get(id);return d&&!d.deleted&&!drawingManagement(d).locked&&drawingVisible(d,interval)?[{before:d,geometry:d.geometry,management:drawingManagement(d),deleted:true}]:[];});await transact(targets);};
 const history=async(mode:'undo'|'redo')=>{if(pending.current)return;const entry=(mode==='undo'?undo:redo).current.at(-1);if(!entry)return;
  if(entry.length===1&&!entry[0].after.management&&!entry[0].before?.management){const c=entry[0];await change(c.after.drawing_id,mode==='undo'?(c.before&&!c.before.deleted?c.before.geometry:null):(c.after.deleted?null:c.after.geometry),mode);return;}
  const targets=entry.map(c=>{const value=mode==='undo'?c.before:c.after;return {before:heads.current.get(c.after.drawing_id)!,geometry:value?.geometry??c.after.geometry,management:drawingManagement(value??c.after),deleted:value?.deleted??true};});await transact(targets,mode);
 };
 const undoLast=()=>history('undo');const redoLast=()=>history('redo');
 const retry=async()=>{if(pending.current&&!mutating.current)await pending.current();};
 void historyVersion;
 return {loading:!ready||loadedFor!==symbol,items,selected,selectedIds,setSelected,select,properties,duplicate,changeMany,removeSelected,available,busy,message,savedAt,retryable,refresh,create,change,undoLast,redoLast,retry,canUndo:undo.current.length>0,canRedo:redo.current.length>0};
}
