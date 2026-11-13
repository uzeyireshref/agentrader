"""Versioned candle-series condition algebra. Independent of TradingView subscriptions."""
from decimal import Decimal
import math
from .indicator_config import defaults_v4,validate_v4,series,multi_series
from .vwap import vwap_series
from .drawings.service import geometry
from .drawings.calculations import query

OPERATORS=('cross','cross_up','cross_down','above','below','equal','not_equal','inside','outside','enter','exit','move_up','move_down','move_up_pct','move_down_pct','rising','falling')
FIELDS=('open','high','low','close','hl2','hlc3','ohlc4','volume','quote_volume')
class ConditionUnavailable(ValueError):pass

def number(value):
    if not isinstance(value,str) or len(value)>60:raise ValueError('INVALID_CONDITION_NUMBER')
    n=Decimal(value)
    if not n.is_finite() or abs(n)>Decimal('1e30'):raise ValueError('INVALID_CONDITION_NUMBER')
    return str(n)

def operand(value,symbol):
    if not isinstance(value,dict):raise ValueError('INVALID_OPERAND')
    kind=value.get('type')
    if kind=='value' and set(value)=={'type','value'}:return dict(type=kind,value=number(value['value']))
    if kind=='market' and set(value)=={'type','field'} and value['field'] in FIELDS:return dict(value)
    if kind=='indicator' and set(value)=={'type','config','output'}:
        c=value['config'];items=defaults_v4()
        if not isinstance(c,dict) or c.get('indicator_id') not in [x['indicator_id'] for x in items]:raise ValueError('INVALID_INDICATOR')
        items=[c if x['indicator_id']==c['indicator_id'] else x for x in items];validate_v4(items)
        outputs=('macd','signal','histogram') if c['kind']=='MACD' else ('basis','upper','lower') if c['kind']=='BB' else ('value',)
        if value['output'] not in outputs or c['kind']=='BB' and c['params']['offset']!=0:raise ValueError('SHIFTED_OR_INVALID_OUTPUT')
        if c['kind']=='ANCHORED_VWAP' and (not c['params']['anchor_time'] or c['params']['anchor_symbol']!=symbol):raise ValueError('VWAP_ANCHOR_REQUIRED')
        return dict(value)
    if kind=='drawing' and set(value)=={'type','geometry','output','ratio'}:
        g=geometry(value['geometry'])
        if g['symbol']!=symbol or g.get('schema')=='chart-channel-family/1' or g['kind'] not in ('horizontal','horizontal_ray','trend','ray','extended_line','fibonacci','fibonacci_extension','parallel_channel'):raise ValueError('DRAWING_NOT_COMPUTABLE')
        if g['kind']=='parallel_channel':
            if value['output'] not in ('lower','middle','upper'):raise ValueError('INVALID_DRAWING_OUTPUT')
        elif value['output']!='value':raise ValueError('INVALID_DRAWING_OUTPUT')
        if g['kind'] in ('fibonacci','fibonacci_extension'):
            allowed=g.get('levels',['0','0.236','0.382','0.5','0.618','0.786','1'])
            if value['ratio'] not in allowed:raise ValueError('INVALID_FIB_RATIO')
        elif value['ratio'] is not None:raise ValueError('INVALID_DRAWING_RATIO')
        return {**value,'geometry':g}
    raise ValueError('INVALID_OPERAND')

def conditions(value,match,symbol):
    if match not in ('all','any') or not isinstance(value,list) or not 1<=len(value)<=8:raise ValueError('INVALID_CONDITIONS')
    result=[]
    for c in value:
        if not isinstance(c,dict) or set(c)!={'left','operator','right','upper','bars'} or c['operator'] not in OPERATORS or type(c['bars']) is not int or not 1<=c['bars']<=100:raise ValueError('INVALID_CONDITION')
        left=operand(c['left'],symbol);right=operand(c['right'],symbol);upper=operand(c['upper'],symbol) if c['upper'] is not None else None
        if c['operator'] in ('inside','outside','enter','exit') and upper is None:raise ValueError('CHANNEL_UPPER_REQUIRED')
        if c['operator'] not in ('inside','outside','enter','exit') and upper is not None:raise ValueError('UNUSED_UPPER')
        if c['operator'].startswith('move_') and right['type']=='value' and Decimal(right['value'])<0:raise ValueError('NEGATIVE_MOVEMENT_THRESHOLD')
        if upper is not None and right['type']==upper['type']=='value' and Decimal(right['value'])>Decimal(upper['value']):raise ValueError('REVERSED_CHANNEL_BOUNDS')
        result.append(dict(left=left,right=right,upper=upper,operator=c['operator'],bars=c['bars']))
    return result

