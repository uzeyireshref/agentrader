import {test} from 'node:test';
import assert from 'node:assert/strict';
import {BotApiError,exchangeDiagnosticMessage} from '../src/botApi';
test('only a proven exchange rejection receives a specific explanation',()=>{
 for(const code of [-2019,-2027,-4061,-1111,-4164]){
  assert.ok(exchangeDiagnosticMessage({category:'EXCHANGE',delivery_status:'REJECTED',code}));
  for(const delivery_status of ['UNKNOWN','NOT_SENT','READ_FAILED'])assert.equal(exchangeDiagnosticMessage({category:'EXCHANGE',delivery_status,code}),null);
 }
 assert.equal(exchangeDiagnosticMessage({category:'EXCHANGE',delivery_status:'REJECTED',code:-1013}),null);
 assert.match(new BotApiError('BOT_EXCHANGE_UNAVAILABLE',{category:'EXCHANGE',delivery_status:'UNKNOWN',code:-2019}).message,/mevcut kimlikle/);
});
