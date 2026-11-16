"""Versioned exchange commands, independent of strategy plans.

Callers hold execution_lock when applying/reconciling mutations. SQLite claims
and the existing delegate journal additionally prevent duplicate delivery.
"""
import hashlib
import json
import re
import time

from agentrader.bot.account_commands import AccountCommands,account_command_body,command_target
from agentrader.bot.plans import canonical,digest,exact_fields,transaction,timestamp
from agentrader.bot.risk import number
from agentrader.shared.exchange import ExchangeError

SETTINGS={'SET_LEVERAGE':('LEVERAGE','leverage'),'SET_MARGIN_TYPE':('MARGIN_TYPE','margin_type'),
          'SET_POSITION_MODE':('POSITION_MODE','enabled'),'SET_MULTI_ASSETS_MODE':('MULTI_ASSETS','enabled'),
          'SET_FEE_BURN':('FEE_BURN','enabled')}
QUERIES={'PUBLIC_QUERY','PRIVATE_QUERY','QUERY_HISTORY','CREATE_HISTORY_EXPORT','QUERY_HISTORY_EXPORT'}

OPERATIONS={
    'GET_MARK_PRICE':{'mutates':False,'private':False,'version':1},
    'QUERY_ORDER':{'mutates':False,'private':True,'version':1},
    'SET_LEVERAGE':{'mutates':True,'private':True,'version':1},
    'SET_MARGIN_TYPE':{'mutates':True,'private':True,'version':1},
    'SET_POSITION_MODE':{'mutates':True,'private':True,'version':1},
    'SET_MULTI_ASSETS_MODE':{'mutates':True,'private':True,'version':1},
    'SET_FEE_BURN':{'mutates':True,'private':True,'version':1},
    'PUBLIC_QUERY':{'mutates':False,'private':False,'version':1},
    'PRIVATE_QUERY':{'mutates':False,'private':True,'version':1},
    'QUERY_HISTORY':{'mutates':False,'private':True,'version':1},
    'CREATE_HISTORY_EXPORT':{'mutates':True,'private':True,'version':1},
    'QUERY_HISTORY_EXPORT':{'mutates':False,'private':True,'version':1},
    'EXECUTE_V1_PLAN':{'mutates':True,'private':True,'version':1,'internal':True},
    'RUN_SINGLE_PLAN':{'mutates':True,'private':True,'version':1},
    'CREATE_NATIVE_TRAILING':{'mutates':True,'private':True,'version':1},
    'QUERY_NATIVE_TRAILING':{'mutates':False,'private':True,'version':1},
    'CANCEL_NATIVE_TRAILING':{'mutates':True,'private':True,'version':1},
    'INCREASE_POSITION':{'mutates':True,'private':True,'version':1},
    'REDUCE_POSITION':{'mutates':True,'private':True,'version':1},
    'CLOSE_POSITION':{'mutates':True,'private':True,'version':1},
    'REVERSE_POSITION':{'mutates':True,'private':True,'version':1},
    'CANCEL_SELECTED_ORDERS':{'mutates':True,'private':True,'version':1},
    'CANCEL_SYMBOL_ORDERS':{'mutates':True,'private':True,'version':1},
    'CANCEL_ACCOUNT_ORDERS':{'mutates':True,'private':True,'version':1},
    'SET_CANCEL_TIMER':{'mutates':True,'private':True,'version':1},
    'REFRESH_CANCEL_TIMER':{'mutates':True,'private':True,'version':1},
    'DISABLE_CANCEL_TIMER':{'mutates':True,'private':True,'version':1},
    'QUERY_CANCEL_TIMER':{'mutates':False,'private':True,'version':1},
    'BATCH_CREATE_ORDERS':{'mutates':True,'private':True,'version':1},
    'BATCH_AMEND_ORDERS':{'mutates':True,'private':True,'version':1},
    'BATCH_CANCEL_ORDERS':{'mutates':True,'private':True,'version':1},
}
INCOMPLETE={'SUBMITTING','UNKNOWN','READ_FAILED'}
FINAL={'APPLIED','REJECTED','NOT_SENT','CANCELED','EXPIRED','FINAL_WITH_ERRORS'}


