"""Küçük demo limit emir deneyi; pozisyon açma stratejisi değildir."""
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
from uuid import uuid4

from .exchange import DemoExchange, ExchangeError


def build_limit(symbol_info, bid):
    filters = {f['filterType']: f for f in symbol_info['filters']}
    tick = Decimal(filters['PRICE_FILTER']['tickSize'])
    lot = filters['LOT_SIZE']
    step = Decimal(lot['stepSize'])
    # Piyasanın %2 altında; GTX anında eşleşen emri reddeder.
    price = (Decimal(bid) * Decimal('0.98') / tick).to_integral_value(rounding=ROUND_FLOOR) * tick
    minimum = Decimal(filters['MIN_NOTIONAL']['notional'])
    qty = (max(Decimal(lot['minQty']), minimum / price) / step).to_integral_value(rounding=ROUND_CEILING) * step
    if not Decimal(filters['PRICE_FILTER']['minPrice']) <= price <= Decimal(filters['PRICE_FILTER']['maxPrice']):
        raise ValueError('Test fiyatı sembol sınırları dışında.')
    if qty > Decimal(lot['maxQty']) or qty * price > Decimal('100'):
        raise ValueError('Test emri 100 USDT tutar sınırını veya miktar sınırını aşıyor.')
    return {'symbol': symbol_info['symbol'], 'side': 'BUY', 'positionSide': 'BOTH',
            'type': 'LIMIT', 'timeInForce': 'GTX', 'quantity': format(qty, 'f'),
            'price': format(price, 'f'), 'newClientOrderId': 'agt-' + uuid4().hex[:28]}


def order_cycle(config, symbol='BTCUSDT', execute=False, journal=Path('logs/demo-orders.jsonl'), exchange_factory=None):
    x = (exchange_factory or DemoExchange)(config)
    x.sync_time()
    mode = x.get('/fapi/v1/positionSide/dual')
    if mode['dualSidePosition']:
        raise ValueError('Bu test yalnızca one-way modunu destekler; hesap modu değiştirilmedi.')
    account = x.get('/fapi/v3/account')
    if any(Decimal(p['positionAmt']) != 0 for p in account['positions']) or x.get('/fapi/v1/openOrders'):
        raise ValueError('Test için açık emir ve pozisyon bulunmamalı.')
    info = x.get('/fapi/v1/exchangeInfo')
    item = next((s for s in info['symbols'] if s['symbol'] == symbol), None)
    if not item or item['status'] != 'TRADING' or item.get('quoteAsset') != 'USDT':
        raise ValueError('İşleme açık USDT sembolü bulunamadı.')
    book = x.get('/fapi/v1/ticker/bookTicker', {'symbol': symbol})
    plan = build_limit(item, book['bidPrice'])
    if hasattr(x, 'configure_entry'):
        x.configure_entry(plan['price'], str(Decimal(plan['price']) * Decimal('.98')))
    report = {'environment': 'demo', 'plan': plan, 'executed': False,
              'available_balance': account['availableBalance']}
    if not execute:
        report['status'] = 'preview'
        return report
    if Decimal(account['availableBalance']) < Decimal(plan['quantity']) * Decimal(plan['price']):
        raise ValueError('Demo kullanılabilir bakiye yetersiz. Demo Futures cüzdanına sanal bakiye ekleyin.')
    journal.parent.mkdir(parents=True, exist_ok=True)
    def record(event, data):
        with journal.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                                     'event': event, 'data': data}, ensure_ascii=False) + '\n')
    lookup = {'symbol': symbol, 'origClientOrderId': plan['newClientOrderId']}
    record('submission_pending', plan)
    # Gönderim tek sefer yapılır. Hata/zaman aşımında tekrar POST yapılmaz.
    try:
        try:
            response = x.request('POST', '/fapi/v1/order', plan)
            record('accepted', response)
        except ExchangeError:
            record('submission_uncertain', lookup)
            # Bir kez sorgula; bulunamazsa belirsiz durum korunur, emir yeniden gönderilmez.
            response = x.get('/fapi/v1/order', lookup)
            record('reconciled', response)
        report['executed'] = True
        report['queried'] = x.get('/fapi/v1/order', lookup)
        record('queried', report['queried'])
    finally:
        # Sadece bu çalıştırmaya ait kimlikle iptal; manuel emirlere dokunulmaz.
        try:
            canceled = x.request('DELETE', '/fapi/v1/order', lookup)
            record('cancel_response', canceled)
        except ExchangeError:
            record('cancel_uncertain', lookup)
        try:
            final = x.get('/fapi/v1/order', lookup)
            record('final', final)
        except ExchangeError:
            raise ExchangeError('Emir durumu belirsiz. Yeni test başlatmayın; logs/demo-orders.jsonl kimliğiyle demo hesabını kontrol edin.') from None
    report['final'] = final
    if final['status'] != 'CANCELED' or Decimal(final['executedQty']) != 0:
        raise ExchangeError('Demo emri beklenen şekilde gerçekleşmeden iptal edilmedi. Günlük ve demo pozisyonlarını kontrol edin.')
    report['status'] = 'passed'
    return report
