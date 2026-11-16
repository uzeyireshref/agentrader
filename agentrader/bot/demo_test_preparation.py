"""Technical acceptance candidates only. Never imports/approves a plan or clears halt."""
from dataclasses import asdict
from datetime import datetime,timedelta,timezone
from decimal import Decimal,ROUND_CEILING,ROUND_FLOOR
import hashlib
import re
import time

from agentrader.application.queries import execution_status
from agentrader.chart.chart_bindings import binding_hash
from agentrader.integration.chart_execution import require_demo_acceptance
from agentrader.bot.execution import TERMINAL
from agentrader.bot.order_rules import validate_order
from agentrader.bot.plan_v2 import validate_v2
from agentrader.integration.preview_preflight import ReadOnlyDemoAccount
from agentrader.bot.recovery_guardian import status
from agentrader.bot.risk import number
from agentrader.bot.v2_preflight import collect_flat_snapshot,joint_step,prepare_single


def candidate(snapshot,limits,direction,*,clock=time.time):
    if direction not in ('LONG','SHORT'):raise ValueError('EXPLICIT_TEST_DIRECTION_REQUIRED')
    now=clock();info=snapshot['symbol_info'];mark=number(snapshot['mark']['markPrice']);filters={v['filterType']:v for v in info['filters']}
    tick=number(filters['PRICE_FILTER']['tickSize']);lot=filters['LOT_SIZE'];market=filters.get('MARKET_LOT_SIZE',lot)
    step=joint_step(lot['stepSize'],market['stepSize']);sign=1 if direction=='LONG' else -1
    snap=lambda value,up=False:(value/tick).to_integral_value(rounding=ROUND_CEILING if up else ROUND_FLOOR)*tick
    entry=snap(mark*(1-Decimal('.0025')*sign),direction=='SHORT')
    stop=snap(entry*(1-Decimal('.01')*sign),direction=='SHORT')
    target=snap(mark*(1+Decimal('.01')*sign),direction=='LONG')
    q=(max(number(lot['minQty']),number(market['minQty']),number(filters['MIN_NOTIONAL']['notional'])/entry)/step).to_integral_value(rounding=ROUND_CEILING)*step
    budget=(q*max(entry,mark)*Decimal('1.005')/Decimal('.01')).to_integral_value(rounding=ROUND_CEILING)*Decimal('.01')
    inputs=dict(direction=direction,entry_price=str(entry),stop=str(stop),target=str(target),notional=str(budget),leverage=int(snapshot['settings']['leverage']),
                margin_mode=snapshot['settings']['marginType'],position_mode=snapshot['position_mode'],max_drift_bps='50',ttl_seconds=120)
    stamp=lambda value:datetime.fromtimestamp(value,timezone.utc).isoformat()
    plan=dict(schema_version=2,plan_id='technical-demo-candidate',version=1,environment='demo',exchange='binance',product='USD-M',symbol=info['symbol'],
              position_mode=inputs['position_mode'],direction=direction,mode='A',created_at=stamp(now),expires_at=stamp(now+120),
              execution=dict(strategy='SINGLE',leverage=inputs['leverage'],margin_mode=inputs['margin_mode']),
              entry=dict(condition='LIMIT',reference_price=str(entry),trigger_price=str(entry),max_drift_bps='50'),sizing=dict(kind='NOTIONAL',amount=str(budget),currency='USDT'),
              stop=str(stop),targets=[dict(price=str(target),fraction='1')],management=dict(break_even_after_target=None,allow_scale_in=False,allow_reverse=False,allow_reentry=False),max_runs=1,
              analysis_ref='technical-acceptance-candidate-only',rationale='Yalnız teknik LIMIT/iptal kabul taslağı; yatırım sinyali, kayıtlı plan veya işlem onayı değildir.')
    validate_v2(plan)
    ps='BOTH' if inputs['position_mode']=='one-way' else direction
    validate_order(dict(symbol=info['symbol'],side='BUY' if sign==1 else 'SELL',positionSide=ps,type='LIMIT',quantity=str(q),price=str(entry),timeInForce='GTC'),info,inputs['position_mode'],'OPEN',str(mark),snapshot['now_ms'])
    blockers=[]
    if budget>limits.max_notional:blockers.append('MINIMUM_VALID_ORDER_EXCEEDS_NOTIONAL_CAP')
    if number(snapshot['daily_loss'])>limits.max_daily_loss:blockers.append('DAILY_LOSS_LIMIT_EXCEEDED')
    prepared=None
    if not blockers:
        try:prepared=prepare_single(plan,snapshot,limits,now=now)
        except ValueError:blockers.append('ACCOUNT_RISK_PREFLIGHT_REJECTED')
    # Export only inputs, never a plan v2 file that can bypass fresh chart binding.
    return dict(schema='demo-test-candidate/1',symbol=info['symbol'],purpose='LIMIT_PENDING_CANCEL_ACCEPTANCE',inputs=inputs,minimum_quantity=str(q),
                budget_usdt=str(budget),fill_possible=True,state='BLOCKED' if blockers else 'DRAFT_ONLY',blockers=blockers,
                preflight_state=prepared['state'] if prepared else 'NOT_ELIGIBLE',quantity=prepared.get('quantity') if prepared else None,
                required_flow=['FRESH_DEMO_SHADOW_EVENT','EXPLICIT_PREVIEW_PARAMETERS','ACCOUNT_REVIEW','PLAN_SPECIFIC_APPROVAL','INDEPENDENT_GUARDIAN'],
                order_authority=False,execution_authorized=False)


