"""Named read commands and single-shot export jobs. No order/risk adoption."""
import json
import math
import re
import time
from urllib.parse import urlsplit

from agentrader.bot.plans import canonical,digest,exact_fields,transaction
from agentrader.bot.risk import number
from agentrader.bot.capabilities import failure_status
from agentrader.bot.query_history import POLICIES,collect,validate_parameters,DAY
from agentrader.shared.query_routes import QUERIES,HISTORY_PATHS,EXPORT_PATHS,arguments
from agentrader.shared.exchange import ExchangeError

OPERATIONS={'PUBLIC_QUERY','PRIVATE_QUERY','QUERY_HISTORY','CREATE_HISTORY_EXPORT','QUERY_HISTORY_EXPORT'}
FIELDS=set('''symbol pair asset marginAsset orderId clientOrderId algoId clientAlgoId actualOrderId actualPrice actualQty
    type orderType origType algoType status algoStatus side positionSide time createTime updateTime triggerTime goodTillDate
    price origQty quantity qty executedQty cumQty cumQuote cumBase avgPrice quoteQty baseQty reduceOnly closePosition
    timeInForce priceMatch selfTradePreventionMode triggerPrice workingType priceProtect activatePrice callbackRate
    incomeType income tranId tradeId info amount deltaType amendmentId amendment modifyId before after origQty count
    assets positions balance walletBalance crossWalletBalance crossUnPnl availableBalance maxWithdrawAmount unrealizedProfit
    isolatedWallet isolatedMargin initialMargin maintMargin positionInitialMargin openOrderInitialMargin marginBalance
    marginAvailable canTrade canDeposit canWithdraw updateTime totalWalletBalance totalMarginBalance totalUnrealizedProfit
    totalInitialMargin totalMaintMargin totalPositionInitialMargin totalOpenOrderInitialMargin totalCrossWalletBalance totalCrossUnPnl
    positionAmt entryPrice breakEvenPrice markPrice indexPrice liquidationPrice leverage marginType isAutoAddMargin
    symbolStatus exchangeFilters rateLimits rateLimitType interval intervalNum limit timezone serverTime symbols status
    contractType onboardDate deliveryDate deliveryTime deliveryPrice quoteAsset baseAsset marginAsset pricePrecision
    quantityPrecision baseAssetPrecision quotePrecision underlyingType underlyingSubType settlePlan triggerProtect
    liquidationFee marketTakeBound maxMoveOrderLimit filters filterType minPrice maxPrice tickSize minQty maxQty stepSize
    notional multiplierUp multiplierDown multiplierDecimal notionalFloor notionalCap initialLeverage maintMarginRatio cum
    notionalCoef brackets orderTypes timeInForce allowedSelfTradePreventionModes defaultSelfTradePreventionMode
    constituents exchange weight component baseAssetList percentage volumeInBaseAsset insuranceFund assetName
    indicators indicator value triggerValue isLocked plannedRecoverTime isAutoExchange feeTier multiAssetsMargin dualSidePosition feeBurn
    makerCommissionRate takerCommissionRate longAccount shortAccount longShortRatio buySellRatio buyVol sellVol timestamp
    sumOpenInterest sumOpenInterestValue CMCCirculatingSupply lastUpdateId E T bids asks bidPrice bidQty askPrice askQty
    priceChange priceChangePercent weightedAvgPrice lastPrice lastQty openPrice highPrice lowPrice volume quoteVolume
    openTime closeTime firstId lastId id p q a f l m nq isBuyerMaker isRPITrade isBestMatch fundingRate fundingTime
    adjustedFundingRateCap adjustedFundingRateFloor fundingIntervalHours disclaimer lastFundingRate interestRate nextFundingTime
    estimatedSettlePrice openInterest index bidRate askRate bidBuffer askBuffer autoExchangeBidBuffer autoExchangeAskBuffer
    adlQuantile LONG SHORT BOTH adlRisk riskLevel basis basisRate futuresPrice annualizedBasisRate
    commission commissionAsset realizedPnl buyer maker notional unRealizedProfit collateralRate autoAssetExchange
'''.split())
NUMERIC=set('price qty origQty quantity executedQty actualQty actualPrice amount income availableBalance balance walletBalance crossWalletBalance crossUnPnl maxWithdrawAmount unrealizedProfit isolatedWallet positionAmt entryPrice markPrice indexPrice liquidationPrice notional initialMargin maintMargin makerCommissionRate takerCommissionRate fundingRate lastFundingRate'.split())


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS exchange_read_pages (
        command_id TEXT NOT NULL,attempt INTEGER NOT NULL,page INTEGER NOT NULL,body TEXT NOT NULL,digest TEXT NOT NULL,
        PRIMARY KEY(command_id,attempt,page))''')
    db.execute('''CREATE TABLE IF NOT EXISTS exchange_history_exports (
        command_id TEXT PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL)''')


def validate(operation,request):
    p=request['parameters'];scope=request['scope']
    if not isinstance(p,dict):raise ValueError('Sorgu parametreleri nesne olmalı.')
    if operation in ('PUBLIC_QUERY','PRIVATE_QUERY'):
        exact_fields(p,'query arguments','Adlandırılmış sorgu')
        if not isinstance(p['query'],str) or p['query'] not in QUERIES:raise ValueError('Sorgu adı desteklenmiyor.')
        spec=QUERIES[p['query']]
        if spec['private']!=(operation=='PRIVATE_QUERY'):raise ValueError('Public/private sorgu yolu uyuşmuyor.')
        field='symbol' if spec['scope'] in ('SYMBOL','PAIR') or spec['scope']=='OPTIONAL_SYMBOL' and 'symbol' in scope else 'account_wide' if spec['private'] else 'market_wide'
        exact_fields(scope,field,'Sorgu kapsamı')
        if field!='symbol' and scope[field] is not True:raise ValueError('Açık hesap/piyasa kapsamı gerekli.')
        arguments(spec,scope,p['arguments'])
    else:
        field='account_wide' if operation in ('CREATE_HISTORY_EXPORT','QUERY_HISTORY_EXPORT') or p.get('kind')=='INCOME' else 'symbol'
        exact_fields(scope,field,'Geçmiş kapsamı')
        if field=='account_wide':
            if scope[field] is not True:raise ValueError('Açık hesap kapsamı gerekli.')
        elif not isinstance(scope[field],str) or not re.fullmatch('[A-Z0-9]{2,20}USDT',scope[field]):raise ValueError('USDT sembol kapsamı gerekli.')
        if operation=='QUERY_HISTORY':validate_parameters(p)
        elif operation=='CREATE_HISTORY_EXPORT':
            exact_fields(p,'kind start_ms end_ms','Geçmiş dışa aktarma')
            if (not isinstance(p['kind'],str) or p['kind'] not in EXPORT_PATHS or type(p['start_ms']) is not int or type(p['end_ms']) is not int or
                    not 0<=p['start_ms']<=p['end_ms']<2**63 or p['end_ms']-p['start_ms']>365*DAY):raise ValueError('Dışa aktarma aralığı veya ailesi geçersiz.')
        else:
            exact_fields(p,'source_command_id','Dışa aktarma iş kimliği')
            if not isinstance(p['source_command_id'],str) or not re.fullmatch('cmd-[a-f0-9]{40}',p['source_command_id']):raise ValueError('Kaynak dışa aktarma komutu gerekli.')


def _project(value,fields=FIELDS,depth=0,key=None):
    if depth>12:raise ValueError('Sorgu yanıtı iç içe sınırını aşıyor.')
    if key in NUMERIC and value is not None:
        if isinstance(value,dict) and key in ('price','origQty') and set(value)=={'before','after'}:
            for item in value.values():number(item)
        else:number(value)
    if isinstance(value,dict):
        return {k:_project(v,FIELDS,depth+1,k) for k,v in value.items() if k in fields or key=='indicators' and re.fullmatch('[A-Z0-9]{2,20}USDT',k)}
    if isinstance(value,list):
        if len(value)>50000:raise ValueError('Sorgu kayıt sınırı aşıldı.')
        return [_project(v,FIELDS,depth+1) for v in value]
    if value is None or type(value) in (bool,int):return value
    if type(value) is float and math.isfinite(value):return value
    if isinstance(value,str) and len(value)<=4096:return value
    raise ValueError('Sorgu yanıtında geçersiz değer.')


def _snapshot(spec,data,scope,query,params):
    shape=spec['shape']
    if shape=='object' and not isinstance(data,dict) or shape in ('list','candles') and not isinstance(data,list) or shape=='either' and not isinstance(data,(dict,list)):
        raise ValueError('Sorgu yanıtının kök şeması uyuşmuyor.')
    if shape=='candles':
        if any(not isinstance(r,list) or len(r)<6 or type(r[0]) is not int or any(not number(v).is_finite() for v in r[1:6]) for r in data):raise ValueError('Mum sorgusu şeması geçersiz.')
    elif isinstance(data,list) and any(not isinstance(r,dict) for r in data):raise ValueError('Sorgu kayıt şeması geçersiz.')
    rows=data if isinstance(data,list) else [data]
    if shape!='candles':
        for row in rows:
            if scope.get('symbol') and 'symbol' in row and row['symbol']!=scope['symbol']:raise ValueError('Sorgu sembolü yanıtla uyuşmuyor.')
            if query.startswith('ACCOUNT_V') and not all(isinstance(row.get(k),list) for k in ('assets','positions')):raise ValueError('Hesap yanıtı eksik.')
            if query=='EXCHANGE_INFO' and not isinstance(row.get('symbols'),list):raise ValueError('Sembol listesi eksik.')
            if query=='TRADING_STATUS' and not isinstance(row.get('indicators'),dict):raise ValueError('İşlem durumu göstergeleri eksik.')
            if query=='ACCOUNT_CONFIG' and type(row.get('canTrade')) is not bool:raise ValueError('Hesap işlem uygunluğu bayrağı eksik.')
            if query=='LEVERAGE_BRACKETS':
                from agentrader.bot.brackets import validate_brackets
                validate_brackets(row.get('brackets'))
            if query in ('DEPTH','RPI_DEPTH'):
                for side in ('bids','asks'):
                    levels=row.get(side)
                    if not isinstance(levels,list) or any(not isinstance(v,list) or len(v)!=2 or number(v[0])<=0 or number(v[1])<0 for v in levels):raise ValueError('Derinlik seviyeleri geçersiz.')
            if query.startswith('BALANCE_') and not isinstance(row.get('asset'),str):raise ValueError('Bakiye varlığı eksik.')
            if query.startswith('POSITIONS_') and ('symbol' not in row or 'positionAmt' not in row):raise ValueError('Pozisyon yanıtı eksik.')
            if query in ('POSITION_MODE','MULTI_ASSETS_MODE','FEE_BURN'):
                field={'POSITION_MODE':'dualSidePosition','MULTI_ASSETS_MODE':'multiAssetsMargin','FEE_BURN':'feeBurn'}[query]
                if type(row.get(field)) is not bool:raise ValueError('Hesap modu yanıtı geçersiz.')
            if query in ('OPEN_ORDER','ALGO_ORDER'):
                id_field='orderId' if query=='OPEN_ORDER' else 'algoId'
                if row.get('symbol')!=scope['symbol'] or type(row.get(id_field)) is not int or row[id_field]<=0:raise ValueError('Sorgu emir kimliği eksik.')
                if id_field in params and row[id_field]!=params[id_field]:raise ValueError('Sorgulanan broker kimliği uyuşmuyor.')
                field='origClientOrderId' if query=='OPEN_ORDER' else 'clientAlgoId'
                response_field='clientOrderId' if query=='OPEN_ORDER' else 'clientAlgoId'
                if field in params and row.get(response_field)!=params[field]:raise ValueError('Sorgulanan istemci kimliği uyuşmuyor.')
            if query in ('OPEN_ORDERS','OPEN_ALGO_ORDERS'):
                id_field='orderId' if query=='OPEN_ORDERS' else 'algoId'
                if (not isinstance(row.get('symbol'),str) or scope.get('symbol') and row['symbol']!=scope['symbol'] or
                        type(row.get(id_field)) is not int or row[id_field]<=0):raise ValueError('Açık emir ad alanı/kimliği doğrulanamadı.')
    fields=spec['fields'] or FIELDS
    result=_project(data,fields)
    if isinstance(data,dict) and not result and query!='PING':raise ValueError('Sorgu yanıtında bilinen alan bulunamadı.')
    return result


def _attempt(commands,body):
    row=commands.store.db.execute('SELECT max(attempt) FROM exchange_read_pages WHERE command_id=?',(body['command_id'],)).fetchone()
    return (row[0] or 0)+1


def _page(commands,body,attempt,page,path,params,data):
    proof={'command_digest':digest(body),'path':path,'parameters':params,'response_digest':digest(data),
           'row_count':len(data) if isinstance(data,list) else None,'observed_at_ms':int(time.time()*1000)}
    with commands.store.db:commands.store.db.execute('INSERT INTO exchange_read_pages VALUES(?,?,?,?,?)',
        (body['command_id'],attempt,page,canonical(proof),digest(proof)))


def _export(commands,body):
    p=body['request']['parameters'];op=body['request']['operation'];cid=body['command_id']
    if op=='CREATE_HISTORY_EXPORT':
        if p['end_ms']>int(time.time()*1000)+getattr(commands.x,'offset_ms',0):return commands._finish(cid,'NOT_SENT',{'reason':'EXPORT_END_IN_FUTURE'})
        if time.time()>=body['expires_at']:return commands._finish(cid,'NOT_SENT',{'reason':'EXPORT_AUTHORITY_EXPIRED'})
        data=commands.x.get(EXPORT_PATHS[p['kind']],{'startTime':p['start_ms'],'endTime':p['end_ms']})
        download=data.get('downloadId') if isinstance(data,dict) else None
        if not isinstance(download,str) or not re.fullmatch('[A-Za-z0-9_-]{1,128}',download):raise ValueError('Dışa aktarma iş kimliği doğrulanamadı.')
        proof={'source_digest':digest(body),'account_ref':commands.account_ref,'owner':commands.owner,'kind':p['kind'],
               'start_ms':p['start_ms'],'end_ms':p['end_ms'],'download_id':download}
        with commands.store.db:commands.store.db.execute('INSERT INTO exchange_history_exports VALUES(?,?,?)',(cid,canonical(proof),digest(proof)))
        return commands._finish(cid,'APPLIED',{'download_id':download,'kind':p['kind'],'job_created':True,'file_downloaded':False,'complete':False,'automatic_resend':False})
    source,source_body=commands._row(p['source_command_id']);saved=commands.store.db.execute('SELECT * FROM exchange_history_exports WHERE command_id=?',(p['source_command_id'],)).fetchone()
    if saved is None:raise ValueError('Kaynak dışa aktarma iş kimliği bilinmiyor; yeni iş oluşturulmaz.')
    proof=json.loads(saved['body'])
    if (source['operation']!='CREATE_HISTORY_EXPORT' or digest(proof)!=saved['digest'] or proof['source_digest']!=source['digest'] or
            proof['account_ref']!=commands.account_ref or proof['owner']!=commands.owner or
            any(proof[k]!=source_body['request']['parameters'][k] for k in ('kind','start_ms','end_ms'))):raise ValueError('Dışa aktarma aile/hesap bağlantısı uyuşmuyor.')
    data=commands.x.get(EXPORT_PATHS[proof['kind']]+'/id',{'downloadId':proof['download_id']})
    if not isinstance(data,dict) or data.get('downloadId')!=proof['download_id'] or data.get('status') not in ('processing','completed'):raise ValueError('Dışa aktarma iş yanıtı uyuşmuyor.')
    result={'download_id':proof['download_id'],'kind':proof['kind'],'status':data['status'].upper(),'complete':False,'file_downloaded':False}
    if data['status']=='completed':
        expiry=data.get('expirationTimestamp');url=data.get('url');parsed=urlsplit(url) if isinstance(url,str) else None
        if (type(expiry) is not int or expiry<=int(time.time()*1000)+getattr(commands.x,'offset_ms',0) or str(data.get('isExpired')).lower()=='true'):
            return commands._finish(cid,'READ_FAILED',result|{'status':'EXPIRED','reason':'EXPORT_LINK_EXPIRED'})
        if parsed is None or parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password:raise ValueError('Dışa aktarma bağlantısı doğrulanamadı.')
        result.update(download_url=url,expiration_ms=expiry,status='READY')
    return commands._finish(cid,'APPLIED',result)


def run(commands,body):
    request=body['request'];p=request['parameters'];op=request['operation'];cid=body['command_id']
    try:
        if op!='PUBLIC_QUERY':commands.x.sync_time()
        if op in ('CREATE_HISTORY_EXPORT','QUERY_HISTORY_EXPORT'):return _export(commands,body)
        attempt=_attempt(commands,body)
        if op=='QUERY_HISTORY':
            selector={'orderId':p['order_id']} if 'order_id' in p else {'origClientOrderId':p['client_order_id']} if 'client_order_id' in p else {}
            report=collect(commands.x,p['kind'],request['scope'].get('symbol'),p['start_ms'],p['end_ms'],page_size=p['page_size'],max_requests=p['max_requests'],selector=selector,
                on_page=lambda n,path,params,rows:_page(commands,body,attempt,n,path,params,rows))
            report['records']=_project(report['records']);report['attempt']=attempt
            if len(canonical(report['records']))>8*1024*1024:report.update(complete=False,reason='RESULT_SIZE_BUDGET',records=[])
            return commands._finish(cid,'APPLIED' if report['complete'] else 'READ_FAILED',report)
        spec=QUERIES[p['query']];params=arguments(spec,request['scope'],p['arguments'])
        if op=='PUBLIC_QUERY' and callable(getattr(commands.x,'public_query',None)):
            data=commands.x.public_query(p['query'],request['scope'],p['arguments'])
        else:data=commands.x.get(spec['path'],params)
        _page(commands,body,attempt,1,spec['path'],params,data)
        data=_snapshot(spec,data,request['scope'],p['query'],params)
        if len(canonical(data))>8*1024*1024:raise ValueError('Sorgu sonucu yerel boyut sınırını aşıyor.')
        return commands._finish(cid,'APPLIED',{'query':p['query'],'data':data,'complete':False,'meaning':'BOUNDED_SNAPSHOT_NOT_FULL_HISTORY',
            'environment':'demo','product':'USD-M','accounting_adopted':False,'observed_at_ms':int(time.time()*1000),'attempt':attempt})
    except ExchangeError as exc:
        return commands._finish(cid,'UNKNOWN' if op=='CREATE_HISTORY_EXPORT' else 'READ_FAILED',
            {'complete':False,'reason':failure_status(exc),'code':exc.code,'automatic_resend':False,'absence_is_rejection':False})
    except (ValueError,KeyError,TypeError):
        return commands._finish(cid,'UNKNOWN' if op=='CREATE_HISTORY_EXPORT' else 'READ_FAILED',
            {'complete':False,'reason':'QUERY_RESPONSE_OR_LINK_UNVERIFIED','automatic_resend':False,'absence_is_rejection':False})


def reconcile(commands,body):
    if body['request']['operation']!='CREATE_HISTORY_EXPORT':return run(commands,body)
    saved=commands.store.db.execute('SELECT * FROM exchange_history_exports WHERE command_id=?',(body['command_id'],)).fetchone()
    if saved:
        proof=json.loads(saved['body'])
        if (digest(proof)!=saved['digest'] or proof['source_digest']!=digest(body) or proof['account_ref']!=commands.account_ref or
                proof['owner']!=commands.owner or any(proof[k]!=body['request']['parameters'][k] for k in ('kind','start_ms','end_ms'))):raise ValueError('Dışa aktarma kaydı bozuk.')
        return commands._finish(body['command_id'],'APPLIED',{'download_id':proof['download_id'],'kind':proof['kind'],'complete':False,'file_downloaded':False,'automatic_resend':False})
    return commands._finish(body['command_id'],'UNKNOWN',{'complete':False,'reason':'EXPORT_JOB_ID_UNKNOWN','automatic_resend':False})
