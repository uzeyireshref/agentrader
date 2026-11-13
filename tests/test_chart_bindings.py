import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from agentrader.chart_bindings import BindingService,BindingError,BindingBlocked,binding_hash
from agentrader.binding_catalog import catalog,definitions
from agentrader.drawings.service import DrawingService,DrawingError,DrawingConflict,DrawingNotFound,management
from agentrader.indicator_config import IndicatorService,defaults_v4
from agentrader.chart_profiles import ProfileService,default_view
from agentrader.migrations import migrate,connect
GRID=[1800000000+i*900 for i in range(12)]
def geometry(kind='horizontal'):
 anchors=[dict(time=GRID[2],price='100')]
 if kind in ('trend','ray','extended_line','zone','fibonacci','fibonacci_extension','ruler','parallel_channel'):anchors.append(dict(time=GRID[6],price='110'))
 if kind=='parallel_channel':anchors.append(dict(time=GRID[4],price='115'))
 g=dict(kind=kind,symbol='BTCUSDT',price_source='LAST_PRICE',label=kind,anchors=anchors)
 if kind in ('ray','extended_line','horizontal_ray'):g['schema']='chart-line/1'
 if kind=='parallel_channel':g['schema']='chart-channel/1'
 if kind=='ruler':g['schema']='chart-ruler/1'
 if kind in ('fibonacci','fibonacci_extension'):g.update(schema='chart-fibonacci/1',time_scope='unbounded',levels=['0','1','1.5'])
 if kind in ('long_plan','short_plan'):
  g.update(schema='chart-position/1',params=dict(risk_budget=None,fee_bps='4',slippage_bps='2'),anchors=[dict(time=t,price=p) for t,p in zip([GRID[2],GRID[6],GRID[6]],['110','100','120'] if kind=='long_plan' else ['110','120','100'])])
 if kind=='text':g.update(schema='chart-annotation/1',text='Not')
 return g
