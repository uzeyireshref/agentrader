"""Local exact-command approval for demo configuration; no implicit configuration changes."""
import argparse
import getpass
import json
from pathlib import Path

from .account_commands import AccountCommands
from .config import Config
from .exchange import DemoExchange,ExchangeError
from .locking import execution_lock
from .state import StateStore


def main(argv=None):
    parser=argparse.ArgumentParser(prog='agentrader settings',description=__doc__)
    parser.add_argument('--database',default='data/execution.sqlite3')
    sub=parser.add_subparsers(dest='command',required=True)
    prepare=sub.add_parser('prepare',help='Somut ayar değişikliği oluştur; borsada değişiklik yapmaz')
    prepare.add_argument('--kind',required=True,choices=['LEVERAGE','MARGIN_TYPE','POSITION_MODE','MULTI_ASSETS','FEE_BURN'])
    prepare.add_argument('--value',required=True)
    prepare.add_argument('--symbol')
    apply=sub.add_parser('apply',help='Yalnız özetini onayladığınız komutu bir kez uygula')
    apply.add_argument('command_id');apply.add_argument('--digest',required=True)
    apply.add_argument('--execute-demo',action='store_true',required=True)
    reconcile=sub.add_parser('reconcile',help='Kaydedilmiş ayarı tekrar göndermeden GET ile uzlaştır')
    reconcile.add_argument('command_id')
    mp=sub.add_parser('margin-prepare',help='İzole pozisyona somut teminat ekleme/azaltma komutu hazırla; yazma yapmaz')
    mp.add_argument('--symbol',required=True);mp.add_argument('--position-side',required=True,choices=['BOTH','LONG','SHORT'])
    mp.add_argument('--action',required=True,choices=['ADD','REMOVE']);mp.add_argument('--amount',required=True)
    mp.add_argument('--ttl',type=int,default=300)
    mp.add_argument('--session-id',help='Teminatı değiştirilecek etkin bot oturumunu açıkça bağla')
    ma=sub.add_parser('margin-apply',help='İzole teminat komutunu bir kez gönder')
    ma.add_argument('command_id');ma.add_argument('--digest',required=True);ma.add_argument('--execute-demo',action='store_true',required=True)
    mr=sub.add_parser('margin-reconcile',help='Teminat geçmişini oku; belirsiz artımlı komutu yeniden gönderme')
    mr.add_argument('command_id')
    for command_parser in (mp,ma,mr):
        command_parser.add_argument('--risk-profile',help='Yönetilen oturumlarla aynı risk profili; dosya değiştirilmez')
    args=parser.parse_args(argv)
    try:
        with execution_lock():
            store=StateStore(Path(args.database))
            try:
                if args.command.startswith('margin-'):
                    from .isolated_margin import IsolatedMarginCommands
                    from .risk import RiskLimits
                    service=IsolatedMarginCommands(DemoExchange(Config.load()),store,'local:'+getpass.getuser(),
                                                    session_id=getattr(args,'session_id',None),
                                                    limits=RiskLimits.load(args.risk_profile) if args.risk_profile else RiskLimits())
                    if args.command=='margin-prepare':result=service.prepare(args.symbol,args.position_side,args.action,args.amount,args.ttl)
                    elif args.command=='margin-apply':result=service.apply(args.command_id,args.digest)
                    else:result=service.reconcile(args.command_id)
                else:service=AccountCommands(DemoExchange(Config.load()),store,'local:'+getpass.getuser())
                if args.command=='prepare':
                    if args.kind=='LEVERAGE':value=int(args.value)
                    elif args.kind=='MARGIN_TYPE':value=args.value
                    else:
                        if args.value not in ('true','false'):raise ValueError('Boolean değer true/false olmalı.')
                        value=args.value=='true'
                    result=service.prepare(args.kind,value,args.symbol)
                elif args.command=='apply':result=service.apply(args.command_id,args.digest)
                elif args.command=='reconcile':result=service.reconcile(args.command_id)
            finally:store.close()
        print(json.dumps(result,ensure_ascii=True,indent=2))
        return 0 if result['state'] in ('PREPARED','APPLIED') else 1
    except (ValueError,ExchangeError,OSError) as exc:
        print(json.dumps({'state':'BLOCKED','error':str(exc)},ensure_ascii=True))
        return 1
