import copy,json,os,subprocess,sys,threading,tempfile,unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from agentrader.local_chart_events import LocalChartEvents,LocalEventError,closed_candidate
from agentrader.chart_bindings import BindingService
from agentrader.chart_evidence import snapshot
from agentrader.chart_clock import POLICY
from agentrader.drawings.service import DrawingService
from agentrader.migrations import connect,migrate
from test_chart_evidence import fixture,capture

def setup_store(db):
 migrate(db);b=BindingService(db,'owner');rows,market,quality=fixture(60);grid=[r['time'] for r in rows]
 # Previous closed candle closes below the touch band; current closed bar spans it.
 rows[-3].update(close=95);rows[-3]['exact']['close']='95'
 d=DrawingService(db,'owner').create('main','drawing',dict(kind='horizontal',symbol='BTCUSDT',price_source='LAST_PRICE',label='P6',anchors=[dict(time=grid[2],price='100')]))
 value=b.save_binding('main','binding','create',0,dict(type='drawing',object_id=d['drawing_id'],revision=1),'BTCUSDT','15m','LINEAR',grid,None,dict(operation='priceAt',output='value',ratio=None),dict(schema='chart-rule-definition/1',kind='touch',direction='ANY',tolerance='0',closed_candle=True,rearm_policy='EXPLICIT'))
 c=dict(transport_state='LIVE',identity=value['definition']['market'],rows=rows,market=market,quality=quality,stream_epoch='a'*32,generation=1,data_revision=1,data_proof=capture(rows,market,quality).view(),timing=dict(schema='chart-time-proof/1',policy=dict(POLICY),state='FRESH',reason=None,data_age_ms=1,upstream_age_upper_ms=2,uncertainty_ms=1,upstream_event_time=rows[-1]['time']*1000+3000))
 return d,value,c

class LocalEventTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.db=Path(self.tmp.name)/'app.db';self.d,self.b,self.c=setup_store(self.db);self.clock=[10.];self.engine=LocalChartEvents(self.db,'owner',monotonic=lambda:self.clock[0],wall=lambda:self.clock[0]);self.ns='replay:test'
 def prepared(self,namespace=None,context=None):return self.engine.prepare('main','binding',namespace or self.ns,self.c if context is None else context)
 def counts(self):
  with closing(connect(self.db)) as db:return {t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('app_chart_local_events','app_chart_local_intents','app_chart_local_phases','app_chart_fake_receipts')}
 def test_atomic_event_intent_phase_and_frozen_evidence(self):
  p=self.prepared();self.c['rows'].clear();r=self.engine.commit(p);self.assertTrue(r['created']);self.assertEqual(r['phase'],'TOUCH_LATCHED');self.assertEqual(list(self.counts().values()),[1,1,1,0]);row=self.engine.list_events('main',self.ns)['events'][0];self.assertEqual(row['intent_state'],'PENDING_FAKE');self.assertEqual(row['event']['level']['numerator'],'100');self.assertFalse(row['event']['order_authority'])
 def test_semantic_dedup_survives_restart_epoch_and_data_revision(self):
  a=self.engine.commit(self.prepared());c=copy.deepcopy(self.c);c.update(stream_epoch='b'*32,generation=2,data_revision=99);c['data_proof']=snapshot(c['rows'],c['market'],c['quality'],symbol='BTCUSDT',interval='15m',epoch=c['stream_epoch'],generation=2,revision=99).view();e=LocalChartEvents(self.db,'owner');r=e.commit(e.prepare('main','binding',self.ns,c));self.assertEqual(r['state'],'DUPLICATE');self.assertEqual(a['event_id'],r['event_id']);self.assertEqual(list(self.counts().values()),[1,1,1,0])
 def test_two_concurrent_recorders_and_dispatchers_have_one_durable_pair(self):
  p=self.prepared();barrier=threading.Barrier(2)
  def record(_):barrier.wait();return self.engine.commit(p)
  with ThreadPoolExecutor(2) as pool:r=list(pool.map(record,range(2)))
  self.assertEqual(sorted(x['state'] for x in r),['DUPLICATE','RECORDED_LOCAL'])
  barrier=threading.Barrier(2)
  def deliver(_):barrier.wait();return self.engine.deliver_one('main',self.ns)
  with ThreadPoolExecutor(2) as pool:r=list(pool.map(deliver,range(2)))
  self.assertEqual(sorted(x['state'] for x in r),['DELIVERED_FAKE','EMPTY']);self.assertEqual(list(self.counts().values()),[1,1,1,1])
 def test_precommit_failure_rolls_back_all_and_retry_records_once(self):
  for stage in ('after_event_insert','before_event_commit'):
   def fault(value):
    if value==stage:raise RuntimeError('crash')
   with self.assertRaises(RuntimeError):self.engine.commit(self.prepared(),_fault=fault)
   self.assertEqual(list(self.counts().values()),[0,0,0,0])
  self.assertTrue(self.engine.commit(self.prepared())['created'])
 def test_postcommit_ack_loss_is_dedup_not_lost_event(self):
  def fault(stage):
   if stage=='after_event_commit':raise RuntimeError('ack lost')
  with self.assertRaises(RuntimeError):self.engine.commit(self.prepared(),_fault=fault)
  self.assertEqual(self.engine.commit(self.prepared())['state'],'DUPLICATE');self.assertEqual(list(self.counts().values()),[1,1,1,0])
 def test_edit_between_prepare_and_commit_fails_head_recheck(self):
  p=self.prepared();DrawingService(self.db,'owner').update(self.d['drawing_id'],'edit',1,{**self.d['geometry'],'label':'changed'})
  with self.assertRaisesRegex(LocalEventError,'REVISION_CHANGED'):self.engine.commit(p)
  self.assertEqual(list(self.counts().values()),[0,0,0,0])
 def test_queued_revision_change_cancels_before_fake_send(self):
  self.engine.commit(self.prepared());DrawingService(self.db,'owner').update(self.d['drawing_id'],'edit',1,{**self.d['geometry'],'label':'changed'});r=self.engine.deliver_one('main',self.ns);self.assertEqual(r['state'],'CANCELED_SUPERSEDED');self.assertEqual(self.counts()['app_chart_fake_receipts'],0)
 def test_revision_change_after_claim_also_cancels_before_receipt(self):
  self.engine.commit(self.prepared())
  def fault(stage):
   if stage=='after_delivery_claim':DrawingService(self.db,'owner').update(self.d['drawing_id'],'edit',1,{**self.d['geometry'],'label':'changed'})
  self.assertEqual(self.engine.deliver_one('main',self.ns,_fault=fault)['state'],'CANCELED_SUPERSEDED');self.assertEqual(self.counts()['app_chart_fake_receipts'],0)
 def test_unknown_delivery_is_not_automatically_retried_or_called_exactly_once(self):
  self.engine.commit(self.prepared())
  def fault(stage):
   if stage=='after_fake_send':raise RuntimeError('ack lost')
  self.assertEqual(self.engine.deliver_one('main',self.ns,_fault=fault)['state'],'DELIVERY_UNKNOWN');self.assertEqual(self.engine.deliver_one('main',self.ns)['state'],'EMPTY');self.assertEqual(self.counts()['app_chart_fake_receipts'],1)
 def test_restart_claim_recovery_keeps_unknown_without_resending(self):
  self.engine.commit(self.prepared())
  def fault(stage):
   if stage=='after_delivery_claim':raise RuntimeError('process died')
  with self.assertRaises(RuntimeError):self.engine.deliver_one('main',self.ns,_fault=fault)
  e=LocalChartEvents(self.db,'owner');self.assertEqual(e.recover_unknown('main',self.ns)['count'],1);self.assertEqual(e.deliver_one('main',self.ns)['state'],'EMPTY');self.assertEqual(self.counts()['app_chart_fake_receipts'],0)
 def test_namespace_isolation_same_domain_identity_separate_storage(self):
  a=self.engine.commit(self.prepared());b=self.engine.commit(self.prepared('replay:other'));self.assertEqual(a['domain_event_id'],b['domain_event_id']);self.assertNotEqual(a['event_id'],b['event_id']);self.assertEqual(len(self.engine.list_events('main',self.ns)['events']),1)
  for ns in ('live','live:test','replay:','replay:../x','replay:x y'):
   with self.assertRaises(LocalEventError):self.prepared(ns)
  self.assertEqual(LocalChartEvents(self.db,'other').list_events('main',self.ns)['events'],[])
 def test_latched_phase_survives_new_bar_and_requires_explicit_rebind(self):
  self.engine.commit(self.prepared());c=copy.deepcopy(self.c)
  for r in c['rows']:r['time']+=900;r['close_time']+=900000
  c['data_proof']=capture(c['rows'],c['market'],c['quality']).view();c['timing']['upstream_event_time']+=900000
  self.assertEqual(self.engine.commit(self.prepared(context=c))['state'],'LATCHED');self.assertEqual(self.counts()['app_chart_local_events'],1)
 def test_elapsed_lock_wait_and_wall_jump_fail_closed(self):
  p=self.prepared();self.clock[0]+=11;self.assertEqual(self.engine.commit(p)['state'],'BLOCKED');self.assertEqual(self.counts()['app_chart_local_events'],0)
  e=LocalChartEvents(self.db,'owner',monotonic=lambda:0,wall=lambda:100);p=e.prepare('main','binding',self.ns,self.c);e.wall=lambda:101
  with self.assertRaisesRegex(LocalEventError,'CLOCK_UNTRUSTED'):e.commit(p)
 def test_no_event_or_missing_proof_never_writes(self):
  c=copy.deepcopy(self.c);c['rows'][-2].update(low=101);c['rows'][-2]['exact']['low']='101';c['rows'][-2]['open']=102;c['rows'][-2]['exact']['open']='102';c['data_proof']=capture(c['rows'],c['market'],c['quality']).view();self.assertEqual(self.engine.commit(self.prepared(context=c))['state'],'NO_EVENT')
  c=copy.deepcopy(self.c);c.pop('timing');self.assertEqual(self.engine.commit(self.prepared(context=c))['state'],'BLOCKED');self.assertEqual(self.counts()['app_chart_local_events'],0)
 def test_actual_process_crash_before_and_after_commit(self):
  for stage,expected in [('before_event_commit',0),('after_event_commit',1)]:
   with self.subTest(stage=stage),tempfile.TemporaryDirectory() as folder:
    db=Path(folder)/'crash.db';d,b,c=setup_store(db);path=Path(folder)/'context.json';path.write_text(json.dumps(c),encoding='utf-8')
    script="import json,os,sys;from agentrader.local_chart_events import LocalChartEvents;e=LocalChartEvents(sys.argv[1],'owner');p=e.prepare('main','binding','replay:crash',json.load(open(sys.argv[2])));e.commit(p,_fault=lambda s:os._exit(73) if s==sys.argv[3] else None)"
    p=subprocess.run([sys.executable,'-c',script,str(db),str(path),stage],capture_output=True,timeout=15);self.assertEqual(p.returncode,73,p.stderr)
    with closing(connect(db)) as conn:
     for table in ('app_chart_local_events','app_chart_local_intents','app_chart_local_phases'):self.assertEqual(conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],expected)
    e=LocalChartEvents(db,'owner');self.assertEqual(e.commit(e.prepare('main','binding','replay:crash',c))['state'],'DUPLICATE' if expected else 'RECORDED_LOCAL')

 def test_independent_bindings_and_explicit_rebind_have_distinct_events(self):
  self.engine.commit(self.prepared());b=BindingService(self.db,'owner');base=self.b['definition'];other=b.save_binding('main','other','other',0,{k:base['target'][k] for k in ('type','object_id','revision')},'BTCUSDT','15m','LINEAR',base['grid']['times'],None,base['query'],base['rule']);self.assertTrue(self.engine.commit(self.engine.prepare('main','other',self.ns,self.c))['created'])
  revised=DrawingService(self.db,'owner').update(self.d['drawing_id'],'rename',1,{**self.d['geometry'],'label':'new'});current=b.show('main','binding');b.save_binding('main','binding','rebind',current['revision'],dict(type='drawing',object_id=self.d['drawing_id'],revision=revised['revision']),'BTCUSDT','15m','LINEAR',base['grid']['times'],None,base['query'],base['rule']);self.assertTrue(self.engine.commit(self.prepared())['created']);self.assertEqual(self.counts()['app_chart_local_events'],3)
 def test_real_process_crash_after_claim_and_fake_send_recovers_unknown(self):
  for stage,receipts in [('after_delivery_claim',0),('after_fake_send',1)]:
   with self.subTest(stage=stage),tempfile.TemporaryDirectory() as folder:
    db=Path(folder)/'delivery.db';d,b,c=setup_store(db);e=LocalChartEvents(db,'owner');e.commit(e.prepare('main','binding','replay:crash',c))
    script="import os,sys;from agentrader.local_chart_events import LocalChartEvents;e=LocalChartEvents(sys.argv[1],'owner');e.deliver_one('main','replay:crash',_fault=lambda s:os._exit(74) if s==sys.argv[2] else None)"
    p=subprocess.run([sys.executable,'-c',script,str(db),stage],capture_output=True,timeout=15);self.assertEqual(p.returncode,74,p.stderr);self.assertEqual(e.recover_unknown('main','replay:crash')['count'],1);self.assertEqual(e.list_events('main','replay:crash')['events'][0]['intent_state'],'DELIVERY_UNKNOWN');self.assertEqual(e.deliver_one('main','replay:crash')['state'],'EMPTY')
    with closing(connect(db)) as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM app_chart_fake_receipts').fetchone()[0],receipts)
 def test_http_history_is_readonly_and_rejects_live_namespace(self):
  from fastapi.testclient import TestClient
  from agentrader.api.app import create_app
  from agentrader.application.settings import WebSettings
  self.engine.commit(self.prepared());settings=WebSettings(application_database=self.db,execution_database=Path(self.tmp.name)/'execution.db',owner='owner')
  with TestClient(create_app(settings),base_url='http://127.0.0.1') as client:
   path='/api/workspaces/main/local-events';r=client.get(path+'?namespace='+self.ns);self.assertEqual(r.status_code,200);self.assertEqual(len(r.json()['events']),1);self.assertEqual(client.post(path,json={'dispatch':True}).status_code,405);self.assertEqual(client.get(path+'?namespace=live').status_code,422);self.assertEqual(client.get('/api/workspaces/other/local-events?namespace='+self.ns).json()['events'],[])
 def test_rule_profile_uses_exact_closed_touch_approach_cross_and_direction(self):
  b=copy.deepcopy(self.b);c=copy.deepcopy(self.c);self.assertEqual(closed_candidate(b,c)['kind'],'TOUCH');b['definition']['rule']['direction']='BELOW';self.assertIsNone(closed_candidate(b,c))
  b['definition']['rule'].update(kind='approach',direction='ABOVE',tolerance='2');r=c['rows'][-2];r.update(open=98,close=99,low=97,high=99.5);r['exact'].update(open='98',close='99',low='97',high='99.5');self.assertEqual(closed_candidate(b,c)['kind'],'APPROACH');r.update(high=100);r['exact']['high']='100';self.assertIsNone(closed_candidate(b,c))
  r.update(open=101,low=101,close=101,high=102);r['exact'].update(open='101',low='101',close='101',high='102');self.assertIsNone(closed_candidate(b,c))
  b['definition']['rule'].update(kind='close_cross',tolerance='0');r.update(close=101,high=102);r['exact'].update(close='101',high='102');self.assertEqual(closed_candidate(b,c)['kind'],'CLOSE_CROSS');b['definition']['rule']['direction']='BELOW';self.assertIsNone(closed_candidate(b,c))
