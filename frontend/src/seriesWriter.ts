import type {Candle} from './types.ts';
export type SeriesSink<T>={setData:(rows:T[])=>void;update:(row:T,historical?:boolean)=>void};
export type VolumePoint={time:number;value:number;color:string};
const volume=(c:Candle):VolumePoint=>({time:c.time,value:c.volume,color:c.close>=c.open?'#285a49':'#603e3b'});
/** Keep both engine series on the same bounded time window as chart state. */
export class ChartSeriesWriter {
 private rows:Candle[]=[];
 private candles:SeriesSink<Candle>;
 private volumes:SeriesSink<VolumePoint>;
 constructor(candles:SeriesSink<Candle>,volumes:SeriesSink<VolumePoint>){this.candles=candles;this.volumes=volumes;}
 write(rows:Candle[],full=false):{reset:boolean;removedLeading:number}{
  const previous=this.rows,last=previous.at(-1)?.time;
  const removedLeading=previous.length&&rows.length&&rows[0].time>previous[0].time?previous.findIndex(c=>c.time===rows[0].time):0;
  const tail=rows.slice(-2);
  const reset=full||last===undefined||!rows.length||rows[0].time!==previous[0]?.time||rows.length-previous.length>2||tail.some(c=>c.time<last&&!previous.some(old=>old.time===c.time));
  const replace=()=>{this.candles.setData(rows);this.volumes.setData(rows.map(volume));};
  let recovered=false;
  if(reset)replace();else{
   let latest=last!;
   try{for(const c of tail){const historical=c.time<latest;this.candles.update(c,historical);this.volumes.update(volume(c),historical);latest=Math.max(latest,c.time);}}
   catch{replace();recovered=true;}
  }
  this.rows=rows;
  return {reset:reset||recovered,removedLeading:Math.max(0,removedLeading)};
 }
}
