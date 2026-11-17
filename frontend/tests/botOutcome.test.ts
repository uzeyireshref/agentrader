import {test} from 'node:test';
import assert from 'node:assert/strict';
import {jobOutcome} from '../src/botOutcome';
import type {BotJob} from '../src/botApi';
test('queue success does not hide uncertain, rejected or partial business results',()=>{
 const job={state:'SUCCEEDED',result:null} as BotJob;
 assert.equal(jobOutcome(job),'Talep işlendi');
 assert.equal(jobOutcome({...job,result_state:'UNKNOWN'}),'Sonuç belirsiz · inceleme gerekiyor');
 for(const [state,label] of [['UNKNOWN','Sonuç belirsiz · inceleme gerekiyor'],['FINAL_WITH_ERRORS','Kısmi sonuç · hata var'],['REJECTED','Borsa veya işlem kontrolü reddetti'],['APPLIED','Uygulandı']])assert.equal(jobOutcome({...job,result:{state}}),label);
 assert.equal(jobOutcome({...job,state:'NEEDS_REVIEW'}),'İnceleme gerekiyor');
});
