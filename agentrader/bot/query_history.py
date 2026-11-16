"""Bounded, stable API-visible history. No ledger adoption or risk release."""
import json
import time
from collections import Counter

from agentrader.bot.history import IncompleteHistory,account_trades
from agentrader.bot.plans import canonical
from agentrader.bot.risk import number
from agentrader.shared.query_routes import HISTORY_PATHS

DAY=86400000
MAX_RECORDS=50000
POLICIES={
    'ORDERS':{'time':'time','id':'orderId','cursor':'orderId','limit':1000,'days':2,'namespace':'NORMAL'},
    'ALGO_ORDERS':{'time':'createTime','id':'algoId','cursor':'algoId','limit':1000,'days':None,'namespace':'ALGO'},
    'TRADES':{'time':'time','id':'id','limit':1000,'days':89,'namespace':'TRADE'},
    'INCOME':{'time':'time','id':'tranId','limit':1000,'days':89,'namespace':'INCOME'},
    'AMENDMENTS':{'time':'time','id':'amendmentId','limit':100,'days':89,'namespace':'AMENDMENT'},
    'FORCE_ORDERS':{'time':'time','id':'orderId','limit':100,'days':89,'namespace':'NORMAL_FORCE'},
    'POSITION_MARGIN':{'time':'time','limit':500,'days':None,'namespace':'MARGIN_EVENT'},
}


class Budget:
    def __init__(self,x,maximum,on_page=None):
        self.x,self.maximum,self.on_page,self.calls=x,maximum,on_page,0
        self.trade_ids=set()
    def get(self,path,params):
        if self.calls>=self.maximum:raise IncompleteHistory('REQUEST_BUDGET_EXHAUSTED')
        self.calls+=1;rows=self.x.get(path,params)
        if not isinstance(rows,list) or len(rows)>params['limit']:raise IncompleteHistory('INVALID_HISTORY_PAGE')
        if self.on_page:self.on_page(self.calls,path,dict(params),rows)
        if path==HISTORY_PATHS['TRADES']:
            for row in rows:
                if isinstance(row,dict) and type(row.get('id')) is int:self.trade_ids.add((row.get('symbol'),row['id']))
            if len(self.trade_ids)>MAX_RECORDS:raise IncompleteHistory('HISTORY_RECORD_BUDGET_EXHAUSTED')
        return rows


def validate_parameters(p):
    base={'kind','start_ms','end_ms','page_size','max_requests'}
    if not isinstance(p,dict) or not isinstance(p.get('kind'),str) or p['kind'] not in POLICIES:raise ValueError('Geçmiş ailesi desteklenmiyor.')
    extra={'order_id','client_order_id'} if p['kind']=='AMENDMENTS' else set()
    if not base<=p.keys() or p.keys()-base-extra:raise ValueError('Geçmiş sorgu alanları geçersiz.')
    if (any(type(p[k]) is not int for k in ('start_ms','end_ms','page_size','max_requests')) or
            not 0<=p['start_ms']<=p['end_ms']<2**63 or p['end_ms']-p['start_ms']>90*DAY or
            not 1<=p['page_size']<=POLICIES[p['kind']]['limit'] or not 2<=p['max_requests']<=1000):raise ValueError('Geçmiş aralığı veya bütçesi geçersiz.')
    if extra:
        from agentrader.shared.query_routes import arguments,QUERIES
        selector={'orderId':p['order_id']} if 'order_id' in p else {'origClientOrderId':p.get('client_order_id')}
        if len(p.keys()&extra)!=1:raise ValueError('Tek bir normal amend emir kimliği gerekli.')
        arguments(QUERIES['OPEN_ORDER'],{'symbol':'BTCUSDT'},selector)


