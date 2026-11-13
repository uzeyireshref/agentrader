"""Exact bounded native LIMIT amendments with modifyId/history reconciliation.

Original plan/creation parameters remain immutable. Only verified revisions are
visible to runners. Caller holds execution_lock; a PUT is never blindly resent.
"""
import hashlib
import json
import time
import uuid
import re

from .exchange import ExchangeError
from .management import split_targets
from .order_revisions import effective_params,commit_projection
from .order_rules import validate_order
from .plans import canonical,digest,timestamp,transaction
from .risk import number
from .v2_preflight import fresh

FINAL={'FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED'}
BUSY={'SUBMITTING','UNKNOWN','ACKNOWLEDGED'}


class OrderAmendments:
    def __init__(self,service,exchange,limits,clock=time.time):
        self.service,self.x,self.limits,self.clock=service,exchange,limits,clock
        self.store=service.store
        self.account_ref=hashlib.sha256(exchange.config.api_key.encode()).hexdigest()
        with self.store.db:
            self.store.db.execute('''CREATE TABLE IF NOT EXISTS order_modifications (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,command_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,modify_id INTEGER UNIQUE NOT NULL,
                body TEXT NOT NULL,digest TEXT NOT NULL,state TEXT NOT NULL,response TEXT)''')
            if 'batch_id'not in{r['name']for r in self.store.db.execute('PRAGMA table_info(order_modifications)')}:
                self.store.db.execute('ALTER TABLE order_modifications ADD COLUMN batch_id TEXT')
            self.store.db.execute('''CREATE TABLE IF NOT EXISTS order_modify_batches (
                batch_id TEXT PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL,state TEXT NOT NULL)''')

    def _session(self,sid):
        s=next((s for s in self.store.sessions()if s['id']==sid),None)
        if s is None:raise ValueError('Emir değiştirmek için etkin oturum gerekli.')
        if s.get('engine')=='grid-v2':
            from .grid_runner import GridRunner
            runner=GridRunner(self.service,self.x,self.limits)
        elif s.get('engine')=='v2':
            from .v2_runner import V2Runner
            runner=V2Runner(self.service,self.x,self.limits)
        else:raise ValueError('Native değiştirme yalnız SINGLE/yönlü GRID v2 oturumlarında desteklenir; neutral amend henüz yok.')
        runner._scope(s)
        return s,runner

    def _read(self,body):
        p=body['before_params']
        a=self.x.get('/fapi/v1/order',{'symbol':p['symbol'],'origClientOrderId':p['newClientOrderId']})
        if not isinstance(a,dict):raise ValueError('Normal emir yanıtı nesne olmalı.')
        if (a.get('clientOrderId')!=p['newClientOrderId']or str(a.get('orderId'))!=str(body['order_id'])
                or any(a.get(k)!=p[k]for k in('symbol','side','positionSide'))or a.get('type')!='LIMIT'
                or a.get('status')not in FINAL|{'NEW','PARTIALLY_FILLED'}
                or not 0<=number(a['executedQty'])<=number(a['origQty'])or type(a.get('updateTime'))is not int):
            raise ValueError('Değiştirilen emir kimliği/durumu doğrulanamadı.')
        return a

    def _validate(self,s,runner,cid,quantity,price):
        row=runner._scope(s)
        p=effective_params(self.store,cid)
        if p.get('type')!='LIMIT' or p.get('timeInForce')!='GTC' or 'priceMatch'in p:
            raise ValueError('İlk amend yolu açık fiyatlı GTC LIMIT emirlerini destekler.')
        if s['engine']=='v2':
            if cid!=s['entry_id']:raise ValueError('SINGLE için yalnız mevcut LIMIT giriş emri değiştirilebilir.')
            operation='OPEN'
            entry=runner._entry(s)
            algos={a['params']['clientAlgoId']:self.x.get('/fapi/v1/algoOrder',{'clientAlgoId':a['params']['clientAlgoId']})
                   for a in s['protections']if self.store.intent(a['params']['clientAlgoId'])}
            runner._owned(s,entry,algos)
        else:
            record=next((r for r in s['orders']if r['proposal']['params']['newClientOrderId']==cid),None)
            if record is None or record['kind']not in('OPEN','REDUCE'):raise ValueError('Grid hücre emri gerekli.')
            operation=record['kind']
            if s['phase']=='STOPPING'or(operation=='OPEN'and s['phase']!='ACTIVE'):raise ValueError('Durdurulan grid açıcı emri değiştirilemez.')
            results=runner._results(s);runner._owned_grid(s,results,runner._algos(s))
        a=self.x.get('/fapi/v1/order',{'symbol':p['symbol'],'origClientOrderId':cid})
        if not isinstance(a,dict):raise ValueError('Normal emir yanıtı nesne olmalı.')
        identity={'before_params':p,'order_id':a.get('orderId')}
        self._read(identity)
        if a['status']in FINAL:raise ValueError('Terminal emir değiştirilemez.')
        if number(a['origQty'])!=number(p['quantity'])or number(a['price'])!=number(p['price']):
            raise ValueError('Emir parametreleri doğrulanmış değişiklik zincirinden farklı.')
        q,price=number(quantity),number(price)
        if not number(a['executedQty'])<q<=number(p['quantity']):raise ValueError('Yeni toplam miktar gerçekleşenden büyük ve önceki miktardan küçük/eşit olmalı.')
        if s['engine']=='grid-v2'and price!=number(p['price']):raise ValueError('Grid fiyat seviyeleri amend ile değiştirilemez.')
        if s['engine']=='v2':
            if (p['side']=='BUY'and price>number(p['price']))or(p['side']=='SELL'and price<number(p['price'])):
                raise ValueError('SINGLE limit fiyatı yalnız daha iyi yönde değiştirilebilir.')
            if q*max(price,number(p['price']))>number(p['quantity'])*number(p['price']):
                raise ValueError('Amend önceki nominal rezervini büyütemez.')
            sign=1 if s['plan']['direction']=='LONG'else -1
            ref=number(s['plan']['entry']['reference_price'])
            if (sign*(price-number(s['plan']['stop']))<=0 or sign*(number(s['plan']['targets'][0]['price'])-price)<=0
                    or abs(price-ref)/ref*10000>number(s['plan']['entry']['max_drift_bps'])):
                raise ValueError('Yeni limit fiyatı planın stop/hedef/tolerans sınırları dışında.')
        if operation=='OPEN':
            if self.store.halt_reason()or self.store.unresolved_account_command():raise ValueError('Belirsiz işlem/durdurma varken açıcı emir amend edilmez.')
            if self.clock()>=timestamp(s['plan']['expires_at'])or(s['engine']=='v2'and self.clock()>=row['approval_until']):
                raise ValueError('Açıcı emir değiştirme yetkisi sona erdi.')
            if self.store.db.execute('SELECT 1 FROM control WHERE name=?',('entry_revoked:'+s['entry_id'],)).fetchone():
                raise ValueError('Giriş yetkisi iptal edildi.')
        mark=self.x.get('/fapi/v1/premiumIndex',{'symbol':p['symbol']})
        now_ms=int(self.clock()*1000)+getattr(self.x,'offset_ms',0)
        fresh(mark,p['symbol'],now_ms,self.limits.max_age_seconds)
        sign=1 if s['plan']['direction']=='LONG'else -1
        stop=runner._grid_stop(s) if s['engine']=='grid-v2' else number(s['plan']['stop'])
        if sign*(number(mark['markPrice'])-stop)<=0 or sign*(number(s['plan']['targets'][-1]['price'])-number(mark['markPrice']))<=0:
            raise ValueError('Amend öncesi stop/son hedef aşıldı; yönetim akışı devralmalı.')
        info=next(i for i in self.x.get('/fapi/v1/exchangeInfo')['symbols']if i['symbol']==p['symbol'])
        desired=validate_order(p|{'quantity':str(q),'price':str(price)},info,s['plan']['position_mode'],operation,mark['markPrice'],now_ms)['params']
        if s['engine']=='v2':
            filters={f['filterType']:f for f in info['filters']}
            split_targets(str(q),s['plan']['targets'],{'lot':filters['LOT_SIZE'],'market':filters.get('MARKET_LOT_SIZE',filters['LOT_SIZE'])})
        return p,a,desired

    def prepare(self,sid,cid,quantity,price,ttl=120):
        if type(ttl)is not int or not 1<=ttl<=600:raise ValueError('Amend geçerliliği 1–600 saniye olmalı.')
        if not isinstance(sid,str)or not sid or not isinstance(cid,str)or not re.fullmatch(r'[.A-Za-z:/0-9_-]{1,36}',cid):
            raise ValueError('Amend oturum/emir kimliği geçersiz.')
        for old in self.store.db.execute("SELECT command_id,body,digest FROM order_modifications WHERE client_id=? AND state='PREPARED'",(cid,)).fetchall():
            body=json.loads(old['body'])
            if digest(body)!=old['digest']:raise ValueError('Bekleyen amend özeti uyuşmuyor.')
            if self.clock()>=body['expires_at']:self._state(old['command_id'],'EXPIRED')
        if self.store.db.execute("SELECT 1 FROM order_modifications WHERE client_id=? AND state IN ('PREPARED','SUBMITTING','UNKNOWN','ACKNOWLEDGED')",(cid,)).fetchone():
            raise ValueError('Bu emrin bekleyen amend komutu önce tamamlanmalı/iptal edilmeli.')
        start=self.clock();self.x.sync_time();s,runner=self._session(sid)
        before,a,desired=self._validate(s,runner,cid,quantity,price)
        if number(before['quantity'])==number(desired['quantity'])and number(before['price'])==number(desired['price']):
            raise ValueError('Amend parametreleri mevcut emirle aynı.')
        if not 0<=self.clock()-start<=self.limits.max_age_seconds:raise ValueError('Amend hazırlık görünümü eskidi.')
        mid=int(uuid.uuid4().hex[:15],16)
        b={'command_id':uuid.uuid4().hex,'account_ref':self.account_ref,'owner':self.service.owner,
           'environment':'demo','session_id':sid,'plan_ref':s['plan_ref'],'client_id':cid,'order_id':a['orderId'],
           'before_params':before,'quantity':desired['quantity'],'price':desired['price'],'modify_id':mid,
           'created_ms':int(self.clock()*1000)+getattr(self.x,'offset_ms',0),'expires_at':self.clock()+ttl}
        h=digest(b)
        with self.store.db:self.store.db.execute('INSERT INTO order_modifications(command_id,client_id,modify_id,body,digest,state)VALUES(?,?,?,?,?,?)',
                                                (b['command_id'],cid,mid,canonical(b),h,'PREPARED'))
        return {'command_id':b['command_id'],'digest':h,'state':'PREPARED','client_id':cid,
                'session_id':sid,'symbol':before['symbol'],'side':before['side'],'position_side':before['positionSide'],
                'before_quantity':before['quantity'],'before_price':before['price'],
                'quantity':b['quantity'],'price':b['price'],'expires_at':b['expires_at']}

    def _row(self,cid):
        row=self.store.db.execute('SELECT * FROM order_modifications WHERE command_id=?',(cid,)).fetchone()
        if row is None:raise ValueError('Amend komutu bulunamadı.')
        b=json.loads(row['body'])
        if (digest(b)!=row['digest']or b['account_ref']!=self.account_ref or b['owner']!=self.service.owner
                or b['environment']!='demo' or b['client_id']!=row['client_id']or b['modify_id']!=row['modify_id']):
            raise ValueError('Amend kapsamı/hesabı/özeti uyuşmuyor.')
        active=any(s['id']==b['session_id']for s in self.store.sessions())
        if active:s,runner=self._session(b['session_id'])
        else:
            s=next((s for s in self.store.sessions(False)if s['id']==b['session_id']),None);runner=None
            parent=self.service.show(b['plan_ref']['plan_id'],b['plan_ref']['version'])
            if (s is None or s.get('account_ref')!=self.account_ref or digest(s['plan'])!=b['plan_ref']['digest']
                    or parent['digest']!=b['plan_ref']['digest']or parent['session_id']!=b['session_id']):
                raise ValueError('Amend geçmiş oturum sahipliği doğrulanamadı.')
        if s['plan_ref']!=b['plan_ref']:raise ValueError('Amend plan sürümü uyuşmuyor.')
        return dict(row),b,s,runner

    def _state(self,cid,state,response=None):
        with self.store.db:self.store.db.execute('UPDATE order_modifications SET state=?,response=?WHERE command_id=?',(state,json.dumps(response),cid))
        return {'command_id':cid,'state':state,'result':response,'automatic_resend':False}

    def cancel(self,cid,confirmed_digest):
        row,b,_,_=self._row(cid)
        if row['digest']!=confirmed_digest:raise ValueError('Amend komut özeti uyuşmuyor.')
        if row['state']!='PREPARED':raise ValueError('Gönderilmiş/belirsiz amend yerel iptalle temizlenemez.')
        if row['batch_id']:raise ValueError('Toplu amend alt komutu tek başına iptal edilmez.')
        return self._state(cid,'CANCELED')

    def reconcile(self,cid):
        row,b,s,runner=self._row(cid)
        if row['state']not in BUSY:return {'command_id':cid,'state':row['state'],'duplicate':True}
        actual=self._read(b)
        history=self.x.get('/fapi/v1/orderAmendment',{'symbol':b['before_params']['symbol'],'origClientOrderId':b['client_id'],
                                                     'startTime':b['created_ms']-1000,'limit':100})
        if not isinstance(history,list)or len(history)>=100:raise ValueError('Amend geçmişi eksik/sayfalama gerekli.')
        matches=[]
        for h in history:
            if not isinstance(h,dict)or not isinstance(h.get('amendment'),dict):raise ValueError('Amend geçmişi alanları geçersiz.')
            change=h.get('amendment',{})
            if (str(h.get('orderId'))==str(b['order_id'])and h.get('clientOrderId')==b['client_id']and h.get('symbol')==b['before_params']['symbol']
                    and type(change.get('modifyId'))is int and change['modifyId']==b['modify_id']
                    and type(h.get('time'))is int and b['created_ms']-1000<=h['time']<=int(self.clock()*1000)+getattr(self.x,'offset_ms',0)+1000):
                try:values=[change['price']['before'],change['price']['after'],change['origQty']['before'],change['origQty']['after']]
                except(KeyError,TypeError):raise ValueError('Amend fiyat/miktar geçmişi eksik.')from None
                if [number(v)for v in values]==[number(b['before_params']['price']),number(b['price']),number(b['before_params']['quantity']),number(b['quantity'])]:
                    matches.append(h)
        if len(matches)==1 and number(actual['origQty'])==number(b['quantity'])and number(actual['price'])==number(b['price']):
            with transaction(self.store)as db:
                current=effective_params(self.store,b['client_id'])
                if current!=b['before_params']:raise ValueError('Amend öncül sürümü değişti.')
                commit_projection(db,b['client_id'],b['quantity'],actual)
                db.execute("UPDATE order_modifications SET state='APPLIED',response=? WHERE command_id=?",(json.dumps(actual),cid))
                db.execute('UPDATE intents SET state=?,response=?WHERE client_id=?',(actual['status'],json.dumps(actual),b['client_id']))
            self.store.event('order_amended',{'command_id':cid,'client_id':b['client_id'],'quantity':b['quantity'],'price':b['price']})
            return {'command_id':cid,'state':'APPLIED','automatic_resend':False}
        if actual['status']in FINAL and number(actual['origQty'])==number(b['before_params']['quantity'])and number(actual['price'])==number(b['before_params']['price']):
            return self._state(cid,'SUPERSEDED',{'order_status':actual['status'],'executed_quantity':actual['executedQty']})
        return self._state(cid,'ACKNOWLEDGED'if row['state']=='ACKNOWLEDGED'else'UNKNOWN',{'history_matches':len(matches)})

    def apply(self,cid,confirmed_digest):
        row,b,s,runner=self._row(cid)
        if row['digest']!=confirmed_digest:raise ValueError('Somut amend komutu onayı uyuşmuyor.')
        if row['batch_id']:raise ValueError('Toplu amend alt komutu tek başına gönderilemez.')
        if row['state']in BUSY:return self.reconcile(cid)
        if row['state']!='PREPARED':return {'command_id':cid,'state':row['state'],'duplicate':True}
        if runner is None:return self._state(cid,'SUPERSEDED',{'reason':'Oturum kapanmış; PUT gönderilmedi.'})
        if self.clock()>=b['expires_at']:return self._state(cid,'EXPIRED')
        start=self.clock();self.x.sync_time()
        before,a,_=self._validate(s,runner,b['client_id'],b['quantity'],b['price'])
        if before!=b['before_params']or str(a['orderId'])!=str(b['order_id']):raise ValueError('Amend öncesi emir sürümü değişti.')
        if self.clock()>=b['expires_at']:return self._state(cid,'EXPIRED')
        if not 0<=self.clock()-start<=self.limits.max_age_seconds:raise ValueError('Amend gönderim görünümü eskidi.')
        p=self._wire(b)
        with transaction(self.store)as db:
            if db.execute("UPDATE order_modifications SET state='SUBMITTING'WHERE command_id=?AND state='PREPARED'",(cid,)).rowcount!=1:
                raise ValueError('Amend komutu başka süreçte kullanıldı.')
        if not self._final_guard(b,s)or not 0<=self.clock()-start<=self.limits.max_age_seconds:
            return self._state(cid,'NOT_SENT',{'reason':'Gönderim öncesi amend yetkisi/görünümü sona erdi.'})
        try:self.x.request('PUT','/fapi/v1/order',p)
        except ExchangeError as exc:
            if exc.delivery_status in('REJECTED','NOT_SENT'):return self._state(cid,'REJECTED',{'code':exc.code})
            self._state(cid,'UNKNOWN',{'code':exc.code});return self.reconcile(cid)
        self._state(cid,'ACKNOWLEDGED')
        return self.reconcile(cid)

    def _wire(self,b):
        before=b['before_params']
        p={'symbol':before['symbol'],'origClientOrderId':b['client_id'],'side':before['side'],
           'quantity':b['quantity'],'price':b['price'],'modifyId':b['modify_id']}
        if str(before.get('reduceOnly')).lower()=='true':p['reduceOnly']='true'
        return p

    def _final_guard(self,b,s):
        if self.clock()>=b['expires_at']:return False
        side=b['before_params']['side'];ps=b['before_params']['positionSide']
        opening=(s['engine']=='v2'or(ps=='BOTH'and str(b['before_params'].get('reduceOnly')).lower()!='true')
                 or(ps=='LONG'and side=='BUY')or(ps=='SHORT'and side=='SELL'))
        if opening:
            row=self.service.show(s['plan_ref']['plan_id'],s['plan_ref']['version'])
            if (self.clock()>=timestamp(s['plan']['expires_at'])or self.store.halt_reason()
                    or(s['engine']=='v2'and self.clock()>=row['approval_until'])
                    or self.store.db.execute('SELECT 1 FROM control WHERE name=?',('entry_revoked:'+s['entry_id'],)).fetchone()):return False
        return True

    def prepare_batch(self,sid,changes,ttl=120):
        if not isinstance(changes,list)or not 1<=len(changes)<=5:raise ValueError('Toplu amend 1–5 alt emir gerektirir.')
        if any(not isinstance(c,dict)or set(c)!={'client_id','quantity','price'}for c in changes):raise ValueError('Toplu amend alanları geçersiz.')
        if any(not isinstance(c['client_id'],str)for c in changes):raise ValueError('Toplu amend istemci kimliği metin olmalı.')
        if len({c['client_id']for c in changes})!=len(changes):raise ValueError('Toplu amend aynı emri iki kez içeremez.')
        prepared=[]
        try:
            for c in changes:prepared.append(self.prepare(sid,c['client_id'],c['quantity'],c['price'],ttl))
            bid=uuid.uuid4().hex
            body={'batch_id':bid,'session_id':sid,'owner':self.service.owner,'account_ref':self.account_ref,
                  'commands':[p['command_id']for p in prepared],'expires_at':min(p['expires_at']for p in prepared)}
            h=digest(body)
            with transaction(self.store)as db:
                db.execute('INSERT INTO order_modify_batches VALUES(?,?,?,?)',(bid,canonical(body),h,'PREPARED'))
                for p in prepared:
                    if db.execute("UPDATE order_modifications SET batch_id=? WHERE command_id=?AND state='PREPARED'",(bid,p['command_id'])).rowcount!=1:
                        raise ValueError('Toplu amend alt komutu değişti.')
            return {'batch_id':bid,'digest':h,'state':'PREPARED','commands':prepared,'session_id':sid}
        except Exception:
            for p in prepared:
                with self.store.db:self.store.db.execute("UPDATE order_modifications SET state='CANCELED'WHERE command_id=?AND state='PREPARED'",(p['command_id'],))
            raise

    def _batch(self,bid):
        row=self.store.db.execute('SELECT * FROM order_modify_batches WHERE batch_id=?',(bid,)).fetchone()
        if row is None:raise ValueError('Toplu amend bulunamadı.')
        b=json.loads(row['body'])
        if digest(b)!=row['digest']or b['owner']!=self.service.owner or b['account_ref']!=self.account_ref:
            raise ValueError('Toplu amend kapsamı/özeti uyuşmuyor.')
        members=[self._row(cid)for cid in b['commands']]
        if any(r['batch_id']!=bid or c['session_id']!=b['session_id']for r,c,_,_ in members):raise ValueError('Toplu amend üyeliği uyuşmuyor.')
        return dict(row),b,members

    def reconcile_batch(self,bid):
        row,b,members=self._batch(bid)
        outcomes=[]
        for r,c,_,_ in members:
            outcomes.append(self.reconcile(c['command_id'])if r['state']in BUSY else{'command_id':c['command_id'],'state':r['state']})
        states={r['state']for r in outcomes}
        state='APPLIED'if states=={'APPLIED'}else('PARTIAL'if states&BUSY else'FINAL_WITH_ERRORS')
        if row['state']=='PREPARED':state='PREPARED'
        if row['state']in('EXPIRED','CANCELED'):state=row['state']
        with self.store.db:self.store.db.execute('UPDATE order_modify_batches SET state=?WHERE batch_id=?',(state,bid))
        return {'batch_id':bid,'state':state,'commands':outcomes,'session_id':b['session_id'],'automatic_resend':False}

    def apply_batch(self,bid,confirmed_digest):
        row,b,members=self._batch(bid)
        if row['digest']!=confirmed_digest:raise ValueError('Somut toplu amend özeti uyuşmuyor.')
        if row['state']!='PREPARED':return self.reconcile_batch(bid)
        if self.clock()>=b['expires_at']:
            with transaction(self.store)as db:
                for r,c,_,_ in members:db.execute("UPDATE order_modifications SET state='EXPIRED'WHERE command_id=?AND state='PREPARED'",(c['command_id'],))
                db.execute("UPDATE order_modify_batches SET state='EXPIRED'WHERE batch_id=?",(bid,))
            return self.reconcile_batch(bid)
        start=self.clock();self.x.sync_time()
        for r,c,s,runner in members:
            if r['state']!='PREPARED'or runner is None:raise ValueError('Toplu amend üyeleri hazır/etkin değil.')
            before,a,_=self._validate(s,runner,c['client_id'],c['quantity'],c['price'])
            if before!=c['before_params']or str(a['orderId'])!=str(c['order_id']):raise ValueError('Toplu amend öncül emir sürümü değişti.')
        if not 0<=self.clock()-start<=self.limits.max_age_seconds:raise ValueError('Toplu amend görünümü eskidi.')
        with transaction(self.store)as db:
            for r,c,_,_ in members:
                if db.execute("UPDATE order_modifications SET state='SUBMITTING'WHERE command_id=?AND state='PREPARED'",(c['command_id'],)).rowcount!=1:raise ValueError('Toplu amend başka süreçte kullanıldı.')
            if db.execute("UPDATE order_modify_batches SET state='SUBMITTING'WHERE batch_id=?AND state='PREPARED'",(bid,)).rowcount!=1:raise ValueError('Toplu amend başka süreçte kullanıldı.')
        if any(not self._final_guard(c,s)for _,c,s,_ in members)or not 0<=self.clock()-start<=self.limits.max_age_seconds:
            for r,c,_,_ in members:self._state(c['command_id'],'NOT_SENT')
            return self.reconcile_batch(bid)
        try:reply=self.x.request('PUT','/fapi/v1/batchOrders',{'batchOrders':json.dumps([self._wire(c)for _,c,_,_ in members],separators=(',',':'))})
        except ExchangeError as exc:
            for r,c,_,_ in members:self._state(c['command_id'],'REJECTED'if exc.delivery_status in('REJECTED','NOT_SENT')else'UNKNOWN',{'code':exc.code})
            return self.reconcile_batch(bid)
        valid=isinstance(reply,list)and len(reply)==len(members)
        for i,(r,c,_,_) in enumerate(members):
            item=reply[i]if valid and isinstance(reply[i],dict)else{}
            rejected=type(item.get('code'))is int and item['code']in(-1100,-1102,-1111,-2011,-2019,-2021,-2022,-5047)
            self._state(c['command_id'],'REJECTED'if rejected else'ACKNOWLEDGED')
        return self.reconcile_batch(bid)

    def cancel_batch(self,bid,confirmed_digest):
        row,b,members=self._batch(bid)
        if row['digest']!=confirmed_digest:raise ValueError('Toplu amend iptal özeti uyuşmuyor.')
        if row['state']!='PREPARED'or any(r['state']not in('PREPARED','EXPIRED')for r,_,_,_ in members):
            raise ValueError('Gönderilmiş/belirsiz toplu amend yerel iptalle temizlenemez.')
        with transaction(self.store)as db:
            for r,c,_,_ in members:db.execute("UPDATE order_modifications SET state='CANCELED'WHERE command_id=?",(c['command_id'],))
            db.execute("UPDATE order_modify_batches SET state='CANCELED'WHERE batch_id=?",(bid,))
        return self.reconcile_batch(bid)
