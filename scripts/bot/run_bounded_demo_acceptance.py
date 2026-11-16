"""One-shot, explicitly authorized Demo acceptance. Never changes the default risk file.

The real daily loss remains an input to every engine preflight. A fixed, audited
ceiling adds only 3 USDT to the initial loss, and is never rebased during this run.
"""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import getpass
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agentrader.shared.config import Config
from agentrader.shared.exchange import DemoExchange
from agentrader.bot.execution import TERMINAL
from agentrader.shared.locking import execution_lock
from agentrader.bot.order_rules import validate_order
from agentrader.bot.plans import PlanService
from agentrader.bot.risk import RiskLimits, number
from agentrader.shared.state import StateStore
from agentrader.bot.v2_preflight import collect_flat_snapshot, joint_step, prepare_single
from agentrader.bot.v2_runner import V2Runner


def fresh_snapshot(exchange,symbol,limits,**options):
    # A failed read-only collection may be repeated, never an order delivery.
    for attempt in range(3):
        try:return collect_flat_snapshot(exchange,symbol,limits,**options)
        except ValueError as exc:
            if str(exc)!='Hesap görünümü toplanırken eskidi.' or attempt==2:raise


class AcceptanceRunner(V2Runner):
    def _collect_snapshot(self,symbol,**options):
        return fresh_snapshot(self.x,symbol,self.limits,**options)


def test_limits(initial_loss):
    return replace(RiskLimits(), max_trade_loss=Decimal('1'),
                   max_total_loss=Decimal('1'), max_daily_loss=number(initial_loss)+Decimal('3'),
                   max_notional=Decimal('60'), max_positions=1)


def make_plan(snapshot, direction, condition, run_id):
    info=snapshot['symbol_info']; mark=number(snapshot['mark']['markPrice'])
    f={v['filterType']:v for v in info['filters']}; tick=number(f['PRICE_FILTER']['tickSize'])
    step=joint_step(f['LOT_SIZE']['stepSize'],f.get('MARKET_LOT_SIZE',f['LOT_SIZE'])['stepSize'])
    sign=1 if direction=='LONG' else -1
    def snap(v, up=False):
        return (v/tick).to_integral_value(rounding=ROUND_CEILING if up else ROUND_FLOOR)*tick
    entry=snap(mark*(1-Decimal('.003')*sign),direction=='SHORT') if condition=='LIMIT' else mark
    q=(max(number(f['LOT_SIZE']['minQty']),number(f.get('MARKET_LOT_SIZE',f['LOT_SIZE'])['minQty']),
           number(f['MIN_NOTIONAL']['notional'])/entry)/step).to_integral_value(rounding=ROUND_CEILING)*step
    # Include 1% sizing headroom so the engine's drift/fee reserve still buys the minimum lot.
    budget=(q*max(entry,mark)*Decimal('1.01')).quantize(Decimal('.01'),rounding=ROUND_CEILING)
    now=time.time(); stamp=lambda n:datetime.fromtimestamp(n,timezone.utc).isoformat()
    return dict(schema_version=2,plan_id=f'accept-{run_id}-{direction}-{condition}',version=1,
        environment='demo',exchange='binance',product='USD-M',symbol=info['symbol'],
        position_mode=snapshot['position_mode'],direction=direction,mode='A',created_at=stamp(now-1),expires_at=stamp(now+120),
        execution=dict(strategy='SINGLE',leverage=int(snapshot['settings']['leverage']),margin_mode=snapshot['settings']['marginType']),
        entry=dict(condition=condition,reference_price=str(entry),trigger_price=str(entry) if condition=='LIMIT' else None,max_drift_bps='50'),
        sizing=dict(kind='NOTIONAL',amount=str(budget),currency='USDT'),
        stop=str(snap(entry*(1-Decimal('.005')*sign),direction=='SHORT')),
        targets=[dict(price=str(snap(mark*(1+Decimal('.005')*sign),direction=='LONG')),fraction='1')],
        management=dict(break_even_after_target=None,allow_scale_in=False,allow_reverse=False,allow_reentry=False),max_runs=1,
        analysis_ref='operator-authorized-demo-acceptance',rationale='User authorized bounded Demo feature tests; sequential minimum lots, cleanup after each case.')


