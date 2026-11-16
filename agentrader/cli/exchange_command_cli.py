"""Strategy-independent, exact Binance demo commands."""
import argparse
import getpass
import json
import sqlite3
import time
from pathlib import Path

from agentrader.bot.exchange_commands import ExchangeCommands
from agentrader.shared.config import Config
from agentrader.shared.exchange import DemoExchange, ExchangeError
from agentrader.shared.locking import execution_lock
from agentrader.shared.state import StateStore


def main(argv=None):
    parser=argparse.ArgumentParser(prog='agentrader commands',description=__doc__)
    parser.add_argument('--database',default='data/execution.sqlite3')
    parser.add_argument('--order-transport',choices=('rest','ws'),default='rest',help='Tekil USD-M emir yolu; WS hatasında REST tekrar gönderimi yapılmaz')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('context')
    sub.add_parser('list')
    worker=sub.add_parser('timer-run',help='Açık yetkili lease boyunca heartbeat; restartta otomatik başlamaz')
    worker.add_argument('timer_id');worker.add_argument('--digest',required=True);worker.add_argument('--execute-demo',action='store_true',required=True)
    worker.add_argument('--iterations',type=int,default=1)
    prepare=sub.add_parser('prepare');prepare.add_argument('file');prepare.add_argument('--ttl',type=int,default=300)
    for name in ('show','apply','reconcile','cancel'):
        command=sub.add_parser(name);command.add_argument('command_id')
        if name in ('apply','cancel'):command.add_argument('--digest',required=True)
        if name=='apply':command.add_argument('--execute-demo',action='store_true')
    args=parser.parse_args(argv)
    if args.command=='timer-run':
        if args.iterations<0:parser.error('iterations sıfır veya pozitif olmalı.')
        return run_timer(args)
    try:
        with execution_lock():
            store=StateStore(Path(args.database))
            try:
                service=ExchangeCommands(DemoExchange(Config.load(),order_transport=args.order_transport,store=store),store,'local:'+getpass.getuser())
                if args.command=='context':result=service.context()
                elif args.command=='list':result=service.list()
                elif args.command=='prepare':
                    content=Path(args.file).read_bytes()
                    if len(content)>32768:raise ValueError('Komut dosyası en fazla 32 KiB olabilir.')
                    result=service.prepare(json.loads(content),args.ttl)
                elif args.command=='apply':result=service.apply(args.command_id,args.digest,execute=args.execute_demo)
                elif args.command=='cancel':result=service.cancel(args.command_id,args.digest)
                else:result=getattr(service,args.command)(args.command_id)
            finally:store.close()
        print(json.dumps(result,ensure_ascii=True,indent=2))
        return 0 if result.get('state','APPLIED') in ('PREPARED','APPLIED','CANCELED') else 1
    except (ValueError,ExchangeError,OSError,sqlite3.Error) as exc:
        # Never echo exchange response bodies or credentials into the CLI.
        error={'state':'BLOCKED','error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__}
        print(json.dumps(error,ensure_ascii=True));return 1


def run_timer(args):
    from agentrader.bot.cancel_timers import tick,load
    store=None
    try:
        store=StateStore(Path(args.database));exchange=DemoExchange(Config.load(),order_transport=args.order_transport,store=store);owner='local:'+getpass.getuser()
        count=0
        while True:
            # Never hold the execution lock while sleeping between heartbeats.
            with execution_lock():
                service=ExchangeCommands(exchange,store,owner)
                result=tick(service,args.timer_id,args.digest,execute=args.execute_demo)
                _,body=load(service,args.timer_id);delay=body['heartbeat_ms']/1000
            count+=1
            if result['worker_state'] not in ('WAITING','REFRESHED') or args.iterations and count>=args.iterations:break
            time.sleep(delay)
        print(json.dumps(result,ensure_ascii=True,indent=2))
        return 0 if result['worker_state'] in ('WAITING','REFRESHED','LEASE_ENDED') else 1
    except (ValueError,ExchangeError,OSError,sqlite3.Error) as exc:
        print(json.dumps({'state':'BLOCKED','error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__}));return 1
    finally:
        if store is not None:store.close()
