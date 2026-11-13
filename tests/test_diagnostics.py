import hashlib
import hmac
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlsplit

from agentrader.config import Config
from agentrader.exchange import DemoExchange, ExchangeError
from agentrader.__main__ import diagnose


class DiagnosticsTests(unittest.TestCase):
    def test_environment_and_incomplete_credentials_rejected(self):
        for content in ('AGENTRADER_ENV=live', 'BINANCE_DEMO_API_KEY=test'):
            with patch.object(Path, 'exists', return_value=True), \
                 patch.object(Path, 'read_text', return_value=content), \
                 patch.dict('os.environ', {}, clear=True), self.assertRaises(ValueError):
                Config.load()

    def test_signed_request_and_no_secret_in_repr(self):
        config = Config('test-key', 'test-secret')
        client = DemoExchange(config)
        client.opener.open = lambda request, timeout: io.BytesIO(b'{}')
        with patch.object(client.opener, 'open', return_value=io.BytesIO(b'{}')) as opened:
            client.get('/fapi/v3/account')
        request = opened.call_args.args[0]
        query, signature = urlsplit(request.full_url).query.split('&signature=')
        expected = hmac.new(b'test-secret', query.encode(), hashlib.sha256).hexdigest()
        self.assertEqual(signature, expected)
        self.assertEqual(request.method, 'GET')
        self.assertNotIn('test-secret', repr(config))

    def test_order_endpoint_rejected_before_network(self):
        with self.assertRaises(ValueError):
            DemoExchange(Config()).request('POST', '/fapi/v1/withdraw')

    def test_api_error_does_not_echo_sensitive_response(self):
        client = DemoExchange(Config())
        error = HTTPError('https://demo-fapi.binance.com', 401, '', {},
                          io.BytesIO(json.dumps({'code': -2015, 'msg': 'secret-value'}).encode()))
        with patch.object(client.opener, 'open', side_effect=error):
            with self.assertRaises(ExchangeError) as caught:
                client.get('/fapi/v1/ping')
        self.assertIn('-2015', str(caught.exception))
        self.assertNotIn('secret-value', str(caught.exception))

    def test_public_diagnosis_never_reads_account(self):
        called = []
        def fake_get(client, path):
            called.append(path)
            return {'/fapi/v1/ping': {}, '/fapi/v1/time': {'serverTime': 1},
                    '/fapi/v1/exchangeInfo': {'symbols': [{'symbol': 'BTCUSDT'}]}}[path]
        with patch.object(DemoExchange, 'get', fake_get):
            result = diagnose(Config(), 'BTCUSDT')
        self.assertEqual(result['account']['status'], 'skipped')
        self.assertTrue(all(path in {'/fapi/v1/ping', '/fapi/v1/time', '/fapi/v1/exchangeInfo'} for path in called))


if __name__ == '__main__':
    unittest.main()
