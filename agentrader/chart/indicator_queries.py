"""Read-only, revision-bound indicator series over an existing chart snapshot."""
from fractions import Fraction
import math
import re

from agentrader.chart.chart_context import ContextReadLimit
from agentrader.chart.chart_evidence import canonical, canonical_row, digest, snapshot as data_snapshot
from agentrader.chart.chart_queries import CONTEXT_FIELDS
from agentrader.chart.drawings.calculations import encoded, timestamp, CalculationBlocked
from agentrader.chart.drawings.service import DrawingError
from agentrader.chart.indicator_config import series, multi_series
from agentrader.shared.market_data import INTERVALS
from agentrader.chart.vwap import vwap_series

REQUEST_SCHEMA = 'indicator-query-request/1'
RESPONSE_SCHEMA = 'indicator-query-response/1'
VERSION = 'chart-indicator-http/1'
MAX_QUERIES = 9
MAX_OUTPUT_BYTES = 524288


class InvalidIndicatorQuery(DrawingError):
    code = 'INVALID_INDICATOR_QUERY'


class IndicatorOutputLimit(DrawingError):
    status = 413
    code = 'INDICATOR_QUERY_OUTPUT_LIMIT'


def outputs(config):
    return ['macd', 'signal', 'histogram'] if config['kind'] == 'MACD' else ['basis', 'upper', 'lower'] if config['kind'] == 'BB' else ['value']


def warmup(config):
    period = config['period']
    if config['kind'] == 'MACD':
        return dict(macd=period, signal=period+config['params']['signal_period']-1,
                    histogram=period+config['params']['signal_period']-1)
    return {name: period+1 if config['kind'] == 'RSI' else 1 if 'VWAP' in config['kind'] else period for name in outputs(config)}


def state_for(reason):
    if reason == 'READY': return 'READY'
    if reason == 'WARMUP': return 'WARMUP'
    if reason == 'ANCHOR_SYMBOL_MISMATCH': return 'SOURCE_MISMATCH'
    if reason == 'SESSION_INTERVAL_UNSUPPORTED': return 'UNSUPPORTED_OPERATION'
    if reason in ('ANCHOR_UNSET', 'ANCHOR_NOT_ON_GRID', 'INVALID_GRID', 'EXACT_VOLUME_UNPROVEN', 'INVALID_VOLUME_SOURCE'):
        return 'INVALID_INPUT'
    return 'WAITING_FOR_DATA'


def failure(entry, state, code, status=422):
    return dict(query_id=entry.get('query_id'), indicator_id=entry.get('indicator_id'),
                operation=entry.get('operation'), state=state, http_status=status, error=dict(code=code), order_authority=False)


def value_of(point):
    if 'exact_ratio' in point:
        ratio = point['exact_ratio']
        return encoded(Fraction(int(ratio['numerator']), int(ratio['denominator'])))
    value = point['value']
    if not math.isfinite(value):
        raise ValueError('NONFINITE_RESULT')
    return dict(decimal=format(value, '.17g'), numeric_basis='FLOAT64', precision_digits=16)


