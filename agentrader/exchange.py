"""Yalnızca Binance demo ortamı; endpoint ve HTTP yöntemi izin listesi."""
import hashlib
import hmac
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

from .config import Config
from .errors import ExchangeError
from .transport import JsonTransport

BASE_URL = "https://demo-fapi.binance.com"
PUBLIC = {"/fapi/v1/ping", "/fapi/v1/time", "/fapi/v1/exchangeInfo", "/fapi/v1/ticker/bookTicker", "/fapi/v1/premiumIndex", "/fapi/v1/assetIndex"}
PRIVATE = {"/fapi/v3/account", "/fapi/v1/openOrders", "/fapi/v1/positionSide/dual",
           "/fapi/v1/openAlgoOrders", "/fapi/v3/positionRisk", "/fapi/v1/income", "/fapi/v1/userTrades",
           "/fapi/v1/symbolConfig", "/fapi/v1/leverageBracket", "/fapi/v1/accountConfig",
           "/fapi/v1/multiAssetsMargin", "/fapi/v1/feeBurn", "/fapi/v1/positionMargin/history", "/fapi/v1/orderAmendment"}

ORDER_REQUESTS = {('GET', '/fapi/v1/order'), ('POST', '/fapi/v1/order'),
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
    return frozenset({('GET', path) for path in PUBLIC | PRIVATE} | ORDER_REQUESTS)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class DemoExchange:
    def __init__(self, config: Config, *, transport=None):
        self.config = config
        self.offset_ms = 0
        self.opener = build_opener(NoRedirect())
        self.transport = transport or JsonTransport()

    def get(self, path: str, params=None):
        return self.request("GET", path, params)

    def request(self, method: str, path: str, params=None):
        if (method, path) not in allowed_requests():
            raise ValueError("Desteklenmeyen endpoint veya HTTP yöntemi.")
        return self.transport.perform(self.opener,lambda:self._signed_request(method,path,params),method,BASE_URL)

    def _signed_request(self,method,path,params):
        headers = {}
        values = dict(params or {})
        if path == '/fapi/v1/listenKey' and values:
            raise ValueError('Kullanıcı akışı isteği parametre kabul etmez.')
        query = urlencode(values)
        if path not in PUBLIC:
            if not self.config.api_key:
                raise ExchangeError("Demo API anahtarları tanımlı değil.",delivery_status='NOT_SENT')
            if path != '/fapi/v1/listenKey':
                values.update(timestamp=int(time.time() * 1000) + self.offset_ms, recvWindow=5000)
                query = urlencode(values)
                signature = hmac.new(self.config.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
                query += "&signature=" + signature
            headers["X-MBX-APIKEY"] = self.config.api_key
        return Request(BASE_URL + path + ("?" + query if query else ""), headers=headers, method=method)

    def sync_time(self):
        start = time.time() * 1000
        server = self.get("/fapi/v1/time")["serverTime"]
        end = time.time() * 1000
        self.offset_ms = round(server - (start + end) / 2)
        return {"server_time_ms": server, "clock_offset_ms": self.offset_ms,
                "round_trip_ms": round(end - start)}
