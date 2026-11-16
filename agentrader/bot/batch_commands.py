"""User-authorized native batches; independent member results and no repost."""
import copy
import json
import re
import time

from agentrader.bot.plans import PlanService,canonical,digest,exact_fields,timestamp,transaction
from agentrader.bot.position_commands import risk_limits
from agentrader.bot.risk import number,RiskLimits
from agentrader.shared.exchange import ExchangeError

CREATE='BATCH_CREATE_ORDERS';AMEND='BATCH_AMEND_ORDERS';CANCEL='BATCH_CANCEL_ORDERS'
OPERATIONS={CREATE,AMEND,CANCEL}


def validate(op,p):
    if op==CREATE:
        from agentrader.bot.single_commands import validate_reference
        exact_fields(p,'plans risk_limits','Toplu giriş')
        if not isinstance(p['plans'],list) or not 1<=len(p['plans'])<=5:raise ValueError('Toplu giriş 1–5 yetkili plan gerektirir.')
        for ref in p['plans']:validate_reference(ref)
        if len({(r['plan_id'],r['version']) for r in p['plans']})!=len(p['plans']):raise ValueError('Tekrarlı toplu plan.')
        risk_limits(p['risk_limits'])
    elif op==AMEND:
        exact_fields(p,'session_id changes','Toplu amend')
        if not isinstance(p['session_id'],str) or not 1<=len(p['session_id'])<=128:raise ValueError('Toplu amend oturumu gerekli.')
        if not isinstance(p['changes'],list) or not 1<=len(p['changes'])<=5:raise ValueError('Toplu amend 1–5 üye gerektirir.')
        ids=[]
        for c in p['changes']:
            exact_fields(c,'client_id quantity price','Toplu amend üyesi')
            if not isinstance(c['client_id'],str) or not re.fullmatch(r'[.A-Za-z:/0-9_-]{1,36}',c['client_id']):raise ValueError('Emir kimliği geçersiz.')
            if number(c['quantity'])<=0 or number(c['price'])<=0:raise ValueError('Amend miktar/fiyatı pozitif olmalı.')
            ids.append(c['client_id'])
        if len(set(ids))!=len(ids):raise ValueError('Tekrarlı amend üyesi.')
    else:
        from agentrader.bot.cancel_commands import validate as validate_cancel,SELECTED
        validate_cancel(SELECTED,p)
        if len(p['targets'])>10 or any(t['namespace']!='NORMAL' for t in p['targets']):raise ValueError('Native batch iptal 1–10 normal emir destekler; algo için seçili iptali kullanın.')


def _plans(commands,request,*,authorized=True):
    service=PlanService(commands.store,commands.owner);rows=[]
    for ref in request['parameters']['plans']:
        row=service.show(ref['plan_id'],ref['version']);plan=row['plan']
        if (row['digest']!=ref['plan_digest'] or plan['schema_version']!=2 or plan['execution']['strategy']!='SINGLE' or
                plan['entry'].get('order_options',{})!=ref['entry_options']):raise ValueError('Toplu plan kapsamı uyuşmuyor.')
        if authorized and (row['state']!='AUTHORIZED' or time.time()>=min(row['approval_until'],timestamp(plan['expires_at']))):raise ValueError('Her toplu plan ayrıca yetkilendirilmiş olmalı.')
        rows.append(row)
    symbols=[r['plan']['symbol'] for r in rows]
    if len(set(symbols))!=len(symbols) or sorted(symbols)!=sorted(request['scope']['symbols']):raise ValueError('Toplu giriş farklı sembollü planların tam kapsamını gerektirir.')
    if len({r['plan']['position_mode'] for r in rows})!=1:raise ValueError('Toplu giriş ortak hesap modu gerektirir.')
    return service,rows


