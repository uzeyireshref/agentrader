import copy
import tempfile
import unittest
from pathlib import Path
from agentrader.price_alerts import PriceAlerts, PriceAlertWorker, definition, AlertError
from agentrader.market_data import SOURCE, INTERVALS
from agentrader.migrations import migrate
from agentrader.indicator_config import defaults_v4

T = 1800057600


def draft(frequency='bar'):
    return dict(schema='technical-alert/4', evaluation='intrabar', name='Live', symbol='BTCUSDT',
                interval='5m', frequency=frequency, expires_at=None, message='Live observation', match='all',
                conditions=[dict(interval='5m', left=dict(type='market', field='close'),
                                 operator='above', right=dict(type='value', value='100'), upper=None, bars=1)])


def context(offset=1, price=101, interval='5m', epoch='a'):
    step = INTERVALS[interval]//1000
    current = T+offset//step*step
    rows = []
    for i in range(-40, 1):
        time = current+i*step
        p = price if i == 0 else 99
        exact = {k:str(v) for k,v in dict(open=99, high=max(102,p), low=min(98,p), close=p, volume=10,
                                        quote_volume=1000).items()}
        rows.append(dict(time=time, close_time=(time+step)*1000-1, closed=i<0,
                         open=99, high=max(102,p), low=min(98,p), close=p, volume=10,
                         quote_volume=1000, exact=dict(state='VERIFIED', **exact)))
    return dict(identity=dict(source=SOURCE, environment='live_public', product='USD-M',
                              price_type='LAST_PRICE', symbol='BTCUSDT', interval=interval),
                rows=rows, transport_state='LIVE', timing=dict(state='FRESH'), quality=dict(state='OK'),
                stream_epoch=epoch, event_time=(T+offset)*1000, data_revision=offset+1)


class IntrabarTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = Path(self.folder.name)/'app.db'
        migrate(self.db)
        self.service = PriceAlerts(self.db, 'test')

    def tearDown(self):
        self.folder.cleanup()

    def start(self, frequency='bar', value=None):
        self.alert = self.service.save(value or draft(frequency))
        self.run_sample(context())

    def run_sample(self, c, boot='b', higher=None):
        sources = {c['identity']['interval']:c, **(higher or {})}
        self.service.process(self.alert['id'], {'_source_contexts':sources}, boot)

    def test_strict_schema_and_legacy_close_frequency_unchanged(self):
        self.assertEqual(definition(draft())['frequency'], 'bar')
        for patch in ({'frequency':'every_tick'}, {'evaluation':'bar_close'}, {'extra':True}):
            with self.assertRaises(AlertError): definition(draft()|patch)
        bad=draft();bad['schema']='technical-alert/3';bad.pop('evaluation')
        with self.assertRaises(AlertError):definition(bad)

    def test_once_triggers_while_forming_and_remains_committed_when_condition_repaints(self):
        self.start('once');self.assertEqual(self.service.events(), [])
        self.run_sample(context(2));self.assertEqual(self.service.list()[0]['state'], 'TRIGGERED')
        self.run_sample(context(3, 90));events=self.service.events();self.assertEqual(len(events),1)
        self.assertFalse(events[0]['confirmed']);self.assertEqual(events[0]['evaluation'],'intrabar')
        self.assertEqual(events[0]['close'],'101');self.assertFalse(events[0]['order_authority'])

    def test_per_bar_dedup_repeated_data_flip_reconnect_and_next_bar(self):
        self.start();self.run_sample(context(2));self.run_sample(context(2));self.run_sample(context(3,90));self.run_sample(context(4,105))
        self.assertEqual(len(self.service.events()),1)
        self.run_sample(context(5),boot='new');self.run_sample(context(6),boot='new')
        self.run_sample(context(7,epoch='new'),boot='new');self.run_sample(context(8,epoch='new'),boot='new')
        self.assertEqual(len(self.service.events()),1)
        for offset in range(9,303):self.run_sample(context(offset,epoch='new'),boot='new')
        self.assertEqual(len(self.service.events()),2)

    def test_minute_is_rolling_sixty_seconds_not_calendar_minute_and_survives_boot(self):
        self.start('minute')
        for offset in range(2,59):self.run_sample(context(offset,90))
        self.run_sample(context(59));self.assertEqual(len(self.service.events()),1)
        for offset in range(60,119):self.run_sample(context(offset),boot='restarted' if offset>=80 else 'b')
        self.assertEqual(len(self.service.events()),1)
        self.run_sample(context(119),boot='restarted');self.assertEqual(len(self.service.events()),2)

    def test_new_sample_required_and_old_revision_cannot_trigger(self):
        self.start('minute');self.run_sample(context(2));self.run_sample(context(2));self.assertEqual(len(self.service.events()),1)
        stale=context(3);stale['data_revision']=1;self.run_sample(stale);self.assertEqual(len(self.service.events()),1)

    def test_invalid_or_disconnected_data_reseeds_without_replay(self):
        for patch in ({'transport_state':'STALE'},{'timing':{'state':'STALE'}},{'quality':{'state':'GAP'}},{'event_time':None}):
            self.start();self.run_sample(context(2)|patch);self.assertEqual(self.service.list()[0]['readiness'],'WAITING_DATA')
            self.run_sample(context(3));self.assertEqual(self.service.events(),[])
            self.service.action(self.alert['id'],1,'delete')
        self.start();bad=context(2);bad['rows'][-1]['exact']['close']='NaN';self.run_sample(bad);self.assertEqual(self.service.list()[0]['readiness'],'WAITING_DATA')

    def test_missing_sample_window_is_baselined(self):
        self.start();self.run_sample(context(60));self.assertEqual(self.service.events(),[])
        self.run_sample(context(61));self.assertEqual(len(self.service.events()),1)

    def test_current_vs_closed_bar_crossing_uses_candle_reference(self):
        d=draft();d['conditions'][0]['operator']='cross_up';self.start(value=d)
        self.run_sample(context(2,99));self.assertEqual(self.service.events(),[])
        self.run_sample(context(3,100));self.assertEqual(len(self.service.events()),1)
        self.run_sample(context(4,99));self.run_sample(context(5,100));self.assertEqual(len(self.service.events()),1)

    def test_indicator_recomputed_with_forming_value_and_warmup_visible(self):
        d=draft();config=copy.deepcopy(defaults_v4()[3]);config['period']=2
        d['conditions'][0]['left']=dict(type='indicator',config=config,output='value')
        self.start(value=d);self.run_sample(context(2,110));self.assertEqual(len(self.service.events()),1)
        self.service.action(self.alert['id'],1,'delete');config['period']=200;self.start(value=d)
        self.assertEqual(self.service.list()[0]['readiness'],'WAITING_CALCULATION')
        self.run_sample(context(2,110));self.assertEqual(self.service.list()[0]['readiness'],'WAITING_CALCULATION')

    def test_mtf_excludes_forming_higher_bar_and_waits_for_late_close(self):
        d=draft();d['conditions'].append({**copy.deepcopy(d['conditions'][0]),'interval':'15m'})
        self.alert=self.service.save(d)
        def higher(offset):
            c=context(offset,1000,'15m');c['rows'][-2]['close']=101;c['rows'][-2]['exact']['close']='101';return {'15m':c}
        self.run_sample(context(1),higher=higher(1));self.run_sample(context(2),higher=higher(2))
        e=self.service.events()[0];self.assertEqual(e['source_closes']['15m'],T-900)
        bad=higher(3);bad['15m']['timing']['state']='STALE';self.run_sample(context(3),higher=bad)
        self.assertEqual(self.service.list()[0]['readiness'],'WAITING_DATA')

    def test_real_api_persists_intrabar_and_rejects_old_revision(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        class Market:
            def selection(self,*args):pass
        class Hub:
            def acquire(self,*args):return object()
            def release(self,*args):pass
            def binding_context(self,*args):return None
            def close(self):pass
        settings=WebSettings(self.db,Path(self.folder.name)/'execution.db',market_database=Path(self.folder.name)/'market.db')
        with TestClient(create_app(settings,market=Market(),hub=Hub()),base_url='http://127.0.0.1') as client:
            r=client.post('/api/alerts',json={'definition':draft('minute')});self.assertEqual(r.status_code,201);a=r.json()
            self.assertEqual(client.get('/api/alerts').json()['alerts'][0]['definition']['evaluation'],'intrabar')
            self.assertEqual(client.put('/api/alerts/'+a['id'],json={'definition':draft(),'revision':1}).status_code,200)
            self.assertEqual(client.put('/api/alerts/'+a['id'],json={'definition':draft(),'revision':1}).status_code,409)
        self.assertFalse(settings.execution_database.exists())

    def test_mtf_boundary_lag_waits_without_consuming_the_base_sample(self):
        d=draft();d['conditions'].append({**copy.deepcopy(d['conditions'][0]),'interval':'15m'})
        self.alert=self.service.save(d)
        def higher(offset):
            c=context(offset,1000,'15m')
            c['rows'][-2]['exact']['close']='101'
            return {'15m':c}
        self.run_sample(context(899),higher=higher(899))
        self.run_sample(context(900),higher=higher(899))
        self.assertEqual(self.service.list()[0]['readiness'],'WAITING_ALIGNMENT')
        self.assertEqual(self.service.events(),[])
        self.run_sample(context(900),higher=higher(900))
        self.assertEqual(len(self.service.events()),1)
        self.assertEqual(self.service.events()[0]['source_closes']['15m'],T)
        self.run_sample(context(900),higher=higher(900));self.assertEqual(len(self.service.events()),1)

    def test_background_worker_observes_live_bar_without_browser_or_close_event(self):
        import threading,time
        self.alert=self.service.save(draft('once'))
        class Hub:
            def __init__(self):self.c=context();self.references=0
            def acquire(self,*args):self.references+=1;return object()
            def release(self,*args):self.references-=1
            def binding_context(self,*args):return copy.deepcopy(self.c)
        hub=Hub();worker=PriceAlertWorker(self.service,hub);worker.start()
        try:
            deadline=time.monotonic()+3
            while self.service.list()[0]['readiness']!='READY' and time.monotonic()<deadline:time.sleep(.02)
            self.assertEqual(self.service.list()[0]['readiness'],'READY')
            hub.c=context(2)
            deadline=time.monotonic()+3
            while not self.service.events() and time.monotonic()<deadline:time.sleep(.02)
            self.assertEqual(len(self.service.events()),1)
            self.assertFalse(self.service.events()[0]['confirmed'])
        finally:worker.close()
        self.assertEqual(hub.references,0)
        self.assertFalse(worker.thread.is_alive())
