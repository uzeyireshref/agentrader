"""Foreground supervised service for an existing session; never creates a plan."""
import argparse
import getpass
import json
import time
import os
import sqlite3
from pathlib import Path

from agentrader.shared.state import StateStore


def service_status(store,session_id,clock=time.time):
    row=store.db.execute('SELECT value FROM control WHERE name=?',('runtime_health:'+session_id,)).fetchone()
    if row is None:return {'state':'NOT_OBSERVED','session_id':session_id}
    body=json.loads(row[0]);age=clock()-body['observed_at']
    stopped=body['state'] in ('CLOSED','MONITOR_STOPPED') or body.get('service_stopped') is True
    return body|{'health':'STOPPED' if stopped else ('FRESH' if 0<=age<=90 else 'STALE'),
                 'age_seconds':round(age,1),'stop_requested':store.service_stop_request(session_id) is not None}


def request_stop(store,session_id,owner):
    row=store.db.execute("SELECT value FROM control WHERE name='plan_owner'").fetchone()
    if row is None or row[0]!=owner:raise ValueError('Servis durdurma yetkilisi uyuşmuyor.')
    matches=[s for s in store.sessions() if s['id']==session_id]
    if len(matches)!=1 or matches[0].get('engine') not in ('v2','grid-v2','neutral-v2'):
        raise ValueError('Durdurulabilecek etkin v2 oturumu bulunamadı.')
    body={'requested':True,'engine':matches[0]['engine'],'owner':owner}
    with store.db:
        store.db.execute('INSERT OR REPLACE INTO control VALUES (?,?)',('service_stop:'+session_id,json.dumps(body)))
        store.db.execute('INSERT OR REPLACE INTO control VALUES (?,?)',
                         ('entry_revoked:'+matches[0]['entry_id'],json.dumps(body)))
    return {'state':'STOP_REQUESTED','session_id':session_id,'close_position':False}


