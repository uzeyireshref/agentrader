import {test} from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import fixture from './fixtures/ruler-parity.json';
import {measureRuler,exactText,durationText} from '../src/ruler';
import RulerReadout from '../src/RulerReadout';
import {moveGeometry} from '../src/drag';
import {editGeometry} from '../src/editGeometry';
import type {Geometry} from '../src/drawings';
import type {Candle,Interval} from '../src/types';

test('all twelve independent ruler references match Python including repeating fractions',()=>{
 for(const c of fixture.cases){const before=structuredClone(c);assert.deepEqual(measureRuler(c.geometry as Geometry,c.tick_size,c.times,c.interval as Interval),c.expected,c.name);assert.deepEqual(c,before);}
});
test('ruler allows flat vertical and zero measurements through editor and drag',()=>{
 const geometry=fixture.cases[2].geometry as Geometry,rows=fixture.cases[2].times!.map(time=>({time})) as Candle[];
 const dates=geometry.anchors.map(a=>new Date(a.time*1000).toISOString().slice(0,19));
 assert.equal(editGeometry(geometry,'flat',['100','100'],dates,'0.25').anchors[1].price,'100');
 const moved=moveGeometry(geometry,rows,0,.25,'0.25',900,null)!;assert.equal(moved.schema,'chart-ruler/1');assert.equal(moved.anchors[0].price,'100.25');assert.equal(moved.anchors[1].price,'100.25');
 const vertical=fixture.cases[3].geometry as Geometry;assert.ok(moveGeometry(vertical,rows,0,1,'0.25',900,null));
});
test('ruler rejects unknown schema bad grid tick price and time units',()=>{
 const c=fixture.cases[0],g=c.geometry as Geometry;
 for(const tick of ['0','-1','NaN'])assert.throws(()=>measureRuler(g,tick,c.times,'15m'));
 assert.throws(()=>measureRuler({...g,schema:undefined},c.tick_size,c.times,'15m'));
 for(const times of [[],[1800000000,1800000000],[1800000900,1800000000],[1800000001,1800000901]])assert.throws(()=>measureRuler(g,c.tick_size,times,'15m'));
 const bad=structuredClone(g);bad.anchors[0].price='0';assert.throws(()=>measureRuler(bad,c.tick_size,c.times,'15m'));
 bad.anchors[0].price='100';bad.anchors[0].time*=1000;assert.throws(()=>measureRuler(bad,c.tick_size,c.times,'15m'));
});
test('timeframe changes bar count while exact prices and UTC duration stay fixed',()=>{
 const g=structuredClone(fixture.cases[0].geometry) as Geometry;g.anchors[1].time=1800003600;
 const first=measureRuler(g,'0.25',[1800000000,1800000900,1800001800,1800002700,1800003600],'15m'),second=measureRuler(g,'0.25',[1800000000,1800003600],'1h');
 assert.deepEqual(first.price_change,second.price_change);assert.equal(first.elapsed_seconds,second.elapsed_seconds);assert.equal(first.bars.count,5);assert.equal(second.bars.count,2);
});
test('readout names actual loaded bars and gap separately from elapsed UTC time',()=>{
 const c=fixture.cases.find(c=>c.name==='gap')!;
 const html=renderToStaticMarkup(<RulerReadout geometry={c.geometry as Geometry} tick={c.tick_size} rows={c.times!.map(time=>({time})) as Candle[]} interval="15m"/>);
 assert.match(html,/3 mum · 2 aralık/);assert.match(html,/1sa/);assert.match(html,/2 eksik mum/);assert.match(html,/40/);
 const absent=renderToStaticMarkup(<RulerReadout geometry={c.geometry as Geometry} tick={c.tick_size} rows={[]} interval="15m"/>);assert.match(absent,/Geçmiş gerekli/);assert.match(absent,/10 USDT/);
});
test('exact fraction text never silently rounds nonterminating percentages',()=>{
 const c=fixture.cases.find(c=>c.name==='repeating_percent')!,m=measureRuler(c.geometry as Geometry,c.tick_size,c.times,'15m');
 assert.equal(exactText(m.percent_change),'100/3');assert.equal(durationText(90061),'1g 1sa 1dk 1sn');assert.equal(durationText(0),'0sn');
});
