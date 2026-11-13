"""A single authorized hedge plan with explicit LONG/SHORT budget shares."""
import copy
import time
from dataclasses import asdict
from decimal import Decimal, ROUND_FLOOR,localcontext

from .brackets import select_bracket
from .grid import arithmetic_levels
from .plans import exact_fields,positive,digest
from .portfolio import Exposure,evaluate_portfolio
from .risk import number
from .v2_preflight import joint_step


def validate_neutral(plan):
    exact_fields(plan,'schema_version plan_id version environment exchange product symbol position_mode direction mode created_at expires_at entry sizing stop targets management max_runs analysis_ref rationale execution grid','Neutral plan')
    if not isinstance(plan.get('execution'),dict) or not isinstance(plan.get('entry'),dict):
        raise ValueError('Neutral yürütme/giriş nesneleri gerekli.')
    if plan['entry'].get('condition')=='LIMIT':
        raise ValueError('Neutral başlangıç LIMIT tohumu kullanmaz; hücre limitleri derlemede oluşturulur.')
    if (plan.get('direction')!='NEUTRAL' or plan.get('position_mode')!='hedge' or
            plan.get('execution',{}).get('strategy')!='NEUTRAL_GRID'):
        raise ValueError('Neutral grid tek NEUTRAL planı ve hedge modu gerektirir.')
    exact_fields(plan.get('stop'),'lower upper','Neutral stop sınırları')
    exact_fields(plan.get('grid'),'lower upper intervals spacing anchor_price long_fraction short_fraction','Neutral grid')
    g=plan['grid'];lo,hi,anchor=map(lambda k:positive(g[k],k),('lower','upper','anchor_price'))
    low_stop,high_stop=positive(plan['stop']['lower'],'Alt stop'),positive(plan['stop']['upper'],'Üst stop')
    if not low_stop<lo<anchor<hi<high_stop or positive(plan['entry']['reference_price'],'Referans')!=anchor:
        raise ValueError('Neutral merkez referansla eşit; stoplar bandın dışında olmalı.')
    if type(g['intervals'])is not int or not 2<=g['intervals']<=20:
        raise ValueError('İlk neutral kapsamı 2–20 grid aralığı destekler.')
    if positive(g['long_fraction'],'LONG payı')+positive(g['short_fraction'],'SHORT payı')!=1:
        raise ValueError('Neutral tarafların bütçe payları toplamı 1 olmalı.')
    if plan.get('targets')!=[]:
        raise ValueError('Neutral çıkışları hücre hedefleri ve iki global stop sınırıyla tanımlanır; targets boş olmalı.')
    if not isinstance(plan.get('management'),dict) or plan['management'].get('trailing') is not None:
        raise ValueError('Neutral takip stopu bu kapsamda desteklenmiyor.')
    # Reuse all v2 identity, authorization, expiry, sizing and grid cycle rules.
    # These copies are validation views, never independent grants or sessions.
    from .plan_v2 import validate_v2
    for side in ('LONG','SHORT'):
        child=copy.deepcopy(plan);child['direction']=side;child['execution']['strategy']='GRID'
        child['grid']={k:g[k] for k in ('lower','upper','intervals','spacing')}
        child['stop']=plan['stop']['lower' if side=='LONG' else 'upper']
        child['targets']=[{'price':plan['stop']['upper' if side=='LONG' else 'lower'],'fraction':'1'}]
        validate_v2(child)
    return plan


