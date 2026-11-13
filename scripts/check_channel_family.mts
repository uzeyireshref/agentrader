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
const reportDir=new URL(process.argv.includes('--dpr2')?'../reports/channel-family-dpr2-20261113/':logMode?'../reports/channel-family-log-20261113/':'../reports/channel-family-20261113/',import.meta.url);await mkdir(reportDir,{recursive:true});
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
 for(const kind of familyKinds){
  await choose(familyNames[kind],isPitchfork(kind)?'Pitchfork araçları':'Çizgi araçları');const a=await point(.25,.55),b=await point(.55,.3),c=await point(.65,.65),before=writes.length;
  await page.mouse.click(a.x,a.y);await page.mouse.move(b.x,b.y);await frame();assert.equal(writes.length,before);assert.equal(await page.locator('.creation-preview [data-drawing]').count(),1);assert.equal(await page.locator('.creation-preview [data-drawing]').first().isVisible(),true,kind+' baseline visible');
  await page.waitForTimeout(550);await page.mouse.click(b.x,b.y);
  if(kind!=='regression_channel'){await page.mouse.move(c.x,c.y);await frame();assert(await page.locator('.creation-preview .family-line').count()>0,kind+' full preview');assert.equal(writes.length,before);await page.waitForTimeout(550);await page.mouse.click(c.x,c.y);}
  await frame();assert.equal(writes.length,before+1);const item=items.at(-1);assert.equal(item.geometry.kind,kind);assert.equal(item.geometry.schema,'chart-channel-family/1');assert.equal(item.geometry.anchors.length,kind==='regression_channel'?2:3);
  const group=page.locator('[data-drawing="'+item.drawing_id+'"]'),handles=page.locator('[data-drawing-handles="'+item.drawing_id+'"]');assert(await group.locator('.family-line').count()>0,kind+' rendered');assert.equal(await handles.locator('circle').count(),kind==='regression_channel'?2:isPitchfork(kind)?3:4);
  await page.getByLabel('Seçili çizimin tüm ayarları',{exact:true}).click();const popup=page.getByRole('region',{name:'Seçili çizim ayarları',exact:true});await popup.getByLabel('Kanal çizgilerini uzat',{exact:true}).selectOption('both');await popup.getByLabel('Kanal ve pitchfork metni',{exact:true}).fill('REA '+kind);await popup.getByLabel('Kanal fiyat etiketlerini göster',{exact:true}).check();
  if(isPitchfork(kind))await popup.getByLabel('Pitchfork seviye oranları',{exact:true}).fill('0.5; 1; 1.5');
  if(kind==='regression_channel'){await popup.getByLabel('Pearson korelasyonunu göster',{exact:true}).check();await popup.getByLabel('Regresyon fiyat kaynağı',{exact:true}).selectOption('hlc3');}
  const styleName=isPitchfork(kind)||kind==='regression_channel'?'Orta çizgi':'İlk sınır',styleRole=styleName==='Orta çizgi'?'median':'base';await popup.getByLabel(styleName+' için özel stil',{exact:true}).check();await popup.getByLabel(styleName+' rengi',{exact:true}).fill('#ff8800');await popup.getByLabel(styleName+' kalınlığı',{exact:true}).selectOption('4');await popup.getByLabel(styleName+' çizgi stili',{exact:true}).selectOption('dotted');
  await popup.getByRole('button',{name:'Kaydet',exact:true}).click();await frame();assert.equal(item.geometry.options.extend,'both');assert.deepEqual(item.geometry.options.line_styles[styleRole],{color:'#ff8800',width:4,style:'dotted'});assert.match(await group.locator('[data-family-role="'+styleRole+'"]').getAttribute('style'),/stroke:#ff8800;stroke-width:4;stroke-dasharray:2 4/);assert.equal(item.geometry.text,'REA '+kind);assert(await group.locator('.family-price').count()>0);await page.getByLabel('Çizim ayarlarını kapat',{exact:true}).click();
  const oldAnchors=structuredClone(item.geometry.anchors),circle=await handles.locator('circle').first().boundingBox();await page.mouse.move(circle!.x+5,circle!.y+5);await page.mouse.down();await page.mouse.move(circle!.x+25,circle!.y+15,{steps:5});await page.mouse.up();await frame();assert.notDeepEqual(item.geometry.anchors,oldAnchors,kind+' endpoint edit');
  await page.locator('.chart-stage').focus();await page.keyboard.press('Control+z');await frame();assert.deepEqual(item.geometry.anchors,oldAnchors,kind+' undo edit');
  if(kind==='flat_channel'||kind==='disjoint_channel'){const derived=await handles.locator('[data-anchor="3"]').boundingBox();const old=structuredClone(item.geometry.anchors);await page.mouse.move(derived!.x+5,derived!.y+5);await page.mouse.down();await page.mouse.move(derived!.x+15,derived!.y-10,{steps:5});await page.mouse.up();await frame();assert.equal(item.geometry.anchors.length,3);assert.notDeepEqual(item.geometry.anchors,old);}
  const isolate=await page.addStyleTag({content:'.drawings-overlay [data-drawing]:not([data-drawing="'+item.drawing_id+'"]){visibility:hidden}'});await page.screenshot({path:new URL(kind+'.png',reportDir).pathname.slice(1)});await isolate.evaluate((node:Element)=>node.remove());checks.push(kind+': phased preview, create, options/text/labels, independent line styles, circular anchors, edit and undo');
 }
 const total=items.length;await page.reload();await page.waitForFunction(()=>document.querySelector('.connection')?.textContent?.includes('Canlı'));await frame();assert.equal(await page.locator('[data-drawing]').count(),total);assert.equal(total,8);assert.equal(await page.locator('[data-family-role="median"]').count()>0,true);checks.push('reload restores all eight saved family geometries and options');
 const snapshot=JSON.stringify(items.map(d=>d.geometry)),writeCount=writes.length,zoomPoint=await point(.45,.45);await page.mouse.move(zoomPoint.x,zoomPoint.y);await page.mouse.wheel(0,-300);await page.waitForTimeout(300);const panPoint=await page.evaluate(()=>{const r=document.querySelector('.chart-host')!.getBoundingClientRect(),o=document.querySelector('svg.drawings-overlay')!.getBoundingClientRect();for(let y=15;y<o.height-15;y+=20)for(let x=20;x<o.width-100;x+=30){const e=document.elementFromPoint(r.left+x,r.top+y);if(e?.tagName==='CANVAS')return {x:r.left+x,y:r.top+y};}return null;});assert(panPoint,'uncovered chart area for pan');await page.mouse.move(panPoint.x,panPoint.y);await page.mouse.down();await page.mouse.move(panPoint.x+60,panPoint.y,{steps:6});await page.mouse.up();await frame();assert.equal(JSON.stringify(items.map(d=>d.geometry)),snapshot,'zoom/pan never rewrites geometry');assert.equal(writes.length,writeCount,'zoom/pan never writes drawing revisions');assert(await page.locator('.family-line:visible').count()>0);checks.push('zoom/pan preserves geometry and revisions with visible reprojection');
 assert.deepEqual(errors,[]);passed=true;
}finally{clearInterval(heartbeat);await writeFile(new URL('result.json',reportDir),JSON.stringify({passed,checks,errors,writes:writes.length,user_workspace_writes:0,scope:'Current App; real Chrome, mocked API/persistence; '+(logMode?'LOG':'LINEAR')+'; DPR '+(process.argv.includes('--dpr2')?2:1)},null,2));await browser.close();console.log(JSON.stringify({passed,checks,errors}));}
