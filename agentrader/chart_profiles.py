"""Local view/settings presets, versioned and owner scoped; no geometry or authority transfer."""
from .binding_lifecycle import stop_bindings
from contextlib import closing
from copy import deepcopy
import json,re
from .migrations import connect
from .indicator_config import defaults_v4,validate_v4,expand_v4
from .drawings.service import DrawingService,DrawingError,DrawingConflict,management,geometry,identifier
from .drawings.fibonacci import levels
from .drawings.position import metrics
from .drawings.channel_family import NEW_KINDS as FAMILY_NEW_KINDS
from .chart_market import validate_selection
KINDS=('horizontal','zone','trend','fibonacci','ruler','horizontal_ray','ray','extended_line','parallel_channel','fibonacci_extension','long_plan','short_plan','text','note','price_label',*FAMILY_NEW_KINDS)
STYLE_KEYS={'color','line_width','line_style'}

def default_view():return dict(theme='dark',show_volume=True,pane_preset='balanced',price_scale='LINEAR',panel='markets',pane_weights=dict(price=4,volume=1,rsi=1.5,atr=1.5,macd=1.5))
def valid_view(v):
 if (not isinstance(v,dict) or set(v)!=set(default_view()) or v['theme'] not in ('dark','light') or type(v['show_volume']) is not bool or v['pane_preset'] not in ('balanced','price-focus') or v['price_scale'] not in ('LINEAR','LOG') or v['panel'] not in ('markets','drawings','data',None) or not isinstance(v['pane_weights'],dict) or set(v['pane_weights'])!=set(default_view()['pane_weights']) or any(type(x) not in (int,float) or not 0<x<=1000 for x in v['pane_weights'].values())):raise DrawingError()
 return deepcopy(v)
def valid_defaults(value):
 if not isinstance(value,dict) or len(value)>len(KINDS) or any(k not in KINDS for k in value):raise DrawingError()
 result={}
 for kind,c in value.items():
  if not isinstance(c,dict) or set(c)!={'style','options'} or not isinstance(c['style'],dict) or set(c['style'])!=STYLE_KEYS or not isinstance(c['options'],dict):raise DrawingError()
  m=management({**management(),**c['style']});options=deepcopy(c['options'])
  if set(options)-({'levels'} if kind in ('fibonacci','fibonacci_extension') else {'params'} if kind in ('long_plan','short_plan') else set()):raise DrawingError()
  try:
   if 'levels' in options:options['levels']=levels(options['levels'])
   if 'params' in options:
    prices=['110','100','120'] if kind=='long_plan' else ['110','120','100']
    metrics(dict(schema='chart-position/1',kind=kind,anchors=[dict(time=t,price=p) for t,p in zip([1,2,2],prices)],params=options['params']))
  except (ValueError,KeyError,TypeError):raise DrawingError() from None
  result[kind]=dict(style={k:m[k] for k in STYLE_KEYS},options=options)
 return result

def profile_body(body):
 if not isinstance(body,dict) or set(body)!={'schema','view','drawing_defaults'} or body['schema']!='chart-profile/1':raise DrawingError()
 return dict(schema='chart-profile/1',view=valid_view(body['view']),drawing_defaults=valid_defaults(body['drawing_defaults']))
def template_body(body):
 if not isinstance(body,dict) or set(body)!={'schema','view','indicators','drawing_defaults'} or body['schema']!='chart-template/1':raise DrawingError()
 items=deepcopy(validate_v4(body['indicators']))
 for c in items:
  c['revision']=0
  if c['kind']=='ANCHORED_VWAP':c['params'].update(anchor_time=0,anchor_symbol='')
 return dict(schema='chart-template/1',view=valid_view(body['view']),indicators=items,drawing_defaults=valid_defaults(body['drawing_defaults']))

