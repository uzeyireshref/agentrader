import copy
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from agentrader.drawings.service import DrawingService, DrawingError, geometry, management
from agentrader.drawings.position import metrics
from agentrader.drawings.calculations import query, canonical_hash, CalculationBlocked
from agentrader.drawings.contracts import legacy_contract, capability
from agentrader.migrations import migrate


def plan(kind='long_plan', costs=False):
    return dict(schema='chart-position/1',kind=kind,symbol='BTCUSDT',price_source='LAST_PRICE',label=kind,
                anchors=[dict(time=1800000000,price='100'),dict(time=1800009000,price='90' if kind=='long_plan' else '110'),dict(time=1800009000,price='120' if kind=='long_plan' else '80')],
                params=dict(risk_budget='100',fee_bps='10' if costs else '0',slippage_bps='20' if costs else '0'))


class ChartPositionTests(unittest.TestCase):
    def test_independent_long_and_short_reference_costs_and_budget(self):
        for kind,risk,reward,entry in [('long_plan','10.57002','19.34004','100.2'),('short_plan','10.63002','19.46004','99.8')]:
            with self.subTest(kind=kind):
                m=metrics(plan(kind,True))
                self.assertEqual(m['gross_risk'],10);self.assertEqual(m['gross_reward'],20)
                self.assertEqual(m['net_risk'],Fraction(risk));self.assertEqual(m['net_reward'],Fraction(reward))
                self.assertEqual(m['entry_fill'],Fraction(entry))
                self.assertEqual(m['quantity']*m['net_risk'],100)
                self.assertEqual(m['net_rr'],Fraction(reward)/Fraction(risk))
                self.assertEqual(m['target_pnl'],m['quantity']*m['net_reward'])

    def test_zero_cost_and_optional_budget_are_explicit(self):
        p=plan();p['params']['risk_budget']=None;m=metrics(p)
        self.assertEqual(m['gross_rr'],2);self.assertEqual(m['net_rr'],2)
        self.assertIsNone(m['quantity']);self.assertIsNone(m['notional'])
        self.assertIsNone(m['target_pnl'])
        response=query(p,'riskReward')
        self.assertFalse(response['order_authority']);self.assertFalse(response['live_eligible'])
        self.assertEqual(response['value']['net_rr']['decimal'],'2')

    def test_reject_zero_risk_wrong_direction_time_and_malformed_assumptions(self):
        for kind in ['long_plan','short_plan']:
            p=plan(kind)
            bad=copy.deepcopy(p);bad['anchors'][1]['price']='100'
            bad_target=copy.deepcopy(p);bad_target['anchors'][2]['price']='100'
            backwards=copy.deepcopy(p);backwards['anchors'][0]['time']=backwards['anchors'][1]['time']
            mismatched=copy.deepcopy(p);mismatched['anchors'][2]['time']+=1
            for value in [bad,bad_target,backwards,mismatched,{**p,'schema':'wrong'}]:
                with self.assertRaises(DrawingError):geometry(value)
            for params in [dict(risk_budget='0'),dict(fee_bps='-1'),dict(fee_bps='1001'),dict(slippage_bps='NaN'),dict(fee_bps=0),dict(extra=True)]:
                with self.subTest(params=params),self.assertRaises(DrawingError):geometry({**p,'params':{**p['params'],**params}})

    def test_expensive_target_can_be_negative_without_false_profit(self):
        p=plan();p['anchors'][2]['price']='100.01';p['params']['fee_bps']='1000'
        self.assertLess(metrics(p)['net_reward'],0)
        self.assertLess(metrics(p)['net_rr'],0)

    def test_exact_precision_context_independent_and_costs_are_hashed(self):
        from decimal import localcontext
        with localcontext() as context:
            context.prec=2
            self.assertEqual(metrics(plan(costs=True))['net_risk'],Fraction('10.57002'))
        self.assertNotEqual(canonical_hash(plan()),canonical_hash(plan(costs=True)))
        p=plan();p['params']['fee_bps']='0.00'
        self.assertEqual(canonical_hash(plan()),canonical_hash(p))
        with self.assertRaises(CalculationBlocked):query(plan(),'priceAt',time=1800000000)

    def test_restart_revision_inverse_and_contract_are_plan_category(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'app.db';migrate(db);s=DrawingService(db,'owner');a=s.create('main','create',plan())
            changed=copy.deepcopy(a['geometry']);changed['anchors'][2]['price']='130'
            b=s.update(a['drawing_id'],'edit',1,changed)
            op=dict(drawing_id=a['drawing_id'],expected_revision=b['revision'],geometry=a['geometry'],management=management(),deleted=False)
            restored=s.operations('main','undo',[op])['drawings'][0]
            self.assertEqual(DrawingService(db,'owner').show(a['drawing_id'])['geometry'],plan())
            c=legacy_contract(restored)
            self.assertEqual(c['category'],'plan');self.assertFalse(c['capabilities']['order_authority'])
            self.assertTrue(capability('plan','long_plan')['computable'])

    def test_v5_api_hides_plans_from_all_old_formats_and_blocks_old_batch_writes(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)
            with TestClient(create_app(WebSettings(f/'app.db',f/'exec.db',market_database=f/'market.db')),base_url='http://127.0.0.1') as c:
                payload=dict(request_id='create',geometry=plan())
                self.assertEqual(c.post('/api/workspaces/main/drawings?format_version=4',json=payload).status_code,422)
                r=c.post('/api/workspaces/main/drawings?format_version=5',json=payload);self.assertEqual(r.status_code,201);a=r.json()
                for v in [1,2,3,4]:
                    suffix='?format_version='+str(v)
                    self.assertEqual(c.get('/api/workspaces/main/drawings'+suffix).json()['drawings'],[])
                    self.assertEqual(c.get('/api/drawings/'+a['drawing_id']+suffix).status_code,422)
                op=dict(drawing_id=a['drawing_id'],expected_revision=1,geometry=a['geometry'],management=a['management'],deleted=False)
                self.assertEqual(c.post('/api/workspaces/main/drawing-operations?format_version=4',json=dict(request_id='old',operations=[op])).status_code,422)
                self.assertEqual(c.post('/api/workspaces/main/drawing-operations?format_version=5',json=dict(request_id='new',operations=[op])).status_code,200)
                self.assertFalse(c.get('/api/health').json()['trading_commands_enabled'])
