"""Sampled live-bar alerts. Higher timeframes remain confirmed, as of source time."""
from decimal import Decimal
import hashlib
import json
from .market_data import INTERVALS, SOURCE, bucket
from .alert_timeframes import intervals
from .alert_conditions import evaluate_all


def live_sample(definition, contexts):
    base = contexts.get(definition['interval']) or {}
    rows = base.get('rows', [])
    if not rows:
        return None
    stamp, revision = base.get('event_time'), base.get('data_revision')
    if type(stamp) is not int or stamp <= 0 or type(revision) is not int or revision <= 0:
        return None
    last = rows[-1]
    end = (last['time'] + INTERVALS[definition['interval']]//1000)*1000
    if stamp < last['time']*1000 or stamp > end+5000 or not last.get('closed') and stamp >= end:
        return None
    cutoff = min(stamp, end)
    aligned, epochs = {}, {}
    for interval in intervals(definition):
        c = contexts.get(interval) or {}
        identity = dict(source=SOURCE, environment='live_public', product='USD-M',
                        price_type='LAST_PRICE', symbol=definition['symbol'], interval=interval)
        if (c.get('transport_state') != 'LIVE' or c.get('timing', {}).get('state') != 'FRESH'
                or c.get('quality', {}).get('state') != 'OK' or c.get('identity') != identity
                or not c.get('stream_epoch')):
            return None
        step = INTERVALS[interval]//1000
        if interval == definition['interval']:
            sample = rows
        else:
            sample = [r for r in c.get('rows', []) if r.get('closed') and (r['time']+step)*1000 <= cutoff]
            expected = bucket(cutoff, interval)//1000-step
            if sample and sample[-1]['time'] != expected:
                return {'waiting': True}
        if len(sample) < 2:
            return None
        for i, row in enumerate(sample):
            close = Decimal(row['exact']['close'])
            if (row.get('exact', {}).get('state') != 'VERIFIED' or not close.is_finite() or close <= 0
                    or bucket(row['time']*1000, interval) != row['time']*1000
                    or row.get('close_time') != (row['time']+step)*1000-1
                    or i < len(sample)-1 and not row.get('closed')
                    or i and row['time']-sample[i-1]['time'] != step):
                return None
        aligned[interval] = sample
        epochs[interval] = c['stream_epoch']
    epoch = hashlib.sha256(json.dumps(epochs, sort_keys=True).encode()).hexdigest()
    token = hashlib.sha256(json.dumps([epoch, revision, stamp, {k:v[-1]['time'] for k,v in aligned.items()}], sort_keys=True).encode()).hexdigest()
    return dict(rows=rows, aligned=aligned, epoch=epoch, token=token, stamp=stamp, revision=revision)


def step(definition, contexts, state, boot):
    """Mutate a transaction-owned checkpoint; return an event decision or None."""
    try:
        sample = live_sample(definition, contexts)
    except (KeyError, ValueError, TypeError, ArithmeticError):
        sample = None
    if sample is None:
        state.update(readiness='WAITING_DATA', reseed=True)
        return None
    if sample.get('waiting'):
        state.update(readiness='WAITING_ALIGNMENT')
        return None
    rows = sample['rows']
    latest, stamp = rows[-1]['time'], sample['stamp']
    seed = (state.get('boot') != boot or state.get('epoch') != sample['epoch'] or state.get('reseed')
            or stamp-state.get('sample_time', stamp) > 20000
            or latest-state.get('last_time', latest) > INTERVALS[definition['interval']]//1000)
    if not seed and (stamp < state['sample_time'] or sample['revision'] < state['sample_revision'] or latest < state['last_time']):
        return None
    if not seed and sample['token'] == state.get('sample_token'):
        return None
    state.update(boot=boot, epoch=sample['epoch'], reseed=False, last_time=latest,
                 sample_time=stamp, sample_revision=sample['revision'], sample_token=sample['token'])
    try:
        hit, checks = evaluate_all(definition, rows, sample['aligned'])
    except (KeyError, ValueError, TypeError, ArithmeticError):
        state.update(readiness='WAITING_CALCULATION')
        return None
    state['readiness'] = 'READY'
    if seed or not hit:
        return None
    frequency = definition['frequency']
    if frequency == 'bar' and state.get('fired_bar') == latest:
        return None
    if frequency == 'minute' and stamp-state.get('fired_time', -60000) < 60000:
        return None
    state.update(fired_bar=latest, fired_time=stamp)
    return dict(token=sample['token'], candle_time=latest, close=rows[-1]['exact']['close'],
                conditions=checks, observed_at=stamp, confirmed=bool(rows[-1].get('closed')),
                source_closes={k:v[-1]['time'] for k,v in sample['aligned'].items()})
