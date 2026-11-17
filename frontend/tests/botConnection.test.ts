import {test} from 'node:test';
import assert from 'node:assert/strict';
import {workerCanRead,workerIssue} from '../src/botConnection';
import type {BotStatus} from '../src/botApi';

test('a fresh heartbeat with a worker error cannot admit more account reads',()=>{
 const fresh={enabled:true,worker:'FRESH'} as BotStatus;
 assert.equal(workerCanRead(fresh),true);
 for(const error_code of ['EXECUTION_BUSY','BOT_MONITOR_UNAVAILABLE','BOT_STORAGE_UNAVAILABLE','DEMO_CREDENTIALS_REQUIRED','UNEXPECTED']){
  const status={...fresh,error_code};
  assert.equal(workerCanRead(status),false);
  assert.ok(workerIssue(status));
 }
 assert.equal(workerCanRead({...fresh,enabled:false}),false);
 assert.equal(workerCanRead({...fresh,worker:'OFFLINE'}),false);
 assert.equal(workerCanRead(null),false);
});
