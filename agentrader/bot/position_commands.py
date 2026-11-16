"""Explicit position actions with independent authority, risk and child identities."""
import json
import re
import time
from dataclasses import asdict,replace
from decimal import ROUND_FLOOR

from agentrader.bot.plans import canonical,digest,exact_fields,positive,timestamp,transaction
from agentrader.bot.risk import number,RiskLimits
from agentrader.bot.native_trailing import bound_session
from agentrader.shared.exchange import ExchangeError

INCREASE='INCREASE_POSITION';REDUCE='REDUCE_POSITION';CLOSE='CLOSE_POSITION';REVERSE='REVERSE_POSITION'
OPERATIONS={INCREASE,REDUCE,CLOSE,REVERSE}
TERMINAL={'FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED'}


def risk_limits(value):
    exact_fields(value,' '.join(RiskLimits.__dataclass_fields__),'Pozisyon risk sınırları')
    values={}
    for key in RiskLimits.__dataclass_fields__:
        if key in ('max_positions','max_age_seconds'):
            if type(value[key]) is not int or value[key]<1:raise ValueError('Risk sayısı/yaşı pozitif tamsayı olmalı.')
            values[key]=value[key]
        else:values[key]=positive(value[key],'Risk sınırı')
    if values['max_age_seconds']>15:raise ValueError('Pozisyon görünümü en fazla 15 saniye olabilir.')
    return RiskLimits(**values)


