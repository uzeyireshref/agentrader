import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {act} from 'react';
import DrawingNotes from '../src/DrawingNotes';
import {drawingManagement,type Drawing} from '../src/drawings';
const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'http://127.0.0.1/'});
Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true});
const {createRoot}=await import('react-dom/client');
const item=():Drawing=>({drawing_id:'manual',revision:3,workspace_id:'main',deleted:false,updated_at:100,
 geometry:{kind:'horizontal',symbol:'BTCUSDT',price_source:'LAST_PRICE',anchors:[{time:1800000000,price:'100'}],label:'Manual'},
 origin:{schema:'drawing-origin/1',kind:'manual',source:'legacy',actor_id:'owner',bot_id:null,strategy_id:null,created_at:1},
 linked_note:{schema:'drawing-linked-note/1',drawing_id:'manual',workspace_id:'main',note_id:'note',revision:2,text:'Unicode 🧭\n<script>literal</script>',deleted:false,state:'ACTIVE',target_revision:3,updated_at:100}});
async function mount(){
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);let refreshed=0;
 const render=async(drawing=item())=>{await act(async()=>root.render(<DrawingNotes drawing={drawing} onRefresh={async()=>{refreshed++;}}/>));};
 await render();return {host,render,refreshed:()=>refreshed,close:async()=>{await act(async()=>root.unmount());host.remove();}};
}
test('long note displays Unicode as text, separate from geometry and origin',async()=>{
 const f=await mount();try{assert.equal(f.host.querySelector('textarea')!.value,item().linked_note!.text);assert.equal(f.host.querySelector('script'),null);assert.match(f.host.textContent!,/Manuel · eski kayıt/);}finally{await f.close();}
});
test('save carries note and target revisions; response loss retry reuses exact request',async()=>{
 const original=globalThis.fetch,f=await mount();const calls:Record<string,unknown>[]=[];let lost=true;
 globalThis.fetch=async(_url,init)=>{const body=JSON.parse(String(init?.body));calls.push(body);if(lost){lost=false;throw Error('response lost');}return new Response(JSON.stringify({...item().linked_note,revision:3,text:body.text}));};
 try{
  await act(async()=>f.host.querySelector('button')!.click());assert.match(f.host.textContent!,/yeniden dene/);assert.equal(f.host.querySelector('textarea')!.disabled,true);
  await act(async()=>f.host.querySelector('button')!.click());assert.deepEqual(calls[0],calls[1]);assert.equal(calls[0].expected_revision,2);assert.equal(calls[0].expected_drawing_revision,3);
  assert.equal(calls[0].text,item().linked_note!.text);assert.equal('origin'in calls[0],false);assert.equal(f.refreshed(),1);
 }finally{globalThis.fetch=original;await f.close();}
});
test('locked targets disable note mutation; refreshed drawing clears retry state',async()=>{
 const original=globalThis.fetch,f=await mount();globalThis.fetch=async()=>new Response('{}',{status:409});
 try{
  await act(async()=>f.host.querySelector('button')!.click());assert.equal(f.host.querySelector('textarea')!.disabled,true);
  const next={...item(),linked_note:{...item().linked_note!,revision:3,text:'fresh'}};await f.render(next);
  assert.equal(f.host.querySelector('textarea')!.value,'fresh');assert.equal(f.host.querySelector('textarea')!.disabled,false);
  await f.render({...next,management:{...drawingManagement(),locked:true}});assert.equal(f.host.querySelector('button')!.disabled,true);
 }finally{globalThis.fetch=original;await f.close();}
});
test('late response cannot overwrite a newer target or note revision',async()=>{
 const original=globalThis.fetch,f=await mount();let finish!:(r:Response)=>void;
 globalThis.fetch=()=>new Promise<Response>(resolve=>{finish=resolve;});
 try{
  await act(async()=>f.host.querySelector('button')!.click());
  await f.render({...item(),revision:4,linked_note:{...item().linked_note!,revision:3,text:'newer'}});
  await act(async()=>finish(new Response(JSON.stringify({...item().linked_note,revision:3}))));
  assert.equal(f.host.querySelector('textarea')!.value,'newer');assert.equal(f.refreshed(),0);
 }finally{globalThis.fetch=original;await f.close();}
});
