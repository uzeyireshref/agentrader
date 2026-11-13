"""Demo one-way pozisyon yaşam döngüsü deneyi. Canlı strateji değildir."""
import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
from uuid import uuid4

from .exchange import DemoExchange, ExchangeError


def position_plan(info, mark):
    filters = {f['filterType']: f for f in info['filters']}
    lot = filters.get('MARKET_LOT_SIZE', filters['LOT_SIZE'])
    step = Decimal(lot['stepSize'])
    if step <= 0:
        lot = filters['LOT_SIZE']
        step = Decimal(lot['stepSize'])
    price = Decimal(mark)
    tick = Decimal(filters['PRICE_FILTER']['tickSize'])
    minimum = Decimal(filters['MIN_NOTIONAL']['notional'])
    # Yuvarlama/kayma payı ve iki geçerli çıkış parçası.
    half = (max(Decimal(lot['minQty']), minimum * Decimal('1.1') / price / 2) / step).to_integral_value(rounding=ROUND_CEILING) * step
    qty = half * 2
    if price <= 0 or qty > Decimal(lot['maxQty']) or qty * price > 100:
        raise ValueError('Demo pozisyonu 100 USDT sınırına veya sembol kurallarına uymuyor.')
    stop = (price * Decimal('.98') / tick).to_integral_value(rounding=ROUND_FLOOR) * tick
    target = (price * Decimal('1.02') / tick).to_integral_value(rounding=ROUND_CEILING) * tick
    return {'symbol': info['symbol'], 'quantity': format(qty, 'f'),
            'partial_quantity': format(half, 'f'), 'stop': format(stop, 'f'),
            'target': format(target, 'f'), 'notional_estimate': str(qty * price)}


class PositionExperiment:
    def __init__(self, exchange, symbol, journal):
        self.x, self.symbol, self.journal = exchange, symbol, journal
        self.algos = []
        self.entry_id = None

    def record(self, event, data):
        with self.journal.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                                     'event': event, 'data': data}, ensure_ascii=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    def amount(self):
        rows = self.x.get('/fapi/v3/positionRisk', {'symbol': self.symbol})
        return sum((Decimal(p['positionAmt']) for p in rows if p['symbol'] == self.symbol), Decimal(0))

    def market(self, side, quantity, reduce=False):
        cid = 'agt-' + uuid4().hex[:28]
        params = {'symbol': self.symbol, 'side': side, 'positionSide': 'BOTH',
                  'type': 'MARKET', 'quantity': format(quantity, 'f'),
                  'newClientOrderId': cid}
        if reduce:
            params['reduceOnly'] = 'true'
        else:
            self.entry_id = cid
        self.record('market_pending', params)
        try:
            self.x.request('POST', '/fapi/v1/order', params)
        except ExchangeError:
            self.record('market_submission_uncertain', {'clientOrderId': cid})
        # Aynı POST yeniden gönderilmez; kabul ile gerçekleşme ayrılır.
        for _ in range(5):
            result = self.x.get('/fapi/v1/order', {'symbol': self.symbol, 'origClientOrderId': cid})
            self.record('market_queried', result)
            if result['status'] == 'FILLED':
                return result
            if result['status'] in ('CANCELED', 'EXPIRED', 'REJECTED'):
                break
            time.sleep(.3)
        raise ExchangeError('Demo market emrinin tam gerçekleşmesi doğrulanamadı.')

    def protect(self, kind, trigger):
        cid = 'agt-' + uuid4().hex[:28]
        self.algos.append(cid)
        params = {'algoType': 'CONDITIONAL', 'symbol': self.symbol, 'side': 'SELL',
                  'positionSide': 'BOTH', 'type': kind, 'triggerPrice': trigger,
                  'workingType': 'MARK_PRICE', 'closePosition': 'true', 'clientAlgoId': cid}
        self.record('protection_pending', params)
        try:
            self.x.request('POST', '/fapi/v1/algoOrder', params)
        except ExchangeError:
            self.record('protection_submission_uncertain', {'clientAlgoId': cid})
        result = self.x.get('/fapi/v1/algoOrder', {'clientAlgoId': cid})
        self.record('protection_verified', result)
        if (result.get('algoStatus') != 'NEW' or result.get('symbol') != self.symbol
                or result.get('side') != 'SELL' or result.get('orderType') != kind
                or str(result.get('closePosition')).lower() != 'true'
                or Decimal(result['triggerPrice']) != Decimal(trigger)):
            raise ExchangeError('Demo koruyucu emir ilişkisi doğrulanamadı.')
        return result

    def cleanup(self):
        # Giriş belirsiz kaldıysa önce kalan giriş miktarını iptal et.
        if self.entry_id:
            lookup = {'symbol': self.symbol, 'origClientOrderId': self.entry_id}
            entry = self.x.get('/fapi/v1/order', lookup)
            if entry['status'] in ('NEW', 'PARTIALLY_FILLED'):
                self.x.request('DELETE', '/fapi/v1/order', lookup)
                entry = self.x.get('/fapi/v1/order', lookup)
                if entry['status'] in ('NEW', 'PARTIALLY_FILLED'):
                    raise ExchangeError('Giriş iptali belirsiz; demo hesabını kontrol edin.')
        remaining = self.amount()
        if remaining:
            self.market('SELL' if remaining > 0 else 'BUY', abs(remaining), reduce=True)
        if self.amount() != 0:
            raise ExchangeError('Demo pozisyon sıfırlanamadı; koruyucu emirler korunuyor.')
        # Pozisyon kapandığı doğrulanmadan stop/TP kaldırılmaz.
        for cid in self.algos:
            lookup = {'clientAlgoId': cid}
            try:
                self.x.request('DELETE', '/fapi/v1/algoOrder', lookup)
            except ExchangeError:
                pass
            result = self.x.get('/fapi/v1/algoOrder', lookup)
            self.record('protection_final', result)
            if result['algoStatus'] not in ('CANCELED', 'FINISHED', 'EXPIRED', 'REJECTED'):
                raise ExchangeError('Demo koruyucu emir temizliği doğrulanamadı.')
        normal = self.x.get('/fapi/v1/openOrders', {'symbol': self.symbol})
        algo = self.x.get('/fapi/v1/openAlgoOrders', {'symbol': self.symbol})
        if normal or algo or self.amount() != 0:
            raise ExchangeError('Test sonunda açık emir veya pozisyon bulundu.')
        self.record('cleanup_verified', {'position': '0', 'open_orders': 0, 'open_algo_orders': 0})


