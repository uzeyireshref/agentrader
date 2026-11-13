"""Compile bounded v2 LONG/SHORT arithmetic/geometric grid envelopes."""
import time
from dataclasses import asdict
from decimal import Decimal, ROUND_FLOOR

from .grid import arithmetic_levels
from .plan_v2 import validate_v2
from .plans import digest
from .portfolio import Exposure, evaluate_portfolio
from .brackets import select_bracket
from .risk import number
from .v2_preflight import joint_step


def compile_grid(plan, snapshot, limits, now=None):
    validate_v2(plan)
    if plan['execution']['strategy'] != 'GRID' or plan['entry']['condition'] == 'LIMIT' or len(plan['targets']) != 1:
        raise ValueError('Grid tek son hedef ve piyasa başlangıcı gerektirir.')
    now = time.time() if now is None else now
    empty=(snapshot.get('flat_verified') is True or
           (snapshot.get('target_flat_verified') is True and snapshot.get('ownership_verified') is True))
    if not empty or not 0 <= now-snapshot['observed_at'] <= limits.max_age_seconds:
        raise ValueError('Grid için taze ve boş hesap görünümü gerekli.')
    if snapshot['position_mode'] != plan['position_mode']:
        raise ValueError('Grid pozisyon modu planla uyuşmuyor.')
    settings = snapshot['settings']
    leverage = plan['execution']['leverage']
    if int(settings['leverage']) != leverage or settings['marginType'] != plan['execution']['margin_mode']:
        raise ValueError('Grid kaldıraç/teminat ayarı planla uyuşmuyor.')
    info = snapshot['symbol_info']
    if info['symbol'] != plan['symbol'] or info['status'] != 'TRADING' or info.get('quoteAsset') != 'USDT' or info.get('contractType', 'PERPETUAL') != 'PERPETUAL':
        raise ValueError('Grid için USDT perpetual filtreleri gerekli.')
    mark = snapshot['mark']
    if mark['symbol'] != plan['symbol']:
        raise ValueError('Grid mark sembolü uyuşmuyor.')
    price, ref, stop = map(number, (mark['markPrice'], plan['entry']['reference_price'], plan['stop']))
    condition = plan['entry']['condition']
    trigger = number(plan['entry']['trigger_price']) if plan['entry']['trigger_price'] is not None else None
    if condition == 'MARK_AT_OR_BELOW' and price > trigger or condition == 'MARK_AT_OR_ABOVE' and price < trigger:
        return {'state': 'WAITING_CONDITION', 'execution_authorized': False}
    sign = 1 if plan['direction'] == 'LONG' else -1
    if sign*(price-stop) <= 0 or sign*(number(plan['targets'][0]['price'])-price) <= 0:
        raise ValueError('Grid başlangıç fiyatı stop/son hedef aralığı dışında.')
    if abs(price-ref)/ref*10000 > number(plan['entry']['max_drift_bps']):
        raise ValueError('Grid başlangıç fiyatı onaylanan tolerans dışında.')
    g = plan['grid'];lo,hi = number(g['lower']),number(g['upper']);count=g['intervals']
    if not lo <= price < hi:
        raise ValueError('Grid başlangıç fiyatı bandın dışında.')
    target = number(plan['targets'][0]['price'])
    if sign == 1 and target < hi or sign == -1 and target > lo:
        raise ValueError('Son hedef gridin çıkış sınırının dışında veya üzerinde olmalı.')
    filters={f['filterType']:f for f in info['filters']}
    pf=filters['PRICE_FILTER'];tick=number(pf['tickSize']);lot=filters['LOT_SIZE']
    market=filters.get('MARKET_LOT_SIZE',lot)
    step=joint_step(lot['stepSize'],market['stepSize'])
    if g['spacing']=='ARITHMETIC':
        levels=arithmetic_levels(lo,hi,count)
    else:
        ratio=(hi/lo)**(Decimal(1)/count)
        levels=[lo]+[(lo*ratio**i/tick).to_integral_value(rounding=ROUND_FLOOR)*tick for i in range(1,count)]+[hi]
    for p in [*levels,stop,target]:
        if p%tick or not number(pf['minPrice'])<=p<=number(pf['maxPrice']):
            raise ValueError('Grid fiyatları tick/aralık filtresine uymuyor.')
    if any(a>=b for a,b in zip(levels,levels[1:])):
        raise ValueError('Tick yuvarlaması grid seviyelerini birleştiriyor.')
    fee=Decimal('.001');amount=number(plan['sizing']['amount']);kind=plan['sizing']['kind']
    valuation_price=max(hi,stop,target)
    peak_unit=valuation_price*count
    adverse_entry=hi if sign==1 else lo
    loss_unit=abs(adverse_entry-stop)*count+peak_unit*fee*2
    unit=peak_unit if kind=='NOTIONAL' else (peak_unit/leverage+peak_unit*fee*2 if kind=='MARGIN' else loss_unit)
    q=(amount/unit/step).to_integral_value(rounding=ROUND_FLOOR)*step
    minimum=number(filters['MIN_NOTIONAL']['notional'])
    minimum_entry=min(levels[:-1] if sign==1 else levels[1:])
    if q<=0 or q*minimum_entry<minimum or not number(lot['minQty'])<=q<=number(lot['maxQty']):
        raise ValueError('Grid bütçesi hücre başına minimum nominal/lot tutarını karşılamıyor.')
    notional=q*peak_unit
    if notional>limits.max_notional:raise ValueError('Grid toplam nominal sınırı aşılıyor.')
    tier=select_bracket(snapshot['brackets'],notional,leverage)
    exposure=Exposure(plan['symbol'],plan['direction'],str(q*count),str(adverse_entry),plan['stop'],
                      leverage,plan['execution']['margin_mode'],str(tier['maintMarginRatio']),'0',
                      notional_price=str(valuation_price))
    risk=evaluate_portfolio([exposure],snapshot['collateral'],snapshot['daily_loss'],snapshot['observed_at'],
                            now,limits,collateral_valuation_verified=True)
    if notional/leverage+notional*fee*2>number(snapshot['collateral']):
        raise ValueError('Grid teminat/masraf rezervi yetersiz.')
    slots=[{'index':i,'lower':str(a),'upper':str(b),'quantity':str(q),
            'seed':a>=price if sign==1 else b<=price} for i,(a,b) in enumerate(zip(levels,levels[1:]))]
    seed=q*sum(c['seed'] for c in slots)
    if seed and (not number(market['minQty'])<=seed<=number(market['maxQty']) or seed%step):
        raise ValueError('Toplam grid başlangıç miktarı MARKET lot filtresine uymuyor.')
    core={'plan_digest':digest(plan),'slots':slots,'seed_quantity':str(seed),'notional_ceiling':str(notional),
          'exposures':[asdict(exposure)]}
    return core | {'state':'READY','compiled_digest':digest(core),'risk':risk,
                   'execution_authorized':False,'geometric_rounding':'FLOOR_TO_TICK' if g['spacing']=='GEOMETRIC' else None}
