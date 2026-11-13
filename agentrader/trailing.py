"""Deterministic mark-price trailing policy; existing plans remain disabled."""
from decimal import ROUND_CEILING, ROUND_FLOOR

from .risk import number


def advance_trailing(policy, direction, mark, tick, current_stop, state=None):
    sign=1 if direction=='LONG' else -1
    if direction not in ('LONG','SHORT'):
        raise ValueError('Takip yönü geçersiz.')
    price,step,previous=map(number,(mark,tick,current_stop))
    if min(price,step,previous)<=0:
        raise ValueError('Takip fiyat/adım/stop verisi geçersiz.')
    state=dict(state or {})
    watermark=number(state.get('watermark',price))
    watermark=max(watermark,price) if sign==1 else min(watermark,price)
    active=state.get('active',False) or sign*(watermark-number(policy['activation_price']))>=0
    state.update(watermark=str(watermark),active=active)
    if not active:
        return state,None
    raw=watermark*(1-sign*number(policy['distance_bps'])/10000)
    trigger=(raw/step).to_integral_value(rounding=ROUND_FLOOR if sign==1 else ROUND_CEILING)*step
    if trigger<=0:
        raise ValueError('Takip stop fiyatı adımla ifade edilemiyor.')
    improvement=sign*(trigger-previous)
    if improvement<=0 or improvement/previous*10000<number(policy['min_step_bps']):
        return state,None
    return state,trigger
