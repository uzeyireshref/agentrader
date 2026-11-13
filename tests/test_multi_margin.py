import copy
import time
import unittest
import io
import json
from contextlib import nullcontext,redirect_stdout
from unittest.mock import patch
from dataclasses import replace
from decimal import Decimal

from agentrader.exchange import ExchangeError
from agentrader.isolated_margin import IsolatedMarginCommands,PATH
from agentrader.risk import number
from agentrader.v2_runner import V2Runner
from test_multi_session import MultiExchange
import test_multi_session as fixtures
from test_neutral import NeutralExchange,neutral_plan,neutral_limits
from agentrader.neutral_runner import NeutralGridRunner


class MarginExchange(MultiExchange):
    def __init__(self):
        super().__init__();self.wallets={s:'20' for s in self.prices}
        self.history=[];self.margin_lost=False
        self.leverages={s:20 for s in self.prices}
    def get(self,path,params=None):
        params=params or {}
        if path==PATH+'/history':return [copy.deepcopy(r) for r in self.history if r['symbol']==params['symbol']]
        result=super().get(path,params)
        if path.endswith('/symbolConfig'):
            for r in result:r.update(marginType='ISOLATED',leverage=self.leverages[r['symbol']])
        if path.endswith('/positionRisk'):
            for r in result:r.update(entryPrice='80000',isolatedWallet=self.wallets.get((r['symbol'],r['positionSide']),self.wallets[r['symbol']]))
        return result
    def request(self,method,path,params):
        if path!=PATH:return super().request(method,path,params)
        self.calls.append((method,path,dict(params)))
        change=number(params['amount'])*(1 if params['type']==1 else -1)
        symbol=params['symbol'];key=symbol if params['positionSide']=='BOTH' else (symbol,params['positionSide'])
        self.wallets[key]=str(number(self.wallets[key])+change)
        self.available=str(number(self.available)-change)
        self.history.append(dict(params,asset='USDT',deltaType='USER_ADJUST',time=int(time.time()*1000)))
        if self.margin_lost:raise ExchangeError('lost',delivery_status='UNKNOWN')
        return dict(code=200,type=params['type'],amount=params['amount'])


class NeutralMarginExchange(MarginExchange,NeutralExchange):
    def __init__(self):
        super().__init__()
        self.wallets.update({(sym,side):'20' for sym in self.prices for side in ('LONG','SHORT')})
        self.leverages={s:10 for s in self.prices}


