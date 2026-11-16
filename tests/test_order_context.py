import copy
import unittest

from agentrader.bot.order_rules import validate_order
from agentrader.bot.order_send_guard import validate_before_send
from test_orders import SYMBOL
from test_v2_preflight import SnapshotExchange


class OrderContextTests(unittest.TestCase):
    def setUp(self):
        self.symbol=copy.deepcopy(SYMBOL)
        self.order=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='LIMIT',quantity='1',price='100',timeInForce='GTC')

    def validate(self,order=None,**context):
        return validate_order(order or self.order,self.symbol,'one-way',context.pop('operation','OPEN'),'100',1000000,**context)

    def test_percent_price_is_directional_and_inclusive(self):
        self.symbol['filters'].append(dict(filterType='PERCENT_PRICE',multiplierUp='1.1',multiplierDown='.9'))
        for side,price in [('BUY','110'),('BUY','80'),('SELL','90'),('SELL','120')]:
            self.validate(self.order|dict(side=side,price=price))
        for side,price in [('BUY','110.1'),('SELL','89.9')]:
            with self.subTest(side=side),self.assertRaisesRegex(ValueError,'bandın dışında'):
                self.validate(self.order|dict(side=side,price=price))

    def test_trigger_direction_and_equality_for_every_stop_and_take_profit(self):
        for kind in ('STOP','STOP_MARKET','TAKE_PROFIT','TAKE_PROFIT_MARKET'):
            for side in ('BUY','SELL'):
                above=(side=='BUY')==(kind in ('STOP','STOP_MARKET'))
                p=dict(symbol='BTCUSDT',side=side,positionSide='BOTH',type=kind,quantity='1',workingType='MARK_PRICE')
                if kind in ('STOP','TAKE_PROFIT'):p.update(price='100')
                valid='110' if above else '90'
                self.assertEqual(self.validate(p|dict(triggerPrice=valid))['path'],'/fapi/v1/algoOrder')
                for bad in ('100','90' if above else '110'):
                    with self.subTest(kind=kind,side=side,bad=bad),self.assertRaisesRegex(ValueError,'hemen tetiklenir'):
                        self.validate(p|dict(triggerPrice=bad))

    def test_contract_reference_is_distinct_required_and_fresh(self):
        p=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='STOP_MARKET',quantity='1',triggerPrice='110')
        self.validate(p|dict(workingType='MARK_PRICE'))
        with self.assertRaises(ValueError):self.validate(p)
        with self.assertRaisesRegex(ValueError,'hemen tetiklenir'):
            self.validate(p,contract_price=dict(symbol='BTCUSDT',price='120',time=1000000))
        self.validate(p,contract_price=dict(symbol='BTCUSDT',price='105',time=1000000))
        for reference in (dict(symbol='ETHUSDT',price='105',time=1000000),dict(symbol='BTCUSDT',price='105',time=984999),dict(symbol='BTCUSDT',price='105',time=1001001),dict(symbol='BTCUSDT',price='NaN',time=1000000)):
            with self.subTest(reference=reference),self.assertRaises(ValueError):self.validate(p,contract_price=reference)

    def test_trailing_callback_range_and_activation_reference(self):
        p=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='TRAILING_STOP_MARKET',quantity='1',reduceOnly='true',workingType='MARK_PRICE',activatePrice='110')
        for callback in ('.1','5','7.5','10','20'):
            self.validate(p|dict(callbackRate=callback),operation='REDUCE')
        for callback in ('.09','20.1','NaN','Infinity'):
            with self.subTest(callback=callback),self.assertRaises(ValueError):
                self.validate(p|dict(callbackRate=callback),operation='REDUCE')
        with self.assertRaises(ValueError):
            self.validate(p|dict(callbackRate='10',workingType='CONTRACT_PRICE'),operation='REDUCE',contract_price=dict(symbol='BTCUSDT',price='120',time=1000000))

    def test_zero_price_rules_and_nonzero_filter_origins(self):
        self.symbol['filters'][0].update(minPrice='0',maxPrice='0',tickSize='0')
        self.validate(self.order|dict(price='100.003'))
        self.symbol['filters'][0].update(minPrice='.05',maxPrice='1000000',tickSize='.1')
        self.validate(self.order|dict(price='100.05'))
        with self.assertRaises(ValueError):self.validate(self.order|dict(price='100'))
        self.symbol['filters'][1].update(minQty='.00015',stepSize='.0001')
        self.symbol['filters'][2]['notional']='0'
        self.validate(self.order|dict(price='100.05',quantity='.00025'))

    def test_unknown_malformed_and_duplicate_filters_fail_explicitly(self):
        for change in ('UNKNOWN','DUPLICATE','MISSING','NAN'):
            s=copy.deepcopy(self.symbol)
            if change=='UNKNOWN':s['filters'].append(dict(filterType='NEW_RULE'))
            elif change=='DUPLICATE':s['filters'].append(copy.deepcopy(s['filters'][0]))
            elif change=='MISSING':del s['filters'][0]['tickSize']
            else:s['filters'][0]['tickSize']='NaN'
            with self.subTest(change=change),self.assertRaises(ValueError):
                validate_order(self.order,s,'one-way','OPEN','100',1000000)

    def test_risk_control_does_not_guess_allowed_opening_side(self):
        control=dict(filterType='POSITION_RISK_CONTROL',positionControlSide='NONE')
        self.symbol['filters'].append(control)
        self.validate()
        control['positionControlSide']='UNDEFINED_RESTRICTION'
        with self.assertRaisesRegex(ValueError,'risk kontrolünde'):self.validate()
        self.validate(dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='MARKET',quantity='1',reduceOnly='true'),operation='REDUCE')

    def test_total_and_algo_order_caps_include_other_order_family(self):
        self.symbol['filters']+= [dict(filterType='MAX_NUM_ORDERS',limit=2),dict(filterType='MAX_NUM_ALGO_ORDERS',limit=1)]
        self.validate(order_counts=dict(normal=1,algo=0))
        with self.assertRaises(ValueError):self.validate(order_counts=dict(normal=1,algo=1))
        self.validate(order_counts=dict(normal=1,algo=1),additional_order=False)
        algo=dict(symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='STOP_MARKET',quantity='1',reduceOnly='true',workingType='MARK_PRICE',triggerPrice='90')
        with self.assertRaises(ValueError):self.validate(algo,operation='REDUCE',order_counts=dict(normal=0,algo=1))


