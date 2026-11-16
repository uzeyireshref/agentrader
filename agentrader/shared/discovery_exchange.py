"""Context-bound discovery transport. Only fixed pure GET routes are possible."""
import hashlib
import hmac
import re
import time
from urllib.parse import urlencode
from urllib.request import Request,build_opener

from agentrader.shared.config import Config,DiscoveryCredentials
from agentrader.shared.exchange import NoRedirect,ExchangeError
from agentrader.shared.product_registry import profile,scoped_identity
from agentrader.shared.transport import JsonTransport


class DiscoveryExchange:
    def __init__(self,context_id,credentials=None,*,transport=None):
        self._profile=profile(context_id)
        if isinstance(credentials,Config):
            if context_id!='usdm-demo':raise ValueError('LEGACY_CREDENTIALS_ARE_USDM_DEMO_ONLY')
            credentials=DiscoveryCredentials(context_id,credentials.api_key,credentials.api_secret)
        self.credentials=credentials or DiscoveryCredentials(context_id)
        if not isinstance(self.credentials,DiscoveryCredentials) or self.credentials.context_id!=context_id:raise ValueError('DISCOVERY_CREDENTIAL_CONTEXT_MISMATCH')
        self._identity=scoped_identity(context_id,self.credentials.api_key)
        self.opener=build_opener(NoRedirect());self.transport=transport or JsonTransport()
        self.offset_ms=0;self._synced=False

    @property
    def profile(self):return self._profile
    @property
    def identity(self):return dict(self._identity)
    @property
    def has_credentials(self):return bool(self.credentials.api_key and self.credentials.api_secret)

    def evidence_identity(self,include_private=False):
        return scoped_identity(self.profile.id,self.credentials.api_key if include_private else '',access='PRIVATE' if include_private else 'PUBLIC')

    def _binding(self):
        if self.credentials.context_id!=self.profile.id or scoped_identity(self.profile.id,self.credentials.api_key)!=self._identity:
            raise ValueError('DISCOVERY_CREDENTIAL_CONTEXT_CHANGED')

    def _arguments(self,path,params):
        params=dict(params or {})
        if path==self.profile.order_lookup:
            symbol=params.get('symbol')
            if not isinstance(symbol,str) or not re.fullmatch('[A-Z0-9_]{2,40}',symbol):raise ValueError('DISCOVERY_ORDER_SYMBOL_REQUIRED')
            if set(params) not in ({'symbol','orderId'},{'symbol','origClientOrderId'}):raise ValueError('DISCOVERY_ONE_NORMAL_ORDER_ID_REQUIRED')
            if 'orderId' in params:
                if type(params['orderId']) is not int or not 0<params['orderId']<2**63:raise ValueError('DISCOVERY_ORDER_ID_INVALID')
            elif not isinstance(params['origClientOrderId'],str) or not re.fullmatch(r'[.A-Za-z:/0-9_-]{1,36}',params['origClientOrderId']):
                raise ValueError('DISCOVERY_CLIENT_ORDER_ID_INVALID')
        elif params:raise ValueError('DISCOVERY_ACCOUNT_QUERY_ACCEPTS_NO_OVERRIDE')
        return params

    def request(self,method,path,params=None):
        self._binding()
        allowed=set(self.profile.public_reads)|set(self.profile.private_reads)
        if self.profile.time_path:allowed.add(self.profile.time_path)
        if self.profile.order_lookup:allowed.add(self.profile.order_lookup)
        if method!='GET' or path not in allowed:raise ValueError('DISCOVERY_READ_ONLY_ROUTE_REJECTED')
        params=self._arguments(path,params)
        private=path in self.profile.private_reads or path==self.profile.order_lookup
        if private:
            if not self.has_credentials:raise ExchangeError('DISCOVERY_CREDENTIALS_MISSING',delivery_status='NOT_SENT')
            if self.profile.time_path and not self._synced:self.sync_time()
        return self.transport.perform(self.opener,lambda:self._request(path,params,private),'GET',self.profile.base_url)

    def _request(self,path,params,private):
        self._binding();values=dict(params);headers={}
        if private:
            values.update(timestamp=int(time.time()*1000)+self.offset_ms,recvWindow=5000)
            query=urlencode(values)
            query+='&signature='+hmac.new(self.credentials.api_secret.encode(),query.encode(),hashlib.sha256).hexdigest()
            headers['X-MBX-APIKEY']=self.credentials.api_key
        else:query=urlencode(values)
        return Request(self.profile.base_url+path+('?' +query if query else ''),headers=headers,method='GET')

    def get(self,path,params=None):return self.request('GET',path,params)

    def sync_time(self):
        if self.profile.time_path is None:return {'clock_source':'LOCAL_UNVERIFIED','offset_ms':0}
        start=time.time()*1000;data=self.get(self.profile.time_path);end=time.time()*1000
        if (not isinstance(data,dict) or type(data.get('serverTime')) is not int or data['serverTime']<=0 or not 0<=end-start<=15000):
            raise ValueError('DISCOVERY_TIME_UNVERIFIED')
        self.offset_ms=round(data['serverTime']-(start+end)/2);self._synced=True
        return {'clock_source':'PROFILE_SERVER_TIME','offset_ms':self.offset_ms}
