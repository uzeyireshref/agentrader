import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fibValue,validateFibonacci,reverseFibAnchors} from '../src/fibonacci.ts';
import {exactDecimal} from '../src/exactGeometry.ts';
import {parseDrawingPackage} from '../src/drawingPackage.ts';
import {drawingManagement,type Geometry} from '../src/drawings.ts';
import {creationPreview} from '../src/creationPreview.ts';
import {moveGeometry} from '../src/drag.ts';
import {drawingWithDefault,captureDrawingDefault,validDrawingDefaults} from '../src/chartProfiles.ts';
import {supportsView} from '../src/viewScale.ts';
const cases=JSON.parse(readFileSync(new URL('./fixtures/projection-g9.json',import.meta.url),'utf8'));
const projection=():Geometry=>({kind:'fibonacci_projection',schema:'chart-fibonacci-projection/1',basis:'PRICE_DELTA',symbol:'BTCUSDT',price_source:'LAST_PRICE',label:'Projection',anchors:[{time:1800000000,price:'100'},{time:1800000900,price:'120'},{time:1800001800,price:'110'}],levels:['0','1','1.618'],time_scope:'right'});
const pack=()=>({schema:'chart-drawing-package/1',market:{source:'binance_usdm_demo_trade_price',environment:'demo_public',product:'USD-M',price_type:'LAST_PRICE',symbol:'BTCUSDT',interval:'15m'},items:[{geometry:projection(),management:drawingManagement(),linked_note:{text:'Unicode 🧭\nNot'}}]});
test('independent projection vectors use C base and exact rational prices',()=>{
 for(const c of cases){const g=projection();g.levels=['0',c.ratio];g.anchors.forEach((a,i)=>a.price=c.prices[i]);if(c.blocked)assert.ok(Number(exactDecimal(fibValue(g,c.ratio)))<=0);else assert.equal(exactDecimal(fibValue(g,c.ratio)),c.expected);}
});
test('projection preview has three roles; zero impulse rejected and third anchor drag preserved',()=>{
 const g=projection(),[a,b,c]=g.anchors;assert.deepEqual(reverseFibAnchors([a,b,c],true),[b,a,c]);const draft=creationPreview('fibonacci_projection','BTCUSDT',a,b,c)!;
 assert.equal(draft.kind,'fibonacci_projection');assert.equal(draft.anchors.length,3);assert.equal(supportsView(draft.kind,'LOG',draft.schema),true);
 assert.throws(()=>validateFibonacci({...g,basis:undefined}));assert.throws(()=>validateFibonacci({...g,anchors:[a,{...b,price:a.price},c]}));
 const moved=moveGeometry(g,[{time:a.time,open:100,high:120,low:90,close:110,volume:1,quote_volume:100,close_time:a.time*1000+899999,closed:true}],0,5,'0.25',900,2)!;
 assert.equal(Number(moved.anchors[2].price),115);assert.deepEqual(moved.anchors.slice(0,2),g.anchors.slice(0,2));assert.equal(exactDecimal(fibValue(moved,'1')),'135');
});
test('package rejects identity/market/invalid text while retaining style and Unicode note',()=>{
 const p=pack();assert.deepEqual(parseDrawingPackage(JSON.stringify(p),'BTCUSDT','15m'),p);
 assert.throws(()=>parseDrawingPackage('{','BTCUSDT','15m'));assert.throws(()=>parseDrawingPackage(JSON.stringify(p),'ETHUSDT','15m'));assert.throws(()=>parseDrawingPackage(JSON.stringify(p),'BTCUSDT','1h'));
 assert.throws(()=>parseDrawingPackage(JSON.stringify({...p,origin:'manual'}),'BTCUSDT','15m'));
 p.items[0].linked_note.text='🧭'.repeat(4000);assert.equal(parseDrawingPackage(JSON.stringify(p),'BTCUSDT','15m').items[0].linked_note!.text,p.items[0].linked_note.text);
 p.items[0].linked_note.text+='x';assert.throws(()=>parseDrawingPackage(JSON.stringify(p),'BTCUSDT','15m'));
});
test('projection templates preserve mandatory basis and apply only supported ratio/style defaults',()=>{
 const g=projection(),drawing={drawing_id:'d',revision:1,workspace_id:'main',geometry:g,deleted:false,updated_at:1,management:drawingManagement()};
 const defaults=captureDrawingDefault(drawing);assert.equal(validDrawingDefaults({fibonacci_projection:defaults}),true);
 defaults.options.levels=['0','2'];const applied=drawingWithDefault(g,defaults);
 assert.equal(applied.geometry.basis,'PRICE_DELTA');assert.equal(applied.geometry.schema,'chart-fibonacci-projection/1');assert.deepEqual(applied.geometry.levels,['0','2']);
});
