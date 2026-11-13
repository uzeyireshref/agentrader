"""Durable, explicitly confirmed demo account settings. Orders are never created."""
import hashlib
import json
import re
import time
import uuid

from .exchange import ExchangeError
from .plans import canonical,digest,transaction
from .risk import number


def command_target(kind,value,symbol=None):
    if kind in ('LEVERAGE','MARGIN_TYPE'):
        if not isinstance(symbol,str) or not re.fullmatch(r'[A-Z0-9]{2,20}USDT',symbol):
            raise ValueError('Sembol gerekli.')
        if kind=='LEVERAGE':
            if type(value) is not int or not 1<=value<=125: raise ValueError('Kaldıraç geçersiz.')
            return '/fapi/v1/leverage',{'symbol':symbol,'leverage':value}
        if value not in ('CROSSED','ISOLATED'): raise ValueError('Teminat modu geçersiz.')
        return '/fapi/v1/marginType',{'symbol':symbol,'marginType':value}
    if type(value) is not bool or symbol is not None:
        raise ValueError('Hesap ayarı boolean olmalı; sembol içermez.')
    if kind=='POSITION_MODE': return '/fapi/v1/positionSide/dual',{'dualSidePosition':str(value).lower()}
    if kind=='MULTI_ASSETS': return '/fapi/v1/multiAssetsMargin',{'multiAssetsMargin':str(value).lower()}
    if kind=='FEE_BURN': return '/fapi/v1/feeBurn',{'feeBurn':str(value).lower()}
    raise ValueError('Desteklenmeyen ayar komutu.')


