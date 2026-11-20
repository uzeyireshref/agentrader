"""Pinned USD-M read contracts; callers cannot supply a URL or signing fields."""
import re

QUERIES={}


def add(name,path,private,scope,shape,arguments='',required='',fields=''):
    QUERIES[name]={'path':path,'private':private,'scope':scope,'shape':shape,
                   'arguments':set(arguments.split()),'required':set(required.split()),'fields':set(fields.split())}


for name,path,shape,fields in [
    ('ACCOUNT_V2','/fapi/v2/account','object','assets positions availableBalance totalWalletBalance totalMarginBalance totalUnrealizedProfit canTrade updateTime'),
    ('ACCOUNT_V3','/fapi/v3/account','object','assets positions availableBalance totalWalletBalance totalMarginBalance totalUnrealizedProfit updateTime'),
    ('BALANCE_V2','/fapi/v2/balance','list','asset balance availableBalance crossWalletBalance crossUnPnl maxWithdrawAmount marginAvailable updateTime'),
    ('BALANCE_V3','/fapi/v3/balance','list','asset balance availableBalance crossWalletBalance crossUnPnl maxWithdrawAmount marginAvailable updateTime'),
    ('ORDER_RATE_LIMIT','/fapi/v1/rateLimit/order','list','rateLimitType interval intervalNum limit count'),
    ('POSITION_MODE','/fapi/v1/positionSide/dual','object','dualSidePosition'),
    ('MULTI_ASSETS_MODE','/fapi/v1/multiAssetsMargin','object','multiAssetsMargin'),
    ('FEE_BURN','/fapi/v1/feeBurn','object','feeBurn'),
    ('ACCOUNT_CONFIG','/fapi/v1/accountConfig','object','canTrade multiAssetsMargin dualSidePosition feeTier updateTime')]:
    add(name,path,True,'ACCOUNT',shape,fields=fields)
for name,path,shape,args,fields in [
    ('TRADING_STATUS','/fapi/v1/apiTradingStatus','object','','indicators updateTime'),
    ('COMMISSION_RATE','/fapi/v1/commissionRate','object','','symbol makerCommissionRate takerCommissionRate'),
    ('SYMBOL_CONFIG','/fapi/v1/symbolConfig','list','','symbol marginType isAutoAddMargin leverage maxNotionalValue'),
    ('LEVERAGE_BRACKETS','/fapi/v1/leverageBracket','either','','symbol notionalCoef brackets'),
    ('POSITIONS_V2','/fapi/v2/positionRisk','list','','symbol positionSide positionAmt entryPrice breakEvenPrice markPrice liquidationPrice leverage marginType isolatedMargin isolatedWallet unRealizedProfit updateTime'),
    ('POSITIONS_V3','/fapi/v3/positionRisk','list','','symbol positionSide positionAmt entryPrice breakEvenPrice markPrice liquidationPrice isolatedWallet notional initialMargin positionInitialMargin maintMargin unrealizedProfit unRealizedProfit marginAsset updateTime'),
    ('OPEN_ORDERS','/fapi/v1/openOrders','list','',''),
    ('OPEN_ALGO_ORDERS','/fapi/v1/openAlgoOrders','list','',''),
    ('ADL_QUANTILE','/fapi/v1/adlQuantile','list','','symbol adlQuantile'),
    ('OPEN_ORDER','/fapi/v1/openOrder','object','orderId origClientOrderId','')]:
    add(name,path,True,'SYMBOL',shape,args,fields=fields)

