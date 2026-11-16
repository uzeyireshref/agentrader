import {test} from 'node:test';
import assert from 'node:assert/strict';
import {act} from 'react';
import {JSDOM} from 'jsdom';
import SignalPreview,{validPreview,sameInputs} from '../src/SignalPreview';
import fixture from './fixtures/signal-preview.json';
import type {Binding} from '../src/bindings';
const b=fixture.binding as unknown as Binding,v=fixture.preview;
const dom=new JSDOM('<body></body>',{url:'http://localhost'});
Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true});
const {createRoot}=await import('react-dom/client');
async function mount(){const host=document.createElement('div');document.body.append(host);const root=createRoot(host);await act(async()=>root.render(<SignalPreview binding={b} eventId={v.event_id} closedPrice="100" eventBindingRevision={b.revision} disabled={false}/>));await act(async()=>{const d=host.querySelector('details')!;d.open=true;d.dispatchEvent(new dom.window.Event('toggle'));});const fill=async(label:string,value:string)=>{const target=host.querySelector('[aria-label="'+label+'"]') as HTMLInputElement|HTMLSelectElement;await act(async()=>{Object.getOwnPropertyDescriptor(target.tagName==='SELECT'?dom.window.HTMLSelectElement.prototype:dom.window.HTMLInputElement.prototype,'value')!.set!.call(target,value);target.dispatchEvent(new dom.window.Event(target.tagName==='SELECT'?'change':'input',{bubbles:true}));});};return {host,root,fill,close:async()=>{await act(async()=>root.unmount());host.remove();}};}

test('Python preview fixture and whole-body hashes validate independently in TypeScript',()=>{assert.equal(validPreview(v,v.event_id,b),true);assert.equal(sameInputs(v.parameters,{...v.parameters,entry_price:'100.000'}),true);assert.equal(sameInputs(v.parameters,{...v.parameters,entry_price:'100.00000000000001'}),false);});

test('authority, wrong identity and altered estimates are rejected',()=>{for(const patch of [{order_authority:true},{execution_eligible:true},{approval_state:'AUTHORIZED'},{environment:'live_public'},{estimates:{...v.estimates,quantity:'100000'}}])assert.equal(validPreview({...v,...patch},v.event_id,b),false);assert.equal(validPreview(v,v.event_id,{...b,revision:99}),false);});

test('existing preview states account checks are missing and has no approval action',async()=>{const original=globalThis.fetch;globalThis.fetch=async()=>new Response(JSON.stringify(v));const f=await mount();try{assert.match(f.host.textContent!,/Yalnız önizleme/);assert.match(f.host.textContent!,/kontrol edilmedi/);assert.equal([...f.host.querySelectorAll('button')].some(x=>/onayla|emir gönder/i.test(x.textContent!)),false);}finally{await f.close();globalThis.fetch=original;}});

test('explicit inputs create only the preview command with optimistic version',async()=>{const original=globalThis.fetch;let sent:any;globalThis.fetch=async(_url,init)=>{if(init?.method){sent=JSON.parse(init.body as string);return new Response(JSON.stringify(v));}return new Response('{}',{status:404});};const f=await mount();try{await f.fill('Önizleme yönü','LONG');await f.fill('Önizleme stop','98');await f.fill('Önizleme hedef','104');await f.fill('Önizleme nominal','60');await f.fill('Önizleme kaldıraç','2');await act(async()=>[...f.host.querySelectorAll('button')].find(x=>x.textContent==='Plan önizlemesi oluştur')!.click());assert.equal(sent.expected_version,0);assert.deepEqual(sent.inputs,v.parameters);assert.match(f.host.textContent!,/Yalnız önizleme/);}finally{await f.close();globalThis.fetch=original;}});

test('failed read removes prior valid preview',async()=>{const original=globalThis.fetch;let fail=false;globalThis.fetch=async()=>new Response(JSON.stringify(v),{status:fail?503:200});const f=await mount();try{assert.match(f.host.textContent!,/Yalnız önizleme/);fail=true;await act(async()=>[...f.host.querySelectorAll('button')].find(x=>x.textContent==='Önizleme kaydını yenile')!.click());assert.equal(f.host.textContent!.includes('Yalnız önizleme'),false);assert.match(f.host.querySelector('[role="alert"]')!.textContent!,/doğrulanamadı/);}finally{await f.close();globalThis.fetch=original;}});
