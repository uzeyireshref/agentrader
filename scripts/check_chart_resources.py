"""D3: post-GC resource counts over warmup + 10 market/indicator cycles."""
import hashlib
import json
import time
import threading
from websockets.sync.server import serve
from websockets.exceptions import ConnectionClosed
from urllib.parse import parse_qs,urlparse
from measure_chart_interactions import main,INSPECT,ROOT

TRACK="""(()=>{const Native=window.WebSocket;const counts={created:0,closed:0,active:0};window.__resourceSockets=counts;window.WebSocket=new Proxy(Native,{construct(target,args){const url=new URL(args[0]);if(url.pathname==='/api/market-stream'){url.hostname='127.0.0.1';url.port='RESOURCE_PORT';url.pathname='/resource-stream';args[0]=url.href;}const ws=Reflect.construct(target,args);counts.created++;counts.active++;ws.addEventListener('close',()=>{counts.closed++;counts.active--;},{once:true});return ws;}});})()"""


def checks(page,sockets,unused,result):
    result.update(date='2026-11-10',task='D3',samples=[],indicator_checks=[])
    def read(expr):
        value=page.evaluate('()=>window.__resourceRead()')
        return value[{'view.symbol':'symbol','view.interval':'interval','view.candles.length':'candles','chart.panes().map(p=>p.getSeries().length)':'series'}[expr]]
    markets=[{'symbol':s,'base_asset':s[:-4],'quote_asset':'USDT','tick_size':'0.1','contract_type':'PERPETUAL'} for s in ['BTCUSDT','ETHUSDT']]
    rows=[{'time':1800000000+i*3600,'open':100+i*.1,'high':110+i*.1,'low':90+i*.1,'close':105+i*.1,'volume':10+i,'quote_volume':1000,'close_time':(1800000000+(i+1)*3600)*1000-1,'closed':i<3999} for i in range(4000)]
    def drawings(symbol):return [{'drawing_id':symbol+'-'+str(i),'workspace_id':'main','revision':1,'deleted':False,'updated_at':0,'geometry':{'kind':'horizontal','symbol':symbol,'price_source':'LAST_PRICE','label':'R'+str(i),'anchors':[{'time':rows[3950]['time'],'price':str(480+i*.1)}]}} for i in range(200)]
    page.route('**/api/markets',lambda r:r.fulfill(json={'markets':markets}))
    page.route('**/api/workspaces/main/drawings*',lambda r:r.fulfill(json={'drawings':drawings(parse_qs(urlparse(r.request.url).query)['symbol'][0])}))
    server_counts={'opened':0,'closed':0,'active':0};lock=threading.Lock()
    def handler(ws):
        with lock:server_counts['opened']+=1;server_counts['active']+=1
        try:
            query=parse_qs(urlparse(ws.request.path).query);symbol=query['symbol'][0];interval=query['interval'][0]
            ws.send(json.dumps({'type':'snapshot','symbol':symbol,'interval':interval,'generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'candles':rows,'market':next(m for m in markets if m['symbol']==symbol)}))
            for _ in ws:pass
        except ConnectionClosed:pass
        finally:
            with lock:server_counts['closed']+=1;server_counts['active']-=1
    server=serve(handler,'127.0.0.1',0,compression=None)
    server_thread=threading.Thread(target=server.serve_forever,daemon=True);server_thread.start()
    page.on('close',lambda *args:server.shutdown())
    page.add_init_script(TRACK.replace('RESOURCE_PORT',str(server.socket.getsockname()[1])));page.reload();page.wait_for_timeout(350)
    observation=INSPECT[:INSPECT.index('return view?')]+"return {symbol:view.symbol,interval:view.interval,candles:view.candles.length,series:chart.panes().map(p=>p.getSeries().length)};}"
    page.evaluate('window.__resourceRead='+observation+';undefined')
    cdp=page.context.new_cdp_session(page);cdp.send('Performance.enable')
    def seed(symbol,interval):
        page.wait_for_function("()=>window.__resourceRead().candles===4000")
        page.wait_for_timeout(180)
        assert read('view.symbol')==symbol and read('view.interval')==interval and read('view.candles.length')==4000
        assert page.locator('[data-drawing]').count()==200
    def series(expected):
        sizes=read('chart.panes().map(p=>p.getSeries().length)');assert sizes==expected,sizes
        result['indicator_checks'].append(sizes)
    def cycle():
        page.get_by_role('button',name='EMA 20/50',exact=True).click();page.get_by_role('button',name='RSI 14',exact=True).click();page.wait_for_timeout(70);series([3,1,1])
        page.get_by_label('Sözleşme seç',exact=True).select_option('ETHUSDT');page.get_by_role('button',name='1 sa',exact=True).click();page.wait_for_timeout(120);seed('ETHUSDT','1h');series([3,1,1])
        page.get_by_role('button',name='EMA 20/50',exact=True).click();page.get_by_role('button',name='RSI 14',exact=True).click();page.wait_for_timeout(70);series([1,1])
        page.get_by_label('Sözleşme seç',exact=True).select_option('BTCUSDT');page.get_by_role('button',name='15 dk',exact=True).click();page.wait_for_timeout(120);seed('BTCUSDT','15m');series([1,1])
    def sample(label):
        page.wait_for_timeout(600)
        cdp.send('HeapProfiler.collectGarbage');page.wait_for_timeout(80);cdp.send('HeapProfiler.collectGarbage')
        metrics={x['name']:x['value'] for x in cdp.send('Performance.getMetrics')['metrics']}
        counters=cdp.send('Memory.getDOMCounters');ws=page.evaluate('window.__resourceSockets')
        assert ws['active']==1 and ws['created']-ws['closed']==1 and server_counts['active']==1,ws
        series([1,1])
        data={'label':label,'cycle':0 if label=='post_warmup' else int(label.rsplit('_',1)[1]),'heap_bytes':metrics['JSHeapUsedSize'],'dom':counters,'sockets':ws,'server_connections':dict(server_counts),'series':[1,1],'drawings':page.locator('[data-drawing]').count(),'canvas':page.locator('.chart-host canvas').count()}
        result['samples'].append(data);return data
    def heap_types():
        chunks=[]
        def chunk(event):chunks.append(event['chunk'])
        cdp.on('HeapProfiler.addHeapSnapshotChunk',chunk)
        cdp.send('HeapProfiler.takeHeapSnapshot',{'reportProgress':False})
        cdp.remove_listener('HeapProfiler.addHeapSnapshotChunk',chunk)
        snap=json.loads(''.join(chunks));fields=snap['snapshot']['meta']['node_fields'];stride=len(fields);names=snap['strings'];types=snap['snapshot']['meta']['node_types'][0];nodes=snap['nodes'];out={}
        for i in range(0,len(nodes),stride):
            key=types[nodes[i+fields.index('type')]]+':'+names[nodes[i+fields.index('name')]]
            entry=out.setdefault(key,[0,0]);entry[0]+=1;entry[1]+=nodes[i+fields.index('self_size')]
        return out
    seed('BTCUSDT','15m')
    for _ in range(3):cycle()
    baseline=sample('post_warmup');heap_before=heap_types()
    for i in range(10):cycle();sample('cycle_'+str(i+1))
    for i in range(20):
        cycle()
        if (i+1)%5==0:sample('diagnostic_cycle_'+str(i+11))
    heap_after=heap_types();changes=[]
    categories={}
    for key in set(heap_before)|set(heap_after):
        category=key.split(':')[0];entry=categories.setdefault(category,{'count_delta':0,'shallow_bytes_delta':0});before=heap_before.get(key,[0,0]);after=heap_after.get(key,[0,0]);entry['count_delta']+=after[0]-before[0];entry['shallow_bytes_delta']+=after[1]-before[1]
    result['heap_growth_categories']=categories
    for key,(count,size) in heap_after.items():
        old=heap_before.get(key,[0,0]);changes.append({'type':key,'count_delta':count-old[0],'shallow_bytes_delta':size-old[1]})
    result['heap_type_growth']=sorted(changes,key=lambda x:x['shallow_bytes_delta'],reverse=True)[:35]
    # CDP counters are actual post-GC aggregate listeners/nodes, not a patched listener registry.
    samples=result['samples'];heaps=[s['heap_bytes'] for s in samples];n=len(heaps);xs=[s['cycle'] for s in samples];mean_x=sum(xs)/n;mean_y=sum(heaps)/n
    slope=sum((x-mean_x)*(y-mean_y) for x,y in zip(xs,heaps))/sum((x-mean_x)**2 for x in xs)
    growth=heaps[-1]-heaps[0]
    result['heap_analysis']={'post_gc_bytes':heaps,'linear_slope_bytes_per_cycle':slope,'net_growth_bytes':growth,'screening_budget_bytes':max(1048576,heaps[0]*.05),'method':'Forced GC twice before each sample. Trend screening, not proof of absence of all leaks.'}
    result['heap_object_growth']=sorted([c for c in changes if c['type'].startswith('object:')],key=lambda x:x['shallow_bytes_delta'],reverse=True)[:20]
    assert not all(b>a for a,b in zip(heaps,heaps[1:])),result['heap_analysis']
    assert growth<=max(1048576,heaps[0]*.05) and slope<=65536,result['heap_analysis']
    for s in samples[1:]:
        assert s['dom']['jsEventListeners']<=baseline['dom']['jsEventListeners'],samples
        assert s['dom']['nodes']<=baseline['dom']['nodes']+10,samples
        assert s['dom']['documents']==baseline['dom']['documents'] and s['canvas']==baseline['canvas'],samples
    result['heap_object_growth']=sorted([c for c in changes if c['type'].startswith('object:')],key=lambda x:x['shallow_bytes_delta'],reverse=True)[:20]
    result['fixture']={'diagnostic_extra_cycles':20,'candles':4000,'drawings':200,'symbols':['BTCUSDT','ETHUSDT'],'intervals':['15m','1h'],'warmup_cycles':3,'measured_cycles':10,'series_on':[3,1,1],'series_off':[1,1]}
    result['browser_mode']='HEADLESS_PRODUCTION_NATIVE_LOCAL_WEBSOCKET_CDP_FORCED_GC'
    result['assets']={str(p.relative_to(ROOT/'agentrader/web_assets')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'agentrader/web_assets').rglob('*')) if p.is_file()}
    result['limitations']=['Local real native WebSocket fixture validates browser/server close counts; no live exchange or OS handle census','CDP aggregate listener/node counts after GC; no continuous allocation attribution','Heap screening over 10 cycles, not unlimited-session or physical-device proof','200 horizontal drawings; mixed four-type performance fixture is D1/D2']
    result['user_workspace_writes']=0;cdp.detach();server.shutdown()


if __name__=='__main__':raise SystemExit(main(checks,'chart-resource-lifecycle-browser-20261110.json',production=True))
