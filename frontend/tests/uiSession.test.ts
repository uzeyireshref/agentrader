import {test} from 'node:test';
import assert from 'node:assert/strict';
import {UiPublisher,type UiEnvelope,type UiPolicy,type UiReply} from '../src/uiSession.ts';
import {currentUiCrosshair,emptyCrosshair} from '../src/uiCrosshair.ts';
import type {Candle} from '../src/types.ts';

const policy:UiPolicy={schema_version:'chart-ui-policy/1',server_instance_id:'epoch-a',ttl_seconds:30,min_publish_interval_ms:500,heartbeat_seconds:5,authentication_required:false};
test('stationary hover uses latest candle and exact source decimals; missing candle clears it',()=>{
 const row:Candle={time:1800000000,open:100,high:110,low:90,close:105,volume:10,quote_volume:1050,close_time:1800000899999,closed:false,exact:{close:'105.0000'}};
 const hover={time:row.time,price:'100.250',pane:0,hover_candle:{close:'stale'}};
 assert.equal(currentUiCrosshair([row],hover).hover_candle?.close,'105.0000');
 assert.equal(currentUiCrosshair([{...row,closed:true,exact:{close:'106.0000'}}],hover).hover_candle?.closed,true);
 assert.deepEqual(currentUiCrosshair([],hover),emptyCrosshair());
});
function fixture(){
 let count=0,state={x:1},env:{visibility:'visible'|'hidden';online:boolean;clientTime:number}={visibility:'visible',online:true,clientTime:1000};
 const calls:{id:string;key:string;value:UiEnvelope;keepalive:boolean}[]=[],statuses:string[]=[];
 let reply:UiReply={status:200},sender:((value:UiEnvelope)=>Promise<UiReply>)|null=null;
 const client=new UiPublisher({policy:{...policy},collect:()=>({...state}),environment:()=>env,
  random:()=>({id:'tab-'+ ++count,key:String(count).repeat(64)}),identity:(id,status)=>statuses.push(id+':'+status),
  refreshPolicy:async()=>({...policy,server_instance_id:'epoch-b'}),
  send:async(id,key,value,keepalive)=>{calls.push({id,key,value,keepalive});return sender?sender(value):reply;}});
 return {client,calls,statuses,env,state,setReply:(r:UiReply)=>{reply=r;},setSender:(fn:typeof sender)=>{sender=fn;}};
}

test('pointer changes coalesce to at most two normal reports per second; quiet state uses heartbeat',async()=>{
 const f=fixture();await f.client.step(0);assert.equal(f.calls.length,1);
 for(let n=1;n<500;n++){f.state.x=n;f.client.markDirty();await f.client.step(n);}
 assert.equal(f.calls.length,1);await f.client.step(500);assert.equal(f.calls.length,2);
 assert.equal(f.calls[1].value.snapshot.x,499);assert.equal(f.calls[1].value.sequence,2);
 await f.client.step(1000);assert.equal(f.calls.length,2);
 f.client.markDirty();await f.client.step(2000);assert.equal(f.calls.length,2);
 await f.client.step(5500);assert.equal(f.calls.length,3);
 assert.equal(f.calls[2].value.sequence,3);assert.equal(f.calls[2].value.client_time_ms,1000);
});

test('hidden/offline/close immediately redact despite pending normal request; delayed response ignored',async()=>{
 const f=fixture();let resolve!:(v:UiReply)=>void;
 f.setSender(value=>value.sequence===1?new Promise(r=>{resolve=r;}):Promise.resolve({status:200}));
 const pending=f.client.step(0);f.env.visibility='hidden';await f.client.restrict(1);
 assert.equal(f.calls[1].value.visibility,'hidden');assert.equal(f.calls[1].keepalive,true);
 resolve({status:200});await pending;assert.equal(f.statuses.at(-1),'tab-1:HIDDEN');
 f.env.visibility='visible';f.env.online=false;await f.client.restrict(2,'OFFLINE');
 assert.equal(f.calls[2].value.client_status,'OFFLINE');await f.client.step(5000);assert.equal(f.calls.length,3);
 await f.client.restrict(3,'CLOSED');assert.equal(f.calls[3].value.client_status,'CLOSED');
 f.env.online=true;await f.client.step(10000);assert.equal(f.calls.length,4);
 f.setSender(null);f.client.resume();await f.client.step(10001);assert.equal(f.calls[4].id,'tab-2');assert.equal(f.calls[4].value.sequence,1);
});

test('expired identity retires, rotates and never reuses old sequence or key',async()=>{
 const f=fixture();await f.client.step(0);f.setReply({status:410,body:{error:{code:'UI_SESSION_EXPIRED'}}});
 await f.client.step(31000);assert.equal(f.calls[2].value.client_status,'CLOSED');
 f.setReply({status:200});await f.client.step(36000);
 assert.equal(f.calls[3].id,'tab-2');assert.equal(f.calls[3].value.sequence,1);assert.notEqual(f.calls[3].key,f.calls[0].key);
 assert.ok(f.statuses.every(v=>!v.includes(f.calls[0].key)));
});

test('server epoch refresh rotates publisher; failed network waits then recovers with fresh state',async()=>{
 const f=fixture();f.setReply({status:409,body:{error:{code:'UI_SESSION_SERVER_RESTARTED'}}});await f.client.step(0);
 f.setReply({status:200});await f.client.step(5000);assert.equal(f.calls[1].value.server_instance_id,'epoch-b');
 f.setSender(async()=>{throw Error('offline');});f.state.x=7;f.client.markDirty();await f.client.step(5500);
 await f.client.step(6000);assert.equal(f.calls.length,3);f.setSender(null);await f.client.step(10500);
 assert.equal(f.calls[3].value.snapshot.x,7);assert.equal(f.statuses.at(-1),'tab-2:READY');
});

test('two publishers never combine tabs and unauthorized/throttled responses back off',async()=>{
 const a=fixture(),b=fixture();a.state.x=2;b.state.x=3;await a.client.step(0);await b.client.step(0);
 assert.equal(a.calls[0].value.snapshot.x,2);assert.equal(b.calls[0].value.snapshot.x,3);
 a.setReply({status:401});a.state.x=4;a.client.markDirty();await a.client.step(500);assert.equal(a.statuses.at(-1),'tab-1:UNAUTHORIZED');
 await a.client.step(1000);assert.equal(a.calls.length,2);a.setReply({status:429});await a.client.step(5500);
 await a.client.step(6000);assert.equal(a.calls.length,3);a.setReply({status:200});await a.client.step(6500);assert.equal(a.calls.length,4);
});
