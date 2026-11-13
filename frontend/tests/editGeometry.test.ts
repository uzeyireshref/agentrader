import {test} from 'node:test';
import assert from 'node:assert/strict';
import {editGeometry} from '../src/editGeometry';
import type {Geometry} from '../src/drawings';
const g:Geometry={kind:'trend',symbol:'BTCUSDT',price_source:'LAST_PRICE',label:'x',anchors:[{time:1800000000,price:'100'},{time:1800000900,price:'110'}]};
const times=g.anchors.map(a=>new Date(a.time*1000).toISOString().slice(0,19));
test('editor keeps exact decimal strings for micro and quarter tick prices',()=>{
 assert.equal(editGeometry(g,'micro',['0,00000013','0.00000014'],times,'0.00000001').anchors[0].price,'0.00000013');
 assert.equal(editGeometry(g,'quarter',['100.25','110.50'],times,'0.25').anchors[0].price,'100.25');
 assert.throws(()=>editGeometry(g,'bad',['100.10','110'],times,'0.25'),/adım/);
});
test('tick validation is exact beyond binary float integer precision',()=>{
 assert.equal(editGeometry(g,'exact',['9007199254740993.25','9007199254740994.25'],times,'0.25').anchors[0].price,'9007199254740993.25');
 assert.throws(()=>editGeometry(g,'bad',['9007199254740993.26','110'],times,'0.25'),/adım/);
});
test('invalid prices and rolled calendar dates never produce geometry',()=>{
 for(const price of ['NaN','Infinity','-1','0','1.2.3',''])assert.throws(()=>editGeometry(g,'bad',[price,'110'],times,'0.1'));
 for(const date of ['2026-02-30T10:00:00','2026-01-01T25:00:00','bad','1970-01-01T00:00:00'])assert.throws(()=>editGeometry(g,'bad',['100','110'],[date,times[1]],'0.1'),/UTC/);
});
test('UTC editing is explicit and legacy coordinates remain untouched when renamed',()=>{
 const legacy={...g,anchors:[{time:g.anchors[0].time,price:'100.25'},g.anchors[1]]};
 const edited=editGeometry(legacy,'renamed',['100.25','110'],times,'0.1');
 assert.deepEqual(edited.anchors,legacy.anchors);
 assert.equal(editGeometry(g,'utc',['100','110'],['2026-11-09T12:34:56',times[1]],'0.1').anchors[0].time,Date.UTC(2026,10,9,12,34,56)/1000);
});
