"""Pure offline linear geometry. Rational results never imply live eligibility."""
from bisect import bisect_right
from fractions import Fraction
import hashlib
import json

from ..chart_precision import decimal_text, PrecisionError
from ..market_data import INTERVALS, bucket
from .service import geometry, DrawingError
from .position import KINDS as POSITION_KINDS, metrics as position_metrics
from .channel import bounds as channel_bounds
from .fibonacci import ratio_text
from .annotations import KINDS as ANNOTATION_KINDS
from .channel_family import SCHEMA as FAMILY_SCHEMA

SCHEMA = 'chart-geometry/1'
RATIOS = ('0', '0.236', '0.382', '0.5', '0.618', '0.786', '1')


class CalculationBlocked(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def timestamp(value):
    if type(value) is not int or not 0 < value <= 32503680000:
        raise CalculationBlocked('INVALID_UTC_SECONDS')
    return value


def price(value):
    try:
        return Fraction(decimal_text(value, positive=True))
    except PrecisionError:
        raise CalculationBlocked('INVALID_DECIMAL_PRICE') from None


def encoded(value):
    """Exact fraction plus terminating decimal when possible; no rounded fallback."""
    value = Fraction(value)
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    decimal = None
    if denominator == 1:
        places = max(twos, fives)
        units = abs(value.numerator) * 2 ** (places - twos) * 5 ** (places - fives)
        digits = str(units).zfill(places + 1)
        decimal = (digits[:-places] + '.' + digits[-places:]).rstrip('0').rstrip('.') if places else digits
        if value < 0:
            decimal = '-' + decimal
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator), 'decimal': decimal}


def logical_position(times, time):
    """Piecewise chart mapping, including known gaps; never extrapolate."""
    timestamp(time)
    if (not isinstance(times, (list, tuple)) or not 2 <= len(times) <= 4000
            or any(type(t) is not int or not 0 < t <= 32503680000 for t in times)
            or any(b <= a for a, b in zip(times, times[1:]))):
        raise CalculationBlocked('INVALID_GRID')
    if not times[0] <= time <= times[-1]:
        raise CalculationBlocked('GRID_OUT_OF_RANGE')
    index = min(bisect_right(times, time) - 1, len(times) - 2)
    return Fraction(index) + Fraction(time - times[index], times[index + 1] - times[index])


def verified_grid(times, interval):
    if not isinstance(interval, str) or interval not in INTERVALS:
        raise CalculationBlocked('UNSUPPORTED_INTERVAL')
    logical_position(times, times[0] if isinstance(times, (list, tuple)) and times else 1)
    step = INTERVALS[interval] // 1000
    if any(bucket(t * 1000, interval) != t * 1000 for t in times):
        raise CalculationBlocked('GRID_BUCKET_MISMATCH')
    if any(b - a != step for a, b in zip(times, times[1:])):
        raise CalculationBlocked('GRID_GAP')
    return tuple(times)


def normalized(value):
    try:
        value = geometry(value)
        if value['kind'] in POSITION_KINDS:
            value = {**value, 'params': {k: None if v is None else decimal_text(v) for k, v in value['params'].items()}}
        return {**value, 'anchors': [{'time': a['time'], 'price': decimal_text(a['price'], positive=True)}
                                    for a in value['anchors']]}
    except (DrawingError, PrecisionError):
        raise CalculationBlocked('INVALID_GEOMETRY') from None


