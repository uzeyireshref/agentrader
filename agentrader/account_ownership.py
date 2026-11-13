"""Read-only, account-wide proof for distinct-symbol v2 sessions.

An order is owned only when both its immutable plan and durable intent match.
No prefix-based adoption, no mutation, and no same-symbol position splitting.
"""
import json
import time

from .history import account_trades
from .order_revisions import effective_params
from .plans import digest
from .risk import number


class AccountOwnership:
    def __init__(self,runner,exclude_session=None,session_views=None):
        self.runner=runner
        self.store,self.x=runner.store,runner.x
        self.exclude_session=exclude_session
        self.session_views=session_views or {}

    def verify(self,*,positions=None,normal=None,algos=None,account_positions=None):
        started=time.time()
        from .v2_runner import V2Runner
        from .grid_runner import GridRunner
        from .neutral_runner import NeutralGridRunner
        sessions=[s for s in self.store.sessions() if s['id']!=self.exclude_session]
        symbols=set();normal_ids=set();algo_clients=set();broker_ids=set();expected={}
        proofs=[];normal_map={};algo_map={};child_ids=set();isolated={}
        for s in sessions:
            if (s.get('engine') not in ('v2','grid-v2','neutral-v2') or s.get('account_ref')!=self.runner.account_ref
                    or s['symbol'] in symbols):
                raise ValueError('Çoklu oturum için aynı hesapta, farklı sembollü v2 sahipliği gerekli.')
            symbols.add(s['symbol'])
            peer={'v2':V2Runner,'grid-v2':GridRunner,'neutral-v2':NeutralGridRunner}[s['engine']](self.runner.service,self.x,self.runner.limits)
            s=peer._session(s['id'])
            if s['id'] in self.session_views:
                s=self.session_views[s['id']]
                peer._scope(s)
            if time.time()*1000+getattr(self.x,'offset_ms',0)-s['started_ms']>6*86400000:
                raise ValueError('Oturum sahipliği geçmiş penceresi aşıldı.')
            mode=self.x.get('/fapi/v1/positionSide/dual').get('dualSidePosition')
            settings=self.x.get('/fapi/v1/symbolConfig',{'symbol':s['symbol']})
            setting=[r for r in settings if r['symbol']==s['symbol']]
            if (mode!=(s['plan']['position_mode']=='hedge') or len(setting)!=1 or
                    int(setting[0]['leverage'])!=s['plan']['execution']['leverage'] or
                    setting[0]['marginType']!=s['plan']['execution']['margin_mode']):
                raise ValueError('Eş oturum hesap modu/kaldıraç/teminat ayarı değişti.')
            # Legacy sessions remain manageable alone; they are never silently
            # assigned an invented risk envelope to admit another live session.
            if peer.book.state(s['id'])=='RELEASED':
                raise ValueError('Etkin oturumun risk rezervi serbest bırakılamaz.')
            reserved=self.store.db.execute('SELECT body FROM risk_reservations WHERE reservation_id=?',(s['id'],)).fetchone()
            reserved=json.loads(reserved['body'])
            exposures=s['prepared'].get('exposures') if s['engine']=='v2' else s['compiled']['exposures']
            if (not exposures or reserved['owner']!=self.runner.service.owner or
                    reserved['plan_digest']!=s['plan_ref']['digest'] or reserved['exposures']!=exposures):
                raise ValueError('Eş oturumun risk rezervi planla uyuşmuyor; eski kayıt kendiliğinden devralınmaz.')
            proposals=([s['prepared']['entry']]+s['exits'] if s['engine']=='v2' else
                       [r['proposal'] for r in s['orders']])
            own_orders={};own_algos={};own_brokers=set();broker_sides={}
            for proposal in proposals:
                p=proposal['params'];cid=p['newClientOrderId'];saved=self.store.intent(cid)
                if saved is None:
                    continue
                if saved['path']!=proposal['path'] or json.loads(saved['params'])!=p:
                    raise ValueError('Eş oturum emir niyeti planla uyuşmuyor.')
                if saved['state']=='REJECTED':continue
                effective=effective_params(self.store,cid)
                if s['engine'] in ('grid-v2','neutral-v2') and saved['state']=='FILLED' and saved.get('response'):
                    actual=json.loads(saved['response'])
                    if actual.get('status')!='FILLED' or number(actual.get('executedQty',0))!=number(effective['quantity']):
                        raise ValueError('Eş grid tam gerçekleşme kaydı uyuşmuyor.')
                else:
                    actual=self.x.get('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':cid})
                if (any(actual.get(k)!=effective[k] for k in ('symbol','side','positionSide','type')) or
                        actual.get('clientOrderId')!=cid or
                        type(actual.get('orderId'))is not int or actual['orderId']<0 or
                        number(actual['origQty'])!=number(effective['quantity']) or
                        str(actual.get('reduceOnly',False)).lower()!=str(effective.get('reduceOnly',False)).lower() or
                        (effective['type']=='LIMIT' and (number(actual.get('price',0))!=number(effective['price']) or
                                                        actual.get('timeInForce')!=effective['timeInForce']))):
                    raise ValueError('Eş oturum normal emir kimliği/miktarı uyuşmuyor.')
                filled=number(actual['executedQty']);quantity=number(actual['origQty']);status=actual.get('status')
                if (status not in ('NEW','PARTIALLY_FILLED','FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED','PENDING_CANCEL')
                        or not 0<=filled<=quantity or (status=='FILLED' and filled!=quantity) or (status=='REJECTED' and filled)):
                    raise ValueError('Eş oturum normal emir durumu/gerçekleşmesi geçersiz.')
                previous=json.loads(saved['response']) if saved.get('response') else {}
                if previous.get('orderId') is not None and str(previous['orderId'])!=str(actual.get('orderId')):
                    raise ValueError('Eş oturum istemci kimliği başka borsa emrinde kullanılmış.')
                bid=str(actual['orderId'])
                if bid in own_brokers:raise ValueError('Aynı sembolde tekrarlanan borsa emir kimliği.')
                own_orders[cid]=actual;own_brokers.add(bid);broker_sides[bid]=actual['positionSide']
            for proposal in s['protections']+[t['proposal'] for t in s.get('stop_transitions',[])]:
                p=proposal['params'];cid=p['clientAlgoId'];saved=self.store.intent(cid)
                if saved is None:continue
                if saved['path']!=proposal['path'] or json.loads(saved['params'])!=p:
                    raise ValueError('Eş oturum koşullu niyeti planla uyuşmuyor.')
                if saved['state']=='REJECTED':continue
                actual=self.x.get('/fapi/v1/algoOrder',{'clientAlgoId':cid})
                if s['engine']=='neutral-v2' and proposal.get('retired_flat') and (
                        actual.get('algoStatus') not in ('CANCELED','EXPIRED') or actual.get('actualOrderId') not in (None,'','0',0)):
                    raise ValueError('Neutral emekli koruma sahipliği/durumu uyuşmuyor.')
                if (any(actual.get(k)!=p[k] for k in ('clientAlgoId','symbol','side','positionSide')) or
                        actual.get('orderType',actual.get('type'))!=p['type'] or
                        actual.get('workingType')!=p['workingType'] or
                        number(actual.get('triggerPrice',0))!=number(p['triggerPrice']) or
                        str(actual.get('closePosition',False)).lower()!=str(p.get('closePosition',False)).lower() or
                        ('quantity' in p and number(actual.get('quantity',0))!=number(p['quantity'])) or
                        ('reduceOnly' in p and str(actual.get('reduceOnly')).lower()!=str(p['reduceOnly']).lower())):
                    raise ValueError('Eş oturum koşullu emir kimliği uyuşmuyor.')
                previous=json.loads(saved['response']) if saved.get('response') else {}
                if previous.get('algoId') is not None and previous['algoId']!=actual.get('algoId'):
                    raise ValueError('Eş oturum koşullu istemci kimliği yeniden kullanılmış.')
                own_algos[cid]=actual
                child=actual.get('actualOrderId')
                if child not in (None,'','0',0):
                    own_brokers.add(str(child));child_ids.add((s['symbol'],str(child)))
                    if str(child) in broker_sides and broker_sides[str(child)]!=p['positionSide']:
                        raise ValueError('Koşullu alt emir farklı pozisyon tarafına bağlanamaz.')
                    broker_sides[str(child)]=p['positionSide']
            trades=account_trades(self.x,s['symbol'],s['started_ms'])
            if any(str(t['orderId']) not in own_brokers for t in trades):
                raise ValueError('Eş oturumda sahiplenilemeyen gerçekleşme var.')
            signed=lambda rows:sum((number(t['qty'])*(1 if t['side']=='BUY' else -1) for t in rows),number(0))
            for o in own_orders.values():
                fills=[t for t in trades if str(t['orderId'])==str(o['orderId'])]
                if (sum((number(t['qty']) for t in fills),number(0))!=number(o['executedQty']) or
                        any(t['side']!=o['side'] or t.get('positionSide',o['positionSide'])!=o['positionSide'] for t in fills)):
                    raise ValueError('Eş oturum gerçekleşmesi emir miktarı/tarafıyla uyuşmuyor.')
            if s['engine']=='neutral-v2':
                if any(t.get('positionSide') not in ('LONG','SHORT') or
                       broker_sides[str(t['orderId'])]!=t['positionSide'] for t in trades):
                    raise ValueError('Neutral gerçekleşme LONG/SHORT sahipliği uyuşmuyor.')
                amounts={ps:signed(t for t in trades if t['positionSide']==ps) for ps in ('LONG','SHORT')}
            else:
                ps='BOTH' if s['plan']['position_mode']=='one-way' else s['plan']['direction']
                amounts={ps:signed(trades)}
            for ps,amount in amounts.items():
                direction=ps if ps!='BOTH' else s['plan']['direction']
                sign=1 if direction=='LONG' else -1
                capacity=(number(s['prepared']['quantity']) if s['engine']=='v2' else
                          sum((number(c['quantity']) for c in s['compiled']['slots']
                               if s['engine']!='neutral-v2' or c['position_side']==ps),number(0)))
                if amount*sign<0 or abs(amount)>capacity:
                    raise ValueError('Eş oturum envanteri onaylanan taraf zarfını aşıyor.')
                expected[s['symbol'],ps]=amount
                if s['plan']['execution']['margin_mode']=='ISOLATED':
                    isolated[s['symbol'],ps]=s['plan']['execution']['leverage']
                protected=False
                for proposal in s['protections']+[t['proposal'] for t in s.get('stop_transitions',[])]:
                    p=proposal['params'];a=own_algos.get(p['clientAlgoId'])
                    if (a is None or p['positionSide']!=ps or p['type']!='STOP_MARKET' or a.get('algoStatus')!='NEW' or
                            a.get('workingType')!='MARK_PRICE' or number(a.get('triggerPrice',0))!=number(p['triggerPrice'])):
                        continue
                    close=str(p.get('closePosition')).lower()=='true'
                    if close and str(a.get('closePosition')).lower()=='true':protected=True
                    elif (number(a.get('quantity',0))>=abs(amount) and
                          (ps!='BOTH' or str(a.get('reduceOnly')).lower()=='true')):protected=True
                proofs.append({'session_id':s['id'],'symbol':s['symbol'],'position_side':ps,
                               'amount':str(amount),'protected':not amount or protected})
            normal_ids.update((s['symbol'],cid) for cid in own_orders)
            algo_clients.update((s['symbol'],cid) for cid in own_algos)
            normal_map.update({(s['symbol'],cid):o for cid,o in own_orders.items()})
            algo_map.update({(s['symbol'],cid):a for cid,a in own_algos.items()})
            broker_ids.update((s['symbol'],bid) for bid in own_brokers)
        positions=self.x.get('/fapi/v3/positionRisk') if positions is None else positions
        actual={}
        for p in positions:
            key=(p['symbol'],p['positionSide']);q=number(p['positionAmt'])
            if key in actual:raise ValueError('Tekrarlanan hesap pozisyon kaydı.')
            actual[key]=q
            if q and key in isolated:
                entry=number(p.get('entryPrice',0));wallet=number(p.get('isolatedWallet',0))
                if entry<=0 or wallet<abs(q)*entry/isolated[key]:
                    raise ValueError('Eş izole pozisyonun gerçek cüzdanı başlangıç teminatını karşılamıyor.')
            if q and (key not in expected or q!=expected[key]):
                raise ValueError('Hesapta yabancı veya eşleşmeyen pozisyon var.')
        if any(actual.get(key,number(0))!=q for key,q in expected.items()):
            raise ValueError('Sahip olunan oturum pozisyonu borsada uyuşmuyor.')
        if account_positions is not None:
            account_map={}
            for p in account_positions:
                key=(p['symbol'],p['positionSide'])
                if key in account_map:raise ValueError('Hesap görünümünde tekrarlanan pozisyon kaydı.')
                account_map[key]=number(p['positionAmt'])
                if account_map[key]!=actual.get(key,number(0)):
                    raise ValueError('Hesap ve pozisyon görünümü uyuşmuyor.')
            if any(q and account_map.get(key,number(0))!=q for key,q in actual.items()):
                raise ValueError('Hesap görünümü sahip olunan pozisyonları eksik gösteriyor.')
        normal=self.x.get('/fapi/v1/openOrders') if normal is None else normal
        algos=self.x.get('/fapi/v1/openAlgoOrders') if algos is None else algos
        for o in normal:
            owned=normal_map.get((o['symbol'],o['clientOrderId']))
            if owned is not None:
                if (str(o.get('orderId'))!=str(owned['orderId']) or
                        owned['status'] not in ('NEW','PARTIALLY_FILLED','PENDING_CANCEL')):
                    raise ValueError('Açık normal emir sahipliğinin borsa kimliği/durumu uyuşmuyor.')
            elif (o['symbol'],str(o.get('orderId'))) not in child_ids:
                raise ValueError('Hesapta sahiplenilemeyen açık normal emir var.')
        for o in algos:
            owned=algo_map.get((o['symbol'],o['clientAlgoId']))
            if (owned is None or owned.get('algoStatus')!='NEW' or
                    (owned.get('algoId') is not None and o.get('algoId')!=owned['algoId'])):
                raise ValueError('Hesapta sahiplenilemeyen açık koşullu emir var.')
        if not 0<=time.time()-started<=self.runner.limits.max_age_seconds:
            raise ValueError('Ortak hesap sahipliği görünümü toplanırken eskidi.')
        return {'sessions':proofs,'normal_ids':normal_ids,'algo_ids':algo_clients,
                'broker_ids':broker_ids,'positions':expected,'digest':digest(proofs)}
