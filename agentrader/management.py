"""Kalıcı hedef çıkışları ve giriş fiyatına stop geçişi; yalnızca reduce-only."""
from decimal import Decimal, ROUND_FLOOR
from uuid import uuid4

from .exchange import ExchangeError

TERMINAL_EXIT = {'FILLED', 'CANCELED', 'EXPIRED', 'EXPIRED_IN_MATCH', 'REJECTED'}


def split_targets(quantity, targets, rules):
    quantity = Decimal(quantity)
    step = Decimal(rules['market']['stepSize'])
    if step <= 0:
        step = Decimal(rules['lot']['stepSize'])
    previous, cumulative = Decimal(0), Decimal(0)
    parts = []
    for index, target in enumerate(targets):
        cumulative += Decimal(target['fraction'])
        boundary = quantity if index == len(targets) - 1 else (quantity * cumulative / step).to_integral_value(rounding=ROUND_FLOOR) * step
        part = boundary - previous
        for lot in (rules['market'], rules['lot']):
            increment = Decimal(lot['stepSize'])
            if part <= 0 or not Decimal(lot['minQty']) <= part <= Decimal(lot['maxQty']) or (increment > 0 and part % increment):
                raise ValueError('Hedef payı lot/minimum miktar sınırlarına uymuyor; bütçe artırılmadı.')
        parts.append({'index': index + 1, 'price': target['price'], 'quantity': str(part),
                      'status': 'WAITING', 'attempts': []})
        previous = boundary
    return parts


