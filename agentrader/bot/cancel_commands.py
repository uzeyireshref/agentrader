"""Frozen cancellation scopes; immutable broker IDs, protected managed stops."""
import json
import re
import time

from agentrader.bot.plans import canonical,digest,exact_fields,transaction
from agentrader.bot.risk import number,RiskLimits
from agentrader.shared.exchange import ExchangeError

SELECTED='CANCEL_SELECTED_ORDERS';SYMBOL='CANCEL_SYMBOL_ORDERS';ACCOUNT='CANCEL_ACCOUNT_ORDERS'
OPERATIONS={SELECTED,SYMBOL,ACCOUNT}
NORMAL_TERMINAL={'FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED'}
ALGO_TERMINAL={'CANCELED','EXPIRED','REJECTED','FINISHED'}
CID=r'[.A-Za-z:/0-9_-]{1,36}'


def validate(op,p):
    exact_fields(p,'targets include_foreign' if op==SELECTED else 'include_foreign','İptal kapsamı')
    if type(p['include_foreign']) is not bool:raise ValueError('Yabancı emir kapsamı açık boolean olmalı.')
    if op==SELECTED:
        if not isinstance(p['targets'],list) or not 1<=len(p['targets'])<=200:raise ValueError('1–200 seçili emir gerekli.')
        identities=[]
        for target in p['targets']:
            exact_fields(target,'namespace client_id','Seçili emir')
            if target['namespace'] not in ('NORMAL','ALGO') or not isinstance(target['client_id'],str) or not re.fullmatch(CID,target['client_id']):
                raise ValueError('Normal/algo kimlik alanı geçersiz.')
            identities.append((target['namespace'],target['client_id']))
        if len(set(identities))!=len(identities):raise ValueError('Tekrarlı seçili emir.')


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS cancellation_members (
        member_id TEXT PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL,state TEXT NOT NULL,result TEXT)''')
    db.execute('''CREATE TABLE IF NOT EXISTS v2_cancellations (
        command_id TEXT PRIMARY KEY,body TEXT NOT NULL,state TEXT NOT NULL)''')


def owned_index(commands):
    """Local immutable authority only; a client prefix/intent alone is not ownership."""
    from agentrader.bot.plans import PlanService
    from agentrader.bot.v2_runner import V2Runner
    from agentrader.bot.grid_runner import GridRunner
    from agentrader.bot.neutral_runner import NeutralGridRunner
    index={}
    sessions=commands.store.sessions()
    if not sessions:return index
    service=PlanService(commands.store,commands.owner)
    def add(s,params,role):
        ns='ALGO' if 'clientAlgoId' in params else 'NORMAL';cid=params.get('clientAlgoId',params.get('newClientOrderId'))
        if cid:index[(s['symbol'],ns,cid)]={'role':role,'session_id':s['id'],'entry_id':s['entry_id'],'params':params}
    for s in sessions:
        engine=s.get('engine')
        if engine not in ('v2','grid-v2','neutral-v2'):
            # Old sessions without account binding remain protected, not silently adopted.
            for p in s.get('protections',[]):add(s,p,'CORE_PROTECTION')
            for claim in commands.store.db.execute("SELECT body,digest FROM exchange_commands WHERE operation='EXECUTE_V1_PLAN' AND account_ref=? AND owner=?",
                                                   (commands.account_ref,commands.owner)):
                body=json.loads(claim['body']);p=body['request']['parameters']
                if p['session_id']!=s['id']:continue
                ref=s.get('plan_ref',{});plan=service.row(commands.store.db,p['plan_id'],p['version'])
                if (digest(body)!=claim['digest'] or ref.get('digest')!=p['plan_digest'] or plan['digest']!=p['plan_digest'] or
                        plan['session_id']!=s['id'] or plan['action_id']!=s['entry_id']):raise ValueError('V1 iptal sahipliği komutla uyuşmuyor.')
                entry=commands.store.intent(s['entry_id'])
                if entry:add(s,json.loads(entry['params']),'SESSION_ORDER')
                for proposal in s.get('exits',[]):add(s,proposal,'SESSION_ORDER')
            continue
        if s.get('account_ref')!=commands.account_ref:continue
        runner={'v2':V2Runner,'grid-v2':GridRunner,'neutral-v2':NeutralGridRunner}[engine](service,commands.x,RiskLimits())
        runner._scope(s)
        proposals=([s['prepared']['entry']]+s['exits'] if engine=='v2' else [r['proposal'] for r in s['orders']])
        for proposal in proposals:add(s,proposal['params'],'SESSION_ORDER')
        protections=s['protections']+[t['proposal'] for t in s.get('stop_transitions',[])]
        if engine=='grid-v2':protections=runner._grid_algos(s)
        for proposal in protections:add(s,proposal['params'],'CORE_PROTECTION')
        from agentrader.bot.native_trailing import session_proposals
        for proposal in session_proposals(commands.store,s,commands.account_ref,commands.owner):add(s,proposal['params'],'OPTIONAL_TRAILING')
        from agentrader.bot.position_commands import session_actions
        for action in session_actions(commands.store,s,commands.account_ref,commands.owner):add(s,action['proposal']['params'],'SESSION_ORDER')
    return index


def _flag(value):
    if type(value) is bool:return value
    if value=='true':return True
    if value in ('false',None):return False
    raise ValueError('Emir boolean alanı geçersiz.')


def normalize(actual,ns):
    if not isinstance(actual,dict):raise ValueError('Emir yanıtı nesne olmalı.')
    cid=actual.get('clientOrderId' if ns=='NORMAL' else 'clientAlgoId');bid=actual.get('orderId' if ns=='NORMAL' else 'algoId')
    symbol=actual.get('symbol')
    if (not isinstance(symbol,str) or not re.fullmatch('[A-Z0-9]{2,30}',symbol) or
            not isinstance(cid,str) or not re.fullmatch(CID,cid) or type(bid) is not int or not 0<bid<2**63 or
            actual.get('side') not in ('BUY','SELL') or actual.get('positionSide') not in ('BOTH','LONG','SHORT')):
        raise ValueError('Borsa emir kimliği veya yönü geçersiz.')
    fingerprint={'symbol':symbol,'client_id':cid,'broker_id':bid,'namespace':ns,'side':actual['side'],
                 'position_side':actual['positionSide'],'reduce_only':_flag(actual.get('reduceOnly'))}
    if ns=='NORMAL':
        q=number(actual.get('origQty'));filled=number(actual.get('executedQty'));status=actual.get('status')
        if (q<=0 or not 0<=filled<=q or status not in {'NEW','PARTIALLY_FILLED','PENDING_CANCEL'}|NORMAL_TERMINAL or
                status=='FILLED' and filled!=q or status in ('NEW','REJECTED') and filled!=0):raise ValueError('Normal emir dolumu doğrulanamadı.')
        fingerprint.update(kind=actual.get('type'),quantity=str(q))
        if fingerprint['kind'] not in ('LIMIT','MARKET'):raise ValueError('Normal emir türü desteklenmiyor.')
        if fingerprint['kind']=='LIMIT':fingerprint.update(price=str(number(actual.get('price'))),tif=actual.get('timeInForce'))
        observation={'status':status,'filled_quantity':str(filled),'child':None,'terminal':status in NORMAL_TERMINAL}
    else:
        close=_flag(actual.get('closePosition'));q=number(actual.get('quantity',0 if close else None));status=actual.get('algoStatus')
        if q<0 or not close and q<=0 or status not in {'NEW','TRIGGERING','TRIGGERED'}|ALGO_TERMINAL:raise ValueError('Algo durumu/miktarı geçersiz.')
        fingerprint.update(kind=actual.get('orderType',actual.get('type')),quantity=str(q),close_position=close,working_type=actual.get('workingType'))
        if fingerprint['kind'] not in ('STOP','STOP_MARKET','TAKE_PROFIT','TAKE_PROFIT_MARKET','TRAILING_STOP_MARKET'):
            raise ValueError('Algo türü desteklenmiyor.')
        for key in ('triggerPrice','activatePrice','callbackRate'):
            if actual.get(key) not in (None,''):fingerprint[key]=str(number(actual[key]))
        observation={'status':status,'filled_quantity':None,'child':None,'terminal':status in ('CANCELED','EXPIRED','REJECTED')}
    return fingerprint,observation


def read(commands,target):
    ns=target['namespace'];symbol=target['symbol'];cid=target['client_id']
    query=({'symbol':symbol,'orderId':target['broker_id']} if ns=='NORMAL' else {'algoId':target['broker_id'],'clientAlgoId':cid})
    actual=commands.x.get('/fapi/v1/order' if ns=='NORMAL' else '/fapi/v1/algoOrder',query)
    fingerprint,observed=normalize(actual,ns)
    if fingerprint!=target['fingerprint']:raise ValueError('İptal önizlemesindeki emir kapsamı değişti.')
    if ns=='ALGO' and actual.get('actualOrderId') not in (None,'','0',0):
        child_id=actual['actualOrderId']
        if not str(child_id).isdigit() or int(child_id)<=0:raise ValueError('Algo alt emir kimliği geçersiz.')
        child=commands.x.get('/fapi/v1/order',{'symbol':symbol,'orderId':int(child_id)})
        child_fp,child_observed=normalize(child,'NORMAL')
        if child_fp['broker_id']!=int(child_id) or any(child_fp[k]!=fingerprint[k] for k in ('symbol','side','position_side')):
            raise ValueError('Algo alt emri kapsamla uyuşmuyor.')
        if not fingerprint['close_position'] and number(child_fp['quantity'])>number(fingerprint['quantity']):raise ValueError('Alt emir miktarı algo sınırını aşıyor.')
        observed.update(child={'namespace':'NORMAL','order_id':int(child_id),'client_id':child_fp['client_id'],'status':child_observed['status'],'filled_quantity':child_observed['filled_quantity']},
                        filled_quantity=child_observed['filled_quantity'],terminal=observed['status'] in ALGO_TERMINAL and child_observed['terminal'])
    return observed,actual


def _owned(target,index,commands,actual):
    key=(target['symbol'],target['namespace'],target['client_id']);entry=index.get(key)
    if entry is None:return None
    if entry['role']=='CORE_PROTECTION':return entry
    intent=commands.store.intent(target['client_id'])
    if not intent:raise ValueError('Sahip olunan emrin kalıcı niyeti eksik.')
    from agentrader.bot.order_revisions import effective_params
    expected=effective_params(commands.store,target['client_id']) if target['namespace']=='NORMAL' else json.loads(intent['params'])
    if (any(actual.get(k)!=expected[k] for k in ('symbol','side','positionSide')) or
            actual.get('orderType',actual.get('type'))!=expected['type'] or
            number(actual.get('origQty' if target['namespace']=='NORMAL' else 'quantity'))!=number(expected.get('quantity',0)) or
            _flag(actual.get('reduceOnly'))!=_flag(expected.get('reduceOnly'))):
        raise ValueError('Sahip olunan emrin miktar/yönü niyetle uyuşmuyor.')
    prior=(json.loads(intent['response']) or {}) if intent['response'] else {}
    id_field='orderId' if target['namespace']=='NORMAL' else 'algoId'
    if prior.get(id_field) is not None and prior[id_field]!=target['broker_id']:raise ValueError('İstemci kimliği yeni borsa emrinde kullanılmış.')
    return entry


def prepare(commands,request):
    op=request['operation'];p=request['parameters'];scope=request['scope'];index=owned_index(commands);targets=[];skipped=[]
    if op==SELECTED:
        rows=[]
        for spec in p['targets']:
            query=({'symbol':scope['symbol'],'origClientOrderId':spec['client_id']} if spec['namespace']=='NORMAL' else {'clientAlgoId':spec['client_id']})
            rows.append((spec['namespace'],commands.x.get('/fapi/v1/order' if spec['namespace']=='NORMAL' else '/fapi/v1/algoOrder',query),spec['client_id']))
    else:
        rows=[];query={} if op==ACCOUNT else {'symbol':scope['symbol']}
        for ns,path in (('NORMAL','/fapi/v1/openOrders'),('ALGO','/fapi/v1/openAlgoOrders')):
            values=commands.x.get(path,query)
            if not isinstance(values,list):raise ValueError('Açık emir listesi geçersiz.')
            for value in values:
                # Open lists may omit details; bind through the exact broker identity.
                if not isinstance(value,dict):raise ValueError('Açık emir kaydı geçersiz.')
                cid=value.get('clientOrderId' if ns=='NORMAL' else 'clientAlgoId');bid=value.get('orderId' if ns=='NORMAL' else 'algoId')
                symbol=value.get('symbol')
                if type(bid) is not int or bid<=0 or not isinstance(cid,str):raise ValueError('Açık emir kimliği eksik.')
                query_one={'symbol':symbol,'orderId':bid} if ns=='NORMAL' else {'algoId':bid,'clientAlgoId':cid}
                rows.append((ns,commands.x.get('/fapi/v1/order' if ns=='NORMAL' else '/fapi/v1/algoOrder',query_one),cid))
    identities=set()
    for ns,actual,expected_cid in rows:
        fp,obs=normalize(actual,ns)
        if fp['client_id']!=expected_cid or op!=ACCOUNT and fp['symbol']!=scope['symbol']:raise ValueError('İptal listesi sembol/kimlik kapsamı uyuşmuyor.')
        key=(fp['symbol'],ns,fp['broker_id'])
        if key in identities:raise ValueError('Tekrarlı borsa emir kaydı.')
        identities.add(key)
        target={k:fp[k] for k in ('symbol','namespace','client_id','broker_id')};target['fingerprint']=fp
        owned=_owned(target,index,commands,actual)
        if owned and owned['role']=='CORE_PROTECTION':
            if op==SELECTED:raise ValueError('Etkin yönetilen stop/hedef doğrudan iptal edilemez.')
            skipped.append({'symbol':fp['symbol'],'namespace':ns,'client_id':fp['client_id'],'reason':'CORE_PROTECTION_PRESERVED'});continue
        if owned is None and not p['include_foreign']:
            if op==SELECTED:raise ValueError('Yabancı emir açık kapsam onayı olmadan iptal edilemez.')
            skipped.append({'symbol':fp['symbol'],'namespace':ns,'client_id':fp['client_id'],'reason':'FOREIGN_NOT_AUTHORIZED'});continue
        target.update(owned=owned is not None,session_id=owned['session_id'] if owned else None,entry_id=owned['entry_id'] if owned else None)
        targets.append(target)
    if len(targets)>200:raise ValueError('Tek komutta en fazla 200 dondurulmuş emir; kapsamı bölün.')
    return {'targets':targets,'skipped':skipped,'prepared_at':time.time(),'frozen_targets':True}


def _params(target):
    if target['namespace']=='NORMAL':return '/fapi/v1/order',{'symbol':target['symbol'],'orderId':target['broker_id']}
    return '/fapi/v1/algoOrder',{'algoId':target['broker_id'],'clientAlgoId':target['client_id']}


def _aliases(target):
    path,params=_params(target);values=[params]
    values.append({'symbol':target['symbol'],'origClientOrderId':target['client_id']} if target['namespace']=='NORMAL' else {'clientAlgoId':target['client_id']})
    if target['namespace']=='ALGO':values.append({'algoId':target['broker_id']})
    return [(digest(json.dumps([path,p],sort_keys=True)),json.dumps([path,p],sort_keys=True)) for p in values]


def _member(commands,target):
    body={'environment':'demo','exchange':'binance','product':'USD-M','account_ref':commands.account_ref,'target':target}
    return digest(['demo','binance','USD-M',commands.account_ref,target['symbol'],target['namespace'],target['broker_id']]),body


def _result(commands,body):
    results=[];complete=True
    for target in body['cancellation']['targets']:
        try:
            observed,actual=read(commands,target);mid,member=_member(commands,target)
            saved=commands.store.db.execute('SELECT body,digest FROM cancellation_members WHERE member_id=?',(mid,)).fetchone()
            if saved and digest(json.loads(saved['body']))!=saved['digest']:raise ValueError('İptal üye günlüğü bozuk.')
            with commands.store.db:
                commands.store.db.execute("UPDATE cancellation_members SET state=CASE WHEN ? THEN 'TERMINAL' WHEN state='PREPARED' THEN 'PREPARED' ELSE 'UNKNOWN' END,result=? WHERE member_id=?",
                    (observed['terminal'],canonical(observed),mid))
            if target['owned']:
                commands.store.update(target['client_id'],observed['status'],actual)
            complete=complete and observed['terminal']
            results.append({k:target[k] for k in ('symbol','namespace','client_id','broker_id')}|observed)
        except (ValueError,ExchangeError) as exc:
            complete=False;results.append({'symbol':target['symbol'],'namespace':target['namespace'],'client_id':target['client_id'],
                                          'status':'UNRESOLVED','code':getattr(exc,'code',None)})
    return commands._finish(body['command_id'],'APPLIED' if complete else 'UNKNOWN',
                            {'orders':results,'skipped':body['cancellation']['skipped'],'frozen_targets':True,'automatic_resend':False})


def run(commands,body,*,batch=False):
    targets=body['cancellation']['targets']
    try:
        index=owned_index(commands)
        for target in targets:
            _,actual=read(commands,target);now_owned=_owned(target,index,commands,actual)
            if now_owned and now_owned['role']=='CORE_PROTECTION':raise ValueError('Hedef artık etkin koruma.')
            if target['owned'] and now_owned is None:raise ValueError('İptal sahipliği değişti.')
        if time.time()>=body['expires_at']:raise ValueError('İptal talimatı sona erdi.')
    except (ValueError,ExchangeError):return commands._finish(body['command_id'],'NOT_SENT',{'reason':'SCOPE_CHANGED','automatic_resend':False})
    with transaction(commands.store) as db:
        for target in targets:
            mid,member=_member(commands,target);old=db.execute('SELECT * FROM cancellation_members WHERE member_id=?',(mid,)).fetchone()
            if old:
                if digest(json.loads(old['body']))!=old['digest']:raise ValueError('İptal üye günlüğü bozuk.')
            else:db.execute('INSERT INTO cancellation_members VALUES(?,?,?,?,NULL)',(mid,canonical(member),digest(member),'PREPARED'))
            if target['owned']:
                db.execute('INSERT OR REPLACE INTO control VALUES(?,?)',('entry_revoked:'+target['entry_id'],'g07:'+body['command_id']))
    pending=[]
    for target in targets:
        try:
            observed,_=read(commands,target)
            if observed['terminal']:continue
            if target['namespace']=='ALGO' and observed['status'] in ALGO_TERMINAL:continue
            current=owned_index(commands).get((target['symbol'],target['namespace'],target['client_id']))
            if current and current['role']=='CORE_PROTECTION':continue
            if time.time()>=body['expires_at']:break
            mid,_=_member(commands,target);aliases=_aliases(target)
            with transaction(commands.store) as db:
                member=db.execute('SELECT * FROM cancellation_members WHERE member_id=?',(mid,)).fetchone()
                claimed=False
                if member['state']=='PREPARED' and not any(db.execute("SELECT 1 FROM v2_cancellations WHERE command_id=? AND state!='NOT_SENT'",(key,)).fetchone() for key,_ in aliases):
                    claimed=db.execute("UPDATE cancellation_members SET state='SUBMITTING' WHERE member_id=? AND state='PREPARED'",(mid,)).rowcount==1
                    if claimed:
                        for key,value in aliases:db.execute("INSERT INTO v2_cancellations VALUES(?,?,?) ON CONFLICT(command_id) DO UPDATE SET state='SUBMITTING' WHERE state='NOT_SENT'",(key,value,'SUBMITTING'))
            if not claimed:continue
            if batch:
                pending.append(target);continue
            path,params=_params(target)
            try:
                commands.x.request('DELETE',path,params);state='RESPONSE_RECEIVED'
            except ExchangeError as exc:state='NOT_SENT' if exc.delivery_status=='NOT_SENT' else 'REJECTED' if exc.delivery_status=='REJECTED' else 'UNKNOWN'
            with commands.store.db:
                commands.store.db.execute('UPDATE cancellation_members SET state=? WHERE member_id=?',('PREPARED' if state=='NOT_SENT' else state,mid))
                for key,_ in aliases:commands.store.db.execute('UPDATE v2_cancellations SET state=? WHERE command_id=?',(state,key))
        except (ValueError,ExchangeError):continue
    if pending:
        if any(t['namespace']!='NORMAL' for t in pending) or len(pending)>10 or len({t['symbol'] for t in pending})!=1:raise ValueError('Native batch iptal kapsamı geçersiz.')
        state='NOT_SENT'
        if time.time()<body['expires_at']:
            try:
                commands.x.request('DELETE','/fapi/v1/batchOrders',{'symbol':pending[0]['symbol'],'orderIdList':json.dumps([t['broker_id'] for t in pending],separators=(',',':'))})
                state='RESPONSE_RECEIVED'
            except ExchangeError as exc:state='NOT_SENT' if exc.delivery_status=='NOT_SENT' else 'REJECTED' if exc.delivery_status=='REJECTED' else 'UNKNOWN'
        with commands.store.db:
            for target in pending:
                mid,_=_member(commands,target)
                commands.store.db.execute('UPDATE cancellation_members SET state=? WHERE member_id=?',('PREPARED' if state=='NOT_SENT' else state,mid))
                for key,_ in _aliases(target):commands.store.db.execute('UPDATE v2_cancellations SET state=? WHERE command_id=?',(state,key))
    return _result(commands,body)


def reconcile(commands,body):return _result(commands,body)
