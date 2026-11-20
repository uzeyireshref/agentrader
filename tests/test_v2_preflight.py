import copy
import unittest
from decimal import Decimal

from agentrader.bot.risk import RiskLimits
from agentrader.bot.v2_preflight import collateral_usdt, collect_flat_snapshot, joint_step, prepare_single
from test_orders import SYMBOL
from test_plan_v2 import plan_v2


def snapshot():
    return {'symbol_info': copy.deepcopy(SYMBOL), 'mark': {'symbol':'BTCUSDT','markPrice':'80000','time':1000000},
            'settings': {'symbol':'BTCUSDT','leverage':20,'marginType':'CROSSED'},
            'position_mode':'one-way','multi_assets':True,'collateral':'5000','daily_loss':'0',
            'brackets':[{'notionalFloor':0,'notionalCap':10000,'initialLeverage':50,'maintMarginRatio':'.004','cum':'0'}],
            'observed_at':1000,'finished_at':1001,'now_ms':1001000,'flat_verified':True}


class SnapshotExchange:
    offset_ms = 0

    def __init__(self):
        self.data = {
            '/fapi/v1/accountConfig':{'canTrade':True,'multiAssetsMargin':True},
            '/fapi/v1/positionSide/dual':{'dualSidePosition':False},
            '/fapi/v3/account':{'availableBalance':'10000','assets':[{'asset':'USDT','availableBalance':'5000','walletBalance':'5000','unrealizedProfit':'0','initialMargin':'0','marginAvailable':True}], 'positions':[]},
            '/fapi/v3/positionRisk':[], '/fapi/v1/openOrders':[], '/fapi/v1/openAlgoOrders':[],
            '/fapi/v1/symbolConfig':[snapshot()['settings']],
            '/fapi/v1/leverageBracket':[{'symbol':'BTCUSDT','brackets':snapshot()['brackets']}],
            '/fapi/v1/exchangeInfo':{'symbols':[SYMBOL]}, '/fapi/v1/income':[],
            '/fapi/v1/assetIndex':{'symbol':'USDTUSD','index':'1','askRate':'1.01','time':1000000},
            '/fapi/v1/premiumIndex':snapshot()['mark']}
        self.calls = []

    def sync_time(self): pass

    def get(self, path, params=None):
        self.calls.append((path, params))
        if path == '/fapi/v1/income':
            return [dict(row, time=params['endTime'], tranId=i+1)
                    if 'income' in row else row for i,row in enumerate(self.data[path])]
        return copy.deepcopy(self.data[path])


