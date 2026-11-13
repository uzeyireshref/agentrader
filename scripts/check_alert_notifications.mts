import {familyKinds,familyNames,isPitchfork} from '../frontend/src/channelFamily.ts';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {defaultVwapIndicators} from '../frontend/src/indicatorConfig.ts';
import {defaultChartView} from '../frontend/src/chartProfiles.ts';
const require=createRequire(import.meta.url),{chromium}=require('../tools/rea/runtime/node_modules/playwright-core');
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000}});const page=await context.newPage(),errors:string[]=[],checks:string[]=[],writes:any[]=[],items:any[]=[];
const logMode=process.argv.includes('--log');
if(logMode)await page.addInitScript(()=>localStorage.setItem('agentrader.chartView',JSON.stringify({schema:'chart-view/1',price_scale:'LOG'})));
const reportDir=new URL(process.argv.includes('--dpr2')?'../reports/channel-family-dpr2-20261113/':logMode?'../reports/channel-family-log-20261113/':'../reports/alert-notifications-20261113/',import.meta.url);await mkdir(reportDir,{recursive:true});
const market={symbol:'BTCUSDT',base_asset:'BTC',quote_asset:'USDT',tick_size:'0.1',contract_type:'PERPETUAL'};
const rows=Array.from({length:300},(_,i)=>({time:1800000000+i*900,open:100+i*.1,high:110+i*.1,low:90+i*.1,close:105+i*.1,volume:10+i,quote_volume:1000,close_time:(1800000000+(i+1)*900)*1000-1,closed:i<299}));
const alertItems:any[]=[],alertEvents:any[]=[{id:'old',name:'Old history',symbol:'BTCUSDT',close:'99',message:'',candle_time:1800057600,created_at:1}];
let socket:any,heartbeat:ReturnType<typeof setInterval>|undefined;
const packet=()=>({type:'snapshot',symbol:'BTCUSDT',interval:'15m',generation:1,sequence:1,status:'LIVE',received_at:Date.now(),candles:rows,market});
page.on('pageerror',(e:Error)=>errors.push(e.message));
await context.routeWebSocket('**/api/market-stream*',(ws:any)=>{socket=ws;ws.send(JSON.stringify(packet()));});
await context.route('**/api/**',async(route:any)=>{
 const path=new URL(route.request().url()).pathname,method=route.request().method(),body=method==='GET'?null:route.request().postDataJSON();
 let response:any;
 if(path==='/api/alerts'){if(method==='GET')response={schema:'price-alerts/1',alerts:alertItems,events:alertEvents,order_authority:false};else{const a={id:'test-alert',revision:1,definition:body.definition,state:'ACTIVE',readiness:'WAITING_DATA'};alertItems.push(a);response=a;}}
 else if(path.startsWith('/api/alerts/')){const a=alertItems.find(a=>a.id===path.split('/')[3]);if(method==='PUT'){a.definition=body.definition;a.revision++;response=a;}else{if(body.action==='delete')alertItems.splice(alertItems.indexOf(a),1);else{a.state=body.action==='pause'?'PAUSED':'ACTIVE';a.revision++;}response={ok:true};}}
 else if(path==='/api/markets')response={markets:[market]};
 else if(path==='/api/workspaces/main/profile')response={workspace_id:'main',revision:0,body:{schema:'chart-profile/1',view:defaultChartView(),drawing_defaults:{}}};
 else if(path==='/api/workspaces/main/indicators')response={schema:'chart-indicators/4',workspace_id:'main',revision:0,indicators:defaultVwapIndicators()};
 else if(path==='/api/workspaces/main')response={revision:0,preferences:{symbol:'BTCUSDT',interval:'15m'}};
 else if(path==='/api/candles')response={candles:[],has_more:false};
 else if(path==='/api/workspaces/main/drawings'){
  if(method==='GET')response={drawings:items.filter(d=>!d.deleted)};
  else{const d={drawing_id:'test-'+(items.length+1),workspace_id:'main',revision:1,deleted:false,updated_at:0,geometry:body.geometry};items.push(d);writes.push(body);response=d;}
 }else if(path.startsWith('/api/drawings/')){
  const d=items.find(d=>d.drawing_id===path.split('/').at(-1));assert(d);Object.assign(d,{revision:d.revision+1,...(method==='DELETE'?{deleted:true}:{geometry:body.geometry,deleted:false})});writes.push(body);response={...d};
 }else if(path==='/api/workspaces/main/drawing-operations'){
  const drawings=body.operations.map((o:any)=>{let d=items.find(d=>d.drawing_id===o.drawing_id);if(!d){d={drawing_id:'test-'+(items.length+1),workspace_id:'main',revision:0,updated_at:0};items.push(d);}Object.assign(d,{revision:d.revision+1,geometry:o.geometry,management:o.management,deleted:o.deleted});return {...d};});writes.push(body);response={drawings};
 }else throw Error('Unexpected API '+path);
 await route.fulfill({json:response});
});
const frame=()=>page.waitForTimeout(100);
const choose=async(name:string,group?:string)=>{if(group)await page.getByLabel(group,{exact:true}).click();await page.locator('.drawing-tools').getByRole('button',{name,exact:true}).click();await page.waitForTimeout(550);};
const point=async(x=.35,y=.42)=>{const host=await page.locator('.chart-host').boundingBox(),overlay=await page.locator('svg.drawings-overlay').first().boundingBox();return {x:host!.x+overlay!.width*x,y:host!.y+overlay!.height*y};};


