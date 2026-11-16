"""Explicit product/environment/account contexts. Discovery never grants writes."""
from dataclasses import asdict,dataclass
import hashlib
import json
from types import MappingProxyType


@dataclass(frozen=True)
class Profile:
    id:str
    product:str
    environment:str
    api_family:str
    base_url:str
    credential_prefix:str
    account_model:str
    time_path:str|None
    public_reads:tuple
    private_reads:tuple
    order_lookup:str|None
    source:str
    execution_registered:bool=False
    note:str=''

    def describe(self):
        return asdict(self)|{'exchange':'binance','discovery_read_only':True,'write_permission':'NOT_VERIFIED',
                            'private_authentication':'HMAC_SHA256','absence_is_rejection':False,
                            'discovery_support':'READ_ONLY' if self.public_reads or self.private_reads else 'DESCRIBED_ONLY'}
    def fingerprint(self):return hashlib.sha256(json.dumps(self.describe(),sort_keys=True,separators=(',',':')).encode()).hexdigest()


_rows=[]
def _add(id,product,environment,family,base,prefix,model,time_path,public=(),private=(),lookup=None,source='',execution=False,note=''):
    _rows.append(Profile(id,product,environment,family,base,prefix,model,time_path,tuple(public),tuple(private),lookup,source,execution,note))


_um='https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info'
_cm='https://developers.binance.com/en/docs/products/derivatives-trading-coin-futures/general-info'
_spot='https://developers.binance.com/en/docs/products/spot/testnet/general-info'
_options='https://developers.binance.com/en/docs/products/derivatives-trading-options/general-info'
_pm='https://developers.binance.com/en/docs/products/derivatives-trading-portfolio-margin/general-info'
_pro='https://developers.binance.com/en/docs/products/derivatives-trading-portfolio-margin-pro/general-info'
for env,base,prefix in [('demo','https://demo-fapi.binance.com','BINANCE_DEMO'),('production','https://fapi.binance.com','BINANCE_USDM_PRODUCTION')]:
    _add('usdm-'+env,'USD-M',env,'FAPI',base,prefix,'USD_M_LINEAR','/fapi/v1/time',
         ('/fapi/v1/time','/fapi/v1/exchangeInfo'),('/fapi/v3/account','/fapi/v1/accountConfig','/fapi/v1/positionSide/dual'),
         '/fapi/v1/order',_um,env=='demo','Legacy execution remains demo USD-M only.')
for env,base,prefix in [('demo','https://demo-dapi.binance.com','BINANCE_COINM_DEMO'),('production','https://dapi.binance.com','BINANCE_COINM_PRODUCTION')]:
    _add('coinm-'+env,'COIN-M',env,'DAPI',base,prefix,'COIN_M_INVERSE','/dapi/v1/time',
         ('/dapi/v1/time','/dapi/v1/exchangeInfo'),('/dapi/v1/account','/dapi/v1/positionSide/dual'),'/dapi/v1/order',_cm)
for env,base,prefix in [('testnet','https://testnet.binance.vision','BINANCE_SPOT_TESTNET'),('production','https://api.binance.com','BINANCE_SPOT_PRODUCTION')]:
    _add('spot-'+env,'SPOT',env,'API',base,prefix,'SPOT','/api/v3/time',
         ('/api/v3/time','/api/v3/exchangeInfo'),('/api/v3/account',),'/api/v3/order',_spot,
         note='Testnet supports /api only; absent historical data is not a rejected order.')
for env,base,prefix in [('demo','https://demo-fapi.binance.com','BINANCE_OPTIONS_DEMO'),('production','https://eapi.binance.com','BINANCE_OPTIONS_PRODUCTION')]:
    _add('options-'+env,'OPTIONS',env,'EAPI',base,prefix,'OPTIONS_MARGIN','/eapi/v1/time',
         ('/eapi/v1/time','/eapi/v1/exchangeInfo'),('/eapi/v1/marginAccount',),source=_options,
         note='Documented demo host is shared with UM, not a shared credential or account model. Access errors prove no eligibility.')
