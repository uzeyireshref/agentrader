import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    api_key: str = field(default="", repr=False)
    api_secret: str = field(default="", repr=False)

    @classmethod
    def load(cls, path: Path = Path(".env")) -> "Config":
        values = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, sep, value = line.partition("=")
                if not sep:
                    raise ValueError(".env satırları ANAHTAR=DEĞER biçiminde olmalı.")
                values[key.strip()] = value.strip().strip("\"'")
        def get(key, default=""):
            return os.environ.get(key, values.get(key, default))
        if get("AGENTRADER_ENV", "demo") != "demo":
            raise ValueError("Bu sürüm yalnızca demo ortamını destekler.")
        key, secret = get("BINANCE_DEMO_API_KEY"), get("BINANCE_DEMO_API_SECRET")
        if bool(key) != bool(secret):
            raise ValueError("Demo API key ve secret birlikte tanımlanmalı.")
        return cls(key, secret)

    @classmethod
    def load_for_discovery(cls,context_id,path=Path('.env')):
        from agentrader.shared.product_registry import profile
        p=profile(context_id)
        if context_id=='usdm-demo':
            old=cls.load(path);return DiscoveryCredentials(context_id,old.api_key,old.api_secret)
        values={};path=Path(path)
        if path.exists():
            for line in path.read_text(encoding='utf-8-sig').splitlines():
                line=line.strip()
                if not line or line.startswith('#'):continue
                key,sep,value=line.partition('=')
                if not sep:raise ValueError('DISCOVERY_CONFIG_FORMAT_INVALID')
                values[key.strip()]=value.strip().strip('"\'')
        def get(suffix):
            name=p.credential_prefix+suffix
            return os.environ.get(name,values.get(name,''))
        return DiscoveryCredentials(context_id,get('_API_KEY'),get('_API_SECRET'))


@dataclass(frozen=True)
class DiscoveryCredentials:
    context_id:str
    api_key:str=field(default='',repr=False)
    api_secret:str=field(default='',repr=False)

    def __post_init__(self):
        from agentrader.shared.product_registry import profile
        profile(self.context_id)
        if not isinstance(self.api_key,str) or not isinstance(self.api_secret,str) or bool(self.api_key)!=bool(self.api_secret):
            raise ValueError('DISCOVERY_CREDENTIAL_PAIR_REQUIRED')
