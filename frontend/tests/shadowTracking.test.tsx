import {test} from 'node:test';
import assert from 'node:assert/strict';
import {act} from 'react';
import {JSDOM} from 'jsdom';
import ShadowTracking,{validShadowStatus} from '../src/ShadowTracking';
import fixture from './fixtures/binding-parity.json';
import type {Binding} from '../src/bindings';
import {marketSource,marketEnvironment} from '../src/marketEnvironment';
const context={source:marketSource,environment:marketEnvironment,product:'USD-M',price_type:'LAST_PRICE'};
const status=()=>({schema:'shadow-status/1',mode:'SHADOW_ONLY',...context,order_authority:false,run:null as any,events:[] as any[],worker:{state:'RUNNING',observed_at:1000}});
const binding=()=>{const b=structuredClone(fixture.bindings[0]) as unknown as Binding;b.definition.rule.kind='touch';return b;};
const dom=new JSDOM('<body></body>',{url:'http://localhost'});
Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true});
const {createRoot}=await import('react-dom/client');

test('shadow status rejects real identity, order authority and malformed events',()=>{
 assert.equal(validShadowStatus(status()),true);
 for(const patch of [{order_authority:true},{environment:'live_public'},{mode:'EXECUTE'},{events:[{}]}])assert.equal(validShadowStatus({...status(),...patch}),false);
 assert.equal(validShadowStatus({...status(),run:{state:'ARMED_FOR_ORDER'}}),false);
});

test('start is explicit, revision bound and creates no order command',async()=>{
 const original=globalThis.fetch,b=binding(),calls:any[]=[];
 globalThis.fetch=async(url,init)=>{calls.push({url,init});const v=status();if(init?.method)v.run={binding_revision:b.revision,definition_hash:b.definition_hash,state:'WAITING_DATA',reason:'INITIAL_SEED_REQUIRED',expires_at:2000,checkpoint:{}};return new Response(JSON.stringify(v));};
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
 try{
  await act(async()=>root.render(<ShadowTracking binding={b} disabled={false}/>));
  assert.equal(calls.filter(c=>c.init?.method).length,0);
  const start=[...host.querySelectorAll('button')].find(x=>x.textContent==='Gölge takibi başlat')!;
  await act(async()=>start.click());
  const command=calls.find(c=>c.init?.method);assert.equal(command.url.endsWith('/shadow'),true);
  assert.deepEqual(JSON.parse(command.init.body),{expected_revision:b.revision,definition_hash:b.definition_hash,action:'start',ttl_seconds:3600});
  assert.match(host.textContent!,/Veri bekleniyor/);assert.match(host.textContent!,/Emir göndermez/);
 }finally{await act(async()=>root.unmount());host.remove();globalThis.fetch=original;}
});

test('failed refresh removes prior ready state and disables starting',async()=>{
 const original=globalThis.fetch;let failed=false;
 globalThis.fetch=async()=>new Response(JSON.stringify(status()),{status:failed?503:200});
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
 try{
  await act(async()=>root.render(<ShadowTracking binding={binding()} disabled={false}/>));
  assert.equal((host.querySelector('button') as HTMLButtonElement).disabled,false);
  failed=true;await act(async()=>[...host.querySelectorAll('button')].find(x=>x.textContent==='Gölge durumu yenile')!.click());
  assert.match(host.querySelector('[role="alert"]')!.textContent!,/doğrulanamadı/);
  assert.equal(host.textContent!.includes('Henüz başlatılmadı'),false);
 }finally{await act(async()=>root.unmount());host.remove();globalThis.fetch=original;}
});

test('observe only or parent-disabled binding cannot start shadow subscription',async()=>{
 const original=globalThis.fetch;globalThis.fetch=async()=>new Response(JSON.stringify(status()));
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
 try{const b=binding();b.definition.rule.kind='observe';await act(async()=>root.render(<ShadowTracking binding={b} disabled={false}/>));assert.equal((host.querySelector('button') as HTMLButtonElement).disabled,true);await act(async()=>root.render(<ShadowTracking binding={binding()} disabled={true}/>));assert.equal((host.querySelector('button') as HTMLButtonElement).disabled,true);}finally{await act(async()=>root.unmount());host.remove();globalThis.fetch=original;}
});


test('late command response cannot replace a newer binding revision status',async()=>{
 const original=globalThis.fetch,b=binding();let finish:(r:Response)=>void=()=>{},current=1;
 const run=(revision:number,state:string)=>({binding_revision:revision,definition_hash:b.definition_hash,state,reason:null,expires_at:2000,checkpoint:{}});
 globalThis.fetch=async(_url,init)=>{if(init?.method)return new Promise<Response>(resolve=>{finish=resolve;});const v=status();if(current===2)v.run=run(2,'WATCHING');return new Response(JSON.stringify(v));};
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
 try{
  await act(async()=>root.render(<ShadowTracking binding={b} disabled={false}/>));
  await act(async()=>[...host.querySelectorAll('button')].find(x=>x.textContent==='Gölge takibi başlat')!.click());
  current=2;await act(async()=>root.render(<ShadowTracking binding={{...b,revision:2}} disabled={false}/>));
  const old=status();old.run=run(1,'LATCHED');await act(async()=>finish(new Response(JSON.stringify(old))));
  assert.match(host.textContent!,/Takip ediliyor/);assert.equal(host.textContent!.includes('Sinyal kaydedildi'),false);
 }finally{await act(async()=>root.unmount());host.remove();globalThis.fetch=original;}
});