def prepare(settings,exchange,limits,symbol,direction,*,clock=time.time,collector=collect_flat_snapshot,
            local_observer=execution_status,continuity=require_demo_acceptance,guardian_observer=status):
    if not isinstance(symbol,str) or not re.fullmatch('[A-Z0-9]{2,20}USDT',symbol) or direction not in ('LONG','SHORT'):
        raise ValueError('EXPLICIT_TEST_CONTEXT_REQUIRED')
    r=dict(schema='demo-test-preparation/1',observed_at=clock(),environment='demo',symbol=symbol,state='BLOCKED',blockers=[],order_requests=0,
           settings_changes=0,halt_cleared=False,halt_release_eligible=False,execution_authorized=False)
    try:
        if not continuity():raise ValueError()
        r['continuity_accepted']=True
    except Exception:r['blockers'].append('DEMO_CONTINUITY_ACCEPTANCE_REQUIRED')
    try:
        r['local']=local_observer(settings.execution_database,settings.owner)
        if r['local']['storage'] not in ('AVAILABLE','NOT_INITIALIZED') or r['local'].get('active_sessions'):
            r['blockers'].append('LOCAL_RUNTIME_NOT_IDLE')
        if any(count for state,count in r['local'].get('intent_counts',{}).items() if state not in TERMINAL):
            r['blockers'].append('LOCAL_HISTORY_RECONCILIATION_REQUIRED')
        snapshot=collector(ReadOnlyDemoAccount(exchange),symbol,limits)
        if snapshot['symbol_info']['symbol']!=symbol or snapshot['mark']['symbol']!=symbol:raise ValueError('SYMBOL_MISMATCH')
        r['account_ref']=hashlib.sha256(exchange.config.api_key.encode()).hexdigest()
        r['daily_loss']=snapshot['daily_loss'];r['max_daily_loss']=str(limits.max_daily_loss);r['verified_usdt_collateral']=snapshot['collateral']
        r['account_settings']=snapshot['settings'];r['position_mode']=snapshot['position_mode'];r['mark_price']=snapshot['mark']['markPrice']
        server_now=datetime.fromtimestamp(snapshot['now_ms']/1000,timezone.utc)
        r['next_utc_day_check_at']=(server_now.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)).isoformat()
        r['candidate']=candidate(snapshot,limits,direction,clock=clock)
        r['blockers']+=r['candidate']['blockers']
        r['risk_profile_hash']=binding_hash({k:str(v) for k,v in asdict(limits).items()})
        r['state']='BLOCKED' if r['blockers'] else 'DRAFT_READY_FOR_REVIEW'
    except Exception:r['blockers'].append('ACCOUNT_OR_SYMBOL_PREPARATION_FAILED')
    try:r['guardian']=guardian_observer(settings.execution_database)
    except Exception:r['guardian']=dict(state='UNAVAILABLE',entry_ready=False)
    return r


def local_prepare(settings,symbol,direction):
    from agentrader.shared.config import Config
    from agentrader.shared.exchange import DemoExchange
    from agentrader.shared.locking import execution_lock
    from agentrader.bot.risk import RiskLimits
    with execution_lock():return prepare(settings,DemoExchange(Config.load()),RiskLimits.load('risk-demo.json'),symbol,direction)
