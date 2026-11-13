"""Offline inventory or explicit read-only demo probes; no order/configuration mutation."""
import argparse
import hashlib
import json
from pathlib import Path

from .capabilities import list_capabilities, probe_capabilities, save_probe, latest_probe
from .config import Config
from .exchange import DemoExchange
from .state import StateStore


def main(argv=None):
    parser = argparse.ArgumentParser(prog='agentrader capabilities', description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    catalog = sub.add_parser('list',help='Anahtar veya ağ olmadan belgeli yetenekleri göster')
    catalog.add_argument('--category')
    catalog.add_argument('--output')
    probe = sub.add_parser('probe',help='Sabit GET kontrolleri; emir veya ayar değişimi yapmaz')
    probe.add_argument('--symbol',default='BTCUSDT')
    probe.add_argument('--account',action='store_true',help='Özel hesap okuma kontrollerini de çalıştır')
    probe.add_argument('--output')
    probe.add_argument('--database',default='data/execution.sqlite3')
    latest = sub.add_parser('latest',help='Aynı anahtar ve sembol için son yerel kanıt; ağ çağrısı yapmaz')
    latest.add_argument('--symbol',default='BTCUSDT')
    latest.add_argument('--account',action='store_true',help='Mevcut anahtar kimliğiyle eşleşen özel hesap kanıtı')
    latest.add_argument('--max-age',type=int,default=300)
    latest.add_argument('--database',default='data/execution.sqlite3')
    latest.add_argument('--output')
    args = parser.parse_args(argv)
    try:
        if args.command == 'list':
            report = list_capabilities(args.category)
        elif args.command == 'probe':
            report = probe_capabilities(DemoExchange(Config.load() if args.account else Config()),
                                        args.symbol,include_account=args.account)
            store = StateStore(Path(args.database))
            try: save_probe(store,report)
            finally: store.close()
        else:
            ref = None
            if args.account:
                key = Config.load().api_key
                if not key: raise ValueError('Hesap kanıtı için demo anahtarı gerekli.')
                ref = hashlib.sha256(key.encode()).hexdigest()[:16]
            store = StateStore(Path(args.database))
            try: report = latest_probe(store,args.symbol,ref,args.max_age)
            finally: store.close()
        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        # Do not flood the user with all 95 rows on every probe.
        shown = report if args.command != 'probe' else {k:v for k,v in report.items() if k != 'operations'}
        if args.command == 'latest' and 'report' in shown:
            shown = dict(shown,report={k:v for k,v in shown['report'].items() if k != 'operations'})
        print(json.dumps(shown,ensure_ascii=True,indent=2))
        return 1 if report.get('status') == 'INCOMPLETE' or report.get('evidence_status') in ('NOT_FOUND','STALE') else 0
    except (ValueError,OSError) as exc:
        print(json.dumps({'status':'ERROR','message':str(exc)},ensure_ascii=True))
        return 1
