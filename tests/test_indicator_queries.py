"""G5 HTTP acceptance: saved configs, real FeedState, independent existing vectors."""
import copy
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentrader.chart.chart_clock import measure_time
from agentrader.chart.chart_precision import exact_tick
from agentrader.chart.indicator_queries import REQUEST_SCHEMA
from agentrader.chart.indicator_config import defaults_v4
from scripts.integration.chart_tool_matrix_cases import candles
import test_chart_context as context_fixture

ROOT=Path(__file__).resolve().parents[1]
HAS_WEB=all(importlib.util.find_spec(m) is not None for m in ('fastapi','httpx'))


def numeric(value):
    return Fraction(int(value['numerator']),int(value['denominator'])) if 'numerator' in value else float(value['decimal'])


@unittest.skipUnless(HAS_WEB,'Optional web dependencies not installed')
class IndicatorHTTPTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        self.f=context_fixture.ChartContextTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.serial=0
        self.context=dict(symbol='BTCUSDT',interval='15m',required_closed_bars=1,include_open=True)
        self.seed(candles(300))
        settings=WebSettings(self.f.database,Path(self.f.temp.name)/'execution.db','','owner',market_database=Path(self.f.temp.name)/'market.db')
        self.settings=settings
        self.app=create_app(settings,hub=SimpleNamespace(binding_context=self.f.hub.binding_context,close=lambda:None))
        self.client=self.enterContext(TestClient(self.app,base_url='http://127.0.0.1'))
        self.app.state.shadow_worker.close();self.app.state.alert_worker.close()
        self.configs={c['indicator_id']:c for c in self.f.indicators.load('main',4)['indicators']}
        config=copy.deepcopy(self.configs['anchored-vwap']);config['params'].update(anchor_time=self.f.rows[20]['time'],anchor_symbol='BTCUSDT')
        self.save(config)

    def seed(self,data,interval='15m',symbol='BTCUSDT'):
        rows=copy.deepcopy(data)
        for r in rows:
            if 'exact' not in r:r['exact']=dict(schema='chart-exact-decimal/1',state='VERIFIED',provenance='UPSTREAM_DECIMAL_TEXT')
            for name in ('open','high','low','close','volume','quote_volume'):r['exact'].setdefault(name,str(r[name]))
        self.f.rows=rows
        self.f.now[0]=max([r['close_time']/1000+.001 for r in rows if r['closed']]+[rows[-1]['time']+2.])
        self.f.market=dict(symbol=symbol,tick_size='0.00000001',exact=exact_tick('0.00000001'))
        self.f.state.symbol=symbol;self.f.state.interval=interval
        client=SimpleNamespace(get=lambda *_:dict(serverTime=int(self.f.now[0]*1000)))
        sample=measure_time(client,lambda:self.f.now[0],lambda:self.f.mono[0])[1]
        step={'15m':900,'1d':86400,'1w':604800}[interval]
        gaps=sum(max(0,(b['time']-a['time'])//step-1) for a,b in zip(rows,rows[1:]))
        self.f.state.seed(dict(clock_sample=sample,server_time=int(self.f.now[0]*1000),market=self.f.market,
                               quality=dict(state='GAP' if gaps else 'OK',missing_bars=gaps),candles=rows))
        self.f.state.timing.observe(int(self.f.now[0]*1000));self.f.state.state='LIVE'
        self.f.hub.feeds.clear();self.f.hub.feeds[(symbol,interval)]=self.f.feed
        self.context.update(symbol=symbol,interval=interval)

    def save(self,config):
        loaded=self.f.indicators.load('main',4)
        items=[{**config,'revision':c['revision']} if c['indicator_id']==config['indicator_id'] else c for c in loaded['indicators']]
        self.serial+=1
        result=self.f.indicators.save('main','g5-save-'+str(self.serial),loaded['revision'],items,4)
        self.configs={c['indicator_id']:c for c in result['indicators']}

    def entry(self,indicator_id,operation='latest',inputs=None,**kwargs):
        return dict(query_id=indicator_id,indicator_id=indicator_id,expected_revision=self.configs[indicator_id]['revision'],
                    operation=operation,inputs=inputs or {},**kwargs)

    def call(self,entries,context=None):
        return self.client.post('/api/workspaces/main/indicator-queries',json=dict(schema_version=REQUEST_SCHEMA,context=context or self.context,queries=entries))

    def test_all_nine_configs_latest_series_at_and_readonly_context(self):
        self.f.create()
        before=self.f.database.read_bytes()
        entries=[self.entry(key) for key in self.configs]
        response=self.call(entries);self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['summary'],dict(succeeded=9,failed=0))
        for result in response.json()['results']:
            with self.subTest(indicator=result['indicator_id']):
                key=result['indicator_id'];last=self.f.rows[-1]['time']
                at=self.call([self.entry(key,'at',dict(time=last+225))]).json()['results'][0]
                page=self.call([self.entry(key,'series',dict(start_time=last))]).json()['results'][0]
                self.assertEqual(at['outputs'],result['outputs']);self.assertEqual(page['outputs'],result['outputs'])
                self.assertEqual(at['effective_time'],last)
                self.assertFalse(result['configuration']['enabled'])
                self.assertFalse(result['order_authority'])
                self.assertEqual(result['timezone'],'UTC')
        self.assertEqual(self.f.database.read_bytes(),before)
        self.assertFalse(self.settings.execution_database.exists());self.assertFalse(self.settings.market_database.exists())

    def test_existing_basic_and_multi_numeric_fixture_groups_through_http(self):
        for filename in ('indicators-v2-parity.json','g05-multi-parity.json'):
            fixture=json.loads((ROOT/'frontend/tests/fixtures'/filename).read_text())
            self.seed(fixture['rows'])
            for case in fixture['cases']:
                with self.subTest(fixture=filename,id=case['config']['indicator_id'],source=case['config']['source']):
                    self.save(case['config']);key=case['config']['indicator_id']
                    response=self.call([self.entry(key,'series',dict(limit=200))])
                    self.assertEqual(response.status_code,200,response.text)
                    result=response.json()['results'][0]
                    expected=case.get('outputs',{'value':case.get('points')})
                    for name,points in expected.items():
                        actual=[p for p in result['outputs'][name]['points'] if p['state']=='READY']
                        self.assertEqual(len(actual),len(points))
                        for a,b in zip(actual,points):
                            self.assertEqual(a['display_time'],b['time'])
                            self.assertAlmostEqual(float(numeric(a['value'])),b['value'],places=9)

    def test_partial_macd_warmup_and_missing_history_do_not_return_zero(self):
        self.seed(candles(30))
        result=self.call([self.entry('macd-main')]).json()['results'][0]
        self.assertEqual(result['state'],'WARMUP')
        self.assertEqual(result['outputs']['macd']['state'],'READY')
        for name in ('signal','histogram'):
            self.assertNotIn('value',result['outputs'][name]['points'][0])
            self.assertEqual(result['outputs'][name]['required_input_count'],34)
        only=self.call([self.entry('macd-main',outputs=['macd'])]).json()['results'][0]
        self.assertEqual(only['state'],'READY')
        result=self.call([self.entry('ema-slow')]).json()['results'][0]
        self.assertEqual(result['state'],'WARMUP');self.assertEqual(result['warmup']['required_input_counts']['value'],50)
        early=self.call([self.entry('ema-fast','at',dict(time=self.f.rows[0]['time']))]).json()['results'][0]
        self.assertEqual(early['state'],'WARMUP');self.assertEqual(early['outputs']['value']['available_input_count'],1)
        self.assertEqual(early['outputs']['value']['loaded_input_count'],30)
        self.assertEqual(early['calculation_input_range']['count'],1)

    def test_pagination_never_reseeds_and_requires_unchanged_context(self):
        first=self.call([self.entry('ema-fast','series',dict(limit=25))]).json()
        context_id=first['context_id']
        self.assertEqual(self.call([self.entry('ema-fast','series',dict(limit=25,offset=25))]).json()['results'][0]['error']['code'],'PAGINATION_CONTEXT_REQUIRED')
        second=self.call([self.entry('ema-fast','series',dict(limit=25,offset=25))],{**self.context,'expected_context_id':context_id}).json()
        at_time=second['results'][0]['outputs']['value']['points'][0]['time']
        at=self.call([self.entry('ema-fast','at',dict(time=at_time))]).json()['results'][0]['outputs']['value']['points'][0]
        self.assertEqual(at,second['results'][0]['outputs']['value']['points'][0])
        config=copy.deepcopy(self.configs['ema-fast']);config['period']=19;self.save(config)
        self.assertEqual(self.call([self.entry('ema-fast')],{**self.context,'expected_context_id':context_id}).status_code,409)

    def test_bb_display_offset_is_separate_from_source_time(self):
        config=copy.deepcopy(self.configs['bb-main']);config['params']['offset']=2;self.save(config)
        result=self.call([self.entry('bb-main')]).json()['results'][0]
        for output in result['outputs'].values():
            point=output['points'][0];self.assertEqual(point['display_time'],point['time']+1800)
        at=self.call([self.entry('bb-main','at',dict(time=self.f.rows[-1]['time']))]).json()['results'][0]
        self.assertEqual(result['outputs'],at['outputs'])

    def test_timezone_invalid_inputs_bounds_and_local_boundary(self):
        entry=self.entry('session-vwap',timezone='Europe/Istanbul')
        result=self.call([entry]).json()['results'][0]
        self.assertEqual(result['state'],'UNSUPPORTED_OPERATION');self.assertEqual(result['error']['code'],'UNSUPPORTED_TIMEZONE')
        for entry in [self.entry('ema-fast','at',dict(time=self.f.rows[-1]['time']*1000)),self.entry('ema-fast','series',dict(limit=201)),self.entry('ema-fast','series',dict(offset=-1)),self.entry('ema-fast',outputs=['unknown']),self.entry('ema-fast',period=3)]:
            self.assertEqual(self.call([entry]).json()['results'][0]['state'],'INVALID_INPUT')
        path='/api/workspaces/main/indicator-queries'
        for entries in ([],[self.entry('ema-fast')]*10):self.assertEqual(self.call(entries).status_code,422)
        self.assertEqual(self.client.post(path,json={},headers={'Origin':'http://foreign.invalid'}).status_code,403)
        self.assertEqual(self.client.post(path,content='x'*65537,headers={'Content-Type':'application/json'}).status_code,422)

    def test_stale_reconnect_revision_race_and_output_deadline(self):
        entry=self.entry('ema-fast')
        self.f.now[0]+=11;self.f.mono[0]+=11
        self.assertEqual(self.call([entry]).json()['results'][0]['state'],'STALE')
        self.seed(candles(300));self.assertEqual(self.call([entry]).json()['results'][0]['state'],'READY')
        changed=copy.deepcopy(self.configs['ema-fast']);changed['period']=18;self.save(changed)
        self.assertEqual(self.call([entry]).json()['results'][0]['state'],'REVISION_CONFLICT')
        service=self.app.state.indicator_queries;original=service._evaluate
        def race(*args):
            result=original(*args);self.f.state.sequence+=1;return result
        with patch.object(service,'_evaluate',side_effect=race):self.assertEqual(self.call([self.entry('ema-fast')]).status_code,409)
        with patch('agentrader.chart.indicator_queries.MAX_OUTPUT_BYTES',100):self.assertEqual(self.call([self.entry('ema-fast')]).status_code,413)
        with patch.object(service.context,'monotonic',side_effect=[0,3,3]):self.assertEqual(self.call([self.entry('ema-fast')]).status_code,503)

    def test_existing_vwap_fixture_group_through_http_including_gaps_and_exact_ratios(self):
        fixture=json.loads((ROOT/'frontend/tests/fixtures/vwap-parity.json').read_text())
        for index,case in enumerate(fixture['cases']):
            with self.subTest(case=index,dataset=case['dataset'],id=case['config']['indicator_id']):
                self.seed(fixture['datasets'][case['dataset']],case['interval'],case['symbol'])
                self.save(case['config']);key=case['config']['indicator_id']
                response=self.call([self.entry(key,'series',dict(limit=200))])
                self.assertEqual(response.status_code,200,response.text)
                result=response.json()['results'][0]
                self.assertIn('outputs',result,result)
                points=result['outputs']['value']['points'];expected=case['result']
                self.assertEqual([(p['time'],p.get('reason','READY')) for p in points],[(p['time'],p['state']) for p in expected['states']])
                ready=[p for p in points if p['state']=='READY']
                self.assertEqual(len(ready),len(expected['points']))
                for a,b in zip(ready,expected['points']):
                    self.assertEqual(a['time'],b['time']);self.assertAlmostEqual(float(numeric(a['value'])),b['value'],places=9)
                    if 'exact_ratio' in b:self.assertEqual(numeric(a['value']),Fraction(int(b['exact_ratio']['numerator']),int(b['exact_ratio']['denominator'])))

    def test_independent_small_numeric_vectors_for_all_nine_slots_and_rsi_versions(self):
        start=1800000000//86400*86400
        rows=[dict(time=start+i*900,close_time=(start+(i+1)*900)*1000-1,closed=True,
                   open=v,high=v+1,low=v-.1,close=v,volume=1,quote_volume=v) for i,v in enumerate([1,2,3,8])]
        self.seed(rows)
        for key,old in list(self.configs.items()):
            config=copy.deepcopy(old)
            if key in ('ema-fast','sma-main','atr-main','bb-main','macd-main'):config['period']=3
            if key in ('ema-slow','rsi-main'):config['period']=2
            if key=='macd-main':config['params'].update(fast_period=2,signal_period=2)
            if key=='bb-main':config['params']['basis_type']='EMA'
            if 'VWAP' in config['kind']:config['source']='close'
            if key=='anchored-vwap':config['params'].update(anchor_time=start,anchor_symbol='BTCUSDT')
            self.save(config)
        result=self.call([self.entry(key) for key in self.configs]).json()
        self.assertEqual(result['summary'],dict(succeeded=9,failed=0))
        actual={r['indicator_id']:{k:float(numeric(v['points'][0]['value'])) for k,v in r['outputs'].items()} for r in result['results']}
        for key,expected in [('ema-fast',5),('ema-slow',Fraction(37,6)),('sma-main',Fraction(13,3)),('atr-main',Fraction(47,15)),('rsi-main',100),('session-vwap',3.5),('anchored-vwap',3.5)]:
            self.assertAlmostEqual(actual[key]['value'],float(expected),places=9)
        for field,expected in [('macd',Fraction(7,6)),('signal',Fraction(5,6)),('histogram',Fraction(1,3))]:self.assertAlmostEqual(actual['macd-main'][field],float(expected),places=9)
        self.assertAlmostEqual(actual['bb-main']['basis'],5);self.assertAlmostEqual(actual['bb-main']['upper'],5+2*(62**.5)/3)
        self.assertAlmostEqual(actual['bb-main']['lower'],5-2*(62**.5)/3)
        flat=[{**r,'open':5,'high':6,'low':4,'close':5} for r in rows]
        self.seed(flat)
        for version,expected in [(1,50),(2,100)]:
            config=copy.deepcopy(self.configs['rsi-main']);config['calculation_version']=version;self.save(config)
            point=self.call([self.entry('rsi-main')]).json()['results'][0]['outputs']['value']['points'][0]
            self.assertEqual(float(numeric(point['value'])),expected)

    def test_vwap_segment_proofs_remain_separate_from_blocked_whole_source(self):
        fixture=json.loads((ROOT/'frontend/tests/fixtures/vwap-parity.json').read_text())
        self.seed(fixture['datasets']['gap'])
        response=self.call([self.entry('session-vwap')]).json()
        self.assertEqual(response['readiness']['state'],'WAITING_FOR_DATA')
        self.assertEqual(response['readiness']['proof']['state'],'BLOCKED')
        result=response['results'][0];self.assertEqual(result['state'],'READY')
        self.assertTrue(result['ready_segments'])
        self.assertTrue(all(s['proof']['state']=='VERIFIED' for s in result['ready_segments']))
        self.assertEqual(result['data_proof_scope'],'VWAP_VALIDATED_SEGMENTS_WHOLE_SOURCE_STILL_BLOCKED')
        blocked=self.call([self.entry('ema-fast')]).json()['results'][0]
        self.assertEqual(blocked['state'],'WAITING_FOR_DATA')

    def test_open_candle_owner_scope_missing_time_and_parallel_reads(self):
        entry=self.entry('ema-fast','at',dict(time=self.f.rows[-1]['time']+225))
        closed=self.call([entry],{**self.context,'include_open':False}).json()['results'][0]
        self.assertEqual(closed['state'],'WAITING_FOR_DATA')
        self.assertEqual(closed['outputs']['value']['reason'],'OPEN_CANDLE_EXCLUDED')
        self.assertEqual(self.call([entry]).json()['results'][0]['state'],'READY')
        missing=self.call([self.entry('ema-fast','at',dict(time=self.f.rows[-1]['time']+900))]).json()['results'][0]
        self.assertEqual(missing['outputs']['value']['reason'],'CANDLE_NOT_LOADED')
        from agentrader.chart.indicator_config import IndicatorService
        other=IndicatorService(self.f.database,'foreign');config=other.load('main',4);config['indicators'][0]['period']=2
        other.save('main','foreign',0,config['indicators'],4)
        self.assertEqual(self.call([self.entry('ema-fast')]).json()['results'][0]['configuration']['period'],20)
        from concurrent.futures import ThreadPoolExecutor
        service=self.app.state.indicator_queries
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(service.run,'main',REQUEST_SCHEMA,self.context,[self.entry('ema-fast')]) for _ in range(2)]
            a,b=[f.result() for f in futures]
        self.assertEqual(a['context_id'],b['context_id']);self.assertEqual(a['results'],b['results'])
