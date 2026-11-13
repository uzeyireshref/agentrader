import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from urllib.error import HTTPError,URLError
from urllib.request import Request

from agentrader.config import Config
from agentrader.exchange import DemoExchange,ExchangeError
from agentrader.transport import JsonTransport,RequestGovernor,retry_after_seconds,rate_headers


def http(status,code=-1000,message='secret-canary',headers=None):
    return HTTPError('https://demo-fapi.binance.com/secret-signed-url',status,'',headers or {},
                     io.BytesIO(json.dumps({'code':code,'msg':message}).encode()))


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.governor=Mock()
        self.governor.record.return_value=None
        self.sleep=Mock()
        self.transport=JsonTransport(self.governor,sleep=self.sleep)
        self.opener=Mock()
        self.factory=lambda:Request('https://demo-fapi.binance.com/fapi/v1/ping')

    def call(self,method='GET'):
        return self.transport.perform(self.opener,self.factory,method,'https://demo-fapi.binance.com')

    def test_get_retries_transient_network_failure_with_bound(self):
        self.opener.open.side_effect=[URLError('secret'),io.BytesIO(b'{}')]
        self.assertEqual(self.call(),{})
        self.assertEqual(self.opener.open.call_count,2)
        self.sleep.assert_called_once_with(.25)

    def test_mutations_never_retry_timeout(self):
        for method in ('POST','PUT','DELETE'):
            with self.subTest(method=method):
                self.opener.open.reset_mock();self.opener.open.side_effect=TimeoutError('secret')
                with self.assertRaises(ExchangeError) as caught:self.call(method)
                self.assertEqual(self.opener.open.call_count,1)
                self.assertEqual(caught.exception.delivery_status,'UNKNOWN')
                self.assertNotIn('secret',str(caught.exception))

    def test_read_retry_is_bounded(self):
        self.opener.open.side_effect=URLError('offline')
        with self.assertRaises(ExchangeError):self.call()
        self.assertEqual(self.opener.open.call_count,2)

    def test_http_503_variants_preserve_uncertainty(self):
        for message,expected in [('Unknown error, please check your request or try again later.','UNKNOWN'),
                                  ('Service Unavailable.','REJECTED'),('unrecognized','UNKNOWN')]:
            with self.subTest(message=message):
                self.opener.open.reset_mock();self.opener.open.side_effect=http(503,message=message)
                with self.assertRaises(ExchangeError) as caught:self.call('POST')
                self.assertEqual(caught.exception.delivery_status,expected)
                self.assertEqual(self.opener.open.call_count,1)
                self.assertNotIn('signed-url',str(caught.exception))

    def test_http_400_timeout_code_is_still_unknown(self):
        self.opener.open.side_effect=http(400,-1007)
        with self.assertRaises(ExchangeError) as caught:self.call('POST')
        self.assertEqual(caught.exception.delivery_status,'UNKNOWN')

    def test_definitive_order_rejection_preserves_code_without_body(self):
        self.opener.open.side_effect=http(400,-2019)
        with self.assertRaises(ExchangeError) as caught:self.call('POST')
        self.assertEqual(caught.exception.delivery_status,'REJECTED')
        self.assertEqual(caught.exception.code,-2019)
        self.assertNotIn('secret-canary',str(caught.exception))

    def test_rate_limit_does_not_retry(self):
        self.opener.open.side_effect=http(429,headers={'Retry-After':'30'})
        self.governor.record.return_value=30
        with self.assertRaises(ExchangeError) as caught:self.call()
        self.assertEqual(self.opener.open.call_count,1)
        self.assertEqual(caught.exception.retry_after,30)
        self.sleep.assert_not_called()

    def test_invalid_json_mutation_is_unknown(self):
        self.opener.open.return_value=io.BytesIO(b'<html>secret</html>')
        with self.assertRaises(ExchangeError) as caught:self.call('POST')
        self.assertEqual(caught.exception.delivery_status,'UNKNOWN')
        self.assertEqual(self.opener.open.call_count,1)

    def test_http_success_with_error_payload_is_not_success(self):
        self.opener.open.return_value=io.BytesIO(b'{"code":-1007,"msg":"secret-canary"}')
        with self.assertRaises(ExchangeError) as caught:self.call('POST')
        self.assertEqual(caught.exception.delivery_status,'UNKNOWN')
        self.assertEqual(caught.exception.code,-1007)
        self.assertNotIn('secret-canary',str(caught.exception))
        self.assertEqual(self.opener.open.call_count,1)

    def test_block_before_send_does_not_create_network_request(self):
        self.governor.check.side_effect=ExchangeError('cooldown',delivery_status='NOT_SENT')
        with self.assertRaises(ExchangeError) as caught:self.call('POST')
        self.assertEqual(caught.exception.delivery_status,'NOT_SENT')
        self.opener.open.assert_not_called()

    def test_signed_get_is_rebuilt_on_each_read_attempt(self):
        x=DemoExchange(Config('key','secret'),transport=self.transport)
        x.opener=self.opener
        self.opener.open.side_effect=[URLError('offline'),io.BytesIO(b'{}')]
        with patch('agentrader.exchange.time.time',side_effect=[1,2]):
            x.get('/fapi/v3/account')
        urls=[c.args[0].full_url for c in self.opener.open.call_args_list]
        self.assertIn('timestamp=1000',urls[0]);self.assertIn('timestamp=2000',urls[1])
        self.assertNotEqual(urls[0],urls[1])


class GovernorTests(unittest.TestCase):
    def test_retry_after_numeric_date_invalid_and_safe_headers(self):
        self.assertEqual(retry_after_seconds({'Retry-After':'5'}),5)
        self.assertEqual(retry_after_seconds({'Retry-After':'Thu, 01 Jan 1970 00:02:00 GMT'},100),20)
        self.assertIsNone(retry_after_seconds({'Retry-After':'NaN'}))
        self.assertIsNone(retry_after_seconds({'Retry-After':'secret'}))
        self.assertEqual(rate_headers({'X-MBX-USED-WEIGHT-1M':'45','X-MBX-ORDER-COUNT-10S':'1',
                                      'X-MBX-APIKEY':'secret','X-MBX-USED-WEIGHT':'secret'}),
                         {'x-mbx-used-weight-1m':45,'x-mbx-order-count-10s':1})

    def test_cooldown_survives_new_instance_and_is_host_scoped(self):
        now=[100]
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            path=Path(folder)/'limit.sqlite3';g=RequestGovernor(path,lambda:now[0])
            g.record('demo-fapi.binance.com',{'Retry-After':'20'},429)
            restarted=RequestGovernor(path,lambda:now[0])
            with self.assertRaises(ExchangeError) as caught:restarted.check('demo-fapi.binance.com')
            self.assertEqual(caught.exception.delivery_status,'NOT_SENT')
            restarted.check('fapi.binance.com')
            now[0]=121;restarted.check('demo-fapi.binance.com')

    def test_new_shorter_cooldown_cannot_shorten_existing_ban(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            g=RequestGovernor(Path(folder)/'limit.sqlite3',lambda:100)
            g.record('host',{'Retry-After':'200'},418)
            g.record('host',{'Retry-After':'1'},429)
            with self.assertRaises(ExchangeError) as caught:g.check('host')
            self.assertEqual(caught.exception.retry_after,200)