RULE=dict(schema='chart-rule-definition/1',kind='observe',direction='ANY',tolerance='0',closed_candle=True,rearm_policy='EXPLICIT')
class BindingTests(unittest.TestCase):
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup);self.db=Path(self.folder.name)/'app.db';migrate(self.db);self.s=DrawingService(self.db,'owner');self.b=BindingService(self.db,'owner');self.i=IndicatorService(self.db,'owner');self.n=0
 def drawing(self,kind='horizontal'):
  self.n+=1;return self.s.create('main','drawing-'+str(self.n),geometry(kind))
 def save(self,d,bid='bind',expected=0,**kw):
  payload=dict(target=dict(type='drawing',object_id=d['drawing_id'],revision=d['revision']),symbol='BTCUSDT',interval='15m',scale='LINEAR',grid_times=GRID,data_snapshot_hash=None,query=dict(operation='priceAt',output='value',ratio=None),rule=RULE);payload.update(kw)
  return self.b.save_binding('main',bid,'save-'+bid+'-'+str(expected),expected,**payload)
 def test_definition_disabled_owner_grid_hash_and_readonly_capabilities(self):
  d=self.drawing();b=self.save(d);self.assertEqual(b['state'],'DISABLED');self.assertEqual(b['definition_hash'],binding_hash(b['definition']));self.assertEqual(b['definition']['owner'],'owner');self.assertEqual(b['definition']['target']['revision'],1);self.assertEqual(b['definition']['grid']['times'],GRID);self.assertFalse(b['definition']['bot_capabilities']['write_target']);self.assertFalse(b['definition']['bot_capabilities']['order_authority']);self.assertFalse(b['live_eligible']);self.assertEqual(b['definition']['data_reference']['state'],'CLIENT_REFERENCE_NOT_ELIGIBILITY');self.assertTrue(self.save(d)['duplicate'])
 def test_edit_undo_and_explicit_rebind_never_reactivate_old_revision(self):
  d=self.drawing();b=self.save(d);g=copy.deepcopy(d['geometry']);g['anchors'][0]['price']='105';edited=self.s.update(d['drawing_id'],'edit',1,g);stopped=self.b.show('main','bind');self.assertEqual((stopped['state'],stopped['revision']),('STOPPED',2));undone=self.s.update(d['drawing_id'],'undo',edited['revision'],d['geometry']);self.assertEqual(self.b.show('main','bind')['revision'],2);rebound=self.save(undone,expected=2);self.assertEqual((rebound['revision'],rebound['state']),(3,'DISABLED'));self.assertNotEqual(rebound['definition_hash'],b['definition_hash']);self.assertEqual(self.b.show('main','bind',1)['definition_hash'],b['definition_hash'])
 def test_delete_restore_cached_ack_and_style_revision_stop_same_transaction(self):
  d=self.drawing();self.save(d);deleted=self.s.update(d['drawing_id'],'delete',1,deleted=True);self.assertEqual(self.b.show('main','bind')['reason'],'TARGET_DELETED');self.assertTrue(self.save(d)['duplicate']);self.assertEqual(self.b.show('main','bind')['state'],'STOPPED')
  with self.assertRaises(BindingBlocked):self.save(deleted,bid='new')
  restored=self.s.update(d['drawing_id'],'undo-delete',deleted['revision'],d['geometry']);self.save(restored,expected=2);self.s.operations('main','style',[dict(drawing_id=restored['drawing_id'],expected_revision=restored['revision'],geometry=restored['geometry'],management={**management(),'color':'#9b6ed6'},deleted=False)]);self.assertEqual(self.b.show('main','bind')['state'],'STOPPED')
 def test_failed_batch_rolls_back_both_drawing_and_binding_head(self):
  a=self.drawing();b=self.drawing();self.save(a);ops=[dict(drawing_id=d['drawing_id'],expected_revision=d['revision'],geometry=d['geometry'],management={**management(),'color':'#9b6ed6'},deleted=False) for d in [a,b]];ops[1]['expected_revision']=99
  with self.assertRaises(DrawingConflict):self.s.operations('main','bad-batch',ops)
  self.assertEqual(self.s.show(a['drawing_id'])['revision'],1);self.assertEqual(self.b.show('main','bind')['state'],'DISABLED')
 def test_indicator_own_revision_and_template_restore_invalidate_exact_changed_targets(self):
  target=dict(type='indicator',object_id='ema-fast',revision=0);q=dict(operation='valueAt',output='value',ratio=None);dummy=dict(drawing_id='unused',revision=0);self.save(dummy,target=target,query=q);items=defaults_v4();items[2]['period']=7;self.i.save('main','rsi-only',0,items,4);self.assertEqual(self.b.show('main','bind')['state'],'DISABLED');items=self.i.load('main',4)['indicators'];items[0]['period']=9;self.i.save('main','ema',1,items,4);self.assertEqual(self.b.show('main','bind')['state'],'STOPPED');self.save(dummy,expected=2,target={**target,'revision':1},query=q)
  p=ProfileService(self.db,'owner');body=dict(schema='chart-template/1',view=default_view(),drawing_defaults={},indicators=defaults_v4());p.save_template('main','template','template-save',0,'Varsayılan',body);p.restore('main','restore',template_id='template',template_revision=1,expected_profile_revision=0,expected_indicator_revision=2,symbol='BTCUSDT',interval='15m',expected_drawings=[],apply_drawing_styles=False);self.assertEqual(self.b.show('main','bind')['state'],'STOPPED')
 def test_owner_workspace_target_and_expected_revision_isolation(self):
  d=self.drawing();self.save(d)
  with self.assertRaises(DrawingNotFound):BindingService(self.db,'other').show('main','bind')
  with self.assertRaises(DrawingNotFound):self.b.show('other','bind')
  with self.assertRaises(DrawingConflict):self.save(d,expected=99)
  other=self.drawing()
  with self.assertRaises(BindingBlocked):self.save(other,expected=1)
 def test_bad_grid_scale_rule_annotation_and_missing_evidence_are_blocked(self):
  d=self.drawing()
  for options in [dict(grid_times=[]),dict(grid_times=GRID[:3]+GRID[4:]),dict(scale='LOG'),dict(data_snapshot_hash='trusted'),dict(rule={**RULE,'closed_candle':False}),dict(rule={**RULE,'order_authority':True}),dict(query=dict(operation='execute',output='value',ratio=None))]:
   with self.subTest(options=options),self.assertRaises(DrawingError):self.save(d,**options)
  with patch('agentrader.chart_bindings.catalog',return_value=dict(state='BLOCKED',reason='QUERY_EVIDENCE_STALE_OR_MISSING')):
   with self.assertRaises(BindingBlocked):self.save(d)
  with self.assertRaises(BindingBlocked):self.save(self.drawing('text'))
 def test_catalog_coverage_every_supported_target_has_query_and_parity_artifacts(self):
  evidence=catalog();self.assertEqual(evidence['state'],'VERIFIED_TRACEABILITY');self.assertEqual(len(evidence['targets']),20)
  for key,entry in evidence['targets'].items():
   self.assertTrue(entry['queries']);self.assertTrue(entry['artifacts']);self.assertTrue(entry['context_requirements'])
   for a in entry['artifacts']:self.assertRegex(a['sha256'],r'^[a-f0-9]{64}$')
  for kind in ['horizontal','trend','ray','extended_line','horizontal_ray','zone','fibonacci','fibonacci_extension','parallel_channel','long_plan','short_plan','ruler']:
   d=self.drawing(kind);entry=evidence['targets']['drawing:'+kind]
   for idx,q in enumerate(entry['queries']):self.save(d,bid=kind+'-'+str(idx),query=dict(operation=q['operation'],output=q['output'],ratio='1' if kind in ('fibonacci','fibonacci_extension') else None))
  for item in defaults_v4():
   if item['kind']=='ANCHORED_VWAP':continue
   for idx,q in enumerate(evidence['targets']['indicator:'+item['kind']]['queries']):self.save(dict(drawing_id='unused',revision=0),bid=item['indicator_id']+'-'+str(idx),target=dict(type='indicator',object_id=item['indicator_id'],revision=0),query=dict(operation=q['operation'],output=q['output'],ratio=None))
 def test_anchored_vwap_binding_requires_saved_symbol_anchor_and_observe_rule(self):
  items=defaults_v4();items[8]['params'].update(anchor_time=GRID[2],anchor_symbol='BTCUSDT');self.i.save('main','anchor',0,items,4);target=dict(type='indicator',object_id='anchored-vwap',revision=1);q=dict(operation='valueAt',output='value',ratio=None);self.save(dict(drawing_id='unused',revision=0),target=target,query=q)
  with self.assertRaises(BindingError):self.save(dict(drawing_id='unused',revision=0),bid='bad-rule',target=target,query=q,rule={**RULE,'kind':'touch'})
 def test_template_bulk_style_restore_latches_binding_and_does_not_reenable(self):
  d=self.drawing();self.save(d);p=ProfileService(self.db,'owner');body=dict(schema='chart-template/1',view=default_view(),indicators=defaults_v4(),drawing_defaults={'horizontal':dict(style=dict(color='#9b6ed6',line_width=3,line_style='dashed'),options={})});p.save_template('main','template','template',0,'Stil',body);args=dict(template_id='template',template_revision=1,expected_profile_revision=0,expected_indicator_revision=0,symbol='BTCUSDT',interval='15m',expected_drawings=[dict(drawing_id=d['drawing_id'],revision=1)],apply_drawing_styles=True);p.restore('main','restore-style',**args);self.assertEqual(self.b.show('main','bind')['state'],'STOPPED');args.update(expected_profile_revision=1,expected_indicator_revision=1,expected_drawings=[dict(drawing_id=d['drawing_id'],revision=2)]);p.restore('main','restore-again',**args);self.assertEqual(self.b.show('main','bind')['revision'],2)
 def test_http_unknown_activation_fields_and_restart_disabled_definition(self):
  from fastapi.testclient import TestClient
  from agentrader.api.app import create_app
  from agentrader.application.settings import WebSettings
  d=self.drawing();settings=WebSettings(self.db,Path(self.folder.name)/'exec.db',owner='owner',market_database=Path(self.folder.name)/'market.db');payload=dict(request_id='http-bind',expected_binding_revision=0,target=dict(type='drawing',object_id=d['drawing_id'],revision=1),symbol='BTCUSDT',interval='15m',scale='LINEAR',grid_times=GRID,data_snapshot_hash=None,query=dict(operation='priceAt',output='value',ratio=None),rule=RULE)
  with TestClient(create_app(settings),base_url='http://127.0.0.1') as c:
   url='/api/workspaces/main/bindings/http-binding';self.assertEqual(c.put(url,json={**payload,'state':'ACTIVE'}).status_code,422);r=c.put(url,json=payload);self.assertEqual(r.status_code,200);self.assertEqual(r.json()['state'],'DISABLED');self.assertFalse(c.get('/api/health').json()['trading_commands_enabled'])
  with TestClient(create_app(settings),base_url='http://127.0.0.1') as c:self.assertEqual(c.get('/api/workspaces/main/bindings/http-binding').json()['state'],'DISABLED')
