"""Actual Demo chart drawing -> live closed-candle event -> reviewed LIMIT entry.

Original chart API/worker stays running. A temporary loopback GET-only preview
endpoint supplies the same persisted event under the inherited small risk profile.
The independent guardian is a separate OS process, never bypassed.
"""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
from contextlib import closing
from dataclasses import asdict
from datetime import datetime,timezone
from decimal import Decimal,ROUND_FLOOR
import getpass
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import httpx
import uvicorn
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from agentrader.application.settings import WebSettings
from agentrader.chart.chart_bindings import BindingService
from agentrader.integration.chart_execution import review_preview,guard_chart_entry,require_demo_acceptance
from agentrader.chart.chart_market import ChartMarket
from agentrader.shared.config import Config
from agentrader.chart.drawings.service import DrawingService
from agentrader.shared.exchange import DemoExchange
from agentrader.bot.execution import TERMINAL
from agentrader.shared.locking import execution_lock
from agentrader.shared.market_feed import MarketFeedHub
from agentrader.bot.plans import PlanService
from agentrader.integration.preview_preflight import local_preview_provider,preflight_preview
from agentrader.bot.recovery_guardian import status,require_guardian
from agentrader.bot.risk import RiskLimits,number
from agentrader.integration.shadow_tracking import ShadowTracking
from agentrader.integration.signal_previews import SignalPreviews
from agentrader.shared.state import StateStore
from scripts.bot.run_bounded_demo_acceptance import AcceptanceRunner,fresh_snapshot,make_plan,flatten_owned
from scripts.bot.run_demo_trigger_acceptance import inherited_limits


def calibration_geometry(context,run_id):
    rows=[r for r in context['rows'] if r['closed']]
    if len(rows)<2:raise ValueError('CLOSED_REAL_BARS_REQUIRED')
    tick=number(context['market']['tick_size']);price=number(rows[-1]['exact']['close'])+tick
    anchor=next((r['time'] for r in reversed(rows) if r['time']%900==0),rows[-1]['time'])
    return dict(kind='horizontal',symbol='BTCUSDT',price_source='LAST_PRICE',
                label='Demo bot bağ testi '+run_id,anchors=[dict(time=anchor,price=str(price))])


def preview_inputs(snapshot,run_id):
    # Explicit technical operator inputs, not an autonomous trading strategy.
    p=make_plan(snapshot,'LONG','LIMIT',run_id)
    return dict(direction='LONG',entry_price=p['entry']['trigger_price'],stop=p['stop'],target=p['targets'][0]['price'],
                notional=p['sizing']['amount'],leverage=p['execution']['leverage'],margin_mode=p['execution']['margin_mode'],
                position_mode=p['position_mode'],max_drift_bps='50',ttl_seconds=300)


def chart_session(sessions,plan_id):
    matches=[s for s in sessions if s.get('engine')=='v2' and s.get('plan',{}).get('plan_id')==plan_id]
    if len(matches)!=1:raise ValueError('CHART_ENTRY_SESSION_EVIDENCE_REQUIRED')
    return matches[0]


