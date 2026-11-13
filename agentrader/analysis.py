"""Kapanmış mumlarda açıklanabilir temel analiz; hiçbir emir üretmez."""
from datetime import datetime, timezone
from decimal import Decimal
import math

from .market_data import INTERVALS, bucket, normalize


def ema(values, period):
    if len(values) < period:
        return None
    value = sum(values[:period]) / period
    alpha = 2 / (period + 1)
    for item in values[period:]:
        value += alpha * (item - value)
    return value


def rsi(values, period=14):
    if len(values) <= period:
        return None
    changes = [b - a for a, b in zip(values, values[1:])]
    gain = sum(max(c, 0) for c in changes[:period]) / period
    loss = sum(max(-c, 0) for c in changes[:period]) / period
    for change in changes[period:]:
        gain = (gain * (period - 1) + max(change, 0)) / period
        loss = (loss * (period - 1) + max(-change, 0)) / period
    if gain == loss == 0:
        return 50.0
    return 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)


def atr(rows, period=14):
    if len(rows) < period:
        return None
    ranges = []
    previous = None
    for row in rows:
        high, low, close = map(float, (row[2], row[3], row[4]))
        ranges.append(high - low if previous is None else max(high - low, abs(high - previous), abs(low - previous)))
        previous = close
    value = sum(ranges[:period]) / period
    for item in ranges[period:]:
        value = (value * (period - 1) + item) / period
    return value


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def timeframe_report(raw_rows, interval, as_of_ms, bars=300):
    rows, quality = normalize(raw_rows, interval)
    closed = [r for r in rows if r[6] < as_of_ms][-bars:]
    open_rows = [r for r in rows if r[0] <= as_of_ms <= r[6]]
    expected = bucket(as_of_ms, interval) - INTERVALS[interval]
    gaps = []
    for left, right in zip(closed, closed[1:]):
        missing = (right[0] - left[0]) // INTERVALS[interval] - 1
        if missing:
            gaps.append({'after_open_ms': left[0], 'missing_bars': missing})
    issues = []
    if not closed or closed[-1][0] != expected:
        issues.append('Beklenen son kapanmış mum eksik veya veri eski.')
    if gaps:
        issues.append('Kapanmış mum geçmişinde boşluk var.')
    if len(closed) < 51:
        issues.append('EMA50/RSI/ATR için yeterli kapanmış veri yok.')
    report = {'interval': interval, 'closed_count': len(closed), 'open_count': len(open_rows),
              'open_candles_excluded': True, 'expected_last_open_ms': expected,
              'latest_closed_at': iso(closed[-1][6]) if closed else None,
              'quality': quality | {'gaps': gaps, 'short_history': len(closed) < bars},
              'issues': issues, 'status': 'INVALID_DATA' if issues else 'OK', 'features': None}
    if issues:
        return report
    closes = [float(r[4]) for r in closed]
    e20, e50, value_rsi, value_atr = ema(closes, 20), ema(closes, 50), rsi(closes), atr(closed)
    quote = [float(r[7]) for r in closed]
    baseline = sum(quote[-21:-1]) / 20
    trend = 'UP' if closes[-1] > e20 > e50 else 'DOWN' if closes[-1] < e20 < e50 else 'MIXED'
    report['features'] = {'close': closes[-1], 'ema20': e20, 'ema50': e50,
                          'rsi14_wilder': value_rsi, 'atr14_wilder': value_atr,
                          'atr_pct': value_atr / closes[-1] * 100, 'trend': trend,
                          'quote_volume_usdt': quote[-1], 'quote_volume_previous20_mean': baseline,
                          'quote_volume_ratio': quote[-1] / baseline if baseline else None}
    if not all(math.isfinite(v) for v in report['features'].values() if isinstance(v, (int, float))):
        raise ValueError('Gösterge hesabı sonlu sonuç üretmedi.')
    report['reasons'] = [f"Kapanış {closes[-1]:.4f}; EMA20 {e20:.4f}, EMA50 {e50:.4f}: trend {trend}.",
                         f"RSI14 {value_rsi:.2f}; ATR14 {value_atr:.4f}."]
    if baseline:
        report['reasons'].append(f"Son kapanmış mum hacmi önceki 20 kapanmış mum ortalamasının {quote[-1] / baseline:.2f} katı.")
    return report


def daily_volume(rows, as_of_ms):
    normalized, _ = normalize(rows, '1d')
    data = {r[0]: r for r in normalized if r[6] < as_of_ms}
    day = INTERVALS['1d']
    midnight = bucket(as_of_ms, '1d')
    recent = [midnight - n * day for n in range(7, 0, -1)]
    prior = [midnight - n * day for n in range(14, 7, -1)]
    table = []
    for stamp in recent:
        row = data.get(stamp)
        table.append({'date_utc': iso(stamp)[:10], 'base_volume': row[5] if row else None,
                      'quote_volume_usdt': row[7] if row else None,
                      'taker_buy_quote_usdt': row[10] if row else None,
                      'taker_sell_quote_usdt': str(Decimal(row[7]) - Decimal(row[10])) if row else None})
    complete = all(t in data for t in recent + prior)
    total = sum((Decimal(data[t][7]) for t in recent), Decimal(0)) if all(t in data for t in recent) else None
    before = sum((Decimal(data[t][7]) for t in prior), Decimal(0)) if all(t in data for t in prior) else None
    return {'days': table, 'current_7d_quote_usdt': str(total) if total is not None else None,
            'previous_7d_quote_usdt': str(before) if before is not None else None,
            'change_pct': float((total / before - 1) * 100) if complete and before else None,
            'comparison_complete': complete, 'period_timezone': 'UTC', 'unit': 'USDT',
            'capital_flows': 'NOT_AVAILABLE',
            'note': 'İşlem hacmi ve taker agresifliği yeni para girişi veya zincir üstü borsa akışı değildir.'}
