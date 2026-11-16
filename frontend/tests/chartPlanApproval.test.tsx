import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';
import {act} from 'react';
import ChartPlanApproval,{validChartReview,validApprovalJob} from '../src/ChartPlanApproval';
import type {Preview} from '../src/SignalPreview';
const fixture=JSON.parse(readFileSync(new URL('./fixtures/chart-review.json',import.meta.url),'utf8'));
const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'http://127.0.0.1/'});
Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true});
const {createRoot}=await import('react-dom/client');

test('Python review hash and exact preview/execution mapping are independently verified',()=>{
 assert.equal(validChartReview(fixture.review,fixture.preview),true);
 for(const field of ['account_ref','plan_digest','preview_hash','review_hash']){
  const changed=structuredClone(fixture.review);changed[field]='b'.repeat(64);assert.equal(validChartReview(changed,fixture.preview),false);
 }
 const changed=structuredClone(fixture.review);changed.plan.stop='1';assert.equal(validChartReview(changed,fixture.preview),false);
});
test('approval outcomes from initial response and later polls require the same exact scope',()=>{
 const job={request_id:'consent',state:'APPROVED',expires_at:1060,result:{state:'AUTHORIZED',approval_until:1060,plan_digest:fixture.review.plan_digest,review_hash:fixture.review.review_hash,executed:false,order_requests:0},error_code:null};
 assert.equal(validApprovalJob(job,'consent',fixture.review),true);
 for(const changed of [{...job,request_id:'other'},{...job,result:null},{...job,result:{...job.result,plan_digest:'b'.repeat(64)}},{...job,result:{...job.result,executed:true}},{...job,result:{...job.result,approval_until:999999}}])assert.equal(validApprovalJob(changed,'consent',fixture.review),false);
});

async function mount(options:{enabled?:boolean;authenticated?:boolean;worker?:boolean;review?:unknown}={}){
 const nativeFetch=globalThis.fetch,nativeNow=Date.now;Date.now=()=>1000000;
 const calls:{url:string;method:string;body?:Record<string,unknown>}[]=[];
 globalThis.fetch=(async(input:unknown,init?:RequestInit)=>{
  const url=String(input),method=init?.method??'GET',body=init?.body?JSON.parse(String(init.body)):undefined;calls.push({url,method,body});
  let value:unknown;
  if(url==='/api/session')value={enabled:options.enabled??true,authenticated:options.authenticated??true};
  else if(url.startsWith('/api/chart-plans?'))value={review:options.review===undefined?fixture.review:options.review,worker_ready:options.worker??true};
  else if(url.endsWith('/approval-requests'))value={request_id:body.request_id,state:'PENDING',expires_at:1060,result:null,error_code:null};
  else throw Error('Unexpected endpoint: '+url);
  return {ok:true,json:async()=>structuredClone(value)} as Response;
 }) as typeof fetch;
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
 const render=async(preview:Preview=fixture.preview)=>{await act(async()=>root.render(<ChartPlanApproval preview={preview} disabled={false}/>));};
 await render();await act(async()=>{const details=host.querySelector('details')!;details.open=true;details.dispatchEvent(new dom.window.Event('toggle'));});
 const close=async()=>{await act(async()=>root.unmount());host.remove();globalThis.fetch=nativeFetch;Date.now=nativeNow;};
 return {host,calls,close,render};
}

test('disabled private API never exposes a financial action or requests plan data',async()=>{
 const f=await mount({enabled:false,authenticated:false});try{
  assert.match(f.host.textContent!,/Yerel onay oturumu kapalı/);
  assert.equal(f.calls.some(c=>c.url.startsWith('/api/chart-plans')),false);
  assert.equal(f.host.querySelector('input[type="checkbox"]'),null);
 }finally{await f.close();}
});
test('worker offline or changed review disables approval',async()=>{
 const f=await mount({worker:false});try{
  const fieldset=f.host.querySelector('fieldset')!;assert.equal(fieldset.disabled,true);
  assert.equal(f.calls.filter(c=>c.method==='POST').length,0);
 }finally{await f.close();}
 const changed=structuredClone(fixture.review);changed.account_ref='b'.repeat(64);
 const g=await mount({review:changed});try{assert.match(g.host.textContent!,/doğrulanamadı/);assert.equal(g.host.querySelector('fieldset'),null);}finally{await g.close();}
});
test('explicit checkbox sends only scoped approval, repeated clicks cannot create another request',async()=>{
 const f=await mount();try{
  const checkbox=f.host.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
  await act(async()=>checkbox.click());
  const button=Array.from(f.host.querySelectorAll('button')).find(b=>b.textContent==='Bu demo planına süreli onay ver')!;
  await act(async()=>{button.click();button.click();});
  const requests=f.calls.filter(c=>c.method==='POST');assert.equal(requests.length,1);
  assert.equal(requests[0].body?.plan_digest,fixture.review.plan_digest);assert.equal(requests[0].body?.account_ref,fixture.review.account_ref);
  assert.equal(requests[0].body?.review_hash,fixture.review.review_hash);assert.equal(requests[0].body?.ttl_seconds,60);
  assert.match(f.host.textContent!,/kuyruğa alındı; henüz onaylanmadı/);
  assert.equal(f.calls.some(c=>/orders|execute|commands/.test(c.url)),false);
 }finally{await f.close();}
});
test('missing local review explains the CLI handoff without inventing account checks',async()=>{
 const f=await mount({review:null});try{
  assert.match(f.host.textContent!,/review-preview main/);assert.equal(f.host.querySelector('fieldset'),null);
  assert.equal(f.calls.filter(c=>c.method==='POST').length,0);
 }finally{await f.close();}
});
