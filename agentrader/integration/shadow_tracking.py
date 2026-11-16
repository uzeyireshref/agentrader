"""Demo closed-candle shadow tracking. No plan, exchange writer or delivery adapter."""
from contextlib import closing
from copy import deepcopy
import json
import threading
import time
import uuid
from pathlib import Path

from agentrader.chart.binding_catalog import catalog
from agentrader.chart.binding_eligibility import evaluate_binding
from agentrader.chart.chart_bindings import BindingService, binding_hash
from agentrader.chart.chart_clock import POLICY
from agentrader.chart.chart_evidence import canonical
from agentrader.chart.drawings.service import DrawingError, DrawingConflict, identifier
from agentrader.chart.local_chart_events import closed_candidate, target_view
from agentrader.shared.locking import execution_lock
from agentrader.shared.market_data import INTERVALS
from agentrader.shared.market_environment import SOURCE, ENVIRONMENT
from agentrader.migrations import connect

ACTIVE = ('WATCHING', 'WAITING_DATA')
PROFILE = 'DEMO_SHADOW_CLOSED_EXPLICIT_REARM/1'


class ShadowError(DrawingError):
    def __init__(self, reason):
        self.code = reason
        super().__init__(reason)


class ShadowTracking:
    def __init__(self, database, owner, *, clock=time.time, monotonic=time.monotonic):
        self.database, self.owner = database, owner
        self.clock, self.monotonic = clock, monotonic
        self.wall_anchor,self.mono_anchor=clock(),monotonic()
        self.bindings = BindingService(database, owner)

    def _supported(self, b):
        d = b['definition']
        if (b['state'] != 'DISABLED' or d['target']['type'] != 'drawing'
                or d['target']['kind'] not in ('horizontal', 'horizontal_ray')
                or d['query'] != dict(operation='priceAt', output='value', ratio=None)
                or d['rule']['kind'] not in ('approach', 'touch', 'close_cross')
                or d['market']['source'] != SOURCE or d['market']['environment'] != ENVIRONMENT):
            raise ShadowError('SHADOW_UNSUPPORTED_OR_STOPPED_BINDING')

    def command(self, workspace, binding_id, expected_revision, definition_hash, action, ttl_seconds=3600):
        identifier(workspace);identifier(binding_id)
        if (action not in ('start', 'pause', 'resume') or type(expected_revision) is not int
                or not isinstance(definition_hash, str) or type(ttl_seconds) is not int
                or not 60 <= ttl_seconds <= 86400):
            raise ShadowError('INVALID_SHADOW_COMMAND')
        now = self.clock()
        with closing(connect(self.database)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            b = self.bindings._view_binding(self.bindings._binding(db,workspace,binding_id),True)
            if b['revision'] != expected_revision or b['definition_hash'] != definition_hash:
                raise DrawingConflict()
            self._supported(b)
            key = (self.owner,workspace,binding_id,expected_revision)
            row = db.execute('SELECT * FROM app_shadow_runs WHERE owner=? AND workspace_id=? AND binding_id=? AND binding_revision=?', key).fetchone()
            if row is None:
                if action != 'start':raise ShadowError('SHADOW_NOT_STARTED')
                count = db.execute("SELECT COUNT(*) FROM app_shadow_runs WHERE owner=? AND state IN ('WATCHING','WAITING_DATA')", (self.owner,)).fetchone()[0]
                if count >= 100:raise ShadowError('SHADOW_RUN_LIMIT')
                db.execute('INSERT INTO app_shadow_runs VALUES (?,?,?,?,?,?,?,?,?,?)', (*key,definition_hash,'WAITING_DATA','INITIAL_SEED_REQUIRED',now+ttl_seconds,'{}',now))
            elif row['expires_at'] <= now or row['state'] in ('LATCHED','STOPPED','EXPIRED'):
                raise ShadowError('SHADOW_EXPLICIT_REBIND_REQUIRED')
            elif action == 'pause':
                db.execute("UPDATE app_shadow_runs SET state='PAUSED',reason='USER_PAUSED',updated_at=? WHERE owner=? AND workspace_id=? AND binding_id=? AND binding_revision=?", (now,*key))
            elif action == 'resume' and row['state'] == 'PAUSED':
                # Resume never extends TTL or interprets closes missed while paused.
                db.execute("UPDATE app_shadow_runs SET state='WAITING_DATA',reason='RESUME_SEED_REQUIRED',checkpoint='{}',updated_at=? WHERE owner=? AND workspace_id=? AND binding_id=? AND binding_revision=?", (now,*key))
        return self.status(workspace,binding_id)

    def runs(self):
        with closing(connect(self.database)) as db:
            return [dict(r) for r in db.execute("SELECT * FROM app_shadow_runs WHERE owner=? AND state IN ('WATCHING','WAITING_DATA') ORDER BY updated_at,binding_id", (self.owner,))]

    def status(self, workspace, binding_id):
        identifier(workspace);identifier(binding_id)
        with closing(connect(self.database)) as db:
            rows = db.execute('SELECT * FROM app_shadow_runs WHERE owner=? AND workspace_id=? AND binding_id=? ORDER BY binding_revision DESC LIMIT 1', (self.owner,workspace,binding_id)).fetchall()
            run = dict(rows[0]) if rows else None
            if run:
                run['checkpoint'] = json.loads(run['checkpoint'])
                if run['state'] in (*ACTIVE,'PAUSED') and run['expires_at'] <= self.clock():run.update(state='EXPIRED',reason='TTL_EXPIRED')
            events = [json.loads(r[0]) for r in db.execute('SELECT body FROM app_shadow_events WHERE owner=? AND workspace_id=? AND binding_id=? ORDER BY created_at DESC,event_id LIMIT 50', (self.owner,workspace,binding_id))]
            worker = db.execute('SELECT state,observed_at FROM app_shadow_worker WHERE name=?', ('shadow',)).fetchone()
        runtime = dict(worker) if worker else dict(state='NOT_OBSERVED',observed_at=None)
        if worker and worker['state']=='RUNNING' and not 0 <= self.clock()-worker['observed_at'] <= 15:runtime['state']='STALE'
        return dict(schema='shadow-status/1',mode='SHADOW_ONLY',source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE',order_authority=False,run=run,events=events,worker=runtime)

    def heartbeat(self, state):
        with closing(connect(self.database)) as db, db:
            db.execute('INSERT OR REPLACE INTO app_shadow_worker VALUES (?,?,?)', ('shadow',state,self.clock()))

    def process(self, run, context, boot, *, _fault=None):
        captured,wall = self.monotonic(),self.clock()
        c = deepcopy(context)
        key = (self.owner,run['workspace_id'],run['binding_id'],run['binding_revision'])
        with closing(connect(self.database)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM app_shadow_runs WHERE owner=? AND workspace_id=? AND binding_id=? AND binding_revision=?',key).fetchone()
            if not row or row['state'] not in ACTIVE:return dict(created=False,reason='INACTIVE')
            checkpoint = json.loads(row['checkpoint'])
            def save(state, reason):
                db.execute('UPDATE app_shadow_runs SET state=?,reason=?,checkpoint=?,updated_at=? WHERE owner=? AND workspace_id=? AND binding_id=? AND binding_revision=?', (state,reason,canonical(checkpoint),self.clock(),*key))
                return dict(created=False,reason=reason,state=state,order_authority=False)
            if self.clock() >= row['expires_at']:return save('EXPIRED','TTL_EXPIRED')
            b = self.bindings._view_binding(self.bindings._binding(db,run['workspace_id'],run['binding_id']),True)
            if b['revision'] != row['binding_revision'] or b['definition_hash'] != row['definition_hash'] or target_view(self.bindings,db,b) is None:
                return save('STOPPED','REVISION_CHANGED')
            try:self._supported(b)
            except ShadowError:return save('STOPPED','BINDING_STOPPED')
            elapsed = (self.monotonic()-captured)*1000
            if elapsed < 0 or abs((self.clock()-wall)*1000-elapsed)>POLICY['wall_jump_ms'] or abs((self.clock()-self.wall_anchor)-(self.monotonic()-self.mono_anchor))*1000>POLICY['wall_jump_ms']:
                checkpoint['reseed']=True;return save('WAITING_DATA','CLOCK_UNTRUSTED')
            if isinstance(c,dict) and isinstance(c.get('timing'),dict):
                for name in ('data_age_ms','upstream_age_upper_ms'):
                    if type(c['timing'].get(name)) in (int,float):c['timing'][name]+=elapsed
                if type(c['timing'].get('uncertainty_ms')) in (int,float):c['timing']['uncertainty_ms']+=elapsed*POLICY['drift_ppm']/1000000
            result=evaluate_binding(b,owner=self.owner,workspace_id=run['workspace_id'],target=target_view(self.bindings,db,b),context=c,traceability=catalog())
            if result['state']!='EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY':
                # The closing frame may precede the clock uncertainty bound by a
                # few milliseconds. Wait for proof, keeping the last evaluated bar.
                # Actual data/clock/source faults still require a fresh baseline.
                if set(result['reasons'])!={'CLOSED_TIME_UNPROVEN'}:checkpoint['reseed']=True
                return save('WAITING_DATA',','.join(result['reasons']) or 'NOT_ELIGIBLE')
            closed=[r for r in c['rows'] if r['closed']]
            latest=closed[-1]['time'];epoch=c['stream_epoch'];payload_hash=binding_hash(closed[-2:])
            seed=checkpoint.get('boot')!=boot or checkpoint.get('epoch')!=epoch or checkpoint.get('reseed')
            if seed:
                checkpoint.update(boot=boot,epoch=epoch,last_time=latest,payload_hash=payload_hash,reseed=False)
                return save('WATCHING','SEEDED_NO_HISTORICAL_SIGNAL')
            if latest==checkpoint['last_time']:
                if payload_hash!=checkpoint['payload_hash']:return save('STOPPED','SEMANTIC_PAYLOAD_CONFLICT')
                return dict(created=False,reason='NO_NEW_CLOSE',order_authority=False)
            if latest-checkpoint['last_time']!=INTERVALS[b['definition']['market']['interval']]//1000:
                checkpoint.update(last_time=latest,payload_hash=payload_hash)
                return save('WATCHING','RESYNC_NO_HISTORICAL_SIGNAL')
            checkpoint.update(last_time=latest,payload_hash=payload_hash)
            try:candidate=closed_candidate(b,c)
            except (ValueError,KeyError,TypeError,ArithmeticError):
                checkpoint['reseed']=True
                return save('WAITING_DATA','QUERY_UNAVAILABLE')
            if not candidate:return save('WATCHING','RULE_NOT_MATCHED')
            event_id=binding_hash(dict(profile=PROFILE,owner=self.owner,workspace=run['workspace_id'],binding_id=b['binding_id'],revision=b['revision'],definition_hash=b['definition_hash'],candle_time=latest,kind=candidate['kind']))
            event={**candidate,'schema':'shadow-domain-event/1','profile':PROFILE,'event_id':event_id,'created_at':self.clock(),'order_authority':False,'reason':dict(rule=b['definition']['rule'],level=candidate['level'],previous_level=candidate['previous_level'],closed_price=candidate['closed_price']),'evidence_hash':binding_hash(c)}
            db.execute('INSERT OR IGNORE INTO app_shadow_events VALUES (?,?,?,?,?,?,?,?)',(event_id,self.owner,run['workspace_id'],b['binding_id'],b['revision'],self.clock(),canonical(event),canonical(dict(definition=b['definition'],context=c,eligibility=result))))
            if _fault:_fault('after_event_insert')
            save('LATCHED','EXPLICIT_REBIND_REQUIRED')
            return dict(created=True,event_id=event_id,state='LATCHED',order_authority=False)


class ShadowWorker:
    def __init__(self, service, hub):
        self.service,self.hub=service,hub
        self.stop=threading.Event();self.thread=None;self.feeds={};self.error=None;self.boot=uuid.uuid4().hex;self.lease=None

    def start(self):
        self.lease=execution_lock(Path(str(self.service.database)+'.shadow.lock'))
        try:self.lease.__enter__()
        except ValueError:
            self.lease=None;self.error='SHADOW_WORKER_ALREADY_RUNNING'
            return False
        self.thread=threading.Thread(target=self.run,name='demo-shadow',daemon=True)
        try:self.thread.start()
        except BaseException:self.lease.__exit__(None,None,None);raise
        return True

    def tick(self):
        runs=self.service.runs();wanted={}
        for run in runs:
            b=self.service.bindings.show(run['workspace_id'],run['binding_id']);m=b['definition']['market'];wanted[(m['symbol'],m['interval'])]=True
        for key in list(self.feeds):
            if key not in wanted:self.hub.release(self.feeds.pop(key))
        for key in wanted:
            if key not in self.feeds:
                try:self.feeds[key]=self.hub.acquire(*key)
                except Exception:self.error='SHADOW_FEED_UNAVAILABLE'
        for run in runs:
            b=self.service.bindings.show(run['workspace_id'],run['binding_id']);m=b['definition']['market']
            self.service.process(run,self.hub.binding_context(m['symbol'],m['interval']),self.boot)

    def run(self):
        try:
            while not self.stop.is_set():
                try:self.error=None;self.tick();self.service.heartbeat(self.error or 'RUNNING')
                except Exception:self.error='SHADOW_WORKER_ERROR';self.service.heartbeat(self.error)
                self.stop.wait(1)
        finally:
            for feed in self.feeds.values():self.hub.release(feed)
            self.feeds.clear()
            try:self.service.heartbeat('STOPPED')
            finally:self.lease.__exit__(None,None,None)

    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=30)
