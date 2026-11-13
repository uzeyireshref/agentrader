import {test} from 'node:test';
import assert from 'node:assert/strict';
import {WheelGestureAxis} from '../src/chartNavigation';
test('horizontal gesture does not become zoom when minor-axis noise wins later frames',()=>{
 const gesture=new WheelGestureAxis();
 for(const [i,[dx,dy]] of [[12,2],[4,7],[0,5],[8,-3]].entries())assert.equal(gesture.choose(dx,dy,false,i*30),'horizontal');
 assert.equal(gesture.choose(0,10,false,400),'vertical');
});
test('vertical gesture and momentum stay zoom even with a horizontal tail',()=>{
 const gesture=new WheelGestureAxis();
 for(const [i,[dx,dy]] of [[1,12],[7,3],[4,0],[0,1]].entries())assert.equal(gesture.choose(dx,dy,false,i*30),'vertical');
 assert.equal(gesture.choose(10,0,false,400),'horizontal');
});
test('pinch modifier starts its own zoom gesture and returning to pan starts fresh',()=>{
 const gesture=new WheelGestureAxis();
 assert.equal(gesture.choose(12,1,false,0),'horizontal');
 assert.equal(gesture.choose(10,4,true,10),'vertical');
 assert.equal(gesture.choose(12,1,false,20),'horizontal');
 assert.equal(gesture.choose(NaN,0,false,25),null);
 assert.equal(gesture.choose(0,0,false,30),null);
});

import {readFileSync} from 'node:fs';

test('recorded physical diagonal ignores one-pixel initial vertical drift in all four segments',()=>{
 const events=JSON.parse(readFileSync(new URL('./fixtures/physical-diagonal-v1.json',import.meta.url),'utf8')) as {dx:number;dy:number;ctrl:boolean;t:number}[];
 const gesture=new WheelGestureAxis();let pending=0,chosen=0;
 for(const e of events){const axis=gesture.choose(e.dx,e.dy,e.ctrl,e.t);if(axis===null)pending++;else {assert.equal(axis,'horizontal');chosen++;}}
 assert.ok(pending>0&&chosen>400);
});

test('tiny horizontal drift before vertical motion does not select pan',()=>{
 const g=new WheelGestureAxis();assert.equal(g.choose(1,0,false,0),null);
 assert.equal(g.choose(0,3,false,10),null);assert.equal(g.choose(1,6,false,20),'vertical');
 assert.equal(g.choose(30,0,false,30),'vertical');
});

test('pending intent resets on idle and pinch stays immediate',()=>{
 const g=new WheelGestureAxis();assert.equal(g.choose(3,0,false,0),null);
 assert.equal(g.choose(0,5,false,250),null);assert.equal(g.choose(0,3,false,260),'vertical');
 assert.equal(g.choose(0,.1,true,270),'vertical');assert.equal(g.choose(1,0,false,280),null);
});

test('balanced diagonal settles after bounded movement',()=>{
 const g=new WheelGestureAxis();for(let i=0;i<23;i++)assert.equal(g.choose(1,1,false,i),null);
 assert.equal(g.choose(1,1,false,23),'vertical');assert.equal(g.choose(20,0,false,24),'vertical');
});
