# Ürün sözleşmeleri ve uygulama kararları

15 Kasım 2026. Bu belge 1–5 geniş araştırma turunun ürün yorumudur. Ayrıntılı alanlar, zorunluluklar, kaynak kuralları, yöntem ve yanıt tipleri `detailed-operation-contracts.json`, yanıt alanları ve enumlar `official-response-models.json` içindedir. Her satır kaynak commit ve satır numarasına bağlıdır. SDK ve Postman aynı şema ailesinden üretilebildiği için aralarındaki uyum bağımsız borsa doğrulaması sayılmaz.

## USD-M Futures — 95 başlangıç işlemi

Kapsam emir oluşturma, test emri, normal/algo sorgu ve iptal, tek/toplu amend, toplu oluşturma/iptal, zamanlayıcılı iptal, pozisyon, leverage/margin/hedge/multi-assets/fee-burn, izole teminat, geçmiş, veri ve futures Convert içerir.

- LIMIT/MARKET ile koşullu emir yolları ve clientOrderId/clientAlgoId ayrılmalı. Tetiklenen algo ile oluşan normal emir birlikte izlenmeli.
- GTC/IOC/FOK/GTX/GTD seçimi kullanıcı talimatında korunmalı. GTD saniye hassasiyeti, en az 600 saniye ve sona erme davranışı ayrıca doğrulanmalı.
- Hedge LONG/SHORT bacakları yön ve işlem amacıyla eşleşmeli. reduceOnly ile closePosition kombinasyonları ürün kuralına göre kurulmalı.
- priceMatch ile açık fiyat birlikte gönderilmemeli. STP ve uygunluk gerektiren RPI seçenekleri sembol ve hesap üzerinden değerlendirilir.
- Batch alt emirleri ayrı başarılı/reddedilmiş/belirsiz olabilir. Tüm hesabı iptal, sembol iptali, seçili iptal ve yalnız botun sahip olduğu emirleri iptal ayrı kapsamdır.
- İptal/değiştirme mevcut dolumu geri almaz. Eski/yeni miktar ve dolum sonrasında rezervler yeniden hesaplanır.
- Hesap/sembol leverageBracket değeri sabit 125 varsayımının yerini almalı. Mevcut kodda sabit üst sınır tespit edildi.
- Şema/yardımcı validator desteği normal kullanıcı komutuyla erişim desteğinden ayrılır. Mevcut LIMIT planı GTC üretir, genel TIF seçimi sunmaz.

Kaynak: [USD-M trade](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade), sabitlenmiş SDK sözleşmeleri. Güncel algo callback aralığı ile yerel 0.1–5 sınırı arasındaki fark önceki USD-M incelemesinde kaydedildi ve bu tur yeniden ölçüldü.

## Spot — 48 başlangıç işlemi

Kapsam normal ve SOR emirleri, test emirleri, order lists, cancel-replace, önceliği koruyan amend, hesap, komisyon, dolum, prevented matches ve piyasa verisidir.

- quantity baz varlık, quoteOrderQty karşı varlık bütçesidir. Kullanıcı niyeti dönüşüm sırasında kaybolmamalı.
- LIMIT_MAKER post-only, iceberg ve trailingDelta ayrı kurallara sahiptir. Spot trailingDelta ile Futures callbackRate farklı birimlerdir.
- OCO/OTO/OTOCO/OPO/OPOCO bağımlı emir modelleridir. Liste kimliği, her alt emir ve bütçe rezervasyonu ayrı izlenir. OPO, ödeme tarafı miktarının diğer emir bütçesiyle ilişkisini gerektirir.
- Cancel-replace iki bileşenli sonuçtur. Eski iptal başarılı, yeni emir başarısız olabilir. HTTP sonucu tek başına iki işlemi başarılı yapmaz.
- Keep-priority amend azaltma işlemidir. Genel fiyat/miktar değiştirmeyle aynı sözleşme altında sunulamaz.
- Pegged emirlerde fiyatın koşullu zorunluluğu ve offset alanları birlikte incelenir.
- SOR için fiili işlem yapılan sembol/workingFloor ve allocation kayıtları başlangıç emriyle ilişkilendirilir.
- PRICE_FILTER, LOT_SIZE, MARKET_LOT_SIZE, NOTIONAL, PERCENT_PRICE_BY_SIDE, ICEBERG_PARTS, TRAILING_DELTA ve emir/liste/amend sayıları ayrı doğrulanır. Sıfır adım veya devre dışı filtre alanı sıfıra bölme üretmemeli.
- Sembolün allowedSelfTradePreventionModes değeri temel alınır. Yeni snapshotta DECREMENT ve TRANSFER görüldü. USD-M enumunun Spot için yeniden kullanılması eksik kalır.
- WS API kullanıcı aboneliği, bağlantı kimliği ve olay zarfı USD-M listenKey akışından farklıdır.

