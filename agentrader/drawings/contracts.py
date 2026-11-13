"""Read-only tool contract registry. No calculation or execution authority."""
from copy import deepcopy

from .service import DrawingError
from .scale_policy import view_policy
from .annotations import KINDS as ANNOTATION_KINDS
from .channel_family import SCHEMA as FAMILY_SCHEMA, KINDS as FAMILY_KINDS, NEW_KINDS as FAMILY_NEW_KINDS, OPTION_KEYS as FAMILY_OPTIONS

SCHEMA = 'chart-tool-contract/1'
REGISTRY_SCHEMA = 'chart-tool-registry/1'
LEGACY_KINDS = ('horizontal', 'zone', 'trend', 'fibonacci')
LINE_KINDS = ('horizontal_ray', 'ray', 'extended_line')
POSITION_KINDS = ('long_plan', 'short_plan')
SUPPORTED_KINDS = LEGACY_KINDS + ('ruler',) + LINE_KINDS + ('parallel_channel', 'fibonacci_extension')


class UnsupportedTool(DrawingError):
    status = 422
    code = 'BLOCKED_UNSUPPORTED_TOOL'


def family_capability(kind):
    if kind not in FAMILY_KINDS:
        raise UnsupportedTool()
    return {'category': 'drawing', 'kind': kind, 'schema': SCHEMA, 'version': 1,
            'readable': True, 'editable': True, 'computable': False,
            'definition': {'state': 'VERSIONED_READABLE', 'anchor_count': 2 if kind == 'regression_channel' else 3,
                           'anchor_time_unit': 'UTC_SECONDS', 'price_encoding': 'DECIMAL_TEXT',
                           'parameter_names': ['text', *sorted(FAMILY_OPTIONS)], 'planned_queries': [],
                           'market_fields': ['source', 'product', 'price_type', 'symbol', 'interval'],
                           'write_schema': FAMILY_SCHEMA},
            'canonical_queries': [], 'calculation_state': 'DISPLAY_ONLY',
            'required_context': [], 'display_model': {'schema': FAMILY_SCHEMA, 'configurable': True},
            'binding_model': None, 'scale_policy': {**view_policy(kind), 'geometry_scale': 'DISPLAY_AXIS', 'LOG': 'NATIVE_SCREEN_GEOMETRY'},
            'tracking_activation': False, 'order_authority': False}


