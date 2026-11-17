"""HTTP-independent application facade. No exchange writer or monitor is created."""
import time

from ..migrations import migrate
from .environment import bind_demo_store
from agentrader.shared.market_environment import SOURCE, ENVIRONMENT
from .commands import CommandQueue
from .queries import execution_status, capabilities


class ApplicationService:
    def __init__(self, settings, clock=time.time):
        self.settings, self.clock = settings, clock
        self.queue = CommandQueue(settings.application_database, clock)

    def initialize(self):
        bind_demo_store(self.settings.application_database)
        result=migrate(self.settings.application_database)
        from .bot_inbox import BotInbox
        BotInbox(self.settings).initialize()
        return result

    def health(self):
        return {'service': 'agentrader', 'api_version': 1, 'status': 'OK',
                'mode': 'LOCAL_BOT_QUEUE' if self.settings.bot_enabled else 'LOCAL_READ_ONLY', 'exchange_access': 'NOT_CHECKED',
                'private_api_enabled': bool(self.settings.token),
                'market_feed': 'DEMO_ON_DEMAND', 'market_source': SOURCE, 'market_environment': ENVIRONMENT,
                'strategy_engine': 'NOT_IMPLEMENTED',
                'trading_commands_enabled': self.settings.bot_enabled}

    def capabilities(self):
        return capabilities()

    def status(self):
        return {'execution': execution_status(self.settings.execution_database, self.settings.owner, self.clock),
                'command_worker': self.queue.worker_status()}

    def operations(self):
        from .operations import operation_status
        return operation_status(self.settings.execution_database,self.settings.owner,clock=self.clock)

    def accept_command(self, command):
        return self.queue.accept(self.settings.owner, command)

    def command(self, request_id):
        return self.queue.show(self.settings.owner, request_id)
