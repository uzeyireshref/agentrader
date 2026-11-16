"""Read-only, owner-bound local operations snapshot. No credentials or network."""
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import time
from decimal import Decimal

from agentrader.application.queries import StorageUnavailable
from agentrader.shared.product_registry import EXECUTION_CONTEXT

STATES=set('PREPARED SUBMITTING UNKNOWN READ_FAILED ACKNOWLEDGED APPLIED REJECTED NOT_SENT CANCELED EXPIRED FINAL_WITH_ERRORS SUPERSEDED NEW PARTIALLY_FILLED FILLED EXPIRED_IN_MATCH ACTIVE RESERVED SUBMITTED RELEASED DISABLED ARMED DISABLE_FAILED REFRESH_FAILED'.split())
PENDING={'SUBMITTING','UNKNOWN','READ_FAILED','ACKNOWLEDGED'}
MAX_ROWS=10000


def _counts(db,tables,table,where='',params=()):
    if table not in tables:return {}
    if db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]>MAX_ROWS:raise ValueError('OPERATION_SNAPSHOT_TOO_LARGE')
    result={}
    for state,count in db.execute(f'SELECT state,COUNT(*) FROM {table} {where} GROUP BY state',params):
        label=state if state in STATES else 'UNRECOGNIZED'
        result[label]=result.get(label,0)+count
    return result


