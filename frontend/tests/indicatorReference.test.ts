import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {ema,rsi} from '../src/indicators.ts';
import type {Candle} from '../src/types.ts';
const fixture=JSON.parse(readFileSync(new URL('../../reports/indicator-reference-20261109.json',import.meta.url),'utf8')) as {cases:{name:string;times:number[];closes:string[];ema20:string[];ema50:string[];rsi14:string[]}[]};
for(const sample of fixture.cases)test('independent Decimal EMA/RSI reference: '+sample.name,()=>{const rows:Candle[]=sample.closes.map((close,i)=>{const value=Number(close);return {time:sample.times[i],open:value,high:value,low:value,close:value,volume:1,quote_volume:value,close_time:sample.times[i]*1000+899999,closed:i<sample.times.length-1};});for(const [actual,expected,offset]of [[ema(rows,20),sample.ema20,19],[ema(rows,50),sample.ema50,49],[rsi(rows),sample.rsi14,14]] as const){assert.equal(actual.length,expected.length);actual.forEach((p,i)=>{assert.equal(p.time,sample.times[i+offset]);assert.ok(Math.abs(p.value-Number(expected[i]))<=1e-8,'reference mismatch at '+i);});}});
