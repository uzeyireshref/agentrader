"""Native trailing reductions bound to an owned SINGLE session; never blind repost."""
import json
import re
import time

from agentrader.bot.plans import digest,exact_fields,positive
from agentrader.bot.risk import number,RiskLimits
from agentrader.shared.exchange import ExchangeError

CREATE='CREATE_NATIVE_TRAILING'
QUERY='QUERY_NATIVE_TRAILING'
CANCEL='CANCEL_NATIVE_TRAILING'
OPERATIONS={CREATE,QUERY,CANCEL}
TERMINAL={'CANCELED','FINISHED','REJECTED','EXPIRED'}
NORMAL_TERMINAL={'FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED'}


def validate(operation,p):
    if operation==CREATE:
        exact_fields(p,'session_id quantity activate_price callback_rate working_type','Native trailing')
        if not isinstance(p['session_id'],str) or not re.fullmatch('v2-[a-f0-9]{28}',p['session_id']):
            raise ValueError('SINGLE oturum kimliği gerekli.')
        positive(p['quantity'],'Trailing miktarı');positive(p['activate_price'],'Trailing aktivasyonu')
        if not number('.1')<=positive(p['callback_rate'],'Callback')<=20:raise ValueError('Callback 0.1–20 aralığında olmalı.')
        if p['working_type'] not in ('MARK_PRICE','CONTRACT_PRICE'):raise ValueError('Trailing fiyat kaynağı geçersiz.')
    else:
        exact_fields(p,'create_command_id','Native trailing bağlantısı')
        if not isinstance(p['create_command_id'],str) or not re.fullmatch('cmd-[a-f0-9]{40}',p['create_command_id']):
            raise ValueError('Trailing oluşturma komutu kimliği gerekli.')


def bound_session(store,sid,account_ref,owner):
    row=store.db.execute('SELECT body FROM managed_sessions WHERE session_id=?',(sid,)).fetchone()
    if row is None:raise ValueError('Trailing oturumu bulunamadı.')
    s=json.loads(row['body']);ref=s['plan_ref']
    plan=store.db.execute('SELECT * FROM plan_versions WHERE plan_id=? AND version=?',(ref['plan_id'],ref['version'])).fetchone()
    if (s.get('engine')!='v2' or s.get('account_ref')!=account_ref or plan is None or plan['owner']!=owner or
            plan['digest']!=ref['digest'] or digest(s['plan'])!=ref['digest'] or plan['session_id']!=sid or
            plan['action_id']!=s['entry_id'] or s['plan']['execution']['strategy']!='SINGLE'):
        raise ValueError('Trailing plan/oturum/hesap sahipliği uyuşmuyor.')
    return s


def params_for(request,s,command_id):
    p=request['parameters'];validate(CREATE,p)
    if p['session_id']!=s['id'] or request['scope']['symbol']!=s['symbol']:raise ValueError('Trailing sembol/oturum kapsamı uyuşmuyor.')
    params={'symbol':s['symbol'],'side':'SELL' if s['plan']['direction']=='LONG' else 'BUY',
            'positionSide':s['prepared']['entry']['params']['positionSide'],'type':'TRAILING_STOP_MARKET',
            'quantity':str(number(p['quantity'])),'activatePrice':str(number(p['activate_price'])),
            'callbackRate':str(number(p['callback_rate'])),'workingType':p['working_type'],
            'algoType':'CONDITIONAL','clientAlgoId':'agt-nt-'+digest(command_id)[:28]}
    if s['plan']['position_mode']=='one-way':params['reduceOnly']='true'
    return params


