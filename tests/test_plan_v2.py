import copy
import unittest

from agentrader.plans import example_plan,validate_plan
from agentrader.plan_v2 import validate_v2


def plan_v2():
    p=example_plan();p.update(schema_version=2,execution={'strategy':'SINGLE','leverage':20,'margin_mode':'CROSSED'})
    return p


class PlanV2Tests(unittest.TestCase):
    def test_existing_v1_and_v2_single_contracts_are_distinct(self):
        self.assertEqual(validate_plan(example_plan())['schema_version'],1)
        self.assertEqual(validate_plan(plan_v2())['execution']['leverage'],20)

    def test_short_targets_and_stop_are_mirrored(self):
        p=plan_v2();p.update(direction='SHORT',stop='81600',targets=[{'price':'78400','fraction':'1'}])
        self.assertEqual(validate_v2(p)['direction'],'SHORT')
        p['stop']='78000'
        with self.assertRaises(ValueError):validate_v2(p)

    def test_grid_requires_explicit_cycle_authority(self):
        p=plan_v2();p['execution']['strategy']='GRID'
        p['grid']={'lower':'73000','upper':'82500','intervals':8,'spacing':'ARITHMETIC'}
        with self.assertRaises(ValueError):validate_v2(p)
        p['management'].update(allow_scale_in=True,allow_reentry=True)
        self.assertEqual(validate_plan(p)['grid']['intervals'],8)

    def test_unsupported_environment_leverage_and_implicit_margin_are_rejected(self):
        for field,value in [('environment','live'),('position_mode','unknown'),('max_runs',2)]:
            p=plan_v2();p[field]=value
            with self.assertRaises(ValueError):validate_v2(p)
        p=plan_v2();p['execution']['leverage']=True
        with self.assertRaises(ValueError):validate_v2(p)

    def test_margin_is_explicit_and_does_not_reinterpret_nominal(self):
        p=plan_v2();p['sizing']['kind']='MARGIN'
        self.assertEqual(validate_v2(p)['sizing']['kind'],'MARGIN')
        p=plan_v2()
        self.assertEqual(validate_v2(p)['sizing']['kind'],'NOTIONAL')
