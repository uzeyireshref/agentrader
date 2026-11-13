import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from agentrader.order_journal import OrderJournal
from agentrader.state import StateStore


class OrderJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'state.sqlite3'
        self.store = StateStore(self.path)
        self.journal = OrderJournal(self.store)
        self.journal.register('buy-1', 'grid', 'BTCUSDT', 'BUY', '.004')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def observe(self, event, status, fill, at):
        return self.journal.observe('buy-1', event, status=status,
                                    cumulative_filled=fill, observed_ms=at)

    def test_partial_fill_duplicate_does_not_double_inventory(self):
        self.observe('a', 'PARTIALLY_FILLED', '.001', 10)
        self.assertTrue(self.observe('a', 'PARTIALLY_FILLED', '.001', 10)['duplicate'])
        self.assertEqual(self.journal.inventory('grid', 'BTCUSDT'), Decimal('.001'))

    def test_cancel_race_records_late_fill_without_reopening(self):
        self.observe('cancel', 'CANCELED', '.001', 20)
        result = self.observe('late', 'PARTIALLY_FILLED', '.002', 19)
        self.assertEqual(result['status'], 'CANCELED')
        self.assertEqual(Decimal(result['fill_delta']), Decimal('.001'))
        self.assertEqual(self.journal.unresolved('grid'), [])
        self.assertEqual(self.journal.inventory('grid', 'BTCUSDT'), Decimal('.002'))

    def test_full_fill_wins_over_cancel_and_old_snapshot(self):
        self.observe('full', 'FILLED', '.004', 30)
        self.observe('old', 'NEW', '0', 10)
        self.assertEqual(self.observe('cancel', 'CANCELED', '.002', 40)['status'], 'FILLED')
        self.assertEqual(self.journal.inventory('grid', 'BTCUSDT'), Decimal('.004'))

    def test_restart_keeps_fills_and_event_identity(self):
        self.observe('a', 'PARTIALLY_FILLED', '.001', 10)
        self.store.close()
        self.store = StateStore(self.path)
        self.journal = OrderJournal(self.store)
        self.assertTrue(self.observe('a', 'PARTIALLY_FILLED', '.001', 10)['duplicate'])
        self.assertEqual(Decimal(self.observe('b', 'FILLED', '.004', 20)['fill_delta']), Decimal('.003'))

    def test_conflicting_replay_is_rejected_atomically(self):
        self.observe('a', 'PARTIALLY_FILLED', '.001', 10)
        with self.assertRaises(ValueError):
            self.observe('a', 'PARTIALLY_FILLED', '.002', 10)
        self.assertEqual(self.journal.inventory('grid', 'BTCUSDT'), Decimal('.001'))

    def test_foreign_orders_and_identity_reuse_rejected(self):
        with self.assertRaises(ValueError):
            self.journal.register('buy-1', 'other', 'BTCUSDT', 'BUY', '.004')
        with self.assertRaises(ValueError):
            self.journal.observe('foreign', 'a', status='FILLED', cumulative_filled='1', observed_ms=1)

    def test_invalid_fill_does_not_consume_event_identity(self):
        with self.assertRaises(ValueError):
            self.observe('a', 'FILLED', '.005', 1)
        self.observe('a', 'FILLED', '.004', 1)
        self.assertEqual(self.journal.inventory('grid', 'BTCUSDT'), Decimal('.004'))

    def test_reduce_side_and_separate_symbol_inventory(self):
        self.observe('a', 'FILLED', '.004', 1)
        self.journal.register('sell-1', 'grid', 'BTCUSDT', 'SELL', '.001')
        self.journal.observe('sell-1', 'a', status='FILLED', cumulative_filled='.001', observed_ms=2)
        self.assertEqual(self.journal.inventory('grid', 'BTCUSDT'), Decimal('.003'))
        self.assertEqual(self.journal.inventory('other', 'BTCUSDT'), 0)

    def test_terminal_rejection_releases_unknown_order(self):
        self.assertEqual(len(self.journal.unresolved('grid')), 1)
        self.observe('a', 'REJECTED', '0', 1)
        self.assertEqual(self.journal.unresolved('grid'), [])
