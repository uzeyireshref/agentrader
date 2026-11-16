"""Isolated real HTTP/WS demo acceptance; never opens an execution account."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import hashlib, json, socket, sys, tempfile, threading, time
from pathlib import Path
from urllib.parse import urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import httpx, uvicorn, websocket
from agentrader.api.app import create_app
from agentrader.application.settings import WebSettings
from agentrader.shared.market_environment import SOURCE, ENVIRONMENT
from agentrader.shared.transport import JsonTransport

ROOT=Path(__file__).resolve().parents[2]

def run():
    external=[]; original=JsonTransport.perform; original_ws=websocket.create_connection
    def transport(self,opener,factory,method,base):
        host=urlsplit(base).hostname;external.append(dict(kind='REST',host=host,method=method))
        assert host=='demo-fapi.binance.com' and method=='GET', 'Non-demo/public request'
        return original(self,opener,factory,method,base)
    def connect(url,*args,**kwargs):
        host=urlsplit(url).hostname
        if host not in ('127.0.0.1','localhost'):
            external.append(dict(kind='WS',host=host));assert host=='demo-fstream.binance.com','Non-demo stream'
        return original_ws(url,*args,**kwargs)
    JsonTransport.perform=transport;websocket.create_connection=connect
    report=dict(schema='demo-transition-validation/1',checks=[],external_requests=external,account_requests=0,order_requests=0)
    server=None;thread=None;stream=None
    try:
        with tempfile.TemporaryDirectory(prefix='demo-transition-') as folder:
            folder=Path(folder);sentinel=folder/'execution.db';sentinel.write_bytes(b'UNCHANGED_EXECUTION_SENTINEL')
            before=hashlib.sha256(sentinel.read_bytes()).hexdigest()
            settings=WebSettings(application_database=folder/'app.db',market_database=folder/'market.db',execution_database=sentinel)
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            server=uvicorn.Server(uvicorn.Config(create_app(settings),host='127.0.0.1',port=port,log_level='error',access_log=False))
            thread=threading.Thread(target=server.run,daemon=True);thread.start()
            base='http://127.0.0.1:'+str(port)
            deadline=time.monotonic()+20
            while not server.started and time.monotonic()<deadline:time.sleep(.1)
            assert server.started
            with httpx.Client(base_url=base,timeout=25) as client:
                health=client.get('/api/health').json();assert health['market_environment']==ENVIRONMENT and not health['trading_commands_enabled']
                catalog=client.get('/api/markets').json();assert catalog['source']==SOURCE and catalog['environment']==ENVIRONMENT
                symbols=[s for s in ('BTCUSDT','ETHUSDT') if any(m['symbol']==s for m in catalog['markets'])];assert len(symbols)==2
                for symbol in symbols:
                    for interval in ('1m','5m','1h','1d'):
                        response=client.get('/api/candles',params=dict(symbol=symbol,interval=interval,limit=30));assert response.status_code==200,response.text
                        data=response.json();assert data['source']==SOURCE and data['environment']==ENVIRONMENT and data['candles']
                        report['checks'].append(dict(name='history',symbol=symbol,interval=interval,bars=len(data['candles']),quality=data['quality']))
                assert client.get('/api/candles',params=dict(symbol='BTCUSDT',interval='7m')).status_code==422
                assert client.post('/api/commands',json=dict(request_id='no-trade',action='order.buy',payload={})).status_code in (401,503)
                from playwright.sync_api import sync_playwright, expect
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel='chrome',headless=True)
                    page=browser.new_page(viewport=dict(width=1536,height=960))
                    page.goto(base,wait_until='networkidle');page.get_by_text('Binance Demo USD-M',exact=False).first.wait_for()
                    expect(page.locator('.loaded-count')).not_to_have_text('0 mum',timeout=45000)
                    expect(page.locator('.shell-state')).to_have_text('Canlı',timeout=45000)
                    page.screenshot(path=str(ROOT/'reports/demo-transition-ui-20261113.png'))
                    report['checks'].append(dict(name='browser_demo_label_and_live_candles',passed=True,loaded=page.locator('.loaded-count').inner_text()))
                    browser.close()
                stream=websocket.create_connection('ws://127.0.0.1:'+str(port)+'/api/market-stream?symbol=BTCUSDT&interval=1m',origin=base,timeout=15)
                started=time.monotonic();closes=set();live=0;last_sequence=-1
                while time.monotonic()-started<150:
                    packet=json.loads(stream.recv())
                    assert packet.get('type')!='error',packet
                    assert packet['source']==SOURCE and packet['environment']==ENVIRONMENT
                    if packet.get('status')=='LIVE':live+=1
                    if packet.get('close_event'):closes.add(packet['close_event']['event_id'])
                    last_sequence=packet['sequence']
                    if live>=2 and len(closes)>=2:break
                report['checks'].append(dict(name='live_stream',live_packets=live,unique_closes=len(closes),duration_seconds=round(time.monotonic()-started,1)))
                assert live>=2 and len(closes)>=2
                stream.close();stream=None
            server.should_exit=True;thread.join(timeout=20);assert not thread.is_alive()
            # Real restart keeps the same demo application marker and persisted DB.
            from agentrader.application.service import ApplicationService
            ApplicationService(settings).initialize()
            assert hashlib.sha256(sentinel.read_bytes()).hexdigest()==before
            report['checks'].append(dict(name='restart_and_execution_unchanged',passed=True))
            report['passed']=True
    except Exception:
        import traceback
        report['passed']=False;report['error']=traceback.format_exc()
    finally:
        if stream:stream.close()
        if server:server.should_exit=True
        if thread:thread.join(timeout=20)
        JsonTransport.perform=original;websocket.create_connection=original_ws
    (ROOT/'reports/demo-transition-validation-20261113.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report));return report['passed']

if __name__=='__main__':sys.exit(0 if run() else 1)
