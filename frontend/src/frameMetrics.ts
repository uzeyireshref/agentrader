/** rAF cadence statistics, not GPU-rendered FPS or a memory-leak verdict. */
export class FrameMetrics {
 private last:number|null=null;
 private intervals:number[]=[];
 private dropped=0;
 private interruptions=0;
 frame(time:number){if(!Number.isFinite(time))return;if(this.last!==null&&time>this.last){if(this.intervals.length<10000)this.intervals.push(time-this.last);else this.dropped++;}this.last=time;}
 interrupt(){this.interruptions++;this.last=null;}
 summary(){const sorted=[...this.intervals].sort((a,b)=>a-b),n=sorted.length;const total=sorted.reduce((a,b)=>a+b,0);return {samples:n,p95_ms:n?sorted[Math.ceil(n*.95)-1]:null,max_ms:n?sorted[n-1]:null,mean_ms:n?total/n:null,approx_callbacks_per_second:total?1000*n/total:null,over_33ms:sorted.filter(v=>v>33.34).length,interruptions:this.interruptions,truncated_samples:this.dropped,usable:n>=30&&this.interruptions===0&&this.dropped===0};}
}
