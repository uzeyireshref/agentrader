import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agentrader.bot.entry_options import validate_options
from agentrader.bot.exchange_commands import ExchangeCommands
from agentrader.bot.plan_v2 import validate_v2
from agentrader.bot.plans import PlanService
from agentrader.bot.risk import RiskLimits,number
from agentrader.bot.v2_preflight import prepare_single
from agentrader.bot.v2_runner import V2Runner
from agentrader.shared.exchange import ExchangeError
from agentrader.shared.state import StateStore
from test_plan_v2 import plan_v2
from test_v2_preflight import snapshot
from test_v2_runner import ExecutionExchange


class OptionExchange(ExecutionExchange):
    def __init__(self):
        super().__init__();self.ioc_partial=False;self.fok_empty=False;self.gtx_reject=False;self.matched_price='80000'
    def get(self,path,params=None):
        result=super().get(path,params)
        if path=='/fapi/v1/openOrders':
            return [r for r in result if r['status'] not in ('EXPIRED','EXPIRED_IN_MATCH','REJECTED')]
        return result
    def request(self,method,path,params):
        entry=method=='POST' and path.endswith('/order') and params.get('reduceOnly')!='true'
        if entry and self.gtx_reject:
            self.calls.append((method,path,copy.deepcopy(params)))
            raise ExchangeError('maker reject',-5022,400,delivery_status='REJECTED')
        if entry and self.ioc_partial:self.partial=True
        if entry and self.fok_empty:self.limit_pending=True
        try:result=super().request(method,path,params)
        finally:self.partial=False
        if entry:
            row=self.orders[params['newClientOrderId']]
            if self.ioc_partial or self.fok_empty:row['status']='EXPIRED'
            if 'priceMatch' in params:row.update(price=self.matched_price,avgPrice=self.matched_price)
            return copy.deepcopy(row)
        return result


