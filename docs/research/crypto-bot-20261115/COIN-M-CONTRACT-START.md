# COIN-M sözleşme incelemesi

15 Kasım 2026. Resmi koleksiyondaki 64 işlem aşağıdadır. Temel ürün farkı kontrat adedi, contractSize, coin teminatı ve coin cinsi muhasebedir. USD-M planındaki USDT miktar/bütçe varsayımları bu ürün için uyarlanmalıdır.

| İşlem | Yöntem | Yol | Parametreler |
|---|---|---|---|
| Compressed/Aggregate Trades List | GET | /dapi/v1/aggTrades | symbol, fromId, startTime, endTime, limit |
| Query Index Price Constituents | GET | /dapi/v1/constituents | symbol |
| Continuous Contract Kline/Candlestick Data | GET | /dapi/v1/continuousKlines | pair, contractType, interval, startTime, endTime, limit |
| Order Book | GET | /dapi/v1/depth | symbol, limit |
| Exchange Information | GET | /dapi/v1/exchangeInfo |  |
| Get Funding Rate Info | GET | /dapi/v1/fundingInfo |  |
| Get Funding Rate History of Perpetual Futures | GET | /dapi/v1/fundingRate | symbol, startTime, endTime, limit |
| Old Trades Lookup (MARKET_DATA) | GET | /dapi/v1/historicalTrades | symbol, limit, fromId |
| Index Price Kline/Candlestick Data | GET | /dapi/v1/indexPriceKlines | pair, interval, startTime, endTime, limit |
| Kline/Candlestick Data | GET | /dapi/v1/klines | symbol, interval, startTime, endTime, limit |
| Mark Price Kline/Candlestick Data | GET | /dapi/v1/markPriceKlines | symbol, interval, startTime, endTime, limit |
| Open Interest | GET | /dapi/v1/openInterest | symbol |
| Test Connectivity | GET | /dapi/v1/ping |  |
| Index Price and Mark Price | GET | /dapi/v1/premiumIndex | symbol, pair |
| Premium index Kline Data | GET | /dapi/v1/premiumIndexKlines | symbol, interval, startTime, endTime, limit |
| 24hr Ticker Price Change Statistics | GET | /dapi/v1/ticker/24hr | symbol, pair |
| Symbol Order Book Ticker | GET | /dapi/v1/ticker/bookTicker | symbol, pair |
| Symbol Price Ticker | GET | /dapi/v1/ticker/price | symbol, pair |
| Check Server time | GET | /dapi/v1/time |  |
| Recent Trades List | GET | /dapi/v1/trades | symbol, limit |
| Basis | GET | /futures/data/basis | pair, contractType, period, limit, startTime, endTime |
| Long/Short Ratio | GET | /futures/data/globalLongShortAccountRatio | pair, period, contractType, limit, startTime, endTime |
| Open Interest Statistics | GET | /futures/data/openInterestHist | pair, contractType, period, limit, startTime, endTime |
| Taker Buy/Sell Volume | GET | /futures/data/takerBuySellVol | pair, contractType, period, limit, startTime, endTime |
| Top Trader Long/Short Account Ratio | GET | /futures/data/topLongShortAccountRatio | pair, period, contractType, limit, startTime, endTime |
| Top Trader Long/Short Position Ratio | GET | /futures/data/topLongShortPositionRatio | pair, period, contractType, limit, startTime, endTime |
| Position ADL Quantile Estimation (USER_DATA) | GET | /dapi/v1/adlQuantile | symbol, recvWindow, timestamp, signature |
| Cancel All Open Orders (TRADE) | DELETE | /dapi/v1/allOpenOrders | symbol, recvWindow, timestamp, signature |
| All Orders (USER_DATA) | GET | /dapi/v1/allOrders | symbol, pair, orderId, startTime, endTime, limit, recvWindow, timestamp, signature |
| Cancel Multiple Orders (TRADE) | DELETE | /dapi/v1/batchOrders | symbol, orderIdList, origClientOrderIdList, recvWindow, timestamp, signature |
| Modify Multiple Orders (TRADE) | PUT | /dapi/v1/batchOrders | batchOrders, recvWindow, timestamp, signature |
| Place Multiple Orders (TRADE) | POST | /dapi/v1/batchOrders | batchOrders, recvWindow, timestamp, signature |
| Auto-Cancel All Open Orders (TRADE) | POST | /dapi/v1/countdownCancelAll | symbol, countdownTime, recvWindow, timestamp, signature |
| User's Force Orders (USER_DATA) | GET | /dapi/v1/forceOrders | symbol, autoCloseType, startTime, endTime, limit, recvWindow, timestamp, signature |
| Change Initial Leverage (TRADE) | POST | /dapi/v1/leverage | symbol, leverage, recvWindow, timestamp, signature |
| Change Margin Type (TRADE) | POST | /dapi/v1/marginType | symbol, marginType, recvWindow, timestamp, signature |
| Query Current Open Order (USER_DATA) | GET | /dapi/v1/openOrder | symbol, orderId, origClientOrderId, recvWindow, timestamp, signature |
| Current All Open Orders (USER_DATA) | GET | /dapi/v1/openOrders | symbol, pair, recvWindow, timestamp, signature |
| Cancel Order (TRADE) | DELETE | /dapi/v1/order | symbol, orderId, origClientOrderId, recvWindow, timestamp, signature |
| Modify Order (TRADE) | PUT | /dapi/v1/order | orderId, origClientOrderId, symbol, side, quantity, price, priceMatch, modifyId, recvWindow, timestamp, signature |
| New Order (TRADE) | POST | /dapi/v1/order | symbol, side, positionSide, type, reduceOnly, quantity, price, newClientOrderId, stopPrice, closePosition, activationPrice, callbackRate, timeInForce, workingType, priceProtect, newOrderRespType, priceMatch, selfTradePreventionMode, recvWindow, timestamp, signature |
| Query Order (USER_DATA) | GET | /dapi/v1/order | symbol, orderId, origClientOrderId, recvWindow, timestamp, signature |
| Get Order Modify History (USER_DATA) | GET | /dapi/v1/orderAmendment | symbol, orderId, origClientOrderId, startTime, endTime, limit, recvWindow, timestamp, signature |
| Modify Isolated Position Margin (TRADE) | POST | /dapi/v1/positionMargin | symbol, positionSide, amount, type, recvWindow, timestamp, signature |
| Get Position Margin Change History (TRADE) | GET | /dapi/v1/positionMargin/history | symbol, type, startTime, endTime, limit, recvWindow, timestamp, signature |
| Position Information (USER_DATA) | GET | /dapi/v1/positionRisk | marginAsset, pair, recvWindow, timestamp, signature |
| Change Position Mode (TRADE) | POST | /dapi/v1/positionSide/dual | dualSidePosition, recvWindow, timestamp, signature |
| Account Trade List (USER_DATA) | GET | /dapi/v1/userTrades | symbol, pair, orderId, startTime, endTime, fromId, limit, recvWindow, timestamp, signature |
| Close User Data Stream (USER_STREAM) | DELETE | /dapi/v1/listenKey |  |
| Keepalive User Data Stream (USER_STREAM) | PUT | /dapi/v1/listenKey |  |
| Start User Data Stream (USER_STREAM) | POST | /dapi/v1/listenKey |  |
| Account Information (USER_DATA) | GET | /dapi/v1/account | recvWindow, timestamp, signature |
| Futures Account Balance (USER_DATA) | GET | /dapi/v1/balance | recvWindow, timestamp, signature |
| User Commission Rate (USER_DATA) | GET | /dapi/v1/commissionRate | symbol, recvWindow, timestamp, signature |
| Get Income History (USER_DATA) | GET | /dapi/v1/income | symbol, incomeType, startTime, endTime, limit, recvWindow, timestamp, signature |
| Get Download Id For Futures Transaction History (USER_DATA) | GET | /dapi/v1/income/asyn | startTime, endTime, recvWindow, timestamp, signature |
| Get Futures Transaction History Download Link by Id (USER_DATA) | GET | /dapi/v1/income/asyn/id | downloadId, recvWindow, timestamp, signature |
| Notional Bracket for Pair (USER_DATA) | GET | /dapi/v1/leverageBracket | pair, recvWindow, timestamp, signature |
| Get Download Id For Futures Order History (USER_DATA) | GET | /dapi/v1/order/asyn | startTime, endTime, recvWindow, timestamp, signature |
| Get Futures Order History Download Link by Id (USER_DATA) | GET | /dapi/v1/order/asyn/id | downloadId, recvWindow, timestamp, signature |
| Get Current Position Mode (USER_DATA) | GET | /dapi/v1/positionSide/dual | recvWindow, timestamp, signature |
| Get Download Id For Futures Trade History (USER_DATA) | GET | /dapi/v1/trade/asyn | startTime, endTime, recvWindow, timestamp, signature |
| Get Futures Trade Download Link by Id (USER_DATA) | GET | /dapi/v1/trade/asyn/id | downloadId, recvWindow, timestamp, signature |
| Notional Bracket for Symbol (USER_DATA) | GET | /dapi/v2/leverageBracket | symbol, recvWindow, timestamp, signature |

Emir doğrulama, hesap olayları, vade/uzlaşma ve ters kontrat muhasebesi ayrıntılı araştırma bekliyor.
