import type {IChartApi} from 'lightweight-charts';
/** Navigation is scoped to the focused chart, never to forms or page shortcuts. */
export function installChartKeyboard(surface:HTMLElement,chart:IChartApi,latest:()=>void):()=>void{
 const key=(event:KeyboardEvent)=>{
  if(event.ctrlKey||event.metaKey||event.altKey||event.target!==surface)return;
  const scale=chart.timeScale(),range=scale.getVisibleLogicalRange();if(!range)return;
  const span=range.to-range.from;
  if(event.key==='End'){event.preventDefault();latest();return;}
  if(event.key==='ArrowLeft'||event.key==='ArrowRight'){
   event.preventDefault();const shift=Math.max(1,span*.1)*(event.key==='ArrowLeft'?-1:1);
   scale.setVisibleLogicalRange({from:range.from+shift,to:range.to+shift});return;
  }
  if(['+','=','-','_'].includes(event.key)){
   event.preventDefault();const spacing=scale.options().barSpacing;
   const next=Math.min(50,Math.max(2,spacing*(event.key==='-'||event.key==='_'?1/1.2:1.2)));
   const width=span*spacing/next,middle=(range.from+range.to)/2;
   scale.setVisibleLogicalRange({from:middle-width/2,to:middle+width/2});
  }
 };
 surface.addEventListener('keydown',key);return()=>surface.removeEventListener('keydown',key);
}