def flatten_owned(runner,sid):
    """Cancel remaining entry, then close only journal-proven owned fills."""
    s=runner._session(sid)
    runner.stop(sid,execute=True)
    if not any(v['id']==sid for v in runner.store.sessions()):return
    s=runner._session(sid); entry=runner._entry(s); algos={}
    for p in s['protections']:
        if runner.store.intent(p['params']['clientAlgoId']):
            algos[p['params']['clientAlgoId']]=runner.x.get(p['path'],{'clientAlgoId':p['params']['clientAlgoId']})
    amount=runner._owned(s,entry,algos)
    if amount:
        info=next(v for v in runner.x.get('/fapi/v1/exchangeInfo')['symbols'] if v['symbol']==s['symbol'])
        mark=runner.x.get('/fapi/v1/premiumIndex',{'symbol':s['symbol']})
        params=dict(symbol=s['symbol'],side='SELL' if amount>0 else 'BUY',positionSide=s['prepared']['entry']['params']['positionSide'],
                    type='MARKET',quantity=str(abs(amount)),newClientOrderId=runner._id(s,['acceptance-close',len(s['exits'])]))
        if s['plan']['position_mode']=='one-way':params['reduceOnly']='true'
        p=validate_order(params,info,s['plan']['position_mode'],'REDUCE',mark['markPrice'],int(time.time()*1000)+runner.x.offset_ms)
        s['exits'].append(p);runner._save(s);runner._post(s,p)
    runner.manage(sid,execute=True)


