"""P2: bot REST writes -> actual production SVG/native chart, no financial access."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json,os,socket,subprocess,sys,tempfile,time,traceback,math,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import httpx
from playwright.sync_api import sync_playwright
from scripts.integration.chart_tool_matrix_cases import drawing_cases,candles,START,STEP
from scripts.chart.measure_chart_interactions import INSPECT,ROOT
from agentrader.chart.chart_evidence import snapshot
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT

OUT=ROOT/'reports/all-chart-tools-20261114'


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--fractional',action='store_true');parser.add_argument('--controls',action='store_true');parser.add_argument('--output-dir',type=Path,default=OUT);parser.add_argument('--only-regression',action='store_true');parser.add_argument('--with-ui',action='store_true');parser.add_argument('--controls-report-local',action='store_true');parser.add_argument('--dpr',type=float,choices=(1,1.25,2),default=1);args=parser.parse_args();OUT=args.output_dir.resolve()
    report_path=OUT/'controls.json' if args.controls and args.controls_report_local else ROOT/'reports/chart-control-bot-readability-20261114.json' if args.controls else OUT/('p2-browser-fractional.json' if args.fractional else 'p2-browser.json')
    result=dict(package='P2',passed=False,cases=[],page_errors=[],unexpected_requests=[],account_requests=0,order_requests=0,scope='Production browser; isolated REST/SQLite; deterministic public fixture',device_scale_factor=args.dpr)
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bot-tool-browser-') as tmp:
        folder=Path(tmp)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}';env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(folder/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(folder/'execution.db'),AGENTRADER_CHART_DATABASE=str(folder/'market.db'),AGENTRADER_WEB_TOKEN='')
        server=subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        market=dict(symbol='BTCUSDT',base_asset='BTC',quote_asset='USDT',tick_size='.25',contract_type='PERPETUAL')
        identity=dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE')
        rows=candles();sockets=[];seq=0
        try:
            with httpx.Client(base_url=base,timeout=10,trust_env=False) as client:
                until=time.time()+15
                while time.time()<until:
                    try:
                        if client.get('/api/health').status_code==200:break
                    except Exception:pass
                    time.sleep(.1)
                with sync_playwright() as pw:
                    browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport=dict(width=1536,height=950),device_scale_factor=args.dpr);page.set_default_timeout(7000)
                    page.on('pageerror',lambda e:result['page_errors'].append(str(e)))
                    def boundary(route):
                        if not route.request.url.startswith(base+'/') or any(x in route.request.url for x in ['/api/account','/api/orders','/api/commands','/api/execution']):
                            result['unexpected_requests'].append(route.request.url);route.abort()
                        else:route.continue_()
                    page.route('**/*',boundary)
                    ui_policy=client.get('/api/workspaces/main/ui-sessions?policy_only=true').json()['policy'] if args.with_ui else None
                    page.route('**/api/markets',lambda r:r.fulfill(json=dict(markets=[market],**identity,**({'ui_session_bridge':ui_policy} if ui_policy else {}))))
                    page.route('**/api/candles*',lambda r:r.fulfill(json=dict(candles=[],has_more=False,**identity)))
                    page.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
                    def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');}')
                    def feed(data):
                        nonlocal seq
                        until=time.time()+5
                        while not sockets and time.time()<until:page.wait_for_timeout(30)
                        assert sockets,'No market socket'
                        seq+=1;proof=snapshot(data,market,dict(state='OK',missing_bars=0),symbol='BTCUSDT',interval='15m',epoch='d'*32,generation=1,revision=seq).view()
                        sockets[-1].send(json.dumps(dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=seq,stream_epoch='d'*32,data_proof=proof,status='LIVE',received_at=int(time.time()*1000),market=market,quality=dict(state='OK',missing_bars=0),candles=data,**identity)))
                        page.wait_for_timeout(160)
                    def frame():
                        # Native LOG mode must refit via autoscale; setVisibleRange
                        # after a mode switch has a known conversion limitation.
                        read('(chart.timeScale().setVisibleLogicalRange({from:260,to:335}),series.applyOptions({autoscaleInfoProvider:()=>({priceRange:{minValue:80,maxValue:200}})}),series.priceScale().applyOptions({autoScale:true}),true)');page.wait_for_timeout(100)
                    def reload(data=rows):
                        sockets.clear();page.goto(base);feed(data);page.get_by_text(str(len(data))+' mum',exact=True).wait_for();frame()
                    def points(g):
                        # Independent affine reference from two native integer bars.
                        # Native v5.2 does not accept fractional logical indices.
                        xref='chart.timeScale().logicalToCoordinate(0)+((a.time-'+str(START)+')/'+str(STEP)+')*(chart.timeScale().logicalToCoordinate(1)-chart.timeScale().logicalToCoordinate(0))'
                        values=read('('+json.dumps(g['anchors'])+').map(a=>({x:'+xref+',y:series.priceToCoordinate(Number(a.price))}))')
                        if g.get('schema')=='chart-channel-family/1':
                            kind=g['kind'];a,b=values[:2]
                            if kind=='regression_channel':
                                return read('('+json.dumps(g['anchors'])+').map(raw=>{const a={time:'+str(START)+'+Math.floor((raw.time-'+str(START)+')/'+str(STEP)+')*'+str(STEP)+'};return {x:'+xref+',y:series.priceToCoordinate(100+Math.floor((raw.time-'+str(START)+')/'+str(STEP)+')*.25)};})')
                            if kind in ('parallel_channel','flat_channel','disjoint_channel'):
                                c=values[2]
                                y=b['y']+c['y']-(a['y']+(b['y']-a['y'])*(c['x']-a['x'])/(b['x']-a['x'])) if kind=='parallel_channel' else c['y']
                                return [a,b,dict(x=b['x'],y=y)]
                        return values
                    def verify(g,did,log=False):
                        node=page.locator('[data-drawing="'+did+'"]');assert node.is_visible(),(g['kind'],'not visible',points(g),read('({mode:series.priceScale().options().mode,pane:chart.paneSize(0)})'))
                        node.press('Enter');page.wait_for_timeout(130)
                        expected=points(g);errors=[]
                        if g['kind'] in ('horizontal','horizontal_ray'):
                            line=node.locator('.shape-line').first
                            errors.append(abs(float(line.get_attribute('y1'))-expected[0]['y']))
                            if g['kind']=='horizontal_ray':errors.append(abs(float(line.get_attribute('x1'))-expected[0]['x']))
                        elif not log or g.get('schema')=='chart-channel-family/1':
                            handles=page.locator('[data-drawing-handles="'+did+'"]')
                            for i,p in enumerate(expected):
                                h=handles.locator('[data-anchor="'+str(i)+'"]');assert h.is_visible(),(g['kind'],i,'handle hidden')
                                errors.extend([abs(float(h.get_attribute('cx'))-p['x']),abs(float(h.get_attribute('cy'))-p['y'])])
                        assert all(math.isfinite(x) and x<=1 for x in errors),(g['kind'],errors)
                        if 'text' in g:
                            text=node.text_content()
                            for part in g['text'].split('\n'):assert part in text,(g['kind'],part,text)
                            assert node.locator('b,script').count()==0
                        return max(errors,default=0)
                    def ui_read(predicate=lambda value:True):
                        until=time.monotonic()+6
                        while time.monotonic()<until:
                            sid=page.evaluate('document.documentElement.dataset.uiSessionId')
                            if sid:
                                value=client.get('/api/workspaces/main/ui-sessions/'+sid).json()
                                if value.get('state')=='READY' and predicate(value['snapshot']):return value
                            page.wait_for_timeout(80)
                        raise AssertionError('Live owned UI report not published')
                    if args.controls:
                        from scripts.chart.chart_control_cases import run_controls
                        reload();result['checks']=run_controls(page,client,read,feed,frame,rows,ui_read=ui_read if args.with_ui else None)
                        page.screenshot(path=str(OUT/'controls.png'))
                    if args.only_regression:
                        probe=next(c['geometry'] for c in drawing_cases() if c['geometry']['kind']=='regression_channel')
                        probe['anchors']=[dict(time=rows[280]['time']+offset,price='999') for offset in (225,450)]
                        created=client.post('/api/workspaces/main/drawings?format_version=10',json=dict(request_id='g4-readiness',geometry=probe)).json();pid=created['drawing_id'];node=page.locator('[data-drawing="'+pid+'"]')
                        reload();assert node.get_attribute('data-family-state')=='WARMUP';assert node.locator('.family-unavailable').is_visible()
                        page.screenshot(path=str(OUT/'same-candle-warmup.png'))
                        probe['anchors'][1]['time']=rows[294]['time']+225
                        changed=client.patch('/api/drawings/'+pid+'?format_version=10',json=dict(request_id='g4-distinct-bars',expected_revision=1,geometry=probe));assert changed.status_code==200
                        reload();assert node.get_attribute('data-family-state')=='READY'
                        feed(rows[:285]+rows[286:]);frame();assert node.get_attribute('data-family-state')=='WAITING_FOR_DATA';assert node.locator('.family-unavailable').is_visible()
                        page.screenshot(path=str(OUT/'gap-waiting.png'))
                        feed(rows);frame();assert node.get_attribute('data-family-state')=='READY';assert node.locator('.family-line').count()>0
                        assert client.get('/api/drawings/'+pid+'?format_version=10').json()['geometry']==probe
                        result['readiness_checks']=['same_candle_warmup_visible','gap_waiting_visible','same_coordinates_recover_without_stale_cache','raw_anchors_preserved']
                        deleted=client.request('DELETE','/api/drawings/'+pid+'?format_version=10',json=dict(request_id='g4-probe-delete',expected_revision=2));assert deleted.status_code==200
                    for future in (() if args.controls else (False,True)):
                        for case in drawing_cases(future,args.fractional,include_projection=True):
                            if args.only_regression and case['geometry']['kind']!='regression_channel':continue
                            cid=('fractional-' if args.fractional else '')+('future-' if future else 'loaded-')+case['case_id'];g=case['geometry']
                            row=dict(case_id=cid,kind=g['kind'],schema=g.get('schema','LEGACY'),state='RUNNING');result['cases'].append(row)
                            response=client.post('/api/workspaces/main/drawings?format_version=10',json=dict(request_id=cid,geometry=g));assert response.status_code==201,response.text
                            d=response.json();did=d['drawing_id'];g=d['geometry'];row['drawing_id']=did
                            reload();assert read('view.candles.length')==300
                            missing_regression=future and g['kind']=='regression_channel'
                            if missing_regression:
                                assert not page.locator('[data-drawing="'+did+'"] .family-line').count()
                                assert page.locator('[data-drawing="'+did+'"]').get_attribute('data-family-state')=='WAITING_FOR_DATA'
                                row['before_source_bars']='WAITING_FOR_DATA_NO_FABRICATED_FIT'
                            else:row['max_anchor_error_css_px']=verify(g,did)
                            before=client.get('/api/drawings/'+did+'?format_version=10').json()['geometry'];assert before==g
                            # Reload is a fresh read from persistent API state, not an in-memory edit.
                            if not future:
                                page.get_by_label('Fiyat ekseni türü',exact=True).select_option('LOG');frame()
                                blocked=g.get('schema')!='chart-channel-family/1' and g['kind'] in ('trend','ray','extended_line','parallel_channel')
                                node=page.locator('[data-drawing="'+did+'"]')
                                if blocked:assert not node.is_visible();row['log']='EXPECTED_BLOCK'
                                else:verify(g,did,True);row['log']='PASS'
                                page.get_by_label('Fiyat ekseni türü',exact=True).select_option('LINEAR');frame()
                            else:
                                feed(candles(340));frame();verify(g,did)
                                assert client.get('/api/drawings/'+did+'?format_version=10').json()['geometry']==before
                                row['bar_arrival_preserves_utc']='PASS'
                                if g['kind']=='regression_channel':
                                    reload(candles(340));verify(g,did)
                                    assert client.get('/api/drawings/'+did+'?format_version=10').json()['geometry']==before
                                    row['reload_after_source_arrival']='PASS'
                            if args.with_ui:
                                ui=ui_read(lambda value:did in value['selection']['drawing_ids']);row['ui_context_read']='PASS_CLIENT_REPORTED';row['ui_sequence']=ui['sequence'];row['ui_order_authority']=ui['order_authority']
                            page.screenshot(path=str(OUT/(cid+'.png')))
                            response=client.request('DELETE','/api/drawings/'+did+'?format_version=10',json=dict(request_id=cid+'-delete',expected_revision=1));assert response.status_code==200,response.text
                            row.update(state='PASS',api_readback='PASS',reload='PASS',candle_count_not_synthesized=True)
                            report_path.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
                    assert not result['page_errors'];assert not result['unexpected_requests'];assert not (folder/'execution.db').exists()
                    result['passed']=all(r['state']=='PASS' for r in result['checks']) if args.controls else all(r['state'] in ('PASS','EXPECTED_BLOCK') for r in result['cases']) and len(result['cases'])==(2 if args.only_regression else 52)
                    browser.close()
        except Exception:
            result['error']=traceback.format_exc()
            try:page.screenshot(path=str(OUT/'p2-failure.png'))
            except Exception:pass
        finally:server.terminate();server.wait(timeout=10)
    report_path.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(package='P2',passed=result['passed'],cases=len(result['cases']),error=result.get('error')),ensure_ascii=True))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
