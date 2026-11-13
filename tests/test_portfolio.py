import unittest
from dataclasses import replace
from decimal import Decimal

from agentrader.portfolio import Exposure,evaluate_portfolio,liquidation_price
from agentrader.risk import RiskLimits


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.limits=replace(RiskLimits(),max_notional=Decimal('1000'),max_trade_loss=Decimal('50'),
                            max_total_loss=Decimal('100'),max_positions=4,max_daily_loss=Decimal('100'))
        self.leg=Exposure('BTCUSDT','LONG','.002','75000','74000',20,'CROSSED','.004')

    def evaluate(self,legs=None,collateral='5000',**changes):
        return evaluate_portfolio(legs or [self.leg],collateral,'0',100,101,self.limits,
                                  collateral_valuation_verified=True,**changes)

    def test_nominal_margin_and_stop_are_different(self):
        r=self.evaluate()
        self.assertEqual(Decimal(r['notional']),150)
        self.assertEqual(Decimal(r['initial_margin']),Decimal('7.5'))
        self.assertEqual(Decimal(r['stop_loss_excluding_costs']),2)

    def test_long_and_short_hedge_risk_is_not_netted(self):
        short=replace(self.leg,direction='SHORT',stop='76000')
        r=self.evaluate([self.leg,short])
        self.assertEqual(Decimal(r['notional']),300)
        self.assertEqual(Decimal(r['stop_loss_excluding_costs']),4)
        self.assertEqual(len(r['positions']),2)

    def test_pending_entries_aggregate_instead_of_releasing_risk(self):
        r=self.evaluate([self.leg,self.leg])
        self.assertEqual(Decimal(r['initial_margin']),15)
        self.assertEqual(len(r['positions']),1)

    def test_isolated_stop_beyond_liquidation_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'likidasyon'):
            self.evaluate([replace(self.leg,margin_mode='ISOLATED',stop='70000')])

    def test_verified_extra_isolated_margin_can_move_liquidation(self):
        r=self.evaluate([replace(self.leg,margin_mode='ISOLATED',stop='70000',extra_isolated_margin='20')])
        self.assertEqual(Decimal(r['initial_margin']),Decimal('27.5'))

    def test_insufficient_margin_and_stale_snapshot_block(self):
        with self.assertRaises(ValueError):self.evaluate(collateral='1')
        with self.assertRaises(ValueError):
            evaluate_portfolio([self.leg],'5000','0',100,200,self.limits,collateral_valuation_verified=True)

    def test_unvalued_collateral_never_assumed_usdt(self):
        with self.assertRaises(ValueError):evaluate_portfolio([self.leg],'5000','0',100,101,self.limits)

    def test_loss_budget_is_not_multiplied_by_leverage(self):
        with self.assertRaises(ValueError):self.evaluate([replace(self.leg,quantity='.02',stop='70000')])

    def test_inconsistent_profiles_same_position_are_rejected(self):
        with self.assertRaises(ValueError):self.evaluate([self.leg,replace(self.leg,leverage=10)])

    def test_formula_direction_and_nan_validation(self):
        self.assertLess(liquidation_price('LONG','1','100','10','.01'),100)
        self.assertGreater(liquidation_price('SHORT','1','100','10','.01'),100)
        with self.assertRaises(ValueError):liquidation_price('LONG','NaN','100','10','.01')

    def test_short_loss_and_nominal_use_separate_conservative_prices(self):
        leg=replace(self.leg,direction='SHORT',entry='73000',stop='79000',notional_price='79000')
        r=self.evaluate([leg])
        self.assertEqual(Decimal(r['notional']),158)
        self.assertEqual(Decimal(r['stop_loss_excluding_costs']),12)
        self.assertEqual(Decimal(r['fee_reserve']),Decimal('.316'))

    def test_isolated_reserve_does_not_invent_extra_liquidation_margin(self):
        leg=replace(self.leg,margin_mode='ISOLATED',stop='70000',notional_price='150000')
        with self.assertRaisesRegex(ValueError,'likidasyon'):self.evaluate([leg])