def run():
    parser=argparse.ArgumentParser();parser.add_argument('--execute-demo',action='store_true')
    parser.add_argument('--resume',type=Path,help='Resume only uncreated cases, preserving the original loss ceiling and deadline')
    parser.add_argument('--extend-read-recovery-window',action='store_true',help='One audited 300-second extension, same loss budget, after read latency repair')
    args=parser.parse_args()
    if not args.execute_demo:parser.error('Explicit --execute-demo required; this sends Demo orders.')
    run_id=uuid.uuid4().hex[:12]; path=Path(f'reports/bounded-demo-acceptance-{run_id}.json')
    report=dict(schema='bounded-demo-acceptance/1',run_id=run_id,environment='demo',started_at=time.time(),
                authority='User explicitly authorized Demo feature-test entries and risk-rule change in this conversation',
                additional_loss_budget='3',default_risk_changed=False,cases=[],state='PREPARING')
    def save():path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    if args.resume:
        path=args.resume;report=json.loads(path.read_text(encoding='utf-8'));run_id=report['run_id']
        if (report['schema']!='bounded-demo-acceptance/1' or report['state']!='STOPPED'
                or report.get('active_sessions')!=0):
            raise ValueError('RESUME_REQUIRES_IDLE_STOPPED_RUN')
        deadline=report['expires_at']
        if args.extend_read_recovery_window:
            if report.get('read_recovery_extension'):raise ValueError('READ_RECOVERY_EXTENSION_ALREADY_USED')
            report['read_recovery_extension']=dict(seconds=300,previous_deadline=deadline,reason='Independent metadata read latency repair; no added loss budget')
            deadline+=300;report['expires_at']=deadline
        if time.time()>deadline:raise ValueError('ORIGINAL_TEST_WINDOW_EXPIRED')
        report['previous_attempts']=report.get('previous_attempts',[])+[dict(state=report['state'],reason=report.get('reason'),finished_at=report['finished_at'])]
        report.pop('reason',None);report.pop('error_type',None)
        report['state']='RESUMING'
    else:deadline=time.time()+600
    save()
    with execution_lock():
        store=StateStore(Path('data/execution.sqlite3'));owner='local:'+getpass.getuser()
        x=DemoExchange(Config.load());service=PlanService(store,owner);runner=None;current=None
        previous_halt=store.halt_reason()
        try:
            if store.sessions() or store.unresolved_account_command():raise ValueError('LOCAL_RUNTIME_NOT_IDLE')
            if any(v['state'] not in TERMINAL for v in store.intents()):raise ValueError('UNRESOLVED_HISTORY')
            # Fresh flat proof is mandatory even if a previous final read expired.
            initial=fresh_snapshot(x,'BTCUSDT',RiskLimits.load('risk-demo.json'))
            if args.resume and hashlib.sha256(x.config.api_key.encode()).hexdigest()!=report['account_ref']:raise ValueError('RESUME_ACCOUNT_MISMATCH')
            limits=test_limits(report['initial_daily_loss'] if args.resume else initial['daily_loss']);runner=AcceptanceRunner(service,x,limits)
            report.update(account_ref=hashlib.sha256(x.config.api_key.encode()).hexdigest(),initial_daily_loss=report['initial_daily_loss'] if args.resume else initial['daily_loss'],
                          limits={k:str(v) for k,v in asdict(limits).items()},expires_at=deadline,previous_halt=previous_halt)
            backup=Path(f'reports/bounded-demo-before-{run_id}.sqlite3')
            import sqlite3
            if not args.resume:
                with sqlite3.connect(backup) as dst:store.db.backup(dst)
            store.event('bounded_demo_test_authorized',dict(run_id=run_id,limits=report['limits'],expires_at=deadline,previous_halt=previous_halt))
            save()
            for direction,condition in [('LONG','LIMIT'),('LONG','IMMEDIATE'),('SHORT','IMMEDIATE')]:
                if args.resume:
                    old=next((c for c in report['cases'] if c['direction']==direction and c['condition']==condition),None)
                    if old and old['state']=='PASSED':continue
                    pid=f'accept-{run_id}-{direction}-{condition}'
                    if store.db.execute('SELECT 1 FROM plan_versions WHERE plan_id=?',(pid,)).fetchone():
                        raise ValueError('EXISTING_PLAN_CANNOT_BE_REPLAYED')
                    if old:report['cases'].remove(old)
                if time.time()>deadline:raise ValueError('TEST_WINDOW_EXPIRED')
                snapshot=fresh_snapshot(x,'BTCUSDT',limits)
                if number(snapshot['daily_loss'])>=limits.max_daily_loss:raise ValueError('ADDITIONAL_TEST_BUDGET_EXHAUSTED')
                plan=make_plan(snapshot,direction,condition,run_id);prepared=prepare_single(plan,snapshot,limits)
                if prepared['state']!='READY':raise ValueError('PREFLIGHT_NOT_READY')
                case=dict(direction=direction,condition=condition,plan=plan,prepared=prepared,state='PREFLIGHT_PASSED')
                report['cases'].append(case);save()
                if time.time()>deadline:raise ValueError('TEST_WINDOW_EXPIRED_BEFORE_AUTHORIZATION')
                created=service.create(plan,owner)
                service.authorize(plan['plan_id'],1,created['authorization_token'],'approve',owner,120)
                # Release only after flat account, terminal history and full small-budget risk preflight.
                if time.time()>deadline:raise ValueError('TEST_WINDOW_EXPIRED_BEFORE_ENTRY')
                store.clear_halt()
                try:
                    result=runner.open(plan['plan_id'],1,execute=True);case['open_result']=result
                    sessions=[s for s in store.sessions() if s['plan']['plan_id']==plan['plan_id']]
                    current=sessions[0]['id'] if sessions else None
                    save()
                    if current:
                        case['observed_entry']=runner._entry(runner._session(current))
                        case['open_algo_orders']=x.get('/fapi/v1/openAlgoOrders')
                        flatten_owned(runner,current);current=None
                    final=fresh_snapshot(x,'BTCUSDT',limits)
                    case.update(state='PASSED',final_daily_loss=final['daily_loss'],flat_after=True)
                finally:
                    store.halt('Bounded Demo test gate: no unattended entries.')
                    save()
            report['state']='PASSED'
        except Exception as exc:
            report.update(state='STOPPED',error_type=type(exc).__name__)
            # Values only; never print a signed URL or transport exception text.
            if isinstance(exc,ValueError):report['reason']=str(exc)[:200]
        finally:
            if runner:
                for session in list(store.sessions()):
                    if session.get('plan',{}).get('plan_id','').startswith('accept-'+run_id+'-'):
                        try:flatten_owned(runner,session['id'])
                        except Exception as exc:report['cleanup_error_type']=type(exc).__name__
            store.halt(previous_halt or 'Demo acceptance complete; new entries require explicit next test.')
            try:
                final=fresh_snapshot(x,'BTCUSDT',RiskLimits.load('risk-demo.json'))
                report.update(final_flat=True,final_daily_loss=final['daily_loss'])
            except Exception:report['final_flat']=False
            report.update(active_sessions=len(store.sessions()),halt_restored=bool(store.halt_reason()),finished_at=time.time())
            save();store.close()
    print(json.dumps(dict(report=str(path),state=report['state'],final_flat=report.get('final_flat'),cases=[c['state'] for c in report['cases']]),ensure_ascii=False))
    return 0 if report['state']=='PASSED' and report.get('final_flat') else 1


if __name__=='__main__':raise SystemExit(run())
