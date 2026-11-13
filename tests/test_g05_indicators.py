import copy,json,tempfile,unittest
from decimal import Decimal,localcontext
from pathlib import Path
from agentrader.indicator_config import defaults_v2,defaults_v3,multi_series,validate_v3,IndicatorService
from agentrader.drawings.service import DrawingError,DrawingConflict
from agentrader.migrations import migrate
class G05Indicators(unittest.TestCase):
 def rows(self,n=80):return [dict(time=1800000000+i*900,close_time=1800000000000+(i+1)*900000-1,closed=True,open=100+i%7,high=125+i%11,low=80+i%3,close=103+(i*7)%19,volume=10,quote_volume=1000) for i in range(n)]
 def test_macd_all_smoothing_outputs_match_independent_decimal_reference(self):
  rows=self.rows();values=[Decimal(r['close']) for r in rows]
  def smooth(v,p,kind):
   if len(v)<p:return []
   out=[sum(v[:p])/p];alpha=Decimal(2)/(p+1)
   for i in range(p,len(v)):out.append(v[i]*alpha+out[-1]*(1-alpha) if kind=='EMA' else sum(v[i-p+1:i+1])/p)
   return out
  with localcontext() as ctx:
   ctx.prec=50
   for oscillator in ['EMA','SMA']:
    for signal in ['EMA','SMA']:
     c=defaults_v3()[5];c['params'].update(oscillator_type=oscillator,signal_type=signal);out=multi_series(rows,c,'15m');fast=smooth(values,12,oscillator)[14:];slow=smooth(values,26,oscillator);macd=[a-b for a,b in zip(fast,slow)];sig=smooth(macd,9,signal);hist=[a-b for a,b in zip(macd[8:],sig)]
     for key,ref,start in [('macd',macd,25),('signal',sig,33),('histogram',hist,33)]:
      self.assertEqual(len(out[key]),len(ref));self.assertEqual(out[key][0]['time'],rows[start]['time'])
      for actual,expected in zip(out[key],ref):self.assertAlmostEqual(actual['value'],float(expected),places=10)
 def test_bollinger_population_variance_ema_basis_and_display_offset(self):
  rows=self.rows(4)
  for r,c in zip(rows,[1,2,3,8]):r.update(open=c,high=c+1,low=c-.1,close=c)
  c=defaults_v3()[6];c['period']=3
  out=multi_series(rows,c,'15m');self.assertEqual(out['basis'][0]['value'],2);self.assertAlmostEqual(out['upper'][0]['value'],2+2*(2/3)**.5)
  c['params'].update(basis_type='EMA',offset=-2);shift=multi_series(rows,c,'15m');self.assertEqual(shift['basis'][-1]['value'],5);self.assertEqual(shift['basis'][0]['time'],rows[0]['time']);mean=13/3;variance=sum((x-mean)**2 for x in [2,3,8])/3;self.assertAlmostEqual(shift['upper'][-1]['value'],5+2*variance**.5)
 def test_parameter_and_style_validation(self):
  for idx,section,key,value in [(5,'params','fast_period',26),(5,'params','fast_period',True),(5,'params','signal_period',0),(5,'params','oscillator_type','WMA'),(6,'params','deviation',float('nan')),(6,'params','deviation',True),(6,'params','offset',1.5),(6,'params','offset',101),(6,'params','basis_type','RMA'),(5,'style','line_width',4)]:
   items=defaults_v3();items[idx][section][key]=value
   with self.subTest(key=key,value=value),self.assertRaises(DrawingError):validate_v3(items)
  for value in ['red','#fff','#123456;script',None]:
   items=defaults_v3();items[5]['style']['colors']['macd']=value
   with self.assertRaises(DrawingError):validate_v3(items)
 def test_v2_expansion_preserves_old_state_and_protects_new_objects(self):
  with tempfile.TemporaryDirectory() as f:
   db=Path(f)/'app.db';migrate(db);s=IndicatorService(db,'owner');old=defaults_v2();old[2]['calculation_version']=1;old[0]['enabled']=True;s.save('main','v2',0,old,2);expanded=s.load('main',3);self.assertEqual(expanded['indicators'][:5],s.load('main',2)['indicators']);self.assertFalse(expanded['indicators'][5]['enabled']);expanded['indicators'][5]['params']['signal_period']=7;expanded['indicators'][6]['style']['colors']['upper']='#aabbcc';saved=s.save('main','v3',1,expanded['indicators'],3);self.assertEqual([i['revision'] for i in saved['indicators'][-2:]],[1,1]);self.assertTrue(s.save('main','v3',1,expanded['indicators'],3)['duplicate'])
   with self.assertRaises(DrawingError):s.save('main','old',2,old,2)
   with self.assertRaises(DrawingConflict):s.save('main','stale',1,expanded['indicators'],3)
   self.assertEqual(IndicatorService(db,'owner').load('main',3)['indicators'],saved['indicators']);self.assertEqual(s.load('other',3)['revision'],0)
 def test_grid_gap_revision_and_warmup_outputs_are_independent(self):
  rows=self.rows()
  for c in defaults_v3()[5:]:
   bad=rows[:20]+rows[21:];self.assertTrue(all(not x for x in multi_series(bad,c,'15m').values()));before=multi_series(rows,c,'15m');revised=copy.deepcopy(rows);revised[-1].update(high=180,low=50,close=170);after=multi_series(revised,c,'15m')
   for key in before:self.assertNotEqual(before[key][-1]['value'],after[key][-1]['value']);self.assertEqual(before[key][:-1],after[key][:-1])
  warm=multi_series(rows[:30],defaults_v3()[5],'15m');self.assertTrue(warm['macd']);self.assertEqual(warm['signal'],[]);self.assertEqual(warm['histogram'],[])
 def test_v3_http_isolation_and_style_roundtrip(self):
  from fastapi.testclient import TestClient
  from agentrader.api.app import create_app
  from agentrader.application.settings import WebSettings
  with tempfile.TemporaryDirectory() as f:
   p=Path(f)
   with TestClient(create_app(WebSettings(p/'app.db',p/'exec.db',market_database=p/'market.db')),base_url='http://127.0.0.1') as client:
    url='/api/workspaces/main/indicators?format_version=3';items=client.get(url).json()['indicators'];items[5]['enabled']=True;body=dict(request_id='g05-http',expected_revision=0,indicators=items);r=client.put(url,json=body);self.assertEqual(r.status_code,200);self.assertEqual(r.json()['schema'],'chart-indicators/3');self.assertEqual(client.get('/api/workspaces/main/indicators?format_version=2').status_code,422);self.assertEqual(client.get(url).json()['indicators'],r.json()['indicators']);self.assertFalse(client.get('/api/health').json()['trading_commands_enabled'])
 def test_shared_fixture_matches_current_reference(self):
  data=json.loads((Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/g05-multi-parity.json').read_text(encoding='utf-8'))
  for case in data['cases']:self.assertEqual(multi_series(data['rows'],case['config'],'15m'),case['outputs'])

 def test_registry_exposes_multi_output_display_model_without_bot_queries(self):
  from agentrader.drawings.contracts import capability
  for kind,outputs in [('macd',['macd','signal','histogram']),('bb',['basis','upper','lower'])]:
   tool=capability('indicator',kind);self.assertEqual(tool['display_model']['outputs'],outputs);self.assertEqual(tool['display_model']['schema'],'chart-indicators/4');self.assertEqual(tool['canonical_queries'],[]);self.assertFalse(tool['computable']);self.assertFalse(tool['tracking_activation']);self.assertFalse(tool['order_authority'])
