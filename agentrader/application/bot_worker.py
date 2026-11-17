"""Explicit terminal worker; never started by HTTP lifespan."""
import json
import sqlite3
import time
from contextlib import contextmanager,closing

from .bot_inbox import BotInbox,BotError
from .bot_engine import BotEngine,verified_store
from agentrader.migrations import connect
from agentrader.shared.locking import execution_lock,ExecutionBusy
from agentrader.shared.exchange import ExchangeError


@contextmanager
def engine_for(settings):
    from agentrader.shared.config import Config
    from agentrader.shared.exchange import DemoExchange
    from agentrader.bot.risk import RiskLimits
    store=verified_store(settings.execution_database)
    try:yield BotEngine(settings,DemoExchange(Config.load(),store=store),store,RiskLimits.load(settings.bot_risk_profile))
    finally:store.close()


def process_bot_once(inbox,*,execute=False,factory=engine_for,checkpoint=None,admission=None):
    """Caller holds the existing global execution lock, including during reads."""
    job=inbox.claim()
    if not job:return None
    try:
        with factory(inbox.settings) as engine:
            if admission is not None:
                admission(engine,job)
            previous = getattr(engine.commands, 'read_checkpoint', None)
            try:
                if checkpoint is not None:
                    engine.commands.read_checkpoint = lambda: checkpoint(engine)
                result=engine.perform(inbox,job,execute)
            finally:
                engine.commands.read_checkpoint = previous
    except BotError as exc:return inbox.finish(job['job_id'],error=exc.code)
    except ExchangeError as exc:
        return inbox.finish(job['job_id'],error='BOT_EXCHANGE_UNAVAILABLE',result={
            'diagnostic': {'category':'EXCHANGE','correlation_id':job['job_id'],
                           'code':exc.code if type(exc.code) is int else None,
                           'delivery_status':exc.delivery_status if exc.delivery_status in ('NOT_SENT','REJECTED','UNKNOWN','READ_FAILED') else 'UNKNOWN'}})
    except (ValueError,KeyError,TypeError,ArithmeticError):return inbox.finish(job['job_id'],error='BOT_VALIDATION_OR_PREFLIGHT_REJECTED')
    except (OSError,sqlite3.Error):return inbox.finish(job['job_id'],error='BOT_STORAGE_UNAVAILABLE')
    return inbox.finish(job['job_id'],result=result)


def timer_job_admission(engine,timers,inbox,job,*,now_ms=None,budget_ms=16000):
    """Conservative one-request budget, not a bound on a whole user operation.

    A refused job is explicitly failed before perform, never requeued/replayed.
    Local timer inspection and reviewed disable remain possible to avoid lockout.
    """
    if not timers:return
    from agentrader.bot.cancel_timers import load,DISABLE,QUERY
    now=int(time.time()*1000) if now_ms is None else now_ms
    tight=False
    for timer_id,source in timers.items():
        row,body=load(engine.commands,timer_id)
        if source!=body['source_digest']:raise BotError('BOT_TIMER_CONTEXT_CHANGED')
        if (row['state']!='ACTIVE' or now<row['last_attempt_ms'] or
                min(body['lease_until_ms'],row['last_attempt_ms']+body['heartbeat_ms'],
                    row['last_attempt_ms']+body['countdown_ms'])-now<=budget_ms):
            tight=True
    if not tight:return
    payload=json.loads(job['payload'])
    if job['action']=='CONTEXT':return
    if job['action'] in ('PREVIEW_COMMAND','READ_COMMAND') and payload['operation'] in (DISABLE,QUERY):return
    if job['action']=='CONFIRM':
        # This only selects the admission exemption. confirm still validates the
        # review digest, account, expiry, authority and command before sending.
        review=inbox.row(payload['review_id'])
        result=json.loads(review['result']) if review['result'] else {}
        if review['action']=='PREVIEW_COMMAND' and result.get('kind')=='COMMAND':
            _,command=engine.commands._row(result['payload']['command_id'])
            if command['request']['operation'] in (DISABLE,QUERY):return
    raise BotError('BOT_TIMER_PRIORITY_REQUIRED',409)


