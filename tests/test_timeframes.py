import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from agentrader.market_data import INTERVALS, bucket, fetch_candles
from agentrader.chart_market import ChartMarket, InvalidMarket
from agentrader.market_feed import FeedState
from agentrader.higher_timeframe import higher_context
from agentrader.drawings.service import DrawingService, management
from agentrader.migrations import migrate

NOW=1800000000123
def raw(t,step):return [t,'100','110','90','105','10',t+step-1,'1050',5,'5','525','0']
class Clock:
    def __init__(self,stamp=NOW):self.stamp=stamp;self.elapsed=0
    def wall(self):return self.stamp/1000
    def mono(self):return 1000+self.elapsed/1000
    def advance(self,ms):self.stamp+=ms;self.elapsed+=ms
class Source:
    def __init__(self,clock):self.clock=clock;self.calls=[]
    def get(self,path,params=None):
        self.calls.append((path,params))
        if path.endswith('/time'):return {'serverTime':self.clock.stamp}
        if path.endswith('exchangeInfo'):return {'symbols':[dict(symbol='BTCUSDT',baseAsset='BTC',quoteAsset='USDT',status='TRADING',contractType='PERPETUAL',filters=[dict(filterType='PRICE_FILTER',tickSize='0.25')])]}
        assert path=='/fapi/v1/klines'
        step=INTERVALS[params['interval']];current=bucket(self.clock.stamp,params['interval']);rows=[raw(current-i*step,step) for i in range(800,-1,-1)]
        return [r for r in rows if r[0]<=params['endTime']][-params['limit']:]

