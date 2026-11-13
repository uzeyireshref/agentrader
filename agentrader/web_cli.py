"""Local API, application migrations, and read-only worker entry points."""
import argparse
import json
import sqlite3

from .application.service import ApplicationService
from .application.settings import WebSettings


def main(argv=None):
    parser = argparse.ArgumentParser(prog='agentrader web')
    sub = parser.add_subparsers(dest='command', required=True)
    serve = sub.add_parser('serve', help='Yalnız 127.0.0.1 üzerinde yerel API')
    serve.add_argument('--port', type=int, default=8765)
    sub.add_parser('migrate', help='Ayrı uygulama deposunun şemasını hazırla')
    worker = sub.add_parser('worker', help='Yalnız runtime.inspect komutlarını işle')
    worker.add_argument('--once', action='store_true')
    worker.add_argument('--interval', type=int, default=2)
    args = parser.parse_args(argv)
    if args.command == 'serve' and not 1 <= args.port <= 65535:
        parser.error('Port 1–65535 aralığında olmalı.')
    try:
        settings = WebSettings.load()
        if args.command == 'serve':
            try:
                import uvicorn
                from .api.app import create_app
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
            from .application.worker import run_worker
            run_worker(ApplicationService(settings), once=args.once, interval=args.interval,
                       emit=lambda result: print(json.dumps(result, ensure_ascii=False), flush=True))
        return 0
    except KeyboardInterrupt:
        return 0
    except (ValueError, OSError, sqlite3.Error):
        # Do not echo config, token, DB payloads or credential-bearing exception text.
        print(json.dumps({'error': 'LOCAL_WEB_START_FAILED'}))
        return 1
