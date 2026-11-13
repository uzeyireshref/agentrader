import copy,json,tempfile,unittest
from pathlib import Path
from agentrader.indicator_config import IndicatorService,defaults,validate,series,SOURCES
from agentrader.migrations import migrate,connect
from agentrader.drawings.service import DrawingConflict,DrawingError,DrawingService
from agentrader.analysis import ema,rsi
class IndicatorConfigurationTests(unittest.TestCase):
 def test_revision_idempotency_conflict_owner_and_workspace_isolation(self):
  with tempfile.TemporaryDirectory() as f:
   p=Path(f)/'app.db';migrate(p);s=IndicatorService(p,'alice');original=s.load('main');items=original['indicators'];items[0].update(period=9,source='hlc3',enabled=True)
   saved=s.save('main','save-1',0,items);self.assertEqual(saved['revision'],1);self.assertEqual([c['revision'] for c in saved['indicators']],[1,0,0]);self.assertEqual(s.save('main','save-1',0,items)['indicators'],saved['indicators'])
   with self.assertRaises(DrawingConflict):s.save('main','save-2',0,items)
   with self.assertRaises(DrawingConflict):s.save('main','save-1',0,defaults())
   stale=copy.deepcopy(saved['indicators']);stale[0]['revision']=0
   with self.assertRaises(DrawingConflict):s.save('main','save-3',1,stale)
   self.assertEqual(IndicatorService(p,'alice').load('main')['indicators'],saved['indicators']);self.assertEqual(IndicatorService(p,'bob').load('main')['revision'],0);self.assertEqual(s.load('other')['revision'],0)
   DrawingService(p,'alice').save_workspace('main','pref',0,{'symbol':'ETHUSDT','interval':'5m'});self.assertEqual(s.load('main')['indicators'],saved['indicators'])
 def test_schema_bounds_and_unsupported_semantics_rejected(self):
  for field,value in [('period',0),('period',501),('period',True),('period',1.5),('source','volume'),('source',None),('enabled',1),('smoothing','RMA'),('anchor','SESSION'),('pane','oscillator'),('calculation_version',2),('revision',-1),('indicator_id','other')]:
   c=defaults();c[0][field]=value
   with self.subTest(field=field,value=value),self.assertRaises(DrawingError):validate(c)
  for c in [[],defaults()[::-1],defaults()+defaults()]:
   with self.assertRaises(DrawingError):validate(c)
 def test_reference_seed_and_warmup_preserve_existing_analysis(self):
  rows=[dict(time=1800000000+i*60,open=100+i%7,high=120+i%11,low=80+i%3,close=103+(i*7)%19) for i in range(80)]
  for source in SOURCES:
   values=[dict(open=r['open'],high=r['high'],low=r['low'],close=r['close'],hl2=(r['high']+r['low'])/2,hlc3=(r['high']+r['low']+r['close'])/3,ohlc4=(r['open']+r['high']+r['low']+r['close'])/4)[source] for r in rows]
   for config in defaults():
    for period in [1,3,14,50,500]:
     config.update(source=source,period=period);out=series(rows,config);start=period-1 if config['kind']=='EMA' else period
     self.assertEqual(len(out),max(0,len(rows)-start));self.assertEqual(out[0]['time'] if out else None,rows[start]['time'] if start<len(rows) else None)
     ref=ema if config['kind']=='EMA' else rsi
     for item in out:
      end=(item['time']-rows[0]['time'])//60+1;self.assertAlmostEqual(item['value'],ref(values[:end],period),places=10)
 def test_flat_v1_rsi_is_50_and_ema_seed_is_arithmetic_mean(self):
  rows=[dict(time=1800000000+i*60,open=10,high=10,low=10,close=10) for i in range(20)];c=defaults()[2];self.assertEqual(series(rows[:14],c),[]);self.assertEqual(series(rows,c)[0]['value'],50)
  c=defaults()[0];c['period']=3;rows[0]['close']=1;rows[1]['close']=2;rows[2]['close']=3;rows[3]['close']=6;self.assertEqual([p['value'] for p in series(rows[:4],c)],[2,4])
 def test_http_validation_conflict_and_restart(self):
  from fastapi.testclient import TestClient
  from agentrader.api.app import create_app
  from agentrader.application.settings import WebSettings
  with tempfile.TemporaryDirectory() as f:
   p=Path(f);settings=WebSettings(p/'app.db',p/'exec.db',market_database=p/'market.db')
   with TestClient(create_app(settings),base_url='http://127.0.0.1') as client:
    value=client.get('/api/workspaces/main/indicators').json();value['indicators'][2].update(period=7,enabled=True)
    body=dict(request_id='indicator-api',expected_revision=0,indicators=value['indicators']);r=client.put('/api/workspaces/main/indicators',json=body);self.assertEqual(r.status_code,200);self.assertEqual(r.json()['indicators'][2]['revision'],1)
    self.assertTrue(client.put('/api/workspaces/main/indicators',json=body).json()['duplicate']);body['request_id']='other';self.assertEqual(client.put('/api/workspaces/main/indicators',json=body).status_code,409)
    body['expected_revision']=1;body['indicators'][0]['period']=501;self.assertEqual(client.put('/api/workspaces/main/indicators',json=body).status_code,422)
    self.assertFalse(client.get('/api/health').json()['trading_commands_enabled'])
   with TestClient(create_app(settings),base_url='http://127.0.0.1') as client:self.assertEqual(client.get('/api/workspaces/main/indicators').json()['indicators'][2]['period'],7)

 def test_shared_frontend_fixture_is_current_backend_reference(self):
  fixture=json.loads((Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/indicator-config-parity.json').read_text(encoding='utf-8'))
  for case in fixture['cases']:self.assertEqual(series(fixture['rows'],case['config']),case['points'])
