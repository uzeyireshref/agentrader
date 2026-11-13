import copy,json,tempfile,unittest
from pathlib import Path
from fractions import Fraction
from agentrader.drawings.service import geometry,DrawingError,DrawingService
from agentrader.drawings.calculations import query,CalculationBlocked,canonical_hash
from agentrader.drawings.contracts import legacy_contract,capability
from agentrader.migrations import migrate

START=1800000000
GRID=[START+i*900 for i in range(8)]
def line(kind='ray',reverse=False):
    anchors=[{'time':GRID[2],'price':'100.25'},{'time':GRID[4],'price':'110.75'}]
    if reverse:anchors.reverse()
    return dict(schema='chart-line/1',kind=kind,symbol='BTCUSDT',price_source='LAST_PRICE',anchors=anchors[:1] if kind=='horizontal_ray' else anchors,label=kind)
def number(result):v=result['value'];return Fraction(int(v['numerator']),int(v['denominator']))

class LineExtensionTests(unittest.TestCase):
    def test_direction_and_exact_forward_backward_queries(self):
        self.assertEqual(number(query(line(),'priceAt',time=GRID[6],times=GRID,interval='15m')),Fraction('121.25'))
        self.assertEqual(number(query(line(reverse=True),'priceAt',time=GRID[0],times=GRID,interval='15m')),Fraction('89.75'))
        for g,t in [(line(),GRID[1]),(line(reverse=True),GRID[5]),(line('horizontal_ray'),GRID[1])]:
            with self.assertRaises(CalculationBlocked) as e:query(g,'priceAt',time=t,times=GRID,interval='15m')
            self.assertEqual(e.exception.code,'OUT_OF_SCOPE')
    def test_extended_line_both_sides_and_grid_fail_closed(self):
        g=line('extended_line');self.assertEqual(number(query(g,'priceAt',time=GRID[0],times=GRID,interval='15m')),Fraction('89.75'))
        for grid,t in [(GRID,GRID[-1]+900),(GRID[:3]+GRID[4:],GRID[5])]:
            with self.assertRaises(CalculationBlocked):query(g,'priceAt',time=t,times=grid,interval='15m')
        for reverse in [False,True]:self.assertEqual(len(canonical_hash(line('ray',reverse),times=GRID,interval='15m')),64)
    def test_horizontal_ray_utc_scope_and_flat_sloped_lines(self):
        self.assertEqual(number(query(line('horizontal_ray'),'priceAt',time=GRID[-1]+900000)),Fraction('100.25'))
        g=line();g['anchors'][1]['price']='100.25';self.assertEqual(number(query(g,'priceAt',time=GRID[-1],times=GRID,interval='15m')),Fraction('100.25'))
        g['anchors'][1]['time']=g['anchors'][0]['time']
        with self.assertRaises(DrawingError):geometry(g)
    def test_versioned_zone_scope_and_legacy_meaning(self):
        z=dict(kind='zone',symbol='BTCUSDT',price_source='LAST_PRICE',label='z',anchors=line()['anchors'])
        with self.assertRaises(CalculationBlocked):query(z,'contains',time=GRID[0],query_price='105')
        unbounded={**z,'schema':'chart-zone/1','time_scope':'unbounded'}
        self.assertTrue(query(unbounded,'contains',time=GRID[0],query_price='105')['value'])
        self.assertEqual(number(query(unbounded,'distance',time=GRID[7],query_price='120')),Fraction('9.25'))
        self.assertNotEqual(canonical_hash(z),canonical_hash(unbounded))
    def test_schema_strictness_and_nonpositive_projection(self):
        for g in [{k:v for k,v in line().items() if k!='schema'},{**line(),'schema':'wrong'},{**line(),'extra':True}]:
            with self.assertRaises(DrawingError):geometry(g)
        g=line('extended_line');g['anchors'][1]['price']='1'
        with self.assertRaises(CalculationBlocked) as e:query(g,'priceAt',time=GRID[-1],times=GRID,interval='15m')
        self.assertEqual(e.exception.code,'NON_POSITIVE_PROJECTION')
    def test_restart_revision_and_contract_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'app.db';migrate(path);service=DrawingService(path,'owner');saved=service.create('main','ray',line(reverse=True));contract=legacy_contract(saved)
            self.assertEqual(contract['time_scope']['mode'],'BACKWARD_RAY');self.assertTrue(capability('drawing','ray')['computable'])
            self.assertEqual(DrawingService(path,'owner').show(saved['drawing_id'])['geometry'],saved['geometry'])
            service.update(saved['drawing_id'],'delete',1,deleted=True);self.assertTrue(service.show(saved['drawing_id'])['deleted'])
    def test_v3_api_isolation_and_revision_conflict(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)
            with TestClient(create_app(WebSettings(f/'app.db',f/'execution.db',market_database=f/'market.db')),base_url='http://127.0.0.1') as c:
                data={'request_id':'new','geometry':line()};self.assertEqual(c.post('/api/workspaces/main/drawings',json=data).status_code,422)
                saved=c.post('/api/workspaces/main/drawings?format_version=3',json=data).json();path='/api/drawings/'+saved['drawing_id']
                for version in [1,2]:
                    self.assertEqual(c.get('/api/workspaces/main/drawings?format_version='+str(version)).json()['drawings'],[])
                    self.assertEqual(c.get(path+'?format_version='+str(version)).status_code,422)
                    self.assertEqual(c.patch(path+'?format_version='+str(version),json={}).status_code,422)
                    self.assertEqual(c.request('DELETE',path+'?format_version='+str(version),json={}).status_code,422)
                changed={**saved['geometry'],'label':'renamed'};body={'request_id':'edit','expected_revision':1,'geometry':changed}
                self.assertEqual(c.patch(path+'?format_version=3',json=body).status_code,200)
                self.assertEqual(c.patch(path+'?format_version=3',json={**body,'request_id':'stale'}).status_code,409)
                self.assertEqual(len(c.get('/api/workspaces/main/drawings?format_version=3').json()['drawings']),1)