def _inputs(commands,request,rows,*,reserved=False):
    from agentrader.bot.v2_runner import V2Runner
    from agentrader.bot.v2_preflight import collect_flat_snapshot,prepare_single
    from agentrader.bot.portfolio import Exposure
    from agentrader.bot.cancel_timers import assert_entry_allowed
    from agentrader.integration.chart_execution import guard_chart_entry
    from agentrader.bot.recovery_guardian import require_guardian
    limits=risk_limits(request['parameters']['risk_limits']);runner=V2Runner(PlanService(commands.store,commands.owner),commands.x,limits)
    if commands.store.halt_reason() or commands.store.unresolved_account_command():raise ValueError('Çözülmemiş hesap/durdurma varken toplu giriş yapılamaz.')
    start=time.time();prepared=[];snaps=[]
    for row in rows:
        plan=row['plan'];assert_entry_allowed(commands.store,plan['symbol'],commands.account_ref)
        guard_chart_entry(runner.service,commands.x,limits,plan)
        if plan.get('analysis_ref','').startswith('shadow-event:'):require_guardian(commands.store.path,commands.owner,commands.x,limits)
        snap=collect_flat_snapshot(commands.x,plan['symbol'],limits)
        item=prepare_single(plan,snap,limits)
        if item['state']!='READY':raise ValueError('Toplu planların hepsi gönderime hazır olmalı.')
        prepared.append(item);snaps.append(snap)
    exposures=[] if reserved else [Exposure(**e) for p in prepared for e in p['exposures']]
    for snap in snaps:runner.book.evaluate(snap,limits,exchange=commands.x,extra_exposures=exposures)
    if not 0<=time.time()-start<=limits.max_age_seconds:raise ValueError('Toplu giriş görünümü eskidi.')
    return runner,prepared,snaps


def _amend_service(commands):
    from agentrader.bot.order_amend import OrderAmendments
    return OrderAmendments(PlanService(commands.store,commands.owner),commands.x,RiskLimits())


def prepare(commands,request,command_id,ttl):
    op=request['operation'];p=request['parameters']
    if op==CANCEL:
        from agentrader.bot.cancel_commands import prepare as preview,SELECTED
        return preview(commands,request|{'operation':SELECTED})
    if op==AMEND:
        service=_amend_service(commands);s,_=service._session(p['session_id'])
        if s['symbol']!=request['scope']['symbol']:raise ValueError('Toplu amend sembolü uyuşmuyor.')
        return service.prepare_batch(p['session_id'],p['changes'],ttl)
    if commands.store.sessions():raise ValueError('İlk toplu giriş adaptörü boş hesap ve etkin oturumsuz journal gerektirir.')
    _,rows=_plans(commands,request);_,prepared,_=_inputs(commands,request,rows)
    return {'members':[{'plan_id':r['plan']['plan_id'],'version':r['plan']['version'],'prepared':p} for r,p in zip(rows,prepared)]}


def _protect_observed(runner,s):
    """Protect this proven filled symbol even if another batch member is unknown."""
    from agentrader.bot.history import account_trades
    entry=runner._entry(s)
    if number(entry['executedQty'])<=0:return
    start=time.time();symbol=s['symbol'];ps=entry['positionSide'];sign=1 if entry['side']=='BUY' else -1
    trades=account_trades(runner.x,symbol,s['started_ms'])
    positions=runner.x.get('/fapi/v3/positionRisk',{'symbol':symbol})
    normal=runner.x.get('/fapi/v1/openOrders',{'symbol':symbol});algos=runner.x.get('/fapi/v1/openAlgoOrders',{'symbol':symbol})
    if (any(str(t['orderId'])!=str(entry['orderId']) or t['side']!=entry['side'] or t.get('positionSide',ps)!=ps for t in trades) or
            sum((number(t['qty']) for t in trades),number(0))!=number(entry['executedQty']) or
            any(p['symbol']!=symbol or p['positionSide']!=ps and number(p['positionAmt'])!=0 for p in positions) or
            sum((number(p['positionAmt']) for p in positions if p['positionSide']==ps),number(0))!=sign*number(entry['executedQty']) or
            any(o['clientOrderId']!=s['entry_id'] for o in normal) or
            any(o['clientAlgoId'] not in {p['params']['clientAlgoId'] for p in s['protections']} for o in algos)):
        raise ValueError('Toplu gerçekleşen sembol sahipliği doğrulanamadı.')
    if not 0<=time.time()-start<=runner.limits.max_age_seconds:raise ValueError('Toplu koruma görünümü eskidi.')
    for proposal in s['protections']:runner._post(s,proposal)


