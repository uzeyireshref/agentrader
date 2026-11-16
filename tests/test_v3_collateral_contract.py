import copy
from decimal import Decimal
import unittest
from unittest.mock import patch
from agentrader.shared.config import Config
from agentrader.integration.preview_preflight import ReadOnlyDemoAccount
from agentrader.bot.history_reconciliation import HistoryReads
from agentrader.bot.v2_preflight import collateral_usdt,collect_flat_snapshot
from agentrader.bot.risk import RiskLimits
from test_v2_preflight import SnapshotExchange


class V3CollateralContractTests(unittest.TestCase):
    def account(self,**changes):
        asset=dict(asset='USDT',availableBalance='10048',walletBalance='4445',unrealizedProfit='0',initialMargin='0')
        asset.update(changes);return dict(availableBalance='10040',assets=[asset])
    def value(self,account,eligible=True):return collateral_usdt(account,{'multiAssetsMargin':True},{'index':'1','askRate':'1'},asset_eligibility=eligible)

    def test_v3_missing_eligibility_uses_explicit_exchange_metadata_and_own_usdt_cap(self):
        self.assertEqual(self.value(self.account()),4445)
        with self.assertRaises(ValueError):self.value(self.account(),None)

    def test_positive_pnl_and_other_asset_capacity_never_expand_usdt_cap(self):
        self.assertEqual(self.value(self.account(unrealizedProfit='100',initialMargin='200')),4245)
        self.assertEqual(self.value(self.account(unrealizedProfit='-100',initialMargin='200')),4145)

    def test_explicit_account_or_exchange_denial_blocks_even_if_other_source_is_true(self):
        with self.assertRaises(ValueError):self.value(self.account(marginAvailable=False),True)
        with self.assertRaises(ValueError):self.value(self.account(marginAvailable=True),False)

    def test_missing_wallet_proof_is_not_replaced_with_global_available_balance(self):
        a=self.account();del a['assets'][0]['walletBalance']
        with self.assertRaises((ValueError,KeyError)):self.value(a)

    def test_collector_accepts_actual_v3_shape_and_rejects_duplicate_asset_metadata(self):
        x=SnapshotExchange();x.data['/fapi/v3/account']=self.account()|{'positions':[]}
        x.data['/fapi/v1/exchangeInfo']['assets']=[dict(asset='USDT',marginAvailable=True)]
        self.assertEqual(Decimal(collect_flat_snapshot(x,'BTCUSDT',RiskLimits(),clock=lambda:1001)['collateral']),4445)
        x.data['/fapi/v1/exchangeInfo']['assets']*=2
        with self.assertRaises(ValueError):collect_flat_snapshot(x,'BTCUSDT',RiskLimits(),clock=lambda:1001)

    def test_both_readonly_wrappers_preserve_signed_clock_and_server_utc_income_window(self):
        class Exchange(SnapshotExchange):
            config=Config('fixture-key','fixture-secret');offset_ms=120000
            def request(self,method,path,params=None):
                if method!='GET':raise AssertionError('mutation')
                return self.get(path,params)
        for wrapper in (ReadOnlyDemoAccount,HistoryReads):
            x=Exchange();x.data['/fapi/v1/premiumIndex']['time']=86420000;x.data['/fapi/v1/assetIndex']['time']=86420000
            with patch('agentrader.bot.history.time.time',return_value=86300):
                s=collect_flat_snapshot(wrapper(x),'BTCUSDT',RiskLimits(),clock=lambda:86300)
            self.assertEqual(s['now_ms'],86420000)
            income=[params for path,params in x.calls if path=='/fapi/v1/income']
            self.assertEqual(income[0]['startTime'],86400000);self.assertEqual(income[0]['endTime'],86420000)
