# Options işlem ve hesap incelemesi

15 Kasım 2026. 44 kayıtlık resmi koleksiyonun işlem aileleri incelendi. Mevcut botun USD-M plan kapısı ve fapi adaptörü Options üretim işlemlerini desteklemiyor.

| Aile | Gerekli sözleşme | Kabul örneği |
|---|---|---|
| Emir | symbol, side, type, quantity, price, timeInForce, reduceOnly, postOnly, clientOrderId, isMmp | Yanlış vade/sembol reddi, kısmi dolum ve miktar azaltma |
| Toplu ve iptal | Tek/sembol/underlying kapsamı, batch alt sonuçları | Bir underlying iptalinde başka varlığın emirlerini koruma |
| Pozisyon | Option position, prim ve kontrat birimi | Dolum sonrası pozisyonu ve hesap hareketini eşleme |
| Uzlaşma | exerciseRecord ve exerciseHistory | Vade sonu kapanışı kullanıcı emrinden ayırt etme |
| Muhasebe | marginAccount ve bill, currency ve recordId | Komisyon, prim ve uzlaşma hareketini tek sayma |
| MMP | underlying, zaman penceresi, qtyLimit ve deltaLimit | Donma, reset ve yeni emir uygunluğunu doğrulama |
| Kill-switch | countdownCancelAll ve HeartBeat | Heartbeat kesilince iptal kapsamını teyit etme |
| Block trade | legs, matching key, oluştur/kabul/uzat/iptal/sorgu | Kabul yanıtı kaybında tekrar kabulden önce sorgulama |
| Kullanıcı akışı | listenKey başlat/canlı tut/kapat | Kopuş sonrası pozisyon, emir ve bill uzlaştırma |

Bütün aileler için normal bot komutu ve ürün muhasebesi geliştirme açığıdır. Parametre listeleri cross-product-operation-catalog.json OP-0074–OP-0117 aralığında bulunur. Her 44 kaydın alan alan doküman karşılaştırması ve WS payload kabulü henüz tamamlanmadı.

[Options Trade](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-options/api/rest-api/trade), [Options Account](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-options/api/rest-api/account).

## Emir ve koruma sözleşmelerinin devamı

Yeni emir türü LIMIT olarak belgelenmiş. Süreler GTC/IOC/FOK/GTX, yanıt türleri ACK/RESULT. clientOrderId bekleyen emirlerde benzersiz olmalı. reduceOnly, postOnly ve isMmp alanları ürün modeli içinde ayrı korunmalı.

Kill-switch underlying kapsamındaki MMP ve diğer açık emirleri heartbeat gelmezse iptal eder. countdownTime=0 kapatır, pozitif en küçük süre 5000 ms olarak belgelenmiştir. GET yalnız aktif ayarları döndürür. MMP tetiklendiğinde mevcut MMP emirleri iptal edilir ve yeni MMP emirleri reddedilir. frozenTimeInMilliseconds=0 için manuel reset gerekir.

Kullanıcı akışında BALANCE_POSITION_UPDATE, ORDER_TRADE_UPDATE, GREEK_UPDATE ve risk seviye değişikliği vardır. Emir olayı execution type ile order status alanlarını farklı anlamlarda taşır. PARTIALLY_FILLED/FILLED durumu son gerçekleşme miktarıyla birlikte uzlaştırılmalıdır.

ExerciseRecord kayıtları symbol, currency, quantity, amount, fee ve createDate üzerinden bill/pozisyon sonuçlarına bağlanmalıdır. Kullanıcı dolum geçmişi için belgelenen üç aylık sorgu sınırı yerel arşiv ihtiyacı doğurur.

Ek kabul senaryoları LIMIT dışı türün anlaşılır reddi, client ID çakışması, underlying iptal kapsamı, 4999/5000 ms countdown sınırı, heartbeat kaybı, MMP manuel reset, yinelenen dolum olayı ve exercise/bill tekilleştirmesidir.

[Koruma endpointleri](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-options/api/rest-api/market-maker-endpoints), [kullanıcı olayları](https://developers.binance.com/en/docs/products/derivatives-trading-options/user-data-streams).

Durum, ana emir ve koruma davranışları belgelendi. Bütün 44 işlem için alan alan kapanış, olay şemalarının tüm alanları, ürün/hesap erişimi ve borsa kabulü açık.

## Olay şemaları incelemesi

Resmi şemada ACCOUNT_UPDATE toplam equity, adjusted equity, wallet, initial ve maintenance margin alanları var. BALANCE_POSITION_UPDATE E/T zamanları, m nedeni ve B/P listelerini taşır. ORDER_TRADE_UPDATE emir nesnesini o alanında taşır. GREEK_UPDATE G listesiyle gelir. RISK_LEVEL_CHANGE NORMAL/REDUCE_ONLY durumlarını taşır ve özellik VIP/Market Maker hesaplarına özgü olarak belgelenmiştir. listenKeyExpired şemasında E string olarak gösteriliyor, diğer olaylarda integer. Parser bu farkı açık doğrulama politikasıyla ele almalı.

Şema sayfası B/P/o/G iç alanlarını ayrıntılandırmıyor. Bu nedenle payload derinliği kaynaktan tamamen çözülmüş kabul edilemez. Resmi SDK modelleri veya örnek olaylarla ek teyit gereklidir.

[Options olay şemaları](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-options/api/ws-streams/~schemas).