class SendGuardTests(unittest.TestCase):
    def setUp(self):
        self.x=SnapshotExchange()
        self.x.data['/fapi/v2/ticker/price']=dict(symbol='BTCUSDT',price='78000',time=1000000)
        self.proposal=dict(operation='OPEN',params=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='LIMIT',price='80000',quantity='.001',timeInForce='GTC'))

    def guard(self,proposals=None,**kwargs):
        return validate_before_send(self.x,proposals or [self.proposal],'one-way',15,clock=lambda:1000,**kwargs)

    def test_contract_price_is_fetched_only_for_contract_trigger(self):
        self.proposal['params']=dict(symbol='BTCUSDT',side='BUY',positionSide='BOTH',type='STOP_MARKET',quantity='.001',triggerPrice='79000')
        self.guard()
        self.assertIn(('/fapi/v2/ticker/price',{'symbol':'BTCUSDT'}),self.x.calls)
        self.proposal['params']['workingType']='MARK_PRICE'
        with self.assertRaisesRegex(ValueError,'hemen tetiklenir'):self.guard()

    def test_stale_mark_and_new_restriction_fail_before_delivery(self):
        self.x.data['/fapi/v1/premiumIndex']['time']=984999
        with self.assertRaises(ValueError):self.guard()
        self.x.data['/fapi/v1/premiumIndex']['time']=1000000
        self.x.data['/fapi/v1/exchangeInfo']['symbols']= [copy.deepcopy(SYMBOL)]
        self.x.data['/fapi/v1/exchangeInfo']['symbols'][0]['filters'].append(dict(filterType='POSITION_RISK_CONTROL',positionControlSide='RESTRICTED'))
        with self.assertRaises(ValueError):self.guard()

    def test_batch_cannot_consume_the_same_remaining_order_slot_twice(self):
        metadata=copy.deepcopy(SYMBOL)
        metadata['filters'].append(dict(filterType='MAX_NUM_ORDERS',limit=1))
        self.x.data['/fapi/v1/exchangeInfo']['symbols']=[metadata]
        with self.assertRaisesRegex(ValueError,'emir sınırı'):
            self.guard([self.proposal,copy.deepcopy(self.proposal)])
        self.guard()

    def test_amendment_does_not_consume_a_new_order_slot(self):
        metadata=copy.deepcopy(SYMBOL)
        metadata['filters'].append(dict(filterType='MAX_NUM_ORDERS',limit=1))
        self.x.data['/fapi/v1/exchangeInfo']['symbols']=[metadata]
        self.x.data['/fapi/v1/openOrders']=[dict(symbol='BTCUSDT')]
        with self.assertRaises(ValueError):self.guard()
        self.guard(additional_order=False)

    def test_context_collection_cannot_outlive_the_age_limit(self):
        times=iter([1000,1016])
        with self.assertRaises(ValueError):
            validate_before_send(self.x,[self.proposal],'one-way',15,clock=lambda:next(times))

    def test_explicit_profile_age_is_not_replaced_by_a_fixed_ceiling(self):
        self.x.data['/fapi/v1/premiumIndex']['time']=900000
        validate_before_send(self.x,[self.proposal],'one-way',120,clock=lambda:1000)
        with self.assertRaises(ValueError):self.guard()
