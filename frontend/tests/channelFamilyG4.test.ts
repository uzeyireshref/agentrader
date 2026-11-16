import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {familyModel,FamilyCalculationError,familyLogAxis} from '../src/channelFamily.ts';
import type {Geometry} from '../src/drawings.ts';
import type {Candle} from '../src/types.ts';
const fixture=JSON.parse(await readFile(new URL('./fixtures/channel-family-g4.json',import.meta.url),'utf8'));
const rows=Array.from({length:40},(_,i)=>({time:fixture.start+i*900,open:100+i,high:105+i,low:95+i,close:100+i,volume:10,quote_volume:1000,close_time:(fixture.start+(i+1)*900)*1000-1,closed:true})) as Candle[];
const geometry=(kind:Geometry['kind']):Geometry=>({schema:'chart-channel-family/1',kind,symbol:'BTCUSDT',price_source:'LAST_PRICE',label:'Synthetic G4',text:'',anchors:structuredClone(kind==='regression_channel'?fixture.anchors.slice(0,2):fixture.anchors),options:structuredClone(fixture.options)});
const rational=(s:string)=>{const [a,b='1']=s.split('/');return Number(a)/Number(b);};

test('G4 shared independent vectors agree with seven data-coordinate channel families',()=>{
 const micro=geometry('disjoint_channel');micro.anchors=micro.anchors.map(a=>({...a,price:String(Number(a.price)*1e-8)}));assert.ok(Math.abs(familyModel(micro,rows,familyLogAxis).handles[3].y-1.68e-6)<1e-18);
 for(const c of fixture.cases){const model=familyModel(geometry(c.kind),rows),at=(l:typeof model.lines[number])=>l.a.y+(l.b.y-l.a.y)*(25-l.a.x)/(l.b.x-l.a.x),median=model.lines.find(l=>l.role==='median')!,edges=model.lines.filter(l=>c.kind.includes('pitchfork')?l.role.startsWith('level:'):['base','offset'].includes(l.role)),values=edges.map(at);
  for(const [key,value]of [['lower',Math.min(...values)],['upper',Math.max(...values)],['middle',at(median)]] as const)assert.ok(Math.abs(value-rational(c.expected[key]))<1e-10,c.kind+' '+key);
 }
});

test('G4 intermediate UTC, reversed anchors and reload preserve raw anchors and actual sample identities',()=>{
 const g=geometry('regression_channel');g.anchors=fixture.regression.raw_times.map((time:number)=>({time,price:'999'}));const sample=rows.slice(0,3).map((r,i)=>({...r,close:fixture.regression.close[i]})),before=JSON.stringify(g),m=familyModel(g,sample);
 assert.equal(JSON.stringify(g),before);assert.deepEqual(m.effectiveAnchorTimes,fixture.regression.effective_times);assert.equal(m.sampleCount,3);assert.ok(Math.abs(m.deviation!**2-4/3)<1e-10);assert.ok(Math.abs(m.pearson!-fixture.regression.pearson)<1e-10);
 assert.deepEqual(familyModel(JSON.parse(before),sample),m);assert.deepEqual(familyModel(g,sample,{to:Math.log,from:Math.exp}),m);
 const reversed=familyModel({...g,anchors:[...g.anchors].reverse()},sample);assert.deepEqual(reversed.handles,[...m.handles].reverse());
 const boundary={...g,anchors:[g.anchors[0],{time:rows[1].time,price:'5'}]};assert.equal(familyModel(boundary,sample).sampleCount,2);
});

test('G4 same candle, unloaded history, gaps and future wait explicitly then recover without shifting UTC',()=>{
 const g=geometry('regression_channel');g.anchors=fixture.regression.raw_times.map((time:number)=>({time,price:'999'}));const same={...g,anchors:[g.anchors[0],{time:rows[0].time+450,price:'7'}]};
 assert.throws(()=>familyModel(same,rows),(e:unknown)=>e instanceof FamilyCalculationError&&e.state==='WARMUP'&&e.code==='INSUFFICIENT_REGRESSION_SAMPLES');
 const identical={...same,anchors:[same.anchors[0],{...same.anchors[1],time:same.anchors[0].time}]};assert.throws(()=>familyModel(identical,rows),(e:unknown)=>e instanceof FamilyCalculationError&&e.state==='WARMUP');
 for(const sample of [rows.slice(1),rows.filter((_,i)=>i!==1)])assert.throws(()=>familyModel(g,sample),(e:unknown)=>e instanceof FamilyCalculationError&&e.state==='WAITING_FOR_DATA');
 const future={...g,anchors:[g.anchors[0],{time:rows[10].time+225,price:'7'}]},before=JSON.stringify(future);assert.throws(()=>familyModel(future,rows.slice(0,8)),FamilyCalculationError);assert.equal(familyModel(future,rows).sampleCount,11);assert.equal(JSON.stringify(future),before);
 const live=rows.slice(0,3).map((r,i)=>({...r,closed:i<2}));assert.equal(familyModel(g,live).openCandleUsed,true);assert.throws(()=>familyModel(g,live.filter(r=>r.closed)),FamilyCalculationError);
});
