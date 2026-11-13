import {test} from 'node:test';
import assert from 'node:assert/strict';
import {familyGeometry,familyModel,clipFamilyLine,validateFamily,type FamilyKind} from '../src/channelFamily.ts';
import {moveGeometry,moveFamilyOnAxis} from '../src/drag.ts';
import type {Candle} from '../src/types.ts';
const t=1800000000,rows=Array.from({length:40},(_,i)=>({time:t+i*900,open:100+i,high:105+i,low:95+i,close:100+i,volume:10,quote_volume:1000,close_time:(t+(i+1)*900)*1000-1,closed:true})) as Candle[];
const anchors=[{time:t,price:'100'},{time:t+9000,price:'140'},{time:t+18000,price:'120'}];
test('REA four pitchfork median fixtures remain distinct with matching side origins',()=>{
 const fixtures:[FamilyKind,number][]=[['pitchfork',150],['schiff_pitchfork',136.66666666666666],['modified_schiff_pitchfork',140],['inside_pitchfork',130]];
 for(const [kind,expected]of fixtures){const m=familyModel(familyGeometry(kind,'BTCUSDT',anchors),rows),median=m.lines.find(l=>l.role==='median')!;const price=median.a.y+(median.b.y-median.a.y)*(25-median.a.x)/(median.b.x-median.a.x);assert.ok(Math.abs(price-expected)<1e-10,kind);assert.deepEqual(m.lines.find(l=>l.role==='level:-1')!.a,{x:10,y:140});assert.deepEqual(m.lines.find(l=>l.role==='level:1')!.a,{x:20,y:120});assert.equal(m.handles.length,3);}
});
test('REA disjoint and flat derive fourth handle rather than persisting a fourth anchor',()=>{
 const flat=familyModel(familyGeometry('flat_channel','BTCUSDT',anchors),rows),disjoint=familyModel(familyGeometry('disjoint_channel','BTCUSDT',anchors),rows);
 assert.deepEqual(flat.handles,[{x:0,y:100},{x:10,y:140},{x:10,y:120},{x:0,y:120}]);
 assert.deepEqual(disjoint.handles,[{x:0,y:100},{x:10,y:140},{x:10,y:120},{x:0,y:160}]);
 const second=disjoint.lines.find(l=>l.role==='offset')!;assert.equal(second.b.y-second.a.y,-40);
});
test('derived disjoint handle and primary endpoint preserve source-observed constraints',()=>{
 const g=familyGeometry('disjoint_channel','BTCUSDT',anchors),d=moveGeometry(g,rows,1,10,'1',900,3)!;
 assert.equal(d.anchors[0].time,t+900);assert.equal(d.anchors[0].price,'90');assert.equal(d.anchors.length,3);
 const b=moveGeometry(g,rows,1,10,'1',900,1)!;assert.equal(b.anchors[1].price,'150');assert.equal(b.anchors[2].price,'110');
});
test('flat width handles move time and common horizontal boundary together',()=>{
 const g=familyGeometry('flat_channel','BTCUSDT',anchors),d=moveGeometry(g,rows,2,5,'1',900,3)!;
 assert.equal(d.anchors[0].time,t+1800);assert.equal(d.anchors[0].price,'100');assert.equal(d.anchors[2].price,'125');
 const b=moveGeometry(g,rows,1,5,'1',900,2)!;assert.equal(b.anchors[1].time,t+9900);assert.equal(b.anchors[2].time,t+9900);
});
test('regression uses candle source and bar indices, ignoring clicked prices',()=>{
 const a=familyGeometry('regression_channel','BTCUSDT',[{time:t,price:'1'},{time:t+9000,price:'999'}]);
 const b={...a,anchors:a.anchors.map(x=>({...x,price:'500'}))},m=familyModel(a,rows);
 assert.deepEqual(m,familyModel(b,rows));assert.deepEqual(m.handles,[{x:0,y:100},{x:10,y:110}]);assert.equal(m.deviation,0);assert.equal(m.pearson,-1);
});
test('regression residual sample deviation and high-low fallback match live observations',()=>{
 const sample=rows.slice(0,3).map((r,i)=>({...r,close:[100,103,102][i]}));const g=familyGeometry('regression_channel','BTCUSDT',[{time:t,price:'50'},{time:t+1800,price:'60'}]);
 const m=familyModel(g,sample);assert.ok(Math.abs(m.deviation!-Math.sqrt(4/3))<1e-10);assert.ok(Math.abs(m.pearson!+.6546536707079771)<1e-10);
 const bounds=familyModel({...g,options:{...g.options!,upper_enabled:false,lower_enabled:false}},sample);assert.equal(bounds.lines.find(l=>l.role==='upper')!.a.y,105);assert.equal(bounds.lines.find(l=>l.role==='lower')!.a.y,95);
});
test('line clipping distinguishes bounded, backward, forward and both directions',()=>{
 const a={x:20,y:20},b={x:40,y:40};assert.deepEqual(clipFamilyLine(a,b,100,100,'none'),[a,b]);assert.deepEqual(clipFamilyLine(a,b,100,100,'right'),[a,{x:100,y:100}]);assert.deepEqual(clipFamilyLine(a,b,100,100,'left'),[{x:0,y:0},b]);assert.deepEqual(clipFamilyLine(a,b,100,100,'both'),[{x:0,y:0},{x:100,y:100}]);
});
test('invalid and empty-band configurations fail or retain median safely',()=>{
 const g=familyGeometry('pitchfork','BTCUSDT',anchors);assert.throws(()=>validateFamily({...g,anchors:[anchors[0],anchors[1],anchors[1]]}));assert.throws(()=>validateFamily({...g,options:{...g.options!,levels:['1','1.0']}}));
 const medianOnly=familyModel({...g,options:{...g.options!,levels:[]}},rows);assert.equal(medianOnly.fill,null);assert.equal(medianOnly.lines.some(l=>l.role.startsWith('level:')),false);
});


