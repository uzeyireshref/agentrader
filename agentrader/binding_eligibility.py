"""P5 pure, point-in-time suitability. Never activates a binding or evaluates a rule."""
from contextlib import closing
import math
from decimal import Decimal

from .binding_catalog import catalog
from .chart_bindings import binding_hash, rule_definition
from .chart_clock import POLICY
from .chart_evidence import snapshot, digest, FIELDS
from .chart_precision import decimal_text
from .drawings.calculations import canonical_hash, verified_grid, CalculationBlocked
from .drawings.service import DrawingError
from .indicator_config import defaults_v4, validate_v4, series, multi_series
from .vwap import vwap_series
from .drawings.fibonacci import LEGACY_LEVELS, ratio_text
from .migrations import connect

STATES = ('BLOCKED', 'OBSERVE_ONLY', 'EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY')


def evaluate_binding(binding, *, owner, workspace_id, target, context, traceability):
    """All inputs are explicit. The HTTP adapter supplies server-owned evidence only.

    No I/O, time reads, mutations, activation, trigger evaluation or order authority.
    A result is valid only for the reported target/data revision and clock observation.
    """
    reasons = []
    checks = []
    def check(name, good, reason):
        checks.append({'name': name, 'passed': bool(good), 'reason': None if good else reason})
        if not good and reason not in reasons:
            reasons.append(reason)
    d = binding.get('definition', {}) if isinstance(binding, dict) else {}
    if not isinstance(d, dict):
        d = {}
    result = dict(schema='chart-binding-eligibility/1', state='BLOCKED', reasons=reasons,
                  checks=checks, binding_id=binding.get('binding_id') if isinstance(binding, dict) else None,
                  binding_revision=binding.get('revision') if isinstance(binding, dict) else None,
                  definition_hash=binding.get('definition_hash') if isinstance(binding, dict) else None,
                  market=d.get('market'), scale=d.get('scale'),
                  evaluated_data=None, activation='DISABLED', live_eligible=False,
                  validity_ms=0,
                  rule_evaluated=False, execute_rule=False, order_authority=False)
    try:
        check('definition', d.get('schema') == 'chart-binding-definition/1' and binding.get('definition_hash') == binding_hash(d), 'DEFINITION_HASH_MISMATCH')
        check('owner', bool(owner) and d.get('owner') == owner and d.get('workspace_id') == workspace_id == binding.get('workspace_id'), 'OWNER_WORKSPACE_MISMATCH')
        check('binding_state', binding.get('state') == 'DISABLED' and d.get('activation') == 'DISABLED', 'BINDING_STOPPED_OR_INVALID')
        check('authority', d.get('bot_capabilities') == dict(read_definition=True, write_target=False, edit_target=False, execute_rule=False, order_authority=False), 'AUTHORITY_CONTRACT_INVALID')
        t = d.get('target', {})
        check('target', isinstance(target, dict) and all(target.get(k) == t.get(k) for k in ('type', 'object_id', 'revision', 'kind', 'snapshot')) and target.get('deleted') is False, 'TARGET_REVISION_OR_CONTENT_MISMATCH')
        market = d.get('market', {})
        check('market_identity', all(market.get(k) == v for k, v in dict(source='binance_usdm_live_trade_price', environment='live_public', product='USD-M', price_type='LAST_PRICE').items()), 'MARKET_IDENTITY_UNPROVEN')
        check('scale', d.get('scale') == 'LINEAR', 'UNSUPPORTED_SCALE')
        grid = d.get('grid', {})
        try:
            times = list(verified_grid(grid.get('times'), market.get('interval')))
            good = grid.get('hash') == digest(dict(interval=market['interval'], times=times)) and grid.get('count') == len(times) and grid.get('first_time') == times[0] and grid.get('last_time') == times[-1]
            value = t.get('snapshot')
            content = canonical_hash(value, times=times, interval=market['interval'], scale=d.get('scale')) if t.get('type') == 'drawing' else digest(dict(schema='chart-indicator-binding-content/1', configuration=value, symbol=market['symbol'], interval=market['interval'], scale=d['scale']))
            good = good and content == t.get('content_hash')
        except (ValueError, KeyError, TypeError, CalculationBlocked):
            good = False
        check('reference_grid_content', good, 'REFERENCE_GRID_OR_CONTENT_INVALID')
        entry = traceability.get('targets', {}).get(str(t.get('type')) + ':' + str(t.get('kind')), {}) if isinstance(traceability, dict) else {}
        check('query_evidence', isinstance(traceability, dict) and traceability.get('state') == 'VERIFIED_TRACEABILITY' and bool(entry) and d.get('query_evidence') == {**entry, 'descriptor': d.get('query_evidence', {}).get('descriptor'), 'hash': digest(entry)}, 'QUERY_EVIDENCE_STALE_OR_MISSING')
        q = d.get('query', {})
        descriptor = next((v for v in entry.get('queries', []) if v['operation'] == q.get('operation') and v['output'] == q.get('output')), None)
        check('query_kind', descriptor is not None and d.get('query_evidence', {}).get('descriptor') == descriptor, 'UNSUPPORTED_KIND_OR_QUERY')
        try:
            ratio = q.get('ratio')
            good = set(q) == {'operation', 'output', 'ratio'} and (ratio_text(ratio) == ratio and ratio in t['snapshot'].get('levels', LEGACY_LEVELS) if t.get('kind') in ('fibonacci','fibonacci_extension') else ratio is None)
        except (ValueError, TypeError, KeyError):
            good = False
        check('query_parameters', good, 'UNSUPPORTED_QUERY_PARAMETERS')
        try:
            rule_definition(d.get('rule'), descriptor['rules'] if descriptor else [])
            good = True
        except (ValueError, TypeError, KeyError, DrawingError):
            good = False
        check('rule', good, 'UNSUPPORTED_RULE_DEFINITION')
        if t.get('type') == 'indicator':
            try:
                items = defaults_v4()
                i = next(i for i, v in enumerate(items) if v['indicator_id'] == t['object_id'])
                items[i] = t['snapshot']
                validate_v4(items)
                good = True
            except (ValueError, KeyError, TypeError, StopIteration, DrawingError):
                good = False
            check('formula', good, 'UNSUPPORTED_FORMULA_VERSION')
        c = context if isinstance(context, dict) else {}
        check('server_feed', bool(c), 'SERVER_FEED_UNAVAILABLE')
        check('server_transport', c.get('transport_state') == 'LIVE', 'SERVER_TRANSPORT_NOT_LIVE')
        check('context_identity', c.get('identity') == market, 'SOURCE_CONTEXT_MISMATCH')
        rows, proof, timing = c.get('rows'), c.get('data_proof'), c.get('timing')
        check('data_proof_present', isinstance(proof, dict), 'DATA_PROOF_MISSING')
        good = False
        closed = []
        if isinstance(rows, list) and isinstance(proof, dict):
            try:
                rebuilt = snapshot(rows, c.get('market'), c.get('quality', {}), symbol=market['symbol'], interval=market['interval'], epoch=c['stream_epoch'], generation=c['generation'], revision=c['data_revision']).view()
                good = rebuilt == proof and proof['state'] == 'VERIFIED' and isinstance(c['stream_epoch'], str) and bool(c['stream_epoch']) and type(c['generation']) is int and c['generation'] > 0 and type(c['data_revision']) is int and c['data_revision'] > 0
                closed = [r for r in rows if r['closed']]
                verified_grid([r['time'] for r in closed], market['interval'])
            except (ValueError, TypeError, KeyError, CalculationBlocked, OverflowError):
                good = False
        check('data_integrity_grid', good, 'DATA_PROOF_OR_GRID_INVALID')
        check('closed_reference', len(closed) >= 2, 'CLOSED_DATA_REFERENCE_MISSING')
        try:
            exact = c['market']['exact']
            good = exact['schema'] == 'chart-exact-decimal/1' and exact['state'] == 'VERIFIED' and exact['provenance'] == 'UPSTREAM_DECIMAL_TEXT' and decimal_text(exact['tick_size'], positive=True) == decimal_text(str(c['market']['tick_size']), positive=True)
            for row in rows:
                e = row['exact']
                good = good and e['schema'] == 'chart-exact-decimal/1' and e['state'] == 'VERIFIED' and e['provenance'] == 'UPSTREAM_DECIMAL_TEXT'
                good = good and all(float(decimal_text(e[k], positive=k in ('open','high','low','close'))) == row[k] for k in FIELDS)
                op,hi,lo,cl = (Decimal(e[k]) for k in ('open','high','low','close'))
                good = good and lo <= min(op,cl) <= max(op,cl) <= hi
                good = good and ((Decimal(e['volume']) == 0 and Decimal(e['quote_volume']) == 0) or (Decimal(e['volume']) > 0 and Decimal(e['quote_volume']) > 0))
        except (KeyError, TypeError, ValueError):
            good = False
        check('native_precision', good, 'NATIVE_PRECISION_UNPROVEN')
        def duration(key, maximum):
            v = timing.get(key) if isinstance(timing, dict) else None
            return type(v) in (int, float) and math.isfinite(v) and 0 <= v <= maximum
        good = isinstance(timing, dict) and timing.get('schema') == 'chart-time-proof/1' and timing.get('policy') == POLICY and timing.get('state') == 'FRESH' and timing.get('reason') is None
        check('clock', good, 'CLOCK_UNTRUSTED')
        check('transport_age', duration('data_age_ms', POLICY['max_transport_age_ms']), 'TRANSPORT_STALE_OR_UNPROVEN')
        check('upstream_age', duration('upstream_age_upper_ms', POLICY['max_upstream_age_ms']), 'UPSTREAM_STALE_OR_UNPROVEN')
        check('clock_uncertainty', duration('uncertainty_ms', POLICY['max_uncertainty_ms']), 'CLOCK_UNCERTAINTY_UNPROVEN')
        event = timing.get('upstream_event_time') if isinstance(timing, dict) else None
        check('closed_time', type(event) is int and bool(closed) and duration('uncertainty_ms', POLICY['max_uncertainty_ms']) and closed[-1]['close_time'] < event - timing['uncertainty_ms'], 'CLOSED_TIME_UNPROVEN')
        check('event_grid', type(event) is int and isinstance(rows,list) and bool(rows) and rows[-1]['time']*1000 <= event <= rows[-1]['close_time'] + POLICY['max_upstream_age_ms'], 'EVENT_GRID_MISMATCH')
        if t.get('type') == 'drawing' and closed:
            try:
                canonical_hash(t['snapshot'], times=[r['time'] for r in closed], interval=market['interval'], scale=d['scale'])
                good = True
            except (KeyError, TypeError, ValueError, CalculationBlocked):
                good = False
            check('current_geometry_grid', good, 'TARGET_OUTSIDE_VERIFIED_GRID')
        if t.get('type') == 'indicator':
            # Display formulas have no canonical signal proof; do not promote them.
            check('warmup', isinstance(proof, dict) and proof.get('warmup_available_closed_bars', 0) >= max(2, t.get('snapshot', {}).get('period', 2)), 'INSUFFICIENT_WARMUP')
            try:
                config = t['snapshot']
                if 'VWAP' in t['kind']:
                    points = vwap_series(closed, config, market['interval'], market['symbol'])['points']
                elif t['kind'] in ('MACD','BB'):
                    # Shifted BB may draw beyond its causal candle; never claim current output.
                    points = [] if t['kind']=='BB' and config['params']['offset'] != 0 else multi_series(closed, config, market['interval'])[q['output']]
                else:
                    points = series(closed, config, market['interval'])
                good = bool(points) and bool(closed) and points[-1]['time'] == closed[-1]['time'] and math.isfinite(points[-1]['value'])
            except (ValueError, TypeError, KeyError, DrawingError, OverflowError):
                good = False
            check('display_output', good, 'DISPLAY_OUTPUT_UNAVAILABLE_OR_SHIFTED')
            result['limitations'] = ['DISPLAY_FORMULA_NOT_CANONICAL_SIGNAL', 'LOADED_HISTORY_SEED_OR_EXPLICIT_SESSION_ANCHOR']
        if isinstance(proof, dict):
            result['evaluated_data'] = {k: proof.get(k) for k in ('snapshot_hash', 'grid_hash', 'stream_epoch', 'generation', 'data_revision', 'last_time')}
        if not reasons:
            result['state'] = 'OBSERVE_ONLY' if d['rule']['kind'] == 'observe' or descriptor['output_type'] != 'PRICE' else 'EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY'
            result['validity_ms'] = min(POLICY['max_transport_age_ms']-timing['data_age_ms'], POLICY['max_upstream_age_ms']-timing['upstream_age_upper_ms'])
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        check('structure', False, 'MALFORMED_EVIDENCE')
    return result


def inspect_binding(service, hub, workspace_id, binding_id):
    """Read current binding and target from one DB snapshot; never write or acquire feeds."""
    with closing(connect(service.database)) as db:
        db.execute('BEGIN')
        b = service._view_binding(service._binding(db, workspace_id, binding_id), True)
        t = b['definition']['target']
        target = None
        try:
            kind, _, value = service._target(db, workspace_id, {k: t[k] for k in ('type','object_id','revision')}, b['definition']['market']['symbol'])
            target = {**{k:t[k] for k in ('type','object_id','revision')}, 'kind':kind, 'snapshot':value, 'deleted':False}
        except DrawingError:
            pass
    market = b['definition']['market']
    context = hub.binding_context(market['symbol'], market['interval'])
    return evaluate_binding(b, owner=service.owner, workspace_id=workspace_id, target=target, context=context, traceability=catalog())
