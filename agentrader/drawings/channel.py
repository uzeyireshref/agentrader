"""Three-anchor bounded parallel price channel, independent of chart pixels."""
from fractions import Fraction
from ..chart_precision import decimal_text


def basis(anchors):
    if not isinstance(anchors, list) or len(anchors) != 3:
        raise ValueError('INVALID_CHANNEL')
    a, b, c = anchors
    if a['time'] == b['time'] or not min(a['time'], b['time']) <= c['time'] <= max(a['time'], b['time']):
        raise ValueError('INVALID_CHANNEL_TIME')
    pa, pb, pc = [Fraction(decimal_text(p['price'], positive=True)) for p in anchors]
    slope = (pb-pa)/(b['time']-a['time'])
    offset = pc-(pa+slope*(c['time']-a['time']))
    if not offset or min(pa+offset, pb+offset) <= 0:
        raise ValueError('DEGENERATE_CHANNEL')
    return pa, slope, offset


def bounds(anchors, time):
    pa, slope, offset = basis(anchors)
    first = pa+slope*(time-anchors[0]['time'])
    lower, upper = sorted((first, first+offset))
    return dict(lower=lower, upper=upper, middle=(lower+upper)/2, width=upper-lower)
