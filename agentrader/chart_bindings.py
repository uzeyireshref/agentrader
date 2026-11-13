"""Disabled, revision-bound local definitions; does not evaluate or activate rules."""
from contextlib import closing
from copy import deepcopy
import json,re,uuid
from .migrations import connect
from .drawings.service import DrawingService,DrawingError,DrawingConflict,DrawingNotFound,identifier
from .drawings.calculations import canonical_hash,verified_grid,CalculationBlocked
from .drawings.fibonacci import LEGACY_LEVELS,ratio_text
from .indicator_config import expand_v4,defaults_v4
from .chart_evidence import digest,chart_number
from .chart_precision import decimal_text
from .binding_catalog import catalog

def binding_hash(value):
 def encode(v):
  if type(v) in (int,float):return {'$f64':chart_number(v)}
  if isinstance(v,list):return [encode(x) for x in v]
  if isinstance(v,dict):return {k:encode(x) for k,x in v.items()}
  return v
 return digest(encode(value))

class BindingError(DrawingError):code='INVALID_BINDING_DEFINITION'
class BindingBlocked(BindingError):
 def __init__(self,reason):self.code=reason;super().__init__(reason)

def rule_definition(rule,allowed):
 fields={'schema','kind','direction','tolerance','closed_candle','rearm_policy'}
 if not isinstance(rule,dict) or set(rule)!=fields or rule['schema']!='chart-rule-definition/1' or rule['kind'] not in allowed or rule['direction'] not in ('ANY','ABOVE','BELOW') or rule['closed_candle'] is not True or rule['rearm_policy']!='EXPLICIT':raise BindingError()
 try:tolerance=decimal_text(rule['tolerance'])
 except ValueError:raise BindingError() from None
 if rule['kind']=='approach' and float(tolerance)<=0 or rule['kind'] in ('observe','close_cross') and tolerance!='0' or rule['kind']=='observe' and rule['direction']!='ANY':raise BindingError()
 return {**rule,'tolerance':tolerance}