class V2PreflightTests(unittest.TestCase):
    def test_real_transport_read_groups_are_bounded_and_share_only_the_governor(self):
        import threading
        from types import SimpleNamespace
        from unittest.mock import patch
        from agentrader.shared.exchange import DemoExchange
        from agentrader.bot.v2_preflight import read_many
        exchange=DemoExchange(SimpleNamespace());exchange.offset_ms=123
        guard=threading.Lock();release=threading.Event();counts={'active':0,'maximum':0};readers=[]
        def get(reader,path,params=None):
            with guard:
                counts['active']+=1;counts['maximum']=max(counts['maximum'],counts['active']);readers.append(reader)
                if counts['active']==4:release.set()
            self.assertTrue(release.wait(2),'GET reads did not overlap')
            with guard:counts['active']-=1
            return path
        with patch.object(DemoExchange,'get',get):
            result=read_many(exchange,tuple(('/read-'+str(i),None) for i in range(6)))
        self.assertEqual(result,tuple('/read-'+str(i) for i in range(6)))
        self.assertEqual(counts['maximum'],4)
        self.assertTrue(all(r is not exchange and r.transport is not exchange.transport and r.transport.governor is exchange.transport.governor and r.offset_ms==123 and r.store is None for r in readers))

    def test_parallel_collection_does_not_extend_or_reset_the_freshness_window(self):
        from agentrader.bot.preflight_errors import PreflightRejection
        x=SnapshotExchange()
        for path in ('/fapi/v1/premiumIndex','/fapi/v1/assetIndex'):x.data[path]['time']=1016000
        times=iter([1000,1016])
        with self.assertRaises(PreflightRejection) as caught:collect_flat_snapshot(x,'BTCUSDT',RiskLimits(),clock=lambda:next(times))
        self.assertEqual(caught.exception.reason,'SNAPSHOT_STALE')

    def setUp(self):
        self.plan = plan_v2()
        self.plan['entry'].update(condition='IMMEDIATE', trigger_price=None)
        self.snap = snapshot()
        self.limits = RiskLimits()

    def prepare(self):
        return prepare_single(self.plan, self.snap, self.limits, now=1001)

    def test_nominal_is_not_multiplied_by_leverage(self):
        r = self.prepare()
        self.assertLessEqual(Decimal(r['notional_ceiling']), 60)
        self.assertEqual(r['entry']['params']['side'], 'BUY')
        self.assertFalse(r['execution_authorized'])
        self.assertEqual(len(r['protections']), 2)

    def test_response_preference_reaches_entry_without_changing_protection_or_risk(self):
        original=self.prepare()
        self.assertNotIn('newOrderRespType',original['entry']['params'])
        for condition,trigger in (('IMMEDIATE',None),('LIMIT','79900')):
            self.plan['entry'].update(condition=condition,trigger_price=trigger)
            baseline=self.prepare()
            for response in ('ACK','RESULT'):
                self.plan['entry']['order_response_type']=response
                prepared=self.prepare()
                self.assertEqual(prepared['entry']['params']['newOrderRespType'],response)
                self.assertEqual(prepared['risk'],baseline['risk'])
                self.assertEqual(prepared['protections'],baseline['protections'])
            del self.plan['entry']['order_response_type']

    def test_short_and_hedge_prepare_correct_sides(self):
        self.plan.update(direction='SHORT', stop='81600', targets=[{'price':'78400','fraction':'1'}],position_mode='hedge')
        self.snap['position_mode']='hedge'
        r = self.prepare()
        self.assertEqual(r['entry']['params']['side'], 'SELL')
        self.assertEqual(r['entry']['params']['positionSide'], 'SHORT')
        self.assertEqual(r['protections'][0]['params']['side'], 'BUY')

    def test_margin_budget_and_max_loss_include_fees(self):
        self.plan['sizing'].update(kind='MARGIN', amount='3')
        r = self.prepare()
        self.assertLessEqual(Decimal(r['risk']['initial_margin'])+Decimal(r['risk']['fee_reserve']), 3)
        self.plan['sizing'].update(kind='MAX_LOSS', amount='2')
        r = self.prepare()
        self.assertLessEqual(Decimal(r['risk']['risk_with_fee_reserve']), 2)

    def test_mode_leverage_and_margin_mismatch_block_without_change(self):
        for key, value in [('leverage',10), ('marginType','ISOLATED')]:
            self.snap = snapshot();self.snap['settings'][key]=value
            with self.assertRaises(ValueError):self.prepare()
        self.snap = snapshot();self.snap['position_mode']='hedge'
        with self.assertRaises(ValueError):self.prepare()

    def test_stale_or_unverified_snapshot_blocks(self):
        self.snap['observed_at']=900
        with self.assertRaises(ValueError):self.prepare()
        self.snap=snapshot();self.snap['flat_verified']=False
        with self.assertRaises(ValueError):self.prepare()

    def test_joint_step_uses_common_multiple(self):
        self.assertEqual(joint_step('.002','.003'), Decimal('.006'))

    def test_condition_waiting_and_limit_are_distinct(self):
        self.plan['entry'].update(condition='MARK_AT_OR_BELOW',trigger_price='79900')
        self.assertEqual(self.prepare()['state'],'WAITING_CONDITION')
        self.plan['entry']['condition']='LIMIT'
        self.assertEqual(self.prepare()['entry']['params']['price'],'79900')

    def test_bracket_cap_and_leverage_are_checked(self):
        self.snap['brackets'][0]['initialLeverage']=10
        with self.assertRaises(ValueError):self.prepare()
        self.snap['brackets'][0].update(initialLeverage=20,notionalCap=40)
        with self.assertRaises(ValueError):self.prepare()

    def test_multi_assets_capacity_is_bounded_by_verified_usdt(self):
        account={'availableBalance':'10000','assets':[{'asset':'USDT','availableBalance':'100','walletBalance':'100','unrealizedProfit':'0','initialMargin':'0','marginAvailable':True},
                    {'asset':'BTC','availableBalance':'3','marginAvailable':True}]}
        self.assertEqual(collateral_usdt(account,{'multiAssetsMargin':True},{'index':'1','askRate':'1.01'}),100)
        account['availableBalance']='50'
        self.assertLess(collateral_usdt(account,{'multiAssetsMargin':True},{'index':'1','askRate':'1.01'}),50)

    def test_missing_index_or_unavailable_collateral_blocks(self):
        account={'availableBalance':'100','assets':[{'asset':'USDT','availableBalance':'100','marginAvailable':False}]}
        with self.assertRaises(ValueError):collateral_usdt(account,{'multiAssetsMargin':True})
        with self.assertRaises(ValueError):collateral_usdt(account,{'multiAssetsMargin':True},{'index':'1','askRate':'1'})

    def test_collector_uses_only_reads_and_reports_flat_snapshot(self):
        x=SnapshotExchange()
        result=collect_flat_snapshot(x,'BTCUSDT',self.limits,clock=lambda:1001)
        self.assertTrue(result['flat_verified'])
        self.assertEqual(Decimal(result['collateral']),5000)
        self.assertEqual(result['position_mode'],'one-way')

    def test_collector_rejects_open_orders_foreign_positions_and_old_price(self):
        for path,value in [('/fapi/v1/openOrders',[{'clientOrderId':'manual'}]),
                           ('/fapi/v3/positionRisk',[{'positionAmt':'1'}]),
                           ('/fapi/v1/premiumIndex',{'symbol':'BTCUSDT','markPrice':'80000','time':1})]:
            x=SnapshotExchange();x.data[path]=value
            with self.assertRaises(ValueError):collect_flat_snapshot(x,'BTCUSDT',self.limits,clock=lambda:1001)

    def test_collector_rejects_incomplete_income_and_unconverted_pnl(self):
        x=SnapshotExchange();x.data['/fapi/v1/income']=[{'asset':'BTC','incomeType':'COMMISSION','income':'-.001'}]
        with self.assertRaises(ValueError):collect_flat_snapshot(x,'BTCUSDT',self.limits,clock=lambda:1001)
        x.data['/fapi/v1/income']=[{}]*1000
        with self.assertRaises(ValueError):collect_flat_snapshot(x,'BTCUSDT',self.limits,clock=lambda:1001)
