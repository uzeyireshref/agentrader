"""Durable, explicitly confirmed demo account settings. Orders are never created."""
import hashlib
import json
import re
import time
import uuid

from agentrader.shared.exchange import ExchangeError
from agentrader.bot.plans import canonical,digest,transaction
from agentrader.bot.risk import number
from agentrader.bot.brackets import leverage_constraints


def affected_products(kind):
    return ['USD-M','COIN-M'] if kind=='POSITION_MODE' else ['USD-M']


def command_target(kind,value,symbol=None):
    if kind in ('LEVERAGE','MARGIN_TYPE'):
        if not isinstance(symbol,str) or not re.fullmatch(r'[A-Z0-9]{2,20}USDT',symbol):
            raise ValueError('Sembol gerekli.')
        if kind=='LEVERAGE':
            if type(value) is not int or value<1: raise ValueError('Kaldıraç geçersiz.')
            return '/fapi/v1/leverage',{'symbol':symbol,'leverage':value}
        if value not in ('CROSSED','ISOLATED'): raise ValueError('Teminat modu geçersiz.')
        return '/fapi/v1/marginType',{'symbol':symbol,'marginType':value}
    if type(value) is not bool or symbol is not None:
        raise ValueError('Hesap ayarı boolean olmalı; sembol içermez.')
    if kind=='POSITION_MODE': return '/fapi/v1/positionSide/dual',{'dualSidePosition':str(value).lower()}
    if kind=='MULTI_ASSETS': return '/fapi/v1/multiAssetsMargin',{'multiAssetsMargin':str(value).lower()}
    if kind=='FEE_BURN': return '/fapi/v1/feeBurn',{'feeBurn':str(value).lower()}
    raise ValueError('Desteklenmeyen ayar komutu.')


