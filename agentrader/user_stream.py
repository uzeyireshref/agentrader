"""Demo-only user stream. Events wake REST reconciliation, never place orders.

The listen key stays in memory. Closing our socket deliberately does not DELETE
the account-wide key, which may also be used by another Binance client.
"""
from collections import OrderedDict
import hashlib
import json
import re
import time
from decimal import Decimal, InvalidOperation

from .exchange import ExchangeError


STREAM_BASE = 'wss://demo-fstream.binance.com/private/ws/'
LISTEN_PATH = '/fapi/v1/listenKey'
KINDS = frozenset(('ORDER_TRADE_UPDATE', 'ALGO_UPDATE', 'ACCOUNT_UPDATE',
                  'ACCOUNT_CONFIG_UPDATE', 'TRADE_LITE', 'MARGIN_CALL',
                  'CONDITIONAL_ORDER_TRIGGER_REJECT', 'STRATEGY_UPDATE', 'GRID_UPDATE'))


class StreamUnavailable(OSError):
    """Transport/lifetime failure: reconnect only after a REST barrier."""


class StreamProtocolError(ValueError):
    """Untrusted or unsupported event content: stop, do not retry mutations."""


def _integer(value):
    if type(value) is not int or value < 0:
        raise StreamProtocolError('Kullanıcı akışında geçersiz sayı veya zaman.')
    return value


def _text(value, pattern):
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise StreamProtocolError('Kullanıcı akışında geçersiz emir kimliği.')
    return value


def normalize_event(raw):
    """Return a small allowlisted record; never persist raw account messages."""
    if not isinstance(raw, (str, bytes)) or len(raw) > 65536:
        raise StreamProtocolError('Kullanıcı akışı mesaj boyutu geçersiz.')
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        raise StreamProtocolError('Kullanıcı akışı geçerli JSON değil.') from None
    if not isinstance(body, dict) or not isinstance(body.get('e'), str):
        raise StreamProtocolError('Kullanıcı akışı olay zarfı geçersiz.')
    if body['e'] == 'listenKeyExpired':
        raise StreamUnavailable('Kullanıcı akışı süresi doldu; yeniden uzlaştırma gerekli.')
    kind = body['e'] if body['e'] in KINDS else 'UNKNOWN'
    result = {'kind': kind, 'event_ms': _integer(body.get('E')),
              'transaction_ms': _integer(body.get('T', body.get('E')))}
    if kind == 'ORDER_TRADE_UPDATE':
        order = body.get('o')
        if not isinstance(order, dict):
            raise StreamProtocolError('Kullanıcı akışı emir gövdesi eksik.')
        status = order.get('X')
        if status not in ('NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED',
                          'EXPIRED', 'EXPIRED_IN_MATCH', 'REJECTED'):
            raise StreamProtocolError('Kullanıcı akışı emir durumu desteklenmiyor.')
        if order.get('S') not in ('BUY', 'SELL'):
            raise StreamProtocolError('Kullanıcı akışı emir yönü geçersiz.')
        try:
            quantity = Decimal(str(order['q']))
            filled = Decimal(str(order['z']))
            if (not quantity.is_finite() or not filled.is_finite() or
                    not 0 <= filled <= quantity or quantity <= 0 or
                    (status == 'FILLED' and filled != quantity) or
                    (status == 'REJECTED' and filled != 0)):
                raise ValueError()
        except (KeyError, InvalidOperation, ValueError):
            raise StreamProtocolError('Kullanıcı akışı gerçekleşme miktarı geçersiz.') from None
        result.update(client_id=_text(order.get('c'), r'[.A-Za-z0-9_:/-]{1,64}'),
                      symbol=_text(order.get('s'), r'[A-Z0-9_]{1,32}'),
                      order_id=_integer(order.get('i')), side=order['S'],
                      status='EXPIRED' if status == 'EXPIRED_IN_MATCH' else status,
                      quantity=str(quantity), cumulative_filled=str(filled))
    elif kind == 'ALGO_UPDATE':
        order = body.get('o')
        if not isinstance(order, dict):
            raise StreamProtocolError('Kullanıcı akışı koşullu emir gövdesi eksik.')
        if order.get('X') not in ('NEW', 'TRIGGERING', 'TRIGGERED', 'FINISHED',
                                  'CANCELED', 'EXPIRED', 'REJECTED') or order.get('S') not in ('BUY', 'SELL'):
            raise StreamProtocolError('Kullanıcı akışı koşullu emir durumu/yönü geçersiz.')
        child = order.get('ai')
        if child not in (None, '', '0', 0):
            if not isinstance(child, str) or not re.fullmatch(r'[0-9]{1,20}', child):
                raise StreamProtocolError('Kullanıcı akışı alt emir kimliği geçersiz.')
            child = int(child)
        else:
            child = None
        try:
            filled = Decimal(str(order.get('aq') or '0'))
            if not filled.is_finite() or filled < 0:
                raise ValueError()
        except (InvalidOperation, ValueError):
            raise StreamProtocolError('Kullanıcı akışı koşullu gerçekleşme miktarı geçersiz.') from None
        result.update(client_algo_id=_text(order.get('caid'), r'[.A-Za-z0-9_:/-]{1,64}'),
                      symbol=_text(order.get('s'), r'[A-Z0-9_]{1,32}'),
                      algo_id=_integer(order.get('aid')), side=order['S'],
                      algo_status=order['X'], actual_order_id=child, actual_filled=str(filled))
    elif kind == 'ACCOUNT_UPDATE' and not isinstance(body.get('a'), dict):
        raise StreamProtocolError('Kullanıcı akışı hesap gövdesi eksik.')
    # Hash the full payload to distinguish same-time account/algo changes.
    # Persist only the hash and allowlisted fields, never the raw message.
    result['event_id'] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return result


