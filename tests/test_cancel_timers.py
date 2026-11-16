import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agentrader.bot.cancel_timers import SET,REFRESH,DISABLE,QUERY,PATH,tick,view,assert_entry_allowed
from agentrader.bot.exchange_commands import ExchangeCommands,validate_command
from agentrader.bot.plans import PlanService
from agentrader.bot.risk import RiskLimits,number
from agentrader.bot.v2_runner import V2Runner
from agentrader.shared.state import StateStore
from test_cancel_scope_commands import CancelExchange
from test_plan_v2 import plan_v2


class CancelTimerTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.path=Path(self.folder.name)/'state.db';self.store=StateStore(self.path)
        self.x=CancelExchange();self.owner='local:g07';self.commands=ExchangeCommands(self.x,self.store,self.owner)
        self.clock=[time.time()];self.time_patch=patch('time.time',side_effect=lambda:self.clock[0]);self.time_patch.start()
    def tearDown(self):self.time_patch.stop();self.store.close();self.folder.cleanup()
    def request(self,op=SET,key='timer',timer_id=None):
        return dict(schema_version=1,client_command_id=key,environment='demo',exchange='binance',product='USD-M',account_ref=self.commands.account_ref,
            operation=op,scope={'symbol':'BTCUSDT'},parameters=dict(countdown_ms=6000,heartbeat_ms=1000,lease_ms=30000,acknowledge_symbol_wide=True) if op==SET else {'timer_id':timer_id})
    def arm(self):
        p=self.commands.prepare(self.request());r=self.commands.apply(p['command_id'],p['digest'],execute=True)
        return p,r,r['result']['timer_id']
    def command(self,op,timer_id,key):
        p=self.commands.prepare(self.request(op,key,timer_id));return p,self.commands.apply(p['command_id'],p['digest'],execute=True)
    def posts(self):return [p for m,path,p in self.x.calls if m=='POST' and path==PATH]
    def advance(self,seconds):self.clock[0]+=seconds
    def test_set_preview_and_duplicate_do_not_send_or_extend_lease(self):
        p=self.commands.prepare(self.request());self.assertEqual(self.posts(),[]);lease=p['prepared_details']['timer']['lease_until_ms']
        self.advance(1)
        with patch.object(self.x,'get',side_effect=AssertionError('duplicate local')):q=self.commands.prepare(self.request())
        self.assertEqual(q['prepared_details']['timer']['lease_until_ms'],lease)
    def test_arm_ack_query_and_duplicate_apply(self):
        p,r,tid=self.arm();self.assertEqual(r['state'],'APPLIED');self.assertEqual(r['result']['state'],'ACTIVE')
        self.commands.apply(p['command_id'],p['digest'],execute=True);_,q=self.command(QUERY,tid,'query')
        self.assertEqual(q['state'],'APPLIED');self.assertFalse(q['result']['remote_status_get_available']);self.assertEqual(len(self.posts()),1)
    def test_explicit_symbol_wide_lease_bounds(self):
        for field,value in (('acknowledge_symbol_wide',False),('countdown_ms',True),('heartbeat_ms',6000),('lease_ms',600001)):
            request=self.request();request['parameters'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_command(request)
    def test_known_position_or_algo_prevents_timer(self):
        self.x.amounts['BTCUSDT']=number('.001')
        with self.assertRaises(ValueError):self.commands.prepare(self.request())
        self.x.amounts['BTCUSDT']=number(0);self.x.add_algo('protect')
        with self.assertRaises(ValueError):self.commands.prepare(self.request())
        self.assertEqual(self.posts(),[])
    def test_managed_pending_entry_prevents_timer(self):
        service=PlanService(self.store,self.owner);p=plan_v2();p['entry'].update(condition='LIMIT',trigger_price='80000')
        created=service.create(p,self.owner);service.authorize(p['plan_id'],1,created['authorization_token'],'approve',self.owner)
        from agentrader.bot.v2_preflight import collect_flat_snapshot
        self.x.limit_pending=True
        with patch('agentrader.bot.v2_runner.collect_flat_snapshot',side_effect=lambda *a,**kw:collect_flat_snapshot(*a,clock=lambda:self.clock[0],**kw)):
            V2Runner(service,self.x,RiskLimits()).open(p['plan_id'],1,True)
        with self.assertRaises(ValueError):self.commands.prepare(self.request())
    def test_timer_blocks_new_plan_before_authority_consumption(self):
        self.arm();service=PlanService(self.store,self.owner);plan=plan_v2();plan['entry'].update(condition='IMMEDIATE',trigger_price=None)
        p=service.create(plan,self.owner);service.authorize(plan['plan_id'],1,p['authorization_token'],'approve',self.owner)
        with self.assertRaises(ValueError):V2Runner(service,self.x,RiskLimits()).open(plan['plan_id'],1,True)
        self.assertEqual(service.show(plan['plan_id'],1)['state'],'AUTHORIZED')
    def test_database_barrier_blocks_raw_opening_intent_but_allows_reduction(self):
        self.arm();params={'symbol':'BTCUSDT','side':'BUY','positionSide':'BOTH','type':'MARKET','quantity':'.001'}
        self.assertFalse(self.store.reserve('raw-open','/fapi/v1/order',params))
        self.assertTrue(self.store.reserve('raw-close','/fapi/v1/order',params|{'side':'SELL','reduceOnly':'true'}))
        self.assertTrue(self.store.reserve('hedge-close','/fapi/v1/order',params|{'positionSide':'SHORT'}))
    def test_disable_ack_removes_barrier(self):
        _,_,tid=self.arm();_,r=self.command(DISABLE,tid,'disable')
        self.assertEqual(r['state'],'APPLIED');self.assertEqual(r['result']['state'],'DISABLED')
        assert_entry_allowed(self.store,'BTCUSDT',self.commands.account_ref)
        self.assertEqual(self.posts()[-1]['countdownTime'],0)
    def test_tick_requires_digest_and_execute_and_waits_until_due(self):
        p,_,tid=self.arm()
        with self.assertRaises(ValueError):tick(self.commands,tid,'wrong',execute=True)
        with self.assertRaises(ValueError):tick(self.commands,tid,p['digest'])
        self.assertEqual(tick(self.commands,tid,p['digest'],execute=True)['worker_state'],'WAITING');self.assertEqual(len(self.posts()),1)
    def test_heartbeat_ack_has_durable_sequence_and_fixed_lease(self):
        p,r,tid=self.arm();lease=r['result']['lease_until_ms'];self.advance(1.1)
        result=tick(self.commands,tid,p['digest'],execute=True)
        self.assertEqual(result['worker_state'],'REFRESHED');self.assertEqual(result['timer']['sequence'],2)
        self.assertEqual(result['timer']['lease_until_ms'],lease)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM cancel_timer_attempts WHERE state='ACK'").fetchone()[0],2)
    def test_lost_arm_response_never_retries_and_does_not_claim_expiry(self):
        self.x.timer_lost=True;p,r,tid=self.arm();self.assertEqual(r['state'],'UNKNOWN')
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.commands.reconcile(p['command_id']);self.assertEqual(len(self.posts()),1)
        self.advance(60);v=view(self.commands,tid);self.assertFalse(v['remote_expiry_proven']);self.assertTrue(v['new_entries_blocked'])
        self.assertEqual(tick(self.commands,tid,p['digest'],execute=True)['worker_state'],'STOPPED_UNCERTAIN')
    def test_lost_refresh_stops_worker_and_holds_entry_barrier(self):
        p,_,tid=self.arm();self.advance(1.1);self.x.timer_lost=True
        self.assertEqual(tick(self.commands,tid,p['digest'],execute=True)['worker_state'],'STOPPED_UNCERTAIN')
        n=len(self.posts());self.advance(1.1);tick(self.commands,tid,p['digest'],execute=True);self.assertEqual(len(self.posts()),n)
        with self.assertRaises(ValueError):assert_entry_allowed(self.store,'BTCUSDT')
    def test_unknown_disable_waits_for_old_acceptance_window_then_needs_new_command(self):
        self.x.timer_lost=True;_,_,tid=self.arm();self.x.timer_lost=False
        _,result=self.command(DISABLE,tid,'early');self.assertEqual(result['state'],'NOT_SENT');self.assertEqual(len(self.posts()),1)
        self.advance(16);_,result=self.command(DISABLE,tid,'settled');self.assertEqual(result['state'],'APPLIED');self.assertEqual(result['result']['state'],'DISABLED')
    def test_lease_end_and_missed_heartbeat_do_not_rearm_after_restart(self):
        p,_,tid=self.arm();self.advance(7)
        self.store.close();self.store=StateStore(self.path);self.commands=ExchangeCommands(self.x,self.store,self.owner)
        self.assertEqual(tick(self.commands,tid,p['digest'],execute=True)['worker_state'],'DEADLINE_PASSED');self.assertEqual(len(self.posts()),1)
        self.advance(30);self.assertEqual(tick(self.commands,tid,p['digest'],execute=True)['worker_state'],'LEASE_ENDED')
        self.assertFalse(view(self.commands,tid)['remote_expiry_proven'])
    def test_new_position_causes_safe_heartbeat_pause(self):
        p,_,tid=self.arm();self.x.amounts['BTCUSDT']=number('.001');self.advance(1.1)
        self.assertEqual(tick(self.commands,tid,p['digest'],execute=True)['worker_state'],'STOPPED_UNSAFE')
        self.assertEqual(view(self.commands,tid)['state'],'PAUSED_UNSAFE');self.assertEqual(len(self.posts()),1)
    def test_wrong_ack_is_unknown_and_secret_error_is_not_logged(self):
        self.x.timer_bad_ack=True;_,r,_=self.arm();self.assertEqual(r['state'],'UNKNOWN')
        self.assertNotIn('SECRET_CANARY',json.dumps(r))
    def test_clock_rollback_does_not_send_heartbeat(self):
        p,_,tid=self.arm();self.advance(-1)
        self.assertEqual(tick(self.commands,tid,p['digest'],execute=True)['worker_state'],'CLOCK_ROLLBACK');self.assertEqual(len(self.posts()),1)
    def test_definitive_refresh_rejection_stops_renewal(self):
        p,_,tid=self.arm();self.advance(1.1);self.x.timer_reject=True
        self.assertEqual(tick(self.commands,tid,p['digest'],execute=True)['worker_state'],'STOPPED_UNCERTAIN')
        self.assertEqual(view(self.commands,tid)['state'],'REFRESH_FAILED');self.assertTrue(view(self.commands,tid)['new_entries_blocked'])
    def test_account_scope_and_second_arm_are_rejected(self):
        _,_,tid=self.arm();p=self.commands.prepare(self.request(key='other'))
        self.assertEqual(self.commands.apply(p['command_id'],p['digest'],execute=True)['state'],'NOT_SENT')
        from agentrader.shared.config import Config
        self.x.config=Config('different-key','secret');other=ExchangeCommands(self.x,self.store,self.owner)
        with self.assertRaises(ValueError):view(other,tid)
    def test_failed_disable_stops_renewal_and_keeps_barrier(self):
        p,_,tid=self.arm();self.x.timer_reject=True
        _,r=self.command(DISABLE,tid,'disable-failed')
        self.assertEqual(r['result']['state'],'DISABLE_FAILED');n=len(self.posts());self.advance(1.1)
        self.assertEqual(tick(self.commands,tid,p['digest'],execute=True)['worker_state'],'STOPPED_UNCERTAIN')
        self.assertEqual(len(self.posts()),n);self.assertTrue(view(self.commands,tid)['new_entries_blocked'])
    def test_corrupted_attempt_blocks_view_and_heartbeat(self):
        p,_,tid=self.arm()
        with self.store.db:self.store.db.execute("UPDATE cancel_timer_attempts SET digest='corrupt'")
        self.advance(1.1)
        with self.assertRaises(ValueError):view(self.commands,tid)
        with self.assertRaises(ValueError):tick(self.commands,tid,p['digest'],execute=True)
        self.assertEqual(len(self.posts()),1)
    def test_cli_worker_requires_explicit_start_and_does_not_hold_lock_during_sleep(self):
        import io
        from contextlib import redirect_stdout
        from contextlib import contextmanager
        from agentrader.cli.exchange_command_cli import main
        p,_,tid=self.arm();held=[False]
        @contextmanager
        def lock():
            self.assertFalse(held[0]);held[0]=True
            try:yield
            finally:held[0]=False
        def sleep(seconds):self.assertFalse(held[0]);self.advance(seconds)
        output=io.StringIO()
        with patch('agentrader.cli.exchange_command_cli.Config.load',return_value=self.x.config),patch('agentrader.cli.exchange_command_cli.DemoExchange',return_value=self.x),patch('agentrader.cli.exchange_command_cli.getpass.getuser',return_value='g07'),patch('agentrader.cli.exchange_command_cli.execution_lock',side_effect=lock),patch('agentrader.cli.exchange_command_cli.time.sleep',side_effect=sleep),redirect_stdout(output):
            code=main(['--database',str(self.path),'timer-run',tid,'--digest',p['digest'],'--execute-demo','--iterations','2'])
        self.assertEqual(code,0,output.getvalue());self.assertEqual(len(self.posts()),2)
