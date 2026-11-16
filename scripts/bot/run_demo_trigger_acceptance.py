"""Bounded native stop/target observation; real Demo prices only, no synthetic triggers."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from dataclasses import asdict
from datetime import datetime,timezone
from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.bot.run_bounded_demo_acceptance import AcceptanceRunner,make_plan,test_limits,fresh_snapshot,flatten_owned
from agentrader.shared.config import Config
from agentrader.shared.exchange import DemoExchange
from agentrader.bot.execution import TERMINAL
from agentrader.shared.locking import execution_lock
from agentrader.bot.plans import PlanService
from agentrader.bot.risk import RiskLimits,number
from agentrader.shared.state import StateStore
from agentrader.bot.v2_preflight import prepare_single
import getpass


def trigger_plan(snapshot,kind,run_id):
    if kind not in ('STOP','TARGET'):raise ValueError('UNKNOWN_TRIGGER_CASE')
    p=make_plan(snapshot,'LONG','IMMEDIATE',run_id)
    p['plan_id']=f'trigger-{run_id}-{kind}'
    mark=number(snapshot['mark']['markPrice'])
    tick=number(next(f for f in snapshot['symbol_info']['filters'] if f['filterType']=='PRICE_FILTER')['tickSize'])
    if kind=='STOP':p['stop']=str((mark*Decimal('.9985')/tick).to_integral_value(rounding=ROUND_FLOOR)*tick)
    else:p['targets'][0]['price']=str((mark*Decimal('1.0015')/tick).to_integral_value(rounding=ROUND_CEILING)*tick)
    p['expires_at']=datetime.fromtimestamp(time.time()+600,timezone.utc).isoformat()
    p['rationale']='Explicitly authorized small Demo native trigger observation; no price manipulation; timeout is not success.'
    return p


def native_result(proposals,responses):
    """Only a terminal exchange algo with a real generated order proves a trigger."""
    found=[]
    for p,r in zip(proposals,responses):
        params=p['params']
        if any(r.get(k)!=params[k] for k in ('clientAlgoId','symbol','side','positionSide')):
            raise ValueError('TRIGGER_IDENTITY_MISMATCH')
        if (r.get('orderType')!=params['type'] or number(r.get('triggerPrice','0'))!=number(params['triggerPrice'])
                or str(r.get('closePosition')).lower()!='true' or r.get('workingType')!='MARK_PRICE'):
            raise ValueError('TRIGGER_CONTENT_MISMATCH')
        if r.get('algoStatus')=='FINISHED' and r.get('actualOrderId') not in (None,'',0,'0'):
            found.append(dict(kind='STOP' if params['type']=='STOP_MARKET' else 'TARGET',algo_id=r.get('algoId'),order_id=r['actualOrderId']))
    return found


def verify_generated_fill(trigger,order,session):
    expected=session['prepared']['entry']['params']
    if (str(order.get('orderId'))!=str(trigger['order_id']) or order.get('symbol')!=session['symbol']
            or order.get('side')!=('SELL' if expected['side']=='BUY' else 'BUY')
            or order.get('positionSide')!=expected['positionSide'] or order.get('status')!='FILLED'
            or not 0<number(order.get('executedQty','0'))<=number(expected['quantity'])):
        raise ValueError('TRIGGERED_ORDER_FILL_NOT_PROVEN')


def inherited_limits(previous,account_ref,now_ms):
    if previous.get('state')!='PASSED' or previous.get('final_flat') is not True or previous['account_ref']!=account_ref:
        raise ValueError('VERIFIED_PREVIOUS_ACCOUNT_REQUIRED')
    previous_day=datetime.fromtimestamp(previous['started_at'],timezone.utc).date()
    if datetime.fromtimestamp(now_ms/1000,timezone.utc).date()!=previous_day:raise ValueError('TEST_BUDGET_UTC_DAY_CHANGED')
    limits=test_limits(previous['initial_daily_loss'])
    if str(limits.max_daily_loss)!=previous['limits']['max_daily_loss']:raise ValueError('TEST_BUDGET_MISMATCH')
    return limits


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute-demo',action='store_true')
    parser.add_argument('--budget-report',type=Path,default=Path('reports/bounded-demo-acceptance-0441916fb777.json'))
    args=parser.parse_args()
    if not args.execute_demo:parser.error('--execute-demo required')
    previous=json.loads(args.budget_report.read_text(encoding='utf-8'));run_id=uuid.uuid4().hex[:12]
    path=Path(f'reports/demo-trigger-acceptance-{run_id}.json')
    report=dict(schema='demo-trigger-acceptance/1',run_id=run_id,started_at=time.time(),environment='demo',state='PREPARING',
                inherited_budget_report=str(args.budget_report),cases=[],new_loss_allowance='0',default_risk_changed=False)
    def save():path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    save()
    with execution_lock():
        store=StateStore(Path('data/execution.sqlite3'));x=DemoExchange(Config.load());owner='local:'+getpass.getuser()
        service=PlanService(store,owner);runner=None;halt=store.halt_reason();deadline=time.time()+600
        try:
            if store.sessions() or store.unresolved_account_command() or any(v['state'] not in TERMINAL for v in store.intents()):
                raise ValueError('LOCAL_IDLE_TERMINAL_HISTORY_REQUIRED')
            snapshot=fresh_snapshot(x,'BTCUSDT',RiskLimits.load('risk-demo.json'))
            ref=hashlib.sha256(x.config.api_key.encode()).hexdigest()
            limits=inherited_limits(previous,ref,snapshot['now_ms']);runner=AcceptanceRunner(service,x,limits)
            report.update(account_ref=ref,initial_daily_loss=snapshot['daily_loss'],limits={k:str(v) for k,v in asdict(limits).items()},expires_at=deadline)
            with sqlite3.connect(f'reports/demo-trigger-before-{run_id}.sqlite3') as target:store.db.backup(target)
            store.event('demo_trigger_test_authorized',dict(run_id=run_id,ceiling=str(limits.max_daily_loss),expires_at=deadline))
            save()
            for kind in ('STOP','TARGET'):
                if time.time()>deadline:raise ValueError('TEST_WINDOW_EXPIRED')
                snapshot=fresh_snapshot(x,'BTCUSDT',limits)
                p=trigger_plan(snapshot,kind,run_id);prepared=prepare_single(p,snapshot,limits)
                if prepared['state']!='READY':raise ValueError('PREFLIGHT_NOT_READY')
                case=dict(requested_trigger=kind,plan=p,prepared=prepared,state='PREPARED',samples=[])
                report['cases'].append(case);save()
                created=service.create(p,owner);service.authorize(p['plan_id'],1,created['authorization_token'],'approve',owner,300)
                if time.time()>deadline:raise ValueError('TEST_WINDOW_EXPIRED')
                store.clear_halt()
                try:
                    case['open_result']=runner.open(p['plan_id'],1,execute=True);save()
                    sessions=[s for s in store.sessions() if s['plan']['plan_id']==p['plan_id']]
                    if not sessions:
                        case['state']='NO_NATIVE_OBSERVATION'
                    else:
                        s=sessions[0];case['session_id']=s['id'];until=min(deadline,time.time()+90)
                        triggered=[]
                        while time.time()<until:
                            responses=[x.get(v['path'],{'clientAlgoId':v['params']['clientAlgoId']}) for v in s['protections'] if store.intent(v['params']['clientAlgoId'])]
                            if len(responses)!=len(s['protections']):break
                            triggered=native_result(s['protections'],responses)
                            case['samples'].append(dict(observed_at=time.time(),responses=responses));save()
                            if triggered:break
                            time.sleep(1)
                        case['native_triggers']=triggered
                        if triggered:
                            case['triggered_orders']=[x.get('/fapi/v1/order',{'symbol':s['symbol'],'orderId':v['order_id']}) for v in triggered]
                            for trigger,order in zip(triggered,case['triggered_orders']):verify_generated_fill(trigger,order,s)
                            runner.manage(s['id'],execute=True)
                        if any(v['id']==s['id'] for v in store.sessions()):flatten_owned(runner,s['id'])
                        case['state']=('PASSED' if any(v['kind']==kind for v in triggered) else 'OTHER_NATIVE_TRIGGER' if triggered else 'TIMEOUT_CLEANED')
                    final=fresh_snapshot(x,'BTCUSDT',limits);case.update(flat_after=True,daily_loss_after=final['daily_loss'])
                finally:store.halt('Demo trigger test gate; no unattended entries.');save()
            report['state']='PASSED' if all(c['state']=='PASSED' for c in report['cases']) else 'PARTIAL'
        except Exception as exc:
            report.update(state='STOPPED',error_type=type(exc).__name__)
            if isinstance(exc,ValueError):report['reason']=str(exc)[:200]
        finally:
            if runner:
                for s in list(store.sessions()):
                    if s.get('plan',{}).get('plan_id','').startswith('trigger-'+run_id+'-'):
                        try:flatten_owned(runner,s['id'])
                        except Exception as exc:report['cleanup_error_type']=type(exc).__name__
            store.halt(halt or 'Demo trigger test complete; new entries require next authorized test.')
            try:
                final=fresh_snapshot(x,'BTCUSDT',RiskLimits.load('risk-demo.json'))
                report.update(final_flat=True,final_daily_loss=final['daily_loss'])
            except Exception:report['final_flat']=False
            report.update(active_sessions=len(store.sessions()),halt_restored=bool(store.halt_reason()),finished_at=time.time());save();store.close()
    print(json.dumps(dict(report=str(path),state=report['state'],final_flat=report.get('final_flat')),ensure_ascii=False))
    return 0 if report.get('final_flat') else 1


if __name__=='__main__':raise SystemExit(main())
