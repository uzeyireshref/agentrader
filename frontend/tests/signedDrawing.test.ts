import {test} from 'node:test';
import assert from 'node:assert/strict';
import {snapDrawingPrice,onDrawingTick,snapPrice,onTick} from '../src/exactGeometry';
import {cursorPrice,creationPreview} from '../src/creationPreview';
import {moveGeometry} from '../src/drag';
import {familyGeometry,validateFamily} from '../src/channelFamily';
import {editGeometry} from '../src/editGeometry';
import type {Candle} from '../src/types';
test('signed drawing ticks preserve zero and round negative halves away from zero; market ticks stay positive',()=>{
 assert.equal(snapDrawingPrice('-1.125','.25'),'-1.25');assert.equal(snapDrawingPrice('1.125','.25'),'1.25');assert.equal(snapDrawingPrice('-.01','.25'),'0.00');assert.equal(snapDrawingPrice('1','.25','-2'),'-1.00');assert.ok(onDrawingTick('-1.25','.25'));assert.ok(onDrawingTick('0','.25'));assert.equal(onTick('-1.25','.25'),false);assert.throws(()=>snapPrice('-1','.25'));
 assert.equal(cursorPrice(-5,'.25',true),'-5.00');assert.equal(cursorPrice(0,'.25',true),'0.00');assert.equal(cursorPrice(-5,'.25'),null);
});
test('linear trend and channel can cross zero without mutating anchors or blocking editing',()=>{
 const a={time:1800000000,price:'10'},b={time:1800000900,price:'-10'};const g=creationPreview('trend','BTCUSDT',a,null,b)!;
 const rows=[{time:a.time},{time:b.time}] as Candle[];const moved=moveGeometry(g,rows,0,-5,.25,900,null)!;
 assert.deepEqual(moved.anchors.map(a=>a.price),['5.00','-15.00']);assert.equal(g.anchors[1].price,'-10');
 const family=familyGeometry('parallel_channel','BTCUSDT',[a,b,{time:b.time,price:'-20'}]);assert.doesNotThrow(()=>validateFamily(family));
 const dates=g.anchors.map(a=>new Date(a.time*1000).toISOString().slice(0,19));assert.equal(editGeometry(g,'signed',['0','-20'],dates,'0.25').anchors[0].price,'0');
});
