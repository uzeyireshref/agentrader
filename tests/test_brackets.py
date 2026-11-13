import copy
import unittest
from agentrader.brackets import select_bracket


class BracketTests(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(notionalFloor=0,notionalCap=100,initialLeverage=50,maintMarginRatio='.004',cum=0),
                   dict(notionalFloor=100,notionalCap=1000,initialLeverage=20,maintMarginRatio='.01',cum='.6')]

    def test_exact_boundary_uses_next_tier_and_enforces_lower_leverage(self):
        self.assertEqual(select_bracket(self.rows,'99.99',50)['initialLeverage'],50)
        self.assertEqual(select_bracket(self.rows,'100',20)['initialLeverage'],20)
        with self.assertRaises(ValueError):select_bracket(self.rows,'100',50)

    def test_gaps_overlap_nan_and_nonmonotonic_ladders_are_rejected(self):
        for change in ({'notionalFloor':101},{'notionalFloor':99},{'maintMarginRatio':'NaN'},
                       {'initialLeverage':60},{'maintMarginRatio':'.001'},{'cum':-1}):
            rows=copy.deepcopy(self.rows);rows[1].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):select_bracket(rows,50,20)

    def test_missing_tier_and_invalid_quantity_fail_closed(self):
        for amount in ('1000','0','NaN','-1'):
            with self.subTest(amount=amount),self.assertRaises(ValueError):select_bracket(self.rows,amount,20)
