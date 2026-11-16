"""Measure the order validator against captured public Demo symbol filters."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agentrader.bot.order_rules import validate_order

DATA = ROOT / 'docs/research/crypto-bot-20261115'


def fixtures(symbol, mark):
    filters = {item['filterType']: item for item in symbol['filters']}
    tick = Decimal(filters['PRICE_FILTER']['tickSize'])
    lot = filters['LOT_SIZE']
    market_lot = filters.get('MARKET_LOT_SIZE', lot)
    step = max(Decimal(lot['stepSize']), Decimal(market_lot['stepSize']))
    price = (mark / tick).to_integral_value(rounding=ROUND_FLOOR) * tick
    minimum = max(Decimal(lot['minQty']), Decimal(market_lot['minQty']),
                  Decimal(filters['MIN_NOTIONAL']['notional']) / price)
    quantity = (minimum / step).to_integral_value(rounding=ROUND_CEILING) * step
    base = dict(symbol=symbol['symbol'], side='BUY', positionSide='BOTH', type='LIMIT',
                quantity=str(quantity), price=str(price), timeInForce='GTC')
    market = {key: value for key, value in base.items() if key not in ('price', 'timeInForce')}
    market['type'] = 'MARKET'
    reduce = market | dict(side='SELL', reduceOnly='true')
    stop = reduce | dict(type='STOP_MARKET', triggerPrice=str(price), workingType='MARK_PRICE')
    trailing = reduce | dict(type='TRAILING_STOP_MARKET', callbackRate='1')
    return [
        ('limit_long', base, 'one-way', 'OPEN', True),
        ('limit_short', base | dict(side='SELL'), 'one-way', 'OPEN', True),
        ('market_long', market, 'one-way', 'OPEN', True),
        ('hedge_long', market | dict(positionSide='LONG'), 'hedge', 'OPEN', True),
        ('hedge_short', market | dict(side='SELL', positionSide='SHORT'), 'hedge', 'OPEN', True),
        ('reduce_market', reduce, 'one-way', 'REDUCE', True),
        ('stop_market', stop, 'one-way', 'REDUCE', True),
        ('trailing', trailing, 'one-way', 'REDUCE', True),
        ('bad_tick', base | dict(price=str(price + tick / 2)), 'one-way', 'OPEN', False),
        ('bad_lot', base | dict(quantity=str(Decimal(lot['stepSize']) / 2)), 'one-way', 'OPEN', False),
        ('zero_quantity', base | dict(quantity='0'), 'one-way', 'OPEN', False),
        ('nan_price', base | dict(price='NaN'), 'one-way', 'OPEN', False),
        ('hedge_reduce_only', reduce | dict(positionSide='LONG'), 'hedge', 'REDUCE', False),
        ('market_limit_fields', base | dict(type='MARKET'), 'one-way', 'OPEN', False),
        ('expired_gtd', base | dict(timeInForce='GTD', goodTillDate=1000001), 'one-way', 'OPEN', False),
        ('invalid_callback', trailing | dict(callbackRate='20.1'), 'one-way', 'REDUCE', False),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'reports/crypto-bot-research-20261115/market-contract-audit.json')
    args = parser.parse_args()
    universe_bytes = (DATA / 'market-universe.json').read_bytes()
    prices_bytes = (DATA / 'mark-prices.json').read_bytes()
    universe = json.loads(universe_bytes)
    prices = {item['symbol']: Decimal(item['mark_price']) for item in json.loads(prices_bytes)['prices']}
    rows = []
    for item in universe['symbols']:
        symbol = dict(symbol=item['symbol'], status=item['status'], filters=item['filters'],
                      orderTypes=item['order_types'])
        mark = prices.get(item['symbol'])
        if mark is None or not mark.is_finite() or mark <= 0:
            rows.append(dict(symbol=item['symbol'], case='fixture', status='FIXTURE_UNAVAILABLE'))
            continue
        price_filter = next(rule for rule in symbol['filters'] if rule['filterType'] == 'PRICE_FILTER')
        if not Decimal(price_filter['minPrice']) <= mark <= Decimal(price_filter['maxPrice']):
            rows.append(dict(symbol=item['symbol'], case='fixture', status='INPUT_DATA_BLOCKED',
                             planned_case_count=16, mark_price=str(mark),
                             detail='Captured mark is outside the captured PRICE_FILTER range.',
                             exchange_acceptance='NOT_RUN'))
            continue
        try:
            cases = fixtures(symbol, mark)
        except (ValueError, ArithmeticError, KeyError) as error:
            rows.append(dict(symbol=item['symbol'], case='fixture', status='FIXTURE_ERROR', detail=str(error)))
            continue
        for name, intent, mode, operation, expected in cases:
            row = dict(symbol=item['symbol'], case=name, expected_acceptance=expected,
                       scope='OFFLINE_VALIDATOR', exchange_acceptance='NOT_RUN')
            try:
                proposal = validate_order(intent, symbol, mode, operation, str(mark), 1000000)
                actual = True
                row['execution_authorized'] = proposal['execution_authorized']
                row['status'] = 'PASS' if expected and proposal['execution_authorized'] is False else 'FAIL'
            except ValueError as error:
                actual = False
                row['status'] = 'PASS' if not expected else 'FAIL'
                row['detail'] = str(error)
            row['actual_acceptance'] = actual
            rows.append(row)
    report = dict(schema_version=1, observed_at_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Captured Demo filters and marks with the existing pure order validator',
                  symbol_count=universe['count'], record_count=len(rows),
                  case_count=sum('actual_acceptance' in row for row in rows),
                  counts=dict(Counter(row['status'] for row in rows)),
                  planned_case_count=universe['count'] * 16,
                  executed_case_count=sum('actual_acceptance' in row for row in rows),
                  blocked_case_count=sum(row.get('planned_case_count', 0) for row in rows),
                  cases_per_symbol=16, exchange_mutations=0,
                  universe_sha256=hashlib.sha256(universe_bytes).hexdigest(),
                  prices_sha256=hashlib.sha256(prices_bytes).hexdigest(),
                  validator_sha256=hashlib.sha256((ROOT / 'agentrader/bot/order_rules.py').read_bytes()).hexdigest(),
                  results=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('symbol_count', 'planned_case_count', 'executed_case_count', 'blocked_case_count', 'counts')}, ensure_ascii=False))
    return 0 if all(row['status'] == 'PASS' for row in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