for name,path,scope,shape,args,required,fields in [
    ('PING','/fapi/v1/ping','MARKET','object','','',''),
    ('SERVER_TIME','/fapi/v1/time','MARKET','object','','','serverTime'),
    ('EXCHANGE_INFO','/fapi/v1/exchangeInfo','MARKET','object','','','timezone serverTime rateLimits exchangeFilters assets symbols'),
    ('DEPTH','/fapi/v1/depth','SYMBOL','object','limit','','lastUpdateId E T bids asks'),
    ('RPI_DEPTH','/fapi/v1/rpiDepth','SYMBOL','object','limit','','lastUpdateId E T bids asks'),
    ('RECENT_TRADES','/fapi/v1/trades','SYMBOL','list','limit','','id price qty quoteQty time isBuyerMaker isRPITrade'),
    ('HISTORICAL_TRADES','/fapi/v1/historicalTrades','SYMBOL','list','limit fromId','','id price qty quoteQty time isBuyerMaker isRPITrade'),
    ('AGG_TRADES','/fapi/v1/aggTrades','SYMBOL','list','limit fromId startTime endTime','','a p q f l T m nq'),
    ('KLINES','/fapi/v1/klines','SYMBOL','candles','interval startTime endTime limit','interval',''),
    ('CONTINUOUS_KLINES','/fapi/v1/continuousKlines','PAIR','candles','contractType interval startTime endTime limit','contractType interval',''),
    ('INDEX_KLINES','/fapi/v1/indexPriceKlines','PAIR','candles','interval startTime endTime limit','interval',''),
    ('MARK_KLINES','/fapi/v1/markPriceKlines','SYMBOL','candles','interval startTime endTime limit','interval',''),
    ('PREMIUM_KLINES','/fapi/v1/premiumIndexKlines','SYMBOL','candles','interval startTime endTime limit','interval',''),
    ('MARK_PRICE','/fapi/v1/premiumIndex','SYMBOL','object','','','symbol markPrice indexPrice estimatedSettlePrice lastFundingRate interestRate nextFundingTime time'),
    ('FUNDING_RATE','/fapi/v1/fundingRate','SYMBOL','list','startTime endTime limit','','symbol fundingTime fundingRate markPrice'),
    ('FUNDING_INFO','/fapi/v1/fundingInfo','MARKET','list','','','symbol adjustedFundingRateCap adjustedFundingRateFloor fundingIntervalHours disclaimer'),
    ('TICKER_24HR','/fapi/v1/ticker/24hr','SYMBOL','object','','','symbol priceChange priceChangePercent weightedAvgPrice lastPrice lastQty openPrice highPrice lowPrice volume quoteVolume openTime closeTime firstId lastId count'),
    ('TICKER_PRICE_V1','/fapi/v1/ticker/price','SYMBOL','object','','','symbol price time'),
    ('TICKER_PRICE_V2','/fapi/v2/ticker/price','SYMBOL','object','','','symbol price time'),
    ('BOOK_TICKER','/fapi/v1/ticker/bookTicker','SYMBOL','object','','','symbol bidPrice bidQty askPrice askQty time'),
    ('OPEN_INTEREST','/fapi/v1/openInterest','SYMBOL','object','','','symbol openInterest time'),
    ('OPEN_INTEREST_HISTORY','/futures/data/openInterestHist','SYMBOL','list','period limit startTime endTime','period','symbol sumOpenInterest sumOpenInterestValue CMCCirculatingSupply timestamp'),
    ('TOP_LONG_SHORT_ACCOUNTS','/futures/data/topLongShortAccountRatio','SYMBOL','list','period limit startTime endTime','period','symbol longShortRatio longAccount shortAccount timestamp'),
    ('TOP_LONG_SHORT_POSITIONS','/futures/data/topLongShortPositionRatio','SYMBOL','list','period limit startTime endTime','period','symbol longShortRatio longAccount shortAccount timestamp'),
    ('GLOBAL_LONG_SHORT','/futures/data/globalLongShortAccountRatio','SYMBOL','list','period limit startTime endTime','period','symbol longShortRatio longAccount shortAccount timestamp'),
    ('TAKER_LONG_SHORT','/futures/data/takerlongshortRatio','SYMBOL','list','period limit startTime endTime','period','buySellRatio buyVol sellVol timestamp'),
    ('BASIS','/futures/data/basis','PAIR','list','contractType period limit startTime endTime','contractType period','indexPrice contractType basisRate futuresPrice annualizedBasisRate basis pair timestamp'),
    ('INDEX_INFO','/fapi/v1/indexInfo','SYMBOL','object','','','symbol time component baseAssetList'),
    ('ASSET_INDEX','/fapi/v1/assetIndex','MARKET','either','','','symbol time index bidRate askRate bidBuffer askBuffer autoExchangeBidBuffer autoExchangeAskBuffer'),
    ('DELIVERY_PRICE','/fapi/v1/deliveryPrice','PAIR','list','','','deliveryTime deliveryPrice'),
    ('CONSTITUENTS','/fapi/v1/constituents','SYMBOL','object','','','symbol time constituents'),
    ('INSURANCE_BALANCE','/fapi/v1/insuranceBalance','MARKET','either','','','symbols assets'),
    ('SYMBOL_ADL_RISK','/fapi/v1/symbolAdlRisk','SYMBOL','either','','','symbol adlRisk riskLevel')]:
    add(name,path,False,scope,shape,args,required,fields)

