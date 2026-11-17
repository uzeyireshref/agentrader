import {test} from 'node:test';
import assert from 'node:assert/strict';
import {draftError,initialBotDraft,defaultGrid,defaultExecution,updateBotDraft,priceMatches} from '../src/botPrototype.ts';

test('prototype rejects invalid amounts and prices instead of showing an approval',()=>{
 for(const value of ['','0','-1','NaN','Infinity','1e309','1,2'])for(const key of ['entry','amount','stop','target'])assert.notEqual(draftError({...initialBotDraft,[key]:value}),'');
});
test('prototype long and short stop/target orientation is checked',()=>{
 assert.equal(draftError(initialBotDraft),'');
 assert.notEqual(draftError({...initialBotDraft,side:'Short'}),'');
 assert.equal(draftError({...initialBotDraft,side:'Short',stop:'94000',target:'88000'}),'');
 assert.notEqual(draftError({...initialBotDraft,stop:initialBotDraft.entry}),'');
});
test('grid and neutral cannot reuse a single ticket for approval',()=>{
 for(const kind of ['GRID','NEUTRAL'] as const)assert.notEqual(draftError({...initialBotDraft,kind}),'');
});

test('directional grid uses budget, band and exit boundary rules',()=>{
 const d={...initialBotDraft,kind:'GRID' as const,grid:{...defaultGrid}};
 assert.equal(draftError(d),'');
 assert.notEqual(draftError({...d,target:'90500'}),'');
 assert.notEqual(draftError({...d,grid:{...defaultGrid,intervals:'101'}}),'');
 assert.notEqual(draftError({...d,grid:{...defaultGrid,budget:'0'}}),'');
 assert.equal(draftError({...d,side:'Short',stop:'92000',target:'88000'}),'');
});
test('neutral requires external stops, internal center, bounded count and nonzero shares',()=>{
 const d={...initialBotDraft,kind:'NEUTRAL' as const,grid:{...defaultGrid}};
 assert.equal(draftError(d),'');
 for(const grid of [{...defaultGrid,intervals:'21'},{...defaultGrid,longPercent:'100'},{...defaultGrid,longPercent:'0'},{...defaultGrid,upperStop:'90500'}])assert.notEqual(draftError({...d,grid}),'');
 assert.notEqual(draftError({...d,entry:'90001'}),'');
 assert.notEqual(draftError({...d,stop:'89500'}),'');
});
test('limit options reject incompatible STP and expired GTD',()=>{
 assert.notEqual(draftError({...initialBotDraft,options:{tif:'FOK',stp:'EXPIRE_BOTH',expires:''}}),'');
 assert.notEqual(draftError({...initialBotDraft,options:{tif:'GTD',stp:'',expires:'2000-01-01T00:00'}}),'');
 assert.equal(draftError({...initialBotDraft,options:{tif:'IOC',stp:'EXPIRE_BOTH',expires:''}}),'');
});

test('execution draft rejects invalid leverage and drift without inventing a bracket maximum',()=>{
 for(const leverage of ['0','-1','1.5','Infinity','99999999999999999'])assert.notEqual(draftError({...initialBotDraft,execution:{...defaultExecution,leverage}}),'');
 for(const driftBps of ['0','101','NaN'])assert.notEqual(draftError({...initialBotDraft,execution:{...defaultExecution,driftBps}}),'');
 assert.equal(draftError({...initialBotDraft,execution:{...defaultExecution,leverage:'20',driftBps:'100'}}),'');
});
test('neutral needs hedge and conditional triggers remain within protection boundaries',()=>{
 const d={...initialBotDraft,kind:'NEUTRAL' as const,grid:{...defaultGrid}};
 assert.notEqual(draftError({...d,execution:{...defaultExecution,positionMode:'one-way'}}),'');
 assert.equal(draftError({...d,execution:{...defaultExecution,condition:'MARK_AT_OR_BELOW',trigger:'90000'}}),'');
 assert.notEqual(draftError({...d,execution:{...defaultExecution,condition:'MARK_AT_OR_ABOVE',trigger:'92000'}}),'');
 assert.notEqual(draftError({...initialBotDraft,execution:{...defaultExecution,condition:'MARK_AT_OR_BELOW'}}),'');
});

test('market and grid transitions remove limit-only authority from the draft',()=>{
 const limit={...initialBotDraft,options:{tif:'GTD' as const,stp:'EXPIRE_BOTH' as const,expires:'2099-01-01T00:00',priceMatch:'QUEUE' as const}};
 const market=updateBotDraft(limit,{orderType:'MARKET'});
 assert.equal(market.options,undefined);
 assert.equal(draftError(market),'');
 assert.equal(updateBotDraft(market,{orderType:'LIMIT'}).options,undefined);
 assert.equal(updateBotDraft(limit,{kind:'GRID',grid:{...defaultGrid}}).options,undefined);
 assert.notEqual(draftError({...market,options:limit.options}),'');
});
test('all supported price matching methods retain a risk reference',()=>{
 for(const priceMatch of priceMatches){
  const d={...initialBotDraft,options:{tif:'GTC' as const,stp:'' as const,expires:'',priceMatch}};
  assert.equal(draftError(d),'');
  assert.notEqual(draftError({...d,entry:''}),'');
 }
});
