import copy
import json
import tempfile
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

from agentrader.exchange import ExchangeError
from agentrader.grid import arithmetic_levels, preview_grid, verify_leverage, GridLedger
from agentrader.risk import RiskLimits
from agentrader.state import StateStore
from test_orders import SYMBOL


def spec(budget='200'):
    return {'environment': 'demo', 'symbol': 'BTCUSDT', 'direction': 'LONG', 'entry': '75725',
            'lower': '73000', 'upper': '82500', 'intervals': 8, 'spacing': 'ARITHMETIC',
            'leverage': 20, 'budget_kind': 'NOTIONAL', 'budget': budget, 'stop': '71000'}


def generous_limits():
    return replace(RiskLimits(), max_notional=Decimal('1000'), max_trade_loss=Decimal('100'),
                   max_total_loss=Decimal('100'), max_daily_loss=Decimal('100'))


class GridTests(unittest.TestCase):
    def test_exact_eight_intervals_and_nine_boundaries(self):
        levels = arithmetic_levels('73000', '82500', 8)
        self.assertEqual(len(levels), 9)
        self.assertEqual(levels[0], 73000)
        self.assertEqual(levels[-1], 82500)
        self.assertEqual(set(b-a for a,b in zip(levels, levels[1:])), {Decimal('1187.5')})

    def test_200_is_total_nominal_not_margin_times_20(self):
        p = preview_grid(spec(), SYMBOL, generous_limits())
        self.assertEqual(p['state'], 'BLOCKED')
        self.assertLessEqual(Decimal(p['maximum_marked_notional_in_band']), 200)
        self.assertEqual(p['grid_quantity'], '0.0003')
        self.assertEqual(Decimal(p['minimum_budget_equal_btc_slots']), Decimal('462'))
        self.assertIn('MINIMUM_GRID_ORDER', [r['code'] for r in p['reasons']])
        self.assertFalse(p['executed'])

    def test_existing_risk_limits_are_not_raised(self):
        p = preview_grid(spec(), SYMBOL, RiskLimits())
        self.assertIn('NOMINAL_RISK_LIMIT', [r['code'] for r in p['reasons']])
        self.assertIn('STOP_RISK_LIMIT', [r['code'] for r in p['reasons']])

    def test_valid_budget_respects_every_exchange_buy_minimum(self):
        p = preview_grid(spec('1000'), SYMBOL, generous_limits())
        self.assertEqual(p['state'], 'VALIDATED_OFFLINE')
        for cell in p['cells']:
            self.assertGreaterEqual(Decimal(cell['buy_price'])*Decimal(cell['quantity']), 50)
        self.assertLessEqual(Decimal(p['maximum_marked_notional_in_band']), 1000)

    def test_bad_modes_prices_and_leverage_rejected(self):
        for change in ({'environment': 'live'}, {'direction': 'SHORT'}, {'budget_kind': 'MARGIN'},
                       {'leverage': True}, {'leverage': 0}, {'stop': '80000'}, {'entry': '90000'},
                       {'upper': '82500.03'}, {'intervals': 0}, {'budget': 'NaN'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                preview_grid(spec() | change, SYMBOL, generous_limits())

    def test_user_four_grid_stop_inside_band_is_recorded_without_silent_changes(self):
        plan = spec() | {'upper':'78000', 'intervals':4, 'stop':'74000'}
        p = preview_grid(plan, SYMBOL, generous_limits())
        self.assertEqual(p['spec'], plan)
        self.assertEqual(p['levels'], ['73000','74250','75500','76750','78000'])
        guard = next(r for r in p['reasons'] if r['code']=='STOP_INSIDE_GRID_REQUIRES_CANCEL')
        self.assertEqual(guard['buy_levels_at_or_below_stop'], ['73000'])
        self.assertEqual(p['state'], 'BLOCKED')


class GridLedgerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.path = Path(self.folder.name) / 'state.sqlite3'
        self.store = StateStore(self.path)
        self.preview = preview_grid(spec('1000'), SYMBOL, generous_limits())
        self.ledger = GridLedger(self.store, 'grid-test', self.preview)

    def tearDown(self):
        self.store.close()
        self.folder.cleanup()

    def fill(self, index):
        action = self.ledger.action(index)
        response = {'clientOrderId': action['newClientOrderId'], 'symbol': action['symbol'],
                    'side': action['side'], 'status': 'FILLED', 'executedQty': action['quantity']}
        self.ledger.filled(index, response)
        return action, response

    def test_seed_then_sell_then_buy_cycle(self):
        seed, response = self.fill(None)
        self.assertEqual(seed['price'], '75725')
        self.assertFalse(self.ledger.filled(None, response))
        sell = self.ledger.action(3)
        self.assertEqual(sell['side'], 'SELL')
        self.assertEqual(sell['reduceOnly'], 'true')
        self.fill(3)
        buy = self.ledger.action(3)
        self.assertEqual(buy['side'], 'BUY')
        self.assertNotEqual(sell['newClientOrderId'], buy['newClientOrderId'])
        self.fill(3)
        self.assertEqual(self.ledger.action(3)['side'], 'SELL')

    def test_restart_keeps_same_action_id_and_fill_does_not_repeat(self):
        action = self.ledger.action()
        self.store.close()
        self.store = StateStore(self.path)
        self.ledger = GridLedger(self.store, 'grid-test')
        self.assertEqual(self.ledger.action(), action)
        _, response = self.fill(None)
        self.assertFalse(self.ledger.filled(None, response))

    def test_partial_unknown_or_wrong_fill_never_advances(self):
        a = self.ledger.action()
        good = {'clientOrderId': a['newClientOrderId'], 'symbol': a['symbol'],
                'side': 'BUY', 'status': 'FILLED', 'executedQty': a['quantity']}
        for change in ({'status': 'PARTIALLY_FILLED'}, {'status': 'UNKNOWN'}, {'clientOrderId': 'other'},
                       {'side': 'SELL'}, {'executedQty': '0.0001'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.ledger.filled(None, good | change)
            self.assertEqual(self.ledger.action(), a)

    def test_invalid_preview_and_changed_plan_are_not_adopted(self):
        with self.assertRaises(ValueError):
            GridLedger(self.store, 'blocked', preview_grid(spec(), SYMBOL, generous_limits()))
        changed = copy.deepcopy(self.preview)
        changed['digest'] = 'different'
        with self.assertRaises(ValueError):
            GridLedger(self.store, 'grid-test', changed)

    def test_stop_prevents_refill_after_restart(self):
        self.fill(None)
        self.ledger.stop()
        restarted = GridLedger(self.store, 'grid-test')
        with self.assertRaises(ValueError): restarted.action(0)

    def test_mark_touching_stop_disables_all_new_cycles(self):
        self.fill(None)
        self.assertEqual(self.ledger.observe_mark('71000'), 'STOPPING')
        with self.assertRaises(ValueError): self.ledger.action(0)


class LeverageTests(unittest.TestCase):
    def setUp(self):
        self.x = Mock()
        self.current = 10
        def get(path, params=None):
            if path.endswith('leverageBracket'):
                return [{'symbol':'BTCUSDT','brackets':[{'initialLeverage':20}]}]
            if path.endswith('symbolConfig'):
                return [{'symbol':'BTCUSDT','leverage':self.current,'marginType':'CROSSED'}]
            return []
        self.x.get.side_effect = get

    def test_default_is_read_only(self):
        result = verify_leverage(self.x, 'BTCUSDT', 20)
        self.assertEqual(result['actual'], 10)
        self.x.request.assert_not_called()

    def test_explicit_apply_verifies_setting_and_never_opens_order(self):
        def post(method,path,params): self.current = params['leverage']; return {}
        self.x.request.side_effect = post
        self.assertEqual(verify_leverage(self.x, 'BTCUSDT', 20, apply=True)['actual'], 20)
        self.x.request.assert_called_once_with('POST', '/fapi/v1/leverage', {'symbol':'BTCUSDT','leverage':20})

    def test_timeout_does_not_retry_or_assume_success(self):
        self.x.request.side_effect = ExchangeError('timeout')
        with self.assertRaises(ExchangeError): verify_leverage(self.x, 'BTCUSDT', 20, apply=True)
        self.assertEqual(self.x.request.call_count, 1)

    def test_unsupported_leverage_is_refused_without_mutation(self):
        with self.assertRaises(ValueError): verify_leverage(self.x, 'BTCUSDT', 100, apply=True)
        self.x.request.assert_not_called()
