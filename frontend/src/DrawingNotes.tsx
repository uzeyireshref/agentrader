import {useEffect,useRef,useState} from 'react';
import {drawingRequest,drawingManagement,type Drawing} from './drawings';
export type LinkedNote={schema:'drawing-linked-note/1';drawing_id:string;workspace_id:string;note_id:string|null;revision:number;text:string;deleted:boolean;state:'EMPTY'|'ACTIVE'|'NOTE_DELETED'|'TARGET_ARCHIVED';target_revision:number;updated_at:number|null};
export type DrawingOrigin={schema:'drawing-origin/1';kind:'manual'|'bot';source:'legacy'|'user'|'bot';actor_id:string;bot_id:string|null;strategy_id:string|null;created_at:number|null};

export default function DrawingNotes({drawing,onRefresh,disabled=false}:{drawing:Drawing;onRefresh:()=>Promise<unknown>;disabled?:boolean}){
 const note=drawing.linked_note;const [text,setText]=useState(note?.deleted?'':note?.text??''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[retryable,setRetryable]=useState(false);
 const pending=useRef<{request_id:string;expected_revision:number;expected_drawing_revision:number;text:string}|null>(null),alive=useRef(true);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 useEffect(()=>{setText(note?.deleted?'':note?.text??'');setError('');setRetryable(false);pending.current=null;},[drawing]);
 const save=async()=>{
  if(busy)return;setBusy(true);setError('');
  const body=pending.current??{request_id:crypto.randomUUID(),expected_revision:note?.revision??0,expected_drawing_revision:drawing.revision,text};pending.current=body;
  try{const next=await drawingRequest<LinkedNote>('/api/drawings/'+encodeURIComponent(drawing.drawing_id)+'/notes','PUT',body);
   if(pending.current!==body)return;
   if(next.drawing_id!==drawing.drawing_id||next.revision!==body.expected_revision+1||next.text!==body.text||next.target_revision!==body.expected_drawing_revision)throw Error('Not yanıtı doğrulanamadı.');
   if(alive.current){if(await onRefresh()===false)throw Error('Not kaydı alındı; son görünüm yüklenemedi. Yeniden dene.');pending.current=null;setRetryable(false);}
  }catch(e){if(alive.current&&pending.current===body){setRetryable(true);setError(e instanceof Error?e.message:'Not kaydedilemedi.');}}
  finally{if(alive.current)setBusy(false);}
 };
 const blocked=disabled||busy||drawingManagement(drawing).locked||drawing.deleted;
 return <section className="drawing-editor drawing-linked-note" aria-label="Çizime bağlı uzun not"><p>Köken: {drawing.origin?.kind==='bot'?'Bot · '+drawing.origin.bot_id+' / '+drawing.origin.strategy_id:drawing.origin?.source==='legacy'?'Manuel · eski kayıt':'Manuel'}</p>
  <label>Uzun not<textarea aria-label="Çizimin uzun notu" rows={6} maxLength={4000} disabled={blocked||retryable} value={text} onChange={e=>setText(e.target.value)}/></label>
  <small>Çizime bağlı ayrı kayıt · {note?.revision??0}. sürüm · en fazla 4000 karakter</small>
  {error&&<p role="alert">{error}</p>}<div className="editor-buttons"><button type="button" disabled={blocked} onClick={()=>void save()}>{retryable?'Not kaydını yeniden dene':'Notu kaydet'}</button>
  {retryable&&<button type="button" disabled={busy} onClick={()=>void onRefresh()}>Notun son kaydını yükle</button>}</div>
 </section>;
}
