"""Local application configuration. Does not load Binance credentials or .env."""
from dataclasses import dataclass, field
import getpass
import os
from pathlib import Path
import re


@dataclass(frozen=True)
class WebSettings:
    application_database: Path = Path('data/application-demo.sqlite3')
    execution_database: Path = Path('data/execution.sqlite3')
    token: str = field(default='', repr=False)
    owner: str = field(default_factory=lambda: 'local:' + getpass.getuser())

    market_database: Path = Path('data/chart-market-demo.sqlite3')
    frontend_directory: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1] / 'web_assets')
    bot_token: str = field(default='', repr=False)
    bot_id: str = 'chart-bot'
    strategy_id: str = 'default'

    def __post_init__(self):
        app_path = Path(self.application_database).resolve()
        execution_path = Path(self.execution_database).resolve()
        if app_path == execution_path or (app_path.exists() and execution_path.exists() and os.path.samefile(app_path, execution_path)):
            raise ValueError('Uygulama ve işlem veritabanları ayrı olmalı.')
        market_path = Path(self.market_database).resolve()
        for target in (app_path, execution_path):
            if market_path == target or (market_path.exists() and target.exists() and os.path.samefile(market_path, target)):
                raise ValueError('Grafik veri deposu işlem ve uygulama depolarından ayrı olmalı.')
        object.__setattr__(self, 'market_database', market_path)
        object.__setattr__(self, 'frontend_directory', Path(self.frontend_directory).resolve())
        if not isinstance(self.token, str) or (self.token and not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', self.token)):
            raise ValueError('Web erişim anahtarı 32–256 güvenli karakter içermeli.')
        if not isinstance(self.owner, str) or not self.owner or len(self.owner) > 128:
            raise ValueError('Yerel uygulama sahibi geçersiz.')
        if not isinstance(self.bot_token,str) or (self.bot_token and (not re.fullmatch(r'[A-Za-z0-9_-]{32,256}',self.bot_token) or not self.token or self.bot_token==self.token)):
            raise ValueError('Bot anahtarı ayrı ve güvenli olmalı; kullanıcı anahtarı da yapılandırılmalı.')
        if any(not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',v) for v in (self.bot_id,self.strategy_id)):
            raise ValueError('Bot/strateji kimliği geçersiz.')
        object.__setattr__(self, 'application_database', app_path)
        object.__setattr__(self, 'execution_database', execution_path)

    @property
    def worker_lock(self):
        return self.application_database.with_suffix(self.application_database.suffix + '.worker.lock')

    @classmethod
    def load(cls):
        return cls(application_database=Path(os.environ.get('AGENTRADER_WEB_DATABASE', 'data/application-demo.sqlite3')),
                   execution_database=Path(os.environ.get('AGENTRADER_EXECUTION_DATABASE', 'data/execution.sqlite3')),
                   token=os.environ.get('AGENTRADER_WEB_TOKEN', ''),
                   bot_token=os.environ.get('AGENTRADER_CHART_BOT_TOKEN',''),
                   bot_id=os.environ.get('AGENTRADER_CHART_BOT_ID','chart-bot'),
                   strategy_id=os.environ.get('AGENTRADER_CHART_STRATEGY_ID','default'),
                   market_database=Path(os.environ.get('AGENTRADER_CHART_DATABASE', 'data/chart-market-demo.sqlite3')))
