"""Unified USD-M order validation for LONG/SHORT, one-way/hedge and protections.

Validation builds request parameters only. Authorization and portfolio ownership
must still be verified by the executor before submitting an order.
"""
import re
from decimal import Decimal

from agentrader.bot.risk import number

CONDITIONAL={'STOP','STOP_MARKET','TAKE_PROFIT','TAKE_PROFIT_MARKET','TRAILING_STOP_MARKET'}
TYPES={'LIMIT','MARKET'}|CONDITIONAL
KNOWN_FILTERS={'PRICE_FILTER','LOT_SIZE','MARKET_LOT_SIZE','MIN_NOTIONAL',
               'PERCENT_PRICE','MAX_NUM_ORDERS','MAX_NUM_ALGO_ORDERS','POSITION_RISK_CONTROL'}


def symbol_filters(symbol,operation):
    rows=symbol.get('filters')
    if not isinstance(rows,list) or any(not isinstance(r,dict) or not isinstance(r.get('filterType'),str) for r in rows):
        raise ValueError('Sembol filtreleri doğrulanamadı.')
    filters={r['filterType']:r for r in rows}
    if len(filters)!=len(rows) or filters.keys()-KNOWN_FILTERS:
        raise ValueError('Tekrarlı veya desteklenmeyen sembol filtresi.')
    if not {'PRICE_FILTER','LOT_SIZE','MIN_NOTIONAL'}<=filters.keys():
        raise ValueError('Zorunlu sembol filtreleri eksik.')
    required_fields={'PRICE_FILTER':('minPrice','maxPrice','tickSize'),
                     'LOT_SIZE':('minQty','maxQty','stepSize'),
                     'MARKET_LOT_SIZE':('minQty','maxQty','stepSize'),
                     'MIN_NOTIONAL':('notional',),'PERCENT_PRICE':('multiplierDown','multiplierUp')}
    for name,fields in required_fields.items():
        if name in filters:
            for field in fields:
                if number(filters[name].get(field))<0:raise ValueError('Sembol filtresi negatif olamaz.')
    control=filters.get('POSITION_RISK_CONTROL')
    if control is not None and (control.get('positionControlSide')!='NONE' and operation=='OPEN'):
        # The public schema does not define all non-NONE values. Do not guess
        # which opening side is permitted. Owned reductions stay available.
        raise ValueError('Sembol pozisyon risk kontrolünde; yeni giriş uygunluğu doğrulanamadı.')
    for name in ('MAX_NUM_ORDERS','MAX_NUM_ALGO_ORDERS'):
        if name in filters and (type(filters[name].get('limit')) is not int or filters[name]['limit']<0):
            raise ValueError('Açık emir limiti doğrulanamadı.')
    return filters


def _fresh_reference(value,symbol,now_ms,max_age_seconds):
    if (not isinstance(value,dict) or value.get('symbol')!=symbol or
            type(value.get('time')) is not int or
            not -1000<=now_ms-value['time']<=max_age_seconds*1000):
        raise ValueError('Tetik fiyat kaynağı eksik, eski veya yanlış sembolde.')
    price=number(value.get('price'))
    if price<=0:raise ValueError('Pozitif contract fiyatı gerekli.')
    return price


def _flag(value):
    if type(value) is bool:return value
    if value=='true':return True
    if value=='false':return False
    raise ValueError('Boolean emir parametresi geçersiz.')


