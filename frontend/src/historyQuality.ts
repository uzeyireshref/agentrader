import { steps } from './evidence';
import { validCandle, type Candle, type Interval } from './types';
export function historyQuality(rows:Candle[],interval:Interval){
 const step=steps[interval],anchor=interval==='1w'?345600:0;
 let missing=0,invalid=0;
 rows.forEach((c,i)=>{if(!validCandle(c)||(c.time-anchor)%step!==0||c.close_time!==c.time*1000+step*1000-1||i>0&&c.time<=rows[i-1].time)invalid++;
 if(i)missing+=Math.max(0,Math.floor((c.time-rows[i-1].time)/step)-1);});
 return {state:!rows.length?'EMPTY':invalid?'INVALID':missing?'GAP':'OK',missing_bars:missing,invalid_bars:invalid,bar_count:rows.length};
}
