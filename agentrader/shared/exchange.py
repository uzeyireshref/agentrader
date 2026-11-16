"""Yalnızca Binance demo ortamı; endpoint ve HTTP yöntemi izin listesi."""
import hashlib
import hmac
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

from agentrader.shared.config import Config
from agentrader.shared.errors import ExchangeError
from agentrader.shared.transport import JsonTransport
from agentrader.shared.query_routes import PUBLIC_READS,PRIVATE_READS,SINGLE_SHOT_GETS,KEY_ONLY_READS

BASE_URL = "https://demo-fapi.binance.com"
COIN_BASE_URL = "https://demo-dapi.binance.com"
COIN_PUBLIC = {'/dapi/v1/time'}
COIN_READS = COIN_PUBLIC | {'/dapi/v1/positionRisk','/dapi/v1/openOrders','/dapi/v1/openAlgoOrders','/dapi/v1/positionSide/dual'}
PUBLIC = {"/fapi/v1/ping", "/fapi/v1/time", "/fapi/v1/exchangeInfo", "/fapi/v1/ticker/bookTicker", "/fapi/v1/premiumIndex", "/fapi/v1/assetIndex", "/fapi/v2/ticker/price"}
PRIVATE = {"/fapi/v3/account", "/fapi/v1/openOrders", "/fapi/v1/positionSide/dual",
           "/fapi/v1/openAlgoOrders", "/fapi/v3/positionRisk", "/fapi/v1/income", "/fapi/v1/userTrades",
           "/fapi/v1/symbolConfig", "/fapi/v1/leverageBracket", "/fapi/v1/accountConfig",
           "/fapi/v1/multiAssetsMargin", "/fapi/v1/feeBurn", "/fapi/v1/positionMargin/history", "/fapi/v1/orderAmendment"}
PUBLIC |= PUBLIC_READS
PRIVATE |= PRIVATE_READS

ORDER_REQUESTS = {('GET', '/fapi/v1/order'), ('POST', '/fapi/v1/order'),
                  ('POST','/fapi/v1/countdownCancelAll'),
                  ('DELETE', '/fapi/v1/order'), ('GET', '/fapi/v1/algoOrder'),
                  ('POST', '/fapi/v1/algoOrder'), ('DELETE', '/fapi/v1/algoOrder'),
                  ('POST', '/fapi/v1/leverage'),('POST','/fapi/v1/marginType'),
                  ('POST','/fapi/v1/positionSide/dual'),('POST','/fapi/v1/multiAssetsMargin'),
                  ('POST','/fapi/v1/feeBurn'), ('POST','/fapi/v1/positionMargin'),
                  ('DELETE','/fapi/v1/batchOrders'), ('PUT','/fapi/v1/order'), ('PUT','/fapi/v1/batchOrders'),
                  ('POST','/fapi/v1/batchOrders'),
                  ('POST','/fapi/v1/listenKey'), ('PUT','/fapi/v1/listenKey'),
                  ('DELETE','/fapi/v1/listenKey')}


def allowed_requests():
    """The runtime adapter and capability report share this single allowlist."""
    return frozenset({('GET', path) for path in PUBLIC | PRIVATE | COIN_READS} | ORDER_REQUESTS)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class DemoExchange:
    def __init__(self, config: Config, *, transport=None, order_transport='rest', store=None, ws_connector=None):
        if getattr(config,'context_id','usdm-demo')!='usdm-demo':raise ValueError('EXECUTION_CONTEXT_MISMATCH')
        if order_transport not in ('rest','ws'):raise ValueError('ORDER_TRANSPORT_INVALID')
        if order_transport=='ws' and store is None:raise ValueError('WS_EXECUTION_STORE_REQUIRED')
        if store is not None:
            from agentrader.shared.state import StateStore
            from agentrader.shared.storage_context import check_execution
            if not isinstance(store,StateStore):raise ValueError('EXECUTION_STORE_REQUIRED')
            check_execution(store.db)
        self.config = config
        self.offset_ms = 0
        self.coin_offset_ms = None
        self.opener = build_opener(NoRedirect())
        self.transport = transport or JsonTransport()
        self.order_transport,self.store=order_transport,store
        self.ws_orders=None
        if order_transport=='ws':
            from agentrader.shared.ws_orders import WsOrders
            self.ws_orders=WsOrders(self,store,ws_connector)

    def get(self, path: str, params=None):
        return self.request("GET", path, params)

    def public_query(self,name,scope,values):
        from agentrader.shared.market_data import PublicMarket
        return PublicMarket(transport=self.transport).query(name,scope,values)

    def request(self, method: str, path: str, params=None):
        if (method, path) not in allowed_requests():
            raise ValueError("Desteklenmeyen endpoint veya HTTP yöntemi.")
        from agentrader.shared.ws_orders import ROUTES,guard_rest
        if self.ws_orders is not None and (method,path) in ROUTES:
            return self.ws_orders.request(method,path,params)
        if self.ws_orders is not None and path=='/fapi/v1/batchOrders' and method!='GET':
            raise ExchangeError('Native batch için WS sözleşmesi yok; REST fallback yapılmadı.',delivery_status='NOT_SENT')
        if self.store is not None:
            import hashlib
            guard_rest(self.store,hashlib.sha256(self.config.api_key.encode()).hexdigest(),method,path,dict(params or {}))
        coin=path in COIN_READS
        if coin and path not in COIN_PUBLIC and self.coin_offset_ms is None:self.sync_coin_time()
        if path in SINGLE_SHOT_GETS:
            return self.transport.perform(self.opener,lambda:self._signed_request(method,path,params),method,BASE_URL,allow_retries=False)
        return self.transport.perform(self.opener,lambda:self._signed_request(method,path,params),method,COIN_BASE_URL if coin else BASE_URL)

    def _signed_request(self,method,path,params):
        headers = {}
        values = dict(params or {})
        if path == '/fapi/v1/listenKey' and values:
            raise ValueError('Kullanıcı akışı isteği parametre kabul etmez.')
        query = urlencode(values)
        if path not in PUBLIC | COIN_PUBLIC:
            if not self.config.api_key:
                raise ExchangeError("Demo API anahtarları tanımlı değil.",delivery_status='NOT_SENT')
            if path != '/fapi/v1/listenKey' and path not in KEY_ONLY_READS:
                offset=self.coin_offset_ms if path in COIN_READS else self.offset_ms
                values.update(timestamp=int(time.time() * 1000) + (offset or 0), recvWindow=5000)
                query = urlencode(values)
                signature = hmac.new(self.config.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
                query += "&signature=" + signature
            headers["X-MBX-APIKEY"] = self.config.api_key
        return Request((COIN_BASE_URL if path in COIN_READS else BASE_URL) + path + ("?" + query if query else ""), headers=headers, method=method)

    def sync_coin_time(self):
        start=time.time()*1000;payload=self.get('/dapi/v1/time');end=time.time()*1000
        if not isinstance(payload,dict) or type(payload.get('serverTime')) is not int or not 0<=end-start<=15000:raise ValueError('COIN-M saat görünümü doğrulanamadı.')
        self.coin_offset_ms=round(payload['serverTime']-(start+end)/2)
        return {'server_time_ms':payload['serverTime'],'clock_offset_ms':self.coin_offset_ms}

    def sync_time(self):
        start = time.time() * 1000
        server = self.get("/fapi/v1/time")["serverTime"]
        end = time.time() * 1000
        self.offset_ms = round(server - (start + end) / 2)
        return {"server_time_ms": server, "clock_offset_ms": self.offset_ms,
                "round_trip_ms": round(end - start)}
