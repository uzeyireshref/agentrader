"""Generate muted/allowed once-alert events in a temporary database."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from agentrader.migrations import migrate
from agentrader.price_alerts import PriceAlerts
from scripts.create_notification_fixture import context


def main():
    with tempfile.TemporaryDirectory() as folder:
        database=Path(folder)/'fixture.db'
        migrate(database)
        now=[datetime(2026,11,16,8,tzinfo=timezone.utc).timestamp()]
        service=PriceAlerts(database,'schedule-fixture',lambda:now[0])
        value=dict(name='Takvimli alarm',symbol='BTCUSDT',interval='1m',operator='above',price='100',
                   frequency='once',expires_at=None,message='Takvim test olayi',notification_schedule=dict(
                   schema='alert-notification-schedule/1',mode='custom',timezone='UTC',windows=[dict(
                   days=[0,1,2,3,4],start='09:00',end='18:00')]))
        alert=service.save(value)
        service.process(alert['id'],context([98,99]),'fixture')
        service.process(alert['id'],context([98,99,101]),'fixture')
        assert service.list()[0]['state']=='ACTIVE'
        now[0]=datetime(2026,11,16,9,tzinfo=timezone.utc).timestamp()
        service.process(alert['id'],context([98,99,101,102]),'fixture')
        assert service.list()[0]['state']=='TRIGGERED'
        events=service.events()
        assert len(events)==2 and events[0]['notification_gate']['allowed'] and not events[1]['notification_gate']['allowed']
        target=Path(__file__).resolve().parents[1]/'reports/alert-schedule-ui-20261113/engine-events.json'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(events),encoding='utf-8')


if __name__=='__main__':
    main()
