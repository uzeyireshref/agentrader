"""Revision-bound HTTP geometry queries over the same read-only chart context."""
from contextlib import closing
import re
import sqlite3

from agentrader.chart.chart_context import ContextReadLimit
from agentrader.chart.chart_evidence import canonical
from agentrader.chart.drawings.calculations import query, CalculationBlocked
from agentrader.chart.drawings.contracts import capability
from agentrader.chart.drawings.service import DrawingError, DrawingNotFound, identifier

REQUEST_SCHEMA = 'chart-query-request/1'
RESPONSE_SCHEMA = 'chart-query-response/1'
CALCULATION_VERSION = 'chart-geometry-http/1'
MAX_QUERIES = 50
MAX_OUTPUT_BYTES = 262144
CONTEXT_FIELDS = {'symbol', 'interval', 'source', 'environment', 'product', 'price_type',
                  'required_closed_bars', 'include_open', 'expected_context_id'}


class InvalidChartQuery(DrawingError):
    code = 'INVALID_CHART_QUERY'


class ChartQueryOutputLimit(DrawingError):
    status = 413
    code = 'CHART_QUERY_OUTPUT_LIMIT'


def failure(entry, state, code, status=422):
    return dict(query_id=entry.get('query_id'), drawing_id=entry.get('drawing_id'), state=state,
                expected_revision=entry.get('expected_revision'), operation=entry.get('operation'),
                inputs=entry.get('inputs'), scale=entry.get('scale', 'LINEAR'),
                http_status=status, error=dict(code=code), order_authority=False)


