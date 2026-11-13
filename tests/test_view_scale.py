import copy
from pathlib import Path
import tempfile
import unittest
from agentrader.drawings.calculations import query, canonical_hash, CalculationBlocked
from agentrader.drawings.contracts import capability, registry
from agentrader.drawings.service import DrawingService
from agentrader.migrations import migrate


class ViewScaleTests(unittest.TestCase):
    def fib(self):
        return dict(kind='fibonacci',schema='chart-fibonacci/1',symbol='BTCUSDT',price_source='LAST_PRICE',label='fib',anchors=[dict(time=1800000000,price='100'),dict(time=1800009000,price='400')],levels=['0','0.5','1','1.618'],time_scope='unbounded')

    def test_policy_explicitly_blocks_straight_slopes_but_keeps_price_levels(self):
        for kind in ['trend','ray','extended_line','parallel_channel']:
            policy=capability('drawing',kind)['scale_policy']
            self.assertEqual(policy['LOG'],'BLOCKED_STRAIGHT_SLOPE')
            self.assertEqual(policy['geometry_scale'],'LINEAR')
            self.assertFalse(policy['view_change_mutates_geometry'])
        for kind in ['horizontal','zone','fibonacci','fibonacci_extension','ruler']:
            self.assertEqual(capability('drawing',kind)['scale_policy']['LOG'],'PRICE_LEVELS_OR_ENDPOINT_MEASUREMENT')
        self.assertEqual(capability('drawing','fibonacci_projection')['scale_policy']['LOG'],'NOT_IMPLEMENTED')

    def test_log_geometry_calculation_is_blocked_instead_of_silently_using_linear(self):
        with self.assertRaises(CalculationBlocked) as error:
            query(self.fib(),'level',ratio='0.5',time=1800004500,scale='LOG')
        self.assertEqual(error.exception.code,'UNSUPPORTED_SCALE')
        with self.assertRaises(CalculationBlocked):canonical_hash(self.fib(),scale='LOG')
        # The native view does not enter the pure calculation API.
        self.assertEqual(query(self.fib(),'level',ratio='0.5',time=1800004500)['value']['decimal'],'250')

    def test_price_anchor_hash_revision_and_restart_have_no_view_scale_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'app.db';migrate(db);s=DrawingService(db,'owner');created=s.create('main','new',self.fib());before={k:copy.deepcopy(v) for k,v in created.items() if k!='duplicate'};digest=canonical_hash(created['geometry'])
            for _ in range(3):
                policy=capability('drawing','fibonacci')['scale_policy'];self.assertEqual(policy['schema'],'chart-scale-policy/1')
                self.assertEqual(s.show(created['drawing_id']),before)
            restored=DrawingService(db,'owner').show(created['drawing_id'])
            self.assertEqual(restored,before);self.assertEqual(canonical_hash(restored['geometry']),digest)

    def test_registry_view_support_never_adds_order_or_tracking_authority(self):
        for tool in registry()['tools']:
            self.assertEqual(tool['scale_policy']['log_geometry_query'],'BLOCKED_UNSUPPORTED_SCALE')
            self.assertFalse(tool['tracking_activation']);self.assertFalse(tool['order_authority'])
