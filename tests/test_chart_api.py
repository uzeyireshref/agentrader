import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from agentrader.application.settings import WebSettings
from agentrader.chart_market import MarketUnavailable, InvalidMarket
from agentrader.market_feed import FeedState
from test_chart_feed import START, event

HAS_WEB = all(importlib.util.find_spec(m) is not None for m in ('fastapi', 'httpx'))
if HAS_WEB:
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
    from agentrader.api.app import create_app


@unittest.skipUnless(HAS_WEB, 'Optional web dependencies')
class ChartAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        self.settings = WebSettings(folder/'app.db', folder/'execution.db', market_database=folder/'chart.db')
        self.market = Mock()
        self.market.catalog.return_value = {'markets': [{'symbol': 'BTCUSDT'}]}
        self.market.history.return_value = {'candles': [], 'source': 'binance_usdm_live_trade_price'}
        self.state = FeedState('BTCUSDT', '15m')
        self.hub = Mock()
        self.hub.acquire.return_value = SimpleNamespace(state=self.state)
        self.client = self.enterContext(TestClient(create_app(self.settings, market=self.market, hub=self.hub), base_url='http://127.0.0.1'))

    def test_public_history_and_markets_do_not_require_trading_credentials(self):
        self.assertEqual(self.client.get('/api/markets').status_code, 200)
        self.assertEqual(self.client.get('/api/candles?symbol=BTCUSDT&interval=15m').status_code, 200)
        self.assertFalse(self.settings.execution_database.exists())

    def test_invalid_request_limits_are_rejected_before_market_call(self):
        self.assertEqual(self.client.get('/api/candles?limit=999999').status_code, 422)
        self.market.history.assert_not_called()

    def test_market_failure_is_explicit_and_sanitized(self):
        self.market.catalog.side_effect = MarketUnavailable('private-details')
        response = self.client.get('/api/markets')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private-details', response.text)

    def test_foreign_or_missing_websocket_origin_cannot_acquire_feed(self):
        for headers in [{}, {'origin': 'http://foreign.invalid'}]:
            with self.assertRaises(WebSocketDisconnect):
                with self.client.websocket_connect('ws://127.0.0.1/api/market-stream?symbol=BTCUSDT&interval=15m', headers=headers):
                    pass
        self.hub.acquire.assert_not_called()

    def test_websocket_snapshot_update_and_disconnect_release(self):
        self.state.seed({'candles': [{'time': START//1000, 'open': 100., 'high': 110., 'low': 90., 'close': 105.,
                                     'volume': 10., 'quote_volume': 1050., 'closed': False, 'close_time': START+899999}],
                         'server_time': START+2000, 'quality': {'state': 'OK', 'missing_bars': 0}, 'market': {}})
        with self.client.websocket_connect('ws://127.0.0.1/api/market-stream?symbol=BTCUSDT&interval=15m',
                                           headers={'origin': 'http://127.0.0.1'}) as ws:
            first = ws.receive_json()
            self.assertEqual(first['type'], 'snapshot')
            self.state.apply(event())
            second = ws.receive_json()
            self.assertEqual(second['type'], 'update')
            self.assertEqual(second['status'], 'LIVE')
        self.hub.release.assert_called_once()

    def test_invalid_subscription_returns_error_and_does_not_leak_parameters(self):
        self.hub.acquire.side_effect = InvalidMarket('private-details')
        with self.client.websocket_connect('ws://127.0.0.1/api/market-stream?symbol=BAD&interval=bad',
                                           headers={'origin': 'http://127.0.0.1'}) as ws:
            response = ws.receive_json()
            self.assertEqual(response['code'], 'MARKET_UNAVAILABLE')
            self.assertNotIn('private-details', str(response))
