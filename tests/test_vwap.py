import copy,json,tempfile,unittest
from pathlib import Path
from fractions import Fraction
from decimal import Decimal
from agentrader.vwap import vwap_series
from agentrader.indicator_config import defaults_v3,defaults_v4,validate_v4,IndicatorService
from agentrader.drawings.service import DrawingError
from agentrader.migrations import migrate
DAY=1800000000//86400*86400

def rows(n=192,start=DAY,step=900):
 result=[]
 for i in range(n):
  price=100+i%7;volume=Decimal('0.1')*(i%5+1);quote=Decimal(price)*volume
  result.append(dict(time=start+i*step,close_time=(start+(i+1)*step)*1000-1,closed=i<n-1,open=price,high=price+2,low=price-1,close=price,volume=float(volume),quote_volume=float(quote),exact=dict(schema='chart-exact-decimal/1',state='VERIFIED',provenance='UPSTREAM_DECIMAL_TEXT',volume=str(volume),quote_volume=str(quote))))
 return result
class VwapTests(unittest.TestCase):
 def test_daily_session_weighting_and_reset_against_decimal(self):
  data=rows();c=defaults_v4()[7];out=vwap_series(data,c,'15m','BTCUSDT');self.assertEqual(len(out['points']),192);total=Decimal(0);weighted=Decimal(0)
  for r,p in zip(data,out['points']):
   if r['time']%86400==0:total=weighted=Decimal(0)
   volume=Decimal(str(r['volume']));source=(Decimal(r['high'])+Decimal(r['low'])+Decimal(r['close']))/3;total+=volume;weighted+=source*volume;self.assertAlmostEqual(p['value'],float(weighted/total),places=10)
 def test_zero_volume_unavailable_then_preserves_positive_accumulator(self):
  data=rows(98);c=defaults_v4()[7]
  for i in [0,1,4,96]:data[i].update(volume=0,quote_volume=0);data[i]['exact'].update(volume='0',quote_volume='0')
  for exact in [False,True]:
   if exact:c.update(source='quote_base');c['params']['computation_mode']='EXACT_QUOTE_BASE'
   out=vwap_series(data,c,'15m','BTCUSDT');states=out['states'];self.assertEqual(states[0]['state'],'ZERO_CUMULATIVE_VOLUME');self.assertEqual(states[1]['state'],'ZERO_CUMULATIVE_VOLUME');self.assertEqual(states[96]['state'],'ZERO_CUMULATIVE_VOLUME');points={p['time']:p['value'] for p in out['points']};self.assertEqual(points[data[4]['time']],points[data[3]['time']]);self.assertNotIn('value',out['plot'][0])
 def test_incomplete_session_gap_and_repaired_history(self):
  data=rows();c=defaults_v4()[7];partial=vwap_series(data[10:],c,'15m','BTCUSDT');self.assertEqual(partial['states'][0]['state'],'SESSION_START_MISSING');self.assertEqual(partial['states'][-1]['state'],'READY');broken=data[:20]+data[21:];gap=vwap_series(broken,c,'15m','BTCUSDT');self.assertEqual(gap['states'][20]['state'],'GRID_GAP');self.assertEqual(gap['states'][95]['state'],'READY');self.assertNotIn('value',gap['plot'][20]);full=vwap_series(data,c,'15m','BTCUSDT');self.assertEqual(partial['points'][-1],full['points'][-1]);self.assertEqual(vwap_series(copy.deepcopy(data),c,'15m','BTCUSDT'),full)
 def test_anchor_scope_before_anchor_missing_history_and_grid(self):
  data=rows();c=defaults_v4()[8];self.assertEqual(vwap_series(data,c,'15m','BTCUSDT')['states'][-1]['state'],'ANCHOR_UNSET');c['params'].update(anchor_time=data[10]['time'],anchor_symbol='BTCUSDT');out=vwap_series(data,c,'15m','BTCUSDT');self.assertEqual(out['states'][0]['state'],'BEFORE_ANCHOR');self.assertAlmostEqual(out['points'][0]['value'],(data[10]['high']+data[10]['low']+data[10]['close'])/3);self.assertEqual(vwap_series(data[11:],c,'15m','BTCUSDT')['states'][0]['state'],'ANCHOR_HISTORY_MISSING');self.assertEqual(vwap_series(data,c,'15m','ETHUSDT')['states'][0]['state'],'ANCHOR_SYMBOL_MISMATCH');c['params']['anchor_time']+=60;self.assertEqual(vwap_series(data,c,'15m','BTCUSDT')['states'][0]['state'],'ANCHOR_NOT_ON_GRID')
 def test_exact_quote_base_uses_rational_native_decimals_not_projection(self):
  data=rows(2)
  for r in data:r.update(open=10,high=11,low=9,close=10)
  data[0]['exact'].update(volume='0.100000000000000001',quote_volume='1.000000000000000019');data[1]['exact'].update(volume='0.200000000000000003',quote_volume='2.000000000000000041')
  for r in data:r.update(volume=float(r['exact']['volume']),quote_volume=float(r['exact']['quote_volume']))
  c=defaults_v4()[7];c.update(source='quote_base');c['params']['computation_mode']='EXACT_QUOTE_BASE';out=vwap_series(data,c,'15m','BTCUSDT');expected=sum(Fraction(r['exact']['quote_volume']) for r in data)/sum(Fraction(r['exact']['volume']) for r in data);ratio=out['points'][-1]['exact_ratio'];self.assertEqual(Fraction(int(ratio['numerator']),int(ratio['denominator'])),expected);self.assertNotEqual(expected,Fraction(str(sum(r['quote_volume'] for r in data)))/Fraction(str(sum(r['volume'] for r in data))));self.assertFalse(out['provenance']['trade_vwap_claim'])
 def test_exact_unproven_and_inconsistent_volume_do_not_fallback(self):
  for change in [lambda r:r.pop('exact'),lambda r:r['exact'].update(state='UNPROVEN'),lambda r:r['exact'].update(volume='99'),lambda r:r.update(volume=0),lambda r:r['exact'].update(quote_volume='0')]:
   data=rows();change(data[3]);c=defaults_v4()[7];c.update(source='quote_base');c['params']['computation_mode']='EXACT_QUOTE_BASE';out=vwap_series(data,c,'15m','BTCUSDT');self.assertEqual(out['states'][3]['state'],'EXACT_VOLUME_UNPROVEN');self.assertEqual(out['states'][95]['state'],'EXACT_VOLUME_UNPROVEN');self.assertEqual(out['states'][96]['state'],'READY')
 def test_daily_and_weekly_session_scope_and_anchor_across_days(self):
  data=rows(2,step=86400);c=defaults_v4()[7];out=vwap_series(data,c,'1d','BTCUSDT');self.assertEqual(len(out['points']),2)
  weekly=rows(2,start=345600+3000*604800,step=604800);self.assertEqual(vwap_series(weekly,c,'1w','BTCUSDT')['states'][0]['state'],'SESSION_INTERVAL_UNSUPPORTED')
  c=defaults_v4()[8];c['params'].update(anchor_time=DAY,anchor_symbol='BTCUSDT');data=rows();out=vwap_series(data,c,'15m','BTCUSDT');self.assertNotEqual(out['points'][96]['value'],(data[96]['high']+data[96]['low']+data[96]['close'])/3);broken=data[:20]+data[21:];self.assertEqual(vwap_series(broken,c,'15m','BTCUSDT')['states'][-1]['state'],'GRID_GAP')
 def test_v4_validation_migration_and_http_persistence(self):
  for field,value in [('period',2),('source','quote_base')]:
   data=defaults_v4();data[7][field]=value
   with self.assertRaises(DrawingError):validate_v4(data)
  for key,value in [('anchor_time',True),('anchor_time',-1),('anchor_symbol','BTCUSDT'),('computation_mode','K_VOLUME')]:
   data=defaults_v4();data[8]['params'][key]=value
   with self.assertRaises(DrawingError):validate_v4(data)
  with tempfile.TemporaryDirectory() as f:
   db=Path(f)/'app.db';migrate(db);s=IndicatorService(db,'owner');old=defaults_v3();old[2]['calculation_version']=1;s.save('main','old',0,old,3);expanded=s.load('main',4);self.assertEqual(expanded['indicators'][:7],s.load('main',3)['indicators']);expanded['indicators'][8]['params'].update(anchor_time=DAY,anchor_symbol='BTCUSDT');saved=s.save('main','vwap',1,expanded['indicators'],4);self.assertEqual(saved['indicators'][8]['revision'],1);self.assertTrue(s.save('main','vwap',1,expanded['indicators'],4)['duplicate']);self.assertEqual(IndicatorService(db,'owner').load('main',4)['indicators'],saved['indicators'])
   with self.assertRaises(DrawingError):s.load('main',3)
 def test_v4_http_roundtrip_and_source_protection(self):
  from fastapi.testclient import TestClient
  from agentrader.api.app import create_app
  from agentrader.application.settings import WebSettings
  with tempfile.TemporaryDirectory() as f:
   p=Path(f)
   with TestClient(create_app(WebSettings(p/'app.db',p/'exec.db',market_database=p/'market.db')),base_url='http://127.0.0.1') as c:
    url='/api/workspaces/main/indicators?format_version=4';head=c.get(url).json();self.assertEqual(len(head['indicators']),9);head['indicators'][7]['enabled']=True;body=dict(request_id='t11-http',expected_revision=0,indicators=head['indicators']);self.assertEqual(c.put(url,json=body).status_code,200);self.assertEqual(c.get('/api/workspaces/main/indicators?format_version=3').status_code,422);self.assertFalse(c.get('/api/health').json()['trading_commands_enabled'])

 def test_shared_vwap_fixture_is_current(self):
  data=json.loads((Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/vwap-parity.json').read_text(encoding='utf-8'))
  for c in data['cases']:self.assertEqual(vwap_series(data['datasets'][c['dataset']],c['config'],c['interval'],c['symbol']),c['result'])
 def test_registry_exposes_provenance_inputs_without_order_or_canonical_query(self):
  from agentrader.drawings.contracts import capability
  for kind in ['session_vwap','anchored_vwap']:
   c=capability('indicator',kind);self.assertEqual(c['display_model']['schema'],'chart-indicators/4');self.assertEqual(c['canonical_queries'],[]);self.assertFalse(c['order_authority']);self.assertFalse(c['tracking_activation'])
