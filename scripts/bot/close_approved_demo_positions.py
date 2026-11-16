"""One-off, explicitly approved Demo reduction. No entry, settings or halt clear.

Authorization scope: 29.8 AAVEUSDT and 1000 TRUMPUSDT LONG/BOTH,
reduceOnly MARKET SELL, in the account bound to the reviewed draft.
"""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from agentrader.application.settings import WebSettings
from agentrader.application.queries import execution_status
from agentrader.chart.chart_bindings import binding_hash
from agentrader.shared.config import Config
from agentrader.bot.demo_readiness import inventory
from agentrader.shared.exchange import DemoExchange
from agentrader.bot.execution import DurableExchange
from agentrader.shared.locking import execution_lock
from agentrader.bot.order_rules import validate_order
from agentrader.bot.risk import number
from agentrader.shared.state import StateStore
from agentrader.bot.v2_preflight import fresh

SCOPE='ec9e0fc7263103546bcd0779b69c44192c61691b2ec407e18a214f57b3d1d10f'
TARGETS={'AAVEUSDT':'29.8','TRUMPUSDT':'1000.00'}
DRAFT=ROOT/'reports/demo-existing-exposure-review-20261114.json'
REPORT=ROOT/'reports/demo-approved-reductions-20261114.json'


def verified_inventory(x):
    start=time.monotonic()
    if x.get('/fapi/v1/positionSide/dual').get('dualSidePosition') is not False:raise ValueError('ONE_WAY_SCOPE_REQUIRED')
    a=inventory(x.get('/fapi/v3/account')['positions'],'one-way')
    b=inventory(x.get('/fapi/v3/positionRisk'),'one-way')
    if a!=b:raise ValueError('POSITION_SNAPSHOTS_DISAGREE')
    if x.get('/fapi/v1/openOrders') or x.get('/fapi/v1/openAlgoOrders'):raise ValueError('OPEN_ORDERS_CHANGED')
    if time.monotonic()-start>15:raise ValueError('POSITION_SNAPSHOT_EXPIRED')
    for (symbol,side),qty in b.items():
        if symbol not in TARGETS or side!='BOTH' or qty!=number(TARGETS[symbol]):raise ValueError('APPROVED_POSITION_SCOPE_CHANGED')
    return b


def params_for(symbol):
    cid='agt-clean-'+hashlib.sha256((SCOPE+':'+symbol).encode()).hexdigest()[:25]
    return dict(symbol=symbol,side='SELL',positionSide='BOTH',type='MARKET',quantity=TARGETS[symbol],reduceOnly='true',newClientOrderId=cid)


