import { test } from "node:test";
import assert from "node:assert/strict";
import fixture from "./fixtures/data-evidence.json";
import {
  startChartMarketSession,
  type MarketSocket,
  type MarketSessionEnvironment,
} from "../src/chartMarketSession";
import {
  initialState,
  type Candle,
  type ChartState,
  type Packet,
} from "../src/types";

function harness(now = () => 1000) {
  const sockets: MarketSocket[] = [],
    later = new Map<number, () => void>(),
    every = new Map<number, () => void>();
  let id = 0;
  let resolveFetch: (response: Response) => void = () => {};
  let rejectFetch: (error:Error) => void = () => {};
  const historyStates:string[]=[];
  const reads: { url: string; signal?: AbortSignal | null }[] = [];
  const environment: MarketSessionEnvironment = {
    origin: "ws://localhost",
    now,
    socket: () => {
      const socket: MarketSocket = {
        onmessage: null,
        onclose: null,
        onerror: null,
        close() {
          socket.onclose?.();
        },
      };
      sockets.push(socket);
      return socket;
    },
    fetch: async (input, init) => {
      reads.push({ url: String(input), signal: init?.signal });
      return new Promise((resolve,reject) => {
        resolveFetch = resolve;
        rejectFetch = reject;
      });
    },
    later: (callback) => {
      const key = ++id;
      later.set(key, callback);
      return key as unknown as ReturnType<typeof setTimeout>;
    },
    cancelLater: (key) => {
      later.delete(key as unknown as number);
    },
    every: (callback) => {
      const key = ++id;
      every.set(key, callback);
      return key as unknown as ReturnType<typeof setInterval>;
    },
    cancelEvery: (key) => {
      every.delete(key as unknown as number);
    },
  };
  const state = { current: initialState("BTCUSDT", "15m") },
    published: ChartState[] = [],
    busy: boolean[] = [],
    errors: boolean[] = [],
    added: number[] = [],
    paints: boolean[] = [];
  let failPaint = false;
  const start = (symbol = "BTCUSDT", preview?:Pick<ChartState,'candles'|'market'|'quality'>) =>
    startChartMarketSession(
      {
        symbol,
        preview,
        interval: "15m",
        state,
        publish: (value) => published.push(value),
        paint: (_, full) => {
          paints.push(full);
          if (failPaint) throw Error("paint");
        },
        beforeHistory: () => (count) => added.push(count),
        historyBusy: (value) => busy.push(value),
        historyError: (value) => errors.push(value),
        hasMore: () => {},
        historyState: (value) => historyStates.push(value),
      },
      environment,
    );
  const sample = fixture.cases[0];
  const packet: Packet = {
    type: "snapshot",
    stream_epoch: sample.proof.stream_epoch,
    data_proof: sample.proof as Packet["data_proof"],
    source: "binance_usdm_demo_trade_price",
    environment: "demo_public",
    product: "USD-M",
    price_type: "LAST_PRICE",
    symbol: "BTCUSDT",
    interval: "15m",
    generation: sample.proof.generation,
    sequence: 1,
    status: "LIVE",
    received_at: 1000,
    candles: structuredClone(sample.rows) as Candle[],
    market: sample.market as Packet["market"],
    quality: sample.quality,
  };
  const send = (value: unknown, index = sockets.length - 1) =>
    sockets[index].onmessage?.({ data: JSON.stringify(value) });
  return {
    start,
    state,
    sockets,
    later,
    every,
    reads,
    published,
    busy,
    errors,
    added,
    paints,
    packet,
    send,
    resolve: (value: unknown) =>
      resolveFetch(new Response(JSON.stringify(value))),
    reject:()=>rejectFetch(Error('network failed')),
    historyStates,
    fail: () => {
      failPaint = true;
    },
    repair: () => {
      failPaint = false;
    },
  };
}

test("session accepts proven snapshots, does not repaint healthy heartbeats, and retires stale socket callbacks", () => {
  const h = harness(),
    session = h.start();
  h.send(h.packet);
  assert.equal(h.state.current.sequence, 1);
  assert.deepEqual(h.paints, [true]);
  h.send({ ...h.packet, type: "update", candles: undefined });
  assert.deepEqual(h.paints, [true]);
  const old = h.sockets[0];
  old.close();
  assert.equal(h.later.size, 1);
  const reconnect = [...h.later.values()][0];
  h.later.clear();
  reconnect();
  const before = h.state.current;
  old.onmessage?.({ data: JSON.stringify({ ...h.packet, sequence: 9 }) });
  assert.equal(h.state.current, before);
  old.onclose?.();
  assert.equal(h.later.size, 0);
  h.send(h.packet);
  assert.equal(h.state.current.snapshot_required, false);
  session.close();
  assert.equal(h.every.size, 0);
  assert.equal(h.later.size, 0);
  const count = h.published.length;
  h.send(h.packet);
  assert.equal(h.published.length, count);
});

