import type {DeepPartial,ChartOptions} from 'lightweight-charts';
/** Keep navigation deliberate rather than relying on changing engine defaults. */
export const navigationOptions:DeepPartial<ChartOptions>={
 handleScroll:{mouseWheel:true,pressedMouseMove:true,horzTouchDrag:true,vertTouchDrag:false},
 handleScale:{mouseWheel:true,pinch:true,axisPressedMouseMove:{time:true,price:true},axisDoubleClickReset:{time:true,price:true}},
 kineticScroll:{mouse:false,touch:true},
 timeScale:{minBarSpacing:2,maxBarSpacing:50,rightBarStaysOnScroll:false,shiftVisibleRangeOnNewBar:true,lockVisibleTimeRangeOnResize:true},
};
/** One physical gesture can contain many events with fluctuating minor deltas. */
export class WheelGestureAxis {
 private axis:'horizontal'|'vertical'|null=null;
 private last=-Infinity;
 private pinch=false;
 private totalX=0;
 private totalY=0;
 choose(dx:number,dy:number,pinch:boolean,now:number):'horizontal'|'vertical'|null{
  if(!Number.isFinite(dx)||!Number.isFinite(dy)||(!dx&&!dy))return null;
  if(now-this.last>200||pinch!==this.pinch){this.axis=null;this.totalX=0;this.totalY=0;}
  this.last=now;this.pinch=pinch;
  if(pinch)return this.axis='vertical';
  if(this.axis!==null)return this.axis;
  this.totalX+=Math.abs(dx);this.totalY+=Math.abs(dy);
  // Ignore tiny initial drift; settle ambiguous diagonals after a bounded distance.
  const major=Math.max(this.totalX,this.totalY),minor=Math.min(this.totalX,this.totalY);
  if(major<8||(major<24&&major<minor*1.25))return null;
  return this.axis=this.totalX>this.totalY?'horizontal':'vertical';
 }
}
/** Keep one axis until the gesture is idle; native engine owns zoom and locks. */
export function installDominantWheel(host:HTMLElement):()=>void{
 const surface=host.parentElement??host;
 const forwarded=new WeakSet<Event>();
 const gesture=new WheelGestureAxis();
 const wheel=(event:WheelEvent)=>{
  if(forwarded.has(event)||!event.target)return;
  const inside=host.contains(event.target as Node);
  const axis=gesture.choose(event.deltaX,event.deltaY,event.ctrlKey,performance.now());
  // Pending intent must not leak the original event to the engine or browser.
  if(axis===null){if(Number.isFinite(event.deltaX)&&Number.isFinite(event.deltaY)&&(event.deltaX||event.deltaY)){event.preventDefault();event.stopImmediatePropagation();}return;}
  const target=inside?event.target:host.firstElementChild;
  if(!target)return;
  event.preventDefault();event.stopImmediatePropagation();
  const horizontal=axis==='horizontal';
  const next=new WheelEvent('wheel',{bubbles:true,cancelable:true,composed:true,
   deltaX:horizontal?event.deltaX:0,deltaY:horizontal?0:event.deltaY,deltaZ:event.deltaZ,deltaMode:event.deltaMode,
   clientX:event.clientX,clientY:event.clientY,screenX:event.screenX,screenY:event.screenY,
   ctrlKey:event.ctrlKey,shiftKey:event.shiftKey,altKey:event.altKey,metaKey:event.metaKey});
  forwarded.add(next);target.dispatchEvent(next);
 };
 surface.addEventListener('wheel',wheel,{capture:true,passive:false});
 return()=>surface.removeEventListener('wheel',wheel,true);
}
