"""Repeatable read-only acceptance audit. Never clears halt, adopts or closes a position."""
import hashlib
import json
import re
import time

from agentrader.application.queries import execution_status
from agentrader.integration.chart_execution import require_demo_acceptance
from agentrader.shared.exchange import PRIVATE
from agentrader.bot.execution import TERMINAL
from agentrader.integration.preview_preflight import ReadOnlyDemoAccount
from agentrader.bot.recovery_guardian import status as guardian_status
from agentrader.bot.risk import number


class AuditExchange(ReadOnlyDemoAccount):
    def __init__(self,exchange):super().__init__(exchange);self.calls=[]
    def request(self,method,path,params=None):
        if method!='GET':raise ValueError('ACCEPTANCE_AUDIT_READ_ONLY')
        self.calls.append(dict(method='GET',path=path,private=path in PRIVATE))
        return super().request(method,path,params)
    def sync_time(self):
        self.calls.append(dict(method='GET',path='/fapi/v1/time',private=False))
        return super().sync_time()


def inventory(rows,mode):
    if not isinstance(rows,list):raise ValueError('INVALID_POSITION_SNAPSHOT')
    values={}
    for row in rows:
        if not isinstance(row,dict):raise ValueError('INVALID_POSITION_SNAPSHOT')
        qty=number(row['positionAmt'])
        if qty==0:continue
        symbol=row['symbol'];side=row.get('positionSide','BOTH' if mode=='one-way' else None)
        if not isinstance(symbol,str) or not re.fullmatch('[A-Z0-9_]{1,40}',symbol) or side not in ('BOTH','LONG','SHORT'):
            raise ValueError('INVALID_POSITION_IDENTITY')
        if mode=='one-way' and side!='BOTH' or mode=='hedge' and side=='BOTH':raise ValueError('POSITION_MODE_MISMATCH')
        if side=='LONG' and qty<0 or side=='SHORT' and qty>0:raise ValueError('POSITION_DIRECTION_MISMATCH')
        if (symbol,side) in values:raise ValueError('DUPLICATE_POSITION_IDENTITY')
        values[symbol,side]=qty
    return values


def audit(settings,exchange,*,clock=time.time,continuity=require_demo_acceptance,
          local_observer=execution_status,guardian_observer=guardian_status):
    """Snapshots readiness only; ready for review is never execution authority."""
    started=clock();x=AuditExchange(exchange)
    report=dict(schema='controlled-demo-readiness/1',observed_at=started,environment='demo',read_only=True,
                positions=[],open_orders=[],open_algo_orders=[],review_blockers=[],execution_blockers=[],
                account_verified=False,plan_review_ready=False,execution_ready=False,execution_authorized=False,
                order_authority=False,order_requests=0,settings_changes=0,local_execution_store_mutations=0)
    blockers=report['review_blockers']
    try:
        if not exchange.config.api_key or not exchange.config.api_secret:raise ValueError('MISSING_DEMO_CREDENTIALS')
        report['account_ref']=hashlib.sha256(exchange.config.api_key.encode()).hexdigest()
        x.sync_time();config=x.get('/fapi/v1/accountConfig');dual=x.get('/fapi/v1/positionSide/dual')['dualSidePosition']
        if type(dual) is not bool:raise ValueError('INVALID_ACCOUNT_MODE')
        mode='hedge' if dual else 'one-way';report['position_mode']=mode
        account=x.get('/fapi/v3/account');risk=x.get('/fapi/v3/positionRisk')
        normal=x.get('/fapi/v1/openOrders');algos=x.get('/fapi/v1/openAlgoOrders')
        if not isinstance(normal,list) or not isinstance(algos,list) or any(not isinstance(v,dict) for v in normal+algos):
            raise ValueError('INVALID_OPEN_ORDER_SNAPSHOT')
        a=inventory(account['positions'],mode);b=inventory(risk,mode)
        if a!=b:
            blockers.append('ACCOUNT_POSITION_SNAPSHOTS_DISAGREE')
            report['position_disagreements']=[dict(symbol=k[0],positionSide=k[1],account_amount=str(a.get(k,0)),risk_amount=str(b.get(k,0))) for k in sorted(a.keys()|b.keys()) if a.get(k,0)!=b.get(k,0)]
        # Union prevents an empty response from hiding exposure seen by the other endpoint.
        for (symbol,side),qty in sorted((a|b).items()):
            report['positions'].append(dict(symbol=symbol,positionSide=side,positionAmt=str(qty),automatic_management_authority=False))
        for output,rows in (('open_orders',normal),('open_algo_orders',algos)):
            report[output]=[{k:v[k] for k in ('symbol','side','positionSide','clientOrderId','clientAlgoId','orderId','algoId','status','algoStatus') if k in v} for v in rows]
        if config.get('canTrade') is not True:blockers.append('ACCOUNT_TRADING_UNAVAILABLE')
        if a or b:blockers.append('EXISTING_ACCOUNT_POSITIONS')
        if normal:blockers.append('EXISTING_NORMAL_ORDERS')
        if algos:blockers.append('EXISTING_ALGO_ORDERS')
        if not 0<=clock()-started<=15:blockers.append('ACCOUNT_AUDIT_EXPIRED')
        report['account_verified']=True
    except Exception:
        # Do not echo signed URLs, credential errors or full account payloads.
        blockers.append('DEMO_ACCOUNT_AUDIT_FAILED')
    try:
        local=local_observer(settings.execution_database,settings.owner)
        report['local']=local
        if local['storage'] not in ('AVAILABLE','NOT_INITIALIZED'):blockers.append('LOCAL_EXECUTION_STORE_UNAVAILABLE')
        if local.get('entry_halted') is True:blockers.append('LOCAL_ENTRY_HALT_ACTIVE')
        if local.get('active_sessions'):blockers.append('LOCAL_ACTIVE_MANAGED_SESSION')
        if any(v for k,v in local.get('intent_counts',{}).items() if k not in TERMINAL):blockers.append('LOCAL_INTENTS_NEED_RECONCILIATION')
    except Exception:blockers.append('LOCAL_EXECUTION_STORE_UNAVAILABLE')
    try:
        if continuity() is not True:raise ValueError()
        report['continuity_accepted']=True
    except Exception:report['continuity_accepted']=False;blockers.append('DEMO_CONTINUITY_ACCEPTANCE_REQUIRED')
    try:report['guardian']=guardian_observer(settings.execution_database)
    except Exception:report['guardian']=dict(state='UNAVAILABLE',entry_ready=False)
    report['plan_review_ready']=not blockers and report['account_verified']
    report['execution_blockers']=list(blockers)
    if report['guardian'].get('entry_ready') is not True:report['execution_blockers'].append('INDEPENDENT_DEMO_GUARDIAN_REQUIRED')
    report['execution_blockers'].append('EXPLICIT_FRESH_PLAN_AND_APPROVAL_REQUIRED')
    report['state']='READY_FOR_PLAN_REVIEW' if report['plan_review_ready'] else 'BLOCKED'
    report['requests']=x.calls;report['private_get_requests']=sum(c['private'] for c in x.calls)
    report['position_count']=len(report['positions']) if report['account_verified'] else None
    report['open_order_count']=len(report['open_orders']) if report['account_verified'] else None
    report['open_algo_count']=len(report['open_algo_orders']) if report['account_verified'] else None
    report['completed_at']=clock()
    return report


def local_audit(settings):
    from agentrader.shared.config import Config
    from agentrader.shared.exchange import DemoExchange
    return audit(settings,DemoExchange(Config.load()))