def start_preview_server(previews,port):
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    @app.middleware('http')
    async def boundary(request,call_next):
        host='127.0.0.1:'+str(port)
        if request.headers.get('host')!=host or request.headers.get('origin') not in (None,'http://'+host):
            return JSONResponse(dict(error='LOCAL_BOUNDARY_REQUIRED'),status_code=403)
        return await call_next(request)
    @app.get('/api/workspaces/{workspace}/shadow-events/{event}/preview')
    def show(workspace:str,event:str,version:int):
        return previews.show(workspace,event,version)
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error',access_log=False))
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    return server,thread


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute-demo',action='store_true');args=parser.parse_args()
    if not args.execute_demo:parser.error('--execute-demo required')
    run_id=uuid.uuid4().hex[:12];path=Path(f'reports/live-chart-entry-{run_id}.json')
    r=dict(schema='live-chart-entry-acceptance/1',run_id=run_id,started_at=time.time(),state='PREPARING',
           environment='demo',new_loss_allowance='0',autonomous_strategy=False,default_risk_changed=False)
    def save():path.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8')
    save();settings=WebSettings.load();x=DemoExchange(Config.load());guardian=None;guardian_log=None
    hub=None;feed=None;server=None;server_thread=None;binding=None;runner=None;store=None;old_halt=None;profile=None
    settings_owner=settings.owner;deadline=time.time()+900
    try:
        require_demo_acceptance()
        # Verify the real chart terminal/worker; never start a duplicate shadow writer.
        with httpx.Client(base_url='http://127.0.0.1:8765',timeout=15,trust_env=False) as client:
            health=client.get('/api/health').json()
        if not health['shadow_tracking']['worker_running'] or health['market_environment']!='demo_public':
            raise ValueError('REAL_DEMO_CHART_WORKER_REQUIRED')
        with execution_lock():
            store=StateStore(settings.execution_database);old_halt=store.halt_reason()
            if store.sessions() or store.unresolved_account_command() or any(v['state'] not in TERMINAL for v in store.intents()):
                raise ValueError('IDLE_TERMINAL_HISTORY_REQUIRED')
            snapshot=fresh_snapshot(x,'BTCUSDT',RiskLimits.load('risk-demo.json'))
            previous=json.loads(Path('reports/bounded-demo-acceptance-0441916fb777.json').read_text(encoding='utf-8'))
            limits=inherited_limits(previous,hashlib.sha256(x.config.api_key.encode()).hexdigest(),snapshot['now_ms'])
            r.update(account_ref=previous['account_ref'],initial_daily_loss=snapshot['daily_loss'],limits={k:str(v) for k,v in asdict(limits).items()})
            with closing(sqlite3.connect(f'reports/live-chart-entry-before-{run_id}.sqlite3')) as backup:store.db.backup(backup)
            store.close();store=None
        profile=Path(f'reports/live-chart-risk-{run_id}.json');profile.write_text(json.dumps(r['limits']),encoding='utf-8')
        guardian_log=Path(f'reports/live-chart-guardian-{run_id}.log').open('w',encoding='utf-8')
        guardian=subprocess.Popen([sys.executable,'-m','agentrader','service','guardian','--execute-demo','--risk-profile',str(profile)],
            stdout=guardian_log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        until=time.time()+40
        while time.time()<until and not status(settings.execution_database)['entry_ready']:
            if guardian.poll() is not None:raise ValueError('GUARDIAN_START_FAILED')
            time.sleep(.5)
        if not status(settings.execution_database)['entry_ready']:raise ValueError('GUARDIAN_NOT_ARMED')
        r['guardian_pid']=guardian.pid;save()
        hub=MarketFeedHub(ChartMarket(settings.market_database));feed=hub.acquire('BTCUSDT','1m')
        until=time.time()+60;context=None
        while time.time()<until:
            context=hub.binding_context('BTCUSDT','1m')
            if context and context['transport_state']=='LIVE' and context['data_proof']['state']=='VERIFIED':break
            time.sleep(.5)
        if not context or context['transport_state']!='LIVE':raise ValueError('LIVE_DEMO_CONTEXT_REQUIRED')
        drawings=DrawingService(settings.application_database,settings_owner);bindings=BindingService(settings.application_database,settings_owner)
        geometry=calibration_geometry(context,run_id)
        drawing=drawings.create('main','chart-acceptance-draw-'+run_id,geometry)
        binding_id='live-test-'+run_id
        binding=bindings.save_binding('main',binding_id,'chart-acceptance-bind-'+run_id,0,
            dict(type='drawing',object_id=drawing['drawing_id'],revision=drawing['revision']), 'BTCUSDT','1m','LINEAR',
            [v['time'] for v in context['rows'] if v['closed']],None,
            dict(operation='priceAt',output='value',ratio=None),
            dict(schema='chart-rule-definition/1',kind='touch',direction='ANY',tolerance='0',closed_candle=True,rearm_policy='EXPLICIT'))
        shadow=ShadowTracking(settings.application_database,settings_owner)
        shadow.command('main',binding_id,1,binding['definition_hash'],'start',900)
        r.update(drawing_id=drawing['drawing_id'],geometry=geometry,binding_id=binding_id,state='WAITING_REAL_CLOSED_TOUCH');save()
        event=None;until=min(deadline,time.time()+300)
        while time.time()<until:
            observed=shadow.status('main',binding_id);r['shadow_run']=observed['run'];save()
            if observed['events']:event=observed['events'][0];break
            time.sleep(1)
        if event is None:raise ValueError('NO_REAL_TOUCH_WITHIN_OBSERVATION_WINDOW')
        r.update(state='REAL_SHADOW_EVENT',event=event);save()
        # Dedicated public, credential-free GET source for this scoped risk profile.
        previews=SignalPreviews(settings.application_database,settings_owner,hub,limits=limits)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server,server_thread=start_preview_server(previews,port)
        until=time.time()+10
        while not server.started and time.time()<until:time.sleep(.1)
        if not server.started:raise ValueError('SCOPED_PREVIEW_SERVER_UNAVAILABLE')
        r['preview_port']=port
        with execution_lock():
            store=StateStore(settings.execution_database);service=PlanService(store,settings_owner);runner=AcceptanceRunner(service,x,limits)
            require_guardian(store.path,settings_owner,x,limits)
            snapshot=fresh_snapshot(x,'BTCUSDT',limits);inputs=preview_inputs(snapshot,run_id)
            preview=previews.create('main',event['event_id'],0,inputs)
            r.update(preview_version=preview['version'],preview_hash=preview['content_hash'],inputs=inputs,state='PREVIEW_CREATED');save()
            provider=local_preview_provider('main',event['event_id'],preview['version'],port)
            def checked_preflight(provider,exchange,limits,**kwargs):
                return preflight_preview(provider,exchange,limits,collect=fresh_snapshot,**kwargs)
            reviewed=review_preview(service,provider,x,limits,workspace='main',event_id=event['event_id'],version=preview['version'],
                port=port,preflight=checked_preflight)
            r.update(plan_id=reviewed['plan']['plan_id'],plan_digest=reviewed['digest'],state='REVIEWED_PENDING_APPROVAL');save()
            guard_chart_entry(service,x,limits,reviewed['plan']);require_guardian(store.path,settings_owner,x,limits)
            service.authorize(r['plan_id'],1,reviewed['authorization_token'],'approve',settings_owner,300)
            if time.time()>deadline:raise ValueError('TEST_WINDOW_EXPIRED')
            store.clear_halt();r['open_result']=runner.open(r['plan_id'],1,execute=True);r['state']='CHART_ENTRY_SUBMITTED';save()
            s=chart_session(store.sessions()+store.sessions(active=False),r['plan_id'])
            r['session_id']=s['id'];r['exchange_entry']=runner._entry(s);save()
            if s['active']:
                flatten_owned(runner,s['id'])
            final=fresh_snapshot(x,'BTCUSDT',limits)
            r.update(state='PASSED',final_flat=True,final_daily_loss=final['daily_loss']);save()
            store.halt(old_halt or 'Chart entry test complete; new entries paused.');store.close();store=None
    except Exception as exc:
        r.update(state='STOPPED',error_type=type(exc).__name__)
        if isinstance(exc,ValueError):r['reason']=str(exc)[:200]
        if hasattr(exc,'code'):r['reason_code']=exc.code
    finally:
        # The main execution lease must cover both cleanup and halt restoration.
        if store:store.close();store=None
        try:
            with execution_lock():
                store=StateStore(settings.execution_database);service=PlanService(store,settings_owner)
                if 'limits' in locals():
                    runner=AcceptanceRunner(service,x,limits)
                    for s in list(store.sessions()):
                        if s.get('plan',{}).get('plan_id')==r.get('plan_id'):
                            flatten_owned(runner,s['id'])
                store.halt(old_halt or 'Chart test finished; new entries remain paused.')
                final=fresh_snapshot(x,'BTCUSDT',RiskLimits.load('risk-demo.json'))
                r.update(final_flat=True,final_daily_loss=final['daily_loss'],active_sessions=len(store.sessions()),halt_restored=bool(store.halt_reason()))
                store.close();store=None
        except Exception as exc:r.update(final_flat=False,cleanup_error_type=type(exc).__name__)
        if binding:
            try:
                # Stop the source after the test; preserve drawing/event evidence.
                current=shadow.status('main',binding['binding_id'])['run']
                if current and current['state'] in ('WATCHING','WAITING_DATA','PAUSED'):
                    shadow.command('main',binding['binding_id'],1,binding['definition_hash'],'pause',900)
            except Exception as exc:r['source_stop_error_type']=type(exc).__name__
        if server:
            server.should_exit=True
            if server_thread:server_thread.join(timeout=20)
        if hub:hub.close()
        if guardian and r.get('final_flat') and not r.get('active_sessions'):
            guardian.terminate()
            try:guardian.wait(timeout=15)
            except subprocess.TimeoutExpired:pass
        if guardian_log:guardian_log.close()
        r['guardian_left_running']=guardian is not None and guardian.poll() is None
        if profile and not r['guardian_left_running']:
            profile.unlink(missing_ok=True);r['temporary_profile_removed']=True
        r['finished_at']=time.time();save()
    print(json.dumps(dict(report=str(path),state=r['state'],reason=r.get('reason'),reason_code=r.get('reason_code'),final_flat=r.get('final_flat')),ensure_ascii=True))
    return 0 if r['state']=='PASSED' and r.get('final_flat') else 1


if __name__=='__main__':raise SystemExit(main())
