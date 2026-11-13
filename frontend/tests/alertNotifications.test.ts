import {test} from 'node:test';
import assert from 'node:assert/strict';
import {collectEvents,preferences,receipts,validEvent,type AlertEvent} from '../src/alertNotifications.ts';
const event=(id:string,created_at=1000):AlertEvent=>({id,name:'Price',symbol:'BTCUSDT',close:'101.01',message:'Note',candle_time:900,created_at});
test('initial history is baselined and repeated, reordered events cannot notify again',()=>{
 const baseline=collectEvents(null,[event('old')],1000);assert.deepEqual(baseline.fresh,[]);assert.deepEqual(baseline.state.unread,[]);
 const next=collectEvents(baseline.state,[event('new'),event('old'),event('new')],1000);assert.deepEqual(next.fresh.map(e=>e.id),['new']);assert.deepEqual(next.state.unread,['new']);
 const reloaded=collectEvents(receipts(JSON.stringify(next.state)),[event('old'),event('new')],1001);assert.deepEqual(reloaded.fresh,[]);assert.deepEqual(reloaded.state.unread,['new']);
});
test('reconnect backlog is unread but stale or future events do not produce disruptive delivery',()=>{
 const result=collectEvents({seen:[],unread:[]},[event('future',1010),event('fresh',999),event('stale',100)],1000);
 assert.deepEqual(result.fresh.map(e=>e.id),['fresh']);assert.deepEqual(result.state.unread,['stale','fresh','future']);
});
test('notification preferences fail to safe defaults and validate serialized receipt state',()=>{
 assert.deepEqual(preferences('{broken'),{inApp:true,sound:false,desktop:false});assert.deepEqual(preferences('{"sound":"true","desktop":1,"inApp":false}'),{inApp:false,sound:false,desktop:false});
 assert.equal(receipts('{"seen":4}'),null);assert.deepEqual(receipts('{"seen":["x",4],"unread":[null,"x"]}'),{seen:['x'],unread:['x']});assert(validEvent(event('a')));assert(!validEvent({...event('a'),created_at:'1000'}));
});
test('retention is bounded and already read events remain claimed',()=>{
 const events=Array.from({length:1200},(_,i)=>event(String(i)));const collected=collectEvents({seen:[],unread:[]},events,1000);assert.equal(collected.state.seen.length,1000);assert.equal(collected.state.unread.length,100);
 const read={...collected.state,unread:[]};assert.equal(collectEvents(read,events.slice(0,100),1000).fresh.length,0);
});
