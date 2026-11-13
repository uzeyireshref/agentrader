"""Single-writer scheduling for multiple independently authorized sessions."""
import time

from .exchange import ExchangeError
from .grid_plan import compile_grid
from .grid_runner import GridRunner
from .portfolio import Exposure
from .risk import number
from .runtime import monitor_session
from .v2_preflight import prepare_single
from .v2_runner import V2Runner
from .neutral_runner import NeutralGridRunner
from .neutral_plan import compile_neutral


def plan_runner(service,exchange,limits,plan):
    return {'GRID':GridRunner,'SINGLE':V2Runner,'NEUTRAL_GRID':NeutralGridRunner}[plan['execution']['strategy']](service,exchange,limits)


def compile_plan(plan,snapshot,limits):
    return {'GRID':compile_grid,'SINGLE':prepare_single,'NEUTRAL_GRID':compile_neutral}[plan['execution']['strategy']](plan,snapshot,limits)


def runner_for(service,exchange,limits,session):
    engine=session.get('engine')
    if engine not in ('v2','grid-v2','neutral-v2'):raise ValueError('Çoklu izleme yalnız v2 oturumlarını destekler.')
    return {'v2':V2Runner,'grid-v2':GridRunner,'neutral-v2':NeutralGridRunner}[engine](service,exchange,limits)


def prepare_many(service,exchange,limits,references):
    if not isinstance(references,list) or not references or len(references)>20:
        raise ValueError('Açıkça belirtilmiş 1–20 plan gerekli.')
    if any(not isinstance(r,tuple) or len(r)!=2 or not isinstance(r[0],str) or
           type(r[1])is not int or r[1]<1 for r in references):
        raise ValueError('Plan kimliği ve pozitif sürüm çifti gerekli.')
    if len(set(references))!=len(references):raise ValueError('Aynı plan iki kez başlatılamaz.')
    snapshots=[];prepared=[];symbols=set();extras=[]
    for plan_id,version in references:
        row=service.show(plan_id,version);plan=row['plan']
        if row['state']!='AUTHORIZED' or plan['schema_version']!=2 or plan['symbol'] in symbols:
            raise ValueError('Farklı sembollü, ayrı ayrı yetkilendirilmiş v2 planları gerekli.')
        symbols.add(plan['symbol'])
        runner=plan_runner(service,exchange,limits,plan)
        snap=runner._snapshot(plan['symbol']);snapshots.append(snap)
        result=compile_plan(plan,snap,limits)
        prepared.append({'plan_id':plan_id,'version':version,'state':result['state']})
        if result['state']=='READY':extras.extend(Exposure(**e) for e in result['exposures'])
    if any(r['state']!='READY' for r in prepared):
        return {'state':'WAITING_CONDITION','plans':prepared,'executed':False}
    conservative={'collateral':str(min(number(s['collateral']) for s in snapshots)),
                  'daily_loss':str(max(number(s['daily_loss']) for s in snapshots)),
                  'observed_at':min(s['observed_at'] for s in snapshots)}
    risk=runner.book.evaluate(conservative,limits,exchange=exchange,extra_exposures=extras)
    return {'state':'READY','plans':prepared,'portfolio_risk':risk,'executed':False}


def start_many(service,exchange,limits,references,*,execute=False):
    preview=prepare_many(service,exchange,limits,references)
    if not execute or preview['state']!='READY':return preview
    opened=[]
    for plan_id,version in references:
        try:
            plan=service.show(plan_id,version)['plan']
            runner=plan_runner(service,exchange,limits,plan)
            result=runner.open(plan_id,version,execute=True)
        except (ValueError,ExchangeError) as exc:
            # A multi-symbol operation is not an exchange transaction. Preserve
            # already opened sessions and native stops; never retry an entry.
            report={'state':'PARTIAL_START_REVIEW_REQUIRED','opened':opened,
                    'failed_plan':{'plan_id':plan_id,'version':version},'automatic_resend':False,
                    'failure':_failure(exc)}
            service.store.event('account_start_review',report)
            return report
        if result.get('executed') is False or not result.get('session_id'):
            report={'state':'PARTIAL_START_REVIEW_REQUIRED','opened':opened,
                    'failed_plan':{'plan_id':plan_id,'version':version},'automatic_resend':False,
                    'failure':{'kind':'CONDITION_CHANGED','state':result.get('state')}}
            service.store.event('account_start_review',report)
            return report
        opened.append({'plan_id':plan_id,'version':version,'result':result})
    return {'state':'STARTED','opened':opened,'executed':True}


