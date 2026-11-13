import {performance} from 'node:perf_hooks';
import {writeFileSync} from 'node:fs';
import {timeToLogical} from '../src/drawings.ts';
import type {Candle} from '../src/types.ts';
const rows=Array.from({length:4000},(_,i)=>({time:1800000000+i*900}) as Candle);
const times=Array.from({length:400},(_,i)=>rows[(i*7919)%4000].time+450);
function linear(time:number){let i=0;while(i<rows.length-2&&rows[i+1].time<time)i++;return i+(time-rows[i].time)/(rows[i+1].time-rows[i].time);}
function sample(project:(t:number)=>number){const samples:number[]=[];let checksum=0;for(let run=0;run<11;run++){const start=performance.now();for(let cycle=0;cycle<100;cycle++)for(const time of times)checksum+=project(time);const ms=performance.now()-start;if(run)samples.push(ms);}samples.sort((a,b)=>a-b);return {median_ms:samples[5],checksum};}
const previous=sample(linear),current=sample(t=>timeToLogical(rows,t)!);
if(previous.checksum!==current.checksum)throw Error('Projection mismatch');
const report={date:new Date().toISOString(),scenario:{candles:4000,drawings:200,anchors_per_drawing:2,projections_per_sample:40000,samples:10},previous,current,speedup:previous.median_ms/current.median_ms,scope:'Coordinate lookup CPU only; not browser FPS or full rendering',idle_projection_loop:false};
writeFileSync('../reports/chart-projection-benchmark-20261109.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
