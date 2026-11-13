import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_chart_p7 import Harness,run_suite,execute
from agentrader.chart_replay import ReplayEngine,PROFILE,event_identity
from agentrader.binding_catalog import catalog
from agentrader.indicator_config import defaults_v4,IndicatorService
from agentrader.drawings.service import DrawingService

class ScenarioTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=run_suite()

def scenario_test(id):
 def test(self):
  r=next(x for x in self.report['cases'] if x['id']==id);self.assertTrue(r['passed'],{k:v for k,v in r.items() if k!='evidence'})
 return test
for i in range(1,37):setattr(ScenarioTests,'test_DR'+str(i).zfill(2),scenario_test('DR'+str(i).zfill(2)))

class ReplayAdditionalTests(unittest.TestCase):
 def setUp(self):self.h=Harness();self.addCleanup(self.h.close)
 def test_resume_after_restart_preserves_latch_and_requires_new_close(self):
  h=self.h;h.seed();h.process();h.engine=ReplayEngine(h.db,'fixture',monotonic=lambda:h.clock[0],wall=lambda:h.clock[1]);c=h.context(3);c['stream_epoch']='b'*32;h.proof(c);r=h.process(c,origin='SNAPSHOT',sequence=1);self.assertEqual(r['phase'],'TOUCH_LATCHED');self.assertTrue(h.engine.resume('main','binding',h.ns,c));r=h.process(c,sequence=2);self.assertEqual(r['reason'],'SEMANTIC_EVENT_ALREADY_RECORDED');self.assertEqual(h.count(),1)
 def test_new_epoch_heartbeat_cannot_bypass_resnapshot_barrier(self):
  h=self.h;h.seed();c=h.context(1);c['stream_epoch']='b'*32;h.proof(c);self.assertEqual(h.process(c,origin='HEARTBEAT')['reason'],'EXPLICIT_RESUME_REQUIRED');self.assertEqual(h.process(c)['outcome'],'BLOCKED');self.assertEqual(h.count(),0)
 def test_invalid_ohlc_and_timestamp_preserve_checkpoint_and_audit(self):
  h=self.h;h.seed();before=h.db.read_bytes()
  for mutation in (lambda c:c['rows'][-2].update(low=101),lambda c:c['rows'][-2].update(close=-1),lambda c:c['rows'][-2].update(time=c['rows'][-3]['time'])):
   c=h.context(1);mutation(c);r=h.process(c);self.assertEqual(r['reason'],'INVALID_PACKET');self.assertEqual(h.db.read_bytes(),before)
 def test_symmetrical_above_profile_and_no_lookahead(self):
  h=self.h;p={**PROFILE,'direction':'FROM_ABOVE'};h.seed(profile=p);r=h.process(h.context(1,close='100.9',high='101.1',low='100.8',previous='102'),profile=p);self.assertEqual(r['event'],'APPROACH');r=h.process(h.context(2,close='100.2',high='100.5',low='100',previous='100.9'),profile=p);self.assertEqual(r['event'],'TOUCH');self.assertEqual(h.count(),2)
  c=h.context(3);c['rows'][-1]['closed']=True;h.proof(c);r=h.process(c,profile=p);self.assertEqual(r['outcome'],'BLOCKED')
 def test_same_semantic_bar_with_changed_payload_is_integrity_error(self):
  h=self.h;h.seed();h.process();before=h.db.read_bytes();r=h.process(h.context(1,close='99.7',high='100',low='99.4'));self.assertEqual(r['reason'],'SEMANTIC_PAYLOAD_CONFLICT');self.assertEqual(h.db.read_bytes(),before);self.assertEqual(h.count(),1)
 def test_retry_budget_and_ttl_use_fake_clock_and_no_receipt_on_failure(self):
  h=self.h;r=h.process();eid=r['event_id'];first=h.engine.simulate_delivery('main',h.ns,eid,'429',retry_after=5);same=h.engine.simulate_delivery('main',h.ns,eid,'429');self.assertEqual(same['attempts'],first['attempts']);h.clock[0]+=61;h.clock[1]+=61;self.assertEqual(h.engine.simulate_delivery('main',h.ns,eid)['state'],'EXPIRED');self.assertEqual(h.count('app_chart_fake_receipts'),0)
 def test_e3_golden_identity_and_invalid_integer_strings(self):
  p=json.loads((ROOT/'docs/chart/contracts/chart-dry-run-v1.json').read_text(encoding='utf-8'))['synthetic_golden_values'];self.assertEqual(event_identity(p['event_components']),p['event_id'])
  for value in ('07','0','-1','1.0'):
   with self.assertRaises(ValueError):event_identity({**p['event_components'],'drawing_revision':value})
 def test_registry_price_query_parity_and_observe_only_outputs(self):
  from test_chart_bindings import geometry
  h=self.h;ctx=h.context(1,close='99.8',high='200',low='50');grid=[r['time'] for r in ctx['rows']];count=0;coverage=[]
  for key,entry in catalog()['targets'].items():
   typ,kind=key.split(':')
   if typ=='drawing':
    g=geometry(kind)
    for i,a in enumerate(g['anchors']):a['time']=grid[-4] if i==0 else grid[-2] if i==1 else grid[-2] if kind in ('long_plan','short_plan') else grid[-3]
    d=DrawingService(h.db,'fixture').create('main','tool-'+kind,g);target=dict(type=typ,object_id=d['drawing_id'],revision=1)
   else:
    config=next(c for c in defaults_v4() if c['kind']==kind)
    if kind=='ANCHORED_VWAP':
     configs=IndicatorService(h.db,'fixture').load('main',4)['indicators'];configs[-1]['params'].update(anchor_time=grid[0],anchor_symbol='BTCUSDT');config=IndicatorService(h.db,'fixture').save('main','anchor',0,configs,4)['indicators'][-1]
    target=dict(type=typ,object_id=config['indicator_id'],revision=config['revision'])
   for i,q in enumerate(entry['queries']):
    bid='coverage-'+kind+'-'+str(i);rule={**h.b['definition']['rule'],'kind':'touch' if q['output_type']=='PRICE' else 'observe','tolerance':'0.1' if q['output_type']=='PRICE' else '0'};h.s.save_binding('main',bid,bid,0,target,'BTCUSDT','15m','LINEAR',grid,None,dict(operation=q['operation'],output=q['output'],ratio='1' if 'fibonacci' in kind else None),rule);r=h.process(ctx,binding_id=bid,namespace='replay:coverage')
    if q['output_type']=='PRICE':self.assertEqual(r['outcome'],'EVENT',(kind,q,r))
    else:self.assertFalse(r['created'],(kind,q,r))
    coverage.append(dict(target=key,operation=q['operation'],output=q['output'],output_type=q['output_type'],outcome=r['outcome'],created=r['created'],passed=True));count+=1
  self.assertGreater(count,40)
  (ROOT/'reports/chart-p7-tool-coverage-20261113.json').write_text(json.dumps(dict(passed=True,target_kinds=len(catalog()['targets']),query_cases=count,checks=coverage),indent=2)+'\n',encoding='utf-8')

