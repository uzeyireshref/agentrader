# Spot resmi sözleşme incelemesi

15 Kasım 2026. Resmi REST belgesinden endpoint, parametre satırı ve kural maddeleri çıkarıldı. Commit e5f8489162e79fa1da6d0ea3ded3ce810b3637a0.

| İşlem | Yöntem ve yol | Önceki koleksiyonda |
|---|---|---|
| Test connectivity | GET /api/v3/ping | Var |
| Check server time | GET /api/v3/time | Var |
| Exchange information | GET /api/v3/exchangeInfo | Var |
| Query Execution Rules | GET /api/v3/executionRules | Var |
| Order book | GET /api/v3/depth | Var |
| Recent trades list | GET /api/v3/trades | Var |
| Old trade lookup | GET /api/v3/historicalTrades | Var |
| Historical Block Trades | GET /api/v3/historicalBlockTrades | Var |
| Compressed/Aggregate trades list | GET /api/v3/aggTrades | Var |
| Kline/Candlestick data | GET /api/v3/klines | Var |
| UIKlines | GET /api/v3/uiKlines | Var |
| Current average price | GET /api/v3/avgPrice | Var |
| 24hr ticker price change statistics | GET /api/v3/ticker/24hr | Var |
| Trading Day Ticker | GET /api/v3/ticker/tradingDay | Var |
| Symbol price ticker | GET /api/v3/ticker/price | Var |
| Symbol order book ticker | GET /api/v3/ticker/bookTicker | Var |
| Rolling window price change statistics | GET /api/v3/ticker | Var |
| Query Reference Price | GET /api/v3/referencePrice | Var |
| Query Reference Price Calculation | GET /api/v3/referencePrice/calculation | Var |
| New order (TRADE) | POST /api/v3/order | Var |
| Test new order (TRADE) | POST /api/v3/order/test | Var |
| Cancel order (TRADE) | DELETE /api/v3/order | Var |
| Cancel All Open Orders on a Symbol (TRADE) | DELETE /api/v3/openOrders | Var |
| Cancel an Existing Order and Send a New Order (TRADE) | POST /api/v3/order/cancelReplace | Var |
| Order Amend Keep Priority (TRADE) | PUT /api/v3/order/amend/keepPriority | Var |
| New OCO - Deprecated (TRADE) | POST /api/v3/order/oco | Var |
| New Order list - OCO (TRADE) | POST /api/v3/orderList/oco | Var |
| New Order list - OTO (TRADE) | POST /api/v3/orderList/oto | Var |
| New Order list - OTOCO (TRADE) | POST /api/v3/orderList/otoco | Var |
| New Order List - OPO (TRADE) | POST /api/v3/orderList/opo | Var |
| New Order List - OPOCO (TRADE) | POST /api/v3/orderList/opoco | Var |
| Cancel Order list (TRADE) | DELETE /api/v3/orderList | Var |
| New order using SOR (TRADE) | POST /api/v3/sor/order | Var |
| Test new order using SOR (TRADE) | POST /api/v3/sor/order/test | Var |
| Account information (USER_DATA) | GET /api/v3/account | Var |
| Query order (USER_DATA) | GET /api/v3/order | Var |
| Current open orders (USER_DATA) | GET /api/v3/openOrders | Var |
| All orders (USER_DATA) | GET /api/v3/allOrders | Var |
| Query Order list (USER_DATA) | GET /api/v3/orderList | Var |
| Query all Order lists (USER_DATA) | GET /api/v3/allOrderList | Var |
| Query Open Order lists (USER_DATA) | GET /api/v3/openOrderList | Var |
| Account trade list (USER_DATA) | GET /api/v3/myTrades | Var |
| Query Unfilled Order Count (USER_DATA) | GET /api/v3/rateLimit/order | Var |
| Query Prevented Matches (USER_DATA) | GET /api/v3/myPreventedMatches | Var |
| Query Allocations (USER_DATA) | GET /api/v3/myAllocations | Var |
| Query Commission Rates (USER_DATA) | GET /api/v3/account/commission | Var |
| Query Order Amendments (USER_DATA) | GET /api/v3/order/amendments | Var |
| Query relevant filters (USER_DATA) | GET /api/v3/myFilters | Var |

Önceki 555 işlem listesi tüm güncel API kapsamını garanti etmiyor. Belge ile koleksiyon arasındaki eksik kayıtlar aşağıdadır.



## Doğrulanan tasarım ihtiyaçları

Spot miktarı base veya quote varlık üzerinden ifade edilebilir. Pegged alanlarında fiyat zorunluluğu değişir. Iceberg için süre kısıtı vardır. Bağlı emirlerde liste kimliği ve bacak kimlikleri birlikte takip edilmelidir. Cancel-replace için iptal ve yeni emir sonuçları ayrı uzlaştırılmalıdır. Kullanıcı akışının abonelik yöntemi USD-M listenKey yaşam döngüsünden ayrıca modellenmelidir. Her alanın tam açıklaması spot-official-contracts.json içinde sürümlü kaynakla korunmuştur.
