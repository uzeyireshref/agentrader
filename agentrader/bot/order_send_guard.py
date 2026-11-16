"""Refresh venue filters/references immediately before a new order or amendment."""
import time

from agentrader.bot.order_rules import CONDITIONAL,validate_order
from agentrader.bot.risk import number


def validate_before_send(exchange,proposals,position_mode,max_age_seconds,*,additional_order=True,clock=None):
    clock=time.time if clock is None else clock
    if type(max_age_seconds) not in (int,float) or number(max_age_seconds)<=0:
        raise ValueError('Gönderim doğrulama yaşı geçersiz.')
    start=clock()
    symbols={p['params']['symbol'] for p in proposals}
    if len(symbols)!=1:raise ValueError('Gönderim kontrolü tek sembol gerektirir.')
    symbol=next(iter(symbols))
    info=exchange.get('/fapi/v1/exchangeInfo')
    if not isinstance(info,dict) or not isinstance(info.get('symbols'),list) or any(not isinstance(s,dict) for s in info['symbols']):
        raise ValueError('Gönderim öncesi sembol yanıtı geçersiz.')
    selected=[s for s in info.get('symbols',[]) if s.get('symbol')==symbol]
    if len(selected)!=1:raise ValueError('Gönderim öncesi sembol filtreleri gerekli.')
    metadata=selected[0]
    counts=None
    if any(f.get('filterType') in ('MAX_NUM_ORDERS','MAX_NUM_ALGO_ORDERS') for f in metadata.get('filters',[])):
        normal=exchange.get('/fapi/v1/openOrders',{'symbol':symbol})
        algos=exchange.get('/fapi/v1/openAlgoOrders',{'symbol':symbol})
        if any(not isinstance(rows,list) or any(not isinstance(o,dict) or not isinstance(o.get('symbol'),str) for o in rows) for rows in (normal,algos)):
            raise ValueError('Gönderim öncesi açık emir sayıları doğrulanamadı.')
        counts={'normal':sum(o['symbol']==symbol for o in normal),'algo':sum(o['symbol']==symbol for o in algos)}
    contract=None
    if any(p['params']['type'] in CONDITIONAL and p['params'].get('workingType','CONTRACT_PRICE')=='CONTRACT_PRICE'
           and any(k in p['params'] for k in ('triggerPrice','activatePrice')) for p in proposals):
        contract=exchange.get('/fapi/v2/ticker/price',{'symbol':symbol})
    mark=exchange.get('/fapi/v1/premiumIndex',{'symbol':symbol})
    end=clock();now=int(end*1000)+getattr(exchange,'offset_ms',0)
    if (not 0<=end-start<=max_age_seconds or not isinstance(mark,dict) or mark.get('symbol')!=symbol or
            type(mark.get('time')) is not int or not -1000<=now-mark['time']<=max_age_seconds*1000):
        raise ValueError('Gönderim öncesi fiyat/görünüm eskidi veya sembolü uyuşmuyor.')
    for proposal in proposals:
        validate_order(proposal['params'],metadata,position_mode,proposal['operation'],mark.get('markPrice'),now,
                       contract_price=contract,order_counts=counts,additional_order=additional_order,max_age_seconds=max_age_seconds)
        if counts is not None and additional_order:
            counts['algo' if proposal['params']['type'] in CONDITIONAL else 'normal']+=1