test('live TradingView closed-bar fixtures match all seven sources, sample deviation, Pearson sign and extrema fallback',async()=>{
 const {readFile}=await import('node:fs/promises');const fixture=JSON.parse(await readFile(new URL('./fixtures/regression-rea-20261113.json',import.meta.url),'utf8'));
 for(const c of fixture.cases){const r=c.rows.map((v:number[])=>({time:v[0],open:v[1],high:v[2],low:v[3],close:v[4],volume:v[5],quote_volume:0,close_time:0,closed:true})) as Candle[];
 const g=familyGeometry('regression_channel','BTCUSDT',[{time:r[0].time,price:'1'},{time:r.at(-1)!.time,price:'2'}]);g.options={...g.options!,source:c.inputs.source,upper_enabled:c.inputs['use upper diviation'],lower_enabled:c.inputs['use lower diviation']};
 const m=familyModel(g,r);for(const [role,key]of [['median','baseLine'],['upper','upLine'],['lower','downLine']]){const l=m.lines.find(l=>l.role===role)!;assert.ok(Math.abs(l.a.y-c.trend[key].startPrice)<1e-6,c.inputs.source+' '+role+' start');assert.ok(Math.abs(l.b.y-c.trend[key].endPrice)<1e-6,c.inputs.source+' '+role+' end');}assert.ok(Math.abs(m.pearson!-c.trend.pearsons)<1e-10,c.inputs.source+' Pearson');}
});


test('log display derives midpoint and disjoint corners on the native axis without rewriting anchors',()=>{
 const axis={to:Math.log,from:Math.exp},g=familyGeometry('disjoint_channel','BTCUSDT',anchors),original=JSON.stringify(g),m=familyModel(g,rows,axis);
 assert.ok(Math.abs(m.handles[3].y-168)<1e-10);assert.equal(JSON.stringify(g),original);
 const p=familyModel(familyGeometry('pitchfork','BTCUSDT',anchors),rows,axis),line=p.lines.find(l=>l.role==='median')!;assert.ok(Math.abs(line.b.y-Math.sqrt(140*120))<1e-10);
});

test('log body drag preserves multiplicative price distances and derived handle constraints',()=>{
 const axis={to:Math.log,from:Math.exp},g=familyGeometry('disjoint_channel','BTCUSDT',anchors);
 const moved=moveFamilyOnAxis(g,rows,0,Math.log(1.1),'0.001',900,null,axis.to,axis.from)!;assert.ok(moved);assert.deepEqual(moved.anchors.map(a=>Number(a.price)),[110,154,132]);
 const corner=moveFamilyOnAxis(g,rows,1,Math.log(1.1),'0.001',900,3,axis.to,axis.from)!;assert.ok(corner);assert.equal(corner.anchors[0].time,t+900);assert.ok(Math.abs(Number(corner.anchors[0].price)-100/1.1)<.001);assert.equal(corner.anchors[2].price,'120');
});

test('regression display statistics remain independent of log projection and reject missing endpoint history',()=>{
 const g=familyGeometry('regression_channel','BTCUSDT',[anchors[0],anchors[1]]);assert.deepEqual(familyModel(g,rows,{to:Math.log,from:Math.exp}),familyModel(g,rows));assert.throws(()=>familyModel(g,rows.slice(1)));
 const flat=rows.map(r=>({...r,open:100,high:100,low:100,close:100})),m=familyModel(g,flat);assert.equal(m.deviation,0);assert.equal(m.pearson,0);
});


