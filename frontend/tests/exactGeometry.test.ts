import {test} from 'node:test';
import assert from 'node:assert/strict';
import reference from './fixtures/geometry-parity.json';
import {decimalRational,exactDecimal,snapPrice,onTick,fibonacciPrice,displayNumber} from '../src/exactGeometry';
import {timeToLogical,type Geometry} from '../src/drawings';
import {moveGeometry} from '../src/drag';
import {editGeometry} from '../src/editGeometry';
import type {Candle} from '../src/types';

const rows=reference.grid.map(time=>({time})) as Candle[];
test('independent geometry fixtures match actual display interpolation and exact Fibonacci',()=>{
 for(const c of reference.cases){
  const anchors=c.geometry.anchors,expected=c.expected;
  if(typeof expected==='boolean'){assert.equal(Number(c.query_price)>=Math.min(...anchors.map(a=>Number(a.price)))&&Number(c.query_price)<=Math.max(...anchors.map(a=>Number(a.price))),expected);continue;}
  if(c.geometry.kind==='fibonacci'){
   const result=fibonacciPrice(anchors[0].price,anchors[1].price,c.ratio!);
   assert.equal(result.n.toString(),expected.numerator);assert.equal(result.d.toString(),expected.denominator);assert.equal(exactDecimal(result),expected.decimal);
  }else if(c.geometry.kind==='trend'){
   const start=timeToLogical(rows,anchors[0].time)!,end=timeToLogical(rows,anchors[1].time)!,at=timeToLogical(rows,c.time)!;
   const display=Number(anchors[0].price)+(Number(anchors[1].price)-Number(anchors[0].price))*(at-start)/(end-start);
   assert.ok(Math.abs(display-Number(expected.numerator)/Number(expected.denominator))<=1e-12);
  }else if(c.geometry.kind==='horizontal'){
   const result=decimalRational(anchors[0].price);assert.equal(result.n.toString(),expected.numerator);assert.equal(result.d.toString(),expected.denominator);
  }else {assert.equal(Math.max(Math.min(...anchors.map(a=>Number(a.price)))-Number(c.query_price),Number(c.query_price)-Math.max(...anchors.map(a=>Number(a.price))),0),Number(expected.decimal));}
 }
});
test('exact tick snapping preserves sub-float originals and rounds half upward',()=>{
 assert.equal(snapPrice('9007199254740993.25','0.25','0.25'),'9007199254740993.50');
 assert.equal(snapPrice('100.125','0.25'),'100.25');
 assert.equal(snapPrice('1.000000000000000000001','0.000000000000000000001','0.000000000000000000001'),'1.000000000000000000002');
 assert.equal(snapPrice('1.3e-7','1e-8'),'0.00000013');
 for(const [p,t] of [['NaN','0.1'],['1','0'],['-1','0.1'],['0.01','1']])assert.throws(()=>snapPrice(p,t));
});
test('form rejects off-tick values while drag snaps onto the same exact lattice',()=>{
 const geometry:Geometry={kind:'trend',symbol:'BTCUSDT',price_source:'LAST_PRICE',label:'exact',anchors:[{time:reference.grid[0],price:'9007199254740993.25'},{time:reference.grid[1],price:'9007199254740993.50'}]};
 const moved=moveGeometry(geometry,rows,0,.25,'0.25',900,null)!;
 assert.equal(moved.anchors[0].price,'9007199254740993.50');
 assert.equal(moved.anchors[1].price,'9007199254740993.75');
 const dates=moved.anchors.map(a=>new Date(a.time*1000).toISOString().slice(0,19));
 assert.deepEqual(editGeometry(moved,'exact',moved.anchors.map(a=>a.price),dates,'0.25'),moved);
 assert.throws(()=>editGeometry(moved,'off-grid',['9007199254740993.51',moved.anchors[1].price],dates,'0.25'));
 for(const a of moved.anchors)assert.ok(onTick(a.price,'0.25'));
 assert.equal(moveGeometry(geometry,rows,0,NaN,'0.25',900,null),null);
});
test('repeating fractions never manufacture a rounded exact decimal',()=>{
 assert.equal(exactDecimal({n:1n,d:3n}),null);
 assert.equal(displayNumber({n:1n,d:3n}),1/3);
 assert.equal(exactDecimal(decimalRational('-1.25')),'-1.25');
});
