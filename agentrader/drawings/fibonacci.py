"""Versioned decimal ratios; two-anchor extension is not three-anchor projection."""
from fractions import Fraction
import re

LEGACY_LEVELS = ('0', '0.236', '0.382', '0.5', '0.618', '0.786', '1')
EXTENSION_LEVELS = ('0', '1', '1.272', '1.618', '2', '2.618')


def ratio_text(value):
    if (not isinstance(value, str) or len(value) > 32
            or not re.fullmatch(r'[+-]?[0-9]+(?:\.[0-9]{1,12})?', value)
            or abs(Fraction(value)) > 10):
        raise ValueError('INVALID_FIBONACCI_RATIO')
    sign = '-' if value.startswith('-') else ''
    whole, _, fraction = value.lstrip('+-').partition('.')
    text = str(int(whole)) + ('.'+fraction.rstrip('0') if fraction.rstrip('0') else '')
    return '0' if Fraction(value) == 0 else sign+text


def levels(value):
    if not isinstance(value, list) or not 2 <= len(value) <= 24:
        raise ValueError('INVALID_FIBONACCI_LEVELS')
    result = [ratio_text(r) for r in value]
    if len(set(result)) != len(result):
        raise ValueError('DUPLICATE_FIBONACCI_RATIO')
    return result
