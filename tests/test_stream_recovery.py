import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from agentrader.runtime import stream_monitor_session
from agentrader.state import StateStore
from agentrader.user_stream import StreamProtocolError


class DurableStreamRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'state.db'
        self.store=StateStore(self.path)

    def tearDown(self):
        self.store.close();self.temp.cleanup()

    def test_barrier_and_audit_survive_restart_and_block_new_entries(self):
        event={'kind':'ACCOUNT_UPDATE','event_id':'safe-id','event_ms':123}
        self.store.save_stream_observation('session',event)
        self.store.close();self.store=StateStore(self.path)
        self.assertEqual(self.store.pending_stream_observation('session'),event)
        self.assertTrue(self.store.unresolved_account_command())
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM events WHERE event='user_stream_observed'").fetchone()[0],1)
        runner=Mock(store=self.store);runner.manage.return_value={'state':'MANAGING'}
        stream=Mock(generation=1);stream.connect.return_value={'state':'STREAM_CONNECTED'}
        list(stream_monitor_session(runner,'session',stream=stream,execute=True,iterations=1))
        self.assertEqual([c.kwargs['execute'] for c in runner.manage.call_args_list],[False,True])
        self.assertFalse(self.store.unresolved_account_command())

    def test_failed_rest_barrier_remains_durable_and_never_executes(self):
        event=dict(kind='ORDER_TRADE_UPDATE',event_id='safe-id',symbol='BTCUSDT',
                   client_id='agt-1',order_id=1,side='BUY',status='FILLED',cumulative_filled='1')
        self.store.save_stream_observation('session',event)
        runner=Mock(store=self.store);runner.manage.return_value={'state':'MANAGING'}
        runner.x.get.return_value=dict(symbol='BTCUSDT',clientOrderId='agt-1',orderId=1,
                                      side='BUY',status='NEW',executedQty='0')
        stream=Mock(generation=1);stream.connect.return_value={'state':'STREAM_CONNECTED'}
        with self.assertRaises(StreamProtocolError):
            list(stream_monitor_session(runner,'session',stream=stream,execute=True,
                                        iterations=1,sleep=Mock()))
        runner.manage.assert_not_called()
        self.assertEqual(self.store.pending_stream_observation('session'),event)
        self.assertTrue(self.store.unresolved_account_command())
        self.assertIsNotNone(self.store.halt_reason())

    def test_mismatched_clear_cannot_remove_newer_event(self):
        event={'kind':'ACCOUNT_UPDATE','event_id':'newer'}
        self.store.save_stream_observation('session',event)
        with self.assertRaises(ValueError):self.store.clear_stream_observation('session','older')
        self.assertEqual(self.store.pending_stream_observation('session'),event)


if __name__=='__main__':unittest.main()
