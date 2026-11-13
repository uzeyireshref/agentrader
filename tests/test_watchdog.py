import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from agentrader.config import Config
from agentrader.exchange import ExchangeError
from agentrader.state import StateStore
from agentrader.watchdog import Watchdog, OwnershipError, watch_loop
from test_positions import PositionExchange


class WatchExchange(PositionExchange):
    def __init__(self):
        super().__init__()
        self.trades = []
        self.reject_stop = False
        self.disconnect = False
        self.drop_protection_response = False

    def get(self, path, params=None):
        if self.disconnect:
            raise ExchangeError('Disconnected')
        if path.endswith('/time'):
            return {'serverTime': int(time.time() * 1000)}
        if path.endswith('income'):
            return []
        if path.endswith('userTrades'):
            return [dict(row, symbol=params['symbol'], id=i+1, time=params['endTime']) for i,row in enumerate(self.trades) if float(row['qty']) > 0]
        if path.endswith('algoOrder') and params['clientAlgoId'] not in self.algos:
            raise ExchangeError('Not found', -2013)
        if path.endswith('positionRisk'):
            return [{'symbol': 'BTCUSDT', 'positionAmt': str(self.qty)}]
        if path.endswith('/order'):
            cid = params['origClientOrderId']
            if cid not in self.orders:
                raise ExchangeError('Not found', -2013)
        return super().get(path, params)

    def request(self, method, path, params):
        if method == 'DELETE' and path.endswith('/order'):
            self.calls.append((method, path, params))
            self.orders[params['origClientOrderId']]['status'] = 'CANCELED'
            return self.orders[params['origClientOrderId']]
        if path.endswith('algoOrder') and method == 'POST' and self.reject_stop:
            raise ExchangeError('Invalid trigger', -2021)
        result = super().request(method, path, params)
        if path.endswith('/order') and method == 'POST':
            result['orderId'] = len(self.orders) + 100
            self.trades.append({'orderId': result['orderId'], 'qty': params['quantity'], 'side': params['side']})
        if path.endswith('algoOrder') and method == 'POST':
            result['algoId'] = len(self.algos) + 1000
            if self.drop_protection_response:
                self.drop_protection_response = False
                raise ExchangeError('Protection accepted but response lost')
        return result


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.path = Path(self.folder.name) / 'state.sqlite3'
        self.store = StateStore(self.path)
        self.x = WatchExchange()
        self.watch = Watchdog(self.x, self.store)

    def tearDown(self):
        self.store.close()
        self.folder.cleanup()

    def test_restart_adopts_protected_position_without_new_order(self):
        self.assertEqual(self.watch.open('BTCUSDT')['status'], 'protected')
        count = len(self.x.calls)
        self.store.close()
        self.store = StateStore(self.path)
        restarted = Watchdog(self.x, self.store)
        self.assertEqual(restarted.tick(True)['status'], 'protected')
        self.assertEqual(len(self.x.calls), count)
        restarted.tick(True, close=True)
        self.assertEqual(self.x.qty, 0)
        self.assertEqual(self.store.sessions(), [])

    def test_readonly_finalize_refuses_open_position_without_mutation(self):
        self.watch.open('BTCUSDT')
        count = len(self.x.calls)
        with self.assertRaises(ValueError):
            self.watch.finalize_flat()
        self.assertEqual(len(self.x.calls), count)
        self.assertTrue(self.store.sessions())

    def test_readonly_finalize_recovers_crash_after_exchange_close(self):
        self.watch.open('BTCUSDT')
        original = self.watch.save
        def crash_before_closed_save(session):
            if not session['active']:
                raise SystemExit('crash before closed session save')
            original(session)
        with patch.object(self.watch, 'save', side_effect=crash_before_closed_save):
            with self.assertRaises(SystemExit):
                self.watch.tick(True, close=True)
        self.assertEqual(self.x.qty, 0)
        count = len(self.x.calls)
        result = self.watch.finalize_flat()
        self.assertEqual(result['exchange_mutations'], 0)
        self.assertEqual(len(self.x.calls), count)
        self.assertEqual(self.store.sessions(), [])

    def test_canceled_stop_repaired_once_and_remaining_position_covered(self):
        self.watch.open('BTCUSDT')
        s = self.store.sessions()[0]
        stop = s['protections'][0]['clientAlgoId']
        self.x.algos[stop]['algoStatus'] = 'CANCELED'
        self.watch.tick(True)
        self.watch.tick(True)
        stops = [a for a in self.x.algos.values() if a['type'] == 'STOP_MARKET']
        self.assertEqual(len(stops), 2)
        self.assertEqual(sum(a['algoStatus'] == 'NEW' for a in stops), 1)

    def test_repair_failure_closes_owned_position(self):
        self.watch.open('BTCUSDT')
        stop = self.store.sessions()[0]['protections'][0]['clientAlgoId']
        self.x.algos[stop]['algoStatus'] = 'CANCELED'
        self.x.reject_stop = True
        result = self.watch.tick(True)
        self.assertEqual(result['status'], 'closed')
        self.assertEqual(self.x.qty, 0)
        self.assertIsNotNone(self.store.halt_reason())

    def test_manual_trade_same_net_quantity_is_not_adopted(self):
        self.watch.open('BTCUSDT')
        self.x.trades.extend([{'orderId': 999, 'side': 'SELL', 'qty': '.0001'},
                              {'orderId': 998, 'side': 'BUY', 'qty': '.0001'}])
        count = len(self.x.calls)
        with self.assertRaises(OwnershipError):
            self.watch.tick(True)
        self.assertEqual(len(self.x.calls), count)
        self.assertNotEqual(self.x.qty, 0)

    def test_disconnect_preserves_protection_and_halts_entries(self):
        self.watch.open('BTCUSDT')
        count = len(self.x.calls)
        self.x.disconnect = True
        with self.assertRaises(ExchangeError):
            self.watch.tick(True)
        self.assertEqual(len(self.x.calls), count)
        self.assertTrue(all(a['algoStatus'] == 'NEW' for a in self.x.algos.values()))
        self.assertIsNotNone(self.store.halt_reason())

    def test_readonly_does_not_repair_or_close(self):
        self.watch.open('BTCUSDT')
        self.x.algos[self.store.sessions()[0]['protections'][0]['clientAlgoId']]['algoStatus'] = 'CANCELED'
        count = len(self.x.calls)
        self.assertEqual(self.watch.tick(False)['status'], 'observed')
        self.assertEqual(len(self.x.calls), count)

    def test_loop_checks_each_iteration(self):
        self.watch.open('BTCUSDT')
        with patch('agentrader.watchdog.time.sleep') as sleep:
            result = list(watch_loop(self.watch, True, iterations=3, interval=1))
        self.assertEqual(len(result), 3)
        self.assertEqual(sleep.call_count, 2)

    def test_loop_retries_after_network_error(self):
        self.watch.open('BTCUSDT')
        original = self.watch.tick
        calls = []
        def tick(**kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise ExchangeError('Temporary network failure')
            return original(**kwargs)
        with patch.object(self.watch, 'tick', side_effect=tick), patch('agentrader.watchdog.time.sleep'):
            result = list(watch_loop(self.watch, True, iterations=2, interval=1))
        self.assertEqual([r['status'] for r in result], ['alarm', 'protected'])

    def test_partial_entry_cancels_remainder_and_protects_actual_position(self):
        self.watch.open('BTCUSDT')
        s = self.store.sessions()[0]
        self.x.qty = Decimal('.0004')
        self.x.trades[0]['qty'] = '.0004'
        self.x.orders[s['entry_id']]['status'] = 'PARTIALLY_FILLED'
        result = self.watch.tick(True)
        self.assertEqual(result['position'], '0.0004')
        self.assertEqual(self.x.orders[s['entry_id']]['status'], 'CANCELED')
        self.assertTrue(all(a['closePosition'] == 'true' for a in self.x.algos.values()))

    def test_unknown_position_quantity_is_not_closed(self):
        self.watch.open('BTCUSDT')
        self.x.qty += Decimal('.0001')
        count = len(self.x.calls)
        with self.assertRaises(OwnershipError):
            self.watch.tick(True, close=True)
        self.assertEqual(len(self.x.calls), count)

    def test_lost_protection_response_is_queried_without_duplicate(self):
        self.x.drop_protection_response = True
        self.assertEqual(self.watch.open('BTCUSDT')['status'], 'protected')
        self.assertEqual(len(self.x.algos), 2)
        self.watch.tick(True)
        self.assertEqual(len(self.x.algos), 2)

    def test_repair_intent_survives_crash_before_submission(self):
        self.watch.open('BTCUSDT')
        s = self.store.sessions()[0]
        previous = dict(s['protections'][0])
        self.x.algos[previous['clientAlgoId']]['algoStatus'] = 'CANCELED'
        pending = dict(previous, clientAlgoId='agt-crash-before-protection-post')
        s['protections'].append(pending)
        self.store.save_session(s)
        self.store.close()
        self.store = StateStore(self.path)
        restarted = Watchdog(self.x, self.store)
        self.assertEqual(restarted.tick(True)['status'], 'protected')
        self.assertIn(pending['clientAlgoId'], self.x.algos)
        self.assertEqual(len(self.x.algos), 3)