def validate(operation,p):
    fields={INCREASE:'session_id quantity price_floor price_ceiling risk_limits',REDUCE:'session_id reduction',
            CLOSE:'session_id',REVERSE:'session_id next_plan_id next_version next_digest risk_limits'}
    exact_fields(p,fields[operation],'Pozisyon komutu')
    if not isinstance(p['session_id'],str) or not re.fullmatch('v2-[a-f0-9]{28}',p['session_id']):raise ValueError('SINGLE oturumu gerekli.')
    if operation==INCREASE:
        positive(p['quantity'],'Artış miktarı')
        if positive(p['price_floor'],'Alt fiyat')>positive(p['price_ceiling'],'Üst fiyat'):raise ValueError('Fiyat aralığı ters.')
    if operation==REDUCE:
        r=p['reduction'];exact_fields(r,'kind value','Azaltma')
        if r['kind'] not in ('QUANTITY','PERCENT'):raise ValueError('Azaltma miktar veya yüzde olmalı.')
        value=positive(r['value'],'Azaltma değeri')
        if r['kind']=='PERCENT' and value>100:raise ValueError('Azaltma yüzdesi en fazla 100 olabilir.')
    if operation in (INCREASE,REVERSE):risk_limits(p['risk_limits'])
    if operation==REVERSE:
        if (not isinstance(p['next_plan_id'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',p['next_plan_id']) or
                type(p['next_version']) is not int or p['next_version']<1 or
                not isinstance(p['next_digest'],str) or not re.fullmatch('[a-f0-9]{64}',p['next_digest'])):
            raise ValueError('Ters yön planının kimliği geçersiz.')


def next_plan(store,request,owner):
    from agentrader.bot.plans import validate_plan
    p=request['parameters'];row=store.db.execute('SELECT * FROM plan_versions WHERE plan_id=? AND version=?',
                                               (p['next_plan_id'],p['next_version'])).fetchone()
    if row is None:raise ValueError('Ters yön planı önceden oluşturulmalı.')
    plan=validate_plan(json.loads(row['body']))
    if (row['owner']!=owner or row['digest']!=p['next_digest'] or digest(plan)!=p['next_digest'] or
            plan['schema_version']!=2 or plan['execution']['strategy']!='SINGLE' or plan['entry']['condition']!='IMMEDIATE' or
            plan['symbol']!=request['scope']['symbol']):raise ValueError('Ters yön planı kapsamı uyuşmuyor.')
    return dict(row),plan


def prepare(commands,request):
    p=request['parameters'];op=request['operation'];s=bound_session(commands.store,p['session_id'],commands.account_ref,commands.owner)
    if not s['active'] or s['symbol']!=request['scope']['symbol']:raise ValueError('Etkin sahip olunan aynı sembollü oturum gerekli.')
    if op in (INCREASE,REDUCE) and len(s['plan']['targets'])!=1:raise ValueError('Artırma/azaltma ilk adaptörü tek hedefli SINGLE gerektirir.')
    if op==INCREASE:
        sign=1 if s['plan']['direction']=='LONG' else -1
        in_protection=lambda value:sign*(number(value)-number(s['plan']['stop']))>0 and sign*(number(s['plan']['targets'][0]['price'])-number(value))>0
        if (s['status']!='PROTECTED' or s.get('stop_transitions') or s['plan']['management'].get('trailing') is not None or
                not s['prepared'].get('exposures') or
                not in_protection(p['price_floor']) or not in_protection(p['price_ceiling'])):
            raise ValueError('Artırma için tam Close-All koruması, ilk risk zarfı ve onaylı fiyat aralığı gerekli.')
    if op==REVERSE:
        if any(peer['id']!=s['id'] for peer in commands.store.sessions()):
            raise ValueError('İlk yön değiştirme adaptörü tek etkin oturum gerektirir.')
        row,plan=next_plan(commands.store,request,commands.owner)
        if (row['state'] not in ('PENDING_APPROVAL','PENDING_ACTIVATION') or timestamp(plan['expires_at'])<=time.time() or
                plan['direction']==s['plan']['direction'] or plan['position_mode']!=s['plan']['position_mode'] or
                plan['execution']['leverage']!=s['plan']['execution']['leverage'] or
                plan['execution']['margin_mode']!=s['plan']['execution']['margin_mode']):
            raise ValueError('Ters plan karşı yönde, aynı hesap ayarlarında ve ayrı onay bekliyor olmalı.')
    return {'session_id':s['id'],'plan_digest':s['plan_ref']['digest']}


def session_actions(store,s,account_ref,owner):
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='position_actions'").fetchone():return []
    result=[]
    rows=store.db.execute('''SELECT a.*,c.body AS command_body,c.digest AS command_digest,c.owner,c.account_ref,c.operation
        FROM position_actions a JOIN exchange_commands c ON c.command_id=a.command_id WHERE c.owner=? AND c.account_ref=?''',(owner,account_ref))
    for row in rows:
        command=json.loads(row['command_body']);request=command['request']
        if request['parameters'].get('session_id')!=s['id']:continue
        body=json.loads(row['body'])
        if (digest(command)!=row['command_digest'] or digest(body)!=row['digest'] or body['command_digest']!=row['command_digest'] or
                command['position']!={'session_id':s['id'],'plan_digest':s['plan_ref']['digest']} or request['scope']['symbol']!=s['symbol']):
            raise ValueError('Pozisyon ek niyeti yetkili kapsamıyla uyuşmuyor.')
        validate(row['operation'],request['parameters']);params=body['proposal']['params'];inc=row['operation']==INCREASE
        side=('BUY' if s['plan']['direction']=='LONG' else 'SELL') if inc else ('SELL' if s['plan']['direction']=='LONG' else 'BUY')
        expected={'symbol':s['symbol'],'side':side,'positionSide':s['prepared']['entry']['params']['positionSide'],
                  'type':'LIMIT' if inc else 'MARKET','quantity':params['quantity'],'newClientOrderId':'agt-pos-'+digest(row['command_id'])[:27]}
        p=request['parameters']
        if inc:expected.update(price=str(number(p['price_ceiling'] if side=='BUY' else p['price_floor'])),timeInForce='IOC')
        elif s['plan']['position_mode']=='one-way':expected['reduceOnly']='true'
        if params!=expected or number(params['quantity'])<=0:raise ValueError('Pozisyon alt emir parametreleri uyuşmuyor.')
        if inc and number(params['quantity'])!=number(p['quantity']):raise ValueError('Artış miktarı değişmiş.')
        if not inc and number(params['quantity'])>number(body['starting_quantity']):raise ValueError('Azaltma başlangıç pozisyonunu aşıyor.')
        if row['operation'] in (CLOSE,REVERSE) and number(params['quantity'])!=number(body['starting_quantity']):raise ValueError('Tam kapanış miktarı değişmiş.')
        if row['operation']==REDUCE:
            approved=number(p['reduction']['value'])
            if (p['reduction']['kind']=='QUANTITY' and number(params['quantity'])!=approved or
                    p['reduction']['kind']=='PERCENT' and number(params['quantity'])>number(body['starting_quantity'])*approved/100):
                raise ValueError('Azaltma miktarı somut yetkiyi aşıyor.')
        if inc:
            from agentrader.bot.portfolio import Exposure
            expected_exposure=replace(Exposure(**s['prepared']['exposures'][0]),quantity=params['quantity'],
                entry=str(number(p['price_ceiling'] if side=='BUY' else p['price_floor'])),notional_price=str(number(p['price_ceiling'])))
            if body['exposure']!=asdict(expected_exposure):raise ValueError('Artırma ek risk zarfı alt emirle uyuşmuyor.')
        intent=store.intent(params['newClientOrderId'])
        if intent is None:raise ValueError('Pozisyon alt niyeti eksik.')
        if intent['path']!='/fapi/v1/order' or json.loads(intent['params'])!=params:raise ValueError('Pozisyon gönderim günlüğü bozuk.')
        if intent['state']=='REJECTED':continue
        result.append({'command_id':row['command_id'],'operation':row['operation'],'proposal':body['proposal'],'exposure':body.get('exposure')})
    return result


def extra_exposures(store,reservation_id,account_ref,owner):
    from agentrader.bot.portfolio import Exposure
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='position_actions'").fetchone():return []
    if not store.db.execute('''SELECT 1 FROM position_actions a JOIN exchange_commands c ON c.command_id=a.command_id
        WHERE c.account_ref=? AND c.owner=? AND c.operation=? AND json_extract(c.body,'$.request.parameters.session_id')=?''',
        (account_ref,owner,INCREASE,reservation_id)).fetchone():return []
    if not store.db.execute('SELECT 1 FROM managed_sessions WHERE session_id=?',(reservation_id,)).fetchone():return []
    s=bound_session(store,reservation_id,account_ref,owner)
    result=[]
    for action in session_actions(store,s,account_ref,owner):
        if action['operation']!=INCREASE:continue
        exposure=Exposure(**action['exposure']);intent=store.intent(action['proposal']['params']['newClientOrderId'])
        observed=(json.loads(intent['response']) or {}) if intent['response'] else {}
        if number(observed.get('executedQty','0'))>0:
            actual=number(observed.get('avgPrice','0'))
            if actual<=0:raise ValueError('Ek risk için gerçek dolum fiyatı gerekli.')
            exposure=replace(exposure,notional_price=str(max(number(exposure.notional_price),actual)),
                entry=str(max(number(exposure.entry),actual) if exposure.direction=='LONG' else min(number(exposure.entry),actual)))
        result.append(exposure)
    return result


def read_order(exchange,store,params,owner,*,write=False):
    actual=exchange.get('/fapi/v1/order',{'symbol':params['symbol'],'origClientOrderId':params['newClientOrderId']})
    if (not isinstance(actual,dict) or actual.get('clientOrderId')!=params['newClientOrderId'] or
            type(actual.get('orderId')) is not int or actual['orderId']<=0 or
            any(actual.get(k)!=params[k] for k in ('symbol','side','positionSide','type')) or
            number(actual.get('origQty'))!=number(params['quantity']) or
            not 0<=number(actual.get('executedQty'))<=number(params['quantity']) or
            actual.get('status') not in {'NEW','PARTIALLY_FILLED'}|TERMINAL or
            actual['status']=='FILLED' and number(actual['executedQty'])!=number(params['quantity']) or
            actual['status'] in ('NEW','REJECTED') and number(actual['executedQty'])!=0 or
            'reduceOnly' in params and str(actual.get('reduceOnly')).lower()!='true' or
            params['type']=='LIMIT' and (number(actual.get('price'))!=number(params['price']) or actual.get('timeInForce')!='IOC')):
        raise ValueError('Pozisyon alt emri kimlik/miktar kapsamı uyuşmuyor.')
    if number(actual['executedQty'])>0 and number(actual.get('avgPrice',0))<=0:raise ValueError('Pozisyon dolum fiyatı gerekli.')
    prior=store.intent(params['newClientOrderId']);previous=(json.loads(prior['response']) or {}) if prior and prior['response'] else {}
    if previous.get('orderId') is not None and previous['orderId']!=actual['orderId']:raise ValueError('Pozisyon istemci kimliği yeniden kullanılmış.')
    if write:
        from agentrader.bot.order_journal import OrderJournal
        journal=OrderJournal(store);journal.register(params['newClientOrderId'],owner,params['symbol'],params['side'],params['quantity'])
        observed=actual.get('updateTime',0)
        journal.observe(params['newClientOrderId'],digest(actual),status='EXPIRED' if actual['status']=='EXPIRED_IN_MATCH' else actual['status'],
                        cumulative_filled=actual['executedQty'],observed_ms=observed)
        store.update(params['newClientOrderId'],actual['status'],actual)
    return actual


def _context(commands,body,limits):
    from agentrader.bot.v2_runner import V2Runner
    from agentrader.bot.plans import PlanService
    s=bound_session(commands.store,body['position']['session_id'],commands.account_ref,commands.owner)
    if body['position']!={'session_id':s['id'],'plan_digest':s['plan_ref']['digest']}:raise ValueError('Pozisyon komutu plan bağı bozuk.')
    runner=V2Runner(PlanService(commands.store,commands.owner),commands.x,limits)
    return runner,s


def _verify_active(runner,sid):
    session=runner._session(sid);entry=runner._entry(session)
    protections={x['params']['clientAlgoId']:runner.x.get('/fapi/v1/algoOrder',{'clientAlgoId':x['params']['clientAlgoId']})
                 for x in session['protections'] if runner.store.intent(x['params']['clientAlgoId'])}
    return abs(runner._owned(session,entry,protections))


def run(commands,body):
    from agentrader.bot.order_rules import validate_order
    from agentrader.bot.order_send_guard import validate_before_send
    from agentrader.bot.v2_preflight import joint_step
    op=body['request']['operation'];p=body['request']['parameters'];limits=risk_limits(p['risk_limits']) if op in (INCREASE,REVERSE) else RiskLimits()
    runner,s=_context(commands,body,limits)
    try:
        if prepare(commands,body['request'])!=body['position']:raise ValueError('Pozisyon yetkisi gönderim öncesi değişti.')
        s=runner._session(s['id']);entry=runner._entry(s)
        if entry['status'] not in TERMINAL:
            runner._cancel('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':s['entry_id']});entry=runner._entry(s)
            if entry['status'] not in TERMINAL:raise ValueError('Başlangıç giriş kalanı terminal değil.')
        protections={x['params']['clientAlgoId']:commands.x.get('/fapi/v1/algoOrder',{'clientAlgoId':x['params']['clientAlgoId']})
                     for x in s['protections'] if commands.store.intent(x['params']['clientAlgoId'])}
        amount=abs(runner._owned(s,entry,protections))
        if amount<=0:raise ValueError('Değiştirilecek sahip olunan pozisyon yok.')
        info=next(x for x in commands.x.get('/fapi/v1/exchangeInfo')['symbols'] if x['symbol']==s['symbol'])
        filters={f['filterType']:f for f in info['filters']};step=joint_step(filters['LOT_SIZE']['stepSize'],filters.get('MARKET_LOT_SIZE',filters['LOT_SIZE'])['stepSize'])
        q=(number(p['quantity']) if op==INCREASE else number(p['reduction']['value']) if op==REDUCE and p['reduction']['kind']=='QUANTITY' else
           (amount*number(p['reduction']['value'])/100/step).to_integral_value(rounding=ROUND_FLOOR)*step if op==REDUCE else amount)
        if q<=0 or op!=INCREASE and q>amount:raise ValueError('Pozisyon miktarı sıfır veya kalan pozisyonu aşıyor.')
        side=('BUY' if s['plan']['direction']=='LONG' else 'SELL') if op==INCREASE else ('SELL' if s['plan']['direction']=='LONG' else 'BUY')
        params={'symbol':s['symbol'],'side':side,'positionSide':s['prepared']['entry']['params']['positionSide'],
                'type':'LIMIT' if op==INCREASE else 'MARKET','quantity':str(q),'newClientOrderId':'agt-pos-'+digest(body['command_id'])[:27]}
        exposure=None
        if op==INCREASE:
            from agentrader.bot.cancel_timers import assert_entry_allowed
            assert_entry_allowed(commands.store,s['symbol'],commands.account_ref)
            from agentrader.bot.portfolio import Exposure
            from agentrader.bot.account_ownership import AccountOwnership
            from agentrader.bot.v2_preflight import collect_flat_snapshot
            if commands.store.halt_reason() or commands.store.unresolved_account_command():raise ValueError('Risk artışı durdurulmuş.')
            if runner.manage(s['id'],False).get('status')!='protected':raise ValueError('Artış öncesi etkin koruma gerekli.')
            params.update(price=str(number(p['price_ceiling'] if side=='BUY' else p['price_floor'])),timeInForce='IOC')
            snap=collect_flat_snapshot(commands.x,s['symbol'],limits,ownership=AccountOwnership(runner),allow_target_owned=True)
            mark=number(snap['mark']['markPrice'])
            if not number(p['price_floor'])<=mark<=number(p['price_ceiling']):raise ValueError('Artış fiyat aralığı geçersizleşti.')
            base=Exposure(**s['prepared']['exposures'][0]);exposure=replace(base,quantity=str(q),
                entry=str(number(p['price_ceiling'] if side=='BUY' else p['price_floor'])),notional_price=str(number(p['price_ceiling'])))
            runner.book.evaluate(snap,limits,exchange=commands.x,extra_exposures=[exposure])
        else:
            if s['plan']['position_mode']=='one-way':params['reduceOnly']='true'
        mark=commands.x.get('/fapi/v1/premiumIndex',{'symbol':s['symbol']})
        proposal=validate_order(params,info,s['plan']['position_mode'],'OPEN' if op==INCREASE else 'REDUCE',mark['markPrice'],int(time.time()*1000)+getattr(commands.x,'offset_ms',0))
        validate_before_send(commands.x,[proposal],s['plan']['position_mode'],limits.max_age_seconds)
        latest=abs(runner._owned(s,runner._entry(s),protections))
        if latest<=0 or op!=INCREASE and q>latest:raise ValueError('Gönderim öncesi sahip olunan pozisyon değişti.')
        if time.time()>=body['expires_at']:raise ValueError('Pozisyon talimatı süresi doldu.')
    except (ValueError,ExchangeError):return commands._finish(body['command_id'],'NOT_SENT',{'phase':'PRECONDITION_FAILED','automatic_resend':False})
    action={'command_digest':digest(body),'starting_quantity':str(amount),'proposal':proposal,'exposure':asdict(exposure) if exposure else None}
    with transaction(commands.store) as db:
        db.execute('INSERT INTO position_actions VALUES(?,?,?)',(body['command_id'],canonical(action),digest(action)))
        db.execute('INSERT INTO intents(client_id,path,params,state) VALUES(?,?,?,?)',(params['newClientOrderId'],'/fapi/v1/order',json.dumps(params),'SUBMITTING'))
    if time.time()>=body['expires_at']:
        commands.store.update(params['newClientOrderId'],'REJECTED')
        return commands._finish(body['command_id'],'NOT_SENT',{'phase':'EXPIRED_BEFORE_DELIVERY','automatic_resend':False})
    try:commands.x.request('POST','/fapi/v1/order',params)
    except ExchangeError as exc:
        commands.store.update(params['newClientOrderId'],'REJECTED' if exc.delivery_status in ('NOT_SENT','REJECTED') else 'UNKNOWN',
                              {'code':exc.code,'delivery_status':exc.delivery_status})
        return reconcile(commands,body)
    try:
        actual=read_order(commands.x,commands.store,params,s['id'],write=True)
        if actual['status'] not in TERMINAL:
            runner._cancel('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':params['newClientOrderId']})
            actual=read_order(commands.x,commands.store,params,s['id'],write=True)
            if actual['status'] not in TERMINAL:return reconcile(commands,body)
        if op==INCREASE and number(actual['executedQty'])>0 and not number(p['price_floor'])<=number(actual['avgPrice'])<=number(p['price_ceiling']):
            commands.store.halt('Pozisyon artışının gerçek dolum fiyatı somut aralık dışında; risk korunuyor.')
        outcome=runner.manage(s['id'],True)
        if op==REVERSE and outcome.get('state')=='CLOSED' and number(actual['executedQty'])==q:
            runner.service.authorize_position_command(p['next_plan_id'],p['next_version'],commands.owner,body['command_id'])
            runner.open(p['next_plan_id'],p['next_version'],True)
    except (ValueError,ExchangeError):pass
    return reconcile(commands,body)


