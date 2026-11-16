"""Explicit normal LIMIT options shared by contracts, compiler and scope checks."""
from agentrader.bot.risk import number

TIFS={'GTC','IOC','FOK','GTX','GTD'}
MATCHES={'OPPONENT','OPPONENT_5','OPPONENT_10','OPPONENT_20','QUEUE','QUEUE_5','QUEUE_10','QUEUE_20'}
STPS={'EXPIRE_MAKER','EXPIRE_TAKER','EXPIRE_BOTH'}


def validate_options(options):
    if not isinstance(options,dict) or options.keys()-{'time_in_force','price_match','self_trade_prevention_mode','good_till_date'}:
        raise ValueError('Normal emir seçenekleri geçersiz.')
    tif=options.get('time_in_force','GTC')
    if not isinstance(tif,str) or tif not in TIFS:raise ValueError('Desteklenmeyen emir süresi.')
    if 'price_match' in options and (not isinstance(options['price_match'],str) or options['price_match'] not in MATCHES):
        raise ValueError('priceMatch seçimi geçersiz.')
    if 'self_trade_prevention_mode' in options:
        if (not isinstance(options['self_trade_prevention_mode'],str) or options['self_trade_prevention_mode'] not in STPS or
                tif not in ('GTC','IOC','GTD')):
            raise ValueError('STP yalnız GTC/IOC/GTD ile açık bir EXPIRE modu kullanır.')
    if tif=='GTD':
        if type(options.get('good_till_date')) is not int or not 0<options['good_till_date']<253402300799000:
            raise ValueError('GTD milisaniye son geçerliliği gerekli.')
    elif 'good_till_date' in options:raise ValueError('good_till_date yalnız GTD içindir.')
    return options


def apply_options(order,entry):
    result=dict(order)
    if result['type']=='LIMIT':result.setdefault('timeInForce','GTC')
    options=entry.get('order_options',{})
    if options:
        validate_options(options)
        result['timeInForce']=options.get('time_in_force','GTC')
        for source,target in (('price_match','priceMatch'),('self_trade_prevention_mode','selfTradePreventionMode')):
            if source in options:result[target]=options[source]
        if 'price_match' in options:result.pop('price',None)
        if 'good_till_date' in options:result['goodTillDate']=options['good_till_date']//1000*1000
    if 'order_response_type' in entry:result['newOrderRespType']=entry['order_response_type']
    return result


def price_in_scope(plan,price):
    value=number(price);ref=number(plan['entry']['reference_price'])
    sign=1 if plan['direction']=='LONG' else -1
    return (value>0 and sign*(value-number(plan['stop']))>0 and
            sign*(number(plan['targets'][0]['price'])-value)>0 and
            abs(value-ref)/ref*10000<=number(plan['entry']['max_drift_bps']))
