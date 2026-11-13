import copy
import unittest

from agentrader.grid_runner import GridRunner
from agentrader.plan_v2 import validate_v2
from agentrader.plans import PlanService
from agentrader.risk import number
from agentrader.state import StateStore
from agentrader.exchange import ExchangeError
import test_grid_runner as fixtures


class GridTrailingTests(unittest.TestCase):
    setUp=fixtures.GridRunnerTests.setUp
    tearDown=fixtures.GridRunnerTests.tearDown
    authorize=fixtures.GridRunnerTests.authorize
    start=fixtures.GridRunnerTests.start
    cell=fixtures.GridRunnerTests.cell
    def enable(self):
        self.plan['management']['trailing']=dict(activation_price='77000',distance_bps='100',min_step_bps='10')
    def test_default_remains_disabled(self):
        sid=self.start();self.x.price='79000';r=self.runner.manage(sid,False)
        self.assertEqual(r['bot_stop'],'74000');self.assertFalse(r['trailing_active'])
    def test_activation_and_monotonic_stop_keep_native_fallback(self):
        self.enable();sid=self.start();native=copy.deepcopy(self.x.algos);before=len(self.x.calls)
        self.x.price='77000';r=self.runner.manage(sid,False)
        self.assertEqual(number(r['bot_stop']),76230)
        self.x.price='79000';self.runner.manage(sid,False)
        self.x.price='78500';r=self.runner.manage(sid,False)
        self.assertEqual(number(r['bot_stop']),78210)
        self.assertEqual(native,self.x.algos);self.assertEqual(before,len(self.x.calls))
    def test_retrace_cancels_entries_and_closes_actual_remaining(self):
        self.enable();sid=self.start();self.x.price='79000';self.runner.manage(sid,False)
        self.x.price='78000';self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_CLOSE_SUBMITTED')
        self.assertEqual(self.x.amount,0)
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(self.runner.book.state(sid),'RELEASED')
    def test_read_only_hit_sets_stop_barrier_without_exchange_writes(self):
        self.enable();sid=self.start();self.x.price='79000';self.runner.manage(sid,False)
        before=len(self.x.calls);self.x.price='78000';r=self.runner.manage(sid,False)
        self.assertEqual(r['state'],'GRID_CANCEL_REQUIRED');self.assertEqual(before,len(self.x.calls))
        self.assertEqual(self.store.sessions()[0]['phase'],'STOPPING')
    def test_restart_keeps_watermark_and_stop(self):
        self.enable();sid=self.start();self.x.price='79000';self.runner.manage(sid,False)
        self.store.close();self.store=StateStore(self.path);self.service=PlanService(self.store,'local:test')
        self.runner=GridRunner(self.service,self.x,self.runner.limits)
        self.x.price='78500';r=self.runner.manage(sid,False)
        self.assertEqual(number(r['bot_stop']),78210)
        self.assertEqual(number(self.store.sessions()[0]['grid_trailing_state']['watermark']),79000)
    def test_cancel_race_fill_is_included_in_close_quantity(self):
        self.enable();sid=self.start();self.x.price='79000';self.runner.manage(sid,False)
        cid=self.cell(1,'OPEN');self.x.late_fill=cid;initial=abs(self.x.amount)
        self.x.price='78000';self.runner.manage(sid,True)
        close=[c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order' and c[2]['type']=='MARKET'][-1]
        self.assertEqual(number(close[2]['quantity']),initial+number(self.x.orders[cid]['origQty']))
    def test_partial_reduce_preserves_only_remaining_quantity_for_stop(self):
        self.enable();self.plan['sizing']['amount']='800';sid=self.start()
        cid=next(r['proposal']['params']['newClientOrderId'] for r in self.store.sessions()[0]['orders'] if r['kind']=='REDUCE')
        self.assertGreater(number(self.x.orders[cid]['origQty']),number('.001'))
        self.x.fill(cid,number('.001'))
        self.x.price='79000';self.runner.manage(sid,True)
        remaining=abs(self.x.amount);self.x.price='78000';self.runner.manage(sid,True)
        close=[c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order' and c[2]['type']=='MARKET'][-1]
        self.assertEqual(number(close[2]['quantity']),remaining)
    def test_short_hedge_stop_moves_down_and_closes_on_bounce(self):
        self.plan.update(direction='SHORT',position_mode='hedge',stop='79000',targets=[{'price':'72000','fraction':'1'}])
        self.snap['position_mode']='hedge';self.x.short=True;self.x.hedge=True
        self.plan['management']['trailing']=dict(activation_price='75000',distance_bps='100',min_step_bps='10')
        sid=self.start();self.x.price='74000';r=self.runner.manage(sid,False)
        self.assertEqual(number(r['bot_stop']),74740)
        self.x.price='74800';self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_CLOSE_SUBMITTED')
        self.assertEqual(self.x.amount,0)
    def test_invalid_activation_and_distance_are_rejected(self):
        self.enable();self.plan['management']['trailing']['activation_price']='81000'
        with self.assertRaises(ValueError):validate_v2(self.plan)
        self.enable();self.plan['management']['trailing']['distance_bps']='0'
        with self.assertRaises(ValueError):validate_v2(self.plan)
    def test_draining_keeps_trailing_management(self):
        self.enable();sid=self.start();self.runner.stop(sid,execute=True)
        self.x.price='79000';self.runner.manage(sid,True)
        self.x.price='78000';self.assertEqual(self.runner.manage(sid,True)['state'],'GRID_CLOSE_SUBMITTED')
    def test_lost_close_response_is_not_sent_twice(self):
        self.enable();sid=self.start();self.x.price='79000';self.runner.manage(sid,False)
        self.x.price='78000';self.x.timeout=True
        with self.assertRaises(ExchangeError):self.runner.manage(sid,True)
        before=len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order' and c[2]['type']=='MARKET'])
        self.assertEqual(self.runner.manage(sid,True)['state'],'CLOSED')
        self.assertEqual(before,len([c for c in self.x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order' and c[2]['type']=='MARKET']))
    def test_minimum_step_retains_previous_trigger(self):
        self.enable();sid=self.start();self.x.price='79000';self.runner.manage(sid,False)
        self.x.price='79001';r=self.runner.manage(sid,False)
        self.assertEqual(number(r['bot_stop']),78210)
    def test_last_moment_refill_checks_bot_stop_before_post(self):
        self.enable();sid=self.start();self.x.price='79000';self.runner.manage(sid,False)
        s=self.store.sessions()[0];self.x.price='78000';before=len(self.x.calls)
        info=next(iter(self.x.get('/fapi/v1/exchangeInfo')['symbols']))
        with self.assertRaises(ValueError):
            self.runner._new_order(s,'OPEN',1,s['compiled']['slots'][1]['quantity'],
                                   self.x.get('/fapi/v1/premiumIndex',{'symbol':s['symbol']}),info)
        self.assertEqual(before,len(self.x.calls));self.assertEqual(self.store.sessions()[0]['phase'],'STOPPING')