def prepare(commands,request,command_id):
    if request['operation']==CREATE:
        s=bound_session(commands.store,request['parameters']['session_id'],commands.account_ref,commands.owner)
        if not s['active'] or s['status']!='PROTECTED':raise ValueError('Trailing için korunmuş etkin SINGLE oturumu gerekli.')
        params=params_for(request,s,command_id)
        from agentrader.bot.position_commands import session_actions,INCREASE
        extra=sum((number(a['proposal']['params']['quantity']) for a in session_actions(commands.store,s,commands.account_ref,commands.owner)
                   if a['operation']==INCREASE),number(0))
        if number(params['quantity'])>number(s['prepared']['quantity'])+extra:raise ValueError('Trailing miktarı oturumun yetkili miktarını aşamaz.')
        return {'session_id':s['id'],'plan_digest':s['plan_ref']['digest'],'params':params}
    row,body=commands._row(request['parameters']['create_command_id'])
    if body['request']['operation']!=CREATE or body['request']['scope']!=request['scope']:
        raise ValueError('Yalnız aynı kapsamdaki native trailing komutuna bağlanabilir.')
    return {'create_command_id':body['command_id']}


def source(commands,body):
    if body['request']['operation']!=CREATE:
        _,body=commands._row(body['request']['parameters']['create_command_id'])
    s=bound_session(commands.store,body['native']['session_id'],commands.account_ref,commands.owner)
    params=params_for(body['request'],s,body['command_id'])
    if body['native']!={'session_id':s['id'],'plan_digest':s['plan_ref']['digest'],'params':params}:
        raise ValueError('Trailing kayıtlı niyeti komutuyla uyuşmuyor.')
    return body,s,params


def session_proposals(store,s,account_ref,owner):
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='exchange_commands'").fetchone():return []
    result=[]
    for row in store.db.execute('SELECT * FROM exchange_commands WHERE operation=? AND account_ref=? AND owner=?',(CREATE,account_ref,owner)):
        body=json.loads(row['body'])
        if body.get('native',{}).get('session_id')!=s['id']:continue
        if digest(body)!=row['digest'] or body['native']['plan_digest']!=s['plan_ref']['digest']:
            raise ValueError('Trailing journal bütünlüğü bozuk.')
        params=params_for(body['request'],s,row['command_id'])
        if params!=body['native']['params']:raise ValueError('Trailing parametre kapsamı bozuk.')
        intent=store.intent(params['clientAlgoId'])
        if intent is None or intent['state']=='REJECTED':continue
        if intent['path']!='/fapi/v1/algoOrder' or json.loads(intent['params'])!=params:
            raise ValueError('Trailing gönderim niyeti uyuşmuyor.')
        result.append({'method':'POST','path':'/fapi/v1/algoOrder','params':params,'operation':'REDUCE'})
    return result


