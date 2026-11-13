"""Explicit public-data-only live chart probe. No execution/account imports."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agentrader.chart_market import ChartMarket
from agentrader.market_feed import MarketFeedHub


def check_live_chart():
    with tempfile.TemporaryDirectory(prefix='agentrader-chart-check-') as folder:
        market = ChartMarket(Path(folder) / 'chart.db')
        hub = MarketFeedHub(market)
        feed = None
        try:
            catalog = market.catalog()
            feed = hub.acquire('BTCUSDT', '15m')
            deadline = time.monotonic() + 45
            live = None
            while time.monotonic() < deadline:
                packet = feed.state.packet(-1)
                if packet['status'] == 'LIVE' and packet.get('candles'):
                    live = packet
                    break
                time.sleep(.1)
            if live is None:
                raise RuntimeError('Public stream did not become live')
            older = market.history('BTCUSDT', '15m', limit=2, end_time=live['candles'][0]['time'] * 1000 - 1)
            assert older['candles'][-1]['time'] < live['candles'][0]['time']
            return {'result': 'PASSED', 'source': live['source'], 'supported_markets': len(catalog['markets']),
                    'candles': len(live['candles']), 'status': live['status'],
                    'history_pagination': True, 'account_requests': 0, 'orders_sent': 0}
        finally:
            if feed is not None:
                hub.release(feed)
            hub.close()


if __name__ == '__main__':
    result = check_live_chart()
    result['date'] = datetime.now(timezone(timedelta(hours=4))).date().isoformat()
    result['command'] = 'python scripts/check_chart_feed.py'
    destination = ROOT/('reports/chart-live-validation-'+result['date'].replace('-', '')+'.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
