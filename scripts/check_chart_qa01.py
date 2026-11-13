"""QA01 current production acceptance: actual input/raster, five runs,20 cleanups."""
import argparse,base64,hashlib,io,json,math,os,platform,time,traceback,sys
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright,expect
from qa_chart_fixture import Fixture,ROOT

MONITOR="""()=>{const m={frames:[],errors:0,hidden:0,truncated:0,viewport:false,start:performance.now(),initial:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio}};let last=null,raf=0;const error=()=>m.errors++;const hidden=()=>{if(document.hidden)m.hidden++};const frame=t=>{if(last!==null){if(m.frames.length<10000)m.frames.push(t-last);else m.truncated++}last=t;m.viewport||=innerWidth!==m.initial.width||innerHeight!==m.initial.height||devicePixelRatio!==m.initial.dpr;raf=requestAnimationFrame(frame)};window.addEventListener('error',error);window.addEventListener('unhandledrejection',error);document.addEventListener('visibilitychange',hidden);raf=requestAnimationFrame(frame);window.__qaFinish=()=>{cancelAnimationFrame(raf);window.removeEventListener('error',error);window.removeEventListener('unhandledrejection',error);document.removeEventListener('visibilitychange',hidden);return {...m,duration:performance.now()-m.start,visibility:document.visibilityState}};}"""
def p95(values):return sorted(values)[math.ceil(len(values)*.95)-1]

def native_point(f,p):
 b=p.locator('.chart-stage').bounding_box();pane=f.read(p,'chart.paneSize(0)')
 for xf in (.75,.45,.25,.85):
  for yf in (.05,.12,.2,.35):
   x=b['x']+pane['width']*xf;y=b['y']+pane['height']*yf
   if p.evaluate('([x,y])=>!!document.elementFromPoint(x,y)?.closest(".chart-host")',[x,y]):return x,y
 raise AssertionError('No native chart input point')

def menu(p,label,button):
 t=p.get_by_label(label,exact=True)
 if t.locator('..').get_attribute('open') is None:t.click()
 t.locator('..').get_by_role('button',name=button,exact=True).click()

