import copy
from decimal import Decimal, localcontext
from fractions import Fraction
import json
from pathlib import Path
import unittest

from agentrader.drawings.calculations import (query, logical_position, encoded, canonical_hash,
                                             CalculationBlocked, verified_grid)

REFERENCE = Path(__file__).resolve().parents[1] / 'frontend/tests/fixtures/geometry-parity.json'


class GeometryCalculationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(REFERENCE.read_text())
        self.times = self.fixture['grid']
        self.trend = copy.deepcopy(self.fixture['cases'][1]['geometry'])

    def test_independent_fixed_references_and_no_input_mutation(self):
        for case in self.fixture['cases']:
            with self.subTest(name=case['name']):
                original = copy.deepcopy(case)
                options = {k: case[k] for k in ('time', 'query_price', 'ratio') if k in case}
                with localcontext() as context:
                    context.prec = 3
                    result = query(case['geometry'], case['operation'], times=self.times, interval='15m', **options)
                self.assertEqual(result['value'], case['expected'])
                self.assertFalse(result['live_eligible'])
                self.assertFalse(result['order_authority'])
                self.assertEqual(case, original)

    def test_reference_decimal_matrix_covers_signed_and_repeating_results(self):
        for numerator in (-1001, -10, -1, 0, 1, 10, 1001):
            for denominator in (1, 2, 4, 5, 8, 10, 25, 125, 1000, 3, 7):
                fraction = Fraction(numerator, denominator)
                result = encoded(fraction)
                self.assertEqual(Fraction(int(result['numerator']), int(result['denominator'])), fraction)
                if denominator not in (3, 7) or numerator == 0:
                    with localcontext() as context:
                        context.prec = 60
                        self.assertEqual(Decimal(result['decimal']), Decimal(numerator) / Decimal(denominator))
                elif fraction.denominator not in (1,):
                    self.assertIsNone(result['decimal'])

    def test_gapped_display_mapping_is_explicit_but_canonical_queries_block(self):
        grid = [self.times[0], self.times[1], self.times[0] + 3600]
        self.assertEqual(logical_position(grid, self.times[0] + 2250), Fraction(3, 2))
        with self.assertRaisesRegex(CalculationBlocked, 'GRID_GAP'):
            query(self.trend, 'priceAt', time=self.times[1], times=grid, interval='15m')

    def test_grid_rejects_bad_order_duplicates_units_missing_or_short_history(self):
        for grid in (None, [], self.times[:1], self.times[::-1], [self.times[0]] * 2,
                     [t * 1000 for t in self.times], [True, self.times[1]]):
            with self.subTest(grid=grid), self.assertRaises(CalculationBlocked):
                query(self.trend, 'priceAt', time=self.times[1], times=grid, interval='15m')
        with self.assertRaisesRegex(CalculationBlocked, 'GRID_BUCKET_MISMATCH'):
            verified_grid([t + 1 for t in self.times], '15m')
        with self.assertRaisesRegex(CalculationBlocked, 'UNSUPPORTED_INTERVAL'):
            verified_grid(self.times, '3m')

    def test_weekly_grid_uses_monday_utc(self):
        monday = 1794182400  # 2026-11-09 00:00:00 UTC
        self.assertEqual(verified_grid([monday, monday + 604800], '1w'), (monday, monday + 604800))
        with self.assertRaisesRegex(CalculationBlocked, 'GRID_BUCKET_MISMATCH'):
            verified_grid([monday + 86400, monday + 691200], '1w')

    def test_outside_scope_and_grid_never_extrapolate(self):
        for time in (self.times[0] - 1, self.times[-1] + 1):
            with self.assertRaisesRegex(CalculationBlocked, 'OUT_OF_SCOPE'):
                query(self.trend, 'priceAt', time=time, times=self.times, interval='15m')
        with self.assertRaisesRegex(CalculationBlocked, 'GRID_OUT_OF_RANGE'):
            query(self.trend, 'priceAt', time=self.times[1], times=self.times[1:], interval='15m')

    def test_invalid_inputs_unsupported_queries_and_scale_fail_closed(self):
        for options in ({'time': self.times[0] * 1000}, {'time': True}, {'time': 0},
                        {'time': self.times[0], 'scale': 'LOG'}):
            with self.assertRaises(CalculationBlocked):
                query(self.trend, 'priceAt', times=self.times, interval='15m', **options)
        with self.assertRaisesRegex(CalculationBlocked, 'UNSUPPORTED_QUERY'):
            query(self.trend, 'level', time=self.times[0])
        for price in (100.0, True, 'NaN', '-1', '0'):
            with self.assertRaises(CalculationBlocked):
                query(self.trend, 'distance', time=self.times[1], query_price=price, times=self.times, interval='15m')
        fib = copy.deepcopy(self.trend); fib['kind'] = 'fibonacci'
        with self.assertRaisesRegex(CalculationBlocked, 'UNSUPPORTED_RATIO'):
            query(fib, 'level', time=self.times[0], ratio='1.618')

    def test_canonical_hash_is_stable_semantic_and_context_bound(self):
        digest = canonical_hash(self.trend, times=self.times, interval='15m')
        changed = copy.deepcopy(self.trend)
        changed['label'] = 'renamed'
        changed['anchors'][0]['price'] = '100.000'
        self.assertEqual(canonical_hash(changed, times=self.times, interval='15m'), digest)
        changed['anchors'][0]['price'] = '100.000000000000000000001'
        self.assertNotEqual(canonical_hash(changed, times=self.times, interval='15m'), digest)
        self.assertNotEqual(canonical_hash(self.trend, times=self.times + [self.times[-1] + 900], interval='15m'), digest)
        with self.assertRaisesRegex(CalculationBlocked, 'UNSUPPORTED_SCALE'):
            canonical_hash(self.trend, times=self.times, interval='15m', scale='LOG')

    def test_hash_rejects_invalid_optional_context_for_any_kind(self):
        line = copy.deepcopy(self.fixture['cases'][0]['geometry'])
        for options in ({'times': [True, False], 'interval': '15m'},
                        {'times': self.times, 'interval': None}, {'interval': []}):
            with self.assertRaises(CalculationBlocked):
                canonical_hash(line, **options)
