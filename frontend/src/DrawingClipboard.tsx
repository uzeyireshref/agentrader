import {useEffect,useRef,useState} from 'react';
import {drawingRequest,type Drawing} from './drawings';
import {parseDrawingPackage,type DrawingPackage} from './drawingPackage';

export default function DrawingClipboard({mode,symbol,interval,selected,busy,retryable,error,onPaste,onRetry,onClose}:{mode:'copy'|'paste';symbol:string;interval:string;selected:Drawing[];busy:boolean;retryable:boolean;error:string;onPaste:(p:DrawingPackage)=>Promise<boolean>;onRetry:()=>Promise<boolean>;onClose:()=>void}){
 const ref=useRef<HTMLDialogElement>(null),[text,setText]=useState(''),[message,setMessage]=useState(''),[loading,setLoading]=useState(false);
 useEffect(()=>{ref.current?.showModal();},[]);
 useEffect(()=>{if(mode!=='copy')return;let active=true;setLoading(true);
  const targets=selected.map(d=>({drawing_id:d.drawing_id,expected_revision:d.revision,expected_note_revision:d.linked_note?.revision??0}));
  drawingRequest<DrawingPackage>('/api/workspaces/main/drawing-packages/export','POST',{symbol,interval,targets}).then(async value=>{if(!active)return;const serialized=JSON.stringify(value);parseDrawingPackage(serialized,symbol,interval);setText(serialized);try{await navigator.clipboard.writeText(serialized);if(active)setMessage('Paket panoya kopyalandı.');}catch{if(active)setMessage('Panoya erişilemedi. Paket metnini seçip elle kopyalayabilirsin.');}}).catch(e=>{if(active)setMessage(e instanceof Error?e.message:'Kopyalama doğrulanamadı.');}).finally(()=>{if(active)setLoading(false);});
  return()=>{active=false;};
 },[]);
 const read=async()=>{try{setText(await navigator.clipboard.readText());setMessage('');}catch{setMessage('Paket metnini aşağıdaki alana elle yapıştır.');}};
 const paste=async()=>{try{setMessage('');const value=parseDrawingPackage(text,symbol,interval);if(await onPaste(value))onClose();else setMessage('Yapıştırma onaylanmadı. Sonucu kontrol et veya aynı kaydı yeniden dene.');}catch(e){setMessage(e instanceof Error?e.message:'Paket geçersiz.');}};
 return <dialog ref={ref} className="indicator-dialog drawing-clipboard-dialog" aria-labelledby="clipboard-title" onCancel={e=>{if(busy)e.preventDefault();else onClose();}}><header><h2 id="clipboard-title">{mode==='copy'?'Çizimleri kopyala':'Çizimleri yapıştır'}</h2><button aria-label="Paket penceresini kapat" disabled={busy} onClick={onClose}>×</button></header>
  <p>{symbol} / {interval} · Geometri, stil ve uzun not korunur. Yeni kimlikler oluşturulur; köken ve revizyon taşınmaz.</p>
  {mode==='paste'&&<button disabled={busy||retryable} onClick={()=>void read()}>Panodan oku</button>}
  <label>Çizim paketi<textarea aria-label="Çizim paketi JSON" rows={12} readOnly={mode==='copy'} disabled={busy||loading||retryable} value={text} onChange={e=>setText(e.target.value)}/></label>
  {(message||error)&&<p role="status">{message||error}</p>}{error&&message&&<p role="alert">{error}</p>}
  <footer>{mode==='copy'?<button disabled={!text||loading} onClick={()=>{const input=ref.current?.querySelector('textarea');input?.focus();input?.select();}}>Paket metnini seç</button>:retryable?<button disabled={busy} onClick={()=>void onRetry().then(ok=>{if(ok)onClose();})}>Aynı kaydı yeniden dene</button>:<button disabled={busy||!text.trim()} onClick={()=>void paste()}>Yeni çizimler olarak yapıştır</button>}<button disabled={busy} onClick={onClose}>Kapat</button></footer>
 </dialog>;
}