class ChartQueries:
    def __init__(self, context):
        self.context = context

    def _head(self, drawing_id, deadline):
        identifier(drawing_id)
        if self.context.monotonic() > deadline:
            raise ContextReadLimit()
        with closing(sqlite3.connect(self.context.database.resolve().as_uri()+'?mode=ro', uri=True, timeout=.2)) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            row = self.context.drawings._head(db, drawing_id)
            if row['deleted']:
                raise DrawingNotFound()
            return self.context.drawings._view(row,db)

    def single(self, drawing_id, schema_version, context, entry):
        # Determine the workspace only after owner-scoped lookup; no foreign metadata leaks.
        deadline = self.context.monotonic()+2
        item = self._head(drawing_id, deadline)
        if not isinstance(entry, dict) or 'drawing_id' in entry:
            raise InvalidChartQuery()
        return self.run(item['workspace_id'], schema_version, context, [{**entry, 'drawing_id': drawing_id}], _deadline=deadline)

    def _evaluate(self, workspace_id, entry, data, snapshot, deadline):
        allowed = {'query_id', 'drawing_id', 'expected_revision', 'operation', 'inputs', 'scale'}
        if (not isinstance(entry, dict) or set(entry)-allowed or not allowed-{'scale'} <= set(entry)
                or type(entry['expected_revision']) is not int or entry['expected_revision'] < 1
                or not isinstance(entry['operation'], str) or not isinstance(entry['inputs'], dict)):
            return failure(entry if isinstance(entry, dict) else {}, 'INVALID_INPUT', 'INVALID_QUERY_FIELDS')
        try:
            item = self._head(entry['drawing_id'], deadline)
        except ContextReadLimit:
            raise
        except DrawingNotFound:
            return failure(entry, 'NOT_FOUND', 'DRAWING_NOT_FOUND', 404)
        except DrawingError:
            return failure(entry, 'INVALID_INPUT', 'INVALID_DRAWING_ID')
        if item['workspace_id'] != workspace_id:
            return failure(entry, 'NOT_FOUND', 'DRAWING_NOT_FOUND', 404)
        if item['revision'] != entry['expected_revision']:
            return failure(entry, 'REVISION_CONFLICT', 'DRAWING_REVISION_CONFLICT', 409)
        geometry = item['geometry']
        if geometry['symbol'] != snapshot['market']['symbol'] or geometry['price_source'] != snapshot['market']['price_type']:
            return failure(entry, 'SOURCE_MISMATCH', 'OBJECT_CONTEXT_MISMATCH')
        category = 'annotation' if geometry['kind'] in ('text', 'note', 'price_label') else 'plan' if geometry['kind'] in ('long_plan', 'short_plan') else 'drawing'
        tool = capability(category, geometry['kind'], record_schema=geometry.get('schema', 'LEGACY_GEOMETRY_V1'))
        operations = {spec['operation']: spec for spec in tool['python_geometry']['operations']}
        spec = operations.get(entry['operation'])
        if spec is None:
            return failure(entry, 'UNSUPPORTED_OPERATION', 'UNSUPPORTED_QUERY')
        scale = entry.get('scale', 'LINEAR')
        if scale not in spec['supported_scales']:
            return failure(entry, 'UNSUPPORTED_OPERATION', 'UNSUPPORTED_SCALE')
        inputs = entry['inputs']
        if set(inputs) != set(spec['required_inputs']):
            return failure(entry, 'INVALID_INPUT', 'INVALID_QUERY_INPUTS')
        if any(not isinstance(inputs[key], str) or len(inputs[key]) > 128 for key in ('query_price', 'ratio') if key in inputs):
            return failure(entry, 'INVALID_INPUT', 'DECIMAL_TEXT_REQUIRED')
        ready = snapshot['derived']['readiness']
        consumes_data = bool(spec['required_context'])
        if ready['state'] in ('SOURCE_MISMATCH', 'INVALID_INPUT') or consumes_data and ready['state'] != 'READY':
            return failure(entry, ready['state'], ready['reasons'][0])
        rows = data['rows'] if consumes_data else []
        rows = rows if ready['open_candle_used'] else [r for r in rows if r['closed']]
        native = dict(times=[row['time'] for row in rows], interval=snapshot['market']['interval'],
                      tick_size=data['market'].get('tick_size')) if consumes_data else {}
        if geometry.get('schema') == 'chart-channel-family/1':
            native['rows'] = rows
        try:
            result = query(geometry, entry['operation'], scale=scale, **inputs, **native)
        except CalculationBlocked as exc:
            state = ('WARMUP' if exc.code == 'INSUFFICIENT_REGRESSION_SAMPLES' else
                     'UNSUPPORTED_OPERATION' if exc.code == 'VERTICAL_GEOMETRY' else
                     'WAITING_FOR_DATA' if exc.code.startswith('GRID_') or exc.code in ('INVALID_GRID', 'REGRESSION_HISTORY_REQUIRED') else 'INVALID_INPUT')
            failed = failure(entry, state, exc.code)
            if exc.details is not None:
                failed['error']['details'] = exc.details
            return failed
        value = result['value']
        # A non-terminating decimal still has an exact fraction; it is not an undefined output.
        undefined = [key for key, output in value.items() if output is None] if isinstance(value, dict) and 'numerator' not in value else []
        return dict(query_id=entry['query_id'], drawing_id=item['drawing_id'], revision=item['revision'],
                    origin=item['origin'], linked_note=item['linked_note'], change=item['change'],
                    geometry_schema=tool['record_schema'], operation=entry['operation'], inputs=inputs, scale=scale,
                    state='READY', scope='GEOMETRY_NOT_ORDER_ELIGIBILITY', http_status=200,
                    data_consumed=consumes_data,
                    consumed_data_hash=ready['consumed_data_hash'] if consumes_data else None,
                    consumed_range=ready['consumed_range'] if consumes_data else None,
                    result=result, undefined_outputs=undefined,
                    number_encoding='EXACT_FRACTION_OR_EXPLICIT_FLOAT64_TOLERANCE' if result.get('numeric_basis') == 'FLOAT64_EXPLICIT_TOLERANCE' else 'EXACT_FRACTION_WITH_DECIMAL_WHEN_TERMINATING', order_authority=False)

    def run(self, workspace_id, schema_version, context, entries, *, _deadline=None):
        if (schema_version != REQUEST_SCHEMA or not isinstance(context, dict) or set(context)-CONTEXT_FIELDS
                or not {'symbol', 'interval'} <= set(context)
                or any(not isinstance(context[key], str) or not context[key] for key in ('symbol', 'interval'))
                or not isinstance(entries, list) or not 1 <= len(entries) <= MAX_QUERIES):
            raise InvalidChartQuery()
        keys = [entry.get('query_id') if isinstance(entry, dict) else None for entry in entries]
        if any(not isinstance(key, str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}', key) for key in keys) or len(set(keys)) != len(keys):
            raise InvalidChartQuery()
        # Per-request deadline stays local: this service is shared by concurrent HTTP requests.
        deadline = _deadline if _deadline is not None else self.context.monotonic()+2
        snapshot, data = self.context.read(workspace_id, **context, limit=1, _capture=True, _deadline=deadline)
        results = [self._evaluate(workspace_id, entry, data, snapshot, deadline) for entry in entries]
        # Reject the whole response on a race; never pair old computations with new revisions/data.
        self.context.read(workspace_id, **{**context, 'expected_context_id': snapshot['context_id']}, limit=1, _deadline=deadline)
        response = dict(schema_version=RESPONSE_SCHEMA, calculation_version=CALCULATION_VERSION,
                        context_id=snapshot['context_id'], server_utc=snapshot['server_utc'], market=snapshot['market'],
                        data_identity=snapshot['data_identity'], readiness=snapshot['derived']['readiness'],
                        indicator_settings_revision=snapshot['indicators']['revision'], results=results,
                        summary=dict(succeeded=sum(r['state']=='READY' for r in results), failed=sum(r['state']!='READY' for r in results)),
                        order_authority=False)
        if len(canonical(response).encode()) > MAX_OUTPUT_BYTES:
            raise ChartQueryOutputLimit()
        if self.context.monotonic() > deadline:
            raise ContextReadLimit()
        return response
