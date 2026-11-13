"""Yerel kullanıcı için plan hazırlama, açık yetkilendirme ve demo yürütme komutları."""
import argparse
import getpass
import json
import logging

from .config import Config
from .exchange import DemoExchange, ExchangeError
from .locking import execution_lock
from .plans import PlanService, example_plan
from .plan_execution import run_plan
from .risk import RiskLimits
from .state import StateStore


def main(argv=None):
    from .notifications import chat_id,NotificationQueue
    parser = argparse.ArgumentParser(prog='agentrader plans', description='Yerel, sürümlü demo işlem planları')
    sub = parser.add_subparsers(dest='command', required=True)
    example = sub.add_parser('example', help='Güncel geçerlilik tarihli örnek JSON yazdır (emir/yetki oluşturmaz)')
    example.add_argument('--staged', action='store_true', help='İki hedef ve ilk hedef sonrası girişe stop taşıma örneği')
    neutral_example_parser=sub.add_parser('neutral-example',help='Açıkça belirttiğiniz toplam bütçeyle örnek neutral JSON yazdır; emir/yetki oluşturmaz')
    neutral_example_parser.add_argument('--amount',required=True,help='İki tarafın toplam USDT nominal bütçesi')
    create = sub.add_parser('create', help='JSON planı içe aktar; onay/etkinleştirme bekler')
    create.add_argument('file')
    preflight = sub.add_parser('preflight', help='Plan v2 dosyasını güncel demo hesap/fiyat/risk ile oku; emir göndermez')
    preflight.add_argument('file')
    preflight.add_argument('--risk-profile', default='risk-demo.json')
    manage = sub.add_parser('manage', help='Yeni oturum kurmadan onaylı SINGLE/grid yönetimini devral')
    manage.add_argument('session_id')
    manage.add_argument('--execute-demo', action='store_true')
    manage.add_argument('--risk-profile', default='risk-demo.json')
    manage.add_argument('--iterations', type=int, help='0: sürekli; demo grid yürütmede varsayılan 0, diğerinde 1')
    manage.add_argument('--interval', type=int, default=5, help='Turlar arası 1–60 saniye')
    manage.add_argument('--user-stream', action='store_true',
                        help='Demo kullanıcı WebSocket olayları ve REST yeniden uzlaştırma ile izle')
    manage.add_argument('--notify-chat-id',type=chat_id,
                        help='Durumları Telegram bildirim kuyruğuna kaydet; gönderim ayrı deliver komutudur')
    for command in ('manage-all','run-many'):
        command_parser=sub.add_parser(command,help='Farklı sembollü v2 oturumlarını tek yürütücüde yönet')
        command_parser.add_argument('--execute-demo',action='store_true')
        command_parser.add_argument('--risk-profile',default='risk-demo.json')
        command_parser.add_argument('--iterations',type=int)
        command_parser.add_argument('--interval',type=int,default=5)
        command_parser.add_argument('--notify-chat-id',type=chat_id)
        if command=='run-many':command_parser.add_argument('--plan',action='append',required=True,help='PLAN_ID:VERSION; her plan için tekrarla')
    stop_grid=sub.add_parser('stop-grid',aliases=['stop-neutral'],help='Grid yeni girişlerini durdur; açık pozisyonu koru veya açıkça kapat')
    stop_grid.add_argument('session_id');stop_grid.add_argument('--execute-demo',action='store_true')
    stop_grid.add_argument('--close-position',action='store_true')
    stop_grid.add_argument('--risk-profile',default='risk-demo.json')
    unused=sub.add_parser('release-unused',help='Oturum/giriş oluşmadan kesilen, gönderilmemiş rezervi doğrula ve planıyla birlikte iptal et')
    unused.add_argument('reservation_id')
    sub.add_parser('reservations',help='Bu hesap ve yerel sahibe ait ortak risk rezervlerini göster; ağ isteği yapmaz')
    sub.add_parser('list', help='Kayıtlı plan durumları')
    for command in ('show', 'approve', 'activate', 'reject', 'cancel', 'run'):
        command_parser = sub.add_parser(command)
        command_parser.add_argument('plan_id')
        command_parser.add_argument('version', type=int)
        if command in ('approve', 'activate'):
            command_parser.add_argument('--token', required=True, help='İçe aktarmada gösterilen tek kullanımlık yerel onay kimliği')
        if command == 'approve':
            command_parser.add_argument('--ttl', type=int, default=120, help='Bu onayın geçerliliği (saniye); demo varsayılanı 120')
        if command == 'run':
            command_parser.add_argument('--execute-demo', action='store_true')
            command_parser.add_argument('--risk-profile', default='risk-demo.json')
            command_parser.add_argument('--iterations',type=int,help='V2 izleme turu; demo grid yürütmede varsayılan 0 (sürekli)')
            command_parser.add_argument('--interval',type=int,default=5)
    args = parser.parse_args(argv)
    if args.command in ('manage','run','manage-all','run-many') and ((args.iterations is not None and args.iterations < 0) or not 1 <= args.interval <= 60):
        parser.error('iterations >= 0 ve interval 1–60 olmalı.')
    try:
        if args.command == 'example':
            report = example_plan(args.staged)
        elif args.command=='neutral-example':
            from .neutral_plan import neutral_example
            report=neutral_example(args.amount)
        elif args.command == 'preflight':
            from pathlib import Path
            from .plan_v2 import validate_v2
            from .v2_preflight import collect_flat_snapshot, prepare_single
            from .grid_plan import compile_grid
            text = Path(args.file).read_text(encoding='utf-8-sig')
            if len(text) > 32768:
                raise ValueError('Plan dosyası 32 KB sınırını aşıyor.')
            plan = validate_v2(json.loads(text))
            limits = RiskLimits.load(args.risk_profile)
            with execution_lock():
                snapshot = collect_flat_snapshot(DemoExchange(Config.load()), plan['symbol'], limits)
                from .account_runtime import compile_plan
            report=compile_plan(plan,snapshot,limits)
            report.update(read_only=True, executed=False)
        else:
            with execution_lock():
                store = StateStore()
                try:
                    # CLI yerel oturumu güvenilir sınır kabul eder. Ağdan gelen actor burada kabul edilmez.
                    owner = 'local:' + getpass.getuser()
                    service = PlanService(store, owner)
                    if args.command == 'create':
                        from pathlib import Path
                        text = Path(args.file).read_text(encoding='utf-8-sig')
                        if len(text) > 32768:
                            raise ValueError('Plan dosyası 32 KB sınırını aşıyor.')
                        report = service.create(json.loads(text), owner)
                    elif args.command == 'list':
                        rows = store.db.execute('SELECT plan_id,version FROM plan_versions ORDER BY plan_id,version').fetchall()
                        report = [service.show(r['plan_id'], r['version']) for r in rows]
                    elif args.command == 'show':
                        report = service.show(args.plan_id, args.version)
                    elif args.command in ('approve', 'activate'):
                        report = service.authorize(args.plan_id, args.version, args.token, args.command, owner, getattr(args, 'ttl', 120))
                    elif args.command in ('reject', 'cancel'):
                        report = service.cancel(args.plan_id, args.version, owner, reject=args.command == 'reject')
                    elif args.command == 'reservations':
                        from .v2_runner import V2Runner
                        runner=V2Runner(service,DemoExchange(Config.load()),RiskLimits())
                        report=runner.book.list_reservations(owner)
                    elif args.command == 'release-unused':
                        from .v2_runner import V2Runner
                        from .account_ownership import AccountOwnership
                        runner=V2Runner(service,DemoExchange(Config.load()),RiskLimits())
                        report=runner.book.release_unused(args.reservation_id,owner,AccountOwnership(runner))
                    elif args.command in ('stop-grid','stop-neutral'):
                        from .grid_runner import GridRunner
                        from .account_runtime import runner_for
                        session=next((s for s in store.sessions() if s['id']==args.session_id),None)
                        if session is None:raise ValueError('Etkin grid oturumu bulunamadı.')
                        if session.get('engine') not in ('grid-v2','neutral-v2'):raise ValueError('Grid durdurma için grid/neutral oturumu gerekli.')
                        report=runner_for(service,DemoExchange(Config.load()),RiskLimits.load(args.risk_profile),session).stop(
                            args.session_id,close_position=args.close_position,execute=args.execute_demo)
                    elif args.command in ('manage-all','run-many'):
                        from .account_runtime import start_many,supervise_account
                        exchange=DemoExchange(Config.load());limits=RiskLimits.load(args.risk_profile)
                        if args.command=='run-many':
                            references=[]
                            for value in args.plan:
                                pair=value.rsplit(':',1)
                                if len(pair)!=2:raise ValueError('Plan PLAN_ID:VERSION biçiminde olmalı.')
                                references.append((pair[0],int(pair[1])))
                            try:
                                result=start_many(service,exchange,limits,references,execute=args.execute_demo)
                            except KeyboardInterrupt:
                                if args.execute_demo:
                                    from .account_runtime import _drain_grids
                                    _drain_grids(service,exchange,limits,lambda r:print(json.dumps(r,ensure_ascii=False),flush=True))
                                raise
                            print(json.dumps(result,ensure_ascii=False),flush=True)
                            if not args.execute_demo or result['state']!='STARTED':
                                return 0 if result['state']=='READY' else 1
                        is_grid=any(s.get('engine') in ('grid-v2','neutral-v2') for s in store.sessions())
                        iterations=args.iterations if args.iterations is not None else (0 if is_grid and args.execute_demo else 1)
                        ready=supervise_account(service,exchange,limits,execute=args.execute_demo,iterations=iterations,
                            interval=args.interval,emit=lambda r:print(json.dumps(r,ensure_ascii=False),flush=True),
                            notification_queue=NotificationQueue(store) if args.notify_chat_id else None,
                            notification_chat=args.notify_chat_id)
                        return 0 if ready else 1
                    elif args.command == 'manage':
                        from .v2_runner import V2Runner
                        from .runtime import supervise_session
                        session=next((s for s in store.sessions() if s['id']==args.session_id),None)
                        if session is None:raise ValueError('Etkin oturum bulunamadı.')
                        from .account_runtime import runner_for
                        runner=runner_for(service,DemoExchange(Config.load()),RiskLimits.load(args.risk_profile),session)
                        is_grid=session.get('engine') in ('grid-v2','neutral-v2')
                        iterations=args.iterations if args.iterations is not None else (0 if is_grid and args.execute_demo else 1)
                        user_stream = None
                        if args.user_stream:
                            from .user_stream import DemoUserStream
                            user_stream = DemoUserStream(runner.x)
                        supervise_session(runner,args.session_id,execute=args.execute_demo,iterations=iterations,
                                          interval=args.interval,drain_on_exit=is_grid,user_stream=user_stream,
                                          notification_queue=NotificationQueue(store) if args.notify_chat_id else None,
                                          notification_chat=args.notify_chat_id,
                                          emit=lambda r:print(json.dumps(r,ensure_ascii=False),flush=True))
                        return 0
                    else:
                        report = run_plan(service, DemoExchange(Config.load()), RiskLimits.load(args.risk_profile),
                                          args.plan_id, args.version, args.execute_demo)
                        session=next((s for s in store.sessions()if s.get('plan_ref',{}).get('plan_id')==args.plan_id
                                      and s.get('plan_ref',{}).get('version')==args.version),None)
                        if args.execute_demo and session and (session.get('engine') in ('grid-v2','neutral-v2') or
                                                               session.get('engine')=='v2'and args.iterations is not None):
                            from .runtime import supervise_session
                            from .v2_runner import V2Runner
                            from .grid_runner import GridRunner
                            print(json.dumps(report,ensure_ascii=False),flush=True)
                            is_grid=session['engine'] in ('grid-v2','neutral-v2')
                            from .account_runtime import runner_for
                            runner=runner_for(service,DemoExchange(Config.load()),RiskLimits.load(args.risk_profile),session)
                            supervise_session(runner,session['id'],execute=True,
                                              iterations=args.iterations if args.iterations is not None else 0,
                                              interval=args.interval,drain_on_exit=is_grid,
                                              emit=lambda r:print(json.dumps(r,ensure_ascii=False),flush=True))
                            return 0
                finally:
                    store.close()
    except KeyboardInterrupt:
        logging.info('İzleme durduruldu; kayıtlı oturum ve borsadaki korumalar korunur.')
        return 130
    except (ValueError, ExchangeError, OSError) as exc:
        logging.error('%s', exc)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0
