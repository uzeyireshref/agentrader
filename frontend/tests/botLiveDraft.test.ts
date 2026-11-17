import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createLiveBotDraft} from '../src/botLiveDraft';
import {draftError,updateBotDraft} from '../src/botPrototype';

test('live plan types cannot inherit prototype prices or a financial budget',()=>{
 const draft=createLiveBotDraft('ETHUSDT');
 assert.equal(draft.symbol,'ETHUSDT');
 assert.deepEqual([draft.entry,draft.stop,draft.target,draft.amount,draft.execution?.trigger],['','','','','']);
 for(const kind of ['SINGLE','GRID','NEUTRAL'] as const){
  const next=updateBotDraft(draft,{kind});
  assert.ok(draftError(next));
  if(kind!=='SINGLE')assert.deepEqual([next.grid?.lower,next.grid?.upper,next.grid?.upperStop,next.grid?.budget],['','','','']);
 }
 draft.grid!.lower='123';draft.execution!.trigger='456';
 const independent=createLiveBotDraft();
 assert.equal(independent.grid?.lower,'');assert.equal(independent.execution?.trigger,'');
});
