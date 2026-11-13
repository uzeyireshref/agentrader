import copy
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from agentrader.alert_schedule import validate_schedule,notification_gate
from agentrader.price_alerts import PriceAlerts,definition,AlertError
from agentrader.migrations import migrate
from test_price_alerts import definition as legacy,context as closed_context
from test_alert_intrabar import draft as live,context as live_context


def schedule(days=None,start='09:00',end='18:00',zone='UTC'):
    return dict(schema='alert-notification-schedule/1',mode='custom',timezone=zone,
                windows=[dict(days=days if days is not None else [0,1,2,3,4],start=start,end=end)])


def stamp(value):return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
def allowed(s,time):return notification_gate({'notification_schedule':s},stamp(time))['allowed']


class ScheduleMathTests(unittest.TestCase):
    def test_legacy_always_and_strict_validation(self):
        self.assertIsNone(notification_gate({},0))
        self.assertTrue(allowed(dict(schema='alert-notification-schedule/1',mode='always',timezone='Asia/Baku',windows=[]),'2026-11-15T12:00Z'))
        for value in (None,{},schedule(zone='UTC+4'),schedule(start='24:00'),schedule(end='24:01'),schedule(start='9:00'),schedule(end='09:00'),schedule(days=[]),schedule(days=[True]),schedule(days=[7]),schedule(days=[0,0]),schedule()|{'extra':True}):
            with self.assertRaises(ValueError):validate_schedule(value)
            self.assertFalse(notification_gate({'notification_schedule':value},0)['allowed'])

    def test_local_zone_boundaries_half_hour_and_full_day(self):
        s=schedule(zone='Asia/Baku')
        self.assertFalse(allowed(s,'2026-11-16T04:59:59Z'))
        self.assertTrue(allowed(s,'2026-11-16T05:00Z'))
        self.assertTrue(allowed(s,'2026-11-16T13:59:59Z'))
        self.assertFalse(allowed(s,'2026-11-16T14:00Z'))
        self.assertTrue(allowed(schedule(days=[0],start='00:00',end='24:00'),'2026-11-16T23:59:59Z'))
        self.assertFalse(allowed(schedule(days=[0],start='00:00',end='24:00'),'2026-11-17T00:00Z'))
        self.assertTrue(allowed(schedule(zone='Asia/Kathmandu'),'2026-11-16T03:15Z'))

    def test_overnight_belongs_to_start_day_and_wraps_week(self):
        s=schedule(days=[4],start='22:00',end='04:00')
        for time,want in [('2026-11-13T21:59Z',False),('2026-11-13T22:00Z',True),('2026-11-14T03:59:59Z',True),('2026-11-14T04:00Z',False),('2026-11-15T03:00Z',False)]:self.assertEqual(allowed(s,time),want,time)
        self.assertTrue(allowed(schedule(days=[6],start='22:00',end='04:00'),'2026-11-16T03:00Z'))

    def test_dst_fall_repeated_hour_and_spring_nonexistent_hour(self):
        fall=schedule(days=[6],start='01:00',end='02:00',zone='America/New_York')
        self.assertTrue(allowed(fall,'2026-11-01T05:30Z'));self.assertTrue(allowed(fall,'2026-11-01T06:30Z'))
        self.assertFalse(allowed(fall,'2026-11-01T07:00Z'))
        spring=schedule(days=[6],start='02:00',end='03:00',zone='America/New_York')
        self.assertFalse(allowed(spring,'2026-03-08T06:59:59Z'));self.assertFalse(allowed(spring,'2026-03-08T07:00Z'))

    def test_multiple_windows_union_and_definition_snapshot_no_mutation(self):
        s=schedule();s['windows'].append(dict(days=[0],start='20:00',end='22:00'))
        self.assertTrue(allowed(s,'2026-11-16T21:00Z'));self.assertFalse(allowed(s,'2026-11-16T19:00Z'))
        d=legacy();d['notification_schedule']=s;before=copy.deepcopy(d);saved=definition(d);s['windows'][0]['start']='12:00'
        self.assertEqual(saved,before);self.assertNotEqual(d,saved)
        with self.assertRaises(AlertError):definition(legacy()|{'notification_schedule':None})


class ScheduleEngineTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.db=Path(self.folder.name)/'a.db';migrate(self.db)
        self.now=stamp('2026-11-16T08:00Z');self.service=PriceAlerts(self.db,'owner',lambda:self.now)
    def tearDown(self):self.folder.cleanup()

    def test_close_once_keeps_monitoring_when_muted_then_consumes_in_window(self):
        d=legacy();d.update(operator='above',frequency='once',notification_schedule=schedule())
        a=self.service.save(d)
        def run(n):self.service.process(a['id'],closed_context(n,'99','101'),'boot')
        run(0);run(1);self.assertEqual(self.service.list()[0]['state'],'ACTIVE')
        muted=self.service.events()[0];self.assertFalse(muted['notification_gate']['allowed'])
        self.now=stamp('2026-11-16T09:00Z');run(2)
        self.assertEqual(self.service.list()[0]['state'],'TRIGGERED');self.assertEqual(len(self.service.events()),2)
        self.assertTrue(self.service.events()[0]['notification_gate']['allowed'])
        self.assertFalse(self.service.events()[1]['notification_gate']['allowed'])
        self.assertEqual(PriceAlerts(self.db,'other').events(),[])

    def test_live_once_muted_log_dedup_then_in_window_same_candle(self):
        d=live('once');d['notification_schedule']=schedule();a=self.service.save(d)
        def run(offset):self.service.process(a['id'],{'_source_contexts':{'5m':live_context(offset)}},'boot')
        run(1);run(2);run(3);run(4)
        self.assertEqual(self.service.list()[0]['state'],'ACTIVE');self.assertEqual(len(self.service.events()),1)
        self.now=stamp('2026-11-16T09:00Z');run(5);run(6)
        self.assertEqual(self.service.list()[0]['state'],'TRIGGERED');self.assertEqual(len(self.service.events()),2)
        self.assertEqual(self.service.events()[0]['notification_gate']['local_time'],'2026-11-16T09:00:00+00:00')

    def test_muted_bar_frequency_still_logs_and_never_stops_monitoring(self):
        d=legacy();d.update(operator='above',notification_schedule=schedule());a=self.service.save(d)
        for n in range(4):self.service.process(a['id'],closed_context(n,'99','101'),'boot')
        self.assertEqual(len(self.service.events()),3);self.assertTrue(all(not e['notification_gate']['allowed'] for e in self.service.events()))
        self.assertEqual(self.service.list()[0]['state'],'ACTIVE')

    def test_real_api_schedule_roundtrip_edit_conflict_and_rejection(self):
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
        d=live('minute');d['notification_schedule']=schedule(days=[4],start='22:00',end='04:00',zone='Asia/Baku')
        with TestClient(create_app(settings,market=Market(),hub=Hub()),base_url='http://127.0.0.1') as client:
            response=client.post('/api/alerts',json={'definition':d});self.assertEqual(response.status_code,201);a=response.json()
            self.assertEqual(client.get('/api/alerts').json()['alerts'][0]['definition'],d)
            self.assertEqual(client.put('/api/alerts/'+a['id'],json={'definition':d,'revision':1}).status_code,200)
            self.assertEqual(client.put('/api/alerts/'+a['id'],json={'definition':d,'revision':1}).status_code,409)
            d['notification_schedule']['timezone']='Bad/Timezone'
            self.assertEqual(client.post('/api/alerts',json={'definition':d}).status_code,422)
        self.assertFalse(settings.execution_database.exists())
