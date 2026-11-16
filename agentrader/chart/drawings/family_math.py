"""Data-coordinate channel geometry; exact LINEAR, explicit FLOAT64 log/statistics."""
from fractions import Fraction
import math
import re

from agentrader.shared.market_data import INTERVALS

OPERATIONS = ('geometry', 'priceAt', 'boundsAt', 'contains', 'distance', 'slope')
PITCHFORKS = ('pitchfork', 'schiff_pitchfork', 'modified_schiff_pitchfork', 'inside_pitchfork')
VERSION = 'chart-channel-calculation/1'


def calculate(g, operation, *, times, interval, rows=None, scale='LINEAR', time=None, query_price=None, ratio=None):
    # Local import avoids a cycle while retaining one validation/error/number vocabulary.
    from agentrader.chart.drawings.calculations import CalculationBlocked, verified_grid, timestamp, price, encoded
    if scale not in ('LINEAR', 'LOG'):
        raise CalculationBlocked('UNSUPPORTED_SCALE')
    if operation not in OPERATIONS+('level',) or operation == 'level' and g['kind'] not in PITCHFORKS:
        raise CalculationBlocked('UNSUPPORTED_QUERY')
    grid = verified_grid(times, interval)
    step = INTERVALS[interval]//1000
    o, kind = g['options'], g['kind']
    approximate = scale == 'LOG' and kind != 'regression_channel' or kind == 'regression_channel'

    def number(v):
        if isinstance(v, Fraction) or isinstance(v, int):
            return encoded(v)
        if not math.isfinite(v):
            raise CalculationBlocked('NONFINITE_RESULT')
        return dict(decimal=format(v, '.17g'), numeric_basis='FLOAT64', precision_digits=16,
                    absolute_tolerance='1e-8', relative_tolerance='1e-10')

    def logical(t):
        timestamp(t)
        # Uniform verified interval; geometric projection never inserts candles.
        return Fraction(t-grid[0], step)

    def to_price(y):
        try:
            result = math.exp(y) if scale == 'LOG' and kind != 'regression_channel' else y
        except OverflowError:
            raise CalculationBlocked('NONFINITE_RESULT') from None
        if not math.isfinite(result):
            raise CalculationBlocked('NONFINITE_RESULT')
        return result

    def point(a):
        y = price(a['price'])
        return (logical(a['time']), math.log(float(y)) if scale == 'LOG' else y)

    def add(a, b): return (a[0]+b[0], a[1]+b[1])
    def sub(a, b): return (a[0]-b[0], a[1]-b[1])
    def mul(a, k): return (a[0]*k, a[1]*k)
    def mid(a, b): return mul(add(a, b), Fraction(1, 2))
    lines = []
    metadata = {}

    def line(a, b, role, visible=True, mode=None):
        value = dict(a=a, b=b, role=role, visible=visible, mode=o['extend'] if mode is None else mode)
        lines.append(value)
        return value

    if kind == 'regression_channel':
        if not isinstance(rows, list) or len(rows) != len(grid) or [r['time'] for r in rows] != list(grid):
            raise CalculationBlocked('REGRESSION_HISTORY_REQUIRED')
        def containing(t):
            timestamp(t)
            return next((i for i, r in enumerate(rows) if r['time'] <= t and t*1000 <= r['close_time']), None)
        indices = [containing(a['time']) for a in g['anchors']]
        selection = dict(raw_anchor_times=[a['time'] for a in g['anchors']],
                         effective_anchor_times=[rows[i]['time'] if i is not None else None for i in indices],
                         required_samples=2)
        if None in indices:
            raise CalculationBlocked('REGRESSION_HISTORY_REQUIRED', selection)
        start, end = sorted(indices)
        if start == end:
            raise CalculationBlocked('INSUFFICIENT_REGRESSION_SAMPLES', {**selection, 'sample_count': 1})
        sample = rows[start:end+1]
        def source(r):
            fields = {key: float(r[key]) for key in ('open', 'high', 'low', 'close')}
            if any(not math.isfinite(v) or v <= 0 for v in fields.values()):
                raise CalculationBlocked('INVALID_REGRESSION_SOURCE')
            key = o['source']
            return ((fields['high']+fields['low'])/2 if key == 'hl2' else
                    (fields['high']+fields['low']+fields['close'])/3 if key == 'hlc3' else
                    sum(fields.values())/4 if key == 'ohlc4' else fields[key])
        values = [source(r) for r in sample]
        n = len(values)
        mx, my = (n-1)/2, sum(values)/n
        xx = sum((i-mx)**2 for i in range(n))
        xy = sum((i-mx)*(y-my) for i, y in enumerate(values))
        yy = sum((y-my)**2 for y in values)
        slope = xy/xx
        intercept = my-slope*mx
        deviation = math.sqrt(sum((y-intercept-slope*i)**2 for i, y in enumerate(values))/(n-1))
        up = deviation*float(o['upper_deviation']) if o['upper_enabled'] else max(r['high']-intercept-slope*i for i, r in enumerate(sample))
        down = deviation*float(o['lower_deviation']) if o['lower_enabled'] else max(intercept+slope*i-r['low'] for i, r in enumerate(sample))
        a, b = (Fraction(start), intercept), (Fraction(end), intercept+slope*(n-1))
        median = line(a, b, 'median', o['median'])
        boundaries = [line((a[0], a[1]+up), (b[0], b[1]+up), 'upper'),
                      line((a[0], a[1]-down), (b[0], b[1]-down), 'lower')]
        handles = [a, b] if indices[0] < indices[1] else [b, a]
        metadata = dict(raw_anchor_times=[a['time'] for a in g['anchors']],
                        effective_anchor_times=[rows[i]['time'] for i in indices],
                        sample_first_time=sample[0]['time'], sample_last_time=sample[-1]['time'], sample_count=n,
                        source=o['source'], open_candle_used=any(not r['closed'] for r in sample),
                        deviation=number(deviation), deviation_basis='RESIDUAL_SAMPLE_N_MINUS_1',
                        pearson=number(0. if yy == 0 else -xy/math.sqrt(xx*yy)),
                        pearson_convention='NEGATED_PRICE_CORRELATION_COMPATIBILITY',
                        scale_basis='RAW_PRICE_OLS_INDEPENDENT_OF_DISPLAY_SCALE')
        x = None
        if operation not in ('geometry', 'slope'):
            index = containing(time)
            if index is None:
                raise CalculationBlocked('REGRESSION_HISTORY_REQUIRED')
            x = Fraction(index)
            metadata['effective_query_time'] = rows[index]['time']
    else:
        a, b, c = [point(anchor) for anchor in g['anchors']]
        if kind in PITCHFORKS:
            m = mid(b, c)
            origin = (a[0], (a[1]+b[1])/2) if kind == 'schiff_pitchfork' else mid(a, b) if kind == 'modified_schiff_pitchfork' else a
            direction = sub(c, mid(a, b)) if kind == 'inside_pitchfork' else sub(m, origin)
            median = line(m if kind == 'inside_pitchfork' else origin, add(m, direction) if kind == 'inside_pitchfork' else m, 'median', o['median'])
            line(b, c, 'connector', o['median'], 'none')
            if kind != 'pitchfork': line(a, b, 'connector', o['median'], 'none')
            if kind == 'inside_pitchfork': line(mid(a, b), c, 'connector', o['median'], 'none')
            half = sub(c, m)
            sides = []
            for level in sorted(Fraction(v) for v in o['levels']):
                for sign in (-1, 1):
                    p = add(m, mul(half, level*sign))
                    sides.append(line(p, add(p, direction), 'level:'+str(float(level*sign)).rstrip('0').rstrip('.')))
            boundaries = sides if sides else [median]
            handles = [a, b, c]
        else:
            if kind == 'parallel_channel':
                offset = c[1]-(a[1]+(b[1]-a[1])*(c[0]-a[0])/(b[0]-a[0]))
                d, end = (a[0], a[1]+offset), (b[0], b[1]+offset)
            elif kind == 'flat_channel':
                d, end = (a[0], c[1]), (b[0], c[1])
            else:
                d, end = (a[0], c[1]+b[1]-a[1]), (b[0], c[1])
            boundaries = [line(a, b, 'base'), line(d, end, 'offset')]
            median = line(mid(a, d), mid(b, end), 'median', o['median'])
            handles = [a, b, end, d]
        x = logical(time) if operation not in ('geometry', 'slope') else None

    def at(segment):
        a, b = segment['a'], segment['b']
        if a[0] == b[0]:
            raise CalculationBlocked('VERTICAL_GEOMETRY')
        position = (x-a[0])/(b[0]-a[0])
        if position < 0 and segment['mode'] not in ('left', 'both') or position > 1 and segment['mode'] not in ('right', 'both'):
            raise CalculationBlocked('OUT_OF_SCOPE')
        return to_price(a[1]+(b[1]-a[1])*position)

    if operation == 'geometry':
        def output_point(p): return dict(logical=number(p[0]), price=number(to_price(p[1])))
        value = dict(lines=[dict(role=s['role'], a=output_point(s['a']), b=output_point(s['b']),
                                extend=s['mode'], visible=s['visible']) for s in lines],
                     handles=[output_point(p) for p in handles])
    elif operation == 'slope':
        value = dict(unit='LOG_PRICE_PER_BAR' if scale == 'LOG' and kind != 'regression_channel' else 'PRICE_PER_BAR',
                     lines=[dict(role=s['role'], state='UNDEFINED_VERTICAL' if s['a'][0] == s['b'][0] else 'READY',
                                 value=None if s['a'][0] == s['b'][0] else number((s['b'][1]-s['a'][1])/(s['b'][0]-s['a'][0])))
                            for s in [median, *boundaries]])
    elif operation == 'priceAt':
        value = number(at(median))
    elif operation == 'level':
        if not isinstance(ratio, str) or not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]{1,12})?|\.[0-9]{1,12})', ratio):
            raise CalculationBlocked('UNSUPPORTED_RATIO')
        try: level = Fraction(ratio)
        except (ValueError, TypeError, ZeroDivisionError): raise CalculationBlocked('UNSUPPORTED_RATIO') from None
        if level == 0:
            value = number(at(median))
        else:
            if abs(level) not in [Fraction(v) for v in o['levels']]:
                raise CalculationBlocked('UNSUPPORTED_RATIO')
            selected = next(s for s in boundaries if Fraction(s['role'].split(':')[1]) == level)
            value = number(at(selected))
    else:
        values_at_time = [at(s) for s in boundaries]
        lower, upper = min(values_at_time), max(values_at_time)
        if operation == 'boundsAt':
            value = dict(lower=number(lower), upper=number(upper), middle=number(at(median)), width=number(upper-lower))
        else:
            observed = price(query_price)
            value = lower <= observed <= upper if operation == 'contains' else number(max(lower-observed, observed-upper, 0))
    return dict(schema=VERSION, calculation_version=VERSION, operation=operation, scale=scale,
                numeric_basis='FLOAT64_EXPLICIT_TOLERANCE' if approximate else 'EXACT_RATIONAL', value=value,
                regression=metadata, live_eligible=False, order_authority=False)
