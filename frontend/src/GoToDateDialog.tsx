import {useId,useRef,useState} from 'react';
import {useModalDialog} from './useModalDialog';
import {parseUtcDate} from './goToDate';
export default function GoToDateDialog({initialTime,onGo,onClose}:{initialTime:number;onGo:(time:number)=>void;onClose:()=>void}){
 const ref=useRef<HTMLDialogElement>(null),id=useId();useModalDialog(ref);
 const [value,setValue]=useState(new Date(initialTime*1000).toISOString().slice(0,16));
 const time=parseUtcDate(value);
 return <dialog ref={ref} className="go-date-dialog" aria-labelledby={id} onCancel={e=>{e.preventDefault();onClose();}}>
  <form onSubmit={e=>{e.preventDefault();if(time!==null){onGo(time);onClose();}}}>
   <h2 id={id}>Tarihe git</h2><p>Tarih ve saat UTC olarak değerlendirilir. Seçilen periyottaki mum görünümün ortasına alınır.</p>
   <label>Tarih ve saat (UTC)<input autoFocus aria-label="Gitmek istediğin tarih ve saat (UTC)" type="datetime-local" required step="60" value={value} onChange={e=>setValue(e.target.value)}/></label>
   <p>En fazla 4000 mum yüklenir. Bu sınırın dışındaki tarihler için bilgi gösterilir.</p>
   <footer><button type="button" onClick={onClose}>Vazgeç</button><button type="submit" disabled={time===null}>Tarihe git</button></footer>
  </form>
 </dialog>;
}
