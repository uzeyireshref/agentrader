# Portfolio Margin işlem envanteri

15 Kasım 2026. Classic ve Pro koleksiyonlarında toplam 126 işlem var. Mevcut botun yerel portfolio.py risk hesabı borsanın Portfolio Margin ürün desteği olarak değerlendirilmez.

| İşlem | Yöntem ve yol | Parametreler |
|---|---|---|
| Test Connectivity | GET /papi/v1/ping |  |
| CM Position ADL Quantile Estimation (USER_DATA) | GET /papi/v1/cm/adlQuantile | symbol, recvWindow, timestamp, signature |
| Cancel All CM Open Orders (TRADE) | DELETE /papi/v1/cm/allOpenOrders | symbol, recvWindow, timestamp, signature |
| Query All CM Orders (USER_DATA) | GET /papi/v1/cm/allOrders | symbol, pair, orderId, startTime, endTime, limit, recvWindow, timestamp, signature |
| Cancel All CM Open Conditional Orders (TRADE) | DELETE /papi/v1/cm/conditional/allOpenOrders | symbol, recvWindow, timestamp, signature |
| Query All CM Conditional Orders (USER_DATA) | GET /papi/v1/cm/conditional/allOrders | symbol, strategyId, startTime, endTime, limit, recvWindow, timestamp, signature |
| Query Current CM Open Conditional Order (USER_DATA) | GET /papi/v1/cm/conditional/openOrder | symbol, strategyId, newClientStrategyId, recvWindow, timestamp, signature |
| Query All Current CM Open Conditional Orders (USER_DATA) | GET /papi/v1/cm/conditional/openOrders | symbol, recvWindow, timestamp, signature |
| Cancel CM Conditional Order (TRADE) | DELETE /papi/v1/cm/conditional/order | symbol, strategyId, newClientStrategyId, recvWindow, timestamp, signature |
| New CM Conditional Order (TRADE) | POST /papi/v1/cm/conditional/order | symbol, side, positionSide, strategyType, timeInForce, quantity, reduceOnly, price, workingType, priceProtect, newClientStrategyId, stopPrice, activationPrice, callbackRate, recvWindow, timestamp, signature |
| Query CM Conditional Order History (USER_DATA) | GET /papi/v1/cm/conditional/orderHistory | symbol, strategyId, newClientStrategyId, recvWindow, timestamp, signature |
| Query User's CM Force Orders (USER_DATA) | GET /papi/v1/cm/forceOrders | symbol, autoCloseType, startTime, endTime, limit, recvWindow, timestamp, signature |
| Query Current CM Open Order (USER_DATA) | GET /papi/v1/cm/openOrder | symbol, orderId, origClientOrderId, recvWindow, timestamp, signature |
| Query All Current CM Open Orders (USER_DATA) | GET /papi/v1/cm/openOrders | symbol, pair, recvWindow, timestamp, signature |
| Cancel CM Order (TRADE) | DELETE /papi/v1/cm/order | symbol, orderId, origClientOrderId, recvWindow, timestamp, signature |
| Modify CM Order (TRADE) | PUT /papi/v1/cm/order | orderId, origClientOrderId, symbol, side, quantity, price, priceMatch, modifyId, recvWindow, timestamp, signature |
| New CM Order (TRADE) | POST /papi/v1/cm/order | symbol, side, positionSide, type, timeInForce, quantity, reduceOnly, price, priceMatch, newClientOrderId, newOrderRespType, recvWindow, timestamp, signature |
| Query CM Order (USER_DATA) | GET /papi/v1/cm/order | symbol, orderId, origClientOrderId, recvWindow, timestamp, signature |
| Query CM Modify Order History (TRADE) | GET /papi/v1/cm/orderAmendment | symbol, orderId, origClientOrderId, startTime, endTime, limit, recvWindow, timestamp, signature |
| CM Account Trade List (USER_DATA) | GET /papi/v1/cm/userTrades | symbol, pair, startTime, endTime, fromId, limit, recvWindow, timestamp, signature |
| Cancel Margin Account All Open Orders on a Symbol (TRADE) | DELETE /papi/v1/margin/allOpenOrders | symbol, recvWindow, timestamp, signature |
| Query Margin Account's all OCO (USER_DATA) | GET /papi/v1/margin/allOrderList | fromId, startTime, endTime, limit, recvWindow, timestamp, signature |
| Query All Margin Account Orders (USER_DATA) | GET /papi/v1/margin/allOrders | symbol, orderId, startTime, endTime, limit, recvWindow, timestamp, signature |
| Query User's Margin Force Orders (USER_DATA) | GET /papi/v1/margin/forceOrders | startTime, endTime, current, size, recvWindow, timestamp, signature |
| Margin Account Trade List (USER_DATA) | GET /papi/v1/margin/myTrades | symbol, orderId, startTime, endTime, fromId, limit, recvWindow, timestamp, signature |
| Query Margin Account's Open OCO (USER_DATA) | GET /papi/v1/margin/openOrderList | recvWindow, timestamp, signature |
| Query Current Margin Open Order (USER_DATA) | GET /papi/v1/margin/openOrders | symbol, recvWindow, timestamp, signature |
| Cancel Margin Account Order (TRADE) | DELETE /papi/v1/margin/order | symbol, orderId, origClientOrderId, newClientOrderId, recvWindow, timestamp, signature |
| New Margin Order (TRADE) | POST /papi/v1/margin/order | symbol, side, type, quantity, quoteOrderQty, price, stopPrice, newClientOrderId, newOrderRespType, icebergQty, sideEffectType, timeInForce, selfTradePreventionMode, autoRepayAtCancel, recvWindow, timestamp, signature |
| Query Margin Account Order (USER_DATA) | GET /papi/v1/margin/order | symbol, orderId, origClientOrderId, recvWindow, timestamp, signature |
| Margin Account New OCO (TRADE) | POST /papi/v1/margin/order/oco | symbol, listClientOrderId, side, quantity, limitClientOrderId, price, limitIcebergQty, stopClientOrderId, stopPrice, stopLimitPrice, stopIcebergQty, stopLimitTimeInForce, newOrderRespType, sideEffectType, recvWindow, timestamp, signature |
| Cancel Margin Account OCO Orders (TRADE) | DELETE /papi/v1/margin/orderList | symbol, orderListId, listClientOrderId, newClientOrderId, recvWindow, timestamp, signature |
| Query Margin Account's OCO (USER_DATA) | GET /papi/v1/margin/orderList | orderListId, origClientOrderId, recvWindow, timestamp, signature |
| Margin Account Repay Debt (TRADE) | POST /papi/v1/margin/repay-debt | asset, amount, specifyRepayAssets, recvWindow, timestamp, signature |
| Margin Account Borrow (MARGIN) | POST /papi/v1/marginLoan | asset, amount, recvWindow, timestamp, signature |
| Margin Account Repay (MARGIN) | POST /papi/v1/repayLoan | asset, amount, recvWindow, timestamp, signature |
| UM Position ADL Quantile Estimation (USER_DATA) | GET /papi/v1/um/adlQuantile | symbol, recvWindow, timestamp, signature |
| Query Current UM Open Algo Order (USER_DATA) | GET /papi/v1/um/algo/algoOrder | algoId, clientAlgoId, recvWindow, timestamp, signature |
| Query UM Algo Order History (USER_DATA) | GET /papi/v1/um/algo/allAlgoOrders | symbol, algoId, startTime, endTime, limit, recvWindow, timestamp, signature |
| Cancel All UM Algo Open Orders (TRADE) | DELETE /papi/v1/um/algo/allOpenOrders | symbol, recvWindow, timestamp, signature |
| Query All Current UM Open Algo Orders (USER_DATA) | GET /papi/v1/um/algo/openAlgoOrders | algoType, symbol, algoId, recvWindow, timestamp, signature |
| Cancel UM Algo Order (TRADE) | DELETE /papi/v1/um/algo/order | algoId, clientAlgoId, recvWindow, timestamp, signature |
| New UM Algo Order (TRADE) | POST /papi/v1/um/algo/order | algoType, symbol, side, positionSide, type, timeInForce, quantity, price, triggerPrice, workingType, priceMatch, closePosition, priceProtect, reduceOnly, activatePrice, callbackRate, clientAlgoId, newOrderRespType, selfTradePreventionMode, goodTillDate, recvWindow, timestamp, signature |
| Cancel All UM Open Orders (TRADE) | DELETE /papi/v1/um/allOpenOrders | symbol, recvWindow, timestamp, signature |
| Query All UM Orders (USER_DATA) | GET /papi/v1/um/allOrders | symbol, orderId, startTime, endTime, limit, recvWindow, timestamp, signature |
| Get UM Futures BNB Burn Status (USER_DATA) | GET /papi/v1/um/feeBurn | recvWindow, timestamp, signature |
| Toggle BNB Burn On UM Futures Trade (TRADE) | POST /papi/v1/um/feeBurn | feeBurn, recvWindow, timestamp, signature |
| Query User's UM Force Orders (USER_DATA) | GET /papi/v1/um/forceOrders | symbol, autoCloseType, startTime, endTime, limit, recvWindow, timestamp, signature |
| Query Current UM Open Order (USER_DATA) | GET /papi/v1/um/openOrder | symbol, orderId, origClientOrderId, recvWindow, timestamp, signature |
| Query All Current UM Open Orders (USER_DATA) | GET /papi/v1/um/openOrders | symbol, recvWindow, timestamp, signature |
| Cancel UM Order (TRADE) | DELETE /papi/v1/um/order | symbol, orderId, origClientOrderId, recvWindow, timestamp, signature |
| Modify UM Order (TRADE) | PUT /papi/v1/um/order | orderId, origClientOrderId, symbol, side, quantity, price, priceMatch, modifyId, recvWindow, timestamp, signature |
| New UM Order (TRADE) | POST /papi/v1/um/order | symbol, side, positionSide, type, timeInForce, quantity, reduceOnly, price, newClientOrderId, newOrderRespType, priceMatch, selfTradePreventionMode, goodTillDate, recvWindow, timestamp, signature |
| Query UM Order (USER_DATA) | GET /papi/v1/um/order | symbol, orderId, origClientOrderId, recvWindow, timestamp, signature |
| Query UM Modify Order History (TRADE) | GET /papi/v1/um/orderAmendment | symbol, orderId, origClientOrderId, startTime, endTime, limit, recvWindow, timestamp, signature |
| Futures TradFi Perps Contract (USER_DATA) | POST /papi/v1/um/stock/contract | recvWindow, timestamp, signature |
| UM Account Trade List (USER_DATA) | GET /papi/v1/um/userTrades | symbol, startTime, endTime, fromId, limit, recvWindow, timestamp, signature |
| Close User Data Stream (USER_STREAM) | DELETE /papi/v1/listenKey |  |
| Keepalive User Data Stream (USER_STREAM) | PUT /papi/v1/listenKey |  |
| Start User Data Stream (USER_STREAM) | POST /papi/v1/listenKey |  |
| Account Information (USER_DATA) | GET /papi/v1/account | recvWindow, timestamp, signature |
| Fund Collection by Asset (TRADE) | POST /papi/v1/asset-collection | asset, amount, futureType, recvWindow, timestamp, signature |
| Fund Auto-collection (TRADE) | POST /papi/v1/auto-collection | recvWindow, timestamp, signature |
| Account Balance (USER_DATA) | GET /papi/v1/balance | asset, recvWindow, timestamp, signature |
| BNB transfer (TRADE) | POST /papi/v1/bnb-transfer | amount, transferSide, recvWindow, timestamp, signature |
| Get CM Account Detail (USER_DATA) | GET /papi/v1/cm/account | recvWindow, timestamp, signature |
| Get User Commission Rate for CM (USER_DATA) | GET /papi/v1/cm/commissionRate | symbol, recvWindow, timestamp, signature |
| Get CM Income History (USER_DATA) | GET /papi/v1/cm/income | symbol, incomeType, startTime, endTime, limit, recvWindow, timestamp, signature |
| Change CM Initial Leverage (TRADE) | POST /papi/v1/cm/leverage | symbol, leverage, recvWindow, timestamp, signature |
| CM Notional and Leverage Brackets (USER_DATA) | GET /papi/v1/cm/leverageBracket | symbol, recvWindow, timestamp, signature |
| Query CM Position Information (USER_DATA) | GET /papi/v1/cm/positionRisk | marginAsset, pair, recvWindow, timestamp, signature |
| Change CM Position Mode (TRADE) | POST /papi/v1/cm/positionSide/dual | dualSidePosition, recvWindow, timestamp, signature |
| Get CM Current Position Mode (USER_DATA) | GET /papi/v1/cm/positionSide/dual | recvWindow, timestamp, signature |
| Get Margin Borrow/Loan Interest History (USER_DATA) | GET /papi/v1/margin/marginInterestHistory | asset, startTime, endTime, current, size, archived, recvWindow, timestamp, signature |
| Query Margin Loan Record (USER_DATA) | GET /papi/v1/margin/marginLoan | asset, txId, startTime, endTime, current, size, archived, recvWindow, timestamp, signature |
| Margin Max Borrow (USER_DATA) | GET /papi/v1/margin/maxBorrowable | asset, recvWindow, timestamp, signature |
| Query Margin Max Withdraw (USER_DATA) | GET /papi/v1/margin/maxWithdraw | asset, recvWindow, timestamp, signature |
| Query Margin repay Record (USER_DATA) | GET /papi/v1/margin/repayLoan | asset, txId, startTime, endTime, current, size, archived, recvWindow, timestamp, signature |
| Query Portfolio Margin Negative Balance Interest History (USER_DATA) | GET /papi/v1/portfolio/interest-history | asset, startTime, endTime, size, recvWindow, timestamp, signature |
| Query User Negative Balance Auto Exchange Record (USER_DATA) | GET /papi/v1/portfolio/negative-balance-exchange-record | startTime, endTime, recvWindow, timestamp, signature |
| Query User Rate Limit (USER_DATA) | GET /papi/v1/rateLimit/order | recvWindow, timestamp, signature |
| Repay futures Negative Balance (USER_DATA) | POST /papi/v1/repay-futures-negative-balance | recvWindow, timestamp, signature |
| Change Auto-repay-futures Status (TRADE) | POST /papi/v1/repay-futures-switch | autoRepay, recvWindow, timestamp, signature |
| Get Auto-repay-futures Status (USER_DATA) | GET /papi/v1/repay-futures-switch | recvWindow, timestamp, signature |
| Get UM Account Detail (USER_DATA) | GET /papi/v1/um/account | recvWindow, timestamp, signature |
| UM Futures Account Configuration (USER_DATA) | GET /papi/v1/um/accountConfig | recvWindow, timestamp, signature |
| Portfolio Margin UM Trading Quantitative Rules Indicators (USER_DATA) | GET /papi/v1/um/apiTradingStatus | symbol, recvWindow, timestamp, signature |
| Get User Commission Rate for UM (USER_DATA) | GET /papi/v1/um/commissionRate | symbol, recvWindow, timestamp, signature |
| Get UM Income History (USER_DATA) | GET /papi/v1/um/income | symbol, incomeType, startTime, endTime, limit, recvWindow, timestamp, signature |
| Get Download Id For UM Futures Transaction History (USER_DATA) | GET /papi/v1/um/income/asyn | startTime, endTime, recvWindow, timestamp, signature |
| Get UM Futures Transaction Download Link by Id (USER_DATA) | GET /papi/v1/um/income/asyn/id | downloadId, recvWindow, timestamp, signature |
| Change UM Initial Leverage (TRADE) | POST /papi/v1/um/leverage | symbol, leverage, recvWindow, timestamp, signature |
| UM Notional and Leverage Brackets (USER_DATA) | GET /papi/v1/um/leverageBracket | symbol, recvWindow, timestamp, signature |
| Get Download Id For UM Futures Order History (USER_DATA) | GET /papi/v1/um/order/asyn | startTime, endTime, recvWindow, timestamp, signature |
| Get UM Futures Order Download Link by Id (USER_DATA) | GET /papi/v1/um/order/asyn/id | downloadId, recvWindow, timestamp, signature |
| Query UM Position Information (USER_DATA) | GET /papi/v1/um/positionRisk | symbol, recvWindow, timestamp, signature |
| Change UM Position Mode (TRADE) | POST /papi/v1/um/positionSide/dual | dualSidePosition, recvWindow, timestamp, signature |
| Get UM Current Position Mode (USER_DATA) | GET /papi/v1/um/positionSide/dual | recvWindow, timestamp, signature |
| UM Futures Symbol Configuration (USER_DATA) | GET /papi/v1/um/symbolConfig | symbol, recvWindow, timestamp, signature |
| Get Download Id For UM Futures Trade History (USER_DATA) | GET /papi/v1/um/trade/asyn | startTime, endTime, recvWindow, timestamp, signature |
| Get UM Futures Trade Download Link by Id (USER_DATA) | GET /papi/v1/um/trade/asyn/id | downloadId, recvWindow, timestamp, signature |
| Get UM Account Detail V2 (USER_DATA) | GET /papi/v2/um/account | recvWindow, timestamp, signature |
| Query Portfolio Margin Asset Index Price (MARKET_DATA) | GET /sapi/v1/portfolio/asset-index-price | asset |
| Portfolio Margin Collateral Rate (MARKET_DATA) | GET /sapi/v1/portfolio/collateralRate |  |
| Get Portfolio Margin Asset Leverage (USER_DATA) | GET /sapi/v1/portfolio/margin-asset-leverage | timestamp, signature |
| Portfolio Margin Pro Tiered Collateral Rate (USER_DATA) | GET /sapi/v2/portfolio/collateralRate | recvWindow, timestamp, signature |
| Get Portfolio Margin Pro Account Info (USER_DATA) | GET /sapi/v1/portfolio/account | recvWindow, timestamp, signature |
| Fund Collection by Asset (USER_DATA) | POST /sapi/v1/portfolio/asset-collection | asset, amount, futureType, recvWindow, timestamp, signature |
| Fund Auto-collection (USER_DATA) | POST /sapi/v1/portfolio/auto-collection | recvWindow, timestamp, signature |
| Get Portfolio Margin Pro Account Balance (USER_DATA) | GET /sapi/v1/portfolio/balance | asset, recvWindow, timestamp, signature |
| BNB transfer (USER_DATA) | POST /sapi/v1/portfolio/bnb-transfer | amount, transferSide, recvWindow, timestamp, signature |
| Get Delta Mode Status (USER_DATA) | GET /sapi/v1/portfolio/delta-mode | recvWindow, timestamp, signature |
| Switch Delta Mode (TRADE) | POST /sapi/v1/portfolio/delta-mode | deltaEnabled, recvWindow, timestamp, signature |
| Get Transferable Earn Asset Balance for Portfolio Margin (USER_DATA) | GET /sapi/v1/portfolio/earn-asset-balance | asset, transferType, recvWindow, timestamp, signature |
| Transfer LDUSDT/RWUSD for Portfolio Margin (TRADE) | POST /sapi/v1/portfolio/earn-asset-transfer | asset, transferType, amount, recvWindow, timestamp, signature |
| Query Portfolio Margin Pro Negative Balance Interest History (USER_DATA) | GET /sapi/v1/portfolio/interest-history | asset, startTime, endTime, size, recvWindow, timestamp, signature |
| Delete Margin Call Level (USER_DATA) | DELETE /sapi/v1/portfolio/margin-call-level | recvWindow, timestamp, signature |
| Get Margin Call Level (USER_DATA) | GET /sapi/v1/portfolio/margin-call-level | recvWindow, timestamp, signature |
| Set Margin Call Level (USER_DATA) | POST /sapi/v1/portfolio/margin-call-level | marginCallLevel, recvWindow, timestamp, signature |
| Query Portfolio Margin Pro Bankruptcy Loan Amount (USER_DATA) | GET /sapi/v1/portfolio/pmLoan | recvWindow, timestamp, signature |
| Query Portfolio Margin Pro Bankruptcy Loan Repay History (USER_DATA) | GET /sapi/v1/portfolio/pmloan-history | startTime, endTime, size, current, recvWindow, timestamp, signature |
| Portfolio Margin Pro Bankruptcy Loan Repay (TRADE) | POST /sapi/v1/portfolio/repay | recvWindow, timestamp, signature |
| Repay futures Negative Balance (USER_DATA) | POST /sapi/v1/portfolio/repay-futures-negative-balance | recvWindow, timestamp, signature |
| Change Auto-repay-futures Status (TRADE) | POST /sapi/v1/portfolio/repay-futures-switch | autoRepay, recvWindow, timestamp, signature |
| Get Auto-repay-futures Status (USER_DATA) | GET /sapi/v1/portfolio/repay-futures-switch | recvWindow, timestamp, signature |
| Get Portfolio Margin Pro SPAN Account Info (USER_DATA) | GET /sapi/v2/portfolio/account | recvWindow, timestamp, signature |

Ayrıntılı hesap/teminat ve emir sözleşmesi incelemesi bekliyor.
