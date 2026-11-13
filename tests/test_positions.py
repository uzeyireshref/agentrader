import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from agentrader.config import Config
from agentrader.exchange import ExchangeError
from agentrader.positions import position_cycle, position_plan
from test_orders import SYMBOL


class PositionExchange:
    def __init__(self):
        self.qty = Decimal(0)
        self.orders = {}
        self.algos = {}
        self.calls = []
        self.fail_protection = False
        self.timeout_entry = False

    def sync_time(self):
        pass

    def get(self, path, params=None):
        params = params or {}
        if path.endswith('dual'):
            return {'dualSidePosition': False}
        if path.endswith('account'):
            return {'positions': [], 'availableBalance': '5000'}
        if path.endswith('openOrders'):
            return []
        if path.endswith('openAlgoOrders'):
            return [v for v in self.algos.values() if v['algoStatus'] == 'NEW']
        if path.endswith('exchangeInfo'):
            return {'symbols': [SYMBOL]}
        if path.endswith('premiumIndex'):
            return {'markPrice': '80000'}
        if path.endswith('positionRisk'):
            return [{'symbol': 'BTCUSDT', 'positionAmt': str(self.qty)}]
        if path.endswith('algoOrder'):
            return self.algos[params['clientAlgoId']]
        return self.orders[params['origClientOrderId']]

    def request(self, method, path, params):
        self.calls.append((method, path, dict(params)))
        if path.endswith('algoOrder'):
            cid = params['clientAlgoId']
            if method == 'POST':
                self.algos[cid] = dict(params, orderType=params['type'], algoStatus='NEW')
                if self.fail_protection:
                    self.algos[cid]['closePosition'] = 'false'
            else:
                self.algos[cid]['algoStatus'] = 'CANCELED'
            return self.algos[cid]
        qty = Decimal(params['quantity'])
        if params.get('reduceOnly') == 'true':
            if qty > abs(self.qty):
                raise AssertionError('Over-close')
        self.qty += qty if params['side'] == 'BUY' else -qty
        result = {'status': 'FILLED', 'executedQty': str(qty)}
        self.orders[params['newClientOrderId']] = result
        if self.timeout_entry and params['side'] == 'BUY':
            raise ExchangeError('timeout after fill')
        return result


class PositionTests(unittest.TestCase):
    def test_plan_has_valid_split_and_demo_cap(self):
        plan = position_plan(SYMBOL, '80000')
        self.assertEqual(Decimal(plan['quantity']), Decimal(plan['partial_quantity']) * 2)
        self.assertLessEqual(Decimal(plan['notional_estimate']), 100)
        self.assertLess(Decimal(plan['stop']), 80000)
        self.assertGreater(Decimal(plan['target']), 80000)

    def run_cycle(self, fake):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            with patch('agentrader.positions.DemoExchange', return_value=fake):
                return position_cycle(Config(), execute=True, journal=Path(folder) / 'events.jsonl')

    def test_normal_cycle_and_lost_entry_response(self):
        for timeout in (False, True):
            fake = PositionExchange()
            fake.timeout_entry = timeout
            result = self.run_cycle(fake)
            self.assertEqual(result['status'], 'passed')
            self.assertEqual(fake.qty, 0)
            market = [p for m, path, p in fake.calls if path.endswith('/order')]
            self.assertEqual(len(market), 3)
            self.assertTrue(all(p.get('reduceOnly') == 'true' for p in market[1:]))
            self.assertTrue(all(a['algoStatus'] == 'CANCELED' for a in fake.algos.values()))

    def test_bad_protection_causes_immediate_exit_before_cancel(self):
        fake = PositionExchange()
        fake.fail_protection = True
        with self.assertRaisesRegex(ExchangeError, 'koruyucu'):
            self.run_cycle(fake)
        self.assertEqual(fake.qty, 0)
        paths = [(m, p) for m, p, _ in fake.calls]
        self.assertEqual(paths[-2:], [('POST', '/fapi/v1/order'), ('DELETE', '/fapi/v1/algoOrder')])

    def test_preview_does_not_submit(self):
        fake = PositionExchange()
        with patch('agentrader.positions.DemoExchange', return_value=fake):
            self.assertEqual(position_cycle(Config())['status'], 'preview')
        self.assertEqual(fake.calls, [])
