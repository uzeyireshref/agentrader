import {test} from 'node:test';
import assert from 'node:assert/strict';
import fixture from './fixtures/data-evidence.json';
import {ChartDisplayCache} from '../src/chartDisplayCache';
import {initialState,type ChartState} from '../src/types';

const sample=fixture.cases[0];
const state={...initialState('BTCUSDT','15m'),candles:sample.rows,market:sample.market,
 data_proof:sample.proof,status:'LIVE',stream_epoch:sample.proof.stream_epoch,quality:'OK'} as ChartState;
test('display cache isolates symbols and intervals and strips eligibility fields',()=>{
 const cache=new ChartDisplayCache(()=>0);cache.put(state);
 assert.equal(cache.get('ETHUSDT','15m'),undefined);assert.equal(cache.get('BTCUSDT','1h'),undefined);
 assert.deepEqual(Object.keys(cache.get('BTCUSDT','15m')!).sort(),['candles','market','quality']);
 assert.equal(cache.get('BTCUSDT','15m')!.candles,state.candles);
});
test('display cache expires previews and bounds retained selections by LRU',()=>{
 let now=0;const cache=new ChartDisplayCache(()=>now,2,100);
 cache.put(state);cache.put({...state,symbol:'ETHUSDT'});cache.get('BTCUSDT','15m');cache.put({...state,symbol:'BNBUSDT'});
 assert.equal(cache.get('ETHUSDT','15m'),undefined);assert.ok(cache.get('BTCUSDT','15m'));
 now=101;assert.equal(cache.get('BTCUSDT','15m'),undefined);
});
test('unproven or invalid candles never become previews',()=>{
 const cache=new ChartDisplayCache(()=>0);
 cache.put({...state,data_proof:undefined});assert.equal(cache.get('BTCUSDT','15m'),undefined);
 cache.put({...state,candles:[{...state.candles[0],time:1.5}]});assert.equal(cache.get('BTCUSDT','15m'),undefined);
});
