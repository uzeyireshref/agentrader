import {test} from 'node:test';
import assert from 'node:assert/strict';
import {draftValidation} from '../src/botDraftValidation';
import {createLiveBotDraft} from '../src/botLiveDraft';
import {initialBotDraft,defaultGrid} from '../src/botPrototype';
test('empty live form identifies every missing field before any preview',()=>{
 assert.deepEqual(Object.keys(draftValidation(createLiveBotDraft()).fields),['entry','stop','target','amount']);
 assert.equal(draftValidation(initialBotDraft).message,'');
});
test('direction errors attach to stop and target and do not change decimal input',()=>{
 const draft={...initialBotDraft,stop:'91000',target:'89000'};
 const result=draftValidation(draft);
 assert.deepEqual(Object.keys(result.fields),['stop','target']);
 assert.equal(draft.stop,'91000');
 assert.ok(draftValidation({...initialBotDraft,amount:'1,5'}).fields.amount);
});
test('grid bounds, intervals and blank budget receive distinct field errors',()=>{
 const result=draftValidation({...initialBotDraft,kind:'GRID',grid:{...defaultGrid,lower:'91000',upper:'89000',intervals:'1',budget:''}});
 for(const field of ['grid.upper','grid.intervals','grid.budget'])assert.ok(result.fields[field]);
});
test('directional grid accepts a stop inside its band and a target exactly at the exit boundary',()=>{
 const valid={...initialBotDraft,kind:'GRID' as const,stop:'89500',target:'91000',grid:{...defaultGrid}};
 assert.equal(draftValidation(valid).message,'');
 assert.ok(draftValidation({...valid,stop:'90001'}).fields.stop);
 assert.ok(draftValidation({...valid,target:'90999'}).fields.target);
});