def read(exchange,store,params):
    """Read and bind algo and normal child namespaces separately; no writes."""
    actual=exchange.get('/fapi/v1/algoOrder',{'clientAlgoId':params['clientAlgoId']})
    if (not isinstance(actual,dict) or any(actual.get(k)!=params[k] for k in ('clientAlgoId','symbol','side','positionSide','workingType')) or
            actual.get('orderType',actual.get('type'))!='TRAILING_STOP_MARKET' or actual.get('algoType')!='CONDITIONAL' or
            type(actual.get('algoId')) is not int or actual['algoId']<=0 or
            actual.get('algoStatus') not in {'NEW','TRIGGERING','TRIGGERED'}|TERMINAL or
            number(actual.get('quantity'))!=number(params['quantity']) or
            str(actual.get('closePosition',False)).lower()!='false' or
            'reduceOnly' in params and str(actual.get('reduceOnly')).lower()!='true'):
        raise ValueError('Trailing borsa kimliği/azaltma kapsamı uyuşmuyor.')
    for field in ('activatePrice','callbackRate'):
        if field in actual and number(actual[field])!=number(params[field]):raise ValueError('Trailing parametre yanıtı uyuşmuyor.')
    previous=store.intent(params['clientAlgoId'])
    previous=(json.loads(previous['response']) or {}) if previous and previous['response'] else {}
    if not isinstance(previous,dict):raise ValueError('Trailing önceki yanıt kaydı geçersiz.')
    if previous.get('algoId') is not None and previous['algoId']!=actual['algoId']:raise ValueError('Trailing algo kimliği yeniden kullanılmış.')
    result={k:actual[k] for k in ('algoId','clientAlgoId','symbol','side','positionSide','workingType','quantity','algoStatus','actualOrderId') if k in actual}
    child=actual.get('actualOrderId');result['child']=None
    old_child=previous.get('actualOrderId')
    if old_child not in (None,'','0',0) and str(child)!=str(old_child):raise ValueError('Trailing alt emir kimliği değişti.')
    if child not in (None,'','0',0):
        if not str(child).isdigit() or int(child)<=0:raise ValueError('Trailing alt emir kimliği geçersiz.')
        order=exchange.get('/fapi/v1/order',{'symbol':params['symbol'],'orderId':int(child)})
        if (not isinstance(order,dict) or type(order.get('orderId')) is not int or order['orderId']!=int(child) or
                any(order.get(k)!=params[k] for k in ('symbol','side','positionSide')) or order.get('type')!='MARKET' or
                order.get('status') not in {'NEW','PARTIALLY_FILLED'}|NORMAL_TERMINAL or
                not 0<number(order.get('origQty'))<=number(params['quantity']) or
                not 0<=number(order.get('executedQty'))<=number(order.get('origQty')) or
                order['status']=='FILLED' and number(order['executedQty'])!=number(order['origQty']) or
                order['status'] in ('NEW','REJECTED') and number(order['executedQty'])!=0 or
                'reduceOnly' in params and str(order.get('reduceOnly')).lower()!='true'):
            raise ValueError('Trailing alt emri algo ile uyuşmuyor.')
        result['child']={k:order[k] for k in ('orderId','symbol','side','positionSide','status','origQty','executedQty')}
        if type(order.get('updateTime',0)) is not int or order.get('updateTime',0)<0:raise ValueError('Alt emir gözlem zamanı geçersiz.')
        result['child']['updateTime']=order.get('updateTime',0)
    return result


def observe_child(store,session_id,actual):
    child=actual['child']
    if child is None:return
    from agentrader.bot.order_journal import OrderJournal
    journal=OrderJournal(store)
    identity='native-child:'+digest([session_id,actual['symbol'],actual['clientAlgoId'],actual['algoId'],child['orderId']])
    journal.register(identity,session_id,child['symbol'],child['side'],child['origQty'])
    journal.observe(identity,digest(child),status='EXPIRED' if child['status']=='EXPIRED_IN_MATCH' else child['status'],
                    cumulative_filled=child['executedQty'],observed_ms=child['updateTime'])


def _observe(commands,body,*,cancel=False):
    creation,s,params=source(commands,body);cid=params['clientAlgoId']
    intent=commands.store.intent(cid)
    if intent is None:
        return commands._finish(body['command_id'],'NOT_SENT',{'client_algo_id':cid,'automatic_resend':False})
    if intent['state']=='REJECTED':return commands._finish(body['command_id'],'REJECTED',{'client_algo_id':cid,'automatic_resend':False})
    try:
        actual=read(commands.x,commands.store,params)
        observe_child(commands.store,s['id'],actual)
        commands.store.update(cid,actual['algoStatus'],actual)
        child=actual['child'];status=actual['algoStatus']
        resolved=(status in TERMINAL and (child is None and status in ('CANCELED','EXPIRED','REJECTED') or
                                         child is not None and child['status'] in NORMAL_TERMINAL)) if cancel else (
                    status in ('NEW','TRIGGERING','TRIGGERED') or child is not None or status in ('CANCELED','EXPIRED','REJECTED'))
        result={'client_algo_id':cid,'algo_id':actual['algoId'],'algo_status':status,'child':child,'automatic_resend':False,
                'cancel_outcome':('CANCELED' if status=='CANCELED' and child is None else 'RACE_OR_CHILD_OBSERVED') if cancel else None,
                'filled_quantity':child['executedQty'] if child else None}
        return commands._finish(body['command_id'],'APPLIED' if resolved else 'UNKNOWN',result)
    except (ValueError,ExchangeError) as exc:
        return commands._finish(body['command_id'],'READ_FAILED' if body['request']['operation']==QUERY else 'UNKNOWN',
                                {'client_algo_id':cid,'code':getattr(exc,'code',None),'automatic_resend':False})