def _budget(database,now):
    p=Path(database)
    if not p.exists():return dict(storage='NOT_INITIALIZED',active_cooldowns=0,max_wait_seconds=0,clock_backwards=False)
    with closing(sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        waits=[]
        if 'pool_cooldowns' in tables:
            waits=[r[0]-now for r in db.execute("SELECT until_ts FROM pool_cooldowns WHERE pool LIKE 'futures:demo:%' AND until_ts>?",(now,))]
        if 'host_limits' in tables:
            waits += [r[0]-now for r in db.execute("SELECT until_ts FROM host_limits WHERE host IN ('demo-fapi.binance.com','demo-dapi.binance.com','testnet.binancefuture.com') AND until_ts>?",(now,))]
        if any(not math.isfinite(v) for v in waits):raise ValueError('OPERATION_BUDGET_TIME_INVALID')
        clock_row=db.execute('SELECT last_ts FROM rate_clock WHERE id=1').fetchone() if 'rate_clock' in tables else None
        if clock_row and not math.isfinite(clock_row[0]):raise ValueError('OPERATION_BUDGET_CLOCK_INVALID')
        return dict(storage='AVAILABLE',active_cooldowns=len(waits),max_wait_seconds=round(max(waits,default=0),3),clock_backwards=bool(clock_row and clock_row[0]>now))


def _unattributed_ws(db,tables):
    """A historical lost receipt is resolved only by an exact business identity.

    Unlinked/unsupported delivery families stay visible for review; a receipt
    alone cannot prove a business outcome. No journal is modified here.
    """
    if 'ws_deliveries' not in tables:return 0
    rows=db.execute("SELECT identity,account_ref,method,path FROM ws_deliveries WHERE state IN ('SUBMITTING','UNKNOWN') LIMIT 1001").fetchall()
    if len(rows)>1000:raise ValueError('OPERATION_WS_REVIEW_TOO_LARGE')
    if not rows:return 0
    from agentrader.shared.ws_orders import identity
    accounts={r[1] for r in rows};matched=set();bindings={}
    sessions=db.execute('SELECT session_id,body FROM managed_sessions LIMIT 10001').fetchall()
    if len(sessions)>MAX_ROWS:raise ValueError('OPERATION_IDENTITY_REVIEW_TOO_LARGE')
    for sid,body in sessions:
        s=json.loads(body)
        if s.get('id')!=sid or not s.get('account_ref'):continue
        def bind(path,p):
            cid=p.get('newClientOrderId',p.get('clientAlgoId'))
            if cid and p.get('symbol'):bindings.setdefault((path,cid,p['symbol']),set()).add(s['account_ref'])
        if s.get('entry_id') and s.get('symbol'):bind('/fapi/v1/order',dict(newClientOrderId=s['entry_id'],symbol=s['symbol']))
        for proposal in s.get('protections',[])+s.get('exits',[]):
            if isinstance(proposal,dict) and isinstance(proposal.get('params'),dict):bind(proposal.get('path'),proposal['params'])
    known=db.execute("SELECT path,params FROM intents WHERE state IN ('NEW','PARTIALLY_FILLED','FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED')").fetchall()
    for path,params in known:
        if path not in ('/fapi/v1/order','/fapi/v1/algoOrder'):continue
        p=json.loads(params)
        if not isinstance(p,dict):raise ValueError('OPERATION_INTENT_PARAMS_INVALID')
        cid=p.get('newClientOrderId',p.get('clientAlgoId'))
        owners=bindings.get((path,cid,p.get('symbol')),set())
        if len(owners)==1:
            account=next(iter(owners))
            if account in accounts:matched.add(identity(account,'POST',path,p))
    if 'order_modifications' in tables:
        amendments=db.execute("SELECT body FROM order_modifications WHERE state IN ('APPLIED','SUPERSEDED','REJECTED')").fetchall()
        if len(amendments)>MAX_ROWS:raise ValueError('OPERATION_AMENDMENT_REVIEW_TOO_LARGE')
        for body, in amendments:
            b=json.loads(body)
            account=b.get('account_ref')
            if account in accounts:
                p=dict(symbol=b['before_params']['symbol'],origClientOrderId=b['client_id'],modifyId=b['modify_id'])
                matched.add(identity(account,'PUT','/fapi/v1/order',p))
    return sum(r[0] not in matched for r in rows)


def operation_status(database,owner,*,governor_database=Path('data/request-governor.sqlite3'),clock=time.time):
    now=clock()
    if type(now) not in (int,float) or not math.isfinite(now) or now<0:raise StorageUnavailable('OPERATIONS_CLOCK_INVALID')
    result=dict(schema='local-operations/1',observed_at=now,observation='LOCAL_ONLY',exchange_access='NOT_CHECKED',
                financial_execution_authorized=False,trading_readiness='UNPROVEN',read_only=True)
    p=Path(database)
    if not p.exists():return result|dict(storage='NOT_INITIALIZED',health='NOT_OBSERVED')
    try:
        with closing(sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
            db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
            # Bound total work on malformed or unexpectedly large journals.
            steps=[0]
            def progress():
                steps[0]+=1
                return int(steps[0]>2000)
            db.set_progress_handler(progress,1000)
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'execution_namespace' not in tables:return result|dict(storage='CONTEXT_UNVERIFIED',health='NOT_OBSERVED')
            rows=db.execute('SELECT body FROM execution_namespace').fetchall()
            if len(rows)!=1 or json.loads(rows[0][0])!=EXECUTION_CONTEXT:return result|dict(storage='CONTEXT_MISMATCH',health='NOT_OBSERVED')
            if 'discovery_contexts' in tables or not {'control','intents','managed_sessions'}<=tables:
                return result|dict(storage='INCOMPLETE_SCHEMA',health='NOT_OBSERVED')
            row=db.execute("SELECT value FROM control WHERE name='plan_owner'").fetchone()
            if not row or row[0]!=owner:return result|dict(storage='OWNER_UNVERIFIED' if not row else 'OWNER_MISMATCH',health='NOT_OBSERVED')
            halted=bool(db.execute("SELECT 1 FROM control WHERE name='halt'").fetchone())
            commands=_counts(db,tables,'exchange_commands','WHERE owner=?',(owner,))
            intents=_counts(db,tables,'intents')
            amendments=_counts(db,tables,'order_modifications')
            settings=_counts(db,tables,'account_commands')
            margin=_counts(db,tables,'margin_commands')
            timers=_counts(db,tables,'cancel_timers','WHERE owner=?',(owner,))
            reservations=_counts(db,tables,'risk_reservations')
            ws=_counts(db,tables,'ws_deliveries')
            ws_review=_unattributed_ws(db,tables)
            projection_conflicts=0
            if 'order_projection' in tables:
                if db.execute('SELECT COUNT(*) FROM order_projection').fetchone()[0]>MAX_ROWS:raise ValueError('OPERATION_PROJECTIONS_TOO_LARGE')
                for status,fill,quantity in db.execute('SELECT status,filled,quantity FROM order_projection'):
                    f,q=Decimal(fill),Decimal(quantity)
                    if not f.is_finite() or not q.is_finite() or not 0<=f<=q or q<=0:raise ValueError('OPERATION_PROJECTION_INVALID')
                    if status not in ('UNKNOWN','NEW','PARTIALLY_FILLED','FILLED','CANCELED','EXPIRED','REJECTED') or (status=='REJECTED' and f>0):projection_conflicts+=1
            pending_stream=db.execute("SELECT count(*) FROM control WHERE name LIKE 'stream_pending:%'").fetchone()[0]
            ages=[];untimed=0
            if 'exchange_commands' in tables:
                for state,body in db.execute("SELECT state,body FROM exchange_commands WHERE owner=? AND state IN ('SUBMITTING','UNKNOWN','READ_FAILED')",(owner,)):
                    stamp=json.loads(body).get('created_at')
                    if type(stamp) not in (int,float) or not math.isfinite(stamp) or stamp<0:untimed+=1
                    elif stamp>now:untimed+=1
                    else:ages.append(now-stamp)
            sessions=db.execute('SELECT session_id,body FROM managed_sessions WHERE active=1 LIMIT 10001').fetchall()
            if len(sessions)>MAX_ROWS:raise ValueError('OPERATION_SESSIONS_TOO_LARGE')
            monitors={'FRESH':0,'STALE':0,'STOPPED':0,'NOT_OBSERVED':0}
            for sid,_ in sessions:
                row=db.execute('SELECT value FROM control WHERE name=?',('runtime_health:'+sid,)).fetchone()
                if not row:monitors['NOT_OBSERVED']+=1;continue
                h=json.loads(row[0]);stamp=h.get('observed_at')
                if type(stamp) not in (int,float) or not math.isfinite(stamp):raise ValueError('OPERATION_HEALTH_TIME_INVALID')
                stopped=h.get('service_stopped') is True or h.get('state') in ('CLOSED','MONITOR_STOPPED')
                monitors['STOPPED' if stopped else 'FRESH' if 0<=now-stamp<=90 else 'STALE']+=1
            counters={}
            if 'operation_counters' in tables:
                for kind,count in db.execute('SELECT kind,count FROM operation_counters'):
                    if kind in ('STREAM_RECONNECTING','STREAM_CONNECTED','STREAM_REST_RECONCILED'):
                        if type(count) is not int or count<0:raise ValueError('OPERATION_COUNTER_INVALID')
                        counters[kind]=count
            recovery=[];recovery_untimed=0
            if 'operation_timing' in tables and 'exchange_commands' in tables:
                for duration in db.execute('''SELECT t.recovery_seconds FROM operation_timing t JOIN exchange_commands c
                    ON c.command_id=t.command_id WHERE c.owner=? AND t.recovered_at IS NOT NULL''',(owner,)):
                    v=duration[0]
                    if v is None:recovery_untimed+=1
                    elif type(v) not in (int,float) or not math.isfinite(v) or v<0:raise ValueError('OPERATION_RECOVERY_TIME_INVALID')
                    else:recovery.append(v)
            faults=None
            if 'ws_deliveries' in tables and 'transport_faults' in {r[1] for r in db.execute('PRAGMA table_info(ws_deliveries)')}:
                faults=db.execute('SELECT COALESCE(SUM(transport_faults),0) FROM ws_deliveries').fetchone()[0]
            unresolved=(sum(commands.get(s,0) for s in PENDING)+sum(intents.get(s,0) for s in ('SUBMITTING','UNKNOWN'))+
                        sum(amendments.get(s,0)+settings.get(s,0)+margin.get(s,0) for s in PENDING)+pending_stream+
                        sum(timers.get(s,0) for s in ('SUBMITTING','UNKNOWN','DISABLE_FAILED','REFRESH_FAILED')))
            unrecognized=sum(c.get('UNRECOGNIZED',0) for c in (commands,intents,amendments,settings,margin,timers,reservations,ws))
            result.update(storage='AVAILABLE',scope='OWNER_EXECUTION_JOURNAL',entry_halted=halted,commands=commands,intents=intents,
                amendments=amendments,account_settings=settings,isolated_margin=margin,timers=timers,
                reservations=reservations,held_reservations=sum(n for s,n in reservations.items() if s!='RELEASED'),
                ws_delivery_history=ws,ws_transport_faults_since_instrumentation=faults,
                ws_unknown_without_business_resolution=ws_review,
                pending_stream_barriers=pending_stream,active_sessions=len(sessions),monitors=monitors,
                unresolved_record_count=unresolved,unrecognized_state_records=unrecognized,projection_conflicts=projection_conflicts,partial_batch_commands=commands.get('FINAL_WITH_ERRORS',0),
                oldest_unresolved_command_age_seconds=round(max(ages),3) if ages else None,
                unresolved_command_ages_unavailable=untimed,stream_counters_since_instrumentation=counters,
                recovery=dict(coverage='SINCE_INSTRUMENTATION',samples=len(recovery),untimed_samples=recovery_untimed,
                    max_seconds=round(max(recovery),3) if recovery else None))
        result['rate_budget']=_budget(governor_database,now)
        budget=result['rate_budget']
        attention=(halted or unresolved or ws_review or unrecognized or projection_conflicts or any(monitors[s] for s in ('STALE','STOPPED','NOT_OBSERVED'))
                   or budget['active_cooldowns'] or budget['clock_backwards'])
        result['health']='ATTENTION_REQUIRED' if attention else 'NO_LOCAL_BLOCKER_OBSERVED'
        return result
    except (sqlite3.Error,ValueError,TypeError,KeyError,AttributeError,ArithmeticError,OSError):
        raise StorageUnavailable('OPERATIONS_STORAGE_UNAVAILABLE') from None


def prometheus(report):
    """Fixed names and numeric values only: no account/owner/ID labels."""
    available=report.get('storage')=='AVAILABLE'
    values={'observed':int(available),'attention_required':int(report.get('health')!='NO_LOCAL_BLOCKER_OBSERVED')}
    if available:
        values.update(unresolved_records=report['unresolved_record_count'],held_reservations=report['held_reservations'],
            projection_conflicts=report['projection_conflicts'],
            ws_unknown_without_business_resolution=report['ws_unknown_without_business_resolution'],
            active_sessions=report['active_sessions'],partial_batch_commands=report['partial_batch_commands'],
            stale_monitors=report['monitors']['STALE'],unobserved_monitors=report['monitors']['NOT_OBSERVED'],
            cooldown_wait_seconds=report['rate_budget']['max_wait_seconds'],
            stream_reconnect_observations=report['stream_counters_since_instrumentation'].get('STREAM_RECONNECTING',0),
            recovery_samples=report['recovery']['samples'])
        for key,value in (('oldest_unresolved_command_age_seconds',report['oldest_unresolved_command_age_seconds']),
                          ('ws_transport_faults_since_instrumentation',report['ws_transport_faults_since_instrumentation']),
                          ('max_recovery_seconds',report['recovery']['max_seconds'])):
            if value is not None:values[key]=value
    return ''.join(f'# TYPE agentrader_operations_{k} gauge\nagentrader_operations_{k} {v}\n' for k,v in values.items())
