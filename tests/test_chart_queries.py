"""G3 HTTP acceptance against independent rational references and real FeedState."""
import copy
import hashlib
import importlib.util
from fractions import Fraction
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentrader.chart.chart_clock import measure_time
from agentrader.chart.chart_queries import REQUEST_SCHEMA
from agentrader.chart.drawings.service import DrawingService
from scripts.integration.chart_tool_matrix_cases import drawing_cases, candles
import test_chart_context as context_fixture
from test_chart_position import plan

HAS_WEB = all(importlib.util.find_spec(module) is not None for module in ('fastapi', 'httpx'))


@unittest.skipUnless(HAS_WEB, 'Optional web dependencies not installed')
class ChartQueryTests(unittest.TestCase):
    def setUp(self):
        from pathlib import Path
        from fastapi.testclient import TestClient
        from agentrader.application.settings import WebSettings
        from agentrader.api.app import create_app
        f = self.fixture = context_fixture.ChartContextTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.rows = candles(300)
        f.now[0] = f.rows[-1]['time']+2.
        client = SimpleNamespace(get=lambda *_: dict(serverTime=int(f.now[0]*1000)))
        sample = measure_time(client, lambda:f.now[0], lambda:f.mono[0])[1]
        f.state.seed(dict(clock_sample=sample, server_time=int(f.now[0]*1000), market=f.market,
                          quality=dict(state='OK', missing_bars=0), candles=f.rows))
        f.state.timing.observe(int(f.now[0]*1000))
        f.state.state = 'LIVE'
        settings = WebSettings(f.database, Path(f.temp.name)/'execution.db', '', 'owner', market_database=Path(f.temp.name)/'market.db')
        self.settings = settings
        app = self.app = create_app(settings, hub=SimpleNamespace(binding_context=f.hub.binding_context, close=lambda:None))
        self.client = self.enterContext(TestClient(app, base_url='http://127.0.0.1'))
        app.state.shadow_worker.close()
        app.state.alert_worker.close()
        self.items = {case['case_id']: f.drawings.create('main', case['case_id'], case['geometry']) for case in drawing_cases()}
        self.context = dict(symbol='BTCUSDT', interval='15m')
        self.time = f.rows[287]['time']

    def entry(self, case, operation, inputs=None, **options):
        item = self.items[case]
        return dict(query_id=case, drawing_id=item['drawing_id'],
                    **{'expected_revision': item['revision'], 'operation': operation, 'inputs': inputs or {}, **options})

    def batch(self, entries, context=None):
        return self.client.post('/api/workspaces/main/chart-queries', json=dict(schema_version=REQUEST_SCHEMA, context=context or self.context, queries=entries))

    def single(self, entry, context=None):
        entry = copy.deepcopy(entry)
        drawing_id = entry.pop('drawing_id')
        return self.client.post('/api/drawings/'+drawing_id+'/queries', json=dict(schema_version=REQUEST_SCHEMA, context=context or self.context, query=entry))

    def fraction(self, encoded):
        return Fraction(int(encoded['numerator']), int(encoded['denominator']))

    def test_all_14_math_variants_have_single_batch_parity_and_revision_evidence(self):
        entries = []
        for case in drawing_cases():
            cid, g = case['case_id'], case['geometry']
            if g.get('schema') == 'chart-channel-family/1' or g['kind'] in ('text', 'note', 'price_label'):
                continue
            op = 'level' if g['kind'] in ('fibonacci', 'fibonacci_extension') else 'contains' if g['kind']=='zone' else 'boundsAt' if g['kind']=='parallel_channel' else 'riskReward' if g['kind'] in ('long_plan','short_plan') else 'measurement' if g['kind']=='ruler' else 'priceAt'
            inputs = {} if op in ('measurement','riskReward') else dict(time=self.time)
            if op == 'level': inputs['ratio']='0.618'
            if op == 'contains': inputs['query_price']='120'
            entries.append(self.entry(cid, op, inputs))
        before = hashlib.sha256(self.fixture.database.read_bytes()).hexdigest()
        response = self.batch(entries)
        self.assertEqual(response.status_code, 200, response.text)
        batch = response.json()
        self.assertEqual(batch['summary'], dict(succeeded=14, failed=0))
        for entry, result in zip(entries, batch['results']):
            with self.subTest(case=entry['query_id']):
                single = self.single(entry)
                self.assertEqual(single.status_code, 200, single.text)
                self.assertEqual(single.json()['results'][0], result)
                self.assertEqual(single.json()['context_id'], batch['context_id'])
                self.assertEqual(result['revision'], entry['expected_revision'])
                self.assertEqual(result['inputs'], entry['inputs'])
                self.assertFalse(result['order_authority'])
        self.assertEqual(hashlib.sha256(self.fixture.database.read_bytes()).hexdigest(), before)
        self.assertFalse(self.settings.execution_database.exists())
        self.assertFalse(self.settings.market_database.exists())

    def test_independent_exact_fibonacci_line_zone_channel_and_ruler_references(self):
        specs = [
            ('horizontal','priceAt',dict(time=self.time)),
            ('trend','priceAt',dict(time=self.time)),
            ('ray','distance',dict(time=self.time,query_price='125')),
            ('zone-legacy','contains',dict(time=self.time,query_price='125')),
            ('zone-v1','distance',dict(time=self.time,query_price='140')),
            ('fib-legacy','level',dict(time=self.time,ratio='0.5')),
            ('fib-v1','level',dict(time=self.time,ratio='0.618')),
            ('fib-extension','level',dict(time=self.time,ratio='1.618')),
            ('parallel-legacy','boundsAt',dict(time=self.time)),
            ('ruler','measurement',{})]
        response = self.batch([self.entry(*s) for s in specs])
        self.assertEqual(response.status_code, 200, response.text)
        results = response.json()['results']
        self.assertTrue(all(r['state']=='READY' for r in results), results)
        values = [r['result']['value'] for r in results]
        for index, expected in [(0,'110.25'),(1,'120.5'),(2,'4.5'),(4,'9.25'),(5,'120.5'),(6,'122.919'),(7,'143.419')]:
            self.assertEqual(self.fraction(values[index]), Fraction(expected))
        self.assertIs(values[3], True)
        self.assertEqual(self.fraction(values[8]['lower']), Fraction('120.5'))
        self.assertEqual(self.fraction(values[8]['upper']), Fraction(1943,14))
        self.assertEqual(self.fraction(values[8]['width']), Fraction(128,7))
        self.assertIsNone(values[8]['upper']['decimal'])
        self.assertEqual(self.fraction(values[9]['price_change']), Fraction('20.5'))
        self.assertEqual(self.fraction(values[9]['tick_change']), 82)
        self.assertEqual(values[9]['duration_seconds'], 12600)
        self.assertEqual(values[9]['bars']['count'], 15)
        intermediate = self.single(self.entry('trend','priceAt',dict(time=self.time+225))).json()['results'][0]
        self.assertEqual(self.fraction(intermediate['result']['value']), Fraction(13537,112))
        self.assertEqual(intermediate['undefined_outputs'], [])

    def test_independent_costed_risk_reward_and_explicit_undefined_outputs(self):
        for kind, risk, reward, fill in [('long_plan','10.57002','19.34004','100.2'),('short_plan','10.63002','19.46004','99.8')]:
            item = self.fixture.drawings.create('main', kind+'-costed', plan(kind, True))
            entry = dict(query_id=kind, drawing_id=item['drawing_id'], expected_revision=1, operation='riskReward', inputs={})
            result = self.single(entry).json()['results'][0]
            values = result['result']['value']
            self.assertEqual(self.fraction(values['net_risk']), Fraction(risk))
            self.assertEqual(self.fraction(values['net_reward']), Fraction(reward))
            self.assertEqual(self.fraction(values['entry_fill']), Fraction(fill))
            self.assertEqual(self.fraction(values['quantity'])*Fraction(risk), 100)
        geometry = plan()
        geometry['params']['risk_budget'] = None
        item = self.fixture.drawings.create('main', 'optional-budget', geometry)
        entry.update(drawing_id=item['drawing_id'], expected_revision=1)
        result = self.single(entry).json()['results'][0]
        self.assertIn('quantity', result['undefined_outputs'])

    def test_mixed_batch_reports_unsupported_and_revision_errors_without_losing_successes(self):
        entries = [self.entry('horizontal','priceAt',dict(time=self.time)),
                   self.entry('family-parallel_channel','boundsAt',dict(time=self.time)),
                   self.entry('note','measurement'),
                   self.entry('trend','priceAt',dict(time=self.time),expected_revision=2)]
        response = self.batch(entries)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r['state'] for r in response.json()['results']], ['READY','READY','UNSUPPORTED_OPERATION','REVISION_CONFLICT'])
        for entry, result in zip(entries[1:], response.json()['results'][1:]):
            single = self.single(entry)
            self.assertEqual(single.status_code, result['http_status'])
            self.assertEqual(single.json()['results'][0], result)

    def test_missing_foreign_other_workspace_deleted_and_wrong_symbol_do_not_leak(self):
        foreign = DrawingService(self.fixture.database,'foreign').create('main','foreign', drawing_cases()[0]['geometry'])
        elsewhere = self.fixture.drawings.create('elsewhere','elsewhere',drawing_cases()[0]['geometry'])
        deleted = self.items['horizontal']
        self.fixture.drawings.update(deleted['drawing_id'],'delete',1,deleted=True)
        entries = [dict(query_id=str(i),drawing_id=key,expected_revision=1,operation='priceAt',inputs=dict(time=self.time)) for i,key in enumerate([foreign['drawing_id'],elsewhere['drawing_id'],deleted['drawing_id'],'missing'])]
        results = self.batch(entries).json()['results']
        self.assertTrue(all(r['state']=='NOT_FOUND' and r['error']['code']=='DRAWING_NOT_FOUND' for r in results))
        self.assertEqual(self.single(entries[0]).status_code,404)
        eth = self.fixture.drawings.create('main','eth',{**drawing_cases()[0]['geometry'],'symbol':'ETHUSDT'})
        entries[0].update(drawing_id=eth['drawing_id'])
        self.assertEqual(self.single(entries[0]).json()['results'][0]['state'],'SOURCE_MISMATCH')

    def test_missing_stale_gap_and_open_candle_policy_cannot_be_spoofed(self):
        entry = self.entry('extended_line','priceAt',dict(time=self.fixture.rows[-1]['time']))
        self.assertEqual(self.single(entry).json()['results'][0]['state'],'WAITING_FOR_DATA')
        self.assertEqual(self.single(entry,{**self.context,'include_open':True}).status_code,200)
        self.fixture.now[0] += 11; self.fixture.mono[0] += 11
        entry['inputs']['time'] = self.time
        self.assertEqual(self.single(entry).json()['results'][0]['state'],'STALE')
        # Pure geometry stays usable, explicitly without consuming stale market data.
        horizontal = self.entry('horizontal','priceAt',dict(time=self.time))
        result = self.single(horizontal).json()['results'][0]
        self.assertEqual(result['state'],'READY'); self.assertFalse(result['data_consumed'])
        self.fixture.hub.feeds.clear()
        self.assertEqual(self.single(entry).json()['results'][0]['state'],'WAITING_FOR_DATA')
        self.assertEqual(self.single(horizontal).status_code,200)
        entry['inputs']['times'] = [self.time]
        self.assertEqual(self.single(entry).json()['results'][0]['error']['code'],'INVALID_QUERY_INPUTS')

    def test_input_limits_decimal_units_unknown_operations_and_body_validation(self):
        base = self.entry('trend','priceAt',dict(time=self.time))
        for entry, code in [({**base,'inputs':dict(time=self.time*1000)},'INVALID_UTC_SECONDS'),
                            ({**base,'inputs':dict(time=float(self.time))},'INVALID_UTC_SECONDS'),
                            ({**base,'scale':'LOG'},'UNSUPPORTED_SCALE'),
                            ({**base,'operation':'bad'},'UNSUPPORTED_QUERY'),
                            ({**base,'operation':'distance','inputs':dict(time=self.time,query_price=125)},'DECIMAL_TEXT_REQUIRED')]:
            result = self.single(entry)
            self.assertEqual(result.status_code,422,result.text)
            self.assertEqual(result.json()['results'][0]['error']['code'],code)
        for entries in [[],[base]*51,[base,base]]:
            self.assertEqual(self.batch(entries).status_code,422)
        self.assertEqual(self.batch([base],{**self.context,'times':[self.time]}).status_code,422)
        self.assertEqual(self.batch([base],{**self.context,'source':'foreign'}).status_code,422)
        path='/api/workspaces/main/chart-queries'
        self.assertEqual(self.client.post(path,content='{"schema_version":1,"schema_version":2}',headers={'Content-Type':'application/json'}).status_code,422)
        self.assertEqual(self.client.post(path,content='x'*65537,headers={'Content-Type':'application/json'}).status_code,422)
        self.assertEqual(self.client.post(path,json={},headers={'Origin':'http://foreign.invalid'}).status_code,403)

    def test_context_revisions_and_races_reject_whole_response(self):
        entry = self.entry('trend','priceAt',dict(time=self.time))
        context_id = self.client.get('/api/workspaces/main/chart-context',params=self.context).json()['context_id']
        self.assertEqual(self.single(entry,{**self.context,'expected_context_id':context_id}).status_code,200)
        service = self.app.state.chart_queries
        original = service._evaluate
        def racing(*args):
            result=original(*args)
            item=self.items['trend']
            self.fixture.drawings.update(item['drawing_id'],'race',1,{**item['geometry'],'label':'changed'})
            return result
        with patch.object(service,'_evaluate',side_effect=racing):
            response = self.single(entry)
        self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(response.json()['error']['code'],'CONTEXT_CHANGED')
        self.assertEqual(self.single(entry,{**self.context,'expected_context_id':context_id}).status_code,409)

    def test_data_warmup_gap_corruption_and_source_mismatch_block_data_calculations(self):
        entry = self.entry('trend','priceAt',dict(time=self.time))
        self.assertEqual(self.single(entry,{**self.context,'required_closed_bars':499}).json()['results'][0]['state'],'WARMUP')
        state = self.fixture.state
        state.rows.pop(285)
        state.quality = dict(state='GAP',missing_bars=1)
        state._capture_evidence()
        self.assertEqual(self.single(entry).json()['results'][0]['state'],'WAITING_FOR_DATA')
        state.rows[-1]['close'] += .1
        self.assertEqual(self.single(entry).json()['results'][0]['error']['code'],'DATA_PROOF_MISMATCH')
        context = self.app.state.chart_context
        original = context._data
        def wrong(*args):
            data=original(*args)
            data['identity']['price_type']='MARK_PRICE'
            return data
        with patch.object(context,'_data',side_effect=wrong):
            self.assertEqual(self.single(entry).json()['results'][0]['state'],'SOURCE_MISMATCH')

    def test_output_deadline_and_parallel_calls_keep_per_request_state(self):
        from concurrent.futures import ThreadPoolExecutor
        service = self.app.state.chart_queries
        entry = self.entry('horizontal','priceAt',dict(time=self.time))
        with patch('agentrader.chart.chart_queries.MAX_OUTPUT_BYTES',100):
            response = self.single(entry)
            self.assertEqual(response.status_code,413)
            self.assertEqual(response.json()['error']['code'],'CHART_QUERY_OUTPUT_LIMIT')
        with patch.object(service.context,'monotonic',side_effect=[0,3]):
            response = self.single(entry)
            self.assertEqual(response.status_code,503)
            self.assertEqual(response.json()['error']['code'],'CONTEXT_READ_TIME_LIMIT')
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(service.run,'main',REQUEST_SCHEMA,self.context,[entry]) for _ in range(2)]
            results = [future.result() for future in futures]
        self.assertEqual(results[0]['context_id'],results[1]['context_id'])
        self.assertEqual(results[0]['results'],results[1]['results'])
