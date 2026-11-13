"""Yetkilendirilmiş planı güncel fiyat/risk kontrolünden geçirip demo watchdog'a bağlar."""
import time
from decimal import Decimal, ROUND_FLOOR

from .plans import timestamp
from .risk import size_for_risk, number
from .watchdog import Watchdog, identity
from .management import split_targets
from .market_data import PublicMarket


def price_check(plan, price):
    price = number(price)
    if price <= 0:
        raise ValueError('Güncel fiyat pozitif olmalı.')
    condition = plan['entry']['condition']
    if condition != 'IMMEDIATE':
        trigger = Decimal(plan['entry']['trigger_price'])
        reached = price <= trigger if condition == 'MARK_AT_OR_BELOW' else price >= trigger
        if not reached:
            return False
    ref = Decimal(plan['entry']['reference_price'])
    if price <= Decimal(plan['stop']) or price >= Decimal(plan['targets'][0]['price']):
        raise ValueError('Güncel fiyat onaylanan stop/hedef aralığı dışında; yeniden plan gerekli.')
    if abs(price - ref) / ref * 10000 > Decimal(plan['entry']['max_drift_bps']):
        raise ValueError('Fiyat onaylanan tolerans dışında; yeniden onay/plan gerekli.')
    return True


def market_guard_check(plan, demo_mark, live_client, now_ms=None, clock_offset_ms=0):
    guard = plan.get('market_guard')
    if guard is None:
        return None
    live = live_client.get('/fapi/v1/premiumIndex', {'symbol': plan['symbol']})
    if now_ms is None:
        now_ms = int(time.time() * 1000) + clock_offset_ms
    for data in (demo_mark, live):
        if data.get('symbol') != plan['symbol'] or type(data.get('time')) is not int:
            raise ValueError('Piyasa karşılaştırması sembol/zaman bilgisi eksik.')
        if not -1000 <= now_ms - data['time'] <= guard['max_age_seconds'] * 1000:
            raise ValueError('Canlı/demo fiyatı eski; giriş engellendi.')
    demo_price, live_price = number(demo_mark['markPrice']), number(live['markPrice'])
    if min(demo_price, live_price) <= 0:
        raise ValueError('Piyasa karşılaştırmasında pozitif fiyat gerekli.')
    difference = abs(demo_price - live_price) / live_price * 10000
    if difference > Decimal(guard['max_divergence_bps']):
        raise ValueError('Canlı/demo fiyat farkı onaylanan toleransı aşıyor; giriş engellendi.')
    return {'demo_mark': str(demo_price), 'live_mark': str(live_price), 'divergence_bps': str(difference)}


