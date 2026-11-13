import json
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

from agentrader.config import Config
from agentrader.exchange import DemoExchange, ExchangeError
from agentrader.user_stream import (DemoUserStream, LISTEN_PATH, STREAM_BASE,
                                    StreamProtocolError, StreamUnavailable, normalize_event, _Socket)

KEY = 'private-listen-key-canary-0123456789'


def order_event(**changes):
    order = dict(c='agt-order-1', s='BTCUSDT', i=42, S='BUY', X='PARTIALLY_FILLED',
                 q='0.002', z='0.001')
    order.update(changes)
    return json.dumps(dict(e='ORDER_TRADE_UPDATE', E=100, T=99, o=order))


class Clock:
    def __init__(self): self.value = 0
    def __call__(self): return self.value


class Socket:
    def __init__(self, clock, messages=()):
        self.clock, self.messages, self.closed = clock, list(messages), False

    def receive(self, timeout):
        if self.messages:
            result = self.messages.pop(0)
            if isinstance(result, Exception): raise result
            return result
        self.clock.value += timeout
        return None

    def close(self): self.closed = True


class UserStreamTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.exchange = Mock()
        self.exchange.request.return_value = {'listenKey': KEY}
        self.socket = Socket(self.clock)
        self.factory = Mock(return_value=self.socket)
        self.stream = DemoUserStream(self.exchange, socket_factory=self.factory, clock=self.clock)

    def test_listen_requests_are_apikey_only_and_have_no_query_or_signature(self):
        exchange = DemoExchange(Config('api-canary', 'secret-canary'))
        for method in ('POST', 'PUT', 'DELETE'):
            request = exchange._signed_request(method, LISTEN_PATH, None)
            self.assertEqual(request.get_header('X-mbx-apikey'), 'api-canary')
            self.assertEqual(urlsplit(request.full_url).query, '')
            self.assertNotIn('secret-canary', repr(request.header_items()))
        with self.assertRaises(ValueError):
            exchange.request('POST', LISTEN_PATH, {'listenKey': KEY})

    def test_normal_signed_orders_still_require_hmac(self):
        exchange = DemoExchange(Config('api-canary', 'secret-canary'))
        request = exchange._signed_request('GET', '/fapi/v1/order', {'symbol': 'BTCUSDT'})
        self.assertIn('signature=', request.full_url)
        self.assertIn('timestamp=', request.full_url)

    def test_connect_and_close_never_delete_shared_account_key_or_return_it(self):
        info = self.stream.connect()
        self.assertEqual(info['generation'], 1)
        self.factory.assert_called_once_with(STREAM_BASE+KEY)
        self.assertNotIn(KEY, json.dumps(info))
        self.stream.close()
        self.assertTrue(self.socket.closed)
        self.assertIsNone(self.stream._key)
        self.exchange.request.assert_called_once_with('POST', LISTEN_PATH)

    def test_handshake_failure_is_redacted_and_key_not_retained(self):
        self.factory.side_effect = RuntimeError(STREAM_BASE+KEY)
        with self.assertRaises(StreamUnavailable) as caught: self.stream.connect()
        self.assertNotIn(KEY, str(caught.exception))
        self.assertIsNone(self.stream._key)

    def test_start_failure_is_redacted_and_not_retried_here(self):
        self.exchange.request.side_effect = ExchangeError(KEY)
        with self.assertRaises(StreamUnavailable) as caught: self.stream.connect()
        self.assertNotIn(KEY, str(caught.exception))
        self.assertEqual(self.exchange.request.call_count, 1)
        self.factory.assert_not_called()

    def test_keepalive_after_30_minutes_and_23_hour_rotation(self):
        self.stream.connect()
        self.clock.value = 1799
        self.stream.maintain()
        self.assertEqual(self.exchange.request.call_count, 1)
        self.clock.value = 1800
        self.stream.maintain()
        self.exchange.request.assert_called_with('PUT', LISTEN_PATH)
        self.clock.value = 23*3600
        with self.assertRaises(StreamUnavailable): self.stream.maintain()
        self.assertTrue(self.socket.closed)

    def test_keepalive_failure_or_key_change_disconnects(self):
        for response in (ExchangeError('hidden'), {'listenKey': 'different'}):
            self.setUp(); self.stream.connect(); self.clock.value = 1800
            if isinstance(response, Exception): self.exchange.request.side_effect = response
            else: self.exchange.request.return_value = response
            with self.assertRaises(StreamUnavailable): self.stream.maintain()
            self.assertTrue(self.socket.closed)

    def test_duplicate_delivery_does_not_wake_or_double_count(self):
        self.stream.connect()
        event = order_event()
        self.socket.messages = [event, event]
        result = self.stream.wait(5)
        self.assertEqual(result['cumulative_filled'], '0.001')
        self.assertIsNone(self.stream.wait(5))

    def test_same_time_account_changes_have_distinct_identity(self):
        a = normalize_event(json.dumps(dict(e='ACCOUNT_UPDATE', E=1, T=1, a={'B': [1]})))
        b = normalize_event(json.dumps(dict(e='ACCOUNT_UPDATE', E=1, T=1, a={'B': [2]})))
        self.assertNotEqual(a['event_id'], b['event_id'])
        self.assertNotIn('B', a)

    def test_event_normalization_and_status_mapping(self):
        event = normalize_event(order_event(X='EXPIRED_IN_MATCH'))
        self.assertEqual(event['status'], 'EXPIRED')
        self.assertEqual(event['order_id'], 42)
        self.assertEqual(event['client_id'], 'agt-order-1')

    def test_invalid_event_cannot_change_projection(self):
        for change in ({'z': 'NaN'}, {'z': '1'}, {'q': '0'}, {'i': True},
                       {'S': 'OTHER'}, {'X': 'FILLED'}, {'c': 'bad\nkey'}):
            with self.subTest(change=change), self.assertRaises(StreamProtocolError):
                normalize_event(order_event(**change))

    def test_expired_key_and_malformed_frames_are_not_logged(self):
        with self.assertRaises(StreamUnavailable) as caught:
            normalize_event(json.dumps(dict(e='listenKeyExpired', E=1, listenKey=KEY)))
        self.assertNotIn(KEY, str(caught.exception))
        for raw in ('[]', '{', 'x'*65537, b'\xff'):
            with self.subTest(raw=str(raw)[:10]), self.assertRaises(StreamProtocolError):
                normalize_event(raw)

    def test_algo_and_unknown_events_wake_rest_without_inventing_inventory(self):
        algo=dict(caid='agt-stop',aid=71,s='BTCUSDT',S='SELL',X='TRIGGERED',ai='42',aq='0.001',rm=KEY)
        for kind, fields in [('ALGO_UPDATE', {'o': algo}), ('NEW_EVENT', {'secret': KEY})]:
            event = normalize_event(json.dumps(dict(e=kind, E=1, **fields)))
            self.assertNotIn(KEY, json.dumps(event))
            self.assertNotIn('cumulative_filled', event)

    def test_idle_preserves_periodic_rest_schedule(self):
        self.stream.connect()
        self.assertIsNone(self.stream.wait(5))
        self.assertEqual(self.clock.value, 5)

    def test_algo_identity_child_and_fill_are_normalized(self):
        event=normalize_event(json.dumps(dict(e='ALGO_UPDATE',E=1,T=1,
            o=dict(caid='agt-stop',aid=7,s='BTCUSDT',S='SELL',X='FINISHED',ai='42',aq='.002'))))
        self.assertEqual(event['actual_order_id'],42)
        self.assertEqual(event['actual_filled'],'0.002')
        self.assertEqual(event['algo_status'],'FINISHED')
        self.assertEqual(event['client_algo_id'],'agt-stop')

    def test_malformed_algo_is_not_a_rest_hint(self):
        for change in ({'aq':'NaN'},{'aid':True},{'ai':'wrong'},{'X':'UNKNOWN'}):
            body=dict(caid='agt-stop',aid=7,s='BTCUSDT',S='SELL',X='NEW',ai='',aq='0')
            body.update(change)
            with self.subTest(change=change),self.assertRaises(StreamProtocolError):
                normalize_event(json.dumps(dict(e='ALGO_UPDATE',E=1,o=body)))

    def test_duplicate_flood_is_bounded(self):
        self.stream.connect()
        self.socket.messages = [order_event()]*300
        self.stream.wait(5)
        with self.assertRaises(StreamProtocolError): self.stream.wait(5)
        self.assertTrue(self.socket.closed)


class SocketBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.connection = Mock()
        self.connection.getstatus.return_value = 101
        self.connection.recv_data.return_value = (10, b'agentrader')

    def connect(self):
        with patch('websocket.create_connection', return_value=self.connection) as factory:
            result = _Socket(STREAM_BASE+KEY)
            factory.assert_called_once_with(STREAM_BASE+KEY, timeout=10, redirect_limit=0)
            return result

    def test_heartbeat_pong_is_required_and_not_treated_as_event(self):
        with patch('agentrader.user_stream.time.monotonic', side_effect=[0, 30]):
            socket = self.connect()
            self.assertIsNone(socket.receive(1))
        self.connection.ping.assert_called_once_with(b'agentrader')
        self.assertFalse(socket.awaiting_pong)

    def test_silent_connection_is_detected_after_ping_deadline(self):
        import websocket
        self.connection.recv_data.side_effect = websocket.WebSocketTimeoutException()
        with patch('agentrader.user_stream.time.monotonic', side_effect=[0, 30, 41]):
            socket = self.connect()
            self.assertIsNone(socket.receive(1))
            with self.assertRaises(StreamUnavailable): socket.receive(1)

    def test_closed_socket_is_not_idle_and_errors_hide_private_url(self):
        for response in ((8, b''), RuntimeError(STREAM_BASE+KEY)):
            socket = self.connect()
            if isinstance(response, Exception): self.connection.recv_data.side_effect = response
            else: self.connection.recv_data.return_value = response
            with self.assertRaises(StreamUnavailable) as caught: socket.receive(1)
            self.assertNotIn(KEY, str(caught.exception))

    def test_http_redirect_is_not_a_successful_websocket(self):
        self.connection.getstatus.return_value = 302
        with self.assertRaises(StreamUnavailable): self.connect()
        self.connection.close.assert_called_once()


if __name__ == '__main__': unittest.main()
