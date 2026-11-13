import {useEffect,useRef,useState,type PointerEvent as ReactPointerEvent} from 'react';
import type {Candle,Interval} from './types';
import type {ViewScale} from './viewScale';
import {supportsView} from './viewScale';
import {drawingManagement,drawingVisible} from './drawings';
import type {useDrawings} from './useDrawings';
import DrawingPanel from './DrawingPanel';
import Icon from './ChartIcon';

type Props={manager:ReturnType<typeof useDrawings>;rows:Candle[];interval:Interval;tick:string;viewScale:ViewScale;onClose:()=>void};
export default function DrawingToolbar({manager,rows,interval,tick,viewScale,onClose}:Props){
 const [settings,setSettings]=useState(false),root=useRef<HTMLDivElement>(null);
 const [position,setPosition]=useState<{x:number;y:number}|null>(null);
 const drag=useRef<{pointer:number;clientX:number;clientY:number;x:number;y:number;target:HTMLButtonElement}|null>(null);
 const clamp=(x:number,y:number)=>{const node=root.current,parent=node?.parentElement;if(!node||!parent)return {x,y};return {x:Math.max(8,Math.min(x,Math.max(8,parent.clientWidth-node.offsetWidth-8))),y:Math.max(8,Math.min(y,Math.max(8,parent.clientHeight-(node.querySelector<HTMLElement>('.drawing-quick-controls')?.offsetHeight??42)-8)))};};
 const place=(x:number,y:number)=>setPosition(old=>{const p=clamp(x,y);return old?.x===p.x&&old.y===p.y?old:p;});
 const stopDrag=(cancel=false)=>{const d=drag.current;drag.current=null;if(!d)return;if(cancel)place(d.x,d.y);if(d.target.hasPointerCapture(d.pointer))d.target.releasePointerCapture(d.pointer);};
 const startDrag=(e:ReactPointerEvent<HTMLButtonElement>)=>{if(!e.isPrimary||e.button!==0||!root.current?.parentElement)return;e.preventDefault();e.stopPropagation();e.currentTarget.focus({preventScroll:true});const box=root.current.getBoundingClientRect(),parent=root.current.parentElement.getBoundingClientRect();drag.current={pointer:e.pointerId,clientX:e.clientX,clientY:e.clientY,x:box.left-parent.left,y:box.top-parent.top,target:e.currentTarget};e.currentTarget.setPointerCapture(e.pointerId);place(box.left-parent.left,box.top-parent.top);};
 useEffect(()=>{const cancel=()=>stopDrag(true);window.addEventListener('blur',cancel);return()=>{window.removeEventListener('blur',cancel);stopDrag();};},[]);
 useEffect(()=>{const parent=root.current?.parentElement;if(!parent)return;const observer=new ResizeObserver(()=>setPosition(old=>{if(!old)return old;const p=clamp(old.x,old.y);return old.x===p.x&&old.y===p.y?old:p;}));observer.observe(parent);return()=>observer.disconnect();},[manager.selected]);
 const multiple=manager.selectedIds.length>1,item=manager.items.find(d=>d.drawing_id===manager.selected&&drawingVisible(d,interval)&&supportsView(d.geometry.kind,viewScale,d.geometry.schema));
 useEffect(()=>{setSettings(false);},[manager.selected]);
 useEffect(()=>{if(settings)root.current?.querySelector<HTMLElement>('.drawing-settings-popup button')?.focus();},[settings]);
 if(!item||multiple)return null;
 const m=drawingManagement(item),blocked=manager.busy||manager.loading||manager.retryable;
 return <div ref={root} className="floating-drawing-toolbar" style={position?{left:position.x,top:position.y,right:'auto',transform:'none',width:'max-content',maxWidth:'calc(100% - 16px)'}:undefined} onPointerDown={e=>e.stopPropagation()} onKeyDown={e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();if(drag.current)stopDrag(true);else if(settings)setSettings(false);else onClose();}}}>
  <div className="drawing-quick-controls" role="toolbar" aria-label="Seçili çizimi düzenle">
   <button type="button" className="drawing-toolbar-grip" aria-label="Çizim çubuğunu taşı" title="Sürükleyerek taşı · Ok tuşlarıyla taşı" onPointerDown={startDrag} onPointerMove={e=>{const d=drag.current;if(d?.pointer===e.pointerId)place(d.x+e.clientX-d.clientX,d.y+e.clientY-d.clientY);}} onPointerUp={e=>{if(drag.current?.pointer===e.pointerId)stopDrag();}} onPointerCancel={e=>{if(drag.current?.pointer===e.pointerId)stopDrag(true);}} onLostPointerCapture={e=>{if(drag.current?.pointer===e.pointerId)stopDrag();}} onKeyDown={e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)||!root.current?.parentElement)return;e.preventDefault();e.stopPropagation();const box=root.current.getBoundingClientRect(),parent=root.current.parentElement.getBoundingClientRect(),step=e.shiftKey?20:5;place(box.left-parent.left+(e.key==='ArrowLeft'?-step:e.key==='ArrowRight'?step:0),box.top-parent.top+(e.key==='ArrowUp'?-step:e.key==='ArrowDown'?step:0));}}>⠿</button>
   <label className="drawing-color-control" title="Çizgi rengi"><span aria-hidden="true">╱</span><select aria-label="Seçili çizimin rengi" disabled={blocked||m.locked} value={m.color??''} onChange={e=>void manager.properties(item.drawing_id,{...m,color:e.target.value||null})}><option value="">Tema</option><option value="#2962ff">Mavi</option><option value="#16a085">Yeşil</option><option value="#d95656">Kırmızı</option><option value="#c99432">Altın</option><option value="#9b6ed6">Mor</option></select><i style={{background:m.color??'var(--accent)'}}/></label>
   <button className="icon-button" title="Metin ve notu düzenle" aria-label="Çizim metni ve notu" disabled={blocked||m.locked} onClick={()=>setSettings(v=>!v)}><Icon name="text"/></button>
   <select aria-label="Seçili çizimin kalınlığı" title="Çizgi kalınlığı" disabled={blocked||m.locked} value={m.line_width} onChange={e=>void manager.properties(item.drawing_id,{...m,line_width:Number(e.target.value) as 1|2|3})}>{[1,2,3].map(w=><option key={w} value={w}>{w} px</option>)}</select>
   <select aria-label="Seçili çizimin stili" title="Çizgi stili" disabled={blocked||m.locked} value={m.line_style} onChange={e=>void manager.properties(item.drawing_id,{...m,line_style:e.target.value as typeof m.line_style})}><option value="default">Otomatik</option><option value="solid">━━━━</option><option value="dashed">┄┄┄┄</option><option value="dotted">········</option></select>
   <span className="drawing-toolbar-divider"/>
   <button className="icon-button" title={m.locked?'Kilidi aç':'Kilitle'} aria-label={m.locked?'Seçili çizimin kilidini aç':'Seçili çizimi kilitle'} aria-pressed={m.locked} disabled={blocked} onClick={()=>void manager.properties(item.drawing_id,{...m,locked:!m.locked})}><Icon name={m.locked?'lock':'unlock'}/></button>
   <button className="icon-button" title="Sil · Delete" aria-label="Seçili çizimi sil" disabled={blocked||m.locked} onClick={()=>void manager.change(item.drawing_id,null)}><Icon name="trash"/></button>
   <button className="icon-button" title="Çizim ayarları" aria-label="Seçili çizimin tüm ayarları" aria-expanded={settings} onClick={()=>setSettings(v=>!v)}><Icon name="settings"/></button>
   <button className="icon-button" title="Seçimi kapat" aria-label="Çizim seçimini kapat" disabled={blocked} onClick={onClose}><Icon name="close"/></button>
  </div>
  {settings&&<div className="drawing-settings-popup" role="region" aria-label="Seçili çizim ayarları"><header><b>{item.geometry.label||'Çizim ayarları'}</b><button className="icon-button" aria-label="Çizim ayarlarını kapat" onClick={()=>setSettings(false)}><Icon name="close"/></button></header><DrawingPanel compact manager={manager} rows={rows} interval={interval} tick={tick} viewScale={viewScale}/></div>}
  {(manager.message||manager.busy)&&<div className="drawing-toolbar-status" role={manager.message?'alert':'status'}>{manager.message||'Kaydediliyor…'}{manager.retryable&&<button disabled={manager.busy} onClick={()=>void manager.retry()}>Tekrar dene</button>}{manager.message&&<button disabled={manager.busy} onClick={()=>void manager.refresh()}>Son kaydı yükle</button>}</div>}
 </div>;
}
