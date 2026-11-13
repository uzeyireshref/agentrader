import {test} from 'node:test';
import assert from 'node:assert/strict';
import {projectLogical,timeToLogical} from '../src/drawings.ts';
import {referenceTime} from '../src/alignment.ts';
import type {Candle} from '../src/types.ts';
// Installed LWC 5.2.1 _indexToCoordinate returns zero for noninteger indices.
const native=(index:number)=>Number.isInteger(index)?200+index*8:0;
test('regression: fractional index is not sent directly to native engine',()=>{assert.equal(native(4.5),0);const seen:number[]=[];assert.equal(projectLogical(4.5,i=>{seen.push(i);return native(i);}),236);assert.deepEqual(seen,[4,5]);});
test('exact, negative and extrapolated logical coordinates preserve linear geometry',()=>{for(const index of [-2,-1.5,0,.25,1,4.75,100.5])assert.equal(projectLogical(index,native),200+index*8);});
test('missing/nonfinite native coordinates are not invented as zero',()=>{assert.equal(projectLogical(.5,()=>null),null);assert.equal(projectLogical(NaN,native),null);assert.equal(projectLogical(.5,i=>i===0?100:NaN),null);});
test('15m, 1h and 4h fractional UTC anchors agree with independent native-time reference',()=>{const base=1800000000;for(const step of [900,3600,14400]){const rows=Array.from({length:20},(_,i)=>({time:base+i*step})) as Candle[];const byTime=(time:number)=>{const index=rows.findIndex(c=>c.time===time);return index<0?null:native(index);};for(const time of [base,base+420,base+step*2+step*.75,base+step*12]){const actual=projectLogical(timeToLogical(rows,time)!,native),expected=referenceTime(rows,time,byTime);assert.ok(actual!==null&&expected!==null);assert.ok(Math.abs(actual-expected)<1e-9);}}});
