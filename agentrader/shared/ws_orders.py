"""Single-flight demo USD-M WS requests with durable no-repost evidence.

One short-lived socket per request avoids session key changes and reconnect
replays. Passive user-data streams remain independent. No REST fallback.
"""
import hashlib
import hmac
import json
import sqlite3
import time
import uuid
from urllib.parse import urlencode

from agentrader.shared.errors import ExchangeError
from agentrader.shared.rate_budget import charges, reserve, observe

WS_URL = 'wss://testnet.binancefuture.com/ws-fapi/v1'
WS_HOST = 'testnet.binancefuture.com'
ROUTES = {
    ('POST', '/fapi/v1/order'): ('order.place', 0, 1),
    ('PUT', '/fapi/v1/order'): ('order.modify', 0, 1),
    ('DELETE', '/fapi/v1/order'): ('order.cancel', 1, 0),
    ('GET', '/fapi/v1/order'): ('order.status', 1, 0),
    ('POST', '/fapi/v1/algoOrder'): ('algoOrder.place', 0, 1),
    ('DELETE', '/fapi/v1/algoOrder'): ('algoOrder.cancel', 1, 0),
}
FIELDS = {
    'order.place': set('symbol side positionSide type timeInForce quantity reduceOnly price newClientOrderId newOrderRespType priceMatch selfTradePreventionMode goodTillDate'.split()),
    'order.modify': set('symbol side quantity price orderId origClientOrderId priceMatch modifyId reduceOnly'.split()),
    'order.cancel': set('symbol orderId origClientOrderId'.split()),
    'order.status': set('symbol orderId origClientOrderId'.split()),
    'algoOrder.place': set('algoType symbol side positionSide type timeInForce quantity price triggerPrice workingType priceMatch closePosition priceProtect reduceOnly activatePrice callbackRate clientAlgoId newOrderRespType selfTradePreventionMode goodTillDate'.split()),
    'algoOrder.cancel': set('algoId clientAlgoId'.split()),
}


def schema(store):
    with store.db:
        store.db.execute('''CREATE TABLE IF NOT EXISTS ws_deliveries (
            identity TEXT PRIMARY KEY, account_ref TEXT NOT NULL, method TEXT NOT NULL,
            path TEXT NOT NULL, request_id TEXT NOT NULL UNIQUE,
            state TEXT NOT NULL, delivery_status TEXT)''')
        columns={r[1] for r in store.db.execute('PRAGMA table_info(ws_deliveries)')}
        for name,definition in (('created_at','REAL'),('updated_at','REAL'),('transport_faults','INTEGER NOT NULL DEFAULT 0')):
            if name not in columns:store.db.execute(f'ALTER TABLE ws_deliveries ADD COLUMN {name} {definition}')