class ReductionScope:
    def __init__(self,x):self.x=x;self.posts=[]
    def get(self,path,params=None):return self.x.get(path,params)
    def request(self,method,path,params=None):
        p=dict(params or {})
        if method!='POST' or path!='/fapi/v1/order' or p.get('symbol') not in TARGETS or p!=params_for(p['symbol']):
            raise ValueError('UNAPPROVED_MUTATION_DENIED')
        positions=verified_inventory(self.x)
        if positions.get((p['symbol'],'BOTH'))!=number(p['quantity']):raise ValueError('POSITION_CHANGED_BEFORE_REDUCTION')
        self.posts.append(dict(symbol=p['symbol'],client_id=p['newClientOrderId']))
        return self.x.request('POST',path,p)


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--execute-demo',action='store_true');parser.add_argument('--approval-scope')
    args=parser.parse_args(argv)
    report=dict(schema='approved-demo-reductions/1',started_at=datetime.now(timezone.utc).isoformat(),environment='demo',
                state='PREPARING',approval_scope=SCOPE,execute_requested=args.execute_demo,orders=[],order_posts=0,halt_cleared=False,settings_changes=0)
    def save():REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    store=None;scoped=None
    try:
        draft=json.loads(DRAFT.read_text(encoding='utf-8'))
        scope=binding_hash(dict(account_ref=draft['account_ref'],position_mode=draft['position_mode'],actions=[dict(position=a['expected_position_amount'],order=a['order']) for a in draft['actions']]))
        if scope!=SCOPE or draft['scope_hash']!=SCOPE:raise ValueError('REVIEWED_SCOPE_CHANGED')
        if args.execute_demo and args.approval_scope!=SCOPE:raise ValueError('EXPLICIT_SCOPE_REQUIRED')
        config=Config.load()
        if hashlib.sha256(config.api_key.encode()).hexdigest()!=draft['account_ref']:raise ValueError('DEMO_ACCOUNT_CHANGED')
        settings=WebSettings.load();x=DemoExchange(config)
        with execution_lock():
            local=execution_status(settings.execution_database,settings.owner)
            if local['storage']!='AVAILABLE' or local['active_sessions']:raise ValueError('LOCAL_RUNTIME_SCOPE_CHANGED')
            x.sync_time();positions=verified_inventory(x)
            info={s['symbol']:s for s in x.get('/fapi/v1/exchangeInfo')['symbols']}
            proposals=[]
            for symbol in TARGETS:
                if (symbol,'BOTH') not in positions:
                    report['orders'].append(dict(symbol=symbol,state='ALREADY_FLAT',submitted=False));continue
                mark=x.get('/fapi/v1/premiumIndex',{'symbol':symbol})
                now=int(time.time()*1000)+x.offset_ms;fresh(mark,symbol,now,15)
                proposals.append(validate_order(params_for(symbol),info[symbol],'one-way','REDUCE',mark['markPrice'],now))
            report['proposals']=proposals
            if not args.execute_demo:report['state']='READ_ONLY_VALIDATED';save();return 0
            # Online backup before any durable journal mutation; no secrets are read.
            backup=ROOT/'reports/demo-approved-reduction-before-20261114.sqlite3'
            if not backup.exists():
                with closing(sqlite3.connect(settings.execution_database.resolve().as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(backup)) as target:
                    source.backup(target)
                    if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('BACKUP_INTEGRITY_FAILED')
            report['backup']=str(backup.relative_to(ROOT))
            store=StateStore(settings.execution_database)
            owner=store.db.execute("SELECT value FROM control WHERE name='plan_owner'").fetchone()
            if owner is None or owner[0]!=settings.owner:raise ValueError('LOCAL_OWNER_CHANGED')
            store.event('user_approved_demo_reductions',dict(scope_hash=SCOPE,targets=TARGETS,operation='REDUCE_ONLY_MARKET',halt_clear_authorized=False))
            scoped=ReductionScope(x);durable=DurableExchange(scoped,store)
            report['state']='EXECUTING_APPROVED_REDUCTIONS';save()
            for proposal in proposals:
                p=proposal['params'];cid=p['newClientOrderId'];row=dict(symbol=p['symbol'],client_id=cid,state='QUERYING_OR_SUBMITTING');report['orders'].append(row);save()
                # DurableExchange commits the identity before delivery. Existing
                # identities always query; a lost POST response is never retried.
                try:durable.request('POST','/fapi/v1/order',p)
                except Exception:row['delivery']='REQUIRES_QUERY'
                for attempt in range(12):
                    result=x.get('/fapi/v1/order',{'symbol':p['symbol'],'origClientOrderId':cid})
                    if (result.get('clientOrderId')!=cid or result.get('symbol')!=p['symbol'] or result.get('side')!='SELL'
                            or result.get('positionSide')!='BOTH' or result.get('type')!='MARKET'
                            or number(result.get('origQty','0'))!=number(p['quantity']) or str(result.get('reduceOnly')).lower()!='true'):
                        raise ValueError('REDUCTION_ORDER_IDENTITY_MISMATCH')
                    store.update(cid,result['status'],result);row.update(state=result['status'],order_id=result.get('orderId'),filled_quantity=result.get('executedQty'),average_price=result.get('avgPrice'));save()
                    if result['status']=='FILLED':
                        if number(result.get('executedQty','0'))!=number(p['quantity']):raise ValueError('REDUCTION_FILL_QUANTITY_MISMATCH')
                        break
                    if result['status'] in ('CANCELED','EXPIRED','REJECTED'):raise ValueError('REDUCTION_NOT_FILLED')
                    time.sleep(.5)
                else:raise ValueError('REDUCTION_FILL_UNCONFIRMED')
                if (p['symbol'],'BOTH') in verified_inventory(x):raise ValueError('REDUCTION_NOT_FLAT')
            final=verified_inventory(x)
            if final:raise ValueError('FINAL_ACCOUNT_NOT_FLAT')
            report.update(state='COMPLETED',position_count=0,open_order_count=0,open_algo_count=0,entry_halt_retained=bool(store.halt_reason()))
            store.event('approved_demo_reductions_completed',dict(scope_hash=SCOPE,position_count=0,halt_cleared=False))
    except Exception:
        report['state']='BLOCKED_REQUIRES_RECONCILIATION';report['error_code']='APPROVED_REDUCTION_VERIFICATION_FAILED'
        if store:store.halt('Onaylı Demo azaltma sonucu uzlaştırılmalı; otomatik tekrar yok.')
    finally:
        if scoped:report['order_posts']=len(scoped.posts)
        if store:store.close()
        report['completed_at']=datetime.now(timezone.utc).isoformat();save()
    print(json.dumps({k:report[k] for k in ('state','orders','order_posts','halt_cleared')},ensure_ascii=False))
    return 0 if report['state']=='COMPLETED' else 1

if __name__=='__main__':raise SystemExit(main())
