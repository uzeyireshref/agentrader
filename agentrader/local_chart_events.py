"""P6 replay-only durable event/intent bridge. Fixed SQLite fake sink, no live adapter."""
from contextlib import closing
from dataclasses import dataclass
from fractions import Fraction
import json
import re
import time

from .binding_catalog import catalog
from .binding_eligibility import evaluate_binding
from .chart_bindings import BindingService, binding_hash
from .chart_clock import POLICY
from .chart_evidence import canonical, digest
from .drawings.calculations import query, encoded, CalculationBlocked
from .drawings.service import DrawingError, DrawingConflict, identifier
from .migrations import connect


def replay_namespace(value):
    if not isinstance(value, str) or not re.fullmatch(r'replay:[A-Za-z0-9_-]{1,64}', value):
        raise LocalEventError('REPLAY_NAMESPACE_REQUIRED')
    return value


class LocalEventError(DrawingError):
    def __init__(self, reason):
        self.code = reason
        super().__init__(reason)


def target_view(service, db, binding):
    t = binding['definition']['target']
    try:
        kind, _, value = service._target(db, binding['workspace_id'], {k:t[k] for k in ('type','object_id','revision')}, binding['definition']['market']['symbol'])
        return {**{k:t[k] for k in ('type','object_id','revision')}, 'kind':kind, 'snapshot':value, 'deleted':False}
    except DrawingError:
        return None


def closed_candidate(binding, context):
    """Versioned explicit-rearm replay profile; exact rationals, closed bars only.

    TOUCH uses the current candle range and a previous close outside the band.
    APPROACH enters its band while getting closer and excludes an exact-level touch.
    CROSS moves strictly past the level from the opposite side (zero may be prior).
    No intrabar path, vendor parity, cooldown or automatic rearm is inferred.
    """
    d = binding['definition'];rule = d['rule'];q = d['query']
    if d['target']['type'] != 'drawing' or rule['kind'] == 'observe':
        return None
    rows = [r for r in context['rows'] if r['closed']]
    if len(rows) < 2:
        return None
    previous, current = rows[-2:]
    def level(row):
        v = query(d['target']['snapshot'], q['operation'], time=row['time'], ratio=q['ratio'], times=[r['time'] for r in rows], interval=d['market']['interval'], scale=d['scale'])['value']
        if q['operation'] == 'boundsAt':v = v[q['output']]
        return Fraction(int(v['numerator']), int(v['denominator']))
    old, now = level(previous), level(current)
    prior = Fraction(previous['exact']['close'])-old
    delta = Fraction(current['exact']['close'])-now
    low, high = (Fraction(current['exact'][k])-now for k in ('low','high'))
    tolerance = Fraction(rule['tolerance'])
    direction = 'ABOVE' if prior < 0 else 'BELOW' if prior > 0 else 'ABOVE' if delta > 0 else 'BELOW'
    allowed = rule['direction'] in ('ANY', direction)
    if rule['kind'] == 'touch':hit = low <= tolerance and high >= -tolerance and abs(prior) > tolerance
    elif rule['kind'] == 'approach':hit = prior*delta > 0 and 0 < abs(delta) <= tolerance < abs(prior) and abs(delta) < abs(prior) and not low <= 0 <= high
    elif rule['kind'] == 'close_cross':hit = prior <= 0 < delta or prior >= 0 > delta
    else:raise LocalEventError('UNSUPPORTED_LOCAL_RULE')
    if not hit or not allowed:return None
    kind = {'touch':'TOUCH','approach':'APPROACH','close_cross':'CLOSE_CROSS'}[rule['kind']]
    return dict(schema='chart-local-domain-event/1', profile='CLOSED_EXPLICIT_REARM/1',
                binding_id=binding['binding_id'], binding_revision=binding['revision'],
                definition_hash=binding['definition_hash'], target={k:d['target'][k] for k in ('type','object_id','revision','kind')},
                market=d['market'], query=q, rule=rule, candle_time=current['time'],
                prior_candle_time=previous['time'], kind=kind, direction=direction, episode=1,
                phase_before='ARMED', phase_after={'TOUCH':'TOUCH_LATCHED','APPROACH':'APPROACH_NOTIFIED','CLOSE_CROSS':'CROSS_LATCHED'}[kind],
                level=encoded(now), previous_level=encoded(old), closed_price=current['exact']['close'])


@dataclass(frozen=True)
class PreparedLocalEvent:
    namespace: str
    workspace_id: str
    binding_id: str
    binding_revision: int
    definition_hash: str
    context_json: str
    captured_mono: float
    captured_wall: float


