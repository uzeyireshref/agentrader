import {test,beforeEach} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {act} from 'react';
import BotLiveReview from '../src/BotLiveReview.tsx';
import BotConnected from '../src/BotConnected.tsx';
import {draftForServer,runBotJob,type BotReviewResult} from '../src/botApi.ts';
import {initialBotDraft} from '../src/botPrototype.ts';
import {liveCommand} from '../src/BotLiveCommands.tsx';
const dom=new JSDOM('<html><body></body></html>',{url:'http://localhost/'});
Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,HTMLDialogElement:dom.window.HTMLDialogElement,localStorage:dom.window.localStorage,IS_REACT_ACT_ENVIRONMENT:true});
Object.assign(dom.window.HTMLDialogElement.prototype,{showModal(this:HTMLDialogElement){this.setAttribute('open','');},close(this:HTMLDialogElement){this.removeAttribute('open');}});
const {createRoot}=await import('react-dom/client');
beforeEach(()=>{window.history.replaceState({},'', '/');});
test('live command forms preserve account scope, decimal text and normal/algo identity boundaries',()=>{
 assert.deepEqual(liveCommand('SET_POSITION_MODE','BTCUSDT',{enabled:'true'},null,[],[]),{operation:'SET_POSITION_MODE',scope:{affected_products:['USD-M','COIN-M']},parameters:{enabled:true}});
 assert.deepEqual(liveCommand('BATCH_CANCEL_ORDERS','BTCUSDT',{foreign:'false'},null,[],[{client_id:'normal-1',quantity:'',price:''}]).parameters,{targets:[{namespace:'NORMAL',client_id:'normal-1'}],include_foreign:false});
 assert.throws(()=>liveCommand('CLOSE_POSITION','BTCUSDT',{session:'unverified'},null,[],[]));
 const snapshot={sessions:[{session_id:'v2-id',symbol:'ETHUSDT'}]} as any;
 const c=liveCommand('INCREASE_POSITION','BTCUSDT',{session:'v2-id',quantity:'0.000000000000000001',floor:'3000',ceiling:'3001'},snapshot,[],[]);
 assert.deepEqual(c.scope,{symbol:'ETHUSDT'});assert.equal(c.parameters.quantity,'0.000000000000000001');assert.equal(c.parameters.risk_limits,undefined);
});
test('GTD conversion uses an explicit epoch and never mutates the editor',()=>{
 const draft={...initialBotDraft,options:{tif:'GTD' as const,stp:'' as const,expires:'2030-01-01T12:00',priceMatch:'' as const}};
 const result=draftForServer(draft);assert.equal((result.options as any).expires_ms,Date.parse(draft.options.expires));assert.equal((draft.options as any).expires_ms,undefined);
});
test('job submission never reposts after a lost response',async()=>{
 const previous=globalThis.fetch;let posts=0;globalThis.fetch=async()=>{posts++;throw Error('response lost');};
 try{await assert.rejects(runBotJob('CONFIRM',{}));assert.equal(posts,1);}finally{globalThis.fetch=previous;}
});
test('execution requires an explicit checkbox and an execution-enabled worker',async()=>{
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);let confirmed=0;
 const review:BotReviewResult={kind:'COMMAND',account_ref:'a'.repeat(64),expires_at:Date.now()/1000+60,review_digest:'b'.repeat(64),payload:{},data:{command_id:'cmd-test',state:'PREPARED',request:{operation:'CLOSE_POSITION',scope:{symbol:'BTCUSDT'},parameters:{session_id:'session'}}},risk_limits:{}};
 const render=(canExecute:boolean)=>root.render(<BotLiveReview review={review} pending={false} canExecute={canExecute} onClose={()=>{}} onConfirm={()=>confirmed++}/>);
 try{await act(async()=>render(true));const submit=()=>[...host.querySelectorAll('button')].find(b=>b.textContent==='Demo hesabında uygula')!;assert.ok(submit().disabled);await act(async()=>(host.querySelector('input[type=checkbox]') as HTMLInputElement).click());assert.equal(confirmed,0);assert.equal(submit().disabled,false);await act(async()=>render(false));assert.ok(submit().disabled);await act(async()=>submit().click());assert.equal(confirmed,0);await act(async()=>render(true));await act(async()=>submit().click());assert.equal(confirmed,1);}finally{await act(async()=>root.unmount());host.remove();}
});
test('unpaired live mode shows setup instead of invented balances or execution forms',async()=>{
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);const previous=globalThis.fetch;const calls:string[]=[];
 globalThis.fetch=async(input)=>{calls.push(String(input));return new Response(JSON.stringify({enabled:false,authenticated:false}),{status:200});};
 try{await act(async()=>root.render(<BotConnected draft={initialBotDraft} onDraft={()=>{}} onChart={()=>{}}/>));assert.match(host.textContent!,/AGENTRADER_WEB_TOKEN/);assert.equal(host.querySelector('.bot-ticket'),null);assert.equal(host.querySelector('table'),null);assert.deepEqual(calls,['/api/session']);}finally{await act(async()=>root.unmount());host.remove();globalThis.fetch=previous;}
});
test('chart trade panel keeps its draft when opening the full terminal and hides account navigation',async()=>{
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);const previous=globalThis.fetch;let opened=0;
 globalThis.fetch=async(input,init)=>new Response(JSON.stringify(String(input)==='/api/session'?{enabled:true,authenticated:true}:String(input)==='/api/bot/status'?{enabled:true,worker:'FRESH',execution_enabled:false}:init?.body?{job_id:'job-read',state:'SUCCEEDED',result:{observed_at:Date.now()/1000,account:{},positions:[],orders:[],algo_orders:[],sessions:[],plans:[],commands:[],account_ref:'a'.repeat(64)}}:{jobs:[]}),{status:200});
 const draft={...initialBotDraft,entry:'65432.10'};
 try{await act(async()=>root.render(<BotConnected compact draft={draft} onDraft={()=>{}} onChart={()=>{}} onTerminal={()=>opened++}/>));assert.ok(host.querySelector('.bot-live-nav')?.hasAttribute('hidden'));assert.ok(host.querySelector('.bot-content')?.hasAttribute('hidden'));assert.equal((host.querySelector('input[value="65432.10"]') as HTMLInputElement)?.value,draft.entry);const button=[...host.querySelectorAll('button')].find(b=>b.textContent==='Tam terminal')!;assert.ok(button);await act(async()=>button.click());assert.equal(opened,1);assert.equal((host.querySelector('input[value="65432.10"]') as HTMLInputElement)?.value,draft.entry);assert.match(host.textContent!,/Strateji ve sözleşme/);assert.match(host.textContent!,/Giriş ve risk/);}finally{await act(async()=>root.unmount());host.remove();globalThis.fetch=previous;}
});
test('connected workflow reads the account, previews and submits only after explicit consent',async()=>{
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);const previous=globalThis.fetch;const writes:any[]=[];
 const snapshot={account_ref:'a'.repeat(64),observed_at:Date.now()/1000,account:{totalWalletBalance:'123.45',availableBalance:'100',totalUnrealizedProfit:'0'},positions:[],orders:[],algo_orders:[],sessions:[],plans:[],commands:[],risk_limits:{},entry_halted:false};
 const review={kind:'PLAN',account_ref:snapshot.account_ref,expires_at:Date.now()/1000+60,review_digest:'b'.repeat(64),payload:{draft:initialBotDraft},data:{preflight:{state:'READY',quantity:'0.001'}},risk_limits:{}};
 globalThis.fetch=async(input,init)=>{const url=String(input);let data:any;
  if(url==='/api/session')data={enabled:true,authenticated:true};else if(url==='/api/bot/status')data={enabled:true,worker:'FRESH',execution_enabled:true};else if(url.startsWith('/api/bot/jobs')&&!init?.body)data={jobs:[]};else if(init?.body){const body=JSON.parse(String(init.body));writes.push(body);data={job_id:'job-'+String(writes.length).repeat(40),action:body.action,state:'SUCCEEDED',created_at:Date.now()/1000,updated_at:Date.now()/1000,error_code:null,result:body.action==='SNAPSHOT'?snapshot:body.action==='PREVIEW_PLAN'?review:{state:'MANAGING'},automatic_resend:false};}else throw Error(url);
  return new Response(JSON.stringify(data),{status:200});};
 const button=(text:string)=>{const b=[...host.querySelectorAll('button')].find(b=>b.textContent===text);assert.ok(b,'missing '+text);return b;};
 try{await act(async()=>root.render(<BotConnected draft={initialBotDraft} onDraft={()=>{}} onChart={()=>{}}/>));assert.deepEqual(writes.map(w=>w.action),['SNAPSHOT']);assert.match(host.textContent!,/123,45/);assert.equal(host.querySelector('.bot-ticket'),null);await act(async()=>button('Yönetim').click());assert.equal(host.querySelector('.bot-ticket'),null);assert.equal(host.querySelectorAll('.bot-command-groups button').length,6);assert.equal(host.querySelector('.bot-command-editor select')?.querySelectorAll('option').length,4);await act(async()=>button('Hesap ayarları').click());assert.equal(host.querySelector('.bot-command-editor select')?.querySelectorAll('option').length,5);await act(async()=>button('Yeni işlem').click());assert.ok(host.querySelector('.bot-live-ticket-only'));assert.ok(host.querySelector('.bot-ticket'));await act(async()=>button('Hesapta ön kontrol yap').click());assert.deepEqual(writes.map(w=>w.action),['SNAPSHOT','PREVIEW_PLAN']);assert.ok(button('Demo hesabında uygula').disabled);await act(async()=>(host.querySelector('dialog input[type=checkbox]') as HTMLInputElement).click());assert.equal(writes.length,2);await act(async()=>button('Demo hesabında uygula').click());assert.equal(writes[2].action,'CONFIRM');assert.equal(writes[2].payload.execute_demo,true);assert.equal(writes[2].payload.review_digest,review.review_digest);assert.equal(writes[2].payload.account_ref,snapshot.account_ref);assert.equal(host.querySelector('dialog'),null);assert.equal(host.querySelector('button[aria-pressed=true]')?.textContent,'Kayıtlar');}finally{await act(async()=>root.unmount());host.remove();globalThis.fetch=previous;}
});


