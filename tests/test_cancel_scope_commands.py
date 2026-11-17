import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agentrader.bot.cancel_commands import SELECTED,SYMBOL,ACCOUNT
from agentrader.bot.exchange_commands import ExchangeCommands
from agentrader.bot.plans import PlanService
from agentrader.bot.risk import RiskLimits,number
from agentrader.bot.v2_runner import V2Runner
from agentrader.shared.exchange import ExchangeError
from agentrader.shared.state import StateStore
from test_multi_session import MultiExchange
from test_plan_v2 import plan_v2


class CancelExchange(MultiExchange):
    def __init__(self):
        super().__init__();self.reject_ids=set();self.lost_ids=set();self.no_effect_ids=set();self.race_id=None
        self.timer_lost=False;self.timer_reject=False;self.timer_bad_ack=False;self.remote_timers={}
    def get(self,path,params=None):
        params=params or {}
        if path.endswith('/order') and 'orderId' in params:
            matches=[o for o in self.orders.values() if o['orderId']==params['orderId'] and o['symbol']==params['symbol']]
            if not matches:raise ExchangeError('missing',-2013)
            return copy.deepcopy(matches[0])
        if path.endswith('/algoOrder'):
            values=[a for a in self.algos.values() if ('algoId' not in params or a['algoId']==params['algoId']) and
                    ('clientAlgoId' not in params or a['clientAlgoId']==params['clientAlgoId'])]
            if len(values)!=1:raise ExchangeError('missing/ambiguous',-2013)
            return copy.deepcopy(values[0])
        return super().get(path,params)
    def request(self,method,path,params):
        if path.endswith('/countdownCancelAll'):
            self.calls.append((method,path,copy.deepcopy(params)))
            if self.timer_reject:raise ExchangeError('rejected',-2015,400,delivery_status='REJECTED')
            self.remote_timers[params['symbol']]=params['countdownTime']
            if self.timer_lost:raise ExchangeError('SECRET_CANARY lost timer',delivery_status='UNKNOWN')
            return {'symbol':'WRONG' if self.timer_bad_ack else params['symbol'],'countdownTime':str(params['countdownTime'])}
        if method=='DELETE':
            self.calls.append((method,path,copy.deepcopy(params)))
            if path.endswith('/algoOrder'):target=self.get(path,params);cid=target['clientAlgoId'];target=self.algos[cid]
            else:target=self.get(path,params);cid=target['clientOrderId'];target=self.orders[cid]
            if cid in self.reject_ids:raise ExchangeError('rejected',-2011,400,delivery_status='REJECTED')
            if cid in self.no_effect_ids:raise ExchangeError('unknown',delivery_status='UNKNOWN')
            if cid==self.race_id and not path.endswith('/algoOrder'):self.fill(cid)
            else:target['algoStatus' if path.endswith('/algoOrder') else 'status']='CANCELED'
            if cid in self.lost_ids:raise ExchangeError('lost',delivery_status='UNKNOWN')
            return {}
        return super().request(method,path,params)
    def add_normal(self,cid,symbol='BTCUSDT'):
        self.limit_pending=True
        self.request('POST','/fapi/v1/order',{'symbol':symbol,'side':'BUY','positionSide':'BOTH','type':'LIMIT',
            'price':'80000','quantity':'.0007','timeInForce':'GTC','newClientOrderId':cid})
    def add_algo(self,cid,symbol='BTCUSDT'):
        self.request('POST','/fapi/v1/algoOrder',{'symbol':symbol,'side':'SELL','positionSide':'BOTH','type':'STOP_MARKET',
            'quantity':'.0007','triggerPrice':'78000','workingType':'MARK_PRICE','algoType':'CONDITIONAL','reduceOnly':'true','clientAlgoId':cid})


class CancelScopeTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.path=Path(self.folder.name)/'state.db';self.store=StateStore(self.path)
        self.x=CancelExchange();self.owner='local:g07';self.commands=ExchangeCommands(self.x,self.store,self.owner)
    def tearDown(self):self.store.close();self.folder.cleanup()
    def request(self,op=SELECTED,key='cancel',foreign=True,targets=None,symbol='BTCUSDT'):
        return dict(schema_version=1,client_command_id=key,environment='demo',exchange='binance',product='USD-M',account_ref=self.commands.account_ref,
            operation=op,scope={'account_wide':True} if op==ACCOUNT else {'symbol':symbol},
            parameters={'include_foreign':foreign}|({'targets':targets or [{'namespace':'NORMAL','client_id':'manual'}]} if op==SELECTED else {}))
    def execute(self,request=None):
        p=self.commands.prepare(request or self.request());return p,self.commands.apply(p['command_id'],p['digest'],execute=True)
    def deletes(self):return [c for c in self.x.calls if c[0]=='DELETE']
    def managed(self,pending=False):
        service=PlanService(self.store,self.owner);plan=plan_v2();plan['entry'].update(condition='LIMIT' if pending else 'IMMEDIATE',trigger_price='80000' if pending else None)
        self.x.limit_pending=pending;created=service.create(plan,self.owner);service.authorize(plan['plan_id'],1,created['authorization_token'],'approve',self.owner)
        runner=V2Runner(service,self.x,RiskLimits());sid=runner.open(plan['plan_id'],1,True)['session_id'];return runner,runner._session(sid)
    def test_preview_displays_frozen_targets_without_mutations_and_duplicate_avoids_reads(self):
        self.x.add_normal('manual');n=len(self.x.calls);p=self.commands.prepare(self.request())
        self.assertEqual(len(self.x.calls),n);self.assertEqual(p['prepared_details']['cancellation']['targets'][0]['client_id'],'manual')
        with patch.object(self.x,'get',side_effect=AssertionError('duplicate must be local')):self.assertTrue(self.commands.prepare(self.request())['duplicate'])
    def test_selected_foreign_requires_explicit_scope(self):
        self.x.add_normal('manual')
        with self.assertRaises(ValueError):self.commands.prepare(self.request(foreign=False))
        self.assertEqual(self.deletes(),[])
    def test_selected_normal_and_algo_keep_separate_ids(self):
        self.x.add_normal('manual');self.x.add_algo('algo');targets=[{'namespace':'NORMAL','client_id':'manual'},{'namespace':'ALGO','client_id':'algo'}]
        _,r=self.execute(self.request(targets=targets));self.assertEqual(r['state'],'APPLIED');self.assertEqual(len(self.deletes()),2)
        self.assertTrue(any('orderId' in p for _,_,p in self.deletes()));self.assertTrue(any('algoId' in p for _,_,p in self.deletes()))
    def test_symbol_scope_does_not_include_new_or_other_symbol_orders(self):
        self.x.add_normal('manual');self.x.add_normal('eth','ETHUSDT');p=self.commands.prepare(self.request(SYMBOL))
        self.x.add_normal('late');r=self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(r['state'],'APPLIED');self.assertEqual(self.x.orders['late']['status'],'NEW');self.assertEqual(self.x.orders['eth']['status'],'NEW')
    def test_account_scope_cancels_both_namespaces_across_symbols(self):
        self.x.add_normal('manual');self.x.add_algo('eth-algo','ETHUSDT');_,r=self.execute(self.request(ACCOUNT))
        self.assertEqual(r['state'],'APPLIED');self.assertEqual(len(r['result']['orders']),2)
    def test_account_scope_requires_true_and_rejects_symbol_alias(self):
        r=self.request(ACCOUNT);r['scope']={'account_wide':False}
        with self.assertRaises(ValueError):self.commands.prepare(r)
        r['scope']={'symbol':'BTCUSDT'}
        with self.assertRaises(ValueError):self.commands.prepare(r)
    def test_owned_entry_cancel_revokes_reentry_without_new_position(self):
        runner,s=self.managed(True);request=self.request(foreign=False,targets=[{'namespace':'NORMAL','client_id':s['entry_id']}])
        _,r=self.execute(request);self.assertEqual(r['state'],'APPLIED')
        self.assertIsNotNone(self.store.db.execute('SELECT 1 FROM control WHERE name=?',('entry_revoked:'+s['entry_id'],)).fetchone())
        self.assertEqual(runner.manage(s['id'],True)['state'],'CLOSED')
    def test_managed_core_protections_cannot_be_selected_or_wide_canceled(self):
        runner,s=self.managed();cid=s['protections'][0]['params']['clientAlgoId']
        with self.assertRaises(ValueError):self.commands.prepare(self.request(targets=[{'namespace':'ALGO','client_id':cid}]))
        _,r=self.execute(self.request(SYMBOL));self.assertEqual(r['state'],'APPLIED');self.assertEqual(self.deletes(),[])
        self.assertEqual(len(r['result']['skipped']),2);self.assertEqual(runner.manage(s['id'],True)['state'],'MANAGING')
    def test_owned_only_scope_skips_foreign_orders(self):
        self.x.add_normal('manual');_,r=self.execute(self.request(SYMBOL,foreign=False))
        self.assertEqual(r['state'],'APPLIED');self.assertEqual(self.deletes(),[]);self.assertEqual(r['result']['skipped'][0]['reason'],'FOREIGN_NOT_AUTHORIZED')
    def test_changed_fingerprint_blocks_entire_group_before_deletion(self):
        self.x.add_normal('manual');self.x.add_normal('other');p=self.commands.prepare(self.request(SYMBOL))
        self.x.orders['other']['price']='79900';r=self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(r['state'],'NOT_SENT');self.assertEqual(self.deletes(),[])
    def test_reused_client_id_cannot_cancel_new_broker_order(self):
        self.x.add_normal('manual');p=self.commands.prepare(self.request());self.x.orders['manual']['orderId']+=100
        r=self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(r['state'],'NOT_SENT');self.assertEqual(self.deletes(),[])
    def test_fill_cancel_race_reports_fill_and_does_not_claim_flat(self):
        self.x.add_normal('manual');self.x.race_id='manual';_,r=self.execute()
        self.assertEqual(r['state'],'APPLIED');self.assertEqual(r['result']['orders'][0]['status'],'FILLED')
        self.assertGreater(number(r['result']['orders'][0]['filled_quantity']),0);self.assertGreater(self.x.amounts['BTCUSDT'],0)
    def test_partial_group_rejection_is_not_whole_group_success(self):
        self.x.add_normal('manual');self.x.add_normal('other');self.x.reject_ids={'other'};p,r=self.execute(self.request(SYMBOL))
        self.assertEqual(r['state'],'UNKNOWN');self.assertEqual(self.x.orders['manual']['status'],'CANCELED');self.assertEqual(self.x.orders['other']['status'],'NEW')
        n=len(self.deletes());self.commands.reconcile(p['command_id']);self.assertEqual(len(self.deletes()),n)
    def test_lost_response_reconciles_without_another_delete(self):
        self.x.add_normal('manual');self.x.lost_ids={'manual'};p,r=self.execute();self.assertEqual(r['state'],'APPLIED')
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(len(self.deletes()),1)
    def test_uncertain_cancel_cannot_be_retried_with_new_key(self):
        self.x.add_normal('manual');self.x.no_effect_ids={'manual'};_,r=self.execute();self.assertEqual(r['state'],'UNKNOWN')
        _,r=self.execute(self.request(key='new-key'));self.assertEqual(r['state'],'UNKNOWN');self.assertEqual(len(self.deletes()),1)
    def test_explicit_execute_and_digest_required(self):
        self.x.add_normal('manual');p=self.commands.prepare(self.request())
        with self.assertRaises(ValueError):self.commands.apply(p['command_id'],p['digest'])
        with self.assertRaises(ValueError):self.commands.apply(p['command_id'],'wrong',execute=True)
        self.assertEqual(self.deletes(),[])
    def test_proven_not_sent_needs_new_explicit_command_to_retry(self):
        self.x.add_normal('manual');p=self.commands.prepare(self.request());original=self.x.request
        def not_sent(method,path,params):
            if method=='DELETE':raise ExchangeError('not sent',delivery_status='NOT_SENT')
            return original(method,path,params)
        with patch.object(self.x,'request',side_effect=not_sent):
            self.assertEqual(self.commands.apply(p['command_id'],p['digest'],execute=True)['state'],'UNKNOWN')
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.assertEqual(self.deletes(),[])
        _,r=self.execute(self.request(key='explicit-retry'))
        self.assertEqual(r['state'],'APPLIED');self.assertEqual(len(self.deletes()),1)
    def test_open_normal_child_is_not_implicitly_selected_by_algo_parent(self):
        self.x.add_algo('algo');self.x.algos['algo'].update(algoStatus='FINISHED',actualOrderId='1000')
        self.x.orders['trigger-child']={'symbol':'BTCUSDT','side':'SELL','positionSide':'BOTH','type':'MARKET',
            'orderId':1000,'clientOrderId':'trigger-child','origQty':'.0007','executedQty':'.0003','status':'PARTIALLY_FILLED','reduceOnly':'true'}
        _,r=self.execute(self.request(targets=[{'namespace':'ALGO','client_id':'algo'}]))
        self.assertEqual(r['state'],'UNKNOWN');self.assertEqual(self.deletes(),[])
        self.assertEqual(r['result']['orders'][0]['child']['client_id'],'trigger-child')
    def test_cli_frozen_cancel_preview_apply_show_and_reconcile(self):
        from agentrader.shared.locking import execution_lock
        lock_patch=patch('agentrader.cli.exchange_command_cli.execution_lock',side_effect=lambda:execution_lock(self.path.with_suffix('.test.lock')))
        lock_patch.start();self.addCleanup(lock_patch.stop)
        import io,json
        from contextlib import redirect_stdout
        from agentrader.cli.exchange_command_cli import main
        self.x.add_normal('manual');file=Path(self.folder.name)/'cancel.json';file.write_text(json.dumps(self.request()),encoding='utf-8')
        def call(args):
            out=io.StringIO()
            with redirect_stdout(out):code=main(['--database',str(self.path)]+args)
            self.assertEqual(code,0,out.getvalue());return json.loads(out.getvalue())
        with patch('agentrader.cli.exchange_command_cli.Config.load',return_value=self.x.config),patch('agentrader.cli.exchange_command_cli.DemoExchange',return_value=self.x),patch('agentrader.cli.exchange_command_cli.getpass.getuser',return_value='g07'):
            p=call(['prepare',str(file)]);self.assertEqual(self.deletes(),[])
            self.assertEqual(len(p['prepared_details']['cancellation']['targets']),1)
            call(['apply',p['command_id'],'--digest',p['digest'],'--execute-demo']);call(['show',p['command_id']]);call(['reconcile',p['command_id']])
        self.assertEqual(len(self.deletes()),1)
    def test_crash_after_delete_intent_never_resends_on_restart(self):
        self.x.add_normal('manual');p=self.commands.prepare(self.request());original=self.x.request
        def crash(method,path,params):
            if method=='DELETE':raise KeyboardInterrupt
            return original(method,path,params)
        with patch.object(self.x,'request',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.store.close();self.store=StateStore(self.path);self.commands=ExchangeCommands(self.x,self.store,self.owner)
        self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'UNKNOWN')
        _,r=self.execute(self.request(key='after-restart'));self.assertEqual(r['state'],'UNKNOWN');self.assertEqual(self.deletes(),[])
    def test_member_state_corruption_is_not_overwritten_or_resent(self):
        self.x.add_normal('manual');self.x.no_effect_ids={'manual'};self.execute()
        with self.store.db:self.store.db.execute("UPDATE cancellation_members SET digest='bad'")
        p=self.commands.prepare(self.request(key='corrupt'))
        with self.assertRaises(ValueError):self.commands.apply(p['command_id'],p['digest'],execute=True)
        self.assertEqual(len(self.deletes()),1)
