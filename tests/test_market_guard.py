import copy
import unittest
from unittest.mock import Mock

from agentrader.plan_execution import market_guard_check
from agentrader.plans import example_plan, validate_plan


class MarketGuardTests(unittest.TestCase):
    def setUp(self):
        self.plan = example_plan()
        self.plan['market_guard'] = {'source': 'binance_usdm_live_mark', 'max_divergence_bps': '50', 'max_age_seconds': 10}
        self.demo = {'symbol': 'BTCUSDT', 'markPrice': '80040', 'time': 100000}
        self.live = Mock()
        self.live.get.return_value = {'symbol': 'BTCUSDT', 'markPrice': '80000', 'time': 100000}

    def test_price_gap_staleness_and_symbol_are_enforced(self):
        validate_plan(self.plan)
        result = market_guard_check(self.plan, self.demo, self.live, 100100)
        self.assertEqual(result['divergence_bps'], '5.0000')
        for change in ({'markPrice': '81000'}, {'time': 1}, {'symbol': 'ETHUSDT'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                market_guard_check(self.plan, self.demo | change, self.live, 100100)

    def test_invalid_guard_is_rejected_and_legacy_plan_needs_no_live_client(self):
        self.assertIsNone(market_guard_check(example_plan(), self.demo, None))
        for change in ({'max_divergence_bps': '200'}, {'max_age_seconds': 100}, {'source': 'unknown'}):
            plan = copy.deepcopy(self.plan)
            plan['market_guard'].update(change)
            with self.assertRaises(ValueError):
                validate_plan(plan)
