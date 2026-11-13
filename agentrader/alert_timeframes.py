"""As-of confirmed-bar join; future higher-timeframe values are never consumed."""
from decimal import Decimal
import hashlib,json
from .market_data import INTERVALS,SOURCE,bucket

def intervals(d):return sorted({d['interval']}|{c.get('interval',d['interval']) for c in d.get('conditions',[])},key=lambda i:INTERVALS[i])

def align(d,contexts):
    base=contexts.get(d['interval'])
    if not base:return None
    closed=[r for r in base.get('rows',[]) if r.get('closed')]
    if not closed:return None
    cutoff=closed[-1]['time']+INTERVALS[d['interval']]//1000
    aligned={};epochs={}
    for interval in intervals(d):
        c=contexts.get(interval) or {};step=INTERVALS[interval]//1000
        if (c.get('transport_state')!='LIVE' or c.get('timing',{}).get('state')!='FRESH' or c.get('quality',{}).get('state')!='OK' or not c.get('stream_epoch') or c.get('identity')!=dict(source=SOURCE,environment='live_public',product='USD-M',price_type='LAST_PRICE',symbol=d['symbol'],interval=interval)):return None
        sample=[r for r in c.get('rows',[]) if r.get('closed') and r['time']+step<=cutoff]
        expected=bucket(cutoff*1000,interval)//1000-step
        if len(sample)<2:return None
        if sample[-1]['time']!=expected:return {'_alignment_wait':True}
        try:
            for i,r in enumerate(sample):
                if r.get('exact',{}).get('state')!='VERIFIED' or not Decimal(r['exact']['close']).is_finite() or Decimal(r['exact']['close'])<=0 or bucket(r['time']*1000,interval)!=r['time']*1000 or r.get('close_time')!=(r['time']+step)*1000-1 or i and r['time']-sample[i-1]['time']!=step:return None
        except (ValueError,KeyError,TypeError,ArithmeticError):return None
        aligned[interval]=sample;epochs[interval]=c['stream_epoch']
    return {**base,'rows':aligned[d['interval']],'_aligned_rows':aligned,'stream_epoch':hashlib.sha256(json.dumps(epochs,sort_keys=True).encode()).hexdigest()}
