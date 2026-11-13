import {test} from 'node:test';
import assert from 'node:assert/strict';
import {FrameMetrics} from '../src/frameMetrics.ts';
test('cadence statistics use nearest-rank p95 and ignore initial frame',()=>{const m=new FrameMetrics();for(let i=0;i<=100;i++)m.frame(i*16);const r=m.summary();assert.equal(r.samples,100);assert.equal(r.p95_ms,16);assert.equal(r.approx_callbacks_per_second,62.5);assert.equal(r.usable,true);});
test('hidden-tab interruption is recorded and not treated as a giant frame',()=>{const m=new FrameMetrics();m.frame(0);m.frame(16);m.interrupt();m.frame(10000);m.frame(10016);const r=m.summary();assert.equal(r.max_ms,16);assert.equal(r.interruptions,1);assert.equal(r.usable,false);});
test('sample storage is bounded and truncated runs cannot be accepted',()=>{const m=new FrameMetrics();for(let i=0;i<11000;i++)m.frame(i*16);assert.equal(m.summary().samples,10000);assert.equal(m.summary().truncated_samples,999);assert.equal(m.summary().usable,false);});
test('slow callbacks are counted and empty runs have no invented metrics',()=>{const m=new FrameMetrics();assert.equal(m.summary().p95_ms,null);m.frame(0);m.frame(50);assert.equal(m.summary().over_33ms,1);assert.equal(m.summary().usable,false);});
