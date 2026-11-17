import { historyQuality } from './historyQuality';
import type { ChartState, Interval } from './types';

type Display = Pick<ChartState,'candles'|'market'|'quality'>;
/** Bounded per-tab previews; every revisit still requires a new proven snapshot. */
export class ChartDisplayCache {
  private entries = new Map<string,{at:number;display:Display}>();
  constructor(private now=()=>performance.now(),private capacity=8,private ttl=120_000){}
  put(state:ChartState){
    if(!state.candles.length||state.data_proof?.state!=='VERIFIED'||historyQuality(state.candles,state.interval).invalid_bars)return;
    const key=state.symbol+':'+state.interval;
    this.entries.delete(key);
    this.entries.set(key,{at:this.now(),display:{candles:state.candles,market:state.market,quality:state.quality}});
    while(this.entries.size>this.capacity)this.entries.delete(this.entries.keys().next().value!);
  }
  get(symbol:string,interval:Interval):Display|undefined {
    const key=symbol+':'+interval,entry=this.entries.get(key);
    if(!entry)return;
    const age=this.now()-entry.at;
    if(age<0||age>this.ttl){this.entries.delete(key);return;}
    this.entries.delete(key);this.entries.set(key,entry);
    return entry.display;
  }
}