test('an unexpired review remains confirmable after the separate account snapshot ages',async(t)=>{
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);const previous=globalThis.fetch;const writes:string[]=[];
 const stamp=Date.now();
 const snapshot={account_ref:'a'.repeat(64),observed_at:stamp/1000,account:{},positions:[],orders:[],algo_orders:[],sessions:[],plans:[],commands:[],risk_limits:{},entry_halted:false};
 const review={kind:'PLAN',account_ref:snapshot.account_ref,expires_at:stamp/1000+60,review_digest:'b'.repeat(64),payload:{draft:initialBotDraft},data:{preflight:{state:'READY',quantity:'0.001'}},risk_limits:{}};
 globalThis.fetch=async(input,init)=>{
  const url=String(input);let data:unknown;
  if(url==='/api/session')data={enabled:true,authenticated:true};
  else if(url==='/api/bot/status')data={enabled:true,worker:'FRESH',execution_enabled:true};
  else if(!init?.body)data={jobs:[]};
  else{const body=JSON.parse(String(init.body));writes.push(body.action);data={job_id:'job-'+String(writes.length).repeat(40),action:body.action,state:'SUCCEEDED',created_at:stamp/1000,updated_at:stamp/1000,error_code:null,result:body.action==='SNAPSHOT'?snapshot:review,automatic_resend:false};}
  return new Response(JSON.stringify(data),{status:200});
 };
 const button=(label:string)=>{const b=[...host.querySelectorAll('button')].find(b=>b.textContent===label);assert.ok(b);return b;};
 try{
  t.mock.timers.enable({apis:['Date','setInterval'],now:stamp});
  await act(async()=>root.render(<BotConnected draft={initialBotDraft} onDraft={()=>{}} onChart={()=>{}}/>));
  await act(async()=>button('Hesabı yenile').click());await act(async()=>button('Yeni işlem').click());await act(async()=>button('Hesapta ön kontrol yap').click());
  await act(async()=>{t.mock.timers.tick(20000);});
  await act(async()=>(host.querySelector('dialog input[type=checkbox]') as HTMLInputElement).click());
  assert.equal(button('Demo hesabında uygula').disabled,false);
  await act(async()=>{t.mock.timers.tick(41000);});
  assert.equal(button('Demo hesabında uygula').disabled,true);
  assert.equal(writes.includes('CONFIRM'),false);
 }finally{t.mock.timers.reset();await act(async()=>root.unmount());host.remove();globalThis.fetch=previous;}
});