def definition(category, kind):
    """Shape and query names are declarations, never implementation claims."""
    anchor_counts = {'text': 1, 'note': 1, 'price_label': 1, 'horizontal': 1, 'zone': 2, 'trend': 2, 'fibonacci': 2,
                     'long_plan': 3, 'short_plan': 3, 'ruler': 2, 'horizontal_ray': 1, 'ray': 2, 'extended_line': 2,
                     'parallel_channel': 3, 'fibonacci_extension': 2,
                     'fibonacci_projection': 3, 'anchored_vwap': 1}
    queries = {
        'horizontal': ['priceAt', 'distance'], 'zone': ['contains', 'distance'],
        'trend': ['priceAt', 'distance'], 'fibonacci': ['level'],
        'ruler': ['measurement'], 'horizontal_ray': ['priceAt', 'distance'],
        'ray': ['priceAt', 'distance'], 'extended_line': ['priceAt', 'distance'],
        'parallel_channel': ['boundsAt', 'contains', 'distance'],
        'fibonacci_extension': ['level'], 'fibonacci_projection': ['level'],
    }
    params = {
        'ruler': ['tick_size', 'interval', 'loaded_bar_grid'],
        'fibonacci': ['ratios', 'scale', 'geometry_basis'],
        'fibonacci_extension': ['ratios', 'scale', 'geometry_basis'],
        'fibonacci_projection': ['ratios', 'scale', 'geometry_basis'],
        'sma': ['period', 'source', 'seed', 'warmup'],
        'ema': ['period', 'source', 'smoothing', 'seed', 'warmup'],
        'rsi': ['period', 'source', 'smoothing', 'seed', 'warmup'],
        'atr': ['period', 'smoothing', 'seed', 'warmup'],
        'macd': ['period', 'fast_period', 'signal_period', 'source', 'oscillator_type', 'signal_type', 'style'],
        'bb': ['period', 'source', 'basis_type', 'deviation', 'offset', 'style'],
        'session_vwap': ['source', 'computation_mode', 'raw_volume_source', 'reset_utc', 'display_interval'],
        'anchored_vwap': ['source', 'computation_mode', 'anchor_time', 'anchor_symbol', 'raw_volume_source', 'display_interval'],
        'long_plan': ['entry', 'stop', 'target', 'risk_budget', 'fee_bps', 'slippage_bps'],
        'short_plan': ['entry', 'stop', 'target', 'risk_budget', 'fee_bps', 'slippage_bps'],
        'approach': ['binding_revision', 'direction', 'tolerance', 'rearm'],
        'touch': ['binding_revision', 'direction', 'tolerance', 'rearm'],
        'close_cross': ['binding_revision', 'direction', 'closed_candle', 'rearm'],
    }
    return {'state': 'VERSIONED_READABLE' if kind == 'ruler' or kind in LINE_KINDS or kind in POSITION_KINDS or kind in ('parallel_channel', 'fibonacci_extension') or kind in ANNOTATION_KINDS else 'LEGACY_READABLE' if kind in LEGACY_KINDS else 'DECLARED_ONLY',
            'anchor_count': anchor_counts.get(kind, 0),
            'anchor_time_unit': 'UTC_SECONDS', 'price_encoding': 'DECIMAL_TEXT',
            'parameter_names': params.get(kind, ['scale', 'geometry_basis']),
            'planned_queries': [] if kind in ANNOTATION_KINDS else queries.get(kind, ['valueAt'] if category == 'indicator'
                                           else ['riskReward'] if category == 'plan' else ['evaluate']),
            'market_fields': ['source', 'product', 'price_type', 'symbol', 'interval'],
            'write_schema': 'chart-annotation/1' if kind in ANNOTATION_KINDS else 'chart-fibonacci/1' if kind == 'fibonacci_extension' else 'chart-channel/1' if kind == 'parallel_channel' else 'chart-position/1' if kind in POSITION_KINDS else 'chart-ruler/1' if kind == 'ruler' else 'chart-line/1' if kind in LINE_KINDS else 'LEGACY_GEOMETRY_V1' if kind in LEGACY_KINDS else None}


def registry():
    groups = {
        'drawing': ('horizontal', 'zone', 'trend', 'fibonacci', 'ruler',
                    'horizontal_ray', 'ray', 'extended_line', 'parallel_channel',
                    'fibonacci_extension', 'fibonacci_projection'),
        'annotation': ANNOTATION_KINDS,
        'indicator': ('sma', 'ema', 'rsi', 'atr', 'session_vwap', 'anchored_vwap', 'macd', 'bb'),
        'plan': ('long_plan', 'short_plan'),
        'rule': ('approach', 'touch', 'close_cross'),
    }
    tools = []
    for category, kinds in groups.items():
        for kind in kinds:
            legacy = category == 'drawing' and kind in SUPPORTED_KINDS or category == 'plan' and kind in POSITION_KINDS or category == 'annotation' and kind in ANNOTATION_KINDS
            tools.append({'category': category, 'kind': kind, 'schema': SCHEMA,
                          'version': 1, 'readable': legacy, 'editable': legacy,
                          'computable': legacy and category != 'annotation',
                          'definition': definition(category, kind),
                          'canonical_queries': definition(category, kind)['planned_queries'] if legacy and category != 'annotation' else [],
                          'calculation_state': 'DISPLAY_ONLY' if category == 'annotation' else 'PURE_OFFLINE_REQUIRES_CONTEXT' if legacy else 'NOT_IMPLEMENTED',
                          'required_context': ['tick_size', 'loaded_bar_grid', 'interval'] if kind == 'ruler' else ['verified_bar_grid', 'interval'] if kind in ('trend', 'ray', 'extended_line', 'parallel_channel') else [],
                          'display_model': {'schema': 'chart-indicators/4', 'state': 'VERSIONED_DISPLAY_CALCULATION', 'outputs': ['macd', 'signal', 'histogram'] if kind == 'macd' else ['basis', 'upper', 'lower'] if kind == 'bb' else ['value'], 'configurable': True} if category == 'indicator' and kind in ('sma', 'ema', 'rsi', 'atr', 'macd', 'bb', 'session_vwap', 'anchored_vwap') else None,
                          'binding_model': {'schema': 'chart-binding-definition/1', 'default_state': 'DISABLED', 'explicit_rebind': True, 'target_write': False, 'target_edit': False, 'execute_rule': False, 'order_authority': False} if legacy and category != 'annotation' or category == 'indicator' and kind in ('sma','ema','rsi','atr','macd','bb','session_vwap','anchored_vwap') else None,
                          'scale_policy': view_policy(kind, legacy), 'tracking_activation': False, 'order_authority': False})
    tools.extend(family_capability(kind) for kind in FAMILY_NEW_KINDS)
    return {'schema': REGISTRY_SCHEMA, 'tools': tools,
            'separation': {'visibility': 'DISPLAY_ONLY', 'lock': 'EDIT_ONLY',
                           'tracking': 'SEPARATE_REVISION_BOUND_RULE',
                           'orders': 'SEPARATE_AUTHORIZATION'}}


