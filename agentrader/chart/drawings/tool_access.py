"""Implemented access surfaces, distinct from planned queries and screen rendering."""

ACCESS_SCHEMA = 'chart-tool-access/1'
LEGACY = 'LEGACY_GEOMETRY_V1'
FAMILY = 'chart-channel-family/1'
DRAWINGS = '/api/workspaces/{workspace_id}/drawings'
OBJECT = '/api/drawings/{drawing_id}'
INDICATORS = '/api/workspaces/{workspace_id}/indicators'


def surface(implemented=False, *, method=None, path=None, reason=None):
    return dict(implemented=implemented, state='IMPLEMENTED' if implemented else 'NOT_APPLICABLE' if reason == 'NOT_APPLICABLE' else 'NOT_IMPLEMENTED',
                method=method, path=path, reason=reason)


def record_access(tool, record_schema):
    category, kind = tool['category'], tool['kind']
    indicator = category == 'indicator'
    persisted = bool(record_schema) and category != 'rule'
    drawing = persisted and not indicator
    mathematical = drawing and category != 'annotation'
    operations = (['geometry', 'priceAt', 'boundsAt', 'contains', 'distance', 'slope'] + (['level'] if 'pitchfork' in kind else [])
                  if record_schema == FAMILY else list(tool['canonical_queries']) if mathematical else [])
    scales = ['LINEAR', 'LOG'] if record_schema in (FAMILY,'chart-fibonacci-projection/1') else ['LINEAR'] if mathematical else []
    fields = ['label'] if drawing else []
    if category == 'annotation' or record_schema == FAMILY:
        fields.append('text')
    access = {
        'metadata_read': surface(persisted, method='GET' if persisted else None,
                                 path=INDICATORS if indicator else OBJECT if drawing else None),
        'text_read': surface(drawing, method='GET' if drawing else None, path=OBJECT if drawing else None),
        'linked_notes_read': surface(drawing, method='GET' if drawing else None, path=OBJECT+'/notes' if drawing else None, reason=None if drawing else 'NOT_APPLICABLE'),
        'linked_notes_write': surface(drawing, method='PUT' if drawing else None, path=OBJECT+'/notes' if drawing else None, reason=None if drawing else 'NOT_APPLICABLE'),
        'revision_history': surface(drawing, method='GET' if drawing else None, path=OBJECT+'/history' if drawing else None, reason=None if drawing else 'NOT_APPLICABLE'),
        'geometry_query': surface(mathematical, method='POST' if mathematical else None,
                                  path=OBJECT+'/queries' if mathematical else None,
                                  reason=None if mathematical else 'NOT_APPLICABLE' if category in ('annotation', 'indicator', 'rule') else 'BACKEND_GEOMETRY_NOT_IMPLEMENTED'),
        'indicator_series': surface(indicator, method='POST' if indicator else None,
                                    path='/api/workspaces/{workspace_id}/indicator-queries' if indicator else None,
                                    reason=None if indicator else 'NOT_APPLICABLE'),
        'ui_state_read': surface(persisted, method='GET' if persisted else None, path='/api/workspaces/{workspace_id}/ui-sessions/{ui_session_id}' if persisted else None, reason=None if persisted else 'NOT_APPLICABLE'),
        'copy_export': surface(drawing,method='POST' if drawing else None,path='/api/workspaces/{workspace_id}/drawing-packages/export' if drawing else None,reason=None if drawing else 'NOT_APPLICABLE'),
        'paste': surface(drawing,method='POST' if drawing else None,path='/api/workspaces/{workspace_id}/drawing-packages/paste' if drawing else None,reason=None if drawing else 'NOT_APPLICABLE'),
        'create': surface(drawing, method='POST' if drawing else None, path=DRAWINGS if drawing else None),
        'edit': surface(persisted, method='PUT' if indicator else 'PATCH' if drawing else None,
                        path=INDICATORS if indicator else OBJECT if drawing else None),
        'delete': surface(drawing, method='DELETE' if drawing else None, path=OBJECT if drawing else None),
    }
    version = (10 if record_schema=='chart-fibonacci-projection/1' else 4 if indicator else 9 if record_schema == FAMILY else 8 if record_schema == 'chart-annotation/1'
               else 7 if record_schema == 'chart-fibonacci/1' else 6 if record_schema == 'chart-channel/1'
               else 5 if record_schema == 'chart-position/1' else 3 if record_schema in ('chart-zone/1', 'chart-line/1')
               else 2 if record_schema == 'chart-ruler/1' else 1)
    requirements = (['times', 'interval'] + (['rows'] if kind == 'regression_channel' else []) if record_schema == FAMILY else
                    ['times', 'interval'] if mathematical and kind in ('trend', 'ray', 'extended_line', 'parallel_channel')
                    else ['tick_size', 'interval'] if mathematical and kind == 'ruler' else [])
    specs = []
    for operation in operations:
        inputs = [] if operation in ('riskReward', 'measurement', 'geometry', 'slope') else ['time']
        if operation in ('contains', 'distance'):
            inputs.append('query_price')
        if operation == 'level':
            inputs.append('ratio')
        specs.append(dict(operation=operation, required_inputs=inputs,
                          required_context=requirements, supported_scales=scales))
    return dict(record_schema=record_schema, implementation_state='IMPLEMENTED' if persisted else 'NOT_IMPLEMENTED',
                resource='INDICATOR_CONFIGURATION' if indicator else 'DRAWING' if drawing else 'DECLARATION',
                format_version=version if persisted else None,
                features={key: value['implemented'] for key, value in access.items()},
                access=access, text_fields=fields, related_notes=drawing,
                http_geometry_operations=[{**spec, 'required_context': ['chart_context'],
                                           'data_required': bool(requirements)} for spec in specs],
                http_batch_query_path='/api/workspaces/{workspace_id}/chart-queries' if mathematical else None,
                http_indicator_operations=[dict(operation=operation,required_inputs=['time'] if operation=='at' else [],
                                                optional_inputs=['start_time','end_time','limit','offset'] if operation=='series' else [])
                                           for operation in ('series','latest','at')] if indicator else [],
                indicator_outputs=tool['display_model']['outputs'] if indicator else [],
                indicator_timezone='UTC' if indicator else None,
                indicator_calculation_version='chart-indicator-http/1' if indicator else None,
                python_geometry=dict(implemented=mathematical,
                                     handler='agentrader.chart.drawings.calculations.query' if mathematical else None,
                                     operations=specs, supported_scales=scales),
                data_requirements=requirements,
                optional_context=['times'] if mathematical and kind == 'ruler' else [],
                constraints=['OWNER_SCOPED', 'REVISION_CHECKED_WRITES', 'LOCK_POLICY', 'SERVER_VERIFIED_ORIGIN', 'BOT_CANNOT_EDIT_MANUAL', 'BOT_STRATEGY_SCOPED_WRITES'] if drawing
                else ['OWNER_SCOPED', 'REVISION_CHECKED_WORKSPACE_CONFIGURATION', 'FIXED_INDICATOR_SLOTS'] if indicator else [],
                order_authority=False)


def enrich(tool):
    """Additive v1 extension: old booleans retain their historical meanings."""
    primary = tool['definition']['write_schema']
    schemas = [primary] if primary else ['chart-indicators/4'] if tool['category'] == 'indicator' else []
    alternatives = {'zone': 'chart-zone/1', 'fibonacci': 'chart-fibonacci/1', 'parallel_channel': FAMILY}
    if (tool['category'] == 'drawing' and tool['kind'] in alternatives
            and alternatives[tool['kind']] not in schemas):
        schemas.append(alternatives[tool['kind']])
    variants = [record_access(tool, schema) for schema in schemas]
    default = record_access(tool, primary if primary else schemas[0] if schemas else None)
    return {**tool, 'access_schema': ACCESS_SCHEMA, **default, 'record_variants': variants,
            'preferred_write_schema': schemas[-1] if schemas else None}
