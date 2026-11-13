import copy
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from agentrader.drawings.service import DrawingService, DrawingError, geometry, management
from agentrader.drawings.fibonacci import levels, LEGACY_LEVELS
from agentrader.drawings.calculations import query, CalculationBlocked, canonical_hash
from agentrader.drawings.contracts import legacy_contract, capability
from agentrader.migrations import migrate

START=1800000000
def fib(versioned=True,kind='fibonacci'):
    g=dict(kind=kind,symbol='BTCUSDT',price_source='LAST_PRICE',label='fib',anchors=[dict(time=START,price='100.25'),dict(time=START+9000,price='110.75')])
    if versioned:g.update(schema='chart-fibonacci/1',levels=['0','0.236','1','1.618','2.618'],time_scope='bounded')
    return g
def q(g,r,time=START+4500):return query(g,'level',ratio=r,time=time)['value']

class ConfigurableFibonacciTests(unittest.TestCase):
    def test_exact_ratios_extension_and_reverse_have_independent_decimal_references(self):
        g=fib(kind='fibonacci_extension');self.assertEqual(q(g,'1.618')['decimal'],'117.239')
        self.assertEqual(q(g,'2.618')['decimal'],'127.739')
        g['anchors'].reverse();self.assertEqual(q(g,'1.618')['decimal'],'93.761')
        self.assertEqual(q(g,'0.236')['decimal'],'108.272')

    def test_ratios_are_strict_normalized_distinct_and_bounded(self):
        self.assertEqual(levels(['-00.2500','+01.000','-0.000']),['-0.25','1','0'])
        for value in [['0','0.00'],['1'],['0','11'],['0','NaN'],['0',1],['0','0.1234567890123'],['0','1e0'],['0']*25]:
            with self.subTest(value=value),self.assertRaises(ValueError):levels(value)
        g=fib();g['levels']=['0','0.00']
        with self.assertRaises(DrawingError):geometry(g)

    def test_legacy_seven_levels_meaning_and_hash_are_unchanged(self):
        old=fib(False);h=canonical_hash(old)
        for r in LEGACY_LEVELS:
            v=q(old,r);self.assertEqual(Fraction(int(v['numerator']),int(v['denominator'])),Fraction('100.25')+Fraction('10.5')*Fraction(r))
        with self.assertRaises(CalculationBlocked):q(old,'1.618')
        self.assertEqual(canonical_hash(old),h)
        self.assertNotIn('schema',geometry(old))

    def test_bounded_right_unbounded_scopes_and_unselected_ratio_are_explicit(self):
        g=fib()
        with self.assertRaises(CalculationBlocked):q(g,'1',START-1)
        g['time_scope']='right';self.assertEqual(q(g,'1',START+999999)['decimal'],'110.75')
        with self.assertRaises(CalculationBlocked):q(g,'1',START-1)
        g['time_scope']='unbounded';self.assertEqual(q(g,'1',START-1)['decimal'],'110.75')
        with self.assertRaises(CalculationBlocked) as e:q(g,'0.5')
        self.assertEqual(e.exception.code,'UNSUPPORTED_RATIO')

    def test_nonpositive_levels_are_stored_but_not_fabricated_or_tick_rounded(self):
        g=fib();g['anchors'].reverse();g['anchors'][1]['price']='90';g['levels']=['0','10'];geometry(g)
        with self.assertRaises(CalculationBlocked) as e:q(g,'10')
        self.assertEqual(e.exception.code,'NON_POSITIVE_LEVEL')
        self.assertEqual(q(fib(),'0.236')['decimal'],'102.728')
        self.assertFalse(query(fib(),'level',ratio='0.236',time=START)['order_authority'])

    def test_promotion_revision_inverse_restart_and_schema_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'app.db';migrate(db);s=DrawingService(db,'owner');old=s.create('main','old',fib(False));s.update(old['drawing_id'],'rename',1,{**old['geometry'],'label':'renamed'})
            self.assertNotIn('schema',s.show(old['drawing_id'])['geometry'])
            promoted=s.update(old['drawing_id'],'promote',2,fib());self.assertEqual(legacy_contract(promoted)['params']['ratios'],fib()['levels'])
            restored=s.operations('main','undo',[dict(drawing_id=old['drawing_id'],expected_revision=3,geometry=old['geometry'],management=management(),deleted=False)])['drawings'][0]
            self.assertEqual(DrawingService(db,'owner').show(old['drawing_id'])['geometry'],old['geometry'])
            self.assertNotIn('schema',restored['geometry'])
            self.assertFalse(capability('drawing','fibonacci_projection')['readable'])

    def test_v7_isolation_preserves_legacy_record_and_blocks_old_client_promotion(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)
            with TestClient(create_app(WebSettings(f/'app.db',f/'exec.db',market_database=f/'market.db')),base_url='http://127.0.0.1') as c:
                old=c.post('/api/workspaces/main/drawings',json=dict(request_id='old',geometry=fib(False))).json();path='/api/drawings/'+old['drawing_id']
                self.assertEqual(c.patch(path+'?format_version=6',json=dict(request_id='bad',expected_revision=1,geometry=fib())).status_code,422)
                self.assertEqual(c.patch(path+'?format_version=7',json=dict(request_id='promote',expected_revision=1,geometry=fib())).status_code,200)
                for v in range(1,7):
                    self.assertEqual(c.get('/api/workspaces/main/drawings?format_version='+str(v)).json()['drawings'],[])
                    self.assertEqual(c.get(path+'?format_version='+str(v)).status_code,422)
                op=dict(drawing_id=old['drawing_id'],expected_revision=2,geometry=fib(),management=management(),deleted=False)
                self.assertEqual(c.post('/api/workspaces/main/drawing-operations?format_version=6',json=dict(request_id='old-batch',operations=[op])).status_code,422)
                self.assertEqual(c.post('/api/workspaces/main/drawing-operations?format_version=7',json=dict(request_id='new-batch',operations=[op])).status_code,200)
