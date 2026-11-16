import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentrader.bot.exchange_commands import ExchangeCommands
from agentrader.bot.plans import PlanService,example_plan
from agentrader.bot.plan_execution import run_plan
from agentrader.bot.risk import RiskLimits
from agentrader.bot.watchdog import Watchdog
from agentrader.shared.state import StateStore
from test_plans import PlanExchange


class LegacyCommandBridgeTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.path=Path(self.folder.name)/'state.db'
        self.store=StateStore(self.path);self.service=PlanService(self.store,'owner');self.x=PlanExchange()
        p=example_plan();self.plan_id=p['plan_id'];created=self.service.create(p,'owner')
        self.service.authorize(self.plan_id,1,created['authorization_token'],'approve','owner')
        self.commands=ExchangeCommands(self.x,self.store,'owner')
    def tearDown(self):self.store.close();self.folder.cleanup()
    def run_plan(self,execute=True):return run_plan(self.service,self.x,RiskLimits(),self.plan_id,1,execute)
    def only(self):
        values=self.commands.list()['commands'];self.assertEqual(len(values),1);return values[0]
    def test_normal_entry_links_existing_identity_and_protected_outcome(self):
        result=self.run_plan();command=self.only();plan=self.service.show(self.plan_id,1)
        self.assertEqual(result['exchange_command']['command_id'],command['command_id'])
        self.assertEqual(command['state'],'APPLIED');self.assertEqual(command['result']['action_id'],plan['action_id'])
        self.assertEqual(command['result']['session_id'],plan['session_id']);self.assertEqual(command['result']['plan_state'],'MANAGING')
        self.assertEqual(command['result']['entry_state'],'FILLED')
        entries=[p for m,path,p in self.x.calls if m=='POST' and path.endswith('/order') and p.get('reduceOnly')!='true']
        self.assertEqual(len(entries),1);self.assertEqual(entries[0]['newClientOrderId'],plan['action_id'])
    def test_preview_does_not_claim_command_or_plan(self):
        self.assertEqual(self.run_plan(False)['state'],'READY');self.assertEqual(self.commands.list()['commands'],[])
        self.assertEqual(self.service.show(self.plan_id,1)['state'],'AUTHORIZED');self.assertEqual(self.x.calls,[])
    def test_atomic_parent_failure_rolls_back_plan_claim(self):
        self.store.db.execute("CREATE TRIGGER fail_bridge BEFORE INSERT ON exchange_commands BEGIN SELECT RAISE(ABORT,'crash'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.run_plan()
        self.assertEqual(self.service.show(self.plan_id,1)['state'],'AUTHORIZED')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM plan_actions').fetchone()[0],0)
        self.assertEqual(self.x.calls,[])
    def test_crash_after_atomic_claim_never_reenters(self):
        original=self.commands.claim_plan
        def crash(*args):original(*args);raise RuntimeError('process lost')
        with patch.object(ExchangeCommands,'claim_plan',side_effect=crash):
            with self.assertRaises(RuntimeError):self.run_plan()
        command=self.only();self.assertEqual(command['state'],'SUBMITTING')
        self.store.close();self.store=StateStore(self.path);self.service=PlanService(self.store,'owner')
        self.commands=ExchangeCommands(self.x,self.store,'owner')
        r=self.commands.reconcile(command['command_id']);self.assertEqual(r['state'],'UNKNOWN')
        self.assertEqual(r['result']['entry_state'],'NO_RECORDED_INTENT')
        with self.assertRaises(ValueError):self.run_plan()
        with self.assertRaises(ValueError):self.commands.apply(command['command_id'],command['digest'],execute=True)
        self.assertEqual(self.x.calls,[])
    def test_crash_after_plan_success_recovers_journal_without_network(self):
        original=ExchangeCommands.finish_plan
        with patch.object(ExchangeCommands,'finish_plan',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.run_plan()
        command=self.only();n=len(self.x.calls)
        self.assertEqual(self.service.show(self.plan_id,1)['state'],'MANAGING')
        with patch.object(self.x,'get',side_effect=AssertionError('no network')):
            self.assertEqual(original(self.commands,command['command_id'])['state'],'APPLIED')
        self.assertEqual(len(self.x.calls),n)
    def test_failed_execution_stays_unknown_without_repost(self):
        with patch.object(Watchdog,'open',side_effect=RuntimeError('failure before entry')):
            with self.assertRaises(RuntimeError):self.run_plan()
        command=self.only();self.assertEqual(command['state'],'UNKNOWN')
        self.assertEqual(command['result']['plan_state'],'NEEDS_REVIEW')
        self.commands.reconcile(command['command_id']);self.assertEqual(self.x.calls,[])
        with self.assertRaises(ValueError):self.run_plan()
    def test_internal_operation_cannot_be_prepared_or_reapplied(self):
        self.run_plan();command=self.only()
        with self.assertRaises(ValueError):self.commands.prepare(command['request'])
        with self.assertRaises(ValueError):self.commands.apply(command['command_id'],command['digest'],execute=True)
    def test_list_and_reconcile_enforce_account_scope(self):
        from agentrader.shared.config import Config
        self.run_plan();command=self.only();self.x.config=Config('other-key','secret')
        other=ExchangeCommands(self.x,self.store,'owner');self.assertEqual(other.list()['commands'],[])
        with self.assertRaises(ValueError):other.reconcile(command['command_id'])
    def test_link_tampering_does_not_resolve_other_execution(self):
        with patch.object(Watchdog,'open',side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):self.run_plan()
        command=self.only()
        with self.store.db:self.store.db.execute("UPDATE plan_versions SET action_id='other'")
        with self.assertRaises(ValueError):self.commands.reconcile(command['command_id'])
    def test_late_recovery_after_verified_close_is_resolved(self):
        with patch.object(ExchangeCommands,'finish_plan',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.run_plan()
        Watchdog(self.x,self.store).tick(True,close=True)
        command=self.only();self.assertEqual(command['state'],'SUBMITTING')
        count=len(self.x.calls);resolved=self.commands.reconcile(command['command_id'])
        self.assertEqual(resolved['state'],'APPLIED');self.assertEqual(resolved['result']['plan_state'],'CLOSED')
        self.assertEqual(len(self.x.calls),count)
