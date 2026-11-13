"""Pinned D1/D2 headless production workload; rAF cadence is not GPU FPS."""
import argparse
import copy
import hashlib
import json
import os
import platform
import time
from pathlib import Path
from measure_chart_interactions import main, INSPECT, ROOT

parser=argparse.ArgumentParser()
parser.add_argument('--seconds',type=int,choices=[10,60],default=10)
parser.add_argument('--runs',type=int,choices=[1,2,3],default=1)
parser.add_argument('--report',default=None)
args=parser.parse_args()


def checks(page,sockets,unused,result):
    def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+f'return ({expr});'+'}')
    rows=[{'time':1800000000+i*900,'open':100+i*.1,'high':110+i*.1,'low':90+i*.1,'close':105+i*.1,'volume':10+i,'quote_volume':1000,'close_time':(1800000000+(i+1)*900)*1000-1,'closed':i<3999} for i in range(4000)]
    items=[]
    for i in range(200):
        kind=['horizontal','zone','trend','fibonacci'][i%4]
        a={'time':rows[3910+i%70]['time'],'price':str(484+(i%25))}
        b={'time':rows[3940+i%60]['time'],'price':str(488+(i%25))}
        items.append({'drawing_id':'perf-'+str(i),'workspace_id':'main','revision':1,'deleted':False,'updated_at':0,'geometry':{'kind':kind,'symbol':'BTCUSDT','price_source':'LAST_PRICE','label':'P'+str(i),'anchors':[a] if kind=='horizontal' else [a,b]}})
    initial=copy.deepcopy(items)
    page.route('**/api/workspaces/main/drawings*',lambda r:r.fulfill(json={'drawings':items}) if r.request.method=='GET' else r.abort())
    page.goto(page.url.split('?')[0]+'?diagnostics=1');page.wait_for_timeout(300)
    sockets[-1].send(json.dumps({'type':'snapshot','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'candles':rows}))
    page.wait_for_function("document.querySelector('.loaded-count')?.textContent.includes('4000')")
    assert page.locator('[data-drawing]').count()==200
    # Fixed selection, viewport, zoom and price range before every measured run.
    def reset():
        page.get_by_label('Görünümü sıfırla',exact=True).click();page.wait_for_timeout(250)
        read('chart.timeScale().setVisibleLogicalRange({from:3890,to:4006})')
        read('series.priceScale().setVisibleRange({from:475,to:520})')
        page.locator('[data-drawing="perf-2"]').press('Enter')
        page.locator('.chart-host').scroll_into_view_if_needed();page.wait_for_timeout(400)
    result['date']='2026-11-10'
    result['task']='D1' if args.seconds==10 else 'D2'
    result['mode']='HEADLESS_PRODUCTION_CONTROLLED_SYNTHETIC_FEED'
    result['hardware']={'os':platform.platform(),'machine':platform.machine(),'processor':platform.processor(),'logical_cpus':os.cpu_count()}
    result['browser_environment']=page.evaluate("({userAgent:navigator.userAgent,hardwareConcurrency:navigator.hardwareConcurrency,deviceMemory:navigator.deviceMemory??null,dpr:devicePixelRatio,viewport:{width:innerWidth,height:innerHeight},visibility:document.visibilityState})")
    assets=ROOT/'agentrader/web_assets'
    result['assets']={str(p.relative_to(assets)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(assets.rglob('*')) if p.is_file()}
    payload=json.dumps({'candles':rows,'drawings':initial},sort_keys=True,separators=(',',':')).encode()
    result['fixture']={'candles':4000,'drawings':200,'types':{k:50 for k in ['horizontal','zone','trend','fibonacci']},'sha256':hashlib.sha256(payload).hexdigest(),'seed':'arithmetic-v1','symbol':'BTCUSDT','interval':'15m','feed':'one fixed synthetic snapshot; repeated-sequence freshness heartbeat each 2-second cycle; no live exchange traffic'}
    result['scenario']={'version':1,'cycle_seconds':2,'actions':['wheel zoom in -120','wheel zoom out +120','native mouse pan +40px','native mouse pan -40px','selected trend anchor drag +12px/-6px then Escape'],'cadence_target_ms':33.34,'metric':'rAF callback intervals, not GPU FPS','validity':'document visible for entire run; no interruption, viewport/workload/status change, errors or truncated samples; >=30 samples'}
    result['runs']=[]
    for index in range(args.runs):
        reset()
        assert read('view.candles.length')==4000 and page.locator('[data-drawing]').count()==200
        page.get_by_role('button',name='10 sn ön kontrol' if args.seconds==10 else '60 sn ölç',exact=True).click()
        page.locator('.chart-host').scroll_into_view_if_needed()
        trace=[];start=time.monotonic();cycle=0
        while time.monotonic()-start<args.seconds-.5:
            cycle_start=time.monotonic()
            sockets[-1].send(json.dumps({'type':'update','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000)}))
            assert page.evaluate("document.visibilityState==='visible'"),'Background page invalidates run'
            b=page.locator('.chart-host').bounding_box();x=b['x']+b['width']*.6;y=b['y']+b['height']*.08
            for delta in [-120,120]:
                before=read('chart.timeScale().getVisibleLogicalRange()');page.mouse.move(x,y);page.mouse.wheel(0,delta);page.wait_for_timeout(210)
                after=read('chart.timeScale().getVisibleLogicalRange()');assert before!=after,'Wheel did not change range'
            for dx in [40,-40]:
                before=read('chart.timeScale().getVisibleLogicalRange()');page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+dx,y,steps=6);page.mouse.up();page.wait_for_timeout(120)
                assert before!=read('chart.timeScale().getVisibleLogicalRange()'),'Pan did not change range'
            handle=page.locator('[data-drawing-handles="perf-2"] [data-anchor="0"]');h=handle.bounding_box();assert h
            hx=h['x']+h['width']/2;hy=h['y']+h['height']/2
            options=read('chart.options().handleScroll')
            page.mouse.move(hx,hy);page.mouse.down();page.mouse.move(hx+12,hy-6,steps=6)
            assert options!=read('chart.options().handleScroll'),'Anchor drag did not start'
            page.keyboard.press('Escape');page.mouse.up();assert options==read('chart.options().handleScroll')
            trace.append({'cycle':cycle,'elapsed_ms':round((time.monotonic()-start)*1000),'completed_actions':5})
            cycle+=1;remaining=2-(time.monotonic()-cycle_start)
            if remaining>0:page.wait_for_timeout(remaining*1000)
        page.wait_for_function("document.querySelector('.performance-panel pre')!==null",timeout=15000)
        measurement=json.loads(page.locator('.performance-panel pre').text_content())
        valid=measurement['cadence']['usable'] and not any(measurement[k] for k in ['workload_changed','non_live_observed','viewport_changed','errors'])
        assert measurement['start']['candles']==4000 and measurement['end']['drawings']==200
        assert measurement['start']['width']==1400 and measurement['start']['height']==1000 and measurement['start']['dpr']==1
        assert items==initial and valid,measurement
        result['runs'].append({'run':index+1,'valid':valid,'trace':trace,'measurement':measurement,'target_passed':measurement['cadence']['p95_ms']<=33.34})
    result['d1_fixture_verified']=True
    result['performance_acceptance']=False
    result['limitations']=['Headless environment; no visible Windows/GPU/native trackpad verdict','Synthetic fixed snapshot; streaming and resource retention are D3/D4 scope','10-second dry run does not complete D2; D2 requires three valid 60-second runs']


if __name__=='__main__':
    report=args.report or 'chart-performance-'+str(args.seconds)+'s-20261110.json'
    assert Path(report).name==report and report.endswith('.json'),'Report must be a JSON basename'
    raise SystemExit(main(checks,report,production=True))
