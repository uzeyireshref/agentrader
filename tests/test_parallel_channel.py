import copy
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from agentrader.drawings.service import DrawingService, DrawingError, geometry, management
from agentrader.drawings.calculations import query, canonical_hash, CalculationBlocked
from agentrader.drawings.contracts import legacy_contract, capability
from agentrader.migrations import migrate

START=1800000000
GRID=[START+i*900 for i in range(12)]
def channel():
    return dict(schema='chart-channel/1',kind='parallel_channel',symbol='BTCUSDT',price_source='LAST_PRICE',label='channel',anchors=[dict(time=GRID[2],price='100.25'),dict(time=GRID[6],price='110.75'),dict(time=GRID[4],price='115.5')])
def q(g,op='boundsAt',**kw):return query(g,op,time=GRID[6],times=GRID,interval='15m',**kw)['value']

class ParallelChannelTests(unittest.TestCase):
    def test_exact_boundaries_midpoint_width_and_reverse_baseline(self):
        p=channel();v=q(p)
        self.assertEqual({k:v[k]['decimal'] for k in v},dict(lower='110.75',upper='120.75',middle='115.75',width='10'))
        p['anchors'][:2]=p['anchors'][:2][::-1]
        self.assertEqual(q(p),v)
        self.assertTrue(capability('drawing','parallel_channel')['computable'])

    def test_negative_offset_flat_baseline_and_fractional_midpoint(self):
        p=channel();p['anchors'][2]['price']='95.5';v=q(p)
        self.assertEqual(v['lower']['decimal'],'100.75');self.assertEqual(v['upper']['decimal'],'110.75')
        p['anchors'][0]['price']=p['anchors'][1]['price']='100';p['anchors'][2]['price']='100.25'
        self.assertEqual(q(p)['middle']['decimal'],'100.125')

    def test_contains_includes_boundaries_and_distance_is_price_units(self):
        p=channel()
        for price in ['110.75','115.75','120.75']:self.assertTrue(q(p,'contains',query_price=price))
        self.assertFalse(q(p,'contains',query_price='121'))
        self.assertEqual(q(p,'distance',query_price='121')['decimal'],'0.25')
        self.assertEqual(q(p,'distance',query_price='109')['decimal'],'1.75')
        self.assertEqual(q(p,'distance',query_price='119')['decimal'],'0')

    def test_zero_width_vertical_outside_third_and_nonpositive_boundary_rejected(self):
        cases=[];p=channel();p['anchors'][2]['price']='105.5';cases.append(p)
        p=channel();p['anchors'][1]['time']=p['anchors'][0]['time'];cases.append(p)
        p=channel();p['anchors'][2]['time']=GRID[8];cases.append(p)
        p=channel();p['anchors'][0]['price']='5';p['anchors'][1]['price']='15';p['anchors'][2]=dict(time=GRID[6],price='1');cases.append(p)
        cases.append({**channel(),'schema':'wrong'})
        for p in cases:
            with self.assertRaises(DrawingError):geometry(p)

    def test_fail_closed_scope_missing_grid_and_gap_even_outside_channel(self):
        for grid,t,code in [(GRID,GRID[1],'OUT_OF_SCOPE'),(GRID[:-2]+GRID[-1:],GRID[4],'GRID_GAP'),(GRID[3:],GRID[4],'GRID_OUT_OF_RANGE')]:
            with self.subTest(code=code),self.assertRaises(CalculationBlocked) as error:query(channel(),'boundsAt',time=t,times=grid,interval='15m')
            self.assertEqual(error.exception.code,code)
        with self.assertRaises(CalculationBlocked):canonical_hash(channel())
        self.assertEqual(len(canonical_hash(channel(),times=GRID,interval='15m')),64)

    def test_revision_restart_inverse_and_contract_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'app.db';migrate(db);s=DrawingService(db,'owner');a=s.create('main','new',channel())
            g=copy.deepcopy(a['geometry']);g['anchors'][2]['price']='120.5';b=s.update(a['drawing_id'],'edit',1,g)
            c=s.operations('main','undo',[dict(drawing_id=a['drawing_id'],expected_revision=2,geometry=a['geometry'],management=management(),deleted=False)])['drawings'][0]
            self.assertEqual(DrawingService(db,'owner').show(a['drawing_id'])['geometry'],channel())
            contract=legacy_contract(c);self.assertEqual(contract['time_scope']['end'],GRID[6]);self.assertEqual(contract['params']['geometry_schema'],'chart-channel/1');self.assertFalse(contract['capabilities']['order_authority'])
            self.assertNotEqual(canonical_hash(a['geometry'],times=GRID,interval='15m'),canonical_hash(b['geometry'],times=GRID,interval='15m'))

    def test_v6_isolation_for_read_create_update_delete_and_batch(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)
            with TestClient(create_app(WebSettings(f/'app.db',f/'exec.db',market_database=f/'market.db')),base_url='http://127.0.0.1') as c:
                body=dict(request_id='new',geometry=channel());self.assertEqual(c.post('/api/workspaces/main/drawings?format_version=5',json=body).status_code,422)
                r=c.post('/api/workspaces/main/drawings?format_version=6',json=body);self.assertEqual(r.status_code,201);a=r.json();path='/api/drawings/'+a['drawing_id']
                for v in range(1,6):
                    suffix='?format_version='+str(v);self.assertEqual(c.get('/api/workspaces/main/drawings'+suffix).json()['drawings'],[]);self.assertEqual(c.get(path+suffix).status_code,422)
                self.assertEqual(c.patch(path+'?format_version=5',json=dict(request_id='old',expected_revision=1,geometry=channel())).status_code,422)
                self.assertEqual(c.request('DELETE',path+'?format_version=5',json=dict(request_id='old',expected_revision=1)).status_code,422)
                op=dict(drawing_id=a['drawing_id'],expected_revision=1,geometry=a['geometry'],management=a['management'],deleted=False)
                self.assertEqual(c.post('/api/workspaces/main/drawing-operations?format_version=5',json=dict(request_id='old-batch',operations=[op])).status_code,422)
                self.assertEqual(c.post('/api/workspaces/main/drawing-operations?format_version=6',json=dict(request_id='new-batch',operations=[op])).status_code,200)
