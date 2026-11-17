"""Local API, application migrations, and read-only worker entry points."""
import argparse
import json
import sqlite3

from agentrader.application.service import ApplicationService
from agentrader.application.settings import WebSettings


def main(argv=None):
    parser = argparse.ArgumentParser(prog='agentrader web')
    sub = parser.add_subparsers(dest='command', required=True)
    serve = sub.add_parser('serve', help='Yalnız 127.0.0.1 üzerinde yerel API')
    serve.add_argument('--port', type=int, default=8765)
    sub.add_parser('migrate', help='Ayrı uygulama deposunun şemasını hazırla')
    worker = sub.add_parser('worker', help='Yalnız runtime.inspect komutlarını işle')
    worker.add_argument('--once', action='store_true')
    worker.add_argument('--interval', type=int, default=2)
    bot_worker=sub.add_parser('bot-worker',help='Kimlik doğrulamalı Bot terminali kuyruğu; yazma yalnız --execute-demo ile')
    bot_worker.add_argument('--once',action='store_true')
    bot_worker.add_argument('--interval',type=int,default=1)
    bot_worker.add_argument('--execute-demo',action='store_true')
    preflight = sub.add_parser('preflight-preview', help='Grafik önizlemesini demo hesapta salt okunur kontrol et; emir/onay oluşturmaz')
    preflight.add_argument('workspace')
    preflight.add_argument('event_id')
    preflight.add_argument('version', type=int)
    preflight.add_argument('--port', type=int, default=8765)
    review = sub.add_parser('review-preview', help='Güncel demo önizlemesini onay bekleyen plana aktar; emir göndermez')
    review.add_argument('workspace')
    review.add_argument('event_id')
    review.add_argument('version', type=int)
    review.add_argument('--port', type=int, default=8765)
    approvals = sub.add_parser('approval-worker', help='Yalnız açık web onay isteklerini demo hesapta kontrol et; emir göndermez')
    approvals.add_argument('--once', action='store_true')
    approvals.add_argument('--interval', type=int, default=2)
    args = parser.parse_args(argv)
    if args.command == 'serve' and not 1 <= args.port <= 65535:
        parser.error('Port 1–65535 aralığında olmalı.')
    if args.command == 'approval-worker' and not 1 <= args.interval <= 10:
        parser.error('Onay işçisi aralığı 1–10 saniye olmalı.')
    try:
        settings = WebSettings.load()
        if args.command == 'bot-worker':
            from agentrader.application.bot_worker import run_bot_worker
            run_bot_worker(settings,execute=args.execute_demo,once=args.once,interval=args.interval,
                           emit=lambda result:print(json.dumps(dict(job_id=result['job_id'],state=result['state'],error_code=result['error_code'])),flush=True))
        elif args.command == 'approval-worker':
            from agentrader.integration.chart_approval import run_approval_worker
            run_approval_worker(settings, once=args.once, interval=args.interval)
        elif args.command == 'review-preview':
            from agentrader.integration.chart_execution import local_review
            print(json.dumps(local_review(settings, args.workspace, args.event_id, args.version, args.port), ensure_ascii=False))
        elif args.command == 'preflight-preview':
            from agentrader.integration.preview_preflight import local_preflight
            print(json.dumps(local_preflight(args.workspace, args.event_id, args.version, args.port), ensure_ascii=False))
        elif args.command == 'serve':
            try:
                import uvicorn
                from agentrader.api.app import create_app
            except ImportError:
                print(json.dumps({'error': 'WEB_DEPENDENCIES_MISSING',
                                  'install': 'python -m pip install -e ".[web]"'}))
                return 1
            # No reload/workers option: HTTP startup never creates a trading monitor.
            uvicorn.run(create_app(settings), host='127.0.0.1', port=args.port,
                        workers=1, proxy_headers=False, server_header=False, access_log=False)
        elif args.command == 'migrate':
            print(json.dumps(ApplicationService(settings).initialize()))
        else:
            from agentrader.application.worker import run_worker
            run_worker(ApplicationService(settings), once=args.once, interval=args.interval,
                       emit=lambda result: print(json.dumps(result, ensure_ascii=False), flush=True))
        return 0
    except KeyboardInterrupt:
        return 0
    except (ValueError, OSError, sqlite3.Error):
        # Do not echo config, token, DB payloads or credential-bearing exception text.
        print(json.dumps({'error': 'LOCAL_WEB_START_FAILED'}))
        return 1