def prepare(plan, info, mark, limits):
    price = number(mark['markPrice'])
    if not price_check(plan, price):
        return None
    if info['status'] != 'TRADING' or info.get('quoteAsset') != 'USDT' or info.get('contractType', 'PERPETUAL') != 'PERPETUAL':
        raise ValueError('İlk plan adaptörü işleme açık USDT perpetual gerektirir.')
    filters = {f['filterType']: f for f in info['filters']}
    # MARKET ve normal miktar adımlarının ikisini de karşıla.
    market = filters.get('MARKET_LOT_SIZE', filters['LOT_SIZE'])
    step = Decimal(market['stepSize'])
    if step <= 0:
        step = Decimal(filters['LOT_SIZE']['stepSize'])
    amount, stop = Decimal(plan['sizing']['amount']), Decimal(plan['stop'])
    # Yetki, stop riski veya nominal üst sınırdır; kaldıraç/teminat tipi desteklenmez.
    if plan['sizing']['kind'] == 'NOTIONAL':
        qty = (amount / price / step).to_integral_value(rounding=ROUND_FLOOR) * step
    else:
        if amount > limits.max_trade_loss:
            raise ValueError('Plan kayıp bütçesi bağımsız işlem risk sınırını aşıyor.')
        qty = size_for_risk(price, stop, amount, step)
    if qty <= 0:
        raise ValueError('Risk/tutar bütçesi geçerli miktara yetmiyor.')
    for lot in (market, filters['LOT_SIZE']):
        lot_step = Decimal(lot['stepSize'])
        if not Decimal(lot['minQty']) <= qty <= Decimal(lot['maxQty']) or (lot_step > 0 and qty % lot_step):
            raise ValueError('Plan miktarı sembol adımlarına/sınırlarına uymuyor.')
    if qty * price < Decimal(filters['MIN_NOTIONAL']['notional']):
        raise ValueError('Plan tutarı borsa minimum nominal tutarının altında.')
    tick = Decimal(filters['PRICE_FILTER']['tickSize'])
    for value in (stop, *(Decimal(t['price']) for t in plan['targets'])):
        if value % tick or not Decimal(filters['PRICE_FILTER']['minPrice']) <= value <= Decimal(filters['PRICE_FILTER']['maxPrice']):
            raise ValueError('Stop/hedef fiyat adımına veya fiyat sınırlarına uymuyor.')
    if qty * price > limits.max_notional or qty * (price - stop) > limits.max_trade_loss:
        raise ValueError('Plan miktarı bağımsız risk/nominal sınırını aşıyor.')
    lot_rules = {'market': market, 'lot': filters['LOT_SIZE'], 'tick': str(tick)}
    target_quantities = split_targets(qty, plan['targets'], lot_rules)
    return {'symbol': plan['symbol'], 'quantity': str(qty), 'stop': plan['stop'],
            'initial_stop': plan['stop'], 'target': plan['targets'][-1]['price'],
            'targets': plan['targets'], 'management': plan['management'], 'lot_rules': lot_rules,
            'target_quantities': target_quantities,
            'notional_estimate': str(qty * price),
            'authorization_caps': {'reference_price': plan['entry']['reference_price'],
                                   'max_drift_bps': plan['entry']['max_drift_bps'],
                                   'kind': plan['sizing']['kind'], 'amount': plan['sizing']['amount'],
                                   'max_trade_loss': str(limits.max_trade_loss), 'max_notional': str(limits.max_notional)}}