class _Socket:
    """Library boundary: sanitize handshake/recv errors, keep TLS verification."""
    def __init__(self, url):
        try:
            import websocket
        except ImportError:
            raise StreamProtocolError('WebSocket için pip install -e ".[streams]" gerekli.') from None
        websocket.enableTrace(False)
        self.timeout_error = websocket.WebSocketTimeoutException
        self.last_ping = time.monotonic()
        self.awaiting_pong = False
        try:
            self.connection = websocket.create_connection(url, timeout=10, redirect_limit=0)
            if self.connection.getstatus() != 101:
                self.close()
                raise StreamUnavailable('Demo WebSocket el sıkışması doğrulanamadı.')
        except Exception:
            raise StreamUnavailable('Demo WebSocket bağlantısı kurulamadı.') from None

    def receive(self, timeout):
        try:
            now = time.monotonic()
            if self.awaiting_pong and now-self.last_ping >= 10:
                raise StreamUnavailable('Demo WebSocket kalp atışı yanıtlanmadı.')
            if not self.awaiting_pong and now-self.last_ping >= 30:
                self.connection.ping(b'agentrader')
                self.last_ping, self.awaiting_pong = now, True
            self.connection.settimeout(timeout)
            opcode, value = self.connection.recv_data(control_frame=True)
            if opcode == 10:  # PONG
                if value == b'agentrader':
                    self.awaiting_pong = False
                return None
            if opcode == 9:  # Library automatically replies PONG to server PING.
                return None
            if opcode == 8:
                raise StreamUnavailable('Demo WebSocket bağlantısı kapandı.')
        except self.timeout_error:
            return None
        except StreamUnavailable:
            raise
        except Exception:
            raise StreamUnavailable('Demo WebSocket bağlantısı kesildi.') from None
        if value in ('', b''):
            raise StreamUnavailable('Demo WebSocket bağlantısı kapandı.')
        return value

    def close(self):
        try:
            self.connection.close(timeout=1)
        except Exception:
            pass


class DemoUserStream:
    def __init__(self, exchange, *, socket_factory=_Socket, clock=time.monotonic):
        self.exchange, self.socket_factory, self.clock = exchange, socket_factory, clock
        self.socket = None
        self._key = None
        self.generation = 0
        self._seen = OrderedDict()

    def connect(self):
        self.close()
        try:
            response = self.exchange.request('POST', LISTEN_PATH)
        except ExchangeError:
            raise StreamUnavailable('Demo kullanıcı akışı başlatılamadı.') from None
        key = response.get('listenKey') if isinstance(response, dict) else None
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,512}', key):
            raise StreamProtocolError('Demo kullanıcı akışı anahtar yanıtı geçersiz.')
        # Do not save key on the object until the handshake succeeds.
        try:
            self.socket = self.socket_factory(STREAM_BASE+key)
        except StreamProtocolError:
            raise
        except Exception:
            raise StreamUnavailable('Demo WebSocket bağlantısı kurulamadı.') from None
        self._key = key
        self.opened_at = self.renewed_at = self.clock()
        self.generation += 1
        return {'state': 'STREAM_CONNECTED', 'generation': self.generation}

    def maintain(self):
        if self.socket is None:
            raise StreamUnavailable('Kullanıcı akışı bağlı değil.')
        now = self.clock()
        if now-self.opened_at >= 23*3600:
            self.close()
            raise StreamUnavailable('Kullanıcı akışı bağlantısı yenilenmeli.')
        if now-self.renewed_at >= 30*60:
            try:
                response = self.exchange.request('PUT', LISTEN_PATH)
            except ExchangeError:
                self.close()
                raise StreamUnavailable('Kullanıcı akışı yenilemesi doğrulanamadı.') from None
            if (not isinstance(response, dict) or
                    ('listenKey' in response and response['listenKey'] != self._key)):
                self.close()
                raise StreamUnavailable('Kullanıcı akışı anahtarı değişti; uzlaştırma gerekli.')
            self.renewed_at = now

    def wait(self, seconds):
        """Wake on one new event, otherwise preserve periodic REST polling."""
        if not 0 <= seconds <= 60:
            raise ValueError('Kullanıcı akışı beklemesi 0–60 saniye olmalı.')
        deadline = self.clock()+seconds
        # Bound duplicate floods even when a fake/fast server never blocks.
        for _ in range(256):
            self.maintain()
            remaining = deadline-self.clock()
            if remaining <= 0:
                return None
            raw = self.socket.receive(min(remaining, 1))
            if raw is None:
                continue
            event = normalize_event(raw)
            if event['event_id'] in self._seen:
                continue
            self._seen[event['event_id']] = None
            if len(self._seen) > 4096:
                self._seen.popitem(last=False)
            return event
        self.close()
        raise StreamProtocolError('Kullanıcı akışı olay yoğunluğu sınırı aşıldı.')

    def close(self):
        if self.socket is not None:
            self.socket.close()
        self.socket, self._key = None, None