def main(argv=None):
    parser=argparse.ArgumentParser(prog='agentrader service')
    sub=parser.add_subparsers(dest='command',required=True)
    operations=sub.add_parser('operations',help='Yerel emir/toparlanma/WS/kota durumunu salt oku; borsa isteği yapmaz')
    operations.add_argument('--database',default='data/execution.sqlite3')
    operations.add_argument('--governor-database',default='data/request-governor.sqlite3')
    operations.add_argument('--format',choices=('json','prometheus'),default='json')
    sub.add_parser('acceptance-check',help='Demo hesabı ve yerel kabul engellerini salt okunur raporla; emir veya temizlik yapmaz')
    history=sub.add_parser('reconcile-history',help='Geçmiş emirlerin kimliğini ve terminal durumunu GET ile doğrula; giriş durdurması korunur')
    history.add_argument('--apply-local',action='store_true',help='Yedekten sonra yalnız doğrulanmış terminal kayıtları yerelde güncelle')
    test_draft=sub.add_parser('prepare-demo-test',help='Hesap/risk ve sembol kurallarıyla teknik test taslağı üret; emir/onay veya durdurma değişikliği yapmaz')
    test_draft.add_argument('--symbol',default='BTCUSDT')
    test_draft.add_argument('--direction',required=True,choices=('LONG','SHORT'))
    guardian=sub.add_parser('guardian',help='Bağımsız süreçte yalnız kayıtlı grafik oturumunu uzlaştır ve koru; yeni giriş açmaz')
    guardian.add_argument('--database',default=os.environ.get('AGENTRADER_EXECUTION_DATABASE','data/execution.sqlite3'))
    guardian.add_argument('--execute-demo',action='store_true')
    guardian.add_argument('--risk-profile',default='risk-demo.json')
    guardian.add_argument('--interval',type=int,default=1)
    guardian.add_argument('--iterations',type=int,default=0)
    guardian_status=sub.add_parser('guardian-status',help='Ağ isteği yapmadan bağımsız izleyici durumunu oku')
    guardian_status.add_argument('--database',default=os.environ.get('AGENTRADER_EXECUTION_DATABASE','data/execution.sqlite3'))
    for name in ('run','run-all'):
        run=sub.add_parser(name,help='Mevcut oturumları sürekli izle; varsayılan salt okunur')
        if name=='run':
            run.add_argument('session_id');run.add_argument('--user-stream',action='store_true')
        run.add_argument('--execute-demo',action='store_true')
        run.add_argument('--risk-profile',default='risk-demo.json');run.add_argument('--interval',type=int,default=5)
        run.add_argument('--notify-chat-id')
    for command in ('status','request-stop'):
        p=sub.add_parser(command);p.add_argument('session_id');p.add_argument('--database',default='data/execution.sqlite3')
    args=parser.parse_args(argv)
    if args.command=='operations':
        from agentrader.application.operations import operation_status,prometheus
        from agentrader.application.queries import StorageUnavailable
        try:
            report=operation_status(args.database,'local:'+getpass.getuser(),governor_database=args.governor_database)
            print(prometheus(report) if args.format=='prometheus' else json.dumps(report,ensure_ascii=True))
            return 0 if report['health']=='NO_LOCAL_BLOCKER_OBSERVED' else 1
        except StorageUnavailable:
            print(json.dumps(dict(storage='UNAVAILABLE',health='NOT_OBSERVED',error='OPERATIONS_STORAGE_UNAVAILABLE',read_only=True)))
            return 2
    if args.command=='prepare-demo-test':
        from agentrader.application.settings import WebSettings
        from agentrader.bot.demo_test_preparation import local_prepare
        try:
            report=local_prepare(WebSettings.load(),args.symbol,args.direction);print(json.dumps(report,ensure_ascii=False))
            return 0 if report['state']=='DRAFT_READY_FOR_REVIEW' else 1
        except Exception:
            print(json.dumps(dict(state='BLOCKED',error='DEMO_TEST_PREPARATION_UNAVAILABLE',order_requests=0)));return 1
    if args.command=='reconcile-history':
        from agentrader.application.settings import WebSettings
        from agentrader.bot.history_reconciliation import local_reconciliation
        try:
            report=local_reconciliation(WebSettings.load(),apply=args.apply_local);print(json.dumps(report,ensure_ascii=False))
            return 0 if report['state'] in ('READ_ONLY_VERIFIED','APPLIED','NO_CHANGES') else 1
        except Exception:
            print(json.dumps(dict(state='BLOCKED',error='HISTORY_RECONCILIATION_UNAVAILABLE',order_requests=0)));return 1
    if args.command=='acceptance-check':
        from agentrader.application.settings import WebSettings
        from agentrader.bot.demo_readiness import local_audit
        try:
            report=local_audit(WebSettings.load());print(json.dumps(report,ensure_ascii=False))
            return 0 if report['plan_review_ready'] else 1
        except Exception:
            print(json.dumps(dict(state='BLOCKED',error='DEMO_ACCEPTANCE_CHECK_UNAVAILABLE',order_requests=0)));return 1
    if args.command=='guardian-status':
        from agentrader.bot.recovery_guardian import status
        print(json.dumps(status(args.database),ensure_ascii=False));return 0
    if args.command=='guardian':
        from agentrader.bot.recovery_guardian import run_guardian
        from agentrader.shared.config import Config
        from agentrader.shared.exchange import DemoExchange
        from agentrader.bot.risk import RiskLimits
        if not 1<=args.interval<=2 or args.iterations<0:parser.error('interval 1–2 ve iterations >=0 olmalı.')
        try:
            run_guardian(Path(args.database),'local:'+getpass.getuser(),lambda:DemoExchange(Config.load()),
                         RiskLimits.load(args.risk_profile),execute=args.execute_demo,interval=args.interval,iterations=args.iterations,
                         emit=lambda r:print(json.dumps(r,ensure_ascii=False),flush=True))
            return 0
        except KeyboardInterrupt:return 130
        except (ValueError,OSError,sqlite3.Error):
            print(json.dumps(dict(state='BLOCKED',error='DEMO_RECOVERY_GUARDIAN_FAILED')));return 1
    if args.command in ('run','run-all'):
        from agentrader.cli.plan_cli import main as manage
        forwarded=(['manage',args.session_id] if args.command=='run' else ['manage-all'])
        forwarded+=['--iterations','0','--interval',str(args.interval),'--risk-profile',args.risk_profile]
        if args.execute_demo:forwarded.append('--execute-demo')
        if getattr(args,'user_stream',False):forwarded.append('--user-stream')
        if args.notify_chat_id:forwarded+=['--notify-chat-id',args.notify_chat_id]
        return manage(forwarded)
    store=StateStore(Path(args.database))
    try:
        report=(service_status(store,args.session_id) if args.command=='status'
                else request_stop(store,args.session_id,'local:'+getpass.getuser()))
        print(json.dumps(report,ensure_ascii=False));return 0
    except (ValueError,OSError) as exc:
        print(json.dumps({'state':'BLOCKED','error':str(exc)},ensure_ascii=False));return 1
    finally:store.close()