class TimeframeTests(unittest.TestCase):
    def test_interval_contract_and_utc_boundaries_include_new_three(self):
        contract=json.loads((Path(__file__).parents[1]/'docs/chart/contracts/intervals-v1.json').read_text())
        self.assertEqual(INTERVALS,contract['milliseconds'])
        for interval,step in INTERVALS.items():
            start=bucket(NOW,interval);self.assertEqual(bucket(start,interval),start);self.assertEqual(bucket(start+step-1,interval),start);self.assertEqual(bucket(start+step,interval),start+step)
        self.assertEqual(bucket(345600000,'1w'),345600000)

    def test_each_new_native_history_pagination_warmup_and_closed_feed_reconnect(self):
        for interval in ['1m','5m','30m']:
            with self.subTest(interval=interval),tempfile.TemporaryDirectory() as folder:
                step=INTERVALS[interval];clock=Clock(bucket(NOW,interval)+step-2000);source=Source(clock)
                market=ChartMarket(Path(folder)/'market.db',client_factory=lambda:source,clock=clock.wall,monotonic=clock.mono)
                history=market.history('BTCUSDT',interval,limit=300);self.assertEqual(len(history['candles']),300);self.assertFalse(history['candles'][-1]['closed']);self.assertEqual(history['precision']['state'],'VERIFIED')
                older=market.history('BTCUSDT',interval,limit=300,end_time=history['next_end_time']);self.assertLess(older['candles'][-1]['time'],history['candles'][0]['time'])
                pages,_=fetch_candles(source,'BTCUSDT',interval,clock.stamp,bars=600);self.assertEqual(len(pages),601);self.assertEqual(len({r[0] for r in pages}),601)
                state=FeedState('BTCUSDT',interval,clock=clock.wall,monotonic=clock.mono);state.seed(history);self.assertEqual(state.evidence.view()['warmup_available_closed_bars'],299)
                current=history['candles'][-1]['time']*1000;clock.advance(2000)
                event=dict(e='kline',E=clock.stamp,s='BTCUSDT',k=dict(s='BTCUSDT',i=interval,t=current,T=current+step-1,x=True,o='100',h='110',l='90',c='105',v='11',q='1155',n=6,V='5',Q='525'))
                state.apply(event);self.assertTrue(state.rows[-1]['closed']);self.assertEqual(state.evidence.view()['warmup_available_closed_bars'],300)
                generation,epoch=state.generation,state.stream_epoch;state.seed(market.history('BTCUSDT',interval,force=True));self.assertGreater(state.generation,generation);self.assertNotEqual(state.stream_epoch,epoch)
                self.assertEqual(len({r['time'] for r in state.rows}),len(state.rows))
                self.assertTrue(all(path in ['/fapi/v1/klines','/fapi/v1/time','/fapi/v1/exchangeInfo'] for path,_ in source.calls))

    def test_native_higher_candle_at_boundary_obeys_clock_uncertainty_and_no_lookahead(self):
        with tempfile.TemporaryDirectory() as folder:
            boundary=bucket(NOW,'1h');clock=Clock(boundary);source=Source(clock);market=ChartMarket(Path(folder)/'market.db',client_factory=lambda:source,clock=clock.wall,monotonic=clock.mono)
            # At exact server boundary,1ms uncertainty conservatively excludes the just-closed bar.
            early=higher_context(market,'BTCUSDT','1m','1h',boundary)
            self.assertEqual(early['state'],'READY');self.assertEqual(early['candle']['time']*1000,boundary-2*INTERVALS['1h'])
            clock.advance(10);ready=higher_context(market,'BTCUSDT','1m','1h',boundary)
            self.assertEqual(ready['candle']['time']*1000,boundary-INTERVALS['1h']);self.assertLess(ready['candle']['close_time'],ready['effective_reference_time'])
            self.assertEqual(ready['provenance'],'BINANCE_NATIVE_KLINE');self.assertFalse(ready['resampled']);self.assertFalse(ready['order_authority'])
            historical=higher_context(market,'BTCUSDT','1m','1h',boundary-10*60000)
            self.assertLess(historical['candle']['close_time'],boundary-10*60000)

    def test_clock_gap_precision_and_wrong_source_block_instead_of_using_open_or_stale_bar(self):
        with tempfile.TemporaryDirectory() as folder:
            clock=Clock(bucket(NOW,'1h')+10000);source=Source(clock);market=ChartMarket(Path(folder)/'market.db',client_factory=lambda:source,clock=clock.wall,monotonic=clock.mono)
            baseline=market.history('BTCUSDT','1h',limit=4,end_time=clock.stamp,force=True)
            for mutate,reason in [(lambda h:h['clock_sample'].update(state='UNTRUSTED'),'CLOCK_UNTRUSTED'),(lambda h:h['quality'].update(missing_bars=1),'GRID_GAP'),(lambda h:h['precision'].update(state='UNPROVEN'),'PRICE_PRECISION_UNPROVEN'),(lambda h:h.update(symbol='ETHUSDT'),'SOURCE_CONTEXT_MISMATCH')]:
                h=copy.deepcopy(baseline);mutate(h);fake=Mock();fake.history.return_value=h;r=higher_context(fake,'BTCUSDT','1m','1h',clock.stamp);self.assertEqual(r['reason'],reason);self.assertIsNone(r['candle'])
            h=copy.deepcopy(baseline)
            for c in h['candles']:c['closed']=False
            fake=Mock();fake.history.return_value=h;self.assertEqual(higher_context(fake,'BTCUSDT','1m','1h',clock.stamp)['state'],'UNAVAILABLE')

    def test_workspace_and_drawing_visibility_persist_all_eight_intervals(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'app.db';migrate(db);s=DrawingService(db,'owner')
            for revision,interval in enumerate(['1m','5m','30m']):self.assertEqual(s.save_workspace('main','pref-'+interval,revision,dict(symbol='BTCUSDT',interval=interval))['preferences']['interval'],interval)
            self.assertEqual(DrawingService(db,'owner').workspace('main')['preferences']['interval'],'30m')
            self.assertEqual(len(management(management()|dict(intervals=list(INTERVALS)))['intervals']),8)

    def test_api_public_context_and_invalid_higher_request(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder);clock=Clock(NOW);source=Source(clock);market=ChartMarket(f/'market.db',client_factory=lambda:source,clock=clock.wall,monotonic=clock.mono)
            with TestClient(create_app(WebSettings(f/'app.db',f/'exec.db',market_database=f/'market.db'),market=market),base_url='http://127.0.0.1') as c:
                r=c.get('/api/higher-context',params=dict(symbol='BTCUSDT',base_interval='1m',interval='1h',reference_time=NOW));self.assertEqual(r.status_code,200);self.assertEqual(r.json()['state'],'READY')
                bad=c.get('/api/higher-context',params=dict(symbol='BTCUSDT',base_interval='1h',interval='1m',reference_time=NOW));self.assertEqual(bad.status_code,422)
                self.assertFalse(c.get('/api/health').json()['trading_commands_enabled'])
