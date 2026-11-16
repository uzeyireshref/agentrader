"""Signed drawing coordinates, deliberately separate from market/order prices."""
import re
from agentrader.chart.chart_precision import decimal_text,PrecisionError

def coordinate_text(value):
    if not isinstance(value,str) or not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?',value):
        raise PrecisionError('INVALID_DRAWING_COORDINATE')
    negative=value.startswith('-')
    magnitude=decimal_text(value[1:] if negative else value)
    return '-'+magnitude if negative and magnitude!='0' else magnitude
