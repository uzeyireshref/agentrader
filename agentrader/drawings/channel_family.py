"""Validated, display-only channel and pitchfork persistence contract.

These drawings do not acquire the legacy parallel channel's bot/query authority.
"""
from fractions import Fraction
import math
import re

from ..chart_precision import decimal_text

SCHEMA = 'chart-channel-family/1'
PITCHFORKS = ('pitchfork', 'schiff_pitchfork', 'modified_schiff_pitchfork', 'inside_pitchfork')
KINDS = ('parallel_channel', 'flat_channel', 'disjoint_channel', 'regression_channel', *PITCHFORKS)
NEW_KINDS = tuple(kind for kind in KINDS if kind != 'parallel_channel')
OPTION_KEYS = {'extend', 'median', 'background', 'fill_opacity', 'prices', 'levels', 'source',
               'upper_deviation', 'lower_deviation', 'upper_enabled', 'lower_enabled', 'pearson'}


def options(value):
    if not isinstance(value, dict) or set(value) not in (OPTION_KEYS, OPTION_KEYS | {'line_styles'}):
        raise ValueError('INVALID_CHANNEL_OPTIONS')
    if (value['extend'] not in ('none', 'left', 'right', 'both')
            or value['source'] not in ('open', 'high', 'low', 'close', 'hl2', 'hlc3', 'ohlc4')
            or any(type(value[key]) is not bool for key in ('median', 'background', 'prices',
                                                           'upper_enabled', 'lower_enabled', 'pearson'))
            or type(value['fill_opacity']) not in (int, float)
            or not math.isfinite(value['fill_opacity']) or not 0 <= value['fill_opacity'] <= 1):
        raise ValueError('INVALID_CHANNEL_OPTIONS')
    styles = value.get('line_styles', {})
    if not isinstance(styles, dict) or len(styles) > 24:
        raise ValueError('INVALID_CHANNEL_LINE_STYLES')
    for role, style in styles.items():
        if (not isinstance(role, str) or not re.fullmatch(r'(median|base|offset|upper|lower|level:-?\d+(?:\.\d+)?)', role)
                or not isinstance(style, dict) or set(style) != {'color', 'width', 'style'}
                or not isinstance(style['color'], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', style['color'])
                or type(style['width']) is not int or not 1 <= style['width'] <= 8
                or style['style'] not in ('solid', 'dashed', 'dotted')):
            raise ValueError('INVALID_CHANNEL_LINE_STYLES')
    levels = value['levels']
    if not isinstance(levels, list) or not 0 <= len(levels) <= 9:
        raise ValueError('INVALID_CHANNEL_LEVELS')
    levels = [decimal_text(level, positive=True) for level in levels]
    if any(Fraction(level) > 10 or len(level.partition('.')[2]) > 12 for level in levels) or len(set(levels)) != len(levels):
        raise ValueError('INVALID_CHANNEL_LEVELS')
    deviations = {key: decimal_text(value[key]) for key in ('upper_deviation', 'lower_deviation')}
    if any(Fraction(v) > 10 or len(v.partition('.')[2]) > 12 for v in deviations.values()):
        raise ValueError('INVALID_CHANNEL_DEVIATION')
    return {**value, **deviations, 'levels': levels}


def text(value):
    if not isinstance(value, str):
        raise ValueError('INVALID_CHANNEL_TEXT')
    value = value.replace('\r\n', '\n').replace('\r', '\n')
    if (len(value) > 1000 or len(value.split('\n')) > 8
            or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', value)):
        raise ValueError('INVALID_CHANNEL_TEXT')
    return value


def validate(value):
    """Anchors have already been type/decimal checked by the drawing service."""
    if value['kind'] not in KINDS or value.get('schema') != SCHEMA:
        raise ValueError('INVALID_CHANNEL_FAMILY')
    result = {**value, 'options': options(value.get('options')), 'text': text(value.get('text'))}
    anchors = result['anchors']
    if len(anchors) != (2 if value['kind'] == 'regression_channel' else 3):
        raise ValueError('INVALID_CHANNEL_ANCHORS')
    a, b = anchors[:2]
    if a['time'] == b['time']:
        raise ValueError('INVALID_CHANNEL_DIRECTION')
    if value['kind'] == 'regression_channel':
        return result
    c = anchors[2]
    pa, pb, pc = (Fraction(anchor['price']) for anchor in (a, b, c))
    if value['kind'] in PITCHFORKS and b['time'] == c['time'] and pb == pc:
        raise ValueError('DUPLICATE_CHANNEL_POINT')
    if value['kind'] in PITCHFORKS:
        midpoint = Fraction(b['time'] + c['time'], 2)
        midpoint_price = (pb + pc) / 2
        origin = Fraction(a['time'])
        origin_price = pa
        if value['kind'] == 'schiff_pitchfork':
            origin_price = (pa + pb) / 2
        if value['kind'] == 'modified_schiff_pitchfork':
            origin = Fraction(a['time'] + b['time'], 2)
            origin_price = (pa + pb) / 2
        elif value['kind'] == 'inside_pitchfork':
            origin, midpoint = Fraction(a['time'] + b['time'], 2), Fraction(c['time'])
            origin_price, midpoint_price = (pa + pb) / 2, pc
        if midpoint == origin and midpoint_price == origin_price:
            raise ValueError('INVALID_PITCHFORK_DIRECTION')
    elif value['kind'] == 'parallel_channel':
        offset = pc - (pa + (pb-pa) * Fraction(c['time']-a['time'], b['time']-a['time']))
        if not offset or min(pa+offset, pb+offset) <= 0:
            raise ValueError('INVALID_CHANNEL_WIDTH')
    elif value['kind'] == 'flat_channel' and pa == pb == pc:
        raise ValueError('INVALID_CHANNEL_WIDTH')
    elif value['kind'] == 'disjoint_channel' and (pa == pb == pc or pc+pb-pa <= 0):
        raise ValueError('INVALID_CHANNEL_WIDTH')
    return result
