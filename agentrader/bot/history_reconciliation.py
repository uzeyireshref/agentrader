"""GET-only, identity-checked terminal reconciliation. Never releases an entry halt."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import uuid

from agentrader.shared.exchange import allowed_requests
from agentrader.chart.chart_bindings import binding_hash
from agentrader.bot.demo_readiness import inventory
from agentrader.bot.execution import TERMINAL
from agentrader.bot.risk import number


class HistoryReads:
    def __init__(self,exchange):self.exchange=exchange;self.calls=[]

    @property
    def config(self):return self.exchange.config

    @property
    def offset_ms(self):return getattr(self.exchange,'offset_ms',0)

    def request(self,method,path,params=None):
        if method!='GET' or (method,path) not in allowed_requests():
            raise ValueError('HISTORY_RECONCILIATION_READ_ONLY')
        self.calls.append(dict(method=method,path=path))
        return self.exchange.request(method,path,params)

    def get(self,path,params=None):return self.request('GET',path,params)

    def sync_time(self):
        self.calls.append(dict(method='GET',path='/fapi/v1/time'))
        return self.exchange.sync_time()


def flat_proof(x,clock):
    start=clock()
    dual=x.get('/fapi/v1/positionSide/dual')['dualSidePosition']
    if type(dual) is not bool:raise ValueError('ACCOUNT_MODE_UNPROVEN')
    mode='hedge' if dual else 'one-way'
    a=inventory(x.get('/fapi/v3/account')['positions'],mode)
    b=inventory(x.get('/fapi/v3/positionRisk'),mode)
    normal=x.get('/fapi/v1/openOrders');algos=x.get('/fapi/v1/openAlgoOrders')
    if a!=b or a or b or not isinstance(normal,list) or not isinstance(algos,list) or normal or algos:
        raise ValueError('FLAT_ACCOUNT_PROOF_REQUIRED')
    if not 0<=clock()-start<=15:raise ValueError('FLAT_ACCOUNT_PROOF_EXPIRED')
    return dict(position_count=0,open_order_count=0,open_algo_count=0,position_mode=mode,started_at=start,verified_at=clock())


def local_snapshot(db,owner):
    db.row_factory=sqlite3.Row
    marker=db.execute("SELECT value FROM control WHERE name='plan_owner'").fetchone()
    if marker is None or marker[0]!=owner:raise ValueError('LOCAL_OWNER_MISMATCH')
    if db.execute('SELECT 1 FROM managed_sessions WHERE active=1').fetchone():raise ValueError('ACTIVE_SESSION_REQUIRES_MANAGER')
    if db.execute("SELECT 1 FROM plan_versions WHERE state IN ('EXECUTING','MANAGING','NEEDS_REVIEW')").fetchone():
        raise ValueError('BUSY_PLAN_REQUIRES_MANAGER')
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='risk_reservations'").fetchone():
        if db.execute("SELECT 1 FROM risk_reservations WHERE state!='RELEASED'").fetchone():raise ValueError('RESERVATION_REQUIRES_MANAGER')
    halted=db.execute("SELECT value FROM control WHERE name='halt'").fetchone()
    rows=[dict(r) for r in db.execute('SELECT * FROM intents ORDER BY client_id') if r['state'] not in TERMINAL]
    return dict(halt=halted[0] if halted else None,rows=rows)


def terminal_response(row,result):
    if not isinstance(result,dict):raise ValueError('INVALID_HISTORY_RESPONSE')
    p=json.loads(row['params']);old=json.loads(row['response']) if row['response'] else {}
    algo=row['path']=='/fapi/v1/algoOrder'
    if row['path'] not in ('/fapi/v1/order','/fapi/v1/algoOrder'):raise ValueError('UNSUPPORTED_INTENT_PATH')
    cid='clientAlgoId' if algo else 'clientOrderId';broker='algoId' if algo else 'orderId'
    kind='orderType' if algo else 'type';quantity='quantity' if algo else 'origQty'
    if (result.get(cid)!=row['client_id'] or result.get('symbol')!=p.get('symbol') or result.get('side')!=p.get('side')
            or result.get('positionSide')!=p.get('positionSide') or result.get(kind)!=p.get('type')
            or result.get(broker) in (None,'',0) or old.get(broker) is not None and str(result[broker])!=str(old[broker])):
        raise ValueError('HISTORY_ORDER_IDENTITY_MISMATCH')
    for key,target in (('quantity',quantity),('price','price'),('triggerPrice','triggerPrice')):
        if key in p and number(p[key])!=number(result[target]):raise ValueError('HISTORY_ORDER_CONTENT_MISMATCH')
    for key in ('reduceOnly','closePosition','workingType','algoType','timeInForce'):
        if key in p and str(p[key]).lower()!=str(result.get(key)).lower():raise ValueError('HISTORY_ORDER_CONTENT_MISMATCH')
        if key in ('reduceOnly','closePosition') and key not in p and key in old and str(old[key]).lower()!=str(result.get(key)).lower():
            raise ValueError('HISTORY_ORDER_CONTENT_MISMATCH')
    for key in ('executedQty','actualQty'):
        if key in result and (number(result[key])<0 or key in old and number(result[key])<number(old[key])):
            raise ValueError('HISTORY_FILL_REGRESSION')
    if old.get('updateTime') is not None and result.get('updateTime') is not None and result['updateTime']<old['updateTime']:
        raise ValueError('HISTORY_TIME_REGRESSION')
    state=result.get('algoStatus' if algo else 'status')
    if state not in TERMINAL-{'RESOLVED_FLAT'}:raise ValueError('HISTORY_NOT_TERMINAL')
    if not algo and state=='FILLED' and number(result.get('executedQty','0'))!=number(p['quantity']):
        raise ValueError('HISTORY_FILL_UNPROVEN')
    return state


def reconcile_terminal_history(settings,exchange,*,apply=False,backup_path=None,clock=time.time):
    """Caller holds execution_lock. Apply all verified terminals atomically, or none."""
    x=HistoryReads(exchange)
    report=dict(schema='demo-terminal-history-reconciliation/1',state='BLOCKED',apply_requested=apply,observed_at=clock(),
                changes=[],issues=[],order_requests=0,settings_changes=0,halt_cleared=False,execution_authorized=False)
    try:
        if not exchange.config.api_key or not exchange.config.api_secret:raise ValueError('DEMO_CREDENTIALS_REQUIRED')
        report['account_ref']=hashlib.sha256(exchange.config.api_key.encode()).hexdigest()
        uri=Path(settings.execution_database).resolve().as_uri()+'?mode=ro'
        with closing(sqlite3.connect(uri,uri=True,timeout=5)) as db:
            db.execute('PRAGMA query_only=ON');db.execute('BEGIN');before=local_snapshot(db,settings.owner)
        report['entry_halted_before']=before['halt'] is not None
        x.sync_time();report['initial_account']=flat_proof(x,clock)
        verified=[]
        for row in before['rows']:
            item=dict(client_id=row['client_id'],from_state=row['state'])
            try:
                params=json.loads(row['params'])
                lookup={'clientAlgoId':row['client_id']} if row['path']=='/fapi/v1/algoOrder' else {'symbol':params['symbol'],'origClientOrderId':row['client_id']}
                result=x.get(row['path'],lookup);state=terminal_response(row,result)
                verified.append((row,result,state));item.update(to_state=state,verified=True,response_hash=binding_hash(result))
            except Exception:
                item.update(verified=False);report['issues'].append(dict(client_id=row['client_id'],code='HISTORY_QUERY_OR_IDENTITY_UNPROVEN'))
            report['changes'].append(item)
        if report['issues']:return report
        final=flat_proof(x,clock);report['final_account']=final
        if not apply:
            report['state']='READ_ONLY_VERIFIED';return report
        if not verified:
            report.update(state='NO_CHANGES',updated_count=0);return report
        if backup_path is None:raise ValueError('BACKUP_PATH_REQUIRED')
        backup=Path(backup_path).resolve()
        if backup.exists() or backup==Path(settings.execution_database).resolve():raise ValueError('NEW_BACKUP_PATH_REQUIRED')
        backup.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(settings.execution_database,timeout=10)) as db:
            db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
            if local_snapshot(db,settings.owner)!=before:raise ValueError('LOCAL_HISTORY_CHANGED')
            with closing(sqlite3.connect(uri,uri=True,timeout=5)) as source,closing(sqlite3.connect(backup)) as target:
                source.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('BACKUP_INTEGRITY_FAILED')
            report['backup']=str(backup)
            if not 0<=clock()-final['started_at']<=15:raise ValueError('FINAL_ACCOUNT_PROOF_EXPIRED')
            try:
                for row,result,state in verified:
                    db.execute('UPDATE intents SET state=?,response=?,updated_at=CURRENT_TIMESTAMP WHERE client_id=?',
                               (state,json.dumps(result,sort_keys=True,allow_nan=False),row['client_id']))
                event=dict(account_ref=report['account_ref'],changes=report['changes'],flat_proof_hash=binding_hash(final),halt_cleared=False)
                db.execute('INSERT INTO events(event,payload) VALUES (?,?)',('terminal_history_reconciled',json.dumps(event,sort_keys=True)))
                db.commit()
            except BaseException:db.rollback();raise
        report.update(state='APPLIED',updated_count=len(verified),entry_halt_preserved=before['halt'] is not None)
    except Exception:report['issues'].append(dict(code='HISTORY_RECONCILIATION_PRECONDITION_FAILED'))
    finally:
        report['requests']=x.calls;report['completed_at']=clock()
    return report


def local_reconciliation(settings,*,apply=False):
    from agentrader.shared.config import Config
    from agentrader.shared.exchange import DemoExchange
    from agentrader.shared.locking import execution_lock
    root=Path(__file__).resolve().parents[2]
    backup=root/'reports'/('history-reconcile-before-'+uuid.uuid4().hex+'.sqlite3') if apply else None
    with execution_lock():return reconcile_terminal_history(settings,DemoExchange(Config.load()),apply=apply,backup_path=backup)
