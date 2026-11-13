import unittest
from unittest.mock import Mock

from agentrader.exchange import ExchangeError
from agentrader.runtime import monitor_session,supervise_session,stream_monitor_session
from agentrader.user_stream import StreamUnavailable, StreamProtocolError


class RuntimeTests(unittest.TestCase):
    def test_continuous_mode_stops_when_owned_session_closes(self):
        runner=Mock();runner.manage.side_effect=[{'state':'ENTRY_PENDING'},{'state':'MANAGING'},{'state':'CLOSED'}]
        sleep=Mock()
        rows=list(monitor_session(runner,'session',execute=True,iterations=0,interval=3,sleep=sleep))
        self.assertEqual([r['monitor_turn'] for r in rows],[1,2,3])
        self.assertEqual(sleep.call_count,2)
        runner.open.assert_not_called()
        runner.manage.assert_called_with('session',execute=True)

    def test_uncertain_failure_stops_without_retry_or_reentry(self):
        runner=Mock();runner.manage.side_effect=ExchangeError('unknown',delivery_status='UNKNOWN')
        sleep=Mock()
        with self.assertRaises(ExchangeError):list(monitor_session(runner,'session',execute=True,iterations=0,sleep=sleep))
        self.assertEqual(runner.manage.call_count,1)
        runner.open.assert_not_called();sleep.assert_not_called()

    def test_single_read_only_turn_does_not_sleep(self):
        runner=Mock();runner.manage.return_value={'state':'PROTECTION_REQUIRED'}
        sleep=Mock()
        self.assertEqual(len(list(monitor_session(runner,'session',sleep=sleep))),1)
        runner.manage.assert_called_once_with('session',execute=False)
        sleep.assert_not_called()

    def test_invalid_schedule_cannot_touch_session(self):
        for kwargs in ({'iterations':-1},{'iterations':True},{'interval':0},{'interval':61}):
            runner=Mock()
            with self.assertRaises(ValueError):list(monitor_session(runner,'session',**kwargs))
            runner.manage.assert_not_called()

    def test_bounded_grid_monitor_drains_remaining_entries(self):
        runner=Mock();runner.manage.return_value={'state':'GRID_RUNNING'}
        runner.stop.return_value={'state':'GRID_DRAINING'};emit=Mock()
        supervise_session(runner,'s',emit=emit,execute=True,drain_on_exit=True)
        runner.stop.assert_called_once_with('s',close_position=False,execute=True)

    def test_closed_grid_does_not_attempt_second_stop(self):
        runner=Mock();runner.manage.return_value={'state':'CLOSED'}
        supervise_session(runner,'s',emit=Mock(),execute=True,drain_on_exit=True)
        runner.stop.assert_not_called()


class StreamRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.runner = Mock()
        self.runner.manage.return_value = {'state': 'MANAGING'}
        self.runner.store.pending_stream_observation.return_value = None
        self.stream = Mock(generation=0)
        def connect():
            self.stream.generation += 1
            return {'state': 'STREAM_CONNECTED', 'generation': self.stream.generation}
        self.stream.connect.side_effect = connect
        self.stream.wait.return_value = None
        self.sleep = Mock()

    def run_monitor(self, iterations=1, **options):
        return list(stream_monitor_session(self.runner, 's', stream=self.stream,
                    execute=True, iterations=iterations, sleep=self.sleep, **options))

    def test_first_connection_requires_read_only_barrier_before_execution(self):
        rows = self.run_monitor()
        self.assertEqual([c.kwargs['execute'] for c in self.runner.manage.call_args_list], [False, True])
        self.assertEqual([r['state'] for r in rows], ['STREAM_CONNECTED', 'STREAM_RECONCILED', 'MANAGING'])
        self.runner.open.assert_not_called()
        self.stream.close.assert_called()

    def test_reconnect_repeats_barrier_and_does_not_repeat_uncertain_mutation(self):
        self.stream.wait.side_effect = StreamUnavailable('offline')
        rows = self.run_monitor(iterations=2)
        self.assertEqual([c.kwargs['execute'] for c in self.runner.manage.call_args_list], [False, True, False, True])
        self.assertEqual(rows[-1]['stream_generation'], 2)

    def test_ownership_failure_after_reconnect_blocks_all_further_execution(self):
        self.runner.manage.side_effect = [{'state': 'MANAGING'}, {'state': 'MANAGING'}, ValueError('foreign fill')]
        self.stream.wait.side_effect = StreamUnavailable('offline')
        with self.assertRaises(ValueError): self.run_monitor(iterations=2)
        self.assertEqual([c.kwargs['execute'] for c in self.runner.manage.call_args_list], [False, True, False])

    def test_unknown_order_delivery_is_not_a_reconnectable_stream_failure(self):
        self.runner.manage.side_effect = [{'state': 'MANAGING'}, ExchangeError('uncertain', delivery_status='UNKNOWN')]
        with self.assertRaises(ExchangeError): self.run_monitor(iterations=2)
        self.assertEqual(self.stream.connect.call_count, 1)
        self.assertEqual(self.runner.manage.call_count, 2)
        self.sleep.assert_not_called()

    def test_network_reconnect_budget_is_finite_and_no_runner_before_connection(self):
        self.stream.connect.side_effect = StreamUnavailable('offline')
        with self.assertRaises(StreamUnavailable): self.run_monitor(iterations=0)
        self.assertEqual(self.stream.connect.call_count, 4)
        self.runner.manage.assert_not_called()
        self.runner.store.halt.assert_called_once()

    def test_renewal_failures_also_have_finite_budget(self):
        self.stream.maintain.side_effect = StreamUnavailable('expired')
        with self.assertRaises(StreamUnavailable): self.run_monitor(iterations=0)
        self.assertEqual(self.stream.connect.call_count, 4)
        self.assertTrue(all(not c.kwargs['execute'] for c in self.runner.manage.call_args_list))

    def test_normalized_event_is_audited_then_rest_rechecked(self):
        event = {'kind': 'ACCOUNT_UPDATE', 'event_id': 'safe-hash'}
        self.stream.wait.return_value = event
        self.run_monitor(iterations=2)
        self.runner.store.save_stream_observation.assert_called_once_with('s', event)
        self.assertEqual(self.runner.manage.call_count, 4)

    def test_malformed_event_stops_and_persists_halt(self):
        self.stream.wait.side_effect = StreamProtocolError('invalid')
        with self.assertRaises(StreamProtocolError): self.run_monitor(iterations=2)
        self.assertEqual(self.runner.manage.call_count, 2)
        self.runner.store.halt.assert_called_once()

    def test_closed_baseline_does_not_mutate_or_drain_again(self):
        self.runner.manage.return_value = {'state': 'CLOSED'}
        supervise_session(self.runner, 's', user_stream=self.stream, emit=Mock(),
                          execute=True, drain_on_exit=True)
        self.runner.manage.assert_called_once_with('s', execute=False)
        self.runner.stop.assert_not_called()

    def test_invalid_schedule_never_connects_or_touches_session(self):
        for kwargs in ({'iterations': -1}, {'interval': 0}, {'iterations': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_monitor(**kwargs)
        self.stream.connect.assert_not_called()
        self.runner.manage.assert_not_called()

    def event(self, **changes):
        event = dict(kind='ORDER_TRADE_UPDATE', event_id='safe-hash', symbol='BTCUSDT',
                     client_id='agt-1', order_id=42, side='BUY', status='FILLED', cumulative_filled='0.002')
        event.update(changes)
        return event

    def order(self, **changes):
        result = dict(symbol='BTCUSDT', clientOrderId='agt-1', orderId=42, side='BUY',
                      status='FILLED', executedQty='0.002')
        result.update(changes)
        return result

    def test_rest_lag_waits_for_fill_before_next_execution(self):
        self.stream.wait.return_value = self.event()
        self.runner.x.get.side_effect = [self.order(status='NEW', executedQty='0'), self.order()]
        self.run_monitor(iterations=2)
        self.assertEqual(self.runner.x.get.call_count, 2)
        self.sleep.assert_called_once_with(1)
        self.assertEqual([c.kwargs['execute'] for c in self.runner.manage.call_args_list], [False, True, False, True])

    def test_persistent_missing_fill_stops_without_second_execution(self):
        self.stream.wait.return_value = self.event()
        self.runner.x.get.return_value = self.order(status='NEW', executedQty='0')
        with self.assertRaises(StreamProtocolError): self.run_monitor(iterations=2)
        self.assertEqual(self.runner.x.get.call_count, 3)
        self.assertEqual(self.runner.manage.call_count, 2)
        self.runner.store.halt.assert_called_once()

    def test_cancellation_must_be_terminal_in_rest_before_execution(self):
        self.stream.wait.return_value = self.event(status='CANCELED', cumulative_filled='0')
        self.runner.x.get.return_value = self.order(status='NEW', executedQty='0')
        with self.assertRaises(StreamProtocolError): self.run_monitor(iterations=2)
        self.assertEqual(self.runner.manage.call_count, 2)

    def test_stream_order_identity_mismatch_cannot_authorize_management(self):
        self.stream.wait.return_value = self.event()
        self.runner.x.get.return_value = self.order(orderId=999)
        with self.assertRaises(StreamProtocolError): self.run_monitor(iterations=2)
        self.assertEqual(self.runner.x.get.call_count, 1)
        self.assertEqual(self.runner.manage.call_count, 2)

    def test_temporary_missing_order_is_read_only_until_visible(self):
        self.stream.wait.return_value = self.event()
        self.runner.x.get.side_effect = [ExchangeError('missing', -2013), self.order()]
        self.run_monitor(iterations=2)
        self.assertEqual(self.runner.x.get.call_count, 2)
        self.runner.x.request.assert_not_called()

    def test_rest_failure_does_not_reconnect_or_resend_orders(self):
        self.stream.wait.return_value = self.event()
        self.runner.x.get.side_effect = ExchangeError('offline')
        with self.assertRaises(ExchangeError): self.run_monitor(iterations=2)
        self.assertEqual(self.stream.connect.call_count, 1)
        self.assertEqual(self.runner.manage.call_count, 2)

    def test_close_observed_during_event_barrier_exits_without_further_execution(self):
        self.stream.wait.return_value = {'kind': 'ACCOUNT_UPDATE', 'event_id': 'safe-hash'}
        self.runner.manage.side_effect = [{'state':'MANAGING'}, {'state':'MANAGING'}, {'state':'CLOSED'}]
        result = self.run_monitor(iterations=2)
        self.assertEqual(result[-1]['state'], 'CLOSED')
        self.assertEqual([c.kwargs['execute'] for c in self.runner.manage.call_args_list], [False, True, False])

    def test_algo_trigger_waits_for_child_and_fill_in_rest(self):
        event=dict(kind='ALGO_UPDATE',event_id='algo-hash',client_algo_id='agt-stop',
                   symbol='BTCUSDT',side='SELL',algo_id=7,algo_status='FINISHED',
                   actual_order_id=42,actual_filled='0.002')
        self.stream.wait.return_value=event
        base=dict(clientAlgoId='agt-stop',symbol='BTCUSDT',side='SELL',algoId=7)
        self.runner.x.get.side_effect=[dict(base,algoStatus='NEW',actualOrderId='',actualQty='0'),
                                      dict(base,algoStatus='FINISHED',actualOrderId='42',actualQty='0.002')]
        self.run_monitor(iterations=2)
        self.assertEqual(self.runner.x.get.call_count,2)
        self.runner.x.get.assert_called_with('/fapi/v1/algoOrder',{'clientAlgoId':'agt-stop'})
        self.assertEqual(self.runner.manage.call_count,4)

    def test_algo_child_mismatch_or_missing_fill_blocks_execution(self):
        event=dict(kind='ALGO_UPDATE',event_id='algo-hash',client_algo_id='agt-stop',
                   symbol='BTCUSDT',side='SELL',algo_id=7,algo_status='FINISHED',
                   actual_order_id=42,actual_filled='0.002')
        self.stream.wait.return_value=event
        self.runner.x.get.return_value=dict(clientAlgoId='agt-stop',symbol='BTCUSDT',side='SELL',
                                           algoId=7,algoStatus='FINISHED',actualOrderId='99',actualQty='0.002')
        with self.assertRaises(StreamProtocolError):self.run_monitor(iterations=2)
        self.assertEqual(self.runner.manage.call_count,2)

    def test_interrupt_attempts_to_cancel_grid_entries_then_propagates(self):
        runner=Mock();runner.manage.side_effect=KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            supervise_session(runner,'s',emit=Mock(),execute=True,drain_on_exit=True)
        runner.stop.assert_called_once_with('s',close_position=False,execute=True)

    def test_uncertain_failure_is_not_masked_by_an_automatic_stop_retry(self):
        runner=Mock();runner.manage.side_effect=ExchangeError('unknown')
        with self.assertRaises(ExchangeError):
            supervise_session(runner,'s',emit=Mock(),execute=True,drain_on_exit=True)
        runner.stop.assert_not_called()
