"""Authenticated web consent inbox. Account reads/plan authorization run only in an explicit CLI worker.

No action in this module submits exchange orders. The read-only W1 inbox is untouched.
"""
from contextlib import closing
import hashlib
import json
import re
import secrets
import sqlite3
import time

from agentrader.chart.chart_bindings import binding_hash
from agentrader.integration.chart_execution import guard_chart_entry
from agentrader.chart.drawings.service import DrawingError, identifier
from agentrader.migrations import connect
from agentrader.bot.plans import digest, timestamp, validate_plan, transaction
from agentrader.integration.preview_preflight import local_preview_provider, preflight_preview


class ApprovalError(DrawingError):
    def __init__(self, code):self.code=code;super().__init__(code)


def plan_view(settings, plan_id, *, clock=time.time):
    """Read-only execution snapshot. Never construct StateStore in the HTTP process."""
    identifier(plan_id)
    if not settings.execution_database.exists():return None
    with closing(sqlite3.connect(settings.execution_database.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'plan_versions','control'} <= tables:return None
        row=db.execute('SELECT * FROM plan_versions WHERE owner=? AND plan_id=? AND version=1',(settings.owner,plan_id)).fetchone()
        if row is None:return None
        plan=validate_plan(json.loads(row['body']))
        binding=db.execute('SELECT value FROM control WHERE name=?',(f'chart_entry:{plan_id}:1',)).fetchone()
        review=db.execute('SELECT value FROM control WHERE name=?',('chart_review:'+plan_id,)).fetchone()
        if not binding or not review:raise ApprovalError('CHART_REVIEW_INCOMPLETE')
        b=json.loads(binding[0]);r=json.loads(review[0])
        if (digest(plan)!=row['digest'] or b['execution_digest']!=row['digest'] or b['owner']!=settings.owner
                or b['content_hash']!=binding_hash({k:v for k,v in b.items() if k!='content_hash'})
                or r['preview_hash']!=b['preview_hash'] or r['account_preflight']['state']!='READY'
                or not plan['analysis_ref'].startswith('shadow-event:') or plan['environment']!='demo'):
            raise ApprovalError('CHART_REVIEW_INTEGRITY')
        scope=dict(schema='chart-plan-review/1',plan=plan,plan_digest=row['digest'],source_binding_hash=b['content_hash'],
                   preview_hash=b['preview_hash'],preview_version=b['preview_version'],event_id=b['event_id'],workspace=b['workspace'],
                   account_ref=b['account_ref'],risk_profile_hash=b['risk_profile_hash'],expires_at=b['expires_at'],
                   account_preflight=r['account_preflight'],checked_at=r['checked_at'])
        scope['review_hash']=binding_hash(scope)
        state=row['state']
        if state in ('PENDING_APPROVAL','AUTHORIZED') and (clock()>=timestamp(plan['expires_at']) or
                state=='AUTHORIZED' and clock()>=row['approval_until']):state='EXPIRED'
        return scope|dict(state=state,approval_until=row['approval_until'],executed=False,order_authority=False)


class ApprovalInbox:
    def __init__(self, settings, clock=time.time):self.settings,self.clock=settings,clock

    def status(self):
        with closing(connect(self.settings.application_database)) as db:
            row=db.execute('SELECT updated_at,mode FROM app_chart_approval_worker WHERE owner=?',(self.settings.owner,)).fetchone()
        ready=bool(row and row['mode']=='APPROVAL_ONLY' and 0<=self.clock()-row['updated_at']<=10)
        return dict(worker_ready=ready,mode='APPROVAL_ONLY',execution_enabled=False)

    @staticmethod
    def _view(row):
        return dict(request_id=row['request_id'],state=row['state'],expires_at=row['expires_at'],
                    result=json.loads(row['result']) if row['result'] else None,error_code=row['error_code'])

    def show(self, request_id):
        identifier(request_id)
        with closing(connect(self.settings.application_database)) as db:
            row=db.execute('SELECT * FROM app_chart_approvals WHERE owner=? AND request_id=?',(self.settings.owner,request_id)).fetchone()
        if row is None:raise ApprovalError('APPROVAL_REQUEST_NOT_FOUND')
        view=self._view(row)
        if view['state']=='PENDING' and self.clock()>=row['expires_at']:view['state']='EXPIRED'
        return view

    def accept(self, plan_id, command):
        fields={'request_id','review_hash','plan_digest','preview_hash','account_ref','ttl_seconds'}
        if not isinstance(command,dict) or set(command)!=fields:raise ApprovalError('INVALID_APPROVAL_REQUEST')
        rid=identifier(command['request_id'])
        if any(not isinstance(command[k],str) or not re.fullmatch('[a-f0-9]{64}',command[k]) for k in fields-{'request_id','ttl_seconds'}):
            raise ApprovalError('INVALID_APPROVAL_SCOPE')
        if type(command['ttl_seconds']) is not int or command['ttl_seconds'] not in (30,60,120):raise ApprovalError('INVALID_APPROVAL_TTL')
        payload={**command,'plan_id':identifier(plan_id)};h=binding_hash(payload);now=self.clock()
        with closing(connect(self.settings.application_database)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM app_chart_approvals WHERE owner=? AND request_id=?',(self.settings.owner,rid)).fetchone()
            if old:
                if old['payload_hash']!=h:raise ApprovalError('APPROVAL_REQUEST_CONFLICT')
                return self._view(old)
            v=plan_view(self.settings,plan_id,clock=self.clock)
            if not v or v['state']!='PENDING_APPROVAL' or any(v[k]!=command[k] for k in ('review_hash','plan_digest','preview_hash','account_ref')):
                raise ApprovalError('APPROVAL_REVIEW_CHANGED')
            worker=db.execute('SELECT updated_at,mode FROM app_chart_approval_worker WHERE owner=?',(self.settings.owner,)).fetchone()
            if not worker or worker['mode']!='APPROVAL_ONLY' or not 0<=now-worker['updated_at']<=10:raise ApprovalError('APPROVAL_WORKER_OFFLINE')
            expires=min(now+60,v['expires_at'])
            db.execute('INSERT INTO app_chart_approvals VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (self.settings.owner,rid,json.dumps(payload,sort_keys=True),h,'PENDING',now,expires,now,None,None))
            return dict(request_id=rid,state='PENDING',expires_at=expires,result=None,error_code=None)


def pulse(settings, mode='APPROVAL_ONLY', clock=time.time):
    with closing(connect(settings.application_database)) as db,db:
        db.execute('INSERT OR REPLACE INTO app_chart_approval_worker VALUES (?,?,?)',(settings.owner,clock(),mode))


def process_once(settings, exchange, limits, *, clock=time.time, guard=guard_chart_entry,
                 preflight=preflight_preview, provider_factory=local_preview_provider):
    """Caller owns both the approval-worker and execution locks. Never sends orders."""
    now=clock()
    with closing(connect(settings.application_database)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("UPDATE app_chart_approvals SET state='EXPIRED',updated_at=? WHERE owner=? AND state='PENDING' AND expires_at<=?",(now,settings.owner,now))
        row=db.execute("SELECT * FROM app_chart_approvals WHERE owner=? AND state='PENDING' ORDER BY created_at,request_id LIMIT 1",(settings.owner,)).fetchone()
        if row is None:return None
        db.execute("UPDATE app_chart_approvals SET state='RUNNING',updated_at=? WHERE owner=? AND request_id=?",(now,settings.owner,row['request_id']))
    result=None;error=None;state='FAILED'
    try:
        from agentrader.bot.plans import PlanService
        from agentrader.shared.state import StateStore
        p=json.loads(row['payload'])
        if binding_hash(p)!=row['payload_hash']:raise ApprovalError('APPROVAL_PAYLOAD_INTEGRITY')
        v=plan_view(settings,p['plan_id'],clock=clock)
        if not v or v['state']!='PENDING_APPROVAL' or any(p[k]!=v[k] for k in ('review_hash','plan_digest','preview_hash','account_ref')):
            raise ApprovalError('APPROVAL_REVIEW_CHANGED')
        store=StateStore(settings.execution_database)
        try:
            service=PlanService(store,settings.owner)
            guard(service,exchange,limits,v['plan'],clock=clock)
            b=json.loads(store.db.execute('SELECT value FROM control WHERE name=?',(f"chart_entry:{p['plan_id']}:1",)).fetchone()[0])
            checked=preflight(provider_factory(b['workspace'],b['event_id'],b['preview_version'],b['port']),exchange,limits,clock=clock)
            if checked['account_preflight']['state']!='READY' or checked['preview_hash']!=p['preview_hash']:
                raise ApprovalError('APPROVAL_ACCOUNT_NOT_READY')
            guard(service,exchange,limits,v['plan'],clock=clock)
            if clock()>=row['expires_at']:raise ApprovalError('APPROVAL_REQUEST_EXPIRED')
            # Authenticated explicit web consent is the authorization credential.
            # Rotate only the pending local token, never persist its plaintext or
            # expose it to the browser. PlanService enforces the normal slot/TTL rules.
            token=secrets.token_urlsafe(32)
            with transaction(store) as db:
                current=service.row(db,p['plan_id'],1)
                if current['state']!='PENDING_APPROVAL' or current['digest']!=p['plan_digest']:
                    raise ApprovalError('APPROVAL_REVIEW_CHANGED')
                db.execute('UPDATE plan_versions SET token_hash=? WHERE plan_id=? AND version=1',
                           (hashlib.sha256(token.encode()).hexdigest(),p['plan_id']))
                service.event(db,'authenticated_chart_consent',dict(request_id=row['request_id'],review_hash=p['review_hash'],account_ref=p['account_ref']))
            authorization=service.authorize(p['plan_id'],1,token,'approve',settings.owner,ttl=p['ttl_seconds'],now=clock())
            result=dict(state=authorization['state'],approval_until=authorization['approval_until'],plan_id=p['plan_id'],
                        plan_digest=p['plan_digest'],review_hash=p['review_hash'],executed=False,order_requests=0)
            state='APPROVED'
        finally:store.close()
    except Exception:
        # Transport exceptions can contain signed URLs. Only a fixed code crosses HTTP.
        error='APPROVAL_REVALIDATION_FAILED'
    with closing(connect(settings.application_database)) as db,db:
        db.execute('UPDATE app_chart_approvals SET state=?,result=?,error_code=?,updated_at=? WHERE owner=? AND request_id=? AND state=\'RUNNING\'',
                   (state,json.dumps(result) if result else None,error,clock(),settings.owner,row['request_id']))
    return dict(request_id=row['request_id'],state=state,result=result,error_code=error)


def run_approval_worker(settings, *, once=False, interval=2):
    from agentrader.application.service import ApplicationService
    from agentrader.shared.config import Config
    from agentrader.shared.exchange import DemoExchange
    from agentrader.shared.locking import execution_lock
    from agentrader.integration.preview_preflight import ReadOnlyDemoAccount
    from agentrader.bot.risk import RiskLimits
    ApplicationService(settings).initialize()
    path=settings.application_database.with_suffix(settings.application_database.suffix+'.approval.lock')
    with execution_lock(path):
        # A crashed consumer never automatically replays a possibly applied consent.
        with closing(connect(settings.application_database)) as db,db:
            db.execute("UPDATE app_chart_approvals SET state='NEEDS_REVIEW',error_code='WORKER_INTERRUPTED',updated_at=? WHERE owner=? AND state='RUNNING'",(time.time(),settings.owner))
        try:
            while True:
                pulse(settings)
                try:
                    with execution_lock():
                        # Lazy: no credential load and no account I/O without a job.
                        inbox=ApprovalInbox(settings)
                        with closing(connect(settings.application_database)) as db:
                            pending=db.execute("SELECT 1 FROM app_chart_approvals WHERE owner=? AND state='PENDING'",(settings.owner,)).fetchone()
                        if pending:
                            result=process_once(settings,ReadOnlyDemoAccount(DemoExchange(Config.load())),RiskLimits.load('risk-demo.json'))
                            if result:print(json.dumps(result,ensure_ascii=False),flush=True)
                except ValueError:pass  # Busy execution lock: leave the request pending.
                if once:return
                time.sleep(interval)
        finally:pulse(settings,'STOPPED')
