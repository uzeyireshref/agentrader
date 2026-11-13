"""Isolated, explicitly called replay engine. No runtime subscriber or external sink."""
from contextlib import closing
from copy import deepcopy
from fractions import Fraction
import hashlib,json,math,uuid,sqlite3

from .binding_catalog import catalog
from .binding_eligibility import evaluate_binding
from .chart_bindings import binding_hash
from .chart_clock import POLICY
from .chart_evidence import canonical,digest,grid_info
from .drawings.calculations import query,encoded,CalculationBlocked
from .drawings.service import DrawingError
from .local_chart_events import LocalChartEvents,LocalEventError,replay_namespace,target_view
from .market_data import INTERVALS
from .migrations import connect

PROFILE=dict(schema='chart-replay-profile/1',direction='FROM_BELOW',approach='1',touch='0.1',rearm='2',cooldown=2,mode='APPROACH_TOUCH',ttl_seconds=60,max_attempts=3)
BLOCKED_STATUSES=('CONNECTING','SYNCING','RECONNECTING','STALE','GAP','STOPPED','ERROR','EMPTY','RENDER_ERROR','CLOSED')
IDENTITY_FIELDS=('source','environment','product','price_type','symbol','interval','workspace_id','drawing_id','drawing_revision','binding_id','binding_version','rule_id','rule_version','event_kind','candle_open_time')

def event_identity(components):
    values=[]
    for key in IDENTITY_FIELDS:
        v=components[key]
        if not isinstance(v,str) or not v:raise ValueError('Invalid event identity')
        if key in ('drawing_revision','binding_version','rule_version','candle_open_time') and (not v.isascii() or not v.isdecimal() or str(int(v))!=v or int(v)<=0):raise ValueError('Invalid identity integer')
        values.append(v)
    return hashlib.sha256(canonical(values).encode()).hexdigest()

def validated_profile(value):
    p=deepcopy(value)
    if set(p)!=set(PROFILE) or p['schema']!=PROFILE['schema'] or p['direction'] not in ('FROM_BELOW','FROM_ABOVE') or p['mode'] not in ('APPROACH_TOUCH','CLOSE_CONFIRMED_W5') or type(p['cooldown']) is not int or not 1<=p['cooldown']<=20:raise ValueError('Invalid replay profile')
    if not Fraction(p['rearm'])>Fraction(p['approach'])>Fraction(p['touch'])>=0 or p['ttl_seconds']!=60 or p['max_attempts']!=3:raise ValueError('Invalid replay thresholds')
    return p

def reason_for(reasons):
    if any('PRECISION' in r for r in reasons):return 'PRICE_PRECISION_UNPROVEN'
    if any('CLOCK' in r or r in ('CLOSED_TIME_UNPROVEN','EVENT_GRID_MISMATCH') for r in reasons):return 'CLOCK_UNTRUSTED'
    if any('STALE' in r and 'EVIDENCE' not in r for r in reasons):return 'STALE_INPUT'
    if any('CONTEXT' in r or 'IDENTITY' in r for r in reasons):return 'IDENTITY_MISMATCH'
    if any('GRID' in r or 'WARMUP' in r or 'DATA_PROOF' in r for r in reasons):return 'GAP_OR_INCOMPLETE_WARMUP'
    return reasons[0] if reasons else 'OBSERVE_ONLY'

