import {createRequire} from 'node:module';
import {writeFile,mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {defaultVwapIndicators} from '../frontend/src/indicatorConfig.ts';
import {defaultChartView} from '../frontend/src/chartProfiles.ts';
const require=createRequire(import.meta.url),{chromium}=require('../tools/rea/runtime/node_modules/playwright-core');
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors:string[]=[],checks:string[]=[],writes:any[]=[],items:any[]=[];
const reportDir=new URL('../reports/drawing-interaction-20261113/',import.meta.url);await mkdir(reportDir,{recursive:true});
const market={symbol:'BTCUSDT',base_asset:'BTC',quote_asset:'USDT',tick_size:'0.1',contract_type:'PERPETUAL'};
const rows=Array.from({length:300},(_,i)=>({time:1800000000+i*900,open:100+i*.1,high:110+i*.1,low:90+i*.1,close:105+i*.1,volume:10+i,quote_volume:1000,close_time:(1800000000+(i+1)*900)*1000-1,closed:i<299}));
let socket:any,heartbeat:ReturnType<typeof setInterval>|undefined;
const packet=()=>({type:'snapshot',symbol:'BTCUSDT',interval:'15m',generation:1,sequence:1,status:'LIVE',received_at:Date.now(),candles:rows,market});
page.on('pageerror',(e:Error)=>errors.push(e.message));
await page.routeWebSocket('**/api/market-stream*',(ws:any)=>{socket=ws;ws.send(JSON.stringify(packet()));});
await page.route('**/api/**',async(route:any)=>{
 const path=new URL(route.request().url()).pathname,method=route.request().method(),body=method==='GET'?null:route.request().postDataJSON();
 let response:any;
 if(path==='/api/markets')response={markets:[market]};
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
 await page.goto(process.argv[2]??'http://127.0.0.1:5174/');await page.waitForFunction(()=>document.querySelector('.connection')?.textContent?.includes('Canlı'));heartbeat=setInterval(()=>socket?.send(JSON.stringify(packet())),1000);await frame();
 await choose('Trend çizgisi','Çizgi araçları');const a=await point(),b=await point(.68,.68);
 await page.mouse.click(a.x,a.y);await page.mouse.move(b.x,b.y);await frame();
 assert.equal(writes.length,0);assert.equal(await page.locator('.creation-preview [data-drawing]').count(),1);assert.equal(await page.locator('.creation-preview [data-drawing-handles] circle').count(),2);assert.equal(await page.locator('.drawing-mouse-price').isVisible(),true);assert.equal(await page.locator('.drawing-price-range').isVisible(),true);
 const line=page.locator('.creation-preview .shape-trend');const x2=await line.getAttribute('x2');await page.mouse.move(b.x-80,b.y-30);await frame();assert.notEqual(await line.getAttribute('x2'),x2);checks.push('live trend preview moves after first click with zero writes');
 await page.screenshot({path:new URL('trend-preview.png',reportDir).pathname.slice(1)});
 await page.waitForTimeout(550);await page.mouse.click(b.x,b.y);await frame();assert.equal(writes.length,1);assert.equal(await page.locator('.creation-preview [data-drawing]').count(),0);assert.equal(await page.getByRole('toolbar',{name:'Seçili çizimi düzenle'}).isVisible(),true);checks.push('completion writes once and opens contextual toolbar');
 const grip=page.getByRole('button',{name:'Çizim çubuğunu taşı',exact:true}),beforeToolbar=await page.locator('.floating-drawing-toolbar').boundingBox(),gripBox=await grip.boundingBox(),beforeMoveWrites=writes.length;
 await page.mouse.move(gripBox!.x+gripBox!.width/2,gripBox!.y+gripBox!.height/2);await page.mouse.down();await page.mouse.move(gripBox!.x+gripBox!.width/2+100,gripBox!.y+gripBox!.height/2+65,{steps:8});await page.mouse.up();await frame();const movedToolbar=await page.locator('.floating-drawing-toolbar').boundingBox();assert(Math.abs(movedToolbar!.x-beforeToolbar!.x-100)<2);assert(Math.abs(movedToolbar!.y-beforeToolbar!.y-65)<2);assert.equal(writes.length,beforeMoveWrites);await grip.focus();await page.keyboard.press('ArrowLeft');await frame();assert(Math.abs((await page.locator('.floating-drawing-toolbar').boundingBox())!.x-movedToolbar!.x+5)<2);checks.push('floating toolbar drags and moves by keyboard without drawing writes');
 const endpoints=page.locator('[data-drawing-handles="test-1"] circle');assert.equal(await endpoints.count(),2);for(const node of await endpoints.all()){assert.equal(await node.getAttribute('r'),'5');assert.notEqual(await node.evaluate((e:Element)=>getComputedStyle(e).stroke),'rgba(0, 0, 0, 0)');}checks.push('selected endpoints have visible circular handles without square outline');
 await page.getByLabel('Seçili çizimin rengi',{exact:true}).selectOption('#d95656');await frame();await page.getByLabel('Seçili çizimin kalınlığı',{exact:true}).selectOption('3');await frame();assert.equal(items[0].management.line_width,3);assert.equal(items[0].management.color,'#d95656');
 await page.getByLabel('Seçili çizimin tüm ayarları',{exact:true}).click();const popup=page.getByRole('region',{name:'Seçili çizim ayarları',exact:true});await popup.getByLabel('Çizim adı',{exact:true}).fill('Destek notu');await popup.getByRole('button',{name:'Kaydet',exact:true}).click();await frame();assert.equal(items[0].geometry.label,'Destek notu');
 await page.getByLabel('Çizim ayarlarını kapat',{exact:true}).click();await page.screenshot({path:new URL('selected-toolbar.png',reportDir).pathname.slice(1)});checks.push('color width and annotation title edit without opening side panel');
 await page.locator('.chart-stage').focus();await page.keyboard.press('Control+z');await frame();assert.notEqual(items[0].geometry.label,'Destek notu');await page.keyboard.press('Control+Shift+z');await frame();assert.equal(items[0].geometry.label,'Destek notu');checks.push('keyboard undo and redo restore persisted title');
 await page.keyboard.press('Delete');await frame();assert.equal(items[0].deleted,true);await page.getByRole('button',{name:'Geri al',exact:true}).click();await frame();assert.equal(items[0].deleted,false);checks.push('Delete and top undo restore drawing');
 // SVG body hover keeps mouse price visible; the native SVG focus outline is gone.
 const hit=page.locator('[data-drawing="test-1"] .hit-line');const x1=Number(await hit.getAttribute('x1')),y1=Number(await hit.getAttribute('y1')),endX=Number(await hit.getAttribute('x2')),endY=Number(await hit.getAttribute('y2')),host=await page.locator('.chart-host').boundingBox();
 await page.mouse.move(host!.x+(x1+endX)/2,host!.y+(y1+endY)/2);await frame();assert.equal(await page.locator('.drawing-mouse-price').isVisible(),true);assert.equal(await page.locator('[data-drawing="test-1"]').evaluate((e:Element)=>getComputedStyle(e).outlineStyle),'none');checks.push('price visible on SVG hover without rectangular outline');
 const beforeDrag=writes.length,oldBand=await page.locator('.drawing-price-range').getAttribute('style');
 await page.mouse.down();await page.mouse.move(host!.x+(x1+endX)/2+20,host!.y+(y1+endY)/2-25,{steps:5});await frame();assert.equal(writes.length,beforeDrag);assert.notEqual(await page.locator('.drawing-price-range').getAttribute('style'),oldBand);await page.mouse.up();await frame();assert.equal(writes.length,beforeDrag+1);checks.push('drag price extent follows preview and saves once on release');
 const anchorBefore=structuredClone(items[0].geometry.anchors),handle=await page.locator('[data-drawing-handles="test-1"] circle').first().boundingBox();await page.mouse.move(handle!.x+handle!.width/2,handle!.y+handle!.height/2);await page.mouse.down();await page.mouse.move(handle!.x+handle!.width/2,handle!.y+handle!.height/2-15,{steps:5});await page.mouse.up();await frame();assert.notEqual(items[0].geometry.anchors[0].price,anchorBefore[0].price);assert.deepEqual(items[0].geometry.anchors[1],anchorBefore[1]);checks.push('circular endpoint drag changes only its own anchor');
 await page.getByLabel('Seçili çizimi kilitle',{exact:true}).click();await frame();const beforeLockedDelete=writes.length;await page.locator('.chart-stage').focus();await page.keyboard.press('Delete');await frame();assert.equal(writes.length,beforeLockedDelete);assert.equal(items[0].deleted,false);await page.getByLabel('Seçili çizimin kilidini aç',{exact:true}).click();await frame();checks.push('locked drawing cannot be deleted by keyboard');
 for(const [name,group] of [['Fibonacci','Fibonacci araçları'],['Fiyat bölgesi',undefined],['Paralel kanal','Çizgi araçları']] as const){
  await choose(name,group);const first=await point(.25,.3),next=await point(.6,.65);const before=writes.length;await page.mouse.click(first.x,first.y);await page.mouse.move(next.x,next.y);await frame();assert.equal(await page.locator('.creation-preview [data-drawing]').count(),1);assert.equal(writes.length,before);
  if(name==='Paralel kanal'){await page.waitForTimeout(550);await page.mouse.click(next.x,next.y);const third=await point(.4,.25);await page.mouse.move(third.x,third.y);await frame();assert.equal(await page.locator('.creation-preview .channel-fill').count(),1);await page.screenshot({path:new URL('channel-preview.png',reportDir).pathname.slice(1)});}
  await page.keyboard.press('Escape');await frame();assert.equal(await page.locator('.creation-preview [data-drawing]').count(),0);assert.equal(writes.length,before);checks.push(name+' previews and Escape cancels without writes');
 }
 await choose('Not','Açıklama araçları');const notePoint=await point(.45,.35);await page.mouse.click(notePoint.x,notePoint.y);await frame();assert.equal(await page.getByRole('toolbar',{name:'Seçili çizimi düzenle'}).isVisible(),true);await page.getByLabel('Çizim metni ve notu',{exact:true}).click();const noteSettings=page.getByRole('region',{name:'Seçili çizim ayarları',exact:true}),text=noteSettings.getByLabel('Açıklama metni',{exact:true});await text.fill('Birinci satır\nİkinci satır');const beforeTextKey=writes.length;await page.keyboard.press('Delete');await frame();assert.equal(writes.length,beforeTextKey);await noteSettings.getByRole('button',{name:'Metni kaydet',exact:true}).click();await frame();assert.equal(items.at(-1).geometry.text,'Birinci satır\nİkinci satır');await page.getByLabel('Çizim ayarlarını kapat',{exact:true}).click();checks.push('multiline note editing and native Delete in textarea preserve drawing');
 await page.setViewportSize({width:650,height:850});await frame();await page.locator('[data-drawing="test-1"]').focus();await page.keyboard.press('Enter');await frame();const toolbar=await page.locator('.floating-drawing-toolbar').boundingBox();assert(toolbar&&toolbar.x>=0&&toolbar.x+toolbar.width<=650);assert.equal(await page.locator('[data-drawing="test-1"]').evaluate((e:Element)=>getComputedStyle(e).outlineStyle),'none');assert.equal(await page.getByLabel('Seçili çizimi sil',{exact:true}).evaluate((e:Element)=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}),true);await page.screenshot({path:new URL('narrow-toolbar.png',reportDir).pathname.slice(1)});checks.push('context toolbar stays inside narrow viewport');
 assert.deepEqual(errors,[]);passed=true;
}finally{
 clearInterval(heartbeat);await writeFile(new URL('result.json',reportDir),JSON.stringify({passed,checks,errors,writes:writes.length,user_workspace_writes:0,scope:'Isolated browser with mocked market and drawing persistence'},null,2));await browser.close();console.log(JSON.stringify({passed,checks,errors}));
}
