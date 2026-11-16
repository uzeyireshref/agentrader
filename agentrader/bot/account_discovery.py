"""Observed product access and account schema, never execution authorization."""
import time
import uuid
import re

from agentrader.bot.capabilities import failure_status
from agentrader.bot.risk import number
from agentrader.shared.exchange import ExchangeError


def _report(client,kind,private):
    return {'schema':'account-discovery/1','run_id':'dsc-'+uuid.uuid4().hex,'kind':kind,
            'identity':client.evidence_identity(private),'observed_ms':int(time.time()*1000),
            'private_requested':private,'read_only':True,'write_permission':'NOT_VERIFIED',
            'financial_execution_authorized':False,'accounting_adopted':False}


def _flags(data):
    result={}
    for key in ('canTrade','canDeposit','canWithdraw','reduceOnly','dualSidePosition','multiAssetsMargin'):
        if key in data:
            if type(data[key]) is not bool:raise ValueError('ACCOUNT_FLAG_SCHEMA_UNPROVEN')
            result[key]=data[key]
    return result


def summarize(client,path,data):
    if not isinstance(data,dict):raise ValueError('DISCOVERY_RESPONSE_SCHEMA_UNPROVEN')
    p=client.profile
    if path.endswith('/time'):
        if type(data.get('serverTime')) is not int or data['serverTime']<=0:raise ValueError('DISCOVERY_SERVER_TIME_UNPROVEN')
        return {'server_time_ms':data['serverTime']}
    if path.endswith('/ping'):return {'responded':True}
    if path.endswith('/exchangeInfo'):
        field='optionSymbols' if p.product=='OPTIONS' else 'symbols';symbols=data.get(field)
        if not isinstance(symbols,list) or any(not isinstance(s,dict) or not isinstance(s.get('symbol'),str) for s in symbols):raise ValueError('DISCOVERY_SYMBOL_SCHEMA_UNPROVEN')
        return {'symbol_count':len(symbols),'account_eligibility':'NOT_PROVEN_BY_PUBLIC_DATA'}
    flags=_flags(data);result={'flags':flags,'account_model_match':'UNPROVEN'}
    if path.endswith('/positionSide/dual'):
        if 'dualSidePosition' not in flags:raise ValueError('DISCOVERY_POSITION_MODE_UNPROVEN')
        return result
    if path.endswith('/accountConfig'):
        if 'canTrade' not in flags or 'multiAssetsMargin' not in flags:raise ValueError('DISCOVERY_ACCOUNT_CONFIG_UNPROVEN')
        return result
    if p.product in ('USD-M','COIN-M'):
        if not isinstance(data.get('assets'),list) or not isinstance(data.get('positions'),list):raise ValueError('DISCOVERY_FUTURES_ACCOUNT_SCHEMA_UNPROVEN')
        result.update(asset_count=len(data['assets']),position_rows=len(data['positions']),account_model_match='ROUTE_SCHEMA_ONLY')
    elif p.product=='SPOT':
        if not isinstance(data.get('balances'),list) or 'canTrade' not in flags or not isinstance(data.get('accountType'),str):raise ValueError('DISCOVERY_SPOT_ACCOUNT_SCHEMA_UNPROVEN')
        reported=data['accountType'] if data['accountType'] in ('SPOT','MARGIN','FUTURES','OPTIONS','PORTFOLIO_MARGIN') else 'UNRECOGNIZED'
        result.update(balance_asset_count=len(data['balances']),reported_account_type=reported,
                      account_model_match='MODEL_REPORTED' if data['accountType']=='SPOT' else 'MISMATCH')
        permissions=data.get('permissions')
        if isinstance(permissions,list):
            known=[v for v in permissions if isinstance(v,str) and (v in ('SPOT','MARGIN','LEVERAGED','FUTURES','OPTIONS') or re.fullmatch('TRD_GRP_[0-9]{3}',v))]
            result.update(reported_permissions=known,unrecognized_permission_count=len(permissions)-len(known))
    elif p.product=='OPTIONS':
        if not isinstance(data.get('asset'),list) or not isinstance(data.get('greek'),list) or 'canTrade' not in flags:raise ValueError('DISCOVERY_OPTIONS_MARGIN_SCHEMA_UNPROVEN')
        result.update(margin_asset_count=len(data['asset']),greek_underlyings=len(data['greek']),account_model_match='OPTIONS_MARGIN_SCHEMA_ONLY')
    elif p.product=='MARGIN':
        if p.account_model=='MARGIN_CROSS':
            if not isinstance(data.get('userAssets'),list) or 'marginLevel' not in data:raise ValueError('DISCOVERY_MARGIN_ACCOUNT_SCHEMA_UNPROVEN')
            number(data['marginLevel']);debts=0
            for asset in data['userAssets']:
                if not isinstance(asset,dict):raise ValueError('DISCOVERY_MARGIN_ASSET_SCHEMA_UNPROVEN')
                if number(asset.get('borrowed',0))>0 or number(asset.get('interest',0))>0:debts+=1
            result.update(asset_count=len(data['userAssets']),debt_asset_count=debts)
        else:
            if not isinstance(data.get('assets'),list):raise ValueError('DISCOVERY_ISOLATED_MARGIN_SCHEMA_UNPROVEN')
            result['isolated_pair_count']=len(data['assets'])
        result['account_model_match']='MARGIN_SCHEMA_ONLY'
    elif p.product in ('PORTFOLIO_MARGIN','PORTFOLIO_MARGIN_PRO'):
        if (data.get('accountStatus') not in ('NORMAL','MARGIN_CALL','SUPPLY_MARGIN','REDUCE_ONLY','ACTIVE_LIQUIDATION','FORCE_LIQUIDATION','BANKRUPTED') or
                not isinstance(data.get('uniMMR'),str) or not data['uniMMR']):raise ValueError('DISCOVERY_PM_SCHEMA_UNPROVEN')
        result.update(account_status=data['accountStatus'],account_model_match='ROUTE_SCHEMA_ONLY')
        if p.product=='PORTFOLIO_MARGIN_PRO':
            value=data.get('accountType')
            if value not in ('PM_1','PM_2','PM_3'):raise ValueError('DISCOVERY_PM_VERSIONED_TYPE_UNPROVEN')
            result['reported_account_type']=value
            result['account_model_match']=('MODEL_REPORTED' if value=='PM_3' else 'MISMATCH') if p.account_model=='PM_PRO_SPAN_V2' else 'VERSIONED_LABEL_UNPROVEN'
    else:raise ValueError('DISCOVERY_MODEL_SUMMARY_NOT_IMPLEMENTED')
    return result


