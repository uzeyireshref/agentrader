import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {act} from 'react';
import BotPlanForm from '../src/BotPlanForm';
import {createLiveBotDraft} from '../src/botLiveDraft';
import {initialBotDraft} from '../src/botPrototype';
test('invalid preview and save focus the first field and never submit; corrected form can preview',async()=>{
 const dom=new JSDOM('<html><body><div id="root"></div></body></html>');
 Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,HTMLDetailsElement:dom.window.HTMLDetailsElement,IS_REACT_ACT_ENVIRONMENT:true,requestAnimationFrame:(fn:()=>void)=>setTimeout(fn,0)});
 const {createRoot}=await import('react-dom/client');const host=document.getElementById('root')!,root=createRoot(host);let submitted=0;
 const render=(draft:typeof initialBotDraft)=>root.render(<BotPlanForm draft={draft} onDraft={()=>{}} onPreview={()=>submitted++}/>);
 try{
  await act(async()=>render(createLiveBotDraft()));
  await act(async()=>{host.querySelector('form')!.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));await new Promise(r=>setTimeout(r,15));});
  assert.equal(submitted,0);assert.equal(host.querySelectorAll('[aria-invalid=true]').length,4);
  assert.equal(document.activeElement?.getAttribute('name'),'entry');
  await act(async()=>{[...host.querySelectorAll('button')].find(b=>b.textContent==='Plan taslağını kaydet')!.click();await new Promise(r=>setTimeout(r,15));});
  assert.equal(submitted,0);
  await act(async()=>render(initialBotDraft));
  assert.equal(host.querySelectorAll('[aria-invalid=true]').length,0);
  await act(async()=>host.querySelector('form')!.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true})));
  assert.equal(submitted,1);
 }finally{await act(async()=>root.unmount());dom.window.close();}
});
