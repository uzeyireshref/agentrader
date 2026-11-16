"""Serve the current build on an ephemeral port for legacy mocked browser suites."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
from urllib.request import build_opener,ProxyHandler
ROOT=Path(__file__).resolve().parents[2]

def main():
    script,*args=sys.argv[1:]
    assert script in {'check_alert_conditions.mts','check_alert_schedule.mts','check_alert_frequencies.mts','check_alert_channels.mts','check_alert_notifications.mts'}
    with tempfile.TemporaryDirectory(prefix='g10-browser-') as folder:
        folder=Path(folder)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(folder/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(folder/'execution.db'),AGENTRADER_CHART_DATABASE=str(folder/'market.db'),AGENTRADER_WEB_TOKEN='',AGENTRADER_CHART_BOT_TOKEN='',AGENTRADER_TEST_BASE_URL=base)
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        server=subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
        try:
            opener=build_opener(ProxyHandler({}))
            for _ in range(150):
                try:
                    with opener.open(base+'/api/health',timeout=1) as response:assert not json.load(response)['trading_commands_enabled']
                    break
                except OSError:time.sleep(.1)
            else:raise RuntimeError('Isolated server unavailable')
            result=subprocess.run(['node',str(ROOT/'frontend/node_modules/tsx/dist/cli.mjs'),str(script_path(script)),*args],cwd=ROOT,env=env,creationflags=flags,timeout=350)
            assert not (folder/'execution.db').exists() and not (folder/'market.db').exists()
            return result.returncode
        finally:server.terminate();server.wait(timeout=10)

if __name__=='__main__':raise SystemExit(main())
