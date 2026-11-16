# USD-M REST işlem envanteri

95 işlem için güncel adaptör izinleri ve kaynak referansları. Kaynakta adresin bulunması komuttan uçtan uca kabulü kanıtlamaz. Aynı adresin GET ve POST işlemleri ayrı satırlardadır.

| Kimlik | İşlem | Yöntem ve yol | Adaptör | Kaynak referansı |
|---|---|---|---|---|
| UM-018 | Hesap özeti V2 | GET /fapi/v2/account | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-019 | Hesap özeti V3 | GET /fapi/v3/account | İzinli | agentrader/__main__.py#34, agentrader/bot/demo_readiness.py#59, agentrader/bot/execution.py#177 |
| UM-020 | Bakiye V2 | GET /fapi/v2/balance | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-021 | Bakiye V3 | GET /fapi/v3/balance | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-022 | Hesap yapılandırması | GET /fapi/v1/accountConfig | İzinli | agentrader/__main__.py#35, agentrader/bot/demo_readiness.py#56, agentrader/bot/grid_runner.py#371 |
| UM-023 | İşlem kısıtları ve sayısal kurallar | GET /fapi/v1/apiTradingStatus | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-024 | BNB komisyon indirimi durumunu oku | GET /fapi/v1/feeBurn | İzinli | agentrader/bot/account_commands.py#26 |
| UM-025 | BNB komisyon indirimi tercihini değiştir | POST /fapi/v1/feeBurn | İzinli | agentrader/bot/account_commands.py#26 |
| UM-026 | Çoklu varlık modunu oku | GET /fapi/v1/multiAssetsMargin | İzinli | agentrader/bot/account_commands.py#25 |
| UM-027 | Hedge veya one-way modunu oku | GET /fapi/v1/positionSide/dual | İzinli | agentrader/__main__.py#37, agentrader/bot/account_commands.py#24, agentrader/bot/account_ownership.py#42 |
| UM-028 | Emir geçmişi indirme işini başlat | GET /fapi/v1/order/asyn | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-029 | Gerçekleşme geçmişi indirme işini başlat | GET /fapi/v1/trade/asyn | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-030 | Gelir geçmişi indirme işini başlat | GET /fapi/v1/income/asyn | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-031 | Emir geçmişi indirme bağlantısını sorgula | GET /fapi/v1/order/asyn/id | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-032 | Gerçekleşme geçmişi indirme bağlantısını sorgula | GET /fapi/v1/trade/asyn/id | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-033 | Gelir geçmişi indirme bağlantısını sorgula | GET /fapi/v1/income/asyn/id | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-034 | Gelir ve komisyon kayıtları | GET /fapi/v1/income | İzinli | agentrader/bot/history.py#85 |
| UM-035 | Kaldıraç ve bakım marjı basamakları | GET /fapi/v1/leverageBracket | İzinli | agentrader/bot/account_commands.py#116, agentrader/bot/grid.py#92, agentrader/bot/grid_runner.py#376 |
| UM-036 | Kullanıcı istek limitlerini oku | GET /fapi/v1/rateLimit/order | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-037 | Sembolün kaldıraç ve teminat ayarları | GET /fapi/v1/symbolConfig | İzinli | agentrader/bot/account_commands.py#77, agentrader/bot/account_ownership.py#43, agentrader/bot/grid.py#101 |
| UM-038 | Kullanıcı komisyon oranları | GET /fapi/v1/commissionRate | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-082 | Çoklu varlık modunu değiştir | POST /fapi/v1/multiAssetsMargin | İzinli | agentrader/bot/account_commands.py#25 |
| UM-083 | Hedge veya one-way modunu değiştir | POST /fapi/v1/positionSide/dual | İzinli | agentrader/__main__.py#37, agentrader/bot/account_commands.py#24, agentrader/bot/account_ownership.py#42 |
| UM-084 | Hesabın gerçekleşmiş işlemlerini oku | GET /fapi/v1/userTrades | İzinli | agentrader/bot/history.py#24 |
| UM-085 | Normal emir geçmişi | GET /fapi/v1/allOrders | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-086 | Normal emirler için zamanlayıcılı iptal | POST /fapi/v1/countdownCancelAll | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-087 | Koşullu emir sorgula | GET /fapi/v1/algoOrder | İzinli | agentrader/bot/account_ownership.py#100, agentrader/bot/execution.py#20, agentrader/bot/execution.py#110 |
| UM-088 | Koşullu emir oluştur | POST /fapi/v1/algoOrder | İzinli | agentrader/bot/account_ownership.py#100, agentrader/bot/execution.py#20, agentrader/bot/execution.py#110 |
| UM-089 | Tek koşullu emri iptal et | DELETE /fapi/v1/algoOrder | İzinli | agentrader/bot/account_ownership.py#100, agentrader/bot/execution.py#20, agentrader/bot/execution.py#110 |
| UM-090 | Sembolde tüm koşullu emirleri iptal et | DELETE /fapi/v1/algoOpenOrders | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-091 | Sembolde tüm normal emirleri iptal et | DELETE /fapi/v1/allOpenOrders | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-092 | Birden fazla limit emri değiştir | PUT /fapi/v1/batchOrders | İzinli | agentrader/bot/batch_cancel.py#75, agentrader/bot/batch_create.py#99, agentrader/bot/order_amend.py#321 |
| UM-093 | Birden fazla emir oluştur | POST /fapi/v1/batchOrders | İzinli | agentrader/bot/batch_cancel.py#75, agentrader/bot/batch_create.py#99, agentrader/bot/order_amend.py#321 |
| UM-094 | Birden fazla normal emri iptal et | DELETE /fapi/v1/batchOrders | İzinli | agentrader/bot/batch_cancel.py#75, agentrader/bot/batch_create.py#99, agentrader/bot/order_amend.py#321 |
| UM-095 | Normal emir sorgula | GET /fapi/v1/order | İzinli | agentrader/bot/account_ownership.py#75, agentrader/bot/batch_cancel.py#37, agentrader/bot/batch_cancel.py#29 |
| UM-096 | Limit emir fiyatı veya miktarı değiştir | PUT /fapi/v1/order | İzinli | agentrader/bot/account_ownership.py#75, agentrader/bot/batch_cancel.py#37, agentrader/bot/batch_cancel.py#29 |
| UM-097 | Normal emir oluştur | POST /fapi/v1/order | İzinli | agentrader/bot/account_ownership.py#75, agentrader/bot/batch_cancel.py#37, agentrader/bot/batch_cancel.py#29 |
| UM-098 | Tek normal emri iptal et | DELETE /fapi/v1/order | İzinli | agentrader/bot/account_ownership.py#75, agentrader/bot/batch_cancel.py#37, agentrader/bot/batch_cancel.py#29 |
| UM-099 | Sembol kaldıraç ayarını değiştir | POST /fapi/v1/leverage | İzinli | agentrader/bot/account_commands.py#19, agentrader/bot/grid.py#100 |
| UM-100 | Cross veya isolated teminat modu seç | POST /fapi/v1/marginType | İzinli | agentrader/bot/account_commands.py#21 |
| UM-101 | Açık koşullu emirleri oku | GET /fapi/v1/openAlgoOrders | İzinli | agentrader/bot/account_commands.py#111, agentrader/bot/account_ownership.py#192, agentrader/bot/demo_readiness.py#60 |
| UM-102 | Açık normal emirleri oku | GET /fapi/v1/openOrders | İzinli | agentrader/__main__.py#36, agentrader/bot/account_commands.py#111, agentrader/bot/account_ownership.py#191 |
| UM-103 | TradFi perpetual sözleşme işlemi | POST /fapi/v1/stock/contract | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-104 | Emir değiştirme geçmişi | GET /fapi/v1/orderAmendment | İzinli | agentrader/bot/order_amend.py#182 |
| UM-105 | İzole teminat değişim geçmişi | GET /fapi/v1/positionMargin/history | İzinli | İşlem referansı bulunamadı |
| UM-106 | İzole pozisyon teminatını ekle veya azalt | POST /fapi/v1/positionMargin | İzinli | agentrader/bot/isolated_margin.py#21 |
| UM-107 | Hesaba ait ADL sırası göstergesi | GET /fapi/v1/adlQuantile | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-108 | Pozisyon bilgisi V2 | GET /fapi/v2/positionRisk | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-109 | Pozisyon bilgisi V3 | GET /fapi/v3/positionRisk | İzinli | agentrader/bot/account_commands.py#110, agentrader/bot/account_ownership.py#167, agentrader/bot/demo_readiness.py#59 |
| UM-110 | Koşullu emir geçmişi | GET /fapi/v1/allAlgoOrders | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-111 | Tek açık normal emri sorgula | GET /fapi/v1/openOrder | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-112 | Gerçek emir oluşturmayan emir doğrulama | POST /fapi/v1/order/test | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-113 | Likidasyon ve zorunlu kapatma kayıtları | GET /fapi/v1/forceOrders | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-045 | Sembol ADL risk göstergesi | GET /fapi/v1/symbolAdlRisk | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-046 | Vadeli ve spot fiyat farkı istatistiği | GET /futures/data/basis | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-047 | Sunucu zamanı | GET /fapi/v1/time | İzinli | agentrader/bot/demo_readiness.py#23, agentrader/bot/history_reconciliation.py#35, agentrader/bot/watchdog.py#389 |
| UM-048 | Bileşik endeks bileşenleri | GET /fapi/v1/indexInfo | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-049 | Birleştirilmiş işlem akışı | GET /fapi/v1/aggTrades | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-050 | Sürekli vadeli kontrat mumları | GET /fapi/v1/continuousKlines | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-051 | Sembol ve emir filtreleri | GET /fapi/v1/exchangeInfo | İzinli | agentrader/__main__.py#26, agentrader/bot/grid_runner.py#473, agentrader/bot/neutral_runner.py#375 |
| UM-052 | Funding geçmişi | GET /fapi/v1/fundingRate | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-053 | Funding sözleşme bilgileri | GET /fapi/v1/fundingInfo | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-054 | Endeks fiyatı mumları | GET /fapi/v1/indexPriceKlines | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-055 | İşlem fiyatı mumları | GET /fapi/v1/klines | İzin listesinde yok | agentrader/shared/market_data.py#35, agentrader/shared/market_data.py#103 |
| UM-056 | Genel long ve short oranı | GET /futures/data/globalLongShortAccountRatio | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-057 | Mark fiyatı ve funding görünümü | GET /fapi/v1/premiumIndex | İzinli | agentrader/bot/execution.py#76, agentrader/bot/grid_native_stop.py#73, agentrader/bot/grid_native_stop.py#83 |
| UM-058 | Mark fiyatı mumları | GET /fapi/v1/markPriceKlines | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-059 | Çoklu varlık değerleme endeksi | GET /fapi/v1/assetIndex | İzinli | agentrader/bot/grid_runner.py#373, agentrader/bot/neutral_runner.py#249, agentrader/bot/v2_preflight.py#146 |
| UM-060 | Tarihsel işlem kayıtları | GET /fapi/v1/historicalTrades | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-061 | Açık pozisyon büyüklüğü | GET /fapi/v1/openInterest | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-062 | Açık pozisyon istatistik geçmişi | GET /futures/data/openInterestHist | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-063 | Emir defteri derinliği | GET /fapi/v1/depth | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-064 | Premium endeks mumları | GET /fapi/v1/premiumIndexKlines | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-065 | Vadeli kontrat uzlaşma fiyatı | GET /fapi/v1/deliveryPrice | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-066 | Fiyat endeksinin bileşenlerini sorgula | GET /fapi/v1/constituents | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-067 | Sigorta fonu bakiye görünümü | GET /fapi/v1/insuranceBalance | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-068 | Son piyasa işlemleri | GET /fapi/v1/trades | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-069 | RPI emir defteri | GET /fapi/v1/rpiDepth | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-070 | En iyi alış ve satış fiyatı | GET /fapi/v1/ticker/bookTicker | İzinli | agentrader/bot/orders.py#42 |
| UM-071 | Son fiyat V1 | GET /fapi/v1/ticker/price | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-072 | Son fiyat V2 | GET /fapi/v2/ticker/price | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-073 | Taker alış ve satış hacmi | GET /futures/data/takerlongshortRatio | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-074 | Bağlantı testi | GET /fapi/v1/ping | İzinli | agentrader/__main__.py#23 |
| UM-075 | Son 24 saat fiyat istatistiği | GET /fapi/v1/ticker/24hr | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-076 | Büyük hesapların long ve short oranı | GET /futures/data/topLongShortAccountRatio | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-077 | Büyük hesapların pozisyon oranı | GET /futures/data/topLongShortPositionRatio | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-078 | Sözleşme işlem takvimi | GET /fapi/v1/tradingSchedule | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-115 | Kullanıcı akışını canlı tut | PUT /fapi/v1/listenKey | İzinli | agentrader/bot/user_stream.py#17 |
| UM-116 | Kullanıcı akışı oturumunu başlat | POST /fapi/v1/listenKey | İzinli | agentrader/bot/user_stream.py#17 |
| UM-117 | Kullanıcı akışı oturumunu kapat | DELETE /fapi/v1/listenKey | İzinli | agentrader/bot/user_stream.py#17 |
| UM-040 | Dönüşüm teklifini kabul et | POST /fapi/v1/convert/acceptQuote | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-041 | Dönüştürülebilir varlık çiftleri | GET /fapi/v1/convert/exchangeInfo | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-042 | Dönüşüm işlemi durumunu oku | GET /fapi/v1/convert/orderStatus | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-043 | Dönüşüm fiyat teklifi al | POST /fapi/v1/convert/getQuote | İzin listesinde yok | İşlem referansı bulunamadı |
| UM-080 | Klasik portföy marjı hesap görünümü | GET /fapi/v1/pmAccountInfo | İzin listesinde yok | İşlem referansı bulunamadı |
