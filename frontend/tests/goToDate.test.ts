import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseUtcDate,intervalOpen} from '../src/goToDate';
test('UTC date parser rejects calendar rollover, missing time and offset injection',()=>{
 for(const s of ['2026-02-30T12:00','2026-13-01T00:00','2026-11-17','2026-11-17T25:00','2026-11-17T12:00+04:00','bad'])assert.equal(parseUtcDate(s),null,s);
 assert.equal(parseUtcDate('2026-11-17T12:35'),Date.UTC(2026,10,17,12,35)/1000);
 assert.equal(parseUtcDate('2024-02-29T23:59'),Date.UTC(2024,1,29,23,59)/1000);
});
test('date navigation aligns intraday daily and Monday weekly candles in UTC',()=>{
 const time=Date.UTC(2026,10,17,12,35)/1000;
 assert.equal(intervalOpen(time,'15m'),Date.UTC(2026,10,17,12,30)/1000);
 assert.equal(intervalOpen(time,'1d'),Date.UTC(2026,10,17)/1000);
 assert.equal(intervalOpen(time,'1w'),Date.UTC(2026,10,16)/1000);
});