def _key(kind,row):
    if kind=='POSITION_MARGIN':return canonical(row)
    if kind=='AMENDMENTS' and 'amendmentId' not in row:
        modify=row.get('amendment',{}).get('modifyId')
        if type(modify) is not int:raise IncompleteHistory('AMENDMENT_IDENTITY_UNPROVEN')
        return (row.get('symbol'),row.get('orderId'),row.get('clientOrderId'),row['time'],modify)
    ident=row.get(POLICIES[kind]['id'])
    if type(ident) is not int or ident<0:raise IncompleteHistory('INVALID_HISTORY_IDENTITY')
    return (row.get('incomeType'),ident) if kind=='INCOME' else (row.get('symbol'),ident)


def _validate(kind,row,symbol,low,high,selector):
    policy=POLICIES[kind]
    if not isinstance(row,dict) or type(row.get(policy['time'])) is not int or not low<=row[policy['time']]<=high:raise IncompleteHistory('HISTORY_TIME_OUT_OF_SCOPE')
    if kind!='INCOME' and row.get('symbol')!=symbol:raise IncompleteHistory('HISTORY_SYMBOL_MISMATCH')
    if kind=='INCOME':
        if not isinstance(row.get('incomeType'),str) or not row['incomeType'] or not isinstance(row.get('asset'),str) or not row['asset']:raise IncompleteHistory('INVALID_INCOME_IDENTITY')
        number(row.get('income'))
    elif kind=='AMENDMENTS':
        if (not isinstance(row.get('amendment'),dict) or
                'orderId' in selector and row.get('orderId')!=selector['orderId'] or
                'origClientOrderId' in selector and row.get('clientOrderId')!=selector['origClientOrderId']):raise IncompleteHistory('AMENDMENT_ORDER_MISMATCH')
        for field in ('price','origQty'):
            pair=row['amendment'].get(field)
            if not isinstance(pair,dict) or set(pair)!={'before','after'} or any(number(v)<=0 for v in pair.values()):raise IncompleteHistory('INVALID_AMENDMENT_CONTENT')
    elif kind=='POSITION_MARGIN':
        if row.get('positionSide') not in ('BOTH','LONG','SHORT') or type(row.get('type')) is not int or row['type'] not in (1,2):raise IncompleteHistory('INVALID_MARGIN_HISTORY')
        number(row.get('amount'))
    elif kind in ('ORDERS','FORCE_ORDERS'):
        if row.get('side') not in ('BUY','SELL') or not 0<=number(row.get('executedQty'))<=number(row.get('origQty')):raise IncompleteHistory('INVALID_ORDER_HISTORY')
    elif kind=='ALGO_ORDERS':
        if row.get('side') not in ('BUY','SELL') or not isinstance(row.get('clientAlgoId'),str) or not row['clientAlgoId']:raise IncompleteHistory('INVALID_ALGO_HISTORY')
    _key(kind,row)


def _millisecond(budget,kind,symbol,stamp,size,selector):
    policy=POLICIES[kind];cursor=0;result=[]
    while True:
        params={'symbol':symbol,'startTime':stamp,'endTime':stamp,'limit':size,policy['cursor']:cursor}|selector
        rows=budget.get(HISTORY_PATHS[kind],params);last=cursor-1
        for row in rows:
            _validate(kind,row,symbol,stamp,stamp,selector);ident=row[policy['id']]
            if ident<cursor or ident<=last:raise IncompleteHistory('HISTORY_ID_CURSOR_NOT_ADVANCING')
            result.append(row);last=ident
            if len(result)>MAX_RECORDS:raise IncompleteHistory('HISTORY_RECORD_BUDGET_EXHAUSTED')
        if len(rows)<size:return result
        cursor=last+1