class LocalChartEvents:
    def __init__(self, database, owner, *, monotonic=time.monotonic, wall=time.time):
        self.database, self.owner = database, owner
        self.monotonic, self.wall = monotonic, wall
        self.bindings = BindingService(database, owner)

    def prepare(self, workspace_id, binding_id, namespace, context):
        replay_namespace(namespace)
        b = self.bindings.show(workspace_id,binding_id)
        # The explicit internal replay caller owns the evidence. No HTTP ingest endpoint.
        return PreparedLocalEvent(namespace,workspace_id,binding_id,b['revision'],b['definition_hash'],canonical(context),self.monotonic(),self.wall())

    def _current(self, db, workspace_id, binding_id, revision, definition_hash):
        b = self.bindings._view_binding(self.bindings._binding(db,workspace_id,binding_id),True)
        if b['revision'] != revision or b['definition_hash'] != definition_hash or b['state'] != 'DISABLED':
            raise LocalEventError('REVISION_CHANGED')
        if target_view(self.bindings,db,b) is None:
            raise LocalEventError('REVISION_CHANGED')
        return b

    def commit(self, prepared, *, _fault=None):
        if not isinstance(prepared,PreparedLocalEvent):raise LocalEventError('INVALID_PREPARED_EVENT')
        p = prepared;replay_namespace(p.namespace)
        identifier(p.workspace_id);identifier(p.binding_id)
        with closing(connect(self.database)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            b = self._current(db,p.workspace_id,p.binding_id,p.binding_revision,p.definition_hash)
            c = json.loads(p.context_json)
            elapsed = (self.monotonic()-p.captured_mono)*1000
            wall_elapsed = (self.wall()-p.captured_wall)*1000
            if elapsed < 0 or abs(wall_elapsed-elapsed)>POLICY['wall_jump_ms']:
                raise LocalEventError('CLOCK_UNTRUSTED')
            timing = c.get('timing') if isinstance(c,dict) else None
            if isinstance(timing,dict):
                for key in ('data_age_ms','upstream_age_upper_ms'):
                    if type(timing.get(key)) in (int,float):timing[key] += elapsed
                if type(timing.get('uncertainty_ms')) in (int,float):timing['uncertainty_ms'] += elapsed*POLICY['drift_ppm']/1000000
            suitability = evaluate_binding(b,owner=self.owner,workspace_id=p.workspace_id,target=target_view(self.bindings,db,b),context=c,traceability=catalog())
            if suitability['state'] != 'EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY':
                return dict(state='BLOCKED',reasons=suitability['reasons'] or ['OBSERVE_ONLY'],created=False,order_authority=False)
            try:candidate = closed_candidate(b,c)
            except (CalculationBlocked,ValueError,KeyError,TypeError) as exc:
                return dict(state='BLOCKED',reasons=[getattr(exc,'code','LOCAL_QUERY_UNAVAILABLE')],created=False,order_authority=False)
            if candidate is None:return dict(state='NO_EVENT',reasons=['RULE_NOT_MATCHED'],created=False,order_authority=False)
            identity = {k:candidate[k] for k in ('schema','profile','binding_id','binding_revision','definition_hash','target','market','query','rule','candle_time','kind','direction','episode')}
            domain_id = binding_hash(dict(owner=self.owner,workspace_id=p.workspace_id,event=identity))
            # Proof epoch, request/transport IDs and snapshot hash are deliberately absent.
            semantic = domain_id
            old = db.execute('SELECT event_id FROM app_chart_local_events WHERE owner=? AND workspace_id=? AND namespace=? AND semantic_key=?',(self.owner,p.workspace_id,p.namespace,semantic)).fetchone()
            if old:return dict(state='DUPLICATE',reason='SEMANTIC_EVENT_ALREADY_RECORDED',created=False,event_id=old['event_id'],domain_event_id=domain_id,order_authority=False)
            phase = db.execute('SELECT phase FROM app_chart_local_phases WHERE owner=? AND workspace_id=? AND namespace=? AND binding_id=? AND binding_revision=?',(self.owner,p.workspace_id,p.namespace,p.binding_id,p.binding_revision)).fetchone()
            if phase:return dict(state='LATCHED',reason='EXPLICIT_REBIND_REQUIRED',phase=phase['phase'],created=False,order_authority=False)
            event_id = digest(dict(namespace=p.namespace,domain_event_id=domain_id))
            body = dict(candidate,domain_event_id=domain_id,namespace=p.namespace,order_authority=False)
            evidence = dict(schema='chart-local-event-evidence/1',definition=b['definition'],context=c,eligibility=suitability,context_hash=binding_hash(c),cross_database_atomicity=False)
            db.execute('INSERT INTO app_chart_local_events VALUES (?,?,?,?,?,?,?,?)',(self.owner,p.workspace_id,p.namespace,semantic,event_id,canonical(body),canonical(evidence),self.wall()))
            if _fault:_fault('after_event_insert')
            intent = dict(schema='chart-local-intent/1',event_id=event_id,binding_id=p.binding_id,binding_revision=p.binding_revision,definition_hash=p.definition_hash,sink='SQLITE_FAKE_ONLY',namespace=p.namespace,order_authority=False)
            db.execute('INSERT INTO app_chart_local_intents VALUES (?,?,?,?,?,?,?)',(event_id,self.owner,p.workspace_id,p.namespace,'PENDING_FAKE',0,canonical(intent)))
            db.execute('INSERT INTO app_chart_local_phases VALUES (?,?,?,?,?,?,?)',(self.owner,p.workspace_id,p.namespace,p.binding_id,p.binding_revision,candidate['phase_after'],event_id))
            if _fault:_fault('before_event_commit')
            db.commit()
            if _fault:_fault('after_event_commit')
            return dict(state='RECORDED_LOCAL',created=True,event_id=event_id,domain_event_id=domain_id,phase=candidate['phase_after'],order_authority=False)

    def list_events(self, workspace_id, namespace, limit=50):
        identifier(workspace_id);replay_namespace(namespace)
        if type(limit) is not int or not 1<=limit<=100:raise LocalEventError('INVALID_EVENT_LIMIT')
        with closing(connect(self.database)) as db:
            rows = db.execute('SELECT e.*,i.state AS intent_state,i.attempts FROM app_chart_local_events e JOIN app_chart_local_intents i ON e.event_id=i.event_id WHERE e.owner=? AND e.workspace_id=? AND e.namespace=? ORDER BY e.created_at DESC,e.event_id LIMIT ?',(self.owner,workspace_id,namespace,limit)).fetchall()
            items = [dict(event_id=r['event_id'],event=json.loads(r['body']),intent_state=r['intent_state'],attempts=r['attempts'],created_at=r['created_at'],evidence_hash=digest(json.loads(r['evidence']))) for r in rows]
        return dict(schema='chart-local-event-list/1',namespace=namespace,events=items,sink='SQLITE_FAKE_ONLY',activation='DISABLED',order_authority=False)

    def _fake_send(self, event_id):
        """Fixed sink. Revision check and fake receipt creation share a DB transaction."""
        with closing(connect(self.database)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM app_chart_local_intents WHERE event_id=? AND owner=?',(event_id,self.owner)).fetchone()
            if not row or row['state']!='IN_FLIGHT_FAKE':return 'DELIVERY_UNKNOWN'
            intent = json.loads(row['body'])
            try:self._current(db,row['workspace_id'],intent['binding_id'],intent['binding_revision'],intent['definition_hash'])
            except DrawingError:return 'CANCELED_SUPERSEDED'
            receipt = dict(schema='chart-fake-receipt/1',event_id=event_id,namespace=row['namespace'],external_messages=0,order_authority=False)
            db.execute('INSERT OR IGNORE INTO app_chart_fake_receipts VALUES (?,?,?,?,?)',(event_id,self.owner,row['workspace_id'],row['namespace'],canonical(receipt)))
            return 'DELIVERED_FAKE'

    def deliver_one(self, workspace_id, namespace, *, _fault=None):
        """Explicit test call only; no thread, timer, external adapter or HTTP action."""
        replay_namespace(namespace);identifier(workspace_id)
        with closing(connect(self.database)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM app_chart_local_intents WHERE owner=? AND workspace_id=? AND namespace=? AND state='PENDING_FAKE' ORDER BY event_id LIMIT 1",(self.owner,workspace_id,namespace)).fetchone()
            if not row:return dict(state='EMPTY',order_authority=False)
            event_id = row['event_id']
            db.execute("UPDATE app_chart_local_intents SET state='IN_FLIGHT_FAKE',attempts=attempts+1 WHERE event_id=?",(event_id,))
        if _fault:_fault('after_delivery_claim')
        try:
            state = self._fake_send(event_id)
            if _fault:_fault('after_fake_send')
        except Exception:
            state = 'DELIVERY_UNKNOWN'
        with closing(connect(self.database)) as db, db:
            db.execute("UPDATE app_chart_local_intents SET state=? WHERE event_id=? AND owner=? AND state='IN_FLIGHT_FAKE'",(state,event_id,self.owner))
            current = db.execute('SELECT state FROM app_chart_local_intents WHERE event_id=? AND owner=?',(event_id,self.owner)).fetchone()['state']
        return dict(state=current,event_id=event_id,order_authority=False)

    def recover_unknown(self, workspace_id, namespace):
        """Offline recovery leaves ambiguous delivery explicit; never retries it."""
        replay_namespace(namespace);identifier(workspace_id)
        with closing(connect(self.database)) as db, db:
            n = db.execute("UPDATE app_chart_local_intents SET state='DELIVERY_UNKNOWN' WHERE owner=? AND workspace_id=? AND namespace=? AND state='IN_FLIGHT_FAKE'",(self.owner,workspace_id,namespace)).rowcount
        return dict(state='RECOVERED_UNKNOWN',count=n,order_authority=False)
