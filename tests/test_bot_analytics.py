import copy
import unittest
from decimal import Decimal
from agentrader.application.bot_analytics import summarize,position_metrics


class AnalyticsMathTests(unittest.TestCase):
    def test_calculator_collector_skips_execution_history_and_still_rejects_stale_reads(self):
        from test_v2_preflight import SnapshotExchange
        from agentrader.application.bot_analytics import collect_snapshot
        from agentrader.bot.risk import RiskLimits
        from agentrader.bot.preflight_errors import PreflightRejection
        x=SnapshotExchange();result=collect_snapshot(x,'BTCUSDT',RiskLimits(),lambda:1001)
        self.assertEqual(result['mark']['markPrice'],'80000')
        paths={p for p,_ in x.calls}
        self.assertNotIn('/fapi/v1/income',paths);self.assertNotIn('/fapi/v1/openOrders',paths)
        for path in ('/fapi/v1/premiumIndex','/fapi/v1/assetIndex'):x.data[path]['time']=1016000
        times=iter([1000,1016])
        with self.assertRaises(PreflightRejection):collect_snapshot(x,'BTCUSDT',RiskLimits(),lambda:next(times))
    def test_analytics_read_weights_are_path_and_method_specific(self):
        from urllib.request import Request
        from agentrader.shared.rate_budget import rest_charges
        costs={'accountConfig':5,'positionSide/dual':30,'symbolConfig':5,'leverageBracket':1,'premiumIndex':1,'assetIndex':1}
        for name,cost in costs.items():
            self.assertEqual(rest_charges(Request('https://demo-fapi.binance.com/fapi/v1/'+name+'?symbol=ETHUSDT'))[0][-1],cost)
        self.assertEqual(rest_charges(Request('https://demo-fapi.binance.com/fapi/v1/premiumIndex'))[0][-1],10)
        self.assertEqual(rest_charges(Request('https://demo-fapi.binance.com/fapi/v1/assetIndex'))[0][-1],10)
        self.assertEqual(rest_charges(Request('https://demo-fapi.binance.com/fapi/v1/accountConfig',data=b''))[0][-1],100)
        self.assertEqual(rest_charges(Request('https://demo-dapi.binance.com/dapi/v1/leverageBracket'))[0][-1],100)
    def test_long_and_short_pnl_fee_reserve_roe_and_liquidation_provenance(self):
        for direction,mark,target,stop in [('LONG','110','120','90'),('SHORT','90','80','110')]:
            plan={'symbol':'TESTUSDT','direction':direction,'stop':stop,'execution':{'strategy':'SINGLE','margin_mode':'ISOLATED'},'entry':{}}
            snap={'observed_at':100,'mark':{'markPrice':mark,'time':100000},'collateral':'1000'}
            compiled={'state':'READY','quantity':'2','entry':{'params':{'price':'100'}},'targets':[{'quantity':'2','price':target}],'notional_ceiling':'200',
                      'risk':{'initial_margin':'20','fee_reserve':'0.4','risk_with_fee_reserve':'20.4','positions':[{'direction':direction,'estimated_liquidation':'91'}]}}
            original=copy.deepcopy((plan,snap,compiled));r=summarize(plan,snap,compiled)
            self.assertEqual(Decimal(r['pnl_at_mark']),20)
            self.assertEqual(Decimal(r['target_gross']),40)
            self.assertEqual(Decimal(r['target_after_fee_reserve']),Decimal('39.6'))
            self.assertEqual(Decimal(r['target_roe_percent']),198)
            self.assertEqual(Decimal(r['target_return_percent']),20)
            self.assertEqual(Decimal(r['stop_after_fee_reserve']),Decimal('-20.4'))
            self.assertEqual(r['liquidation'],compiled['risk']['positions'])
            self.assertFalse(r['order_sent']);self.assertFalse(r['execution_authorized'])
            self.assertEqual((plan,snap,compiled),original)

    def test_actual_rounded_target_parts_determine_profit(self):
        plan={'symbol':'TESTUSDT','direction':'LONG','stop':'90','execution':{'strategy':'SINGLE','margin_mode':'CROSSED'},'entry':{}}
        snap={'observed_at':100,'mark':{'markPrice':'100','time':100000},'collateral':'1000'}
        compiled={'state':'READY','quantity':'3','entry':{'params':{'price':'100'}},'targets':[{'quantity':'1','price':'110'},{'quantity':'2','price':'130'}],'notional_ceiling':'300','risk':{'initial_margin':'30','fee_reserve':'.6','risk_with_fee_reserve':'30.6','positions':[]}}
        self.assertEqual(Decimal(summarize(plan,snap,compiled)['target_gross']),70)
        plan['entry']['order_options']={'price_match':'OPPONENT'}
        self.assertNotIn('target_gross',summarize(plan,snap,compiled))

    def test_grid_and_waiting_condition_never_invent_single_trade_profit(self):
        plan={'symbol':'TESTUSDT','execution':{'strategy':'NEUTRAL_GRID','margin_mode':'ISOLATED'}}
        snap={'observed_at':100,'finished_at':101,'mark':{'markPrice':'100','time':101000},'collateral':'1000'}
        waiting=summarize(plan,snap,{'state':'WAITING_CONDITION'})
        self.assertNotIn('initial_margin',waiting);self.assertEqual(waiting['calculated_at'],101)
        ready=summarize(plan,snap,{'state':'READY','notional_ceiling':'200','risk':{'initial_margin':'20','fee_reserve':'.4','risk_with_fee_reserve':'5','positions':[]}})
        self.assertEqual(ready['initial_margin'],'20');self.assertNotIn('target_gross',ready)

    def test_missing_margin_and_zero_liquidation_never_become_fabricated_percentages(self):
        self.assertEqual(position_metrics({'positionAmt':'1','markPrice':'100','liquidationPrice':'0','unRealizedProfit':'20'}),{'roe_percent':None,'liquidation_distance_percent':None})
        for amount,liq in [('1','80'),('-1','120')]:
            r=position_metrics({'positionAmt':amount,'markPrice':'100','liquidationPrice':liq,'unRealizedProfit':'20','positionInitialMargin':'50'})
            self.assertEqual(Decimal(r['roe_percent']),40)
            self.assertEqual(Decimal(r['liquidation_distance_percent']),20)
