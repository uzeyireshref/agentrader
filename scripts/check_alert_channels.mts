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
const reportDir=new URL(process.argv.includes('--dpr2')?'../reports/channel-family-dpr2-20261113/':logMode?'../reports/channel-family-log-20261113/':'../reports/alert-channels-ui-20261113/',import.meta.url);await mkdir(reportDir,{recursive:true});
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
const open=async()=>{await page.getByRole('button',{name:'Alarm oluştur ve yönet',exact:true}).click();return page.getByRole('dialog');};
const close=async()=>page.getByRole('button',{name:'Alarmları kapat',exact:true}).click();
try{
 await page.goto('http://127.0.0.1:8765');await page.waitForFunction(()=>localStorage.getItem('agentrader.alert-receipts.v1'));let d=await open();await d.getByLabel('Koşul 1 karşılaştırma değeri',{exact:true}).fill('100');await d.getByRole('button',{name:'Kanallar',exact:true}).click();assert.equal(await d.getByLabel('Bildirim seçimi',{exact:true}).inputValue(),'inherit');await d.getByLabel('Bildirim seçimi',{exact:true}).selectOption('custom');await d.getByRole('checkbox',{name:'Bildirim kartı',exact:true}).uncheck();await d.getByText('Yalnızca geçmiş',{exact:true}).waitFor();await page.screenshot({path:new URL('channels-dark.png',reportDir).pathname.slice(1)});await d.locator('form').getByRole('button',{name:'Oluştur',exact:true}).click();await page.waitForTimeout(100);assert.deepEqual(alertItems[0].definition.notification_channels,{schema:'alert-notification-channels/1',mode:'custom',inApp:false,sound:false,desktop:false});checks.push('default inheritance and history-only alarm persisted');
 await d.getByRole('button',{name:'Düzenle',exact:true}).click();await d.getByRole('button',{name:'Kanallar',exact:true}).click();await d.getByRole('checkbox',{name:'Sesli uyarı',exact:true}).check();await d.getByText(/Ses bu tarayıcıda kapalı/).waitFor();assert.equal(await page.evaluate(()=>(window as any).__permissionRequests),0);await d.getByRole('button',{name:'Kaydet ve yeniden başlat',exact:true}).click();await page.waitForTimeout(100);await page.reload();d=await open();await d.getByRole('navigation',{name:'Alarm bölümleri'}).getByRole('button',{name:/^Alarmlar/}).click();await d.getByRole('button',{name:'Düzenle',exact:true}).click();await d.getByRole('button',{name:'Kanallar',exact:true}).click();assert(await d.getByRole('checkbox',{name:'Sesli uyarı',exact:true}).isChecked());assert(!await d.getByRole('checkbox',{name:'Bildirim kartı',exact:true}).isChecked());await d.getByLabel('Bildirim seçimi',{exact:true}).selectOption('inherit');await d.getByRole('button',{name:'Kaydet ve yeniden başlat',exact:true}).click();await page.waitForTimeout(100);assert.deepEqual(alertItems[0].definition.notification_channels,{schema:'alert-notification-channels/1',mode:'inherit'});await close();checks.push('independent selections survive reload/edit and can return to inheritance without permission prompts');
 d=await open();await d.getByRole('button',{name:'Bildirimler',exact:true}).click();await d.getByRole('checkbox',{name:'Sesli uyarı',exact:false}).check();await d.getByRole('checkbox',{name:'Masaüstü bildirimi',exact:false}).check();await close();
 const fixtures=JSON.parse(await readFile(new URL('engine-events.json',reportDir),'utf8'));alertEvents.unshift(...fixtures.map((e:any)=>({...e,created_at:Date.now()/1000})));await page.waitForFunction(()=>(window as any).__desktop.length===1);await page.getByLabel('3 okunmamış alarm',{exact:true}).waitFor();assert.equal(await page.locator('.alert-toast').count(),1);await page.locator('.alert-toast strong').getByText('Card',{exact:true}).waitFor();assert.equal(await page.evaluate(()=>(window as any).__audioStarts),2);assert.equal(await page.evaluate(()=>(window as any).__desktop[0].title),'Desktop');await page.screenshot({path:new URL('channel-delivery.png',reportDir).pathname.slice(1)});checks.push('real mixed batch routes only Card to toast, Sound to audio, Desktop to OS API; History stays silent');
 await page.locator('.alert-toast').getByRole('button',{name:'Geçmişi aç',exact:true}).click();d=page.getByRole('dialog');await page.waitForFunction(()=>!document.querySelector('.alert-unread-badge'));assert.equal(await d.locator('.alert-list-record').count(),5);await d.getByRole('button',{name:'Bildirimler',exact:true}).click();await d.getByRole('checkbox',{name:'Sesli uyarı',exact:false}).uncheck();await d.getByRole('checkbox',{name:'Masaüstü bildirimi',exact:false}).uncheck();await d.getByRole('checkbox',{name:'Uygulama içi bildirim',exact:false}).uncheck();await close();alertEvents.unshift(...fixtures.map((e:any)=>({...e,id:e.id+'-off',created_at:Date.now()/1000})));await page.getByLabel('3 okunmamış alarm',{exact:true}).waitFor();assert.equal(await page.locator('.alert-toast').count(),0);assert.equal(await page.evaluate(()=>(window as any).__audioStarts),2);assert.equal(await page.evaluate(()=>(window as any).__desktop.length),1);checks.push('browser master switches override per-alert selections while eligible events stay in history');
 alertEvents.unshift({...fixtures[0],id:'schedule-muted',created_at:Date.now()/1000,notification_gate:{schema:'alert-notification-gate/1',allowed:false,reason:'OUTSIDE_SCHEDULE',timezone:'UTC'}});await page.waitForFunction(()=>JSON.parse(localStorage.getItem('agentrader.alert-receipts.v1')||'{}').seen?.includes('schedule-muted'));assert.equal(await page.locator('.alert-unread-badge').textContent(),'3');checks.push('schedule gate still mutes explicitly selected per-alert channels');
 await page.reload();await page.waitForTimeout(3300);assert.equal(await page.locator('.alert-toast').count(),0);assert.equal(await page.evaluate(()=>(window as any).__desktop.length),0);checks.push('receipt persistence prevents delivery replay after reload');
 await page.setViewportSize({width:600,height:800});d=await open();await d.getByRole('button',{name:'Kanallar',exact:true}).click();await d.getByLabel('Bildirim seçimi',{exact:true}).selectOption('custom');assert(await d.evaluate((n:Element)=>n.scrollWidth<=n.clientWidth+1));await page.screenshot({path:new URL('channels-mobile.png',reportDir).pathname.slice(1)});await close();await page.setViewportSize({width:1440,height:1000});await page.getByRole('button',{name:'Açık temaya geç',exact:true}).click();d=await open();await d.getByRole('button',{name:'Kanallar',exact:true}).click();await d.getByLabel('Bildirim seçimi',{exact:true}).selectOption('custom');await page.screenshot({path:new URL('channels-light.png',reportDir).pathname.slice(1)});await close();checks.push('dark/light and 600px editor layout');assert.deepEqual(errors,[]);passed=true;
}finally{await writeFile(new URL('result.json',reportDir),JSON.stringify({passed,checks,errors,personal_workspace_writes:0,scope:'production Chromium, real engine event fixtures, actual Web Audio and mocked OS Notification API'},null,2));await browser.close();console.log(JSON.stringify({passed,checks,errors}));}
