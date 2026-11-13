"""Generate a browser fixture through the real alert engine, in a temporary DB."""
import json
from pathlib import Path
import tempfile
from agentrader.price_alerts import PriceAlerts
from agentrader.migrations import migrate
from agentrader.market_data import SOURCE


def context(prices):
    start = 1800057600
    rows = [dict(time=start+i*60, close_time=(start+(i+1)*60)*1000-1,
                 closed=True, exact=dict(state='VERIFIED', close=str(price)))
            for i, price in enumerate(prices)]
    return dict(identity=dict(source=SOURCE, environment='live_public', product='USD-M',
                              price_type='LAST_PRICE', symbol='BTCUSDT', interval='1m'),
                transport_state='LIVE', timing=dict(state='FRESH'), quality=dict(state='OK'),
                stream_epoch='fixture', rows=rows)


def main():
    with tempfile.TemporaryDirectory() as folder:
        database = Path(folder)/'fixture.db'
        migrate(database)
        service = PriceAlerts(database, 'notification-fixture')
        alert = service.save(dict(name='Fiyat alarmi', symbol='BTCUSDT', interval='1m',
                                 operator='cross_up', price='100', frequency='bar_close',
                                 expires_at=None, message='Kapanis esigi gecildi.'))
        service.process(alert['id'], context([98, 99]), 'fixture')
        service.process(alert['id'], context([98, 99, 101]), 'fixture')
        assert len(service.events()) == 1
        target = Path(__file__).resolve().parents[1]/'reports/alert-notifications-20261113/engine-event.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(service.events()[0]), encoding='utf-8')


if __name__ == '__main__':
    main()
