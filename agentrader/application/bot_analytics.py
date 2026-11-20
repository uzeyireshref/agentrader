"""Read-only scenario pricing. Execution compilers remain the only order sizers."""
from agentrader.bot.risk import number
from decimal import Decimal, ROUND_FLOOR
from copy import deepcopy


def collect_snapshot(exchange,symbol,limits,clock):
    """Calculator inputs only: no order journal, ownership or daily-history gate."""
    from agentrader.bot.v2_preflight import read_many,fresh,collateral_usdt,usdt_eligibility
    from agentrader.bot.preflight_errors import PreflightRejection
    start=clock();exchange.sync_time()
    config,mode,account,settings,brackets,info=read_many(exchange,(
        ('/fapi/v1/accountConfig',None),('/fapi/v1/positionSide/dual',None),('/fapi/v3/account',None),
        ('/fapi/v1/symbolConfig',{'symbol':symbol}),('/fapi/v1/leverageBracket',{'symbol':symbol}),('/fapi/v1/exchangeInfo',None)))
    selected=[s for s in settings if s['symbol']==symbol]
    ladder=[brackets] if isinstance(brackets,dict) else brackets
    ladder=[b for b in ladder if b['symbol']==symbol]
    symbols=[s for s in info['symbols'] if s['symbol']==symbol]
    if len(selected)!=1 or len(ladder)!=1 or len(symbols)!=1:raise ValueError('Analysis metadata unavailable')
    if type(mode.get('dualSidePosition')) is not bool:raise ValueError('Analysis position mode unavailable')
    quotes=read_many(exchange,((('/fapi/v1/assetIndex',{'symbol':'USDTUSD'}),) if config.get('multiAssetsMargin') is True else ())+(('/fapi/v1/premiumIndex',{'symbol':symbol}),))
    mark=quotes[-1];index=quotes[0] if len(quotes)==2 else None;end=clock()
    fresh(mark,symbol,int(end*1000)+getattr(exchange,'offset_ms',0),limits.max_age_seconds)
    if number(mark['markPrice'])<=0:raise ValueError('Analysis mark must be positive')
    if index is not None:fresh(index,'USDTUSD',int(end*1000)+getattr(exchange,'offset_ms',0),limits.max_age_seconds)
    if not 0<=end-start<=limits.max_age_seconds:raise PreflightRejection('SNAPSHOT_STALE','Analysis collection expired')
    try:collateral=str(collateral_usdt(account,config,index,asset_eligibility=usdt_eligibility(info)))
    except (ValueError,KeyError,TypeError):collateral=None
    positions=account.get('positions')
    assets=[a for a in account.get('assets',[]) if a.get('asset')=='USDT']
    flat=(isinstance(positions,list) and all('positionAmt' in p and number(p['positionAmt'])==0 for p in positions)
          and len(assets)==1 and 'initialMargin' in assets[0] and number(assets[0]['initialMargin'])==0)
    return dict(symbol_info=symbols[0],settings=selected[0],brackets=ladder[0]['brackets'] if number(ladder[0].get('notionalCoef',1))==1 else [],
                mark=mark,collateral=collateral,position_mode='hedge' if mode['dualSidePosition'] else 'one-way',
                observed_at=start,finished_at=end,now_ms=int(end*1000)+getattr(exchange,'offset_ms',0),
                account_trade_enabled=config.get('canTrade') is True,account_flat=flat)


def scenario(plan,snapshot,limits):
    """A scenario is never execution eligibility, even when a compiler can price it."""
    from agentrader.bot.account_runtime import compile_plan
    from agentrader.bot.preflight_errors import PreflightRejection
    reasons=[]
    if snapshot['position_mode']!=plan['position_mode']:reasons.append('ACCOUNT_MODE_MISMATCH')
    if (int(snapshot['settings']['leverage'])!=plan['execution']['leverage'] or snapshot['settings']['marginType']!=plan['execution']['margin_mode']):reasons.append('ACCOUNT_SETTINGS_MISMATCH')
    if snapshot.get('account_trade_enabled') is False:reasons.append('ACCOUNT_NOT_ELIGIBLE')
    hypothetical=deepcopy(snapshot)
    hypothetical.update(flat_verified=True,position_mode=plan['position_mode'],daily_loss='0',collateral=snapshot.get('collateral') or '0')
    hypothetical['settings'].update(leverage=plan['execution']['leverage'],marginType=plan['execution']['margin_mode'])
    try:
        compiled=compile_plan(plan,hypothetical,limits)
        if compiled['state']!='READY':
            reasons.append('ENTRY_CONDITION_WAITING');result=indicative(plan,snapshot)
        else:result=summarize(plan,hypothetical,compiled)
    except ValueError as exc:
        reasons.append(exc.reason if isinstance(exc,PreflightRejection) else 'EXECUTION_CHECK_REQUIRED')
        result=indicative(plan,snapshot)
    reasons.extend(result.pop('scenario_warnings',[]))
    if plan['execution']['margin_mode']=='CROSSED' and not snapshot.get('account_flat',False):
        result['liquidation']=[];reasons.append('CROSS_PORTFOLIO_REQUIRED')
    result.update(state='SCENARIO',constraints=list(dict.fromkeys(reasons)),execution_preflight_required=True,
                  requested_budget=plan['sizing']['amount'],execution_authorized=False,order_sent=False,
                  account_leverage=snapshot['settings']['leverage'],account_margin=snapshot['settings']['marginType'])
    return result