def monitor_account(service,exchange,limits,*,execute=False,iterations=1,interval=5,sleep=time.sleep):
    if type(iterations)is not int or iterations<0 or type(interval)is not int or not 1<=interval<=60:
        raise ValueError('Çoklu izleme turu/aralığı geçersiz.')
    blocked=set();paused=set();turn=0
    while iterations==0 or turn<iterations:
        sessions=service.store.sessions()
        if not sessions:
            yield {'state':'ACCOUNT_IDLE','executed':False};return
        turn+=1
        for session in sessions:
            if session['id'] in blocked|paused:continue
            runner=runner_for(service,exchange,limits,session)
            try:
                result=next(monitor_session(runner,session['id'],execute=execute,iterations=1))
            except (ValueError,ExchangeError) as exc:
                blocked.add(session['id'])
                result={'state':'SESSION_REVIEW_REQUIRED','session_id':session['id'],
                        'executed':False,'automatic_retry':False,'failure':_failure(exc)}
                service.store.event('account_session_review',result)
            result=result|{'session_id':session['id'],'account_turn':turn}
            if result.get('service_stopped') is True:paused.add(session['id'])
            service.store.runtime_health(session['id'],result,time.time())
            yield result
        remaining={s['id'] for s in service.store.sessions()}
        if remaining and remaining<=blocked|paused:
            yield {'state':'ACCOUNT_REVIEW_REQUIRED' if blocked else 'ACCOUNT_MONITOR_STOPPED','executed':False};return
        if not remaining or (iterations and turn>=iterations):return
        sleep(interval)


def supervise_account(service,exchange,limits,*,emit,execute=False,iterations=1,interval=5,
                      sleep=time.sleep,notification_queue=None,notification_chat=None):
    from .notifications import queue_session_report,chat_id
    if notification_queue is not None:notification_chat=chat_id(notification_chat)
    previous={};review=False;stopped=set()
    def output(report):
        if notification_queue is not None:
            key=report.get('session_id','account')
            signature=(report['state'],report.get('quantity'),report.get('position'),str(report.get('positions')))
            if signature!=previous.get(key) or report['state'] not in ('MANAGING','GRID_RUNNING','GRID_DRAINING','NEUTRAL_RUNNING','NEUTRAL_DRAINING'):
                queue_session_report(notification_queue,notification_chat,report)
            previous[key]=signature
        emit(report)
    try:
        for report in monitor_account(service,exchange,limits,execute=execute,iterations=iterations,
                                      interval=interval,sleep=sleep):
            output(report)
            review=review or report['state'] in ('SESSION_REVIEW_REQUIRED','ACCOUNT_REVIEW_REQUIRED')
            if report.get('service_stopped') is True:stopped.add(report['session_id'])
    except KeyboardInterrupt:
        if execute:_drain_grids(service,exchange,limits,output,stopped)
        raise
    if execute and not review:_drain_grids(service,exchange,limits,output,stopped)
    return not review


def _drain_grids(service,exchange,limits,emit,skip=()):
    for session in service.store.sessions():
        if session.get('engine') not in ('grid-v2','neutral-v2') or session['id'] in skip:continue
        try:
            report=runner_for(service,exchange,limits,session).stop(session['id'],close_position=False,execute=True)
        except (ValueError,ExchangeError):
            report={'state':'GRID_STOP_INCOMPLETE','session_id':session['id'],'executed':False}
        service.store.runtime_health(session['id'],report,time.time());emit(report)


def _failure(exc):
    if isinstance(exc,ExchangeError):
        return {'kind':'EXCHANGE','code':exc.code if type(exc.code)is int else None,
                'delivery_status':exc.delivery_status if exc.delivery_status in
                 ('NOT_SENT','REJECTED','UNKNOWN','READ_FAILED') else 'UNKNOWN'}
    return {'kind':'VALIDATION','message':'Plan/yetki/risk veya sahiplik kontrolü yeniden doğrulanmalı.'}
