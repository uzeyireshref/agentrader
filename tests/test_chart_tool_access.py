"""Discovery must describe handlers that actually accept the advertised records."""
import tempfile
import unittest
import importlib.util
from pathlib import Path

from agentrader.application.settings import WebSettings
from agentrader.chart.drawings.calculations import query, CalculationBlocked
from agentrader.chart.drawings.contracts import capability, registry
from scripts.integration.chart_tool_matrix_cases import drawing_cases, candles

HAS_WEB = all(importlib.util.find_spec(module) is not None for module in ('fastapi', 'httpx'))
if HAS_WEB:
    from fastapi.testclient import TestClient
    from agentrader.api.app import create_app

@unittest.skipUnless(HAS_WEB, 'Optional web dependencies not installed')
class ChartToolAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        self.settings = WebSettings(folder/'app.db', folder/'execution.db', '', 'local:access',
                                    market_database=folder/'market.db')
        self.app = create_app(self.settings)
        self.client = self.enterContext(TestClient(self.app, base_url='http://127.0.0.1'))

    def test_all_25_record_variants_discover_and_use_real_crud_and_python_handlers(self):
        times = [c['time'] for c in candles()]
        for index, case in enumerate(drawing_cases()):
            with self.subTest(case=case['case_id']):
                geometry = case['geometry']
                category = 'annotation' if geometry['kind'] in ('text', 'note', 'price_label') else 'plan' if geometry['kind'] in ('long_plan', 'short_plan') else 'drawing'
                schema = geometry.get('schema', 'LEGACY_GEOMETRY_V1')
                response = self.client.get(f"/api/chart-tools/{category}/{geometry['kind']}", params={'record_schema': schema})
                self.assertEqual(response.status_code, 200)
                tool = response.json()
                self.assertEqual(tool['record_schema'], schema)
                self.assertEqual(tool['features']['geometry_query'], tool['python_geometry']['implemented'])
                self.assertEqual([s['operation'] for s in tool['http_geometry_operations']],
                                 [s['operation'] for s in tool['python_geometry']['operations']])
                params = {'format_version': tool['format_version']}
                created = self.client.post(tool['access']['create']['path'].format(workspace_id='main'), params=params,
                                           json=dict(request_id=f'create-{index}', geometry=geometry))
                self.assertEqual(created.status_code, 201, created.text)
                item = created.json()
                path = tool['access']['metadata_read']['path'].format(drawing_id=item['drawing_id'])
                self.assertEqual(self.client.get(path, params=params).json()['geometry'], item['geometry'])
                contract = self.client.get(path+'/contract').json()
                self.assertEqual(contract['capabilities']['record_schema'], schema)
                for field in tool['text_fields']:
                    self.assertIn(field, item['geometry'])
                operations = tool['python_geometry']['operations']
                if operations:
                    for spec in operations:
                        active = {**geometry, 'options': {**geometry['options'], 'extend': 'both'}} if schema == 'chart-channel-family/1' else geometry
                        result = query(active, spec['operation'], time=times[290], query_price='120',
                                       ratio='0.5' if schema == 'chart-channel-family/1' else '0.618', times=times, rows=candles(), interval='15m', tick_size='0.25')
                        self.assertEqual(result['operation'], spec['operation'])
                        self.assertFalse(result['order_authority'])
                        if schema != 'chart-channel-family/1':
                            with self.assertRaises(CalculationBlocked):
                                query(geometry, spec['operation'], scale='LOG')
                else:
                    with self.assertRaises(CalculationBlocked):
                        query(geometry, 'priceAt', time=times[290])
                changed = {**item['geometry'], 'label': 'updated'}
                updated = self.client.patch(path, params=params, json=dict(request_id=f'edit-{index}', expected_revision=1, geometry=changed))
                self.assertEqual(updated.status_code, 200, updated.text)
                deleted = self.client.request('DELETE', path, params=params, json=dict(request_id=f'delete-{index}', expected_revision=2))
                self.assertEqual(deleted.status_code, 200)
                self.assertTrue(deleted.json()['deleted'])
        self.assertFalse(self.settings.execution_database.exists())

    def test_every_advertised_http_surface_has_registered_method_and_version(self):
        routes = {(path, method.upper()) for path, operations in self.app.openapi()['paths'].items()
                  for method in operations}
        result = self.client.get('/api/chart-tools').json()
        self.assertEqual(result['access_schema'], 'chart-tool-access/1')
        for tool in result['tools']:
            for variant in tool['record_variants']:
                for name, feature in variant['access'].items():
                    self.assertEqual(variant['features'][name], feature['implemented'])
                    if feature['implemented']:
                        self.assertIn((feature['path'], feature['method']), routes)
                self.assertEqual(variant['features']['indicator_series'], tool['category']=='indicator')
                self.assertTrue(variant['features']['ui_state_read'])
        projection = capability('drawing', 'fibonacci_projection')
        self.assertEqual(projection['implementation_state'], 'IMPLEMENTED')
        self.assertTrue(projection['features']['geometry_query']);self.assertEqual(projection['format_version'],10)

    def test_indicator_configuration_and_series_access_are_separate_from_fixed_slot_crud(self):
        for kind in ('sma', 'ema', 'rsi', 'atr', 'macd', 'bb', 'session_vwap', 'anchored_vwap'):
            tool = capability('indicator', kind)
            self.assertTrue(tool['features']['metadata_read'])
            self.assertTrue(tool['features']['edit'])
            self.assertFalse(tool['features']['create'])
            self.assertFalse(tool['features']['delete'])
            self.assertTrue(tool['features']['indicator_series'])
        path = tool['access']['metadata_read']['path'].format(workspace_id='main')
        value = self.client.get(path, params={'format_version': 4}).json()
        response = self.client.put(path, params={'format_version': 4}, json=dict(request_id='indicator-edit', expected_revision=value['revision'], indicators=value['indicators']))
        self.assertEqual(response.status_code, 200)

    def test_parallel_schema_selection_and_unknown_schema_do_not_inherit_capabilities(self):
        old = capability('drawing', 'parallel_channel', record_schema='chart-channel/1')
        new = capability('drawing', 'parallel_channel', record_schema='chart-channel-family/1')
        self.assertTrue(old['python_geometry']['implemented'])
        self.assertTrue(new['python_geometry']['implemented'])
        self.assertEqual(new['text_fields'], ['label', 'text'])
        self.assertEqual(len(new['record_variants']), 1)
        for kind, schema in [('parallel_channel', 'bad'), ('horizontal', 'chart-channel-family/1')]:
            self.assertEqual(self.client.get(f'/api/chart-tools/drawing/{kind}', params={'record_schema': schema}).status_code, 422)
        result = registry()
        result['tools'][0]['record_variants'][0]['features']['create'] = False
        self.assertTrue(registry()['tools'][0]['features']['create'])