def reconcile(commands,body):
    p=body['request']['parameters'];op=body['request']['operation'];limits=risk_limits(p['risk_limits']) if op in (INCREASE,REVERSE) else RiskLimits()
    runner,s=_context(commands,body,limits)
    row=commands.store.db.execute('SELECT * FROM position_actions WHERE command_id=?',(body['command_id'],)).fetchone()
    if row is None:return commands._finish(body['command_id'],'NOT_SENT',{'phase':'NO_CHILD_INTENT','automatic_resend':False})
    # Validate the immutable child through the shared ownership adapter before lookup.
    actions=session_actions(commands.store,s,commands.account_ref,commands.owner)
    action=json.loads(row['body']);params=action['proposal']['params'];intent=commands.store.intent(params['newClientOrderId'])
    if intent['state']=='REJECTED':return commands._finish(body['command_id'],'REJECTED',{'phase':'CHILD_REJECTED','automatic_resend':False})
    try:
        actual=read_order(commands.x,commands.store,params,s['id'],write=True)
        state=runner.service.show(s['plan_ref']['plan_id'],s['plan_ref']['version'])['state']
        remaining=number(0) if state=='CLOSED' else _verify_active(runner,s['id'])
        result={'phase':'CHILD_PENDING','child_order_id':actual['orderId'],'child_status':actual['status'],
                'filled_quantity':actual['executedQty'],'requested_quantity':params['quantity'],'remaining_quantity':str(remaining),
                'source_plan_state':state,'automatic_resend':False}
        done=actual['status'] in TERMINAL
        if op==REVERSE:
            next_row,_=next_plan(commands.store,body['request'],commands.owner);result['next_plan_state']=next_row['state']
            result['next_session_id']=next_row['session_id']
            next_intent=commands.store.intent(next_row['action_id']) if next_row['action_id'] else None
            next_projection=commands.store.db.execute('SELECT * FROM order_projection WHERE client_id=?',(next_row['action_id'],)).fetchone() if next_row['action_id'] else None
            result['next_entry_state']=next_intent['state'] if next_intent else 'NOT_SUBMITTED'
            result['next_filled_quantity']=next_projection['filled'] if next_projection else '0'
            result['next_requested_quantity']=next_projection['quantity'] if next_projection else None
            if next_row['state']=='MANAGING':_verify_active(runner,next_row['session_id'])
            done=done and state=='CLOSED' and next_row['state'] in ('MANAGING','CLOSED') and number(result['next_filled_quantity'])>0
            result['phase']=('REVERSED_PARTIAL' if done and number(result['next_filled_quantity'])<number(result['next_requested_quantity']) else
                             'REVERSED' if done else 'OPEN_REJECTED' if result['next_entry_state']=='REJECTED' else 'CLOSE_OR_OPEN_INCOMPLETE')
        elif done:
            result['phase']='NO_FILL' if number(actual['executedQty'])==0 else 'FULL_FILL' if number(actual['executedQty'])==number(params['quantity']) else 'PARTIAL_FILL'
            done=(state=='CLOSED' if remaining==0 else state=='MANAGING')
        if op==INCREASE and number(actual['executedQty'])>0:
            result['price_bound_violation']=not number(p['price_floor'])<=number(actual['avgPrice'])<=number(p['price_ceiling'])
            if result['price_bound_violation']:done=False;result['phase']='PRICE_BOUND_REVIEW'
        return commands._finish(body['command_id'],'APPLIED' if done else 'UNKNOWN',result)
    except (ValueError,ExchangeError):return commands._finish(body['command_id'],'UNKNOWN',{'phase':'UNRESOLVED_CHILD','automatic_resend':False})