test('cold empty preparing snapshot keeps its socket until the proven candles arrive',()=>{
 const h=harness(),session=h.start();
 h.send({...h.packet,status:'CONNECTING',generation:0,sequence:0,candles:[],data_proof:null,market:null,received_at:null});
 assert.equal(h.later.size,0);assert.equal(h.sockets.length,1);assert.equal(h.state.current.stream_epoch,undefined);
 assert.equal(h.state.current.status,'CONNECTING');assert.deepEqual(h.paints,[]);
 h.send(h.packet);assert.equal(h.state.current.status,'LIVE');assert.equal(h.state.current.candles.length,h.packet.candles!.length);
 assert.equal(h.later.size,0);session.close();
});

test('cached preview paints immediately but cannot restore proof or live eligibility',async()=>{
 const h=harness(),preview={candles:h.packet.candles!,market:h.packet.market!,quality:'OK'};
 const session=h.start('BTCUSDT',preview);
 assert.deepEqual(h.paints,[true]);assert.equal(h.state.current.candles,preview.candles);
 assert.equal(h.state.current.status,'CONNECTING');assert.equal(h.state.current.stream_epoch,undefined);
 assert.equal(h.state.current.data_proof,undefined);assert.equal(h.state.current.timing,undefined);
 await session.loadOlder();assert.equal(h.reads.length,0);
 h.send({...h.packet,type:'update',candles:undefined});
 assert.equal(h.state.current.status,'CONNECTING');assert.equal(h.state.current.stream_epoch,undefined);
 h.send(h.packet);assert.equal(h.state.current.status,'LIVE');assert.ok(h.state.current.data_proof);
 session.close();
});

test("late history after a symbol switch cannot mutate state or clear the new session busy flag", async () => {
  const h = harness(),
    first = h.start();
  h.send(h.packet);
  const pending = first.loadOlder();
  assert.equal(h.reads.length, 1);
  assert.equal(h.busy.at(-1), true);
  first.close();
  assert.equal(h.reads[0].signal?.aborted, true);
  const second = h.start("ETHUSDT"),
    current = h.state.current,
    count = h.busy.length;
  h.resolve({ ...h.packet, candles: h.packet.candles, has_more: true });
  await pending;
  assert.equal(h.state.current, current);
  assert.equal(h.busy.length, count);
  assert.deepEqual(h.added, []);
  second.close();
});

test("history load deduplicates requests and preserves live candles", async () => {
  const h = harness(),
    session = h.start();
  h.send(h.packet);
  const old = h.state.current.candles[0],
    older = {
      ...old,
      time: old.time - 900,
      close_time: old.close_time - 900000,
    };
  const request = session.loadOlder();
  const duplicate = session.loadOlder();
  assert.equal(duplicate, request);
  assert.equal(h.reads.length, 1);
  h.resolve({
    ...h.packet,
    candles: [older],
    has_more: true,
  });
  await Promise.all([request, duplicate]);
  assert.equal(h.state.current.candles[0].time, older.time);
  assert.deepEqual(h.state.current.candles[1], old);
  assert.deepEqual(h.added, [1]);
  assert.equal(h.busy.at(-1), false);
  session.close();
});

test("wrong history identity is rejected and failed painting remains in recovery", async () => {
  const h = harness(),
    session = h.start();
  h.send(h.packet);
  let request = session.loadOlder();
  h.resolve({ ...h.packet, symbol: "ETHUSDT" });
  await request;
  assert.equal(h.errors.at(-1), true);
  const before = h.state.current.candles;
  h.fail();
  request = session.loadOlder();
  h.resolve({ ...h.packet, candles: [{...before[0],time:before[0].time-900,close_time:before[0].close_time-900000}], has_more: true });
  await request;
  assert.equal(h.state.current.status, "RENDER_ERROR");
  assert.deepEqual(h.added, []);
  h.repair();
  h.send({ ...h.packet, type: "update", candles: undefined });
  assert.equal(h.state.current.status, "LIVE");
  assert.equal(h.paints.at(-1), true);
  assert.deepEqual(h.state.current.candles, before);
  session.close();
});

test("invalid advancing proof forces a fresh snapshot and cleanup cancels reconnect", () => {
  const h = harness(),
    session = h.start();
  h.send(h.packet);
  const bad = structuredClone(h.packet);
  bad.sequence++;
  bad.data_proof!.snapshot_hash = "0".repeat(64);
  h.send(bad);
  assert.equal(h.state.current.snapshot_required, true);
  assert.equal(h.later.size, 1);
  session.close();
  assert.equal(h.later.size, 0);
  assert.equal(h.every.size, 0);
});

