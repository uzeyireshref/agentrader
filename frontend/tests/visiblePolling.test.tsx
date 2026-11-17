import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {act} from 'react';
import {createRoot} from 'react-dom/client';
import {useVisiblePolling} from '../src/useVisiblePolling';
const dom=new JSDOM('<html><body></body></html>');
Object.assign(globalThis,{window:dom.window,document:dom.window.document,IS_REACT_ACT_ENVIRONMENT:true});
test('polling does not overlap reads, pauses while hidden and refreshes on visibility',async(t)=>{
 let visible='visible',calls=0,release:(()=>void)|undefined;
 Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>visible});
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
 function Component(){useVisiblePolling(async()=>{calls++;if(calls===1)await new Promise<void>(resolve=>{release=resolve;});},()=>assert.fail('unexpected failure'));return null;}
 try{
  t.mock.timers.enable({apis:['setInterval']});await act(async()=>root.render(<Component/>));assert.equal(calls,1);
  await act(async()=>{t.mock.timers.tick(20000);});assert.equal(calls,1);
  await act(async()=>release!());await act(async()=>{t.mock.timers.tick(5000);});assert.equal(calls,2);
  visible='hidden';await act(async()=>{document.dispatchEvent(new dom.window.Event('visibilitychange'));t.mock.timers.tick(10000);});assert.equal(calls,2);
  visible='visible';await act(async()=>{document.dispatchEvent(new dom.window.Event('visibilitychange'));});assert.equal(calls,3);
  await act(async()=>root.unmount());t.mock.timers.tick(10000);assert.equal(calls,3);
 }finally{t.mock.timers.reset();host.remove();}
});
