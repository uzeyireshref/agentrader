"""Explicit deterministic acceptance inputs, separate from production defaults."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from copy import deepcopy
from decimal import Decimal

START=1800000000
STEP=900


def family_options():
    return dict(extend='none',median=True,background=True,fill_opacity=.2,prices=True,
                levels=['0.5','1'],source='close',upper_deviation='2',lower_deviation='2',
                upper_enabled=True,lower_enabled=True,pearson=True)


def drawing_cases(future=False,fractional=False,include_projection=False):
    index=[305,319,313] if future else [280,294,288]
    anchors=[dict(time=START+i*STEP,price=p) for i,p in zip(index,['110.25','130.75','140.25'])]
    cases=[]
    def add(cid,kind,**extra):
        count=1 if kind in ('horizontal','horizontal_ray','text','note','price_label') else 3 if kind in ('parallel_channel','long_plan','short_plan','flat_channel','disjoint_channel','pitchfork','schiff_pitchfork','modified_schiff_pitchfork','inside_pitchfork') else 2
        g=dict(kind=kind,symbol='BTCUSDT',price_source='LAST_PRICE',label='Bot test '+cid,anchors=deepcopy(anchors[:count]))
        g.update(extra);cases.append(dict(case_id=cid,geometry=g))
    add('horizontal','horizontal')
    add('zone-legacy','zone')
    add('zone-v1','zone',schema='chart-zone/1',time_scope='bounded')
    add('trend','trend')
    add('fib-legacy','fibonacci')
    add('fib-v1','fibonacci',schema='chart-fibonacci/1',time_scope='unbounded',levels=['0','0.382','0.618','1','1.618'])
    add('ruler','ruler',schema='chart-ruler/1')
    for kind in ('horizontal_ray','ray','extended_line'):add(kind,kind,schema='chart-line/1')
    add('parallel-legacy','parallel_channel',schema='chart-channel/1')
    for kind in ('parallel_channel','flat_channel','disjoint_channel','regression_channel','pitchfork','schiff_pitchfork','modified_schiff_pitchfork','inside_pitchfork'):
        add('family-'+kind,kind,schema='chart-channel-family/1',options=family_options(),text='Kanal notu: Türkçe ✓\nİkinci satır <b>düz metin</b>')
    add('fib-extension','fibonacci_extension',schema='chart-fibonacci/1',time_scope='right',levels=['0','0.618','1','1.618'])
    for kind in ('long_plan','short_plan'):
        a=deepcopy(anchors);a[2]['time']=a[1]['time'];a[0]['price']='120.25';a[1]['price']='110.25' if kind=='long_plan' else '140.25';a[2]['price']='140.25' if kind=='long_plan' else '100.25'
        add(kind,kind,schema='chart-position/1',anchors=a,params=dict(risk_budget='5',fee_bps='4',slippage_bps='2'))
    for kind in ('text','note','price_label'):
        add(kind,kind,schema='chart-annotation/1',text='Türkçe: çizgi 🧭 <b>metin</b>' if kind=='price_label' else 'Türkçe not 🧭 <b>metin</b>\nİkinci satır: ı İ ş ğ ü ö ç')
    if include_projection:
        add('fib-projection','fibonacci_projection',schema='chart-fibonacci-projection/1',anchors=deepcopy(anchors),basis='PRICE_DELTA',time_scope='right',levels=['0','0.618','1','1.618'])
    if fractional:
        for case in cases:
            for anchor in case['geometry']['anchors']:
                anchor['time']+=225
                anchor['price']=str(Decimal(anchor['price'])+Decimal('0.12345678'))
    return cases


def candles(count=300):
    result=[]
    for i in range(count):
        t=START+i*STEP;c=100+i*.25
        r=dict(time=t,open=c-.25,high=c+.5,low=c-.5,close=c,volume=10,quote_volume=10*c,
               close_time=(t+STEP)*1000-1,closed=i<count-1)
        r['exact']=dict(schema='chart-exact-decimal/1',state='VERIFIED',provenance='UPSTREAM_DECIMAL_TEXT',
                        **{k:str(r[k]) for k in ('open','high','low','close','volume','quote_volume')})
        result.append(r)
    return result