def run(commands,body):
    from agentrader.bot.v2_runner import V2Runner
    from agentrader.bot.plans import PlanService
    from agentrader.bot.order_send_guard import validate_before_send
    operation=body['request']['operation'];creation,s,params=source(commands,body)
    if operation==QUERY:return _observe(commands,body)
    runner=V2Runner(PlanService(commands.store,commands.owner),commands.x,RiskLimits())
    if operation==CANCEL:
        try:
            actual=read(commands.x,commands.store,params)
            if actual['algoStatus'] not in TERMINAL:
                if time.time()>=body['expires_at']:return commands._finish(body['command_id'],'EXPIRED',{'automatic_resend':False})
                runner._cancel('/fapi/v1/algoOrder',{'clientAlgoId':params['clientAlgoId']})
        except (ValueError,ExchangeError):return _observe(commands,body,cancel=True)
        return _observe(commands,body,cancel=True)
    if commands.store.intent(params['clientAlgoId']) is not None:return _observe(commands,body)
    try:
        outcome=runner.manage(s['id'],execute=False)
        if outcome.get('status')!='protected':raise ValueError('Trailing öncesi etkin koruma doğrulanmalı.')
        s=runner._session(s['id']);entry=runner._entry(s)
        if entry['status'] not in NORMAL_TERMINAL:raise ValueError('Trailing öncesi giriş kalanı terminal olmalı.')
        protections={p['params']['clientAlgoId']:commands.x.get('/fapi/v1/algoOrder',{'clientAlgoId':p['params']['clientAlgoId']}) for p in s['protections']}
        amount=runner._owned(s,entry,protections)
        if not 0<number(params['quantity'])<=abs(amount):raise ValueError('Trailing miktarı sahip olunan pozisyonu aşıyor.')
        for proposal in session_proposals(commands.store,s,commands.account_ref,commands.owner):
            existing=read(commands.x,commands.store,proposal['params'])
            if (existing['algoStatus'] not in TERMINAL or
                    existing['child'] is not None and existing['child']['status'] not in NORMAL_TERMINAL):
                raise ValueError('Oturumda zaten etkin bir native trailing var.')
        proposal={'params':params,'operation':'REDUCE'}
        commands.x.sync_time()
        validate_before_send(commands.x,[proposal],s['plan']['position_mode'],runner.limits.max_age_seconds)
    except (ValueError,ExchangeError):return commands._finish(body['command_id'],'NOT_SENT',{'reason':'PRECONDITION_FAILED','automatic_resend':False})
    if time.time()>=body['expires_at']:return commands._finish(body['command_id'],'EXPIRED',{'automatic_resend':False})
    if not commands.store.reserve(params['clientAlgoId'],'/fapi/v1/algoOrder',params):return _observe(commands,body)
    if time.time()>=body['expires_at']:
        commands.store.update(params['clientAlgoId'],'REJECTED')
        return commands._finish(body['command_id'],'NOT_SENT',{'reason':'EXPIRED_BEFORE_DELIVERY','automatic_resend':False})
    try:commands.x.request('POST','/fapi/v1/algoOrder',params)
    except ExchangeError as exc:
        if exc.delivery_status in ('REJECTED','NOT_SENT'):
            commands.store.update(params['clientAlgoId'],'REJECTED')
            return commands._finish(body['command_id'],'NOT_SENT' if exc.delivery_status=='NOT_SENT' else 'REJECTED',{'code':exc.code,'automatic_resend':False})
        commands.store.update(params['clientAlgoId'],'UNKNOWN')
    return _observe(commands,body)


def reconcile(commands,body):return _observe(commands,body,cancel=body['request']['operation']==CANCEL)