class ProfileService(DrawingService):
 def profile(self,workspace_id):
  identifier(workspace_id)
  with closing(connect(self.database)) as db:return self._profile(db,workspace_id)
 def _profile(self,db,workspace_id):
  row=db.execute('SELECT * FROM app_chart_profiles WHERE owner=? AND workspace_id=?',(self.owner,workspace_id)).fetchone()
  return dict(workspace_id=workspace_id,revision=row['revision'] if row else 0,body=json.loads(row['body']) if row else dict(schema='chart-profile/1',view=default_view(),drawing_defaults={}))
 def save_profile(self,workspace_id,request_id,expected_revision,body):
  identifier(workspace_id);body=profile_body(body)
  if type(expected_revision) is not int or expected_revision<0:raise DrawingError()
  def apply(db):
   old=self._profile(db,workspace_id)
   if old['revision']!=expected_revision:raise DrawingConflict()
   db.execute('INSERT OR REPLACE INTO app_chart_profiles VALUES (?,?,?,?)',(self.owner,workspace_id,expected_revision+1,json.dumps(body)))
   return dict(workspace_id=workspace_id,revision=expected_revision+1,body=body)
  return self._mutation(request_id,['profile',workspace_id],dict(expected_revision=expected_revision,body=body),apply)
 def templates(self,workspace_id):
  identifier(workspace_id)
  with closing(connect(self.database)) as db:
   rows=db.execute('SELECT template_id,MAX(revision) AS revision FROM app_chart_templates WHERE owner=? AND workspace_id=? GROUP BY template_id ORDER BY template_id',(self.owner,workspace_id)).fetchall()
   return dict(templates=[self._template(db,workspace_id,r['template_id'],r['revision'],False) for r in rows])
 def _template(self,db,workspace_id,template_id,revision=0,include_body=True):
  if type(revision) is not int or not 0<=revision<=100:raise DrawingError()
  if revision==0:
   revision=db.execute('SELECT MAX(revision) FROM app_chart_templates WHERE owner=? AND workspace_id=? AND template_id=?',(self.owner,workspace_id,template_id)).fetchone()[0]
  row=db.execute('SELECT * FROM app_chart_templates WHERE owner=? AND workspace_id=? AND template_id=? AND revision=?',(self.owner,workspace_id,template_id,revision)).fetchone()
  if not row:raise DrawingError()
  return dict(template_id=template_id,revision=row['revision'],name=row['name'],**({'body':json.loads(row['body'])} if include_body else {}))
 def template(self,workspace_id,template_id,revision=0):
  identifier(workspace_id);identifier(template_id)
  with closing(connect(self.database)) as db:return self._template(db,workspace_id,template_id,revision)
 def save_template(self,workspace_id,template_id,request_id,expected_revision,name,body):
  identifier(workspace_id);identifier(template_id);body=template_body(body)
  if type(expected_revision) is not int or not 0<=expected_revision<100 or not isinstance(name,str) or not 1<=len(name.strip())<=64 or re.search(r'[\x00-\x1f\x7f]',name):raise DrawingError()
  name=name.strip()
  def apply(db):
   old=db.execute('SELECT MAX(revision) FROM app_chart_templates WHERE owner=? AND workspace_id=? AND template_id=?',(self.owner,workspace_id,template_id)).fetchone()[0] or 0
   if old!=expected_revision:raise DrawingConflict()
   if not old and db.execute('SELECT COUNT(DISTINCT template_id) FROM app_chart_templates WHERE owner=? AND workspace_id=?',(self.owner,workspace_id)).fetchone()[0]>=40:raise DrawingError()
   db.execute('INSERT INTO app_chart_templates VALUES (?,?,?,?,?,?)',(self.owner,workspace_id,template_id,old+1,name,json.dumps(body)))
   return dict(template_id=template_id,revision=old+1,name=name,body=body)
  return self._mutation(request_id,['template',workspace_id,template_id],dict(expected_revision=expected_revision,name=name,body=body),apply)
 def restore(self,workspace_id,request_id,template_id,template_revision,expected_profile_revision,expected_indicator_revision,symbol,interval,expected_drawings,apply_drawing_styles):
  identifier(workspace_id);identifier(template_id);validate_selection(symbol,interval)
  if (type(template_revision) is not int or not 1<=template_revision<=100 or type(expected_profile_revision) is not int or expected_profile_revision<0 or type(expected_indicator_revision) is not int or expected_indicator_revision<0 or type(apply_drawing_styles) is not bool or not isinstance(expected_drawings,list) or len(expected_drawings)>200):raise DrawingError()
  heads={}
  for d in expected_drawings:
   if not isinstance(d,dict) or set(d)!={'drawing_id','revision'} or type(d['revision']) is not int or d['revision']<1:raise DrawingError()
   identifier(d['drawing_id'])
   if d['drawing_id'] in heads:raise DrawingError()
   heads[d['drawing_id']]=d['revision']
  payload=dict(template_id=template_id,template_revision=template_revision,expected_profile_revision=expected_profile_revision,expected_indicator_revision=expected_indicator_revision,symbol=symbol,interval=interval,expected_drawings=expected_drawings,apply_drawing_styles=apply_drawing_styles)
  def apply(db):
   template=self._template(db,workspace_id,template_id,template_revision);body=template_body(template['body']);profile=self._profile(db,workspace_id)
   if profile['revision']!=expected_profile_revision:raise DrawingConflict()
   row=db.execute('SELECT * FROM app_indicator_configs WHERE owner=? AND workspace_id=?',(self.owner,workspace_id)).fetchone()
   if (row['revision'] if row else 0)!=expected_indicator_revision:raise DrawingConflict()
   old=expand_v4(json.loads(row['body'])) if row else defaults_v4();items=[]
   for before,target in zip(old,body['indicators']):
    target=deepcopy(target);target['revision']=before['revision']
    if target['kind']=='ANCHORED_VWAP':target['params'].update(anchor_time=before['params']['anchor_time'],anchor_symbol=before['params']['anchor_symbol'])
    target['revision']+=int(target!=before);items.append(target)
   rows=db.execute('SELECT r.* FROM app_drawing_revisions r JOIN app_drawing_heads h ON r.owner=h.owner AND r.drawing_id=h.drawing_id AND r.revision=h.revision WHERE r.owner=? AND r.workspace_id=? AND r.deleted=0',(self.owner,workspace_id)).fetchall()
   rows=[r for r in rows if json.loads(r['geometry'])['symbol']==symbol]
   if {r['drawing_id']:r['revision'] for r in rows}!=heads:raise DrawingConflict()
   changed=[];skipped=[]
   for r in rows:
    m=management(json.loads(r['management']));kind=json.loads(r['geometry'])['kind'];default=body['drawing_defaults'].get(kind)
    if not apply_drawing_styles or not default:continue
    if m['locked'] or m['hidden'] or m['intervals'] and interval not in m['intervals']:skipped.append(r['drawing_id']);continue
    new={**m,**default['style']}
    if new==m:continue
    revision=r['revision']+1
    db.execute('INSERT INTO app_drawing_revisions VALUES (?,?,?,?,?,?,?,?)',(self.owner,r['drawing_id'],revision,workspace_id,r['geometry'],0,self.clock(),json.dumps(new)))
    db.execute('UPDATE app_drawing_heads SET revision=? WHERE owner=? AND drawing_id=?',(revision,self.owner,r['drawing_id']));changed.append(r['drawing_id'])
   stop_bindings(db,self.owner,workspace_id,'drawing',set(changed),'TARGET_REVISION_CHANGED')
   stop_bindings(db,self.owner,workspace_id,'indicator',{c['indicator_id'] for before,c in zip(old,items) if c['revision']!=before['revision']},'TARGET_REVISION_CHANGED')
   profile=profile_body(dict(schema='chart-profile/1',view=body['view'],drawing_defaults=body['drawing_defaults']))
   db.execute('INSERT OR REPLACE INTO app_chart_profiles VALUES (?,?,?,?)',(self.owner,workspace_id,expected_profile_revision+1,json.dumps(profile)))
   db.execute('INSERT OR REPLACE INTO app_indicator_configs VALUES (?,?,?,?)',(self.owner,workspace_id,expected_indicator_revision+1,json.dumps(items)))
   return dict(schema='chart-template-restore/1',symbol=symbol,interval=interval,template_id=template_id,template_revision=template_revision,profile=dict(workspace_id=workspace_id,revision=expected_profile_revision+1,body=profile),indicators=dict(schema='chart-indicators/4',workspace_id=workspace_id,revision=expected_indicator_revision+1,indicators=items),changed_drawings=changed,skipped_drawings=skipped,order_authority=False)
  return self._mutation(request_id,['template-restore',workspace_id],payload,apply)