class ReplayEngine(LocalChartEvents):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.boot_id=uuid.uuid4().hex
    def checkpoint(self,workspace_id,binding_id,namespace,profile=None):
        replay_namespace(namespace);p=validated_profile(profile or PROFILE)
        b=self.bindings.show(workspace_id,binding_id)
        with closing(connect(self.database)) as db:
            row=db.execute('SELECT body FROM app_chart_replay_checkpoints WHERE owner=? AND workspace_id=? AND namespace=? AND binding_id=? AND binding_revision=? AND profile_hash=?',(self.owner,workspace_id,namespace,binding_id,b['revision'],binding_hash(p))).fetchone()
        return json.loads(row['body']) if row else None

    def process(self,workspace_id,binding_id,namespace,context,*,sequence,origin='CLOSE',renderer='READY',profile=None,ordered_pattern=False,_before_transaction=None,_fault=None):
        replay_namespace(namespace);p=validated_profile(profile or PROFILE);phash=binding_hash(p)
        if type(sequence) is not int or sequence<0 or origin not in ('SNAPSHOT','HISTORY','HEARTBEAT','CLOSE'):return dict(outcome='BLOCKED',reason='INVALID_PACKET',created=False)
        try:b0=self.bindings.show(workspace_id,binding_id)
        except (DrawingError,OSError,sqlite3.Error):return dict(outcome='BLOCKED',reason='DRAWING_NOT_FOUND_OR_DELETED',created=False)
        if _before_transaction:_before_transaction()
        with closing(connect(self.database)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            try:
                t=b0['definition']['target']
                if t['type']=='drawing' and self.bindings._head(db,t['object_id'])['deleted']:return dict(outcome='BLOCKED',reason='DRAWING_NOT_FOUND_OR_DELETED',created=False)
                b=self._current(db,workspace_id,binding_id,b0['revision'],b0['definition_hash'])
            except (OSError,sqlite3.Error):return dict(outcome='BLOCKED',reason='DRAWING_NOT_FOUND_OR_DELETED',created=False)
            except DrawingError:return dict(outcome='BLOCKED',reason='REVISION_CHANGED',created=False,explicit_rebind_required=True)
            key=(self.owner,workspace_id,namespace,binding_id,b['revision'],phash)
            row=db.execute('SELECT body FROM app_chart_replay_checkpoints WHERE owner=? AND workspace_id=? AND namespace=? AND binding_id=? AND binding_revision=? AND profile_hash=?',key).fetchone()
            state=json.loads(row['body']) if row else dict(phase='ARMED',lifecycle='DISABLED_REPLAY',cooldown=0,episode=1,last_time=None,epoch=None,sequence=-1,paused=False)
            before=deepcopy(state);c=deepcopy(context) if isinstance(context,dict) else {}
            epoch=c.get('stream_epoch')
            if epoch==state['epoch'] and sequence<=state['sequence']:return dict(outcome='BLOCKED',reason='INVALID_PACKET',created=False,phase=state['phase'])
            try:
                rows=c['rows'];times=[r['time'] for r in rows]
                if not grid_info(rows,b['definition']['market']['interval'])['valid'] or any(type(r[k]) not in (int,float) or not math.isfinite(r[k]) or r[k]<0 for r in rows for k in ('open','high','low','close','volume','quote_volume')) or any(y<=x for x,y in zip(times,times[1:])):raise ValueError()
            except (ValueError,KeyError,TypeError):return dict(outcome='BLOCKED',reason='INVALID_PACKET',created=False)
            eligibility=evaluate_binding(b,owner=self.owner,workspace_id=workspace_id,target=target_view(self.bindings,db,b),context=c,traceability=catalog())
            if state.get('boot_id')==self.boot_id:
                elapsed=(self.monotonic()-state['mono'])*1000;wall_elapsed=(self.wall()-state['wall'])*1000
                if elapsed<0 or abs(elapsed-wall_elapsed)>POLICY['wall_jump_ms']:
                    eligibility.update(state='BLOCKED',reasons=['CLOCK_UNTRUSTED'])
            result=dict(outcome='NO_EVENT',reason='OUTSIDE_APPROACH',created=False,phase_before=before['phase'],phase=state['phase'],event=None,order_authority=False)
            def save():
                state.update(boot_id=self.boot_id,mono=self.monotonic(),wall=self.wall())
                result['phase']=state['phase'];result['episode']=state['episode'];result['checkpoint']=deepcopy(state)
                db.execute('INSERT OR REPLACE INTO app_chart_replay_checkpoints VALUES (?,?,?,?,?,?,?)',(*key,canonical(state)))
                audit=dict(result,binding_id=binding_id,binding_revision=b['revision'],definition_hash=b['definition_hash'],market=b['definition']['market'],data_proof=c.get('data_proof'),eligibility=eligibility,profile=p)
                db.execute('INSERT INTO app_chart_replay_observations(owner,workspace_id,namespace,binding_id,body) VALUES (?,?,?,?,?)',(self.owner,workspace_id,namespace,binding_id,canonical(audit)))
                if _fault:_fault('before_replay_commit')
                return result
            if eligibility['state']!='EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY' or renderer!='READY' or c.get('transport_state')!='LIVE':
                state.update(paused=True,lifecycle='PAUSED_DATA')
                reasons=list(eligibility['reasons'])
                if c.get('quality',{}).get('state')!='OK':reasons+=['QUALITY_NOT_OK']
                if any('GRID' in r or 'WARMUP' in r or 'DATA_PROOF' in r for r in reasons):reasons+=['GAP_OR_INCOMPLETE_WARMUP']
                result.update(outcome='BLOCKED',reason='RENDER_OR_TRANSPORT_NOT_READY' if renderer!='READY' else reason_for(reasons),reasons=list(dict.fromkeys(reasons)))
                return save()
            closed=[r for r in rows if r['closed']];bar=closed[-1];step=INTERVALS[b['definition']['market']['interval']]//1000
            if origin in ('SNAPSHOT','HISTORY'):
                state.update(epoch=epoch,sequence=sequence,last_time=bar['time'],last_payload_hash=binding_hash(bar))
                if before['epoch'] is not None:state.update(paused=True,lifecycle='PAUSED_DATA')
                result.update(outcome='OBSERVE_ONLY',reason='HISTORICAL_CATCHUP' if origin=='HISTORY' else 'HISTORY_BOOTSTRAP',resume_requires_fresh_proofs=True)
                return save()
            if origin=='HEARTBEAT':
                if state['epoch'] is not None and epoch!=state['epoch'] or row and before.get('boot_id')!=self.boot_id:
                    state.update(paused=True,lifecycle='PAUSED_DATA');result.update(outcome='BLOCKED',reason='EXPLICIT_RESUME_REQUIRED');return save()
                state.update(epoch=epoch,sequence=sequence);result.update(outcome='OBSERVE_ONLY',reason='HEARTBEAT_NOT_CLOSE');return save()
            if row and before.get('boot_id')!=self.boot_id:
                state.update(paused=True,lifecycle='PAUSED_DATA');result.update(outcome='BLOCKED',reason='EXPLICIT_RESUME_REQUIRED');return save()
            if state['epoch'] is not None and (epoch!=state['epoch'] or state['last_time'] is not None and bar['time']>state['last_time']+step):
                state.update(paused=True,lifecycle='PAUSED_DATA');result.update(outcome='BLOCKED',reason='EXPLICIT_RESUME_REQUIRED');return save()
            if state['paused']:result.update(outcome='BLOCKED',reason='EXPLICIT_RESUME_REQUIRED');return save()
            if state['last_time'] is not None and bar['time']<=state['last_time']:
                if bar['time']==state['last_time'] and state.get('last_payload_hash')!=binding_hash(bar):return dict(outcome='BLOCKED',reason='SEMANTIC_PAYLOAD_CONFLICT',created=False)
                state.update(epoch=epoch,sequence=sequence)
                result.update(outcome='OBSERVE_ONLY',reason='SEMANTIC_EVENT_ALREADY_RECORDED');return save()
            state.update(epoch=epoch,sequence=sequence)
            if ordered_pattern:result.update(outcome='INTRABAR_ORDER_UNKNOWN',reason='OHLC_PATH_UNKNOWABLE');return save()
            # A packet whose only newer candle is open must not reevaluate its old close.
            state.update(last_time=bar['time'],last_payload_hash=binding_hash(bar))
            d=b['definition'];q=d['query']
            try:
                def level(r):
                    v=query(d['target']['snapshot'],q['operation'],time=r['time'],ratio=q['ratio'],query_price=r['exact']['close'],times=[x['time'] for x in closed],interval=d['market']['interval'],scale=d['scale'])['value']
                    if q['operation']=='boundsAt':v=v[q['output']]
                    return Fraction(int(v['numerator']),int(v['denominator']))
                current,prior=level(bar),level(closed[-2])
            except (CalculationBlocked,ValueError,TypeError,KeyError) as e:
                result.update(outcome='OUT_OF_SCOPE' if getattr(e,'code','')=='OUT_OF_SCOPE' else 'BLOCKED',reason='GRID_OR_GEOMETRY_UNSUPPORTED');return save()
            sign=1 if p['direction']=='FROM_BELOW' else -1
            previous=(Fraction(closed[-2]['exact']['close'])-prior)*sign
            delta=(Fraction(bar['exact']['close'])-current)*sign
            lo,hi=sorted((Fraction(bar['exact'][v])-current)*sign for v in ('low','high'))
            approach,touch,rearm=(Fraction(p[k]) for k in ('approach','touch','rearm'))
            kind=None
            if state['phase']=='TOUCH_LATCHED':
                state['cooldown']+=1
                if state['cooldown']>=p['cooldown'] and hi<=-rearm:state.update(phase='ARMED',cooldown=0,episode=state['episode']+1);result['reason']='REARMED_NO_EVENT'
                else:result['reason']='CONTACT_EPISODE_CONTINUES'
                return save()
            if state['phase']=='APPROACH_NOTIFIED' and hi<=-rearm:state.update(phase='ARMED',episode=state['episode']+1);result['reason']='SEPARATED_NO_EVENT';return save()
            if p['mode']=='CLOSE_CONFIRMED_W5':
                if previous<=touch and delta>touch:kind='CLOSE_CROSS'
            elif lo<=touch and hi>=-touch and previous < -touch:kind='TOUCH'
            elif state['phase']=='ARMED' and previous < -approach and -approach<=delta < -touch and delta>previous and hi < -touch:kind='APPROACH'
            if not kind:return save()
            components=dict(d['market'],workspace_id=workspace_id,drawing_id=d['target']['object_id'],drawing_revision=str(d['target']['revision']),binding_id=binding_id,binding_version=str(b['revision']),rule_id='replay_'+binding_hash(p),rule_version='1',event_kind=kind,candle_open_time=str(bar['time']))
            domain_id=event_identity(components);event_id=digest(dict(owner=self.owner,namespace=namespace,domain_event_id=domain_id))
            next_phase={'TOUCH':'TOUCH_LATCHED','APPROACH':'APPROACH_NOTIFIED','CLOSE_CROSS':'TOUCH_LATCHED'}[kind]
            event=dict(schema='chart-local-domain-event/1',profile='CLOSED_EPISODE_REPLAY/1',namespace=namespace,domain_event_id=domain_id,identity_components=components,binding_id=binding_id,binding_revision=b['revision'],definition_hash=b['definition_hash'],target=d['target']|{'snapshot':None},market=d['market'],query=q,rule=p,candle_time=bar['time'],kind=kind,direction='ABOVE' if sign==1 else 'BELOW',phase_before=before['phase'],phase_after=next_phase,episode=state['episode'],level=encoded(current),order_authority=False)
            evidence=dict(definition=d,context=c,eligibility=eligibility,profile=p,cross_database_atomicity=False)
            old=db.execute('SELECT event_id FROM app_chart_local_events WHERE owner=? AND workspace_id=? AND namespace=? AND semantic_key=?',(self.owner,workspace_id,namespace,domain_id)).fetchone()
            if old:result.update(reason='SEMANTIC_EVENT_ALREADY_RECORDED');return save()
            db.execute('INSERT INTO app_chart_local_events VALUES (?,?,?,?,?,?,?,?)',(self.owner,workspace_id,namespace,domain_id,event_id,canonical(event),canonical(evidence),self.wall()))
            if _fault:_fault('after_replay_event')
            intent=dict(schema='chart-local-intent/1',event_id=event_id,binding_id=binding_id,binding_revision=b['revision'],definition_hash=b['definition_hash'],sink='SQLITE_FAKE_ONLY',namespace=namespace,order_authority=False)
            db.execute('INSERT INTO app_chart_local_intents VALUES (?,?,?,?,?,?,?)',(event_id,self.owner,workspace_id,namespace,'PENDING_FAKE',0,canonical(intent)))
            db.execute('INSERT INTO app_chart_replay_delivery_policy VALUES (?,?,?)',(event_id,self.wall()+p['ttl_seconds'],self.wall()))
            state.update(phase=next_phase,cooldown=0)
            result.update(outcome='EVENT',reason=kind,event=kind,created=True,event_id=event_id,domain_event_id=domain_id,distance=str(abs(delta)))
            return save()

    def resume(self,workspace_id,binding_id,namespace,context,*,profile=None):
        """Explicit isolated replay operation; not exposed as an HTTP action."""
        p=validated_profile(profile or PROFILE);replay_namespace(namespace)
        with closing(connect(self.database)) as db,db:
            db.execute('BEGIN IMMEDIATE');b=self.bindings._view_binding(self.bindings._binding(db,workspace_id,binding_id),True)
            e=evaluate_binding(b,owner=self.owner,workspace_id=workspace_id,target=target_view(self.bindings,db,b),context=context,traceability=catalog())
            if e['state']!='EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY':return False
            key=(self.owner,workspace_id,namespace,binding_id,b['revision'],binding_hash(p));r=db.execute('SELECT body FROM app_chart_replay_checkpoints WHERE owner=? AND workspace_id=? AND namespace=? AND binding_id=? AND binding_revision=? AND profile_hash=?',key).fetchone()
            if not r:return False
            bar=max((x for x in context['rows'] if x['closed']),key=lambda x:x['time'])
            s=json.loads(r['body']);s.update(paused=False,lifecycle='DISABLED_REPLAY',epoch=context['stream_epoch'],last_time=bar['time'],last_payload_hash=binding_hash(bar),boot_id=self.boot_id,mono=self.monotonic(),wall=self.wall())
            db.execute('UPDATE app_chart_replay_checkpoints SET body=? WHERE owner=? AND workspace_id=? AND namespace=? AND binding_id=? AND binding_revision=? AND profile_hash=?',(canonical(s),*key));return True

    def simulate_delivery(self,workspace_id,namespace,event_id,outcome='OK',retry_after=1):
        replay_namespace(namespace)
        if outcome not in ('OK','NO_CHANNEL','429','PERMANENT','ACK_LOST'):raise ValueError('Unsupported fake outcome')
        with closing(connect(self.database)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            r=db.execute('SELECT i.*,p.expires_at,p.retry_at FROM app_chart_local_intents i JOIN app_chart_replay_delivery_policy p ON i.event_id=p.event_id WHERE i.event_id=? AND i.owner=? AND i.workspace_id=? AND i.namespace=?',(event_id,self.owner,workspace_id,namespace)).fetchone()
            if not r:raise LocalEventError('LOCAL_INTENT_NOT_FOUND')
            if r['state'] not in ('PENDING_FAKE','RETRY_BOUNDED'):return dict(state=r['state'],attempts=r['attempts'])
            intent=json.loads(r['body']);attempts=r['attempts'];now=self.wall()
            try:self._current(db,workspace_id,intent['binding_id'],intent['binding_revision'],intent['definition_hash']);state=None
            except DrawingError:state='CANCELED_SUPERSEDED'
            if not state and now>=r['expires_at']:state='EXPIRED'
            if not state and now<r['retry_at']:return dict(state=r['state'],attempts=attempts)
            if not state:
                attempts+=1
                if outcome=='NO_CHANNEL':state='CHANNEL_UNCONFIGURED'
                elif outcome=='PERMANENT':state='FAILED'
                elif outcome=='429':
                    state='FAILED' if attempts>=PROFILE['max_attempts'] else 'RETRY_BOUNDED'
                    db.execute('UPDATE app_chart_replay_delivery_policy SET retry_at=? WHERE event_id=?',(now+max(1,min(60,retry_after)),event_id))
                else:
                    receipt=dict(schema='chart-fake-receipt/1',event_id=event_id,namespace=namespace,external_messages=0,order_authority=False)
                    db.execute('INSERT OR IGNORE INTO app_chart_fake_receipts VALUES (?,?,?,?,?)',(event_id,self.owner,workspace_id,namespace,canonical(receipt)))
                    state='DELIVERY_UNKNOWN' if outcome=='ACK_LOST' else 'DELIVERED_FAKE'
            db.execute('UPDATE app_chart_local_intents SET state=?,attempts=? WHERE event_id=?',(state,attempts,event_id))
            return dict(state=state,attempts=attempts)
