"""Foreground supervised service for an existing session; never creates a plan."""
import argparse
import getpass
import json
import time
from pathlib import Path

from .state import StateStore


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
    if args.command in ('run','run-all'):
        from .plan_cli import main as manage
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
