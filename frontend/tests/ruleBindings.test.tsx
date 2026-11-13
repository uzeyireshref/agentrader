import {test} from 'node:test';
import assert from 'node:assert/strict';
import {act} from 'react';
import {JSDOM} from 'jsdom';
import RuleBindings from '../src/RuleBindings';
import {defaultFullIndicators} from '../src/indicatorConfig';
const dom=new JSDOM('<body></body>',{url:'http://localhost'});
Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true});
dom.window.HTMLDialogElement.prototype.showModal=function(){};
dom.window.HTMLDialogElement.prototype.close=function(){};
const {createRoot}=await import('react-dom/client');
test('failed evidence refresh disables creation after a previously valid catalog',async()=>{
 const original=globalThis.fetch;let failed=false,mutations=0;
 const catalog={schema:'chart-binding-catalog/1',state:'VERIFIED_TRACEABILITY',reason:null,evaluation_state:'NOT_IMPLEMENTED_P5',order_authority:false,targets:{'indicator:EMA':{numeric_basis:'DISPLAY_ONLY',artifacts:[{path:'fixture',sha256:'a'.repeat(64)}],queries:[{operation:'valueAt',output:'value',output_type:'DISPLAY_NUMBER',rules:['observe']}]}}};
 globalThis.fetch=async(input,init)=>{if(init?.method)mutations++;return new Response(JSON.stringify(String(input).includes('binding-catalog')?catalog:{bindings:[]}),{status:failed?503:200});};
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
 try{
  await act(async()=>{root.render(<RuleBindings symbol="BTCUSDT" interval="15m" scale="LINEAR" rows={[{time:1800000000},{time:1800000900}] as any} drawings={[]} indicators={defaultFullIndicators()} selected={null} disabled={false} onRefreshTargets={async()=>{}} onClose={()=>{}}/>);});
  const save=host.querySelector('button[type="submit"]') as HTMLButtonElement;
  assert.equal(save.disabled,false);
  failed=true;await act(async()=>{([...host.querySelectorAll('button')].find(b=>b.textContent==='Bağları yenile') as HTMLButtonElement).click();});
  assert.equal(save.disabled,true);assert.match(host.querySelector('[role="alert"]')!.textContent!,/yüklenemedi/);assert.equal(mutations,0);
 }finally{await act(async()=>root.unmount());host.remove();globalThis.fetch=original;}
});
