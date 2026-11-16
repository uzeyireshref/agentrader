"""Offline product registry and explicit read-only account discovery."""
import argparse
import json
import sqlite3
from pathlib import Path

from agentrader.bot.account_discovery import probe,lookup_order
from agentrader.shared.config import Config,DiscoveryCredentials
from agentrader.shared.discovery_exchange import DiscoveryExchange
from agentrader.shared.discovery_store import DiscoveryStore
from agentrader.shared.exchange import ExchangeError
from agentrader.shared.product_registry import inventory,PROFILES


def main(argv=None):
    parser=argparse.ArgumentParser(prog='agentrader discovery',description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('list',help='Ürün/ortam/hesap sınırlarını ağ veya anahtar okumadan göster')
    run=sub.add_parser('probe',help='Seçili bağlamda salt GET keşfi; yazma izni üretmez')
    latest=sub.add_parser('latest',help='Yalnız aynı bağlam/anahtarın yerel keşif kanıtını oku')
    latest.add_argument('--max-age',type=int,default=300)
    lookup=sub.add_parser('lookup-order',help='Tek NORMAL emir kimliğini oku; bulunamama ret sayılmaz')
    lookup.add_argument('--symbol',required=True)
    ids=lookup.add_mutually_exclusive_group(required=True)
    ids.add_argument('--order-id',type=int);ids.add_argument('--client-order-id')
    for command in (run,latest,lookup):
        command.add_argument('--context',choices=tuple(PROFILES),default='usdm-demo')
        command.add_argument('--private',action='store_true',required=command is lookup,help='Yalnız bu bağlamın ayrı anahtar profilini yükle')
        command.add_argument('--database',default='data/discovery.sqlite3',help='Yürütme/grafik deposundan ayrı keşif kaydı')
    args=parser.parse_args(argv);store=None
    try:
        if args.command=='list':report=inventory()
        else:
            credentials=Config.load_for_discovery(args.context) if args.private else DiscoveryCredentials(args.context)
            client=DiscoveryExchange(args.context,credentials)
            store=DiscoveryStore(Path(args.database))
            if args.command=='latest':report=store.latest(client.evidence_identity(args.private),max_age=args.max_age)
            else:
                report=(probe(client,include_private=args.private) if args.command=='probe' else
                        lookup_order(client,args.symbol,order_id=args.order_id,client_order_id=args.client_order_id))
                store.save(report)
        print(json.dumps(report,ensure_ascii=True,indent=2))
        fresh_success=report.get('evidence_status')=='FRESH' and report.get('report',{}).get('status') in ('READ_COMPLETE','ORDER_OBSERVED')
        return 0 if args.command=='list' or report.get('status') in ('READ_COMPLETE','ORDER_OBSERVED') or fresh_success else 1
    except (ValueError,OSError,sqlite3.Error,ExchangeError) as exc:
        print(json.dumps({'status':'BLOCKED','reason':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,
                          'read_only':True,'write_permission':'NOT_VERIFIED','financial_execution_authorized':False},ensure_ascii=True))
        return 1
    finally:
        if store is not None:store.close()
