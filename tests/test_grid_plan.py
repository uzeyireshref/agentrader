import copy
import tempfile
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from agentrader.grid_plan import compile_grid
from agentrader.portfolio import Exposure
from agentrader.reservations import ReservationBook
from agentrader.risk import RiskLimits
from agentrader.state import StateStore
from test_plan_v2 import plan_v2
from test_v2_preflight import snapshot


def grid_plan():
    p=plan_v2()
    p['execution']['strategy']='GRID'
    p['entry'].update(condition='IMMEDIATE',reference_price='75725',trigger_price=None)
    p['stop']='74000';p['targets']=[{'price':'80000','fraction':'1'}]
    p['grid']={'lower':'73000','upper':'78000','intervals':4,'spacing':'ARITHMETIC'}
    p['management'].update(allow_scale_in=True,allow_reentry=True)
    p['sizing']['amount']='300'
    return p


def grid_snapshot():
    s=snapshot();s['mark']['markPrice']='75725'
    return s


def limits():
    return replace(RiskLimits(),max_notional=Decimal('1000'),max_trade_loss=Decimal('100'),
                   max_total_loss=Decimal('100'),max_daily_loss=Decimal('100'))


class GridCompilerTests(unittest.TestCase):
    def test_four_slots_reserve_nominal_without_leverage_multiplication(self):
        r=compile_grid(grid_plan(),grid_snapshot(),limits(),now=1001)
        self.assertEqual(len(r['slots']),4)
        self.assertLessEqual(Decimal(r['notional_ceiling']),300)
        self.assertEqual(r['slots'][0]['lower'],'73000')
        self.assertEqual(r['slots'][-1]['upper'],'78000')
        self.assertEqual(sum(s['seed'] for s in r['slots']),1)

    def test_user_200_nominal_still_cannot_bypass_exchange_minimum(self):
        p=grid_plan();p['sizing']['amount']='200'
        with self.assertRaisesRegex(ValueError,'minimum'):compile_grid(p,grid_snapshot(),limits(),now=1001)

    def test_short_grid_reserves_full_gross_position(self):
        p=grid_plan();p.update(direction='SHORT',stop='79000',targets=[{'price':'72000','fraction':'1'}])
        r=compile_grid(p,grid_snapshot(),limits(),now=1001)
        self.assertEqual(sum(s['seed'] for s in r['slots']),2)
        self.assertEqual(r['exposures'][0]['direction'],'SHORT')
        self.assertEqual(Decimal(r['exposures'][0]['quantity']),sum(Decimal(s['quantity']) for s in r['slots']))

    def test_geometric_levels_are_tick_aligned_and_strictly_ordered(self):
        p=grid_plan();p['grid']['spacing']='GEOMETRIC'
        r=compile_grid(p,grid_snapshot(),limits(),now=1001)
        self.assertEqual(r['geometric_rounding'],'FLOOR_TO_TICK')
        for s in r['slots']:
            self.assertEqual(Decimal(s['lower'])%Decimal('.1'),0)
            self.assertLess(Decimal(s['lower']),Decimal(s['upper']))

    def test_margin_and_loss_budgets_reserve_fees(self):
        for kind,amount in [('MARGIN','20'),('MAX_LOSS','30')]:
            p=grid_plan();p['sizing'].update(kind=kind,amount=amount)
            r=compile_grid(p,grid_snapshot(),limits(),now=1001)
            used=(Decimal(r['notional_ceiling'])/20+Decimal(r['notional_ceiling'])*Decimal('.002')
                  if kind=='MARGIN' else Decimal(r['risk']['risk_with_fee_reserve']))
            self.assertLessEqual(used,Decimal(amount))

    def test_stale_wrong_mode_or_excessive_risk_blocks(self):
        s=grid_snapshot();s['position_mode']='hedge'
        with self.assertRaises(ValueError):compile_grid(grid_plan(),s,limits(),now=1001)
        with self.assertRaises(ValueError):compile_grid(grid_plan(),grid_snapshot(),limits(),now=1100)
        with self.assertRaises(ValueError):compile_grid(grid_plan(),grid_snapshot(),RiskLimits(),now=1001)


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.db'
        self.store=StateStore(self.path);self.book=ReservationBook(self.store,'account',clock=lambda:1001)
        self.leg=Exposure('BTCUSDT','LONG','.002','75000','74000',20,'CROSSED','.004')
        self.limits=replace(limits(),max_notional=Decimal('250'))

    def tearDown(self):self.store.close();self.temp.cleanup()

    def reserve(self,rid='one',leg=None):
        return self.book.reserve(rid,'owner','plan-hash',[leg or self.leg],grid_snapshot(),self.limits)

    def test_two_reservations_cannot_spend_same_capacity(self):
        self.reserve()
        with self.assertRaises(ValueError):self.reserve('two')
        self.assertEqual(self.book.state('one'),'RESERVED')

    def test_restart_and_duplicate_keep_full_refill_envelope(self):
        self.reserve();self.book.mark_submitted('one')
        self.store.close();self.store=StateStore(self.path)
        self.book=ReservationBook(self.store,'account',clock=lambda:1001)
        self.assertTrue(self.reserve()['duplicate'])
        with self.assertRaises(ValueError):self.reserve('two')

    def test_scope_change_and_other_key_are_rejected(self):
        self.reserve()
        with self.assertRaises(ValueError):self.reserve(leg=replace(self.leg,quantity='.001'))
        with self.assertRaises(ValueError):ReservationBook(self.store,'other').state('one')

    def test_release_requires_flat_and_terminal_proof_and_cannot_reopen(self):
        self.reserve()
        with self.assertRaises(ValueError):self.book.release('one',flat_verified=True,orders_terminal=False)
        self.book.release('one',flat_verified=True,orders_terminal=True)
        with self.assertRaises(ValueError):self.reserve()
        self.assertEqual(self.reserve('two')['state'],'RESERVED')

    def test_stale_snapshot_does_not_reserve(self):
        self.book.clock=lambda:1100
        with self.assertRaises(ValueError):self.reserve()

    def test_different_symbols_still_share_account_nominal_capacity(self):
        self.reserve()
        other=Exposure('ETHUSDT','LONG','.06','2500','2490',20,'CROSSED','.004')
        with self.assertRaisesRegex(ValueError,'nominal'):
            self.book.reserve('eth','owner','another',[other],grid_snapshot(),replace(self.limits,max_positions=2))
