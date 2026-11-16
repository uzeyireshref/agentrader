"""Current packet envelope for explicit synthetic browser fixtures, not market evidence."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import hashlib
import sys
from pathlib import Path
from urllib.parse import urlparse,parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from agentrader.chart.chart_evidence import snapshot
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT

IDENTITY=dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE')
_snapshots={}


def fixture_response(url,value):
    path=urlparse(url).path
    if path=='/api/markets':return {**IDENTITY,**value}
    if path=='/api/candles':
        q=parse_qs(urlparse(url).query)
        return {**IDENTITY,'symbol':q.get('symbol',['BTCUSDT'])[0],'interval':q.get('interval',['15m'])[0],**value}
    return value


def fixture_packet(packet):
    p={**IDENTITY,**packet}
    p.setdefault('stream_epoch',hashlib.sha256(('fixture:'+p['symbol']+':'+p['interval']+':'+str(p['generation'])).encode()).hexdigest()[:32])
    p.setdefault('quality',dict(state='OK',missing_bars=0))
    if 'data_proof' not in p:
        # Preserve incomplete precision as BLOCKED. Do not fabricate raw decimals,
        # alter intentional gaps, or upgrade missing source/volume evidence.
        key=(p['symbol'],p['interval'],p['stream_epoch']);old=_snapshots.get(key,{})
        if 'market' not in p and 'market' in old:p['market']=old['market']
        if p['type']=='snapshot':rows=p.get('candles',[])
        else:
            values={r['time']:r for r in old.get('rows',[])}
            for r in p.get('tail',[]) or ([p['candle']] if p.get('candle') else []):values[r['time']]=r
            rows=sorted(values.values(),key=lambda r:r['time'])[-4000:]
        heartbeat=p['type']=='update' and not p.get('tail') and not p.get('candle') and p['sequence']==old.get('sequence')
        p['data_proof']=old['proof'] if heartbeat and 'proof' in old else snapshot(rows[-499:],p.get('market'),p['quality'],symbol=p['symbol'],interval=p['interval'],
            epoch=p['stream_epoch'],generation=p['generation'],revision=max(1,p['sequence'])).view()
        _snapshots[key]=dict(rows=rows,market=p.get('market'),proof=p['data_proof'],sequence=p['sequence'])
    return p