class IndicatorQueries:
    def __init__(self, context):
        self.context = context

    def _calculate(self, rows, config, interval, symbol):
        """Compute the full loaded input once; slicing must never reseed EMA/ATR/MACD."""
        names = outputs(config)
        if 'VWAP' in config['kind']:
            result = vwap_series(rows, config, interval, symbol)
            points = {'value': {p['time']: p for p in result['points']}}
            reasons = {p['time']: p['state'] for p in result['states']}
            return points, reasons, result['provenance']
        raw = multi_series(rows, config, interval) if config['kind'] in ('MACD', 'BB') else {'value': series(rows, config, interval)}
        shift = config['params']['offset']*(INTERVALS[interval]//1000) if config['kind'] == 'BB' else 0
        return {key: {p['time']-shift: p for p in raw[key]} for key in names}, {}, dict(
            seed='LOADED_HISTORY_START', first_input_time=rows[0]['time'] if rows else None,
            display_offset_bars=config.get('params', {}).get('offset', 0), filter_reseeds=False)

    def _segments(self, rows, config, points, data, market):
        """Prove each valid VWAP accumulation range without changing the source proof."""
        segments=[]
        step=INTERVALS[market['interval']]//1000
        session=config['kind']=='SESSION_VWAP'
        for row in rows:
            t=row['time']
            if t not in points['value']:continue
            if (segments and t==segments[-1]['last_time']+step
                    and (not session or t//86400==segments[-1]['first_time']//86400)):
                segments[-1]['last_time']=t;segments[-1]['count']+=1
            else:
                segments.append(dict(segment_id='segment-'+str(len(segments)),first_time=t,last_time=t,count=1,
                                     input_first_time=t//86400*86400 if session else config['params']['anchor_time']))
        for segment in segments:
            source=[r for r in rows if segment['input_first_time']<=r['time']<=segment['last_time']]
            segment['input_count']=len(source)
            segment['proof']=data_snapshot(source,data['market'],dict(state='OK',missing_bars=0),
                                           symbol=market['symbol'],interval=market['interval'],epoch=data['stream_epoch'],
                                           generation=data['generation'],revision=data['data_revision']).view()
        return segments

    def _evaluate(self, entry, snapshot, data, deadline, cache):
        allowed = {'query_id', 'indicator_id', 'expected_revision', 'operation', 'inputs', 'outputs', 'timezone'}
        required = {'query_id', 'indicator_id', 'expected_revision', 'operation', 'inputs'}
        if (not required <= set(entry) or set(entry)-allowed or type(entry['expected_revision']) is not int
                or entry['expected_revision'] < 0 or not isinstance(entry['inputs'], dict)):
            return failure(entry, 'INVALID_INPUT', 'INVALID_QUERY_FIELDS')
        config = next((c for c in snapshot['indicators']['indicators'] if c['indicator_id'] == entry['indicator_id']), None)
        if config is None:
            return failure(entry, 'NOT_FOUND', 'INDICATOR_NOT_FOUND', 404)
        if config['revision'] != entry['expected_revision']:
            return failure(entry, 'REVISION_CONFLICT', 'INDICATOR_REVISION_CONFLICT', 409)
        if entry.get('timezone', 'UTC') != 'UTC':
            return failure(entry, 'UNSUPPORTED_OPERATION', 'UNSUPPORTED_TIMEZONE')
        names = entry.get('outputs', outputs(config))
        if (not isinstance(names, list) or not names or any(not isinstance(k, str) or k not in outputs(config) for k in names)
                or len(names) != len(set(names))):
            return failure(entry, 'INVALID_INPUT', 'INVALID_OUTPUTS')
        operation, inputs = entry['operation'], entry['inputs']
        if operation not in ('series', 'latest', 'at'):
            return failure(entry, 'UNSUPPORTED_OPERATION', 'UNSUPPORTED_QUERY')
        if set(inputs)-({'start_time', 'end_time', 'limit', 'offset'} if operation == 'series' else {'time'} if operation == 'at' else set()) or operation == 'at' and set(inputs) != {'time'}:
            return failure(entry, 'INVALID_INPUT', 'INVALID_QUERY_INPUTS')
        try:
            for key in ('time', 'start_time', 'end_time'):
                if key in inputs: timestamp(inputs[key])
        except CalculationBlocked:
            return failure(entry, 'INVALID_INPUT', 'INVALID_UTC_SECONDS')
        limit, offset = inputs.get('limit', 100), inputs.get('offset', 0)
        if (type(limit) is not int or not 1 <= limit <= 200 or type(offset) is not int or not 0 <= offset <= 499
                or inputs.get('start_time', 0) > inputs.get('end_time', 32503680000)):
            return failure(entry, 'INVALID_INPUT', 'INVALID_PAGE_OR_RANGE')
        if offset and not snapshot.get('_pagination_bound'):
            return failure(entry, 'INVALID_INPUT', 'PAGINATION_CONTEXT_REQUIRED')
        ready = snapshot['derived']['readiness']
        # Existing VWAP resets can recover a later complete session after an older gap.
        # Keep the whole-source BLOCKED proof visible; never upgrade it to VERIFIED.
        segmented = (data is not None and 'VWAP' in config['kind'] and ready['state'] == 'WAITING_FOR_DATA'
                     and ready.get('proof') is not None and ready['proof']['valid']
                     and set(ready['proof']['blocked_reasons']) <= {'GRID_GAP', 'QUALITY_UNPROVEN', 'PRICE_PRECISION_UNPROVEN'}
                     and (ready['proof']['missing_bars'] > 0 or 'PRICE_PRECISION_UNPROVEN' in ready['proof']['blocked_reasons'])
                     and data['quality']['state'] == ('GAP' if ready['proof']['missing_bars'] else 'OK')
                     and data['quality']['missing_bars'] == ready['proof']['missing_bars']
                     and data['transport_state'] == 'LIVE' and data['timing']['state'] == 'FRESH')
        if ready['state'] != 'READY' and not segmented:
            return failure(entry, ready['state'], ready['reasons'][0])
        rows = data['rows'] if snapshot['_include_open'] else [r for r in data['rows'] if r['closed']]
        if self.context.monotonic() > deadline: raise ContextReadLimit()
        key = config['indicator_id']
        if key not in cache:
            try:
                cache[key] = self._calculate(rows, config, snapshot['market']['interval'], snapshot['market']['symbol'])
            except (ValueError, KeyError, TypeError, OverflowError):
                return failure(entry, 'INVALID_INPUT', 'INVALID_INDICATOR_DATA')
        points, reasons, provenance = cache[key]
        segments=[]
        segment_by_time={}
        if 'VWAP' in config['kind']:
            segment_key=('segments',key)
            if segment_key not in cache:cache[segment_key]=self._segments(rows,config,points,data,snapshot['market'])
            segments=cache[segment_key]
            for segment in segments:
                for row in rows:
                    if segment['first_time']<=row['time']<=segment['last_time']:
                        segment_by_time[row['time']]=segment
        effective_time = None
        selection_reason='NO_CANDLES_IN_RANGE'
        if operation == 'latest':
            selected = rows[-1:]
            total = len(selected)
        elif operation == 'at':
            selected = [r for r in rows if r['time'] <= inputs['time'] and inputs['time']*1000 <= r['close_time']]
            effective_time = selected[0]['time'] if selected else None
            if not selected:
                selection_reason=('OPEN_CANDLE_EXCLUDED' if not snapshot['_include_open'] and any(
                    r['time']<=inputs['time'] and inputs['time']*1000<=r['close_time'] and not r['closed'] for r in data['rows'])
                                  else 'CANDLE_NOT_LOADED')
            total = len(selected)
        else:
            in_range = [r for r in rows if inputs.get('start_time', 0) <= r['time'] <= inputs.get('end_time', 32503680000)]
            total = len(in_range)
            selected = in_range[offset:offset+limit]
        requirements = warmup(config)
        positions={r['time']:i+1 for i,r in enumerate(rows)}
        available_prefix=max((positions[r['time']] for r in selected),default=0)
        result_outputs = {}
        states = []
        partial = False
        try:
            for name in names:
                output = []
                for row in selected:
                    t = row['time']
                    point = points[name].get(t)
                    reason = 'READY' if point is not None else reasons.get(t, 'WARMUP')
                    segment=segment_by_time.get(t)
                    if point is not None and 'VWAP' in config['kind'] and (segment is None or segment['proof']['state']!='VERIFIED'):
                        point=None;reason='EXACT_VOLUME_UNPROVEN'
                    record = dict(time=t, state=state_for(reason), available_input_count=positions[t])
                    if point is not None:
                        record.update(value=value_of(point), display_time=point['time'])
                        if segment is not None:record['segment_id']=segment['segment_id']
                    else:
                        record['reason'] = reason
                    output.append(record)
                status = 'READY' if any(p['state'] == 'READY' for p in output) else output[-1]['state'] if output else 'WAITING_FOR_DATA'
                partial = partial or any(p['state'] != 'READY' for p in output)
                states.append(status)
                result_outputs[name] = dict(state=status, required_input_count=requirements[name],
                                            available_input_count=available_prefix, loaded_input_count=len(rows),
                                            ready_count=sum(p['state']=='READY' for p in output),
                                            points=output, reason=output[-1].get('reason') if output else selection_reason)
        except (ValueError, OverflowError, ZeroDivisionError):
            return failure(entry, 'INVALID_INPUT', 'NONFINITE_INDICATOR_RESULT')
        priority = ['INVALID_INPUT', 'SOURCE_MISMATCH', 'UNSUPPORTED_OPERATION', 'WAITING_FOR_DATA', 'WARMUP']
        state = next((s for s in priority if s in states), 'READY')
        selected_segments={p.get('segment_id') for output in result_outputs.values() for p in output['points'] if p['state']=='READY'}
        return dict(query_id=entry['query_id'], indicator_id=key, revision=config['revision'],
                    state=state, http_status=200 if state == 'READY' else 422,
                    scope='INDICATOR_CALCULATION_NOT_ORDER_ELIGIBILITY', configuration=config,
                    operation=operation, inputs=inputs, effective_time=effective_time, timezone='UTC',
                    session_boundary='UTC_00:00' if config['kind']=='SESSION_VWAP' else None,
                    warmup=dict(required_input_counts=requirements, available_input_count=available_prefix, loaded_input_count=len(rows),
                                first_input_time=rows[0]['time'] if rows else None, seed=config['anchor']),
                    source_price_field=config['source'], provenance=provenance, calculated_on_request=True,
                    open_candle_used=any(not r['closed'] for r in rows),
                    consumed_range=ready['consumed_range'], consumed_data_hash=ready['consumed_data_hash'],
                    calculation_input_range=dict(first_time=rows[0]['time'],last_time=rows[available_prefix-1]['time'],count=available_prefix) if available_prefix else None,
                    calculation_input_hash=digest([canonical_row(r) for r in rows[:available_prefix]]) if available_prefix else None,
                    data_proof_scope='VWAP_VALIDATED_SEGMENTS_WHOLE_SOURCE_STILL_BLOCKED' if segmented else 'VERIFIED_SOURCE_SNAPSHOT',
                    ready_segments=[s for s in segments if s['segment_id'] in selected_segments], partial=partial, outputs=result_outputs,
                    pagination=dict(limit=limit if operation=='series' else 1, offset=offset if operation=='series' else 0,
                                    total=total, next_offset=offset+limit if operation=='series' and offset+limit<total else None),
                    number_encoding='EXACT_RATIO_WHERE_AVAILABLE_OTHERWISE_FLOAT64_DECIMAL',
                    tolerance=dict(absolute='1e-8',relative='1e-10'), order_authority=False)

    def run(self, workspace_id, schema_version, context, entries):
        if (schema_version != REQUEST_SCHEMA or not isinstance(context, dict) or set(context)-CONTEXT_FIELDS
                or not {'symbol','interval'} <= set(context)
                or any(not isinstance(context[k],str) or not context[k] for k in ('symbol','interval'))
                or not isinstance(entries,list) or not 1 <= len(entries) <= MAX_QUERIES):
            raise InvalidIndicatorQuery()
        keys = [e.get('query_id') if isinstance(e,dict) else None for e in entries]
        if any(not isinstance(k,str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',k) for k in keys) or len(keys)!=len(set(keys)):
            raise InvalidIndicatorQuery()
        deadline = self.context.monotonic()+2
        snapshot, data = self.context.read(workspace_id, **context, limit=1, _capture=True, _deadline=deadline)
        snapshot['_include_open'] = context.get('include_open',False)
        snapshot['_pagination_bound'] = context.get('expected_context_id') is not None
        cache = {}
        results = [self._evaluate(e,snapshot,data,deadline,cache) for e in entries]
        self.context.read(workspace_id, **{**context,'expected_context_id':snapshot['context_id']},limit=1,_deadline=deadline)
        result = dict(schema_version=RESPONSE_SCHEMA,calculation_version=VERSION,context_id=snapshot['context_id'],
                      server_utc=snapshot['server_utc'],market=snapshot['market'],data_identity=snapshot['data_identity'],
                      readiness=snapshot['derived']['readiness'],indicator_settings_revision=snapshot['indicators']['revision'],
                      results=results,summary=dict(succeeded=sum(r['state']=='READY' for r in results),failed=sum(r['state']!='READY' for r in results)),
                      order_authority=False)
        if len(canonical(result).encode())>MAX_OUTPUT_BYTES: raise IndicatorOutputLimit()
        if self.context.monotonic()>deadline: raise ContextReadLimit()
        return result
