import type {IChartApi,ISeriesApi} from 'lightweight-charts';
/** Public API gestures: vertical intent releases autoscale; axis drag zooms about its grab price. */
export function installChartGestures(host:HTMLElement,chart:IChartApi,series:ISeriesApi<'Candlestick'>,canPan:()=>boolean):()=>void{
 const surface=host.parentElement??host;
 type AxisDrag={id:number;y:number;pivot:number;from:number;to:number;log:boolean};
 let axis:AxisDrag|null=null,pan:{id:number;x:number;y:number}|null=null;
 const position=(e:MouseEvent|PointerEvent)=>{const r=host.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};};
 const inAxis=(e:MouseEvent|PointerEvent)=>{const p=position(e),size=chart.paneSize(0);return p.x>=size.width&&p.y>=0&&p.y<size.height&&p.x<host.clientWidth;};
 const down=(e:PointerEvent)=>{
  if(e.button!==0||!e.isPrimary)return;
  const scale=series.priceScale(),p=position(e),size=chart.paneSize(0);
  if(inAxis(e)){
   const options=chart.options().handleScale;
   if(options===false||typeof options==='object'&&(options.axisPressedMouseMove===false||typeof options.axisPressedMouseMove==='object'&&!options.axisPressedMouseMove.price))return;
   const range=scale.getVisibleRange(),pivot=series.coordinateToPrice(p.y),log=scale.options().mode===1;
   if(!range||pivot===null||!Number.isFinite(pivot)||log&&Math.min(range.from,range.to,pivot)<=0)return;
   const to=log?Math.log:((v:number)=>v);axis={id:e.pointerId,y:e.clientY,pivot:to(pivot),from:to(range.from),to:to(range.to),log};
   scale.applyOptions({autoScale:false});surface.setPointerCapture(e.pointerId);e.preventDefault();e.stopImmediatePropagation();
  }else if(canPan()&&p.x>=0&&p.x<size.width&&p.y>=0&&p.y<size.height&&!(e.target as Element)?.closest('[data-drawing],[data-drawing-handles],button,input,select,textarea,.pane-legend'))pan={id:e.pointerId,x:e.clientX,y:e.clientY};
 };
 const move=(e:PointerEvent)=>{
  if(axis?.id===e.pointerId){
   const factor=Math.exp(Math.max(-6,Math.min(6,(e.clientY-axis.y)*.006))),from=axis.pivot+(axis.from-axis.pivot)*factor,to=axis.pivot+(axis.to-axis.pivot)*factor;
   const range=axis.log?{from:Math.exp(from),to:Math.exp(to)}:{from,to};
   if(Number.isFinite(range.from)&&Number.isFinite(range.to)&&range.to>range.from&&(!axis.log||range.from>0))series.priceScale().setVisibleRange(range);
   e.preventDefault();e.stopImmediatePropagation();
  }else if(pan?.id===e.pointerId&&e.buttons===1&&canPan()&&Math.abs(e.clientY-pan.y)>3){series.priceScale().applyOptions({autoScale:false});pan=null;}
 };
 const finish=(e?:PointerEvent)=>{if(e&&axis&&axis.id!==e.pointerId)return;const id=axis?.id;axis=null;pan=null;if(id!==undefined&&surface.hasPointerCapture(id))surface.releasePointerCapture(id);};
 const reset=(e:MouseEvent)=>{if(inAxis(e)){finish();series.priceScale().applyOptions({autoScale:true});e.preventDefault();e.stopImmediatePropagation();}};
 const blur=()=>finish();
 surface.addEventListener('pointerdown',down,true);surface.addEventListener('pointermove',move,true);surface.addEventListener('pointerup',finish,true);surface.addEventListener('pointercancel',finish,true);surface.addEventListener('lostpointercapture',finish,true);surface.addEventListener('dblclick',reset,true);window.addEventListener('blur',blur);
 return()=>{finish();surface.removeEventListener('pointerdown',down,true);surface.removeEventListener('pointermove',move,true);surface.removeEventListener('pointerup',finish,true);surface.removeEventListener('pointercancel',finish,true);surface.removeEventListener('lostpointercapture',finish,true);surface.removeEventListener('dblclick',reset,true);window.removeEventListener('blur',blur);};
}
