import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from agentrader.runtime import supervise_session
from agentrader.service_cli import request_stop,service_status
from agentrader.state import StateStore
import test_v2_runner as fixtures


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=StateStore(Path(self.temp.name)/'state.db')
        with self.store.db:self.store.db.execute("INSERT INTO control VALUES ('plan_owner','owner')")
    def tearDown(self):self.store.close();self.temp.cleanup()

    def test_health_has_fresh_stale_and_stopped_states(self):
        self.assertEqual(service_status(self.store,'s')['state'],'NOT_OBSERVED')
        self.store.runtime_health('s',{'state':'GRID_DRAINING'},100)
        self.assertEqual(service_status(self.store,'s',clock=lambda:101)['health'],'FRESH')
        self.assertEqual(service_status(self.store,'s',clock=lambda:191)['health'],'STALE')
        self.store.runtime_health('s',{'state':'GRID_DRAINING','service_stopped':True},100)
        self.assertEqual(service_status(self.store,'s',clock=lambda:101)['health'],'STOPPED')

    def test_stop_request_is_owner_checked_and_revokes_future_entries_atomically(self):
        self.store.save_session(dict(id='s',entry_id='entry',engine='grid-v2',active=True))
        with self.assertRaises(ValueError):request_stop(self.store,'s','foreign')
        request_stop(self.store,'s','owner')
        self.assertTrue(self.store.service_stop_request('s')['requested'])
        self.assertIsNotNone(self.store.db.execute("SELECT 1 FROM control WHERE name='entry_revoked:entry'").fetchone())

    def test_grid_service_stop_drains_once_without_reopening_or_flattening(self):
        self.store.save_session(dict(id='s',entry_id='entry',engine='grid-v2',active=True))
        request_stop(self.store,'s','owner')
        runner=Mock(store=self.store);runner.stop.return_value={'state':'GRID_DRAINING','session_id':'s'}
        supervise_session(runner,'s',emit=Mock(),execute=True,iterations=0,drain_on_exit=True)
        runner.stop.assert_called_once_with('s',close_position=False,execute=True)
        runner.open.assert_not_called();runner.manage.assert_not_called()
        self.assertIsNone(self.store.service_stop_request('s'))

    def test_read_only_stop_does_not_clear_unexecuted_grid_cancellation(self):
        self.store.save_session(dict(id='s',entry_id='entry',engine='grid-v2',active=True))
        request_stop(self.store,'s','owner')
        runner=Mock(store=self.store);runner.stop.return_value={'state':'GRID_STOP_PREVIEW'}
        supervise_session(runner,'s',emit=Mock(),execute=False,iterations=0)
        runner.stop.assert_called_once_with('s',close_position=False,execute=False)
        self.assertIsNotNone(self.store.service_stop_request('s'))


class ServiceRunnerTests(unittest.TestCase):
    setUp=fixtures.V2RunnerTests.setUp
    tearDown=fixtures.V2RunnerTests.tearDown
    authorize=fixtures.V2RunnerTests.authorize
    open=fixtures.V2RunnerTests.open

    def test_stopping_pending_single_cancels_entry_without_new_trade(self):
        self.plan['entry'].update(condition='LIMIT',trigger_price='79900');self.x.limit_pending=True
        self.authorize();sid=self.open()['session_id']
        request_stop(self.store,sid,'local:test')
        supervise_session(self.runner,sid,emit=Mock(),execute=True,iterations=0)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='POST']),1)
        self.assertEqual(len([c for c in self.x.calls if c[0]=='DELETE']),1)
        self.assertEqual(self.x.amount,0)
        self.assertEqual(self.store.sessions(),[])