test('regression handles two bars, reversed anchors, live updates and rejects nonfinite history',()=>{
 const g=familyGeometry('regression_channel','BTCUSDT',[anchors[0],{time:t+900,price:'102'}]),sample=rows.slice(0,2),m=familyModel(g,sample);
 assert.equal(m.deviation,0);assert.equal(m.pearson,-1);assert.deepEqual(familyModel({...g,anchors:[...g.anchors].reverse()},sample).handles,[...m.handles].reverse());
 const live=sample.map((r,i)=>({...r,closed:i===0,close:i?120:r.close}));assert.equal(familyModel(g,live).handles[1].y,120);
 assert.throws(()=>familyModel(g,sample.map((r,i)=>({...r,close:i?NaN:r.close}))));assert.throws(()=>familyModel(g,[{...sample[0],high:Infinity},sample[1]]));
});


test('all pitchfork canvas segments match live TradingView LINEAR and LOG render observations within 0.001 CSS px',async()=>{
 const {readFile}=await import('node:fs/promises');const cases=JSON.parse(await readFile(new URL('./fixtures/pitchfork-render-rea-20261113.json',import.meta.url),'utf8'));
 for(const c of cases){const [a,b]=c.points,[sa,sb]=c.screenAnchors,transform=(p:number)=>c.log?Math.log(p):p,untransform=(p:number)=>c.log?Math.exp(p):p,pa=transform(a.price),pb=transform(b.price),axis={to:(p:number)=>sa.y+(transform(p)-pa)*(sb.y-sa.y)/(pb-pa),from:(v:number)=>untransform(pa+(v-sa.y)*(pb-pa)/(sb.y-sa.y))};
 const rows=c.times.map((time:number)=>({time})) as Candle[],g=familyGeometry(c.kind,'BTCUSDT',c.points.map((p:{index:number;price:number})=>({time:c.times[p.index],price:String(p.price)}))),m=familyModel(g,rows,axis),project=(p:{x:number;y:number})=>({x:sa.x+(p.x-a.index)*(sb.x-sa.x)/(b.index-a.index),y:axis.to(p.y)}),near=(p:{x:number;y:number},q:{x:number;y:number})=>Math.hypot(p.x-q.x,p.y-q.y)<.001;
 assert.equal(m.lines.length,c.lines.length,c.kind+' '+c.log+' segment count');for(const l of m.lines){const p=project(l.a),q=project(l.b);assert.ok(c.lines.some((v:any)=>near(p,v.points[0])&&near(q,v.points[1])&&v.extendright===(l.mode==='right')),c.kind+' '+c.log+' '+l.role);}
 }
});


test('three channel canvas boundaries match live TradingView LINEAR and LOG within 0.001 CSS px',async()=>{
 const {readFile}=await import('node:fs/promises');const cases=JSON.parse(await readFile(new URL('./fixtures/channel-render-rea-20261113.json',import.meta.url),'utf8'));
 for(const c of cases){const [a,b]=c.points,[sa,sb]=c.screenAnchors,transform=(p:number)=>c.log?Math.log(p):p,untransform=(p:number)=>c.log?Math.exp(p):p,pa=transform(a.price),pb=transform(b.price),axis={to:(p:number)=>sa.y+(transform(p)-pa)*(sb.y-sa.y)/(pb-pa),from:(v:number)=>untransform(pa+(v-sa.y)*(pb-pa)/(sb.y-sa.y))};
 const rows=c.times.map((time:number)=>({time})) as Candle[],anchors=c.points.map((p:{index:number;price:number})=>({time:c.times[p.index],price:String(p.price)})),g={...familyGeometry(c.kind,'BTCUSDT',anchors),anchors},m=familyModel(g,rows,axis),project=(p:{x:number;y:number})=>({x:sa.x+(p.x-a.index)*(sb.x-sa.x)/(b.index-a.index),y:axis.to(p.y)}),near=(p:{x:number;y:number},q:{x:number;y:number})=>Math.hypot(p.x-q.x,p.y-q.y)<.001;
 for(const l of m.lines){const p=project(l.a),q=project(l.b);assert.ok(c.lines.some((v:any)=>near(p,v.points[0])&&near(q,v.points[1])||near(q,v.points[0])&&near(p,v.points[1])),c.kind+' '+c.log+' '+l.role);}
 }
});
