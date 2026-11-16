import copy
import unittest
from unittest.mock import Mock

import test_signal_previews as preview_tests
from agentrader.integration.preview_preflight import ReadOnlyDemoAccount, preflight_preview
from agentrader.bot.risk import RiskLimits


class AccountBridgeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = preview_tests.PreviewTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.body = self.fixture.create()
        self.exchange = Mock()
        self.collect = Mock(return_value={})
        self.prepare = Mock(return_value={'state': 'READY', 'execution_authorized': False})

    def run_check(self, provider=None):
        return preflight_preview(provider or (lambda: self.fixture.service.show('main', self.fixture.event)),
                                 self.exchange, RiskLimits(), clock=lambda: self.fixture.clock[1],
                                 collect=self.collect, prepare=self.prepare)

    def test_ready_does_not_grant_order_authority(self):
        result = self.run_check()
        self.assertFalse(result['order_authority'])
        self.assertFalse(result['execution_eligible'])
        self.assertEqual(result['approval_state'], 'NOT_REQUESTED')
        self.assertIsInstance(self.collect.call_args.args[0], ReadOnlyDemoAccount)
        self.exchange.assert_not_called()

    def test_expiry_during_account_io_blocks_result(self):
        self.collect.side_effect = lambda *args: self.fixture.clock.__setitem__(1, self.body['expires_at'] + 1) or {}
        with self.assertRaisesRegex(ValueError, 'NOT_CURRENT'):
            self.run_check()

    def test_drawing_revision_during_account_io_blocks_result(self):
        # A superseded/revoked provider state must fail even with a READY account check.
        later = copy.deepcopy(self.body)
        later.update(state='INVALIDATED', reasons=['PREVIEW_REVISION_CHANGED'])
        provider = Mock(side_effect=[self.body, later])
        with self.assertRaisesRegex(ValueError, 'NOT_CURRENT'):
            self.run_check(provider)

    def test_tampered_plan_blocks_before_account_request(self):
        bad = copy.deepcopy(self.body)
        bad['plan']['stop'] = '1'
        with self.assertRaisesRegex(ValueError, 'INTEGRITY'):
            self.run_check(lambda: bad)
        self.collect.assert_not_called()

    def test_transport_rejects_every_mutating_method(self):
        account = ReadOnlyDemoAccount(self.exchange)
        for method in ('POST', 'PUT', 'DELETE'):
            with self.assertRaisesRegex(ValueError, 'READ_ONLY'):
                account.request(method, '/fapi/v1/order', {})
        with self.assertRaises(ValueError):
            account.get('/fapi/v1/listenKey')
        self.exchange.request.assert_not_called()
        account.get('/fapi/v3/account')
        self.exchange.request.assert_called_once_with('GET', '/fapi/v3/account', None)

    def test_failed_account_check_does_not_recheck_or_approve(self):
        self.prepare.side_effect = ValueError('account settings incompatible')
        with self.assertRaises(ValueError):
            self.run_check()

    def test_real_risk_preparer_accepts_matching_account_and_rejects_leverage(self):
        from test_v2_preflight import snapshot
        from agentrader.bot.v2_preflight import prepare_single
        snap = snapshot()
        snap['mark'].update(markPrice='100')
        snap['settings'].update(leverage=2, marginType='ISOLATED')
        self.collect.return_value = snap
        self.prepare.side_effect = lambda p, s, limits: prepare_single(p, s, limits, now=1001)
        self.assertEqual(self.run_check()['account_preflight']['state'], 'READY')
        snap['settings']['leverage'] = 20
        with self.assertRaises(ValueError):
            self.run_check()

