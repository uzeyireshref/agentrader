"""D4 native production 30-minute streaming soak; --smoke is harness-only."""
import argparse
import copy
import hashlib
import json
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from websockets.sync.server import serve
from websockets.exceptions import ConnectionClosed
from measure_chart_interactions import main,INSPECT,ROOT
from check_chart_resources import TRACK

parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
DURATION=20 if args.smoke else 1800
NAME='chart-soak-smoke-20261110.json' if args.smoke else 'chart-soak-browser-20261110.json'
CHECKPOINT=ROOT/'reports'/('chart-soak-smoke-progress-20261110.json' if args.smoke else 'chart-soak-progress-20261110.json')

def digest(rows,fields):
    data=[[str(r[k]) if isinstance(r[k],bool) else format(float(r[k]),'.8f') for k in fields] for r in rows]
    return hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest()


def checks(page,sockets,unused,result):
    result.update(date='2026-11-10',task='D4_SMOKE' if args.smoke else 'D4',samples=[],events=[],mode='HEADLESS_PRODUCTION_NATIVE_LOCAL_STREAM',requested_seconds=DURATION)
    lock=threading.RLock();stop=threading.Event();connections={};server_counts={'opened':0,'closed':0,'active':0};journal={};boundaries=[]
    # Production run uses real 15-minute candle spacing and two boundaries 900 seconds apart.
    spacing=8 if args.smoke else 900;first_boundary=2 if args.smoke else 60
    origin=int(time.time())//900*900
    rows=[{'time':origin-(3999-i)*900,'open':100+i*.1,'high':110+i*.1,'low':90+i*.1,'close':105+i*.1,'volume':10+i,'quote_volume':1000,'close_time':(origin-(3998-i)*900)*1000-1,'closed':i<3999} for i in range(4000)]
    market={'symbol':'BTCUSDT','base_asset':'BTC','quote_asset':'USDT','tick_size':'0.1','contract_type':'PERPETUAL'}
    drawings=[]
    for i in range(200):
        kind=['horizontal','zone','trend','fibonacci'][i%4];anchors=[{'time':rows[3910+i%70]['time'],'price':str(484+i%25)}]
        if kind!='horizontal':anchors.append({'time':rows[3940+i%60]['time'],'price':str(488+i%25)})
        drawings.append({'drawing_id':'soak-'+str(i),'workspace_id':'main','revision':1,'deleted':False,'updated_at':0,'geometry':{'kind':kind,'symbol':'BTCUSDT','price_source':'LAST_PRICE','label':'S'+str(i),'anchors':anchors}})
    fields=['time','open','high','low','close','volume','quote_volume','close_time','closed'];sequence=[1];started=[time.monotonic()]
    def remember():journal[sequence[0]]=digest(rows,fields)
    remember()
    def handler(ws):
        with lock:
            server_counts['opened']+=1;generation=server_counts['opened'];server_counts['active']+=1;connections[ws]=generation
            ws.send(json.dumps({'type':'snapshot','symbol':'BTCUSDT','interval':'15m','generation':generation,'sequence':sequence[0],'status':'LIVE','received_at':int(time.time()*1000),'market':market,'candles':rows}))
        try:
            for _ in ws:pass
        except ConnectionClosed:pass
        finally:
            with lock:connections.pop(ws,None);server_counts['closed']+=1;server_counts['active']-=1
    def broadcast():
        while not stop.wait(1 if args.smoke else 2):
            with lock:
                elapsed=time.monotonic()-started[0];tail=[]
                if len(boundaries)<2 and elapsed>=first_boundary+len(boundaries)*spacing:
                    closed=dict(rows[-1],closed=True);rows[-1]=closed
                    fresh=dict(closed,time=closed['time']+900,open=closed['close'],close=closed['close'],closed=False,volume=1,quote_volume=1000,close_time=closed['close_time']+900000)
                    rows.append(fresh);del rows[0];tail=[closed,fresh];boundaries.append({'elapsed_seconds':elapsed,'closed_time':closed['time'],'new_time':fresh['time']})
                else:
                    rows[-1]=dict(rows[-1],close=rows[-1]['open']+((sequence[0]%7)-3)*.1,volume=rows[-1]['volume']+1)
                    rows[-1]['high']=max(rows[-1]['high'],rows[-1]['close']);rows[-1]['low']=min(rows[-1]['low'],rows[-1]['close']);tail=[rows[-1]]
                sequence[0]+=1;remember()
                for ws,generation in list(connections.items()):
                    try:ws.send(json.dumps({'type':'update','symbol':'BTCUSDT','interval':'15m','generation':generation,'sequence':sequence[0],'status':'LIVE','received_at':int(time.time()*1000),'tail':tail}))
                    except ConnectionClosed:pass
    page.route('**/api/workspaces/main/drawings*',lambda r:r.fulfill(json={'drawings':drawings}) if r.request.method=='GET' else r.abort())
    server=serve(handler,'127.0.0.1',0,compression=None);threading.Thread(target=server.serve_forever,daemon=True).start()
    thread=threading.Thread(target=broadcast,daemon=True)
    page.on('close',lambda *unused:server.shutdown())
    page.add_init_script(TRACK.replace('RESOURCE_PORT',str(server.socket.getsockname()[1])))
    page.reload();page.wait_for_timeout(350)
    observer=INSPECT[:INSPECT.index('return view?')]+"return {view,candles,volume,series:chart.panes().map(p=>p.getSeries().length),drawings:document.querySelectorAll('[data-drawing]').length};}"
    page.evaluate('window.__soakRead='+observer+';undefined')
    page.wait_for_function('()=>window.__soakRead().view.candles.length===4000')
    page.locator('.chart-host').scroll_into_view_if_needed()
    cdp=page.context.new_cdp_session(page);cdp.send('Performance.enable')
    page.evaluate("""()=>{const s=window.__soak={frames:0,last:null,max_ms:0,bins:{},errors:0,rejections:0,hidden:document.hidden?1:0};window.addEventListener('error',()=>s.errors++);window.addEventListener('unhandledrejection',()=>s.rejections++);document.addEventListener('visibilitychange',()=>{if(document.hidden)s.hidden++;});const frame=t=>{if(s.last!==null){const dt=t-s.last;s.max_ms=Math.max(s.max_ms,dt);const key=Math.min(10000,Math.round(dt*10));s.bins[key]=(s.bins[key]??0)+1;s.frames++;}s.last=t;s.raf=requestAnimationFrame(frame);};s.raf=requestAnimationFrame(frame);} """)
    # Baseline heap-type data allows D3 code/runtime growth to be reviewed after the soak.
    def heap_types():
        chunks=[]
        def chunk(e):chunks.append(e['chunk'])
        cdp.on('HeapProfiler.addHeapSnapshotChunk',chunk);cdp.send('HeapProfiler.takeHeapSnapshot',{'reportProgress':False});cdp.remove_listener('HeapProfiler.addHeapSnapshotChunk',chunk)
        raw=json.loads(''.join(chunks));meta=raw['snapshot']['meta'];f=meta['node_fields'];stride=len(f);nodes=raw['nodes'];out={}
        for i in range(0,len(nodes),stride):
            key=meta['node_types'][0][nodes[i+f.index('type')]];v=out.setdefault(key,[0,0]);v[0]+=1;v[1]+=nodes[i+f.index('self_size')]
        return out
    def sample(label,gc=False):
        with lock:
            page.wait_for_timeout(150)
            if gc:cdp.send('HeapProfiler.collectGarbage');page.wait_for_timeout(60);cdp.send('HeapProfiler.collectGarbage')
            metrics={x['name']:x['value'] for x in cdp.send('Performance.getMetrics')['metrics']}
            counters=cdp.send('Memory.getDOMCounters')
            state=page.evaluate('()=>window.__soakRead()');v=state['view'];actual=digest(v['candles'],fields)
            with lock:expected=journal[v['sequence']];counts=dict(server_counts);events=copy.deepcopy(boundaries)
            assert actual==expected,'Client candle state differs from canonical stream sequence'
            assert len(v['candles'])==4000 and len(state['candles'])==4000 and len(state['volume'])==4000
            for stored,candle,volume in zip(v['candles'],state['candles'],state['volume']):
                assert all(stored[k]==candle[k] for k in ['time','open','high','low','close']) and volume['time']==stored['time'] and volume['value']==stored['volume']
            assert v['status']=='LIVE' and state['drawings']==200 and state['series']==[1,1],state['series']
            ws=page.evaluate('window.__resourceSockets');monitor=page.evaluate('window.__soak');assert ws['active']==1 and counts['active']==1
            assert not any(monitor[k] for k in ['errors','rejections','hidden']),monitor
            data={'label':label,'elapsed_seconds':time.monotonic()-began,'sequence':v['sequence'],'generation':v['generation'],'canonical_hash_matched':True,'candles':4000,'drawings':200,'last_time':v['candles'][-1]['time'],'dom':counters,'heap_bytes':metrics['JSHeapUsedSize'],'forced_gc':gc,'sockets':ws,'server_connections':counts,'boundary_count':len(events),'monitor':monitor}
            result['samples'].append(data)
            CHECKPOINT.write_text(json.dumps({'status':'RUNNING','elapsed_seconds':data['elapsed_seconds'],'samples':len(result['samples']),'boundaries':events,'reconnects':result['events'],'latest':data},indent=2)+'\n',encoding='utf-8')
            return data
    began=time.monotonic();started[0]=began
    try:
        baseline=sample('baseline',True);before_types=heap_types();thread.start()
        next_sample=2 if args.smoke else 30;next_gc=5 if args.smoke else 300;reconnects=[6,14] if args.smoke else [300,1200];done=set()
        while time.monotonic()-began<DURATION:
            elapsed=time.monotonic()-began
            for at in reconnects:
                if at in done or elapsed<at:continue
                with lock:targets=list(connections);previous=server_counts['opened']
                for ws in targets:ws.close(1012,'controlled D4 reconnect')
                page.wait_for_function("()=>window.__resourceSockets.active===0",timeout=5000)
                observed=page.evaluate('()=>window.__soakRead().view.status');assert observed=='RECONNECTING',observed
                page.wait_for_function("()=>window.__soakRead().view.status==='LIVE' && window.__resourceSockets.active===1",timeout=15000)
                with lock:assert server_counts['opened']>previous
                event={'scheduled_seconds':at,'actual_seconds':time.monotonic()-began,'reconnecting_observed':True,'recovered':True};result['events'].append(event);done.add(at)
            if elapsed>=next_sample:
                collect=elapsed>=next_gc;sample('periodic',collect)
                if collect:next_gc+=5 if args.smoke else 300
                next_sample+=2 if args.smoke else 30
            page.wait_for_timeout(250)
        final=sample('final',True);after_types=heap_types()
        result['heap_type_delta']={k:{'count_delta':after_types.get(k,[0,0])[0]-before_types.get(k,[0,0])[0],'shallow_bytes_delta':after_types.get(k,[0,0])[1]-before_types.get(k,[0,0])[1]} for k in set(before_types)|set(after_types)}
        gc_samples=[s for s in result['samples'] if s['forced_gc']];growth=final['heap_bytes']-baseline['heap_bytes'];budget=max(2097152,baseline['heap_bytes']*.2)
        result['heap_review']={'post_gc_samples':[{'elapsed_seconds':s['elapsed_seconds'],'bytes':s['heap_bytes']} for s in gc_samples],'net_growth_bytes':growth,'screening_budget_bytes':budget,'within_budget':growth<=budget,'plateau_verified':False,'note':'Heap snapshots include runtime compiled code/native records; forced GC pauses are included in monitor, not compared with D2 interaction p95.'}
        result['duration_seconds']=time.monotonic()-began;result['boundaries']=copy.deepcopy(boundaries);result['assets']={str(p.relative_to(ROOT/'agentrader/web_assets')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'agentrader/web_assets').rglob('*')) if p.is_file()}
        assert len(boundaries)>=2 and len(done)==2 and growth<=budget,result['heap_review']
        assert all(s['dom']['jsEventListeners']==baseline['dom']['jsEventListeners'] and s['dom']['nodes']<=baseline['dom']['nodes']+10 and s['dom']['documents']==1 for s in gc_samples)
        result['d4_eligible']=not args.smoke and result['duration_seconds']>=1800
        result['scope']='Controlled production native local WebSocket, canonical client/native-series comparisons; no live exchange, physical touch or full release acceptance'
        CHECKPOINT.write_text(json.dumps({'status':'COMPLETED_SMOKE' if args.smoke else 'COMPLETED','duration_seconds':result['duration_seconds'],'samples':len(result['samples']),'boundary_count':len(boundaries),'reconnect_count':len(done),'d4_eligible':result['d4_eligible']},indent=2)+'\n',encoding='utf-8')
    finally:
        stop.set()
        with lock:targets=list(connections)
        for ws in targets:ws.close(1000,'test completed')
        server.shutdown();thread.join(timeout=3);cdp.detach()


if __name__=='__main__':raise SystemExit(main(checks,NAME,production=True))
