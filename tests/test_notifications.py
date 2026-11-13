import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError,URLError

from agentrader.notifications import NotificationQueue,TelegramSender,DeliveryError
from agentrader.runtime import supervise_session
from agentrader.state import StateStore


TOKEN='123456:'+('private-canary-'*3)


class OutboxTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.db'
        self.store=StateStore(self.path);self.now=100
        self.queue=NotificationQueue(self.store,clock=lambda:self.now)
        self.sender=Mock();self.sender.send.return_value={'message_id':7}
    def tearDown(self):self.store.close();self.temp.cleanup()

    def test_identity_dedup_and_success_are_durable(self):
        self.queue.enqueue('alarm-1','123','rapor')
        self.assertEqual(self.queue.enqueue('alarm-1','123','rapor')['state'],'ALREADY_QUEUED')
        with self.assertRaises(ValueError):self.queue.enqueue('alarm-1','123','different')
        self.assertEqual(self.queue.deliver_one(self.sender)['state'],'DELIVERED')
        self.store.close();self.store=StateStore(self.path);self.queue=NotificationQueue(self.store)
        self.assertEqual(self.queue.deliver_one(self.sender)['state'],'IDLE')
        self.assertEqual(self.sender.send.call_count,1)

    def test_retry_after_is_persistent_and_bounded(self):
        self.queue.enqueue('alarm-1','123','rapor');self.sender.send.side_effect=DeliveryError(retry_after=30)
        self.assertEqual(self.queue.deliver_one(self.sender)['state'],'RETRY')
        self.now=129;self.assertEqual(self.queue.deliver_one(self.sender)['state'],'IDLE')
        self.now=130;self.sender.send.side_effect=None
        self.assertEqual(self.queue.deliver_one(self.sender)['state'],'DELIVERED')

    def test_crashed_sender_lease_blocks_concurrent_delivery_then_recovers(self):
        self.queue.enqueue('alarm-1','123','rapor');self.queue._claim()
        other=StateStore(self.path)
        try:
            worker=NotificationQueue(other,clock=lambda:self.now)
            self.assertEqual(worker.deliver_one(self.sender)['state'],'IDLE')
            self.now=161
            self.assertEqual(worker.deliver_one(self.sender)['state'],'DELIVERED')
        finally:other.close()

    def test_permanent_failure_is_visible_and_not_retried(self):
        self.queue.enqueue('alarm-1','123','rapor');self.sender.send.side_effect=DeliveryError(retryable=False)
        self.assertEqual(self.queue.deliver_one(self.sender)['state'],'FAILED')
        self.assertEqual(self.queue.status(),{'FAILED':1})
        self.assertEqual(self.queue.deliver_one(self.sender)['state'],'IDLE')

    def test_runtime_records_actions_without_sending_or_repeating_routine_status(self):
        runner=Mock();runner.manage.return_value={'state':'MANAGING','session_id':'s','quantity':'1'}
        supervise_session(runner,'s',emit=Mock(),iterations=2,sleep=Mock(),
                          notification_queue=self.queue,notification_chat='123')
        self.assertEqual(self.queue.status(),{'PENDING':1})
        self.sender.send.assert_not_called();runner.open.assert_not_called()


class TelegramSenderTests(unittest.TestCase):
    def setUp(self):
        self.opener=Mock();self.sender=TelegramSender(TOKEN,'123',opener=self.opener)
    def test_response_must_match_configured_chat_and_message_id(self):
        self.opener.open.return_value=io.BytesIO(json.dumps({'ok':True,'result':{'message_id':7,'chat':{'id':123}}}).encode())
        self.assertEqual(self.sender.send('123','rapor'),{'message_id':7})
        with self.assertRaises(DeliveryError):self.sender.send('999','rapor')
        self.assertEqual(self.opener.open.call_count,1)
    def test_network_error_redacts_token_and_private_url(self):
        self.opener.open.side_effect=URLError('https://api.telegram.org/bot'+TOKEN)
        with self.assertRaises(DeliveryError) as caught:self.sender.send('123','rapor')
        self.assertNotIn(TOKEN,str(caught.exception))
        self.assertEqual(self.opener.open.call_count,1)
    def test_telegram_rate_limit_retains_retry_after(self):
        self.opener.open.side_effect=HTTPError('private',429,'',{},io.BytesIO(b'{"parameters":{"retry_after":42}}'))
        with self.assertRaises(DeliveryError) as caught:self.sender.send('123','rapor')
        self.assertEqual(caught.exception.retry_after,42)
    def test_wrong_chat_in_response_is_not_marked_delivered(self):
        self.opener.open.return_value=io.BytesIO(b'{"ok":true,"result":{"message_id":7,"chat":{"id":999}}}')
        with self.assertRaises(DeliveryError):self.sender.send('123','rapor')
