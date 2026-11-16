import {test} from 'node:test';
import assert from 'node:assert/strict';
import {drawingTimeAt} from '../src/drawingTime';
import {timeToLogical,type Geometry} from '../src/drawings';
import {logicalToTime,moveGeometry} from '../src/drag';
import {continuousLineGrid,verifiedLineGrid} from '../src/lineGeometry';
import {steps} from '../src/evidence';
import type {Candle,Interval} from '../src/types';

const candle=(time:number,step:number)=>({time,close_time:(time+step)*1000-1} as Candle);
test('future pointer slots use each selected interval, including a Monday weekly grid',()=>{
 for(const [interval,step] of Object.entries(steps)){
  const base=interval==='1w'?345600:1800000000,rows=[candle(base,step),candle(base+step,step)];
  assert.equal(drawingTimeAt(rows,6.1,interval as Interval),base+6*step);
  assert.equal(timeToLogical(rows,base+6*step,step),6);
  assert.equal(rows.length,2);
 }
});
test('missing last bars do not stretch future time; both directions round trip on the explicit cadence',()=>{
 const rows=[candle(1800000000,60),candle(1800000060,60),candle(1800000300,60)];
 for(const logical of [-3,0,1,2,3,8]){
  const time=drawingTimeAt(rows,logical,'1m')!;
  assert.equal(logicalToTime(rows,logical,60),time);
  assert.equal(timeToLogical(rows,time,60),logical);
 }
 assert.equal(drawingTimeAt(rows,3,'1m'),1800000360);
});
test('a persisted future anchor stays on its UTC time when real bars arrive and history is prepended',()=>{
 const rows=[candle(1800000000,60),candle(1800000060,60)],time=drawingTimeAt(rows,5,'1m')!;
 const advanced=[candle(1799999940,60),...rows,...[2,3,4,5,6].map(i=>candle(1800000000+i*60,60))];
 assert.equal(timeToLogical(advanced,time,60),6);
 assert.equal(advanced[6].time,time);
});
test('moving future trend endpoints keeps the selected interval instead of the edge gap length',()=>{
 const rows=[candle(1800000000,60),candle(1800000060,60),candle(1800000300,60)];
 const g:Geometry={kind:'trend',symbol:'BTCUSDT',price_source:'LAST_PRICE',label:'',anchors:[{time:1800000360,price:'100'},{time:1800000480,price:'110'}]};
 assert.deepEqual(moveGeometry(g,rows,2,1,'0.1',60,null)?.anchors,[{time:1800000480,price:'101.0'},{time:1800000600,price:'111.0'}]);
});
test('future drawing projection never upgrades the bounded calculation grid to market evidence',()=>{
 const rows=[candle(1800000000,60),candle(1800000060,60)];
 const g:Geometry={kind:'ray',symbol:'BTCUSDT',price_source:'LAST_PRICE',label:'',anchors:[{time:1800000300,price:'100'},{time:1800000360,price:'110'}]};
 assert.equal(continuousLineGrid(rows,'1m'),true);
 assert.equal(verifiedLineGrid(g,rows,'1m'),false);
});
test('empty, non-finite or out-of-domain drawing coordinates cannot create anchors',()=>{
 const rows=[candle(1800000000,60)];
 for(const logical of [null,NaN,Infinity,1e20,-1e20])assert.equal(drawingTimeAt(rows,logical,'1m'),null);
 assert.equal(drawingTimeAt([],1,'1m'),null);
});