def values(o,rows,interval,symbol):
    kind=o['type']
    if kind=='value':return [Decimal(o['value'])]*len(rows)
    if kind=='market':
        result=[]
        for r in rows:
            def v(key):
                raw=r.get('exact',{}).get(key)
                if raw is None:raise ConditionUnavailable('EXACT_SOURCE_MISSING')
                n=Decimal(raw)
                if not n.is_finite():raise ConditionUnavailable('NONFINITE_SOURCE')
                return n
            field=o['field'];result.append((v('high')+v('low'))/2 if field=='hl2' else (v('high')+v('low')+v('close'))/3 if field=='hlc3' else (v('open')+v('high')+v('low')+v('close'))/4 if field=='ohlc4' else v(field))
        return result
    if kind=='indicator':
        c=o['config']
        if c['kind'] in ('MACD','BB'):points=multi_series(rows,c,interval)[o['output']]
        elif c['kind'] in ('SESSION_VWAP','ANCHORED_VWAP'):points=vwap_series(rows,c,interval,symbol)['plot']
        else:points=series(rows,c,interval)
        mapped={p['time']:Decimal(str(p['value'])) for p in points if 'value' in p and math.isfinite(p['value'])}
        return [mapped.get(r['time']) for r in rows]
    g=o['geometry'];op='boundsAt' if g['kind']=='parallel_channel' else 'level' if g['kind'] in ('fibonacci','fibonacci_extension') else 'priceAt';result=[]
    for r in rows:
        try:
            v=query(g,op,time=r['time'],times=[x['time'] for x in rows],interval=interval,ratio=o['ratio'])['value']
            if op=='boundsAt':v=v[o['output']]
            result.append(Decimal(v['numerator'])/Decimal(v['denominator']))
        except (ValueError,KeyError,TypeError):result.append(None)
    return result

def evaluate(c,rows,interval,symbol,cache):
    import json
    def data(o):
        key=json.dumps(o,sort_keys=True)
        if key not in cache:cache[key]=values(o,rows,interval,symbol)
        return cache[key]
    left,right=data(c['left']),data(c['right']);i=len(rows)-1;op=c['operator'];look=c['bars'] if op.startswith('move_') or op in ('rising','falling') else 1
    if i<look:raise ConditionUnavailable('WARMUP_REQUIRED')
    needed=left[i-look:i+1]+right[i-1:i+1]
    if any(x is None or not x.is_finite() for x in needed):raise ConditionUnavailable('WARMUP_OR_SCOPE_REQUIRED')
    a,b=left[i-1]-right[i-1],left[i]-right[i]
    if op=='cross':return a<0<=b or a>0>=b
    if op=='cross_up':return a<0<=b
    if op=='cross_down':return a>0>=b
    if op=='above':return b>0
    if op=='below':return b<0
    if op=='equal':return b==0
    if op=='not_equal':return b!=0
    if op in ('inside','outside','enter','exit'):
        upper=data(c['upper'])
        if any(x is None for x in upper[-2:]) or any(right[j]>upper[j] for j in (i-1,i)):raise ConditionUnavailable('INVALID_CHANNEL_BOUNDS')
        old=right[i-1]<=left[i-1]<=upper[i-1];now=right[i]<=left[i]<=upper[i]
        return now if op=='inside' else not now if op=='outside' else not old and now if op=='enter' else old and not now
    if op in ('rising','falling'):return all((y>x if op=='rising' else y<x) for x,y in zip(left[i-look:i],left[i-look+1:i+1]))
    change=left[i]-left[i-look]
    if op.endswith('_pct'):
        if left[i-look]==0:raise ConditionUnavailable('ZERO_PERCENT_BASE')
        change=change/abs(left[i-look])*100
    amount=right[i]
    if amount<0:raise ConditionUnavailable('NEGATIVE_MOVEMENT_THRESHOLD')
    return change>=amount if op in ('move_up','move_up_pct') else -change>=amount

def evaluate_all(definition,rows,aligned=None):
    caches={};checks=[]
    for c in definition['conditions']:
        interval=c.get('interval',definition['interval']);sample=aligned[interval] if aligned is not None else rows
        checks.append(evaluate(c,sample,interval,definition['symbol'],caches.setdefault(interval,{})))
    return (all(checks) if definition['match']=='all' else any(checks)),checks