def _create(commands,body):
    from agentrader.bot.portfolio import Exposure
    from agentrader.bot.batch_create import NativeBatchCreate
    request=body['request'];sessions=[];runner=None
    try:
        if commands.store.sessions():raise ValueError('Toplu giriş öncesi hesapta oturum oluştu.')
        service,rows=_plans(commands,request);runner,prepared,snaps=_inputs(commands,request,rows)
        frozen=body['batch']['members']
        if len(frozen)!=len(rows):raise ValueError('Toplu giriş üyeliği değişti.')
        for r,current,saved in zip(rows,prepared,frozen):
            if (saved['plan_id'],saved['version'])!=(r['plan']['plan_id'],r['plan']['version']) or current['entry']!=saved['prepared']['entry'] or current['exposures']!=saved['prepared']['exposures']:
                raise ValueError('Toplu giriş miktarı/fiyatı/risk zarfı değişti; yeni önizleme gerekli.')
        if time.time()>=body['expires_at']:raise ValueError('Toplu giriş yetkisi doldu.')
        created=[]
        with transaction(commands.store) as db:
            for row,p,snap in zip(rows,prepared,snaps):
                plan=row['plan'];sid='v2-'+digest([plan['plan_id'],plan['version'],row['digest']])[:28]
                runner.book.reserve(sid,commands.owner,row['digest'],[Exposure(**e) for e in p['exposures']],snap,runner.limits,_db=db)
                cid=service.claim(plan['plan_id'],plan['version'],sid,_db=db);p=copy.deepcopy(p);p['entry']['params']['newClientOrderId']=cid
                s={'id':sid,'engine':'v2','symbol':plan['symbol'],'active':True,'status':'OPENING','entry_id':cid,'account_ref':commands.account_ref,
                   'started_ms':int(time.time()*1000)+getattr(commands.x,'offset_ms',0),'plan':plan,'plan_ref':{'plan_id':plan['plan_id'],'version':plan['version'],'digest':row['digest']},
                   'prepared':p,'protections':[],'exits':[]}
                for i,protection in enumerate(p['protections']):
                    protection['params']['clientAlgoId']=runner._id(s,'protection-'+str(i));s['protections'].append(protection)
                db.execute('INSERT INTO managed_sessions VALUES(?,?,1)',(sid,canonical(s)));created.append(s)
        sessions=created
        expected=digest(sorted([s['prepared']['entry']['params'] for s in sessions],key=lambda p:p['newClientOrderId']))
        def authorize(params,phase):
            if digest(params)!=expected or time.time()>=body['expires_at']:raise ValueError('Toplu giriş yetkisi/kapsamı değişti.')
            for s in sessions:runner._scope(s,entry=True)
            _,latest,_=_inputs(commands,request,rows,reserved=True)
            if any(p['entry']!=f['prepared']['entry'] or p['exposures']!=f['prepared']['exposures'] for p,f in zip(latest,frozen)):
                raise ValueError('Son toplu giriş görünümü değişti.')
            if time.time()>=body['expires_at']:raise ValueError('Toplu komut gönderim öncesi sona erdi.')
            for s in sessions:runner._scope(s,entry=True)
            return True
        for s in sessions:runner.book.mark_submitted(s['id'])
        NativeBatchCreate(commands.x,commands.store,body['command_id'],max_age_seconds=runner.limits.max_age_seconds,
            owners={s['entry_id']:s['id'] for s in sessions}).submit([s['prepared']['entry'] for s in sessions],authorize)
    except (ValueError,ExchangeError):
        # Claims/reservations already persisted are conservative; never start a new batch.
        pass
    if runner is not None:
        for s in sessions:
            try:
                intent=commands.store.intent(s['entry_id'])
                if intent and intent['state']!='REJECTED':_protect_observed(runner,s)
            except (ValueError,ExchangeError):commands.store.halt('Toplu giriş koruması/sahipliği uzlaştırılmalı.')
        for s in sessions:
            try:runner.manage(s['id'],execute=True)
            except (ValueError,ExchangeError):runner.service.outcome(s['plan']['plan_id'],s['plan']['version'],'NEEDS_REVIEW')
    return reconcile(commands,body)


