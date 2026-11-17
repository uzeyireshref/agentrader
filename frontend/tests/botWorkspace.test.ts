import {test} from 'node:test';
import assert from 'node:assert/strict';
import {draftFromDrawing} from '../src/botChartBridge.ts';
import {draftError,initialBotDraft,updateBotDraft} from '../src/botPrototype.ts';
import {parseLocalRecords} from '../src/botLocalState.ts';
import {timerDraftError} from '../src/timerPrototype.ts';
import {batchError} from '../src/BotBatch.tsx';
import type {Drawing} from '../src/drawings.ts';

const drawing:Drawing={drawing_id:'position-1',revision:4,workspace_id:'main',deleted:false,updated_at:1,geometry:{kind:'long_plan',schema:'chart-position/1',symbol:'ETHUSDT',price_source:'LAST_PRICE',label:'Plan',params:{risk_budget:null,fee_bps:'0',slippage_bps:'0'},anchors:[{time:1000,price:'3000'},{time:2000,price:'2900'},{time:2000,price:'3300'}]}};
test('chart import retains decimal text and revision without mutating chart or granting execution',()=>{
 const before=structuredClone(drawing);const draft=draftFromDrawing(initialBotDraft,drawing);
 assert.equal(draft.entry,'3000');assert.equal(draft.stop,'2900');assert.equal(draft.target,'3300');assert.equal(draft.symbol,'ETHUSDT');assert.equal(draft.source?.revision,4);assert.deepEqual(drawing,before);
 assert.equal(updateBotDraft(draft,{entry:'3010'}).source,undefined);
 assert.throws(()=>draftFromDrawing(initialBotDraft,{...drawing,deleted:true}));
 assert.throws(()=>draftFromDrawing(initialBotDraft,{...drawing,geometry:{...drawing.geometry,kind:'horizontal'}}));
});
test('target weights are exact and break-even cannot reference the last target',()=>{
 const d={...initialBotDraft,targets:[{price:'94000',percent:'33.3'},{price:'95000',percent:'33.3'},{price:'96000',percent:'33.4'}],breakEven:'1'};
 assert.equal(draftError(d),'');
 assert.notEqual(draftError({...d,breakEven:'3'}),'');
 assert.notEqual(draftError({...d,targets:[{price:'94000',percent:'99.999999999999999999'}]}),'');
 assert.notEqual(draftError({...d,targets:[{price:'95000',percent:'50'},{price:'94000',percent:'50'}]}),'');
});
test('local records reject malformed or oversized external content',()=>{
 assert.deepEqual(parseLocalRecords(null),[]);assert.throws(()=>parseLocalRecords('{}'));assert.throws(()=>parseLocalRecords(JSON.stringify(Array(201).fill({}))));
 assert.throws(()=>parseLocalRecords(JSON.stringify([{id:'1',at:'bad',kind:'command',label:'x',detail:''}])));
});
test('timer requires explicit scope and bounded heartbeat/lease',()=>{
 const d={action:'Kur' as const,symbol:'BTCUSDT',countdown:'60000',heartbeat:'10000',lease:'60000',timerId:'',acknowledged:true};
 assert.equal(timerDraftError(d),'');assert.notEqual(timerDraftError({...d,acknowledged:false}),'');assert.notEqual(timerDraftError({...d,heartbeat:'31000'}),'');assert.notEqual(timerDraftError({...d,lease:'600001'}),'');assert.notEqual(timerDraftError({...d,action:'Yenile'}),'');
 assert.equal(timerDraftError({...d,action:'Sorgula',timerId:'tmr-'+'a'.repeat(40)}),'');
});
test('batch detects duplicate and mixed-scope members instead of treating HTTP success as all-member success',()=>{
 const r={id:'r1',symbol:'BTCUSDT',reference:'plan-a',version:'1',digest:'a'.repeat(64),quantity:'0.001',price:'90000',selected:true};
 assert.equal(batchError('Oluştur',[r]),'');assert.notEqual(batchError('Oluştur',[r,{...r,id:'r2'}]),'');
 assert.notEqual(batchError('Değiştir',[r,{...r,id:'r2',symbol:'ETHUSDT',reference:'order-b'}]),'');
 assert.notEqual(batchError('İptal',[]),'');
});

test('local trailing limits and plan transitions cannot carry incompatible policies',()=>{
 const trailing={activation:'91000',distance:'100',step:'25',nativeStop:false};
 assert.equal(draftError({...initialBotDraft,trailing}),'');
 assert.notEqual(draftError({...initialBotDraft,trailing:{...trailing,step:'101'}}),'');
 assert.equal(updateBotDraft({...initialBotDraft,trailing},{kind:'NEUTRAL'}).trailing,undefined);
 assert.equal(updateBotDraft({...initialBotDraft,orderType:'MARKET',execution:{leverage:'3',margin:'ISOLATED',positionMode:'hedge',condition:'MARK_AT_OR_BELOW',trigger:'90000',driftBps:'50'}},{orderType:'LIMIT'}).execution?.condition,'IMMEDIATE');
});
