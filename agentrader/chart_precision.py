"""Versioned exact decimal sidecar; presentation floats never establish precision."""
from decimal import Decimal, InvalidOperation

SCHEMA = 'chart-exact-decimal/1'
FIELDS = {'open':1, 'high':2, 'low':3, 'close':4, 'volume':5, 'quote_volume':7}

class PrecisionError(ValueError):
    pass


def decimal_text(value, *, positive=False):
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise PrecisionError('PRICE_PRECISION_UNPROVEN')
    # Decimal accepts whitespace and underscores; wire decimal text does not.
    import re
    if not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', value):
        raise PrecisionError('INVALID_DECIMAL')
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise PrecisionError('INVALID_DECIMAL') from None
    if not number.is_finite() or not -30 <= number.adjusted() <= 30 or number < 0 or (positive and number <= 0):
        raise PrecisionError('INVALID_DECIMAL')
    # No normalize()/arithmetic: neither may round using the ambient Decimal context.
    text = format(number, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return '0' if number == 0 else text.lstrip('+')


def exact_candle(row):
    if any(not isinstance(row[i], str) for i in FIELDS.values()):
        return {'schema':SCHEMA, 'state':'UNPROVEN', 'reason':'PRICE_PRECISION_UNPROVEN'}
    values = {name:decimal_text(row[i], positive=name in ('open','high','low','close')) for name,i in FIELDS.items()}
    op,hi,lo,cl = (Decimal(values[k]) for k in ('open','high','low','close'))
    if lo > min(op,cl) or hi < max(op,cl) or lo > hi:
        raise PrecisionError('INVALID_OHLC')
    return {'schema':SCHEMA, 'state':'VERIFIED', 'provenance':'UPSTREAM_DECIMAL_TEXT', **values}


def exact_tick(value):
    try:
        return {'schema':SCHEMA, 'state':'VERIFIED', 'provenance':'UPSTREAM_DECIMAL_TEXT', 'tick_size':decimal_text(value, positive=True)}
    except PrecisionError:
        return {'schema':SCHEMA, 'state':'UNPROVEN', 'reason':'PRICE_PRECISION_UNPROVEN'}


def validate_tick_price(price, tick):
    """Reject off-grid anchors; never round. Integer ratios avoid context rounding."""
    p = Decimal(decimal_text(price, positive=True))
    t = Decimal(decimal_text(tick, positive=True))
    pn,pd = p.as_integer_ratio();tn,td = t.as_integer_ratio()
    if (pn*td) % (pd*tn):
        raise PrecisionError('PRICE_OFF_TICK')
    return decimal_text(price, positive=True)


def precision_summary(rows, market):
    count = sum(r.get('exact',{}).get('schema')==SCHEMA and r['exact'].get('state')=='VERIFIED' for r in rows)
    tick = (market or {}).get('exact',{})
    verified = bool(rows) and count==len(rows) and tick.get('schema')==SCHEMA and tick.get('state')=='VERIFIED'
    return {'schema':SCHEMA, 'state':'VERIFIED' if verified else 'UNPROVEN', 'reason':None if verified else 'PRICE_PRECISION_UNPROVEN', 'verified_candles':count, 'required_candles':len(rows), 'bot_eligible':False}
