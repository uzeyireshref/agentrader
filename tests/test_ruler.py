import copy
import importlib.util
from decimal import localcontext
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agentrader.drawings.calculations import measure_ruler, query, CalculationBlocked
from agentrader.drawings.service import DrawingService, DrawingError, DrawingConflict, geometry
from agentrader.drawings.contracts import legacy_contract, capability
from agentrader.migrations import migrate
from agentrader.application.settings import WebSettings

FIXTURE=Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/ruler-parity.json'


class RulerTests(unittest.TestCase):
    def setUp(self):self.cases=json.loads(FIXTURE.read_text())['cases']

    def test_fixed_independent_references_match_even_at_low_decimal_precision(self):
        for case in self.cases:
            with self.subTest(name=case['name']),localcontext() as context:
                context.prec=3
                before=copy.deepcopy(case)
                actual=measure_ruler(case['geometry'],tick_size=case['tick_size'],times=case['times'],interval=case['interval'])
                self.assertEqual(actual,case['expected'])
                self.assertEqual(query(case['geometry'],'measurement',tick_size=case['tick_size'],times=case['times'],interval=case['interval'])['value'],actual)
                self.assertEqual(case,before)

    def test_ruler_schema_does_not_change_legacy_validation_or_allow_unknown_versions(self):
        ruler=self.cases[0]['geometry']
        for change in ({'schema':'chart-ruler/2'},{'kind':'trend'},{'unknown':True}):
            with self.assertRaises(DrawingError):geometry(ruler|change)
        missing=copy.deepcopy(ruler);missing.pop('schema')
        with self.assertRaises(DrawingError):geometry(missing)
        expanded=copy.deepcopy(ruler);expanded['anchors'][0]['price']='1e-8'
        self.assertEqual(geometry(expanded)['anchors'][0]['price'],'0.00000001')
        for invalid in (' 100 ', '1e31', '1.'+'0'*64):
            bad=copy.deepcopy(ruler);bad['anchors'][0]['price']=invalid
            with self.assertRaises(DrawingError):geometry(bad)
        for name in ('flat','vertical','point'):self.assertEqual(geometry(next(c['geometry'] for c in self.cases if c['name']==name))['kind'],'ruler')

    def test_bad_grid_tick_and_zero_start_price_fail_explicitly(self):
        c=self.cases[0]
        for tick in ('0','-1','NaN',.25):
            with self.assertRaises(CalculationBlocked):measure_ruler(c['geometry'],tick_size=tick,times=c['times'],interval='15m')
        for times in ([],[True,1800000900],[1800000900,1800000000],[1800000000,1800000000],[1800000001,1800000901]):
            with self.assertRaises(CalculationBlocked):measure_ruler(c['geometry'],tick_size='0.25',times=times,interval='15m')
        bad=copy.deepcopy(c['geometry']);bad['anchors'][0]['price']='0'
        with self.assertRaises(CalculationBlocked):measure_ruler(bad,tick_size='0.25',interval='15m')
        with self.assertRaises(CalculationBlocked):query(c['geometry'],'measurement',tick_size='0.25',interval='15m',scale='LOG')

    def test_timeframe_context_changes_only_bar_counts_and_not_anchor_prices(self):
        c=copy.deepcopy(self.cases[0]);c['geometry']['anchors'][1]['time']=1800003600
        a=measure_ruler(c['geometry'],tick_size='0.25',times=[1800000000+i*900 for i in range(5)],interval='15m')
        b=measure_ruler(c['geometry'],tick_size='0.25',times=[1800000000,1800003600],interval='1h')
        self.assertEqual((a['price_change'],a['elapsed_seconds']),(b['price_change'],b['elapsed_seconds']))
        self.assertEqual((a['bars']['count'],b['bars']['count']),(5,2))

    def test_persistence_conflict_undo_restart_and_contract_keep_exact_ruler(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'app.db';migrate(path);service=DrawingService(path,'owner')
            c=self.cases[9]['geometry'];saved=service.create('main','create',c)
            changed=copy.deepcopy(c);changed['anchors'][1]['price']='9007199254740994.00'
            updated=service.update(saved['drawing_id'],'update',1,changed)
            with self.assertRaises(DrawingConflict):service.update(saved['drawing_id'],'stale',1,c)
            deleted=service.update(saved['drawing_id'],'delete',2,deleted=True)
            restored=service.update(saved['drawing_id'],'restore',3,c)
            restarted=DrawingService(path,'owner').show(saved['drawing_id'])
            self.assertEqual(restarted['geometry'],c)
            self.assertEqual(restarted['revision'],4)
            self.assertTrue(deleted['deleted']);self.assertFalse(restored['deleted'])
            self.assertEqual(legacy_contract(restarted)['origin'],'CHART_RULER_V1')
            self.assertEqual(capability('drawing','ruler')['definition']['write_schema'],'chart-ruler/1')

    @unittest.skipUnless(all(importlib.util.find_spec(m) for m in ('fastapi','httpx')), 'Optional web dependencies')
    def test_real_api_format_v2_isolated_from_old_clients_and_never_calls_exchange(self):
        from agentrader.api.app import create_app
        from fastapi.testclient import TestClient
        with tempfile.TemporaryDirectory() as folder:
            settings=WebSettings(Path(folder)/'app.db',Path(folder)/'execution.db',market_database=Path(folder)/'market.db')
            with TestClient(create_app(settings),base_url='http://127.0.0.1') as client,patch('agentrader.exchange.DemoExchange.request',side_effect=AssertionError('exchange access')):
                data={'request_id':'ruler-create','geometry':self.cases[0]['geometry']}
                response=client.post('/api/workspaces/main/drawings',json=data);self.assertEqual(response.status_code,201)
                saved=response.json();path='/api/drawings/'+saved['drawing_id']
                self.assertTrue(client.post('/api/workspaces/main/drawings',json=data).json()['duplicate'])
                self.assertEqual(client.get('/api/workspaces/main/drawings').json()['drawings'],[])
                self.assertEqual(len(client.get('/api/workspaces/main/drawings?format_version=2').json()['drawings']),1)
                self.assertEqual(client.get(path).json()['error']['code'],'DRAWING_FORMAT_VERSION_REQUIRED')
                self.assertEqual(client.get(path+'?format_version=2').status_code,200)
                delete={'request_id':'delete','expected_revision':1}
                self.assertEqual(client.request('DELETE',path,json=delete).status_code,422)
                self.assertEqual(client.request('DELETE',path+'?format_version=2',json=delete).status_code,200)
                undo={'request_id':'undo','expected_revision':2,'geometry':saved['geometry']}
                self.assertEqual(client.patch(path+'?format_version=2',json=undo).json()['revision'],3)
                self.assertEqual(client.get('/api/workspaces/main/drawings?format_version=3').status_code,200)
                self.assertEqual(client.get('/api/workspaces/main/drawings?format_version=4').status_code,200)
                self.assertEqual(client.get('/api/workspaces/main/drawings?format_version=5').status_code,200)
                self.assertEqual(client.get('/api/workspaces/main/drawings?format_version=6').status_code,200)
                self.assertEqual(client.get('/api/workspaces/main/drawings?format_version=7').status_code,200)
                self.assertEqual(client.get('/api/workspaces/main/drawings?format_version=8').status_code,200)
                self.assertEqual(client.get('/api/workspaces/main/drawings?format_version=9').status_code,200)
                self.assertEqual(client.get('/api/workspaces/main/drawings?format_version=10').status_code,422)
                self.assertEqual(client.get('/api/workspaces/main/drawings?symbol=ETHUSDT&format_version=2').json()['drawings'],[])
            self.assertFalse(settings.execution_database.exists())
