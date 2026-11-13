"""One neutral hedge session, one budget and one durable stop barrier."""
import json
import time

from .batch_cancel import OwnedBatchCancel
from .exchange import ExchangeError
from .neutral_plan import compile_neutral,validate_neutral
from .order_rules import validate_order
from .plans import digest,timestamp
from .portfolio import Exposure
from .risk import number
from .v2_preflight import collect_flat_snapshot,collateral_usdt,fresh
from .v2_runner import V2Runner,NORMAL_TERMINAL,ALGO_TERMINAL
from .history import income_history
from datetime import datetime,timezone


class NeutralGridRunner(V2Runner):
    def _scope(self,s,entry=False):
        row=self.service.show(s['plan_ref']['plan_id'],s['plan_ref']['version'])
        if (s.get('engine')!='neutral-v2' or s.get('account_ref')!=self.account_ref or
                row['state'] not in ('EXECUTING','MANAGING','NEEDS_REVIEW') or
                row['session_id']!=s['id'] or row['action_id']!=s['entry_id'] or
                row['digest']!=s['plan_ref']['digest'] or digest(s['plan'])!=row['digest']):
            raise ValueError('Neutral plan/oturum/hesap sahipliği uyuşmuyor.')
        validate_neutral(s['plan']);c=s['compiled']
        core={k:c[k] for k in ('plan_digest','slots','notional_ceiling','exposures','budgets','anchor_price')}
        if c['plan_digest']!=row['digest'] or digest(core)!=c['compiled_digest']:
            raise ValueError('Neutral derleme özeti uyuşmuyor.')
        self.book.assert_binding(s['id'],self.service.owner,row['digest'],c['exposures'])
        for seq,r in enumerate(s['orders']):
            p=self._params(s,r['kind'],r['cell'],r['position_side'],r['proposal']['params']['quantity'],seq)
            if r['proposal']['path']!='/fapi/v1/order' or r['proposal']['params']!=p:
                raise ValueError('Neutral hücre emri onaylanan kapsamla uyuşmuyor.')
        generations={};seen=set();active_keys=set()
        for p in s['protections']:
            expected=self._protection_params(s,p['leg'],p['params']['type'],p['generation'])
            key=p['leg'],p['params']['type'];identity=(*key,p['generation'])
            if (p['path']!='/fapi/v1/algoOrder' or p['params']!=expected or identity in seen or
                    p['generation']!=generations.get(key,-1)+1 or type(p.get('retired_flat'))is not bool):
                raise ValueError('Neutral koruma parametresi onaylanan sınırla uyuşmuyor.')
            seen.add(identity);generations[key]=p['generation']
            if not p['retired_flat']:
                if key in active_keys:raise ValueError('Neutral koruma nesli önceki nesil emekli edilmeden değiştirilemez.')
                active_keys.add(key)
            if p['retired_flat']:
                saved=self.store.intent(p['params']['clientAlgoId'])
                if not saved or saved['state'] not in ('CANCELED','EXPIRED'):
                    raise ValueError('Neutral flat koruma emekliliği doğrulanmış terminal kayıt gerektirir.')
        if entry:
            first=self.store.intent(s['orders'][0]['proposal']['params']['newClientOrderId']) if s['orders'] else None
            first_sent=(first is not None and first['state'] in ('NEW','PARTIALLY_FILLED','FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH')
                        and first.get('response') and json.loads(first['response']).get('orderId') is not None)
            if (s['phase']!='ACTIVE' or self.store.halt_reason() or self.store.unresolved_account_command() or
                    time.time()>=timestamp(s['plan']['expires_at']) or
                    self.store.db.execute('SELECT 1 FROM control WHERE name=?',('entry_revoked:'+s['entry_id'],)).fetchone() or
                    not first_sent and time.time()>=row['approval_until']):
                raise ValueError('Neutral yeni giriş yetkisi durdurulmuş veya süresi dolmuş.')
        return row

    def _session(self,sid):
        rows=[s for s in self.store.sessions() if s['id']==sid and s.get('engine')=='neutral-v2']
        if len(rows)!=1:raise ValueError('Etkin neutral oturumu bulunamadı.')
        self._scope(rows[0]);return rows[0]

    def open(self,plan_id,version,execute=False):
        row=self.service.show(plan_id,version)
        if row['state']!='AUTHORIZED' or self.store.halt_reason() or self.store.unresolved_account_command():
            raise ValueError('Neutral başlangıcı için geçerli, engellenmemiş plan yetkisi gerekli.')
        snap=self._snapshot(row['plan']['symbol']);compiled=compile_neutral(row['plan'],snap,self.limits)
        if not execute or compiled['state']!='READY':
            if compiled['state']=='READY':compiled['portfolio_risk']=self._joint_risk(snap,[Exposure(**e) for e in compiled['exposures']])
            return compiled|{'executed':False}
        sid='neutral-'+digest([plan_id,version,row['digest']])[:24]
        self.book.reserve(sid,self.service.owner,row['digest'],[Exposure(**e) for e in compiled['exposures']],snap,self.limits)
        entry_id=self.service.claim(plan_id,version,sid)
        s=dict(id=sid,engine='neutral-v2',active=True,status='OPENING',phase='ACTIVE',entry_id=entry_id,
               symbol=row['plan']['symbol'],account_ref=self.account_ref,plan=row['plan'],compiled=compiled,
               plan_ref={'plan_id':plan_id,'version':version,'digest':row['digest']},orders=[],protections=[],
               started_ms=int(time.time()*1000)+getattr(self.x,'offset_ms',0),cursor=0)
        self._save(s)
        try:return self.manage(sid,execute=True)
        except Exception:
            self.service.outcome(plan_id,version,'NEEDS_REVIEW')
            self.store.halt('Neutral başlangıcı uzlaştırılmalı; aynı giriş tekrar gönderilmez.')
            raise

    def stop(self,sid,*,close_position=False,execute=False):
        s=self._session(sid)
        phase='STOPPING' if close_position else 'DRAINING'
        if not execute:return {'state':'NEUTRAL_STOP_PREVIEW','session_id':sid,'next_phase':phase,'executed':False}
        if s['phase']!='STOPPING':s.update(phase=phase,stop_reason='Kullanıcı neutral yeni girişlerini durdurdu.');self._save(s)
        report=self.manage(sid,True)
        for _ in range(4):
            if report['state']!='NEUTRAL_PROTECTION_RETIRED':break
            report=self.manage(sid,True)
        return report

    def _post(self,s,proposal,*,entry=False):
        try:return super()._post(s,proposal,entry=entry)
        except (TypeError,AttributeError,KeyError):
            cid=proposal['params'].get('clientAlgoId',proposal['params'].get('newClientOrderId'))
            if self.store.intent(cid):self.store.update(cid,'UNKNOWN',{'reason':'MALFORMED_RESPONSE'})
            self.store.halt('Neutral koruma yanıtı doğrulanamadı; yeniden POST yok.')
            raise ExchangeError('Neutral koruma yanıtı geçersiz; kayıtlı kimlikle uzlaştırılmalı.',delivery_status='UNKNOWN') from None

    def _stop(self,s,reason):
        s.update(phase='STOPPING',stop_reason=reason);self._save(s)

    def _params(self,s,kind,cell,side,quantity,seq):
        if kind not in ('OPEN','REDUCE','CLOSE') or side not in ('LONG','SHORT'):
            raise ValueError('Neutral emir rolü/tarafı geçersiz.')
        q=number(quantity)
        capacity=sum((number(c['quantity']) for c in s['compiled']['slots'] if c['position_side']==side),number(0))
        if not 0<q<=capacity:raise ValueError('Neutral emir miktarı taraf kapasitesini aşıyor.')
        opening=kind=='OPEN'
        p={'symbol':s['symbol'],'side':('BUY' if side=='LONG' else 'SELL') if opening else ('SELL' if side=='LONG' else 'BUY'),
           'positionSide':side,'type':'MARKET' if kind=='CLOSE' else 'LIMIT','quantity':str(q),
           'newClientOrderId':s['entry_id'] if seq==0 else self._id(s,['neutral',seq])}
        if kind=='CLOSE':
            if cell is not None:raise ValueError('Global neutral kapanışı hücreye bağlanamaz.')
        else:
            if type(cell)is not int or not 0<=cell<len(s['compiled']['slots']):raise ValueError('Neutral hücre kimliği geçersiz.')
            slot=s['compiled']['slots'][cell]
            if slot['position_side']!=side or q>number(slot['quantity']) or opening and q!=number(slot['quantity']):
                raise ValueError('Neutral hücre tarafı/miktarı uyuşmuyor.')
            p.update(price=slot['lower'] if opening==(side=='LONG') else slot['upper'],
                     timeInForce='GTC',selfTradePreventionMode='EXPIRE_BOTH')
        return p

    def _protection_params(self,s,side,kind,generation):
        if side not in ('LONG','SHORT') or kind not in ('STOP_MARKET','TAKE_PROFIT_MARKET') or type(generation)is not int or generation<0:
            raise ValueError('Neutral koruma rolü geçersiz.')
        lower=(side=='LONG')==(kind=='STOP_MARKET')
        return {'symbol':s['symbol'],'side':'SELL' if side=='LONG' else 'BUY','positionSide':side,
                'type':kind,'closePosition':'true','triggerPrice':str(number(s['plan']['stop']['lower' if lower else 'upper'])),
                'workingType':'MARK_PRICE','algoType':'CONDITIONAL',
                'clientAlgoId':self._id(s,['neutral-protection',side,kind,generation])}

    def _results(self,s):
        result={}
        for r in s['orders']:
            p=r['proposal']['params'];cid=p['newClientOrderId'];saved=self.store.intent(cid)
            if saved is None or saved['state']=='REJECTED':
                a=p|dict(clientOrderId=cid,origQty=p['quantity'],executedQty='0',status='REJECTED',updateTime=0)
            elif saved['state']=='FILLED' and saved.get('response'):a=json.loads(saved['response'])
            else:a=self.x.get('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':cid})
            if (saved and (saved['path']!='/fapi/v1/order' or json.loads(saved['params'])!=p) or
                    any(a.get(k)!=p[k] for k in ('symbol','side','positionSide','type')) or
                    a.get('clientOrderId')!=cid or number(a['origQty'])!=number(p['quantity']) or
                    p['type']=='LIMIT' and (number(a.get('price',0))!=number(p['price']) or
                        a.get('timeInForce')!='GTC' or a.get('selfTradePreventionMode')!='EXPIRE_BOTH')):
                raise ValueError('Neutral normal emir niyeti/borsa yanıtı uyuşmuyor.')
            if saved and saved.get('response'):
                old=json.loads(saved['response'])
                if old.get('orderId') is not None and str(old['orderId'])!=str(a.get('orderId')):
                    raise ValueError('Neutral istemci kimliği başka borsa emri için kullanılmış.')
            self.journal.register(cid,s['id'],s['symbol'],p['side'],p['quantity'])
            self.journal.observe(cid,digest(a),status='EXPIRED' if a['status']=='EXPIRED_IN_MATCH' else a['status'],
                                 cumulative_filled=a['executedQty'],observed_ms=int(a.get('updateTime',0)))
            if saved:self.store.update(cid,a['status'],a)
            result[cid]=a
        return result

    def _algos(self,s):
        result={}
        for p in s['protections']:
            cid=p['params']['clientAlgoId'];saved=self.store.intent(cid)
            if saved:
                a=(p['params']|{'algoStatus':'REJECTED'} if saved['state']=='REJECTED' else
                   self.x.get('/fapi/v1/algoOrder',{'clientAlgoId':cid}))
                result[cid]=a
                if saved['state']!='REJECTED':self.store.update(cid,a.get('algoStatus','UNKNOWN'),a)
        return result

    def _owned(self,s,results=None,algos=None):
        from .account_ownership import AccountOwnership
        proof=AccountOwnership(self,session_views={s['id']:s}).verify()
        return {side:proof['positions'].get((s['symbol'],side),number(0)) for side in ('LONG','SHORT')}

    def _inventory(self,s,results,index):
        inventory=number(0)
        for r in s['orders']:
            if r['cell']==index:
                inventory+=number(results[r['proposal']['params']['newClientOrderId']]['executedQty'])*(1 if r['kind']=='OPEN' else -1)
        if not 0<=inventory<=number(s['compiled']['slots'][index]['quantity']):
            raise ValueError('Neutral hücre envanteri sınırı aşıldı.')
        return inventory

    def _cancelled_by_us(self,path,params):
        cid=digest(json.dumps([path,params],sort_keys=True))
        return self.store.db.execute('SELECT 1 FROM v2_cancellations WHERE command_id=?',(cid,)).fetchone() is not None

    def _ensure_protections(self,s,amounts,algos,mark,info,execute):
        for p in s['protections']:
            a=algos.get(p['params']['clientAlgoId'])
            if p.get('retired_flat') and a is not None and (a.get('algoStatus') not in ('CANCELED','EXPIRED') or
                    a.get('actualOrderId') not in (None,'','0',0)):
                self._stop(s,'Emekli neutral koruma beklenmeyen duruma geçti.');return None
        for side in sorted(('LONG','SHORT'),key=lambda side:not bool(amounts[side])):
            for p in [p for p in s['protections'] if p['leg']==side and not p.get('retired_flat')]:
                a=algos.get(p['params']['clientAlgoId'])
                if a is not None and (a.get('algoStatus') in ('TRIGGERING','TRIGGERED','FINISHED','REJECTED') or
                        a.get('actualOrderId') not in (None,'','0',0)):
                    self._stop(s,'Neutral koşullu koruma tetiklendi/tüketildi.');return None
                if not amounts[side] and a is not None:
                    cid=p['params']['clientAlgoId'];status=a.get('algoStatus')
                    if status=='NEW':
                        if not execute:return {'state':'NEUTRAL_PROTECTION_RETIRE_REQUIRED','session_id':s['id'],'executed':False}
                        self._cancel('/fapi/v1/algoOrder',{'clientAlgoId':cid})
                        retired=self.x.get('/fapi/v1/algoOrder',{'clientAlgoId':cid})
                        if retired.get('algoStatus') not in ('CANCELED','EXPIRED') or retired.get('actualOrderId') not in (None,'','0',0):
                            raise ValueError('Flat tarafın eski neutral koruması terminal değil.')
                        self.store.update(cid,retired['algoStatus'],retired)
                        p['retired_flat']=True;self._save(s)
                        return {'state':'NEUTRAL_PROTECTION_RETIRED','session_id':s['id'],'executed':True}
                    if status=='EXPIRED' or status=='CANCELED' and self._cancelled_by_us('/fapi/v1/algoOrder',{'clientAlgoId':cid}):
                        p['retired_flat']=True;self._save(s)
                    else:self._stop(s,'Neutral koruma kullanıcı/borsa tarafından değiştirildi.');return None
            if not amounts[side]:continue
            for kind in ('STOP_MARKET','TAKE_PROFIT_MARKET'):
                previous=[p for p in s['protections'] if p['leg']==side and p['params']['type']==kind]
                active=[p for p in previous if not p.get('retired_flat')]
                if len(active)>1:raise ValueError('Neutral tarafta birden fazla etkin koruma nesli var.')
                if not active:
                    generation=max((p['generation'] for p in previous),default=-1)+1
                    params=self._protection_params(s,side,kind,generation)
                    p=validate_order(params,info,'hedge','CLOSE',mark['markPrice'],int(time.time()*1000))
                    p.update(leg=side,generation=generation,retired_flat=False);s['protections'].append(p);self._save(s)
                else:p=active[0]
                cid=p['params']['clientAlgoId'];a=algos.get(cid)
                if a is None:
                    if not execute:return {'state':'NEUTRAL_PROTECTION_REQUIRED','session_id':s['id'],'executed':False}
                    try:self._post(s,p)
                    except ExchangeError as exc:
                        if exc.delivery_status not in ('NOT_SENT','REJECTED'):raise
                        self._stop(s,'Neutral koruma kesin reddedildi; envanter kapatılmalı.');return None
                    a=self.x.get('/fapi/v1/algoOrder',{'clientAlgoId':cid});algos[cid]=a
                expected=p['params']
                if (a.get('algoStatus')!='NEW' or any(a.get(k)!=expected[k] for k in ('clientAlgoId','symbol','side','positionSide','workingType')) or
                        a.get('orderType',a.get('type'))!=kind or str(a.get('closePosition')).lower()!='true' or
                        number(a.get('triggerPrice',0))!=number(expected['triggerPrice'])):
                    self._stop(s,'Neutral etkin koruma doğrulanamadı.');return None
        return None

    def _risk(self,s):
        start=time.time();self.x.sync_time();account=self.x.get('/fapi/v3/account');config=self.x.get('/fapi/v1/accountConfig')
        if config.get('canTrade')is not True:raise ValueError('Hesap işlem uygunluğu gerekli.')
        index=self.x.get('/fapi/v1/assetIndex',{'symbol':'USDTUSD'}) if config['multiAssetsMargin'] else None
        if index is not None:fresh(index,'USDTUSD',int(time.time()*1000)+getattr(self.x,'offset_ms',0),self.limits.max_age_seconds)
        end=int(time.time()*1000)+getattr(self.x,'offset_ms',0)
        midnight=datetime.fromtimestamp(end/1000,timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
        rows=income_history(self.x,int(midnight.timestamp()*1000),end)
        relevant=[r for r in rows if r['incomeType'] in ('REALIZED_PNL','COMMISSION','FUNDING_FEE')]
        if any(r['asset']!='USDT' for r in relevant):raise ValueError('Neutral günlük varlık dönüşümü gerekli.')
        pnl=sum((number(r['income']) for r in relevant),number(0))
        assets=[a for a in account['assets'] if a['asset']=='USDT']
        if len(assets)!=1 or 'unrealizedProfit' not in assets[0]:raise ValueError('Neutral gerçekleşmemiş sonuç gerekli.')
        pnl+=min(number(assets[0]['unrealizedProfit']),number(0))
        result=self.book.evaluate({'collateral':str(collateral_usdt(account,config,index)),
            'daily_loss':str(max(-pnl,number(0))),'observed_at':start},self.limits,exchange=self.x)
        own_loss=sum((number(e['quantity'])*(abs(number(e['entry'])-number(e['stop']))+
                       number(e['notional_price'] or e['entry'])*number('.002')) for e in s['compiled']['exposures']),number(0))
        if own_loss>self.limits.max_trade_loss:
            raise ValueError('Neutral iki tarafının toplam stop/masraf riski güncel işlem sınırını aşıyor.')
        return result

    def _submit(self,s,kind,slot,side,quantity,mark,info,results):
        import copy
        started=time.time()
        base=copy.deepcopy(s);seq=len(s['orders']);params=self._params(s,kind,slot,side,quantity,seq)
        p=validate_order(params,info,'hedge','OPEN' if kind=='OPEN' else 'REDUCE',mark['markPrice'],int(time.time()*1000))
        record={'kind':kind,'cell':slot,'position_side':side,'proposal':p}
        amounts=self._owned(s)
        if kind!='OPEN' and number(quantity)>abs(amounts[side]):raise ValueError('Neutral azaltma sahip olunan taraftan büyük.')
        if kind=='OPEN':self._scope(s,entry=True);self._risk(s)
        s['orders'].append(record);self._save(s)
        cid=params['newClientOrderId'];self.journal.register(cid,s['id'],s['symbol'],params['side'],params['quantity'])
        if not self.store.reserve(cid,'/fapi/v1/order',params):raise ValueError('Neutral emir kimliği daha önce ayrılmış; yeniden POST yok.')
        try:
            if kind=='OPEN':self._scope(s,entry=True);self._risk(s)
            current=self._owned(base)
            if current!=amounts:raise ValueError('Neutral gönderim öncesi envanter değişti.')
            refreshed=self._results(base)
            if slot is not None:
                inventory=self._inventory(base,refreshed,slot)
                if kind=='OPEN' and inventory!=0 or kind=='REDUCE' and inventory!=number(quantity):
                    raise ValueError('Neutral gönderim öncesi hücre envanteri değişti.')
                if self._conflicts(params,refreshed):raise ValueError('Neutral son kontrolde kendi emriyle eşleşme riski var.')
            if kind!='CLOSE':
                latest_algos=self._algos(base)
                if any(not p.get('retired_flat') and latest_algos.get(p['params']['clientAlgoId'],{}).get('algoStatus')!='NEW'
                       for p in base['protections']):
                    self._stop(s,'Neutral son gönderim kontrolünde koruma tüketildi.')
                    raise ValueError('Neutral koruma değişti; yeni normal emir gönderilmedi.')
            latest=self.x.get('/fapi/v1/premiumIndex',{'symbol':s['symbol']})
            fresh(latest,s['symbol'],int(time.time()*1000)+getattr(self.x,'offset_ms',0),self.limits.max_age_seconds)
            price=number(latest['markPrice'])
            if kind=='OPEN' and (not number(s['plan']['grid']['lower'])<price<number(s['plan']['grid']['upper']) or
                (side=='LONG' and number(params['price'])>=price) or (side=='SHORT' and number(params['price'])<=price)):
                raise ValueError('Neutral açılış fiyatı güncel banda/pasif tarafa uymuyor.')
            self.book.mark_submitted(s['id'])
            if kind=='OPEN':self._scope(s,entry=True)
            if not 0<=time.time()-started<=self.limits.max_age_seconds:
                raise ValueError('Neutral gönderim öncesi görünümü eskidi.')
        except (ValueError,ExchangeError):
            self.store.update(cid,'REJECTED',{'delivery_status':'NOT_SENT'});raise
        try:reply=self.x.request('POST','/fapi/v1/order',params)
        except ExchangeError as exc:
            self.store.update(cid,'REJECTED' if exc.delivery_status in ('NOT_SENT','REJECTED') else 'UNKNOWN',
                              {'delivery_status':exc.delivery_status,'code':exc.code})
            self.store.halt('Neutral emir yanıtı uzlaştırılmalı; yeniden POST yok.');raise
        if not isinstance(reply,dict) or reply.get('status') not in NORMAL_TERMINAL|{'NEW','PARTIALLY_FILLED'}:
            self.store.update(cid,'UNKNOWN',{'reason':'MALFORMED_RESPONSE'})
            self.store.halt('Neutral POST yanıtı doğrulanamadı; yeniden POST yok.')
            raise ExchangeError('Neutral emir yanıtı geçersiz; kayıtlı kimlikle uzlaştırılmalı.',delivery_status='UNKNOWN')
        self.store.update(cid,reply.get('status','UNKNOWN'),reply)
        return record

    def _conflicts(self,params,results):
        conflicts=[]
        if params['type']!='LIMIT':return conflicts
        for cid,a in results.items():
            if a['status'] in NORMAL_TERMINAL or a['side']==params['side']:continue
            if (params['side']=='BUY' and number(params['price'])>=number(a['price']) or
                    params['side']=='SELL' and number(params['price'])<=number(a['price'])):conflicts.append(cid)
        return conflicts

    def _cleanup(self,s,results,algos,mark,info,execute):
        pending=[cid for cid,a in results.items() if a['status'] not in NORMAL_TERMINAL]
        if pending:
            if not execute:return {'state':'NEUTRAL_CANCEL_REQUIRED','session_id':s['id'],'executed':False}
            for offset in range(0,len(pending),10):
                chunk=pending[offset:offset+10]
                if len(chunk)==1:self._cancel('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':chunk[0]})
                else:
                    report=OwnedBatchCancel(self.x,self.store).cancel(s['symbol'],chunk,owned_client_ids=set(results))
                    if report['unresolved']:raise ValueError('Neutral toplu iptali doğrulanamadı.')
            results=self._results(s)
            if any(a['status'] not in NORMAL_TERMINAL for a in results.values()):raise ValueError('Neutral iptal bariyeri terminal değil.')
        if s['phase']=='DRAINING':return None
        children={str(a['actualOrderId']) for a in algos.values() if a.get('actualOrderId') not in (None,'','0',0)}
        for a in self.x.get('/fapi/v1/openOrders'):
            if a['symbol']!=s['symbol']:continue
            if str(a['orderId']) not in children:raise ValueError('Neutral temizliğinde yabancı alt emir var.')
            if not execute:return {'state':'NEUTRAL_CHILD_CANCEL_REQUIRED','session_id':s['id'],'executed':False}
            query={'symbol':s['symbol'],'origClientOrderId':a['clientOrderId']};self._cancel('/fapi/v1/order',query)
            if self.x.get('/fapi/v1/order',query)['status'] not in NORMAL_TERMINAL:raise ValueError('Neutral alt emir terminal değil.')
        if any(a.get('algoStatus') in ('TRIGGERING','TRIGGERED') and a.get('actualOrderId') in (None,'','0',0) for a in algos.values()):
            return {'state':'NEUTRAL_NATIVE_PENDING','session_id':s['id'],'executed':False}
        amounts=self._owned(s)
        for side in ('LONG','SHORT'):
            if amounts[side]:
                if not execute:return {'state':'NEUTRAL_CLOSE_REQUIRED','session_id':s['id'],'position_side':side,'executed':False}
                self._submit(s,'CLOSE',None,side,str(abs(amounts[side])),mark,info,results)
                return {'state':'NEUTRAL_CLOSE_SUBMITTED','session_id':s['id'],'position_side':side,'executed':True}
        for cid,a in algos.items():
            if a.get('algoStatus')=='NEW':
                if not execute:return {'state':'NEUTRAL_CLEANUP_REQUIRED','session_id':s['id'],'executed':False}
                self._cancel('/fapi/v1/algoOrder',{'clientAlgoId':cid})
                if self.x.get('/fapi/v1/algoOrder',{'clientAlgoId':cid}).get('algoStatus') not in ALGO_TERMINAL:
                    raise ValueError('Neutral koruma temizliği terminal değil.')
            elif a.get('algoStatus') not in ALGO_TERMINAL:
                return {'state':'NEUTRAL_NATIVE_PENDING','session_id':s['id'],'executed':False}
        if any(self._owned(s).values()) or any(o['symbol']==s['symbol'] for o in self.x.get('/fapi/v1/openOrders')+self.x.get('/fapi/v1/openAlgoOrders')):
            raise ValueError('Neutral temizliği henüz flat değil.')
        s.update(active=False,status='CLOSED',phase='CLOSED');self.book.close_session(s,flat_verified=True,orders_terminal=True)
        self.service.show(s['plan_ref']['plan_id'],s['plan_ref']['version'])
        return {'state':'CLOSED','session_id':s['id'],'executed':execute,'reason':s.get('stop_reason')}

    def _manage(self,sid,execute=False):
        s=self._session(sid);self.x.sync_time();results=self._results(s);algos=self._algos(s)
        amounts=self._owned(s);mark=self.x.get('/fapi/v1/premiumIndex',{'symbol':s['symbol']})
        fresh(mark,s['symbol'],int(time.time()*1000)+getattr(self.x,'offset_ms',0),self.limits.max_age_seconds)
        info=next(i for i in self.x.get('/fapi/v1/exchangeInfo')['symbols'] if i['symbol']==s['symbol']);price=number(mark['markPrice'])
        if self.store.halt_reason() or price<=number(s['plan']['stop']['lower']) or price>=number(s['plan']['stop']['upper']):
            self._stop(s,'Neutral global stop/hesap durdurması.')
        if s['phase']=='ACTIVE' and (time.time()>=timestamp(s['plan']['expires_at']) or
                self.store.db.execute('SELECT 1 FROM control WHERE name=?',('entry_revoked:'+s['entry_id'],)).fetchone()):
            s.update(phase='DRAINING',stop_reason='Neutral yeni giriş yetkisi sona erdi.');self._save(s)
        for cid,a in results.items():
            if a['status']=='REJECTED' or a['status'] in ('CANCELED','EXPIRED','EXPIRED_IN_MATCH') and not self._cancelled_by_us('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':cid}):
                self._stop(s,'Neutral normal emir reddedildi veya kullanıcı/STP tarafından sonlandırıldı.')
        if s['phase']=='STOPPING':return self._cleanup(s,results,algos,mark,info,execute)
        if s['phase']=='DRAINING':
            opening={r['proposal']['params']['newClientOrderId'] for r in s['orders'] if r['kind']=='OPEN'}
            pending=[cid for cid,a in results.items() if cid in opening and a['status'] not in NORMAL_TERMINAL]
            if pending:
                if not execute:return {'state':'NEUTRAL_DRAIN_REQUIRED','session_id':sid,'executed':False}
                for cid in pending:self._cancel('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':cid})
                results=self._results(s)
                if any(results[c]['status'] not in NORMAL_TERMINAL for c in pending):raise ValueError('Neutral açıcı iptali terminal değil.')
                amounts=self._owned(s)
        protection=self._ensure_protections(s,amounts,algos,mark,info,execute)
        if s['phase']=='STOPPING':return self._cleanup(s,results,self._algos(s),mark,info,execute)
        if protection is not None:return protection
        if s['phase']=='DRAINING' and not any(amounts.values()):
            self._stop(s,'Neutral boşaltılmış plan tamamlandı.');return self._cleanup(s,results,self._algos(s),mark,info,execute)
        for cid,a in results.items():
            if a['status'] not in NORMAL_TERMINAL and number(a['executedQty']):
                if not execute:return {'state':'NEUTRAL_PARTIAL_CANCEL_REQUIRED','session_id':sid,'executed':False}
                self._cancel('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':cid})
                if self.x.get('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':cid})['status'] not in NORMAL_TERMINAL:
                    raise ValueError('Neutral kısmi emir kalanı terminal değil.')
                return {'state':'NEUTRAL_PARTIAL_CANCELED','session_id':sid,'executed':True}
        slots=s['compiled']['slots'];cursor=s.get('cursor',0);actions=[]
        for slot in slots[cursor:]+slots[:cursor]:
            if any(r['cell']==slot['index'] and results[r['proposal']['params']['newClientOrderId']]['status'] not in NORMAL_TERMINAL for r in s['orders']):continue
            inventory=self._inventory(s,results,slot['index']);kind='REDUCE' if inventory else 'OPEN'
            if kind=='OPEN' and (s['phase']!='ACTIVE' or not number(s['plan']['grid']['lower'])<price<number(s['plan']['grid']['upper'])):continue
            q=str(inventory) if inventory else slot['quantity'];side=slot['position_side']
            params=self._params(s,kind,slot['index'],side,q,len(s['orders']))
            if kind=='OPEN' and ((side=='LONG' and number(params['price'])>=price) or (side=='SHORT' and number(params['price'])<=price)):continue
            conflicts=self._conflicts(params,results)
            if conflicts:
                opening={r['proposal']['params']['newClientOrderId'] for r in s['orders'] if r['kind']=='OPEN'}
                if kind!='REDUCE' or any(cid not in opening for cid in conflicts):continue
                actions.append(('CANCEL_CONFLICT',slot,side,q,conflicts))
            else:actions.append((kind,slot,side,q,[]))
        if actions:
            kind,slot,side,q,conflicts=next((a for a in actions if a[0] in ('REDUCE','CANCEL_CONFLICT')),actions[0])
            if kind=='CANCEL_CONFLICT':
                if not execute:return {'state':'NEUTRAL_CONFLICT_CANCEL_REQUIRED','session_id':sid,'executed':False}
                for cid in conflicts:
                    query={'symbol':s['symbol'],'origClientOrderId':cid};self._cancel('/fapi/v1/order',query)
                    if self.x.get('/fapi/v1/order',query)['status'] not in NORMAL_TERMINAL:
                        raise ValueError('Neutral kendi açıcı emriyle eşleşme iptal bariyeri terminal değil.')
                return {'state':'NEUTRAL_CONFLICT_CANCELED','session_id':sid,'executed':True}
            if not execute:return {'state':'NEUTRAL_ACTION_REQUIRED','kind':kind,'position_side':side,'cell':slot['index'],'session_id':sid,'executed':False}
            try:self._submit(s,kind,slot['index'],side,q,mark,info,results)
            except ValueError:
                self._stop(s,'Neutral gönderim öncesi yetki/risk/envanter denetimi yeni emri durdurdu.')
                return self._cleanup(s,self._results(s),self._algos(s),mark,info,True)
            except ExchangeError as exc:
                if exc.delivery_status not in ('NOT_SENT','REJECTED'):raise
                self._stop(s,'Neutral normal emir kesin reddedildi; kalan envanter kapatılmalı.')
                return self._cleanup(s,self._results(s),self._algos(s),mark,info,True)
            s['cursor']=(slot['index']+1)%len(slots)
            s['status']='PROTECTED' if any(amounts.values()) else 'RUNNING';self._save(s)
            self.service.outcome(s['plan_ref']['plan_id'],s['plan_ref']['version'],'MANAGING')
            current=self._results(s);current_amounts=self._owned(s);current_algos=self._algos(s)
            if any(a['status']=='REJECTED' or a['status'] in ('CANCELED','EXPIRED','EXPIRED_IN_MATCH') and
                   not self._cancelled_by_us('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':cid}) for cid,a in current.items()):
                self._stop(s,'Neutral gönderilen emir reddedildi veya STP/kullanıcı tarafından sonlandı.')
                return self._cleanup(s,current,current_algos,mark,info,True)
            protection=self._ensure_protections(s,current_amounts,current_algos,mark,info,True)
            if s['phase']=='STOPPING':return self._cleanup(s,current,self._algos(s),mark,info,True)
            if protection is not None:return protection
            return {'state':'NEUTRAL_ORDER_SUBMITTED','kind':kind,'position_side':side,'cell':slot['index'],'session_id':sid,'executed':True}
        s['status']='PROTECTED' if any(amounts.values()) else 'RUNNING';self._save(s)
        return {'state':'NEUTRAL_DRAINING' if s['phase']=='DRAINING' else 'NEUTRAL_RUNNING',
                'session_id':sid,'positions':{k:str(v) for k,v in amounts.items()},'executed':False}
