import type { ITimeScaleApi, Time } from 'lightweight-charts';
import { candleCoordinate, candleLogicalAt, engineLogicalAt } from './chartTime';
import { timeToLogical } from './drawings';
import type { Candle } from './types';
export type TimeViewport={from:number;to:number;bars:number};
function timeAt(rows:Candle[],index:number,step:number){
 const last=rows.length-1;if(index<0)return rows[0].time+index*step;if(index>last)return rows[last].time+(index-last)*step;
 const i=Math.floor(index);return rows[i].time+(i===last?0:(rows[i+1].time-rows[i].time)*(index-i));
}
export function captureTimeViewport(rows:Candle[],step:number,scale:ITimeScaleApi<Time>):TimeViewport|null {
 const a=candleLogicalAt(rows,0,scale),b=candleLogicalAt(rows,scale.width(),scale);
 return a===null||b===null?null:{from:timeAt(rows,a,step),to:timeAt(rows,b,step),bars:b-a};
}
export function restoreTimeViewport(rows:Candle[],step:number,scale:ITimeScaleApi<Time>,view:TimeViewport){
 const a=timeToLogical(rows,view.from,step),b=timeToLogical(rows,view.to,step);if(a===null||b===null)return;
 const x=candleCoordinate(rows,a,scale),y=candleCoordinate(rows,b,scale);if(x===null||y===null)return;
 const from=engineLogicalAt(x,scale),to=engineLogicalAt(y,scale);if(from!==null&&to!==null&&to>from){
  // Public logical ranges include both endpoint bars; coordinates address centers.
  // Account for half a bar on either side and the engine's one-pixel right inset.
  const width=scale.width(),span=to-from;if(!(width>0))return;
  const inset=span/width;
  scale.setVisibleLogicalRange({from:from+.5-inset,to:to-.5-inset});
 }
}
export function changeViewportInterval(view:TimeViewport,step:number):TimeViewport {
 const middle=(view.from+view.to)/2,bars=Math.min(1000,Math.max(2,view.bars));return {from:middle-bars*step/2,to:middle+bars*step/2,bars};
}
/** Preserve candle density and right padding relative to the actual candle tail. */
export function followLatestViewport(view:TimeViewport,tail:number,step:number,nextTail:number,nextStep:number):TimeViewport {
 const bars=Math.min(1000,Math.max(2,view.bars));
 const to=nextTail+(view.to-tail)/step*nextStep;
 return {from:to-bars*nextStep,to,bars};
}