def capability(category, kind, version=1):
    if type(version) is not int or version != 1:
        raise UnsupportedTool()
    for tool in registry()['tools']:
        if tool['category'] == category and tool['kind'] == kind:
            return tool
    raise UnsupportedTool()


def legacy_contract(drawing):
    """Project existing geometry without rewriting history or inferring interval."""
    geometry = drawing['geometry']
    if geometry.get('schema') == FAMILY_SCHEMA:
        tool = family_capability(geometry['kind'])
        return {'schema': SCHEMA, 'version': 1, 'category': 'drawing', 'kind': geometry['kind'],
                'object_id': drawing['drawing_id'], 'revision': drawing['revision'],
                'workspace_id': drawing['workspace_id'], 'deleted': drawing['deleted'],
                'presentation': deepcopy(drawing.get('management', {})),
                'edit_state': 'LOCKED' if drawing.get('management', {}).get('locked') else 'EDITABLE',
                'label': geometry['label'],
                'market': {'source': 'binance_usdm_live_trade_price', 'product': 'USD-M',
                           'price_type': geometry['price_source'], 'symbol': geometry['symbol'],
                           'interval': None, 'interval_state': 'NOT_BOUND_TO_INTERVAL'},
                'anchors': deepcopy(geometry['anchors']),
                'params': {'geometry_schema': FAMILY_SCHEMA, 'options': deepcopy(geometry['options']),
                           'text': geometry['text'], 'bot_use': 'DISPLAY_ONLY'},
                'time_scope': {'mode': 'DISPLAY_EXTENT', 'unit': 'UTC_SECONDS',
                               'start': min(a['time'] for a in geometry['anchors']),
                               'end': max(a['time'] for a in geometry['anchors'])},
                'capabilities': tool,
                'evaluation': {'state': 'BLOCKED', 'reason': 'DISPLAY_ONLY_CHANNEL_FAMILY'},
                'origin': FAMILY_SCHEMA}
    if geometry['kind'] in LINE_KINDS and geometry.get('schema') != 'chart-line/1':
        raise UnsupportedTool()
    if geometry['kind'] in ANNOTATION_KINDS and geometry.get('schema') != 'chart-annotation/1':
        raise UnsupportedTool()
    if geometry['kind'] == 'fibonacci_extension' and geometry.get('schema') != 'chart-fibonacci/1':
        raise UnsupportedTool()
    if geometry['kind'] == 'parallel_channel' and geometry.get('schema') != 'chart-channel/1':
        raise UnsupportedTool()
    if geometry['kind'] in POSITION_KINDS and geometry.get('schema') != 'chart-position/1':
        raise UnsupportedTool()
    tool = capability('annotation' if geometry['kind'] in ANNOTATION_KINDS else 'plan' if geometry['kind'] in POSITION_KINDS else 'drawing', geometry['kind'])
    if not tool['readable']:
        raise UnsupportedTool()
    kind = geometry['kind']
    scope = 'UNBOUNDED' if kind == 'horizontal' else 'ANCHOR_BOUNDED'
    params = {'scale': 'LINEAR', 'geometry_basis': 'LEGACY_LOGICAL_GRID'}
    if kind == 'ruler':
        params = {'geometry_schema': 'chart-ruler/1', 'geometry_basis': 'UTC_AND_LOADED_BAR_INTERVALS_V1'}
    if kind == 'fibonacci':
        params['ratios'] = ['0', '0.236', '0.382', '0.5', '0.618', '0.786', '1']
    start = None if kind == 'horizontal' else min(a['time'] for a in geometry['anchors'])
    end = None if kind == 'horizontal' else max(a['time'] for a in geometry['anchors'])
    if kind in LINE_KINDS or geometry.get('schema') == 'chart-zone/1':
        params = {'scale': 'LINEAR', 'geometry_schema': geometry['schema'],
                  'geometry_basis': 'VERIFIED_LOGICAL_GRID' if kind in ('ray', 'extended_line') else 'UTC_PRICE_SCOPE'}
        if kind == 'extended_line' or geometry.get('time_scope') == 'unbounded':
            scope, start, end = 'UNBOUNDED', None, None
        elif kind == 'horizontal_ray' or kind == 'ray':
            forward = kind == 'horizontal_ray' or geometry['anchors'][1]['time'] > geometry['anchors'][0]['time']
            scope = 'FORWARD_RAY' if forward else 'BACKWARD_RAY'
            start, end = (geometry['anchors'][0]['time'], None) if forward else (None, geometry['anchors'][0]['time'])
    if geometry.get('schema') == 'chart-fibonacci/1':
        params = {'ratios': geometry['levels'], 'scale': 'LINEAR', 'geometry_schema': 'chart-fibonacci/1', 'geometry_basis': 'TWO_ANCHOR_PRICE_INTERPOLATION'}
        if geometry['time_scope'] == 'unbounded':
            scope, start, end = 'UNBOUNDED', None, None
        elif geometry['time_scope'] == 'right':
            scope, end = 'FORWARD_FROM_EARLIEST_ANCHOR', None
    if kind == 'parallel_channel':
        params = {'geometry_schema': 'chart-channel/1', 'geometry_basis': 'VERIFIED_LOGICAL_GRID', 'scale': 'LINEAR', 'scope': 'BASE_ANCHOR_BOUNDED'}
        start, end = sorted(a['time'] for a in geometry['anchors'][:2])
    if kind in POSITION_KINDS:
        params = {**geometry['params'], 'geometry_schema': 'chart-position/1', 'geometry_basis': 'HYPOTHETICAL_PRICE_LEVELS', 'cost_basis': 'ADVERSE_PER_SIDE_BPS'}
    if kind in ANNOTATION_KINDS:
        params = {'geometry_schema': 'chart-annotation/1', 'geometry_basis': 'UTC_PRICE_ANCHOR', 'text': geometry['text'], 'bot_use': 'DISPLAY_ONLY'}
        scope = 'ANCHOR_POINT'
    return {'schema': SCHEMA, 'version': 1, 'category': 'annotation' if kind in ANNOTATION_KINDS else 'plan' if kind in POSITION_KINDS else 'drawing', 'kind': kind,
            'object_id': drawing['drawing_id'], 'revision': drawing['revision'],
            'workspace_id': drawing['workspace_id'], 'deleted': drawing['deleted'],
            'presentation': deepcopy(drawing.get('management', {})),
            'edit_state': 'LOCKED' if drawing.get('management', {}).get('locked') else 'EDITABLE',
            'label': geometry['label'],
            'market': {'source': 'binance_usdm_live_trade_price', 'product': 'USD-M',
                       'price_type': geometry['price_source'], 'symbol': geometry['symbol'],
                       'interval': None, 'interval_state': 'NOT_BOUND_TO_INTERVAL' if kind in ANNOTATION_KINDS else 'UNSPECIFIED_LEGACY'},
            'anchors': deepcopy(geometry['anchors']), 'params': params,
            'time_scope': {'mode': scope, 'unit': 'UTC_SECONDS',
                           'start': start, 'end': end},
            'capabilities': tool, 'evaluation': {'state': 'BLOCKED',
                                               'reason': 'LIVE_EVALUATION_NOT_IMPLEMENTED'},
            'origin': geometry.get('schema', 'LEGACY_GEOMETRY_V1_READ_PROJECTION') if kind != 'ruler' else 'CHART_RULER_V1'}