def validate_command(request):
    exact_fields(request,'schema_version client_command_id environment exchange product account_ref operation scope parameters','Borsa komutu')
    if type(request['schema_version']) is not int or request['schema_version']!=1:
        raise ValueError('Borsa komutu sürümü desteklenmiyor.')
    if (request['environment'],request['exchange'],request['product'])!=('demo','binance','USD-M'):
        raise ValueError('Genel komut çekirdeği şu anda demo Binance USD-M destekler.')
    if not isinstance(request['account_ref'],str) or not re.fullmatch('[a-f0-9]{64}',request['account_ref']):
        raise ValueError('Komut hesap kapsamı geçersiz.')
    if not isinstance(request['client_command_id'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',request['client_command_id']):
        raise ValueError('İstemci komut kimliği geçersiz.')
    operation=request['operation']
    if not isinstance(operation,str) or operation not in OPERATIONS:
        raise ValueError('Desteklenmeyen borsa işlemi.')
    if operation in QUERIES:
        from agentrader.bot.query_commands import validate
        validate(operation,request)
        symbol=request['scope'].get('symbol')
    elif operation=='SET_POSITION_MODE':
        exact_fields(request['scope'],'affected_products','Ortak pozisyon modu kapsamı')
        if request['scope']['affected_products']!=['USD-M','COIN-M']:raise ValueError('Pozisyon modu açık USD-M ve COIN-M ortak kapsamı gerektirir.')
        symbol=None
    elif operation=='BATCH_CREATE_ORDERS':
        exact_fields(request['scope'],'symbols','Toplu sembol kapsamı')
        symbols=request['scope']['symbols']
        if (not isinstance(symbols,list) or not 1<=len(symbols)<=5 or any(not isinstance(s,str) or not re.fullmatch('[A-Z0-9]{2,20}USDT',s) for s in symbols) or len(set(symbols))!=len(symbols)):
            raise ValueError('Toplu giriş 1–5 farklı USDT sembol gerektirir.')
        symbol=None
    elif operation in ('CANCEL_ACCOUNT_ORDERS','SET_MULTI_ASSETS_MODE','SET_FEE_BURN'):
        exact_fields(request['scope'],'account_wide','Hesap kapsamı')
        if request['scope']['account_wide'] is not True:raise ValueError('Açık hesap çapında kapsam gerekli.')
        symbol=None
    else:
        exact_fields(request['scope'],'symbol','İşlem kapsamı')
        symbol=request['scope']['symbol']
        if not isinstance(symbol,str) or not re.fullmatch('[A-Z0-9]{2,20}USDT',symbol):
            raise ValueError('Açık USDT sembol kapsamı gerekli.')
    params=request['parameters']
    if operation in QUERIES:pass
    elif operation in ('BATCH_CREATE_ORDERS','BATCH_AMEND_ORDERS','BATCH_CANCEL_ORDERS'):
        from agentrader.bot.batch_commands import validate
        validate(operation,params)
    elif operation in ('CANCEL_SELECTED_ORDERS','CANCEL_SYMBOL_ORDERS','CANCEL_ACCOUNT_ORDERS'):
        from agentrader.bot.cancel_commands import validate
        validate(operation,params)
    elif operation in ('SET_CANCEL_TIMER','REFRESH_CANCEL_TIMER','DISABLE_CANCEL_TIMER','QUERY_CANCEL_TIMER'):
        from agentrader.bot.cancel_timers import validate
        validate(operation,params)
    elif operation in ('INCREASE_POSITION','REDUCE_POSITION','CLOSE_POSITION','REVERSE_POSITION'):
        from agentrader.bot.position_commands import validate
        validate(operation,params)
    elif operation in ('CREATE_NATIVE_TRAILING','QUERY_NATIVE_TRAILING','CANCEL_NATIVE_TRAILING'):
        from agentrader.bot.native_trailing import validate
        validate(operation,params)
    elif operation=='GET_MARK_PRICE':exact_fields(params,'','Mark sorgusu')
    elif operation in SETTINGS:
        kind,field=SETTINGS[operation]
        exact_fields(params,field,'Ayar parametreleri')
        command_target(kind,params[field],symbol)
    elif operation=='RUN_SINGLE_PLAN':
        from agentrader.bot.single_commands import validate_reference
        validate_reference(params)
    elif operation=='EXECUTE_V1_PLAN':
        exact_fields(params,'plan_id version plan_digest session_id','Eski plan bağlantısı')
        if (not isinstance(params['plan_id'],str) or not 1<=len(params['plan_id'])<=64 or
                type(params['version']) is not int or params['version']<1 or
                not isinstance(params['plan_digest'],str) or not re.fullmatch('[a-f0-9]{64}',params['plan_digest']) or
                not isinstance(params['session_id'],str) or not 1<=len(params['session_id'])<=128):
            raise ValueError('Eski plan bağlantısı geçersiz.')
    else:
        if not isinstance(params,dict) or set(params) not in ({'order_id'},{'client_order_id'}):
            raise ValueError('Tek bir normal emir kimliği gerekli.')
        if 'order_id' in params:
            if type(params['order_id']) is not int or not 0<params['order_id']<2**63:
                raise ValueError('Borsa emir kimliği geçersiz.')
        elif not isinstance(params['client_order_id'],str) or not re.fullmatch(r'[.A-Za-z:/0-9_-]{1,36}',params['client_order_id']):
            raise ValueError('İstemci emir kimliği geçersiz.')
    return json.loads(canonical(request))


class ExchangeCommands:
    def __init__(self,exchange,store,owner):
        if not isinstance(owner,str) or not 1<=len(owner)<=128:raise ValueError('Yerel komut sahibi gerekli.')
        self.x,self.store,self.owner=exchange,store,owner
        self.account_ref=hashlib.sha256(exchange.config.api_key.encode()).hexdigest()
        with transaction(store) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS exchange_commands (
                command_id TEXT PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL,
                account_ref TEXT NOT NULL,owner TEXT NOT NULL,operation TEXT NOT NULL,
                state TEXT NOT NULL,result TEXT)''')
            db.execute('''CREATE TABLE IF NOT EXISTS position_actions (
                command_id TEXT PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL)''')
            from agentrader.bot.cancel_commands import schema as cancel_schema
            from agentrader.bot.cancel_timers import schema as timer_schema
            cancel_schema(db);timer_schema(db)
            from agentrader.bot.query_commands import schema as read_schema
            read_schema(db)
            from agentrader.shared.operation_telemetry import schema as telemetry_schema
            telemetry_schema(db)

    def context(self):
        from agentrader.shared.query_routes import QUERIES as contracts
        return {'schema_version':1,'environment':'demo','exchange':'binance','product':'USD-M',
                'account_ref':self.account_ref,'operations':{k:dict(v) for k,v in OPERATIONS.items()},
                'query_contracts':{name:{'path':s['path'],'private':s['private'],'scope':s['scope'],
                    'arguments':sorted(s['arguments']),'required':sorted(s['required']),'snapshot_only':True} for name,s in contracts.items()}}

    def _id(self,request):
        return 'cmd-'+digest([request['environment'],request['exchange'],request['product'],
                              self.account_ref,self.owner,request['client_command_id']])[:40]

    def _row(self,command_id):
        row=self.store.db.execute('SELECT * FROM exchange_commands WHERE command_id=?',(command_id,)).fetchone()
        if row is None:raise ValueError('Borsa komutu bulunamadı.')
        body=json.loads(row['body']);request=validate_command(body['request'])
        if (digest(body)!=row['digest'] or body['owner']!=self.owner or body['account_ref']!=self.account_ref or
                request['account_ref']!=self.account_ref or row['owner']!=self.owner or row['account_ref']!=self.account_ref or
                body['command_id']!=command_id or self._id(request)!=command_id or row['operation']!=request['operation'] or
                body['handler_version']!=OPERATIONS[request['operation']]['version'] or row['state'] not in FINAL|INCOMPLETE|{'PREPARED'}):
            raise ValueError('Borsa komutu sahibi, hesabı veya sürümlü kapsamı uyuşmuyor.')
        return dict(row),body

    def show(self,command_id):
        row,body=self._row(command_id)
        result={'command_id':command_id,'digest':row['digest'],'state':row['state'],
                'request':body['request'],'expires_at':body['expires_at'],
                'result':json.loads(row['result']) if row['result'] else None,'automatic_resend':False}
        details={key:body[key] for key in ('cancellation','timer','batch') if key in body}
        if details:result['prepared_details']=details
        return result

    def list(self):
        rows=self.store.db.execute('SELECT command_id FROM exchange_commands WHERE account_ref=? AND owner=? ORDER BY rowid DESC LIMIT 200',
                                   (self.account_ref,self.owner)).fetchall()
        return {'commands':[self.show(row['command_id']) for row in rows],'limit':200}

    def prepare(self,request,ttl=300):
        request=validate_command(request)
        if request['account_ref']!=self.account_ref:raise ValueError('Komut etkin hesap kapsamıyla uyuşmuyor.')
        if type(ttl) is not int or not 1<=ttl<=600:raise ValueError('Komut geçerliliği 1–600 saniye.')
        spec=OPERATIONS[request['operation']]
        if spec.get('internal'):raise ValueError('Bu işlem yalnız mevcut yetkili plans run yolundan başlatılır.')
        if spec['private'] and not self.x.config.api_key:raise ValueError('Bu işlem için hesap anahtarı gerekli.')
        # Initializes the existing setting schema/owner before the atomic insert.
        # This does not create or execute a setting intent.
        if request['operation'] in SETTINGS:AccountCommands(self.x,self.store,self.owner)
        if request['operation']=='RUN_SINGLE_PLAN':
            from agentrader.bot.plans import PlanService
            plan_service=PlanService(self.store,self.owner)
        command_id=self._id(request);now=time.time()
        preview=None
        existing=self.store.db.execute('SELECT 1 FROM exchange_commands WHERE command_id=?',(command_id,)).fetchone()
        if not existing:
            if request['operation'] in ('BATCH_CREATE_ORDERS','BATCH_AMEND_ORDERS','BATCH_CANCEL_ORDERS'):
                from agentrader.bot.batch_commands import prepare
                preview=prepare(self,request,command_id,ttl)
            elif request['operation'] in ('CANCEL_SELECTED_ORDERS','CANCEL_SYMBOL_ORDERS','CANCEL_ACCOUNT_ORDERS'):
                from agentrader.bot.cancel_commands import prepare
                preview=prepare(self,request)
            elif request['operation'] in ('SET_CANCEL_TIMER','REFRESH_CANCEL_TIMER','DISABLE_CANCEL_TIMER','QUERY_CANCEL_TIMER'):
                from agentrader.bot.cancel_timers import prepare
                preview=prepare(self,request,command_id,now)
        with transaction(self.store) as db:
            old=db.execute('SELECT command_id FROM exchange_commands WHERE command_id=?',(command_id,)).fetchone()
            if old:
                _,existing=self._row(command_id)
                if existing['request']!=request:raise ValueError('Aynı istemci komut kimliği farklı parametreyle kullanılamaz.')
            else:
                if request['operation']=='RUN_SINGLE_PLAN':
                    # Already inside the preparation transaction: row() avoids
                    # nested transactions and never grants new plan authority.
                    row=plan_service.row(db,request['parameters']['plan_id'],request['parameters']['version'])
                    p=request['parameters'];plan=row['plan']
                    if (row['owner']!=self.owner or row['state']!='AUTHORIZED' or row['digest']!=p['plan_digest'] or
                            row['approval_until']<=now or timestamp(plan['expires_at'])<=now or
                            plan['schema_version']!=2 or plan['execution']['strategy']!='SINGLE' or
                            plan['symbol']!=request['scope']['symbol'] or plan['entry'].get('order_options',{})!=p['entry_options']):
                        raise ValueError('Genel SINGLE komutu için aynı kapsamda yetkili plan gerekli.')
                body={'command_id':command_id,'request':request,'owner':self.owner,'account_ref':self.account_ref,
                      'created_at':now,'expires_at':now+ttl,'handler_version':spec['version'],'delegate':None}
                if request['operation'] in ('BATCH_CREATE_ORDERS','BATCH_AMEND_ORDERS'):body['batch']=preview
                if request['operation']=='BATCH_CANCEL_ORDERS':body['cancellation']=preview
                if request['operation'] in ('CANCEL_SELECTED_ORDERS','CANCEL_SYMBOL_ORDERS','CANCEL_ACCOUNT_ORDERS'):body['cancellation']=preview
                if request['operation'] in ('SET_CANCEL_TIMER','REFRESH_CANCEL_TIMER','DISABLE_CANCEL_TIMER','QUERY_CANCEL_TIMER'):body['timer']=preview
                if request['operation'] in ('INCREASE_POSITION','REDUCE_POSITION','CLOSE_POSITION','REVERSE_POSITION'):
                    from agentrader.bot.position_commands import prepare
                    body['position']=prepare(self,request)
                if request['operation'] in ('CREATE_NATIVE_TRAILING','QUERY_NATIVE_TRAILING','CANCEL_NATIVE_TRAILING'):
                    from agentrader.bot.native_trailing import prepare
                    body['native']=prepare(self,request,command_id)
                if request['operation'] in SETTINGS:
                    kind,field=SETTINGS[request['operation']]
                    delegate=account_command_body(kind,request['parameters'][field],request['scope'].get('symbol'),
                                                  self.owner,self.account_ref,ttl,command_id=digest(['setting',command_id])[:32],now=now)
                    delegate_digest=digest(delegate)
                    db.execute('INSERT INTO account_commands(command_id,body,digest,state,result) VALUES(?,?,?,?,NULL)',
                               (delegate['command_id'],canonical(delegate),delegate_digest,'PREPARED'))
                    body['delegate']={'command_id':delegate['command_id'],'digest':delegate_digest}
                db.execute('INSERT INTO exchange_commands VALUES(?,?,?,?,?,?,?,NULL)',
                           (command_id,canonical(body),digest(body),self.account_ref,self.owner,request['operation'],'PREPARED'))
        return self.show(command_id)|{'duplicate':bool(old)}

    def _finish(self,command_id,state,result):
        if state not in FINAL|INCOMPLETE:raise ValueError('Komut sonuç durumu geçersiz.')
        with transaction(self.store) as db:
            changed=db.execute("UPDATE exchange_commands SET state=?,result=? WHERE command_id=? AND state IN ('SUBMITTING','UNKNOWN','READ_FAILED')",
                               (state,canonical(result),command_id))
            if changed.rowcount:
                from agentrader.shared.operation_telemetry import command_state
                command_state(db,command_id,state,time.time())
                db.execute('INSERT INTO events(event,payload) VALUES(?,?)',
                           ('exchange_command_state',canonical({'command_id':command_id,'state':state})))
        return self.show(command_id)

    def _delegate(self,body):
        service=AccountCommands(self.x,self.store,self.owner)
        link=body['delegate']
        if not isinstance(link,dict):raise ValueError('Ayar komutu bağlantısı eksik.')
        row,child=service.row(link['command_id'])
        request=body['request']
        kind,field=SETTINGS[request['operation']]
        if (row['digest']!=link['digest'] or child['kind']!=kind or
                child['value']!=request['parameters'][field] or child['symbol']!=request['scope'].get('symbol') or
                child['expires_at']!=body['expires_at']):
            raise ValueError('Alt ayar komutu üst talimatla uyuşmuyor.')
        return service,row

    def _setting_result(self,body):
        _,child=self._delegate(body)
        state=child['state']
        mapping={'APPLIED':'APPLIED','REJECTED':'REJECTED','EXPIRED':'EXPIRED','CANCELED':'NOT_SENT','NOT_SENT':'NOT_SENT'}
        kind,field=SETTINGS[body['request']['operation']]
        from agentrader.bot.account_commands import affected_products
        result={'delegate_state':state,'automatic_resend':False,'kind':kind,'affected_products':affected_products(kind),
                'observation':json.loads(child['result']) if child.get('result') else None}
        if state=='APPLIED':result[field]=body['request']['parameters'][field]
        return self._finish(body['command_id'],mapping.get(state,'UNKNOWN'),result)

    def apply(self,command_id,confirmed_digest,*,execute=False):
        row,body=self._row(command_id)
        if OPERATIONS[body['request']['operation']].get('internal'):
            raise ValueError('Eski plan yeniden gönderilemez; mevcut plans yönetim/uzlaştırma yolunu kullanın.')
        if confirmed_digest!=row['digest']:raise ValueError('Somut borsa komutu özeti uyuşmuyor.')
        mutates=OPERATIONS[body['request']['operation']]['mutates']
        if mutates and execute is not True:raise ValueError('Finansal komutu uygulamak için açık execute-demo bayrağı gerekli.')
        if row['state']!='PREPARED':return self.show(command_id)|{'duplicate':True}
        with transaction(self.store) as db:
            if time.time()>=body['expires_at']:
                db.execute("UPDATE exchange_commands SET state='EXPIRED' WHERE command_id=? AND state='PREPARED'",(command_id,))
                if body['delegate']:db.execute("UPDATE account_commands SET state='CANCELED' WHERE command_id=? AND state='PREPARED'",(body['delegate']['command_id'],))
                claimed=False
            else:
                if mutates and db.execute("SELECT 1 FROM exchange_commands WHERE account_ref=? AND operation IN ('SET_LEVERAGE','SET_MARGIN_TYPE','SET_POSITION_MODE','SET_MULTI_ASSETS_MODE','SET_FEE_BURN') AND command_id!=? AND state IN ('SUBMITTING','UNKNOWN')",
                                          (self.account_ref,command_id)).fetchone():
                    raise ValueError('Önce bekleyen genel hesap komutunu uzlaştırın.')
                claimed=db.execute("UPDATE exchange_commands SET state='SUBMITTING' WHERE command_id=? AND state='PREPARED'",(command_id,)).rowcount==1
        if not claimed:
            if body['request']['operation']=='BATCH_AMEND_ORDERS':
                from agentrader.bot.batch_commands import cancel_prepared
                cancel_prepared(self,body)
            return self.show(command_id)|{'duplicate':True}
        if body['request']['operation'] in QUERIES:
            from agentrader.bot.query_commands import run
            return run(self,body)
        if body['request']['operation'] in ('BATCH_CREATE_ORDERS','BATCH_AMEND_ORDERS','BATCH_CANCEL_ORDERS'):
            from agentrader.bot.batch_commands import run
            return run(self,body)
        if body['request']['operation'] in ('CANCEL_SELECTED_ORDERS','CANCEL_SYMBOL_ORDERS','CANCEL_ACCOUNT_ORDERS'):
            from agentrader.bot.cancel_commands import run
            return run(self,body)
        if body['request']['operation'] in ('SET_CANCEL_TIMER','REFRESH_CANCEL_TIMER','DISABLE_CANCEL_TIMER','QUERY_CANCEL_TIMER'):
            from agentrader.bot.cancel_timers import run
            return run(self,body)
        if body['request']['operation'] in ('INCREASE_POSITION','REDUCE_POSITION','CLOSE_POSITION','REVERSE_POSITION'):
            from agentrader.bot.position_commands import run
            return run(self,body)
        if body['request']['operation'] in ('CREATE_NATIVE_TRAILING','QUERY_NATIVE_TRAILING','CANCEL_NATIVE_TRAILING'):
            from agentrader.bot.native_trailing import run
            return run(self,body)
        if body['request']['operation']=='RUN_SINGLE_PLAN':
            from agentrader.bot.single_commands import run
            return run(self,body)
        if not mutates:return self._read(body)
        service,child=self._delegate(body)
        try:
            service.apply(child['command_id'],body['delegate']['digest'])
        except (ValueError,ExchangeError):
            # The child journal, rather than exception type, establishes whether
            # a request could have left the process.
            return self._recover_setting(body)
        return self._setting_result(body)

    def _recover_setting(self,body):
        service,child=self._delegate(body)
        if child['state']=='PREPARED':
            # Atomically retire an intent proven unsent. A concurrent apply must
            # still win the child's PREPARED -> SUBMITTING claim before POST.
            with transaction(self.store) as db:
                db.execute("UPDATE account_commands SET state='CANCELED' WHERE command_id=? AND state='PREPARED'",(child['command_id'],))
            return self._setting_result(body)
        if child['state'] in ('SUBMITTING','UNKNOWN'):
            try:service.reconcile(child['command_id'])
            except (ValueError,ExchangeError):
                return self._finish(body['command_id'],'UNKNOWN',{'delegate_state':child['state'],'automatic_resend':False})
        return self._setting_result(body)

    def reconcile(self,command_id):
        row,body=self._row(command_id)
        if row['state'] not in INCOMPLETE:return self.show(command_id)
        if body['request']['operation'] in QUERIES:
            from agentrader.bot.query_commands import reconcile
            return reconcile(self,body)
        if body['request']['operation'] in ('BATCH_CREATE_ORDERS','BATCH_AMEND_ORDERS','BATCH_CANCEL_ORDERS'):
            from agentrader.bot.batch_commands import reconcile
            return reconcile(self,body)
        if body['request']['operation'] in ('CANCEL_SELECTED_ORDERS','CANCEL_SYMBOL_ORDERS','CANCEL_ACCOUNT_ORDERS'):
            from agentrader.bot.cancel_commands import reconcile
            return reconcile(self,body)
        if body['request']['operation'] in ('SET_CANCEL_TIMER','REFRESH_CANCEL_TIMER','DISABLE_CANCEL_TIMER','QUERY_CANCEL_TIMER'):
            from agentrader.bot.cancel_timers import reconcile
            return reconcile(self,body)
        if body['request']['operation'] in ('INCREASE_POSITION','REDUCE_POSITION','CLOSE_POSITION','REVERSE_POSITION'):
            from agentrader.bot.position_commands import reconcile
            return reconcile(self,body)
        if body['request']['operation'] in ('CREATE_NATIVE_TRAILING','QUERY_NATIVE_TRAILING','CANCEL_NATIVE_TRAILING'):
            from agentrader.bot.native_trailing import reconcile
            return reconcile(self,body)
        if body['request']['operation']=='RUN_SINGLE_PLAN':
            from agentrader.bot.single_commands import reconcile
            return reconcile(self,body)
        if body['request']['operation']=='EXECUTE_V1_PLAN':return self.finish_plan(command_id)
        if OPERATIONS[body['request']['operation']]['mutates']:return self._recover_setting(body)
        return self._read(body)

    def claim_plan(self,service,plan_id,version,session_id):
        """Journal the authorized V1 claim atomically; never create fresh authority."""
        if service.store is not self.store or service.owner!=self.owner:
            raise ValueError('Plan ve komut deposu/sahibi uyuşmuyor.')
        if not self.x.config.api_key:raise ValueError('Plan yürütmesi için hesap anahtarı gerekli.')
        current=service.show(plan_id,version)
        if current['plan']['schema_version']!=1:raise ValueError('Bu köprü yalnız V1 planı içindir.')
        request=validate_command({'schema_version':1,'environment':'demo','exchange':'binance','product':'USD-M',
            'account_ref':self.account_ref,'client_command_id':'v1-'+digest([plan_id,version])[:40],
            'operation':'EXECUTE_V1_PLAN','scope':{'symbol':current['plan']['symbol']},
            'parameters':{'plan_id':plan_id,'version':version,'plan_digest':current['digest'],'session_id':session_id}})
        command_id=self._id(request)
        def record(db,row,action_id):
            if row['digest']!=current['digest']:raise ValueError('Plan özeti talep sırasında değişti.')
            body={'command_id':command_id,'request':request,'owner':self.owner,'account_ref':self.account_ref,
                'created_at':time.time(),'expires_at':row['approval_until'],'handler_version':1,
                'delegate':{'action_id':action_id}}
            db.execute('INSERT INTO exchange_commands VALUES(?,?,?,?,?,?,?,NULL)',
                (command_id,canonical(body),digest(body),self.account_ref,self.owner,'EXECUTE_V1_PLAN','SUBMITTING'))
        action_id=service.claim(plan_id,version,session_id,_on_claim=record)
        return action_id,command_id

    def finish_plan(self,command_id):
        """Observe the delegated lifecycle. Unknown never consumes a new plan or POST."""
        from agentrader.bot.plans import PlanService
        row,body=self._row(command_id)
        if body['request']['operation']!='EXECUTE_V1_PLAN':raise ValueError('Plan köprüsü komutu gerekli.')
        if row['state'] not in INCOMPLETE:return self.show(command_id)
        p=body['request']['parameters'];plan=PlanService(self.store,self.owner).show(p['plan_id'],p['version'])
        action_id=body['delegate']['action_id']
        if (plan['digest']!=p['plan_digest'] or plan['plan']['symbol']!=body['request']['scope']['symbol'] or
                plan['action_id']!=action_id or plan['session_id']!=p['session_id']):
            raise ValueError('Plan yürütme kimliği komut bağlantısıyla uyuşmuyor.')
        intent=self.store.intent(action_id)
        result={'plan_id':p['plan_id'],'version':p['version'],'plan_state':plan['state'],
                'action_id':action_id,'session_id':p['session_id'],
                'entry_state':intent['state'] if intent else 'NO_RECORDED_INTENT','automatic_resend':False,
                'meaning':'DELEGATED_PLAN_EXECUTION; NOT_POSITION_CLOSED'}
        # Only the existing plan executor establishes successful protected management.
        # A filled entry alone cannot prove protection or complete the parent.
        return self._finish(command_id,'APPLIED' if plan['state'] in ('MANAGING','CLOSED') else 'UNKNOWN',result)

    def cancel(self,command_id,confirmed_digest):
        row,body=self._row(command_id)
        if row['digest']!=confirmed_digest:raise ValueError('İptal özeti uyuşmuyor.')
        if row['state']!='PREPARED':raise ValueError('Yalnız gönderilmemiş hazır komut iptal edilebilir.')
        if body['request']['operation']=='BATCH_AMEND_ORDERS':
            from agentrader.bot.batch_commands import cancel_prepared
            cancel_prepared(self,body)
        with transaction(self.store) as db:
            changed=db.execute("UPDATE exchange_commands SET state='CANCELED' WHERE command_id=? AND state='PREPARED'",(command_id,))
            if changed.rowcount!=1:raise ValueError('Komut başka süreç tarafından kullanıldı.')
            if body['delegate']:
                db.execute("UPDATE account_commands SET state='CANCELED' WHERE command_id=? AND state='PREPARED'",(body['delegate']['command_id'],))
        return self.show(command_id)

    def _read(self,body):
        request=body['request'];symbol=request['scope']['symbol']
        try:
            self.x.sync_time()
            if request['operation']=='GET_MARK_PRICE':
                value=self.x.get('/fapi/v1/premiumIndex',{'symbol':symbol})
                now=int(time.time()*1000)+getattr(self.x,'offset_ms',0)
                if (not isinstance(value,dict) or value.get('symbol')!=symbol or type(value.get('time')) is not int or
                        not -1000<=now-value['time']<=15000 or number(value.get('markPrice'))<=0):
                    raise ValueError('Mark sorgusunun sembolü, fiyatı veya zamanı doğrulanamadı.')
                result={'symbol':symbol,'mark_price':str(number(value['markPrice'])),'exchange_time_ms':value['time']}
            else:
                p=request['parameters']
                selector={'orderId':p['order_id']} if 'order_id' in p else {'origClientOrderId':p['client_order_id']}
                value=self.x.get('/fapi/v1/order',{'symbol':symbol}|selector)
                if (not isinstance(value,dict) or value.get('symbol')!=symbol or
                        type(value.get('orderId')) is not int or value['orderId']<=0 or
                        ('order_id' in p and value['orderId']!=p['order_id']) or
                        ('client_order_id' in p and value.get('clientOrderId')!=p['client_order_id']) or
                        value.get('status') not in ('NEW','PARTIALLY_FILLED','FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED') or
                        not 0<=number(value.get('executedQty'))<=number(value.get('origQty')) or number(value.get('origQty'))<=0):
                    raise ValueError('Emir sorgusu kapsamı veya gerçekleşmesi doğrulanamadı.')
                if (value['status']=='FILLED' and number(value['executedQty'])!=number(value['origQty']) or
                        value['status'] in ('NEW','REJECTED') and number(value['executedQty'])!=0):
                    raise ValueError('Tam dolum miktarı uyuşmuyor.')
                result={k:value[k] for k in ('symbol','orderId','clientOrderId','status','origQty','executedQty') if k in value}
            return self._finish(body['command_id'],'APPLIED',result)
        except (ValueError,ExchangeError) as exc:
            error={'kind':'EXCHANGE' if isinstance(exc,ExchangeError) else 'INVALID_RESPONSE',
                   'code':getattr(exc,'code',None),'http_status':getattr(exc,'http_status',None),'automatic_resend':False}
            return self._finish(body['command_id'],'READ_FAILED',error)