class AccountCommands:
    def __init__(self,exchange,store,owner):
        if not owner: raise ValueError('Yerel yetkili kullanıcı gerekli.')
        self.x,self.store,self.owner=exchange,store,owner
        key=exchange.config.api_key
        self.account_ref=hashlib.sha256(key.encode()).hexdigest()
        with transaction(store) as db:
            old=db.execute("SELECT value FROM control WHERE name='plan_owner'").fetchone()
            if old and old['value']!=owner: raise ValueError('Hesap komutu yetkilisi uyuşmuyor.')
            db.execute("INSERT OR IGNORE INTO control VALUES ('plan_owner',?)",(owner,))
            db.execute('''CREATE TABLE IF NOT EXISTS account_commands (
                command_id TEXT PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL,
                state TEXT NOT NULL,result TEXT)''')

    def prepare(self,kind,value,symbol=None,ttl=300):
        if type(ttl) is not int or not 1<=ttl<=600: raise ValueError('Komut geçerliliği 1–600 saniye.')
        path,params=command_target(kind,value,symbol)
        body={'command_id':uuid.uuid4().hex,'environment':'demo','kind':kind,'value':value,
              'symbol':symbol,'path':path,'params':params,'owner':self.owner,
              'account_ref':self.account_ref,'expires_at':time.time()+ttl}
        h=digest(body)
        with self.store.db:
            self.store.db.execute('INSERT INTO account_commands VALUES (?,?,?,?,NULL)',
                                  (body['command_id'],canonical(body),h,'PREPARED'))
        return {'command_id':body['command_id'],'digest':h,'kind':kind,'value':value,
                'symbol':symbol,'state':'PREPARED','expires_at':body['expires_at']}

    def row(self,command_id):
        row=self.store.db.execute('SELECT * FROM account_commands WHERE command_id=?',(command_id,)).fetchone()
        if not row: raise ValueError('Ayar komutu bulunamadı.')
        body=json.loads(row['body'])
        path,params=command_target(body['kind'],body['value'],body['symbol'])
        if (digest(body)!=row['digest'] or body['owner']!=self.owner or body['account_ref']!=self.account_ref
                or body['environment']!='demo' or (body['path'],body['params'])!=(path,params)):
            raise ValueError('Ayar komutu kapsamı veya kimliği uyuşmuyor.')
        return dict(row),body

    def set_state(self,command_id,state,result=None):
        with self.store.db:
            self.store.db.execute('UPDATE account_commands SET state=?,result=? WHERE command_id=?',
                                  (state,json.dumps(result),command_id))
        self.store.event('account_command_state',{'command_id':command_id,'state':state,'result':result})
        return {'command_id':command_id,'state':state,'result':result}

    def observed(self,body):
        kind=body['kind']
        if kind in ('LEVERAGE','MARGIN_TYPE'):
            rows=self.x.get('/fapi/v1/symbolConfig',{'symbol':body['symbol']})
            selected=next(r for r in rows if r['symbol']==body['symbol'])
            return int(selected['leverage']) if kind=='LEVERAGE' else selected['marginType']
        payload=self.x.get(body['path'])
        field={'POSITION_MODE':'dualSidePosition','MULTI_ASSETS':'multiAssetsMargin','FEE_BURN':'feeBurn'}[kind]
        if type(payload.get(field)) is not bool: raise ValueError('Ayar yanıtı boolean değil.')
        return payload[field]

    def reconcile(self,command_id):
        row,body=self.row(command_id)
        if row['state'] not in ('SUBMITTING','UNKNOWN'):
            return {'command_id':command_id,'state':row['state'],'duplicate':True}
        current=self.observed(body)
        if current==body['value']:
            return self.set_state(command_id,'APPLIED',{'observed':current,'resolved_by_read':True})
        return self.set_state(command_id,'UNKNOWN',{'observed':current,'automatic_resend':False})

    def apply(self,command_id,confirmed_digest,*,cross_product_flat_verified=False):
        """Caller holds execution_lock. Confirmation refers to this exact command.

        Development approval alone is not confirmed_digest; no command is run by default.
        """
        row,body=self.row(command_id)
        if confirmed_digest!=row['digest']: raise ValueError('Somut ayar komutu onayı uyuşmuyor.')
        if row['state'] in ('SUBMITTING','UNKNOWN'): return self.reconcile(command_id)
        if row['state']!='PREPARED': return {'command_id':command_id,'state':row['state'],'duplicate':True}
        if time.time()>=body['expires_at']: return self.set_state(command_id,'EXPIRED')
        unresolved=self.store.unresolved_account_command()
        if unresolved: raise ValueError('Önce belirsiz hesap komutunu uzlaştırın.')
        if body['kind'] in ('POSITION_MODE','MULTI_ASSETS') and not cross_product_flat_verified:
            raise ValueError('Hesap çapındaki değişim için diğer ürünlerin de boşluğu doğrulanmalı.')
        if self.store.sessions(): raise ValueError('Aktif yönetilen oturum varken hesap ayarı değişmez.')
        self.x.sync_time()
        if (any(number(p['positionAmt'])!=0 for p in self.x.get('/fapi/v3/positionRisk'))
                or self.x.get('/fapi/v1/openOrders') or self.x.get('/fapi/v1/openAlgoOrders')):
            raise ValueError('Hesap boş ve emirsiz olmalı.')
        current=self.observed(body)
        if current==body['value']: return self.set_state(command_id,'APPLIED',{'observed':current,'changed':False})
        if body['kind']=='LEVERAGE':
            brackets=self.x.get('/fapi/v1/leverageBracket',{'symbol':body['symbol']})
            selected=next(r for r in brackets if r['symbol']==body['symbol'])
            if not any(b['initialLeverage']>=body['value'] for b in selected['brackets']):
                raise ValueError('Kaldıraç sözleşmede desteklenmiyor.')
        if time.time()>=body['expires_at']: return self.set_state(command_id,'EXPIRED')
        with transaction(self.store) as db:
            updated=db.execute("UPDATE account_commands SET state='SUBMITTING' WHERE command_id=? AND state='PREPARED'",(command_id,))
            if updated.rowcount!=1: raise ValueError('Komut başka süreç tarafından kullanıldı.')
        try:
            self.x.request('POST',body['path'],body['params'])
        except ExchangeError as exc:
            if exc.delivery_status in ('NOT_SENT','REJECTED'):
                return self.set_state(command_id,'REJECTED',{'code':exc.code,'http_status':exc.http_status})
            self.set_state(command_id,'UNKNOWN',{'code':exc.code,'http_status':exc.http_status})
        return self.reconcile(command_id)
