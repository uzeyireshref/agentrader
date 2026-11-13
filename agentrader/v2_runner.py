"""Authorized, restartable v2 SINGLE market entry and exchange-held protection.

Supports bounded SINGLE market/limit entries, staged targets and break-even stops.
Every POST identity is reserved before delivery. Lost responses are queried only.
Caller holds execution_lock. Nothing in this module enables live trading.
"""
from .history import account_trades
import hashlib
import json
import time
from decimal import ROUND_CEILING, ROUND_FLOOR

from .exchange import ExchangeError
from .order_journal import OrderJournal
from .order_revisions import effective_params
from .order_rules import validate_order
from .plans import digest, timestamp
from .risk import number
from .portfolio import Exposure
from .reservations import ReservationBook
from .management import split_targets
from .v2_preflight import collect_flat_snapshot, prepare_single, fresh

NORMAL_TERMINAL = {'FILLED', 'CANCELED', 'EXPIRED', 'EXPIRED_IN_MATCH', 'REJECTED'}
ALGO_ACTIVE = {'NEW'}
ALGO_TERMINAL = {'CANCELED', 'FINISHED', 'REJECTED', 'EXPIRED'}


class V2Runner:
    def __init__(self, service, exchange, limits):
        self.service, self.x, self.limits = service, exchange, limits
        self.store = service.store
        self.journal = OrderJournal(self.store)
        self.account_ref = hashlib.sha256(exchange.config.api_key.encode()).hexdigest()
        self.book=ReservationBook(self.store,self.account_ref)
        self.store.db.execute('''CREATE TABLE IF NOT EXISTS v2_cancellations (
            command_id TEXT PRIMARY KEY, body TEXT NOT NULL, state TEXT NOT NULL)''')

    def _save(self, session):
        self.store.save_session(session)

    def _id(self, session, role):
        return 'agt-v2-' + digest([session['id'], role])[:27]

    def _collect_snapshot(self,symbol,**options):
        return collect_flat_snapshot(self.x,symbol,self.limits,**options)

    def _snapshot(self,symbol,exclude_session=None):
        from .account_ownership import AccountOwnership
        peers=[s for s in self.store.sessions() if s['id']!=exclude_session]
        if peers:
            return self._collect_snapshot(symbol,ownership=AccountOwnership(self,exclude_session))
        return self._collect_snapshot(symbol)

    def _joint_risk(self,snapshot,extra_exposures=()):
        count=self.store.db.execute("SELECT COUNT(*) FROM risk_reservations WHERE account_ref=? AND state!='RELEASED'",
                                    (self.account_ref,)).fetchone()[0]
        return self.book.evaluate(snapshot,self.limits,extra_exposures=extra_exposures,
                                  exchange=self.x if count+bool(extra_exposures)>1 else None)

    def _scope(self, session, entry=False):
        row = self.service.show(session['plan_ref']['plan_id'], session['plan_ref']['version'])
        if (row['digest'] != session['plan_ref']['digest'] or row['session_id'] != session['id']
                or row['action_id'] != session['entry_id'] or session['account_ref'] != self.account_ref
                or row['state'] not in ('EXECUTING', 'MANAGING', 'NEEDS_REVIEW')):
            raise ValueError('V2 oturum/plan/hesap sahipliği uyuşmuyor.')
        if digest(session['plan']) != row['digest'] or session['prepared']['plan_digest'] != row['digest']:
            raise ValueError('V2 oturum içeriği onaylanan planla uyuşmuyor.')
        if session['prepared'].get('exposures'):
            self.book.assert_binding(session['id'],self.service.owner,row['digest'],session['prepared']['exposures'])
        elif self.store.db.execute('SELECT 1 FROM risk_reservations WHERE reservation_id=?',(session['id'],)).fetchone():
            raise ValueError('Risk rezervli SINGLE oturumun maruziyet kaydı eksik.')
        plan = row['plan']
        side = 'BUY' if plan['direction'] == 'LONG' else 'SELL'
        ps = 'BOTH' if plan['position_mode'] == 'one-way' else plan['direction']
        params = session['prepared']['entry']['params']
        expected = {'symbol': plan['symbol'], 'side': side, 'positionSide': ps,
                    'type': 'LIMIT' if plan['entry']['condition'] == 'LIMIT' else 'MARKET',
                    'quantity': session['prepared']['quantity'],
                    'newClientOrderId': session['entry_id']}
        if expected['type'] == 'LIMIT':
            expected.update(price=str(number(plan['entry']['trigger_price'])), timeInForce='GTC')
        if params != expected or number(params['quantity']) <= 0:
            raise ValueError('V2 kayıtlı giriş kapsamı uyuşmuyor.')
        if len(session['protections']) != 2:
            raise ValueError('V2 koruma paketi eksik.')
        for index, (kind, trigger) in enumerate((('STOP_MARKET', plan['stop']),
                                                ('TAKE_PROFIT_MARKET', plan['targets'][-1]['price']))):
            expected = {'symbol': plan['symbol'], 'side': 'SELL' if side == 'BUY' else 'BUY',
                        'positionSide': ps, 'type': kind, 'closePosition': 'true',
                        'triggerPrice': str(number(trigger)), 'workingType': 'MARK_PRICE',
                        'algoType': 'CONDITIONAL', 'clientAlgoId': self._id(session, 'protection-'+str(index))}
            proposal = session['protections'][index]
            if proposal['path'] != '/fapi/v1/algoOrder' or proposal['params'] != expected:
                raise ValueError('V2 kayıtlı koruma onaylanan seviyelerle uyuşmuyor.')
        previous=session['protections'][0]['params']['clientAlgoId']
        previous_trigger=number(plan['stop']);previous_quantity=number(session['prepared']['quantity'])
        transitions=session.get('stop_transitions',[])
        for index,transition in enumerate(transitions):
            reason=transition.get('reason','break-even')
            if (reason not in ('break-even','trailing') or
                    (reason=='trailing' and plan['management'].get('trailing') is None) or
                    (reason=='break-even' and plan['management']['break_even_after_target'] is None)):
                raise ValueError('Stop geçişi onaylanan yönetim politikasıyla uyuşmuyor.')
            p=transition['proposal']['params'];q=number(p.get('quantity',0));trigger=number(p.get('triggerPrice',0))
            expected={'symbol':plan['symbol'],'side':'SELL' if side=='BUY' else 'BUY','positionSide':ps,
                      'type':'STOP_MARKET','quantity':str(q),'triggerPrice':str(trigger),'workingType':'MARK_PRICE',
                      'algoType':'CONDITIONAL','clientAlgoId':self._id(session,[reason,index])}
            if ps=='BOTH':expected['reduceOnly']='true'
            sign=1 if plan['direction']=='LONG' else -1
            if (transition['proposal']['path']!='/fapi/v1/algoOrder' or p!=expected or
                    not 0<q<=previous_quantity or trigger<=0 or sign*(trigger-previous_trigger)<0 or
                    transition.get('previous')!=previous or transition.get('state') not in ('PREPARED','VERIFIED','APPLIED') or
                    (index<len(transitions)-1 and transition['state']!='APPLIED')):
                raise ValueError('Stop geçiş zincirinin yön/miktar/fiyat/sahiplik kapsamı uyuşmuyor.')
            previous,previous_trigger,previous_quantity=p['clientAlgoId'],trigger,q
        if entry:
            if (row['state'] != 'EXECUTING'
                    or time.time() >= min(row['approval_until'], timestamp(row['plan']['expires_at']))):
                raise ValueError('V2 giriş yetkisi sona erdi veya kullanıldı.')
            if self.store.halt_reason() or self.store.unresolved_account_command():
                raise ValueError('Yeni girişler durdurulmuş veya hesap ayarı belirsiz.')
            if self.store.db.execute('SELECT 1 FROM control WHERE name=?',
                                     ('entry_revoked:'+session['entry_id'],)).fetchone():
                raise ValueError('V2 giriş yetkisi iptal edildi.')
        return row

    def _post(self, session, proposal, *, entry=False):
        params, path = proposal['params'], proposal['path']
        cid = params.get('newClientOrderId', params.get('clientAlgoId'))
        self._scope(session, entry=entry)
        existing = self.store.intent(cid)
        if existing:
            if existing['path'] != path or json.loads(existing['params']) != params:
                raise ValueError('V2 emir kimliği farklı parametreyle kullanılamaz.')
            if existing['state'] == 'REJECTED':
                raise ValueError('Reddedilen V2 emri aynı kimlikle tekrar gönderilmez.')
            query = {'clientAlgoId': cid} if path.endswith('algoOrder') else {
                'symbol': session['symbol'], 'origClientOrderId': cid}
            result = self.x.get(path, query)
        else:
            if not self.store.reserve(cid, path, params):
                raise ValueError('V2 emir kimliği başka yürütücüde ayrılmış.')
            try:
                if entry:
                    current = self._scope(session, entry=True)
                    snapshot = self._snapshot(session['symbol'],session['id'])
                    prepared = prepare_single(current['plan'], snapshot, self.limits)
                    if (prepared['state'] != 'READY'
                            or number(params['quantity']) > number(prepared['quantity'])):
                        raise ValueError('Gönderim öncesi koşul veya bütçe değişti.')
                    self._scope(session, entry=True)
                    self._joint_risk(snapshot)
                    self.book.mark_submitted(session['id'])
                result = self.x.request('POST', path, params)
            except ValueError:
                self.store.update(cid, 'REJECTED')
                raise
            except ExchangeError as exc:
                rejected = exc.delivery_status in ('NOT_SENT', 'REJECTED')
                self.store.update(cid, 'REJECTED' if rejected else 'UNKNOWN',
                                  {'code': exc.code, 'delivery_status': exc.delivery_status})
                self.store.halt('V2 emir yanıtı doğrulanmalı; otomatik tekrar yok.')
                raise
        self.store.update(cid, result.get('status', result.get('algoStatus', 'UNKNOWN')), result)
        return result

    def _cancel(self, path, params):
        body = json.dumps([path, params], sort_keys=True)
        cid = digest(body)
        with self.store.db:
            old = self.store.db.execute('SELECT * FROM v2_cancellations WHERE command_id=?', (cid,)).fetchone()
            if old:
                return  # The caller always queries terminal state after cancellation.
            self.store.db.execute('INSERT INTO v2_cancellations VALUES (?,?,?)', (cid, body, 'SUBMITTING'))
        try:
            self.x.request('DELETE', path, params)
        except ExchangeError:
            with self.store.db:
                self.store.db.execute("UPDATE v2_cancellations SET state='UNKNOWN' WHERE command_id=?", (cid,))
            raise
        with self.store.db:
            self.store.db.execute("UPDATE v2_cancellations SET state='ACKNOWLEDGED' WHERE command_id=?", (cid,))

    def open(self, plan_id, version, execute=False):
        row = self.service.show(plan_id, version)
        plan = row['plan']
        if row['state'] != 'AUTHORIZED':
            raise ValueError('V2 planı yetkili değil veya giriş hakkı kullanıldı.')
        if plan['schema_version'] != 2 or plan['execution']['strategy'] != 'SINGLE':
            raise ValueError('V2 yürütücüsü SINGLE girişini destekler.')
        if self.store.halt_reason() or self.store.unresolved_account_command():
            raise ValueError('Aktif oturum veya çözülmemiş durdurma/hesap ayarı var.')
        snapshot = self._snapshot(plan['symbol'])
        prepared = prepare_single(plan, snapshot, self.limits)
        if not execute or prepared['state'] != 'READY':
            if prepared['state']=='READY':
                prepared['portfolio_risk']=self._joint_risk(snapshot,[Exposure(**e) for e in prepared['exposures']])
            return prepared | {'executed': False}
        sid = 'v2-' + digest([plan_id, version, row['digest']])[:28]
        self.book.reserve(sid,self.service.owner,row['digest'],[Exposure(**e) for e in prepared['exposures']],snapshot,self.limits)
        entry_id = self.service.claim(plan_id, version, sid)
        proposal = prepared['entry']
        proposal['params']['newClientOrderId'] = entry_id
        session = {'id': sid, 'engine': 'v2', 'symbol': plan['symbol'], 'active': True,
                   'status': 'OPENING', 'entry_id': entry_id, 'account_ref': self.account_ref,
                   'started_ms': int(time.time()*1000)+getattr(self.x,'offset_ms',0), 'plan': plan,
                   'plan_ref': {'plan_id': plan_id, 'version': version, 'digest': row['digest']},
                   'prepared': prepared, 'protections': [], 'exits': []}
        for index, protection in enumerate(prepared['protections']):
            protection['params']['clientAlgoId'] = self._id(session, 'protection-'+str(index))
            session['protections'].append(protection)
        self._save(session)
        try:
            self.journal.register(entry_id, sid, plan['symbol'], proposal['params']['side'], prepared['quantity'])
            self._post(session, proposal, entry=True)
            return self.manage(sid, execute=True)
        except Exception:
            self.service.outcome(plan_id, version, 'NEEDS_REVIEW')
            self.store.halt('V2 oturum devralınmalı; yeni giriş gönderilmeyecek.')
            raise

    def _session(self, sid):
        matches = [s for s in self.store.sessions() if s['id'] == sid and s.get('engine') == 'v2']
        if len(matches) != 1:
            raise ValueError('Etkin V2 oturumu bulunamadı.')
        self._scope(matches[0])
        return matches[0]

    def _entry(self, s):
        result = self.x.get('/fapi/v1/order', {'symbol': s['symbol'], 'origClientOrderId': s['entry_id']})
        expected = effective_params(self.store,s['entry_id'])
        if (result.get('clientOrderId') != s['entry_id'] or result.get('symbol') != s['symbol']
                or result.get('side') != expected['side']
                or result.get('positionSide') != expected['positionSide']
                or result.get('type')!=expected['type']or number(result['origQty']) != number(expected['quantity'])
                or(expected['type']=='LIMIT'and number(result['price'])!=number(expected['price']))):
            raise ValueError('Borsa giriş emri kayıtlı niyetle uyuşmuyor.')
        saved=self.store.intent(s['entry_id']);previous=json.loads(saved['response'])if saved and saved['response']else{}
        if previous.get('orderId')is not None and str(previous['orderId'])!=str(result.get('orderId')):
            raise ValueError('Giriş istemci kimliği başka borsa emri için yeniden kullanılmış.')
        status = result['status']
        normalized = 'EXPIRED' if status == 'EXPIRED_IN_MATCH' else status
        self.journal.observe(s['entry_id'], digest(result), status=normalized,
                             cumulative_filled=result['executedQty'],
                             observed_ms=int(result.get('updateTime', time.time()*1000)))
        self.store.update(s['entry_id'], status, result)
        return result

    def _owned(self, s, entry, algos):
        observed=time.time()
        if time.time()*1000-s['started_ms'] > 6*86400000:
            raise ValueError('V2 otomatik devralma geçmiş sınırı aşıldı.')
        mode = self.x.get('/fapi/v1/positionSide/dual')['dualSidePosition']
        if mode != (s['plan']['position_mode'] == 'hedge'):
            raise ValueError('V2 hesap modu değişti.')
        settings = self.x.get('/fapi/v1/symbolConfig', {'symbol': s['symbol']})
        setting = next((r for r in settings if r['symbol'] == s['symbol']), None)
        if (setting is None or int(setting['leverage']) != s['plan']['execution']['leverage']
                or setting['marginType'] != s['plan']['execution']['margin_mode']):
            raise ValueError('V2 kaldıraç veya teminat modu değişti.')
        known = {str(entry['orderId'])}
        for algo in algos.values():
            if algo.get('actualOrderId') not in (None, '', '0', 0):
                known.add(str(algo['actualOrderId']))
        for proposal in s['exits']:
            result = self.x.get('/fapi/v1/order', {'symbol': s['symbol'],
                                'origClientOrderId': proposal['params']['newClientOrderId']})
            params = effective_params(self.store,proposal['params']['newClientOrderId'])
            if (result.get('clientOrderId') != params['newClientOrderId']
                    or result.get('symbol') != s['symbol'] or result.get('side') != params['side']
                    or result.get('positionSide') != params['positionSide']
                    or number(result['origQty']) != number(params['quantity'])):
                raise ValueError('V2 kapanış emri kayıtlı niyetle uyuşmuyor.')
            known.add(str(result['orderId']))
        trades = account_trades(self.x, s['symbol'], s['started_ms'])
        if any(str(t['orderId']) not in known for t in trades):
            raise ValueError('V2 gerçekleşme geçmişi eksik veya yabancı işlem içeriyor.')
        expected = sum((number(t['qty'])*(1 if t['side'] == 'BUY' else -1) for t in trades), number(0))
        ps = s['prepared']['entry']['params']['positionSide']
        positions = self.x.get('/fapi/v3/positionRisk')
        multi=len(self.store.sessions())>1
        if not multi and any(number(p['positionAmt']) and (p['symbol'] != s['symbol'] or p['positionSide'] != ps) for p in positions):
            raise ValueError('V2 oturumu dışında pozisyon var.')
        amount = sum((number(p['positionAmt']) for p in positions if p['symbol'] == s['symbol'] and p['positionSide'] == ps), number(0))
        if amount != expected or abs(amount) > number(entry['executedQty']):
            raise ValueError('V2 pozisyon miktarı sahip olunan gerçekleşmelerle uyuşmuyor.')
        direction = 1 if s['plan']['direction'] == 'LONG' else -1
        if amount*direction < 0:
            raise ValueError('V2 pozisyon yönü değişti.')
        own_normal = {s['entry_id']} | {p['params']['newClientOrderId'] for p in s['exits']}
        own_algo = {p['params']['clientAlgoId'] for p in s['protections']}
        own_algo.update(t['proposal']['params']['clientAlgoId'] for t in s.get('stop_transitions', []))
        if multi:
            from .account_ownership import AccountOwnership
            AccountOwnership(self).verify(positions=positions)
            if not 0<=time.time()-observed<=self.limits.max_age_seconds:
                raise ValueError('Çoklu SINGLE sahiplik görünümü eskidi.')
            return amount
        if any(o.get('symbol')!=s['symbol'] or (o['clientOrderId'] not in own_normal and str(o.get('orderId')) not in known)
               for o in self.x.get('/fapi/v1/openOrders')):
            raise ValueError('Yabancı açık normal emir var.')
        if any(o.get('symbol')!=s['symbol'] or o['clientAlgoId'] not in own_algo for o in self.x.get('/fapi/v1/openAlgoOrders')):
            raise ValueError('Yabancı açık koşullu emir var.')
        if not 0<=time.time()-observed<=self.limits.max_age_seconds:
            raise ValueError('SINGLE sahiplik görünümü eskidi.')
        return amount

    def manage(self, sid, execute=False):
        try:
            return self._manage(sid, execute)
        except (ValueError, ExchangeError):
            self.store.halt('V2 yönetim kontrolü başarısız; oturum uzlaştırılmalı.')
            raise

    def _staged_target(self, s, entry, amount, mark, algos, execute):
        if len(s['plan']['targets']) == 1:
            return None
        info = next(i for i in self.x.get('/fapi/v1/exchangeInfo')['symbols'] if i['symbol'] == s['symbol'])
        filters = {f['filterType']: f for f in info['filters']}
        rules = {'lot': filters['LOT_SIZE'], 'market': filters.get('MARKET_LOT_SIZE', filters['LOT_SIZE'])}
        stages = split_targets(entry['executedQty'], s['plan']['targets'], rules)
        sign = 1 if s['plan']['direction'] == 'LONG' else -1
        for stage in stages[:-1]:
            attempts = [p for p in s['exits'] if p.get('stage_index') == stage['index']]
            filled = number(0)
            for previous in attempts:
                cid = previous['params']['newClientOrderId']
                result = self.x.get('/fapi/v1/order', {'symbol': s['symbol'], 'origClientOrderId': cid})
                if result['status'] not in NORMAL_TERMINAL:
                    if not execute:
                        return {'state': 'TARGET_CANCEL_REQUIRED', 'stage': stage['index'], 'session_id': s['id'], 'executed': False}
                    self._cancel('/fapi/v1/order', {'symbol': s['symbol'], 'origClientOrderId': cid})
                    result = self.x.get('/fapi/v1/order', {'symbol': s['symbol'], 'origClientOrderId': cid})
                    if result['status'] not in NORMAL_TERMINAL:
                        raise ValueError('Kademeli hedef kalanı terminal iptal bekliyor.')
                filled += number(result['executedQty'])
            required = number(stage['quantity'])-filled
            if required < 0:
                raise ValueError('Hedef gerçekleşmesi onaylanan payı aşıyor.')
            if required == 0:
                continue
            if not attempts and sign*(number(mark['markPrice'])-number(stage['price'])) < 0:
                return None
            if not execute:
                return {'state': 'TARGET_EXIT_REQUIRED', 'stage': stage['index'], 'session_id': s['id'], 'executed': False}
            owned = self._owned(s, self._entry(s), algos)
            if required > abs(owned):
                raise ValueError('Hedef miktarı sahip olunan kalan pozisyonu aşıyor.')
            params = {'symbol': s['symbol'], 'side': 'SELL' if sign == 1 else 'BUY',
                      'positionSide': s['prepared']['entry']['params']['positionSide'],
                      'type': 'MARKET', 'quantity': str(required),
                      'newClientOrderId': self._id(s, ['target', stage['index'], len(attempts)])}
            if s['plan']['position_mode'] == 'one-way':
                params['reduceOnly'] = 'true'
            proposal = validate_order(params, info, s['plan']['position_mode'], 'REDUCE',
                                      mark['markPrice'], int(time.time()*1000)+getattr(self.x, 'offset_ms', 0))
            proposal['stage_index'] = stage['index']
            s['exits'].append(proposal)
            self._save(s)
            self._post(s, proposal)
            return {'state': 'TARGET_EXIT_SUBMITTED', 'stage': stage['index'], 'session_id': s['id'], 'executed': True}
        return None

    def _break_even(self, s, entry, amount, mark, algos, execute):
        after = s['plan']['management']['break_even_after_target']
        if after is None:
            return None
        info = next(i for i in self.x.get('/fapi/v1/exchangeInfo')['symbols'] if i['symbol'] == s['symbol'])
        filters = {f['filterType']: f for f in info['filters']}
        stages = split_targets(entry['executedQty'], s['plan']['targets'],
                               {'lot': filters['LOT_SIZE'], 'market': filters.get('MARKET_LOT_SIZE', filters['LOT_SIZE'])})
        for stage in stages[:after]:
            results = [self.x.get('/fapi/v1/order', {'symbol': s['symbol'], 'origClientOrderId': p['params']['newClientOrderId']})
                       for p in s['exits'] if p.get('stage_index') == stage['index']]
            if any(r['status'] not in NORMAL_TERMINAL for r in results):
                return None
            if sum((number(r['executedQty']) for r in results), number(0)) != number(stage['quantity']):
                return None
        average = number(entry.get('avgPrice', 0))
        if average <= 0:
            raise ValueError('Girişe stop için gerçek ortalama gerçekleşme fiyatı gerekli.')
        tick = number(filters['PRICE_FILTER']['tickSize'])
        sign = 1 if s['plan']['direction'] == 'LONG' else -1
        trigger = (average/tick).to_integral_value(rounding=ROUND_CEILING if sign == 1 else ROUND_FLOOR)*tick
        return self._move_quantity_stop(s, entry, amount, mark, algos, execute, trigger, info, 'break-even')

    def _move_quantity_stop(self, s, entry, amount, mark, algos, execute, trigger, info, reason):
        transitions = s.setdefault('stop_transitions', [])
        sign = 1 if s['plan']['direction'] == 'LONG' else -1
        if transitions and transitions[-1]['state'] in ('VERIFIED', 'APPLIED'):
            current = number(transitions[-1]['proposal']['params']['triggerPrice'])
        else:
            current = number(s['plan']['stop'])
        trigger = max(current, trigger) if sign == 1 else min(current, trigger)
        if transitions and transitions[-1]['state'] == 'APPLIED' and number(transitions[-1]['proposal']['params']['quantity']) == abs(amount):
            if number(transitions[-1]['proposal']['params']['triggerPrice']) == trigger:
                return None
        if not execute:
            return {'state': 'STOP_MOVE_REQUIRED', 'session_id': s['id'], 'executed': False}
        owned = self._owned(s, self._entry(s), algos)
        if owned != amount:
            raise ValueError('Stop geçişi sırasında kalan pozisyon değişti.')
        if sign*(number(mark['markPrice'])-trigger) <= 0:
            params = {'symbol': s['symbol'], 'side': 'SELL' if sign == 1 else 'BUY',
                      'positionSide': s['prepared']['entry']['params']['positionSide'],
                      'type': 'MARKET', 'quantity': str(abs(amount)),
                      'newClientOrderId': self._id(s, [reason+'-close', len(s['exits'])])}
            if s['plan']['position_mode'] == 'one-way':params['reduceOnly']='true'
            proposal = validate_order(params, info, s['plan']['position_mode'], 'REDUCE', mark['markPrice'], int(time.time()*1000))
            s['exits'].append(proposal);self._save(s);self._post(s, proposal)
            return {'state': 'EXIT_SUBMITTED', 'session_id': s['id'], 'executed': True}
        if not transitions or transitions[-1]['state'] == 'APPLIED':
            previous = transitions[-1]['proposal']['params']['clientAlgoId'] if transitions else s['protections'][0]['params']['clientAlgoId']
            params = {'symbol': s['symbol'], 'side': 'SELL' if sign == 1 else 'BUY',
                      'positionSide': s['prepared']['entry']['params']['positionSide'],
                      'type': 'STOP_MARKET', 'quantity': str(abs(amount)), 'triggerPrice': str(trigger),
                      'workingType': 'MARK_PRICE', 'clientAlgoId': self._id(s, [reason, len(transitions)])}
            if s['plan']['position_mode'] == 'one-way':params['reduceOnly']='true'
            proposal = validate_order(params, info, s['plan']['position_mode'], 'REDUCE', mark['markPrice'], int(time.time()*1000))
            transitions.append({'proposal': proposal, 'previous': previous, 'state': 'PREPARED', 'reason': reason})
            self._save(s)
        transition = transitions[-1]
        params = transition['proposal']['params']
        if number(params['triggerPrice']) != trigger or number(params['quantity']) != abs(amount):
            raise ValueError('Bekleyen stop geçişi güncel fiyat/miktarla uyuşmuyor.')
        self._post(s, transition['proposal'])
        actual = self.x.get('/fapi/v1/algoOrder', {'clientAlgoId': params['clientAlgoId']})
        self._verify_quantity_stop(params, actual)
        algos[params['clientAlgoId']] = actual
        if self._owned(s, self._entry(s), algos) != amount:
            raise ValueError('Yeni stop doğrulanırken pozisyon değişti; eski stop korunuyor.')
        transition['state'] = 'VERIFIED';self._save(s)
        # New stop is proven active before retiring the previous stop.
        self._cancel('/fapi/v1/algoOrder', {'clientAlgoId': transition['previous']})
        previous = self.x.get('/fapi/v1/algoOrder', {'clientAlgoId': transition['previous']})
        if previous.get('algoStatus') not in ALGO_TERMINAL:
            raise ValueError('Önceki stop iptali terminal değil.')
        transition['state'] = 'APPLIED';self._save(s)
        return {'state': 'STOP_MOVED', 'session_id': s['id'], 'executed': True, 'trigger_price': str(trigger)}

    def _trailing(self, s, entry, amount, mark, algos, execute):
        policy = s['plan']['management'].get('trailing')
        if policy is None:
            return None
        from .trailing import advance_trailing
        info = next(i for i in self.x.get('/fapi/v1/exchangeInfo')['symbols'] if i['symbol'] == s['symbol'])
        tick = next(f['tickSize'] for f in info['filters'] if f['filterType'] == 'PRICE_FILTER')
        transitions = s.get('stop_transitions', [])
        current = number(transitions[-1]['proposal']['params']['triggerPrice']) if transitions else number(s['plan']['stop'])
        state, trigger = advance_trailing(policy, s['plan']['direction'], mark['markPrice'], tick,
                                          current, s.get('trailing_state'))
        s['trailing_state'] = state
        self._save(s)
        resize = transitions and number(transitions[-1]['proposal']['params']['quantity']) != abs(amount)
        if trigger is None and not resize:
            return None
        return self._move_quantity_stop(s, entry, amount, mark, algos, execute,
                                         current if trigger is None else trigger, info, 'trailing')

    def _verify_quantity_stop(self, params, result):
        if (result.get('algoStatus') not in ALGO_ACTIVE
                or any(result.get(k) != params[k] for k in ('clientAlgoId', 'symbol', 'side', 'positionSide', 'workingType'))
                or result.get('orderType', result.get('type')) != 'STOP_MARKET'
                or number(result.get('triggerPrice', 0)) != number(params['triggerPrice'])
                or number(result.get('quantity', 0)) != number(params['quantity'])
                or str(result.get('closePosition', False)).lower() != 'false'
                or ('reduceOnly' in params and str(result.get('reduceOnly')).lower() != 'true')):
            raise ValueError('Miktarlı girişe stop borsada doğrulanamadı.')

    def _manage(self, sid, execute=False):
        s = self._session(sid)
        self.x.sync_time()
        saved_entry = next((r for r in self.store.intents() if r['client_id'] == s['entry_id']), None)
        if saved_entry is None or saved_entry['state'] == 'REJECTED':
            # A definite local rejection/no-send can be retired only after a new
            # independently read flat account snapshot. UNKNOWN is never treated so.
            self._snapshot(s['symbol'],s['id'])
            self.journal.register(s['entry_id'], sid, s['symbol'],
                                  s['prepared']['entry']['params']['side'], s['prepared']['quantity'])
            self.journal.observe(s['entry_id'], 'definitely-unsent', status='REJECTED',
                                 cumulative_filled='0', observed_ms=int(time.time()*1000))
            s.update(status='CLOSED', active=False)
            if s['prepared'].get('exposures'):
                self.book.close_session(s,flat_verified=True,orders_terminal=True)
            else:self._save(s)
            return {'state': self.service.show(s['plan_ref']['plan_id'], s['plan_ref']['version'])['state'],
                    'session_id': sid, 'executed': False, 'entry_rejected': True}
        entry = self._entry(s)
        if entry['status'] not in NORMAL_TERMINAL:
            if s['prepared']['entry']['params']['type'] == 'LIMIT' and number(entry['executedQty']) == 0:
                row = self._scope(s)
                mark = self.x.get('/fapi/v1/premiumIndex', {'symbol': s['symbol']})
                fresh(mark, s['symbol'], int(time.time()*1000)+getattr(self.x, 'offset_ms', 0),
                      self.limits.max_age_seconds)
                sign = 1 if s['plan']['direction'] == 'LONG' else -1
                price = number(mark['markPrice'])
                in_range = (sign*(price-number(s['plan']['stop'])) > 0
                            and sign*(number(s['plan']['targets'][-1]['price'])-price) > 0)
                revoked = self.store.db.execute('SELECT 1 FROM control WHERE name=?',
                                                ('entry_revoked:'+s['entry_id'],)).fetchone()
                if in_range and not revoked and time.time() < min(row['approval_until'], timestamp(s['plan']['expires_at'])):
                    # Persisted entry owns the reserved budget; never place another entry.
                    self._owned(s, entry, {})
                    return {'state': 'ENTRY_PENDING', 'executed': execute, 'session_id': sid}
            if not execute:
                return {'state': 'ENTRY_CANCEL_REQUIRED', 'executed': False, 'session_id': sid}
            self._cancel('/fapi/v1/order', {'symbol': s['symbol'], 'origClientOrderId': s['entry_id']})
            entry = self._entry(s)
            if entry['status'] not in NORMAL_TERMINAL:
                raise ValueError('V2 giriş kalanı terminal iptal bekliyor.')
        algos = {}
        all_protections = s['protections'] + [t['proposal'] for t in s.get('stop_transitions', [])]
        for proposal in all_protections:
            cid = proposal['params']['clientAlgoId']
            saved = next((r for r in self.store.intents() if r['client_id'] == cid), None)
            if saved:
                if saved['state'] == 'REJECTED':
                    raise ValueError('V2 koruma reddedilmiş; otomatik yeniden gönderilmez.')
                algos[cid] = self.x.get('/fapi/v1/algoOrder', {'clientAlgoId': cid})
                params = proposal['params']
                result = algos[cid]
                if any(result.get(key) != params[key] for key in ('clientAlgoId', 'symbol', 'side', 'positionSide')):
                    raise ValueError('V2 koşullu emir kimliği kayıtlı niyetle uyuşmuyor.')
        amount = self._owned(s, entry, algos)
        if amount == 0:
            for p in s['exits']:
                cid=p['params']['newClientOrderId']
                actual=self.x.get('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':cid})
                if actual['status'] not in NORMAL_TERMINAL:
                    if not execute:return {'state':'CLEANUP_REQUIRED','session_id':sid,'executed':False}
                    self._cancel('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':cid})
                    if self.x.get('/fapi/v1/order',{'symbol':s['symbol'],'origClientOrderId':cid})['status'] not in NORMAL_TERMINAL:
                        raise ValueError('SINGLE kapanış emri kalanı terminal değil; rezerv korunuyor.')
            for cid, algo in algos.items():
                if algo.get('algoStatus') not in ALGO_TERMINAL:
                    if not execute:
                        return {'state': 'CLEANUP_REQUIRED', 'executed': False, 'session_id': sid}
                    self._cancel('/fapi/v1/algoOrder', {'clientAlgoId': cid})
                    if self.x.get('/fapi/v1/algoOrder', {'clientAlgoId': cid}).get('algoStatus') not in ALGO_TERMINAL:
                        raise ValueError('V2 koruma iptali terminal değil.')
            # Re-read after cancellations to detect late fills before closing state.
            if self._owned(s, self._entry(s), algos) != 0:
                raise ValueError('V2 temizleme sırasında pozisyon değişti.')
            s.update(status='CLOSED', active=False)
            if s['prepared'].get('exposures'):
                self.book.close_session(s,flat_verified=True,orders_terminal=True)
            else:self._save(s)
            state = self.service.show(s['plan_ref']['plan_id'], s['plan_ref']['version'])['state']
            return {'state': state, 'executed': execute, 'session_id': sid}
        mark = self.x.get('/fapi/v1/premiumIndex', {'symbol': s['symbol']})
        now_ms = int(time.time()*1000)+getattr(self.x, 'offset_ms', 0)
        fresh(mark, s['symbol'], now_ms, self.limits.max_age_seconds)
        sign = 1 if s['plan']['direction'] == 'LONG' else -1
        price = number(mark['markPrice'])
        applied = [t for t in s.get('stop_transitions', []) if t['state'] in ('VERIFIED', 'APPLIED')]
        effective_stop = applied[-1]['proposal']['params']['triggerPrice'] if applied else s['plan']['stop']
        crossed = sign*(price-number(effective_stop)) <= 0 or sign*(price-number(s['plan']['targets'][-1]['price'])) >= 0
        if crossed:
            if not execute:
                return {'state': 'EXIT_REQUIRED', 'session_id': sid, 'executed': False}
            for previous in s['exits']:
                cid = previous['params']['newClientOrderId']
                result = self.x.get('/fapi/v1/order', {'symbol': s['symbol'], 'origClientOrderId': cid})
                if result['status'] not in NORMAL_TERMINAL:
                    self._cancel('/fapi/v1/order', {'symbol': s['symbol'], 'origClientOrderId': cid})
                    if self.x.get('/fapi/v1/order', {'symbol': s['symbol'], 'origClientOrderId': cid})['status'] not in NORMAL_TERMINAL:
                        raise ValueError('V2 önceki kapanış kalanı iptal bekliyor.')
            amount = self._owned(s, self._entry(s), algos)
            if amount == 0:
                return {'state': 'CLEANUP_REQUIRED', 'session_id': sid, 'executed': True}
            params = {'symbol': s['symbol'], 'side': 'SELL' if sign == 1 else 'BUY',
                      'positionSide': s['prepared']['entry']['params']['positionSide'],
                      'type': 'MARKET', 'quantity': str(abs(amount)),
                      'newClientOrderId': self._id(s, 'close-'+str(len(s['exits'])))}
            if s['plan']['position_mode'] == 'one-way':
                params['reduceOnly'] = 'true'
            info = next(i for i in self.x.get('/fapi/v1/exchangeInfo')['symbols'] if i['symbol'] == s['symbol'])
            proposal = validate_order(params, info, s['plan']['position_mode'], 'REDUCE', price, now_ms)
            s['exits'].append(proposal)
            self._save(s)
            self._post(s, proposal)
            return {'state': 'EXIT_SUBMITTED', 'session_id': sid, 'executed': True}
        missing = []
        for proposal in s['protections']:
            if proposal['params']['type'] == 'STOP_MARKET' and applied:
                continue
            cid = proposal['params']['clientAlgoId']
            result = algos.get(cid)
            if result is None:
                if execute:
                    self._owned(s, self._entry(s), algos)
                    result = self._post(s, proposal)
                    # A successful HTTP POST is not proof of an active protection.
                    result = self.x.get('/fapi/v1/algoOrder', {'clientAlgoId': cid})
                    algos[cid] = result
                else:
                    missing.append(cid)
                    continue
            params = proposal['params']
            if (result.get('algoStatus') not in ALGO_ACTIVE or result.get('clientAlgoId') != cid
                    or result.get('symbol') != params['symbol'] or result.get('side') != params['side']
                    or result.get('positionSide') != params['positionSide']
                    or result.get('orderType', result.get('type')) != params['type']
                    or str(result.get('closePosition')).lower() != 'true'
                    or result.get('workingType') != 'MARK_PRICE'
                    or number(result.get('triggerPrice', 0)) != number(params['triggerPrice'])):
                raise ValueError('V2 koruma etkin veya planla eşleşir durumda değil.')
        if applied:
            self._verify_quantity_stop(applied[-1]['proposal']['params'], algos[applied[-1]['proposal']['params']['clientAlgoId']])
        if missing:
            return {'state': 'PROTECTION_REQUIRED', 'missing': missing, 'executed': False, 'session_id': sid}
        s['status'] = 'PROTECTED'
        self._save(s)
        self.service.outcome(s['plan_ref']['plan_id'], s['plan_ref']['version'], 'MANAGING')
        transitions = s.get('stop_transitions', [])
        if transitions and transitions[-1]['state'] != 'APPLIED':
            pending = transitions[-1]
            info = next(i for i in self.x.get('/fapi/v1/exchangeInfo')['symbols'] if i['symbol'] == s['symbol'])
            return self._move_quantity_stop(s, entry, amount, mark, algos, execute,
                    number(pending['proposal']['params']['triggerPrice']), info, pending.get('reason', 'break-even'))
        moved = self._break_even(s, entry, amount, mark, algos, execute)
        if moved is not None:
            return moved
        trailed = self._trailing(s, entry, amount, mark, algos, execute)
        if trailed is not None:
            return trailed
        stage = self._staged_target(s, entry, amount, mark, algos, execute)
        if stage is not None:
            return stage
        return {'state': 'MANAGING', 'status': 'protected', 'executed': execute, 'session_id': sid,
                'quantity': str(abs(amount)), 'protections_verified': len(s['protections'])}
