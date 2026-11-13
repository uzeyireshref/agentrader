import {test} from 'node:test';
import assert from 'node:assert/strict';
import {applyPacket,initialState,type Packet} from '../src/types';
import {checkFreshness} from '../src/freshness';
import {validTiming,type TimeProof} from '../src/timing';
const proof:TimeProof={schema:'chart-time-proof/1',policy:{schema:'chart-time-policy/1'},state:'FRESH',reason:null,data_age_ms:0,upstream_age_upper_ms:1,uncertainty_ms:1,upstream_event_time:1800000000000};
const packet:Packet={type:'snapshot',symbol:'BTCUSDT',interval:'15m',status:'LIVE',sequence:1,generation:1,received_at:1800000000000,timing:proof};
const live=()=>applyPacket(initialState('BTCUSDT','15m'),packet,100,1000);

test('producer wall epoch never participates in consumer timing subtraction',()=>{
 const state=live();assert.equal(checkFreshness(state,1001,101),state);
 assert.equal(checkFreshness(state,11001,10101).status,'STALE');
});
test('identical fresh heartbeat replay cannot reset frozen upstream age',()=>{
 let state=live();
 for(let i=1;i<=6;i++)state=applyPacket(state,{...packet,type:'update'},100+i*2000,1000+i*2000);
 assert.equal(state.timing!.data_age_ms,12000);
 assert.equal(checkFreshness(state,13000,12100).status,'STALE');
});
test('fresh transport heartbeat with old producer data remains stale',()=>{
 const state=applyPacket(live(),{...packet,type:'update',timing:{...proof,data_age_ms:11000,upstream_age_upper_ms:11001}},200,1100);
 assert.equal(checkFreshness(state,1100,200).status,'STALE');
});
test('wall jumps in either direction are sticky until a new snapshot',()=>{
 for(const wall of [-99000,101000]){
  const blocked=checkFreshness(live(),wall,100);assert.equal(blocked.status,'STALE');assert.equal(blocked.consumer_clock_untrusted,true);
  const beat=applyPacket(blocked,{...packet,type:'update'},200,wall+100);assert.equal(checkFreshness(beat,wall+100,200).status,'STALE');
  const snapshot=applyPacket(beat,{...packet,generation:2},300,wall+200);
  assert.equal(checkFreshness(snapshot,wall+200,300).status,'LIVE');
 }
});
test('packet ingestion detects wall jumps between heartbeats',()=>{
 const next=applyPacket(live(),{...packet,type:'update'},200,100000);
 assert.equal(checkFreshness(next,100000,200).status,'STALE');
});
test('missing, malformed, future and excessive uncertainty evidence is blocked',()=>{
 for(const value of [null,{}, {...proof,data_age_ms:NaN},{...proof,uncertainty_ms:-1},{...proof,upstream_event_time:null}])assert.equal(validTiming(value),false);
 for(const reason of ['CLOCK_UNTRUSTED','FUTURE_UPSTREAM_TIME','SNAPSHOT_REQUIRED','AWAITING_UPSTREAM']){
  const state=applyPacket(live(),{...packet,type:'update',timing:{...proof,state:'BLOCKED',reason}},200,1100);
  assert.equal(checkFreshness(state,1100,200).status,'STALE');
 }
 const uncertain=applyPacket(live(),{...packet,type:'update',timing:{...proof,uncertainty_ms:1001}},200,1100);assert.equal(checkFreshness(uncertain,1100,200).status,'STALE');
 const legacy={...initialState('BTCUSDT','15m'),status:'LIVE',received_at:2000};assert.equal(checkFreshness(legacy,1000).status,'STALE');
});
test('a new source event cannot be smuggled in an equal-sequence heartbeat',()=>{
 const state=applyPacket(live(),{...packet,type:'update',timing:{...proof,upstream_event_time:1800000000001}},200,1100);
 assert.equal(state.status,'STALE');
});