def probe(client,*,include_private=False):
    if type(include_private) is not bool:raise ValueError('EXPLICIT_DISCOVERY_ACCESS_REQUIRED')
    report=_report(client,'ACCOUNT_DISCOVERY',include_private);checks=[];p=client.profile
    report.update(checks=checks,product_eligibility='UNPROVEN',permissions={'public_read':'NOT_PROBED','private_read':'NOT_REQUESTED',
        'can_trade_flag':None,'write_permission':'NOT_VERIFIED'},status='INCOMPLETE')
    if not p.public_reads and not p.private_reads:
        report['status']='DISCOVERY_NOT_IMPLEMENTED';return report
    blocked=False;auth_blocked=False;trade_flags=[]
    for private,paths in ((False,p.public_reads),(True,p.private_reads)):
        for path in paths:
            check={'method':'GET','path':path,'private':private}
            if private and not include_private:check['status']='ACCOUNT_NOT_REQUESTED'
            elif blocked:check['status']='SKIPPED_AFTER_ACCESS_ERROR'
            elif private and not client.has_credentials:check['status']='CREDENTIALS_MISSING'
            elif private and auth_blocked:check['status']='SKIPPED_AFTER_PRIVATE_ERROR'
            else:
                try:
                    start=time.time();data=client.get(path);summary=summarize(client,path,data)
                    if not 0<=time.time()-start<=15:raise ValueError('DISCOVERY_VIEW_EXPIRED')
                    check.update(status='READ_VERIFIED',summary=summary)
                    if summary.get('account_model_match')=='MISMATCH':check['status']='MODEL_MISMATCH'
                    if 'canTrade' in summary.get('flags',{}):trade_flags.append(summary['flags']['canTrade'])
                except ExchangeError as exc:
                    check.update(status=failure_status(exc),code=exc.code,http_status=exc.http_status)
                    if exc.http_status in (403,418,429,451):blocked=True
                    if private and exc.code in (-2014,-2015,-1022):auth_blocked=True
                except (ValueError,KeyError,TypeError):check['status']='SCHEMA_OR_CONTEXT_UNPROVEN'
            checks.append(check)
    for private,key in ((False,'public_read'),(True,'private_read')):
        selected=[c for c in checks if c['private']==private]
        if private and not include_private:continue
        report['permissions'][key]='VERIFIED' if selected and all(c['status']=='READ_VERIFIED' for c in selected) else 'UNPROVEN'
    needed=[c for c in checks if include_private or not c['private']]
    report['status']='READ_COMPLETE' if needed and all(c['status']=='READ_VERIFIED' for c in needed) else 'INCOMPLETE'
    if trade_flags and len(set(trade_flags))==1:report['permissions']['can_trade_flag']=trade_flags[0]
    elif len(set(trade_flags))>1:report.update(status='INCOMPLETE',reason='ACCOUNT_FLAGS_CHANGED_OR_INCONSISTENT')
    if report['permissions']['private_read']=='VERIFIED' and report['status']=='READ_COMPLETE':report['product_eligibility']='ACCOUNT_FLAG_RESTRICTED' if report['permissions']['can_trade_flag'] is False else 'SCHEMA_OBSERVED_ONLY'
    report['finished_ms']=int(time.time()*1000)
    return report


