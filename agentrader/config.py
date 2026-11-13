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