class ReplayReportTests(unittest.TestCase):
 def test_packaged_result_source_hashes_and_no_auto_integration(self):
  from agentrader.replay_report import replay_summary
  r=replay_summary();self.assertEqual(r['state'],'VERIFIED_ISOLATED');self.assertEqual(r['passed_count'],36);self.assertFalse(r['runtime_connected']);self.assertFalse(r['order_authority'])
 def test_missing_stale_or_inconsistent_report_fails_closed(self):
  import tempfile
  from unittest.mock import patch
  import agentrader.replay_report as module
  original=json.loads(module.REPORT.read_text(encoding='utf-8'))
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'report.json'
   with patch.object(module,'REPORT',path):
    self.assertEqual(module.replay_summary()['state'],'BLOCKED')
    for mutation in (lambda r:r['cases'][0]['observed'].update(reason='WRONG'),lambda r:r['source_hashes'].update({'missing.py':'0'*64}),lambda r:r['side_effects'].update(order_requests=1)):
     r=copy.deepcopy(original);mutation(r);path.write_text(json.dumps(r),encoding='utf-8');self.assertEqual(module.replay_summary()['state'],'BLOCKED')
 def test_http_report_is_readonly(self):
  import tempfile
  from fastapi.testclient import TestClient
  from agentrader.api.app import create_app
  from agentrader.application.settings import WebSettings
  with tempfile.TemporaryDirectory() as folder:
   settings=WebSettings(application_database=Path(folder)/'app.db',execution_database=Path(folder)/'execution.db')
   with TestClient(create_app(settings),base_url='http://127.0.0.1') as client:
    r=client.get('/api/replay-validation');self.assertEqual(r.status_code,200);self.assertEqual(r.json()['passed_count'],36);self.assertEqual(client.post('/api/replay-validation',json={'activate':True}).status_code,405);self.assertFalse((Path(folder)/'execution.db').exists())
