import {test} from 'node:test';
import assert from 'node:assert/strict';
import fixture from './fixtures/data-evidence.json';
import {isDemoMarket,marketSource,marketEnvironment} from '../src/marketEnvironment';
import {applyPacket,initialState,type Packet} from '../src/types';

test('demo source identity rejects production and partial or mixed identities',()=>{
 const good={source:marketSource,environment:marketEnvironment,product:'USD-M',price_type:'LAST_PRICE'};
 assert.equal(isDemoMarket(good),true);
 for(const patch of [{source:'binance_usdm_live_trade_price'},{environment:'live_public'},{product:'COIN-M'},{price_type:'MARK_PRICE'}])assert.equal(isDemoMarket({...good,...patch}),false);
 assert.equal(isDemoMarket({}),false);assert.equal(isDemoMarket(null),false);
});

test('real source cannot enter demo stream even with otherwise valid demo proof',()=>{
 const c=fixture.cases[0],p={type:'snapshot',source:marketSource,environment:marketEnvironment,product:'USD-M',price_type:'LAST_PRICE',symbol:'BTCUSDT',interval:'15m',status:'LIVE',sequence:1,generation:c.proof.generation,stream_epoch:c.proof.stream_epoch,data_proof:c.proof,quality:c.quality,market:c.market,candles:c.rows,received_at:1000} as Packet;
 const state=initialState('BTCUSDT','15m');
 assert.notEqual(applyPacket(state,p),state);
 for(const patch of [{source:'binance_usdm_live_trade_price'},{environment:'live_public'}])assert.equal(applyPacket(state,{...p,...patch}),state);
});