_add('margin-production','MARGIN','production','SAPI','https://api.binance.com','BINANCE_MARGIN_PRODUCTION','MARGIN_CROSS','/api/v3/time',
     ('/api/v3/time',),('/sapi/v1/margin/account',),source='https://developers.binance.com/en/docs/catalog/core-trading-margin-trading/api/rest-api/account')
_add('margin-isolated-production','MARGIN','production','SAPI','https://api.binance.com','BINANCE_MARGIN_ISOLATED_PRODUCTION','MARGIN_ISOLATED','/api/v3/time',
     ('/api/v3/time',),('/sapi/v1/margin/isolated/account',),source='https://developers.binance.com/en/docs/catalog/core-trading-margin-trading/api/rest-api/account')
_add('portfolio-margin-production','PORTFOLIO_MARGIN','production','PAPI','https://papi.binance.com','BINANCE_PM_PRODUCTION','PM',None,
     ('/papi/v1/ping',),('/papi/v1/account',),source=_pm)
_add('portfolio-margin-pro-production','PORTFOLIO_MARGIN_PRO','production','SAPI','https://api.binance.com','BINANCE_PM_PRO_PRODUCTION','PM_PRO_V1','/api/v3/time',
     ('/api/v3/time',),('/sapi/v1/portfolio/account',),source=_pro,note='PM_1 has version-dependent descriptions; do not normalize it to a linear risk model.')
_add('portfolio-margin-span-production','PORTFOLIO_MARGIN_PRO','production','SAPI','https://api.binance.com','BINANCE_PM_SPAN_PRODUCTION','PM_PRO_SPAN_V2','/api/v3/time',
     ('/api/v3/time',),('/sapi/v2/portfolio/account',),source=_pro)
for id,product,prefix in [('convert-production','CONVERT','BINANCE_CONVERT_PRODUCTION'),('wallet-production','WALLET','BINANCE_WALLET_PRODUCTION'),('sub-account-production','SUB_ACCOUNT','BINANCE_SUB_ACCOUNT_PRODUCTION')]:
    _add(id,product,'production','SAPI','https://api.binance.com',prefix,product,None,
         source='docs/research/crypto-bot-20261115/ENVIRONMENT-REVIEW.md',
         note='Registered boundary only; product-specific discovery and execution remain in G19/G20/G21.')

PROFILES=MappingProxyType({p.id:p for p in _rows})


def profile(context_id):
    if not isinstance(context_id,str) or context_id not in PROFILES:raise ValueError('CONTEXT_NOT_REGISTERED')
    return PROFILES[context_id]


def inventory():
    return {'schema':'product-environment-registry/1','profiles':[p.describe() for p in PROFILES.values()],
            'execution_contexts':['usdm-demo'],'production_execution_enabled':False,
            'no_implicit_host_or_credential_fallback':True}


def scoped_identity(context_id,api_key='',*,access=None):
    p=profile(context_id)
    access=('PRIVATE' if api_key else 'PUBLIC') if access is None else access
    if access not in ('PUBLIC','PRIVATE'):raise ValueError('DISCOVERY_ACCESS_SCOPE_INVALID')
    credential_ref=hashlib.sha256(api_key.encode()).hexdigest() if api_key else None
    account_scope=hashlib.sha256(json.dumps(['binance',p.id,p.product,p.environment,p.api_family,p.base_url,p.account_model,
                                         credential_ref or 'PUBLIC'],separators=(',',':')).encode()).hexdigest()
    context_ref=hashlib.sha256(json.dumps([account_scope,p.fingerprint(),access],separators=(',',':')).encode()).hexdigest()
    return {'context_id':p.id,'context_ref':context_ref,'profile_digest':p.fingerprint(),
            'account_ref':credential_ref if p.id=='usdm-demo' and credential_ref else account_scope,
            'credential_ref':credential_ref,'product':p.product,'environment':p.environment,
            'account_model':p.account_model,'base_url':p.base_url,'api_family':p.api_family,'exchange':'binance'}


EXECUTION_CONTEXT={'schema':'execution-namespace/1','exchange':'binance','environment':'demo','product':'USD-M',
                   'base_url':PROFILES['usdm-demo'].base_url,'legacy_account_ref_algorithm':'SHA256_API_KEY_UNCHANGED'}
