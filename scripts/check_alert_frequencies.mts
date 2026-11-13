import {familyKinds,familyNames,isPitchfork} from '../frontend/src/channelFamily.ts';
import {createRequire} from 'node:module';
import {writeFile,mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {defaultVwapIndicators} from '../frontend/src/indicatorConfig.ts';
import {defaultChartView} from '../frontend/src/chartProfiles.ts';
const require=createRequire(import.meta.url),{chromium}=require('../tools/rea/runtime/node_modules/playwright-core');
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:process.argv.includes('--dpr2')?2:1}),errors:string[]=[],checks:string[]=[],writes:any[]=[],items:any[]=[];
const logMode=process.argv.includes('--log');
if(logMode)await page.addInitScript(()=>localStorage.setItem('agentrader.chartView',JSON.stringify({schema:'chart-view/1',price_scale:'LOG'})));
const reportDir=new URL(process.argv.includes('--dpr2')?'../reports/channel-family-dpr2-20261113/':logMode?'../reports/channel-family-log-20261113/':'../reports/alert-frequencies-ui-20261113/',import.meta.url);await mkdir(reportDir,{recursive:true});
const market={symbol:'BTCUSDT',base_asset:'BTC',quote_asset:'USDT',tick_size:'0.1',contract_type:'PERPETUAL'};
const rows=Array.from({length:300},(_,i)=>({time:1800000000+i*900,open:100+i*.1,high:110+i*.1,low:90+i*.1,close:105+i*.1,volume:10+i,quote_volume:1000,close_time:(1800000000+(i+1)*900)*1000-1,closed:i<299}));
const alertItems:any[]=[],alertEvents:any[]=[];
let socket:any,heartbeat:ReturnType<typeof setInterval>|undefined;
const packet=()=>({type:'snapshot',symbol:'BTCUSDT',interval:'15m',generation:1,sequence:1,status:'LIVE',received_at:Date.now(),candles:rows,market});
page.on('pageerror',(e:Error)=>errors.push(e.message));
await page.routeWebSocket('**/api/market-stream*',(ws:any)=>{socket=ws;ws.send(JSON.stringify(packet()));});
await page.route('**/api/**',async(route:any)=>{
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


let passed=false;
try{
 await page.goto('http://127.0.0.1:8765');await page.waitForFunction(()=>document.querySelector('.connection')?.textContent?.includes('Canlı'));
 await page.getByRole('button',{name:'Alarm oluştur ve yönet',exact:true}).click();let d=page.getByRole('dialog');assert.equal(await d.getByLabel('Alarm değerlendirme zamanı',{exact:true}).inputValue(),'bar_close');checks.push('existing default remains close-only');
 await d.getByLabel('Koşul 1 karşılaştırma değeri',{exact:true}).fill('100');await d.getByLabel('Alarm değerlendirme zamanı',{exact:true}).selectOption('intrabar');assert.deepEqual(await d.getByLabel('Alarm sıklığı',{exact:true}).locator('option').evaluateAll((nodes:HTMLOptionElement[])=>nodes.map(n=>n.value)),['once','bar','minute']);await d.getByLabel('Alarm sıklığı',{exact:true}).selectOption('bar');await page.screenshot({path:new URL('intrabar-dark.png',reportDir).pathname.slice(1)});await d.locator('form').getByRole('button',{name:'Oluştur',exact:true}).click();await page.waitForTimeout(100);assert.equal(alertItems[0].definition.schema,'technical-alert/4');assert.equal(alertItems[0].definition.evaluation,'intrabar');assert.equal(alertItems[0].definition.frequency,'bar');assert.equal(alertItems[0].definition.conditions[0].interval,'15m');checks.push('live once/bar/minute choices and explicit v4 persisted source intervals');
 await d.getByRole('button',{name:'Düzenle',exact:true}).click();await d.getByLabel('Alarm sıklığı',{exact:true}).selectOption('minute');await d.getByRole('button',{name:'Kaydet ve yeniden başlat',exact:true}).click();await page.waitForTimeout(100);await page.reload();await page.getByRole('button',{name:'Alarm oluştur ve yönet',exact:true}).click();d=page.getByRole('dialog');await d.getByRole('navigation',{name:'Alarm bölümleri'}).getByRole('button',{name:/^Alarmlar/}).click();await d.getByRole('button',{name:'Düzenle',exact:true}).click();assert.equal(await d.getByLabel('Alarm değerlendirme zamanı',{exact:true}).inputValue(),'intrabar');assert.equal(await d.getByLabel('Alarm sıklığı',{exact:true}).inputValue(),'minute');checks.push('rolling minute selection restored after reload and edit');
 await d.getByLabel('Alarm değerlendirme zamanı',{exact:true}).selectOption('bar_close');await d.getByLabel('Alarm sıklığı',{exact:true}).selectOption('bar_close');await d.getByRole('button',{name:'Kaydet ve yeniden başlat',exact:true}).click();await page.waitForTimeout(100);assert.equal(alertItems[0].definition.schema,'technical-alert/3');assert(!('evaluation' in alertItems[0].definition));assert.equal(alertItems[0].definition.frequency,'bar_close');checks.push('switch back to confirmed mode removes live contract and preserves legacy close behavior');
 await d.getByRole('button',{name:'Düzenle',exact:true}).click();await d.getByLabel('Alarm değerlendirme zamanı',{exact:true}).selectOption('intrabar');await d.getByRole('button',{name:'Kaydet ve yeniden başlat',exact:true}).click();await page.waitForTimeout(100);assert.equal(alertItems[0].definition.frequency,'once');checks.push('live once-only selection saves and resets safely on mode change');
 const fixture=JSON.parse(await (await import('node:fs/promises')).readFile(new URL('../reports/alert-frequencies-ui-20261113/engine-event.json',import.meta.url),'utf8'));alertEvents.push({...fixture,created_at:Date.now()/1000});await d.getByRole('button',{name:'Geçmiş',exact:true}).click();await d.getByText(/Anlık · oluşan mum/).waitFor();await page.screenshot({path:new URL('intrabar-history.png',reportDir).pathname.slice(1)});await d.getByRole('button',{name:'Alarmları kapat',exact:true}).click();checks.push('actual live engine event displayed as forming-candle observation in history');
 await page.setViewportSize({width:600,height:800});await page.getByRole('button',{name:'Alarm oluştur ve yönet',exact:true}).click();d=page.getByRole('dialog');await d.getByLabel('Alarm değerlendirme zamanı',{exact:true}).selectOption('intrabar');assert(await d.evaluate((n:Element)=>n.scrollWidth<=n.clientWidth+1));await page.screenshot({path:new URL('intrabar-mobile.png',reportDir).pathname.slice(1)});await d.getByRole('button',{name:'Alarmları kapat',exact:true}).click();await page.setViewportSize({width:1440,height:1000});await page.getByRole('button',{name:'Açık temaya geç',exact:true}).click();await page.getByRole('button',{name:'Alarm oluştur ve yönet',exact:true}).click();d=page.getByRole('dialog');await d.getByLabel('Alarm değerlendirme zamanı',{exact:true}).selectOption('intrabar');await page.screenshot({path:new URL('intrabar-light.png',reportDir).pathname.slice(1)});await d.getByRole('button',{name:'Alarmları kapat',exact:true}).click();checks.push('dark/light and responsive live frequency editor');assert.deepEqual(errors,[]);passed=true;
}finally{await writeFile(new URL('result.json',reportDir),JSON.stringify({passed,checks,errors,personal_workspace_writes:0,scope:'Chrome production UI with isolated API fixtures and actual backend event'},null,2));await browser.close();console.log(JSON.stringify({passed,checks,errors}));}
