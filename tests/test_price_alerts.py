from contextlib import closing
import copy,tempfile,unittest
from pathlib import Path
from agentrader.migrations import migrate,connect
from agentrader.price_alerts import PriceAlerts,PriceAlertWorker,AlertError
from agentrader.drawings.service import DrawingConflict
from agentrader.market_data import SOURCE

def definition(**kw):return dict(name='Test',symbol='BTCUSDT',interval='1m',operator='cross_up',price='100',frequency='bar_close',expires_at=None,message='Test',**kw)
def context(n=0,old='98',new='99',epoch='epoch'):
    def row(t,p):return dict(time=t,closed=True,exact=dict(state='VERIFIED',close=p))
    return dict(identity=dict(source=SOURCE,environment='live_public',product='USD-M',price_type='LAST_PRICE',symbol='BTCUSDT',interval='1m'),transport_state='LIVE',timing=dict(state='FRESH'),quality=dict(state='OK'),stream_epoch=epoch,rows=[row(1800000000+n*60,old),row(1800000060+n*60,new)])
class PriceAlertTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'app.db';migrate(self.db);self.now=1800000200;self.s=PriceAlerts(self.db,'owner',lambda:self.now)
    def tearDown(self):self.tmp.cleanup()
    def make(self,**changes):d=definition();d.update(changes);return self.s.save(d)
    def test_closed_cross_dedup_restart_and_persisted_history(self):
        a=self.make();self.s.process(a['id'],context(),'boot');self.assertEqual(self.s.events(),[])
        c=context(1,'99','101');self.s.process(a['id'],c,'boot');self.s.process(a['id'],c,'boot');self.assertEqual(len(self.s.events()),1)
        self.assertEqual(PriceAlerts(self.db,'owner').events(),self.s.events());self.assertEqual(PriceAlerts(self.db,'other').events(),[])
        self.s.process(a['id'],context(2,'99','102'),'restart');self.assertEqual(len(self.s.events()),1)
        self.s.process(a['id'],context(3,'99','103'),'restart');self.assertEqual(len(self.s.events()),2)
    def test_pause_resume_edit_delete_revision_and_once(self):
        a=self.make(frequency='once');self.s.action(a['id'],1,'pause');self.s.process(a['id'],context(1,'99','101'),'boot');self.assertEqual(self.s.events(),[])
        with self.assertRaises(DrawingConflict):self.s.action(a['id'],1,'resume')
        self.s.action(a['id'],2,'resume');self.s.process(a['id'],context(),'boot');self.s.process(a['id'],context(1,'99','101'),'boot');self.assertEqual(self.s.list()[0]['state'],'TRIGGERED')
        self.s.process(a['id'],context(2,'99','101'),'boot');self.assertEqual(len(self.s.events()),1)
        d=definition();d['price']='105';self.s.save(d,a['id'],3);self.assertEqual(self.s.list()[0]['revision'],4);self.s.action(a['id'],4,'delete');self.assertEqual(self.s.list(),[]);self.assertEqual(len(self.s.events()),1)
    def test_stale_epoch_and_missed_closes_reseed_without_replay(self):
        a=self.make();self.s.process(a['id'],context(),'boot');bad=context(1,'99','101');bad['timing']['state']='BLOCKED';self.s.process(a['id'],bad,'boot');self.s.process(a['id'],context(2,'99','101'),'boot');self.assertEqual(self.s.events(),[])
        self.s.process(a['id'],context(3,'99','101',epoch='new'),'boot');self.assertEqual(self.s.events(),[])
        self.s.process(a['id'],context(6,'99','101',epoch='new'),'boot');self.assertEqual(self.s.events(),[])
        self.s.process(a['id'],context(7,'99','101',epoch='new'),'boot');self.assertEqual(len(self.s.events()),1)
    def test_expiry_and_invalid_inputs(self):
        a=self.make(expires_at=self.now+1);self.now+=2;self.s.process(a['id'],None,'boot');self.assertEqual(self.s.list()[0]['state'],'EXPIRED')
        for patch in ({'price':'NaN'},{'price':'-1'},{'frequency':'intrabar'},{'interval':'2m'},{'expires_at':float('nan')},{'name':''}):
            d=definition();d.update(patch)
            with self.assertRaises(AlertError):self.s.save(d)
    def test_worker_owns_feed_without_browser_and_releases_after_pause(self):
        a=self.make()
        class Hub:
            def __init__(self):self.held=0;self.c=context()
            def acquire(self,*args):self.held+=1;return object()
            def release(self,f):self.held-=1
            def binding_context(self,*args):return self.c
        h=Hub();w=PriceAlertWorker(self.s,h);w.tick();self.assertEqual(h.held,1);h.c=context(1,'99','101');w.tick();self.assertEqual(len(self.s.events()),1)
        self.s.action(a['id'],1,'pause');w.tick();self.assertEqual(h.held,0);w.close()
    def test_bad_market_or_open_only_history_never_triggers(self):
        a=self.make();self.s.process(a['id'],context(),'boot')
        for alter in ('identity','exact','closed'):
            c=context(1,'99','101')
            if alter=='identity':c['identity']['symbol']='ETHUSDT'
            elif alter=='exact':c['rows'][-1]['exact']['close']='NaN'
            else:c['rows'][-1]['closed']=False
            self.s.process(a['id'],c,'boot')
        self.assertEqual(self.s.events(),[])


