"""Produce independent channel events through the real engine in a temporary DB."""
import json,tempfile
from pathlib import Path
from agentrader.price_alerts import PriceAlerts
from agentrader.migrations import migrate
from scripts.create_notification_fixture import context

def main():
    with tempfile.TemporaryDirectory() as folder:
        db=Path(folder)/'app.db';migrate(db);s=PriceAlerts(db,'channel-fixture')
        for name,key in [('History',None),('Card','inApp'),('Sound','sound'),('Desktop','desktop')]:
            p=dict(schema='alert-notification-channels/1',mode='custom',inApp=False,sound=False,desktop=False)
            if key:p[key]=True
            d=dict(name=name,symbol='BTCUSDT',interval='1m',operator='cross_up',price='100',frequency='once',expires_at=None,message=name+' event',notification_channels=p)
            a=s.save(d);s.process(a['id'],context([98,99]),'fixture');s.process(a['id'],context([98,99,101]),'fixture')
        assert len(s.events())==4 and all(a['state']=='TRIGGERED' for a in s.list())
        target=Path(__file__).resolve().parents[1]/'reports/alert-channels-ui-20261113/engine-events.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(s.events()),encoding='utf-8')

if __name__=='__main__':main()
