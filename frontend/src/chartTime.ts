import type { ITimeScaleApi, Time, UTCTimestamp } from 'lightweight-charts';
import type { Candle } from './types';

/** Drawing indices belong to the candle grid, never the union of engine series. */
export function candleCoordinate(rows:Candle[], logical:number, scale:ITimeScaleApi<Time>):number|null {
 if(!rows.length||!Number.isFinite(logical))return null;
 const last=rows.length-1;
 const at=(i:number)=>scale.timeToCoordinate(rows[i].time as UTCTimestamp);
 if(logical<0||logical>last){const i=logical<0?0:last,x=at(i);return x===null?null:x+(logical-i)*scale.options().barSpacing;}
 const i=Math.floor(logical),a=at(i);if(a===null||i===last||logical===i)return a;
 const b=at(i+1);return b===null?null:a+(b-a)*(logical-i);
}
export function candleLogicalAt(rows:Candle[],x:number,scale:ITimeScaleApi<Time>):number|null {
 if(!rows.length||!Number.isFinite(x))return null;
 const last=rows.length-1,firstX=candleCoordinate(rows,0,scale),lastX=candleCoordinate(rows,last,scale);
 if(firstX===null||lastX===null)return null;
 const spacing=scale.options().barSpacing;if(!(spacing>0))return null;
 if(x<firstX)return (x-firstX)/spacing;
 if(x>lastX)return last+(x-lastX)/spacing;
 if(!last)return 0;
 let low=0,high=last;
 while(low+1<high){const mid=(low+high)>>>1,p=candleCoordinate(rows,mid,scale);if(p===null)return null;if(p<x)low=mid;else high=mid;}
 const a=candleCoordinate(rows,low,scale),b=candleCoordinate(rows,high,scale);
 return a===null||b===null||b<=a?null:low+(x-a)/(b-a);
}

/** coordinateToLogical snaps to a bar in v5; retain sub-bar viewport precision. */
export function engineLogicalAt(x:number,scale:ITimeScaleApi<Time>):number|null {
 const index=scale.coordinateToLogical(x);if(index===null)return null;
 const at=scale.logicalToCoordinate(index),spacing=scale.options().barSpacing;
 return at===null||!(spacing>0)?null:index+(x-at)/spacing;
}
