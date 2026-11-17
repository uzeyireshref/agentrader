import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {act,useState} from 'react';
import BotTerminal from '../src/BotTerminal.tsx';
import {initialBotDraft,type BotDraft} from '../src/botPrototype.ts';
const dom=new JSDOM('<html><body></body></html>',{url:'http://localhost/'});
Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,HTMLDialogElement:dom.window.HTMLDialogElement,localStorage:dom.window.localStorage,IS_REACT_ACT_ENVIRONMENT:true});
Object.assign(dom.window.HTMLDialogElement.prototype,{showModal(this:HTMLDialogElement){this.setAttribute('open','');},close(this:HTMLDialogElement){this.removeAttribute('open');}});
const {createRoot}=await import('react-dom/client');
test('complete bot ticket invalidates old approval and persists local feedback without network mutations',async()=>{
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);let current:BotDraft=initialBotDraft;let requests=0;const previous=globalThis.fetch;
 globalThis.fetch=async()=>{requests++;throw Error('Prototype must not use network');};
 function Harness(){const [draft,setDraft]=useState(initialBotDraft);current=draft;return <BotTerminal draft={draft} onDraft={setDraft} onChart={()=>{}}/>;}
 const button=(text:string)=>{const found=[...host.querySelectorAll('button')].find(b=>b.textContent===text||b.getAttribute('aria-label')===text);assert.ok(found,'Missing '+text);return found;};
 const field=(text:string)=>{const label=[...host.querySelectorAll('label')].find(l=>l.firstChild?.textContent===text);assert.ok(label,'Missing '+text);return label.querySelector('input,select,textarea')!;};
 const set=async(element:Element,value:string)=>{await act(async()=>{const prototype=element instanceof dom.window.HTMLSelectElement?dom.window.HTMLSelectElement.prototype:element instanceof dom.window.HTMLTextAreaElement?dom.window.HTMLTextAreaElement.prototype:dom.window.HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(prototype,'value')!.set!.call(element,value);element.dispatchEvent(new dom.window.Event(element instanceof dom.window.HTMLSelectElement?'change':'input',{bubbles:true}));});};
 try{
  await act(async()=>root.render(<Harness/>));await act(async()=>button('İşlemi önizle').click());assert.ok(host.querySelector('[aria-label="İşlem önizlemesi"]'));
  await set(field('Emir türü'),'MARKET');assert.equal(current.orderType,'MARKET');assert.equal(host.querySelector('[aria-label="İşlem önizlemesi"]'),null);
  await act(async()=>button('İşlemi önizle').click());assert.match(host.textContent!,/dolum garantisi değildir/);
  await act(async()=>button('Prototip adımını onayla').click());assert.match(localStorage.getItem('agentrader.bot-prototype.records.v1')!,/SINGLE/);
  await act(async()=>button('Geri bildirim').click());assert.equal(host.querySelector('.bot-ticket'),null);assert.equal(host.querySelector('.bot-metrics'),null);await set(field('Açıklama'),'Mobil ekranda test geri bildirimi');
  await act(async()=>button('Yerel geri bildirim kaydet').click());assert.match(localStorage.getItem('agentrader.bot-prototype.records.v1')!,/Mobil ekranda/);
  await act(async()=>button('Pozisyonlar').click());assert.equal(host.querySelector('.bot-ticket'),null);await act(async()=>button('Azalt').click());assert.ok(host.querySelector('dialog[open]'));await act(async()=>button('Pozisyon formunu kapat').click());
  await act(async()=>button('Yeni işlem').click());assert.ok(host.querySelector('.bot-ticket'));assert.equal(host.querySelector('.bot-metrics'),null);assert.equal(host.querySelector('details.bot-account-settings')?.hasAttribute('open'),false);
 }finally{await act(async()=>root.unmount());host.remove();globalThis.fetch=previous;}
 assert.equal(requests,0);
});