await context.addInitScript(()=>{
 Object.defineProperty(window,'__name',{value:Function('return arguments[0]')});
 const w=window as any;w.__desktop=[];w.__permissionRequests=0;w.__audioStarts=0;
 class FakeNotification{static permission='default';static async requestPermission(){w.__permissionRequests++;return this.permission='granted';}onclose:any;onerror:any;onclick:any;constructor(title:string,options:any){w.__desktop.push({title,options});}close(){this.onclose?.();}}
 Object.defineProperty(window,'Notification',{value:FakeNotification,configurable:true});
 const original=AudioContext.prototype.createOscillator;AudioContext.prototype.createOscillator=function(){const o=original.call(this),start=o.start.bind(o);o.start=((...args:any[])=>{w.__audioStarts++;return start(...args);}) as any;return o;};
});
let passed=false;
const fixture=JSON.parse(await readFile(new URL('engine-event.json',reportDir),'utf8'));
const trigger=(id:string)=>alertEvents.unshift({...fixture,id,created_at:Date.now()/1000});
const prefs=async()=>{await page.getByRole('button',{name:'Alarm oluştur ve yönet',exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:'Bildirimler',exact:true}).click();return page.getByRole('dialog');};
const close=async()=>page.getByRole('button',{name:'Alarmları kapat',exact:true}).click();
try{
 await page.goto('http://127.0.0.1:8765');await page.waitForFunction(()=>localStorage.getItem('agentrader.alert-receipts.v1'));assert.equal(await page.locator('.alert-toast').count(),0);checks.push('old history baseline causes no notification');
 let d=await prefs();assert(await d.getByRole('checkbox',{name:'Uygulama içi bildirim',exact:false}).isChecked());assert(!await d.getByRole('checkbox',{name:'Sesli uyarı',exact:false}).isChecked());assert.equal(await page.evaluate(()=>(window as any).__permissionRequests),0);
 await d.getByRole('checkbox',{name:'Sesli uyarı',exact:false}).check();await d.getByRole('button',{name:'Sesi dene',exact:true}).click();await page.waitForFunction(()=>(window as any).__audioStarts===2);await d.getByRole('checkbox',{name:'Masaüstü bildirimi',exact:false}).check();assert.equal(await page.evaluate(()=>(window as any).__permissionRequests),1);await page.screenshot({path:new URL('preferences-dark.png',reportDir).pathname.slice(1)});await close();checks.push('explicit sound unlock and desktop permission only on user action');
 trigger('live-1');await page.locator('.alert-toast').waitFor();await page.waitForFunction(()=>(window as any).__desktop.length===1);assert.equal(await page.evaluate(()=>(window as any).__audioStarts),4);await page.getByLabel('1 okunmamış alarm',{exact:true}).waitFor();await page.screenshot({path:new URL('toast-dark.png',reportDir).pathname.slice(1)});await page.waitForTimeout(3300);assert.equal(await page.evaluate(()=>(window as any).__desktop.length),1);assert.equal(await page.evaluate(()=>(window as any).__audioStarts),4);checks.push('real engine event reaches toast badge sound and desktop exactly once across repeated polls');
 await page.reload();await page.waitForFunction(()=>document.querySelector('.alert-unread-badge'));await page.waitForTimeout(3300);assert.equal(await page.locator('.alert-toast').count(),0);assert.equal(await page.evaluate(()=>(window as any).__desktop.length),0);d=await prefs();assert(await d.getByRole('checkbox',{name:'Sesli uyarı',exact:false}).isChecked());await close();checks.push('reload preserves preferences and unread without replaying delivery');
 await page.getByRole('button',{name:'Alarm oluştur ve yönet',exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:/^Geçmiş/}).click();await page.waitForFunction(()=>!document.querySelector('.alert-unread-badge'));await page.getByRole('dialog').getByText('Fiyat alarmi',{exact:true}).waitFor();await close();checks.push('history acknowledges unread and displays real persisted event payload');
 d=await prefs();await d.getByRole('checkbox',{name:'Sesli uyarı',exact:false}).uncheck();await d.getByRole('checkbox',{name:'Masaüstü bildirimi',exact:false}).uncheck();await d.getByRole('checkbox',{name:'Uygulama içi bildirim',exact:false}).uncheck();await close();trigger('quiet');await page.getByLabel('1 okunmamış alarm',{exact:true}).waitFor();assert.equal(await page.locator('.alert-toast').count(),0);assert.equal(await page.evaluate(()=>(window as any).__desktop.length),0);assert.equal(await page.evaluate(()=>(window as any).__audioStarts),0);checks.push('all delivery preferences off still preserves unread history');
 d=await prefs();await page.evaluate(()=>{(Notification as any).permission='denied';});await d.getByRole('checkbox',{name:'Masaüstü bildirimi',exact:false}).click();assert(!await d.getByRole('checkbox',{name:'Masaüstü bildirimi',exact:false}).isChecked());await d.getByText(/İzin engellendi/).waitFor();await close();checks.push('denied desktop permission remains off and explains recovery');
 d=await prefs();await d.getByRole('checkbox',{name:'Uygulama içi bildirim',exact:false}).check();await page.evaluate(()=>{(Notification as any).permission='granted';});await d.getByRole('checkbox',{name:'Masaüstü bildirimi',exact:false}).check();await close();
 const second=await context.newPage();second.on('pageerror',(e:Error)=>errors.push(e.message));await second.goto('http://127.0.0.1:8765');await second.waitForTimeout(3300);const before=await page.evaluate(()=>(window as any).__desktop.length);trigger('two-tabs');await page.waitForTimeout(4000);const total=await page.evaluate(()=>(window as any).__desktop.length)+await second.evaluate(()=>(window as any).__desktop.length);assert.equal(total-before,1);await second.close();checks.push('two tabs share an atomic Web Lock receipt claim and deliver desktop once');
 await page.setViewportSize({width:600,height:800});d=await prefs();assert(await d.evaluate((n:Element)=>n.scrollWidth<=n.clientWidth+1));await page.screenshot({path:new URL('preferences-mobile.png',reportDir).pathname.slice(1)});await close();await page.setViewportSize({width:1440,height:1000});await page.getByRole('button',{name:'Açık temaya geç',exact:true}).click();d=await prefs();await page.screenshot({path:new URL('preferences-light.png',reportDir).pathname.slice(1)});await close();checks.push('light theme and 600px responsive preferences');
 let offline=true;await context.route('**/api/alerts',async(route:any)=>{if(offline)await route.fulfill({status:503,json:{error:'test'}});else await route.fallback();});await page.locator('.alert-notification-warning').waitFor();d=await prefs();await d.getByText(/Alarm bildirimleri güncellenemiyor/).waitFor();offline=false;await close();await page.waitForFunction(()=>!document.querySelector('.alert-notification-warning'));checks.push('polling failure is visible and recovers automatically');
 await page.evaluate(()=>{Storage.prototype.setItem=function(){throw new DOMException('blocked','SecurityError');};});trigger('storage-blocked');await page.waitForFunction(()=>document.querySelector('.alert-notification-warning'));d=await prefs();await d.getByText(/Tarayıcı depolaması kullanılamıyor/).waitFor();await close();const storageCount=await page.evaluate(()=>(window as any).__desktop.length);await page.waitForTimeout(3300);assert.equal(await page.evaluate(()=>(window as any).__desktop.length),storageCount);checks.push('blocked storage reports degraded persistence and in-memory dedup stays active');
assert.deepEqual(errors,[]);passed=true;
}finally{clearInterval(heartbeat);await writeFile(new URL('result.json',reportDir),JSON.stringify({passed,checks,errors,personal_workspace_writes:0,desktop_delivery:'mocked OS API; real Chromium Web Locks and AudioContext',engine_event:'isolated real PriceAlerts database'},null,2));await browser.close();console.log(JSON.stringify({passed,checks,errors}));}
