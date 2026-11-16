"""Revision-bound plan v2 drafts in the application DB. Never imports PlanService or a writer."""
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
import json, re, time

from agentrader.chart.binding_catalog import catalog
from agentrader.chart.binding_eligibility import evaluate_binding
from agentrader.chart.chart_bindings import BindingService, binding_hash
from agentrader.chart.chart_clock import POLICY
from agentrader.chart.chart_evidence import canonical
from agentrader.chart.chart_precision import decimal_text
from agentrader.chart.drawings.service import DrawingError, DrawingConflict, DrawingNotFound, identifier
from agentrader.chart.local_chart_events import target_view, closed_candidate
from agentrader.shared.market_data import PublicMarket
from agentrader.shared.market_environment import SOURCE, ENVIRONMENT
from agentrader.migrations import connect
from agentrader.bot.order_rules import validate_order
from agentrader.bot.plan_v2 import validate_v2
from agentrader.bot.risk import RiskLimits, number
from agentrader.integration.shadow_tracking import PROFILE
from agentrader.bot.v2_preflight import joint_step

EVENT_TTL = 300
FIELDS = {'direction','entry_price','stop','target','notional','leverage','margin_mode','position_mode','max_drift_bps','ttl_seconds'}


class PreviewError(DrawingError):
    def __init__(self, reason):self.code=reason;super().__init__(reason)


def parameters(value):
    if not isinstance(value,dict) or set(value)!=FIELDS:raise PreviewError('INVALID_PREVIEW_PARAMETERS')
    if value['direction'] not in ('LONG','SHORT') or value['position_mode'] not in ('one-way','hedge') or value['margin_mode'] not in ('ISOLATED','CROSSED'):
        raise PreviewError('INVALID_PREVIEW_PARAMETERS')
    if type(value['leverage']) is not int or value['leverage']<1 or type(value['ttl_seconds']) is not int or not 30<=value['ttl_seconds']<=300:
        raise PreviewError('INVALID_PREVIEW_PARAMETERS')
    result=dict(value)
    try:
        for k in ('entry_price','stop','target','notional','max_drift_bps'):
            if not isinstance(value[k],str):raise ValueError()
            result[k]=decimal_text(value[k],positive=True)
        if number(result['max_drift_bps'])>100:raise ValueError()
        direction=1 if result['direction']=='LONG' else -1
        if direction*(number(result['entry_price'])-number(result['stop']))<=0 or direction*(number(result['target'])-number(result['entry_price']))<=0:raise ValueError()
    except ValueError:raise PreviewError('INVALID_PREVIEW_PRICES_OR_BUDGET') from None
    return result