def performance(f,p,result,seconds=60):
 result['runs']=[];result['fixture']=f.evidence();f.pin_view(p)
 for run in range(5):
  f.pin_view(p);p.locator('[data-drawing="'+f.trend['drawing_id']+'"]').press('Enter');p.wait_for_timeout(150)
  p.evaluate(MONITOR);start=time.monotonic();cycles=0
  while time.monotonic()-start<seconds:
   x,y=native_point(f,p);p.mouse.move(x,y)
   for delta in (-100,100):
    old=f.read(p,'chart.timeScale().getVisibleLogicalRange()');p.mouse.wheel(0,delta);p.wait_for_timeout(70);assert old!=f.read(p,'chart.timeScale().getVisibleLogicalRange()'),'Wheel workload missing'
   x,y=native_point(f,p)
   for dx in (20,-20):
    old=f.read(p,'chart.timeScale().getVisibleLogicalRange()');p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+dx,y,steps=3);p.mouse.up();p.wait_for_timeout(40);assert old!=f.read(p,'chart.timeScale().getVisibleLogicalRange()'),'Pan workload missing'
   handle=p.locator('[data-drawing-handles="'+f.trend['drawing_id']+'"] [data-anchor="0"]');b=handle.bounding_box();assert b
   before=f.read(p,'chart.options().handleScroll');p.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);p.mouse.down();p.mouse.move(b['x']+b['width']/2+10,b['y']+b['height']/2-5,steps=3);assert f.read(p,'chart.options().handleScroll')!=before
   p.keyboard.press('Escape');p.mouse.up();assert f.read(p,'chart.options().handleScroll')==before;cycles+=1
  m=p.evaluate('window.__qaFinish()');intervals=m.pop('frames');m.update(samples=len(intervals),raf_p95_ms=p95(intervals),raf_max_ms=max(intervals),cycles=cycles,run=run+1)
  m['valid']=len(intervals)>=30 and not any(m[k] for k in ('errors','hidden','viewport','truncated')) and m['visibility']=='visible' and m['duration']>=seconds*1000 and f.read(p,'view.candles.length')==1001 and p.locator('[data-drawing]').count()==200 and f.read(p,'view.status')=='LIVE'
  result['runs'].append(m);print('run '+str(run+1)+' p95='+str(round(m['raf_p95_ms'],2))+'ms valid='+str(m['valid']),flush=True)
  assert m['valid'] and m['raf_p95_ms']<=33.34,m
 # Chrome's own input-to-frame-swap timestamps exclude screenshot encoding/transport.
 session=p.context.new_cdp_session(p);events=[];done=[];session.on('Tracing.dataCollected',lambda e:events.extend(e['value']));session.on('Tracing.tracingComplete',lambda e:done.append(True));session.send('Tracing.start',dict(categories='benchmark,latencyInfo',transferMode='ReportEvents'))
 f.pin_view(p)
 for i in range(20):
  x,y=native_point(f,p);p.mouse.move(x,y);old=f.read(p,'chart.timeScale().getVisibleLogicalRange()');p.mouse.wheel(0,-80 if i%2==0 else 80);p.wait_for_timeout(160);assert old!=f.read(p,'chart.timeScale().getVisibleLogicalRange()')
 session.send('Tracing.end')
 for _ in range(100):
  if done:break
  p.wait_for_timeout(50)
 assert done,'Incomplete trace'
 latencies={}
 for e in events:
  if e['name']!='InputLatency::MouseWheel' or e['ph']!='b':continue
  info=e.get('args',{}).get('chrome_latency_info',{});c={x['component_type']:x['time_us'] for x in info.get('component_info',[])}
  if 'COMPONENT_INPUT_EVENT_LATENCY_FRAME_SWAP' in c and 'COMPONENT_INPUT_EVENT_LATENCY_ORIGINAL' in c:
   original=c['COMPONENT_INPUT_EVENT_LATENCY_ORIGINAL'];value=(c['COMPONENT_INPUT_EVENT_LATENCY_FRAME_SWAP']-original)/1000
   if not info.get('is_coalesced'):latencies[original]=max(latencies.get(original,0),value)
 values=list(latencies.values());assert len(values)==20 and all(x>0 for x in values),values
 trace=ROOT/('reports/qa01-wheel-'+('acceptance' if seconds==60 else 'calibration')+'-20261113.json');trace.write_text(json.dumps(dict(traceEvents=events)),encoding='utf-8')
 result['feedback']=dict(method='Chrome InputLatency::MouseWheel ORIGINAL to FRAME_SWAP; compositor presentation proxy, not physical display scanout',samples=values,p95_ms=p95(values),maximum_ms=max(values),target_ms=100,trace=str(trace.relative_to(ROOT)),trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest())
 assert result['feedback']['p95_ms']<=100,result['feedback'];session.detach()

