import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {act} from 'react';
import BotPlanAnalytics from '../src/BotPlanAnalytics';
import {initialBotDraft} from '../src/botPrototype';

test('automatic calculations follow edits, hide old values and stop while inactive or disconnected',async(t)=>{
 const dom=new JSDOM('<html><body><div id="root"></div></body></html>');
 Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true});
 const {createRoot}=await import('react-dom/client');const host=document.getElementById('root')!,root=createRoot(host);
 const original=globalThis.fetch,actions:string[]=[],readGate={current:true};let fail=false;
 const stamp=Date.now();
 globalThis.fetch=async(_input,init)=>{
  const request=JSON.parse(String(init?.body));actions.push(request.action);
  if(fail)throw Error('test connection lost');
  return new Response(JSON.stringify({job_id:'analytics-test',state:'SUCCEEDED',result:{state:'READY',symbol:'BTCUSDT',observed_at:Date.now()/1000,mark_time:Date.now(),mark_price:'80000',quantity:'0.001',initial_margin:'20',fee_reserve:'0.4',target_gross:'40',target_after_fee_reserve:'39.6',target_roe_percent:'198',stop_after_fee_reserve:'-20.4',reward_risk:'1.94',liquidation:[{direction:'LONG',estimated_liquidation:'70000'}],strategy:'SINGLE',execution_authorized:false,order_sent:false}}));
 };
 const render=(active=true,enabled=true,draft=initialBotDraft)=>root.render(<BotPlanAnalytics draft={draft} active={active} enabled={enabled} readGate={readGate}/>);
 const tick=async(ms:number)=>act(async()=>{t.mock.timers.tick(ms);});
 try{
  t.mock.timers.enable({apis:['Date','setInterval'],now:stamp});
  await act(async()=>render());await tick(2000);
  assert.equal(actions.length,0);readGate.current=false;await tick(1000);
  assert.deepEqual(actions,['ANALYZE_PLAN']);assert.match(host.textContent!,/39,6/);assert.match(host.textContent!,/70.000/);
  const changed={...initialBotDraft,entry:'90001'};await act(async()=>render(true,true,changed));
  assert.doesNotMatch(host.textContent!,/39,6/);await tick(2000);assert.equal(actions.length,2);
  await act(async()=>render(false,true,changed));await tick(30000);assert.equal(actions.length,2);
  await act(async()=>render(true,false,changed));assert.doesNotMatch(host.textContent!,/39,6/);await tick(30000);assert.equal(actions.length,2);
  await act(async()=>render(true,true,changed));await tick(2000);assert.equal(actions.length,3);
  fail=true;await tick(6000);assert.match(host.textContent!,/test connection lost/);assert.match(host.textContent!,/39,6/);
  await tick(10000);assert.match(host.textContent!,/39,6/);assert.match(host.textContent!,/güncel piyasa fiyatı değildir/);
  await tick(45000);assert.doesNotMatch(host.textContent!,/39,6/);
  assert.ok(actions.every(a=>a==='ANALYZE_PLAN'));
 }finally{await act(async()=>root.unmount());t.mock.timers.reset();globalThis.fetch=original;dom.window.close();}
});

test('a below-minimum grid scenario shows its numbers together with execution constraints',async(t)=>{
 const dom=new JSDOM('<html><body><div id="root"></div></body></html>');
 Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true});
 const {createRoot}=await import('react-dom/client');const root=createRoot(document.getElementById('root')!),original=globalThis.fetch;
 const {defaultGrid}=await import('../src/botPrototype');const actions:string[]=[];
 globalThis.fetch=async(_url,init)=>{
  actions.push(JSON.parse(String(init?.body)).action);
  return new Response(JSON.stringify({state:'SUCCEEDED',result:{state:'SCENARIO',symbol:'BTCUSDT',observed_at:Date.now()/1000,calculated_at:Date.now()/1000,mark_time:Date.now()-20000,mark_price:'63500',requested_budget:'10',initial_margin:'1',notional_ceiling:'10',fee_reserve:'.02',theoretical:true,theoretical_quantity:'.0000714',rounded_quantity:'0',strategy:'GRID',constraints:['ACCOUNT_SETTINGS_MISMATCH','GRID_BUDGET_TOO_SMALL'],execution_authorized:false,order_sent:false}}));
 };
 try{
  t.mock.timers.enable({apis:['Date','setInterval'],now:Date.now()});
  await act(async()=>root.render(<BotPlanAnalytics draft={{...initialBotDraft,kind:'GRID',grid:{...defaultGrid,budget:'10'}}} active enabled/>));
  await act(async()=>{t.mock.timers.tick(2000);});
  const metric=(label:string)=>[...document.querySelectorAll('dl>div')].find(e=>e.querySelector('dt')?.textContent?.startsWith(label))?.querySelector('dd')?.textContent;
  assert.match(document.body.textContent!,/güncel piyasa fiyatı değildir/);assert.equal(metric('Başlangıç teminatı'),'1');assert.equal(metric('Lot adımına göre miktar'),'0');
  assert.match(document.body.textContent!,/Bu değerler teoriktir/);assert.match(document.body.textContent!,/her hücrenin/);
  assert.deepEqual(actions,['ANALYZE_PLAN']);
 }finally{await act(async()=>root.unmount());globalThis.fetch=original;t.mock.timers.reset();dom.window.close();}
});
