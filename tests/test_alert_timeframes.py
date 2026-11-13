import copy,tempfile,unittest
from pathlib import Path
from agentrader.alert_timeframes import align,intervals
from agentrader.price_alerts import definition,PriceAlerts,PriceAlertWorker,AlertError
from agentrader.market_data import INTERVALS,SOURCE,bucket
from agentrader.migrations import migrate
T=1800057600

def condition(interval):return dict(interval=interval,left=dict(type='market',field='close'),right=dict(type='value',value='100'),upper=None,operator='above',bars=1)
def draft():return dict(schema='technical-alert/3',name='MTF',symbol='BTCUSDT',interval='1h',frequency='bar_close',expires_at=None,message='',match='all',conditions=[condition('1m'),condition('5m')])
def context(interval,last,price=101):
    step=INTERVALS[interval]//1000
    rows=[]
    for t in range(last-step*3,last+1,step):rows.append(dict(time=t,close_time=(t+step)*1000-1,closed=True,close=price,exact=dict(state='VERIFIED',close=str(price))))
    return dict(identity=dict(source=SOURCE,environment='live_public',product='USD-M',price_type='LAST_PRICE',symbol='BTCUSDT',interval=interval),rows=rows,transport_state='LIVE',timing=dict(state='FRESH'),quality=dict(state='OK'),stream_epoch='epoch')
def sources(base=T+600,higher=T+300):return {'1m':context('1m',base),'5m':context('5m',higher)}

class TimeframeTests(unittest.TestCase):
    def test_definition_normalizes_smallest_clock_and_rejects_unknown(self):
        d=definition(draft());self.assertEqual(d['interval'],'1m');self.assertEqual(intervals(d),['1m','5m']);self.assertEqual(d['conditions'][1]['interval'],'5m')
        for value in ('2m',None,[]):
            bad=draft();bad['conditions'][0]['interval']=value
            with self.assertRaises(AlertError):definition(bad)
    def test_asof_join_uses_last_fully_closed_higher_bar(self):
        d=definition(draft());c=sources(higher=T+600);a=align(d,c)
        self.assertEqual(a['_aligned_rows']['5m'][-1]['time'],T+300)
        self.assertEqual(a['_aligned_rows']['1m'][-1]['time'],T+600)
        c=sources(base=T+540);self.assertEqual(align(d,c)['_aligned_rows']['5m'][-1]['time'],T+300)
    def test_week_anchor_and_closed_boundary(self):
        d=draft();d['conditions'][1]['interval']='1w';d=definition(d);base=T+600;cutoff=base+60;last=bucket(cutoff*1000,'1w')//1000-604800
        a=align(d,{'1m':context('1m',base),'1w':context('1w',last)})
        self.assertEqual(a['_aligned_rows']['1w'][-1]['time'],last)
    def test_stale_or_wrong_identity_blocks_even_any_and_epoch_changes(self):
        d=definition(draft());c=sources();a=align(d,c);c['5m']['stream_epoch']='new';self.assertNotEqual(a['stream_epoch'],align(d,c)['stream_epoch'])
        c['5m']['timing']['state']='STALE';self.assertIsNone(align(d,c));c=sources();c['5m']['identity']['symbol']='ETHUSDT';self.assertIsNone(align(d,c))
    def test_late_boundary_waits_then_fires_once_without_future_or_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'a.db';migrate(db);s=PriceAlerts(db,'test');a=s.save(draft())
            def run(c,boot='b'):s.process(a['id'],{'_source_contexts':c},boot)
            run(sources(base=T+480,higher=T));self.assertEqual(s.events(),[])
            run(sources(base=T+540,higher=T));self.assertEqual(s.list()[0]['readiness'],'WAITING_ALIGNMENT');self.assertEqual(s.events(),[])
            run(sources(base=T+540,higher=T+300));self.assertEqual(len(s.events()),1)
            e=s.events()[0];self.assertEqual(e['source_closes'],{'1m':T+540,'5m':T+300});run(sources(base=T+540,higher=T+300));self.assertEqual(len(s.events()),1)
            c=sources(base=T+600);c['5m']['stream_epoch']='restart';run(c);self.assertEqual(len(s.events()),1)
            run(sources(base=T+660),'newboot');self.assertEqual(len(s.events()),1)
    def test_worker_acquires_all_intervals_and_releases_on_pause(self):
        class Hub:
            def __init__(self):self.held=set()
            def acquire(self,symbol,period):self.held.add(period);return period
            def release(self,token):self.held.remove(token)
            def binding_context(self,symbol,period):return sources()[period]
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'a.db';migrate(db);s=PriceAlerts(db,'test');a=s.save(draft());h=Hub();w=PriceAlertWorker(s,h);w.tick();self.assertEqual(h.held,{'1m','5m'});s.action(a['id'],1,'pause');w.tick();self.assertEqual(h.held,set());w.close()
