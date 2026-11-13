import copy,tempfile,unittest
from pathlib import Path
from agentrader.price_alerts import PriceAlerts,definition,AlertError
from agentrader.migrations import migrate
from test_price_alerts import definition as legacy,context
from test_alert_intrabar import draft

def policy(**kwargs):return dict(schema='alert-notification-channels/1',mode='custom',inApp=False,sound=False,desktop=False)|kwargs

class ChannelTests(unittest.TestCase):
    def test_strict_policy_and_existing_schemas(self):
        for base in (legacy(),draft()):
            for p in (policy(),policy(sound=True),dict(schema='alert-notification-channels/1',mode='inherit')):
                value=base|{'notification_channels':p};before=copy.deepcopy(value)
                self.assertEqual(definition(value)['notification_channels'],p);self.assertEqual(value,before)
        for p in (None,{},policy(sound=1),policy(desktop='true'),policy(extra=True),dict(schema='alert-notification-channels/1',mode='inherit',sound=True)):
            with self.assertRaises(AlertError):definition(legacy()|{'notification_channels':p})

    def test_history_only_once_is_consumed_and_event_policy_snapshot_survives_edit(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'app.db';migrate(db);s=PriceAlerts(db,'owner');d=legacy();d.update(frequency='once',notification_channels=policy())
            a=s.save(d);s.process(a['id'],context(),'b');s.process(a['id'],context(1,'99','101'),'b')
            self.assertEqual(s.list()[0]['state'],'TRIGGERED');e=s.events()[0];self.assertEqual(e['definition']['notification_channels'],policy())
            d['notification_channels']=policy(desktop=True);s.save(d,a['id'],1)
            self.assertEqual(s.events()[0]['definition']['notification_channels'],policy());self.assertEqual(s.list()[0]['definition']['notification_channels'],policy(desktop=True))

    def test_api_roundtrip_revision_conflict_and_bad_policy_rejection(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        class Market:
            def selection(self,*a):pass
        class Hub:
            def acquire(self,*a):return object()
            def release(self,*a):pass
            def binding_context(self,*a):return None
            def close(self):pass
        with tempfile.TemporaryDirectory() as folder:
            settings=WebSettings(Path(folder)/'app.db',Path(folder)/'execution.db',market_database=Path(folder)/'market.db')
            with TestClient(create_app(settings,market=Market(),hub=Hub()),base_url='http://127.0.0.1') as client:
                d=draft()|{'notification_channels':policy(sound=True)};r=client.post('/api/alerts',json={'definition':d});self.assertEqual(r.status_code,201);a=r.json()
                self.assertEqual(client.get('/api/alerts').json()['alerts'][0]['definition']['notification_channels'],policy(sound=True))
                self.assertEqual(client.put('/api/alerts/'+a['id'],json={'definition':d,'revision':1}).status_code,200)
                self.assertEqual(client.put('/api/alerts/'+a['id'],json={'definition':d,'revision':1}).status_code,409)
                d['notification_channels']=policy(inApp='false');self.assertEqual(client.post('/api/alerts',json={'definition':d}).status_code,422)
            self.assertFalse(settings.execution_database.exists())