class MultiMarginTests(unittest.TestCase):
    setUp=fixtures.MultiSessionTests.setUp
    tearDown=fixtures.MultiSessionTests.tearDown
    authorize=fixtures.MultiSessionTests.authorize
    open=fixtures.MultiSessionTests.open
    open_grid=fixtures.MultiSessionTests.open_grid
    def plan(self,symbol,grid=False):
        p=fixtures.MultiSessionTests.plan(self,symbol,grid)
        p['execution']['margin_mode']='ISOLATED'
        if grid:p['execution']['leverage']=10
        if grid and getattr(self,'margin_grid_budget',False):p['sizing'].update(kind='MARGIN',amount='12')
        return p
    def start(self,grid=False):
        self.x=MarginExchange()
        self.limits=replace(self.limits,max_notional=Decimal('400'),max_trade_loss=Decimal('10'),
                            max_total_loss=Decimal('20'),max_daily_loss=Decimal('20'))
        self.runner=V2Runner(self.service,self.x,self.limits)
        self.btc=self.open('BTCUSDT')
        if grid:
            self.x.leverages['ETHUSDT']=10
            self.x.limit_pending=True
            self.grid,self.eth=self.open_grid('ETHUSDT')
        else:self.eth=self.open('ETHUSDT')
        self.margin=IsolatedMarginCommands(self.x,self.store,'local:test',session_id=self.btc,limits=self.limits)
    def test_two_sessions_add_once_without_touching_peer(self):
        self.start();peer=copy.deepcopy(self.x.algos)
        p=self.margin.prepare('BTCUSDT','BOTH','ADD','5');before=len(self.x.calls)
        self.assertEqual(self.margin.apply(p['command_id'],p['digest'])['state'],'APPLIED')
        self.assertEqual(self.x.wallets['BTCUSDT'],'25');self.assertEqual(self.x.wallets['ETHUSDT'],'20')
        self.assertEqual(self.x.algos,peer)
        self.margin.apply(p['command_id'],p['digest']);self.assertEqual(len(self.x.calls),before+1)
        self.assertEqual(self.runner.manage(self.eth,False)['state'],'MANAGING')
    def test_peer_budget_blocks_add_even_if_cash_covers_amount(self):
        self.start();self.x.available='10';before=len(self.x.calls)
        with self.assertRaises(ValueError):self.margin.prepare('BTCUSDT','BOTH','ADD','9')
        self.assertEqual(len(self.x.calls),before)
    def test_peer_unprotected_or_foreign_position_blocks(self):
        self.start();before=len(self.x.calls)
        stop=next(a for a in self.x.algos.values() if a['symbol']=='ETHUSDT' and a['type']=='STOP_MARKET')
        stop['algoStatus']='CANCELED'
        with self.assertRaises(ValueError):self.margin.prepare('BTCUSDT','BOTH','ADD','1')
        stop['algoStatus']='NEW';self.x.amounts['ETHUSDT']+=number('.001')
        with self.assertRaises(ValueError):self.margin.prepare('BTCUSDT','BOTH','ADD','1')
        self.assertEqual(len(self.x.calls),before)
    def test_apply_rechecks_changed_peer_risk_before_post(self):
        self.start();p=self.margin.prepare('BTCUSDT','BOTH','ADD','5');before=len(self.x.calls)
        self.x.available='7'
        with self.assertRaises(ValueError):self.margin.apply(p['command_id'],p['digest'])
        self.assertEqual(len(self.x.calls),before)
    def test_lost_post_remains_unknown_across_new_command_object(self):
        self.start();p=self.margin.prepare('BTCUSDT','BOTH','ADD','5');self.x.margin_lost=True
        self.assertEqual(self.margin.apply(p['command_id'],p['digest'])['state'],'UNKNOWN');before=len(self.x.calls)
        other=IsolatedMarginCommands(self.x,self.store,'local:test',limits=self.limits)
        self.assertEqual(other.apply(p['command_id'],p['digest'])['state'],'UNKNOWN')
        self.assertEqual(len(self.x.calls),before)
    def test_remove_preserves_minimum_wallet_and_peer(self):
        self.start();p=self.margin.prepare('BTCUSDT','BOTH','REMOVE','5')
        self.assertEqual(self.margin.apply(p['command_id'],p['digest'])['state'],'APPLIED')
        before=len(self.x.calls)
        with self.assertRaises(ValueError):self.margin.prepare('BTCUSDT','BOTH','REMOVE','14')
        self.assertEqual(len(self.x.calls),before)
    def test_single_with_pending_peer_grid_can_add(self):
        self.start(grid=True);before=copy.deepcopy(self.x.orders)
        p=self.margin.prepare('BTCUSDT','BOTH','ADD','1')
        self.assertEqual(self.margin.apply(p['command_id'],p['digest'])['state'],'APPLIED')
        self.assertEqual(before,self.x.orders)
    def test_grid_owned_pending_orders_allow_margin_change(self):
        self.start(grid=True)
        self.margin=IsolatedMarginCommands(self.x,self.store,'local:test',session_id=self.eth,limits=self.limits)
        p=self.margin.prepare('ETHUSDT','BOTH','ADD','1')
        self.assertEqual(self.margin.apply(p['command_id'],p['digest'])['state'],'APPLIED')
        self.assertEqual(self.grid.manage(self.eth,False)['state'],'GRID_RUNNING')
    def test_tightened_dynamic_bracket_blocks_add(self):
        self.start();self.x.caps['ETHUSDT']=10;before=len(self.x.calls)
        with self.assertRaises(ValueError):self.margin.prepare('BTCUSDT','BOTH','ADD','1')
        self.assertEqual(len(self.x.calls),before)
    def test_daily_peer_loss_blocks_add(self):
        self.start();self.x.unrealized='-100';before=len(self.x.calls)
        with self.assertRaises(ValueError):self.margin.prepare('BTCUSDT','BOTH','ADD','1')
        self.assertEqual(len(self.x.calls),before)
    def test_foreign_resting_order_blocks_grid_margin(self):
        self.start(grid=True);self.x.orders['manual']=dict(symbol='ETHUSDT',clientOrderId='manual',orderId=999,status='NEW')
        before=len(self.x.calls)
        with self.assertRaises(ValueError):self.margin.prepare('BTCUSDT','BOTH','ADD','1')
        self.assertEqual(len(self.x.calls),before)
    def test_partial_grid_fill_requires_management_first(self):
        self.start(grid=True)
        o=next(o for o in self.x.orders.values() if o['symbol']=='ETHUSDT' and o['status']=='NEW')
        o.update(status='PARTIALLY_FILLED',executedQty=str(number(o['origQty'])/2))
        self.x.amounts['ETHUSDT']+=number(o['executedQty'])*(1 if o['side']=='BUY' else -1)
        self.margin=IsolatedMarginCommands(self.x,self.store,'local:test',session_id=self.eth,limits=self.limits)
        before=len(self.x.calls)
        with self.assertRaises(ValueError):self.margin.prepare('ETHUSDT','BOTH','ADD','1')
        self.assertEqual(len(self.x.calls),before)
    def test_grid_shared_collateral_keeps_future_refill_capacity(self):
        self.start(grid=True)
        self.x.available='15';before=len(self.x.calls)
        margin=IsolatedMarginCommands(self.x,self.store,'local:test',session_id=self.eth,limits=self.limits)
        with self.assertRaises(ValueError):margin.prepare('ETHUSDT','BOTH','ADD','10')
        self.assertEqual(len(self.x.calls),before)
    def test_margin_budget_caps_wallet_plus_unfilled_grid(self):
        self.margin_grid_budget=True;self.start(grid=True);self.x.wallets['ETHUSDT']='10'
        margin=IsolatedMarginCommands(self.x,self.store,'local:test',session_id=self.eth,limits=self.limits)
        before=len(self.x.calls)
        with self.assertRaisesRegex(ValueError,'MARGIN'):margin.prepare('ETHUSDT','BOTH','ADD','1')
        self.assertEqual(len(self.x.calls),before)
    def test_cli_passes_selected_limits_to_prepare_and_apply(self):
        from agentrader.settings_cli import main
        self.start();out=io.StringIO()
        common=['--database',str(self.path)]
        with patch('agentrader.settings_cli.execution_lock',return_value=nullcontext()), \
             patch('agentrader.settings_cli.getpass.getuser',return_value='test'), \
             patch('agentrader.settings_cli.Config.load',return_value=self.x.config), \
             patch('agentrader.settings_cli.DemoExchange',return_value=self.x), \
             patch('agentrader.risk.RiskLimits.load',return_value=self.limits) as load,redirect_stdout(out):
            self.assertEqual(main(common+['margin-prepare','--symbol','BTCUSDT','--position-side','BOTH',
                '--action','ADD','--amount','1','--session-id',self.btc,'--risk-profile','selected.json']),0)
            prepared=json.loads(out.getvalue());out.seek(0);out.truncate()
            self.assertEqual(main(common+['margin-apply',prepared['command_id'],'--digest',prepared['digest'],
                '--execute-demo','--risk-profile','selected.json']),0)
            self.assertEqual(json.loads(out.getvalue())['state'],'APPLIED')
            self.assertEqual(load.call_count,2);load.assert_called_with('selected.json')


