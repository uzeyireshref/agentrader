"""Exact native LIMIT amendment commands for existing authorized v2 sessions."""
import argparse
import getpass
import json
from pathlib import Path

from .config import Config
from .exchange import DemoExchange,ExchangeError
from .locking import execution_lock
from .order_amend import OrderAmendments
from .plans import PlanService
from .risk import RiskLimits
from .runtime import supervise_session
from .state import StateStore


def main(argv=None):
    parser=argparse.ArgumentParser(prog='agentrader orders',description=__doc__)
    parser.add_argument('--database',default='data/execution.sqlite3')
    parser.add_argument('--risk-profile',default='risk-demo.json')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('amend-prepare',help='Somut fiyat/miktar değişikliğini hazırla; PUT göndermez')
    p.add_argument('session_id');p.add_argument('client_id');p.add_argument('--quantity',required=True);p.add_argument('--price',required=True)
    p.add_argument('--ttl',type=int,default=120)
    p=sub.add_parser('batch-amend-prepare',help='1–5 seçili LIMIT değişikliğini JSON dosyasından hazırla')
    p.add_argument('session_id');p.add_argument('file');p.add_argument('--ttl',type=int,default=120)
    for name in ('amend-apply','amend-reconcile','amend-cancel','batch-amend-apply','batch-amend-reconcile','batch-amend-cancel'):
        p=sub.add_parser(name);p.add_argument('command_id')
        if name.endswith(('-apply','-cancel')):p.add_argument('--digest',required=True)
        if name.endswith('-apply'):p.add_argument('--execute-demo',action='store_true',required=True)
        elif name.endswith('-reconcile'):p.add_argument('--execute-demo',action='store_true',help='Doğrulandıysa mevcut yönetimi de devral')
        if name.endswith(('-apply','-reconcile')):
            p.add_argument('--iterations',type=int);p.add_argument('--interval',type=int,default=5)
    args=parser.parse_args(argv)
    if hasattr(args,'iterations')and((args.iterations is not None and args.iterations<0)or not 1<=args.interval<=60):
        parser.error('iterations >= 0 ve interval 1–60 olmalı.')
    try:
        with execution_lock():
            store=StateStore(Path(args.database))
            try:
                owner='local:'+getpass.getuser();service=PlanService(store,owner)
                x=DemoExchange(Config.load());limits=RiskLimits.load(args.risk_profile)
                amendments=OrderAmendments(service,x,limits)
                cmd=args.command
                if cmd=='amend-prepare':report=amendments.prepare(args.session_id,args.client_id,args.quantity,args.price,args.ttl)
                elif cmd=='batch-amend-prepare':
                    text=Path(args.file).read_text(encoding='utf-8-sig')
                    if len(text)>32768:raise ValueError('Toplu amend dosyası 32 KB sınırını aşıyor.')
                    report=amendments.prepare_batch(args.session_id,json.loads(text),args.ttl)
                elif cmd=='amend-apply':report=amendments.apply(args.command_id,args.digest)
                elif cmd=='amend-reconcile':report=amendments.reconcile(args.command_id)
                elif cmd=='amend-cancel':report=amendments.cancel(args.command_id,args.digest)
                elif cmd=='batch-amend-apply':report=amendments.apply_batch(args.command_id,args.digest)
                elif cmd=='batch-amend-reconcile':report=amendments.reconcile_batch(args.command_id)
                else:report=amendments.cancel_batch(args.command_id,args.digest)
                print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
                if getattr(args,'execute_demo',False)and report['state']in('APPLIED','SUPERSEDED','FINAL_WITH_ERRORS'):
                    if cmd.startswith('batch-'):
                        _,b,members=amendments._batch(args.command_id)
                        s=members[0][2];runner=members[0][3]
                    else:_,b,s,runner=amendments._row(args.command_id)
                    if runner is not None:
                        grid=s.get('engine')=='grid-v2'
                        supervise_session(runner,s['id'],execute=True,emit=lambda r:print(json.dumps(r,ensure_ascii=False),flush=True),
                                          iterations=args.iterations if args.iterations is not None else(0 if grid else 1),
                                          interval=args.interval,drain_on_exit=grid)
                return 0 if report['state']in('PREPARED','APPLIED','SUPERSEDED','CANCELED')else 1
            finally:store.close()
    except KeyboardInterrupt:
        print(json.dumps({'state':'MONITOR_STOPPED','message':'Mevcut oturum korunur; grid giriş iptallerinin sonucunu denetleyin.'},ensure_ascii=False));return 130
    except(ValueError,ExchangeError,OSError)as exc:
        print(json.dumps({'state':'BLOCKED','error':str(exc)},ensure_ascii=False));return 1