def indicative(plan,snapshot):
    """Paper quantities below exchange minimums remain explicitly theoretical."""
    from agentrader.bot.v2_preflight import joint_step
    from agentrader.bot.brackets import select_bracket
    from agentrader.bot.portfolio import liquidation_price
    mark=number(snapshot['mark']['markPrice']);amount=number(plan['sizing']['amount']);lev=plan['execution']['leverage'];fee=Decimal('.001')
    result=dict(symbol=plan['symbol'],observed_at=snapshot['observed_at'],calculated_at=snapshot['finished_at'],mark_time=snapshot['mark']['time'],mark_local_time=snapshot['mark']['time']-(snapshot.get('now_ms',int(snapshot.get('finished_at',snapshot['observed_at'])*1000))-int(snapshot.get('finished_at',snapshot['observed_at'])*1000)),mark_price=str(mark),
                strategy=plan['execution']['strategy'],margin_mode=plan['execution']['margin_mode'],liquidation=[],theoretical=True,scenario_warnings=[])
    if plan['execution']['strategy']=='NEUTRAL_GRID':
        result['estimate_unavailable']=True
        return result
    sign=1 if plan['direction']=='LONG' else -1;stop=number(plan['stop']);kind=plan['sizing']['kind']
    grid=plan['execution']['strategy']=='GRID'
    entry=number(plan['entry']['trigger_price']) if plan['entry']['condition']=='LIMIT' else mark
    drift=number(plan['entry']['max_drift_bps'])/10000
    count=plan['grid']['intervals'] if grid else 1
    if grid:
        valuation=max(number(plan['grid']['upper']),stop,number(plan['targets'][0]['price']))
        risk_entry=number(plan['grid']['upper'] if sign==1 else plan['grid']['lower'])
    else:
        valuation=max(entry,mark)*(1+drift)
        risk_entry=valuation if sign==1 else min(entry,mark)*(1-drift)
    loss_unit=(abs(risk_entry-stop) if grid else max(abs(entry-stop),abs(valuation-stop),abs(min(entry,mark)*(1-drift)-stop)))
    unit=valuation if kind=='NOTIONAL' else valuation/lev+valuation*fee*2 if kind=='MARGIN' else loss_unit+valuation*fee*2
    raw=amount/unit/count
    filters={f['filterType']:f for f in snapshot['symbol_info']['filters']};lot=filters['LOT_SIZE'];market=filters.get('MARKET_LOT_SIZE',lot)
    step=joint_step(lot['stepSize'],market['stepSize']);rounded=(raw/step).to_integral_value(rounding=ROUND_FLOOR)*step
    minimum_entry=entry
    if grid:
        lo=number(plan['grid']['lower']);hi=number(plan['grid']['upper']);tick=number(filters['PRICE_FILTER']['tickSize'])
        minimum_entry=lo if sign==1 else lo+(hi-lo)/count if plan['grid']['spacing']=='ARITHMETIC' else (lo*(hi/lo)**(Decimal(1)/count)/tick).to_integral_value(rounding=ROUND_FLOOR)*tick
    minimum_qty=number(lot['minQty']) if grid else max(number(lot['minQty']),number(market['minQty']))
    if rounded<=0 or rounded<minimum_qty or rounded*minimum_entry<number(filters['MIN_NOTIONAL']['notional']):
        result['scenario_warnings'].append('GRID_BUDGET_TOO_SMALL' if grid else 'BUDGET_TOO_SMALL')
    qty=(rounded if rounded>0 else raw)*count
    ceiling=qty*valuation;margin=ceiling/lev;fees=ceiling*fee*2
    result.update(theoretical_quantity=str(qty),rounded_quantity=str(rounded*count),notional_ceiling=str(ceiling),initial_margin=str(margin),fee_reserve=str(fees),stop_risk=str(qty*loss_unit+fees))
    try:
        tier=select_bracket(snapshot['brackets'],ceiling,lev)
        allocation=qty*risk_entry/lev if plan['execution']['margin_mode']=='ISOLATED' else number(snapshot.get('collateral'))-fees
        if allocation>=0:
            liq=liquidation_price(plan['direction'],str(qty),str(risk_entry),str(allocation),tier['maintMarginRatio'])
            result['liquidation']=[dict(direction=plan['direction'],estimated_liquidation=str(liq))]
            if liq>0 and (stop<=liq*Decimal('1.0025') if sign==1 else stop>=liq*Decimal('.9975')):result['scenario_warnings'].append('LIQUIDATION_BUFFER')
    except (ValueError,KeyError,TypeError):result['scenario_warnings'].append('LIQUIDATION_UNAVAILABLE')
    if not grid and not plan['entry'].get('order_options',{}).get('price_match'):
        gross=sum((sign*qty*number(t['fraction'])*(number(t['price'])-entry) for t in plan['targets']),number(0));stop_result=sign*qty*(stop-entry)-fees
        result.update(target_gross=str(gross),target_after_fee_reserve=str(gross-fees),stop_after_fee_reserve=str(stop_result),target_return_percent=str(gross/(qty*entry)*100),
                      target_roe_percent=str((gross-fees)/margin*100),reward_risk=str((gross-fees)/abs(stop_result)) if stop_result else None)
    elif not grid:result['pnl_unavailable']='PRICE_MATCH_ENTRY_UNKNOWN'
    return result