def run(commands,body):
    op=body['request']['operation']
    if op==CREATE:return _create(commands,body)
    if op==CANCEL:
        from agentrader.bot.cancel_commands import run as cancel
        return cancel(commands,body,batch=True)
    service=_amend_service(commands);link=body['batch']
    try:service.apply_batch(link['batch_id'],link['digest'],authorize=lambda:time.time()<body['expires_at'])
    except (ValueError,ExchangeError):pass
    return reconcile(commands,body)


def reconcile(commands,body):
    op=body['request']['operation']
    if op==CANCEL:
        from agentrader.bot.cancel_commands import reconcile as cancel
        return cancel(commands,body)
    if op==AMEND:
        service=_amend_service(commands);link=body['batch'];row,_,_=service._batch(link['batch_id'])
        if row['digest']!=link['digest']:raise ValueError('Toplu amend üst bağlantısı bozuk.')
        result=service.reconcile_batch(link['batch_id'])
        if result['state'] in ('PREPARED','CANCELED','EXPIRED'):
            if result['state']=='PREPARED':result=service.cancel_batch(link['batch_id'],link['digest'])
            state='NOT_SENT'
        else:state='APPLIED' if result['state']=='APPLIED' else 'FINAL_WITH_ERRORS' if result['state']=='FINAL_WITH_ERRORS' else 'UNKNOWN'
        return commands._finish(body['command_id'],state,result)
    from agentrader.bot.single_commands import reconcile as single
    from agentrader.bot.v2_runner import V2Runner
    service,rows=_plans(commands,body['request'],authorized=False);results=[]
    runner=V2Runner(service,commands.x,risk_limits(body['request']['parameters']['risk_limits']))
    # SINGLE result verification is read-only; use a result sink, never mutate this parent per member.
    class Sink:
        def __init__(self):self.__dict__.update(commands.__dict__)
        def _finish(self,command_id,state,result):return {'state':state,'result':result}
    for ref,row in zip(body['request']['parameters']['plans'],rows):
        child={'request':{'parameters':ref,'scope':{'symbol':row['plan']['symbol']}}}
        try:
            observed=None
            if row['session_id'] and row['state']!='CLOSED':observed=runner.manage(row['session_id'],execute=False)
            result=single(Sink(),child|{'command_id':body['command_id']})
            result['result']['risk_profile']='EXPLICIT_BATCH_RISK_LIMITS'
            if result['result'].get('entry_state')=='NO_RECORDED_INTENT':result['state']='NOT_SENT'
            if result['result'].get('entry_state')=='REJECTED':result['state']='REJECTED'
            if observed and observed['state']=='ENTRY_PENDING':
                result['state']='APPLIED';result['result']['phase']='ENTRY_ACCEPTED_PENDING'
        except (ValueError,ExchangeError):result={'state':'UNKNOWN','result':{'plan_id':ref['plan_id'],'phase':'UNRESOLVED'}}
        results.append(result)
    states={r['state'] for r in results}
    state=('APPLIED' if states=={'APPLIED'} else 'NOT_SENT' if states=={'NOT_SENT'} else
           'FINAL_WITH_ERRORS' if states<={'APPLIED','REJECTED','NOT_SENT'} else 'UNKNOWN')
    return commands._finish(body['command_id'],state,{'orders':results,'automatic_resend':False,'meaning':'INDEPENDENT_SINGLE_LIFECYCLES'})


def cancel_prepared(commands,body):
    if body['request']['operation']==AMEND:
        link=body['batch'];service=_amend_service(commands);row,_,_=service._batch(link['batch_id'])
        if row['digest']!=link['digest']:raise ValueError('Toplu amend üst bağlantısı bozuk.')
        if row['state']!='CANCELED':service.cancel_batch(link['batch_id'],link['digest'])