def _sweep(budget,kind,symbol,start,end,size,selector):
    result=[];low=start
    while low<=end:
        high=min(end,low+7*DAY-1)
        if kind=='TRADES':
            result.extend(account_trades(budget,symbol,low,high,page_size=size,max_requests=budget.maximum))
            if len(result)>MAX_RECORDS:raise IncompleteHistory('HISTORY_RECORD_BUDGET_EXHAUSTED')
            low=high+1;continue
        pending=[(low,high)]
        while pending:
            a,b=pending.pop();params={'startTime':a,'endTime':b,'limit':size}|selector
            if symbol is not None:params['symbol']=symbol
            rows=budget.get(HISTORY_PATHS[kind],params)
            for row in rows:_validate(kind,row,symbol,a,b,selector)
            if len(rows)==size:
                if a<b:
                    middle=(a+b)//2;pending.extend(((middle+1,b),(a,middle)));continue
                if 'cursor' not in POLICIES[kind]:raise IncompleteHistory('SATURATED_MILLISECOND_WITHOUT_CURSOR')
                rows=_millisecond(budget,kind,symbol,a,size,selector)
            result.extend(rows)
            if len(result)>MAX_RECORDS:raise IncompleteHistory('HISTORY_RECORD_BUDGET_EXHAUSTED')
        low=high+1
    if kind=='POSITION_MARGIN':return sorted(result,key=canonical)
    seen={}
    for row in result:
        key=_key(kind,row)
        if key in seen and seen[key]!=row:raise IncompleteHistory('CONFLICTING_HISTORY_IDENTITY')
        seen[key]=row
    return sorted(seen.values(),key=canonical)


def collect(exchange,kind,symbol,start,end,*,page_size=1000,max_requests=127,selector=None,now_ms=None,on_page=None,enforce_retention=True):
    if kind not in POLICIES:raise ValueError('Geçmiş ailesi desteklenmiyor.')
    if (type(start) is not int or type(end) is not int or not 0<=start<=end or type(page_size) is not int or
            not 1<=page_size<=POLICIES[kind]['limit'] or type(max_requests) is not int or not 2<=max_requests<=1000):raise ValueError('Geçmiş aralığı veya bütçesi geçersiz.')
    policy=POLICIES[kind];selector=selector or {};now_ms=int(time.time()*1000)+getattr(exchange,'offset_ms',0) if now_ms is None else now_ms
    budget=Budget(exchange,max_requests,on_page);data=[]
    report={'kind':kind,'namespace':policy['namespace'],'requested_start_ms':start,'requested_end_ms':end,
            'complete':False,'pagination_complete':False,'stable_reads':False,'records':data,'requests':0,
            'coverage':'API_VISIBLE_INTERVAL_ONLY','accounting_adopted':False,'reason':None}
    try:
        if end>now_ms:raise IncompleteHistory('HISTORY_END_IN_FUTURE')
        if enforce_retention and policy['days'] is not None and start<now_ms-policy['days']*DAY:raise IncompleteHistory('RETENTION_GAP')
        data=_sweep(budget,kind,symbol,start,end,page_size,selector);report['records']=data
        if len(data)>MAX_RECORDS:raise IncompleteHistory('HISTORY_RECORD_BUDGET_EXHAUSTED')
        again=_sweep(budget,kind,symbol,start,end,page_size,selector)
        if Counter(canonical(r) for r in data)!=Counter(canonical(r) for r in again):raise IncompleteHistory('HISTORY_CHANGED_DURING_COLLECTION')
        report.update(pagination_complete=True,stable_reads=True,complete=policy['days'] is not None or not enforce_retention)
        if not report['complete']:report['reason']='RETENTION_OR_EVENT_IDENTITY_NOT_DOCUMENTED'
    except (IncompleteHistory,ValueError) as exc:report['reason']=str(exc)
    report['requests']=budget.calls;report['record_count']=len(report['records'])
    return report


def amendment_history(exchange,symbol,client_id,start_ms,end_ms,*,expected_order_id=None,max_requests=127):
    report=collect(exchange,'AMENDMENTS',symbol,start_ms,end_ms,page_size=100,max_requests=max_requests,
                   selector={'origClientOrderId':client_id},now_ms=end_ms,enforce_retention=False)
    if not report['complete'] or expected_order_id is not None and any(str(r.get('orderId'))!=str(expected_order_id) for r in report['records']):
        raise IncompleteHistory('Amend geçmişi eksik veya emir kimliği doğrulanamadı.')
    return report['records']
