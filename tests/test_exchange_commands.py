import io
import json
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agentrader.bot.account_commands import AccountCommands
from agentrader.bot.exchange_commands import ExchangeCommands,validate_command
from agentrader.shared.state import StateStore
from agentrader.shared.exchange import ExchangeError
from test_account_commands import SettingsExchange


class CommandExchange(SettingsExchange):
    def __init__(self):
        super().__init__();self.reads=[];self.stale=False;self.bad_order=False
    def get(self,path,params=None):
        self.reads.append((path,params))
        if path.endswith('premiumIndex'):
            return {'symbol':'BTCUSDT','markPrice':'100','time':int(time.time()*1000)-(20000 if self.stale else 0),'secret':'hidden'}
        if path=='/fapi/v1/order':
            return {'symbol':'WRONG' if self.bad_order else 'BTCUSDT','orderId':7,'clientOrderId':'my-order',
                    'status':'PARTIALLY_FILLED','origQty':'2','executedQty':'1','secret':'hidden'}
        return super().get(path,params)


class ExchangeCommandTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.path=Path(self.folder.name)/'state.db'
        self.store=StateStore(self.path);self.x=CommandExchange();self.s=ExchangeCommands(self.x,self.store,'owner')
    def tearDown(self):self.store.close();self.folder.cleanup()
    def request(self,operation='SET_LEVERAGE',key='one'):
        return {'schema_version':1,'client_command_id':key,'environment':'demo','exchange':'binance','product':'USD-M',
                'account_ref':self.s.account_ref,'operation':operation,'scope':{'symbol':'BTCUSDT'},
                'parameters':{'leverage':20} if operation=='SET_LEVERAGE' else {'order_id':7} if operation=='QUERY_ORDER' else {}}
    def prepare(self,operation='SET_LEVERAGE',key='one'):return self.s.prepare(self.request(operation,key))
    def apply(self,p):return self.s.apply(p['command_id'],p['digest'],execute=True)
    def test_prepare_atomic_and_no_network(self):
        p=self.prepare();self.assertEqual(p['state'],'PREPARED');self.assertEqual(self.x.reads+self.x.calls,[])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM account_commands').fetchone()[0],1)
    def test_duplicate_preserves_expiry_and_single_delegate(self):
        p=self.prepare();q=self.prepare();self.assertEqual(p['expires_at'],q['expires_at']);self.assertTrue(q['duplicate'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM account_commands').fetchone()[0],1)
    def test_changed_payload_same_key_rejected(self):
        self.prepare();r=self.request();r['parameters']['leverage']=15
        with self.assertRaises(ValueError):self.s.prepare(r)
    def test_schema_rejects_scope_escape(self):
        for field,value in [('product','SPOT'),('environment','live'),('schema_version',True),('operation','POST')]:
            r=self.request();r[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_command(r)
        r=self.request();r['url']='/anything'
        with self.assertRaises(ValueError):validate_command(r)
    def test_bad_order_selectors(self):
        for params in ({'order_id':True},{'order_id':0},{'order_id':7,'client_order_id':'a'},{'client_order_id':'bad space'}):
            r=self.request('QUERY_ORDER');r['parameters']=params
            with self.subTest(params=params),self.assertRaises(ValueError):validate_command(r)
    def test_digest_and_execute_gate(self):
        p=self.prepare()
        with self.assertRaises(ValueError):self.s.apply(p['command_id'],'wrong',execute=True)
        with self.assertRaises(ValueError):self.s.apply(p['command_id'],p['digest'])
        self.assertEqual(self.s.show(p['command_id'])['state'],'PREPARED');self.assertEqual(self.x.calls,[])
    def test_once_and_restart(self):
        p=self.prepare();self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.store.close();self.store=StateStore(self.path);self.s=ExchangeCommands(self.x,self.store,'owner')
        self.apply(p);self.assertEqual(len(self.x.calls),1)
    def test_noop(self):
        self.x.leverage=20;p=self.prepare();self.assertEqual(self.apply(p)['state'],'APPLIED');self.assertEqual(self.x.calls,[])
    def test_cancel_both_intents(self):
        p=self.prepare();self.s.cancel(p['command_id'],p['digest']);self.apply(p)
        self.assertEqual(self.x.calls,[]);self.assertEqual(self.store.db.execute('SELECT state FROM account_commands').fetchone()[0],'CANCELED')
    def test_expired_no_send(self):
        p=self.prepare()
        with patch('agentrader.bot.exchange_commands.time.time',return_value=p['expires_at']+1):
            self.assertEqual(self.apply(p)['state'],'EXPIRED')
        self.assertEqual(self.x.calls,[])
    def test_open_positions_proven_not_sent(self):
        self.x.positions=[{'positionAmt':'1'}];p=self.prepare()
        self.assertEqual(self.apply(p)['state'],'NOT_SENT');self.assertEqual(self.x.calls,[])
    def test_rejected(self):
        self.x.reject=True;p=self.prepare();self.assertEqual(self.apply(p)['state'],'REJECTED');self.apply(p)
        self.assertEqual(len(self.x.calls),1)
    def test_lost_response_reconciles(self):
        self.x.lose_response=True;p=self.prepare();self.assertEqual(self.apply(p)['state'],'APPLIED');self.assertEqual(len(self.x.calls),1)
    def test_unknown_never_automatically_reposts_and_blocks_other_mutation(self):
        def uncertain(*args):
            self.x.calls.append(args);raise ExchangeError('secret',delivery_status='UNKNOWN')
        self.x.request=uncertain;p=self.prepare();self.assertEqual(self.apply(p)['state'],'UNKNOWN')
        self.apply(p);self.assertEqual(len(self.x.calls),1)
        other=self.prepare(key='two')
        with self.assertRaises(ValueError):self.apply(other)
        self.x.leverage=20;self.assertEqual(self.s.reconcile(p['command_id'])['state'],'APPLIED');self.assertEqual(len(self.x.calls),1)
    def test_crash_before_child_claim_retires_unsent(self):
        p=self.prepare()
        with patch.object(AccountCommands,'apply',side_effect=RuntimeError('crash')):
            with self.assertRaises(RuntimeError):self.apply(p)
        self.assertEqual(self.s.show(p['command_id'])['state'],'SUBMITTING')
        self.assertEqual(self.s.reconcile(p['command_id'])['state'],'NOT_SENT');self.assertEqual(self.x.calls,[])
    def test_crash_after_child_success_recovers_without_post(self):
        p=self.prepare();original=AccountCommands.apply
        def crash(service,*args):original(service,*args);raise RuntimeError('crash')
        with patch.object(AccountCommands,'apply',crash):
            with self.assertRaises(RuntimeError):self.apply(p)
        self.assertEqual(self.s.reconcile(p['command_id'])['state'],'APPLIED');self.assertEqual(len(self.x.calls),1)
    def test_mark_selected_snapshot_duplicate(self):
        p=self.prepare('GET_MARK_PRICE');r=self.apply(p);self.assertEqual(r['state'],'APPLIED');self.assertNotIn('hidden',json.dumps(r))
        n=len(self.x.reads);self.apply(p);self.assertEqual(len(self.x.reads),n)
    def test_stale_mark_explicit_read_recovery(self):
        self.x.stale=True;p=self.prepare('GET_MARK_PRICE');self.assertEqual(self.apply(p)['state'],'READ_FAILED')
        self.x.stale=False;self.assertEqual(self.s.reconcile(p['command_id'])['state'],'APPLIED');self.assertEqual(self.x.calls,[])
    def test_query_identity_and_selected_result(self):
        p=self.prepare('QUERY_ORDER');r=self.apply(p);self.assertEqual(r['state'],'APPLIED');self.assertNotIn('hidden',json.dumps(r))
        self.x.bad_order=True;p=self.prepare('QUERY_ORDER','two');self.assertEqual(self.apply(p)['state'],'READ_FAILED')
    def test_owner_and_digest_integrity(self):
        p=self.prepare('GET_MARK_PRICE')
        with self.assertRaises(ValueError):ExchangeCommands(self.x,self.store,'other').show(p['command_id'])
        with self.store.db:self.store.db.execute("UPDATE exchange_commands SET digest='bad'")
        with self.assertRaises(ValueError):self.s.show(p['command_id'])
    def test_prepare_transaction_rolls_back_delegate(self):
        AccountCommands(self.x,self.store,'owner')
        self.store.db.execute("CREATE TRIGGER fail_parent BEFORE INSERT ON exchange_commands BEGIN SELECT RAISE(ABORT,'fail'); END")
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):self.prepare()
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM account_commands').fetchone()[0],0)
    def test_cli_prepare_show_cancel(self):
        from agentrader.cli.exchange_command_cli import main
        r=self.request('GET_MARK_PRICE');file=Path(self.folder.name)/'command.json';file.write_text(json.dumps(r))
        def run(args):
            output=io.StringIO()
            with redirect_stdout(output):code=main(['--database',str(self.path)]+args)
            self.assertEqual(code,0,output.getvalue());return json.loads(output.getvalue())
        with patch('agentrader.cli.exchange_command_cli.DemoExchange',return_value=self.x),patch('agentrader.cli.exchange_command_cli.Config.load',return_value=self.x.config),patch('agentrader.cli.exchange_command_cli.execution_lock'):
            run(['context']);p=run(['prepare',str(file)]);run(['show',p['command_id']]);run(['cancel',p['command_id'],'--digest',p['digest']])
        self.assertEqual(self.x.reads+self.x.calls,[])
    def test_concurrent_same_identity_prepares_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        barrier=Barrier(2);request=self.request()
        def prepare():
            store=StateStore(self.path)
            try:
                service=ExchangeCommands(self.x,store,'owner');barrier.wait(timeout=5)
                return service.prepare(request)
            finally:store.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:prepare(),range(2)))
        self.assertEqual(results[0]['command_id'],results[1]['command_id'])
        self.assertEqual(sum(r['duplicate'] for r in results),1)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM account_commands').fetchone()[0],1)
    def test_concurrent_apply_claim_sends_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        p=self.prepare();barrier=Barrier(2)
        def apply():
            store=StateStore(self.path)
            try:
                service=ExchangeCommands(self.x,store,'owner');barrier.wait(timeout=5)
                return service.apply(p['command_id'],p['digest'],execute=True)
            finally:store.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:apply(),range(2)))
        self.assertEqual(len(self.x.calls),1)
        self.assertEqual(self.s.show(p['command_id'])['state'],'APPLIED')
    def test_same_key_other_account_is_distinct(self):
        from agentrader.shared.config import Config
        p=self.prepare('GET_MARK_PRICE');other=CommandExchange();other.config=Config('another-key','secret')
        service=ExchangeCommands(other,self.store,'owner');r=self.request('GET_MARK_PRICE');r['account_ref']=service.account_ref
        q=service.prepare(r);self.assertNotEqual(p['command_id'],q['command_id'])
        with self.assertRaises(ValueError):service.show(p['command_id'])
    def test_exchange_error_body_is_not_exposed(self):
        p=self.prepare('GET_MARK_PRICE')
        with patch.object(self.x,'get',side_effect=ExchangeError('SECRET_CANARY',-1000,500)):
            r=self.apply(p)
        self.assertEqual(r['state'],'READ_FAILED');self.assertNotIn('SECRET_CANARY',json.dumps(r))