def position_metrics(position):
    result=dict(roe_percent=None,liquidation_distance_percent=None)
    try:
        margin=number(position.get('positionInitialMargin'))
        pnl=number(position.get('unRealizedProfit',position.get('unrealizedProfit')))
        if margin>0:result['roe_percent']=str(pnl/margin*100)
    except (ValueError,TypeError,ArithmeticError):pass
    try:
        mark=number(position.get('markPrice'));liq=number(position.get('liquidationPrice'))
        qty=number(position.get('positionAmt'))
        if mark>0 and liq>0 and qty:
            result['liquidation_distance_percent']=str((mark-liq if qty>0 else liq-mark)/mark*100)
    except (ValueError,TypeError,ArithmeticError):pass
    return result


def summarize(plan, snapshot, compiled):
    mark = number(snapshot['mark']['markPrice'])
    result = dict(state=compiled['state'],symbol=plan['symbol'],observed_at=snapshot['observed_at'],calculated_at=snapshot.get('finished_at',snapshot['observed_at']),
                  mark_price=str(mark),mark_time=snapshot['mark']['time'],mark_local_time=snapshot['mark']['time']-(snapshot.get('now_ms',int(snapshot.get('finished_at',snapshot['observed_at'])*1000))-int(snapshot.get('finished_at',snapshot['observed_at'])*1000)),
                  execution_authorized=False,order_sent=False,model='USD-M linear; funding excluded')
    if compiled['state']!='READY':return result
    risk=compiled['risk']
    result.update(initial_margin=risk['initial_margin'],fee_reserve=risk['fee_reserve'],
                  stop_risk=risk['risk_with_fee_reserve'],notional_ceiling=compiled['notional_ceiling'],
                  liquidation=risk['positions'],margin_mode=plan['execution']['margin_mode'],
                  collateral=snapshot['collateral'],strategy=plan['execution']['strategy'])
    if plan['execution']['strategy']!='SINGLE':return result
    qty=number(compiled['quantity'])
    result['quantity']=str(qty)
    entry=number(compiled['entry']['params'].get('price',str(mark)))
    # priceMatch is a book-selected entry: no fabricated exact entry/PnL.
    if plan['entry'].get('order_options',{}).get('price_match'):
        result['pnl_unavailable']='PRICE_MATCH_ENTRY_UNKNOWN'
        return result
    sign=1 if plan['direction']=='LONG' else -1
    gross=sum((sign*number(t['quantity'])*(number(t['price'])-entry) for t in compiled['targets']),number(0))
    stop=sign*qty*(number(plan['stop'])-entry)
    fees=number(risk['fee_reserve']);margin=number(risk['initial_margin'])
    result.update(quantity=str(qty),entry_price=str(entry),pnl_at_mark=str(sign*qty*(mark-entry)),
                  target_gross=str(gross),target_after_fee_reserve=str(gross-fees),
                  stop_after_fee_reserve=str(stop-fees),
                  target_return_percent=str(gross/(qty*entry)*100) if qty*entry>0 else None,
                  target_roe_percent=str((gross-fees)/margin*100) if margin>0 else None,
                  reward_risk=str((gross-fees)/abs(stop-fees)) if stop-fees else None)
    return result
