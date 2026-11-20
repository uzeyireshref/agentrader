"""Authenticated terminal inbox. HTTP never owns exchange credentials or a writer."""
import hashlib
import json
import re
import time
from contextlib import closing

from agentrader.migrations import connect

ACTIONS={'CONTEXT','SNAPSHOT','ANALYZE_PLAN','READ_COMMAND','SAVE_PLAN','PREVIEW_PLAN_AUTHORIZATION','PREVIEW_PLAN','PREVIEW_COMMAND','PREVIEW_CONTROL','CONFIRM','RECONCILE'}
READS={'CONTEXT','SNAPSHOT','ANALYZE_PLAN','RECONCILE'}


def encoded(value):
    from decimal import Decimal
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False,
                      default=lambda v:str(v) if isinstance(v,Decimal) else (_ for _ in ()).throw(ValueError('Invalid value')))


def checksum(value):return hashlib.sha256(encoded(value).encode()).hexdigest()


class BotError(ValueError):
    def __init__(self,code,status=422):self.code,self.status=code,status;super().__init__(code)


class BotInbox:
    def __init__(self,settings,clock=time.time):self.settings,self.clock=settings,clock

    def initialize(self):
        from agentrader.migrations import migrate
        migrate(self.settings.application_database)

    def status(self):
        with closing(connect(self.settings.application_database)) as db:
            row=db.execute('SELECT * FROM app_bot_worker WHERE owner=?',(self.settings.owner,)).fetchone()
            queue=db.execute("""SELECT
                sum(CASE WHEN state='PENDING' THEN 1 ELSE 0 END) AS pending,
                sum(CASE WHEN state='RUNNING' THEN 1 ELSE 0 END) AS running,
                min(CASE WHEN state='PENDING' THEN created_at END) AS oldest,
                min(CASE WHEN state='RUNNING' THEN updated_at END) AS started
                FROM app_bot_jobs WHERE owner=? AND state IN ('PENDING','RUNNING')""",(self.settings.owner,)).fetchone()
        fresh=bool(row and 0<=self.clock()-row['updated_at']<=30 and row['mode']!='STOPPED')
        return dict(enabled=self.settings.bot_enabled,environment='demo',product='USD-M',
                    authenticated_access_required=True,worker='FRESH' if fresh else 'NOT_READY',
                    execution_enabled=bool(self.settings.bot_enabled and fresh and row['mode']=='EXECUTE_DEMO' and not row['error_code']),
                    error_code=row['error_code'] if row else None,
                    queue=dict(pending=queue['pending'] or 0,running=queue['running'] or 0,
                               running_age_seconds=max(0,int(self.clock()-queue['started'])) if queue['started'] is not None else None,
                               oldest_pending_age_seconds=max(0,int(self.clock()-queue['oldest'])) if queue['oldest'] is not None else None))

    def pulse(self,execute,error=None):
        with closing(connect(self.settings.application_database)) as db,db:
            db.execute('INSERT OR REPLACE INTO app_bot_worker VALUES(?,?,?,?)',
                       (self.settings.owner,self.clock(),'EXECUTE_DEMO' if execute else 'READ_ONLY',error))

    def accept(self,request):
        if not self.settings.bot_enabled:raise BotError('BOT_DISABLED',503)
        if not isinstance(request,dict) or set(request)!={'request_id','action','payload'}:raise BotError('INVALID_BOT_JOB')
        rid,action,p=request['request_id'],request['action'],request['payload']
        if not isinstance(rid,str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',rid) or not isinstance(action,str) or action not in ACTIONS or not isinstance(p,dict):raise BotError('INVALID_BOT_JOB')
        expected={'CONTEXT':set(),'SNAPSHOT':{'symbol'},'ANALYZE_PLAN':{'draft'},'READ_COMMAND':{'operation','scope','parameters'},'SAVE_PLAN':{'draft'},'PREVIEW_PLAN_AUTHORIZATION':{'draft'},'PREVIEW_PLAN':{'draft'},'PREVIEW_COMMAND':{'operation','scope','parameters'},
                  'PREVIEW_CONTROL':{'session_id','kind','close_position'},'CONFIRM':{'review_id','review_digest','account_ref','execute_demo'},'RECONCILE':{'command_id'}}[action]
        if set(p)!=expected:raise BotError('INVALID_BOT_PAYLOAD')
        if action=='SNAPSHOT' and (not isinstance(p['symbol'],str) or not re.fullmatch('[A-Z0-9]{2,20}USDT',p['symbol'])):raise BotError('INVALID_SYMBOL')
        if action=='CONFIRM':
            if p['execute_demo'] is not True or not all(isinstance(p[k],str) and re.fullmatch('[a-f0-9]{64}',p[k]) for k in ('review_digest','account_ref')):raise BotError('EXPLICIT_DEMO_CONSENT_REQUIRED')
            if not isinstance(p['review_id'],str) or not re.fullmatch('job-[a-f0-9]{40}',p['review_id']):raise BotError('INVALID_REVIEW_ID')
        if action=='RECONCILE' and (not isinstance(p['command_id'],str) or not re.fullmatch('cmd-[a-f0-9]{40}',p['command_id'])):raise BotError('INVALID_COMMAND_ID')
        body=encoded(p)
        if len(body.encode())>32768:raise BotError('BOT_PAYLOAD_TOO_LARGE',413)
        # One irreversible consent job per review, even across double-clicks/tabs.
        identity=['confirm',p['review_id']] if action=='CONFIRM' else ['request',rid]
        jid='job-'+checksum([self.settings.owner,identity])[:40];h=checksum([self.settings.owner,action,p]);now=self.clock()
        with closing(connect(self.settings.application_database)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM app_bot_jobs WHERE job_id=?',(jid,)).fetchone()
            if old:
                if old['payload_hash']!=h:raise BotError('BOT_JOB_CONFLICT',409)
            else:
                pending=db.execute("SELECT count(*) FROM app_bot_jobs WHERE owner=? AND state IN ('PENDING','RUNNING')",(self.settings.owner,)).fetchone()[0]
                if action in ('SNAPSHOT','ANALYZE_PLAN'):
                    reads=db.execute("SELECT count(*) FROM app_bot_jobs WHERE owner=? AND action IN ('SNAPSHOT','ANALYZE_PLAN') AND state IN ('PENDING','RUNNING')",(self.settings.owner,)).fetchone()[0]
                    if reads>=2:raise BotError('BOT_READ_QUEUE_BUSY',429)
                if pending>=50:raise BotError('BOT_QUEUE_FULL',429)
                db.execute('INSERT INTO app_bot_jobs VALUES(?,?,?,?,?,?,?, ?,NULL,NULL,NULL)',
                           (jid,self.settings.owner,action,body,h,'PENDING',now,now))
        return self.show(jid)|{'duplicate':bool(old)}

    def row(self,jid):
        with closing(connect(self.settings.application_database)) as db:
            row=db.execute('SELECT * FROM app_bot_jobs WHERE job_id=? AND owner=?',(jid,self.settings.owner)).fetchone()
        return self._verified(row)

    def _verified(self, row):
        if row is None:raise BotError('BOT_JOB_NOT_FOUND',404)
        p=json.loads(row['payload'])
        if row['payload_hash']!=checksum([self.settings.owner,row['action'],p]):raise BotError('BOT_JOB_INTEGRITY',409)
        if row['result'] and row['result_hash']!=checksum(json.loads(row['result'])):raise BotError('BOT_RESULT_INTEGRITY',409)
        return dict(row)

    def _view(self, r):
        return {k:r[k] for k in ('job_id','action','state','created_at','updated_at','error_code')} | {
            'result': json.loads(r['result']) if r['result'] else None,
            'automatic_resend': False,
        }

    def show(self, jid):
        return self._view(self.row(jid))

    def recent(self, *, summary=False, include_snapshots=True):
        # The summary never reads or decodes large result bodies. Details retain
        # payload/result verification; a list row cannot authorize any action.
        columns = 'j.job_id,j.action,j.state,j.created_at,j.updated_at,j.error_code,o.result_state' if summary else 'j.*'
        join = 'LEFT JOIN app_bot_job_outcomes o ON o.job_id=j.job_id' if summary else ''
        snapshot_filter = '' if include_snapshots else "AND j.action NOT IN ('SNAPSHOT','ANALYZE_PLAN')"
        with closing(connect(self.settings.application_database)) as db:
            rows = db.execute(
                f'SELECT {columns} FROM app_bot_jobs j {join} WHERE j.owner=? {snapshot_filter} ORDER BY j.created_at DESC,j.job_id DESC LIMIT 100',
                (self.settings.owner,),
            ).fetchall()
        if summary:
            return [dict(r) | {'result': None, 'result_loaded': False, 'automatic_resend': False} for r in rows]
        return [self._view(self._verified(r)) for r in rows]

    def recover(self):
        with closing(connect(self.settings.application_database)) as db,db:
            # No blanket replay after crash; financial intent is reconciled separately.
            db.execute("UPDATE app_bot_jobs SET state='NEEDS_REVIEW',error_code='WORKER_INTERRUPTED',updated_at=? WHERE owner=? AND state='RUNNING'",(self.clock(),self.settings.owner))

    def prune_readings(self, *, retention_seconds=604800, batch_size=200):
        """Bounded cleanup of completed successful ephemeral readings."""
        if type(retention_seconds) is not int or retention_seconds<86400:
            raise ValueError('Retention must be at least one day')
        if type(batch_size) is not int or not 1<=batch_size<=1000:
            raise ValueError('Invalid cleanup batch size')
        with closing(connect(self.settings.application_database)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute("""SELECT job_id FROM app_bot_jobs WHERE owner=?
                AND action IN ('SNAPSHOT','ANALYZE_PLAN') AND state='SUCCEEDED'
                AND updated_at<? ORDER BY updated_at,job_id LIMIT ?""",
                (self.settings.owner,self.clock()-retention_seconds,batch_size)).fetchall()
            ids=[(r[0],) for r in rows]
            db.executemany('DELETE FROM app_bot_job_outcomes WHERE job_id=?',ids)
            db.executemany('DELETE FROM app_bot_jobs WHERE job_id=?',ids)
        return len(ids)

    def claim(self):
        with closing(connect(self.settings.application_database)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            r=db.execute("SELECT job_id FROM app_bot_jobs WHERE owner=? AND state='PENDING' ORDER BY CASE WHEN action IN ('SNAPSHOT','ANALYZE_PLAN') THEN 1 ELSE 0 END,created_at,job_id LIMIT 1",(self.settings.owner,)).fetchone()
            if r is None:return None
            db.execute("UPDATE app_bot_jobs SET state='RUNNING',updated_at=? WHERE job_id=?",(self.clock(),r[0]))
        return self.row(r[0])

    def finish(self,jid,result=None,error=None):
        if error and result is None:
            category = 'STORAGE' if error=='BOT_STORAGE_UNAVAILABLE' else 'VALIDATION' if error=='BOT_VALIDATION_OR_PREFLIGHT_REJECTED' else 'CONTROL'
            result = {'diagnostic': {'category':category,'correlation_id':jid,'code':error}}
        body=encoded(result) if result is not None else None
        with closing(connect(self.settings.application_database)) as db,db:
            changed = db.execute("UPDATE app_bot_jobs SET state=?,result=?,result_hash=?,error_code=?,updated_at=? WHERE job_id=? AND owner=? AND state='RUNNING'",
                       ('FAILED' if error else 'SUCCEEDED',body,checksum(result) if body else None,error,self.clock(),jid,self.settings.owner))
            if changed.rowcount:
                state = result.get('state') if isinstance(result,dict) else None
                state = state if isinstance(state,str) and len(state)<=64 else None
                db.execute('INSERT OR REPLACE INTO app_bot_job_outcomes VALUES(?,?)',(jid,state))
        return self.show(jid)