test('automatic account reads run only in the active visible view and never submit a financial action',async(t)=>{
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);const previous=globalThis.fetch;
 const descriptor=Object.getOwnPropertyDescriptor(document,'visibilityState');const actions:string[]=[];let requests=0;
 globalThis.fetch=async(input,init)=>{requests++;const url=String(input);let data:unknown;
  if(url==='/api/session')data={enabled:true,authenticated:true};
  else if(url==='/api/bot/status')data={enabled:true,worker:'FRESH',execution_enabled:false};
  else if(init?.body){const body=JSON.parse(String(init.body));actions.push(body.action);data={job_id:'job-auto-'+actions.length,state:'SUCCEEDED',result:{observed_at:Date.now()/1000,account:{totalWalletBalance:'100'},account_ref:'a'.repeat(64),positions:[],orders:[],algo_orders:[],sessions:[],plans:[],commands:[],entry_halted:false}};}
  else data={jobs:[]};return new Response(JSON.stringify(data),{status:200});};
 const render=(active:boolean)=>root.render(<BotConnected active={active} draft={initialBotDraft} onDraft={()=>{}} onChart={()=>{}}/>);
 try{t.mock.timers.enable({apis:['Date','setInterval'],now:Date.now()});await act(async()=>render(false));assert.equal(requests,0);
  await act(async()=>render(true));assert.deepEqual(actions,['SNAPSHOT']);assert.match(host.textContent!,/100/);
  await act(async()=>{t.mock.timers.tick(10000);});assert.deepEqual(actions,['SNAPSHOT','SNAPSHOT']);
  Object.defineProperty(document,'visibilityState',{configurable:true,value:'hidden'});
  await act(async()=>{t.mock.timers.tick(30000);});assert.equal(actions.length,2);
  await act(async()=>render(false));Object.defineProperty(document,'visibilityState',{configurable:true,value:'visible'});
  await act(async()=>{t.mock.timers.tick(30000);});assert.equal(actions.length,2);
  await act(async()=>render(true));assert.deepEqual(actions,['SNAPSHOT','SNAPSHOT','SNAPSHOT']);
  const section=[...host.querySelectorAll('button')].find(b=>b.textContent==='Yönetim')!;await act(async()=>section.click());assert.equal(new URLSearchParams(window.location.search).get('section'),'Yönetim');assert.equal(new URLSearchParams(window.location.search).get('view'),'bot');
 }finally{await act(async()=>root.unmount());host.remove();globalThis.fetch=previous;t.mock.timers.reset();if(descriptor)Object.defineProperty(document,'visibilityState',descriptor);else Reflect.deleteProperty(document,'visibilityState');}
});

