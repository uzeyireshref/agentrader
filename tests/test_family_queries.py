"""G4 real HTTP: all family variants, LOG and regression readiness/recovery."""
import copy
import unittest

from agentrader.chart.chart_clock import measure_time
from scripts.integration.chart_tool_matrix_cases import candles
import test_chart_queries as query_fixture
import test_family_math as math_fixture


@unittest.skipUnless(query_fixture.HAS_WEB,'Optional web dependencies not installed')
class FamilyHTTPTests(unittest.TestCase):
    def setUp(self):
        self.http=query_fixture.ChartQueryTests()
        self.http.setUp();self.addCleanup(self.http.doCleanups)
        self.f=self.http.fixture

    def entry(self,kind,op='boundsAt',inputs=None,**options):
        g=math_fixture.geometry(kind)
        if kind=='regression_channel':
            g['anchors']=[dict(time=t,price='999') for t in math_fixture.FIXTURE['regression']['raw_times']]
        item=self.f.drawings.create('main','g4-'+kind,g)
        return dict(query_id=kind,drawing_id=item['drawing_id'],expected_revision=1,operation=op,
                    inputs=inputs if inputs is not None else dict(time=self.f.rows[25]['time']),**options)

    def test_all_eight_families_http_and_log_share_reference_geometry_without_writes(self):
        entries=[self.entry(c['kind']) for c in math_fixture.FIXTURE['cases']]
        entries.append(self.entry('regression_channel',inputs=dict(time=math_fixture.FIXTURE['regression']['raw_times'][1])))
        before=self.f.database.read_bytes()
        response=self.http.batch(entries);self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['summary'],dict(succeeded=8,failed=0))
        for c,result,entry in zip(math_fixture.FIXTURE['cases'],response.json()['results'],entries):
            for key in ('lower','upper','middle'):
                self.assertEqual(math_fixture.numeric(result['result']['value'][key]),math_fixture.Fraction(c['expected'][key]))
            single=self.http.single(entry);self.assertEqual(single.json()['results'][0],result)
        for entry in entries:
            log=self.http.single({**entry,'scale':'LOG'})
            self.assertEqual(log.status_code,200,log.text)
            self.assertFalse(log.json()['order_authority'])
        regression=response.json()['results'][-1]['result']['regression']
        self.assertEqual(regression['effective_anchor_times'],math_fixture.FIXTURE['regression']['effective_times'])
        self.assertEqual(regression['sample_count'],3)
        self.assertEqual(self.f.database.read_bytes(),before)

    def test_same_candle_open_candle_and_future_recovery_preserve_raw_record(self):
        entry=self.entry('regression_channel',inputs=dict(time=self.f.rows[290]['time']))
        item=self.f.drawings.show(entry['drawing_id']);g=copy.deepcopy(item['geometry'])
        g['anchors']=[dict(time=self.f.rows[i]['time']+225,price='999') for i in (280,299)]
        self.f.drawings.update(item['drawing_id'],'open-anchors',1,g);entry['expected_revision']=2
        self.assertEqual(self.http.single(entry).json()['results'][0]['state'],'WAITING_FOR_DATA')
        included=self.http.single(entry,{**self.http.context,'include_open':True})
        self.assertEqual(included.status_code,200,included.text)
        self.assertTrue(included.json()['results'][0]['result']['regression']['open_candle_used'])
        g['anchors']=[dict(time=self.f.rows[280]['time']+offset,price='999') for offset in (225,450)]
        self.f.drawings.update(item['drawing_id'],'same-bar',2,g);entry['expected_revision']=3
        same=self.http.single(entry).json()['results'][0]
        self.assertEqual(same['state'],'WARMUP')
        self.assertEqual(same['error']['details']['sample_count'],1)
        self.assertEqual(same['error']['details']['effective_anchor_times'],[self.f.rows[280]['time']]*2)
        future=candles(340)
        g['anchors']=[dict(time=future[i]['time']+225,price='999') for i in (305,319)]
        self.f.drawings.update(item['drawing_id'],'future',3,g);entry['expected_revision']=4;entry['inputs']['time']=future[310]['time']+225
        self.assertEqual(self.http.single(entry).json()['results'][0]['state'],'WAITING_FOR_DATA')
        self.f.now[0]=future[-1]['time']+2
        client=query_fixture.SimpleNamespace(get=lambda *_:dict(serverTime=int(self.f.now[0]*1000)))
        sample=measure_time(client,lambda:self.f.now[0],lambda:self.f.mono[0])[1]
        self.f.state.seed(dict(clock_sample=sample,server_time=int(self.f.now[0]*1000),market=self.f.market,quality=dict(state='OK',missing_bars=0),candles=future))
        self.f.state.timing.observe(int(self.f.now[0]*1000));self.f.state.state='LIVE'
        result=self.http.single(entry)
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['results'][0]['result']['regression']['effective_anchor_times'],[future[i]['time'] for i in (305,319)])
        self.assertEqual(self.f.drawings.show(item['drawing_id'])['geometry'],g)