def account_command_body(kind,value,symbol,owner,account_ref,ttl=300,*,command_id=None,now=None):
    """Build a setting intent without committing, for atomic parent/child preparation."""
    if type(ttl) is not int or not 1<=ttl<=600:raise ValueError('Komut geçerliliği 1–600 saniye.')
    if command_id is not None and not re.fullmatch('[a-f0-9]{32}',command_id):
        raise ValueError('Ayar komutu kimliği geçersiz.')
    path,params=command_target(kind,value,symbol)
    return {'command_id':command_id or uuid.uuid4().hex,'environment':'demo','kind':kind,'value':value,
            'symbol':symbol,'path':path,'params':params,'owner':owner,
            'account_ref':account_ref,'expires_at':(time.time() if now is None else now)+ttl,
            'affected_products':affected_products(kind)}


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
            db.execute('''CREATE TABLE IF NOT EXISTS account_command_checks (
                command_id TEXT PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL)''')

    def prepare(self,kind,value,symbol=None,ttl=300):
        body=account_command_body(kind,value,symbol,self.owner,self.account_ref,ttl)
        h=digest(body)
        with self.store.db:
            self.store.db.execute('INSERT INTO account_commands VALUES (?,?,?,?,NULL)',
                                  (body['command_id'],canonical(body),h,'PREPARED'))
        return {'command_id':body['command_id'],'digest':h,'kind':kind,'value':value,
                'symbol':symbol,'state':'PREPARED','expires_at':body['expires_at'],'affected_products':body['affected_products']}

    def row(self,command_id):
        row=self.store.db.execute('SELECT * FROM account_commands WHERE command_id=?',(command_id,)).fetchone()
        if not row: raise ValueError('Ayar komutu bulunamadı.')
        body=json.loads(row['body'])
        path,params=command_target(body['kind'],body['value'],body['symbol'])
        if (digest(body)!=row['digest'] or body['owner']!=self.owner or body['account_ref']!=self.account_ref
                or body['environment']!='demo' or (body['path'],body['params'])!=(path,params)):
            raise ValueError('Ayar komutu kapsamı veya kimliği uyuşmuyor.')
        if 'affected_products' in body and body['affected_products']!=affected_products(body['kind']):raise ValueError('Ayarın etkilenen ürün kapsamı uyuşmuyor.')
        return dict(row),body

    def show(self,command_id):
        row,body=self.row(command_id)
        return {'command_id':command_id,'digest':row['digest'],'state':row['state'],'request':body,
                'affected_products':affected_products(body['kind']),'result':json.loads(row['result']) if row['result'] else None,
                'automatic_resend':False}

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
            if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows):raise ValueError('Sembol ayarı yanıtı geçersiz.')
            selected=[r for r in rows if r.get('symbol')==body['symbol']]
            if len(selected)!=1:raise ValueError('Tekil sembol ayarı gerekli.')
            selected=selected[0]
            if kind=='LEVERAGE':
                value=number(selected.get('leverage'))
                if type(selected.get('leverage')) is bool or value<1 or value!=value.to_integral_value():raise ValueError('Gözlenen kaldıraç geçersiz.')
                value=int(value)
            else:
                value=selected.get('marginType')
                if value not in ('CROSSED','ISOLATED'):raise ValueError('Gözlenen teminat modu geçersiz.')
            self.last_observation={'USD-M':value};return value
        payload=self.x.get(body['path'])
        field={'POSITION_MODE':'dualSidePosition','MULTI_ASSETS':'multiAssetsMargin','FEE_BURN':'feeBurn'}[kind]
        if not isinstance(payload,dict) or type(payload.get(field)) is not bool: raise ValueError('Ayar yanıtı boolean değil.')
        self.last_observation={'USD-M':payload[field]}
        if kind=='POSITION_MODE':
            coin=self.x.get('/dapi/v1/positionSide/dual')
            if not isinstance(coin,dict) or type(coin.get(field)) is not bool:raise ValueError('COIN-M pozisyon modu doğrulanamadı.')
            self.last_observation['COIN-M']=coin[field]
            if coin[field]!=payload[field]:raise ValueError('USD-M ve COIN-M ortak pozisyon modu uyuşmuyor.')
        return payload[field]

    def _flat(self,body):
        products=[('USD-M','/fapi/v3/positionRisk','/fapi/v1/openOrders','/fapi/v1/openAlgoOrders')];proof={}
        if body['kind']=='POSITION_MODE':products.append(('COIN-M','/dapi/v1/positionRisk','/dapi/v1/openOrders','/dapi/v1/openAlgoOrders'))
        for product,position_path,normal_path,algo_path in products:
            positions=self.x.get(position_path);normal=self.x.get(normal_path);algos=self.x.get(algo_path)
            if any(not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows) for rows in (positions,normal,algos)):
                raise ValueError('Ürün emir/pozisyon görünümü doğrulanamadı; boş hesap varsayılmaz.')
            if any('positionAmt' not in p or number(p['positionAmt'])!=0 for p in positions) or normal or algos:
                raise ValueError('Etkilenen ürünlerin hesabı boş ve emirsiz olmalı.')
            proof[product]={'position_rows':len(positions),'nonzero_positions':0,'normal_orders':0,'algo_orders':0,'observed_at':time.time()}
        return proof

    def reconcile(self,command_id):
        row,body=self.row(command_id)
        if row['state'] not in ('SUBMITTING','UNKNOWN'):
            return {'command_id':command_id,'state':row['state'],'duplicate':True}
        start=time.time()
        try:
            current=self.observed(body)
            if not 0<=time.time()-start<=15:raise ValueError('Ayar teyit görünümü eskidi.')
        except (ValueError,ExchangeError) as exc:
            return self.set_state(command_id,'UNKNOWN',{'reason':'SETTING_OBSERVATION_UNVERIFIED','code':getattr(exc,'code',None),
                'affected_products':affected_products(body['kind']),'automatic_resend':False})
        if current==body['value']:
            result={'observed':current,'observed_products':self.last_observation,
                'affected_products':affected_products(body['kind']),'resolved_by_read':True}
            check=self.store.db.execute('SELECT * FROM account_command_checks WHERE command_id=?',(command_id,)).fetchone()
            if check:
                proof=json.loads(check['body'])
                if digest(proof)!=check['digest'] or proof['command_digest']!=row['digest']:raise ValueError('Ayar gönderim kanıtı bozuk.')
                result['preflight']=proof
            return self.set_state(command_id,'APPLIED',result)
        return self.set_state(command_id,'UNKNOWN',{'observed':current,'observed_products':self.last_observation,'automatic_resend':False})

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
        # Legacy boolean is accepted for source compatibility, never trusted as proof.
        if self.store.sessions(): raise ValueError('Aktif yönetilen oturum varken hesap ayarı değişmez.')
        start=time.time();self.x.sync_time();flat=self._flat(body)
        constraints=None
        if body['kind']=='LEVERAGE':constraints=leverage_constraints(self.x.get('/fapi/v1/leverageBracket',{'symbol':body['symbol']}),body['symbol'],body['value'])
        current=self.observed(body)
        if not 0<=time.time()-start<=15:raise ValueError('Ayar hazırlık görünümü eskidi.')
        if time.time()>=body['expires_at']:return self.set_state(command_id,'EXPIRED')
        if current==body['value']: return self.set_state(command_id,'APPLIED',{'observed':current,'observed_products':self.last_observation,
            'changed':False,'affected_products':affected_products(body['kind']),'constraints':constraints,'flat_products':flat})
        # Re-read both affected products and the complete symbol ladder at the final send boundary.
        flat=self._flat(body)
        if body['kind']=='LEVERAGE':constraints=leverage_constraints(self.x.get('/fapi/v1/leverageBracket',{'symbol':body['symbol']}),body['symbol'],body['value'])
        if not 0<=time.time()-start<=15:raise ValueError('Ayar gönderim görünümü eskidi.')
        if time.time()>=body['expires_at']: return self.set_state(command_id,'EXPIRED')
        with transaction(self.store) as db:
            updated=db.execute("UPDATE account_commands SET state='SUBMITTING' WHERE command_id=? AND state='PREPARED'",(command_id,))
            if updated.rowcount!=1: raise ValueError('Komut başka süreç tarafından kullanıldı.')
            proof={'command_digest':row['digest'],'account_ref':self.account_ref,'affected_products':affected_products(body['kind']),
                   'flat_verified':True,'flat_products':flat,'observed_products':self.last_observation,'constraints':constraints,'observed_at':time.time()}
            db.execute('INSERT INTO account_command_checks VALUES(?,?,?)',(command_id,canonical(proof),digest(proof)))
        if time.time()>=body['expires_at'] or not 0<=time.time()-start<=15:
            return self.set_state(command_id,'NOT_SENT',{'reason':'EXPIRED_BEFORE_DELIVERY','automatic_resend':False})
        try:
            self.x.request('POST',body['path'],body['params'])
        except ExchangeError as exc:
            if exc.delivery_status in ('NOT_SENT','REJECTED'):
                return self.set_state(command_id,'REJECTED',{'code':exc.code,'http_status':exc.http_status})
            self.set_state(command_id,'UNKNOWN',{'code':exc.code,'http_status':exc.http_status})
        result=self.reconcile(command_id)
        if constraints is not None:
            result['constraints']=constraints
        return result
