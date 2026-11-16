"""Trusted service actors. HTTP constructs bot actors only from configured credentials."""
from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class DrawingActor:
    kind: str
    actor_id: str
    bot_id: str | None = None
    strategy_id: str | None = None

    def __post_init__(self):
        if self.kind not in ('manual','bot') or not self.actor_id:
            raise ValueError('Invalid drawing actor')
        if self.kind=='bot' and (not self.bot_id or not self.strategy_id):
            raise ValueError('Bot identity must be configured by the server')

    def view(self):
        return dict(kind=self.kind,actor_id=self.actor_id,bot_id=self.bot_id,strategy_id=self.strategy_id)

    @property
    def namespace(self):
        return 'bot-'+hashlib.sha256(json.dumps([self.bot_id,self.strategy_id],separators=(',',':')).encode()).hexdigest()[:20] if self.kind=='bot' else None
