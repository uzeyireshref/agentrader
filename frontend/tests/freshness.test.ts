import {test} from 'node:test';
import assert from 'node:assert/strict';
import {checkFreshness} from '../src/freshness';
import {initialState,type ChartState} from '../src/types';
const live:ChartState={...initialState('BTCUSDT','15m'),status:'LIVE',received_at:1000};
test('display freshness changes only beyond the declared ten-second boundary',()=>{
 assert.equal(checkFreshness(live,11000),live);
 const stale=checkFreshness(live,11001);
 assert.equal(stale.status,'STALE');assert.equal(stale.candles,live.candles);
 assert.equal(checkFreshness({...live,received_at:null},11001).status,'STALE');
});
test('old LIVE heartbeat stays stale while a fresh packet may restore LIVE',()=>{
 assert.equal(checkFreshness({...live,status:'LIVE'},14000).status,'STALE');
 assert.equal(checkFreshness({...live,received_at:14000},14001).status,'LIVE');
});
test('freshness never hides rendering, reconnect or synchronization states',()=>{
 for(const status of ['RENDER_ERROR','RECONNECTING','SYNCING','GAP','ERROR']){
  const state={...live,status};assert.equal(checkFreshness(state,50000),state);
 }
});
