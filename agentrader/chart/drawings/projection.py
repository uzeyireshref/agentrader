"""Three-anchor price-delta projection, distinct from two-anchor extension."""
from fractions import Fraction
SCHEMA='chart-fibonacci-projection/1'
KIND='fibonacci_projection'


def extent(value):
    a,b,c=value['anchors']
    return c['time'],c['time']+abs(b['time']-a['time'])


def validate(value):
    a,b,c=value['anchors']
    if a['time']==b['time'] or Fraction(a['price'])==Fraction(b['price']):raise ValueError('INVALID_PROJECTION_IMPULSE')
    if value['time_scope']=='bounded' and extent(value)[1]>32503680000:raise ValueError('INVALID_PROJECTION_EXTENT')
    return value


def level(value,ratio):
    a,b,c=value['anchors']
    return Fraction(c['price'])+Fraction(ratio)*(Fraction(b['price'])-Fraction(a['price']))