def validate_order(intent,symbol,position_mode,operation,mark_price,now_ms,*,
                   contract_price=None,order_counts=None,additional_order=True,max_age_seconds=15):
    if type(now_ms) is not int or now_ms<0 or type(max_age_seconds) not in (int,float) or number(max_age_seconds)<=0:
        raise ValueError('Fiyat doğrulama zamanı veya yaşı geçersiz.')
    required={'symbol','side','positionSide','type'}
    optional={'quantity','price','timeInForce','reduceOnly','closePosition','triggerPrice',
              'workingType','priceProtect','activatePrice','callbackRate','newClientOrderId',
              'clientAlgoId','priceMatch','selfTradePreventionMode','goodTillDate','algoType',
              'newOrderRespType'}
    if not required<=intent.keys() or intent.keys()-required-optional:
        raise ValueError('Emir alanları eksik veya desteklenmiyor.')
    params=dict(intent)
    if 'newOrderRespType' in params and params['newOrderRespType'] not in ('ACK','RESULT'):
        raise ValueError('Emir yanıt türü ACK veya RESULT olmalı.')
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
    filters=symbol_filters(symbol,operation)
    pf=filters['PRICE_FILTER'];tick=number(pf['tickSize'])
    low,high=number(pf['minPrice']),number(pf['maxPrice'])
    if min(tick,low,high)<0 or (high and low>high):raise ValueError('Fiyat filtresi geçersiz.')
    mark=number(mark_price)
    if mark<=0:raise ValueError('Güncel mark fiyatı gerekli.')
    def check_price(field):
        value=number(params[field])
        if value<=0 or (tick and (value-low)%tick) or (low and value<low) or (high and value>high):
            raise ValueError('Fiyat adımı veya aralığı geçersiz.')
        params[field]=str(value);return value
    for field in ('price','triggerPrice','activatePrice'):
        if field in params:check_price(field)
    band=filters.get('PERCENT_PRICE')
    if band is not None:
        down,up=number(band.get('multiplierDown')),number(band.get('multiplierUp'))
        if not 0<down<=up:raise ValueError('Dinamik fiyat bandı geçersiz.')
        if 'price' in params:
            price=number(params['price'])
            if (side=='BUY' and price>mark*up) or (side=='SELL' and price<mark*down):
                raise ValueError('Emir fiyatı mark fiyatına bağlı yönlü bandın dışında.')
    if order_counts is not None:
        if (not isinstance(order_counts,dict) or any(type(order_counts.get(k)) is not int or order_counts[k]<0 for k in ('normal','algo'))
                or type(additional_order) is not bool):
            raise ValueError('Açık emir sayısı doğrulanamadı.')
        total=order_counts['normal']+order_counts['algo']+int(additional_order)
        algos=order_counts['algo']+int(additional_order and kind in CONDITIONAL)
        if ('MAX_NUM_ORDERS' in filters and total>filters['MAX_NUM_ORDERS']['limit'] or
                'MAX_NUM_ALGO_ORDERS' in filters and algos>filters['MAX_NUM_ALGO_ORDERS']['limit']):
            raise ValueError('Sembol açık emir sınırı aşılıyor.')
    if not close:
        if 'quantity' not in params:raise ValueError('Miktar gerekli.')
        q=number(params['quantity'])
        if q<=0:raise ValueError('Pozitif miktar gerekli.')
        lot=filters.get('MARKET_LOT_SIZE',filters['LOT_SIZE']) if kind=='MARKET' or kind.endswith('_MARKET') else filters['LOT_SIZE']
        for rule in (filters['LOT_SIZE'],lot):
            step=number(rule['stepSize'])
            minimum,maximum=number(rule['minQty']),number(rule['maxQty'])
            if step<0 or minimum<0 or maximum<minimum or not minimum<=q<=maximum or (step>0 and (q-minimum)%step):
                raise ValueError('Miktar adımı veya lot sınırı geçersiz.')
        params['quantity']=str(q)
        if operation=='OPEN' and q*number(params.get('price',mark))<number(filters['MIN_NOTIONAL']['notional']):
            raise ValueError('Yeni emir minimum nominal tutarın altında.')
    if kind in ('LIMIT','STOP','TAKE_PROFIT'):
        if ('price' in params)==('priceMatch' in params):
            raise ValueError('Limit emir için fiyat veya priceMatch gerekli; birlikte kullanılamaz.')
        if kind in ('STOP','TAKE_PROFIT'):params.setdefault('timeInForce','GTC')
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
            if not Decimal('.1')<=callback<=20:raise ValueError('Trailing callbackRate 0.1–20 arasında olmalı.')
            if 'activatePrice' in params:
                reference=mark if params.get('workingType','CONTRACT_PRICE')=='MARK_PRICE' else _fresh_reference(contract_price,params['symbol'],now_ms,max_age_seconds)
                activation=number(params['activatePrice'])
                if (side=='BUY' and activation>=reference) or (side=='SELL' and activation<=reference):
                    raise ValueError('Trailing aktivasyon fiyatı mevcut fiyatın yanlış tarafında.')
        elif 'triggerPrice' not in params:raise ValueError('Koşullu emir tetik fiyatı gerekli.')
        elif 'activatePrice' in params or 'callbackRate' in params:raise ValueError('Trailing alanları başka türde kullanılamaz.')
        else:
            reference=mark if params.get('workingType','CONTRACT_PRICE')=='MARK_PRICE' else _fresh_reference(contract_price,params['symbol'],now_ms,max_age_seconds)
            trigger=number(params['triggerPrice'])
            stop_kind=kind in ('STOP','STOP_MARKET')
            fires_above=(side=='BUY')==stop_kind
            if (fires_above and trigger<=reference) or (not fires_above and trigger>=reference):
                raise ValueError('Koşullu emir mevcut referans fiyatında hemen tetiklenir.')
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
    if params.get('selfTradePreventionMode') not in (None,'NONE'):
        if params.get('timeInForce') not in ('GTC','IOC','GTD'):
            raise ValueError('STP bu emir süresiyle etkili değil.')
        allowed=symbol.get('allowedSelfTradePreventionModes')
        if allowed is not None and (not isinstance(allowed,list) or params['selfTradePreventionMode'] not in allowed):
            raise ValueError('STP modu sembolde desteklenmiyor.')
    if kind=='LIMIT' and 'timeInForce' in symbol and params['timeInForce'] not in symbol['timeInForce']:
        raise ValueError('Emir süresi sembolde desteklenmiyor.')
    return {'method':'POST','path':endpoint,'params':params,'operation':operation,'execution_authorized':False}
