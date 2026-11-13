import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from agentrader.exchange import ExchangeError
from agentrader.execution import DurableExchange, resolve_absent_flat
from agentrader.state import StateStore


class MissingProtectionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.store = StateStore(Path(self.folder.name) / 'state.sqlite3')
        self.params = {'clientAlgoId': 'missing', 'symbol': 'BTCUSDT', 'type': 'STOP_MARKET'}
        self.store.reserve('missing', '/fapi/v1/algoOrder', self.params)
        self.store.update('missing', 'UNKNOWN')
        self.row = self.store.intents()[0]
        self.x = Mock()
        self.x.get.side_effect = lambda path: []

    def tearDown(self):
        self.store.close()
        self.folder.cleanup()

    def test_flat_missing_order_can_finish_without_resending(self):
        result = resolve_absent_flat(self.x, self.store, self.row, ExchangeError('missing', -2013))
        self.assertEqual(result['resolution'], 'RESOLVED_FLAT')
        self.assertEqual(self.store.intents()[0]['state'], 'RESOLVED_FLAT')
        self.x.request.assert_not_called()

    def test_open_position_or_any_open_order_preserves_unknown(self):
        for blocked_path, value in [('/fapi/v3/positionRisk', [{'positionAmt': '.0004'}]),
                                    ('/fapi/v1/openOrders', [{}]), ('/fapi/v1/openAlgoOrders', [{}])]:
            with self.subTest(path=blocked_path):
                self.x.get.side_effect = lambda path: value if path == blocked_path else []
                with self.assertRaises(ExchangeError):
                    resolve_absent_flat(self.x, self.store, self.row, ExchangeError('missing', -2013))
                self.assertEqual(self.store.intents()[0]['state'], 'UNKNOWN')

    def test_network_failure_does_not_resolve_missing_order(self):
        self.x.get.side_effect = ExchangeError('offline')
        with self.assertRaises(ExchangeError):
            resolve_absent_flat(self.x, self.store, self.row, ExchangeError('missing', -2013))
        self.assertEqual(self.store.intents()[0]['state'], 'UNKNOWN')

    def test_definitive_reject_keeps_original_error_code(self):
        params = dict(self.params, clientAlgoId='reject')
        self.x.request.side_effect = ExchangeError('duplicate close-all', -4130, 400)
        with self.assertRaises(ExchangeError):
            DurableExchange(self.x, self.store).request('POST', '/fapi/v1/algoOrder', params)
        row = self.store.intents()[-1]
        self.assertEqual(row['state'], 'REJECTED')
        self.assertEqual(json.loads(row['response'])['error']['code'], -4130)
