"""Read-only grid preflight; no execution path until full protective integration is verified."""
import argparse
import json
from pathlib import Path

from .config import Config
from .exchange import DemoExchange, ExchangeError
from .grid import preview_grid, verify_leverage
from .risk import RiskLimits


def main(argv=None):
    parser = argparse.ArgumentParser(prog='agentrader grid', description=__doc__)
    parser.add_argument('command', choices=['preview'])
    parser.add_argument('file')
    parser.add_argument('--risk-profile', default='risk-demo.json')
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    try:
        spec = json.loads(Path(args.file).read_text(encoding='utf-8-sig'))
        x = DemoExchange(Config.load())
        x.sync_time()
        symbol = next(s for s in x.get('/fapi/v1/exchangeInfo')['symbols'] if s['symbol'] == spec['symbol'])
        report = preview_grid(spec, symbol, RiskLimits.load(args.risk_profile))
        report['leverage_check'] = verify_leverage(x, spec['symbol'], spec['leverage'])
        report['mark'] = x.get('/fapi/v1/premiumIndex', {'symbol': spec['symbol']})
        report['execution_enabled'] = False
        report['remaining_work'] = ['Grid entries need scoped authorization, portfolio risk, stop/cleanup and live ownership reconciliation.']
        if args.output:
            Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 1 if report['state'] == 'BLOCKED' else 0
    except (ValueError, OSError, ExchangeError, StopIteration, KeyError) as exc:
        print(json.dumps({'state': 'BLOCKED', 'error': str(exc), 'executed': False}, ensure_ascii=True))
        return 1