test("exhausted history also blocks viewport requests until a new session", async () => {
  for (const emptyPage of [false, true]) {
    const h = harness(), session = h.start();
    h.send(h.packet);
    const old = h.state.current.candles[0];
    const pending = session.loadOlder();
    h.resolve({ ...h.packet, candles: emptyPage ? [] : [{ ...old, time: old.time - 900, close_time: old.close_time - 900000 }], has_more: false });
    await pending;
    const redundant = session.loadOlder();
    assert.equal(h.reads.length, 1);
    await redundant;
    await session.loadOlder();
    assert.equal(h.reads.length, 1);
    session.close();
    const next = h.start();
    h.send(h.packet);
    const nextPage = next.loadOlder();
    assert.equal(h.reads.length, 2);
    h.resolve({ ...h.packet, candles: [], has_more: false });
    await nextPage;
    next.close();
  }
});

test("failed history remains retryable and successful nonterminal pages continue", async () => {
  const h = harness(), session = h.start();
  h.send(h.packet);
  let pending = session.loadOlder();
  h.resolve({ ...h.packet, symbol: "ETHUSDT" });
  await pending;
  assert.equal(h.errors.at(-1), true);
  pending = session.loadOlder();
  const old = h.state.current.candles[0];
  h.resolve({ ...h.packet, candles: [{ ...old, time: old.time - 900, close_time: old.close_time - 900000 }], has_more: true });
  await pending;
  assert.equal(h.errors.at(-1), false);
  pending = session.loadOlder();
  assert.equal(h.reads.length, 3);
  h.resolve({ ...h.packet, candles: [], has_more: false });
  await pending;
  session.close();
});


test("history GAP is exposed independently of the verified live window", async () => {
 const {marketReadiness}=await import('../src/chartReadiness');
 const h=harness(),session=h.start();h.send(h.packet);
 const first=h.state.current.candles[0];const request=session.loadOlder();
 h.resolve({...h.packet,candles:[{...first,time:first.time-1800,close_time:first.close_time-1800000}],quality:{state:'GAP',missing_bars:1},has_more:true});
 await request;
 assert.equal(h.state.current.data_proof?.state,'VERIFIED');
 const ready=marketReadiness(h.state.current,'BTCUSDT','15m');
 assert.equal(ready.status,'GAP');assert.equal(ready.fresh,false);assert.equal(ready.history.missing_bars,1);
 session.close();
});
test("failed historical paint rolls back added candles until an explicit successful retry", async()=>{
 const h=harness(),session=h.start();h.send(h.packet);const before=h.state.current.candles,first=before[0];
 const page={...h.packet,candles:[{...first,time:first.time-900,close_time:first.close_time-900000}],has_more:true};
 h.fail();let request=session.loadOlder();h.resolve(page);await request;
 assert.equal(h.state.current.candles,before);assert.deepEqual(h.added,[]);
 h.repair();h.send({...h.packet,type:'update',candles:undefined});
 assert.equal(h.state.current.candles,before);assert.equal(h.state.current.status,'LIVE');
 request=session.loadOlder();h.resolve(page);await request;
 assert.equal(h.state.current.candles[0].time,first.time-900);assert.deepEqual(h.added,[1]);session.close();
});
test("history rejects malformed UTC grid without silently accepting a partial page",async()=>{
 const h=harness(),session=h.start();h.send(h.packet);const before=h.state.current.candles,first=before[0];
 const request=session.loadOlder();h.resolve({...h.packet,candles:[{...first,time:first.time-901}],has_more:true});await request;
 assert.equal(h.state.current.candles,before);assert.equal(h.errors.at(-1),true);session.close();
});


test("history outcomes distinguish provider boundary, cap, network, invalid data and render failure",async()=>{
 for(const expected of ['EXHAUSTED','LIMIT','NETWORK_ERROR','INVALID_DATA','RENDER_ERROR']){
  const h=harness(),session=h.start();h.send(h.packet);
  if(expected==='LIMIT'){
   const first=h.state.current.candles[0];
   h.state.current={...h.state.current,candles:Array.from({length:4000},(_,i)=>({...first,time:first.time+i*900,close_time:first.close_time+i*900000}))};
  }
  if(expected==='RENDER_ERROR')h.fail();
  const pending=session.loadOlder();
  if(expected==='NETWORK_ERROR')h.reject();
  else if(expected==='INVALID_DATA')h.resolve({...h.packet,symbol:'ETHUSDT'});
  else if(expected!=='LIMIT')h.resolve({...h.packet,candles:[],has_more:false});
  assert.equal(await pending,expected);assert.equal(h.historyStates.at(-1),expected);
  if(expected==='LIMIT')assert.equal(h.reads.length,0);
  session.close();
 }
});

