"""Persistent closed-candle and sampled live-candle alerts. Local history only; no order adapter."""
from contextlib import closing
from decimal import Decimal
import hashlib,json,math,re,threading,time,uuid,logging
from .migrations import connect
from .drawings.service import DrawingError,DrawingConflict,DrawingNotFound
from .chart_precision import decimal_text
from .market_data import INTERVALS,SOURCE
from .alert_timeframes import align,intervals
from .alert_intrabar import step as intrabar_step
from .alert_conditions import conditions,evaluate_all,ConditionUnavailable

class AlertError(DrawingError):code='INVALID_ALERT'

def _definition(v):
    if isinstance(v,dict) and v.get('schema')=='technical-alert/4':
        if v.get('evaluation')!='intrabar' or v.get('frequency') not in ('once','bar','minute'):raise AlertError()
        checked=definition({k:x for k,x in v.items() if k!='evaluation'}|{'schema':'technical-alert/3','frequency':'bar_close'})
        return {**checked,'schema':'technical-alert/4','evaluation':'intrabar','frequency':v['frequency']}
    if isinstance(v,dict) and v.get('schema')=='technical-alert/3':
        original=v['conditions'];prepared=[]
        for c in original:
            if not isinstance(c,dict) or set(c)!={'interval','left','right','upper','operator','bars'} or c['interval'] not in INTERVALS:raise AlertError()
            prepared.append({k:x for k,x in c.items() if k!='interval'})
        checked=definition({**v,'schema':'technical-alert/2','conditions':prepared})
        checked.update(schema='technical-alert/3',conditions=[{**c,'interval':o['interval']} for c,o in zip(checked['conditions'],original)])
        checked['interval']=min((c['interval'] for c in checked['conditions']),key=lambda i:INTERVALS[i])
        return checked
    multi=isinstance(v,dict) and v.get('schema')=='technical-alert/2'
    if multi:
        if set(v)!={'schema','name','symbol','interval','frequency','expires_at','message','match','conditions'}:raise AlertError()
        try:checked=conditions(v['conditions'],v['match'],v['symbol'])
        except (ValueError,KeyError,TypeError,ArithmeticError):raise AlertError() from None
        base=definition({k:v[k] for k in ('name','symbol','interval','frequency','expires_at','message')}|{'operator':'above','price':'1'})
        return {**{k:base[k] for k in ('name','symbol','interval','frequency','expires_at','message')},'schema':'technical-alert/2','match':v['match'],'conditions':checked}
    if not isinstance(v,dict) or set(v)!={'name','symbol','interval','operator','price','frequency','expires_at','message'}:raise AlertError()
    if not isinstance(v['name'],str) or not 1<=len(v['name'].strip())<=80 or not isinstance(v['message'],str) or len(v['message'])>1000:raise AlertError()
    if not isinstance(v['symbol'],str) or not re.fullmatch('[A-Z0-9]{3,24}',v['symbol']) or v['interval'] not in INTERVALS:raise AlertError()
    if v['operator'] not in ('cross','cross_up','cross_down','above','below') or v['frequency'] not in ('once','bar_close'):raise AlertError()
    end=v['expires_at']
    if end is not None and (type(end) not in (int,float) or not math.isfinite(end) or end<=0):raise AlertError()
    try:price=decimal_text(v['price'],positive=True)
    except ValueError:raise AlertError() from None
    return {**v,'name':v['name'].strip(),'price':price}

def definition(value):
    try:return _definition(value)
    except (ValueError,TypeError,KeyError,ArithmeticError,OverflowError):raise AlertError() from None

