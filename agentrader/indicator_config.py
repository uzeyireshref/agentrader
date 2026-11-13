"""Versioned display-indicator configuration; no execution authority."""
from .binding_lifecycle import stop_bindings
from contextlib import closing
import json
import math
from .market_data import INTERVALS,bucket
from .migrations import connect
from .drawings.service import DrawingService,DrawingError,DrawingConflict,identifier
SOURCES=('open','high','low','close','hl2','hlc3','ohlc4')
SPECS=(('ema-fast','EMA',20,'price','EMA_SMA_SEED'),('ema-slow','EMA',50,'price','EMA_SMA_SEED'),('rsi-main','RSI',14,'oscillator','WILDER_SMA_SEED'))
def defaults():
 return [dict(indicator_id=i,revision=0,kind=k,period=p,source='close',smoothing=s,anchor='LOADED_HISTORY_START',pane=pane,enabled=False,calculation_version=1) for i,k,p,pane,s in SPECS]
def validate(items):
 if not isinstance(items,list) or len(items)!=3:raise DrawingError()
 result=[]
 for item,(key,kind,_,pane,smoothing) in zip(items,SPECS):
  if (not isinstance(item,dict) or set(item)!=set(defaults()[0]) or item['indicator_id']!=key or item['kind']!=kind
      or type(item['revision']) is not int or item['revision']<0 or type(item['period']) is not int or not 1<=item['period']<=500
      or item['source'] not in SOURCES or item['smoothing']!=smoothing or item['anchor']!='LOADED_HISTORY_START'
      or item['pane']!=pane or type(item['enabled']) is not bool or type(item['calculation_version']) is not int or item['calculation_version']!=1):raise DrawingError()
  result.append(dict(item))
 return result
EXTRA_SPECS=(('sma-main','SMA',20,'price','ROLLING_SMA'),('atr-main','ATR',14,'volatility','WILDER_TR_SMA_SEED'))
def defaults_v2():
 items=defaults();items[2]['calculation_version']=2
 return items+[dict(indicator_id=i,revision=0,kind=k,period=p,source='ohlc' if k=='ATR' else 'close',smoothing=s,anchor='LOADED_HISTORY_START',pane=pane,enabled=False,calculation_version=1) for i,k,p,pane,s in EXTRA_SPECS]
def validate_v2(items):
 if not isinstance(items,list) or len(items)!=5:raise DrawingError()
 for item,default in zip(items,defaults_v2()):
  if (not isinstance(item,dict) or set(item)!=set(default) or any(item[k]!=default[k] for k in ('indicator_id','kind','smoothing','anchor','pane'))
      or type(item['period']) is not int or not 1<=item['period']<=500 or type(item['revision']) is not int or item['revision']<0
      or type(item['enabled']) is not bool or item['source'] not in (('ohlc',) if item['kind']=='ATR' else SOURCES)
      or type(item['calculation_version']) is not int or item['calculation_version'] not in ((1,2) if item['kind']=='RSI' else (1,))):raise DrawingError()
 return [dict(c) for c in items]
def expand(items):
 if len(items)==3:return validate(items)+defaults_v2()[3:]
 return validate_v2(items)
def defaults_v3():
 base=defaults_v2()[0]
 return defaults_v2()+[
  {**base,'indicator_id':'macd-main','kind':'MACD','period':26,'pane':'macd','smoothing':'MACD_CONFIGURED','params':dict(fast_period=12,signal_period=9,oscillator_type='EMA',signal_type='EMA'),'style':dict(line_width=1,colors=dict(macd='#6099ef',signal='#e9a252',positive_rising='#26a69a',positive_falling='#a4d8cf',negative_rising='#efb2b7',negative_falling='#ef5350'))},
  {**base,'indicator_id':'bb-main','kind':'BB','period':20,'smoothing':'BB_POPULATION','params':dict(basis_type='SMA',deviation=2,offset=0),'style':dict(line_width=1,colors=dict(basis='#d4b462',upper='#709ee6',lower='#709ee6'))}]
