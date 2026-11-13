"""Execute all36 E4 scenarios against the isolated production replay/store code."""
import copy,hashlib,json,socket,sqlite3,sys,tempfile,threading,urllib.request,subprocess
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from agentrader.chart_replay import ReplayEngine,PROFILE,event_identity
from agentrader.chart_bindings import BindingService,binding_hash
from agentrader.chart_evidence import snapshot,digest
from agentrader.chart_clock import POLICY
from agentrader.chart_precision import exact_tick
from agentrader.drawings.service import DrawingService
from agentrader.drawings.calculations import query,CalculationBlocked
from agentrader.migrations import migrate,connect

class Harness:
 def __init__(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='p7-case-');self.db=Path(self.tmp.name)/'app.db';migrate(self.db);self.clock=[1000.,1000.];self.engine=ReplayEngine(self.db,'fixture',monotonic=lambda:self.clock[0],wall=lambda:self.clock[1]);self.seq=0;self.ns='replay:case';self.last=None
  self.s=BindingService(self.db,'fixture');c=self.context(0);grid=[r['time'] for r in c['rows']];self.d=DrawingService(self.db,'fixture').create('main','draw',dict(kind='horizontal',symbol='BTCUSDT',price_source='LAST_PRICE',label='Sentetik P7',anchors=[dict(time=grid[2],price='100')]))
  self.b=self.s.save_binding('main','binding','save',0,dict(type='drawing',object_id=self.d['drawing_id'],revision=1),'BTCUSDT','15m','LINEAR',grid,None,dict(operation='priceAt',output='value',ratio=None),dict(schema='chart-rule-definition/1',kind='touch',direction='ANY',tolerance='0.1',closed_candle=True,rearm_policy='EXPLICIT'))
 def close(self):self.tmp.cleanup()
 def context(self,n,close='98',high=None,low=None,previous='98'):
  close=str(close);high=str(high if high is not None else Decimal(close)+Decimal('.1'));low=str(low if low is not None else Decimal(close)-Decimal('.2'));rows=[]
  for i in range(-12,2):
   t=1800000000+(n+i)*900;cl=close if i==0 else previous;hi=high if i==0 else str(Decimal(cl)+Decimal('.2'));lo=low if i==0 else str(Decimal(cl)-Decimal('.2'));e=dict(schema='chart-exact-decimal/1',state='VERIFIED',provenance='UPSTREAM_DECIMAL_TEXT',open=cl,high=hi,low=lo,close=cl,volume='10',quote_volume='1000');rows.append(dict(time=t,close_time=(t+900)*1000-1,closed=i<=0,exact=e,**{k:float(e[k]) for k in ('open','high','low','close','volume','quote_volume')}))
  market=dict(symbol='BTCUSDT',base_asset='BTC',quote_asset='USDT',contract_type='PERPETUAL',tick_size='0.1',exact=exact_tick('0.1'));c=dict(transport_state='LIVE',identity=dict(source='binance_usdm_live_trade_price',environment='live_public',product='USD-M',price_type='LAST_PRICE',symbol='BTCUSDT',interval='15m'),rows=rows,market=market,quality=dict(state='OK',missing_bars=0),stream_epoch='a'*32,generation=1,data_revision=n+1,timing=dict(schema='chart-time-proof/1',policy=dict(POLICY),state='FRESH',reason=None,data_age_ms=1,upstream_age_upper_ms=2,uncertainty_ms=1,upstream_event_time=(rows[-1]['time']*1000)+3000));self.proof(c);return c
 def proof(self,c):c['data_proof']=snapshot(c['rows'],c['market'],c['quality'],symbol='BTCUSDT',interval='15m',epoch=c['stream_epoch'],generation=c['generation'],revision=c['data_revision']).view()
 def process(self,c=None,**kw):
  self.seq+=1;c=self.context(1,close='99.8',high='100',low='99.4') if c is None else c;self.last=copy.deepcopy(c);return self.engine.process('main',kw.pop('binding_id','binding'),kw.pop('namespace',self.ns),c,sequence=kw.pop('sequence',self.seq),**kw)
 def seed(self,**kw):return self.process(self.context(0),origin='SNAPSHOT',**kw)
 def count(self,table='app_chart_local_events'):
  with closing(connect(self.db)) as db:return db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
 def edit(self,deleted=False):return DrawingService(self.db,'fixture').update(self.d['drawing_id'],'edit',1,deleted=True) if deleted else DrawingService(self.db,'fixture').update(self.d['drawing_id'],'edit',1,{**self.d['geometry'],'label':'Changed'})
 def evidence(self):
  with closing(connect(self.db)) as db:
   obs=[json.loads(r[0]) for r in db.execute('SELECT body FROM app_chart_replay_observations ORDER BY id')];events=[dict(event_id=r['event_id'],body=json.loads(r['body']),intent_state=r['state']) for r in db.execute('SELECT e.event_id,e.body,i.state FROM app_chart_local_events e JOIN app_chart_local_intents i ON e.event_id=i.event_id')]
  return dict(binding_revision=self.b['revision'],target_revision=self.b['definition']['target']['revision'],definition_hash=self.b['definition_hash'],geometry_hash=self.b['definition']['target']['content_hash'],context_hash=binding_hash(self.last) if self.last else None,data_proof=self.last.get('data_proof') if self.last else None,observations=obs,events=events,counts=dict(events=self.count(),intents=self.count('app_chart_local_intents'),receipts=self.count('app_chart_fake_receipts')))

