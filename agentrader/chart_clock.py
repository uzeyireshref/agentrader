"""P2 process-local clock evidence; exported durations never expose producer monotonic time."""
from collections import OrderedDict
from dataclasses import dataclass
import math
import threading
import time
import uuid

POLICY = {'schema': 'chart-time-policy/1', 'max_transport_age_ms': 10000,
          'max_upstream_age_ms': 10000, 'max_uncertainty_ms': 1000,
          'wall_jump_ms': 250, 'long_gap_ms': 20000, 'sample_ttl_ms': 300000,
          'drift_ppm': 100}
_SAMPLES = OrderedDict()
_LOCK = threading.RLock()


@dataclass(frozen=True)
class ClockSample:
    wall_ms: float
    mono_ms: float
    server_ms: float
    uncertainty_ms: float


def measure_time(client, wall=time.time, monotonic=time.monotonic):
    w0, m0 = wall() * 1000, monotonic() * 1000
    stamp = client.get('/fapi/v1/time')['serverTime']
    w1, m1 = wall() * 1000, monotonic() * 1000
    if type(stamp) is not int or stamp <= 0:
        raise ValueError('Invalid server clock')
    rtt = m1 - m0
    valid = all(math.isfinite(v) for v in (w0, w1, m0, m1)) and rtt >= 0 and abs((w1-w0)-rtt) <= POLICY['wall_jump_ms']
    uncertainty = rtt / 2 + 1
    valid = valid and uncertainty <= POLICY['max_uncertainty_ms']
    sample_id = uuid.uuid4().hex
    if valid:
        with _LOCK:
            _SAMPLES[sample_id] = ClockSample(w1, m1, stamp + rtt / 2, uncertainty)
            while len(_SAMPLES) > 128:
                _SAMPLES.popitem(last=False)
    return stamp, {'schema': 'chart-clock-sample/1', 'sample_id': sample_id,
                   'state': 'MEASURED' if valid else 'UNTRUSTED',
                   'offset_ms': round(stamp + rtt / 2 - w1, 3) if valid else None,
                   'rtt_ms': round(rtt, 3) if math.isfinite(rtt) else None,
                   'uncertainty_ms': round(uncertainty, 3) if math.isfinite(uncertainty) else None}


class StreamTiming:
    def __init__(self, wall=time.time, monotonic=time.monotonic):
        self.wall, self.monotonic = wall, monotonic
        self.sample = None
        self.last_mono = self.event_time = None
        self.needs_snapshot = True
        self.enforced = False

    def seed(self, evidence):
        sample_id = (evidence.get('sample_id') if isinstance(evidence, dict)
                     and evidence.get('schema') == 'chart-clock-sample/1'
                     and evidence.get('state') == 'MEASURED' else None)
        if not isinstance(sample_id, str):
            sample_id = None
        with _LOCK:
            self.sample = _SAMPLES.get(sample_id)
        self.last_mono = self.event_time = None
        self.needs_snapshot = False
        self.enforced = self.clock_state()[0] is None

    def clock_state(self):
        if self.sample is None:
            return 'CLOCK_UNTRUSTED', None, None
        now, wall = self.monotonic()*1000, self.wall()*1000
        age = now-self.sample.mono_ms
        if not all(math.isfinite(v) for v in (now, wall, age)) or age < 0:
            return 'CLOCK_UNTRUSTED', None, None
        uncertainty = self.sample.uncertainty_ms + age * POLICY['drift_ppm'] / 1000000
        if (age > POLICY['sample_ttl_ms'] or uncertainty > POLICY['max_uncertainty_ms']
                or abs((wall-self.sample.wall_ms)-age) > POLICY['wall_jump_ms']):
            return 'CLOCK_UNTRUSTED', None, None
        return None, self.sample.server_ms+age, uncertainty

    def observe(self, stamp):
        error, server, uncertainty = self.clock_state()
        now = self.monotonic()*1000
        if not error and self.last_mono is not None and now-self.last_mono > POLICY['long_gap_ms']:
            self.needs_snapshot = True
        if error:
            self.needs_snapshot = True
            return error
        if self.needs_snapshot:
            return 'SNAPSHOT_REQUIRED'
        if type(stamp) is not int or stamp > server+uncertainty:
            self.needs_snapshot = True
            return 'FUTURE_UPSTREAM_TIME'
        if server-stamp+uncertainty > POLICY['max_upstream_age_ms']:
            self.needs_snapshot = True
            return 'UPSTREAM_STALE'
        self.last_mono, self.event_time = now, stamp
        return None

    def proof(self):
        error, server, uncertainty = self.clock_state()
        if error:
            self.needs_snapshot = True
        age = None if self.last_mono is None else max(0, self.monotonic()*1000-self.last_mono)
        upstream = None if error or self.event_time is None else max(0, server-self.event_time+uncertainty)
        reason = error or ('SNAPSHOT_REQUIRED' if self.needs_snapshot else None)
        if not reason:
            if age is None:
                reason = 'AWAITING_UPSTREAM'
            elif age > POLICY['long_gap_ms']:
                self.needs_snapshot = True
                reason = 'SNAPSHOT_REQUIRED'
            elif age > POLICY['max_transport_age_ms'] or upstream > POLICY['max_upstream_age_ms']:
                reason = 'UPSTREAM_STALE'
        return {'schema': 'chart-time-proof/1', 'policy': dict(POLICY),
                'state': 'BLOCKED' if reason else 'FRESH', 'reason': reason,
                'data_age_ms': age, 'upstream_age_upper_ms': upstream,
                'uncertainty_ms': uncertainty, 'upstream_event_time': self.event_time,
                'live_eligible': False, 'order_authority': False}
