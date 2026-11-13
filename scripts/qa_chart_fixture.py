"""Current production App with isolated SQLite and real loopback WebSockets."""
import hashlib,json,math,os,socket,subprocess,sys,tempfile,threading,time
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from urllib.request import Request,build_opener,ProxyHandler
from websockets.sync.server import serve
from websockets.exceptions import ConnectionClosed
from measure_chart_interactions import INSPECT,ROOT
from playwright.sync_api import expect
from agentrader.migrations import migrate
from agentrader.drawings.service import DrawingService,management

class Fixture:
 def __init__(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='chart-qa01-');self.folder=Path(self.tmp.name);self.db=self.folder/'app.db';migrate(self.db)
  self.markets=[dict(symbol=s,base_asset=s[:-4],quote_asset='USDT',contract_type='PERPETUAL',tick_size='0.25') for s in ('BTCUSDT','ETHUSDT')]
  self.rows=[]
  for i in range(1001):
   t=1800000000+i*900;o=100+i*.02+math.sin(i*.13)*3;c=o+1
   r=dict(time=t,open=o,high=c+1,low=o-1,close=c,volume=10+i%20,quote_volume=(10+i%20)*c,close_time=(t+900)*1000-1,closed=i<1000)
   r['exact']=dict(schema='chart-exact-decimal/1',state='VERIFIED',provenance='UPSTREAM_DECIMAL_TEXT',**{k:str(r[k]) for k in ('open','high','low','close','volume','quote_volume')});self.rows.append(r)
  kinds=['horizontal','trend','zone','fibonacci','horizontal_ray','ray','extended_line','fibonacci_extension','parallel_channel','long_plan','short_plan','ruler','text','price_label']
  self.items={};self.reference=None;self.trend=None
  service=DrawingService(self.db,'qa01')
  for symbol in ('BTCUSDT','ETHUSDT'):
   self.items[symbol]=[]
   for i in range(200 if symbol=='BTCUSDT' else 0):
    kind=kinds[i%len(kinds)];a=dict(time=self.rows[930+i%25]['time'],price=str(100+i%16));b=dict(time=self.rows[990+i%8]['time'],price=str(114+i%16));g=dict(kind=kind,symbol=symbol,price_source='LAST_PRICE',label='QA-'+str(i),anchors=[a] if kind in ('horizontal','horizontal_ray','text','price_label') else [a,b])
    if kind in ('ray','extended_line','horizontal_ray'):g['schema']='chart-line/1'
    if kind in ('fibonacci','fibonacci_extension'):g.update(schema='chart-fibonacci/1',time_scope='unbounded',levels=['0','0.382','0.618','1','1.618'])
    if kind=='parallel_channel':g.update(schema='chart-channel/1',anchors=[a,b,dict(time=self.rows[975]['time'],price='140')])
    if kind in ('long_plan','short_plan'):g.update(schema='chart-position/1',params=dict(risk_budget=None,fee_bps='4',slippage_bps='2'),anchors=[dict(time=a['time'],price='110'),dict(time=b['time'],price='100' if kind=='long_plan' else '120'),dict(time=b['time'],price='120' if kind=='long_plan' else '100')])
    if kind=='ruler':g['schema']='chart-ruler/1'
    if kind in ('text','price_label'):g.update(schema='chart-annotation/1',text='Uzun açıklama '+str(i))
    if i==0:g['anchors'][0]['price']='147.75';g['label']='Raster referansı'
    d=service.create('main',symbol+'-'+str(i),g);self.items[symbol].append(d)
    if symbol=='BTCUSDT' and i==0:self.reference=d
    if symbol=='BTCUSDT' and i==1:self.trend=d
  d=self.reference;service.operations('main','ref-color',[dict(drawing_id=d['drawing_id'],expected_revision=1,geometry=d['geometry'],management={**management(),'color':'#9b6ed6'},deleted=False)])
  self.reference=service.show(d['drawing_id'])
  self.counts=dict(opened=0,closed=0,active=0);self.lock=threading.RLock();self.receipts=[];self.packet_provider=None;self.pause_stream=threading.Event()
  def handler(ws):
   with self.lock:self.counts['opened']+=1;self.counts['active']+=1;gen=self.counts['opened']
   try:
    q=parse_qs(urlparse(ws.request.path).query);symbol=q['symbol'][0];interval=q['interval'][0]
    initial=self.packet_provider(symbol,interval,gen,True) if self.packet_provider else dict(type='snapshot',symbol=symbol,interval=interval,generation=gen,sequence=1,status='LIVE',received_at=int(time.time()*1000),candles=self.rows,market=next(m for m in self.markets if m['symbol']==symbol),quality={'state':'OK','missing_bars':0})
    ws.send(json.dumps(initial))
    while True:
     try:ws.recv(timeout=.5)
     except TimeoutError:pass
     if not self.pause_stream.is_set():
      packet=self.packet_provider(symbol,interval,gen,False) if self.packet_provider else dict(type='update',symbol=symbol,interval=interval,generation=gen,sequence=1,status='LIVE',received_at=int(time.time()*1000))
      ws.send(json.dumps(packet))
   except (ConnectionClosed,OSError):pass
   finally:
    with self.lock:self.counts['closed']+=1;self.counts['active']-=1
  self.ws_server=serve(handler,'127.0.0.1',0,compression=None);self.ws_port=self.ws_server.socket.getsockname()[1]
  self.ws_thread=threading.Thread(target=self.ws_server.serve_forever,daemon=True);self.ws_thread.start()
  with socket.socket() as s:s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
  self.base=f'http://127.0.0.1:{self.port}';self.opener=build_opener(ProxyHandler({}))
  env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(self.db),AGENTRADER_EXECUTION_DATABASE=str(self.folder/'execution.db'),AGENTRADER_CHART_DATABASE=str(self.folder/'market.db'),AGENTRADER_WEB_TOKEN='')
  # Owner is selected in the child app, without touching the user's environment/stores.
  child="from agentrader.api.app import create_app;from agentrader.application.settings import WebSettings;import uvicorn,sys;from pathlib import Path;p=Path(sys.argv[1]);s=WebSettings(application_database=p/'app.db',execution_database=p/'execution.db',market_database=p/'market.db',owner='qa01');uvicorn.run(create_app(s),host='127.0.0.1',port=int(sys.argv[2]),log_level='error')"
  self.server=subprocess.Popen([sys.executable,'-c',child,str(self.folder),str(self.port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
  for _ in range(100):
   try:self.api('/api/health');break
   except Exception:time.sleep(.1)
  else:raise AssertionError('QA server unavailable')
 def api(self,path,body=None,method=None):
  req=Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,method=method or ('PUT' if body else 'GET'),headers={'Content-Type':'application/json'})
  with self.opener.open(req,timeout=5) as r:return json.load(r)
 def setup(self,page,result,diagnostics=False,wait=True):
  page.on('pageerror',lambda e:result['page_errors'].append(str(e)))
  result.setdefault('console_errors',[]);page.on('console',lambda m:result['console_errors'].append(dict(text=m.text,location=m.location)) if m.type=='error' else None)
  def guard(route):
   u=route.request.url
   if not u.startswith(self.base+'/') or any(x in u for x in ('/api/account','/api/orders','/api/commands','/api/execution')):result['unexpected_requests'].append(u);route.abort()
   else:route.continue_()
  page.route('**/*',guard);page.route('**/api/markets',lambda r:r.fulfill(json={'markets':self.markets}));page.route('**/api/candles*',lambda r:r.fulfill(json={'candles':[],'has_more':False}))
  page.add_init_script("""(()=>{const Native=window.WebSocket;const counts={opened:0,closed:0,active:0};window.__qaSockets=counts;window.WebSocket=new Proxy(Native,{construct(target,args){const u=new URL(args[0]);if(u.pathname==='/api/market-stream'){u.port='PORT';args[0]=u.href;}const ws=Reflect.construct(target,args);counts.opened++;counts.active++;ws.addEventListener('close',()=>{counts.closed++;counts.active--;},{once:true});return ws;}});})()""".replace('PORT',str(self.ws_port)))
  page.goto(self.base+('/?diagnostics=1' if diagnostics else '/'))
  if wait:self.ready(page)
 def read(self,page,expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');'+'}')
 def ready(self,page,symbol='BTCUSDT'):
  expect(page.get_by_text('1001 mum',exact=True)).to_be_visible();page.wait_for_function("s=>document.querySelector('.shell-instrument')?.textContent.includes(s)",arg=symbol[:-4]);
  if symbol=='BTCUSDT':expect(page.locator('[data-drawing]').nth(199)).to_be_visible()
  page.wait_for_timeout(100)
  assert self.read(page,'view.candles.length')==1001 and page.locator('[data-drawing]').count()==(200 if symbol=='BTCUSDT' else 0)
 def pin_view(self,page):
  self.read(page,'chart.timeScale().setVisibleLogicalRange({from:920,to:1006})');self.read(page,'series.priceScale().setVisibleRange({from:90,to:155})');page.wait_for_timeout(150)
 def evidence(self):return dict(candles=1001,closed_candles=1000,open_candles=1,drawings=200,kinds=sorted({d['geometry']['kind'] for d in self.items['BTCUSDT']}),sha256=hashlib.sha256(json.dumps(dict(rows=self.rows,geometries=[d['geometry'] for d in self.items['BTCUSDT']]),sort_keys=True).encode()).hexdigest(),scope='Projection/display fixture; real loopback WebSocket, no market eligibility claim')
 def close(self):
  self.server.terminate();self.server.wait(timeout=10);self.ws_server.shutdown();self.ws_thread.join(timeout=3);self.tmp.cleanup()
