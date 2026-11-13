from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from agentrader.chart_market import ChartMarket, MarketUnavailable


class ChartHistoryBoundaryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.client = Mock()
        self.market = ChartMarket(Path(temp.name)/'chart.db', client_factory=lambda: self.client)
        self.market.selection = Mock(return_value={'symbol': 'GRAMUSDT'})

    def answer(self, klines):
        self.client.get.side_effect = lambda path, params=None: {'serverTime': 1800000000000} if path.endswith('/time') else klines

    def test_valid_empty_older_page_is_terminal_and_cacheable(self):
        self.answer([])
        result = self.market.history('GRAMUSDT', '1w', end_time=1782691199999)
        self.assertEqual(result['candles'], [])
        self.assertEqual(result['quality']['state'], 'EMPTY')
        self.assertFalse(result['has_more'])
        self.assertIsNone(result['next_end_time'])
        calls = self.client.get.call_count
        self.assertEqual(self.market.history('GRAMUSDT', '1w', end_time=1782691199999), result)
        self.assertEqual(self.client.get.call_count, calls)

    def test_empty_initial_snapshot_is_still_an_error(self):
        self.answer([])
        with self.assertRaises(MarketUnavailable):
            self.market.history('GRAMUSDT', '1w')

    def test_malformed_older_page_is_not_treated_as_history_boundary(self):
        for data in [None, {}, {'code': -1}, [['invalid']]]:
            self.answer(data)
            with self.assertRaises(MarketUnavailable):
                self.market.history('GRAMUSDT', '1w', end_time=1782691199999, force=True)

    def test_failed_request_is_not_treated_as_history_boundary(self):
        self.client.get.side_effect = OSError('offline')
        with self.assertRaises(MarketUnavailable):
            self.market.history('GRAMUSDT', '1w', end_time=1782691199999)
