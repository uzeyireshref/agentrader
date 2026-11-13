import copy
import unittest

from agentrader.drawings.contracts import capability, legacy_contract, registry, UnsupportedTool
from pathlib import Path
import tempfile
from agentrader.drawings.service import DrawingService
from agentrader.migrations import migrate
from test_drawings import line, zone


class ToolRegistryTests(unittest.TestCase):
    def test_only_existing_tools_offer_offline_queries_without_authority(self):
        entries = registry()['tools']
        self.assertEqual(len(entries), 34)
        self.assertEqual(len({(t['category'], t['kind']) for t in entries}), len(entries))
        for tool in entries:
            if tool['category'] == 'annotation' or tool['definition']['write_schema'] == 'chart-channel-family/1':
                self.assertTrue(tool['readable']); self.assertTrue(tool['editable']); self.assertFalse(tool['computable'])
                self.assertEqual(tool['canonical_queries'], []); self.assertEqual(tool['calculation_state'], 'DISPLAY_ONLY')
            elif tool['readable']:
                self.assertTrue(tool['computable'])
                self.assertTrue(tool['canonical_queries'])
                self.assertEqual(tool['calculation_state'], 'PURE_OFFLINE_REQUIRES_CONTEXT')
            else:
                self.assertEqual(tool['canonical_queries'], [])
                self.assertFalse(tool['computable'])
            self.assertFalse(tool['tracking_activation'])
            self.assertFalse(tool['order_authority'])
        for kind in ('horizontal', 'zone', 'trend', 'fibonacci'):
            self.assertTrue(capability('drawing', kind)['editable'])
        self.assertTrue(capability('plan', 'long_plan')['readable'])
        self.assertTrue(capability('plan', 'short_plan')['readable'])

    def test_unknown_category_kind_and_version_are_blocked(self):
        for args in [('drawing', 'unknown'), ('rule', 'horizontal'),
                     ('drawing', 'horizontal', 2), ('drawing', 'horizontal', True)]:
            with self.assertRaises(UnsupportedTool):
                capability(*args)

    def test_registry_result_cannot_mutate_future_capabilities(self):
        result = registry()
        result['tools'][0]['order_authority'] = True
        self.assertFalse(registry()['tools'][0]['order_authority'])


class LegacyContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "app.db"
        migrate(self.path)
        self.service = DrawingService(self.path, "owner")

    def test_projection_preserves_revision_geometry_and_restart(self):
        for kind in ('horizontal', 'zone', 'trend', 'fibonacci'):
            value = line() if kind == 'horizontal' else dict(zone(), kind=kind)
            saved = self.service.create('main', 'contract-' + kind, value)
            original = copy.deepcopy(saved)
            contract = legacy_contract(saved)
            self.assertEqual(saved, original)
            self.assertEqual(contract['revision'], 1)
            self.assertEqual(contract['anchors'], saved['geometry']['anchors'])
            self.assertIsNone(contract['market']['interval'])
            self.assertEqual(contract['evaluation']['state'], 'BLOCKED')
            contract['anchors'][0]['price'] = '1'
            restarted = DrawingService(self.path, 'owner')
            self.assertEqual(restarted.show(saved['drawing_id'])['geometry'], original['geometry'])
            deleted = self.service.update(saved['drawing_id'], 'delete-' + kind, 1, deleted=True)
            self.assertTrue(legacy_contract(deleted)['deleted'])

    def test_future_tool_cannot_be_projected_as_legacy(self):
        saved = self.service.create('main', 'line', line())
        saved['geometry']['kind'] = 'ray'
        with self.assertRaises(UnsupportedTool):
            legacy_contract(saved)

    def test_declared_shapes_and_scope_preserve_legacy_meaning(self):
        for kind in ('horizontal', 'zone', 'trend', 'fibonacci'):
            saved = self.service.create('main', 'scope-' + kind,
                                        line() if kind == 'horizontal' else dict(zone(), kind=kind))
            contract = legacy_contract(saved)
            scope = contract['time_scope']
            if kind == 'horizontal':
                self.assertEqual(scope, {'mode': 'UNBOUNDED', 'unit': 'UTC_SECONDS', 'start': None, 'end': None})
            else:
                times = [a['time'] for a in saved['geometry']['anchors']]
                self.assertEqual((scope['start'], scope['end']), (min(times), max(times)))
            self.assertEqual(contract['capabilities']['definition']['anchor_count'], len(saved['geometry']['anchors']))
            if kind == 'fibonacci':
                self.assertEqual(contract['params']['ratios'], ['0', '0.236', '0.382', '0.5', '0.618', '0.786', '1'])
