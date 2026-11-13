"""Bounded demo grid runner with owned inventory and a durable stop barrier.

One new cell order per management turn limits bursts. No order is resent after an
uncertain delivery. Exchange stops do not cancel normal grid orders by themselves;
the monitor must remain running to perform stop cleanup and handle late fills.
"""
from .history import account_trades, income_history
from .brackets import select_bracket
import json
import time
from datetime import datetime, timezone

from .exchange import ExchangeError
from .batch_cancel import OwnedBatchCancel
from .batch_create import NativeBatchCreate
from .grid_plan import compile_grid
from .order_rules import validate_order
from .order_revisions import effective_params
from .plans import digest, timestamp
from .portfolio import Exposure, evaluate_portfolio
from .reservations import ReservationBook
from .risk import number
from .v2_preflight import collect_flat_snapshot, collateral_usdt, fresh
from .v2_runner import V2Runner, NORMAL_TERMINAL, ALGO_ACTIVE, ALGO_TERMINAL


class GridRunner(V2Runner):
    def __init__(self, service, exchange, limits):
        super().__init__(service, exchange, limits)
        self.book = ReservationBook(self.store, self.account_ref)

    def _collect_snapshot(self,symbol,**options):
        return collect_flat_snapshot(self.x,symbol,self.limits,**options)

    def _scope(self, s, entry=False):
        row = self.service.show(s['plan_ref']['plan_id'], s['plan_ref']['version'])
        if (s.get('engine') != 'grid-v2' or row['state'] not in ('EXECUTING','MANAGING','NEEDS_REVIEW')
                or row['digest'] != s['plan_ref']['digest'] or digest(s['plan']) != row['digest']
                or row['session_id'] != s['id'] or row['action_id'] != s['entry_id']
                or s['account_ref'] != self.account_ref):
            raise ValueError('Grid oturumu/planı/hesabı uyuşmuyor.')
        c=s['compiled'];core={k:c[k] for k in ('plan_digest','slots','seed_quantity','notional_ceiling','exposures')}
        if c['plan_digest'] != row['digest'] or digest(core) != c['compiled_digest'] or self.book.state(s['id']) == 'RELEASED':
            raise ValueError('Grid rezervasyon veya derleme özeti uyuşmuyor.')
        self.book.assert_binding(s['id'],self.service.owner,row['digest'],c['exposures'])
        from .grid_native_stop import validate_transitions
        validate_transitions(self,s)
        if s['protections']:
            if len(s['protections'])!=2:raise ValueError('Grid koruma paketi eksik.')
            for i,(kind,price)in enumerate((('STOP_MARKET',s['plan']['stop']),('TAKE_PROFIT_MARKET',s['plan']['targets'][0]['price']))):
                expected={'symbol':s['symbol'],'side':'SELL'if s['plan']['direction']=='LONG'else'BUY',
                          'positionSide':'BOTH'if s['plan']['position_mode']=='one-way'else s['plan']['direction'],
                          'type':kind,'closePosition':'true','triggerPrice':str(number(price)),'workingType':'MARK_PRICE',
                          'algoType':'CONDITIONAL','clientAlgoId':self._id(s,['grid-protection',i])}
                if s['protections'][i]['path']!='/fapi/v1/algoOrder'or s['protections'][i]['params']!=expected:
                    raise ValueError('Grid koruma seviyeleri onaylanan planla uyuşmuyor.')
        return row

    def _session(self, sid):
        rows=[s for s in self.store.sessions() if s['id']==sid and s.get('engine')=='grid-v2']
        if len(rows)!=1:raise ValueError('Etkin grid oturumu bulunamadı.')
        self._scope(rows[0]);return rows[0]

    def _stop(self, s, reason):
        s.update(phase='STOPPING',stop_reason=reason)
        self._save(s)

    def _grid_stop(self,s):
        """Bot-managed session stop; the exchange keeps the original fallback."""
        original=number(s['plan']['stop'])
        current=number(s.get('grid_trailing_stop',original))
        sign=1 if s['plan']['direction']=='LONG' else -1
        if current<=0 or sign*(current-original)<0:
            raise ValueError('Grid takip stopu başlangıç korumasını gevşetemez.')
        if s['plan']['management'].get('trailing') is None and current!=original:
            raise ValueError('Grid takip stopu için onaylı politika gerekli.')
        return current

    def _grid_algos(self,s):
        return s['protections']+[t['proposal'] for t in s.get('stop_transitions',[])]

    def _bad_grid_algos(self,s,algos):
        from .grid_native_stop import retired
        return any(a.get('algoStatus') not in ALGO_ACTIVE and not retired(self,s,cid,a)
                   for cid,a in algos.items())

    def _advance_grid_trailing(self,s,amount,mark,info):
        policy=s['plan']['management'].get('trailing')
        if policy is None or not amount or s['phase']=='STOPPING':return
        from .trailing import advance_trailing
        tick=next(f['tickSize'] for f in info['filters'] if f['filterType']=='PRICE_FILTER')
        state,trigger=advance_trailing(policy,s['plan']['direction'],mark['markPrice'],tick,
                                       self._grid_stop(s),s.get('grid_trailing_state'))
        s['grid_trailing_state']=state
        if trigger is not None:s['grid_trailing_stop']=str(trigger)
        self._save(s)

    def stop(self,sid,*,close_position=False,execute=False):
        s=self._session(sid)
        phase='STOPPING'if close_position else'DRAINING'
        if not execute:return {'state':'GRID_STOP_PREVIEW','next_phase':phase,'session_id':sid,'executed':False}
        if s['phase']!='STOPPING':s.update(phase=phase,stop_reason='Kullanıcı grid yeni girişlerini durdurdu.');self._save(s)
        return self.manage(sid,execute=True)

    def open(self, plan_id, version, execute=False):
        row=self.service.show(plan_id,version)
        if row['state']!='AUTHORIZED':raise ValueError('Grid başlangıcı için geçerli plan yetkisi gerekli.')
        if self.store.halt_reason() or self.store.unresolved_account_command():
            raise ValueError('Grid için aktif oturum/durdurma/belirsiz ayar çözülmeli.')
        snap=self._snapshot(row['plan']['symbol'])
        compiled=compile_grid(row['plan'],snap,self.limits)
        if not execute or compiled['state']!='READY':
            if compiled['state']=='READY':compiled['portfolio_risk']=self._joint_risk(snap,[Exposure(**e) for e in compiled['exposures']])
            return compiled|{'executed':False}
        sid='grid-'+digest([plan_id,version,row['digest']])[:27]
        self.book.reserve(sid,self.service.owner,row['digest'],[Exposure(**e) for e in compiled['exposures']],snap,self.limits)
        try:entry_id=self.service.claim(plan_id,version,sid)
        except Exception:
            # A raced/uncertain claim must not release another worker's live envelope.
            raise
        s={'id':sid,'engine':'grid-v2','active':True,'status':'OPENING','phase':'ACTIVE',
           'entry_id':entry_id,'symbol':row['plan']['symbol'],'account_ref':self.account_ref,
           'plan':row['plan'],'plan_ref':{'plan_id':plan_id,'version':version,'digest':row['digest']},
           'compiled':compiled,'orders':[],'protections':[],'started_ms':int(time.time()*1000)+getattr(self.x,'offset_ms',0)}
        self._save(s)
        try:
            if number(compiled['seed_quantity']):
                self._new_order(s,'SEED',None,compiled['seed_quantity'],snap['mark'],snap['symbol_info'])
            return self.manage(sid,execute=True)
        except Exception:
            self.service.outcome(plan_id,version,'NEEDS_REVIEW')
            self.store.halt('Grid başlangıcı uzlaştırılmalı; aynı giriş tekrar gönderilmez.')
            raise

    def _new_order(self,s,kind,cell,quantity,mark,info):
        sign=1 if s['plan']['direction']=='LONG' else -1
        opening=kind in ('OPEN','SEED')
        first_send=not s['orders']
        if opening:
            row=self._scope(s)
            if (s['phase']!='ACTIVE' or self.store.halt_reason() or self.store.unresolved_account_command()
                    or time.time()>=timestamp(s['plan']['expires_at'])
                    or self.store.db.execute('SELECT 1 FROM control WHERE name=?',('entry_revoked:'+s['entry_id'],)).fetchone()):
                raise ValueError('Grid yeni giriş yetkisi durdurulmuş.')
            if not s['orders'] and time.time()>=row['approval_until']:
                raise ValueError('Grid ilk giriş onayı sona erdi.')
            if kind=='SEED':
                before_send=self._snapshot(s['symbol'],s['id'])
                check=compile_grid(s['plan'],before_send,self.limits)
                if check.get('compiled_digest')!=s['compiled']['compiled_digest']:
                    raise ValueError('Grid başlangıç hesabı/fiyatı değişti; tekrar giriş gönderilmedi.')
                self._joint_risk(before_send)
            latest=self.x.get('/fapi/v1/premiumIndex',{'symbol':s['symbol']})
            fresh(latest,s['symbol'],int(time.time()*1000)+getattr(self.x,'offset_ms',0),self.limits.max_age_seconds)
            if sign*(number(latest['markPrice'])-self._grid_stop(s))<=0 or sign*(number(s['plan']['targets'][0]['price'])-number(latest['markPrice']))<=0:
                self._stop(s,'Gönderim öncesi grid stop sınırı aşıldı.')
                raise ValueError('Grid gönderiminden önce stop/son hedef aşıldı.')
            if s['orders']:
                algos=self._algos(s)
                if self._bad_grid_algos(s,algos):
                    self._stop(s,'Borsa koruması tüketildi; grid yeniden giriş üretmeyecek.')
                    raise ValueError('Grid koruması tüketilmiş veya iptal edilmiş.')
                current=self._results(s);self._owned_grid(s,current,algos)
                if cell is not None:
                    if self._inventory(s,current,cell)!=0 or any(r['cell']==cell and current[r['proposal']['params']['newClientOrderId']]['status']not in NORMAL_TERMINAL for r in s['orders']):
                        raise ValueError('Grid hücresi yeni alış için boş değil.')
        p=self._proposal(s,kind,cell,quantity,mark,info,len(s['orders']));params=p['params']
        record={'proposal':p,'kind':kind,'cell':cell}
        s['orders'].append(record);self._save(s)
        self.journal.register(params['newClientOrderId'],s['id'],s['symbol'],params['side'],params['quantity'])
        if opening:
            row=self._scope(s)
            if (time.time()>=timestamp(s['plan']['expires_at']) or (first_send and time.time()>=row['approval_until'])
                    or self.store.halt_reason() or self.store.unresolved_account_command()
                    or self.store.db.execute('SELECT 1 FROM control WHERE name=?',('entry_revoked:'+s['entry_id'],)).fetchone()):
                raise ValueError('Gönderimden önce grid giriş yetkisi değişti.')
        self.book.mark_submitted(s['id'])
        self._post(s,p)
        return record

    def _proposal(self,s,kind,cell,quantity,mark,info,seq):
        sign=1 if s['plan']['direction']=='LONG'else -1;opening=kind in('OPEN','SEED')
        params={'symbol':s['symbol'],'side':('BUY' if sign==1 else 'SELL') if opening else ('SELL' if sign==1 else 'BUY'),
                'positionSide':'BOTH' if s['plan']['position_mode']=='one-way' else s['plan']['direction'],
                'type':'MARKET' if kind in ('SEED','CLOSE') else 'LIMIT','quantity':str(number(quantity)),
                'newClientOrderId':s['entry_id'] if kind=='SEED' else self._id(s,['grid',seq])}
        if kind in ('OPEN','REDUCE'):
            slot=s['compiled']['slots'][cell]
            price=slot['lower'] if (opening==(sign==1)) else slot['upper']
            params.update(price=price,timeInForce='GTC')
        if not opening and s['plan']['position_mode']=='one-way':params['reduceOnly']='true'
        return validate_order(params,info,s['plan']['position_mode'],'OPEN' if opening else 'REDUCE',mark['markPrice'],int(time.time()*1000))

    def _ready_actions(self,s,results,price):
        slots=s['compiled']['slots'];cursor=s.get('cursor',0);ready=[]
        for slot in slots[cursor:]+slots[:cursor]:
            active=[r for r in s['orders']if r['cell']==slot['index']and results[r['proposal']['params']['newClientOrderId']]['status']not in NORMAL_TERMINAL]
            if len(active)>1:raise ValueError('Hücrede birden fazla aktif grid emri var.')
            if active:
                if number(results[active[0]['proposal']['params']['newClientOrderId']]['executedQty']):return []
                continue
            inventory=self._inventory(s,results,slot['index']);kind='REDUCE'if inventory else'OPEN'
            if slot['index']in s.get('manual_cells',[]):continue
            if kind=='OPEN'and(s['phase']!='ACTIVE'or not number(s['plan']['grid']['lower'])<=price<number(s['plan']['grid']['upper'])):continue
            ready.append((kind,slot['index'],str(inventory)if inventory else slot['quantity']))
            if len(ready)==5:break
        return ready

    def _new_batch(self,s,actions,mark,info,results,algos):
        import copy
        base=copy.deepcopy(s);start=time.time();opening=any(k=='OPEN'for k,_,_ in actions)
        if opening:
            try:self._refill_risk(s)
            except ValueError as exc:
                self._stop(s,'Grid toplu yenileme risk denetimi reddetti: '+str(exc))
                return self._cleanup(s,results,algos,mark,info,True)
        records=[{'proposal':self._proposal(s,k,i,q,mark,info,len(s['orders'])+n),'kind':k,'cell':i}
                 for n,(k,i,q)in enumerate(actions)]
        expected=digest(sorted((r['proposal']['params']for r in records),key=lambda p:p['newClientOrderId']))
        s['orders'].extend(records);self._save(s)
        def authorize(params,phase):
            row=self._scope(s)
            if digest(params)!=expected or not 0<=time.time()-start<=self.limits.max_age_seconds:raise ValueError('Toplu grid kapsamı/görünümü değişti.')
            latest=self.x.get('/fapi/v1/premiumIndex',{'symbol':s['symbol']})
            fresh(latest,s['symbol'],int(time.time()*1000)+getattr(self.x,'offset_ms',0),self.limits.max_age_seconds)
            sign=1 if s['plan']['direction']=='LONG'else -1;price=number(latest['markPrice'])
            if (sign*(price-self._grid_stop(s))<=0 or sign*(number(s['plan']['targets'][0]['price'])-price)<=0):
                self._stop(s,'Toplu gönderim öncesi grid stop sınırı aşıldı.')
                raise ValueError('Toplu grid gönderiminden önce stop/son hedef aşıldı.')
            current=self._results(base);protection=self._algos(base);amount=self._owned_grid(base,current,protection)
            if self._bad_grid_algos(s,protection):raise ValueError('Toplu grid koruması tüketilmiş.')
            reducing=number(0)
            for kind,index,q in actions:
                inventory=self._inventory(base,current,index)
                if any(r['cell']==index and current[r['proposal']['params']['newClientOrderId']]['status']not in NORMAL_TERMINAL for r in base['orders']):raise ValueError('Toplu grid hücresinde aktif emir var.')
                if (kind=='OPEN'and inventory!=0)or(kind=='REDUCE'and inventory!=number(q)):raise ValueError('Toplu grid hücre envanteri değişti.')
                if kind=='REDUCE':reducing+=number(q)
            if reducing>abs(amount):raise ValueError('Toplu azaltma sahip olunan pozisyonu aşıyor.')
            if opening and (s['phase']!='ACTIVE'or time.time()>=timestamp(s['plan']['expires_at'])
                            or(not base['orders']and time.time()>=row['approval_until'])or self.store.halt_reason()
                            or self.store.unresolved_account_command()
                            or self.store.db.execute('SELECT 1 FROM control WHERE name=?',('entry_revoked:'+s['entry_id'],)).fetchone()):
                raise ValueError('Toplu açıcı grid yetkisi sona erdi/durduruldu.')
            if not 0<=time.time()-start<=self.limits.max_age_seconds:raise ValueError('Toplu grid son gönderim görünümü eskidi.')
            return True
        self.book.mark_submitted(s['id'])
        report=NativeBatchCreate(self.x,self.store,s['id']).submit([r['proposal']for r in records],authorize)
        if report['state']=='UNKNOWN':raise ExchangeError('Toplu grid alt emri belirsiz; tekrar gönderilmez.',delivery_status='UNKNOWN')
        current=self._results(s);protection=self._algos(s);amount=self._owned_grid(s,current,protection)
        if report['state']=='FINAL_WITH_ERRORS':
            self._stop(s,'Toplu grid alt emri reddedildi; kalanlar güvenle temizlenecek.')
            return self._cleanup(s,current,protection,mark,info,True)
        if amount:self._protect_grid(s,amount,mark,info,True,protection)
        s.update(cursor=(actions[-1][1]+1)%len(s['compiled']['slots']),status='PROTECTED'if amount else'RUNNING');self._save(s)
        self.service.outcome(s['plan_ref']['plan_id'],s['plan_ref']['version'],'MANAGING')
        return {'state':'GRID_BATCH_SUBMITTED','session_id':s['id'],'executed':True,'orders':report['orders']}

    def _results(self,s):
        result={}
        for record in s['orders']:
            cid=record['proposal']['params']['newClientOrderId']
            saved=self.store.intent(cid)
            p=effective_params(self.store,cid)if saved else record['proposal']['params']
            if saved is None:
                # Crash before reserve means no network submission was possible.
                value=p|{'clientOrderId':cid,'origQty':p['quantity'],'executedQty':'0','status':'REJECTED'}
            elif saved['state']=='REJECTED':
                value=p|{'clientOrderId':cid,'origQty':p['quantity'],'executedQty':'0','status':'REJECTED'}
                cached=json.loads(saved['response'])if saved['response']else{}
                if cached.get('status')=='REJECTED'and cached.get('orderId')is not None:value=cached
            elif saved['state']=='FILLED'and saved['response']:
                # A fully executed owned order cannot acquire another fill.
                # Keep its authoritative identity after exchange history retention.
                value=json.loads(saved['response'])
                if value.get('status')!='FILLED'or number(value.get('executedQty',0))!=number(p['quantity']):
                    raise ValueError('Grid tam gerçekleşme kaydı miktarla uyuşmuyor.')
            else:
                value=self.x.get('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':cid})
            if (value.get('clientOrderId')!=cid or any(value.get(k)!=p[k] for k in ('symbol','side','positionSide'))
                    or value.get('type')!=p['type']or number(value['origQty'])!=number(p['quantity'])
                    or(p['type']=='LIMIT'and number(value['price'])!=number(p['price']))):
                raise ValueError('Grid emri kayıtlı niyetle uyuşmuyor.')
            previous=json.loads(saved['response'])if saved and saved['response']else{}
            if previous.get('orderId')is not None and str(previous['orderId'])!=str(value.get('orderId')):
                raise ValueError('Grid istemci kimliği başka borsa emri için yeniden kullanılmış.')
            status=value['status'];normalized='EXPIRED' if status=='EXPIRED_IN_MATCH' else status
            self.journal.register(cid,s['id'],s['symbol'],p['side'],p['quantity'])
            self.journal.observe(cid,digest(value),status=normalized,cumulative_filled=value['executedQty'],
                                 observed_ms=int(value.get('updateTime',s['started_ms'])))
            if saved:self.store.update(cid,status,value)
            result[cid]=value
        return result

    def _algos(self,s):
        result={}
        for p in self._grid_algos(s):
            cid=p['params']['clientAlgoId']
            saved=self.store.intent(cid)
            if saved:
                if saved['state']=='REJECTED':
                    if p in s['protections']:raise ValueError('Grid koruması reddedildi; yeniden gönderilmez.')
                    a=p['params']|{'algoStatus':'REJECTED'}
                else:a=self.x.get('/fapi/v1/algoOrder',{'clientAlgoId':cid})
                if any(a.get(k)!=p['params'][k] for k in ('clientAlgoId','symbol','side','positionSide')):
                    raise ValueError('Grid koşullu emir kimliği uyuşmuyor.')
                params=p['params']
                if (a.get('orderType',a.get('type'))!=params['type'] or
                        a.get('workingType')!=params['workingType'] or
                        number(a.get('triggerPrice',0))!=number(params['triggerPrice']) or
                        str(a.get('closePosition',False)).lower()!='true' or
                        number(a.get('quantity',0))!=0 or str(a.get('reduceOnly',False)).lower()!='false'):
                    raise ValueError('Grid koşullu emir koruma alanları uyuşmuyor.')
                previous=json.loads(saved['response']) if saved.get('response') else {}
                if previous.get('algoId') is not None and previous['algoId']!=a.get('algoId'):
                    raise ValueError('Grid koşullu istemci kimliği yeniden kullanılmış.')
                result[cid]=a
        return result

    def _owned_grid(self,s,results,algos):
        observed=time.time()
        if time.time()*1000-s['started_ms']>6*86400000:raise ValueError('Grid geçmişi otomatik devralma sınırını aştı.')
        if self.x.get('/fapi/v1/positionSide/dual')['dualSidePosition']!=(s['plan']['position_mode']=='hedge'):
            raise ValueError('Grid pozisyon modu değişti.')
        setting=next((r for r in self.x.get('/fapi/v1/symbolConfig',{'symbol':s['symbol']}) if r['symbol']==s['symbol']),None)
        if setting is None or int(setting['leverage'])!=s['plan']['execution']['leverage'] or setting['marginType']!=s['plan']['execution']['margin_mode']:
            raise ValueError('Grid kaldıraç/teminat ayarı değişti.')
        normal_ids={str(v['orderId']) for v in results.values() if 'orderId'in v}
        algo_ids={str(a['actualOrderId']) for a in algos.values() if a.get('actualOrderId')not in (None,'',0,'0')}
        trades=account_trades(self.x,s['symbol'],s['started_ms'])
        if any(str(t['orderId'])not in normal_ids|algo_ids for t in trades):
            raise ValueError('Grid geçmişi eksik veya yabancı işlem içeriyor.')
        def total(rows):return sum((number(t['qty'])*(1 if t['side']=='BUY' else -1) for t in rows),number(0))
        if total(t for t in trades if str(t['orderId'])in normal_ids)!=self.journal.inventory(s['id'],s['symbol']):
            raise ValueError('Grid kümülatif gerçekleşme ve işlem geçmişi uyuşmuyor.')
        ps='BOTH' if s['plan']['position_mode']=='one-way' else s['plan']['direction']
        positions=self.x.get('/fapi/v3/positionRisk')
        multi=len(self.store.sessions())>1
        if not multi and any(number(p['positionAmt'])and(p['symbol']!=s['symbol']or p['positionSide']!=ps) for p in positions):
            raise ValueError('Grid dışında pozisyon var.')
        amount=sum((number(p['positionAmt']) for p in positions if p['symbol']==s['symbol']and p['positionSide']==ps),number(0))
        sign=1 if s['plan']['direction']=='LONG' else -1
        capacity=sum(number(c['quantity'])for c in s['compiled']['slots'])
        if amount!=total(trades)or amount*sign<0 or abs(amount)>capacity:raise ValueError('Grid pozisyon/envanter sınırı uyuşmuyor.')
        if multi:
            from .account_ownership import AccountOwnership
            AccountOwnership(self,session_views={s['id']:s}).verify(positions=positions)
            if not 0<=time.time()-observed<=self.limits.max_age_seconds:
                raise ValueError('Çoklu grid sahiplik görünümü eskidi.')
            return amount
        for o in self.x.get('/fapi/v1/openOrders'):
            if o.get('symbol')!=s['symbol'] or (o['clientOrderId']not in results and str(o.get('orderId'))not in algo_ids):
                raise ValueError('Yabancı açık grid emri var.')
        own={p['params']['clientAlgoId']for p in self._grid_algos(s)}
        if any(o.get('symbol')!=s['symbol'] or o['clientAlgoId']not in own for o in self.x.get('/fapi/v1/openAlgoOrders')):
            raise ValueError('Yabancı açık koşullu grid emri var.')
        if not 0<=time.time()-observed<=self.limits.max_age_seconds:
            raise ValueError('Grid sahiplik görünümü eskidi.')
        return amount

    def _inventory(self,s,results,index):
        slot=s['compiled']['slots'][index]
        seed=next((r for r in s['orders']if r['kind']=='SEED'),None)
        inventory=number(slot['quantity'])if slot['seed']and seed and results[seed['proposal']['params']['newClientOrderId']]['status']=='FILLED' else number(0)
        for r in s['orders']:
            if r['cell']==index:
                inventory+=number(results[r['proposal']['params']['newClientOrderId']]['executedQty'])*(1 if r['kind']=='OPEN'else -1)
        if not 0<=inventory<=number(slot['quantity']):raise ValueError('Grid hücre envanteri sınırı aşıldı.')
        return inventory

    def _refill_risk(self,s):
        start=time.time();account=self.x.get('/fapi/v3/account');config=self.x.get('/fapi/v1/accountConfig')
        if config.get('canTrade')is not True:raise ValueError('Grid hesap işlem uygunluğu doğrulanamadı.')
        index=self.x.get('/fapi/v1/assetIndex',{'symbol':'USDTUSD'})if config['multiAssetsMargin']else None
        if index is not None:fresh(index,'USDTUSD',int(time.time()*1000)+getattr(self.x,'offset_ms',0),self.limits.max_age_seconds)
        collateral=collateral_usdt(account,config,index)
        published=self.x.get('/fapi/v1/leverageBracket',{'symbol':s['symbol']})
        published=[published] if isinstance(published,dict) else published
        selected=[r for r in published if r.get('symbol')==s['symbol']]
        if len(selected)!=1 or number(selected[0].get('notionalCoef',1))!=1:
            raise ValueError('Grid güncel kaldıraç basamakları doğrulanamadı.')
        tier=select_bracket(selected[0]['brackets'],s['compiled']['notional_ceiling'],s['plan']['execution']['leverage'])
        midnight=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
        incomes=income_history(self.x,int(midnight.timestamp()*1000))
        relevant=[r for r in incomes if r['incomeType']in('REALIZED_PNL','COMMISSION','FUNDING_FEE')]
        if any(r['asset']!='USDT'for r in relevant):raise ValueError('Grid günlük varlık dönüşümü gerekli.')
        pnl=sum((number(r['income'])for r in relevant),number(0))
        pnl+=min(number(next(a for a in account['assets']if a['asset']=='USDT').get('unrealizedProfit',0)),number(0))
        if datetime.now(timezone.utc).date()!=midnight.date():raise ValueError('Grid günlük sonuç görünümü yenilenmeli.')
        exposures=[Exposure(**(e|{'maintenance_ratio':str(tier['maintMarginRatio']),
                                 'maintenance_deduction':'0'})) for e in s['compiled']['exposures']]
        evaluate_portfolio(exposures,collateral,max(-pnl,number(0)),
                           start,time.time(),self.limits,collateral_valuation_verified=True)
        self._joint_risk({'collateral':str(collateral),'daily_loss':str(max(-pnl,number(0))),
                          'observed_at':start})

    def _protect_grid(self,s,amount,mark,info,execute,algos):
        if not amount:return True
        if not s['protections']:
            sign=1 if s['plan']['direction']=='LONG'else -1
            for i,(kind,price)in enumerate((('STOP_MARKET',s['plan']['stop']),('TAKE_PROFIT_MARKET',s['plan']['targets'][0]['price']))):
                p={'symbol':s['symbol'],'side':'SELL'if sign==1 else 'BUY','positionSide':'BOTH'if s['plan']['position_mode']=='one-way'else s['plan']['direction'],
                   'type':kind,'closePosition':'true','triggerPrice':price,'workingType':'MARK_PRICE','clientAlgoId':self._id(s,['grid-protection',i])}
                s['protections'].append(validate_order(p,info,s['plan']['position_mode'],'CLOSE',mark['markPrice'],int(time.time()*1000)))
            self._save(s)
        for p in s['protections']:
            cid=p['params']['clientAlgoId'];saved=self.store.intent(cid)
            if not saved and not execute:return False
            if execute and not saved:self._post(s,p)
            a=algos.get(cid)
            if a is None:a=self.x.get('/fapi/v1/algoOrder',{'clientAlgoId':cid});algos[cid]=a
            params=p['params']
            if (a.get('algoStatus')not in ALGO_ACTIVE or any(a.get(k)!=params[k]for k in('clientAlgoId','symbol','side','positionSide','workingType'))
                    or a.get('orderType',a.get('type'))!=params['type']or str(a.get('closePosition')).lower()!='true'
                    or number(a.get('triggerPrice',0))!=number(params['triggerPrice'])):
                raise ValueError('Grid borsa koruması etkin/eşleşen durumda değil.')
        return True

    def _cleanup(self,s,results,algos,mark,info,execute):
        pending=[r['proposal']['params']['newClientOrderId']for r in s['orders']if results[r['proposal']['params']['newClientOrderId']]['status']not in NORMAL_TERMINAL]
        if pending:
            if not execute:return {'state':'GRID_CANCEL_REQUIRED','session_id':s['id'],'executed':False}
            self._cancel_regular(s,pending);results=self._results(s)
            if any(results[c]['status']not in NORMAL_TERMINAL for c in pending):raise ValueError('Grid iptali terminal değil.')
        child_ids={str(a['actualOrderId'])for a in algos.values()if a.get('actualOrderId')not in(None,'',0,'0')}
        for child in self.x.get('/fapi/v1/openOrders'):
            if child['symbol']!=s['symbol']:continue
            if child['clientOrderId']not in results:
                if str(child.get('orderId'))not in child_ids:raise ValueError('Grid temizliğinde yabancı emir var.')
                if not execute:return {'state':'GRID_CHILD_CANCEL_REQUIRED','session_id':s['id'],'executed':False}
                query={'symbol':s['symbol'],'origClientOrderId':child['clientOrderId']}
                self._cancel('/fapi/v1/order',query)
                if self.x.get('/fapi/v1/order',query)['status']not in NORMAL_TERMINAL:
                    raise ValueError('Grid tetiklenmiş koruma alt emri iptal bekliyor.')
        if any(a.get('algoStatus') in ('TRIGGERING','TRIGGERED') and
               a.get('actualOrderId') in (None,'',0,'0') for a in algos.values()):
            return {'state':'GRID_NATIVE_CHILD_PENDING','session_id':s['id'],'executed':False}
        amount=self._owned_grid(s,results,algos)
        if amount:
            if not execute:return {'state':'GRID_CLOSE_REQUIRED','session_id':s['id'],'executed':False}
            self._new_order(s,'CLOSE',None,str(abs(amount)),mark,info)
            return {'state':'GRID_CLOSE_SUBMITTED','session_id':s['id'],'executed':True}
        for cid,a in algos.items():
            if a.get('algoStatus')not in ALGO_TERMINAL:
                if not execute:return {'state':'GRID_CLEANUP_REQUIRED','session_id':s['id'],'executed':False}
                self._cancel('/fapi/v1/algoOrder',{'clientAlgoId':cid})
                if self.x.get('/fapi/v1/algoOrder',{'clientAlgoId':cid}).get('algoStatus')not in ALGO_TERMINAL:
                    raise ValueError('Grid koşullu iptali terminal değil.')
        own_open=[o for o in self.x.get('/fapi/v1/openOrders')+self.x.get('/fapi/v1/openAlgoOrders') if o['symbol']==s['symbol']]
        if own_open or self._owned_grid(s,self._results(s),self._algos(s)):
            raise ValueError('Grid temizliği henüz boş hesapla doğrulanmadı.')
        s.update(active=False,status='CLOSED',phase='CLOSED')
        self.book.close_session(s,flat_verified=True,orders_terminal=True)
        self.service.show(s['plan_ref']['plan_id'],s['plan_ref']['version'])
        return {'state':'CLOSED','session_id':s['id'],'executed':execute,'reason':s.get('stop_reason')}

    def _cancel_regular(self,s,client_ids):
        self._scope(s)
        if s['phase']not in('STOPPING','DRAINING'):raise ValueError('Toplu grid iptali için durdurma bariyeri gerekli.')
        owned={r['proposal']['params']['newClientOrderId']for r in s['orders']}
        for offset in range(0,len(client_ids),10):
            chunk=client_ids[offset:offset+10]
            if len(chunk)==1:self._cancel('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':chunk[0]})
            else:
                report=OwnedBatchCancel(self.x,self.store).cancel(s['symbol'],chunk,owned_client_ids=owned)
                if report['unresolved']:raise ValueError('Toplu grid iptalinde sonlanmamış alt emir var.')

    def _manage(self,sid,execute=False):
        s=self._session(sid);self.x.sync_time()
        results=self._results(s);algos=self._algos(s)
        amount=self._owned_grid(s,results,algos)
        mark=self.x.get('/fapi/v1/premiumIndex',{'symbol':s['symbol']})
        fresh(mark,s['symbol'],int(time.time()*1000)+getattr(self.x,'offset_ms',0),self.limits.max_age_seconds)
        info=next(i for i in self.x.get('/fapi/v1/exchangeInfo')['symbols']if i['symbol']==s['symbol'])
        sign=1 if s['plan']['direction']=='LONG'else -1;price=number(mark['markPrice'])
        self._advance_grid_trailing(s,amount,mark,info)
        if (sign*(price-self._grid_stop(s))<=0 or sign*(price-number(s['plan']['targets'][0]['price']))>=0
                or self.store.halt_reason()
                or self._bad_grid_algos(s,algos)):
            self._stop(s,'Stop/hedef/süre/yetki veya koruma durumu grid girişlerini durdurdu.')
        if (time.time()>=timestamp(s['plan']['expires_at'])or self.store.db.execute('SELECT 1 FROM control WHERE name=?',('entry_revoked:'+s['entry_id'],)).fetchone())and s['phase']=='ACTIVE':
            s.update(phase='DRAINING',stop_reason='Yeni giriş yetkisi sona erdi; mevcut pozisyon korumayla yönetiliyor.');self._save(s)
        for r in s['orders']:
            a=results[r['proposal']['params']['newClientOrderId']]
            if a['status']=='REJECTED':self._stop(s,'Gönderilmeyen/reddedilen grid niyeti uzlaştırılıyor.')
            if r['kind']=='SEED'and a['status']!='FILLED':self._stop(s,'Kısmi/bekleyen başlangıç envanteri; güvenli kapanış.')
            if r['kind']=='SEED'and a['status']=='FILLED':
                avg=number(a.get('avgPrice',0))
                if avg<=0 or (sign==1 and avg>number(s['plan']['grid']['upper']))or(sign==-1 and avg<number(s['plan']['grid']['lower'])):
                    self._stop(s,'Başlangıç gerçekleşmesi ayrılan fiyat zarfını aştı.')
            if a['status']in('CANCELED','EXPIRED','EXPIRED_IN_MATCH'):
                command=digest(json.dumps(['/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':r['proposal']['params']['newClientOrderId']}],sort_keys=True))
                if not self.store.db.execute('SELECT 1 FROM v2_cancellations WHERE command_id=?',(command,)).fetchone():
                    if s['phase']=='ACTIVE':s.update(phase='DRAINING',stop_reason='Harici/sistem iptali; yeni girişler kapalı, mevcut koruma sürüyor.')
                    cells=s.setdefault('manual_cells',[])
                    if r['cell']is not None and r['cell']not in cells:cells.append(r['cell'])
                    self._save(s)
        if s['phase']=='STOPPING':return self._cleanup(s,results,algos,mark,info,execute)
        if s['phase']=='DRAINING':
            pending=[r['proposal']['params']['newClientOrderId']for r in s['orders']if r['kind']in('OPEN','SEED')and results[r['proposal']['params']['newClientOrderId']]['status']not in NORMAL_TERMINAL]
            if pending:
                if not execute:return {'state':'GRID_ENTRY_CANCEL_REQUIRED','session_id':sid,'executed':False}
                self._cancel_regular(s,pending)
            results=self._results(s);amount=self._owned_grid(s,results,algos)
            if any(r['kind']in('OPEN','SEED')and results[r['proposal']['params']['newClientOrderId']]['status']not in NORMAL_TERMINAL for r in s['orders']):
                raise ValueError('Grid giriş iptali terminal değil; yeni eylem üretilmedi.')
            if not amount:return self._cleanup(s,results,algos,mark,info,execute)
        if not self._protect_grid(s,amount,mark,info,execute,algos):return {'state':'PROTECTION_REQUIRED','session_id':sid,'executed':False}
        from .grid_native_stop import move_stop
        moved=move_stop(self,s,amount,mark,info,execute,results,algos)
        if moved is not None:return moved
        if execute:
            ready=self._ready_actions(s,results,price)
            if len(ready)>1:return self._new_batch(s,ready,mark,info,results,algos)
        slots=s['compiled']['slots'];cursor=s.get('cursor',0)
        for slot in slots[cursor:]+slots[:cursor]:
            active=[r for r in s['orders']if r['cell']==slot['index']and results[r['proposal']['params']['newClientOrderId']]['status']not in NORMAL_TERMINAL]
            if len(active)>1:raise ValueError('Hücrede birden fazla aktif grid emri var.')
            if active:
                p=active[0]['proposal']['params'];a=results[p['newClientOrderId']]
                if number(a['executedQty']):
                    if not execute:return {'state':'GRID_PARTIAL_CANCEL_REQUIRED','session_id':sid,'executed':False}
                    self._cancel('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':p['newClientOrderId']})
                    s['cursor']=(slot['index']+1)%len(slots);self._save(s)
                    return {'state':'GRID_PARTIAL_CANCELED','session_id':sid,'executed':True}
                continue
            inventory=self._inventory(s,results,slot['index']);kind='REDUCE'if inventory else'OPEN'
            if kind=='OPEN'and s['phase']=='DRAINING':continue
            if slot['index']in s.get('manual_cells',[]):continue
            if kind=='OPEN'and not number(s['plan']['grid']['lower'])<=price<number(s['plan']['grid']['upper']):continue
            if not execute:return {'state':'GRID_ACTION_REQUIRED','kind':kind,'cell':slot['index'],'session_id':sid,'executed':False}
            if kind=='OPEN':
                if self.store.unresolved_account_command():raise ValueError('Belirsiz hesap ayarı varken grid artırılmaz.')
                try:self._refill_risk(s)
                except ValueError as exc:
                    self._stop(s,'Grid yenileme risk denetimi reddetti: '+str(exc))
                    return self._cleanup(s,results,algos,mark,info,execute)
                latest=self.x.get('/fapi/v1/premiumIndex',{'symbol':s['symbol']})
                fresh(latest,s['symbol'],int(time.time()*1000)+getattr(self.x,'offset_ms',0),self.limits.max_age_seconds)
                if sign*(number(latest['markPrice'])-self._grid_stop(s))<=0:
                    self._stop(s,'Gönderim öncesi stop aşıldı.');return {'state':'GRID_STOPPING','session_id':sid,'executed':False}
                if not s['orders']and time.time()>=self._scope(s)['approval_until']:
                    self._stop(s,'İlk emirden önce onay süresi doldu.');return {'state':'GRID_STOPPING','session_id':sid,'executed':False}
                self._owned_grid(s,self._results(s),self._algos(s))
            self._new_order(s,kind,slot['index'],str(inventory)if inventory else slot['quantity'],mark,info)
            s['cursor']=(slot['index']+1)%len(slots)
            s['status']='PROTECTED' if amount else 'RUNNING';self._save(s)
            self.service.outcome(s['plan_ref']['plan_id'],s['plan_ref']['version'],'MANAGING')
            return {'state':'GRID_ORDER_SUBMITTED','kind':kind,'cell':slot['index'],'session_id':sid,'executed':True}
        return {'state':'GRID_DRAINING'if s['phase']=='DRAINING'else'GRID_RUNNING','session_id':sid,'executed':False,'position':str(amount),
                'bot_stop':str(self._grid_stop(s)),'trailing_active':s.get('grid_trailing_state',{}).get('active',False)}
