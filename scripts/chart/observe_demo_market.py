"""Bounded, credential-free 30-minute demo data observer. No app/execution DB."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse,json,sys,tempfile,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from agentrader.chart.chart_market import ChartMarket
from agentrader.shared.market_feed import MarketFeedHub
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT


def observe(seconds=1800):
    output=ROOT/'reports/demo-observation-20261113.json'
    report=dict(schema='demo-observation/1',state='RUNNING',passed=None,started_at=datetime.now(timezone.utc).isoformat(),target_seconds=seconds,elapsed_seconds=0,source=SOURCE,environment=ENVIRONMENT,account_requests=0,order_requests=0,samples=0,live_samples=0,closed_events=[],issues=[],transitions=[],outages=[],violations=[])
    def save():
        temp=output.with_suffix('.json.tmp');temp.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');temp.replace(output)
    start=time.monotonic();hub=None;feed=None;previous=None;ready=False;seen=set();outage=None
    save()
    try:
        with tempfile.TemporaryDirectory(prefix='demo-observation-') as folder:
            hub=MarketFeedHub(ChartMarket(Path(folder)/'market.db'))
            feed=hub.acquire('BTCUSDT','1m')
            while time.monotonic()-start<seconds:
                packet=feed.state.packet(-1)
                age=time.monotonic()-start
                report['samples']+=1;report['elapsed_seconds']=round(age,1)
                assert packet['source']==SOURCE and packet['environment']==ENVIRONMENT
                status=packet['status']
                if status!=previous:report['transitions'].append(dict(at=round(age,1),state=status));previous=status
                valid=status=='LIVE' and (packet.get('data_proof') or {}).get('state')=='VERIFIED' and packet.get('timing',{}).get('state')=='FRESH'
                if valid:
                    ready=True;report['live_samples']+=1
                    if outage is not None:
                        duration=age-outage;report['outages'].append(dict(start=round(outage,1),end=round(age,1),seconds=round(duration,1)))
                        if duration>30:report['violations'].append('RECOVERY_EXCEEDED_30_SECONDS')
                        outage=None
                elif ready or age>30:
                    if outage is None:outage=age
                    if len(report['issues'])<200:report['issues'].append(dict(at=round(age,1),reason='NOT_FRESH_VERIFIED_LIVE',state=status,timing_reason=packet.get('timing',{}).get('reason'),quality=packet.get('quality')))
                close=packet.get('close_event')
                if valid and close and close['event_id'] not in seen:
                    if report['closed_events'] and close['time']-report['closed_events'][-1]['time']!=60:report['violations'].append('CLOSED_EVENT_GAP')
                    seen.add(close['event_id']);report['closed_events'].append(close)
                if report['samples']%10==0:save()
                time.sleep(min(1,max(0,seconds-(time.monotonic()-start))))
            hub.release(feed);hub.close();hub=None
        report['elapsed_seconds']=round(time.monotonic()-start,1)
        report['state']='COMPLETED'
        if outage is not None:
            duration=report['elapsed_seconds']-outage;report['outages'].append(dict(start=round(outage,1),end=report['elapsed_seconds'],seconds=round(duration,1)))
            if duration>30:report['violations'].append('RECOVERY_EXCEEDED_30_SECONDS')
        report['acceptance_policy']='DEMO_OBSERVATION_2: verified live closes, no internal close gap, each resync <=30s; raw outages retained'
        report['passed']=not report['violations'] and len(seen)>=max(1,seconds//60-1)
    except Exception as exc:
        report['state']='FAILED';report['passed']=False;report['issues'].append(dict(reason=type(exc).__name__))
    finally:
        if hub:hub.close()
        save()
    print(json.dumps(dict(state=report['state'],passed=report['passed'],elapsed_seconds=report['elapsed_seconds'],closes=len(seen))))
    return report['passed']

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=1800);args=parser.parse_args()
    if not 60<=args.seconds<=1800:parser.error('seconds must be 60..1800')
    sys.exit(0 if observe(args.seconds) else 1)