test('successful history retry clears render error without needing a heartbeat', async()=>{
 const h=harness(),session=h.start();h.send(h.packet);
 const first=h.state.current.candles[0];
 const page={...h.packet,candles:[{...first,time:first.time-900,close_time:first.close_time-900000}],has_more:true};
 h.fail();let pending=session.loadOlder();h.resolve(page);
 assert.equal(await pending,'RENDER_ERROR');assert.equal(h.state.current.status,'RENDER_ERROR');
 h.repair();pending=session.loadOlder();h.resolve(page);
 assert.equal(await pending,'READY');assert.equal(h.state.current.status,'LIVE');
 assert.equal(h.errors.at(-1),false);assert.deepEqual(h.added,[1]);session.close();
});

test('successful history retry preserves stale or disconnected transport status',async()=>{
 for(const status of ['STALE','RECONNECTING']){
  const h=harness(),session=h.start();h.send({...h.packet,status});
  const first=h.state.current.candles[0];
  const page={...h.packet,candles:[{...first,time:first.time-900,close_time:first.close_time-900000}],has_more:true};
  h.fail();let pending=session.loadOlder();h.resolve(page);await pending;
  h.repair();pending=session.loadOlder();h.resolve(page);await pending;
  assert.equal(h.state.current.status,status);session.close();
 }
});

test('history paint recovery rechecks data age instead of reviving an old LIVE packet',async()=>{
 let now=1000;const h=harness(()=>now),session=h.start();h.send(h.packet);
 const first=h.state.current.candles[0];
 const page={...h.packet,candles:[{...first,time:first.time-900,close_time:first.close_time-900000}],has_more:true};
 h.fail();let pending=session.loadOlder();h.resolve(page);await pending;
 now=20000;h.repair();pending=session.loadOlder();h.resolve(page);
 assert.equal(await pending,'READY');assert.equal(h.state.current.status,'STALE');session.close();
});

test('out-of-bound and nonprogress history pages are invalid and explicitly retryable',async()=>{
 for(const kind of ['duplicate','future','empty-more']){
  const h=harness(),session=h.start();h.send(h.packet);
  const before=h.state.current.candles,first=before[0],tail=before.at(-1)!;
  let pending=session.loadOlder();
  h.resolve({...h.packet,candles:kind==='empty-more'?[]:[kind==='duplicate'?first:{...tail,time:tail.time+900,close_time:tail.close_time+900000}],has_more:true});
  assert.equal(await pending,'INVALID_DATA');assert.equal(h.state.current.candles,before);
  assert.equal(h.errors.at(-1),true);assert.deepEqual(h.added,[]);
  pending=session.loadOlder();assert.equal(h.reads.length,2);
  h.resolve({...h.packet,candles:[{...first,time:first.time-900,close_time:first.close_time-900000}],has_more:true});
  assert.equal(await pending,'READY');assert.equal(h.errors.at(-1),false);session.close();
 }
});

test('clock jump schedules one reconnect and only a proven snapshot restores eligibility',()=>{
 const originalNow=Date.now,descriptor=Object.getOwnPropertyDescriptor(globalThis,'performance');
 let wall=1000,mono=0;
 Date.now=()=>wall;Object.defineProperty(globalThis,'performance',{configurable:true,value:{now:()=>mono}});
 const h=harness(()=>wall),session=h.start();
 const packet={...h.packet,timing:{schema:'chart-time-proof/1',policy:{schema:'chart-time-policy/1'},state:'FRESH',reason:null,data_age_ms:100,upstream_age_upper_ms:200,uncertainty_ms:100,upstream_event_time:h.packet.candles!.at(-1)!.time*1000+1000}};
 try{
  h.send(packet);assert.equal(h.state.current.status,'LIVE');
  mono=500;wall=11500;for(const fn of h.every.values())fn();
  assert.equal(h.state.current.consumer_clock_untrusted,true);
  assert.equal(h.state.current.snapshot_required,true);assert.equal(h.later.size,1);
  for(let i=0;i<3;i++){h.send({...packet,type:'update',candles:undefined},0);for(const fn of h.every.values())fn();}
  assert.equal(h.later.size,1);assert.equal(h.sockets.length,1);
  const reconnect=[...h.later.values()][0];h.later.clear();reconnect();
  h.send({...packet,type:'update',candles:undefined});assert.equal(h.state.current.snapshot_required,true);
  h.send(packet);assert.equal(h.state.current.consumer_clock_untrusted,false);
  assert.equal(h.state.current.snapshot_required,false);assert.equal(h.state.current.status,'LIVE');
 }finally{session.close();Date.now=originalNow;if(descriptor)Object.defineProperty(globalThis,'performance',descriptor);}
});