def lookup_order(client,symbol,*,order_id=None,client_order_id=None):
    if client.profile.order_lookup is None:raise ValueError('ORDER_LOOKUP_NOT_REGISTERED_FOR_CONTEXT')
    if (order_id is None)==(client_order_id is None):raise ValueError('ONE_NORMAL_ORDER_ID_REQUIRED')
    params={'symbol':symbol}|({'orderId':order_id} if order_id is not None else {'origClientOrderId':client_order_id})
    client._arguments(client.profile.order_lookup,params)
    report=_report(client,'NORMAL_ORDER_LOOKUP',True)
    report.update(namespace='NORMAL',symbol=symbol,absence_is_rejection=False,reset_possible=client.profile.environment in ('demo','testnet'))
    try:
        data=client.get(client.profile.order_lookup,params)
        if (not isinstance(data,dict) or data.get('symbol')!=symbol or type(data.get('orderId')) is not int or data['orderId']<=0 or
                order_id is not None and data['orderId']!=order_id or client_order_id is not None and data.get('clientOrderId')!=client_order_id or
                data.get('status') not in ('NEW','PARTIALLY_FILLED','FILLED','CANCELED','PENDING_CANCEL','REJECTED','EXPIRED','EXPIRED_IN_MATCH')):
            raise ValueError('ORDER_IDENTITY_UNPROVEN')
        if 'origQty' in data and 'executedQty' in data:
            if not 0<=number(data['executedQty'])<=number(data['origQty']):raise ValueError('ORDER_FILL_UNPROVEN')
            if (data['status']=='FILLED' and number(data['executedQty'])!=number(data['origQty']) or
                    data['status'] in ('NEW','REJECTED') and number(data['executedQty'])!=0):raise ValueError('ORDER_STATUS_FILL_MISMATCH')
        report.update(status='ORDER_OBSERVED',order={k:data[k] for k in ('symbol','orderId','clientOrderId','status','origQty','executedQty','time','updateTime') if k in data})
        for key,value in report['order'].items():
            if isinstance(value,str) and value in (client.credentials.api_key,client.credentials.api_secret):report['order'][key]='REDACTED'
    except ExchangeError as exc:
        report.update(status='ORDER_NOT_OBSERVED' if exc.code==-2013 else failure_status(exc),code=exc.code,http_status=exc.http_status,
                      history_status='UNPROVEN_RESET_RETENTION_OR_IDENTITY')
    except (ValueError,KeyError,TypeError):report.update(status='ORDER_IDENTITY_UNPROVEN')
    return report
