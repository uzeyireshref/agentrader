"""Fresh flat-account risk and executable parameter preparation for plan v2.

Multi-assets totals are USD values, not coin amounts. Restrict new capacity to
verified USDT collateral and convert the aggregate USD ceiling conservatively.
No settings or orders are changed here.
"""
from .history import income_history
from .brackets import select_bracket
import time
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from math import lcm

from .management import split_targets
from .order_rules import validate_order
from .plan_v2 import validate_v2
from .plans import digest
from .portfolio import Exposure, evaluate_portfolio
from .risk import number


def fresh(data, symbol, now_ms, max_age):
    if data.get('symbol') != symbol or type(data.get('time')) is not int:
        raise ValueError('Fiyat sembolü/zamanı eksik.')
    if not -1000 <= now_ms-data['time'] <= max_age*1000:
        raise ValueError('Fiyat veya varlık endeksi eski.')


def collateral_usdt(account, config, index=None):
    multi = config.get('multiAssetsMargin')
    if type(multi) is not bool:
        raise ValueError('Çoklu varlık modu doğrulanamadı.')
    assets = [a for a in account['assets'] if a['asset'] == 'USDT']
    if len(assets) != 1:
        raise ValueError('USDT teminat kaydı gerekli.')
    asset = assets[0]
    available = number(asset['availableBalance'])
    if multi:
        if asset.get('marginAvailable') is not True or index is None:
            raise ValueError('USDT teminat uygunluğu/endeksi gerekli.')
        # USD needed to acquire one USDT: use the larger quoted rate.
        rate = max(number(index['index']), number(index['askRate']))
        if rate <= 0 or number(index['index']) <= 0 or number(index['askRate']) <= 0:
            raise ValueError('USDT/USD dönüşüm fiyatı geçersiz.')
        ceiling = number(account['availableBalance']) / rate
    else:
        ceiling = number(account['availableBalance'])
    value = min(available, ceiling)
    if value <= 0:
        raise ValueError('Doğrulanmış kullanılabilir USDT teminatı yok.')
    return value


