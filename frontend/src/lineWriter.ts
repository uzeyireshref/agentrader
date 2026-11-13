import type {IndicatorPoint} from './indicators.ts';
import type {SeriesSink} from './seriesWriter.ts';
/** Avoid setData/rebuilding the time scale for every open-candle tick. */
export class LineSeriesWriter<T extends {time:number;value?:number;color?:string}=IndicatorPoint> {
 private previous:T[]=[];
 private sink:SeriesSink<T>;
 constructor(sink:SeriesSink<T>){this.sink=sink;}
 write(points:T[],full=false){if(full){this.sink.setData(points);this.previous=points;return;}const old=this.previous;let first=0;while(first<old.length&&first<points.length&&old[first].time===points[first].time&&old[first].value===points[first].value&&old[first].color===points[first].color)first++;
  if(first===old.length&&first===points.length)return;
  const tail=points.slice(first);const appendable=old.length>0&&points.length>=old.length&&tail.length<=2&&old[0].time===points[0]?.time&&tail.every((p,i)=>first+i>=old.length||p.time===old[first+i].time);
  if(!appendable)this.sink.setData(points);else{let last=old.at(-1)!.time;try{for(const point of tail){this.sink.update(point,point.time<last);last=Math.max(last,point.time);}}catch{this.sink.setData(points);}}
  this.previous=points;
 }
}
