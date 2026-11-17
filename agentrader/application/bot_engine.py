"""Terminal adapter for the existing demo plan/command engines; one OS writer lock."""
import hashlib
import json
import secrets
import re
import sqlite3
import time
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .bot_inbox import BotError,checksum,encoded
from agentrader.bot.plans import PlanService,digest,transaction
from agentrader.bot.risk import RiskLimits,number
from agentrader.bot.exchange_commands import ExchangeCommands,OPERATIONS
from agentrader.bot.account_runtime import plan_runner,compile_plan,monitor_account,runner_for
from agentrader.shared.state import StateStore
from agentrader.shared.product_registry import EXECUTION_CONTEXT


def verified_store(path):
    try:
        return StateStore(path)
    except ValueError as exc:
        # StateStore's shared context gate runs before schema/namespace writes.
        raise BotError(str(exc), 409) from None


def make_plan(draft,identity,now):
    from agentrader.bot.plan_v2 import validate_v2
    if not isinstance(draft,dict) or set(draft)-set('symbol side kind entry stop target amount grid options execution orderType sizing targets breakEven response trailing source'.split()):raise BotError('INVALID_TERMINAL_DRAFT')
    strategy={'SINGLE':'SINGLE','GRID':'GRID','NEUTRAL':'NEUTRAL_GRID'}.get(draft.get('kind'))
    if not strategy:raise BotError('INVALID_PLAN_KIND')
    e=draft.get('execution') or dict(leverage='3',margin='ISOLATED',positionMode='hedge',condition='IMMEDIATE',trigger='90000',driftBps='50')
    if not isinstance(e,dict):raise BotError('INVALID_EXECUTION')
    if not isinstance(e.get('leverage'),str) or not re.fullmatch('[0-9]+',e['leverage']):raise BotError('INVALID_LEVERAGE')
    single=strategy=='SINGLE';neutral=strategy=='NEUTRAL_GRID'
    order=draft.get('orderType','LIMIT')
    if order not in ('MARKET','LIMIT'):raise BotError('INVALID_ORDER_TYPE')
    condition='LIMIT' if single and order=='LIMIT' else e['condition']
    entry=dict(condition=condition,reference_price=draft['entry'],trigger_price=draft['entry'] if condition=='LIMIT' else None if condition=='IMMEDIATE' else e['trigger'],max_drift_bps=e['driftBps'])
    if single and draft.get('response'):entry['order_response_type']=draft['response']
    if single and condition=='LIMIT' and draft.get('options'):
        o=draft['options'];opts={'time_in_force':o['tif']}
        if o.get('stp'):opts['self_trade_prevention_mode']=o['stp']
        if o.get('priceMatch'):opts['price_match']=o['priceMatch']
        if o['tif']=='GTD':
            # Browser sends an unambiguous UTC epoch, never a server-local datetime.
            if type(o.get('expires_ms')) is not int:raise BotError('GTD_UTC_REQUIRED')
            opts['good_till_date']=o['expires_ms']
        entry['order_options']=opts
    elif single and order=='MARKET' and draft.get('options'):raise BotError('MARKET_LIMIT_OPTIONS_FORBIDDEN')
    g=draft.get('grid') or {}
    targets=[] if neutral else [{'price':t['price'],'fraction':str(number(t['percent'])/100)} for t in (draft.get('targets') or [dict(price=draft['target'],percent='100')])] if single else [dict(price=draft['target'],fraction='1')]
    if draft.get('breakEven') and (not isinstance(draft['breakEven'],str) or not re.fullmatch('[0-9]+',draft['breakEven'])):raise BotError('INVALID_BREAK_EVEN')
    if not single and (not isinstance(g.get('intervals'),str) or not re.fullmatch('[0-9]+',g['intervals'])):raise BotError('INVALID_GRID_INTERVALS')
    management=dict(break_even_after_target=int(draft['breakEven']) if single and draft.get('breakEven') else None,
                    allow_scale_in=not single,allow_reverse=False,allow_reentry=not single)
    if draft.get('trailing'):
        t=draft['trailing'];management['trailing']=dict(activation_price=t['activation'],distance_bps=t['distance'],min_step_bps=t['step'])
        if not single:management['trailing']['native_stop']=t.get('nativeStop',False)
        elif t.get('nativeStop'):raise BotError('NATIVE_GRID_STOP_ONLY')
    # datetime rounds fractional timestamps to microseconds. On a coarse clock
    # that can put created_at just ahead of the next unchanged time.time read.
    def stamp(t):return datetime.fromtimestamp(int(t),timezone.utc).isoformat()
    plan=dict(schema_version=2,plan_id='web-'+checksum(identity)[:28],version=1,environment='demo',exchange='binance',product='USD-M',
              symbol=draft['symbol'],position_mode=e['positionMode'],direction='NEUTRAL' if neutral else {'Long':'LONG','Short':'SHORT'}[draft['side']],
              mode='A',created_at=stamp(now),expires_at=stamp(now+300),entry=entry,
              sizing=dict(kind=draft.get('sizing','NOTIONAL') if single else g['sizing'],amount=draft['amount'] if single else g['budget'],currency='USDT'),
              stop=dict(lower=draft['stop'],upper=g['upperStop']) if neutral else draft['stop'],targets=targets,management=management,max_runs=1,
              analysis_ref='web-terminal:'+checksum(identity)[:28],rationale='Authenticated manual terminal plan',
              execution=dict(strategy=strategy,leverage=int(e['leverage']),margin_mode=e['margin']))
    if not single:
        plan['grid']=dict(lower=g['lower'],upper=g['upper'],intervals=int(g['intervals']),spacing=g['spacing'])
        if neutral:plan['grid'].update(anchor_price=draft['entry'],long_fraction=str(number(g['longPercent'])/100),short_fraction=str(1-number(g['longPercent'])/100))
    return validate_v2(plan)


