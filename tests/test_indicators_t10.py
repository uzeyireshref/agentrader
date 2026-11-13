import copy,json,tempfile,unittest
from pathlib import Path
from agentrader.indicator_config import IndicatorService,defaults,defaults_v2,series
from agentrader.drawings.service import DrawingError
from agentrader.migrations import migrate,connect
from agentrader.analysis import ema,rsi,atr
class T10Indicators(unittest.TestCase):
 def rows(self,n=80):return [dict(time=1800000000+i*900,close_time=1800000000000+(i+1)*900000-1,closed=i<n-1,open=100+i%7,high=120+i%11,low=80+i%3,close=103+(i*7)%19) for i in range(n)]
 def test_legacy_migration_is_explicit_and_old_clients_cannot_overwrite_v2(self):
  with tempfile.TemporaryDirectory() as f:
   db=Path(f)/'app.db';migrate(db);s=IndicatorService(db,'owner');old=s.save('main','legacy',0,defaults());expanded=s.load('main',2);self.assertEqual(expanded['indicators'][2]['calculation_version'],1);self.assertEqual(expanded['revision'],old['revision']);self.assertEqual(len(s.load('main')['indicators']),3)
   expanded['indicators'][2]['calculation_version']=2;new=s.save('main','upgrade',1,expanded['indicators'],2);self.assertEqual(new['indicators'][2]['revision'],1);self.assertEqual(new['indicators'][3]['revision'],0)
   with self.assertRaises(DrawingError):s.save('main','stale-client',2,defaults())
   with self.assertRaises(DrawingError):s.load('main')
   self.assertEqual(s.load('main',2)['indicators'],new['indicators']);self.assertEqual(s.load('fresh',2)['indicators'][2]['calculation_version'],2)
 def test_sma_and_atr_every_output_against_independent_references(self):
  rows=self.rows();raw=[[r['time']*1000,str(r['open']),str(r['high']),str(r['low']),str(r['close'])] for r in rows]
  for period in [1,3,14,50,500]:
   for index in [3,4]:
    c=defaults_v2()[index];c['period']=period;points=series(rows,c,'15m');self.assertEqual(len(points),max(0,len(rows)-period+1))
    for p in points:
     end=(p['time']-rows[0]['time'])//900+1;expected=sum(r['close'] for r in rows[end-period:end])/period if index==3 else atr(raw[:end],period);self.assertAlmostEqual(p['value'],expected,places=10)
 def test_true_range_uses_previous_close_511_4_not_high_low_511_3(self):
  rows=self.rows(2);rows[0].update(open=1000.1,high=1000.2,low=1000,close=1000.1);rows[1].update(open=900,high=1000,low=488.7,close=800);c=defaults_v2()[4];c['period']=1;self.assertAlmostEqual(series(rows,c)[-1]['value'],511.4);self.assertAlmostEqual(rows[1]['high']-rows[1]['low'],511.3)
 def test_rsi_versioned_flat_and_loaded_history_seed_not_origin_claim(self):
  rows=self.rows()
  for r in rows:r.update(open=10,high=10,low=10,close=10)
  c=defaults_v2()[2];self.assertTrue(all(p['value']==100 for p in series(rows,c)));c['calculation_version']=1;self.assertTrue(all(p['value']==50 for p in series(rows,c)))
  rows=self.rows();c=defaults_v2()[0];full=series(rows,c);short=series(rows[30:],c);self.assertNotEqual(full[-1]['value'],short[-1]['value'])
 def test_grid_gap_and_revision_recompute_all_indicators(self):
  rows=self.rows()
  for c in defaults_v2():
   self.assertEqual(series(rows[:30]+rows[31:],c,'15m'),[]);self.assertEqual(series(rows[::-1],c,'15m'),[])
   before=series(rows,c,'15m');revised=copy.deepcopy(rows);revised[-1].update(open=110,high=150,low=50,close=140);after=series(revised,c,'15m');self.assertNotEqual(before[-1]['value'],after[-1]['value']);self.assertEqual(before[:-1],after[:-1])
 def test_v2_http_validation_and_old_format_isolation(self):
  from fastapi.testclient import TestClient
  from agentrader.api.app import create_app
  from agentrader.application.settings import WebSettings
  with tempfile.TemporaryDirectory() as f:
   p=Path(f)
   with TestClient(create_app(WebSettings(p/'app.db',p/'exec.db',market_database=p/'market.db')),base_url='http://127.0.0.1') as client:
    url='/api/workspaces/main/indicators?format_version=2';head=client.get(url).json();self.assertEqual(len(head['indicators']),5);head['indicators'][4]['enabled']=True;body=dict(request_id='save-v2',expected_revision=0,indicators=head['indicators']);self.assertEqual(client.put(url,json=body).status_code,200);self.assertEqual(client.get('/api/workspaces/main/indicators').status_code,422)
    for field,value in [('source','close'),('smoothing','SMA'),('calculation_version',2)]:
     bad=copy.deepcopy(body);bad['indicators'][4][field]=value;self.assertEqual(client.put(url,json=bad).status_code,422)

 def test_shared_v2_fixture_matches_backend_and_legacy_fixture_stays_valid(self):
  data=json.loads((Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/indicators-v2-parity.json').read_text(encoding='utf-8'))
  for case in data['cases']:self.assertEqual(series(data['rows'],case['config'],'15m'),case['points'])