def uncertain_financial(store):
    if store.unresolved_account_command():
        return True
    tables = {r[0] for r in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in ('intents','v2_cancellations','batch_cancellations','order_create_batches','ws_deliveries'):
        if table in tables and store.db.execute(
                f"SELECT 1 FROM {table} WHERE state IN ('SUBMITTING','UNKNOWN') LIMIT 1").fetchone():
            return True
    if 'exchange_commands' in tables:
        from agentrader.bot.exchange_commands import OPERATIONS
        for row in store.db.execute("SELECT operation FROM exchange_commands WHERE state IN ('SUBMITTING','UNKNOWN')"):
            if OPERATIONS.get(row[0],{}).get('mutates', True):
                return True
    return False


def monitor(engine,timers):
    from agentrader.bot.account_runtime import runner_for
    from agentrader.shared.runtime import monitor_session
    from agentrader.bot.cancel_timers import tick
    for tid,source in list(timers.items()):
        try:result=tick(engine.commands,tid,source,execute=True)
        except (ValueError,ExchangeError):result={'worker_state':'STOPPED_UNCERTAIN'}
        if result['worker_state'] not in ('WAITING','REFRESHED'):timers.pop(tid,None)
    for session in engine.store.sessions():
        sid = session['id']
        pause_key, retry_key = 'bot_monitor_paused:'+sid, 'bot_monitor_retry:'+sid
        if engine.store.db.execute('SELECT 1 FROM control WHERE name=?',(pause_key,)).fetchone():
            continue
        retry = engine.store.db.execute('SELECT value FROM control WHERE name=?',(retry_key,)).fetchone()
        attempts = 0
        try:
            attempts = int(retry[0]) if retry else 0
            engine.owned_session(sid)
            runner = runner_for(engine.plans,engine.x,engine.limits,session)
            baseline = next(monitor_session(runner,sid,execute=False,iterations=1)) if retry else None
            report = baseline if baseline and (baseline['state']=='CLOSED' or baseline.get('service_stopped')) else next(monitor_session(runner,sid,execute=True,iterations=1))
            with engine.store.db:
                engine.store.db.execute('DELETE FROM control WHERE name=?',(retry_key,))
        except (ValueError,ExchangeError,StopIteration) as exc:
            uncertain = uncertain_financial(engine.store)
            recoverable = (isinstance(exc,ExchangeError) and exc.delivery_status=='READ_FAILED'
                           and exc.retryable and not uncertain and attempts < 3)
            if recoverable:
                with engine.store.db:
                    engine.store.db.execute('INSERT OR REPLACE INTO control VALUES(?,?)',(retry_key,str(attempts+1)))
                report = dict(state='MONITOR_READ_RETRY',session_id=sid,service_stopped=False,automatic_resend=False)
            else:
                reason = 'UNCERTAIN_MUTATION' if uncertain else 'READ_RETRIES_EXHAUSTED' if retry else 'RECONCILIATION_REQUIRED'
                with engine.store.db:
                    engine.store.db.execute('INSERT OR REPLACE INTO control VALUES(?,?)',
                        (pause_key,json.dumps(dict(reason=reason,observed_at=time.time()))))
                report = dict(state='SESSION_REVIEW_REQUIRED',session_id=sid,service_stopped=True,automatic_resend=False)
        if report.get('service_stopped') is True:
            with engine.store.db:
                engine.store.db.execute('INSERT OR IGNORE INTO control VALUES(?,?)',(pause_key,json.dumps({'reason':'SERVICE_STOPPED'})))
        engine.store.runtime_health(sid,report,time.time())


def run_bot_worker(settings,*,execute=False,once=False,interval=1,sleep=time.sleep,factory=engine_for,emit=None):
    from .service import ApplicationService
    if not settings.bot_enabled or not settings.token:raise BotError('BOT_ENABLED_AND_WEB_TOKEN_REQUIRED')
    if type(interval)is not int or not 1<=interval<=10:raise BotError('INVALID_WORKER_INTERVAL')
    ApplicationService(settings).initialize();inbox=BotInbox(settings)
    path=settings.application_database.with_suffix(settings.application_database.suffix+'.bot-worker.lock')
    timers={}  # Only leases explicitly armed in THIS process; never reload on restart.
    with execution_lock(path):
        inbox.recover()
        try:
            while True:
                result=None
                inbox.pulse(execute)
                try:
                    with execution_lock():
                        if execute:
                            with factory(settings) as engine:monitor(engine,timers)
                        result=process_bot_once(inbox,execute=execute,factory=factory,
                            checkpoint=(lambda engine: monitor(engine,timers)) if execute else None,
                            admission=(lambda engine,job: timer_job_admission(engine,timers,inbox,job)) if execute else None)
                        if result and emit:emit(result)
                        r=result.get('result') if result else None
                        if execute and r and r.get('state')=='APPLIED' and r.get('request',{}).get('operation')=='SET_CANCEL_TIMER':
                            tid=r.get('result',{}).get('timer_id')
                            if tid:timers[tid]=r['digest']
                        if execute:
                            with factory(settings) as engine:monitor(engine,timers)
                except ExecutionBusy:inbox.pulse(execute,'EXECUTION_BUSY')
                except BotError as exc:inbox.pulse(execute,exc.code)
                except (ValueError,ExchangeError,OSError,sqlite3.Error):inbox.pulse(execute,'BOT_MONITOR_UNAVAILABLE')
                if once:return result
                sleep(interval)
        finally:
            with closing(connect(settings.application_database)) as db,db:
                db.execute("UPDATE app_bot_worker SET mode='STOPPED',updated_at=? WHERE owner=?",(time.time(),settings.owner))