def collect_flat_snapshot(exchange, symbol, limits, clock=time.time, *, ownership=None):
    start = clock()
    exchange.sync_time()
    config = exchange.get('/fapi/v1/accountConfig')
    if config.get('canTrade') is not True:
        raise ValueError('Hesap işlem uygunluğu doğrulanamadı.')
    mode = exchange.get('/fapi/v1/positionSide/dual')
    if type(mode.get('dualSidePosition')) is not bool:
        raise ValueError('Pozisyon modu doğrulanamadı.')
    account = exchange.get('/fapi/v3/account')
    positions = exchange.get('/fapi/v3/positionRisk')
    normal = exchange.get('/fapi/v1/openOrders')
    algos = exchange.get('/fapi/v1/openAlgoOrders')
    flat=not (any(number(p['positionAmt']) for p in account['positions']+positions) or normal or algos)
    proof=None
    if ownership is None:
        if not flat:raise ValueError('İlk v2 yürütmesi için hesap pozisyonsuz ve emirsiz olmalı.')
    else:
        proof=ownership.verify(positions=positions,normal=normal,algos=algos,account_positions=account['positions'])
        if (any(s['symbol']==symbol for s in proof['sessions']) or
                any(p['symbol']==symbol and number(p['positionAmt']) for p in positions) or
                any(o['symbol']==symbol for o in normal+algos) or
                any(not s['protected'] for s in proof['sessions'])):
            raise ValueError('Yeni sembol boş olmalı; eş oturumların etkin stop koruması gerekli.')
    settings = exchange.get('/fapi/v1/symbolConfig', {'symbol': symbol})
    selected = [s for s in settings if s['symbol'] == symbol]
    if len(selected) != 1:
        raise ValueError('Sembol hesap ayarı doğrulanamadı.')
    brackets = exchange.get('/fapi/v1/leverageBracket', {'symbol': symbol})
    brackets = [brackets] if isinstance(brackets, dict) else brackets
    selected_brackets = [b for b in brackets if b['symbol'] == symbol]
    if len(selected_brackets) != 1 or number(selected_brackets[0].get('notionalCoef', 1)) != 1:
        raise ValueError('Kaldıraç basamağı veya özel çarpanı ayrıca doğrulanmalı.')
    info = exchange.get('/fapi/v1/exchangeInfo')
    symbols = [s for s in info['symbols'] if s['symbol'] == symbol]
    if len(symbols) != 1:
        raise ValueError('Sembol filtreleri gerekli.')
    midnight = datetime.fromtimestamp(start, timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    incomes = income_history(exchange, int(midnight.timestamp()*1000))
    relevant = [r for r in incomes if r['incomeType'] in ('REALIZED_PNL', 'COMMISSION', 'FUNDING_FEE')]
    if any(r['asset'] != 'USDT' for r in relevant):
        raise ValueError('Günlük sonuçların varlık dönüşümü gerekli.')
    pnl = sum((number(r['income']) for r in relevant), Decimal(0))
    if proof is not None and any(number(s['amount']) for s in proof['sessions']):
        usdt=[a for a in account['assets'] if a['asset']=='USDT']
        if len(usdt)!=1 or 'unrealizedProfit' not in usdt[0]:
            raise ValueError('Çoklu oturum günlük riski için USDT gerçekleşmemiş sonuç gerekli.')
        pnl+=min(number(usdt[0]['unrealizedProfit']),Decimal(0))
    index = exchange.get('/fapi/v1/assetIndex', {'symbol': 'USDTUSD'}) if config['multiAssetsMargin'] else None
    if index is not None and not isinstance(index, dict):
        raise ValueError('Tek USDTUSD endeksi bekleniyor.')
    mark = exchange.get('/fapi/v1/premiumIndex', {'symbol': symbol})
    end = clock()
    now_ms = int(end*1000) + getattr(exchange, 'offset_ms', 0)
    fresh(mark, symbol, now_ms, limits.max_age_seconds)
    if index is not None:
        fresh(index, 'USDTUSD', now_ms, limits.max_age_seconds)
    if not 0 <= end-start <= limits.max_age_seconds:
        raise ValueError('Hesap görünümü toplanırken eskidi.')
    if datetime.fromtimestamp(end, timezone.utc).date() != midnight.date():
        raise ValueError('Gün değişti; günlük kayıp görünümü yenilenmeli.')
    return {'symbol_info': symbols[0], 'mark': mark, 'settings': selected[0],
            'position_mode': 'hedge' if mode['dualSidePosition'] else 'one-way',
            'multi_assets': config['multiAssetsMargin'],
            'collateral': str(collateral_usdt(account, config, index)),
            'daily_loss': str(max(-pnl, Decimal(0))),
            'brackets': selected_brackets[0]['brackets'], 'observed_at': start,
            'finished_at': end, 'now_ms': now_ms, 'flat_verified': flat,
            'target_flat_verified':True,'ownership_verified':proof is not None,
            'ownership_digest':proof['digest'] if proof else None}


def joint_step(*steps):
    steps = [number(s) for s in steps if number(s) > 0]
    if not steps:
        raise ValueError('Pozitif miktar adımı gerekli.')
    scale = 10 ** max(max(-s.as_tuple().exponent, 0) for s in steps)
    return Decimal(lcm(*(int(s*scale) for s in steps))) / scale


def prepare_single(plan, snapshot, limits, now=None):
    validate_v2(plan)
    if plan['execution']['strategy'] != 'SINGLE':
        raise ValueError('Grid için ayrı rezervasyon ve yürütme gerekli.')
    if snapshot.get('flat_verified') is not True and not (snapshot.get('target_flat_verified') is True and snapshot.get('ownership_verified') is True):
        raise ValueError('Boş hesap kanıtı gerekli.')
    now = time.time() if now is None else now
    if not 0 <= now-snapshot['observed_at'] <= limits.max_age_seconds:
        raise ValueError('Hesap görünümü eskidi.')
    if snapshot['position_mode'] != plan['position_mode']:
        raise ValueError('Hesap pozisyon modu planla uyuşmuyor.')
    settings = snapshot['settings']
    if (int(settings['leverage']) != plan['execution']['leverage']
            or settings['marginType'] != plan['execution']['margin_mode']):
        raise ValueError('Kaldıraç/teminat ayarı planla uyuşmuyor; otomatik değiştirilmedi.')
    info, mark = snapshot['symbol_info'], snapshot['mark']
    if info.get('quoteAsset') != 'USDT' or info.get('contractType', 'PERPETUAL') != 'PERPETUAL':
        raise ValueError('USDT perpetual sözleşmesi gerekli.')
    if info['symbol'] != plan['symbol'] or mark['symbol'] != plan['symbol']:
        raise ValueError('Plan ve görünüm sembolü uyuşmuyor.')
    price = number(mark['markPrice'])
    direction = 1 if plan['direction'] == 'LONG' else -1
    stop = number(plan['stop'])
    condition = plan['entry']['condition']
    trigger = number(plan['entry']['trigger_price']) if plan['entry']['trigger_price'] is not None else None
    if condition == 'MARK_AT_OR_BELOW' and price > trigger or condition == 'MARK_AT_OR_ABOVE' and price < trigger:
        return {'state': 'WAITING_CONDITION', 'execution_authorized': False}
    entry = trigger if condition == 'LIMIT' else price
    for value in (price, entry):
        if direction*(value-stop) <= 0 or direction*(number(plan['targets'][0]['price'])-value) <= 0:
            raise ValueError('Fiyat stop ve hedef aralığı dışında.')
        if abs(value-number(plan['entry']['reference_price']))/number(plan['entry']['reference_price'])*10000 > number(plan['entry']['max_drift_bps']):
            raise ValueError('Fiyat onaylı tolerans dışında.')
    filters = {f['filterType']: f for f in info['filters']}
    lot = filters['LOT_SIZE']
    market_lot = filters.get('MARKET_LOT_SIZE', lot)
    step = joint_step(lot['stepSize'], market_lot['stepSize'])
    amount = number(plan['sizing']['amount'])
    leverage = plan['execution']['leverage']
    # Reserve drift and round-trip fees inside every requested budget.
    fee = Decimal('.001')
    worst_price = max(entry, price) * (1+number(plan['entry']['max_drift_bps'])/10000)
    kind = plan['sizing']['kind']
    unit_cost = worst_price if kind == 'NOTIONAL' else (
        worst_price/leverage+worst_price*fee*2 if kind == 'MARGIN'
        else max(abs(entry-stop), abs(worst_price-stop),
                 abs(min(entry, price)*(1-number(plan['entry']['max_drift_bps'])/10000)-stop)) + worst_price*fee*2)
    quantity = (amount/unit_cost/step).to_integral_value(rounding=ROUND_FLOOR)*step
    if quantity <= 0:
        raise ValueError('Bütçe geçerli miktara yetmiyor.')
    notional = quantity*worst_price
    tier = select_bracket(snapshot['brackets'],notional,leverage)
    # Evaluate adverse LONG and SHORT entry separately; SHORT loss grows when entry falls.
    risk_entry = worst_price if direction == 1 else min(entry, price)*(1-number(plan['entry']['max_drift_bps'])/10000)
    exposure = Exposure(plan['symbol'], plan['direction'], str(quantity), str(risk_entry),
                        plan['stop'], leverage, plan['execution']['margin_mode'],
                        str(tier['maintMarginRatio']), '0', notional_price=str(worst_price))
    risk = evaluate_portfolio([exposure], snapshot['collateral'], snapshot['daily_loss'],
                              snapshot['observed_at'], now, limits,
                              collateral_valuation_verified=True)
    worst_margin = notional/leverage + notional*fee*2
    worst_loss = quantity*abs(risk_entry-stop) + notional*fee*2
    if worst_margin > number(snapshot['collateral']):
        raise ValueError('En yüksek nominalde teminat ve masraf rezervi yetersiz.')
    if kind == 'MAX_LOSS' and worst_loss > amount or kind == 'MARGIN' and worst_margin > amount:
        raise ValueError('Güncel fiyat rezervi onaylanan bütçeyi aşıyor.')
    # SHORT adverse entry reduces nominal; enforce the high-price ceiling separately.
    if notional > limits.max_notional:
        raise ValueError('Nominal üst sınırı aşılıyor.')
    side = 'BUY' if direction == 1 else 'SELL'
    ps = 'BOTH' if plan['position_mode'] == 'one-way' else plan['direction']
    order = {'symbol': plan['symbol'], 'side': side, 'positionSide': ps,
             'type': 'LIMIT' if condition == 'LIMIT' else 'MARKET', 'quantity': str(quantity)}
    if condition == 'LIMIT':
        order.update(price=str(entry), timeInForce='GTC')
    proposal = validate_order(order, info, plan['position_mode'], 'OPEN', price, snapshot['now_ms'])
    targets = split_targets(str(quantity), plan['targets'],
                            {'market': market_lot | {'stepSize': str(step)}, 'lot': lot})
    exit_side = 'SELL' if direction == 1 else 'BUY'
    protections = []
    for kind_, value in (('STOP_MARKET', plan['stop']), ('TAKE_PROFIT_MARKET', plan['targets'][-1]['price'])):
        params = {'symbol': plan['symbol'], 'side': exit_side, 'positionSide': ps,
                  'type': kind_, 'closePosition': 'true', 'triggerPrice': value,
                  'workingType': 'MARK_PRICE'}
        protections.append(validate_order(params, info, plan['position_mode'], 'CLOSE', price, snapshot['now_ms']))
    return {'state': 'READY', 'plan_digest': digest(plan), 'quantity': str(quantity),
            'notional_ceiling': str(notional), 'risk': risk, 'entry': proposal,
            'targets': targets, 'protections': protections, 'exposures':[asdict(exposure)],'execution_authorized': False}