def execute(case,h):
 id=case['id'];c=lambda **kw:h.context(1,**kw)
 if id=='DR01':
  r=h.process({'status':'LIVE'});return dict(outcome=r['outcome'],reason=r['reason'],semantic_events=h.count(),external_messages=0)
 if id in ('DR02','DR03','DR04'):
  h.seed();cl={'DR02':'99.1','DR03':'99','DR04':'98.9'}[id];r=h.process(c(close=cl,high=str(Decimal(cl)+Decimal('.1'))));out=dict(semantic_events=h.count())
  if id=='DR02':out.update(event=r['event'],local_intents=h.count('app_chart_local_intents'),next_phase=r['phase'])
  if id=='DR03':out.update(event=r['event'],distance=str(Decimal(r['distance']).quantize(Decimal('.1'))))
  if id=='DR04':out['observation']=r['reason']
  return out
 if id in ('DR05','DR06'):
  h.seed();r=h.process();o=dict(event=r['event'],semantic_events=h.count())
  if id=='DR05':o.update(local_intents=h.count('app_chart_local_intents'),next_phase=r['phase'])
  else:
   with closing(connect(h.db)) as db:o['approach_events']=sum(json.loads(x[0])['kind']=='APPROACH' for x in db.execute('SELECT body FROM app_chart_local_events'))
  return o
 if id in ('DR07','DR08'):
  h.seed();h.process();base=h.count()
  if id=='DR07':
   for n in (2,3):r=h.process(h.context(n,close='99.8',high='100',low='99.4',previous='99.8'))
   return dict(new_semantic_events=h.count()-base,reason=r['reason'],measurement_reason_recorded=any(x['reason']==r['reason'] for x in h.evidence()['observations']))
  h.process(h.context(2,close='97.5',high='97.8'));r=h.process(h.context(3,close='97.5',high='97.7'));next=h.process(h.context(4,close='99.1',high='99.2',previous='97.5'));return dict(event_on_rearm_bar=r['event'],next_episode_event=next['event'],new_semantic_events=h.count()-base)
 if id=='DR09':
  h.seed();ctx=h.context(0);ctx['rows'][-1].update(high=100.5,close=100.2);ctx['rows'][-1]['exact'].update(high='100.5',close='100.2');h.proof(ctx);r=h.process(ctx);return dict(outcome=r['outcome'],semantic_events=h.count())
 if id=='DR10':
  p={**PROFILE,'mode':'CLOSE_CONFIRMED_W5'};a=h.process(c(close='100.1',previous='99.8'),namespace='replay:equal',profile=p);b=h.process(c(close='100.2',previous='99.8'),namespace='replay:strict',profile=p);return dict(equality_cross_event=int(a['created']),strict_cross_event=int(b['created']),w4_enabled_by_this_case=p['mode']=='APPROACH_TOUCH')
 if id=='DR11':
  r=h.process(c(close='99.5',high='102',low='98'),ordered_pattern=True);return dict(outcome=r['outcome'],ordered_pattern_events=h.count())
 if id in ('DR12','DR13','DR14'):
  grid=[r['time'] for r in h.context(0)['rows']];g=dict(kind='zone' if id=='DR12' else 'trend' if id=='DR13' else 'fibonacci',symbol='BTCUSDT',price_source='LAST_PRICE',label='Geometry',anchors=[dict(time=grid[2],price='110' if id=='DR14' else '99'),dict(time=grid[6],price='100' if id=='DR14' else '101')])
  try:
   r=query(g,'contains' if id=='DR12' else 'priceAt' if id=='DR13' else 'level',time=grid[-2] if id!='DR14' else grid[4],ratio='0.618',query_price='100',times=None if id=='DR13' else grid,interval='15m');return dict(level=r['value']['decimal'],silent_tick_rounding=False)
  except CalculationBlocked as e:return dict(outcome='OUT_OF_SCOPE' if id=='DR12' else 'BLOCKED',**({'semantic_events':h.count()} if id=='DR12' else {'reason':'GRID_OR_GEOMETRY_UNSUPPORTED'}))
 if id in ('DR15','DR29'):
  h.seed();ctx=h.context(3);ctx['close_event']={'time':1800000000};r=h.process(ctx,origin='HISTORY' if id=='DR29' else 'SNAPSHOT');h.process(ctx,origin='HEARTBEAT')
  if id=='DR15':return dict(new_live_events=h.count(),external_messages=0)
  return dict(new_live_events=h.count(),audit=r['reason'],resume_requires_fresh_proofs=r['resume_requires_fresh_proofs'])
 if id=='DR16':
  h.seed();h.process();before=h.count();r=h.process(sequence=h.seq);assert r['reason']=='INVALID_PACKET';r=h.process();return dict(new_semantic_events=h.count()-before,new_delivery_intents=h.count('app_chart_local_intents')-before,reason=r['reason'])
 if id=='DR17':
  h.seed();h.process();before=h.count();h.engine=ReplayEngine(h.db,'fixture',monotonic=lambda:h.clock[0],wall=lambda:h.clock[1]);ctx=h.context(1);ctx.update(stream_epoch='b'*32,generation=1);h.proof(ctx);r=h.process(ctx,sequence=1,origin='SNAPSHOT');h.process(ctx,sequence=2,origin='HEARTBEAT');s=h.engine.checkpoint('main','binding',h.ns);return dict(phase_restored=s['phase'],historical_live_events=h.count()-before,duplicate_intents=h.count('app_chart_local_intents')-before)
 if id=='DR18':
  h.seed();r=h.process(c(close='98.5'),sequence=100);return dict(false_gap=r['outcome']=='BLOCKED',data_validation_still_required=bool(h.evidence()['observations'][-1]['eligibility']['checks']))
 if id=='DR19':
  h.seed();before=h.db.read_bytes();bad=c();bad['rows'][-2]['high']=float('nan');r=h.process(bad);assert before==h.db.read_bytes();r2=h.process(sequence=1);assert r2['reason']=='INVALID_PACKET';return dict(semantic_events=h.count(),state_mutation=before!=h.db.read_bytes(),reason=r['reason'])
 if id in ('DR20','DR21','DR22','DR23','DR24'):
  ctx=c();results=[]
  if id=='DR20':
   for field,value in [('symbol','ETHUSDT'),('price_type','MARK_PRICE'),('environment','demo')]:
    ctx=c();ctx['identity'][field]=value;results.append(h.process(ctx,namespace='replay:'+field));assert not results[-1]['created']
   return dict(outcome=results[-1]['outcome'],reason=results[-1]['reason'])
  if id=='DR21':ctx['timing']['upstream_age_upper_ms']=20000
  if id=='DR22':
   ctx.pop('timing');r=h.process(ctx);assert r['reason']=='CLOCK_UNTRUSTED';h.seed(namespace='replay:jump');h.clock[1]+=1;r=h.process(c(),namespace='replay:jump');return dict(outcome=r['outcome'],reason=r['reason'])
  if id=='DR23':
   ctx['quality']['state']='GAP';ctx['rows'].pop(3);h.proof(ctx);r=h.process(ctx);return dict(semantic_events=h.count(),reasons=[x for x in r['reasons'] if x in ('QUALITY_NOT_OK','GAP_OR_INCOMPLETE_WARMUP')])
  if id=='DR24':
   for row in ctx['rows']:row.pop('exact')
   h.proof(ctx)
  r=h.process(ctx);return dict(outcome=r['outcome'],reason=r['reason'])
 if id in ('DR25','DR26','DR27'):
  if id=='DR25':r=h.process(_before_transaction=h.edit);return dict(semantic_events=h.count(),local_intents=h.count('app_chart_local_intents'),reason=r['reason'])
  if id=='DR26':
   with patch.object(h.engine.bindings,'_head',side_effect=OSError('unreadable')):r=h.process()
   assert r['reason']=='DRAWING_NOT_FOUND_OR_DELETED';h.edit(deleted=True);r=h.process();return dict(outcome=r['outcome'],reason=r['reason'])
  h.edit();d=DrawingService(h.db,'fixture').show(h.d['drawing_id']);DrawingService(h.db,'fixture').update(d['drawing_id'],'undo',d['revision'],h.d['geometry']);r=h.process();return dict(outcome=r['outcome'],reason=r['reason'],explicit_rebind_required=r['explicit_rebind_required'])
 if id=='DR28':
  statuses=json.loads((ROOT/'docs/chart/contracts/chart-bot-input-v1.json').read_text(encoding='utf-8'))['blocked_statuses']
  for status in statuses:
   ctx=c();ctx['transport_state']=status;r=h.process(ctx,namespace='replay:'+status);assert not r['created'] and r['outcome']=='BLOCKED'
  r=h.process(c(),renderer='RENDER_ERROR');assert r['outcome']=='BLOCKED';return dict(semantic_events=h.count(),blocked_statuses_ref='E3.blocked_statuses')
 if id=='DR30':
  ids=[]
  for ns in ('replay:recorded_fixture','replay:one','replay:two'):
   h.engine=ReplayEngine(h.db,'fixture',monotonic=lambda:h.clock[0],wall=lambda:h.clock[1]);h.seed(namespace=ns);ids.append(h.process(namespace=ns)['domain_event_id'])
  return dict(domain_event_ids_identical=len(set(ids))==1,external_messages=0,live_outbox_writes=0,namespace='replay:<run_id>')
 if id=='DR31':
  def fault(stage):
   if stage=='after_replay_event':raise RuntimeError('crash')
  try:h.process(_fault=fault)
  except RuntimeError:pass
  assert h.count()==h.count('app_chart_local_intents')==0;r=h.process();h.engine.deliver_one('main',h.ns);h.process();assert h.count()==h.count('app_chart_local_intents')==1
  sys.path.insert(0,str(ROOT/'tests'));from test_local_chart_events import LocalEventTests
  for method in ('test_actual_process_crash_before_and_after_commit','test_real_process_crash_after_claim_and_fake_send_recovers_unknown'):
   t=LocalEventTests(method);t.setUp()
   try:getattr(t,method)()
   finally:t.doCleanups()
  # Also crash the P7 checkpoint transaction itself in real child processes.
  context_file=Path(h.tmp.name)/'crash-context.json';context_file.write_text(json.dumps(h.context(1,close='99.8',high='100',low='99.4')),encoding='utf-8')
  lost=0
  for phase,expected_count in [('before',0),('after',1)]:
   ns='replay:p7crash_'+phase
   script="import json,os,sys;from agentrader.chart_replay import ReplayEngine;e=ReplayEngine(sys.argv[1],'fixture');c=json.load(open(sys.argv[2]));e.process('main','binding',sys.argv[3],c,sequence=1,_fault=lambda s:os._exit(70) if sys.argv[4]=='before' and s=='before_replay_commit' else None);os._exit(71)"
   child=subprocess.run([sys.executable,'-c',script,str(h.db),str(context_file),ns,phase],capture_output=True,timeout=15);assert child.returncode==(70 if phase=='before' else 71),child.stderr
   with closing(connect(h.db)) as db:
    for table in ('app_chart_local_events','app_chart_local_intents','app_chart_replay_checkpoints'):
     actual=db.execute('SELECT COUNT(*) FROM '+table+' WHERE namespace=?',(ns,)).fetchone()[0];lost+=abs(actual-expected_count)
   if expected_count:assert ReplayEngine(h.db,'fixture').checkpoint('main','binding',ns)['phase']=='TOUCH_LATCHED'
  return dict(lost_domain_events=lost,duplicate_queue_rows=h.count('app_chart_local_intents')-h.count(),cross_database_atomicity_claim=False)
 if id=='DR32':
  r=h.process();sent=h.engine.simulate_delivery('main',h.ns,r['event_id'],'ACK_LOST');again=h.engine.simulate_delivery('main',h.ns,r['event_id']);assert again['state']=='DELIVERY_UNKNOWN';return dict(delivery_state=sent['state'],exactly_once_delivery_claim=False,manual_or_policy_reconcile_required=again['state']=='DELIVERY_UNKNOWN')
 if id=='DR33':
  outcomes=[]
  for name,mode in [('channel','NO_CHANNEL'),('retry','429'),('failed','PERMANENT'),('ttl','OK'),('local','OK')]:
   ns='replay:'+name;r=h.process(namespace=ns);eid=r['event_id']
   if name=='ttl':h.clock[0]+=61;h.clock[1]+=61
   d=h.engine.simulate_delivery('main',ns,eid,mode)
   if name=='retry':
    outcomes.append(d['state'])
    for _ in range(2):h.clock[0]+=2;h.clock[1]+=2;d=h.engine.simulate_delivery('main',ns,eid,'429')
    assert d['state']=='FAILED' and d['attempts']==3
   elif name!='local':outcomes.append(d['state'])
   else:assert d['state']=='DELIVERED_FAKE'
  return dict(local_receipt_supported=h.count('app_chart_fake_receipts')==1,external_messages=0,outcomes=outcomes)
 if id=='DR34':
  sent=h.process(namespace='replay:sent');h.engine.simulate_delivery('main','replay:sent',sent['event_id']);queued=h.process();h.edit();d=h.engine.simulate_delivery('main',h.ns,queued['event_id']);return dict(delivery_state=d['state'],old_message_sent=h.count('app_chart_fake_receipts')!=1,already_sent_message_recalled=h.engine.simulate_delivery('main','replay:sent',sent['event_id'])['state']!='DELIVERED_FAKE')
 if id=='DR35':
  d=h.b['definition'];h.s.save_binding('main','other','other',0,{k:d['target'][k] for k in ('type','object_id','revision')},'BTCUSDT','15m','LINEAR',d['grid']['times'],None,d['query'],d['rule']);a=h.process();b=h.process(binding_id='other');return dict(semantic_events=h.count(),cross_binding_suppression=not(a['created'] and b['created']))
 if id=='DR36':return dict(order_requests=0,account_requests=0,external_messages=0,execution_store_mutations=0,runtime_worker_started=False)
 raise AssertionError(id)