def cleanup(f,p,result):
 result['samples']=[];session=p.context.new_cdp_session(p);session.send('Performance.enable')
 def sample(i):
  session.send('HeapProfiler.collectGarbage');session.send('HeapProfiler.collectGarbage');dom=session.send('Memory.getDOMCounters');metrics={x['name']:x['value'] for x in session.send('Performance.getMetrics')['metrics']};result['samples'].append(dict(cycle=i,**dom,heap_bytes=metrics['JSHeapUsedSize'],connected_elements=p.evaluate('document.querySelectorAll("*").length'),canvas=p.locator('canvas').count(),series=f.read(p,'chart.panes().map(x=>x.getSeries().length)'),sockets=p.evaluate('window.__qaSockets'),server_connections=dict(f.counts)))
 def cycle():
  # Use stable pressed-state controls, not implementation state writes.
  for which in ('EMA','RSI','MACD'):
   t=p.get_by_label('Göstergeler',exact=True)
   if t.locator('..').get_attribute('open') is None:t.click()
   btn=t.locator('..').get_by_label('MACD göstergesi',exact=True) if which=='MACD' else t.locator('..').get_by_role('button',include_hidden=True).filter(has_text=which).first
   
   with p.expect_response(lambda r:r.request.method=='PUT' and '/indicators' in r.url):btn.click()
   expect(btn).to_have_attribute('aria-pressed','true');p.wait_for_timeout(65)
   if t.locator('..').get_attribute('open') is not None:t.click()
  assert sum(f.read(p,'chart.panes().map(x=>x.getSeries().length)'))==8
  p.get_by_label('Sözleşme seç',exact=True).select_option('ETHUSDT');f.ready(p,'ETHUSDT');p.get_by_label('Sözleşme seç',exact=True).select_option('BTCUSDT');f.ready(p)
  for which in ('MACD','RSI','EMA'):
   t=p.get_by_label('Göstergeler',exact=True)
   if t.locator('..').get_attribute('open') is None:t.click()
   btn=t.locator('..').get_by_label('MACD göstergesi',exact=True) if which=='MACD' else t.locator('..').get_by_role('button',include_hidden=True).filter(has_text=which).first
   
   with p.expect_response(lambda r:r.request.method=='PUT' and '/indicators' in r.url):btn.click()
   expect(btn).to_have_attribute('aria-pressed','false');p.wait_for_timeout(65)
   if t.locator('..').get_attribute('open') is not None:t.click()
  menu(p,'Paneller','Kuru çalışma sonuçları');expect(p.get_by_role('dialog')).to_be_visible();p.get_by_role('button',name='Kuru çalışma sonuçlarını kapat',exact=True).click()
  p.get_by_label('Açık temaya geç',exact=True).click();p.get_by_label('Koyu temaya geç',exact=True).click();p.wait_for_timeout(150)
  
  for _ in range(30):
   if f.read(p,'chart.panes().map(x=>x.getSeries().length)')==[1,1]:break
   p.wait_for_timeout(50)
  assert f.read(p,'chart.panes().map(x=>x.getSeries().length)')==[1,1],dict(panes=f.read(p,'chart.panes().map(x=>x.getSeries().length)'),config=f.api('/api/workspaces/main/indicators?format_version=4'))
  for _ in range(20):
   if f.counts['active']==1 and p.evaluate('window.__qaSockets.active')==1:break
   p.wait_for_timeout(50)
 for _ in range(2):cycle()
 sample(0)
 for i in range(20):cycle();sample(i+1);print('cleanup '+str(i+1),flush=True)
 baseline=result['samples'][0]
 for s in result['samples']:
  assert s['canvas']==baseline['canvas'] and s['series']==[1,1] and s['sockets']['active']==s['server_connections']['active']==1,s
  assert s['connected_elements']==baseline['connected_elements'] and s['jsEventListeners']<=baseline['jsEventListeners']+10,s
  assert s['nodes']<=baseline['nodes']+256,s
 growth=result['samples'][-1]['heap_bytes']-baseline['heap_bytes'];result['heap_screening']=dict(growth_bytes=growth,budget_bytes=max(2097152,baseline['heap_bytes']*.1),scope='20 post-warmup cycles, not unlimited-session no-leak proof');assert growth<=result['heap_screening']['budget_bytes']
 p.goto('about:blank')
 for _ in range(40):
  if f.counts['active']==0:break
  p.wait_for_timeout(50)
 assert f.counts['active']==0;result['all_native_sockets_closed']=True;session.detach()

def raster(f,p,result):
 result['matrix']=[];out=ROOT/'reports/qa01-raster-20261113';out.mkdir(exist_ok=True);session=p.context.new_cdp_session(p)
 def error(img,x,y,dpr,predicate,axis='y'):
  best=999
  for yy in range(max(0,int(y*dpr)-4),min(img.height,int(y*dpr)+5)):
   for xx in range(max(0,int(x*dpr)-4),min(img.width,int(x*dpr)+5)):
    if predicate(img.getpixel((xx,yy))):best=min(best,abs((yy+.5)/dpr-y) if axis=='y' else abs((xx+.5)/dpr-x))
  return best
 def purple(rgb):r,g,b=rgb[:3];return b-r>25 and r-g>25
 def green(rgb):r,g,b=rgb[:3];return g-r>25 and g-b>4
 for w in (1536,1280,1024):
  for dpr in (1,1.25,2):
   session.send('Emulation.setDeviceMetricsOverride',dict(width=w,height=900,deviceScaleFactor=dpr,mobile=False))
   for theme in ('dark','light'):
    if p.locator('.terminal').get_attribute('data-theme')!=theme:p.get_by_label('Açık temaya geç' if theme=='light' else 'Koyu temaya geç',exact=True).click()
    f.pin_view(p);p.wait_for_timeout(100);assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert p.evaluate('document.documentElement.style.colorScheme')==theme;assert p.locator('meta[name="theme-color"]').get_attribute('content')==('#ffffff' if theme=='light' else '#11151c')
    box=p.locator('.chart-stage').bounding_box();pane=f.read(p,'chart.paneSize(0)');raw=base64.b64decode(session.send('Page.captureScreenshot',dict(format='png',clip={**box,'scale':1}))['data']);img=Image.open(io.BytesIO(raw)).convert('RGB');scale=img.width/box['width'];assert abs(scale-dpr)<.01,(scale,dpr);y=f.read(p,'series.priceToCoordinate(147.75)');probes=[]
    for fraction in (.22,.43,.65,.82):probes.append(error(img,pane['width']*fraction,y,scale,purple))
    assert max(probes)<=1,(w,dpr,theme,probes)
    assert error(img,pane['width']*.43,y+4,scale,purple)>1
    p.locator('.drawings-overlay').evaluate('(e)=>{e.style.visibility="hidden"}');p.wait_for_timeout(50);native_raw=base64.b64decode(session.send('Page.captureScreenshot',dict(format='png',clip={**box,'scale':1}))['data']);native_img=Image.open(io.BytesIO(native_raw)).convert('RGB');p.locator('.drawings-overlay').evaluate('(e)=>{e.style.visibility=""}');p.wait_for_timeout(50)
    r=f.rows[925];x=f.read(p,'chart.timeScale().timeToCoordinate('+str(r['time'])+')')
    for field in ('high','low'):
     yy=f.read(p,'series.priceToCoordinate('+str(r[field])+')');probes.append(error(native_img,x,yy,scale,green))
    
    if max(probes)>1:
     debug=out/'failed-native-probe.png';debug.write_bytes(raw);raise AssertionError(dict(width=w,dpr=dpr,theme=theme,probes=probes,box=box,png=[img.width,img.height],x=x,expected_y=[f.read(p,'series.priceToCoordinate('+str(r[k])+')') for k in ('high','low')],source=r,native=f.read(p,'series.data().find(x=>x.time=='+str(r['time'])+')')))
    path=out/(str(w)+'-'+str(dpr)+'-'+theme+'.png');path.write_bytes(raw);path.with_stem(path.stem+'-native').write_bytes(native_raw);result['matrix'].append(dict(width=w,dpr=dpr,theme=theme,probes=len(probes),max_error_css_px=max(probes),negative4px_rejected=True,path=str(path.relative_to(ROOT)).replace('\\','/')))
 session.send('Emulation.clearDeviceMetricsOverride');session.detach()