test('a disconnected worker still allows draft editing but cannot save or preview an exchange operation',async()=>{
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);const previous=globalThis.fetch;const actions:string[]=[];
 globalThis.fetch=async(input,init)=>{if(init?.body)actions.push(JSON.parse(String(init.body)).action);return new Response(JSON.stringify(String(input)==='/api/session'?{enabled:true,authenticated:true}:String(input)==='/api/bot/status'?{enabled:true,worker:'NOT_READY',execution_enabled:false}:{jobs:[]}),{status:200});};
 try{await act(async()=>root.render(<BotConnected draft={initialBotDraft} onDraft={()=>{}} onChart={()=>{}}/>));assert.match(host.textContent!,/Hesap bağlantısı kapalı/);await act(async()=>[...host.querySelectorAll('button')].find(b=>b.textContent==='Yeni işlem')!.click());const input=host.querySelector('.bot-ticket input') as HTMLInputElement;assert.ok(input);assert.equal(input.closest('fieldset')?.disabled,false);for(const label of ['Hesapta ön kontrol yap','Plan taslağını kaydet']){const b=[...host.querySelectorAll('button')].find(b=>b.textContent===label)!;assert.ok(b.disabled);}assert.deepEqual(actions,[]);}finally{await act(async()=>root.unmount());host.remove();globalThis.fetch=previous;}
});
