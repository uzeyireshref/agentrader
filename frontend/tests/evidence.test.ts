import {checkFreshness} from '../src/freshness';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fixture from './fixtures/data-evidence.json';
import {sha256,canonical,verifyEvidence,type DataProof} from '../src/evidence';
import {applyPacket,beginStream,initialState,type Candle,type Market,type Packet} from '../src/types';
const example=fixture.cases[0];
function packet(epoch='a'.repeat(32),generation=1,sequence=1):Packet{
 // Re-hash the fixed Python payload with independent node crypto when changing context.
 const proof=structuredClone(example.proof) as DataProof;
 const rows=structuredClone(example.rows) as Candle[],market=structuredClone(example.market) as Market;
 const quality=structuredClone(example.quality);
 const floatHex=(n:number)=>{const b=Buffer.alloc(8);b.writeDoubleBE(n===0?0:n);return b.toString('hex');};
 const payload={schema:'chart-data-snapshot/1',source:'binance_usdm_live_trade_price',environment:'live_public',product:'USD-M',price_type:'LAST_PRICE',symbol:'BTCUSDT',interval:'15m',stream_epoch:epoch,generation,data_revision:proof.data_revision,market,quality,rows:rows.map(r=>({time:r.time,close_time:r.close_time,closed:r.closed,chart_values:[r.open,r.high,r.low,r.close,r.volume,r.quote_volume].map(floatHex),exact:r.exact??null}))};
 proof.stream_epoch=epoch;proof.generation=generation;proof.snapshot_hash=createHash('sha256').update(canonical(payload)).digest('hex');
 return {type:'snapshot',stream_epoch:epoch,data_proof:proof,source:'binance_usdm_live_trade_price',environment:'live_public',product:'USD-M',price_type:'LAST_PRICE',symbol:'BTCUSDT',interval:'15m',generation,sequence,status:'LIVE',received_at:1000,candles:rows,market,quality};
}
test('fingerprint matches independent node crypto for padding boundaries and Unicode',()=>{
 for(const length of [0,1,55,56,63,64,65,127,128,129,1000,10000])for(const word of ['a','ç🙂']){
  const text=word.repeat(length);assert.equal(sha256(text),createHash('sha256').update(text).digest('hex'));
 }
 assert.equal(sha256('abc'),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
});
test('all Python snapshot fixtures independently verify in TypeScript',()=>{
 for(const c of fixture.cases)assert.equal(verifyEvidence(c.rows as Candle[],c.market,c.quality,'BTCUSDT','15m',c.proof.stream_epoch,c.proof.generation,c.proof as DataProof),true,c.name);
});
test('first update and malformed or missing snapshot proof cannot cross barrier',()=>{
 const state=initialState('BTCUSDT','15m'),p=packet();
 assert.equal(applyPacket(state,{...p,type:'update',candles:undefined,tail:p.candles!.slice(-2)}),state);
 assert.equal(applyPacket(state,{...p,data_proof:null}),state);
 assert.equal(applyPacket(state,{...p,stream_epoch:'invalid'}),state);
 const bad=structuredClone(p);bad.candles![0].close+=1;assert.equal(applyPacket(state,bad),state);
 const accepted=applyPacket(state,p);assert.equal(accepted.stream_epoch,p.stream_epoch);assert.equal(accepted.snapshot_required,false);
});
test('restart epoch permits reset counters only after snapshot and rejects retired epoch',()=>{
 const first=applyPacket(initialState('BTCUSDT','15m'),packet('a'.repeat(32),9,100));
 const waiting=beginStream(first),next=packet('b'.repeat(32),1,1);
 assert.equal(applyPacket(waiting,{...next,type:'update',candles:undefined,tail:next.candles!.slice(-2)}),waiting);
 const restarted=applyPacket(waiting,next);assert.equal(restarted.generation,1);assert.equal(restarted.stream_epoch,next.stream_epoch);
 assert.equal(applyPacket(restarted,packet('a'.repeat(32),10,101)),restarted);
 assert.equal(applyPacket(restarted,{...next,stream_epoch:undefined,data_proof:undefined}),restarted);
});
test('same producer epoch websocket reconnect still requires a full snapshot',()=>{
 const p=packet(),first=applyPacket(initialState('BTCUSDT','15m'),p),waiting=beginStream(first);
 assert.equal(applyPacket(waiting,{...p,type:'update',candles:undefined,tail:p.candles!.slice(-2)}),waiting);
 assert.equal(applyPacket(waiting,p).snapshot_required,false);
});
test('sequence jump alone is not a grid gap; stale packets change nothing',()=>{
 const p=packet(),first=applyPacket(initialState('BTCUSDT','15m'),p);
 const jump=applyPacket(first,{...p,type:'update',sequence:100,candles:undefined,tail:p.candles!.slice(-2)});
 assert.equal(jump.sequence,100);assert.equal(jump.data_proof!.missing_bars,0);
 assert.equal(applyPacket(jump,{...p,sequence:99}),jump);
 const duplicate=applyPacket(jump,{...p,type:'update',sequence:100,candles:undefined,tail:p.candles!.slice(-2)});
 assert.equal(duplicate.candles,jump.candles);assert.equal(duplicate.data_proof!.data_revision,jump.data_proof!.data_revision);
});
test('payload market quality grid and proof metadata tampering all fail',()=>{
 const original=packet(),state=initialState('BTCUSDT','15m');
 for(const field of ['price','exact','market','quality','grid','warmup','epoch','source']){
  const p=structuredClone(original);
  if(field==='price')p.candles![0].close+=1;
  if(field==='exact')p.candles![0].exact!.close='105.000000000000000000001';
  if(field==='market')p.market!.tick_size='1';
  if(field==='quality')p.quality!.state='GAP';
  if(field==='grid')p.candles!.splice(10,1);
  if(field==='warmup')p.data_proof!.warmup_available_closed_bars++;
  if(field==='epoch')p.stream_epoch='f'.repeat(32);
  if(field==='source')p.price_type='MARK_PRICE';
  assert.equal(applyPacket(state,p),state,field);
 }
});
test('independent older loaded history does not alter verified producer window',()=>{
 const p=packet();const old={...p.candles![0],time:p.candles![0].time-900,close_time:p.candles![0].close_time-900000};
 const initial={...initialState('BTCUSDT','15m'),candles:[old]};const state=applyPacket(initial,p);
 assert.equal(state.candles.length,p.candles!.length+1);assert.equal(state.data_proof!.snapshot_hash,p.data_proof!.snapshot_hash);
});

test('retired epochs are remembered for the entire current view lifetime',()=>{
 let state=applyPacket(initialState('BTCUSDT','15m'),packet('a'.repeat(32),1,1));
 for(let i=1;i<=66;i++)state=applyPacket(state,packet(i.toString(16).padStart(32,'0'),i+1,1));
 assert.equal(state.retired_epochs!.length,66);
 assert.equal(applyPacket(beginStream(state),packet('a'.repeat(32),999,999)).stream_epoch,state.stream_epoch);
});

test('blocked grid and unproven precision never render a Live label',()=>{
 for(const c of fixture.cases.filter(c=>c.proof.state==='BLOCKED')){
  const p={...packet(),candles:c.rows as Candle[],market:c.market,quality:c.quality,data_proof:c.proof as DataProof};
  const state=applyPacket(initialState('BTCUSDT','15m'),p);
  assert.ok(state.data_proof);
  assert.equal(checkFreshness(state,1000).status,c.name==='gap'?'GAP':'UNVERIFIED');
 }
});