def position_cycle(config, symbol='BTCUSDT', execute=False, journal=Path('logs/demo-positions.jsonl'), exchange_factory=None):
    x = (exchange_factory or DemoExchange)(config)
    x.sync_time()
    if x.get('/fapi/v1/positionSide/dual')['dualSidePosition']:
        raise ValueError('Bu demo testi one-way hesap gerektirir.')
    account = x.get('/fapi/v3/account')
    if (any(Decimal(p['positionAmt']) != 0 for p in account['positions'])
            or x.get('/fapi/v1/openOrders') or x.get('/fapi/v1/openAlgoOrders')):
        raise ValueError('Demo testinden önce hesapta açık pozisyon veya emir bulunmamalı.')
    info = next((s for s in x.get('/fapi/v1/exchangeInfo')['symbols'] if s['symbol'] == symbol), None)
    if not info or info['status'] != 'TRADING' or info.get('quoteAsset') != 'USDT':
        raise ValueError('İşleme açık USDT sözleşmesi bulunamadı.')
    mark = x.get('/fapi/v1/premiumIndex', {'symbol': symbol})['markPrice']
    plan = position_plan(info, mark)
    if hasattr(x, 'configure_entry'):
        x.configure_entry(mark, plan['stop'])
    report = {'environment': 'demo', 'plan': plan, 'status': 'preview'}
    if not execute:
        return report
    if Decimal(account['availableBalance']) < Decimal(plan['notional_estimate']) * Decimal('1.1'):
        raise ValueError('Demo kullanılabilir bakiye yetersiz.')
    journal.parent.mkdir(parents=True, exist_ok=True)
    lock = journal.with_suffix('.lock')
    try:
        lock_file = lock.open('x')
    except FileExistsError:
        raise ValueError('Önceki pozisyon deneyi kilidi var; günlük ve demo hesabını uzlaştırmadan yeniden çalıştırmayın.') from None
    run = PositionExperiment(x, symbol, journal)
    clean = False
    try:
        run.record('plan', plan)
        try:
            report['entry'] = run.market('BUY', Decimal(plan['quantity']))
            if run.amount() != Decimal(plan['quantity']):
                raise ExchangeError('Giriş pozisyon miktarı doğrulanamadı.')
            report['stop'] = run.protect('STOP_MARKET', plan['stop'])
            report['take_profit'] = run.protect('TAKE_PROFIT_MARKET', plan['target'])
            report['partial_exit'] = run.market('SELL', Decimal(plan['partial_quantity']), reduce=True)
            remaining = run.amount()
            if remaining != Decimal(plan['partial_quantity']):
                raise ExchangeError('Kısmi çıkış sonrası pozisyon miktarı beklenenden farklı.')
            report['remaining_after_partial'] = str(remaining)
            report['full_exit'] = run.market('SELL', remaining, reduce=True)
        finally:
            run.cleanup()
            clean = True
        report['status'] = 'passed'
        run.record('passed', report)
        return report
    finally:
        lock_file.close()
        if clean:
            lock.unlink()
