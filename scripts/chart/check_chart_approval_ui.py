
# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from contextlib import ExitStack
"""Real isolated API/browser/worker acceptance with frozen demo market contexts."""
import argparse,copy,hashlib,json,socket,sys,tempfile,threading,time,secrets
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import httpx,uvicorn
from playwright.sync_api import sync_playwright,expect
from scripts.chart.run_chart_p7 import Harness
from agentrader.api.app import create_app
from agentrader.application.settings import WebSettings
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT
from agentrader.integration.signal_previews import SignalPreviews
from agentrader.bot.risk import RiskLimits
from agentrader.chart.drawings.service import DrawingService
sys.path.insert(0,str(ROOT/'tests'))
from test_orders import SYMBOL
from test_v2_preflight import SnapshotExchange
from agentrader.shared.config import Config
from agentrader.integration.preview_preflight import ReadOnlyDemoAccount,local_preview_provider
from agentrader.integration.chart_execution import review_preview,guard_chart_entry,require_demo_acceptance
from agentrader.integration.chart_approval import pulse,process_once
from agentrader.bot.plans import PlanService
from agentrader.shared.state import StateStore


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--synthetic-demo-acceptance',action='store_true');args=parser.parse_args()
    report=dict(passed=False,checks=[],external_requests=0,account_requests=0,order_requests=0)
    report['demo_acceptance_scope']='INJECTED_TEST_DEPENDENCY_NOT_LIVE_ACCEPTANCE' if args.synthetic_demo_acceptance else 'REAL_CONTINUITY_RECEIPT'
    acceptance_options=dict(acceptance=lambda:True) if args.synthetic_demo_acceptance else {}
    def fixture_guard(*a,**kw):return guard_chart_entry(*a,**kw,**acceptance_options)
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
    public_calls=[]
    class Public:
        def get(self,path,params=None):
            public_calls.append(path)
            if path.endswith('exchangeInfo'):return dict(symbols=[{**copy.deepcopy(SYMBOL),'contractType':'PERPETUAL'}])
            if path.endswith('premiumIndex'):return dict(symbol='BTCUSDT',markPrice='100',time=int(time.time()*1000))
            if path.endswith('/time'):return dict(serverTime=int(time.time()*1000))
            raise AssertionError('Unexpected public endpoint')
    class Market:
        def catalog(self):return dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE',markets=[hub.value['market']],intervals=['15m'])
        def history(self,*args,**kwargs):return dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE',symbol='BTCUSDT',interval='15m',candles=hub.value['rows'],has_more=False)
    try:
        with ExitStack() as stack:
            folder=stack.enter_context(tempfile.TemporaryDirectory(prefix='shadow-acceptance-'))
            folder=Path(folder);execution=folder/'execution.db'
            if args.synthetic_demo_acceptance:
                try:require_demo_acceptance(folder);raise AssertionError('Missing live evidence accepted')
                except ValueError as error:assert str(error)=='DEMO_CONTINUITY_ACCEPTANCE_REQUIRED'
                report['checks'].append('production live acceptance still rejects absent evidence; UI fixture injects acceptance dependency only')
            settings=WebSettings(application_database=folder/'app.db',execution_database=execution,market_database=folder/'market.db',owner='fixture',token=secrets.token_urlsafe(32))
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            previews=SignalPreviews(settings.application_database,'fixture',hub,public_factory=Public,limits=RiskLimits())
            app=create_app(settings,market=Market(),hub=hub,previews=previews)
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
                    page.get_by_text('İşlem planı önizlemesi',exact=True).click()
                    form=page.get_by_role('region',name='Sinyalden plan önizlemesi')
                    form.get_by_label('Önizleme yönü',exact=True).select_option('LONG')
                    for label,value in [('Önizleme giriş','100'),('Önizleme stop','98'),('Önizleme hedef','104'),('Önizleme nominal','60'),('Önizleme kaldıraç','2')]:form.get_by_label(label,exact=True).fill(value)
                    form.get_by_role('button',name='Plan önizlemesi oluştur',exact=True).click()
                    expect(form.get_by_role('status')).to_contain_text('Yalnız önizleme')
                    preview_url='/api/workspaces/main/shadow-events/'+status['events'][0]['event_id']+'/preview'
                    preview=client.get(preview_url).json()
                    assert preview['version']==1 and preview['execution_eligible'] is False and preview['approval_state']=='NOT_REQUESTED'
                    class FakeAccount(SnapshotExchange):
                        config=Config('isolated-demo-key','isolated-secret')
                        def request(self,method,path,params=None):
                            if method!='GET':raise AssertionError('Exchange mutation forbidden')
                            return self.get(path,params)
                        def get(self,path,params=None):
                            for key in ('/fapi/v1/premiumIndex','/fapi/v1/assetIndex'):
                                self.data[key]['time']=int(time.time()*1000)
                            return super().get(path,params)
                    account=FakeAccount();account.data['/fapi/v1/symbolConfig'][0].update(leverage=2,marginType='ISOLATED')
                    account.data['/fapi/v1/premiumIndex']['markPrice']='100'
                    account=ReadOnlyDemoAccount(account)
                    store=StateStore(execution)
                    try:
                        service=PlanService(store,'fixture')
                        reviewed=review_preview(service,local_preview_provider('main',preview['event_id'],1,port),account,RiskLimits(),workspace='main',event_id=preview['event_id'],version=1,port=port,**acceptance_options)
                        assert reviewed['state']=='PENDING_APPROVAL'
                        pulse(settings)
                        page.get_by_text('Yerel demo planını incele ve onayla',exact=True).click()
                        approval=page.get_by_role('region',name='Demo planı kullanıcı onayı')
                        approval.get_by_label('Yerel erişim anahtarı',exact=True).fill(settings.token)
                        approval.get_by_role('button',name='Yerel oturumu aç',exact=True).click()
                        expect(approval.get_by_text('Plan özeti:',exact=False)).to_be_visible()
                        approve=approval.get_by_role('button',name='Bu demo planına süreli onay ver',exact=True)
                        expect(approve).to_be_disabled()
                        approval.get_by_label('Planı ve demo hesap kimliğini kontrol ettim',exact=True).check()
                        expect(approve).to_be_enabled()
                        with page.expect_response('**/approval-requests') as queued:approve.click()
                        job=queued.value.json();assert job['state']=='PENDING'
                        assert service.show(reviewed['plan']['plan_id'],1)['state']=='PENDING_APPROVAL'
                        report['checks'].append('authenticated browser review and explicit checkbox only enqueue scoped consent')
                        result=process_once(settings,account,RiskLimits(),guard=fixture_guard)
                        assert result['state']=='APPROVED',result
                        expect(approval.get_by_role('status')).to_contain_text('Demo planı onaylandı; emir gönderilmedi.')
                        expect(approval.get_by_text('Plan '+reviewed['plan']['plan_id']+' · v1 · Onaylı',exact=True)).to_be_visible()
                        assert service.show(reviewed['plan']['plan_id'],1)['state']=='AUTHORIZED'
                        assert store.intents()==[]
                        assert settings.token not in page.locator('body').inner_text()
                        assert reviewed['authorization_token'] not in page.locator('body').inner_text()
                        assert settings.token not in page.evaluate('JSON.stringify({...localStorage,...sessionStorage})')
                        page.screenshot(path=str(ROOT/'reports/chart-approval-ui-20261114.png'))
                        report['checks'].append('read-only fake account revalidation authorizes exact plan, no exchange orders or browser-stored secrets')
                        DrawingService(settings.application_database,'fixture').update(drawing['drawing_id'],'after-consent',1,{**drawing['geometry'],'label':'Changed after consent'})
                        try:fixture_guard(service,account,RiskLimits(),reviewed['plan']);raise AssertionError('revoked source accepted')
                        except ValueError:pass
                        assert store.intents()==[]
                        report['checks'].append('drawing change after consent still blocks entry; account and order endpoints never exposed')
                    finally:store.close()
                    browser.close()
            report['public_demo_fixture_calls']=public_calls
            report['passed']=True
    except Exception:
        import traceback
        report['error']=traceback.format_exc()
    finally:
        if server:server.should_exit=True
        if thread:thread.join(timeout=20)
        h.close()
    (ROOT/'reports/chart-approval-ui-validation-20261114.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report));return report['passed']

if __name__=='__main__':sys.exit(0 if main() else 1)