class NeutralMarginTests(unittest.TestCase):
    setUp=fixtures.MultiSessionTests.setUp
    tearDown=fixtures.MultiSessionTests.tearDown
    def start(self,margin_budget=False):
        self.x=NeutralMarginExchange();self.limits=neutral_limits();self.plan=neutral_plan()
        self.plan['execution'].update(margin_mode='ISOLATED',leverage=10)
        if margin_budget:self.plan['sizing'].update(kind='MARGIN',amount='30')
        p=self.plan;c=self.service.create(p,'local:test')
        self.service.authorize(p['plan_id'],1,c['authorization_token'],'approve','local:test')
        self.runner=NeutralGridRunner(self.service,self.x,self.limits)
        sid=self.runner.open(p['plan_id'],1,True)['session_id']
        for _ in range(10):self.runner.manage(sid,True)
        # Fill one opening on each side and let the controller place protections/exits.
        for side in ('LONG','SHORT'):
            o=next(o for o in self.x.orders.values() if o['positionSide']==side)
            self.x.fill(o['clientOrderId'])
        for _ in range(10):self.runner.manage(sid,True)
        self.margin=IsolatedMarginCommands(self.x,self.store,'local:test',session_id=sid,limits=self.limits)
        return sid
    def test_neutral_long_add_does_not_change_short_wallet_or_orders(self):
        sid=self.start();before=copy.deepcopy(self.x.orders)
        p=self.margin.prepare('BTCUSDT','LONG','ADD','1')
        self.assertEqual(self.margin.apply(p['command_id'],p['digest'])['state'],'APPLIED')
        self.assertEqual(self.x.wallets['BTCUSDT','LONG'],'21')
        self.assertEqual(self.x.wallets['BTCUSDT','SHORT'],'20')
        self.assertEqual(self.x.orders,before)
        self.assertEqual(self.runner.manage(sid,False)['state'],'NEUTRAL_RUNNING')
    def test_neutral_short_remove_uses_its_own_stop(self):
        self.start();p=self.margin.prepare('BTCUSDT','SHORT','REMOVE','1')
        self.assertEqual(self.margin.apply(p['command_id'],p['digest'])['state'],'APPLIED')
        self.assertEqual(self.x.wallets['BTCUSDT','SHORT'],'19')
        self.assertEqual(self.x.wallets['BTCUSDT','LONG'],'20')
    def test_neutral_margin_split_cannot_borrow_other_legs_budget(self):
        self.start(margin_budget=True);before=len(self.x.calls)
        with self.assertRaisesRegex(ValueError,'MARGIN'):
            self.margin.prepare('BTCUSDT','LONG','ADD','1')
        self.assertEqual(len(self.x.calls),before)
    def test_neutral_both_side_is_not_valid(self):
        self.start();before=len(self.x.calls)
        with self.assertRaises(ValueError):self.margin.prepare('BTCUSDT','BOTH','ADD','1')
        self.assertEqual(len(self.x.calls),before)
