import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from agentrader.config import Config
from agentrader.exchange import ExchangeError
from agentrader.orders import build_limit, order_cycle

SYMBOL = {'symbol': 'BTCUSDT', 'status': 'TRADING', 'quoteAsset': 'USDT', 'filters': [
    {'filterType': 'PRICE_FILTER', 'tickSize': '0.10', 'minPrice': '1', 'maxPrice': '1000000'},
    {'filterType': 'LOT_SIZE', 'stepSize': '0.0001', 'minQty': '0.0001', 'maxQty': '100'},
    {'filterType': 'MIN_NOTIONAL', 'notional': '50'}]}


class FakeExchange:
    def __init__(self, config):
        self.calls = []
        self.canceled = False
        self.timeout = False
        self.balance = '1000'

    def sync_time(self):
        pass

    def get(self, path, params=None):
        if path.endswith('dual'):
            return {'dualSidePosition': False}
        if path.endswith('account'):
            return {'availableBalance': self.balance, 'positions': []}
        if path.endswith('openOrders'):
            return []
        if path.endswith('exchangeInfo'):
            return {'symbols': [SYMBOL]}
        if path.endswith('bookTicker'):
            return {'bidPrice': '70000'}
        return {'status': 'CANCELED' if self.canceled else 'NEW', 'executedQty': '0'}

    def request(self, method, path, params):
        self.calls.append(method)
        if method == 'DELETE':
            self.canceled = True
        if method == 'POST' and self.timeout:
            raise ExchangeError('timeout')
        return self.get('/fapi/v1/order')


class OrderTests(unittest.TestCase):
    def test_decimal_steps_and_minimum_notional(self):
        plan = build_limit(SYMBOL, '70000.03')
        price, qty = Decimal(plan['price']), Decimal(plan['quantity'])
        self.assertEqual(price % Decimal('.1'), 0)
        self.assertEqual(qty % Decimal('.0001'), 0)
        self.assertGreaterEqual(price * qty, 50)
        self.assertEqual(plan['timeInForce'], 'GTX')

    def test_preview_and_zero_balance_never_submit(self):
        fake = FakeExchange(Config())
        fake.balance = '0'
        with patch('agentrader.orders.DemoExchange', return_value=fake):
            self.assertEqual(order_cycle(Config())['status'], 'preview')
            with self.assertRaisesRegex(ValueError, 'bakiye'):
                order_cycle(Config(), execute=True)
        self.assertEqual(fake.calls, [])

    def test_success_and_timeout_reconcile_without_duplicate_post(self):
        for timeout in (False, True):
            fake = FakeExchange(Config())
            fake.timeout = timeout
            with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
                with patch('agentrader.orders.DemoExchange', return_value=fake):
                    result = order_cycle(Config(), execute=True, journal=Path(folder) / 'events.jsonl')
                self.assertEqual(result['status'], 'passed')
                self.assertEqual(fake.calls, ['POST', 'DELETE'])
                self.assertIn('final', (Path(folder) / 'events.jsonl').read_text())