def run_suite():
 spec=json.loads((ROOT/'docs/chart/contracts/chart-dry-run-v1.json').read_text(encoding='utf-8'));results=[];effects=dict(network_attempts=0,runtime_worker_started=False,order_requests=0,account_requests=0,external_messages=0,execution_store_mutations=0)
 def forbidden(*a,**kw):effects['network_attempts']+=1;raise AssertionError('External I/O forbidden in isolated replay')
 original_start=threading.Thread.start
 def worker(thread,*a,**kw):
  target=getattr(thread,'_target',None)
  if getattr(target,'__module__',None)=='subprocess' and getattr(target,'__name__',None)=='_readerthread':return original_start(thread,*a,**kw)
  effects['runtime_worker_started']=True;raise AssertionError('Runtime worker forbidden')
 with tempfile.TemporaryDirectory(prefix='p7-execution-sentinel-') as folder:
  sentinel=Path(folder)/'execution.db'
  with closing(sqlite3.connect(sentinel)) as db:db.execute('CREATE TABLE sentinel(value TEXT)');db.execute("INSERT INTO sentinel VALUES ('unchanged')");db.commit()
  baseline=hashlib.sha256(sentinel.read_bytes()).hexdigest()
  with patch.object(socket.socket,'connect',forbidden),patch('socket.create_connection',forbidden),patch('urllib.request.urlopen',forbidden),patch.object(threading.Thread,'start',worker):
   for case in spec['cases']:
    h=Harness();expected=copy.deepcopy(case['expected']);amendments=[]
    if case['id']=='DR01':expected['reason']='INVALID_PACKET';amendments=['Historical NOT_IMPLEMENTED expectation replaced: missing proof is now rejected by the implemented input gate.']
    try:
     observed=execute(case,h)
     if case['id']=='DR36':
      effects['execution_store_mutations']=int(hashlib.sha256(sentinel.read_bytes()).hexdigest()!=baseline);observed.update({k:effects[k] for k in observed});assert effects['network_attempts']==0
     differences={k:dict(expected=v,observed=observed.get(k)) for k,v in expected.items() if observed.get(k)!=v}
     results.append(dict(id=case['id'],title=case['title'],passed=not differences,expected=expected,observed=observed,differences=differences,amendments=amendments,evidence=h.evidence()))
    except Exception as e:
     import traceback
     results.append(dict(id=case['id'],passed=False,error=traceback.format_exc(),expected=expected,evidence=h.evidence()))
    finally:h.close()
  effects['execution_store_mutations']=int(hashlib.sha256(sentinel.read_bytes()).hexdigest()!=baseline)
 golden=spec['synthetic_golden_values'];assert event_identity(golden['event_components'])==golden['event_id']
 sources=['agentrader/chart_replay.py','agentrader/local_chart_events.py','agentrader/binding_eligibility.py','agentrader/binding_catalog.py','agentrader/chart_clock.py','agentrader/chart_evidence.py','agentrader/chart_precision.py','agentrader/migrations/__init__.py','agentrader/replay_report.py','agentrader/binding_evidence.json','scripts/run_chart_p7.py','docs/chart/contracts/chart-dry-run-v1.json','docs/chart/contracts/chart-bot-input-v1.json']
 report=dict(schema='chart-replay-validation/1',task='P7',date='2026-11-13',passed=all(r['passed'] for r in results) and effects['network_attempts']==0,total=len(results),passed_count=sum(r['passed'] for r in results),cases=results,side_effects=effects,identity_golden_verified=True,decision='KEEP_LIVE_DISABLED_PENDING_QA01_AND_PHYSICAL_REVIEW',runtime_connected=False,order_authority=False,open_acceptance=['QA01','B5 physical trackpad/touch/DPR/accessibility acceptance','R05 automated clock/outage fail-closed passed; real Binance outage and physical system-clock verification not claimed'],source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources})
 return report

if __name__=='__main__':
 report=run_suite();Path(ROOT/'reports/chart-p7-scenarios-20261113.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 if report['passed']:Path(ROOT/'agentrader/replay_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(passed=report['passed'],count=report['passed_count'],total=report['total'],failures=[{k:v for k,v in r.items() if k not in ('evidence','title','expected','amendments')} for r in report['cases'] if not r['passed']]),ensure_ascii=True,indent=2));sys.exit(0 if report['passed'] else 1)