QUERIES['HISTORICAL_TRADES']['private']=True
QUERIES['HISTORICAL_TRADES']['key_only']=True
add('ALGO_ORDER','/fapi/v1/algoOrder',True,'SYMBOL','object','algoId clientAlgoId')
for name in ('TRADING_STATUS','SYMBOL_CONFIG','LEVERAGE_BRACKETS','POSITIONS_V2','POSITIONS_V3','OPEN_ORDERS','OPEN_ALGO_ORDERS','ADL_QUANTILE'):
    QUERIES[name]['scope']='OPTIONAL_SYMBOL'

HISTORY_PATHS={'ORDERS':'/fapi/v1/allOrders','ALGO_ORDERS':'/fapi/v1/allAlgoOrders','TRADES':'/fapi/v1/userTrades',
               'INCOME':'/fapi/v1/income','AMENDMENTS':'/fapi/v1/orderAmendment','FORCE_ORDERS':'/fapi/v1/forceOrders',
               'POSITION_MARGIN':'/fapi/v1/positionMargin/history'}
EXPORT_PATHS={'ORDERS':'/fapi/v1/order/asyn','TRADES':'/fapi/v1/trade/asyn','INCOME':'/fapi/v1/income/asyn'}
SINGLE_SHOT_GETS=set(EXPORT_PATHS.values())
PUBLIC_READS={q['path'] for q in QUERIES.values() if not q['private']}
PRIVATE_READS={q['path'] for q in QUERIES.values() if q['private']}|set(HISTORY_PATHS.values())|SINGLE_SHOT_GETS|{p+'/id' for p in EXPORT_PATHS.values()}
KEY_ONLY_READS={q['path'] for q in QUERIES.values() if q.get('key_only')}


def arguments(spec,scope,values):
    if not isinstance(values,dict) or values.keys()-spec['arguments'] or not spec['required']<=values.keys():raise ValueError('Sorgu argümanları eksik veya desteklenmiyor.')
    result=dict(values)
    for field,value in result.items():
        if field in ('limit','startTime','endTime','fromId','orderId','algoId'):
            if type(value) is not int or value<0 or value>=2**63 or field in ('limit','orderId','algoId') and value<1:raise ValueError('Sorgu sayısı/kimliği/zamanı geçersiz.')
            maximum=1500 if spec['shape']=='candles' else 1000 if spec['path'].endswith(('trades','Trades','fundingRate','historicalTrades','depth','rpiDepth')) else 500
            if field=='limit' and value>maximum:raise ValueError('Sorgu sayfa sınırı aşıldı.')
        elif field in ('interval','period'):
            allowed={'1m','3m','5m','15m','30m','1h','2h','4h','6h','8h','12h','1d','3d','1w','1M'} if field=='interval' else {'5m','15m','30m','1h','2h','4h','6h','12h','1d'}
            if not isinstance(value,str) or value not in allowed:raise ValueError('Sorgu zaman dilimi desteklenmiyor.')
        elif field=='contractType':
            if value not in ('PERPETUAL','CURRENT_QUARTER','NEXT_QUARTER'):raise ValueError('Sözleşme türü desteklenmiyor.')
        elif field in ('origClientOrderId','clientAlgoId'):
            if not isinstance(value,str) or not re.fullmatch(r'[.A-Za-z:/0-9_-]{1,36}',value):raise ValueError('Normal istemci emir kimliği geçersiz.')
    if 'startTime' in result and 'endTime' in result and result['startTime']>result['endTime']:raise ValueError('Sorgu zaman aralığı ters.')
    if spec['path'].endswith('/aggTrades') and 'fromId' in result and any(k in result for k in ('startTime','endTime')):raise ValueError('AggTrade kimliği ve zaman aralığı birlikte kullanılamaz.')
    if spec['path'].endswith('/openOrder') and len(result)!=1:raise ValueError('Tek bir normal emir kimliği gerekli.')
    if spec['path'].endswith('/algoOrder') and len(result)!=1:raise ValueError('Tek bir algo emir kimliği gerekli.')
    if spec['path'].endswith(('/depth','/rpiDepth')) and 'limit' in result and result['limit'] not in (5,10,20,50,100,500,1000):raise ValueError('Derinlik sayfa boyutu desteklenmiyor.')
    if spec['scope'] in ('SYMBOL','PAIR') or spec['scope']=='OPTIONAL_SYMBOL' and 'symbol' in scope:
        symbol=scope.get('symbol')
        if not isinstance(symbol,str) or not re.fullmatch('[A-Z0-9]{2,20}USDT',symbol):raise ValueError('Açık USDT sembol kapsamı gerekli.')
        result['pair' if spec['scope']=='PAIR' else 'symbol']=symbol
    return result
