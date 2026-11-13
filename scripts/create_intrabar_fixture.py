"""Produce a real forming-bar alert event without touching a personal database."""
import copy
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
        service=PriceAlerts(database,'intrabar-fixture')
        definition=dict(schema='technical-alert/4',evaluation='intrabar',name='Canli fiyat alarmi',
                        symbol='BTCUSDT',interval='1m',frequency='bar',expires_at=None,
                        message='Olusan mum gozlemi',match='all',conditions=[dict(interval='1m',
                        left=dict(type='market',field='close'),operator='above',
                        right=dict(type='value',value='100'),upper=None,bars=1)])
        alert=service.save(definition)
        first=context([98,99,101])
        first['rows'][-1]['closed']=False
        first.update(data_revision=1,event_time=first['rows'][-1]['time']*1000+1000)
        service.process(alert['id'],{'_source_contexts':{'1m':first}},'fixture')
        second=copy.deepcopy(first)
        second['data_revision']=2
        second['event_time']+=1000
        second['rows'][-1]['exact']['close']='102'
        service.process(alert['id'],{'_source_contexts':{'1m':second}},'fixture')
        events=service.events()
        assert len(events)==1 and not events[0]['confirmed']
        target=Path(__file__).resolve().parents[1]/'reports/alert-frequencies-ui-20261113/engine-event.json'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(events[0]),encoding='utf-8')


if __name__=='__main__':
    main()
