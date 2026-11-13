"""Independent high-precision reference fixtures, no market/network access."""
from decimal import Decimal, localcontext
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]

def ema_reference(prices, period):
    if len(prices) < period:
        return []
    value = mean(prices[:period])
    result = [value]
    weight = Decimal(2) / Decimal(period + 1)
    for price in prices[period:]:
        value += weight * (price - value)
        result.append(value)
    return result

def rsi_reference(prices, period=14):
    changes = [b-a for a, b in zip(prices, prices[1:])]
    gains = [max(change, Decimal(0)) for change in changes]
    losses = [max(-change, Decimal(0)) for change in changes]
    if len(changes) < period:
        return []
    gain, loss = mean(gains[:period]), mean(losses[:period])
    averages = [(gain, loss)]
    for next_gain, next_loss in zip(gains[period:], losses[period:]):
        gain = (gain * (period-1) + next_gain) / period
        loss = (loss * (period-1) + next_loss) / period
        averages.append((gain, loss))
    return [Decimal(50) if g == l == 0 else Decimal(100) if l == 0 else Decimal(100) * g/(g+l) for g, l in averages]

def main():
    with localcontext() as context:
        context.prec = 50
        base = [Decimal(100) + Decimal(i)/4 + Decimal((i*17)%23-11)/10 for i in range(300)]
        cases = {'flat': [Decimal(100)]*300,
                 'rising': [Decimal(100)+Decimal(i)/4 for i in range(300)],
                 'falling': [Decimal(200)-Decimal(i)/4 for i in range(300)],
                 'mixed': base,
                 'time_gap': base,
                 'changed_live_close': base[:-1]+[base[-1]+Decimal('3.75')]}
        result = []
        for name, prices in cases.items():
            times = [1800000000+i*900+(2700 if name == 'time_gap' and i >= 133 else 0) for i in range(len(prices))]
            result.append({'name': name, 'times': times, 'closes': [str(p) for p in prices],
                           'ema20': [str(v) for v in ema_reference(prices,20)],
                           'ema50': [str(v) for v in ema_reference(prices,50)],
                           'rsi14': [str(v) for v in rsi_reference(prices)]})
        report = {'date': '2026-11-09', 'reference': 'Python Decimal precision 50; SMA EMA seed, Wilder RSI; flat RSI=50',
                  'network_requests': 0, 'cases': result}
    path = ROOT/'reports/indicator-reference-20261109.json'
    path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'cases': len(result), 'reference_values': sum(len(c[k]) for c in result for k in ('ema20','ema50','rsi14')), 'path': str(path)}))

if __name__ == '__main__':
    main()
