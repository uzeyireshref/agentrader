"""Kalıcı sahiplik kanıtıyla tek demo LONG pozisyonu izleme ve koruma onarımı."""
from .history import account_trades
import time
from decimal import Decimal, ROUND_FLOOR
from uuid import uuid4

from .exchange import ExchangeError
from .execution import DurableExchange, TERMINAL, reconcile, resolve_absent_flat
from .positions import position_plan
from .management import StagedManagement, split_targets
from .plans import digest, validate_plan


def identity():
    return 'agt-' + uuid4().hex[:28]


class OwnershipError(ValueError):
    pass


class Watchdog(StagedManagement):
    def __init__(self, exchange, store, limits=None):
        self.x, self.store = exchange, store
        self.engine = DurableExchange(exchange, store) if limits is None else DurableExchange(exchange, store, limits)

    def save(self, session):
        self.store.save_session(session)

    def session(self):
        sessions = self.store.sessions()
        if len(sessions) != 1:
            raise OwnershipError('Tam bir aktif yönetilen oturum gerekli.')
        if sessions[0].get('engine') in ('v2','grid-v2'):
            raise OwnershipError('V2 oturumunu plans manage SESSION_ID ile devralın; eski LONG watchdog kullanılamaz.')
        return sessions[0]

    def order(self, session, cid):
        return self.x.get('/fapi/v1/order', {'symbol': session['symbol'], 'origClientOrderId': cid})

    def algo(self, cid):
        return self.x.get('/fapi/v1/algoOrder', {'clientAlgoId': cid})

    def snapshot(self, s):
        """Miktar eşleşmesi tek başına sahiplik sayılmaz: bütün fill'ler eşleşmeli."""
        if self.x.get('/fapi/v1/positionSide/dual')['dualSidePosition']:
            raise OwnershipError('Hesap modu değişti.')
        if time.time() * 1000 - s['started_ms'] > 6 * 86400000:
            raise OwnershipError('Oturum 6 günlük otomatik devralma sınırını aştı.')
        known = set()
        entry = self.order(s, s['entry_id'])
        known.add(str(entry['orderId']))
        exit_orders = {}
        stage_ids = self.stage_exit_ids(s)
        for params in s['exits']:
            # Yanıtı belirsiz bir çıkış yeniden gönderilmez.
            cid = params['newClientOrderId']
            if cid in stage_ids:
                saved = next((r for r in self.store.intents() if r['client_id'] == cid), None)
                if saved is None or saved['state'] == 'REJECTED':
                    exit_orders[cid] = {'status': 'NOT_SUBMITTED' if saved is None else 'REJECTED', 'executedQty': '0'}
                    continue
            result = self.order(s, params['newClientOrderId'])
            exit_orders[cid] = result
            known.add(str(result['orderId']))
            if result['status'] not in TERMINAL and cid not in stage_ids:
                raise OwnershipError('Çıkış emri henüz sonlanmadı.')
        algos = {}
        for protection in s['protections']:
            cid = protection['clientAlgoId']
            # Henüz gönderilmemiş kalıcı onarım niyeti varsa güvenle ilk gönderim yapılabilir.
            saved = next((row for row in self.store.intents() if row['client_id'] == cid), None)
            if saved is None:
                continue
            if saved['state'] == 'REJECTED':
                algos[cid] = {'algoStatus': 'REJECTED'}
                continue
            if saved['state'] == 'RESOLVED_FLAT':
                algos[cid] = {'algoStatus': 'EXPIRED'}
                continue
            try:
                result = self.algo(cid)
            except ExchangeError as exc:
                result = resolve_absent_flat(self.x, self.store, saved, exc)
            algos[cid] = result
            if result.get('actualOrderId') not in (None, '', '0', 0):
                known.add(str(result['actualOrderId']))
        trades = account_trades(self.x, s['symbol'], s['started_ms'])
        if any(str(t['orderId']) not in known for t in trades):
            raise OwnershipError('Oturum başladıktan sonra manuel/başka bot işlemi saptandı.')
        expected = sum((Decimal(t['qty']) * (1 if t['side'] == 'BUY' else -1) for t in trades), Decimal(0))
        rows = self.x.get('/fapi/v3/positionRisk')
        if any(Decimal(p['positionAmt']) != 0 and p['symbol'] != s['symbol'] for p in rows):
            raise OwnershipError('Hesapta başka sembolde pozisyon var.')
        amount = sum((Decimal(p['positionAmt']) for p in rows if p['symbol'] == s['symbol']), Decimal(0))
        if expected != amount or amount < 0 or amount > Decimal(s['plan']['quantity']):
            raise OwnershipError('Borsa pozisyonu kayıtlı gerçekleşmelerle uyuşmuyor.')
        own_normal = {s['entry_id']} | {p['newClientOrderId'] for p in s['exits']}
        if any(o['clientOrderId'] not in own_normal for o in self.x.get('/fapi/v1/openOrders')):
            raise OwnershipError('Bilinmeyen açık emir var.')
        own_algo = {p['clientAlgoId'] for p in s['protections']}
        if any(o['clientAlgoId'] not in own_algo for o in self.x.get('/fapi/v1/openAlgoOrders')):
            raise OwnershipError('Bilinmeyen açık koruyucu emir var.')
        snapshot = {'amount': amount, 'entry': entry, 'algos': algos, 'exit_orders': exit_orders}
        self.verify_plan_scope(s, snapshot)
        return snapshot

    def verify_plan_scope(self, session, snapshot):
        ref = session.get('plan_ref')
        if not ref:
            return
        import json
        row = self.store.db.execute('SELECT body,digest,action_id,state FROM plan_versions WHERE plan_id=? AND version=?',
                                    (ref['plan_id'], ref['version'])).fetchone()
        if not row:
            raise OwnershipError('Yönetilen oturumun yetkili plan kaydı bulunamadı.')
        approved = validate_plan(json.loads(row['body']))
        plan = session['plan']
        if (digest(approved) != ref['digest'] or row['digest'] != ref['digest']
                or row['action_id'] != session['entry_id'] or row['state'] not in ('EXECUTING', 'MANAGING', 'NEEDS_REVIEW')
                or approved['targets'] != plan.get('targets') or approved['management'] != plan.get('management')
                or approved['stop'] != plan.get('initial_stop') or approved['targets'][-1]['price'] != plan['target']):
            raise OwnershipError('Pozisyon yönetimi onaylanan plan kapsamıyla uyuşmuyor.')
        target_management = session.get('target_management')
        if target_management:
            actual = Decimal(snapshot['entry']['executedQty'])
            expected_stages = split_targets(actual, approved['targets'], plan['lot_rules'])
            stages = target_management['targets']
            if Decimal(target_management['entry_quantity']) != actual or len(stages) != len(expected_stages):
                raise OwnershipError('Hedef dağılımı onaylı plan/giriş gerçekleşmesiyle uyuşmuyor.')
            exits = {p['newClientOrderId']: p for p in session['exits']}
            for stage, expected_stage in zip(stages, expected_stages):
                if any(stage[key] != expected_stage[key] for key in ('index', 'price', 'quantity')):
                    raise OwnershipError('Hedef miktarı/seviyesi onaylı pay dağılımıyla uyuşmuyor.')
                allocated = Decimal(0)
                for cid in stage['attempts']:
                    params, response = exits[cid], snapshot['exit_orders'][cid]
                    if (params['symbol'] != session['symbol'] or params['side'] != 'SELL'
                            or params.get('positionSide') != 'BOTH' or params['type'] != 'MARKET'
                            or params.get('reduceOnly') != 'true'):
                        raise OwnershipError('Hedef eylemi izinli reduce-only çıkış değil.')
                    filled = Decimal(response['executedQty'])
                    requested = Decimal(params['quantity'])
                    if not 0 <= filled <= requested:
                        raise OwnershipError('Hedef gerçekleşme miktarı istekle uyuşmuyor.')
                    allocated += filled
                    if response['status'] in ('NOT_SUBMITTED', 'NEW', 'PARTIALLY_FILLED'):
                        allocated += requested - filled
                if allocated > Decimal(stage['quantity']):
                    raise OwnershipError('Hedef için ayrılan miktar izinli payı aşıyor.')
        transition = session.get('stop_transition')
        if not transition:
            if Decimal(plan['stop']) != Decimal(approved['stop']):
                raise OwnershipError('Onaylanmamış stop değişimi.')
            return
        index = approved['management']['break_even_after_target']
        stages = session.get('target_management', {}).get('targets', [])
        if index is None or len(stages) < index:
            raise OwnershipError('Girişe stop taşıma yetkisi veya hedef gerçekleşmesi yok.')
        stage = stages[index - 1]
        filled = sum((Decimal(snapshot['exit_orders'][cid]['executedQty']) for cid in stage['attempts']), Decimal(0))
        tick = Decimal(plan['lot_rules']['tick'])
        expected = (Decimal(snapshot['entry']['avgPrice']) / tick).to_integral_value(rounding=ROUND_FLOOR) * tick
        if (stage['status'] != 'COMPLETED' or filled != Decimal(stage['quantity'])
                or Decimal(transition['from']) != Decimal(approved['stop'])
                or Decimal(transition['to']) != expected or Decimal(plan['stop']) != expected):
            raise OwnershipError('Stop geçişi yetkili hedef gerçekleşmesi veya giriş fiyatıyla uyuşmuyor.')

    def valid_protection(self, s, params, response):
        close_all = str(response.get('closePosition')).lower() == 'true'
        transition = s.get('stop_transition')
        management = s.get('target_management', {})
        remaining = Decimal(management.get('entry_quantity', s['plan']['quantity'])) - sum(
            (Decimal(t['quantity']) for t in management.get('targets', []) if t['status'] == 'COMPLETED'), Decimal(0))
        quantity_stop = (params['type'] == 'STOP_MARKET' and transition
                         and Decimal(params['triggerPrice']) == Decimal(transition['to'])
                         and params.get('reduceOnly') == 'true'
                         and str(response.get('reduceOnly')).lower() == 'true'
                         and not close_all and Decimal(params.get('quantity', '0')) > 0
                         and Decimal(response.get('quantity', '0')) == Decimal(params['quantity'])
                         and Decimal(params['quantity']) >= remaining
                         and Decimal(params['quantity']) <= Decimal(s['plan']['quantity']))
        return (response.get('algoStatus') == 'NEW'
                and response.get('symbol') == s['symbol']
                and response.get('side') == 'SELL'
                and response.get('positionSide') == 'BOTH'
                and response.get('orderType') == params['type']
                and response.get('workingType') == 'MARK_PRICE'
                and (close_all or quantity_stop)
                and Decimal(response['triggerPrice']) == Decimal(params['triggerPrice'])
                and Decimal(params['triggerPrice']) == Decimal(s['plan']['stop' if params['type'] == 'STOP_MARKET' else 'target']))

    def send_protection(self, params):
        try:
            self.engine.request('POST', '/fapi/v1/algoOrder', params)
        except ExchangeError:
            # Sunucu kabul etmiş olabilir: aynı kimlikle sorgula, yeni emir üretme.
            saved = next(r for r in self.store.intents() if r['client_id'] == params['clientAlgoId'])
            if saved['state'] == 'REJECTED':
                raise
        return self.algo(params['clientAlgoId'])

    def ensure_protection(self, s, snap, kind):
        candidates = [p for p in s['protections'] if p['type'] == kind]
        for p in candidates:
            result = snap['algos'].get(p['clientAlgoId'])
            if result and self.valid_protection(s, p, result):
                if kind == 'STOP_MARKET' and s.get('stop_transition'):
                    self.retire_previous_stop(s, self.snapshot(s))
                return result
            if result and result['algoStatus'] not in TERMINAL:
                transition = s.get('stop_transition')
                previous_stop = (kind == 'STOP_MARKET' and transition
                                 and Decimal(p['triggerPrice']) == Decimal(transition['from']))
                if not previous_stop:
                    raise ExchangeError('Koruyucu emir belirsiz/geçersiz; yeni emir üretilmedi.')
        # Çökme, kaydın yazılması ile gönderim arasındaysa aynı niyeti tamamla.
        pending = next((p for p in candidates if p['clientAlgoId'] not in snap['algos']
                        and Decimal(p['triggerPrice']) == Decimal(s['plan']['stop' if kind == 'STOP_MARKET' else 'target'])), None)
        if pending is None:
            pending = {'algoType': 'CONDITIONAL', 'symbol': s['symbol'], 'side': 'SELL',
                       'positionSide': 'BOTH', 'type': kind, 'workingType': 'MARK_PRICE',
                       'closePosition': 'true', 'triggerPrice': s['plan']['stop' if kind == 'STOP_MARKET' else 'target'],
                       'clientAlgoId': identity()}
            if kind == 'STOP_MARKET' and s.get('stop_transition'):
                # Do not submit a second Close-All stop while the old one is live.
                # Protect only the verified remaining amount, without opening/reversing.
                pending.pop('closePosition')
                pending.update(quantity=str(snap['amount']), reduceOnly='true')
            s['protections'].append(pending)
            self.save(s)
        response = self.send_protection(pending)
        if not self.valid_protection(s, pending, response):
            raise ExchangeError('Koruma onarımı doğrulanamadı.')
        if kind == 'STOP_MARKET' and s.get('stop_transition'):
            self.retire_previous_stop(s, self.snapshot(s))
        self.store.event('protection_repaired', {'session_id': s['id'], 'response': response})
        return response

    def close_owned(self, s):
        snap = self.snapshot(s)
        if snap['entry']['status'] not in TERMINAL:
            self.engine.request('DELETE', '/fapi/v1/order', {'symbol': s['symbol'], 'origClientOrderId': s['entry_id']})
            if self.order(s, s['entry_id'])['status'] not in TERMINAL:
                raise ExchangeError('Giriş iptali doğrulanamadı.')
            snap = self.snapshot(s)
        self.settle_stage_exits(s, snap)
        snap = self.snapshot(s)
        if snap['amount']:
            params = {'symbol': s['symbol'], 'side': 'SELL', 'positionSide': 'BOTH',
                      'type': 'MARKET', 'quantity': str(snap['amount']), 'reduceOnly': 'true',
                      'newClientOrderId': identity()}
            s['exits'].append(params)
            self.save(s)
            try:
                self.engine.request('POST', '/fapi/v1/order', params)
            except ExchangeError:
                pass
            result = self.order(s, params['newClientOrderId'])
            if result['status'] != 'FILLED':
                raise ExchangeError('Kapatma yanıtı belirsiz; stop korunuyor, tekrar emir yok.')
        snap = self.snapshot(s)
        if snap['amount'] != 0:
            raise ExchangeError('Pozisyon kapanmadı; koruma korunuyor.')
        for p in s['protections']:
            cid = p['clientAlgoId']
            result = snap['algos'].get(cid)
            if result and result['algoStatus'] not in TERMINAL:
                try:
                    self.engine.request('DELETE', '/fapi/v1/algoOrder', {'clientAlgoId': cid})
                except ExchangeError:
                    pass
                if self.algo(cid)['algoStatus'] not in TERMINAL:
                    raise ExchangeError('Koruma iptali doğrulanamadı.')
        s['active'] = False
        s['status'] = 'CLOSED'
        self.save(s)
        self.store.event('managed_closed', {'session_id': s['id']})
        return {'status': 'closed', 'session_id': s['id'], 'position': '0'}

    def finalize_flat(self):
        """Finalize an already closed session using GET requests only."""
        s = self.session()
        self.x.sync_time()
        snap = self.snapshot(s)
        if (snap['amount'] != 0 or snap['entry']['status'] not in TERMINAL
                or any(o['status'] not in TERMINAL for o in snap['exit_orders'].values())
                or any(o['algoStatus'] not in TERMINAL for o in snap['algos'].values())
                or self.x.get('/fapi/v1/openOrders') or self.x.get('/fapi/v1/openAlgoOrders')):
            raise ValueError('Salt okunur sonlandırma için pozisyon boş ve tüm emirler sonlanmış olmalı.')
        s.update(active=False, status='CLOSED')
        self.save(s)
        self.store.event('managed_finalized_flat', {'session_id': s['id'], 'exchange_mutations': 0})
        return {'status': 'closed', 'session_id': s['id'], 'position': '0', 'exchange_mutations': 0}

    def tick(self, execute=False, close=False):
        s = self.session()
        try:
            self.x.sync_time()
            snap = self.snapshot(s)
            report = {'session_id': s['id'], 'position': str(snap['amount']),
                      'status': 'observed', 'entry_status': snap['entry']['status']}
            report['protection'] = {kind: any(
                self.valid_protection(s, p, snap['algos'].get(p['clientAlgoId'], {}))
                for p in s['protections'] if p['type'] == kind)
                for kind in ('STOP_MARKET', 'TAKE_PROFIT_MARKET')}
            if not execute:
                return report
            if close or snap['amount'] == 0:
                return self.close_owned(s)
            caps = s['plan'].get('authorization_caps')
            if caps and Decimal(snap['entry'].get('executedQty', '0')) > 0:
                average = Decimal(snap['entry'].get('avgPrice', '0'))
                filled = Decimal(snap['entry']['executedQty'])
                stop = Decimal(s['plan'].get('initial_stop', s['plan']['stop']))
                ref = Decimal(caps['reference_price'])
                loss = max(average - stop, Decimal(0)) * filled
                used = average * filled if caps['kind'] == 'NOTIONAL' else loss
                if (average <= 0 or average <= stop or average >= Decimal(s['plan']['target'])
                        or abs(average - ref) / ref * 10000 > Decimal(caps['max_drift_bps'])
                        or used > Decimal(caps['amount']) or loss > Decimal(caps['max_trade_loss'])
                        or average * filled > Decimal(caps['max_notional'])):
                    self.store.halt('Gerçekleşme fiyatı plan yetki/risk sınırını aştı; demo pozisyon kapatılıyor.')
                    return self.close_owned(s)
            # Kısmi dolmuş girişin kalanını durdur, gerçekleşen kısmı koru.
            if snap['entry']['status'] not in TERMINAL:
                self.engine.request('DELETE', '/fapi/v1/order', {'symbol': s['symbol'], 'origClientOrderId': s['entry_id']})
                if self.order(s, s['entry_id'])['status'] not in TERMINAL:
                    raise ExchangeError('Kısmi girişin kalan miktarı iptal edilemedi.')
                snap = self.snapshot(s)
            mark = self.x.get('/fapi/v1/premiumIndex', {'symbol': s['symbol']})
            self.check_mark_time(mark)
            if Decimal(mark['markPrice']) <= Decimal(s['plan']['stop']):
                self.store.halt('Stop seviyesi aşılmış; sahipliği doğrulanmış demo pozisyon kapatılıyor.')
                return self.close_owned(s)
            try:
                self.initialize_targets(s, snap)
                for kind in ('STOP_MARKET', 'TAKE_PROFIT_MARKET'):
                    self.ensure_protection(s, snap, kind)
            except (ExchangeError, ValueError):
                self.store.halt('Koruma onarılamadı; sahipliği doğrulanmış demo pozisyon kapatılıyor.')
                # Yeni sahiplik kontrolü başarısızsa manuel pozisyona dokunulmaz.
                return self.close_owned(s)
            target_result = self.process_targets(s, mark['markPrice'])
            if target_result:
                return target_result
            # Onarım sırasında fiyat/pozisyon değişmiş olabilir; yeniden eşleştir.
            verified = self.snapshot(s)
            if verified['amount'] == 0:
                return self.close_owned(s)
            for kind in ('STOP_MARKET', 'TAKE_PROFIT_MARKET'):
                if not any(self.valid_protection(s, p, verified['algos'].get(p['clientAlgoId'], {}))
                           for p in s['protections'] if p['type'] == kind):
                    raise ExchangeError('Son kontrolde koruma kayboldu; tekrar kontrol gerekli.')
            s['status'] = 'PROTECTED'
            s['last_check_ms'] = int(time.time() * 1000)
            self.save(s)
            report.update(status='protected', position=str(verified['amount']),
                          protection={'STOP_MARKET': True, 'TAKE_PROFIT_MARKET': True})
            if 'target_management' in s:
                report['targets'] = s['target_management']['targets']
                report['stop'] = s['plan']['stop']
            self.store.event('watchdog_healthy', report)
            return report
        except (ExchangeError, ValueError) as exc:
            self.store.halt('Watchdog bağlantı/sahiplik hatası: yeni girişler durduruldu.')
            self.store.event('watchdog_alarm', {'session_id': s['id'], 'action': 'halt_entries_preserve_protection', 'reason': str(exc)})
            raise

    def check_mark_time(self, mark):
        if 'time' in mark:
            age = (time.time() * 1000 + getattr(self.x, 'offset_ms', 0) - int(mark['time'])) / 1000
            if not -1 <= age <= self.engine.limits.max_age_seconds:
                raise ExchangeError('Eski fiyat verisiyle koruma değiştirilemez.')

    def open(self, symbol, prepared=None, plan_ref=None, entry_id=None, session_id=None):
        if self.store.sessions():
            raise ValueError('Aktif yönetilen oturum varken yeni pozisyon açılamaz.')
        if not reconcile(self.x, self.store)['ready']:
            raise ValueError('Demo hesap uzlaştırması tamamlanmadı.')
        info = next((i for i in self.x.get('/fapi/v1/exchangeInfo')['symbols'] if i['symbol'] == symbol), None)
        if not info or info['status'] != 'TRADING' or info.get('quoteAsset') != 'USDT':
            raise ValueError('Geçerli USDT sembolü gerekli.')
        mark = self.x.get('/fapi/v1/premiumIndex', {'symbol': symbol})['markPrice']
        plan = dict(prepared) if prepared is not None else position_plan(info, mark)
        self.engine.configure_entry(mark, plan['stop'])
        self.x.sync_time()
        s = {'id': session_id or identity(), 'active': True, 'status': 'OPENING', 'symbol': symbol,
             'started_ms': self.x.get('/fapi/v1/time')['serverTime'], 'plan': plan,
             'entry_id': entry_id or identity(), 'protections': [], 'exits': []}
        if plan_ref:
            s['plan_ref'] = plan_ref
        params = {'symbol': symbol, 'side': 'BUY', 'positionSide': 'BOTH', 'type': 'MARKET',
                  'quantity': plan['quantity'], 'newClientOrderId': s['entry_id']}
        # Risk reddedilirse sahipsiz yönetilen oturum yaratma.
        self.engine.check_entry(params)
        self.save(s)
        try:
            self.engine.request('POST', '/fapi/v1/order', params)
            return self.tick(execute=True)
        except (ExchangeError, ValueError):
            self.store.halt('Yönetilen giriş tamamlanamadı; watchdog ile devralma gerekli.')
            raise


def watch_loop(watchdog, execute=False, iterations=1, interval=5, close=False):
    if iterations < 0 or not 1 <= interval <= 60:
        raise ValueError('iterations >= 0 ve 1 <= interval <= 60 olmalı.')
    completed = 0
    while iterations == 0 or completed < iterations:
        try:
            result = watchdog.tick(execute=execute, close=close)
        except ExchangeError:
            result = {'status': 'alarm', 'action': 'halt_entries_preserve_protection_retry',
                      'session_id': watchdog.session()['id']}
        yield result
        completed += 1
        if result['status'] == 'closed':
            return
        if iterations == 0 or completed < iterations:
            time.sleep(interval)
