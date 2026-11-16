import type {Candle,Interval} from './types';
import {steps} from './evidence';

/** Calendar slots for drawing anchors only. Never creates market rows/evidence. */
export function drawingTimeAt(rows:Candle[],logical:number|null,interval:Interval):number|null{
 if(!rows.length||logical===null||!Number.isFinite(logical))return null;
 const index=Math.round(logical),last=rows.length-1,step=steps[interval];
 const time=index<0?rows[0].time+index*step:index>last?rows[last].time+(index-last)*step:rows[index].time;
 return Number.isSafeInteger(time)&&time>0&&time<=32503680000?time:null;
}