def fingerprint(compiled):
    return checksum({k:compiled[k] for k in ('quantity','entry','targets','protections','stop','slots','seed_quantity','notional_ceiling','exposures','compiled_digest') if k in compiled})


class BotEngine:
    def __init__(self,settings,exchange,store,limits,clock=time.time):
        self.settings,self.x,self.store,self.limits,self.clock=settings,exchange,store,limits,clock
        if not exchange.config.api_key or not exchange.config.api_secret:raise BotError('DEMO_CREDENTIALS_REQUIRED',503)
        self.plans=PlanService(store,settings.owner);self.commands=ExchangeCommands(exchange,store,settings.owner)
        self.account_ref=self.commands.account_ref

    def risk(self):return json.loads(encoded(asdict(self.limits)))

    def check_source(self,draft):
        source=draft.get('source')
        if not source:return
        from agentrader.chart.drawings.service import DrawingService
        item=DrawingService(self.settings.application_database,self.settings.owner).show(source['drawingId'])
        g=item['geometry']
        if (item['deleted'] or item['revision']!=source['revision'] or item['workspace_id']!=source['workspace'] or g['symbol']!=draft['symbol'] or
            g.get('schema')!='chart-position/1' or g['kind']!=('long_plan' if draft['side']=='Long' else 'short_plan') or
            [a['price'] for a in g['anchors']]!=[draft['entry'],draft['stop'],draft['target']]):raise BotError('CHART_SOURCE_CHANGED',409)

    def read(self,name,symbol=None):
        from agentrader.shared.query_routes import QUERIES,arguments
        from agentrader.bot.query_commands import _snapshot
        spec=QUERIES[name];scope={'symbol':symbol} if symbol else {'account_wide':True}
        params=arguments(spec,scope,{})
        return _snapshot(spec,self.x.get(spec['path'],params),scope,name,params)

    def snapshot(self,symbol):
        started=self.clock()
        self.x.sync_time();account=self.read('ACCOUNT_V3');positions=self.read('POSITIONS_V3');orders=self.read('OPEN_ORDERS');algos=self.read('OPEN_ALGO_ORDERS')
        if not 0<=self.clock()-started<=15:raise BotError('ACCOUNT_SNAPSHOT_STALE')
        sessions=[]
        for s in self.store.sessions():
            ref=s.get('plan_ref',{});row=self.plans.show(ref['plan_id'],ref['version'])
            if row['owner']!=self.settings.owner or s.get('account_ref')!=self.account_ref or row['digest']!=ref.get('digest'):raise BotError('SESSION_OWNERSHIP_UNVERIFIED')
            health=self.store.db.execute('SELECT value FROM control WHERE name=?',('runtime_health:'+s['id'],)).fetchone()
            paused=bool(self.store.db.execute('SELECT 1 FROM control WHERE name=?',('bot_monitor_paused:'+s['id'],)).fetchone())
            sessions.append(dict(session_id=s['id'],symbol=s['symbol'],engine=s.get('engine'),state=s.get('status'),plan_ref=ref,plan=row['plan'],monitor_paused=paused,runtime_health=json.loads(health[0]) if health else None))
        plan_rows=self.store.db.execute('SELECT plan_id,version FROM plan_versions WHERE owner=? ORDER BY rowid DESC LIMIT 100',(self.settings.owner,)).fetchall()
        plans=[self.plans.show(r[0],r[1]) for r in plan_rows]
        return dict(environment='demo',product='USD-M',account_ref=self.account_ref,observed_at=started,atomic_snapshot=False,symbol=symbol,
                    account=account,positions=positions,orders=orders,algo_orders=algos,sessions=sessions,plans=plans,
                    commands=self.commands.list()['commands'],entry_halted=bool(self.store.halt_reason()),risk_limits=self.risk())

    def review(self,kind,payload,data):
        result=dict(kind=kind,account_ref=self.account_ref,expires_at=self.clock()+60,payload=payload,data=data,risk_limits=self.risk())
        return result|{'review_digest':checksum(result)}

    def save_plan(self,draft,jid):
        self.check_source(draft);plan=make_plan(draft,jid,self.clock())
        self.plans.create(plan,self.settings.owner)
        return self.plans.show(plan['plan_id'],plan['version'])

    def prepare_plan(self,draft,jid,authorize_only=False):
        self.check_source(draft);plan=make_plan(draft,jid,self.clock())
        runner=plan_runner(self.plans,self.x,self.limits,plan);compiled=compile_plan(plan,runner._snapshot(plan['symbol']),self.limits)
        self.plans.create(plan,self.settings.owner)  # plaintext local approval token is intentionally discarded
        return self.review('PLAN',dict(plan_id=plan['plan_id'],version=1,plan_digest=digest(plan),draft=draft,authorize_only=authorize_only),dict(plan=plan,preflight=compiled,fingerprint=fingerprint(compiled)))

    def prepare_command(self,p,jid):
        op=p['operation']
        if op not in OPERATIONS or op in ('EXECUTE_V1_PLAN','RUN_SINGLE_PLAN'):raise BotError('UNSUPPORTED_WEB_OPERATION')
        params=dict(p['parameters'])
        if op in ('INCREASE_POSITION','REVERSE_POSITION','BATCH_CREATE_ORDERS'):params['risk_limits']=self.risk()
        if op=='BATCH_CREATE_ORDERS':
            refs=[]
            for ref in params['plans']:
                row=self.plans.show(ref['plan_id'],ref['version'])
                if row['digest']!=ref['plan_digest']:raise BotError('PLAN_REFERENCE_CHANGED')
                refs.append(dict(ref,entry_options=row['plan']['entry'].get('order_options',{})))
            params['plans']=refs
        request=dict(schema_version=1,client_command_id=jid,environment='demo',exchange='binance',product='USD-M',account_ref=self.account_ref,operation=op,scope=p['scope'],parameters=params)
        prepared=self.commands.prepare(request,ttl=120)
        return self.review('COMMAND',dict(command_id=prepared['command_id'],digest=prepared['digest']),prepared)

    def owned_session(self,sid):
        s=next((s for s in self.store.sessions() if s['id']==sid),None)
        if not s:raise BotError('SESSION_NOT_ACTIVE')
        ref=s['plan_ref'];row=self.plans.show(ref['plan_id'],ref['version'])
        if row['digest']!=ref['digest'] or s.get('account_ref')!=self.account_ref:raise BotError('SESSION_OWNERSHIP_UNVERIFIED')
        return s

    def confirm(self,inbox,p,execute):
        if not execute:raise BotError('BOT_WORKER_READ_ONLY',409)
        job=inbox.row(p['review_id']);r=json.loads(job['result']) if job['result'] else None
        if job['state']!='SUCCEEDED' or job['action'] not in ('PREVIEW_PLAN','PREVIEW_PLAN_AUTHORIZATION','PREVIEW_COMMAND','PREVIEW_CONTROL') or not r:raise BotError('REVIEW_NOT_READY')
        core={k:v for k,v in r.items() if k!='review_digest'}
        if r['review_digest']!=checksum(core) or p['review_digest']!=r['review_digest'] or p['account_ref']!=self.account_ref or r['account_ref']!=self.account_ref:raise BotError('REVIEW_SCOPE_CHANGED',409)
        if self.clock()>=r['expires_at'] or r['risk_limits']!=self.risk():raise BotError('REVIEW_EXPIRED_OR_RISK_CHANGED',409)
        payload=r['payload']
        if r['kind']=='COMMAND':return self.commands.apply(payload['command_id'],payload['digest'],execute=True)
        if r['kind']=='CONTROL':
            s=self.owned_session(payload['session_id'])
            if payload['kind']=='RESUME_MONITOR':
                from .bot_worker import uncertain_financial
                if uncertain_financial(self.store):raise BotError('MONITOR_UNCERTAIN_MUTATION',409)
                runner=runner_for(self.plans,self.x,self.limits,s)
                from agentrader.shared.runtime import monitor_session
                baseline=next(monitor_session(runner,s['id'],execute=False,iterations=1))
                if baseline.get('service_stopped') or baseline['state'] in ('SESSION_REVIEW_REQUIRED','CLOSED'):
                    raise BotError('MONITOR_RECONCILIATION_REQUIRED',409)
                with self.store.db:
                    self.store.db.execute('DELETE FROM control WHERE name IN (?,?)',('bot_monitor_paused:'+s['id'],'bot_monitor_retry:'+s['id']))
                return dict(state='MONITOR_RESUMED',session_id=s['id'],reconciled_state=baseline['state'],order_sent=False)
            if payload['kind']=='HALT_ENTRY':return self.plans.cancel(s['plan_ref']['plan_id'],s['plan_ref']['version'],self.settings.owner)
            return runner_for(self.plans,self.x,self.limits,s).stop(s['id'],close_position=payload['close_position'],execute=True)
        self.check_source(payload['draft'])
        row=self.plans.show(payload['plan_id'],payload['version']);plan=row['plan']
        if row['digest']!=payload['plan_digest'] or row['state']!='PENDING_APPROVAL':raise BotError('PLAN_AUTHORITY_CHANGED',409)
        runner=plan_runner(self.plans,self.x,self.limits,plan);compiled=compile_plan(plan,runner._snapshot(plan['symbol']),self.limits)
        if compiled['state']!='READY' or fingerprint(compiled)!=r['data']['fingerprint']:raise BotError('PLAN_PREFLIGHT_CHANGED',409)
        token=secrets.token_urlsafe(32)
        with transaction(self.store) as db:
            current=self.plans.row(db,plan['plan_id'],plan['version'])
            if current['state']!='PENDING_APPROVAL' or current['digest']!=row['digest']:raise BotError('PLAN_AUTHORITY_CHANGED',409)
            db.execute('UPDATE plan_versions SET token_hash=? WHERE plan_id=? AND version=?',(hashlib.sha256(token.encode()).hexdigest(),plan['plan_id'],plan['version']))
            self.plans.event(db,'authenticated_terminal_consent',dict(review_id=p['review_id'],review_digest=p['review_digest'],account_ref=self.account_ref))
        authorization=self.plans.authorize(plan['plan_id'],plan['version'],token,'approve',self.settings.owner,ttl=max(1,min(60,int(r['expires_at']-self.clock()))))
        if payload.get('authorize_only'):return authorization|{'plan_id':plan['plan_id'],'version':plan['version'],'order_sent':False}
        return runner.open(plan['plan_id'],plan['version'],execute=True)

    def perform(self,inbox,job,execute=False):
        p=json.loads(job['payload']);action=job['action']
        if action=='CONTEXT':
            return dict(account_ref=self.account_ref,environment='demo',product='USD-M',risk_limits=self.risk(),operations=[op for op in OPERATIONS if op not in ('EXECUTE_V1_PLAN','RUN_SINGLE_PLAN')])
        if action=='SNAPSHOT':return self.snapshot(p['symbol'])
        if action=='SAVE_PLAN':return self.save_plan(p['draft'],job['job_id'])
        if action=='PREVIEW_PLAN_AUTHORIZATION':return self.prepare_plan(p['draft'],job['job_id'],authorize_only=True)
        if action=='PREVIEW_PLAN':return self.prepare_plan(p['draft'],job['job_id'])
        if action=='PREVIEW_COMMAND':return self.prepare_command(p,job['job_id'])
        if action=='READ_COMMAND':
            if p['operation'] not in OPERATIONS or OPERATIONS[p['operation']]['mutates']:raise BotError('READ_ONLY_OPERATION_REQUIRED')
            r=self.prepare_command(p,job['job_id'])
            return self.commands.apply(r['payload']['command_id'],r['payload']['digest'],execute=False)
        if action=='CONFIRM':return self.confirm(inbox,p,execute)
        if action=='RECONCILE':return self.commands.reconcile(p['command_id'])
        if action=='PREVIEW_CONTROL':
            if p['kind'] not in ('HALT_ENTRY','STOP_GRID','RESUME_MONITOR') or type(p['close_position']) is not bool:raise BotError('INVALID_CONTROL')
            s=self.owned_session(p['session_id'])
            if p['kind']=='STOP_GRID' and s.get('engine') not in ('grid-v2','neutral-v2'):raise BotError('GRID_SESSION_REQUIRED')
            return self.review('CONTROL',p,dict(session_id=s['id'],symbol=s['symbol'],engine=s.get('engine'),state=s.get('status')))
        raise BotError('INVALID_BOT_JOB')
