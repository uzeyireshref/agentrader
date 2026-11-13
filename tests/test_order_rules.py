import unittest
from agentrader.order_rules import validate_order
from test_orders import SYMBOL


class OrderRuleTests(unittest.TestCase):
    def setUp(self):
        self.order={'symbol':'BTCUSDT','side':'BUY','positionSide':'BOTH','type':'LIMIT',
                    'price':'75000','quantity':'.001','timeInForce':'GTC'}
    def build(self,p=None,mode='one-way',operation='OPEN'):
        return validate_order(p or self.order,SYMBOL,mode,operation,'75000',1000000)
    def test_long_and_short_open_orders(self):
        self.assertEqual(self.build()['path'],'/fapi/v1/order')
        self.assertEqual(self.build(self.order|{'side':'SELL'})['operation'],'OPEN')
    def test_hedge_side_and_reduce_only_rules(self):
        p=self.order|{'positionSide':'SHORT','side':'SELL'}
        self.build(p,'hedge')
        with self.assertRaises(ValueError):self.build(p|{'reduceOnly':'true'},'hedge')
        with self.assertRaises(ValueError):self.build(p|{'side':'BUY'},'hedge')
    def test_reducing_market_exit_can_be_below_entry_minimum(self):
        p={'symbol':'BTCUSDT','side':'SELL','positionSide':'BOTH','type':'MARKET','quantity':'.0001','reduceOnly':'true'}
        self.assertEqual(self.build(p,operation='REDUCE')['params']['quantity'],'0.0001')
        with self.assertRaises(ValueError):self.build(p)
    def test_stop_close_all_and_quantity_conflict(self):
        p={'symbol':'BTCUSDT','side':'SELL','positionSide':'BOTH','type':'STOP_MARKET',
           'closePosition':'true','triggerPrice':'74000','workingType':'MARK_PRICE'}
        self.assertEqual(self.build(p,operation='CLOSE')['path'],'/fapi/v1/algoOrder')
        for change in ({'quantity':'.001'},{'reduceOnly':'true'}):
            with self.assertRaises(ValueError):self.build(p|change,operation='CLOSE')
    def test_minimum_steps_and_unknown_fields(self):
        for change in ({'quantity':'.0001'},{'price':'75000.03'},{'withdraw':'true'}):
            with self.assertRaises(ValueError):self.build(self.order|change)
    def test_market_does_not_accept_limit_fields(self):
        with self.assertRaises(ValueError):self.build(self.order|{'type':'MARKET'})
    def test_gtd_requires_a_valid_future_time(self):
        self.build(self.order|{'timeInForce':'GTD','goodTillDate':2000000})
        with self.assertRaises(ValueError):self.build(self.order|{'timeInForce':'GTD','goodTillDate':1100000})
    def test_trailing_stop_direction_and_callback(self):
        p={'symbol':'BTCUSDT','side':'SELL','positionSide':'BOTH','type':'TRAILING_STOP_MARKET',
           'quantity':'.001','reduceOnly':'true','callbackRate':'1','activatePrice':'76000'}
        self.build(p,operation='REDUCE')
        with self.assertRaises(ValueError):self.build(p|{'callbackRate':'20'},operation='REDUCE')
        with self.assertRaises(ValueError):self.build(p|{'activatePrice':'74000'},operation='REDUCE')
    def test_stop_limit_and_take_profit_limit_are_conditional(self):
        for kind in ('STOP','TAKE_PROFIT'):
            p=self.order|{'type':kind,'triggerPrice':'74500'}
            self.assertEqual(self.build(p)['path'],'/fapi/v1/algoOrder')
    def test_output_is_only_a_proposal_without_execution_permission(self):
        self.assertFalse(self.build()['execution_authorized'])

    def test_integer_does_not_count_as_boolean(self):
        with self.assertRaises(ValueError):
            self.build(self.order|{'reduceOnly':0})

    def test_gtd_millisecond_rounding_does_not_bypass_minimum(self):
        with self.assertRaises(ValueError):
            self.build(self.order|{'timeInForce':'GTD','goodTillDate':1600999})