def run_plan(service, exchange, limits, plan_id, version, execute=False):
    row = service.show(plan_id, version)
    plan = row['plan']
    if plan['schema_version'] != 1:
        if plan['execution']['strategy']=='NEUTRAL_GRID':
            from .neutral_runner import NeutralGridRunner
            return NeutralGridRunner(service,exchange,limits).open(plan_id,version,execute)
        if plan['execution']['strategy'] == 'GRID':
            from .grid_runner import GridRunner
            return GridRunner(service, exchange, limits).open(plan_id, version, execute)
        from .v2_runner import V2Runner
        return V2Runner(service, exchange, limits).open(plan_id, version, execute)
    if row['state'] != 'AUTHORIZED':
        raise ValueError('Plan henüz yetkili değil veya kullanıldı: ' + row['state'])
    exchange.sync_time()
    mark = exchange.get('/fapi/v1/premiumIndex', {'symbol': plan['symbol']})
    price = number(mark['markPrice'])
    trigger = plan['entry']['trigger_price']
    observation = {
        'plan_id': plan_id, 'version': version, 'symbol': plan['symbol'],
        'source': 'binance_usdm_demo_mark', 'observed_at_ms': int(time.time() * 1000),
        'exchange_time_ms': mark.get('time'), 'mark_price': str(price),
        'condition': plan['entry']['condition'], 'trigger_price': trigger,
        'trigger_distance': str(price - Decimal(trigger)) if trigger is not None else None,
        'reference_price': plan['entry']['reference_price'],
        'approval_until': row['approval_until'],
    }
    info = next((s for s in exchange.get('/fapi/v1/exchangeInfo')['symbols'] if s['symbol'] == plan['symbol']), None)
    if not info:
        raise ValueError('Plan sembolü borsada bulunamadı.')
    try:
        prepared = prepare(plan, info, mark, limits)
    except ValueError as exc:
        service.store.event('plan_price_check', dict(observation, decision='BLOCKED', reason=str(exc)))
        raise
    observation.update(decision='CONDITION_MET' if prepared else 'WAITING_CONDITION',
                       reason='Giriş koşulu sağlandı; ek risk kontrolleri gerekli.' if prepared
                       else 'Demo mark fiyatı giriş eşiğini sağlamıyor.')
    service.store.event('plan_price_check', observation)
    if prepared is None:
        return {'state': 'WAITING_CONDITION', 'plan_id': plan_id, 'version': version,
                'executed': False, 'observation': observation}
    watcher = Watchdog(exchange, service.store, limits)
    live_client = PublicMarket() if plan.get('market_guard') else None
    def compare_market(latest):
        if live_client is not None:
            # Canlı GET sonrasındaki saati kullan; eski demo fiyatı canlı çağrı gecikmesiyle tazelenmiş sayılmaz.
            result = market_guard_check(plan, latest, live_client,
                                        clock_offset_ms=getattr(exchange, 'offset_ms', 0))
            service.store.event('plan_market_guard', {'plan_id': plan_id, 'version': version, 'comparison': result})
    def preview_guard(order, latest):
        current = service.show(plan_id, version)
        if current['state'] != 'AUTHORIZED' or current['approval_until'] <= time.time():
            raise ValueError('Ön kontrolde plan yetkisi geçersiz.')
        if not price_check(plan, latest['markPrice']):
            raise ValueError('Giriş koşulu ön kontrol sırasında değişti.')
        compare_market(latest)
    watcher.engine.entry_guard = preview_guard
    watcher.engine.configure_entry(mark['markPrice'], plan['stop'])
    params = {'symbol': plan['symbol'], 'side': 'BUY', 'positionSide': 'BOTH', 'type': 'MARKET', 'quantity': prepared['quantity']}
    try:
        watcher.engine.check_entry(params)
    except ValueError as exc:
        service.store.event('plan_entry_blocked', dict(observation, decision='BLOCKED', reason=str(exc)))
        raise
    result = {'state': 'READY', 'plan_id': plan_id, 'version': version, 'mode': plan['mode'],
              'executed': False, 'prepared': prepared, 'observation': observation,
              'warning': 'Önizleme yetkiyi tüketmez ve emir göndermez.'}
    if not execute:
        return result
    sid = identity()
    # Yetki kullanımını gönderimden önce atomik olarak ayır; çökmede yeniden giriş yok.
    action_id = service.claim(plan_id, version, sid)

    def guard(order, latest):
        current = service.show(plan_id, version)
        if (current['state'] != 'EXECUTING' or current['action_id'] != action_id
                or order['newClientOrderId'] != action_id or order['symbol'] != plan['symbol']
                or order['side'] != 'BUY' or order['type'] != 'MARKET'
                or order.get('positionSide') != 'BOTH' or order.get('reduceOnly') == 'true'
                or Decimal(order['quantity']) != Decimal(prepared['quantity'])
                or current['digest'] != row['digest']):
            raise ValueError('Emir ile kullanılan plan yetkisi uyuşmuyor.')
        if time.time() >= min(current['approval_until'], timestamp(plan['expires_at'])):
            raise ValueError('Emir gönderilmeden önce yetki süresi doldu.')
        if not price_check(plan, latest['markPrice']):
            raise ValueError('Onaylanmış giriş koşulu artık sağlanmıyor.')
        qty, price = Decimal(order['quantity']), Decimal(latest['markPrice'])
        used = qty * price if plan['sizing']['kind'] == 'NOTIONAL' else qty * (price - Decimal(plan['stop']))
        if used > Decimal(plan['sizing']['amount']):
            raise ValueError('Güncel fiyat onaylanan tutar/risk bütçesini aşıyor.')
        compare_market(latest)

    watcher.engine.entry_guard = guard
    try:
        report = watcher.open(plan['symbol'], prepared=prepared,
                              plan_ref={'plan_id': plan_id, 'version': version, 'digest': row['digest']},
                              entry_id=action_id, session_id=sid)
        service.outcome(plan_id, version, 'MANAGING' if report['status'] == 'protected' else 'NEEDS_REVIEW')
        result.update(state=service.show(plan_id, version)['state'], executed=True, session=report)
        return result
    except Exception:
        service.outcome(plan_id, version, 'NEEDS_REVIEW')
        service.store.halt('Plan yürütmesi tamamlanmadı; yeniden giriş yapmadan kayıtları uzlaştırın.')
        raise
