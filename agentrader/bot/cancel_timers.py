"""Bounded countdown leases. No remote status GET exists; uncertainty blocks entry."""
import json
import re
import time

from agentrader.bot.plans import canonical,digest,exact_fields,transaction
from agentrader.bot.risk import number
from agentrader.shared.exchange import ExchangeError

SET='SET_CANCEL_TIMER';REFRESH='REFRESH_CANCEL_TIMER';DISABLE='DISABLE_CANCEL_TIMER';QUERY='QUERY_CANCEL_TIMER'
OPERATIONS={SET,REFRESH,DISABLE,QUERY}
PATH='/fapi/v1/countdownCancelAll'


def validate(op,p):
    if op==SET:
        exact_fields(p,'countdown_ms heartbeat_ms lease_ms acknowledge_symbol_wide','Timer yetkisi')
        if (p['acknowledge_symbol_wide'] is not True or type(p['countdown_ms']) is not int or not 1000<=p['countdown_ms']<=86400000 or
                type(p['heartbeat_ms']) is not int or not 1000<=p['heartbeat_ms']<=min(60000,p['countdown_ms']//2) or
                type(p['lease_ms']) is not int or not p['heartbeat_ms']<=p['lease_ms']<=600000):
            raise ValueError('Timer sembol çapında açık yetki, uygun heartbeat ve en fazla 10 dakikalık lease gerektirir.')
    else:
        exact_fields(p,'timer_id','Timer kimliği')
        if not isinstance(p['timer_id'],str) or not re.fullmatch('tmr-[a-f0-9]{40}',p['timer_id']):raise ValueError('Timer kimliği geçersiz.')


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS cancel_timers (
        timer_id TEXT PRIMARY KEY,account_ref TEXT NOT NULL,owner TEXT NOT NULL,symbol TEXT NOT NULL,
        body TEXT NOT NULL,digest TEXT NOT NULL,state TEXT NOT NULL,seq INTEGER NOT NULL,
        last_attempt_ms INTEGER NOT NULL,expected_deadline_ms INTEGER,settle_until_ms INTEGER NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS cancel_timer_attempts (
        timer_id TEXT NOT NULL,seq INTEGER NOT NULL,body TEXT NOT NULL,digest TEXT NOT NULL,state TEXT NOT NULL,
        PRIMARY KEY(timer_id,seq))''')
    db.execute('''CREATE TRIGGER IF NOT EXISTS block_entries_with_cancel_timer BEFORE INSERT ON intents
        WHEN NEW.path IN ('/fapi/v1/order','/fapi/v1/algoOrder')
        AND COALESCE(CAST(json_extract(NEW.params,'$.reduceOnly') AS TEXT),'false') NOT IN ('true','1')
        AND COALESCE(CAST(json_extract(NEW.params,'$.closePosition') AS TEXT),'false') NOT IN ('true','1')
        AND (COALESCE(json_extract(NEW.params,'$.positionSide'),'BOTH')='BOTH'
             OR json_extract(NEW.params,'$.positionSide')='LONG' AND json_extract(NEW.params,'$.side')='BUY'
             OR json_extract(NEW.params,'$.positionSide')='SHORT' AND json_extract(NEW.params,'$.side')='SELL')
        AND EXISTS(SELECT 1 FROM cancel_timers WHERE symbol=json_extract(NEW.params,'$.symbol') AND state NOT IN ('DISABLED','REJECTED'))
        BEGIN SELECT RAISE(ABORT,'Active or uncertain cancellation timer blocks opening orders'); END''')


def assert_entry_allowed(store,symbol,account_ref=None):
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cancel_timers'").fetchone():return
    query="SELECT 1 FROM cancel_timers WHERE symbol=? AND state NOT IN ('DISABLED','REJECTED')"
    values=[symbol]
    if account_ref is not None:query+=' AND account_ref=?';values.append(account_ref)
    if store.db.execute(query,values).fetchone():raise ValueError('Timer devre dışı ACK ile doğrulanmadan bu sembolde yeni giriş açılamaz.')


def is_opening(params):
    if str(params.get('closePosition',False)).lower()=='true' or str(params.get('reduceOnly',False)).lower()=='true':return False
    ps=params.get('positionSide','BOTH')
    return ps=='BOTH' or (ps=='LONG' and params.get('side')=='BUY') or (ps=='SHORT' and params.get('side')=='SELL')


def _safe(commands,symbol):
    # Do not assume countdown excludes protective/algo orders after migrations.
    started=time.time()
    if any(s['symbol']==symbol for s in commands.store.sessions()):raise ValueError('Yönetilen oturumda geniş timer kurulmaz.')
    positions=commands.x.get('/fapi/v3/positionRisk',{'symbol':symbol})
    algos=commands.x.get('/fapi/v1/openAlgoOrders',{'symbol':symbol})
    normal=commands.x.get('/fapi/v1/openOrders',{'symbol':symbol})
    if (not isinstance(positions,list) or not isinstance(algos,list) or not isinstance(normal,list) or
            any(not isinstance(p,dict) or not isinstance(p.get('symbol'),str) for p in positions+algos+normal)):
        raise ValueError('Timer için sembol görünümü doğrulanamadı.')
    if any(p['symbol']==symbol and number(p['positionAmt'])!=0 for p in positions) or any(p['symbol']==symbol for p in algos):
        raise ValueError('Timer için sembol pozisyonsuz ve algo emirsiz olmalı.')
    if not 0<=time.time()-started<=15:raise ValueError('Timer görünümü toplanırken eskidi.')
    return {'normal_orders_at_preview':len([p for p in normal if p['symbol']==symbol]),'no_position_or_algo_verified':True}


def load(commands,timer_id,symbol=None):
    row=commands.store.db.execute('SELECT * FROM cancel_timers WHERE timer_id=?',(timer_id,)).fetchone()
    if row is None:raise ValueError('Timer kaydı yok.')
    body=json.loads(row['body'])
    if (digest(body)!=row['digest'] or row['account_ref']!=commands.account_ref or row['owner']!=commands.owner or
            body['account_ref']!=commands.account_ref or body['owner']!=commands.owner or body['symbol']!=row['symbol'] or
            symbol is not None and symbol!=row['symbol']):raise ValueError('Timer sahibi/hesabı/sembolü uyuşmuyor.')
    source,original=commands._row(body['source_command_id'])
    if (source['digest']!=body['source_digest'] or original['request']['operation']!=SET or
            original['timer']['timer_id']!=timer_id or original['timer']['lease_until_ms']!=body['lease_until_ms'] or
            original['request']['scope']['symbol']!=body['symbol'] or
            original['request']['parameters']['countdown_ms']!=body['countdown_ms'] or
            original['request']['parameters']['heartbeat_ms']!=body['heartbeat_ms']):
        raise ValueError('Timer ilk yetkisiyle uyuşmuyor.')
    attempt=commands.store.db.execute('SELECT * FROM cancel_timer_attempts WHERE timer_id=? AND seq=?',(timer_id,row['seq'])).fetchone()
    if attempt is None:raise ValueError('Timer son deneme kaydı eksik.')
    proof=json.loads(attempt['body'])
    if (digest(proof)!=attempt['digest'] or proof['source_digest']!=body['source_digest'] or proof['sent_at_ms']!=row['last_attempt_ms'] or
            proof['purpose'] not in ('ARM','REFRESH','HEARTBEAT','DISABLE') or
            proof['countdown_ms']!=(0 if proof['purpose']=='DISABLE' else body['countdown_ms'])):
        raise ValueError('Timer deneme günlüğü bozuk.')
    return dict(row),body


def prepare(commands,request,command_id,now):
    p=request['parameters'];symbol=request['scope']['symbol']
    if request['operation']==SET:
        safe=_safe(commands,symbol)
        return safe|{'timer_id':'tmr-'+digest(command_id)[:40],'lease_until_ms':int(now*1000)+p['lease_ms']}
    load(commands,p['timer_id'],symbol)
    return {'timer_id':p['timer_id']}


def view(commands,timer_id):
    row,body=load(commands,timer_id);now=int(time.time()*1000)
    ack=commands.store.db.execute("SELECT body,digest FROM cancel_timer_attempts WHERE timer_id=? AND state='ACK' ORDER BY seq DESC LIMIT 1",(timer_id,)).fetchone()
    if ack and digest(json.loads(ack['body']))!=ack['digest']:raise ValueError('Timer ACK kaydı bozuk.')
    earliest=json.loads(ack['body'])['sent_at_ms']+body['countdown_ms'] if ack and row['expected_deadline_ms'] is not None else None
    return {'timer_id':timer_id,'state':row['state'],'symbol':row['symbol'],'sequence':row['seq'],
            'lease_until_ms':body['lease_until_ms'],'expected_deadline_ms':row['expected_deadline_ms'],
            'earliest_deadline_ms':earliest,'deadline_may_have_passed':earliest is not None and now>=earliest,
            'lease_expired':now>=body['lease_until_ms'],'remote_status_get_available':False,
            'remote_expiry_proven':False,'new_entries_blocked':row['state'] not in ('DISABLED','REJECTED'),
            'source_digest':body['source_digest'],'automatic_resend':False}


def _send(commands,timer_id,purpose,*,arm_body=None,valid_until_ms=None):
    commands.x.sync_time()
    now=int(time.time()*1000)
    if arm_body is not None:
        request=arm_body['request'];p=request['parameters'];symbol=request['scope']['symbol']
        timer_body={'account_ref':commands.account_ref,'owner':commands.owner,'symbol':symbol,
                    'source_command_id':arm_body['command_id'],'source_digest':digest(arm_body),
                    'lease_until_ms':arm_body['timer']['lease_until_ms'],'countdown_ms':p['countdown_ms'],'heartbeat_ms':p['heartbeat_ms']}
        if now>=timer_body['lease_until_ms'] or time.time()>=arm_body['expires_at']:raise ValueError('Timer ilk yetkisi sona erdi.')
        _safe(commands,symbol)
    else:
        row,timer_body=load(commands,timer_id);symbol=timer_body['symbol']
        if purpose!='DISABLE':
            if (row['state']!='ACTIVE' or now>=timer_body['lease_until_ms'] or now<row['last_attempt_ms'] or
                    now>=row['last_attempt_ms']+timer_body['countdown_ms']):
                raise ValueError('Timer yenilenebilir durumda değil; restart/belirsizlik/süreyi aşamaz.')
            try:_safe(commands,symbol)
            except (ValueError,ExchangeError):
                with commands.store.db:commands.store.db.execute("UPDATE cancel_timers SET state='PAUSED_UNSAFE' WHERE timer_id=?",(timer_id,))
                raise ValueError('Timer güvenli yenileme görünümü kayboldu; tekrar gönderilmedi.') from None
        elif row['state'] in ('SUBMITTING','UNKNOWN') and now<row['settle_until_ms']:
            raise ValueError('Önce önceki belirsiz timer isteğinin kabul penceresinin bitmesi beklenmeli.')
    countdown=0 if purpose=='DISABLE' else timer_body['countdown_ms']
    now=int(time.time()*1000)
    if (valid_until_ms is not None and now>=valid_until_ms) or purpose!='DISABLE' and now>=timer_body['lease_until_ms']:
        raise ValueError('Timer yetkisi gönderim öncesi sona erdi.')
    if arm_body is None and purpose!='DISABLE' and now>=row['last_attempt_ms']+timer_body['countdown_ms']:
        raise ValueError('Gecikmiş heartbeat timerı yeniden kuramaz.')
    with transaction(commands.store) as db:
        if arm_body is not None:
            if db.execute("SELECT 1 FROM cancel_timers WHERE account_ref=? AND symbol=? AND state NOT IN ('DISABLED','REJECTED')",(commands.account_ref,symbol)).fetchone():
                raise ValueError('Bu sembolde önceki timer kapatılmalı.')
            db.execute('INSERT INTO cancel_timers VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (timer_id,commands.account_ref,commands.owner,symbol,canonical(timer_body),digest(timer_body),'ACTIVE',0,0,None,0))
        current=db.execute('SELECT * FROM cancel_timers WHERE timer_id=?',(timer_id,)).fetchone()
        if arm_body is None and (current['seq']!=row['seq'] or current['state']=='SUBMITTING' and now<current['settle_until_ms']):
            raise ValueError('Timer başka süreçte değişti veya önceki kabul penceresi açık.')
        if purpose!='DISABLE' and current['state']!='ACTIVE':raise ValueError('Timer başka işlemde veya belirsiz.')
        seq=current['seq']+1;before=current['state']
        attempt={'purpose':purpose,'countdown_ms':countdown,'sent_at_ms':now,'source_digest':timer_body['source_digest']}
        db.execute('INSERT INTO cancel_timer_attempts VALUES(?,?,?,?,?)',(timer_id,seq,canonical(attempt),digest(attempt),'SUBMITTING'))
        db.execute("UPDATE cancel_timers SET state='SUBMITTING',seq=?,last_attempt_ms=?,settle_until_ms=? WHERE timer_id=?",
                   (seq,now,now+15000,timer_id))
    try:
        if ((valid_until_ms is not None and int(time.time()*1000)>=valid_until_ms) or
                purpose!='DISABLE' and int(time.time()*1000)>=timer_body['lease_until_ms']):
            raise ExchangeError('Timer yetkisi gönderim öncesi sona erdi.',delivery_status='NOT_SENT')
        reply=commands.x.request('POST',PATH,{'symbol':symbol,'countdownTime':countdown})
        if (not isinstance(reply,dict) or reply.get('symbol')!=symbol or not re.fullmatch('[0-9]+',str(reply.get('countdownTime'))) or
                int(reply['countdownTime'])!=countdown or int(time.time()*1000)<now):raise ValueError('Timer ACK doğrulanamadı.')
        state='DISABLED' if countdown==0 else 'ACTIVE';delivery='ACK';outcome='APPLIED'
    except (ValueError,ExchangeError) as exc:
        definite=isinstance(exc,ExchangeError) and exc.delivery_status in ('NOT_SENT','REJECTED')
        state=('REJECTED' if arm_body is not None else 'REFRESH_FAILED' if purpose!='DISABLE' else 'DISABLE_FAILED') if definite else 'UNKNOWN'
        delivery='REJECTED' if definite else 'UNKNOWN';outcome='REJECTED' if definite else 'UNKNOWN'
    end=int(time.time()*1000)
    with transaction(commands.store) as db:
        db.execute('UPDATE cancel_timer_attempts SET state=? WHERE timer_id=? AND seq=?',(delivery,timer_id,seq))
        deadline=(end+countdown if countdown else None) if delivery=='ACK' else current['expected_deadline_ms']
        db.execute('UPDATE cancel_timers SET state=?,expected_deadline_ms=?,settle_until_ms=? WHERE timer_id=?',
                   (state,deadline,max(now,end)+15000 if delivery=='UNKNOWN' else 0,timer_id))
    return outcome,view(commands,timer_id)


def run(commands,body):
    op=body['request']['operation'];timer_id=body['timer']['timer_id']
    if op==QUERY:return commands._finish(body['command_id'],'APPLIED',view(commands,timer_id))
    try:outcome,result=_send(commands,timer_id,'ARM' if op==SET else 'DISABLE' if op==DISABLE else 'REFRESH',arm_body=body if op==SET else None,valid_until_ms=int(body['expires_at']*1000))
    except (ValueError,ExchangeError):return commands._finish(body['command_id'],'NOT_SENT',{'timer_id':timer_id,'phase':'TIMER_PRECONDITION_FAILED','automatic_resend':False})
    return commands._finish(body['command_id'],outcome,result)


def reconcile(commands,body):
    timer_id=body['timer']['timer_id'];result=view(commands,timer_id)
    if body['request']['operation']==QUERY:return commands._finish(body['command_id'],'APPLIED',result)
    return commands._finish(body['command_id'],'APPLIED' if body['request']['operation']==DISABLE and result['state']=='DISABLED' else 'UNKNOWN',result)


def tick(commands,timer_id,source_digest,*,execute=False):
    row,body=load(commands,timer_id)
    if source_digest!=body['source_digest'] or execute is not True:raise ValueError('Timer çalışanı somut ilk digest ve execute-demo gerektirir.')
    now=int(time.time()*1000)
    if row['state']!='ACTIVE':return {'worker_state':'STOPPED_UNCERTAIN','timer':view(commands,timer_id)}
    if now>=body['lease_until_ms']:return {'worker_state':'LEASE_ENDED','timer':view(commands,timer_id)}
    if now<row['last_attempt_ms']:return {'worker_state':'CLOCK_ROLLBACK','timer':view(commands,timer_id)}
    if now>=row['last_attempt_ms']+body['countdown_ms']:return {'worker_state':'DEADLINE_PASSED','timer':view(commands,timer_id)}
    if now-row['last_attempt_ms']<body['heartbeat_ms']:return {'worker_state':'WAITING','timer':view(commands,timer_id)}
    try:outcome,result=_send(commands,timer_id,'HEARTBEAT')
    except (ValueError,ExchangeError):return {'worker_state':'STOPPED_UNSAFE','timer':view(commands,timer_id)}
    return {'worker_state':'REFRESHED' if outcome=='APPLIED' else 'STOPPED_UNCERTAIN','timer':result}
