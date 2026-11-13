"""HTTP-independent application facade. No exchange writer or monitor is created."""
import time

from ..migrations import migrate
from .commands import CommandQueue
from .queries import execution_status, capabilities


class ApplicationService:
    def __init__(self, settings, clock=time.time):
        self.settings, self.clock = settings, clock
        self.queue = CommandQueue(settings.application_database, clock)

    def initialize(self):
        return migrate(self.settings.application_database)

    def health(self):
        return {'service': 'agentrader', 'api_version': 1, 'status': 'OK',
                'mode': 'LOCAL_READ_ONLY', 'exchange_access': 'NOT_CHECKED',
                'private_api_enabled': bool(self.settings.token),
                'market_feed': 'NOT_IMPLEMENTED', 'strategy_engine': 'NOT_IMPLEMENTED',
                'trading_commands_enabled': False}

    def capabilities(self):
        return capabilities()

    def status(self):
        return {'execution': execution_status(self.settings.execution_database, self.settings.owner, self.clock),
                'command_worker': self.queue.worker_status()}

    def accept_command(self, command):
        return self.queue.accept(self.settings.owner, command)

    def command(self, request_id):
        return self.queue.show(self.settings.owner, request_id)
