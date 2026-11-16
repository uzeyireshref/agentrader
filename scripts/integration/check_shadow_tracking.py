
# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from contextlib import ExitStack
"""Real isolated API/browser/worker acceptance with frozen demo market contexts."""
import copy,hashlib,json,socket,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import httpx,uvicorn
from playwright.sync_api import sync_playwright,expect
from scripts.chart.run_chart_p7 import Harness
from agentrader.api.app import create_app
from agentrader.application.settings import WebSettings
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT


def main():
    report=dict(passed=False,checks=[],external_requests=0,account_requests=0,order_requests=0)
    server=None;thread=None;h=Harness()
    class Hub:
        def __init__(self):self.value=h.context(0);self.references=0;self.sequence=0;self.closed=False
        def acquire(self,*args):self.references+=1;return type('Feed',(),{'state':self})()
        def release(self,feed):self.references-=1
        def binding_context(self,*args):return copy.deepcopy(self.value) if self.references else None
        def packet(self,*args):
            c=copy.deepcopy(self.value);self.sequence+=1
            return dict(type='snapshot',source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE',symbol='BTCUSDT',interval='15m',stream_epoch=c['stream_epoch'],generation=c['generation'],sequence=self.sequence,status='LIVE',received_at=int(time.time()*1000),candles=c['rows'],quality=c['quality'],market=c['market'],data_proof=c['data_proof'],timing=c['timing'],close_event=None)
        def close(self):self.closed=True
    hub=Hub()
    class Market:
        def catalog(self):return dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE',markets=[hub.value['market']],intervals=['15m'])
        def history(self,*args,**kwargs):return dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE',symbol='BTCUSDT',interval='15m',candles=hub.value['rows'],has_more=False)
    try:
        with ExitStack() as stack:
            folder=stack.enter_context(tempfile.TemporaryDirectory(prefix='shadow-acceptance-'))
            folder=Path(folder);execution=folder/'execution.db';execution.write_bytes(b'UNCHANGED_EXECUTION')
            baseline=hashlib.sha256(execution.read_bytes()).hexdigest()
            settings=WebSettings(application_database=folder/'app.db',execution_database=execution,market_database=folder/'market.db',owner='fixture')
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            app=create_app(settings,market=Market(),hub=hub)
            server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='error',access_log=False))
            thread=threading.Thread(target=server.run,daemon=True);thread.start()
            def stop_server():
                server.should_exit=True;thread.join(timeout=30)
            stack.callback(stop_server)
            deadline=time.monotonic()+15
            while not server.started and time.monotonic()<deadline:time.sleep(.1)
            assert server.started
            base='http://127.0.0.1:'+str(port)
            with httpx.Client(base_url=base,timeout=10) as client:
                drawing=client.post('/api/workspaces/main/drawings',json=dict(request_id='drawing',geometry=h.d['geometry'])).json()
                d=h.b['definition'];payload=dict(request_id='binding',expected_binding_revision=0,target=dict(type='drawing',object_id=drawing['drawing_id'],revision=1),symbol='BTCUSDT',interval='15m',scale='LINEAR',grid_times=d['grid']['times'],data_snapshot_hash=None,query=d['query'],rule=d['rule'])
                response=client.put('/api/workspaces/main/bindings/shadow-test',json=payload);assert response.status_code==200,response.text
                binding=response.json();url='/api/workspaces/main/bindings/shadow-test/shadow'
                assert client.post(url,json=dict(expected_revision=1,definition_hash=binding['definition_hash'],action='start',ttl_seconds=60,context=hub.value)).status_code==422
                assert client.post(url,headers={'Origin':'https://evil.invalid'},json={}).status_code==403
                report['checks'].append('client evidence injection and cross-origin command rejected')
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel='chrome',headless=True)
                    page=browser.new_page(viewport=dict(width=1536,height=960));page.goto(base,wait_until='networkidle')
                    page.locator('summary[aria-label="Paneller"]').click();page.get_by_role('button',name='Araç / kural bağları',exact=True).click()
                    section=page.get_by_role('region',name='Gölge sinyal takibi')
                    # Section has an accessible name and is a real named region.
                    start=section.get_by_role('button',name='Gölge takibi başlat',exact=True)
                    expect(start).to_be_enabled();start.click()
                    deadline=time.monotonic()+10
                    while time.monotonic()<deadline:
                        status=client.get(url).json()
                        if status['run'] and status['run']['state']=='WATCHING':break
                        time.sleep(.1)
                    assert status['run']['state']=='WATCHING',status
                    assert not status['events']
                    browser.close()
                deadline=time.monotonic()+5
                while hub.references>1 and time.monotonic()<deadline:time.sleep(.1)
                assert hub.references==1,hub.references
                report['checks'].append('explicit UI start, seed without event, worker retains feed after browser closes')
                hub.value=h.context(1,close='99.8',high='100',low='99.4')
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    status=client.get(url).json()
                    if status['events']:break
                    time.sleep(.1)
                assert status['run']['state']=='LATCHED' and len(status['events'])==1,status
                assert status['events'][0]['kind']=='TOUCH' and status['events'][0]['order_authority'] is False
                time.sleep(1.2);assert len(client.get(url).json()['events'])==1
                report['checks'].append('browser-independent worker records one explained event and latches')
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel='chrome',headless=True);page=browser.new_page(viewport=dict(width=1536,height=960));page.goto(base,wait_until='networkidle')
                    page.locator('summary[aria-label="Paneller"]').click();page.get_by_role('button',name='Araç / kural bağları',exact=True).click()
                    expect(page.get_by_role('status').filter(has_text='Sinyal kaydedildi')).to_be_visible()
                    page.get_by_role('region',name='Gölge sinyal takibi').locator('li').first.scroll_into_view_if_needed()
                    page.screenshot(path=str(ROOT/'reports/shadow-tracking-ui-20261113.png'));browser.close()
                assert hashlib.sha256(execution.read_bytes()).hexdigest()==baseline
                report['checks'].append('event history visible on reopen; execution sentinel unchanged')
            server.should_exit=True;thread.join(timeout=20);assert not thread.is_alive()
            report['passed']=True
    except Exception:
        import traceback
        report['error']=traceback.format_exc()
    finally:
        if server:server.should_exit=True
        if thread:thread.join(timeout=20)
        h.close()
    (ROOT/'reports/shadow-tracking-validation-20261113.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report));return report['passed']

if __name__=='__main__':sys.exit(0 if main() else 1)
