import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import type {Candle} from '../src/types';
import {candleCoordinate,candleLogicalAt} from '../src/chartTime';
import {drawingTimeAt} from '../src/drawingTime';
import {captureTimeViewport,restoreTimeViewport,changeViewportInterval,followLatestViewport} from '../src/chartViewport';
const dom=new JSDOM('<!doctype html><html><body></body></html>',{pretendToBeVisual:true});
Object.assign(globalThis,{window:dom.window,document:dom.window.document});
dom.window.requestAnimationFrame=()=>1;dom.window.cancelAnimationFrame=()=>{};
dom.window.matchMedia=(()=>({matches:false,addListener(){},removeListener(){},addEventListener(){},removeEventListener(){}})) as never;
dom.window.HTMLCanvasElement.prototype.getContext=function(){return new Proxy({canvas:this,measureText:(s:string)=>({width:s.length*7})},{get:(o,k)=>k in o?o[k as keyof typeof o]:()=>{}}) as never;};
const {createChart,CandlestickSeries,LineSeries}=await import('lightweight-charts');
const candle=(time:number):Candle=>({time,close_time:time*1000+3599999,open:100,high:110,low:90,close:105,volume:10,quote_volume:1050,closed:true});
const rows=Array.from({length:100},(_,i)=>candle(1800000000+i*3600));
function fixture(){const host=document.createElement('div');document.body.append(host);const chart=createChart(host,{width:900,height:500,layout:{attributionLogo:false}}),price=chart.addSeries(CandlestickSeries),line=chart.addSeries(LineSeries);price.setData(rows as never);chart.timeScale().setVisibleLogicalRange({from:0,to:106});chart.takeScreenshot();return {chart,price,line,flush(){chart.takeScreenshot();},close(){chart.remove();host.remove();}};}
for(const offset of [-30,30])test('real engine: BB offset '+offset+' cannot change a persisted candle anchor',()=>{const f=fixture();try{f.line.setData(rows.slice(19).map(r=>({time:r.time+offset*3600,value:100})) as never);f.flush();const scale=f.chart.timeScale();for(const i of [0,1,35,99]){const x=scale.timeToCoordinate(rows[i].time as never)!;assert.equal(candleCoordinate(rows,i,scale),x);const index=candleLogicalAt(rows,x,scale)!;assert.ok(Math.abs(index-i)<1e-8);assert.equal(drawingTimeAt(rows,index,'1h'),rows[i].time);}for(const i of [-5,110,25.5]){const x=candleCoordinate(rows,i,scale)!;assert.ok(Math.abs(candleLogicalAt(rows,x,scale)!-i)<1e-8);}}finally{f.close();}});
test('real engine: UTC viewport survives prepend and leading trim with extra indicator times',()=>{const f=fixture();try{const scale=f.chart.timeScale();f.line.setData(rows.slice(19).map(r=>({time:r.time-30*3600,value:100})) as never);scale.setVisibleLogicalRange({from:30.35,to:80.73});f.flush();const saved=captureTimeViewport(rows,3600,scale)!;const older=[...Array.from({length:20},(_,i)=>candle(rows[0].time-(20-i)*3600)),...rows];f.price.setData(older as never);restoreTimeViewport(older,3600,scale,saved);f.flush();let result=captureTimeViewport(older,3600,scale)!;assert.ok(Math.abs(result.from-saved.from)<.001);assert.ok(Math.abs(result.to-saved.to)<.001);const trimmed=older.slice(10);f.price.setData(trimmed as never);restoreTimeViewport(trimmed,3600,scale,saved);f.flush();result=captureTimeViewport(trimmed,3600,scale)!;assert.ok(Math.abs(result.from-saved.from)<.001);assert.ok(Math.abs(result.to-saved.to)<.001);}finally{f.close();}});
test('periyot transition preserves UTC middle and candle density rather than jumping to latest',()=>{const view={from:1800000000,to:1800000000+100*900,bars:100};const hour=changeViewportInterval(view,3600);assert.equal((hour.from+hour.to)/2,(view.from+view.to)/2);assert.equal(hour.bars,100);assert.equal(hour.to-hour.from,360000);const back=changeViewportInterval(hour,900);assert.deepEqual(back,view);});

test('live-follow interval transition preserves candle count and candle-tail padding',()=>{
 const tail=1803596400,view={from:tail-108*3600,to:tail+7*3600,bars:115};
 const nextTail=tail+2700,next=followLatestViewport(view,tail,3600,nextTail,900);
 assert.equal(next.bars,115);assert.equal((next.to-nextTail)/900,7);
 assert.ok(next.from<nextTail&&next.to>nextTail);
 const appended=followLatestViewport(next,nextTail,900,nextTail+900,900);
 assert.equal(appended.from-next.from,900);assert.equal(appended.to-next.to,900);
});
test('real engine: old hourly indicator dates cannot corrupt drawing conversion on daily candles',()=>{const f=fixture();try{f.line.setData(rows.slice(19).map(r=>({time:r.time,value:100})) as never);const daily=Array.from({length:100},(_,i)=>({...candle(1800000000-95*86400+i*86400),close_time:(1800000000-95*86400+(i+1)*86400)*1000-1}));f.price.setData(daily as never);f.flush();const scale=f.chart.timeScale();for(const i of [0,90,95,99]){const x=scale.timeToCoordinate(daily[i].time as never)!;assert.ok(Math.abs(candleLogicalAt(daily,x,scale)!-i)<1e-8);assert.equal(candleCoordinate(daily,i,scale),x);}}finally{f.close();}});
