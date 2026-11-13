import json
import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from agentrader.execution import DurableExchange, reconcile, resolve_absent_flat
from agentrader.exchange import ExchangeError
from agentrader.risk import evaluate, size_for_risk, RiskLimits
from agentrader.state import StateStore
from agentrader.locking import execution_lock


class Exchange:
    def __init__(self):
        self.sent = 0
        self.response = {'status': 'NEW', 'executedQty': '0'}
        self.fail_send = False
        self.positions = []
        self.algos = []
        self.income = []

    def sync_time(self):
        pass

    def get(self, path, params=None):
        if path.endswith('/account'):
            return {'positions': self.positions, 'availableBalance': '5000'}
        if path.endswith('openOrders'):
            return []
        if path.endswith('openAlgoOrders'):
            return self.algos
        if path.endswith('premiumIndex'):
            return {'markPrice': '80000'}
        if path.endswith('dual'):
            return {'dualSidePosition': False}
        if path.endswith('income'):
            return [dict(row, time=params['endTime'], tranId=i+1) for i,row in enumerate(self.income)]
        return self.response

    def request(self, method, path, params):
        self.sent += 1
        if self.fail_send:
            raise ExchangeError('Lost response')
        return self.response


PARAMS = {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET',
          'quantity': '0.0008', 'newClientOrderId': 'agt-test'}


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.path = Path(self.folder.name) / 'state.sqlite3'
        self.store = StateStore(self.path)
        self.exchange = Exchange()
        self.engine = DurableExchange(self.exchange, self.store)
        self.engine.configure_entry('80000', '78400')

    def tearDown(self):
        self.store.close()
        self.folder.cleanup()

    def test_restart_after_lost_response_never_reposts(self):
        self.exchange.fail_send = True
        with self.assertRaises(ExchangeError):
            self.engine.request('POST', '/fapi/v1/order', PARAMS)
        self.store.close()
        self.store = StateStore(self.path)
        restarted = DurableExchange(self.exchange, self.store)
        self.exchange.response = {'status': 'FILLED', 'executedQty': '.0008'}
        result = restarted.request('POST', '/fapi/v1/order', PARAMS)
        self.assertEqual(result['status'], 'FILLED')
        self.assertEqual(self.exchange.sent, 1)
        self.assertEqual(self.store.intents()[0]['state'], 'FILLED')

    def test_crash_after_reservation_does_not_send_on_restart(self):
        self.store.reserve(PARAMS['newClientOrderId'], '/fapi/v1/order', PARAMS)
        with patch.object(self.exchange, 'get', side_effect=ExchangeError('not found')):
            with self.assertRaises(ExchangeError):
                self.engine.request('POST', '/fapi/v1/order', PARAMS)
        self.assertEqual(self.exchange.sent, 0)

    def test_partial_fill_and_manual_position_halt_without_mutation(self):
        self.store.reserve('agt-test', '/fapi/v1/order', PARAMS)
        self.exchange.response = {'status': 'PARTIALLY_FILLED', 'executedQty': '.0004'}
        self.exchange.positions = [{'positionAmt': '.0004'}]
        self.exchange.algos = [{'algoStatus': 'NEW'}]
        report = reconcile(self.exchange, self.store, clear_halt=True)
        self.assertFalse(report['ready'])
        self.assertIsNotNone(self.store.halt_reason())
        self.assertEqual(self.exchange.sent, 0)

    def test_halt_blocks_entries_but_allows_reduce_only(self):
        self.store.halt('stop failure')
        with self.assertRaises(ValueError):
            self.engine.request('POST', '/fapi/v1/order', PARAMS)
        closing = dict(PARAMS, side='SELL', reduceOnly='true', newClientOrderId='agt-close')
        self.engine.request('POST', '/fapi/v1/order', closing)
        self.assertEqual(self.exchange.sent, 1)

    def test_daily_limit_and_missing_risk_reject_before_post(self):
        self.exchange.income = [{'income': '-26', 'incomeType': 'REALIZED_PNL', 'asset': 'USDT'}]
        with self.assertRaisesRegex(ValueError, 'Günlük'):
            self.engine.request('POST', '/fapi/v1/order', PARAMS)
        self.engine.entry_risk = None
        with self.assertRaises(ValueError):
            self.engine.request('POST', '/fapi/v1/order', PARAMS)
        self.assertEqual(self.exchange.sent, 0)

    def test_clear_halt_only_on_clean_account(self):
        self.store.halt('previous issue')
        self.assertFalse(reconcile(self.exchange, self.store)['ready'])
        self.assertTrue(reconcile(self.exchange, self.store, clear_halt=True)['ready'])

    def test_reused_id_different_parameters_rejected(self):
        self.engine.request('POST', '/fapi/v1/order', PARAMS)
        with self.assertRaisesRegex(ValueError, 'farklı'):
            self.engine.request('POST', '/fapi/v1/order', dict(PARAMS, quantity='1'))
        self.assertEqual(self.exchange.sent, 1)

    def test_concurrent_store_reservation_is_unique(self):
        another = StateStore(self.path)
        try:
            self.assertTrue(self.store.reserve('same', '/fapi/v1/order', PARAMS))
            self.assertFalse(another.reserve('same', '/fapi/v1/order', PARAMS))
        finally:
            another.close()

    def test_runtime_lock_rejects_second_executor(self):
        path = Path(self.folder.name) / 'runtime.lock'
        with execution_lock(path):
            with self.assertRaises(ValueError):
                with execution_lock(path):
                    pass


class RiskTests(unittest.TestCase):
    def test_size_rounds_down(self):
        self.assertEqual(size_for_risk('100', '90', '1.05', '.01'), Decimal('.10'))

    def test_limits_and_stale_data(self):
        base = dict(entry='80000', stop='78400', quantity='.0008', equity='5000',
                    open_risk='0', daily_loss='0', positions=0, observed_at=100, now=101)
        self.assertEqual(evaluate(**base)['estimated_stop_loss'], '1.2800')
        for change in ({'daily_loss': '25'}, {'open_risk': '10'}, {'quantity': '1'},
                       {'positions': 1}, {'now': 200}, {'now': 99}, {'entry': 'NaN'},
                       {'equity': '1'}, {'stop': '80000'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                evaluate(**(base | change))
