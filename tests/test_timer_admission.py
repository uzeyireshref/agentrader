"""Timer admission uses temporary journals and the existing fake exchange only."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_cancel_timers as timers
import test_bot_terminal as terminal
from agentrader.application.bot_worker import timer_job_admission,process_bot_once
from agentrader.application.bot_inbox import BotError


class TimerAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.f=timers.CancelTimerTests();self.f.setUp();self.addCleanup(self.f.tearDown)
        p,_,tid=self.f.arm()
        self.timers={tid:p['digest']};self.engine=SimpleNamespace(commands=self.f.commands)
        self.inbox=Mock()
        self.job=dict(action='SNAPSHOT',payload=json.dumps({'symbol':'BTCUSDT'}))

    def test_near_heartbeat_refuses_without_sending_or_extending_lease(self):
        before=self.f.store.db.execute('SELECT * FROM cancel_timers').fetchone()
        count=len(self.f.x.calls)
        with self.assertRaisesRegex(BotError,'BOT_TIMER_PRIORITY_REQUIRED'):
            timer_job_admission(self.engine,self.timers,self.inbox,self.job)
        self.assertEqual(len(self.f.x.calls),count)
        self.assertEqual(dict(self.f.store.db.execute('SELECT * FROM cancel_timers').fetchone()),dict(before))
        timer_job_admission(self.engine,self.timers,self.inbox,self.job,now_ms=before['last_attempt_ms'],budget_ms=999)
        with self.assertRaisesRegex(BotError,'PRIORITY'):
            timer_job_admission(self.engine,self.timers,self.inbox,self.job,now_ms=before['last_attempt_ms'],budget_ms=1000)

    def test_expiry_rollback_and_wrong_source_never_extend_authority(self):
        for shift in (-1,31000):
            row=self.f.store.db.execute('SELECT * FROM cancel_timers').fetchone()
            with self.assertRaisesRegex(BotError,'PRIORITY'):
                timer_job_admission(self.engine,self.timers,self.inbox,self.job,now_ms=row['last_attempt_ms']+shift)
        with self.assertRaisesRegex(BotError,'CONTEXT'):
            timer_job_admission(self.engine,{next(iter(self.timers)):'wrong'},self.inbox,self.job)

    def test_timer_query_and_disable_review_remain_available(self):
        for op in (timers.DISABLE,timers.QUERY):
            job=dict(action='PREVIEW_COMMAND',payload=json.dumps({'operation':op}))
            timer_job_admission(self.engine,self.timers,self.inbox,job)
            prepared=self.f.commands.prepare(self.f.request(op,key='admit-'+op,timer_id=next(iter(self.timers))))
            self.inbox.row.return_value=dict(action='PREVIEW_COMMAND',result=json.dumps(dict(kind='COMMAND',payload={'command_id':prepared['command_id']})))
            timer_job_admission(self.engine,self.timers,self.inbox,dict(action='CONFIRM',payload=json.dumps({'review_id':'review'})))
        self.assertEqual(len(self.f.posts()),1)  # initial arm only


class WorkerAdmissionTests(unittest.TestCase):
    def test_refused_job_finishes_explicitly_before_perform_and_is_not_replayed(self):
        f=terminal.BotTerminalTests();f.setUp();self.addCleanup(f.doCleanups)
        job=f.job('CONTEXT',{})
        perform=Mock(side_effect=AssertionError('must not run'))
        f.engine.perform=perform
        def refuse(engine,job):raise BotError('BOT_TIMER_PRIORITY_REQUIRED',409)
        result=process_bot_once(f.inbox,factory=f.factory,admission=refuse)
        self.assertEqual(result['state'],'FAILED')
        self.assertEqual(result['error_code'],'BOT_TIMER_PRIORITY_REQUIRED')
        self.assertFalse(result['automatic_resend'])
        self.assertIsNone(process_bot_once(f.inbox,factory=f.factory))
        self.assertEqual(f.inbox.show(job['job_id'])['state'],'FAILED')
        perform.assert_not_called()
