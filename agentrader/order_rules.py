"""Unified USD-M order validation for LONG/SHORT, one-way/hedge and protections.

Validation builds request parameters only. Authorization and portfolio ownership
must still be verified by the executor before submitting an order.
"""
import re
from decimal import Decimal

from .risk import number

CONDITIONAL={'STOP','STOP_MARKET','TAKE_PROFIT','TAKE_PROFIT_MARKET','TRAILING_STOP_MARKET'}
TYPES={'LIMIT','MARKET'}|CONDITIONAL


def _flag(value):
    if type(value) is bool:return value
    if value=='true':return True
    if value=='false':return False
    raise ValueError('Boolean emir parametresi geçersiz.')


def validate_order(intent,symbol,position_mode,operation,mark_price,now_ms):
    required={'symbol','side','positionSide','type'}
    optional={'quantity','price','timeInForce','reduceOnly','closePosition','triggerPrice',
              'workingType','priceProtect','activatePrice','callbackRate','newClientOrderId',
              'clientAlgoId','priceMatch','selfTradePreventionMode','goodTillDate','algoType'}
    if not required<=intent.keys() or intent.keys()-required-optional:
        raise ValueError('Emir alanları eksik veya desteklenmiyor.')
    params=dict(intent)
    kind=params['type'];side=params['side'];ps=params['positionSide']
    if kind not in TYPES or side not in ('BUY','SELL') or operation not in ('OPEN','REDUCE','CLOSE'):
        raise ValueError('Emir türü/yönü/işlemi geçersiz.')
    if params['symbol']!=symbol['symbol'] or symbol['status']!='TRADING':
        raise ValueError('Sembol işleme açık değil.')
    if kind not in symbol.get('orderTypes',list(TYPES)):
        raise ValueError('Emir türü bu sözleşmede desteklenmiyor.')
    if position_mode=='one-way':
        if ps!='BOTH':raise ValueError('One-way için BOTH gerekli.')
    elif position_mode=='hedge':
        if ps not in ('LONG','SHORT') or 'reduceOnly' in params:
            raise ValueError('Hedge için LONG/SHORT gerekli; reduceOnly gönderilmez.')
        expected=('BUY' if ps=='LONG' else 'SELL') if operation=='OPEN' else ('SELL' if ps=='LONG' else 'BUY')
        if side!=expected:raise ValueError('Hedge emir yönü işlemle uyuşmuyor.')
    else:raise ValueError('Pozisyon modu geçersiz.')
    close=_flag(params.get('closePosition',False))
    if close and (kind not in ('STOP_MARKET','TAKE_PROFIT_MARKET') or operation=='OPEN'
                  or 'quantity' in params or 'reduceOnly' in params):
        raise ValueError('Close-All miktar/reduceOnly içermez ve yalnız koruyucu piyasa emridir.')
    if position_mode=='one-way' and not close:
        reduce=_flag(params.get('reduceOnly',False))
        if reduce!=(operation!='OPEN'):raise ValueError('Reduce-only işlem amacıyla uyuşmuyor.')
        if 'reduceOnly' in params:params['reduceOnly']=str(reduce).lower()
    filters={f['filterType']:f for f in symbol['filters']}
    pf=filters['PRICE_FILTER'];tick=number(pf['tickSize'])
    mark=number(mark_price)
    if mark<=0:raise ValueError('Güncel mark fiyatı gerekli.')
    def check_price(field):
        value=number(params[field])
        if value<=0 or value%tick or not number(pf['minPrice'])<=value<=number(pf['maxPrice']):
            raise ValueError('Fiyat adımı veya aralığı geçersiz.')
        params[field]=str(value);return value
    for field in ('price','triggerPrice','activatePrice'):
        if field in params:check_price(field)
    if not close:
        if 'quantity' not in params:raise ValueError('Miktar gerekli.')
        q=number(params['quantity'])
        lot=filters.get('MARKET_LOT_SIZE',filters['LOT_SIZE']) if kind=='MARKET' or kind.endswith('_MARKET') else filters['LOT_SIZE']
        for rule in (filters['LOT_SIZE'],lot):
            step=number(rule['stepSize'])
            if not number(rule['minQty'])<=q<=number(rule['maxQty']) or (step>0 and q%step):
                raise ValueError('Miktar adımı veya lot sınırı geçersiz.')
        params['quantity']=str(q)
        if operation=='OPEN' and q*number(params.get('price',mark))<number(filters['MIN_NOTIONAL']['notional']):
            raise ValueError('Yeni emir minimum nominal tutarın altında.')
    if kind in ('LIMIT','STOP','TAKE_PROFIT'):
        if ('price' in params)==('priceMatch' in params):
            raise ValueError('Limit emir için fiyat veya priceMatch gerekli; birlikte kullanılamaz.')
        if params.get('timeInForce') not in ('GTC','IOC','FOK','GTX','GTD'):
            raise ValueError('Limit emir süresi gerekli/desteklenmiyor.')
    elif 'price' in params or 'priceMatch' in params or 'timeInForce' in params:
        raise ValueError('Piyasa emrinde limit fiyat/süre parametresi kullanılamaz.')
    if 'priceMatch' in params and params['priceMatch'] not in (
            'OPPONENT','OPPONENT_5','OPPONENT_10','OPPONENT_20','QUEUE','QUEUE_5','QUEUE_10','QUEUE_20'):
        raise ValueError('priceMatch geçersiz.')
    if params.get('timeInForce')=='GTD':
        expiry=params.get('goodTillDate')
        if type(expiry) is not int or not now_ms+600000<(expiry//1000)*1000<253402300799000:
            raise ValueError('GTD son geçerlilik en az 600 saniye ileride olmalı.')
        params['goodTillDate']=(expiry//1000)*1000
    elif 'goodTillDate' in params:raise ValueError('goodTillDate yalnız GTD ile kullanılır.')
    if kind in CONDITIONAL:
        if params.get('workingType','CONTRACT_PRICE') not in ('MARK_PRICE','CONTRACT_PRICE'):
            raise ValueError('Tetik fiyat türü geçersiz.')
        if kind=='TRAILING_STOP_MARKET':
            if 'triggerPrice' in params or 'callbackRate' not in params:raise ValueError('Trailing stop geri çekilme oranı gerekli.')
            callback=number(params['callbackRate'])
            if not Decimal('.1')<=callback<=5:raise ValueError('Trailing callbackRate doğrulanmış aralık dışında.')
            if 'activatePrice' in params:
                activation=number(params['activatePrice'])
                if (side=='BUY' and activation>=mark) or (side=='SELL' and activation<=mark):
                    raise ValueError('Trailing aktivasyon fiyatı mevcut fiyatın yanlış tarafında.')
        elif 'triggerPrice' not in params:raise ValueError('Koşullu emir tetik fiyatı gerekli.')
        elif 'activatePrice' in params or 'callbackRate' in params:raise ValueError('Trailing alanları başka türde kullanılamaz.')
        if params.get('algoType','CONDITIONAL')!='CONDITIONAL':raise ValueError('Algo emir türü geçersiz.')
        params['algoType']='CONDITIONAL'
        for field in ('closePosition','priceProtect'):
            if field in params:params[field]=str(_flag(params[field])).lower()
        if 'newClientOrderId' in params:raise ValueError('Koşullu emir clientAlgoId kullanır.')
        endpoint='/fapi/v1/algoOrder'
    else:
        if any(k in params for k in ('triggerPrice','workingType','priceProtect','activatePrice','callbackRate','algoType','clientAlgoId','closePosition')):
            raise ValueError('Normal emirde koşullu emir alanı kullanılamaz.')
        endpoint='/fapi/v1/order'
    for field in ('newClientOrderId','clientAlgoId'):
        if field in params and (not isinstance(params[field],str) or not re.fullmatch(r'[.A-Za-z:/0-9_-]{1,36}',params[field])):
            raise ValueError('İstemci emir kimliği geçersiz.')
    if 'selfTradePreventionMode' in params and params['selfTradePreventionMode'] not in (
            'NONE','EXPIRE_MAKER','EXPIRE_TAKER','EXPIRE_BOTH'):
        raise ValueError('Kendi kendine işlem önleme parametresi geçersiz.')
    return {'method':'POST','path':endpoint,'params':params,'operation':operation,'execution_authorized':False}
