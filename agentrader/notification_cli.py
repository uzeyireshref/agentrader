"""Inspect or explicitly deliver the persistent notification outbox."""
import argparse
import json
import os
from pathlib import Path

from .notifications import NotificationQueue,TelegramSender
from .state import StateStore


def main(argv=None):
    parser=argparse.ArgumentParser(prog='agentrader notifications')
    parser.add_argument('--database',default='data/execution.sqlite3')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('status')
    work=sub.add_parser('deliver',help='Kuyruktaki bildirimleri yapılandırılmış Telegram sohbetine gönder')
    work.add_argument('--execute-send',action='store_true',required=True)
    work.add_argument('--limit',type=int,default=10)
    args=parser.parse_args(argv)
    if args.command=='deliver' and not 1<=args.limit<=100:parser.error('limit 1–100 olmalı.')
    store=StateStore(Path(args.database))
    try:
        queue=NotificationQueue(store)
        if args.command=='status':result=queue.status()
        else:
            # Telegram secrets are process environment only; never echo them.
            sender=TelegramSender(os.environ.get('TELEGRAM_BOT_TOKEN',''),os.environ.get('TELEGRAM_CHAT_ID',''))
            result=[]
            for _ in range(args.limit):
                report=queue.deliver_one(sender);result.append(report)
                if report['state']=='IDLE':break
        print(json.dumps(result,ensure_ascii=False))
        return 0
    except (ValueError,OSError) as exc:
        print(json.dumps({'state':'BLOCKED','error':str(exc)},ensure_ascii=False))
        return 1
    finally:store.close()
