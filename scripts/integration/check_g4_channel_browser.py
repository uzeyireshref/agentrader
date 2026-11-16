"""Run existing eight-family pointer/settings acceptance on an isolated local server."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import build_opener, ProxyHandler

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/chart-interface-g4-20261115/browser-pointer'


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--log',action='store_true');parser.add_argument('--dpr2',action='store_true');parser.add_argument('--output-dir',type=Path);args=parser.parse_args()
    if args.output_dir is not None:OUT=args.output_dir.resolve()
    elif args.log:OUT=OUT.with_name('browser-pointer-log')
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='g4-pointer-') as folder:
        folder=Path(folder)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(folder/'app.db'),
                 AGENTRADER_EXECUTION_DATABASE=str(folder/'execution.db'),
                 AGENTRADER_CHART_DATABASE=str(folder/'market.db'),AGENTRADER_WEB_TOKEN='',AGENTRADER_CHART_BOT_TOKEN='')
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        server=subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,
                                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
        try:
            opener=build_opener(ProxyHandler({}))
            for _ in range(100):
                try:
                    with opener.open(f'http://127.0.0.1:{port}/api/health',timeout=1) as response:
                        assert not json.load(response)['trading_commands_enabled']
                    break
                except OSError: time.sleep(.1)
            else: raise RuntimeError('Isolated server unavailable')
            result=subprocess.run(['node',str(ROOT/'frontend/node_modules/tsx/dist/cli.mjs'),
                                   str(ROOT/'scripts/chart/check_channel_family.mts'),f'http://127.0.0.1:{port}',
                                   '--report-dir',str(OUT)]+(['--log'] if args.log else [])+(['--dpr2'] if args.dpr2 else []),cwd=ROOT,env=env,creationflags=flags,timeout=240)
            evidence=json.loads((OUT/'result.json').read_text())
            assert not (folder/'execution.db').exists()
            assert not (folder/'market.db').exists()
            return 0 if result.returncode==0 and evidence['passed'] else 1
        finally:
            server.terminate();server.wait(timeout=10)


if __name__=='__main__':raise SystemExit(main())
