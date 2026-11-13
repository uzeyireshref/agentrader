"""Exact, durable isolated-margin adjustments; additive requests never retry.

Margin history has no client command ID. A lost POST response cannot be proven
ours merely because a matching history row exists, so it remains UNKNOWN.
Caller holds execution_lock. Managed positions require an explicit session binding.
"""
import hashlib
import json
import re
import time
import uuid
from collections import Counter

from .account_commands import AccountCommands
from .exchange import ExchangeError
from .plans import canonical, digest, transaction
from .portfolio import liquidation_price
from .risk import number, RiskLimits
from .v2_preflight import fresh

PATH='/fapi/v1/positionMargin'


class IsolatedMarginCommands:
    def __init__(self,exchange,store,owner,clock=time.time,*,session_id=None,limits=None):
        AccountCommands(exchange,store,owner)  # Bind the existing local owner.
        self.x,self.store,self.owner,self.clock=exchange,store,owner,clock
        self.account_ref=hashlib.sha256(exchange.config.api_key.encode()).hexdigest()
        self.session_id=session_id
        self.managed_ref=None
        self.limits=limits or RiskLimits()
        with store.db:
            store.db.execute('''CREATE TABLE IF NOT EXISTS margin_commands (
                command_id TEXT PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL,
                state TEXT NOT NULL,ack TEXT,result TEXT)''')

    def _params(self,symbol,position_side,action,amount):
        if not isinstance(symbol,str)or not re.fullmatch(r'[A-Z0-9]{2,20}USDT',symbol):raise ValueError('USDT sembolü gerekli.')
        if position_side not in('BOTH','LONG','SHORT')or action not in('ADD','REMOVE'):raise ValueError('Pozisyon tarafı/teminat işlemi geçersiz.')
        amount=number(amount)
        if amount<=0:raise ValueError('Teminat miktarı pozitif olmalı.')
        return {'symbol':symbol,'positionSide':position_side,'amount':str(amount),'type':1 if action=='ADD'else 2}

    def _history(self,params,start_ms):
        end=int(self.clock()*1000)+getattr(self.x,'offset_ms',0)
        if not 0<=end-start_ms<=30*86400000:raise ValueError('Teminat geçmişi doğrulama penceresi geçersiz/eski.')
        rows=self.x.get(PATH+'/history',{'symbol':params['symbol'],'startTime':start_ms,'endTime':end,'limit':500})
        if not isinstance(rows,list)or len(rows)>=500:raise ValueError('Teminat geçmişinde sayfalama/doğrulama gerekli.')
        normalized=[]
        for r in rows:
            if r.get('symbol')!=params['symbol']or type(r.get('time'))is not int or not start_ms<=r['time']<=end:
                raise ValueError('Teminat geçmişi sembol/zaman alanı geçersiz.')
            if r.get('positionSide')not in('BOTH','LONG','SHORT')or type(r.get('type'))is not int or r['type']not in(1,2):
                raise ValueError('Teminat geçmişi alanları geçersiz.')
            normalized.append({k:r[k]for k in('symbol','positionSide','time','type','asset','deltaType')}|
                              {'amount':str(number(r['amount']))})
        return normalized

    def _position(self,params):
        start=self.clock();self.x.sync_time()
        if self.store.sessions() or self.session_id is not None:
            self._managed_scope(params)
        config=self.x.get('/fapi/v1/accountConfig')
        if config.get('canTrade')is not True or config.get('multiAssetsMargin')is not False:
            raise ValueError('İzole teminat için işlem uygunluğu ve single-asset modu gerekli.')
        mode=self.x.get('/fapi/v1/positionSide/dual').get('dualSidePosition')
        if type(mode)is not bool or mode!=(params['positionSide']!='BOTH'):raise ValueError('Teminat pozisyon tarafı hesap moduyla uyuşmuyor.')
        rows=self.x.get('/fapi/v1/symbolConfig',{'symbol':params['symbol']})
        selected=[r for r in rows if r['symbol']==params['symbol']]
        if len(selected)!=1 or selected[0]['marginType']!='ISOLATED':raise ValueError('Sözleşme ISOLATED olmalı.')
        rows=self.x.get('/fapi/v3/positionRisk',{'symbol':params['symbol']})
        selected=[r for r in rows if r['symbol']==params['symbol']and r['positionSide']==params['positionSide']and number(r['positionAmt'])]
        if len(selected)!=1:raise ValueError('Seçili tarafta tek açık izole pozisyon gerekli.')
        p=selected[0];q=number(p['positionAmt'])
        if (params['positionSide']=='LONG'and q<0)or(params['positionSide']=='SHORT'and q>0):raise ValueError('Pozisyon miktar yönü uyuşmuyor.')
        entry,wallet=number(p['entryPrice']),number(p['isolatedWallet'])
        if entry<=0 or wallet<=0:raise ValueError('Pozisyon giriş/izole cüzdan verisi geçersiz.')
        if self.x.get('/fapi/v1/openOrders',{'symbol':params['symbol']}) and self.managed_ref is None:
            raise ValueError('Bekleyen normal emir varken teminat değişmez.')
        if not 0<=self.clock()-start<=15:raise ValueError('Teminat pozisyon görünümü eskidi.')
        return {'symbol':params['symbol'],'positionSide':params['positionSide'],'positionAmt':str(q),
                'entryPrice':str(entry),'isolatedWallet':str(wallet)}

    def _managed_scope(self,params):
        if not self.session_id:
            raise ValueError('Aktif bot oturumunun teminatı bağımsız komutla değiştirilmez; session-id gerekli.')
        from .plans import PlanService
        from .account_runtime import runner_for
        from .account_ownership import AccountOwnership
        sessions=self.store.sessions()
        matches=[s for s in sessions if s['id']==self.session_id]
        if len(matches)!=1:
            raise ValueError('Teminat için sahipliği doğrulanmış etkin oturum gerekli.')
        s=matches[0]
        if s.get('engine') not in ('v2','grid-v2','neutral-v2'):
            raise ValueError('Bu oturum motorunda teminat entegrasyonu desteklenmiyor.')
        service=PlanService(self.store,self.owner)
        runner=runner_for(service,self.x,self.limits,s)
        runner._session(self.session_id)
        plan=s['plan'];ps=('BOTH'if plan['position_mode']=='one-way'else
                            params['positionSide'] if s['engine']=='neutral-v2' else plan['direction'])
        if (s['account_ref']!=self.account_ref or plan['execution']['margin_mode']!='ISOLATED'
                or (params['symbol'],params['positionSide'])!=(s['symbol'],ps)
                or s['engine']=='neutral-v2' and ps not in ('LONG','SHORT')):
            raise ValueError('Teminat komutu etkin planın hesap/sembol/izole tarafıyla uyuşmuyor.')
        proof={'session_id':s['id'],'engine':s['engine'],'plan_ref':s['plan_ref'],'account_ref':s['account_ref']}
        if self.managed_ref is not None and proof!=self.managed_ref:
            raise ValueError('Teminat komutunun bağlı olduğu plan değişti.')
        report=runner.manage(self.session_id,execute=False)
        if report['state'] not in ('MANAGING','GRID_RUNNING','GRID_DRAINING','NEUTRAL_RUNNING','NEUTRAL_DRAINING'):
            raise ValueError('Teminat değişiminden önce bekleyen emir/koruma yönetimi tamamlanmalı.')
        # Existing single-session records remain usable; admitting peers or
        # resting grid orders requires the full account ownership proof.
        if len(sessions)>1 or s['engine']!='v2':
            ownership=AccountOwnership(runner).verify()
            if any(not leg['protected'] for leg in ownership['sessions']):
                raise ValueError('Teminat değişiminde tüm etkin tarafların stop koruması gerekli.')
        self.managed_ref=proof

    def _shared_risk(self,params):
        """Keep all refill envelopes and debit additions before delivery.

        No released-margin credit, no envelope rewrite, no budget increase.
        Legacy SINGLE alone retains its existing checks.
        """
        if self.managed_ref is None:return
        sessions=self.store.sessions()
        if len(sessions)==1 and sessions[0]['engine']=='v2':return
        from .account_runtime import runner_for
        from .plans import PlanService
        from .v2_preflight import collateral_usdt
        from .history import income_history
        from datetime import datetime,timezone
        started=self.clock()
        account=self.x.get('/fapi/v3/account')
        config=self.x.get('/fapi/v1/accountConfig')
        if config.get('canTrade') is not True or config.get('multiAssetsMargin') is not False:
            raise ValueError('Ortak teminat için işlem uygun single-asset hesap gerekli.')
        collateral=collateral_usdt(account,config)
        if params['type']==1:collateral-=number(params['amount'])
        midnight=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
        incomes=income_history(self.x,int(midnight.timestamp()*1000))
        relevant=[r for r in incomes if r['incomeType'] in ('REALIZED_PNL','COMMISSION','FUNDING_FEE')]
        if any(r['asset']!='USDT' for r in relevant):raise ValueError('Ortak teminat günlük varlık dönüşümü gerekli.')
        pnl=sum((number(r['income']) for r in relevant),number(0))
        pnl+=min(number(next(a for a in account['assets'] if a['asset']=='USDT').get('unrealizedProfit',0)),number(0))
        if datetime.now(timezone.utc).date()!=midnight.date():raise ValueError('Günlük teminat görünümü yenilenmeli.')
        runner=runner_for(PlanService(self.store,self.owner),self.x,self.limits,
                          next(s for s in sessions if s['id']==self.session_id))
        runner.book.evaluate({'collateral':str(collateral),'daily_loss':str(max(-pnl,number(0))),
                              'observed_at':started},self.limits,exchange=self.x)

    def _check_change(self,params,p):
        amount=number(params['amount'])
        self._shared_risk(params)
        if params['type']==1:
            if self.managed_ref is not None:
                plan=next(s['plan'] for s in self.store.sessions() if s['id']==self.session_id)
                if plan['sizing']['kind']=='MARGIN':
                    s=next(s for s in self.store.sessions() if s['id']==self.session_id)
                    budget=number(plan['sizing']['amount']);pending=number(0)
                    if s['engine']!='v2':
                        exposures=s['compiled']['exposures']
                        direction=plan['direction'] if params['positionSide']=='BOTH' else params['positionSide']
                        legs=[e for e in exposures if e['direction']==direction]
                        full=sum((number(e['quantity'])*number(e['notional_price'] or e['entry'])/e['leverage'] for e in legs),number(0))
                        pending=max(number(0),full-abs(number(p['positionAmt']))*number(p['entryPrice'])/plan['execution']['leverage'])
                        if s['engine']=='neutral-v2':
                            budget*=number(plan['grid']['long_fraction' if direction=='LONG' else 'short_fraction'])
                    if number(p['isolatedWallet'])+amount+pending>budget:
                        raise ValueError('Teminat eklemesi ve kalan grid rezervi planın açık MARGIN bütçesini aşıyor.')
            account=self.x.get('/fapi/v3/account')
            assets=[a for a in account['assets']if a['asset']=='USDT']
            if len(assets)!=1 or amount>number(assets[0]['availableBalance']):raise ValueError('Kullanılabilir USDT teminatı yetersiz.')
            return
        wallet=number(p['isolatedWallet'])-amount
        if wallet<=0:raise ValueError('Teminat azaltması izole cüzdanı tüketiyor.')
        if self.managed_ref is not None:
            plan=next(s['plan'] for s in self.store.sessions() if s['id']==self.session_id)
            if wallet<abs(number(p['positionAmt']))*number(p['entryPrice'])/plan['execution']['leverage']:
                raise ValueError('Kalan izole cüzdan ortak sahipliğin başlangıç teminatını karşılamıyor.')
        mark=self.x.get('/fapi/v1/premiumIndex',{'symbol':params['symbol']})
        fresh(mark,params['symbol'],int(self.clock()*1000)+getattr(self.x,'offset_ms',0),15)
        q=abs(number(p['positionAmt']));price=number(mark['markPrice'])
        if price<=0:raise ValueError('Pozitif mark fiyatı gerekli.')
        rows=self.x.get('/fapi/v1/leverageBracket',{'symbol':params['symbol']})
        rows=[rows]if isinstance(rows,dict)else rows
        rows=[r for r in rows if r['symbol']==params['symbol']]
        if len(rows)!=1 or number(rows[0].get('notionalCoef',1))!=1:raise ValueError('İzole risk basamağı doğrulanamadı.')
        tier=next((r for r in rows[0]['brackets']if number(r['notionalFloor'])<=q*price<number(r['notionalCap'])),None)
        if tier is None:raise ValueError('Pozisyon bakım teminatı basamağı eksik.')
        direction='LONG'if number(p['positionAmt'])>0 else'SHORT'
        fee_reserve=q*max(price,number(p['entryPrice']))*number('.002')
        liq=liquidation_price(direction,q,p['entryPrice'],wallet-fee_reserve,tier['maintMarginRatio'],'0')
        algos=self.x.get('/fapi/v1/openAlgoOrders',{'symbol':params['symbol']})
        for a in algos:
            if (a.get('symbol')!=params['symbol']or a.get('positionSide')!=params['positionSide']
                    or a.get('algoStatus')!='NEW' or a.get('orderType',a.get('type'))!='STOP_MARKET'
                    or a.get('side')!=('SELL'if direction=='LONG'else'BUY')or a.get('workingType')!='MARK_PRICE'):
                continue
            close=str(a.get('closePosition')).lower()=='true'
            reducing=(params['positionSide']!='BOTH'or str(a.get('reduceOnly')).lower()=='true')
            if not close and not(reducing and number(a.get('quantity',0))>=q):continue
            stop=number(a.get('triggerPrice',0))
            if ((direction=='LONG'and liq*number('1.0025')<stop<price)
                    or(direction=='SHORT'and price<stop<liq*number('.9975'))):return
        raise ValueError('Teminat azaltması için likidasyondan önce tamponlu, etkin MARK_PRICE stop gerekli.')

    def prepare(self,symbol,position_side,action,amount,ttl=300):
        if type(ttl)is not int or not 1<=ttl<=600:raise ValueError('Komut süresi 1–600 saniye olmalı.')
        params=self._params(symbol,position_side,action,amount)
        begin=self.clock();position=self._position(params);self._check_change(params,position)
        created=self.clock();start=int(created*1000)+getattr(self.x,'offset_ms',0)-1000
        history=self._history(params,start)
        if not 0<=self.clock()-begin<=15:raise ValueError('Teminat hazırlık görünümü eskidi.')
        body={'command_id':uuid.uuid4().hex,'environment':'demo','owner':self.owner,'account_ref':self.account_ref,
              'params':params,'position':position,'baseline':sorted(digest(r)for r in history),
              'history_start_ms':start,'created_at':created,'expires_at':created+ttl}
        if self.managed_ref is not None:
            body['managed_ref']=self.managed_ref
        h=digest(body)
        with self.store.db:self.store.db.execute('INSERT INTO margin_commands VALUES (?,?,?,?,NULL,NULL)',(body['command_id'],canonical(body),h,'PREPARED'))
        return {'command_id':body['command_id'],'digest':h,'state':'PREPARED','symbol':symbol,
                'position_side':position_side,'action':action,'amount':params['amount'],'expires_at':body['expires_at']}

    def _row(self,cid):
        row=self.store.db.execute('SELECT * FROM margin_commands WHERE command_id=?',(cid,)).fetchone()
        if row is None:raise ValueError('Teminat komutu bulunamadı.')
        b=json.loads(row['body']);p=b['params']
        if (digest(b)!=row['digest']or b['owner']!=self.owner or b['account_ref']!=self.account_ref or b['environment']!='demo'
                or type(p.get('type'))is not int or p['type']not in(1,2)
                or p!=self._params(p['symbol'],p['positionSide'],'ADD'if p['type']==1 else'REMOVE',p['amount'])):
            raise ValueError('Teminat komutunun kapsamı/özeti uyuşmuyor.')
        self.managed_ref=b.get('managed_ref')
        self.session_id=self.managed_ref['session_id'] if self.managed_ref else None
        return dict(row),b

    def _state(self,cid,state,result=None,ack=None):
        with self.store.db:
            self.store.db.execute('UPDATE margin_commands SET state=?,result=?,ack=COALESCE(?,ack) WHERE command_id=?',
                                  (state,json.dumps(result),json.dumps(ack)if ack is not None else None,cid))
        self.store.event('isolated_margin_command',{'command_id':cid,'state':state,'result':result})
        return {'command_id':cid,'state':state,'result':result}

    def reconcile(self,cid):
        row,b=self._row(cid)
        if row['state']not in('SUBMITTING','ACKNOWLEDGED','UNKNOWN'):return {'command_id':cid,'state':row['state'],'duplicate':True}
        history=self._history(b['params'],b['history_start_ms'])
        baseline=Counter(b['baseline']);current=Counter(digest(r)for r in history)
        if baseline-current:raise ValueError('Teminat geçmişi eksik; uzlaştırma tamamlanamaz.')
        added=current-baseline
        candidates=[r for r in history if added[digest(r)]and r['positionSide']==b['params']['positionSide']and r['asset']=='USDT'
                    and r['deltaType']=='USER_ADJUST'and r['type']==b['params']['type']
                    and (abs(number(r['amount']))if r['type']==2 else number(r['amount']))==number(b['params']['amount'])]
        result={'matching_history_count':len(candidates),'post_acknowledged':bool(row['ack']),'automatic_resend':False}
        if row['ack']and sum(added.values())==1 and len(candidates)==1:
            p=self._position(b['params']);before=b['position']
            expected=number(before['isolatedWallet'])+number(b['params']['amount'])*(1 if b['params']['type']==1 else -1)
            if all(p[k]==before[k]for k in('positionAmt','entryPrice','symbol','positionSide'))and number(p['isolatedWallet'])==expected:
                return self._state(cid,'APPLIED',result)
        return self._state(cid,'ACKNOWLEDGED'if row['ack']else'UNKNOWN',result)

    def apply(self,cid,confirmed_digest):
        row,b=self._row(cid)
        if confirmed_digest!=row['digest']:raise ValueError('Somut teminat komutu onayı uyuşmuyor.')
        if row['state']in('SUBMITTING','UNKNOWN','ACKNOWLEDGED'):return self.reconcile(cid)
        if row['state']!='PREPARED':return {'command_id':cid,'state':row['state'],'duplicate':True}
        if self.clock()>=b['expires_at']:return self._state(cid,'EXPIRED')
        if self.store.unresolved_account_command():raise ValueError('Önce belirsiz hesap/teminat komutunu uzlaştırın.')
        start=self.clock();p=self._position(b['params'])
        if p!=b['position']:raise ValueError('Pozisyon/teminat hazırlıktan sonra değişti.')
        self._check_change(b['params'],p)
        if sorted(digest(r)for r in self._history(b['params'],b['history_start_ms']))!=b['baseline']:
            raise ValueError('Teminat geçmişi hazırlıktan sonra değişti.')
        if self.clock()>=b['expires_at']:return self._state(cid,'EXPIRED')
        if not 0<=self.clock()-start<=15:raise ValueError('Teminat gönderim öncesi görünümü eskidi.')
        with transaction(self.store)as db:
            if db.execute("UPDATE margin_commands SET state='SUBMITTING' WHERE command_id=? AND state='PREPARED'",(cid,)).rowcount!=1:
                raise ValueError('Teminat komutu başka süreçte kullanıldı.')
        try:reply=self.x.request('POST',PATH,b['params'])
        except ExchangeError as exc:
            return self._state(cid,'REJECTED'if exc.delivery_status in('NOT_SENT','REJECTED')else'UNKNOWN',{'code':exc.code})
        try:reply_amount=number(reply.get('amount',0))if isinstance(reply,dict)else number(0)
        except ValueError:reply_amount=number(0)
        if (not isinstance(reply,dict)or type(reply.get('code'))is not int or reply['code']!=200
                or type(reply.get('type'))is not int or reply['type']!=b['params']['type']
                or (abs(reply_amount)if b['params']['type']==2 else reply_amount)!=number(b['params']['amount'])):
            return self._state(cid,'UNKNOWN',{'reason':'Teminat POST yanıtı doğrulanamadı.','automatic_resend':False})
        self._state(cid,'ACKNOWLEDGED',ack={'code':200,'type':reply['type'],'amount':str(number(reply['amount']))})
        return self.reconcile(cid)
