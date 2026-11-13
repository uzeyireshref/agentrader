"""Closed native higher-timeframe context, with a conservative no-lookahead cutoff."""
import math
from .chart_market import InvalidMarket, validate_selection
from .market_data import INTERVALS, SOURCE, bucket


def higher_context(market, symbol, base_interval, interval, reference_time):
    validate_selection(symbol, base_interval)
    validate_selection(symbol, interval)
    if (INTERVALS[interval] <= INTERVALS[base_interval] or type(reference_time) is not int
            or not 0 < reference_time <= 32503680000000):
        raise InvalidMarket('Üst zaman dilimi daha büyük, referans zamanı geçerli UTC milisaniye olmalı.')
    history = market.history(symbol, interval, limit=4, end_time=reference_time, force=True)
    result = dict(schema='chart-higher-context/1', symbol=symbol, base_interval=base_interval,
                  interval=interval, requested_reference_time=reference_time,
                  effective_reference_time=None, source=SOURCE, environment='live_public', product='USD-M',
                  price_type='LAST_PRICE', provenance='BINANCE_NATIVE_KLINE', resampled=False,
                  state='BLOCKED', reason=None, candle=None, server_time=history.get('server_time'),
                  precision=history.get('precision'), history_quality=history.get('quality'), clock_state=history.get('clock_sample', {}).get('state'), clock_uncertainty_ms=history.get('clock_sample', {}).get('uncertainty_ms'),
                  live_eligible=False, order_authority=False)
    clock, server = history.get('clock_sample', {}), history.get('server_time')
    uncertainty = clock.get('uncertainty_ms')
    if (clock.get('schema') != 'chart-clock-sample/1' or clock.get('state') != 'MEASURED'
            or type(server) is not int or server <= 0 or type(uncertainty) not in (int, float)
            or not math.isfinite(uncertainty) or not 0 <= uncertainty <= 1000):
        result['reason'] = 'CLOCK_UNTRUSTED'
        return result
    cutoff = min(reference_time, math.floor(server-uncertainty))
    result['effective_reference_time'] = cutoff
    if (history.get('symbol') != symbol or history.get('interval') != interval
            or history.get('source') != SOURCE or history.get('product') != 'USD-M'
            or history.get('price_type') != 'LAST_PRICE' or history.get('environment') != 'live_public'):
        result['reason'] = 'SOURCE_CONTEXT_MISMATCH'
        return result
    if history.get('precision', {}).get('state') != 'VERIFIED':
        result['reason'] = 'PRICE_PRECISION_UNPROVEN'
        return result
    quality = history.get('quality', {})
    if quality.get('missing_bars', 0) or quality.get('state') not in ('OK', 'STALE', 'EMPTY'):
        result['reason'] = 'GRID_GAP'
        return result
    expected = bucket(cutoff, interval)-INTERVALS[interval]
    candidates = [row for row in history.get('candles', [])
                  if row.get('closed') is True and type(row.get('time')) is int
                  and row.get('close_time') == row['time']*1000+INTERVALS[interval]-1
                  and row['close_time'] < cutoff and bucket(row['time']*1000, interval) == row['time']*1000]
    candidate = max(candidates, key=lambda row: row['time'], default=None)
    if candidate is None or candidate['time']*1000 != expected:
        result.update(state='UNAVAILABLE', reason='CLOSED_HIGHER_CANDLE_UNAVAILABLE')
        return result
    if candidate.get('exact', {}).get('state') != 'VERIFIED':
        result['reason'] = 'PRICE_PRECISION_UNPROVEN'
        return result
    result.update(state='READY', reason=None, candle=candidate)
    return result
