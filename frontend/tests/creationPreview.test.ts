import {test} from 'node:test';
import assert from 'node:assert/strict';
import type {Candle} from '../src/types.ts';
import {creationPreview,drawingPriceExtent,cursorPrice} from '../src/creationPreview.ts';
const a={time:1800000000,price:'100'},b={time:1800001800,price:'120'},c={time:1800000900,price:'130'};
test('cursor labels ignore invalid scale positions and tick values without throwing',()=>{
 for(const p of [null,NaN,Infinity,-10,0,.001])assert.equal(cursorPrice(p,'0.1'),null);
 assert.equal(cursorPrice(100.26,'0.1'),'100.3');assert.equal(cursorPrice(100,''),null);
});
test('two-point tools preview after first anchor, without mutating saved anchors',()=>{
 for(const tool of ['trend','zone','fibonacci','fibonacci_extension','ruler','ray','extended_line'] as const){
  assert.equal(creationPreview(tool,'BTCUSDT',null,null,b),null);
  const g=creationPreview(tool,'BTCUSDT',a,null,b)!;assert.deepEqual(g.anchors,[a,b]);assert.deepEqual(drawingPriceExtent(g),[100,120]);
  const moved=creationPreview(tool,'BTCUSDT',a,null,c)!;assert.equal(moved.anchors[1].price,'130');assert.equal(g.anchors[1].price,'120');
 }
 assert.equal(creationPreview('trend','BTCUSDT',a,null,null),null);
 assert.equal(creationPreview('cursor','BTCUSDT',a,null,b),null);
});
test('channel previews baseline then full parallel boundaries; invalid third point stays safe',()=>{
 assert.equal(creationPreview('parallel_channel','BTCUSDT',a,null,b)!.kind,'trend');
 const g=creationPreview('parallel_channel','BTCUSDT',a,b,c)!;assert.equal(g.kind,'parallel_channel');
 // Width is placed at the second endpoint, matching the new channel family.
 assert.deepEqual(drawingPriceExtent(g,[{time:a.time},{time:c.time},{time:b.time}] as Candle[]),[100,130]);
 assert.equal(creationPreview('parallel_channel','BTCUSDT',a,b,{...c,price:'120'})!.kind,'trend');
 assert.equal(creationPreview('parallel_channel','BTCUSDT',a,b,{...c,time:b.time+900})!.kind,'parallel_channel');
});
test('one-point tools preview at cursor before committing',()=>{
 assert.deepEqual(creationPreview('line','BTCUSDT',null,null,a)?.anchors,[a]);
 assert.equal(creationPreview('horizontal_ray','BTCUSDT',null,null,a)?.kind,'horizontal_ray');
 assert.equal(creationPreview('note','BTCUSDT',null,null,a)?.schema,'chart-annotation/1');
});
test('position preview keeps stop at moving end time and rejects wrong-sided target',()=>{
 const stop={...b,price:'90'},target={...b,price:'125'};
 const g=creationPreview('long_plan','BTCUSDT',a,stop,target)!;assert.equal(g.kind,'long_plan');assert.equal(g.anchors[1].time,target.time);
 assert.equal(creationPreview('long_plan','BTCUSDT',a,stop,{...target,price:'95'})!.kind,'trend');
});