class G04Tests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.path=Path(self.folder.name)/'state.db';self.store=StateStore(self.path)
        self.service=PlanService(self.store,'owner');self.x=OptionExchange();self.limits=RiskLimits()
        self.runner=V2Runner(self.service,self.x,self.limits);self.commands=ExchangeCommands(self.x,self.store,'owner')
        self.plan=plan_v2();self.plan['entry'].update(condition='LIMIT',trigger_price='80000')
        self.snap=snapshot();self.snap.update(observed_at=time.time(),finished_at=time.time(),now_ms=int(time.time()*1000))
        self.mock=patch('agentrader.bot.v2_runner.collect_flat_snapshot',side_effect=lambda *a,**kw:copy.deepcopy(self.snap));self.mock.start()
    def tearDown(self):self.mock.stop();self.store.close();self.folder.cleanup()
    def authorize(self):
        created=self.service.create(self.plan,'owner')
        self.service.authorize(self.plan['plan_id'],1,created['authorization_token'],'approve','owner',ttl=1800)
        return self.service.show(self.plan['plan_id'],1)
    def request(self,key='g04'):
        row=self.service.show(self.plan['plan_id'],1)
        return {'schema_version':1,'client_command_id':key,'environment':'demo','exchange':'binance','product':'USD-M',
                'account_ref':self.commands.account_ref,'operation':'RUN_SINGLE_PLAN','scope':{'symbol':'BTCUSDT'},
                'parameters':{'plan_id':self.plan['plan_id'],'version':1,'plan_digest':row['digest'],
                              'entry_options':self.plan['entry'].get('order_options',{})}}
    def run_command(self):
        p=self.commands.prepare(self.request());return p,self.commands.apply(p['command_id'],p['digest'],execute=True)
    def entry_posts(self):return [p for m,path,p in self.x.calls if m=='POST' and path.endswith('/order') and p.get('reduceOnly')!='true']
    def test_all_tifs_compile_and_keep_old_default(self):
        old=prepare_single(self.plan,self.snap,self.limits);self.assertEqual(old['entry']['params']['timeInForce'],'GTC')
        for tif in ('GTC','IOC','FOK','GTX','GTD'):
            opts={'time_in_force':tif}
            if tif=='GTD':opts['good_till_date']=self.snap['now_ms']+701999
            self.plan['entry']['order_options']=opts;p=prepare_single(self.plan,self.snap,self.limits)
            self.assertEqual(p['entry']['params']['timeInForce'],tif)
            if tif=='GTD':self.assertEqual(p['entry']['params']['goodTillDate']%1000,0)
    def test_options_rejected_when_ignored_or_inapplicable(self):
        for opts in ({'time_in_force':'RPI'},{'time_in_force':'FOK','self_trade_prevention_mode':'EXPIRE_BOTH'},
                     {'time_in_force':'GTX','self_trade_prevention_mode':'EXPIRE_MAKER'},
                     {'good_till_date':123},{'time_in_force':'GTD','good_till_date':True},{'price_match':'NONE'},
                     {'self_trade_prevention_mode':'NONE'},{'price':'80000'}):
            with self.subTest(opts=opts),self.assertRaises(ValueError):validate_options(opts)
        self.plan['entry']['order_options']={'time_in_force':'IOC'}
        self.plan['entry'].update(condition='IMMEDIATE',trigger_price=None)
        with self.assertRaises(ValueError):validate_v2(self.plan)
        self.plan['execution']['strategy']='GRID'
        with self.assertRaises(ValueError):validate_v2(self.plan)
    def test_gtd_strict_600_seconds_after_truncation(self):
        self.plan['entry']['order_options']={'time_in_force':'GTD','good_till_date':self.snap['now_ms']+600000}
        with self.assertRaises(ValueError):prepare_single(self.plan,self.snap,self.limits)
    def test_matching_modes_compile_without_explicit_exchange_price(self):
        for mode in ('OPPONENT','OPPONENT_5','OPPONENT_10','OPPONENT_20','QUEUE','QUEUE_5','QUEUE_10','QUEUE_20'):
            self.plan['entry']['order_options']={'price_match':mode};p=prepare_single(self.plan,self.snap,self.limits)
            self.assertNotIn('price',p['entry']['params']);self.assertEqual(p['entry']['params']['priceMatch'],mode)
    def test_generic_command_requires_exact_authorized_options(self):
        self.plan['entry']['order_options']={'time_in_force':'IOC'};self.authorize();r=self.request()
        r['parameters']['entry_options']['time_in_force']='FOK'
        with self.assertRaises(ValueError):self.commands.prepare(r)
        self.assertEqual(self.x.calls,[])
    def test_generic_fok_no_fill_releases_full_reservation_and_never_reposts(self):
        self.plan['entry']['order_options']={'time_in_force':'FOK'};self.x.fok_empty=True;self.authorize()
        p,r=self.run_command();self.assertEqual(r['state'],'APPLIED');self.assertEqual(r['result']['entry_outcome'],'NO_FILL')
        self.assertEqual(r['result']['plan_state'],'CLOSED')
        self.assertEqual(self.runner.book.state(r['result']['session_id']),'RELEASED')
        self.commands.apply(p['command_id'],p['digest'],execute=True);self.commands.reconcile(p['command_id'])
        self.assertTrue(self.commands.prepare(self.request())['duplicate'])
        with self.assertRaises(ValueError):self.commands.prepare(self.request('new-key'))
        self.assertEqual(len(self.entry_posts()),1)
    def test_ioc_partial_releases_only_unfilled_risk_after_protection(self):
        self.plan['entry']['order_options']={'time_in_force':'IOC','self_trade_prevention_mode':'EXPIRE_BOTH'}
        self.x.ioc_partial=True;self.authorize();p,r=self.run_command()
        self.assertEqual(r['state'],'APPLIED');self.assertEqual(r['result']['entry_outcome'],'PARTIAL_FILL')
        sid=r['result']['session_id'];self.assertEqual(self.runner.book.state(sid),'COMMITTED')
        import json
        row=self.store.db.execute('SELECT * FROM risk_reservations WHERE reservation_id=?',(sid,)).fetchone()
        effective=self.runner.book._effective_exposures(self.store.db,row,json.loads(row['body']))
        self.assertEqual(number(effective[0].quantity),abs(self.x.amount))
        self.assertLess(number(effective[0].quantity),number(json.loads(row['body'])['exposures'][0]['quantity']))
        self.assertEqual(len(self.x.algos),2);self.assertEqual(len(self.entry_posts()),1)
    def test_lost_ioc_response_restart_queries_existing_identity(self):
        self.plan['entry']['order_options']={'time_in_force':'IOC'};self.x.ioc_partial=True;self.x.timeout=True;self.authorize()
        p,r=self.run_command();self.assertEqual(r['state'],'UNKNOWN')
        self.store.close();self.store=StateStore(self.path);self.service=PlanService(self.store,'owner')
        self.runner=V2Runner(self.service,self.x,self.limits);self.commands=ExchangeCommands(self.x,self.store,'owner')
        sid=self.service.show(self.plan['plan_id'],1)['session_id'];self.runner.manage(sid,True)
        r=self.commands.reconcile(p['command_id']);self.assertEqual(r['state'],'APPLIED');self.assertEqual(len(self.entry_posts()),1)
    def test_gtx_definitive_rejection_is_not_reposted(self):
        self.plan['entry']['order_options']={'time_in_force':'GTX'};self.x.gtx_reject=True;self.authorize();p,r=self.run_command()
        self.assertEqual(r['state'],'UNKNOWN');self.assertEqual(r['result']['entry_state'],'REJECTED')
        self.runner.manage(r['result']['session_id'],True);self.assertEqual(self.commands.reconcile(p['command_id'])['state'],'APPLIED')
        self.assertEqual(len(self.entry_posts()),1)
    def test_price_match_round_trip_and_mutated_scope_rejected(self):
        self.plan['entry']['order_options']={'price_match':'QUEUE_5'};self.authorize();p,r=self.run_command()
        self.assertEqual(r['state'],'APPLIED');self.assertNotIn('price',self.entry_posts()[0])
        from agentrader.bot.account_ownership import AccountOwnership
        self.assertTrue(AccountOwnership(self.runner).verify()['sessions'][0]['protected'])
        cid=r['result']['action_id'];self.x.orders[cid]['priceMatch']='OPPONENT'
        with self.assertRaises(ValueError):self.runner.manage(r['result']['session_id'],True)
    def test_match_outside_budget_closes_owned_fill_instead_of_accepting(self):
        self.plan['entry']['order_options']={'price_match':'OPPONENT'};self.x.matched_price='81000';self.authorize()
        p,r=self.run_command();self.assertEqual(r['state'],'UNKNOWN');self.assertEqual(self.x.amount,0)
        self.runner.manage(r['result']['session_id'],True);self.assertEqual(self.commands.reconcile(p['command_id'])['result']['plan_state'],'CLOSED')
    def test_gtd_delayed_venue_expiry_is_canceled_not_recreated(self):
        deadline=int(time.time()*1000)+701999
        self.plan['entry']['order_options']={'time_in_force':'GTD','good_till_date':deadline};self.x.limit_pending=True;self.authorize()
        p,r=self.run_command();self.assertEqual(r['state'],'UNKNOWN');sid=r['result']['session_id']
        with patch('agentrader.bot.v2_runner.time.time',return_value=deadline/1000+1):self.runner.manage(sid,True)
        self.assertEqual(self.commands.reconcile(p['command_id'])['result']['plan_state'],'CLOSED')
        self.assertEqual(len(self.entry_posts()),1)
    def test_terminal_cap_late_fill_can_only_increase_reserved_quantity(self):
        import json
        self.plan['entry']['order_options']={'time_in_force':'IOC'};self.x.ioc_partial=True;self.authorize();_,r=self.run_command()
        sid=r['result']['session_id'];cid=r['result']['action_id']
        row=self.store.db.execute('SELECT * FROM risk_reservations WHERE reservation_id=?',(sid,)).fetchone()
        original=number(json.loads(row['body'])['exposures'][0]['quantity'])
        self.runner.journal.observe(cid,'late-full-fill',status='EXPIRED',cumulative_filled=str(original),observed_ms=int(time.time()*1000)+1000)
        effective=self.runner.book._effective_exposures(self.store.db,row,json.loads(row['body']))
        self.assertEqual(number(effective[0].quantity),original)
    def test_corrupt_cap_cannot_free_risk(self):
        import json
        self.plan['entry']['order_options']={'time_in_force':'IOC'};self.x.ioc_partial=True;self.authorize();_,r=self.run_command()
        sid=r['result']['session_id']
        with self.store.db:self.store.db.execute("UPDATE single_reservation_caps SET digest='bad'")
        row=self.store.db.execute('SELECT * FROM risk_reservations WHERE reservation_id=?',(sid,)).fetchone()
        with self.assertRaises(ValueError):self.runner.book._effective_exposures(self.store.db,row,json.loads(row['body']))
    def test_cli_prepare_apply_show_and_reconcile_use_generic_path(self):
        import io,json
        from contextlib import redirect_stdout
        from agentrader.cli.exchange_command_cli import main
        self.plan['entry']['order_options']={'time_in_force':'FOK'};self.x.fok_empty=True;self.authorize()
        cli_path=Path(self.folder.name)/'cli.db';cli_store=StateStore(cli_path)
        try:
            service=PlanService(cli_store,'local:g04');created=service.create(self.plan,'local:g04')
            service.authorize(self.plan['plan_id'],1,created['authorization_token'],'approve','local:g04')
        finally:cli_store.close()
        file=Path(self.folder.name)/'command.json';file.write_text(json.dumps(self.request()),encoding='utf-8')
        def call(args):
            output=io.StringIO()
            with redirect_stdout(output):code=main(['--database',str(cli_path)]+args)
            self.assertEqual(code,0,output.getvalue());return json.loads(output.getvalue())
        with patch('agentrader.cli.exchange_command_cli.DemoExchange',return_value=self.x),patch('agentrader.cli.exchange_command_cli.Config.load',return_value=self.x.config),patch('agentrader.cli.exchange_command_cli.getpass.getuser',return_value='g04'):
            p=call(['prepare',str(file)]);self.assertEqual(self.x.calls,[])
            r=call(['apply',p['command_id'],'--digest',p['digest'],'--execute-demo'])
            self.assertEqual(r['result']['entry_outcome'],'NO_FILL')
            call(['show',p['command_id']]);call(['reconcile',p['command_id']]);self.assertEqual(len(self.entry_posts()),1)
    def test_short_hedge_matching_keeps_correct_leg_and_protection(self):
        self.plan.update(direction='SHORT',position_mode='hedge',stop='81600',targets=[{'price':'78400','fraction':'1'}])
        self.plan['entry']['order_options']={'price_match':'QUEUE','self_trade_prevention_mode':'EXPIRE_MAKER'}
        self.snap['position_mode']='hedge';self.x.short=True;self.x.hedge=True;self.authorize();_,r=self.run_command()
        self.assertEqual(r['state'],'APPLIED');entry=self.entry_posts()[0]
        self.assertEqual((entry['side'],entry['positionSide']),('SELL','SHORT'));self.assertNotIn('reduceOnly',entry)
        self.assertTrue(all(a['side']=='BUY' and a['positionSide']=='SHORT' for a in self.x.algos.values()))
    def test_symbol_tif_and_stp_restrictions_are_enforced(self):
        self.plan['entry']['order_options']={'time_in_force':'IOC','self_trade_prevention_mode':'EXPIRE_BOTH'}
        self.snap['symbol_info']['timeInForce']=['GTC']
        with self.assertRaises(ValueError):prepare_single(self.plan,self.snap,self.limits)
        self.snap['symbol_info']['timeInForce']=['IOC'];self.snap['symbol_info']['allowedSelfTradePreventionModes']=['EXPIRE_MAKER']
        with self.assertRaises(ValueError):prepare_single(self.plan,self.snap,self.limits)
    def test_generic_execute_gate_preserves_authority(self):
        self.plan['entry']['order_options']={'time_in_force':'IOC'};self.authorize();p=self.commands.prepare(self.request())
        with self.assertRaises(ValueError):self.commands.apply(p['command_id'],p['digest'])
        self.assertEqual(self.service.show(self.plan['plan_id'],1)['state'],'AUTHORIZED');self.assertEqual(self.x.calls,[])