def identity(account_ref, method, path, params):
    # Delivery identity follows the operation, never the mutable price/quantity.
    # A changed payload cannot acquire a second right to send the same CID.
    fields = params
    if method == 'POST':
        fields = {k:params.get(k) for k in ('symbol','newClientOrderId','clientAlgoId')}
    elif method in ('PUT','DELETE'):
        fields = {k:params.get(k) for k in ('symbol','orderId','origClientOrderId','algoId','clientAlgoId')}
        if method == 'PUT': fields['modifyId'] = params.get('modifyId')
    return hashlib.sha256(json.dumps([account_ref, method, path, fields], sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def guard_rest(store, account_ref, method, path, params):
    if method == 'GET' or (method, path) not in ROUTES: return
    schema(store)
    row = store.db.execute('SELECT state FROM ws_deliveries WHERE identity=?',
                          (identity(account_ref, method, path, params),)).fetchone()
    if row:
        raise ExchangeError('Önceki WS gönderimi sorgulanmalı; REST tekrar gönderimi engellendi.',
                            delivery_status='UNKNOWN')


def connect(url):
    import websocket
    websocket.enableTrace(False)
    return websocket.create_connection(url, timeout=15, redirect_limit=0)


class WsOrders:
    def __init__(self, exchange, store, connector=None):
        self.exchange, self.store = exchange, store
        self.connector = connector or connect
        self.account_ref = hashlib.sha256(exchange.config.api_key.encode()).hexdigest()
        self._config = exchange.config
        self._synced = False
        schema(store)

    def request(self, method, path, params):
        if (method, path) not in ROUTES: raise ValueError('WS_ROUTE_NOT_REGISTERED')
        if self.exchange.config != self._config: raise ValueError('WS_CREDENTIAL_CONTEXT_CHANGED')
        if not self._config.api_key or not self._config.api_secret:
            raise ExchangeError('Demo WS anahtarları gerekli.', delivery_status='NOT_SENT')
        name, weight, orders = ROUTES[method, path]; params = dict(params or {})
        self._validate(name, params)
        # Official shared SDK signs URL-encoded pairs; current Spot WS docs
        # prescribe raw UTF-8 pairs. Futures only explicitly requires sorting.
        # Permit the common proven subset until product-specific wire evidence
        # resolves punctuation encoding. Never try a second signing variant.
        unsigned = dict(params, apiKey=self._config.api_key)
        if urlencode(sorted(unsigned.items())) != '&'.join(f'{k}={v}' for k,v in sorted(unsigned.items())):
            raise ValueError('WS_PARAMETER_ENCODING_UNPROVEN')
        if not self._synced:
            try: self.exchange.sync_time()
            except Exception:
                raise ExchangeError('WS öncesi demo saat okuması başarısız; gönderim yok.', delivery_status='NOT_SENT') from None
            self._synced = True
        mutation = method != 'GET'
        ident = identity(self.account_ref, method, path, params)
        rid = 'ws-' + uuid.uuid4().hex
        if mutation:
            try:
                with self.store.db:
                    now=time.time()
                    self.store.db.execute('''INSERT INTO ws_deliveries
                        (identity,account_ref,method,path,request_id,state,created_at,updated_at)
                        VALUES (?,?,?,?,?,?,?,?)''',
                        (ident, self.account_ref, method, path, rid, 'SUBMITTING',now,now))
            except sqlite3.IntegrityError:
                raise ExchangeError('WS kimliği daha önce ayrıldı; otomatik tekrar yok.', delivery_status='UNKNOWN') from None
        socket = None; started = False
        try:
            governor = self.exchange.transport.governor
            governor.check(WS_HOST)
            reserve(governor, charges('demo', 'WS', 5))
            socket = self.connector(WS_URL)
            reserve(governor, charges('demo', 'WS', max(1, weight), orders))
            values = dict(params)
            values.update(apiKey=self._config.api_key, timestamp=int(time.time()*1000)+self.exchange.offset_ms, recvWindow=5000)
            payload = urlencode(sorted(values.items()))
            values['signature'] = hmac.new(self._config.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
            started = True  # send() may fail after writing part/all of the frame.
            socket.send(json.dumps(dict(id=rid, method=name, params=values), separators=(',', ':'), allow_nan=False))
            raw = socket.recv()
            if not isinstance(raw, str) or len(raw) > 1024*1024: raise ValueError('WS_FRAME_INVALID')
            body = json.loads(raw)
            if not isinstance(body, dict) or body.get('id') != rid or type(body.get('status')) is not int:
                raise ValueError('WS_RESPONSE_CORRELATION_FAILED')
            status = body['status']
            limits = body.get('rateLimits', [])
            if not isinstance(limits, list) or len(limits) > 100: raise ValueError('WS_RATE_SCHEMA_INVALID')
            retry = None
            if status in (418, 429):
                stamp = body.get('retryAfter')
                if type(stamp) in (int, float) and 0 <= stamp <= 10**16:
                    retry = max(0, stamp/1000-governor.clock())
                else: retry = 300 if status == 418 else 60
            observe(governor, WS_HOST, limits, retry)
            if status != 200:
                error = body.get('error', {})
                code = error.get('code') if isinstance(error, dict) else None
                code = code if type(code) is int else None
                delivery = 'READ_FAILED' if not mutation else 'UNKNOWN'
                if mutation and status in (400, 401, 403, 404, 405, 422) and code not in (None, -1006, -1007):
                    delivery = 'REJECTED'
                raise ExchangeError('WS işlem yanıtı başarısız; sonuç kimlikle doğrulanmalı.', code, status,
                                    delivery_status=delivery, retry_after=retry)
            result = body.get('result')
            if not isinstance(result, dict) or 'error' in body: raise ValueError('WS_RESULT_INVALID')
            self._match(name, params, result)
            if mutation: self._state(ident, 'ACKNOWLEDGED', 'ACKNOWLEDGED')
            return result
        except ExchangeError as exc:
            delivery = (exc.delivery_status or 'UNKNOWN') if started else 'NOT_SENT'
            if started and delivery == 'NOT_SENT': delivery = 'UNKNOWN' if mutation else 'READ_FAILED'
            if mutation: self._state(ident, delivery, delivery, fault=started and exc.http_status is None)
            raise ExchangeError('WS isteği tamamlanamadı; gönderim kaydıyla doğrulanmalı.',
                                exc.code,exc.http_status,delivery_status=delivery,retry_after=exc.retry_after) from None
        except Exception:
            delivery = ('UNKNOWN' if mutation else 'READ_FAILED') if started else 'NOT_SENT'
            if mutation: self._state(ident, delivery, delivery, fault=True)
            raise ExchangeError('WS bağlantı veya yanıt hatası; otomatik tekrar yok.', delivery_status=delivery) from None
        finally:
            if socket is not None:
                try: socket.close()
                except Exception: pass

    def _state(self, ident, state, delivery, *, fault=False):
        with self.store.db:
            self.store.db.execute('''UPDATE ws_deliveries SET state=?,delivery_status=?,updated_at=?,
                transport_faults=transport_faults+? WHERE identity=?''', (state,delivery,time.time(),int(fault),ident))

    @staticmethod
    def _validate(name, params):
        if not params or set(params)-FIELDS[name]: raise ValueError('WS_PARAMETERS_NOT_REGISTERED')
        if any(type(v) not in (str, int) for v in params.values()): raise ValueError('WS_PARAMETERS_REQUIRE_EXACT_STRINGS_OR_INTEGERS')
        for field in ('orderId', 'algoId', 'modifyId', 'goodTillDate'):
            if field in params and (type(params[field]) is not int or not 0 < params[field] < 2**63):
                raise ValueError('WS_INTEGER_PARAMETER_INVALID')
        if name.endswith('.place') and not params.get('newClientOrderId' if name == 'order.place' else 'clientAlgoId'):
            raise ValueError('WS_DURABLE_CLIENT_ID_REQUIRED')
        if name in ('order.cancel', 'order.status', 'order.modify') and (not params.get('symbol') or not (params.get('orderId') or params.get('origClientOrderId'))):
            raise ValueError('WS_NORMAL_ORDER_ID_REQUIRED')
        if name == 'algoOrder.cancel' and not (params.get('algoId') or params.get('clientAlgoId')):
            raise ValueError('WS_ALGO_ID_REQUIRED')
        if name == 'order.modify' and not params.get('modifyId'):
            raise ValueError('WS_DURABLE_MODIFY_ID_REQUIRED')
        for field in ('price','quantity','triggerPrice','activatePrice','callbackRate'):
            if field in params and type(params[field]) is not str:
                raise ValueError('WS_DECIMAL_STRING_REQUIRED')

    @staticmethod
    def _match(name, params, result):
        for field in ('symbol', 'orderId', 'algoId', 'modifyId'):
            if field in params and str(result.get(field)) != str(params[field]): raise ValueError('WS_RESULT_IDENTITY_MISMATCH')
        for source, target in (('newClientOrderId', 'clientOrderId'), ('origClientOrderId', 'clientOrderId'), ('clientAlgoId', 'clientAlgoId')):
            if source in params and result.get(target) != params[source]: raise ValueError('WS_RESULT_CLIENT_ID_MISMATCH')
        if name.startswith('order.') and (type(result.get('orderId')) is not int or result['orderId'] <= 0):
            raise ValueError('WS_RESULT_NORMAL_ORDER_ID_MISSING')
        if name == 'algoOrder.place' and (type(result.get('algoId')) is not int or result['algoId'] <= 0):
            raise ValueError('WS_RESULT_ALGO_ID_MISSING')
