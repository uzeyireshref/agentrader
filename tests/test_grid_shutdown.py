import tempfile
import unittest
from pathlib import Path

from agentrader.grid_shutdown import GridShutdown
from agentrader.order_journal import OrderJournal
from agentrader.state import StateStore


class GridShutdownTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = StateStore(Path(self.temp.name) / 'state.db')
        self.journal = OrderJournal(self.store)
        self.journal.register('buy', 'grid', 'BTCUSDT', 'BUY', '.004')
        self.stop = GridShutdown(self.store, self.journal, 'grid', 'BTCUSDT')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def cleanup(self, position='0', ids=(), fresh=True, owned=True):
        return self.stop.cleanup(account_position=position, open_client_ids=ids,
                                 snapshot_fresh=fresh, ownership_verified=owned)

    def fill(self, cid, event, status, quantity, at):
        return self.journal.observe(cid, event, status=status,
                                    cumulative_filled=quantity, observed_ms=at)

    def test_stop_barrier_persists_and_cannot_reopen(self):
        self.stop.assert_entry_allowed()
        self.stop.stop('mark crossed stop')
        resumed = GridShutdown(self.store, self.journal, 'grid', 'BTCUSDT')
        with self.assertRaises(ValueError):
            resumed.assert_entry_allowed()
        self.assertEqual(resumed.stop('second stop'), 'STOPPING')

    def test_unknown_submission_must_be_resolved_even_if_open_list_empty(self):
        self.stop.stop('stop')
        result = self.cleanup()
        self.assertEqual(result['blocked'], 'WAIT_FOR_TERMINAL_ORDERS')
        self.assertEqual(result['actions'][0]['client_id'], 'buy')

    def test_cancel_fill_race_closes_actual_residual_only_after_cancel(self):
        self.stop.stop('stop')
        self.fill('buy', 'cancel', 'CANCELED', '.001', 20)
        self.fill('buy', 'late', 'PARTIALLY_FILLED', '.002', 19)
        action = self.cleanup('.002')['actions'][0]
        self.assertEqual(action, {'kind': 'REDUCE_ONLY_CLOSE', 'side': 'SELL', 'quantity': '0.002'})
        self.journal.register('exit', 'grid', 'BTCUSDT', 'SELL', '.002')
        self.assertEqual(self.cleanup('.002')['blocked'], 'WAIT_FOR_TERMINAL_ORDERS')
        self.fill('exit', 'filled', 'FILLED', '.002', 30)
        self.assertEqual(self.cleanup()['phase'], 'CLOSED')
        with self.assertRaises(ValueError):
            self.stop.assert_entry_allowed()

    def test_reduction_orders_also_cancel_before_market_close(self):
        self.fill('buy', 'fill', 'FILLED', '.004', 10)
        self.journal.register('target', 'grid', 'BTCUSDT', 'SELL', '.004')
        self.stop.stop('stop')
        self.assertEqual(self.cleanup('.004', ['target'])['blocked'], 'WAIT_FOR_TERMINAL_ORDERS')

    def test_foreign_inventory_stale_data_and_unowned_orders_block_cleanup(self):
        self.stop.stop('stop')
        self.fill('buy', 'c', 'CANCELED', '0', 10)
        self.assertEqual(self.cleanup(fresh=False)['blocked'], 'FRESH_OWNED_SNAPSHOT_REQUIRED')
        self.assertEqual(self.cleanup(owned=False)['blocked'], 'FRESH_OWNED_SNAPSHOT_REQUIRED')
        self.assertEqual(self.cleanup(ids=['manual'])['blocked'], 'FOREIGN_OPEN_ORDER')
        self.assertEqual(self.cleanup('.001')['blocked'], 'INVENTORY_POSITION_MISMATCH')

    def test_empty_flat_confirmed_account_can_finish(self):
        self.stop.stop('stop')
        self.fill('buy', 'c', 'CANCELED', '0', 10)
        self.assertEqual(self.cleanup()['phase'], 'CLOSED')
        self.assertFalse(self.cleanup()['execution_authorized'])
