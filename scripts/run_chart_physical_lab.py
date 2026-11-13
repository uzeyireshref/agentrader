"""CL04 isolated native-wheel lab; synthetic market and temporary drawing stores."""
import json,os,re,socket,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fastapi import Request
from fastapi.responses import HTMLResponse, Response
import uvicorn
from agentrader.api.app import create_app
from agentrader.application.settings import WebSettings
from agentrader.application.service import ApplicationService
from agentrader.drawings.service import DrawingService
from measure_chart_interactions import INSPECT

def main():
 with tempfile.TemporaryDirectory(prefix='agentrader-physical-') as folder:
  p=Path(folder);settings=WebSettings(p/'app.db',p/'execution.db',market_database=p/'market.db');ApplicationService(settings).initialize()
  rows=[{'time':1800000000+i*900,'open':100+i*.1,'high':110+i*.1,'low':90+i*.1,'close':105+i*.1,'volume':10+i,'quote_volume':1000,'close_time':(1800000000+(i+1)*900)*1000-1,'closed':i<299} for i in range(300)]
  info={'symbol':'BTCUSDT','base_asset':'BTC','quote_asset':'USDT','contract_type':'PERPETUAL','tick_size':'0.1'}
  class Market:
   def catalog(self):return {'markets':[info]}
   def history(self,*args,**kw):return {'candles':[] if kw.get('end_time') else rows,'has_more':False,'quality':{'state':'OK','missing_bars':0},'market':info}
  class State:
   def packet(self,generation):
    packet={'type':'snapshot' if generation!=1 else 'update','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'quality':{'state':'OK','missing_bars':0},'market':info}
    if packet['type']=='snapshot':packet['candles']=rows
    return packet
  class Feed:state=State()
  class Hub:
   def acquire(self,*args):return Feed()
   def release(self,*args):pass
   def close(self):pass
  service=DrawingService(settings.application_database,settings.owner)
  for kind in ['horizontal','zone','trend','fibonacci']:
   anchors=[{'time':rows[240]['time'],'price':'129.0'}]
   if kind!='horizontal':anchors.append({'time':rows[260]['time'],'price':'134.0'})
   service.create('main','fixture_'+kind,{'kind':kind,'symbol':'BTCUSDT','price_source':'LAST_PRICE','anchors':anchors,'label':'TEST '+kind})
  app=create_app(settings,market=Market(),hub=Hub());app.router.routes=[r for r in app.router.routes if getattr(r,'path',None)!='/']
  native=INSPECT[:INSPECT.index('return view?')]+"return {chart,series,view};}"
  script=r"""
const native=NATIVE;
let active=null,timer=null;
function observe(){const n=native();if(!n?.chart)return null;return {bundle:document.querySelector('script[type=module]')?.getAttribute('src'),range:n.chart.timeScale().getVisibleLogicalRange(),bar_spacing:n.chart.timeScale().options().barSpacing,distance_20_bars:n.chart.timeScale().timeToCoordinate(1800234000)-n.chart.timeScale().timeToCoordinate(1800216000),dpr:devicePixelRatio,width:innerWidth,height:innerHeight,screen_width:screen.width,screen_height:screen.height,fullscreen:!!document.fullscreenElement,status:n.view.status};}
window.beginPhysical=function(kind){const n=native();if(!n?.view.candles.length)return;clearTimeout(timer);n.chart.timeScale().setVisibleLogicalRange({from:200,to:280});n.series.priceScale().applyOptions({autoScale:true});active=null;document.getElementById('lab-status').textContent='Ölçek hazırlanıyor…';requestAnimationFrame(()=>requestAnimationFrame(()=>{active={kind,started_at:new Date().toISOString(),before:observe(),events:[]};document.getElementById('lab-status').textContent=kind+' hazır: imleci grafiğin orta kısmına getirip tek kısa hareket yap.';}));};
window.finishPhysical=async function(){if(!active)return;const data=active;active=null;data.after=observe();data.trusted_events=data.events.filter(e=>e.trusted).length;const forward=data.events.filter(e=>!e.trusted&&e.type==='wheel');data.forwarded_axes=[...new Set(forward.map(e=>Math.abs(e.dx)>0?'horizontal':Math.abs(e.dy)>0?'vertical':'zero'))];data.spacing_change_percent=100*(data.after.bar_spacing/data.before.bar_spacing-1);const trusted=data.events.filter(e=>e.trusted);data.ctrl_seen=trusted.some(e=>e.ctrl);data.native_total_dx=trusted.reduce((v,e)=>v+Math.abs(e.dx),0);data.native_total_dy=trusted.reduce((v,e)=>v+Math.abs(e.dy),0);data.user_physical_source=window.__labHarness?'AUTOMATED_HARNESS_NOT_PHYSICAL':'PENDING_USER_ATTESTATION';data.harness_smoke=!!window.__labHarness;const r=await fetch('/lab/trace',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const body=await r.json();document.getElementById('lab-status').textContent=data.kind+' kaydedildi ('+data.trusted_events+' tarayıcı olayı). Sıradaki düğmeye geçebilirsin. Kayıt: '+body.name;};
window.addEventListener('wheel',e=>{if(!active||!e.target?.closest?.('.chart-stage'))return;if(active.events.length<1000)active.events.push({type:'wheel',t:performance.now(),trusted:e.isTrusted,dx:e.deltaX,dy:e.deltaY,mode:e.deltaMode,ctrl:e.ctrlKey,shift:e.shiftKey,clientX:e.clientX,clientY:e.clientY});if(e.isTrusted){clearTimeout(timer);timer=setTimeout(()=>window.finishPhysical(),1000);}}, {capture:true,passive:true});
""".replace('NATIVE',native)
  banner="""<aside style="position:sticky;top:0;z-index:1000;padding:10px;background:#233133;color:white;font:13px Arial"><b>CL04 TEST - Sentetik veri; kişisel çizimleriniz etkilenmez</b><div style="display:flex;gap:8px;margin-top:8px"><button onclick="beginPhysical('horizontal')">1 Yatay</button><button onclick="beginPhysical('diagonal')">2 Çapraz</button><button onclick="beginPhysical('pinch')">3 Pinch</button><button onclick="finishPhysical()">Kaydı bitir</button><button onclick="beginPhysical('vertical')">4 Dikey</button></div><p id="lab-status">Her düğmeden sonra grafiğin ortasında tek kısa hareket yap. Parmağını kaldırınca kayıt otomatik tamamlanır.</p></aside>"""
  @app.get('/')
  def index():
   html=(settings.frontend_directory/'index.html').read_text(encoding='utf-8').replace('<title>','<title>CL04 TEST - ').replace('<body>','<body>'+banner)
   return HTMLResponse(html.replace('</body>','<script>'+script+'</script><script src="/lab/acceptance.js"></script></body>'))
  @app.get('/lab/acceptance.js')
  def acceptance_js():return Response((ROOT/'scripts/b5_acceptance_lab.js').read_text(encoding='utf-8'),media_type='text/javascript')
  @app.post('/lab/acceptance-trace')
  async def acceptance_trace(request:Request):
   raw=await request.body();assert len(raw)<=2000000
   data=json.loads(raw);assert isinstance(data.get('events'),list)
   folder=ROOT/'reports/chart-b5-final-20261110';folder.mkdir(exist_ok=True)
   name=('smoke-' if data.get('harness_smoke') else '')+'acceptance-'+str(time.time_ns())+'.json'
   (folder/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return {'saved':True,'name':name}
  @app.get('/lab/gesture-control')
  def gesture_control():
   return HTMLResponse("""<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>B5 - Grafik olmadan hareket kontrolü</title>
<style>body{background:#142022;color:#edf3f1;font:17px system-ui;padding:24px}button{padding:12px;font:inherit}#pad{margin-top:20px;width:min(90vw,1000px);height:320px;overflow:auto;border:3px solid #bba566;overscroll-behavior:contain}#content{width:3200px;height:900px;background:repeating-linear-gradient(90deg,#233738 0px,#233738 99px,#78908d 100px);padding:24px;box-sizing:border-box}pre{white-space:pre-wrap}</style>
<h1>Grafiksiz yatay hareket kontrolü</h1><p>Ctrl tuşuna basmadan, iki parmağını aynı yönde sağa veya sola kaydır. Parmaklarını açıp kapatma.</p>
<button id="start">Kaydı başlat</button> <button id="finish">Kaydı bitir</button><p id="status">Bu sayfada grafik kütüphanesi yok. Yalnız tarayıcının aldığı olaylar kaydedilir.</p>
<div id="pad" tabindex="0" aria-label="Yatay kaydırma test alanı"><div id="content">Hareketi bu alanın ortasında yap →</div></div><pre id="result"></pre>
<script>
let recording=null,timer=null,ctrlDown=false;const pad=document.getElementById('pad');
window.addEventListener('keydown',e=>{if(e.key==='Control')ctrlDown=true;});window.addEventListener('keyup',e=>{if(e.key==='Control')ctrlDown=false;});window.addEventListener('blur',()=>ctrlDown=false);
document.getElementById('start').onclick=()=>{clearTimeout(timer);pad.scrollLeft=500;pad.scrollTop=200;recording={context:'NO_CHART_NATIVE_SCROLL_CONTROL',started_at:new Date().toISOString(),before:{left:pad.scrollLeft,top:pad.scrollTop,dpr:devicePixelRatio,width:innerWidth,height:innerHeight},events:[]};document.getElementById('status').textContent='Hazır: çerçeveli alanda tek kısa yatay hareket yap.';};
async function finish(){if(!recording)return;clearTimeout(timer);const data=recording;recording=null;data.after={left:pad.scrollLeft,top:pad.scrollTop,dpr:devicePixelRatio,width:innerWidth,height:innerHeight};data.harness_smoke=!!window.__labHarness;const r=await fetch('/lab/control-trace',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!r.ok){document.getElementById('status').textContent='Kayıt başarısız';return;}const result=await r.json();document.getElementById('status').textContent='Kaydedildi: '+result.name;document.getElementById('result').textContent=JSON.stringify({events:data.events.length,ctrlEvents:data.events.filter(e=>e.ctrl).length,totalDx:data.events.reduce((n,e)=>n+Math.abs(e.dx),0),totalDy:data.events.reduce((n,e)=>n+Math.abs(e.dy),0),before:data.before,after:data.after},null,2);}
document.getElementById('finish').onclick=finish;
pad.addEventListener('wheel',e=>{if(!recording)return;if(recording.events.length<1000)recording.events.push({trusted:e.isTrusted,dx:e.deltaX,dy:e.deltaY,mode:e.deltaMode,ctrl:e.ctrlKey,control_key_observed_down:ctrlDown,t:performance.now()});clearTimeout(timer);timer=setTimeout(finish,1500);},{passive:true});
</script></html>""")
  @app.post('/lab/control-trace')
  async def control_trace(request:Request):
   raw=await request.body();assert len(raw)<=512000
   data=json.loads(raw);assert data.get('context')=='NO_CHART_NATIVE_SCROLL_CONTROL'
   folder=ROOT/'reports/chart-physical-control-20261110';folder.mkdir(exist_ok=True)
   name=('smoke-' if data.get('harness_smoke') else '')+'native-'+str(time.time_ns())+'.json'
   (folder/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return {'saved':True,'name':name}
  trace_dir=ROOT/'reports/chart-physical-20261110';trace_dir.mkdir(exist_ok=True)
  @app.post('/lab/trace')
  async def trace(request:Request):
   raw=await request.body();assert len(raw)<=512000
   data=json.loads(raw);assert data.get('kind') in ['horizontal','diagonal','pinch','vertical']
   name=('smoke-' if data.get('harness_smoke') else '')+data['kind']+'-'+str(time.time_ns())+'.json';(trace_dir/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return {'saved':True,'name':name}
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  bundle=re.search(r'index-[^"/]+\.js',(settings.frontend_directory/'index.html').read_text(encoding='utf-8')).group()
  ready={'task':'CL04','status':'READY_FOR_PHYSICAL_INPUT','url':'http://127.0.0.1:'+str(port)+'/?diagnostics=1','pid':os.getpid(),'bundle':bundle,'trace_directory':str(trace_dir),'synthetic_data':True,'user_workspace_writes':0,'browser_access_host':'UNAVAILABLE','physical_touchscreen':'UNAVAILABLE_PER_PRIOR_USER_REPORT'}
  (ROOT/'reports/chart-physical-lab-20261110.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  uvicorn.run(app,host='127.0.0.1',port=port,access_log=False)

if __name__=='__main__':main()