def canonical_hash(value, *, times=None, interval=None, scale='LINEAR'):
    value = normalized(value)
    if value.get('schema') == FAMILY_SCHEMA:
        raise CalculationBlocked('DISPLAY_ONLY_CHANNEL_FAMILY')
    if value['kind'] in ANNOTATION_KINDS:
        raise CalculationBlocked('DISPLAY_ONLY_ANNOTATION')
    if scale != 'LINEAR':
        raise CalculationBlocked('UNSUPPORTED_SCALE')
    if interval is not None and (not isinstance(interval, str) or interval not in INTERVALS):
        raise CalculationBlocked('UNSUPPORTED_INTERVAL')
    if times is not None or value['kind'] in ('trend', 'ray', 'extended_line', 'parallel_channel'):
        times = verified_grid(times, interval)
    if value['kind'] in ('trend', 'ray', 'extended_line', 'parallel_channel'):
        for anchor in value['anchors']:
            logical_position(times, anchor['time'])
    # Labels are presentation; revision/owner must be bound separately by P4.
    semantic = {k: v for k, v in value.items() if k != 'label'}
    payload = {'schema': SCHEMA, 'geometry': semantic, 'scale': scale,
               'source': 'binance_usdm_live_trade_price', 'environment': 'live_public', 'product': 'USD-M',
               'interval': interval, 'grid': list(times) if times is not None else None}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def measure_ruler(value, *, tick_size, times=None, interval=None):
    value = normalized(value)
    if value['kind'] != 'ruler':
        raise CalculationBlocked('UNSUPPORTED_QUERY')
    if not isinstance(interval, str) or interval not in INTERVALS:
        raise CalculationBlocked('UNSUPPORTED_INTERVAL')
    p0, p1 = [price(a['price']) for a in value['anchors']]
    t0, t1 = [a['time'] for a in value['anchors']]
    tick = price(tick_size)
    delta = p1 - p0
    bars = {'state': 'UNAVAILABLE', 'reason': 'GRID_UNAVAILABLE', 'count': None,
            'intervals': None, 'missing_bars': None}
    if times is not None:
        if (not isinstance(times, (list, tuple)) or not 1 <= len(times) <= 4000
                or any(type(t) is not int or not 0 < t <= 32503680000 for t in times)
                or any(b <= a for a, b in zip(times, times[1:]))):
            raise CalculationBlocked('INVALID_GRID')
        if any(bucket(t * 1000, interval) != t * 1000 for t in times):
            raise CalculationBlocked('GRID_BUCKET_MISMATCH')
        low, high = sorted((t0, t1))
        if low < times[0] or high > times[-1]:
            bars['reason'] = 'GRID_OUT_OF_RANGE'
        else:
            positions = [logical_position(times, t) for t in (t0, t1)] if len(times) > 1 else [Fraction(0), Fraction(0)]
            step = INTERVALS[interval] // 1000
            count = sum(low <= t <= high for t in times)
            anchor = 345600 if interval == '1w' else 0
            first = (low-anchor+step-1)//step*step+anchor
            last = (high-anchor)//step*step+anchor
            missing = max(0, (last-first)//step+1)-count
            bars = {'state': 'GAPPED' if missing else 'COMPLETE', 'reason': 'GRID_GAP' if missing else None,
                    'count': count,
                    'intervals': encoded(abs(positions[1]-positions[0])), 'missing_bars': missing}
    return {'schema': 'chart-ruler-measurement/1', 'price_change': encoded(delta),
            'percent_change': encoded(delta / p0 * 100), 'tick_change': encoded(delta / tick),
            'elapsed_seconds': t1-t0, 'duration_seconds': abs(t1-t0), 'bars': bars,
            'live_eligible': False, 'order_authority': False}


def query(value, operation, *, time=None, query_price=None, ratio=None,
          times=None, interval=None, scale='LINEAR', tick_size=None):
    """Calculate from explicit inputs only, with fail-closed scope and grid checks."""
    value = normalized(value)
    if scale != 'LINEAR':
        raise CalculationBlocked('UNSUPPORTED_SCALE')
    if value.get('schema') == FAMILY_SCHEMA:
        raise CalculationBlocked('DISPLAY_ONLY_CHANNEL_FAMILY')
    kind, anchors = value['kind'], value['anchors']
    if kind in ANNOTATION_KINDS:
        raise CalculationBlocked('DISPLAY_ONLY_ANNOTATION')
    if value.get('schema') == 'chart-fibonacci/1':
        if operation != 'level':
            raise CalculationBlocked('UNSUPPORTED_QUERY')
        timestamp(time)
        low, high = sorted(a['time'] for a in anchors)
        if value['time_scope'] == 'bounded' and not low <= time <= high or value['time_scope'] == 'right' and time < low:
            raise CalculationBlocked('OUT_OF_SCOPE')
        try:
            ratio = ratio_text(ratio)
        except ValueError:
            raise CalculationBlocked('UNSUPPORTED_RATIO') from None
        if ratio not in value['levels']:
            raise CalculationBlocked('UNSUPPORTED_RATIO')
        result = price(anchors[0]['price']) + (price(anchors[1]['price'])-price(anchors[0]['price']))*Fraction(ratio)
        if result <= 0:
            raise CalculationBlocked('NON_POSITIVE_LEVEL')
        return {'schema': SCHEMA, 'operation': operation, 'value': encoded(result),
                'live_eligible': False, 'order_authority': False}
    if kind == 'parallel_channel':
        if operation not in ('boundsAt', 'contains', 'distance'):
            raise CalculationBlocked('UNSUPPORTED_QUERY')
        timestamp(time)
        if not min(a['time'] for a in anchors[:2]) <= time <= max(a['time'] for a in anchors[:2]):
            raise CalculationBlocked('OUT_OF_SCOPE')
        grid = verified_grid(times, interval)
        for anchor in anchors:
            logical_position(grid, anchor['time'])
        logical_position(grid, time)
        bounds = channel_bounds(anchors, time)
        observed = None if operation == 'boundsAt' else price(query_price)
        result = ({k: encoded(v) for k, v in bounds.items()} if operation == 'boundsAt'
                  else bounds['lower'] <= observed <= bounds['upper'] if operation == 'contains'
                  else encoded(max(bounds['lower']-observed, observed-bounds['upper'], Fraction(0))))
        return {'schema': SCHEMA, 'operation': operation, 'value': result,
                'live_eligible': False, 'order_authority': False}
    if kind in POSITION_KINDS:
        if operation != 'riskReward':
            raise CalculationBlocked('UNSUPPORTED_QUERY')
        return {'schema': 'chart-position-metrics/1', 'operation': operation,
                'value': {k: None if v is None else encoded(v) for k, v in position_metrics(value).items()},
                'live_eligible': False, 'order_authority': False}
    if kind == 'ruler':
        if operation != 'measurement':
            raise CalculationBlocked('UNSUPPORTED_QUERY')
        return {'schema': SCHEMA, 'operation': operation,
                'value': measure_ruler(value, tick_size=tick_size, times=times, interval=interval),
                'live_eligible': False, 'order_authority': False}
    allowed = {'horizontal': ('priceAt', 'distance'), 'horizontal_ray': ('priceAt', 'distance'),
               'ray': ('priceAt', 'distance'), 'extended_line': ('priceAt', 'distance'), 'trend': ('priceAt', 'distance'),
               'zone': ('contains', 'distance'), 'fibonacci': ('level',)}
    if operation not in allowed[kind]:
        raise CalculationBlocked('UNSUPPORTED_QUERY')
    timestamp(time)
    if kind == 'horizontal_ray' and time < anchors[0]['time']:
        raise CalculationBlocked('OUT_OF_SCOPE')
    if kind == 'ray' and (time-anchors[0]['time'])*(anchors[1]['time']-anchors[0]['time']) < 0:
        raise CalculationBlocked('OUT_OF_SCOPE')
    bounded = kind not in ('ray', 'extended_line') and not (kind == 'zone' and value.get('time_scope') == 'unbounded')
    if bounded and len(anchors) == 2 and not min(a['time'] for a in anchors) <= time <= max(a['time'] for a in anchors):
        raise CalculationBlocked('OUT_OF_SCOPE')
    p0 = price(anchors[0]['price'])
    if kind in ('horizontal', 'horizontal_ray'):
        result = p0
    elif kind == 'zone':
        low, high = sorted((p0, price(anchors[1]['price'])))
        observed = price(query_price)
        result = low <= observed <= high if operation == 'contains' else max(low - observed, observed - high, Fraction(0))
    elif kind == 'fibonacci':
        if not isinstance(ratio, str) or ratio not in RATIOS:
            raise CalculationBlocked('UNSUPPORTED_RATIO')
        result = p0 + (price(anchors[1]['price']) - p0) * Fraction(ratio)
    else:
        grid = verified_grid(times, interval)
        start, end, current = [logical_position(grid, t) for t in (anchors[0]['time'], anchors[1]['time'], time)]
        result = p0 + (price(anchors[1]['price']) - p0) * (current - start) / (end - start)
        if result <= 0:
            raise CalculationBlocked('NON_POSITIVE_PROJECTION')
    if operation == 'distance' and kind != 'zone':
        result = abs(price(query_price) - result)
    return {'schema': SCHEMA, 'operation': operation,
            'value': result if isinstance(result, bool) else encoded(result),
            'live_eligible': False, 'order_authority': False}
