"""Isolated real HTTP process harness shared by adapter tests and acceptance."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import httpx

ROOT=Path(__file__).resolve().parents[2]


class ChartBotFixture:
    def __init__(self):
        self.temp=tempfile.TemporaryDirectory(prefix='g8-chart-bot-');self.folder=Path(self.temp.name)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
        self.base=f'http://127.0.0.1:{self.port}';self.human_token=secrets.token_hex(24);self.bot_token=secrets.token_hex(24)
        self.env=dict(os.environ,AGENTRADER_G8_FIXTURE='EXPLICIT_SYNTHETIC',AGENTRADER_WEB_DATABASE=str(self.folder/'app.db'),
                      AGENTRADER_EXECUTION_DATABASE=str(self.folder/'execution.db'),AGENTRADER_CHART_DATABASE=str(self.folder/'market.db'),
                      AGENTRADER_WEB_TOKEN=self.human_token,AGENTRADER_CHART_BOT_TOKEN=self.bot_token,
                      AGENTRADER_CHART_BOT_ID='alpha',AGENTRADER_CHART_STRATEGY_ID='synthetic')
        self.server=None;self.log=None
        self.human=httpx.Client(base_url=self.base,headers={'Authorization':'Bearer '+self.human_token},timeout=10)

    def start(self):
        self.log=(self.folder/'server.log').open('a',encoding='utf-8')
        self.server=subprocess.Popen([sys.executable,'-m','uvicorn','scripts.integration.g8_fixture_server:create','--factory','--host','127.0.0.1','--port',str(self.port),'--log-level','warning'],
                     cwd=ROOT,env=self.env,stdout=self.log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for _ in range(100):
            if self.server.poll() is not None:break
            try:
                if self.human.get('/api/health').status_code==200:return self
            except httpx.HTTPError:pass
            time.sleep(.1)
        raise RuntimeError('Isolated chart bot fixture failed to start')

    def stop(self):
        if self.server is not None and self.server.poll() is None:self.server.terminate();self.server.wait(timeout=10)
        if self.log is not None:self.log.close()

    def close(self):
        self.stop();self.human.close();self.temp.cleanup()

    def __enter__(self):
        try:return self.start()
        except BaseException:self.close();raise

    def __exit__(self,*args):self.close()