def validate_v3(items):
 import re
 if not isinstance(items,list) or len(items)!=7:raise DrawingError()
 validate_v2(items[:5])
 for c,d in zip(items[5:],defaults_v3()[5:]):
  if (not isinstance(c,dict) or set(c)!=set(d) or any(c[k]!=d[k] for k in ('indicator_id','kind','pane','smoothing','anchor'))
      or type(c['revision']) is not int or c['revision']<0 or type(c['enabled']) is not bool or type(c['period']) is not int or not 1<=c['period']<=500
      or c['source'] not in SOURCES or type(c['calculation_version']) is not int or c['calculation_version']!=1):raise DrawingError()
  params,style=c['params'],c['style']
  if not isinstance(params,dict) or set(params)!=set(d['params']):raise DrawingError()
  if c['kind']=='MACD':
   if (type(params['fast_period']) is not int or not 1<=params['fast_period']<c['period'] or type(params['signal_period']) is not int or not 1<=params['signal_period']<=500
       or params['oscillator_type'] not in ('SMA','EMA') or params['signal_type'] not in ('SMA','EMA')):raise DrawingError()
  elif (params['basis_type'] not in ('SMA','EMA') or type(params['deviation']) not in (int,float) or not math.isfinite(params['deviation']) or not .1<=params['deviation']<=10
        or type(params['offset']) is not int or not -100<=params['offset']<=100):raise DrawingError()
  if (not isinstance(style,dict) or set(style)!={'line_width','colors'} or type(style['line_width']) is not int or style['line_width'] not in (1,2,3)
      or not isinstance(style['colors'],dict) or set(style['colors'])!=set(d['style']['colors']) or any(not isinstance(x,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',x) for x in style['colors'].values())):raise DrawingError()
 return [dict(c) for c in items]
def expand_v3(items):
 return expand(items)+defaults_v3()[5:] if len(items) in (3,5) else validate_v3(items)
def defaults_v4():
 base=defaults_v2()[0]
 return defaults_v3()+[
  {**base,'indicator_id':'session-vwap','kind':'SESSION_VWAP','period':1,'source':'hlc3','anchor':'UTC_SESSION','smoothing':'CUMULATIVE_VOLUME','params':dict(computation_mode='BAR_PRICE_VOLUME'),'style':dict(line_width=2,colors=dict(value='#e9be62'))},
  {**base,'indicator_id':'anchored-vwap','kind':'ANCHORED_VWAP','period':1,'source':'hlc3','anchor':'SAVED_UTC_ANCHOR','smoothing':'CUMULATIVE_VOLUME','params':dict(computation_mode='BAR_PRICE_VOLUME',anchor_time=0,anchor_symbol=''),'style':dict(line_width=2,colors=dict(value='#c789dc'))}]
def validate_v4(items):
 import re
 if not isinstance(items,list) or len(items)!=9:raise DrawingError()
 validate_v3(items[:7])
 for c,d in zip(items[7:],defaults_v4()[7:]):
  if (not isinstance(c,dict) or set(c)!=set(d) or any(c[k]!=d[k] for k in ('indicator_id','kind','pane','smoothing','anchor'))
      or type(c['period']) is not int or c['period']!=1 or type(c['revision']) is not int or c['revision']<0 or type(c['enabled']) is not bool or type(c['calculation_version']) is not int or c['calculation_version']!=1):raise DrawingError()
  p,style=c['params'],c['style']
  if not isinstance(p,dict) or set(p)!=set(d['params']) or p['computation_mode'] not in ('BAR_PRICE_VOLUME','EXACT_QUOTE_BASE'):raise DrawingError()
  if c['source'] not in (('quote_base',) if p['computation_mode']=='EXACT_QUOTE_BASE' else SOURCES):raise DrawingError()
  if c['kind']=='ANCHORED_VWAP' and (type(p['anchor_time']) is not int or not 0<=p['anchor_time']<=32503680000 or not isinstance(p['anchor_symbol'],str) or (p['anchor_time']==0 and p['anchor_symbol']!='') or (p['anchor_time']>0 and not re.fullmatch(r'[A-Z0-9]{2,20}USDT',p['anchor_symbol']))):raise DrawingError()
  if (not isinstance(style,dict) or set(style)!={'line_width','colors'} or type(style['line_width']) is not int or style['line_width'] not in (1,2,3) or not isinstance(style['colors'],dict) or set(style['colors'])!={'value'} or not isinstance(style['colors']['value'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',style['colors']['value'])):raise DrawingError()
 return [dict(c) for c in items]
def expand_v4(items):
 return expand_v3(items)+defaults_v4()[7:] if len(items) in (3,5,7) else validate_v4(items)
class IndicatorService(DrawingService):
 def load(self,workspace_id,format_version=1):
  identifier(workspace_id)
  if format_version not in (1,2,3,4):raise DrawingError()
  with closing(connect(self.database)) as db:
   row=db.execute('SELECT * FROM app_indicator_configs WHERE owner=? AND workspace_id=?',(self.owner,workspace_id)).fetchone()
  items=json.loads(row['body']) if row else (defaults_v4() if format_version==4 else defaults_v3() if format_version==3 else defaults_v2() if format_version==2 else defaults())
  items=expand_v4(items) if format_version==4 else expand_v3(items) if format_version==3 else expand(items) if format_version==2 else validate(items)
  return dict(schema='chart-indicators/'+str(format_version),workspace_id=workspace_id,revision=row['revision'] if row else 0,indicators=items)
 def save(self,workspace_id,request_id,expected_revision,indicators,format_version=1):
  identifier(workspace_id)
  if format_version not in (1,2,3,4):raise DrawingError()
  items=validate_v4(indicators) if format_version==4 else validate_v3(indicators) if format_version==3 else validate_v2(indicators) if format_version==2 else validate(indicators)
  if type(expected_revision) is not int or expected_revision<0:raise DrawingError()
  def apply(db):
   row=db.execute('SELECT * FROM app_indicator_configs WHERE owner=? AND workspace_id=?',(self.owner,workspace_id)).fetchone()
   if (row['revision'] if row else 0)!=expected_revision:raise DrawingConflict()
   previous=json.loads(row['body']) if row else (defaults_v4() if format_version==4 else defaults_v3() if format_version==3 else defaults_v2() if format_version==2 else defaults());previous=expand_v4(previous) if format_version==4 else expand_v3(previous) if format_version==3 else expand(previous) if format_version==2 else validate(previous);updated=[]
   for old,new in zip(previous,items):
    if old['revision']!=new['revision']:raise DrawingConflict()
    updated.append({**new,'revision':old['revision']+int(old!=new)})
   stop_bindings(db,self.owner,workspace_id,'indicator',{c['indicator_id'] for old,c in zip(previous,updated) if c['revision']!=old['revision']},'TARGET_REVISION_CHANGED')
   revision=expected_revision+1
   db.execute('INSERT OR REPLACE INTO app_indicator_configs VALUES (?,?,?,?)',(self.owner,workspace_id,revision,json.dumps(updated)))
   return dict(schema='chart-indicators/'+str(format_version),workspace_id=workspace_id,revision=revision,indicators=updated)
  return self._mutation(request_id,['indicators',workspace_id,format_version],dict(expected_revision=expected_revision,indicators=items),apply)
def series(rows,config,interval=None):
 """Independent Python reference; explicit RSI version and optional strict UTC grid."""
 config=validate_v2([{**d,**config} if d['indicator_id']==config.get('indicator_id') else d for d in defaults_v2()])[[x['indicator_id'] for x in defaults_v2()].index(config['indicator_id'])]
 if interval is not None:
  if interval not in INTERVALS:raise ValueError('Invalid interval')
  step=INTERVALS[interval]
  if any(type(r.get('time')) is not int or bucket(r['time']*1000,interval)!=r['time']*1000 or r.get('close_time')!=(r['time']*1000+step-1) or i and (r['time']-rows[i-1]['time'])*1000!=step for i,r in enumerate(rows)):return []
 period=config['period'];values=[];result=[]
 for row in rows:
  o,h,l,c=(row[k] for k in ('open','high','low','close'))
  if not all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in (o,h,l,c)):raise ValueError('Invalid source')
  values.append(dict(open=o,high=h,low=l,close=c,hl2=(h+l)/2,hlc3=(h+l+c)/3,ohlc4=(o+h+l+c)/4)[config['source']] if config['kind']!='ATR' else h-l)
 if config['kind'] in ('SMA','ATR'):
  if config['kind']=='ATR':values=[max(r['high']-r['low'],abs(r['high']-rows[i-1]['close']),abs(r['low']-rows[i-1]['close'])) if i else r['high']-r['low'] for i,r in enumerate(rows)]
  value=0
  for i,x in enumerate(values):
   if i<period:value+=x
   if i==period-1:value/=period
   elif i>=period:value=(value*(period-1)+x)/period if config['kind']=='ATR' else sum(values[i-period+1:i+1])/period
   if i>=period-1:result.append(dict(time=rows[i]['time'],value=value))
 elif config['kind']=='EMA':
  value=0;alpha=2/(period+1)
  for i,x in enumerate(values):
   if i<period:value+=x
   if i==period-1:value/=period
   elif i>=period:value=x*alpha+value*(1-alpha)
   if i>=period-1:result.append(dict(time=rows[i]['time'],value=value))
 else:
  gain=loss=0
  for i in range(1,len(values)):
   change=values[i]-values[i-1];g=max(0,change);l=max(0,-change)
   if i<=period:
    gain+=g;loss+=l
    if i==period:gain/=period;loss/=period
   else:gain=(gain*(period-1)+g)/period;loss=(loss*(period-1)+l)/period
   if i>=period:result.append(dict(time=rows[i]['time'],value=(50 if config['calculation_version']==1 else 100) if gain==loss==0 else 100 if loss==0 else 100-100/(1+gain/loss)))
 return result

def multi_series(rows,config,interval):
 """Versioned multi-output display reference; shifted BB is never a bot signal."""
 config=validate_v3([config if d['indicator_id']==config['indicator_id'] else d for d in defaults_v3()])[5 if config['kind']=='MACD' else 6]
 names=('macd','signal','histogram') if config['kind']=='MACD' else ('basis','upper','lower')
 step=INTERVALS[interval];result={key:[] for key in names}
 if any(type(r.get('time')) is not int or bucket(r['time']*1000,interval)!=r['time']*1000 or r.get('close_time')!=r['time']*1000+step-1 or i and (r['time']-rows[i-1]['time'])*1000!=step for i,r in enumerate(rows)):return result
 source=config['source'];values=[]
 for r in rows:
  o,h,l,c=(r[k] for k in ('open','high','low','close'))
  if not all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in (o,h,l,c)):raise ValueError('Invalid source')
  values.append(dict(open=o,high=h,low=l,close=c,hl2=(h+l)/2,hlc3=(h+l+c)/3,ohlc4=(o+h+l+c)/4)[source])
 def smooth(points,period,kind):
  output=[];value=0
  for i,(t,x) in enumerate(points):
   if i<period:value+=x
   if i==period-1:value/=period
   elif i>=period:value=x*2/(period+1)+value*(1-2/(period+1)) if kind=='EMA' else sum(v for _,v in points[i-period+1:i+1])/period
   if i>=period-1:output.append((t,value))
  return output
 points=[(r['time'],v) for r,v in zip(rows,values)];p=config['params'];period=config['period']
 if config['kind']=='MACD':
  fast=dict(smooth(points,p['fast_period'],p['oscillator_type']));macd=[(t,fast[t]-v) for t,v in smooth(points,period,p['oscillator_type'])];signal=smooth(macd,p['signal_period'],p['signal_type']);m=dict(macd);hist=[(t,m[t]-v) for t,v in signal]
  return {key:[dict(time=t,value=v) for t,v in data] for key,data in zip(names,(macd,signal,hist))}
 basis=dict(smooth(points,period,p['basis_type']))
 for i in range(period-1,len(rows)):
  t=rows[i]['time'];window=values[i-period+1:i+1];mean=sum(window)/period;deviation=math.sqrt(sum((x-mean)**2 for x in window)/period)*p['deviation'];shift=t+p['offset']*(step//1000)
  for key,value in zip(names,(basis[t],basis[t]+deviation,basis[t]-deviation)):result[key].append(dict(time=shift,value=value))
 return result