class PriceAlerts:
    def __init__(self,database,owner,clock=time.time):self.database,self.owner,self.clock=database,owner,clock
    def list(self):
        with closing(connect(self.database)) as db:
            return [dict(id=r['id'],revision=r['revision'],definition=json.loads(r['body']),state=r['state'],readiness=json.loads(r['checkpoint']).get('readiness','WAITING_DATA')) for r in db.execute('SELECT * FROM app_price_alerts WHERE owner=? ORDER BY rowid DESC',(self.owner,))]
    def events(self):
        with closing(connect(self.database)) as db:return [json.loads(r['body']) for r in db.execute('SELECT body FROM app_price_alert_events WHERE owner=? ORDER BY created_at DESC,rowid DESC LIMIT 100',(self.owner,))]
    def save(self,value,alert_id=None,revision=0):
        value=definition(value)
        if value['expires_at'] is not None and value['expires_at']<=self.clock():raise AlertError()
        with closing(connect(self.database)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            if alert_id:
                row=db.execute('SELECT revision FROM app_price_alerts WHERE owner=? AND id=?',(self.owner,alert_id)).fetchone()
                if not row:raise DrawingNotFound()
                if type(revision) is not int or row['revision']!=revision:raise DrawingConflict()
                db.execute('UPDATE app_price_alerts SET revision=?,body=?,state=?,checkpoint=? WHERE owner=? AND id=?',(revision+1,json.dumps(value),'ACTIVE','{}',self.owner,alert_id))
            else:
                alert_id=uuid.uuid4().hex;db.execute('INSERT INTO app_price_alerts VALUES (?,?,?,?,?,?)',(self.owner,alert_id,1,json.dumps(value),'ACTIVE','{}'))
        return next(x for x in self.list() if x['id']==alert_id)
    def action(self,alert_id,revision,action):
        if action not in ('pause','resume','delete') or type(revision) is not int:raise AlertError()
        with closing(connect(self.database)) as db,db:
            db.execute('BEGIN IMMEDIATE');r=db.execute('SELECT * FROM app_price_alerts WHERE owner=? AND id=?',(self.owner,alert_id)).fetchone()
            if not r:raise DrawingNotFound()
            if r['revision']!=revision:raise DrawingConflict()
            if action=='delete':db.execute('DELETE FROM app_price_alerts WHERE owner=? AND id=?',(self.owner,alert_id))
            else:
                d=json.loads(r['body'])
                if action=='resume' and d['expires_at'] is not None and d['expires_at']<=self.clock():raise AlertError()
                db.execute('UPDATE app_price_alerts SET revision=revision+1,state=?,checkpoint=? WHERE owner=? AND id=?',('PAUSED' if action=='pause' else 'ACTIVE','{}',self.owner,alert_id))
    def process(self,alert_id,context,boot):
        with closing(connect(self.database)) as db,db:
            db.execute('BEGIN IMMEDIATE');r=db.execute('SELECT * FROM app_price_alerts WHERE owner=? AND id=?',(self.owner,alert_id)).fetchone()
            if not r or r['state']!='ACTIVE':return
            d=json.loads(r['body']);state=json.loads(r['checkpoint']);now=self.clock()
            if d['expires_at'] is not None and now>=d['expires_at']:
                db.execute("UPDATE app_price_alerts SET state='EXPIRED' WHERE owner=? AND id=?",(self.owner,alert_id));return
            def store():db.execute('UPDATE app_price_alerts SET checkpoint=? WHERE owner=? AND id=?',(json.dumps(state),self.owner,alert_id))
            if d.get('schema')=='technical-alert/4':
                decision=intrabar_step(d,(context or {}).get('_source_contexts',{}),state,boot)
                if decision:
                    event_id=hashlib.sha256(json.dumps([self.owner,alert_id,r['revision'],decision['token']],separators=(',',':')).encode()).hexdigest()
                    event=dict(id=event_id,alert_id=alert_id,revision=r['revision'],name=d['name'],symbol=d['symbol'],interval=d['interval'],operator='compound',level='',definition=d,created_at=now,message=d['message'],delivery='LOCAL_HISTORY',order_authority=False,evaluation='intrabar',**decision)
                    db.execute('INSERT OR IGNORE INTO app_price_alert_events VALUES (?,?,?,?,?)',(self.owner,event_id,alert_id,now,json.dumps(event)))
                    if d['frequency']=='once':db.execute("UPDATE app_price_alerts SET state='TRIGGERED' WHERE owner=? AND id=?",(self.owner,alert_id))
                store();return
            if d.get('schema')=='technical-alert/3':context=align(d,(context or {}).get('_source_contexts',{}))
            if context and context.get('_alignment_wait'):
                state.update(readiness='WAITING_ALIGNMENT');store();return
            c=context or {};ident=c.get('identity',{});rows=c.get('rows',[])
            valid=(c.get('transport_state')=='LIVE' and c.get('timing',{}).get('state')=='FRESH' and c.get('quality',{}).get('state')=='OK' and ident==dict(source=SOURCE,environment='live_public',product='USD-M',price_type='LAST_PRICE',symbol=d['symbol'],interval=d['interval']))
            closed=[x for x in rows if x.get('closed')]
            try:
                if len(closed)<2:valid=False
                for x in closed:
                    if x.get('exact',{}).get('state')!='VERIFIED' or not Decimal(x['exact']['close']).is_finite() or Decimal(x['exact']['close'])<=0:valid=False
                if any(y['time']-x['time']!=INTERVALS[d['interval']]//1000 for x,y in zip(closed,closed[1:])):valid=False
            except (KeyError,ValueError,TypeError,ArithmeticError):valid=False
            if not valid:state.update(readiness='WAITING_DATA',reseed=True);store();return
            latest=closed[-1]['time'];epoch=c.get('stream_epoch')
            if not epoch:state.update(readiness='WAITING_DATA',reseed=True);store();return
            if state.get('boot')!=boot or state.get('epoch')!=epoch or state.get('reseed'):
                readiness='READY'
                if d.get('schema') in ('technical-alert/2','technical-alert/3'):
                    try:evaluate_all(d,closed,c.get('_aligned_rows'))
                    except (ValueError,TypeError,KeyError,ArithmeticError):readiness='WAITING_CALCULATION'
                state.update(boot=boot,epoch=epoch,last_time=latest,reseed=False,readiness=readiness);store();return
            if latest<=state['last_time']:store();return
            state['readiness']='READY'
            if latest-state['last_time']!=INTERVALS[d['interval']]//1000:
                state['last_time']=latest;store();return
            old,cur=closed[-2:];checks=None
            if d.get('schema') in ('technical-alert/2','technical-alert/3'):
                try:hit,checks=evaluate_all(d,closed,c.get('_aligned_rows'))
                except (ValueError,TypeError,KeyError,ArithmeticError):
                    state.update(readiness='WAITING_CALCULATION',last_time=latest);store();return
            else:
                a,b=Decimal(old['exact']['close']),Decimal(cur['exact']['close']);level=Decimal(d['price'])
                hit={'cross':a<level<=b or a>level>=b,'cross_up':a<level<=b,'cross_down':a>level>=b,'above':b>level,'below':b<level}[d['operator']]
            state['last_time']=latest
            if hit:
                event_id=hashlib.sha256(json.dumps([self.owner,alert_id,r['revision'],latest],separators=(',',':')).encode()).hexdigest()
                event=dict(id=event_id,alert_id=alert_id,revision=r['revision'],name=d['name'],symbol=d['symbol'],interval=d['interval'],operator=d.get('operator','compound'),level=d.get('price',''),conditions=checks,definition=d,source_closes={k:v[-1]['time'] for k,v in c.get('_aligned_rows',{}).items()},close=cur['exact']['close'],candle_time=latest,created_at=now,message=d['message'],delivery='LOCAL_HISTORY',order_authority=False)
                db.execute('INSERT OR IGNORE INTO app_price_alert_events VALUES (?,?,?,?,?)',(self.owner,event_id,alert_id,now,json.dumps(event)))
                if d['frequency']=='once':db.execute("UPDATE app_price_alerts SET state='TRIGGERED' WHERE owner=? AND id=?",(self.owner,alert_id))
            store()

class PriceAlertWorker:
    def __init__(self,service,hub):self.service,self.hub=service,hub;self.stop=threading.Event();self.feeds={};self.boot=uuid.uuid4().hex;self.thread=None;self.error=None
    def start(self):
        self.thread=threading.Thread(target=self.run,name='price-alerts',daemon=True);self.thread.start()
    def tick(self):
        items=self.service.list();keys={(x['definition']['symbol'],period) for x in items for period in intervals(x['definition']) if x['state']=='ACTIVE' and (x['definition']['expires_at'] is None or x['definition']['expires_at']>self.service.clock())}
        for key in list(self.feeds):
            if key not in keys:self.hub.release(self.feeds.pop(key))
        for key in keys:
            if key not in self.feeds:
                try:self.feeds[key]=self.hub.acquire(*key)
                except Exception:pass
        for item in items:
            if item['state']=='ACTIVE':
                d=item['definition'];context={'_source_contexts':{i:self.hub.binding_context(d['symbol'],i) for i in intervals(d)}} if d.get('schema') in ('technical-alert/3','technical-alert/4') else self.hub.binding_context(d['symbol'],d['interval']);self.service.process(item['id'],context,self.boot)
    def run(self):
        while not self.stop.is_set():
            try:self.tick()
            except Exception:
                self.error='ALERT_WORKER_ERROR';logging.getLogger(__name__).exception('Price alert worker cycle failed')
            else:self.error=None
            self.stop.wait(1)
    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=15)
        for f in self.feeds.values():self.hub.release(f)
        self.feeds.clear()
