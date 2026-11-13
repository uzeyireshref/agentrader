import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from agentrader.binding_eligibility import evaluate_binding,inspect_binding
from agentrader.binding_catalog import catalog
from agentrader.chart_bindings import BindingService,binding_hash
from agentrader.chart_evidence import snapshot
from agentrader.chart_clock import POLICY
from agentrader.drawings.service import DrawingService
from agentrader.indicator_config import defaults_v4
from agentrader.market_feed import MarketFeedHub,FeedState
from agentrader.migrations import migrate
from test_chart_evidence import fixture,capture

class EligibilityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.db=Path(self.tmp.name)/'app.db';migrate(self.db);self.s=BindingService(self.db,'owner')
  rows,market,quality=fixture(60);self.rows=rows;self.market=market;self.quality=quality;grid=[r['time'] for r in rows]
  d=DrawingService(self.db,'owner').create('main','drawing',dict(kind='horizontal',symbol='BTCUSDT',price_source='LAST_PRICE',label='Hedef',anchors=[dict(time=grid[2],price='100')]))
  self.drawing_id=d['drawing_id'];self.b=self.s.save_binding('main','binding','create',0,dict(type='drawing',object_id=d['drawing_id'],revision=1),'BTCUSDT','15m','LINEAR',grid,None,dict(operation='priceAt',output='value',ratio=None),dict(schema='chart-rule-definition/1',kind='touch',direction='ANY',tolerance='0',closed_candle=True,rearm_policy='EXPLICIT'))
  self.context=dict(transport_state='LIVE',identity=self.b['definition']['market'],rows=rows,market=market,quality=quality,stream_epoch='a'*32,generation=1,data_revision=1,data_proof=capture(rows,market,quality).view(),timing=dict(schema='chart-time-proof/1',policy=dict(POLICY),state='FRESH',reason=None,data_age_ms=1,upstream_age_upper_ms=2,uncertainty_ms=1,upstream_event_time=rows[-1]['time']*1000+3000))
  t=self.b['definition']['target'];self.target={**t,'deleted':False};self.evidence=catalog()
 def run_eval(self,b=None,c=None,t=None,e=None):
  return evaluate_binding(self.b if b is None else b,owner='owner',workspace_id='main',target=self.target if t is None else t,context=self.context if c is None else c,traceability=self.evidence if e is None else e)
 def rehash(self,b):b['definition_hash']=binding_hash(b['definition']);return b
 def test_valid_price_is_eligible_without_activation_or_order_authority(self):
  before=copy.deepcopy((self.b,self.context,self.target,self.evidence));r=self.run_eval();self.assertEqual(r['state'],'EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY');self.assertEqual(r['reasons'],[]);self.assertTrue(all(c['passed'] for c in r['checks']));self.assertEqual(before,(self.b,self.context,self.target,self.evidence));self.assertEqual(r['activation'],'DISABLED');self.assertFalse(r['live_eligible']);self.assertFalse(r['rule_evaluated']);self.assertFalse(r['order_authority']);self.assertEqual(r,self.run_eval())
 def test_every_required_context_proof_missing_fails_closed(self):
  for key in self.context:
   with self.subTest(key=key):
    c=copy.deepcopy(self.context);c.pop(key);self.assertEqual(self.run_eval(c=c)['state'],'BLOCKED')
  for key in self.context['timing']:
   if key in ('reason',):continue
   with self.subTest(timing=key):
    c=copy.deepcopy(self.context);c['timing'].pop(key);self.assertEqual(self.run_eval(c=c)['state'],'BLOCKED')
 def test_definition_tamper_owner_target_revision_and_stopped(self):
  for change in [lambda b:b.update(state='STOPPED'),lambda b:b['definition'].update(owner='other'),lambda b:b['definition']['target'].update(revision=2),lambda b:b['definition'].update(bot_capabilities={}),lambda b:b.update(definition_hash='f'*64)]:
   b=copy.deepcopy(self.b);change(b);self.assertEqual(self.run_eval(b=self.rehash(b) if b['definition_hash']!='f'*64 else b)['state'],'BLOCKED')
 def test_live_visibility_and_client_snapshot_are_not_proof(self):
  c={'status':'LIVE','visible':True};r=self.run_eval(c=c);self.assertEqual(r['state'],'BLOCKED');self.assertIn('DATA_PROOF_MISSING',r['reasons']);self.assertIn('CLOCK_UNTRUSTED',r['reasons'])
  b=copy.deepcopy(self.b);b['definition']['data_reference']['snapshot_hash']=self.context['data_proof']['snapshot_hash'];self.assertEqual(self.run_eval(b=self.rehash(b),c=c)['state'],'BLOCKED')
 def test_clock_policy_stale_negative_nan_future_and_closed_time(self):
  for k,v in [('data_age_ms',10001),('upstream_age_upper_ms',10001),('uncertainty_ms',1001),('data_age_ms',-1),('upstream_age_upper_ms',float('nan')),('state','BLOCKED'),('policy',{}),('upstream_event_time',self.rows[-2]['close_time'])]:
   with self.subTest(k=k,v=v):
    c=copy.deepcopy(self.context);c['timing'][k]=v;self.assertEqual(self.run_eval(c=c)['state'],'BLOCKED')
 def test_data_hash_generation_grid_and_native_sidecar_tamper(self):
  for change in [lambda c:c['data_proof'].update(snapshot_hash='0'*64),lambda c:c.update(generation=2),lambda c:c['rows'][0].update(close=106),lambda c:c['rows'][0]['exact'].update(close='106'),lambda c:c['market']['exact'].update(tick_size='1'),lambda c:c['rows'].pop(5),lambda c:c['quality'].update(state='GAP')]:
   c=copy.deepcopy(self.context);change(c);self.assertEqual(self.run_eval(c=c)['state'],'BLOCKED')
 def test_unsupported_kind_scale_grid_query_formula_and_missing_catalog(self):
  for change in [lambda d:d.update(scale='LOG'),lambda d:d['target'].update(kind='unknown'),lambda d:d['grid']['times'].pop(5),lambda d:d['query'].update(operation='execute'),lambda d:d['query'].update(ratio='1'),lambda d:d['rule'].update(closed_candle=False)]:
   b=copy.deepcopy(self.b);change(b['definition']);self.assertEqual(self.run_eval(b=self.rehash(b))['state'],'BLOCKED')
  self.assertEqual(self.run_eval(e={})['state'],'BLOCKED')
 def indicator(self,index=0):
  config=defaults_v4()[index];b=self.s.save_binding('main','indicator'+str(index),'indicator'+str(index),0,dict(type='indicator',object_id=config['indicator_id'],revision=0),'BTCUSDT','15m','LINEAR',[r['time'] for r in self.rows],None,dict(operation='valueAt',output='histogram' if config['kind']=='MACD' else 'upper' if config['kind']=='BB' else 'value',ratio=None),dict(schema='chart-rule-definition/1',kind='observe',direction='ANY',tolerance='0',closed_candle=True,rearm_policy='EXPLICIT'));return b,{**b['definition']['target'],'deleted':False}
 def test_observe_only_and_indicator_formula_warmup(self):
  for i in range(7):
   with self.subTest(i=i):
    b,t=self.indicator(i);self.assertEqual(self.run_eval(b=b,t=t)['state'],'OBSERVE_ONLY')
  b,t=self.indicator();b['definition']['target']['snapshot']['calculation_version']=99;self.rehash(b);r=self.run_eval(b=b,t=t);self.assertIn('UNSUPPORTED_FORMULA_VERSION',r['reasons'])
  b,t=self.indicator();c=copy.deepcopy(self.context);c['rows']=c['rows'][-3:];c['data_proof']=capture(c['rows'],c['market'],c['quality']).view();self.assertIn('INSUFFICIENT_WARMUP',self.run_eval(b=b,t=t,c=c)['reasons'])
 def test_service_reads_current_heads_without_writes(self):
  hub=SimpleNamespace(binding_context=lambda *a:copy.deepcopy(self.context));before=self.db.read_bytes();r=inspect_binding(self.s,hub,'main','binding');self.assertEqual(r['state'],'EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY');self.assertEqual(before,self.db.read_bytes())
  d=DrawingService(self.db,'owner').show(self.drawing_id);DrawingService(self.db,'owner').update(self.drawing_id,'edit',1,{**d['geometry'],'label':'edit'});r=inspect_binding(self.s,hub,'main','binding');self.assertEqual(r['state'],'BLOCKED');self.assertIn('BINDING_STOPPED_OR_INVALID',r['reasons'])
 def test_hub_only_existing_subscribed_feed_detached_and_no_acquire(self):
  hub=MarketFeedHub(None);self.assertIsNone(hub.binding_context('BTCUSDT','15m'));state=FeedState('BTCUSDT','15m');state.rows=self.rows;state.market=self.market;state.quality=self.quality;state.generation=1;state._capture_evidence();feed=SimpleNamespace(state=state,references=1);hub.feeds[('BTCUSDT','15m')]=feed
  c=hub.binding_context('BTCUSDT','15m');c['rows'].clear();self.assertEqual(len(state.rows),60);feed.references=0;self.assertIsNone(hub.binding_context('BTCUSDT','15m'));self.assertEqual(len(hub.feeds),1)
 def test_http_readonly_endpoint_ignores_no_client_proof_and_no_binding_changes(self):
  from fastapi.testclient import TestClient
  from agentrader.api.app import create_app
  from agentrader.application.settings import WebSettings
  hub=SimpleNamespace(binding_context=lambda *a:None,close=lambda:None)
  settings=WebSettings(application_database=self.db,execution_database=Path(self.tmp.name)/'exec.db',owner='owner')
  with TestClient(create_app(settings,hub=hub),base_url='http://127.0.0.1') as client:
   p='/api/workspaces/main/bindings/binding/eligibility';r=client.get(p);self.assertEqual(r.status_code,200);self.assertEqual(r.json()['state'],'BLOCKED');self.assertEqual(client.post(p,json=self.context).status_code,405);self.assertEqual(client.get('/api/workspaces/main/bindings/binding').json()['state'],'DISABLED');self.assertEqual(client.get('/api/workspaces/other/bindings/binding/eligibility').status_code,404)

 def test_every_supported_drawing_query_has_deterministic_suitability_class(self):
  from test_chart_bindings import geometry,GRID
  for kind in ('horizontal','trend','horizontal_ray','ray','extended_line','zone','fibonacci','fibonacci_extension','parallel_channel','long_plan','short_plan','ruler'):
   g=geometry(kind)
   for a in g['anchors']:a['time']=self.rows[GRID.index(a['time'])]['time']
   drawing=DrawingService(self.db,'owner').create('main','draw-'+kind,g)
   entry=self.evidence['targets']['drawing:'+kind]
   for i,q in enumerate(entry['queries']):
    with self.subTest(kind=kind,query=q):
     rule=dict(schema='chart-rule-definition/1',kind='touch' if q['output_type']=='PRICE' else 'observe',direction='ANY',tolerance='0',closed_candle=True,rearm_policy='EXPLICIT')
     b=self.s.save_binding('main',kind+str(i),'save-'+kind+str(i),0,dict(type='drawing',object_id=drawing['drawing_id'],revision=1),'BTCUSDT','15m','LINEAR',[r['time'] for r in self.rows],None,dict(operation=q['operation'],output=q['output'],ratio='1' if 'fibonacci' in kind else None),rule)
     r=self.run_eval(b=b,t={**b['definition']['target'],'deleted':False});self.assertEqual(r['state'],'EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY' if q['output_type']=='PRICE' else 'OBSERVE_ONLY',r)
 def test_vwap_session_and_anchor_require_real_available_output(self):
  b,t=self.indicator(7);r=self.run_eval(b=b,t=t);self.assertEqual(r['state'],'OBSERVE_ONLY',r)
  c=copy.deepcopy(self.context)
  for row in c['rows']:row.update(volume=0,quote_volume=0);row['exact'].update(volume='0',quote_volume='0')
  c['data_proof']=capture(c['rows'],c['market'],c['quality']).view();r=self.run_eval(b=b,t=t,c=c);self.assertIn('DISPLAY_OUTPUT_UNAVAILABLE_OR_SHIFTED',r['reasons'])
 def test_current_grid_outside_anchors_and_event_outside_snapshot_block(self):
  from test_chart_bindings import geometry
  g=geometry('trend');g['anchors']=[dict(time=self.rows[2]['time'],price='100'),dict(time=self.rows[6]['time'],price='110')];d=DrawingService(self.db,'owner').create('main','trend',g)
  b=self.s.save_binding('main','trend','trendbind',0,dict(type='drawing',object_id=d['drawing_id'],revision=1),'BTCUSDT','15m','LINEAR',[r['time'] for r in self.rows],None,dict(operation='priceAt',output='value',ratio=None),self.b['definition']['rule'])
  c=copy.deepcopy(self.context);c['rows']=c['rows'][-10:];c['data_proof']=capture(c['rows'],c['market'],c['quality']).view();r=self.run_eval(b=b,t={**b['definition']['target'],'deleted':False},c=c);self.assertIn('TARGET_OUTSIDE_VERIFIED_GRID',r['reasons'])
  c=copy.deepcopy(self.context);c['timing']['upstream_event_time']+=9000000;self.assertIn('EVENT_GRID_MISMATCH',self.run_eval(c=c)['reasons'])
 def test_reconnecting_server_and_missing_target_or_catalog_never_eligible(self):
  c=copy.deepcopy(self.context);c['transport_state']='RECONNECTING';self.assertIn('SERVER_TRANSPORT_NOT_LIVE',self.run_eval(c=c)['reasons']);self.assertEqual(self.run_eval(t={})['state'],'BLOCKED');self.assertEqual(self.run_eval(e={'state':'BLOCKED'})['state'],'BLOCKED')
