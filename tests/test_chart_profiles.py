import copy,tempfile,unittest
from pathlib import Path
from agentrader.chart_profiles import ProfileService,default_view,valid_defaults,profile_body,template_body
from agentrader.indicator_config import IndicatorService,defaults_v4
from agentrader.drawings.service import DrawingService,DrawingError,DrawingConflict,management
from agentrader.migrations import migrate,connect
class ProfileTests(unittest.TestCase):
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup);self.db=Path(self.folder.name)/'app.db';migrate(self.db);self.p=ProfileService(self.db,'owner');self.i=IndicatorService(self.db,'owner');self.d=DrawingService(self.db,'owner')
 def body(self):return dict(schema='chart-template/1',view=default_view(),indicators=defaults_v4(),drawing_defaults={'horizontal':dict(style=dict(color='#9b6ed6',line_width=3,line_style='dashed'),options={})})
 def drawing(self,request='line',symbol='BTCUSDT'):
  return self.d.create('main',request,dict(kind='horizontal',symbol=symbol,price_source='LAST_PRICE',label='Seviye',anchors=[dict(time=1800000000,price='100')]))
 def restore(self,**kwargs):
  payload=dict(template_id='template',template_revision=1,expected_profile_revision=0,expected_indicator_revision=0,symbol='BTCUSDT',interval='15m',expected_drawings=[],apply_drawing_styles=False);payload.update(kwargs);return self.p.restore('main','restore',**payload)
 def test_legacy_defaults_profile_version_and_idempotency(self):
  self.assertEqual(self.p.profile('main')['revision'],0);self.assertEqual(self.p.profile('main')['body']['drawing_defaults'],{});body=dict(schema='chart-profile/1',view=default_view(),drawing_defaults={});saved=self.p.save_profile('main','save',0,body);self.assertEqual(saved['revision'],1);self.assertTrue(self.p.save_profile('main','save',0,body)['duplicate'])
  with self.assertRaises(DrawingConflict):self.p.save_profile('main','stale',0,body)
  self.assertEqual(ProfileService(self.db,'owner').profile('main'),{k:v for k,v in saved.items() if k!='duplicate'});self.assertEqual(ProfileService(self.db,'other').profile('main')['revision'],0)
 def test_versioned_template_history_sanitizes_anchors_and_never_transfers_authority(self):
  body=self.body();body['indicators'][8]['params'].update(anchor_time=1800000000,anchor_symbol='BTCUSDT');one=self.p.save_template('main','template','save-1',0,'Bir',body);self.assertEqual(one['body']['indicators'][8]['params']['anchor_time'],0);body['view']['theme']='light';two=self.p.save_template('main','template','save-2',1,'İki',body);self.assertEqual(two['revision'],2);self.assertEqual(self.p.template('main','template',1)['body']['view']['theme'],'dark');self.assertEqual(self.p.templates('main')['templates'][0]['revision'],2)
  with self.assertRaises(DrawingConflict):self.p.save_template('main','template','stale',1,'Eski',body)
  with self.assertRaises(DrawingError):ProfileService(self.db,'other').template('main','template')
  with self.assertRaises(DrawingError):self.p.template('main','template',10**100)
 def test_atomic_restore_updates_settings_and_unlocked_styles_preserving_geometry_and_anchor(self):
  a=self.drawing();b=self.drawing('locked');locked=self.d.operations('main','lock',[dict(drawing_id=b['drawing_id'],expected_revision=1,geometry=b['geometry'],management={**management(), 'locked':True},deleted=False)])['drawings'][0];original=defaults_v4();original[8]['params'].update(anchor_time=1800000000,anchor_symbol='BTCUSDT');self.i.save('main','original',0,original,4);body=self.body();body['indicators'][0].update(enabled=True,period=9);self.p.save_template('main','template','save',0,'Yerleşim',body)
  result=self.restore(expected_indicator_revision=1,expected_drawings=[dict(drawing_id=a['drawing_id'],revision=1),dict(drawing_id=b['drawing_id'],revision=2)],apply_drawing_styles=True);self.assertEqual(result['changed_drawings'],[a['drawing_id']]);self.assertEqual(result['skipped_drawings'],[b['drawing_id']]);self.assertEqual(self.d.show(a['drawing_id'])['geometry'],a['geometry']);self.assertEqual(self.d.show(a['drawing_id'])['management']['color'],'#9b6ed6');self.assertEqual(self.d.show(b['drawing_id']),locked);self.assertEqual(result['indicators']['indicators'][8]['params']['anchor_time'],1800000000);self.assertFalse(result['order_authority'])
  self.assertTrue(self.restore(expected_indicator_revision=1,expected_drawings=[dict(drawing_id=a['drawing_id'],revision=1),dict(drawing_id=b['drawing_id'],revision=2)],apply_drawing_styles=True)['duplicate'])
 def test_conflict_rolls_back_profile_indicators_and_every_drawing(self):
  d=self.drawing();self.p.save_template('main','template','save',0,'Yerleşim',self.body())
  with self.assertRaises(DrawingConflict):self.restore(expected_drawings=[dict(drawing_id=d['drawing_id'],revision=99)],apply_drawing_styles=True)
  self.assertEqual(self.p.profile('main')['revision'],0);self.assertEqual(self.i.load('main',4)['revision'],0);self.assertEqual(self.d.show(d['drawing_id'])['revision'],1)
  with self.assertRaises(DrawingConflict):self.restore(expected_drawings=[],apply_drawing_styles=False)
 def test_style_scope_respects_symbol_visibility_interval_and_lock(self):
  a=self.drawing();other=self.drawing('other','ETHUSDT');hidden=self.d.operations('main','hide',[dict(drawing_id=a['drawing_id'],expected_revision=1,geometry=a['geometry'],management={**management(),'intervals':['1h']},deleted=False)])['drawings'][0];self.p.save_template('main','template','save',0,'Yerleşim',self.body());r=self.restore(expected_drawings=[dict(drawing_id=a['drawing_id'],revision=2)],apply_drawing_styles=True);self.assertEqual(r['changed_drawings'],[]);self.assertEqual(r['skipped_drawings'],[a['drawing_id']]);self.assertEqual(self.d.show(other['drawing_id']),{k:v for k,v in other.items() if k!='duplicate'});self.assertEqual(self.d.show(a['drawing_id']),hidden)
 def test_validation_rejects_authority_unknown_geometry_and_unsafe_defaults(self):
  b=self.body();b['order_authority']=True
  with self.assertRaises(DrawingError):template_body(b)
  for c in [dict(horizontal=dict(style=dict(color='#9b6ed6',line_width=3,line_style='dashed',locked=True),options={})),dict(horizontal=dict(style=dict(color='#9b6ed6',line_width=3,line_style='dashed'),options={'anchors':[]}))]:
   with self.assertRaises(DrawingError):valid_defaults(c)
  b=self.body();b['view']['pane_weights']['price']=float('nan')
  with self.assertRaises(DrawingError):template_body(b)
  b=self.body();b['drawing_defaults']['fibonacci']=dict(style=b['drawing_defaults']['horizontal']['style'],options={'levels':['0','0.0']})
  with self.assertRaises(DrawingError):template_body(b)
 def test_tool_options_are_validated_but_existing_geometry_is_not_rewritten(self):
  style=self.body()['drawing_defaults']['horizontal']['style'];v=valid_defaults(dict(fibonacci=dict(style=style,options={'levels':['0.0','1.5']}),long_plan=dict(style=style,options={'params':{'risk_budget':'50','fee_bps':'4','slippage_bps':'2'}})));self.assertEqual(v['fibonacci']['options']['levels'],['0','1.5'])
 def test_http_profile_template_restore_and_old_workspace_compatibility(self):
  from fastapi.testclient import TestClient
  from agentrader.api.app import create_app
  from agentrader.application.settings import WebSettings
  with TestClient(create_app(WebSettings(self.db,Path(self.folder.name)/'exec.db',market_database=Path(self.folder.name)/'market.db')),base_url='http://127.0.0.1') as c:
   self.assertEqual(c.get('/api/workspaces/main').json()['preferences'],{'symbol':'BTCUSDT','interval':'15m'});url='/api/workspaces/main/templates/template';r=c.put(url,json=dict(request_id='http-save',expected_revision=0,name='Şablon',body=self.body()));self.assertEqual(r.status_code,200);body=dict(request_id='http-restore',template_id='template',template_revision=1,expected_profile_revision=0,expected_indicator_revision=0,symbol='ETHUSDT',interval='5m',expected_drawings=[],apply_drawing_styles=False);r=c.post('/api/workspaces/main/template-restore',json=body);self.assertEqual(r.status_code,200);self.assertEqual(r.json()['symbol'],'ETHUSDT');self.assertFalse(r.json()['order_authority']);self.assertFalse(c.get('/api/health').json()['trading_commands_enabled']);self.assertEqual(c.get('/api/workspaces/main').json()['preferences'],{'symbol':'BTCUSDT','interval':'15m'})
