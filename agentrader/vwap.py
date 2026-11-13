"""Display VWAP: explicit UTC session/anchor completeness and native volume provenance."""
import math
from fractions import Fraction
from .market_data import INTERVALS,bucket
from .chart_precision import decimal_text

def vwap_series(rows,config,interval,symbol):
 step=INTERVALS[interval]//1000;session=config['kind']=='SESSION_VWAP';p=config['params'];exact=p['computation_mode']=='EXACT_QUOTE_BASE';anchor=p.get('anchor_time',0)
 result=dict(points=[],plot=[],states=[],provenance=dict(computation_mode=p['computation_mode'],price_source=config['source'],volume_source='NATIVE_DECIMAL_QUOTE_BASE' if exact else 'RAW_KLINE_BASE_VOLUME',session='UTC_00:00' if session else None,anchor_time=None if session else anchor,anchor_symbol=None if session else p['anchor_symbol'],display_interval=interval,trade_vwap_claim=False,order_authority=False))
 def blocked(reason):
  result['plot']=[] if reason=='INVALID_GRID' else [dict(time=r['time']) for r in rows];result['states']=[dict(time=r['time'],state=reason) for r in rows];return result
 if any(type(r.get('time')) is not int or bucket(r['time']*1000,interval)!=r['time']*1000 or r.get('close_time')!=(r['time']+step)*1000-1 or i and r['time']<=rows[i-1]['time'] for i,r in enumerate(rows)):return blocked('INVALID_GRID')
 if session and (step>86400 or 86400%step):return blocked('SESSION_INTERVAL_UNSUPPORTED')
 if not session:
  if not anchor:return blocked('ANCHOR_UNSET')
  if p['anchor_symbol']!=symbol:return blocked('ANCHOR_SYMBOL_MISMATCH')
  if bucket(anchor*1000,interval)!=anchor*1000:return blocked('ANCHOR_NOT_ON_GRID')
  if rows and anchor<rows[0]['time']:return blocked('ANCHOR_HISTORY_MISSING')
 total=Fraction(0) if exact else 0.;weighted=Fraction(0) if exact else 0.;current=None;complete=False;reason='SESSION_START_MISSING' if session else 'BEFORE_ANCHOR'
 for i,r in enumerate(rows):
  t=r['time'];day=t//86400*86400;reset=(session and current!=day) or (not session and t==anchor)
  if reset:
   current=day;total=Fraction(0) if exact else 0.;weighted=Fraction(0) if exact else 0.;complete=t==day if session else True;reason='SESSION_START_MISSING' if session else 'ANCHOR_HISTORY_MISSING'
  elif i and t-rows[i-1]['time']!=step:complete=False;reason='GRID_GAP'
  if not session and t<anchor:state='BEFORE_ANCHOR'
  elif not complete:state=reason
  else:
   try:
    if exact:
     e=r.get('exact',{})
     if e.get('schema')!='chart-exact-decimal/1' or e.get('state')!='VERIFIED' or e.get('provenance')!='UPSTREAM_DECIMAL_TEXT':raise ValueError()
     v=Fraction(decimal_text(e['volume']));q=Fraction(decimal_text(e['quote_volume']))
     if float(v)!=r['volume'] or float(q)!=r['quote_volume'] or not ((v==0 and q==0) or (v>0 and q>0)):raise ValueError()
     amount=q
    else:
     v=r['volume']
     if type(v) not in (int,float) or not math.isfinite(v) or v<0:raise ValueError()
     o,h,l,c=(r[k] for k in ('open','high','low','close'))
     if not all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:raise ValueError()
     value=dict(open=o,high=h,low=l,close=c,hl2=(h+l)/2,hlc3=(h+l+c)/3,ohlc4=(o+h+l+c)/4)[config['source']];amount=value*v
    total+=v;weighted+=amount
    if total==0:state='ZERO_CUMULATIVE_VOLUME'
    else:
     value=weighted/total;point=dict(time=t,value=float(value))
     if exact:point['exact_ratio']=dict(numerator=str(value.numerator),denominator=str(value.denominator))
     result['points'].append(point);result['plot'].append(dict(time=t,value=point['value']));state='READY'
   except (AssertionError,KeyError,ValueError,TypeError,OverflowError):
    complete=False;reason='EXACT_VOLUME_UNPROVEN' if exact else 'INVALID_VOLUME_SOURCE';state=reason
  if state!='READY':result['plot'].append(dict(time=t))
  result['states'].append(dict(time=t,state=state))
 return result
