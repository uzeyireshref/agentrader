import { steps } from './evidence';
import type { Interval } from './types';
/** datetime-local input is deliberately interpreted as UTC, independent of host zone. */
export function parseUtcDate(value:string):number|null {
 if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(value))return null;
 const stamp=Date.parse(value+'Z');
 if(!Number.isSafeInteger(stamp)||stamp<=0||stamp>32503680000000)return null;
 return new Date(stamp).toISOString().slice(0,value.length)===value?stamp/1000:null;
}
export function intervalOpen(time:number,interval:Interval){
 const step=steps[interval],anchor=interval==='1w'?345600:0;
 return Math.floor((time-anchor)/step)*step+anchor;
}
