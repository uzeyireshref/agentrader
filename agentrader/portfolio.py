"""Decimal portfolio risk for leveraged LONG/SHORT inventory and pending entries.

All inputs must come from a fresh, reconciled account snapshot. Pending reductions
never release margin or risk before their fills. This evaluator does not submit orders.
"""
from dataclasses import dataclass
from decimal import Decimal

from .risk import RiskLimits,number


@dataclass(frozen=True)
class Exposure:
    symbol: str
    direction: str
    quantity: str
    entry: str
    stop: str
    leverage: int
    margin_mode: str
    maintenance_ratio: str
    maintenance_deduction: str = '0'
    extra_isolated_margin: str = '0'
    notional_price: str | None = None


def liquidation_price(direction,quantity,entry,margin,maintenance_ratio,deduction='0'):
    q,e,m,r,d=map(number,(quantity,entry,margin,maintenance_ratio,deduction))
    if q<=0 or e<=0 or m<0 or not 0<=r<1 or d<0:
        raise ValueError('Likidasyon girdileri geçersiz.')
    if direction=='LONG': return max(Decimal(0),(q*e-m-d)/(q*(1-r)))
    if direction=='SHORT': return (q*e+m+d)/(q*(1+r))
    raise ValueError('Yön LONG veya SHORT olmalı.')


def evaluate_portfolio(exposures,available_collateral,daily_loss,observed_at,now,
                       limits=RiskLimits(),fee_rate='0.001',liquidation_buffer_bps='25',
                       *,collateral_valuation_verified=False):
    if not collateral_valuation_verified:
        raise ValueError('Çoklu varlık/teminat değerlemesi doğrulanmadan giriş yapılamaz.')
    collateral,day,fee,buffer=map(number,(available_collateral,daily_loss,fee_rate,liquidation_buffer_bps))
    if collateral<=0 or day<0 or not 0<=fee<=Decimal('.1') or not 0<=buffer<=1000:
        raise ValueError('Portföy girdileri geçersiz.')
    if not 0<=number(now)-number(observed_at)<=limits.max_age_seconds:
        raise ValueError('Portföy görünümü eski veya gelecekte.')
    if not exposures: raise ValueError('En az bir maruziyet gerekli.')
    groups={}
    for leg in exposures:
        if leg.direction not in ('LONG','SHORT') or leg.margin_mode not in ('CROSSED','ISOLATED'):
            raise ValueError('Desteklenmeyen yön veya teminat modu.')
        if type(leg.leverage) is not int or not 1<=leg.leverage<=125:
            raise ValueError('Kaldıraç geçersiz.')
        q,e,s,r,d,extra=map(number,(leg.quantity,leg.entry,leg.stop,leg.maintenance_ratio,
                                   leg.maintenance_deduction,leg.extra_isolated_margin))
        if min(q,e,s)<=0 or not 0<=r<1 or d<0 or extra<0:
            raise ValueError('Maruziyet geçersiz.')
        valuation=number(leg.notional_price)if leg.notional_price is not None else e
        if valuation<e or valuation<=0:raise ValueError('Nominal değerleme fiyatı girişin altında olamaz.')
        if (leg.direction=='LONG' and s>=e) or (leg.direction=='SHORT' and s<=e):
            raise ValueError('Stop yönle uyumsuz.')
        key=(leg.symbol,leg.direction)
        profile=(leg.leverage,leg.margin_mode,r,d)
        group=groups.setdefault(key,{'profile':profile,'qty':Decimal(0),'cost':Decimal(0),
                                    'loss':Decimal(0),'valuation':Decimal(0),'stops':[],'extra':Decimal(0)})
        if group['profile']!=profile:
            raise ValueError('Aynı pozisyonda çelişen kaldıraç/teminat/basamak bilgisi.')
        group['qty']+=q;group['cost']+=q*e;group['loss']+=q*abs(e-s)
        group['valuation']+=q*valuation
        group['stops'].append(s);group['extra']+=extra
    total=sum(g['valuation'] for g in groups.values())
    loss=sum(g['loss'] for g in groups.values())
    margin=sum(g['valuation']/g['profile'][0]+g['extra'] for g in groups.values())
    fees=total*fee*2
    if total>limits.max_notional: raise ValueError('Toplam nominal tutar sınırı.')
    if len(groups)>limits.max_positions: raise ValueError('Pozisyon sayısı sınırı.')
    if any(g['loss']+g['valuation']*fee*2>limits.max_trade_loss for g in groups.values()):
        raise ValueError('İşlem başına stop ve masraf bütçesi.')
    if loss+fees>limits.max_total_loss: raise ValueError('Toplam açık risk bütçesi.')
    if day+loss+fees>limits.max_daily_loss: raise ValueError('Günlük kayıp bütçesi.')
    if margin+fees>collateral: raise ValueError('Başlangıç teminatı ve masraf rezervi yetersiz.')
    isolated=sum(g['valuation']/g['profile'][0]+g['extra'] for g in groups.values() if g['profile'][1]=='ISOLATED')
    cross_total=sum(g['cost'] for g in groups.values() if g['profile'][1]=='CROSSED')
    results=[]
    for (symbol,direction),g in groups.items():
        leverage,mode,mmr,deduction=g['profile']
        allocation=(g['cost']/leverage+g['extra'] if mode=='ISOLATED'
                    else (collateral-isolated-fees)*g['cost']/cross_total)
        liq=liquidation_price(direction,g['qty'],g['cost']/g['qty'],allocation,mmr,deduction)
        # Require every authorized stop to precede liquidation, conservatively.
        safe=(min(g['stops'])>liq*(1+buffer/10000) if direction=='LONG'
              else max(g['stops'])<liq*(1-buffer/10000))
        if not safe: raise ValueError('Stop likidasyondan önce güvenli tamponla çalışmıyor.')
        results.append({'symbol':symbol,'direction':direction,'notional':str(g['valuation']),
                        'estimated_liquidation':str(liq),'margin_mode':mode})
    return {'notional':str(total),'initial_margin':str(margin),'fee_reserve':str(fees),
            'stop_loss_excluding_costs':str(loss),'risk_with_fee_reserve':str(loss+fees),
            'positions':results,'warning':'Likidasyon hesabı modeldir; borsa basamağı/teminat verisi güncel doğrulanmalıdır.'}
