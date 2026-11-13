"""P3 immutable data evidence; never a clock, rule or execution permission."""
from dataclasses import dataclass
import hashlib
import json
import math
import struct

from .chart_precision import precision_summary
from .market_data import INTERVALS, SOURCE, bucket

SCHEMA = 'chart-data-proof/1'
PAYLOAD_SCHEMA = 'chart-data-snapshot/1'
FIELDS = ('open', 'high', 'low', 'close', 'volume', 'quote_volume')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def chart_number(value):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError('Invalid chart number')
    return struct.pack('>d', float(value) if value else 0.).hex()


def canonical_row(row):
    return {'time': row['time'], 'close_time': row['close_time'], 'closed': row['closed'],
            'chart_values': [chart_number(row[k]) for k in FIELDS], 'exact': row.get('exact')}


def grid_info(rows, interval):
    step = INTERVALS[interval] // 1000
    valid = bool(rows) and len(rows) <= 499
    missing = 0
    previous = None
    for row in rows:
        t = row.get('time')
        good = (type(t) is int and 0 < t <= 32503680000 and bucket(t*1000, interval) == t*1000
                and type(row.get('closed')) is bool
                and type(row.get('close_time')) is int and row['close_time'] == t*1000 + step*1000 - 1)
        numbers = [row.get(k) for k in FIELDS]
        good = good and all(type(v) in (int, float) and math.isfinite(v) for v in numbers)
        if good:
            op, hi, lo, cl, volume, quote = numbers
            good = min(op, hi, lo, cl) > 0 and lo <= min(op, cl) and hi >= max(op, cl) and min(volume, quote) >= 0
        if not good or previous is not None and t <= previous:
            valid = False
        if good and previous is not None and t > previous:
            missing += max(0, (t-previous)//step-1)
        previous = t if good else None
    if any(not row.get('closed') for row in rows[:-1]):
        valid = False
    available = 0
    closed = [row for row in rows if row.get('closed')]
    # Count only the closed suffix immediately preceding the optional current bar.
    end = len(rows)-1
    if end >= 0 and not rows[end].get('closed'):
        end -= 1
    while end >= 0 and rows[end].get('closed'):
        if available and rows[end+1]['time']-rows[end]['time'] != step:
            break
        available += 1
        end -= 1
    return {'valid': bool(valid), 'missing_bars': missing, 'bar_count': len(rows),
            'closed_count': len(closed), 'warmup_available_closed_bars': available}


@dataclass(frozen=True)
class DataEvidence:
    payload_json: str
    proof_json: str

    def view(self):
        return json.loads(self.proof_json)

    def payload(self):
        return json.loads(self.payload_json)


def snapshot(rows, market, quality, *, symbol, interval, epoch, generation, revision):
    grid = grid_info(rows, interval)
    reasons = []
    if not rows: reasons.append('EMPTY_SNAPSHOT')
    if not grid['valid']: reasons.append('INVALID_GRID')
    if grid['missing_bars']: reasons.append('GRID_GAP')
    if quality.get('state') != 'OK' or type(quality.get('missing_bars')) is not int or quality['missing_bars'] != 0:
        reasons.append('QUALITY_UNPROVEN')
    if precision_summary(rows, market)['state'] != 'VERIFIED': reasons.append('PRICE_PRECISION_UNPROVEN')
    if not isinstance(market, dict) or market.get('symbol') != symbol: reasons.append('MARKET_IDENTITY_UNPROVEN')
    payload = {'schema': PAYLOAD_SCHEMA, 'source': SOURCE, 'environment': 'live_public',
               'product': 'USD-M', 'price_type': 'LAST_PRICE', 'symbol': symbol, 'interval': interval,
               'stream_epoch': epoch, 'generation': generation, 'data_revision': revision,
               'market': market, 'quality': quality, 'rows': [canonical_row(r) for r in rows]}
    proof = {'schema': SCHEMA, 'stream_epoch': epoch, 'generation': generation,
             'data_revision': revision, 'state': 'BLOCKED' if reasons else 'VERIFIED',
             'blocked_reasons': reasons, 'snapshot_hash': digest(payload),
             'grid_hash': digest({'interval': interval, 'times': [r['time'] for r in rows]}),
             'first_time': rows[0]['time'] if rows else None, 'last_time': rows[-1]['time'] if rows else None,
             **grid, 'live_eligible': False, 'order_authority': False}
    return DataEvidence(canonical(payload), canonical(proof))


def require_warmup(evidence, required):
    proof = evidence.view()
    if type(required) is not int or required < 1:
        return {'state': 'BLOCKED', 'reason': 'WARMUP_REQUIREMENT_UNSPECIFIED'}
    if proof['state'] != 'VERIFIED':
        return {'state': 'BLOCKED', 'reason': proof['blocked_reasons'][0]}
    if proof['warmup_available_closed_bars'] < required:
        return {'state': 'BLOCKED', 'reason': 'INSUFFICIENT_WARMUP'}
    return {'state': 'DATA_PROOF_VERIFIED_NOT_ELIGIBILITY', 'live_eligible': False, 'order_authority': False}
