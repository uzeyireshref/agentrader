import {test} from 'node:test';
import assert from 'node:assert/strict';
import {planSelectionKey,batchPlanRows,reversePlanRows,planTimeEligible} from '../src/botPlanSelection';
import {liveCommand} from '../src/BotLiveCommands';
import type {PlanRow,BotSnapshot,LiveSession} from '../src/botApi';
const row=(id:string,version:number,state='AUTHORIZED',symbol='BTCUSDT',direction='LONG'):PlanRow=>({state,digest:String(version).repeat(64),plan:{plan_id:id,version,symbol,direction,execution:{strategy:'SINGLE'}}});
test('expired plans and expired approval leases are excluded without renewing authority',()=>{
 const now=Date.now(),expired=row('expired',1),lease=row('lease',1),pending=row('pending',1,'PENDING_APPROVAL');
 expired.plan.expires_at=new Date(now-1000).toISOString();
 lease.plan.expires_at=new Date(now+60000).toISOString();lease.approval_until=(now-1000)/1000;
 pending.plan.expires_at=new Date(now-1000).toISOString();
 assert.equal(planTimeEligible(expired),false);assert.equal(planTimeEligible(lease,true),false);
 assert.throws(()=>batchPlanRows([expired],['expired@1']));assert.throws(()=>batchPlanRows([lease],['lease@1']));
 assert.deepEqual(reversePlanRows([pending]),[]);
 assert.equal(lease.approval_until,(now-1000)/1000);
});
test('batch selection pins the selected version even when the same id has newer versions',()=>{
 const old=row('plan-a',1),next=row('plan-a',2),eth=row('plan-b',1,'AUTHORIZED','ETHUSDT');
 const result=batchPlanRows([next,old,eth],[planSelectionKey(old),planSelectionKey(eth)]);
 assert.deepEqual(result,[old,eth]);
 const command=liveCommand('BATCH_CREATE_ORDERS','BTCUSDT',{}, {plans:[next,old,eth],sessions:[]} as unknown as BotSnapshot,[planSelectionKey(old),planSelectionKey(eth)],[]);
 assert.deepEqual((command.parameters.plans as {version:number}[]).map(r=>r.version),[1,1]);
});
test('batch refuses vanished, unauthorized, duplicate-version or duplicate-symbol selections',()=>{
 const a=row('a',1),b=row('b',1),pending=row('c',1,'PENDING_APPROVAL');
 for(const selected of [[],['a'],['a@1','a@1'],['a@1','b@1'],['c@1'],['missing@1']])assert.throws(()=>batchPlanRows([a,b,pending],selected));
});
test('reverse plan selection excludes wrong symbol, same direction and nonpending versions',()=>{
 const source={session_id:'v2-owned',symbol:'BTCUSDT',plan:{direction:'LONG'}} as LiveSession;
 const wrong=row('opposite',1,'PENDING_APPROVAL','BTCUSDT','SHORT');
 const selected=row('opposite',2,'PENDING_APPROVAL','BTCUSDT','SHORT');
 const plans=[wrong,selected,row('same',1,'PENDING_APPROVAL'),row('eth',1,'PENDING_APPROVAL','ETHUSDT','SHORT'),row('old',1,'EXPIRED','BTCUSDT','SHORT')];
 assert.deepEqual(reversePlanRows(plans,source),[wrong,selected]);
 const command=liveCommand('REVERSE_POSITION','BTCUSDT',{session:source.session_id,nextPlan:planSelectionKey(selected)},{plans,sessions:[source]} as BotSnapshot,[],[]);
 assert.equal(command.parameters.next_version,2);assert.equal(command.parameters.next_digest,selected.digest);
 assert.throws(()=>liveCommand('REVERSE_POSITION','BTCUSDT',{session:source.session_id,nextPlan:'opposite'},{plans,sessions:[source]} as BotSnapshot,[],[]));
});