class StagedManagement:
    def stage_exit_ids(self, session):
        return {cid for stage in session.get('target_management', {}).get('targets', []) for cid in stage['attempts']}

    def initialize_targets(self, session, snapshot):
        if 'targets' not in session['plan']:
            return
        filled = Decimal(snapshot['entry']['executedQty'])
        if 'target_management' not in session:
            stages = split_targets(filled, session['plan']['targets'], session['plan']['lot_rules'])
            session['target_management'] = {'entry_quantity': str(filled), 'targets': stages}
            self.save(session)
        elif filled != Decimal(session['target_management']['entry_quantity']):
            raise ValueError('Hedefler dağıtıldıktan sonra giriş gerçekleşmesi değişti; otomatik çıkış durdu.')

    def settle_stage_exits(self, session, snapshot):
        """Açık kısmi hedefin kalanı önce iptal edilip terminal durum doğrulanır."""
        for cid in self.stage_exit_ids(session):
            result = snapshot['exit_orders'].get(cid)
            if result and result['status'] not in TERMINAL_EXIT | {'NOT_SUBMITTED'}:
                self.engine.request('DELETE', '/fapi/v1/order', {'symbol': session['symbol'], 'origClientOrderId': cid})
                if self.order(session, cid)['status'] not in TERMINAL_EXIT:
                    raise ExchangeError('Hedef emrinin kalan kısmı iptal edilmedi; yeni çıkış gönderilmedi.')

    def retire_previous_stop(self, session, snapshot):
        transition = session.get('stop_transition')
        if not transition:
            return
        if snapshot['amount'] > 0 and not any(self.valid_protection(session, p, snapshot['algos'].get(p['clientAlgoId'], {}))
                                             for p in session['protections'] if p['type'] == 'STOP_MARKET'):
            raise ExchangeError('Yeni stop son kontrolde geçerli değil; eski stop korunuyor.')
        for params in session['protections']:
            cid = params['clientAlgoId']
            if params['type'] != 'STOP_MARKET' or params['triggerPrice'] == session['plan']['stop']:
                continue
            result = snapshot['algos'].get(cid)
            if result and result['algoStatus'] not in {'CANCELED', 'EXPIRED', 'REJECTED', 'FINISHED'}:
                try:
                    self.engine.request('DELETE', '/fapi/v1/algoOrder', {'clientAlgoId': cid})
                except ExchangeError:
                    pass
                if self.algo(cid)['algoStatus'] not in {'CANCELED', 'EXPIRED', 'REJECTED', 'FINISHED'}:
                    raise ExchangeError('Yeni stop doğrulandı ama eski stop iptali belirsiz.')
        transition['state'] = 'APPLIED'
        self.save(session)

    def move_stop_to_entry(self, session, snapshot):
        transition = session.get('stop_transition')
        if transition and transition['state'] == 'APPLIED':
            return
        if not transition:
            average = Decimal(snapshot['entry']['avgPrice'])
            tick = Decimal(session['plan']['lot_rules']['tick'])
            new_stop = (average / tick).to_integral_value(rounding=ROUND_FLOOR) * tick
            old_stop = Decimal(session['plan']['stop'])
            if average <= 0 or new_stop < old_stop:
                raise ValueError('Girişe stop taşıma riski artıramaz.')
            session['stop_transition'] = {'from': str(old_stop), 'to': str(new_stop), 'state': 'PENDING'}
            session['plan']['stop'] = str(new_stop)
            self.save(session)
        mark = self.x.get('/fapi/v1/premiumIndex', {'symbol': session['symbol']})
        self.check_mark_time(mark)
        if Decimal(mark['markPrice']) <= Decimal(session['plan']['stop']):
            return self.close_owned(session)
        try:
            self.ensure_protection(session, self.snapshot(session), 'STOP_MARKET')
        except ExchangeError:
            self.store.halt('Girişe stop taşıma doğrulanamadı; demo pozisyon kapatılıyor.')
            return self.close_owned(session)
        self.store.event('stop_moved_to_entry', {'session_id': session['id'], 'stop': session['plan']['stop']})

    def process_targets(self, session, mark_price):
        if 'target_management' not in session:
            return
        for stage in session['target_management']['targets']:
            snapshot = self.snapshot(session)
            if snapshot['amount'] == 0:
                return self.close_owned(session)
            current_mark = self.x.get('/fapi/v1/premiumIndex', {'symbol': session['symbol']})
            self.check_mark_time(current_mark)
            mark_price = current_mark['markPrice']
            if Decimal(mark_price) <= Decimal(session['plan']['stop']):
                return self.close_owned(session)
            if stage['status'] == 'FAILED':
                raise ExchangeError('Hedef çıkışı başarısız; koruma sürüyor, yeni deneme yapılmadı.')
            if stage['status'] == 'COMPLETED':
                verified_done = sum((Decimal(snapshot['exit_orders'][cid]['executedQty']) for cid in stage['attempts']), Decimal(0))
                if verified_done != Decimal(stage['quantity']):
                    raise ValueError('Tamamlanmış hedef kaydı borsa gerçekleşmesiyle uyuşmuyor.')
            if stage['status'] != 'COMPLETED':
                if stage['status'] == 'WAITING' and Decimal(mark_price) < Decimal(stage['price']):
                    return
                stage['status'] = 'TRIGGERED'
                self.save(session)
                self.settle_stage_exits(session, snapshot)
                snapshot = self.snapshot(session)
                done = sum((Decimal(snapshot['exit_orders'][cid]['executedQty']) for cid in stage['attempts']), Decimal(0))
                desired = Decimal(stage['quantity'])
                if done > desired:
                    raise ValueError('Hedef gerçekleşmesi izinli miktarı aşıyor.')
                if any(snapshot['exit_orders'][cid]['status'] == 'REJECTED' for cid in stage['attempts']):
                    stage['status'] = 'FAILED'
                    self.save(session)
                    raise ExchangeError('Hedef emri reddedildi; otomatik yeni deneme durdu.')
                if done < desired:
                    pending = next((p for p in session['exits'] if p['newClientOrderId'] in stage['attempts']
                                    and snapshot['exit_orders'][p['newClientOrderId']]['status'] == 'NOT_SUBMITTED'), None)
                    if pending is None:
                        if len(stage['attempts']) >= 3:
                            stage['status'] = 'FAILED'
                            self.save(session)
                            raise ExchangeError('Hedef çıkışında üç deneme sınırı; koruma korunuyor.')
                        if snapshot['amount'] < desired - done:
                            raise ValueError('Kalan pozisyon hedef miktarından küçük; yeniden uzlaştırma gerekli.')
                        for lot in (session['plan']['lot_rules']['market'], session['plan']['lot_rules']['lot']):
                            step = Decimal(lot['stepSize'])
                            if not Decimal(lot['minQty']) <= desired - done <= Decimal(lot['maxQty']) or (step > 0 and (desired - done) % step):
                                stage['status'] = 'FAILED'
                                self.save(session)
                                raise ValueError('Hedefin kalan miktarı borsa adım/minimum sınırlarına uymuyor.')
                        pending = {'symbol': session['symbol'], 'side': 'SELL', 'positionSide': 'BOTH',
                                   'type': 'MARKET', 'quantity': str(desired - done), 'reduceOnly': 'true',
                                   'newClientOrderId': 'agt-' + uuid4().hex[:28]}
                        stage['attempts'].append(pending['newClientOrderId'])
                        session['exits'].append(pending)
                        self.save(session)
                    try:
                        self.engine.request('POST', '/fapi/v1/order', pending)
                    except ExchangeError:
                        pass
                    # Aynı POST tekrarlanmaz. Yeni turda yalnızca kesin terminal kalanın devamı mümkün.
                    self.order(session, pending['newClientOrderId'])
                    snapshot = self.snapshot(session)
                    done = sum((Decimal(snapshot['exit_orders'][cid]['executedQty']) for cid in stage['attempts']), Decimal(0))
                    if done > desired:
                        raise ValueError('Hedef gerçekleşmesi izinli miktarı aşıyor.')
                    if done < desired:
                        return
                stage['status'] = 'COMPLETED'
                self.save(session)
                self.store.event('target_completed', {'session_id': session['id'], 'index': stage['index'], 'quantity': stage['quantity']})
            snapshot = self.snapshot(session)
            if snapshot['amount'] == 0:
                return self.close_owned(session)
            if session['plan']['management']['break_even_after_target'] == stage['index']:
                result = self.move_stop_to_entry(session, snapshot)
                if result:
                    return result