def compile_neutral(plan,snapshot,limits,now=None):
    validate_neutral(plan)
    now=time.time() if now is None else now
    if not (snapshot.get('flat_verified') is True or
            snapshot.get('target_flat_verified') is True and snapshot.get('ownership_verified') is True):
        raise ValueError('Neutral için sembolün boş ve hesabın sahipliğinin doğrulanmış olması gerekli.')
    if not 0<=now-snapshot['observed_at']<=limits.max_age_seconds or snapshot['position_mode']!='hedge':
        raise ValueError('Taze hedge hesap görünümü gerekli; hesap modu otomatik değiştirilmez.')
    settings=snapshot['settings'];execution=plan['execution']
    if int(settings['leverage'])!=execution['leverage'] or settings['marginType']!=execution['margin_mode']:
        raise ValueError('Neutral kaldıraç/teminat ayarı planla uyuşmuyor.')
    info=snapshot['symbol_info'];mark=snapshot['mark'];price=number(mark['markPrice'])
    if (info['symbol']!=plan['symbol'] or mark['symbol']!=plan['symbol'] or info['status']!='TRADING' or
            info.get('quoteAsset')!='USDT' or info.get('contractType','PERPETUAL')!='PERPETUAL'):
        raise ValueError('Neutral için USDT perpetual filtreleri gerekli.')
    entry=plan['entry'];trigger=number(entry['trigger_price']) if entry['trigger_price'] is not None else None
    if entry['condition']=='LIMIT':raise ValueError('Neutral başlangıç LIMIT tohumu kullanmaz.')
    if (entry['condition']=='MARK_AT_OR_BELOW' and price>trigger or
            entry['condition']=='MARK_AT_OR_ABOVE' and price<trigger):
        return {'state':'WAITING_CONDITION','execution_authorized':False}
    g=plan['grid'];lo,hi,anchor=map(number,(g['lower'],g['upper'],g['anchor_price']))
    if not lo<price<hi or abs(price-anchor)/anchor*10000>number(entry['max_drift_bps']):
        raise ValueError('Neutral başlangıç fiyatı bant veya onaylı tolerans dışında.')
    filters={f['filterType']:f for f in info['filters']};pf=filters['PRICE_FILTER'];tick=number(pf['tickSize'])
    lot=filters['LOT_SIZE'];market=filters.get('MARKET_LOT_SIZE',lot);step=joint_step(lot['stepSize'],market['stepSize'])
    count=g['intervals']
    if g['spacing']=='ARITHMETIC':levels=arithmetic_levels(lo,hi,count)
    else:
        with localcontext() as context:
            context.prec=40
            levels=[lo]+[(lo*(hi/lo)**(Decimal(i)/count)/tick).to_integral_value(rounding=ROUND_FLOOR)*tick for i in range(1,count)]+[hi]
    for p in [*levels,number(plan['stop']['lower']),number(plan['stop']['upper'])]:
        if p%tick or not number(pf['minPrice'])<=p<=number(pf['maxPrice']):
            raise ValueError('Neutral fiyat adımı/aralığı geçersiz.')
    if anchor not in levels[1:-1] or any(a>=b for a,b in zip(levels,levels[1:])):
        raise ValueError('Neutral merkez iç grid seviyelerinden biri olmalı; yuvarlama seviyeleri birleştiremez.')
    slots=[{'index':i,'lower':str(a),'upper':str(b),'position_side':'LONG' if b<=anchor else 'SHORT'}
           for i,(a,b) in enumerate(zip(levels,levels[1:]))]
    valuation=number(plan['stop']['upper']);fee=number('.001');quantities={};budgets={}
    for side in ('LONG','SHORT'):
        side_slots=[c for c in slots if c['position_side']==side];n=len(side_slots)
        amount=number(plan['sizing']['amount'])*number(g['long_fraction' if side=='LONG' else 'short_fraction'])
        budgets[side]=str(amount);stop=number(plan['stop']['lower' if side=='LONG' else 'upper'])
        nominal_unit=valuation*n
        unit=(nominal_unit if plan['sizing']['kind']=='NOTIONAL' else
              nominal_unit/execution['leverage']+nominal_unit*fee*2 if plan['sizing']['kind']=='MARGIN' else
              n*abs(anchor-stop)+nominal_unit*fee*2)
        q=(amount/unit/step).to_integral_value(rounding=ROUND_FLOOR)*step
        for rule in (lot,market):
            rule_step=number(rule['stepSize'])
            if q<=0 or not number(rule['minQty'])<=q<=number(rule['maxQty']) or rule_step>0 and q%rule_step:
                raise ValueError('Neutral taraf bütçesi geçerli hücre lotuna yetmiyor.')
        if q*n>number(market['maxQty']):
            raise ValueError('Neutral tarafın toplam kapanış miktarı MARKET lotunu aşıyor.')
        if any(q*number(c['lower' if side=='LONG' else 'upper'])<number(filters['MIN_NOTIONAL']['notional']) for c in side_slots):
            raise ValueError('Neutral bütçe hücre başına minimum nominali karşılamıyor; bütçe artırılmadı.')
        quantities[side]=q
    for c in slots:c['quantity']=str(quantities[c['position_side']])
    total=sum((number(c['quantity'])*valuation for c in slots),number(0))
    tier=select_bracket(snapshot['brackets'],total,execution['leverage'])
    exposures=[Exposure(plan['symbol'],side,str(quantities[side]*sum(c['position_side']==side for c in slots)),
                str(anchor),plan['stop']['lower' if side=='LONG' else 'upper'],execution['leverage'],
                execution['margin_mode'],str(tier['maintMarginRatio']),'0',notional_price=str(valuation)) for side in ('LONG','SHORT')]
    risk=evaluate_portfolio(exposures,snapshot['collateral'],snapshot['daily_loss'],snapshot['observed_at'],now,
                            limits,collateral_valuation_verified=True)
    if number(risk['risk_with_fee_reserve'])>limits.max_trade_loss:
        raise ValueError('Neutral planın iki tarafının toplam stop/masraf riski işlem sınırını aşıyor.')
    core={'plan_digest':digest(plan),'slots':slots,'notional_ceiling':str(total),
          'exposures':[asdict(e) for e in exposures],'budgets':budgets,'anchor_price':str(anchor)}
    return core|{'state':'READY','compiled_digest':digest(core),'risk':risk,'execution_authorized':False}


def neutral_example(amount):
    from .plans import example_plan
    positive(amount,'Örnek toplam bütçe')
    p=example_plan();p.update(schema_version=2,plan_id='demo-neutral-example',direction='NEUTRAL',position_mode='hedge',
        stop={'lower':'76000','upper':'84000'},targets=[],execution={'strategy':'NEUTRAL_GRID','leverage':20,'margin_mode':'CROSSED'})
    p['sizing']['amount']=amount;p['entry'].update(condition='IMMEDIATE',trigger_price=None)
    p['management'].update(allow_scale_in=True,allow_reentry=True)
    p['grid']={'lower':'78000','upper':'82000','intervals':4,'spacing':'ARITHMETIC','anchor_price':'80000',
               'long_fraction':'.5','short_fraction':'.5'}
    p['rationale']='Örnek şemadır; fiyatlar işlem önerisi değildir. Yazdırma emir veya kullanıcı onayı oluşturmaz.'
    return validate_neutral(p)