class BindingService(DrawingService):
 def _binding(self,db,workspace_id,binding_id,revision=0):
  identifier(workspace_id);identifier(binding_id)
  if type(revision) is not int or not 0<=revision<=1000:raise BindingError()
  if not revision:
   r=db.execute('SELECT revision FROM app_chart_binding_heads WHERE owner=? AND binding_id=?',(self.owner,binding_id)).fetchone()
   if not r:raise DrawingNotFound()
   revision=r['revision']
  row=db.execute('SELECT * FROM app_chart_binding_revisions WHERE owner=? AND workspace_id=? AND binding_id=? AND revision=?',(self.owner,workspace_id,binding_id,revision)).fetchone()
  if not row:raise DrawingNotFound()
  return row
 def _target(self,db,workspace_id,target,symbol=None):
  if not isinstance(target,dict) or set(target)!={'type','object_id','revision'} or target['type'] not in ('drawing','indicator') or type(target['revision']) is not int or target['revision']<0:raise BindingError()
  identifier(target['object_id'])
  if target['type']=='drawing':
   row=self._head(db,target['object_id'])
   if row['workspace_id']!=workspace_id:raise DrawingNotFound()
   if row['deleted']:raise BindingBlocked('TARGET_DELETED')
   if row['revision']!=target['revision']:raise DrawingConflict()
   g=json.loads(row['geometry']);return g['kind'],g['symbol'],g
  row=db.execute('SELECT * FROM app_indicator_configs WHERE owner=? AND workspace_id=?',(self.owner,workspace_id)).fetchone();items=expand_v4(json.loads(row['body'])) if row else defaults_v4();c=next((x for x in items if x['indicator_id']==target['object_id']),None)
  if not c:raise BindingBlocked('UNSUPPORTED_TARGET_KIND')
  if c['revision']!=target['revision']:raise DrawingConflict()
  if not isinstance(symbol,str) or not re.fullmatch(r'[A-Z0-9]{2,20}USDT',symbol):raise BindingError()
  if c['kind']=='ANCHORED_VWAP':
   if not c['params']['anchor_time']:raise BindingBlocked('ANCHOR_UNSET')
   if c['params']['anchor_symbol']!=symbol:raise BindingBlocked('ANCHOR_SYMBOL_MISMATCH')
  return c['kind'],symbol,c
 def _definition(self,db,workspace_id,target,symbol,interval,scale,grid_times,data_snapshot_hash,query,rule):
  if scale!='LINEAR':raise BindingBlocked('UNSUPPORTED_SCALE')
  try:grid=list(verified_grid(grid_times,interval))
  except CalculationBlocked as e:raise BindingBlocked(e.code) from None
  if data_snapshot_hash is not None and (not isinstance(data_snapshot_hash,str) or not re.fullmatch(r'[a-f0-9]{64}',data_snapshot_hash)):raise BindingError()
  kind,actual_symbol,value=self._target(db,workspace_id,target,symbol)
  if value.get('schema')=='chart-channel-family/1':raise BindingBlocked('DISPLAY_ONLY_CHANNEL_FAMILY')
  if actual_symbol!=symbol:raise BindingBlocked('SOURCE_CONTEXT_MISMATCH')
  evidence=catalog()
  if evidence['state']!='VERIFIED_TRACEABILITY':raise BindingBlocked(evidence['reason'])
  entry=evidence['targets'].get(target['type']+':'+kind)
  if not entry:raise BindingBlocked('DISPLAY_ONLY_ANNOTATION' if kind in ('text','note','price_label') else 'UNSUPPORTED_TARGET_KIND')
  if not isinstance(query,dict) or set(query)!={'operation','output','ratio'}:raise BindingError()
  descriptor=next((q for q in entry['queries'] if q['operation']==query['operation'] and q['output']==query['output']),None)
  if not descriptor:raise BindingBlocked('UNSUPPORTED_BINDING_QUERY')
  if kind in ('fibonacci','fibonacci_extension'):
   try:ratio=ratio_text(query['ratio'])
   except (ValueError,TypeError):raise BindingError() from None
   if ratio not in value.get('levels',LEGACY_LEVELS):raise BindingBlocked('UNSUPPORTED_RATIO')
   query={**query,'ratio':ratio}
  elif query['ratio'] is not None:raise BindingError()
  rule=rule_definition(rule,descriptor['rules'])
  try:content_hash=canonical_hash(value,times=grid,interval=interval,scale=scale) if target['type']=='drawing' else digest({'schema':'chart-indicator-binding-content/1','configuration':value,'symbol':symbol,'interval':interval,'scale':scale})
  except CalculationBlocked as e:raise BindingBlocked(e.code) from None
  return dict(schema='chart-binding-definition/1',owner=self.owner,workspace_id=workspace_id,target={**target,'kind':kind,'content_hash':content_hash,'snapshot':value},market=dict(source='binance_usdm_live_trade_price',environment='live_public',product='USD-M',price_type='LAST_PRICE',symbol=symbol,interval=interval),scale=scale,grid=dict(schema='chart-binding-grid/1',times=grid,hash=digest({'interval':interval,'times':grid}),first_time=grid[0],last_time=grid[-1],count=len(grid)),data_reference=dict(snapshot_hash=data_snapshot_hash,state='CLIENT_REFERENCE_NOT_ELIGIBILITY'),query=query,rule=rule,query_evidence={**entry,'descriptor':descriptor,'hash':digest(entry)},activation='DISABLED',evaluation_state='SEPARATE_READ_ONLY_P5',bot_capabilities=dict(read_definition=True,write_target=False,edit_target=False,execute_rule=False,order_authority=False))
 def _view_binding(self,row,full=False):
  d=json.loads(row['definition']);summary=deepcopy(d)
  if not full:summary['grid'].pop('times',None);summary['target'].pop('snapshot',None)
  return dict(schema='chart-binding/1',binding_id=row['binding_id'],revision=row['revision'],workspace_id=row['workspace_id'],state=row['state'],reason=row['reason'],definition_hash=binding_hash(d),definition=summary,live_eligible=False,order_authority=False)
 def show(self,workspace_id,binding_id,revision=0):
  with closing(connect(self.database)) as db:return self._view_binding(self._binding(db,workspace_id,binding_id,revision),True)
 def list_bindings(self,workspace_id,target_type=None,object_id=None):
  identifier(workspace_id)
  if target_type is not None or object_id is not None:
   identifier(object_id)
   if target_type not in ('drawing','indicator'):raise BindingError()
  with closing(connect(self.database)) as db:
   rows=db.execute('SELECT r.* FROM app_chart_binding_revisions r JOIN app_chart_binding_heads h ON r.owner=h.owner AND r.binding_id=h.binding_id AND r.revision=h.revision WHERE r.owner=? AND r.workspace_id=? ORDER BY r.binding_id',(self.owner,workspace_id)).fetchall()
   values=[self._view_binding(r) for r in rows];return dict(schema='chart-binding-list/1',bindings=[b for b in values if target_type is None or b['definition']['target']['type']==target_type and b['definition']['target']['object_id']==object_id],order_authority=False)
 def save_binding(self,workspace_id,binding_id,request_id,expected_binding_revision,target,symbol,interval,scale,grid_times,data_snapshot_hash,query,rule):
  identifier(workspace_id);identifier(binding_id)
  if type(expected_binding_revision) is not int or not 0<=expected_binding_revision<1000:raise BindingError()
  payload=dict(expected_binding_revision=expected_binding_revision,target=target,symbol=symbol,interval=interval,scale=scale,grid_times=grid_times,data_snapshot_hash=data_snapshot_hash,query=query,rule=rule)
  def apply(db):
   head=db.execute('SELECT revision FROM app_chart_binding_heads WHERE owner=? AND binding_id=?',(self.owner,binding_id)).fetchone()
   if (head['revision'] if head else 0)!=expected_binding_revision:raise DrawingConflict()
   if head:
    before=json.loads(self._binding(db,workspace_id,binding_id)['definition'])['target']
    if not isinstance(target,dict) or before['type']!=target.get('type') or before['object_id']!=target.get('object_id'):raise BindingBlocked('REBIND_TARGET_MISMATCH')
   elif db.execute('SELECT COUNT(*) FROM app_chart_binding_revisions WHERE owner=? AND workspace_id=? AND revision=1',(self.owner,workspace_id)).fetchone()[0]>=100:raise BindingError()
   definition=self._definition(db,workspace_id,target,symbol,interval,scale,grid_times,data_snapshot_hash,query,rule);revision=expected_binding_revision+1
   db.execute('INSERT INTO app_chart_binding_revisions VALUES (?,?,?,?,?,?,?)',(self.owner,workspace_id,binding_id,revision,'DISABLED',None,json.dumps(definition)))
   db.execute('INSERT OR REPLACE INTO app_chart_binding_heads VALUES (?,?,?)',(self.owner,binding_id,revision))
   return self._view_binding(self._binding(db,workspace_id,binding_id),True)
  return self._mutation(request_id,['binding',workspace_id,binding_id],payload,apply)
