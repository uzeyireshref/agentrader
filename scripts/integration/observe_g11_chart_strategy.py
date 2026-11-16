"""Real Demo public feed + separate production strategy process, bounded and order-free."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse,hashlib,json,os,secrets,socket,subprocess,sys,threading,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import httpx,uvicorn
from agentrader.api.app import create_app
from agentrader.application.settings import WebSettings
from agentrader.integration.chart_bot import ChartBot
from agentrader.chart.chart_market import ChartMarket
from agentrader.shared.market_data import PublicMarket
from agentrader.shared.market_feed import MarketFeedHub
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT

OUT=ROOT/'reports/chart-interface-g11-20261115'

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,default=OUT);args=parser.parse_args();OUT=args.output_dir.resolve()
    OUT.mkdir(parents=True,exist_ok=True);folder=OUT/'runtime';folder.mkdir(exist_ok=True)
    # Never reuse another run's state with a different ephemeral server identity.
    if (folder/'app.db').exists():raise RuntimeError('Archive the previous G11 runtime before a new observation')
    sources=['agentrader/integration/chart_strategy.py','agentrader/integration/chart_bot.py','agentrader/cli/chart_bot_cli.py','agentrader/shared/market_feed.py','agentrader/chart/chart_context.py','agentrader/chart/indicator_queries.py','scripts/integration/observe_g11_chart_strategy.py']
    source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
    report=dict(schema='g11-demo-strategy-observation/1',state='RUNNING',passed=False,source=SOURCE,environment=ENVIRONMENT,scope='REAL_DEMO_PUBLIC_FEED_PRODUCTION_HTTP_ADAPTER_SEPARATE_STRATEGY_PROCESS',account_requests=0,order_requests=0,public_requests=[],checks=[],phases=[],started_at=time.time(),source_sha256=source_hashes)
    def save():(OUT/'observation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def check(name,value):report['checks'].append(dict(name=name,passed=bool(value)));save();assert value,name
    class AuditedPublic(PublicMarket):
        def get(self,path,params=None):
            value=super().get(path,params)
            report['public_requests'].append(dict(at=time.time(),method='GET',path=path,params=params,response_sha256=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()))
            return value
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}';human_token=secrets.token_hex(24);bot_token=secrets.token_hex(24)
    settings=WebSettings(application_database=folder/'app.db',market_database=folder/'market.db',execution_database=folder/'execution.db',owner='g11-observation',token=human_token,bot_token=bot_token,bot_id='g11-bot',strategy_id='closed-ema20')
    env=dict(os.environ,AGENTRADER_CHART_BOT_TOKEN=bot_token,PYTHONIOENCODING='utf-8')
    bot=ChartBot(base,bot_token,bot_id='g11-bot',strategy_id='closed-ema20',workspace_id='g11-demo',journal=folder/'bot.db')
    server=thread=hub=feed=child=log=None
    human=httpx.Client(base_url=base,headers={'Authorization':'Bearer '+human_token},trust_env=False,timeout=10)
    def start():
        nonlocal server,thread,hub,feed
        market=ChartMarket(folder/'market.db',client_factory=AuditedPublic);hub=MarketFeedHub(market)
        app=create_app(settings,market=market,hub=hub)
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error',access_log=False))
        thread=threading.Thread(target=server.run,daemon=True);thread.start();until=time.monotonic()+15
        while not server.started and time.monotonic()<until:time.sleep(.1)
        assert server.started
        feed=hub.acquire('BTCUSDT','1m')
    def stop():
        nonlocal server,thread,hub,feed
        if hub and feed:hub.release(feed);feed=None
        if server:server.should_exit=True
        if thread:thread.join(timeout=20);assert not thread.is_alive()
        server=thread=hub=None
    def ready():
        until=time.monotonic()+60
        while time.monotonic()<until:
            try:
                value=bot.snapshot('BTCUSDT','1m')
                if value['derived']['readiness']['state']=='READY':return value
            except Exception:pass
            time.sleep(.5)
        raise RuntimeError('Real Demo feed did not become READY')
    def run_phase(number,required_applied):
        nonlocal child,log
        path=OUT/('strategy-phase'+str(number)+'.jsonl');log=path.open('w',encoding='utf-8')
        command=[sys.executable,'-m','agentrader','chart-bot','--url',base,'--bot-id','g11-bot','--strategy-id','closed-ema20','--workspace','g11-demo','--journal',str(folder/'bot.db'),'strategy-watch','--state',str(folder/'strategy.json'),'--seconds','180','--trace',str(OUT/'http-trace.jsonl')]
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        until=time.monotonic()+150;events=[]
        while time.monotonic()<until:
            lines=path.read_text(encoding='utf-8').splitlines();events=[]
            for line in lines:
                try:events.append(json.loads(line))
                except ValueError:pass
            if len([e for e in events if e.get('state')=='APPLIED'])>=required_applied and events[-1].get('state')=='NO_CHANGE':break
            if child.poll() is not None:break
            report['elapsed_seconds']=round(time.time()-report['started_at'],1);save();time.sleep(.5)
        if child.poll() is None:child.terminate()
        child.wait(timeout=10);child=None;log.close();log=None
        report['phases'].append(dict(number=number,events=len(events),applied=sum(e.get('state')=='APPLIED' for e in events),unchanged=sum(e.get('state')=='NO_CHANGE' for e in events),pauses=sum(e.get('state')=='PAUSED' for e in events),evidence=path.name))
        assert sum(e.get('state')=='APPLIED' for e in events)>=required_applied,events[-1:]
        return events
    try:
        save();start();context=ready();report['initial_context']=context
        check('read_only_live_context_verified',context['derived']['readiness']['proof']['state']=='VERIFIED' and context['derived']['readiness']['source_clock']['state']=='FRESH')
        geometry=dict(kind='horizontal',symbol='BTCUSDT',price_source='LAST_PRICE',label='Manual G11 sentinel',anchors=[dict(time=context['derived']['readiness']['last_closed_candle'],price='50000')])
        response=human.post('/api/workspaces/g11-demo/drawings?format_version=10',json=dict(request_id='manual-sentinel',geometry=geometry));assert response.status_code==201
        manual=response.json();mid=manual['drawing_id']
        assert human.put('/api/drawings/'+mid+'/notes',json=dict(request_id='manual-note',expected_revision=0,expected_drawing_revision=1,text='Manuel sentinel 🧭; bot değiştiremez.')).status_code==200
        before=bot.get(mid)
        events=run_phase(1,2);applied=[e for e in events if e.get('state')=='APPLIED'];did=applied[0]['drawing_id']
        check('autonomous_new_closed_bar_updates_same_object',len({e['drawing_id'] for e in applied})==1 and len({e['bar_time'] for e in applied})>=2 and applied[-1]['revision']>applied[0]['revision'])
        # No synthetic packet or stale payload is injected. Release the real subscription:
        # the official context must become unavailable and the running strategy must pause.
        hub.release(feed);feed=None
        paused_context=bot.snapshot('BTCUSDT','1m')
        from agentrader.integration.chart_strategy import DrawingStrategy
        strategy=DrawingStrategy(bot,folder/'strategy.json')
        before_item=bot.get(did);pause=strategy.step();report['controlled_subscription_pause']=pause
        check('real_subscription_absence_stops_new_decisions',pause['state']=='PAUSED' and bot.get(did)==before_item)
        stop();start();ready()
        replay=strategy.step();report['immediate_restart_result']=replay
        check('same_closed_bar_restart_has_no_second_object',replay['state']=='NO_CHANGE' and len(bot.find_own('BTCUSDT','1m'))==1)
        second=run_phase(2,1);all_applied=applied+[e for e in second if e.get('state')=='APPLIED']
        check('separate_restarted_process_continues_same_drawing',all(e['drawing_id']==did for e in all_applied) and len(bot.find_own('BTCUSDT','1m'))==1)
        check('manual_sentinel_geometry_origin_revision_note_unchanged',bot.get(mid)==before)
        check('every_decision_records_closed_source_and_math',all(not e['indicator']['open_candle_used'] and e['indicator']['effective_time']==e['bar_time'] and e['indicator']['consumed_data_hash']==e['source_readiness']['consumed_data_hash'] and e['query']['state']=='READY' for e in all_applied))
        report['manual_sentinel_sha256']=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest();report['final_bot_object']=bot.get(did)
        trace=[json.loads(line) for line in (OUT/'http-trace.jsonl').read_text(encoding='utf-8').splitlines()]
        check('actual_adapter_http_calls_recorded',any(r['method']=='POST' and '/drawings?' in r['path'] for r in trace) and any(r['method']=='PATCH' for r in trace) and any(r['path'].endswith('/queries') for r in trace) and any('/indicator-queries' in r['path'] for r in trace))
        check('no_account_or_order_capability_used',not (folder/'execution.db').exists() and all('/account' not in r['path'] and '/orders' not in r['path'] for r in trace))
        check('public_market_requests_only',all(r['method']=='GET' and r['path'] in ('/fapi/v1/time','/fapi/v1/exchangeInfo','/fapi/v1/klines') for r in report['public_requests']))
        check('observed_sources_unchanged',all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in source_hashes.items()))
        report.update(state='COMPLETED',passed=True,applied_decisions=len(all_applied),limitations=['Controlled subscription loss is not a claim of a real exchange outage.','No profitability, real order or physical UI acceptance claimed.'])
    except Exception:report.update(state='FAILED',error=traceback.format_exc())
    finally:
        if child and child.poll() is None:child.terminate();child.wait(timeout=10)
        if log:log.close()
        stop();human.close();report['elapsed_seconds']=round(time.time()-report['started_at'],1);save()
    print(json.dumps(dict(state=report['state'],passed=report['passed'],checks=len(report['checks']),error=report.get('error'))));return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