def functional(f,p,result):
 checks=result.setdefault('checks',[])
 def record(name,**kw):checks.append(dict(name=name,passed=True,**kw))
 f.pin_view(p);surface=p.get_by_role('region',name='Fiyat grafiği',exact=True);surface.focus();before=f.read(p,'chart.timeScale().getVisibleLogicalRange()');p.keyboard.press('+');p.wait_for_timeout(60);zoom=f.read(p,'chart.timeScale().getVisibleLogicalRange()');assert zoom['to']-zoom['from']<before['to']-before['from'];p.keyboard.press('-');p.wait_for_timeout(80);p.keyboard.press('ArrowLeft');p.wait_for_timeout(60);assert f.read(p,'chart.timeScale().getVisibleLogicalRange()')['from']<before['from'];p.keyboard.press('End');record('keyboard_zoom_pan_latest_and_visible_focus')
 assert p.evaluate('getComputedStyle(document.activeElement).outlineStyle')!='none'
 search=p.get_by_label('Coin ara',exact=True);search.focus();before=f.read(p,'chart.timeScale().getVisibleLogicalRange()');p.keyboard.press('ArrowLeft');p.keyboard.press('End');assert f.read(p,'chart.timeScale().getVisibleLogicalRange()')==before;record('text_input_keys_are_isolated_from_chart')
 p.locator('.skip-link').focus();p.keyboard.press('Enter');assert p.evaluate('document.activeElement.id')=='chart-main';record('skip_link_and_main_focus')
 p.get_by_label('Grafiği tam ekran aç',exact=True).click();p.wait_for_function('document.fullscreenElement!==null');p.get_by_label('Tam ekrandan çık',exact=True).click();p.wait_for_function('document.fullscreenElement===null');record('fullscreen_enter_exit_browser_api_not_physical_acceptance')
 f.pin_view(p);d=f.trend;d_id=d['drawing_id'];p.locator('[data-drawing="'+d_id+'"]').press('Enter');p.wait_for_timeout(100);saved=f.api('/api/drawings/'+d_id+'?format_version=8');native=f.read(p,'chart.options().handleScroll');before_events=f.api('/api/workspaces/main/local-events')
 for mode in ('escape','pointercancel','lostcapture','blur','hidden'):
  handle=p.locator('[data-drawing-handles="'+d_id+'"] [data-anchor="0"]');b=handle.bounding_box();x=b['x']+b['width']/2;y=b['y']+b['height']/2;p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+18,y-8,steps=4);assert f.read(p,'chart.options().handleScroll')!=native
  if mode=='escape':p.keyboard.press('Escape')
  elif mode=='pointercancel':handle.locator('..').evaluate('(e)=>e.dispatchEvent(new PointerEvent("pointercancel",{pointerId:1,bubbles:true,isPrimary:true}))')
  elif mode=='lostcapture':handle.locator('..').evaluate('(e)=>{if(e.hasPointerCapture(1))e.releasePointerCapture(1)}')
  elif mode=='blur':p.evaluate('window.dispatchEvent(new Event("blur"))')
  else:p.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:true});document.dispatchEvent(new Event("visibilitychange"));delete document.hidden;')
  p.mouse.up();p.wait_for_timeout(90);assert f.read(p,'chart.options().handleScroll')==native,mode;assert f.api('/api/drawings/'+d_id+'?format_version=8')==saved;assert f.api('/api/workspaces/main/local-events')==before_events;record('uncommitted_'+mode+'_clears_preview_and_lock_without_persistence_or_event')
 # A real gesture must still commit and undo after all interruption paths.
 handle=p.locator('[data-drawing-handles="'+d_id+'"] [data-anchor="0"]');b=handle.bounding_box();p.mouse.move(b['x']+5,b['y']+5);p.mouse.down();p.mouse.move(b['x']+23,b['y']-3,steps=4);p.mouse.up();p.wait_for_timeout(220);current=f.api('/api/drawings/'+d_id+'?format_version=8');assert current['revision']==saved['revision']+1;p.get_by_label('Çizimleri göster veya gizle',exact=True).click();p.get_by_label('Çizim değişikliğini geri al',exact=True).click();p.wait_for_timeout(220);assert f.api('/api/drawings/'+d_id+'?format_version=8')['geometry']==saved['geometry'];record('next_real_gesture_commits_then_undo_restores_geometry')
 menu(p,'Paneller','Kuru çalışma sonuçları');dialog=p.get_by_role('dialog');expect(dialog).to_be_visible();p.get_by_role('button',name='Kuru çalışma sonuçlarını kapat',exact=True).focus()
 count=0
 for _ in range(48):
  p.keyboard.press('Tab');box=p.evaluate('(()=>{const e=document.activeElement,b=e.getBoundingClientRect(),f=document.querySelector("dialog footer").getBoundingClientRect();return {tag:e.tagName,inside:!!e.closest("dialog"),top:b.top,bottom:b.bottom,footer:f.top,isFooter:!!e.closest("footer")}})()');assert box['inside'] or box['tag']=='BODY',box
  if box['inside'] and box['tag']!='DIALOG':assert box['isFooter'] or box['bottom']<=box['footer']+1,box
  else:assert p.evaluate('document.querySelector("dialog").matches(":modal")')
  count+=1
 p.keyboard.press('Escape');p.wait_for_timeout(80);assert p.get_by_role('dialog').count()==0;record('dialog_focus_trap_no_sticky_footer_occlusion_and_escape',tabs=count)
 result['physical_limit']='Pointercancel/hidden/blur dispatched synthetically; lost capture is browser generated; no physical trackpad/touch or screen-reader claim'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--section',choices=['functional','raster','cleanup','performance'],required=True);ap.add_argument('--seconds',type=int,choices=[10,60],default=60);args=ap.parse_args();result=dict(task='QA01',section=args.section,mode='CALIBRATION' if args.section=='performance' and args.seconds!=60 else 'ACCEPTANCE',passed=False,page_errors=[],unexpected_requests=[]);f=Fixture()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True);p=browser.new_page(viewport={'width':1536,'height':900});p.set_default_timeout(7000);f.setup(p,result);result.update(browser=browser.version,platform=platform.platform(),cpus=os.cpu_count(),fixture=f.evidence(),assets={str(x.relative_to(ROOT/'agentrader/web_assets')):hashlib.sha256(x.read_bytes()).hexdigest() for x in (ROOT/'agentrader/web_assets').rglob('*') if x.is_file()})
   globals()[args.section](f,p,result,**({'seconds':args.seconds} if args.section=='performance' else {}));assert not result['page_errors'] and not result['unexpected_requests'] and not result.get('console_errors');result['passed']=True;browser.close()
 except Exception:result['error']=traceback.format_exc()
 finally:f.close()
 (ROOT/('reports/chart-qa01-'+args.section+('-calibration' if args.section=='performance' and args.seconds!=60 else '')+'-20261113.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ('runs','samples','matrix','assets')},ensure_ascii=True,indent=2));return 0 if result['passed'] else 1

if __name__=='__main__':sys.exit(main())