Kaynaklar: [Spot API](https://github.com/binance/binance-spot-api-docs/blob/e5f8489162e79fa1da6d0ea3ded3ce810b3637a0/rest-api.md), [filtreler](https://github.com/binance/binance-spot-api-docs/blob/e5f8489162e79fa1da6d0ea3ded3ce810b3637a0/filters.md), [enumlar](https://github.com/binance/binance-spot-api-docs/blob/e5f8489162e79fa1da6d0ea3ded3ce810b3637a0/enums.md), [OPO](https://github.com/binance/binance-spot-api-docs/blob/e5f8489162e79fa1da6d0ea3ded3ce810b3637a0/faqs/opo.md).

## Margin — 69 başlangıç işlemi

Kapsam cross/isolated hesap, borç/geri ödeme, faiz, envanter ve teminat sınırları, normal/bağlı emir, tasfiye kayıtları, küçük borç dönüşümü, liquidation loan ve özel anahtar yönetimidir.

- isIsolated ve symbol hesap kimliğinin parçasıdır. Cross ve isolated borçları aynı bakiye olarak birleştirilemez.
- BORROW/REPAY ve emir sideEffectType ayrı işlemlerdir. MARGIN_BUY, AUTO_REPAY, AUTO_BORROW_REPAY seçimleri kullanıcı talimatına bağlıdır. Auto-repay sonucu borç sorgusuyla teyit edilir.
- Borç anaparası ve faiz ayrı izlenir. Maksimum borç, envanter, collateral haircut ve mevcut risk oranı gönderim öncesi koşullardır.
- -3007 devam eden hesap işlemi sonrasında her varlık için kör tekrar uygun değildir. Hesap bazlı sıralama ve durum sorgusu gerekir.
- OCO/OTO/OTOCO listeleri borç yan etkileri ve iptal sonrası geri ödeme ile birlikte yönetilir. Spot ürününün bütün liste oluşturma olanakları Margin'e taşınamaz.
- Margin manual liquidation ve liquidation loan repay ayrı kullanıcı amaçlarıdır. Pozisyon kapatma emriyle eşit kabul edilemez.
- Yeni listen-token aboneliği ve eski listen-key yolları sürüm ayrımıyla saklanır. Güncel token geçerliliği ve yeniden abonelik önceki Margin akış incelemesine bağlıdır.
- Liabilities, risk level, executionReport ve balance olayları farklı kayıtları günceller. Geç gelen borç olayı, eski bilanço sürümüne geri dönüş yapmamalı.

Kaynak: [Margin trade](https://developers.binance.com/en/docs/catalog/core-trading-margin-trading/api/rest-api/trade), 69 SDK sözleşmesi, `MARGIN-CORE-REVIEW.md` ve `MARGIN-ACCOUNT-STREAM-REVIEW.md`.

## COIN-M — 64 başlangıç işlemi

Kapsam perpetual/teslimli kontratlar, normal/toplu emir, amend, hesap modu, coin teminat, kaldıraç ve teminat, pozisyon, geçmiş ve piyasa verisidir.

- Miktar kontrat adedi, contractSize nominal sözleşme büyüklüğüdür. Coin miktarı ve kontrat miktarı birbirine eşitlenemez.
- Inverse PnL ve coin komisyon/funding/uzlaşma muhasebesi gerekir. Mevcut doğrusal USD-M risk modeli yeniden kullanılamaz.
- Vade, kontrat durumu ve son işlem koşulları keşfedilir. Borsanın teslim kapatması yerel kullanıcının kapatma emri gibi işaretlenmez.
- UM/CM ortak position mode ve limit havuzu önemlidir. Birini değiştirmek diğer ürünün koşullarına bağlı olabilir.
- CM normal/algo geçişi ile eski SDK yolları arasında belgelenmiş uyuşmazlık bulunuyor. Normal stop emirlerinin -4120 davranışı ve yeni algo alanları sürüm kapısı gerektirir.
- Amend fiyat ve miktarı birlikte ele alır. Yeni miktar gerçekleşen miktara indiğinde veya GTX fiyatı karşı tarafı geçtiğinde iptal sonucu oluşabilir.
- Genel enumların aynı görünmesi yeni CM algo yolunun ve callback sınırının kanıtı değildir. Bu konu Q-CM-01 olarak açık sınırla kaydedilmiştir.

Kaynak: [CM trade](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-coin-m-futures/api/rest-api/trade), [CM/UM entegrasyon duyurusu](https://developers.binance.com/en/docs/products/derivatives-trading-coin-futures/Important-CM-UM-Integration-Notice), önceki COIN-M incelemeleri.

## Options — 44 başlangıç işlemi

Kapsam LIMIT emirleri, toplu emir/iptal, pozisyon ve kullanım kayıtları, hesap nakit akışı, komisyon, MMP, kill-switch ve market-maker block trade yaşam döngüsüdür.

- CALL/PUT, underlying, strike, expiry, unit ve premium tutarı saklanır. Sembolü yalnız USDT son ekine göre yorumlamak uygun değildir.
- LIMIT, TIF, postOnly, reduceOnly ve isMmp koşulları ürün sözleşmesine göre doğrulanır.
- Pozisyon miktarı ile prim, gerçekleşmiş PnL, ücret ve exercise/settlement tutarları ayrı muhasebeleştirilir.
- MMP tetiklenmesi yeni MMP emirlerini engelleyebilir. Manuel reset ile süreli çözülme ayırt edilir. Kill-switch heartbeat kaybı ayrı toplu iptal davranışıdır.
- Block trade oluşturma/kabul/uzatma/iptal ve detay sorguları normal emir defteri emirlerinden ayrı süreçtir.
- Trade geçmişinin desteklediği süre, vade sonu kayıtları ve sorgu pencereleri sınırsız geçmiş varsayımını engeller.
- Olay model sınıfları indirildi. Kaynakta eksik tanımlanmış iç alanlar için gerçek hesap kabulü henüz yoktur. Bu alanlar Q-OPT-01 kaydına bağlıdır.

Kaynak: [Options trade](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-options/api/rest-api/trade), 44 SDK sözleşmesi ve `OPTIONS-REVIEW.md`.

## Portfolio Margin — 102, Pro — 24 başlangıç işlemi

PM ve Pro ürünlerinin hesap, teminat ve işlem yolu farklılığı korunur. Pro SPAN sürümü ayrı şemadır. UM normal/algo, CM normal/conditional ve Margin emirleri hesap modeliyle birlikte yönlendirilir. Borç, faiz, negatif bakiye, auto-repay/auto-exchange, açık emir kaybı ve teminat basamakları tek hesap riskini etkiler. Mevcut `portfolio.py` bu borsa ürününün adaptörü değildir.

Ürün statüleri emir kabulünü sınırlar. Boş sayısal alan sıfır sayılamaz. USD cinsinden transfer tavanı doğrudan coin miktarı değildir. Bileşen akışları tam hesap snapshotı gibi işlenmez. Q-PM-01 Pro/SPAN ayrıntılı model kabulünü açık tutar.

Kaynaklar ve önceki eşik incelemesi `PORTFOLIO-MARGIN-REVIEW.md` içinde. 126 kaydın alan ve yanıt modelleri yeni JSON teslimindedir.

## Convert — 9 başlangıç işlemi

Teklif alma, kabul ve sonuç sorgusu ayrı aşamalardır. Teklif için 10s/30s/1m, limit emir için 1_D/3_D/7_D/30_D süre seçenekleri SDK'da kayıtlıdır. Kaynak/hedef tutar seçimi, precision, cüzdan birleşimi ve bakiye uygunluğu saklanır. Teklif kabulü ara sonuç döndürebilir. Limit iptalindeki gerçekleşme ve transfer sonrasındaki gerçek varlık değişimi uzlaştırılır.

Kaynak: [Convert trade](https://developers.binance.com/en/docs/catalog/core-trading-convert/api/rest-api/trade), OP-0001–OP-0009 sözleşmeleri.

## Wallet — 50 başlangıç işlemi

Kapsam varlık/cüzdan bakiyeleri, universal transfer ve geçmişi, dust dönüşümleri, deposit/withdraw ağ/adres/limit/geçmiş, API izinleri, hesap durumu, ücret/BNB ayarı, delist ve Travel Rule yollarıdır.

Transfer, yatırma ve çekme ayrı muhasebe kimlikleri kullanır. Ağ seçimi, memo/tag, miktar adımı, ücret ve minimum/maksimumlar güncel metadata ile doğrulanır. Sorgu pencereleri bölünür. Günlük hesap snapshotı anlık işlem sonucu sayılmaz. Dust dönüşümünde kaynak varlıklar, alınan varlık ve servis ücretleri uzlaştırılır.

Travel Rule işlemleri yerel kuruluşun istediği questionnaire, kimlik ve adres koşullarına bağlıdır. Gereksinim sorgusu ile normal/localentity yolu seçilir. Bu tur endpointlerin SDK alanları kaydedildi, canlı belge sayfası zaman aşımı verdi. Q-WAL-01 bu kaynak ve hesap uygunluğu sınırını korur. `fromSymbol/toSymbol` şema örneği tutarsızlığı Q-WAL-02 olarak ayrıldı.

Kaynaklar: [Wallet capital](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/capital), [Wallet asset](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/asset), SDK Wallet API sınıfları.

## Sub Account — 50 başlangıç işlemi

Kapsam master/sub/managed account keşfi, ürün etkinleştirme, bakiye/pozisyon, transfer, pozisyon taşıma ve API key izin/IP yönetimidir. Her komutta çağıran hesap, kaynak hesap ve hedef hesap ayrı kimliktir. Anahtar oluşturma yanıtının hassas alanları günlüklerde tutulamaz.

Pozisyon taşıma kaynağı yalnız master, VIP 7–9 ve Trading izni koşullarını bildirir. Cross desteklenir, MARK_PRICE kullanılır, kaynak pozisyon gerekli, MSA ve reduce-only semboller desteklenmez. Bir istekte UM/OPTION karışmaz, en fazla 10 pozisyon taşınır. Alt sonuçlar ve iki hesap muhasebesi teyit edilir. Bu kurallar transfer endpointine veya normal emir yaratmaya genellenmez.

Kaynak: [Sub Account asset management](https://developers.binance.com/en/docs/catalog/vip-and-institutional-sub-account/api/rest-api/asset-management), sabitlenmiş SDK `move_position_for_sub_account` sözleşmesi. Hesap yetkileri nedeniyle özel hesap üzerinde yürütme kabulü ayrı teslimdir.

## İnceleme sınırı

555 başlangıç kaydının tamamı SDK yöntem, alan, açıklama, zorunlu kontrol ve yanıt tipiyle eşleşti. 83 WS API komutu ayrıca çıkarıldı. 1484 model dosyasından 2010 model/enum sınıfı kaydedildi. Bu, bütün canlı belgelerin her cümlesinin bağımsız teyidi veya bütün kombinasyonların borsada yürütülmesi anlamına gelmez. Kaynak çelişkileri ve erişilemeyen sözleşme ayrıntıları ayrı açık kaydıdır. İşlenmemiş satır ile incelenmiş fakat dış doğrulama bekleyen satır aynı durum değildir.