class PriceAlertApiTests(unittest.TestCase):
    def test_real_api_lifecycle_restart_owner_and_no_execution_store(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        class Market:
            def selection(self,*args):return None
        class Hub:
            def binding_context(self,*args):return None
            def acquire(self,*args):return object()
            def release(self,*args):pass
            def close(self):pass
        with tempfile.TemporaryDirectory() as folder:
            settings=WebSettings(Path(folder)/'app.db',Path(folder)/'execution.db',market_database=Path(folder)/'market.db')
            for run in (0,1):
                with TestClient(create_app(settings,market=Market(),hub=Hub()),base_url='http://127.0.0.1') as client:
                    if run==0:
                        r=client.post('/api/alerts',json={'definition':definition()});self.assertEqual(r.status_code,201);a=r.json()
                        self.assertEqual(client.post('/api/alerts/'+a['id']+'/action',json={'revision':1,'action':'pause'}).status_code,200)
                    else:
                        data=client.get('/api/alerts').json();self.assertEqual(data['alerts'][0]['state'],'PAUSED');self.assertFalse(data['order_authority'])
                        self.assertEqual(client.post('/api/alerts/'+a['id']+'/action',json={'revision':1,'action':'resume'}).status_code,409)
                        self.assertEqual(client.post('/api/alerts/'+a['id']+'/action',json={'revision':2,'action':'resume'}).status_code,200)
                        self.assertEqual(client.put('/api/alerts/'+a['id'],json={'revision':3,'definition':definition()}).status_code,200)
                        self.assertEqual(client.post('/api/alerts/'+a['id']+'/action',json={'revision':4,'action':'delete'}).status_code,200)
                        self.assertEqual(client.get('/api/alerts').json()['alerts'],[])
                    self.assertFalse(settings.execution_database.exists())


class BackgroundAlertTests(unittest.TestCase):
    def test_background_thread_triggers_without_http_or_browser_clients_and_shuts_down(self):
        import threading,time
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'app.db';migrate(db);service=PriceAlerts(db,'owner');a=service.save(definition())
            class Hub:
                def __init__(self):self.c=context();self.references=0;self.seeded=threading.Event()
                def acquire(self,*args):self.references+=1;return object()
                def release(self,f):self.references-=1
                def binding_context(self,*args):self.seeded.set();return copy.deepcopy(self.c)
            hub=Hub();worker=PriceAlertWorker(service,hub);worker.start()
            try:
                self.assertTrue(hub.seeded.wait(3))
                deadline=time.monotonic()+3
                while service.list()[0]['readiness']!='READY' and time.monotonic()<deadline:time.sleep(.02)
                hub.c=context(1,'99','101');deadline=time.monotonic()+4
                while not service.events() and time.monotonic()<deadline:time.sleep(.02)
                self.assertEqual(len(service.events()),1);self.assertEqual(hub.references,1)
            finally:worker.close()
            self.assertFalse(worker.thread.is_alive());self.assertEqual(hub.references,0)