class SignalPreviews:
    def __init__(self,database,owner,hub,*,public_factory=PublicMarket,limits=None,clock=time.time,monotonic=time.monotonic):
        self.database,self.owner,self.hub=database,owner,hub
        self.public_factory,self.fixed_limits=public_factory,limits
        self.clock,self.monotonic=clock,monotonic
        self.bindings=BindingService(database,owner)

    def limits(self):
        try:return self.fixed_limits or RiskLimits.load('risk-demo.json')
        except (OSError,ValueError):raise PreviewError('PREVIEW_RISK_PROFILE_UNAVAILABLE') from None

    def _event(self,db,workspace,event_id):
        row=db.execute('SELECT * FROM app_shadow_events WHERE owner=? AND workspace_id=? AND event_id=?',(self.owner,workspace,event_id)).fetchone()
        if row is None:raise DrawingNotFound()
        event=json.loads(row['body']);evidence=json.loads(row['evidence'])
        b=self.bindings._view_binding(self.bindings._binding(db,workspace,row['binding_id']),True)
        if b['revision']!=row['binding_revision'] or b['state']!='DISABLED' or event.get('definition_hash')!=b['definition_hash'] or target_view(self.bindings,db,b) is None:
            raise PreviewError('PREVIEW_REVISION_CHANGED')
        identity=binding_hash(dict(profile=PROFILE,owner=self.owner,workspace=workspace,binding_id=b['binding_id'],revision=b['revision'],definition_hash=b['definition_hash'],candle_time=event['candle_time'],kind=event['kind']))
        if (identity!=event_id or event.get('event_id')!=event_id or event.get('profile')!=PROFILE
                or event.get('order_authority') is not False or event.get('evidence_hash')!=binding_hash(evidence['context'])
                or binding_hash(evidence['definition'])!=b['definition_hash']):raise PreviewError('PREVIEW_EVENT_INTEGRITY_FAILED')
        candidate=closed_candidate(b,evidence['context'])
        if not candidate or any(candidate[k]!=event[k] for k in candidate if k not in ('schema','profile')):raise PreviewError('PREVIEW_EVENT_INTEGRITY_FAILED')
        if not 0<=self.clock()-row['created_at']<=EVENT_TTL:raise PreviewError('PREVIEW_EVENT_EXPIRED')
        run=db.execute('SELECT expires_at FROM app_shadow_runs WHERE owner=? AND workspace_id=? AND binding_id=? AND binding_revision=?',(self.owner,workspace,b['binding_id'],b['revision'])).fetchone()
        if run is None or run['expires_at']<=self.clock():raise PreviewError('PREVIEW_TRACKING_EXPIRED')
        return row,event,b,min(row['created_at']+EVENT_TTL,run['expires_at'])

    def _context(self,db,b):
        m=b['definition']['market'];c=self.hub.binding_context(m['symbol'],m['interval'])
        result=evaluate_binding(b,owner=self.owner,workspace_id=b['workspace_id'],target=target_view(self.bindings,db,b),context=c,traceability=catalog())
        if result['state']!='EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY':raise PreviewError('PREVIEW_DATA_NOT_FRESH')
        return c

    def show(self,workspace,event_id,version=0):
        identifier(workspace)
        if not isinstance(event_id,str) or not re.fullmatch('[a-f0-9]{64}',event_id) or type(version) is not int or version<0:raise PreviewError('INVALID_PREVIEW_REFERENCE')
        with closing(connect(self.database)) as db:
            db.execute('BEGIN')
            head=db.execute('SELECT version FROM app_signal_preview_heads WHERE owner=? AND event_id=?',(self.owner,event_id)).fetchone()
            if head is None:raise DrawingNotFound()
            row=db.execute('SELECT body FROM app_signal_previews WHERE owner=? AND workspace_id=? AND event_id=? AND version=?',(self.owner,workspace,event_id,version or head[0])).fetchone()
            if row is None:raise DrawingNotFound()
            body=json.loads(row[0]);state='PREVIEW_ONLY';reasons=[];current=None
            if body['version']!=head[0]:state='SUPERSEDED';reasons.append('NEWER_PREVIEW_VERSION')
            try:
                _,event,b,_=self._event(db,workspace,event_id)
                current=self._context(db,b)
                if body['risk_profile_hash']!=binding_hash({k:str(v) for k,v in asdict(self.limits()).items()}):raise PreviewError('PREVIEW_RISK_PROFILE_CHANGED')
            except (PreviewError,DrawingNotFound) as exc:
                state='INVALIDATED' if 'REVISION' in exc.code or 'INTEGRITY' in exc.code or 'PROFILE' in exc.code else 'BLOCKED'
                reasons.append(exc.code)
            if body.get('content_hash')!=binding_hash({k:v for k,v in body.items() if k!='content_hash'}):state='INVALIDATED';reasons.append('PREVIEW_CONTENT_INTEGRITY')
            if body['plan_digest']!=binding_hash(body['plan']) or body['parameters_hash']!=binding_hash(body['parameters']):state='INVALIDATED';reasons.append('PREVIEW_CONTENT_INTEGRITY')
            if self.clock()>=body['expires_at']:state='EXPIRED';reasons.append('PREVIEW_TTL_EXPIRED')
            return {**body,'state':state,'reasons':reasons,'current_last_price':current['rows'][-1]['exact']['close'] if current else None,'execution_eligible':False,'order_authority':False,'approval_state':'NOT_REQUESTED'}

    def create(self,workspace,event_id,expected_version,inputs):
        identifier(workspace)
        if not isinstance(event_id,str) or not re.fullmatch('[a-f0-9]{64}',event_id) or type(expected_version) is not int or expected_version<0:raise PreviewError('INVALID_PREVIEW_REFERENCE')
        p=parameters(inputs);ph=binding_hash(p);limits=self.limits()
        # Snapshot only public demo symbol/mark data, never an account or executor.
        with closing(connect(self.database)) as db:
            row,event,b,deadline=self._event(db,workspace,event_id);self._context(db,b)
            head=db.execute('SELECT version FROM app_signal_preview_heads WHERE owner=? AND event_id=?',(self.owner,event_id)).fetchone()
            if head:
                old=db.execute('SELECT parameters_hash FROM app_signal_previews WHERE owner=? AND event_id=? AND version=?',(self.owner,event_id,head[0])).fetchone()
                if old[0]==ph:return self.show(workspace,event_id)
        start=self.monotonic();wall=self.clock();public=self.public_factory()
        try:
            info=public.get('/fapi/v1/exchangeInfo')
            symbol=next(s for s in info['symbols'] if s['symbol']==b['definition']['market']['symbol'])
            mark=public.get('/fapi/v1/premiumIndex',{'symbol':symbol['symbol']})
            server=public.get('/fapi/v1/time')['serverTime']
            rules={f['filterType']:f for f in symbol['filters']}
            for kind,fields in (('PRICE_FILTER',('tickSize','minPrice','maxPrice')),('LOT_SIZE',('stepSize','minQty','maxQty')),('MIN_NOTIONAL',('notional',))):
                for name in fields:number(rules[kind][name])
            if number(rules['PRICE_FILTER']['tickSize'])<=0 or number(rules['LOT_SIZE']['stepSize'])<=0:raise ValueError()
            if symbol.get('quoteAsset')!='USDT' or symbol.get('contractType')!='PERPETUAL' or mark['symbol']!=symbol['symbol'] or type(mark.get('time')) is not int or type(server) is not int or not 0<=server-mark['time']<=limits.max_age_seconds*1000:raise ValueError()
        except Exception:raise PreviewError('PREVIEW_DEMO_SYMBOL_OR_QUOTE_UNAVAILABLE') from None
        with closing(connect(self.database)) as db,db:
            db.execute('BEGIN IMMEDIATE')
            row,event,b,deadline=self._event(db,workspace,event_id);context=self._context(db,b)
            elapsed=self.monotonic()-start
            if not 0<=elapsed<=limits.max_age_seconds or abs((self.clock()-wall)-elapsed)*1000>POLICY['wall_jump_ms']:raise PreviewError('PREVIEW_SNAPSHOT_EXPIRED')
            head=db.execute('SELECT version FROM app_signal_preview_heads WHERE owner=? AND event_id=?',(self.owner,event_id)).fetchone()
            old_version=head[0] if head else 0
            if head:
                old=db.execute('SELECT parameters_hash FROM app_signal_previews WHERE owner=? AND event_id=? AND version=?',(self.owner,event_id,old_version)).fetchone()
                if old[0]==ph:return self.show(workspace,event_id)
            if old_version!=expected_version:raise DrawingConflict()
            version=old_version+1;now=self.clock();expires=min(deadline,now+p['ttl_seconds'])
            if expires<=now:raise PreviewError('PREVIEW_EVENT_EXPIRED')
            entry,stop,target,amount=map(number,(p['entry_price'],p['stop'],p['target'],p['notional']))
            filters={f['filterType']:f for f in symbol['filters']};lot=filters['LOT_SIZE'];market_lot=filters.get('MARKET_LOT_SIZE',lot)
            step=joint_step(lot['stepSize'],market_lot['stepSize'])
            worst=entry*(1+number(p['max_drift_bps'])/10000)
            qty=(amount/worst/step).to_integral_value(rounding=ROUND_FLOOR)*step
            direction=1 if p['direction']=='LONG' else -1;ps='BOTH' if p['position_mode']=='one-way' else p['direction']
            try:
                validate_order(dict(symbol=symbol['symbol'],side='BUY' if direction==1 else 'SELL',positionSide=ps,type='LIMIT',quantity=str(qty),price=p['entry_price'],timeInForce='GTC'),symbol,p['position_mode'],'OPEN',mark['markPrice'],server)
                tick=number(filters['PRICE_FILTER']['tickSize'])
                if any(x%tick or not number(filters['PRICE_FILTER']['minPrice'])<=x<=number(filters['PRICE_FILTER']['maxPrice']) for x in (entry,stop,target)):raise ValueError()
                if not number(market_lot['minQty'])<=qty<=number(market_lot['maxQty']):raise ValueError()
            except ValueError:raise PreviewError('PREVIEW_SYMBOL_FILTER_REJECTED') from None
            fee=Decimal('.001');slip=Decimal('.0005')
            entry_fill=entry*(1+direction*slip);stop_fill=stop*(1-direction*slip);target_fill=target*(1-direction*slip)
            loss=qty*(direction*(entry_fill-stop_fill)+fee*(entry_fill+stop_fill))
            reward=qty*(direction*(target_fill-entry_fill)-fee*(entry_fill+target_fill))
            if amount>limits.max_notional or qty*worst>limits.max_notional or loss>limits.max_trade_loss:raise PreviewError('PREVIEW_INDEPENDENT_RISK_LIMIT')
            stamp=lambda t:datetime.fromtimestamp(t,timezone.utc).isoformat()
            plan=dict(schema_version=2,plan_id='shadow-'+event_id[:24],version=version,environment='demo',exchange='binance',product='USD-M',symbol=symbol['symbol'],position_mode=p['position_mode'],direction=p['direction'],mode='A',created_at=stamp(now),expires_at=stamp(expires),execution=dict(strategy='SINGLE',leverage=p['leverage'],margin_mode=p['margin_mode']),entry=dict(condition='LIMIT',reference_price=p['entry_price'],trigger_price=p['entry_price'],max_drift_bps=p['max_drift_bps']),sizing=dict(kind='NOTIONAL',amount=p['notional'],currency='USDT'),stop=p['stop'],targets=[dict(price=p['target'],fraction='1')],management=dict(break_even_after_target=None,allow_scale_in=False,allow_reverse=False,allow_reentry=False),max_runs=1,analysis_ref='shadow-event:'+event_id,rationale='Kullanıcının açık parametreleriyle gölge sinyalden oluşturulan önizleme; işlem onayı değildir.')
            validate_v2(plan)
            body=dict(schema='signal-preview/1',event_id=event_id,workspace_id=workspace,version=version,created_at=now,expires_at=expires,source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE',binding_id=b['binding_id'],binding_revision=b['revision'],definition_hash=b['definition_hash'],parameters=p,parameters_hash=ph,plan=plan,plan_digest=binding_hash(plan),risk_profile_hash=binding_hash({k:str(v) for k,v in asdict(limits).items()}),risk_limits={k:str(v) for k,v in asdict(limits).items()},estimates=dict(quantity=str(qty),notional=str(qty*entry),margin_with_fee_reserve=str(qty*worst/Decimal(p['leverage'])+qty*worst*fee*2),stop_loss_with_cost_reserve=str(loss),target_pnl_with_cost_reserve=str(reward),net_rr=str(reward/loss)),assumptions=dict(fee_rate=str(fee),slippage_bps='5',stop_trigger_price_type='MARK_PRICE',actual_account_fees='NOT_CHECKED'),warnings=['NON_POSITIVE_NET_REWARD'] if reward<=0 else [],account_preflight='NOT_CHECKED',unchecked=['available_balance','account_mode_and_leverage','portfolio_and_daily_loss','ownership','liquidation','execution_quote_revalidation','future_funding','actual_commission_and_slippage'],evidence=dict(event_hash=binding_hash(event),current_snapshot_hash=context['data_proof']['snapshot_hash'],symbol_filters_hash=binding_hash(symbol),demo_mark=mark,public_observed_at_ms=server),execution_eligible=False,order_authority=False,approval_state='NOT_REQUESTED')
            body['content_hash']=binding_hash(body)
            db.execute('INSERT INTO app_signal_previews VALUES (?,?,?,?,?,?)',(self.owner,workspace,event_id,version,ph,canonical(body)))
            db.execute('INSERT OR REPLACE INTO app_signal_preview_heads VALUES (?,?,?)',(self.owner,event_id,version))
        return self.show(workspace,event_id)
