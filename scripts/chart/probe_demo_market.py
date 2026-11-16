"""Read-only demo REST/WS evidence. No credentials, account or order access."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json, time, sys
from pathlib import Path
from urllib.request import Request, build_opener
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agentrader.shared.exchange import NoRedirect
import websocket


def run():
    report = dict(environment='demo_public', account_requests=0, order_requests=0, checks=[])
    opener = build_opener(NoRedirect())
    for path in ('/fapi/v1/time', '/fapi/v1/exchangeInfo', '/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=3', '/fapi/v1/premiumIndex?symbol=BTCUSDT'):
        try:
            with opener.open(Request('https://demo-fapi.binance.com'+path), timeout=15) as response:
                data = json.load(response)
            good = isinstance(data, (dict, list)) and bool(data)
            report['checks'].append(dict(path=path, passed=good))
        except Exception as exc:
            report['checks'].append(dict(path=path, passed=False, error=type(exc).__name__))
    url = 'wss://demo-fstream.binance.com/market/ws/btcusdt@kline_1m'
    connection = None
    try:
        connection = websocket.create_connection(url, timeout=15, redirect_limit=0)
        data = json.loads(connection.recv())
        good = data.get('e') == 'kline' and data.get('s') == 'BTCUSDT' and data.get('k', {}).get('i') == '1m'
        report['checks'].append(dict(url=url, passed=good, event=data.get('e')))
    except Exception as exc:
        report['checks'].append(dict(url=url, passed=False, error=type(exc).__name__))
    finally:
        if connection: connection.close()
    report['passed'] = all(c['passed'] for c in report['checks'])
    report['observed_at_ms'] = int(time.time()*1000)
    return report

if __name__ == '__main__':
    report = run()
    target = Path(__file__).resolve().parents[2]/'reports/demo-market-probe-20261113.json'
    target.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))
    sys.exit(0 if report['passed'] else 1)
