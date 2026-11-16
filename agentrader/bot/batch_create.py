"""Durable native batch creation for pre-authorized normal LIMIT proposals.

The runner supplies fresh scope/risk checks before reservation and before send.
All client identities are reserved atomically; partial/lost replies never resend.
"""
import hashlib
import json
import time
import re

from agentrader.shared.exchange import ExchangeError
from agentrader.bot.order_journal import OrderJournal
from agentrader.bot.order_revisions import effective_params
from agentrader.bot.plans import canonical,digest,transaction
from agentrader.bot.risk import number

REJECTIONS={-1100,-1102,-1111,-2019,-2021,-2022,-4164,-4003,-5022}


class NativeBatchCreate:
    def __init__(self,exchange,store,session_id,*,max_age_seconds=15,owners=None):
        self.x,self.store,self.session_id=exchange,store,session_id
        self.max_age_seconds=max_age_seconds
        self.owners=owners
        self.account_ref=hashlib.sha256(exchange.config.api_key.encode()).hexdigest()
        self.journal=OrderJournal(store)
        with store.db:store.db.execute('''CREATE TABLE IF NOT EXISTS order_create_batches (
            batch_id TEXT PRIMARY KEY,body TEXT NOT NULL,state TEXT NOT NULL)''')

    def _reconcile(self,body):
        outcomes=[]
        for p in body['params']:
            cid=p['newClientOrderId'];saved=self.store.intent(cid)
            if saved is None or saved['path']!='/fapi/v1/order'or json.loads(saved['params'])!=p:
                raise ValueError('Toplu oluşturma niyeti değişti.')
            if saved['state']=='REJECTED':
                self.journal.observe(cid,'batch-rejected',status='REJECTED',cumulative_filled='0',observed_ms=body['created_ms'])
                outcomes.append({'client_id':cid,'state':'REJECTED'});continue
            try:a=self.x.get('/fapi/v1/order',{'symbol':p['symbol'],'origClientOrderId':cid})
            except ExchangeError as exc:
                if exc.code!=-2013:raise
                self.store.update(cid,'UNKNOWN');outcomes.append({'client_id':cid,'state':'UNKNOWN'});continue
            effective=effective_params(self.store,cid)
            if (a.get('clientOrderId')!=cid or any(a.get(k)!=effective[k]for k in('symbol','side','positionSide','type'))
                    or any(a.get(k)!=effective[k] for k in ('timeInForce','priceMatch','selfTradePreventionMode','goodTillDate') if k in effective)
                    or number(a['origQty'])!=number(effective['quantity'])or ('price' in effective and number(a['price'])!=number(effective['price']))
                    or ('priceMatch' in effective and number(a.get('price',0))<=0)
                    or type(a.get('orderId')) is not int or a['orderId']<=0
                    or (effective['positionSide']=='BOTH'and str(a.get('reduceOnly',False)).lower()!=str(effective.get('reduceOnly',False)).lower())
                    or a.get('status')not in('NEW','PARTIALLY_FILLED','FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED')):
                raise ValueError('Toplu oluşturulan emir planlanan parametrelerle uyuşmuyor.')
            previous=json.loads(saved['response']) if saved.get('response') else {}
            if previous.get('orderId') is not None and previous['orderId']!=a['orderId']:raise ValueError('Toplu emir istemci kimliği yeniden kullanılmış.')
            self.journal.observe(cid,digest(a),status='EXPIRED'if a['status']=='EXPIRED_IN_MATCH'else a['status'],
                                 cumulative_filled=a['executedQty'],observed_ms=int(a['updateTime']))
            self.store.update(cid,a['status'],a)
            outcomes.append({'client_id':cid,'state':'RECONCILED','order_status':a['status'],'executed_quantity':a['executedQty']})
        state='UNKNOWN'if any(r['state']=='UNKNOWN'for r in outcomes)else('FINAL_WITH_ERRORS'if any(r['state']=='REJECTED'for r in outcomes)else'RECONCILED')
        with self.store.db:self.store.db.execute('UPDATE order_create_batches SET state=?WHERE batch_id=?',(state,body['batch_id']))
        if state=='UNKNOWN':self.store.halt('Toplu oluşturma alt emri belirsiz; yeniden POST yapılmayacak.')
        report={'batch_id':body['batch_id'],'state':state,'orders':outcomes,'automatic_resend':False}
        self.store.event('native_batch_created',report)
        return report

    def submit(self,proposals,authorize):
        if not isinstance(proposals,list)or not 1<=len(proposals)<=5 or not callable(authorize):
            raise ValueError('Toplu oluşturma 1–5 doğrulanmış emir ve kapsam denetimi gerektirir.')
        if any(not isinstance(p,dict)or not isinstance(p.get('params'),dict)for p in proposals):
            raise ValueError('Toplu oluşturma emir alanları geçersiz.')
        # Freeze caller-owned objects before the authorization callback can run.
        params=json.loads(canonical([p['params']for p in proposals]))
        if any(p.get('method')!='POST'or p.get('path')!='/fapi/v1/order'or p.get('operation')not in('OPEN','REDUCE')for p in proposals):
            raise ValueError('Toplu oluşturma yalnız normal açıcı/azaltıcı emirleri destekler.')
        allowed={'symbol','side','positionSide','type','quantity','newClientOrderId','price','timeInForce','priceMatch','goodTillDate','selfTradePreventionMode','newOrderRespType','reduceOnly'}
        if any(p.keys()-allowed or p.get('type') not in ('LIMIT','MARKET') or not p.get('newClientOrderId') or number(p.get('quantity',0))<=0 for p in params):
            raise ValueError('Toplu oluşturma yalnız normal LIMIT/MARKET emirlerini destekler.')
        for p in params:
            if p['type']=='LIMIT':
                if p.get('timeInForce') not in ('GTC','IOC','FOK','GTX','GTD') or ('price' in p)==('priceMatch' in p):raise ValueError('Toplu LIMIT fiyat/süre kapsamı geçersiz.')
                if 'price' in p and number(p['price'])<=0:raise ValueError('Toplu LIMIT fiyatı pozitif olmalı.')
            elif any(k in p for k in ('price','priceMatch','timeInForce','goodTillDate')):raise ValueError('Toplu MARKET limit seçenekleri içeremez.')
        if any(p.get('side')not in('BUY','SELL')or p.get('positionSide')not in('BOTH','LONG','SHORT')
               or not isinstance(p.get('symbol'),str)or not re.fullmatch(r'[A-Z0-9]{2,20}USDT',p['symbol'])
               or not isinstance(p['newClientOrderId'],str)or not re.fullmatch(r'[.A-Za-z:/0-9_-]{1,36}',p['newClientOrderId'])for p in params):
            raise ValueError('Toplu oluşturma sembol/yön/kimlik alanları geçersiz.')
        ids=[p['newClientOrderId']for p in params]
        if len(set(ids))!=len(ids):raise ValueError('Toplu oluşturma farklı kimlikler gerektirir.')
        params.sort(key=lambda p:p['newClientOrderId'])
        base={'account_ref':self.account_ref,'session_id':self.session_id,'params':params}
        if self.owners is not None:
            if set(self.owners)!=set(ids) or any(not isinstance(v,str) or not v for v in self.owners.values()):raise ValueError('Toplu emir oturum sahipleri eksik.')
            base['owners']=dict(self.owners)
        bid=digest(base);body=base|{'batch_id':bid,'created_ms':int(time.time()*1000)}
        old=self.store.db.execute('SELECT * FROM order_create_batches WHERE batch_id=?',(bid,)).fetchone()
        if old:
            previous=json.loads(old['body'])
            if {k:previous.get(k)for k in base}!=base or previous.get('batch_id')!=bid:raise ValueError('Toplu oluşturma kaydı özeti uyuşmuyor.')
            return self._reconcile(previous)
        if any(self.store.intent(cid)for cid in ids):raise ValueError('Mevcut emir kimliği yeni toplu gönderime karıştırılamaz.')
        operations={p['params']['newClientOrderId']:p['operation'] for p in proposals}
        fingerprint=digest(params)
        if authorize(params,'before_reserve')is not True or digest(params)!=fingerprint:
            raise ValueError('Toplu oluşturma plan/risk yetkisi doğrulanamadı.')
        for p in params:self.journal.register(p['newClientOrderId'],self.owners[p['newClientOrderId']] if self.owners is not None else self.session_id,p['symbol'],p['side'],p['quantity'])
        with transaction(self.store)as db:
            db.execute('INSERT INTO order_create_batches VALUES(?,?,?)',(bid,canonical(body),'SUBMITTING'))
            for p in params:db.execute('INSERT INTO intents(client_id,path,params,state)VALUES(?,?,?,?)',
                                      (p['newClientOrderId'],'/fapi/v1/order',json.dumps(p),'SUBMITTING'))
        try:
            from agentrader.bot.order_send_guard import validate_before_send
            for symbol in sorted({p['symbol'] for p in params}):
                group=[p for p in params if p['symbol']==symbol]
                validate_before_send(self.x,[{'params':p,'operation':operations[p['newClientOrderId']]} for p in group],
                                     'one-way' if all(p['positionSide']=='BOTH' for p in group) else 'hedge',self.max_age_seconds)
            if authorize(params,'before_send')is not True or digest(params)!=fingerprint:
                raise ValueError('Gönderim öncesi toplu emir yetkisi değişti.')
        except (ValueError,ExchangeError):
            for p in params:self.store.update(p['newClientOrderId'],'REJECTED',{'delivery_status':'NOT_SENT'})
            with self.store.db:self.store.db.execute("UPDATE order_create_batches SET state='NOT_SENT'WHERE batch_id=?",(bid,))
            raise
        try:reply=self.x.request('POST','/fapi/v1/batchOrders',{'batchOrders':json.dumps(params,separators=(',',':'))})
        except ExchangeError as exc:
            for p in params:self.store.update(p['newClientOrderId'],'REJECTED'if exc.delivery_status in('NOT_SENT','REJECTED')else'UNKNOWN',
                                            {'code':exc.code,'delivery_status':exc.delivery_status})
            return self._reconcile(body)
        if isinstance(reply,list)and len(reply)==len(params):
            for p,r in zip(params,reply):
                if isinstance(r,dict)and type(r.get('code'))is int and r['code']in REJECTIONS:self.store.update(p['newClientOrderId'],'REJECTED',{'code':r['code']})
        return self._reconcile(body)
