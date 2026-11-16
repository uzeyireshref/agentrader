# Borsa işlemleri için düzeltilmiş araştırma kapsamı

15 Kasım 2026. Kullanıcının hedefi, verdiği borsa işlem talimatlarının yazılım tarafından eksiksiz uygulanabilmesi. İncelemenin ölçüsü her ürünün işlemleri, parametreleri, hesap durumları ve hata sonrası tamamlanma davranışıdır. Önceki rapordaki strateji seçimi ve kârlılık araştırması bu hedefin kabul ölçütlerini karşılamıyordu.

Bu turda mevcut USD-M REST kataloğundaki 95 işlem güncel adaptör ve kaynak koduyla tekrar eşleştirildi. Parametre desteğini ölçmek için 12 çevrimdışı örnek yürütüldü. Sonuçlar [işlem envanterinde](EXCHANGE-OPERATIONS.md) ve [makine tarafından okunabilir kanıtta](../../../reports/crypto-bot-research-20261115/exchange-operation-audit.json) bulunuyor.

| Ölçüm | Sonuç | Anlamı |
|---|---|---|
| İncelenen USD-M REST işlemi | 95 | Mevcut belgeli işlem kataloğunun bu tur eşleştirilen kapsamı |
| DemoExchange izin listesinde bulunan işlem | 39 | Yöntem ve yol adaptörde izinli |
| Başka istemcide kaynak referansı | 1 | Mum verisi PublicMarket üzerinden okunuyor |
| Tarama kapsamında uygulama adresi bulunamayan işlem | 55 | İncelenecek adaptör veya ürün kapsamı açığı |
| Çevrimdışı parametre örneği | 12 | 7 kabul, 5 ret gözlendi |
| Yeni borsa yürütme kabulü | Bekliyor | Bu turdaki kanıt kaynak taraması ve yerel fonksiyon çağrıları |

39 izinli işlem için her parametreyle tamamlanmış kullanıcı komutu olduğu sonucu çıkarılamaz. 55 adresin bulunmaması da 55 farklı kullanıcı ihtiyacının tamamen eksik olduğu anlamına gelmez. Örneğin V3 hesap özeti bazı bakiye ihtiyaçlarını karşılıyor. Ayrı bakiye endpoint’i ve eski API sürümü eşdeğer sonuç açısından değerlendirilmeli. Kline yolu başka üretim istemcisinde bulunduğu için ayrıca kaydedildi.

| İşlem ailesi | Botun yerine getirebilmesi gereken talimat örnekleri |
|---|---|
| Emir oluşturma | Market/limit alış ve satış, long/short, post-only, IOC/FOK/GTD, fiyat eşleme ve istemci kimliği |
| Koşullu emir | Stop-market, stop-limit, take-profit-market, take-profit-limit, borsa trailing emri, mark/contract tetikleyici |
| Emir değiştirme | Fiyat/miktar değiştir, kısmi dolumdan sonra kalan miktarı değiştir, birden fazla emri değiştir |
| İptal | Tek emri, seçili emirleri, tüm normal emirleri, tüm algo emirlerini iptal et, süreli otomatik iptal kur |
| Pozisyon | Kısmen/tamamen azalt, artır, ayrı long/short bacaklarını yönet, açık talimata göre yön değiştir |
| Hesap ve teminat | Kaldıraç, cross/isolated, one-way/hedge, multi-assets, izole teminat ekleme/azaltma, komisyon tercihi |
| Sorgu ve geçmiş | Açık/terminal emir, algo-child ilişkisi, dolumlar, gelir, funding, komisyon, teminat ve emir değişiklik geçmişi |
| Veri ve toparlanma | Sembol kuralları, fiyat, defter, saat, bağlantı kopması, belirsiz yanıt, restart ve eşzamanlı komut |
| Ürün kapsamı | USD-M, Spot, Margin, COIN-M, Options ve ürünler arası hesap hareketlerinin kendi işlem sözleşmeleri |

USD-M emir ve hesap parametreleri Binance’in resmi sözleşmeleriyle karşılaştırılmalı. Test ortamında endpoint kullanılabilirliği ve hesap yetkisi ayrıca gözlenmeli. [Binance USD-M işlemleri](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade), [ortam ve hata davranışı](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info)

| Doğrulanan bulgu | Botta görülen durum | Gerekli kabul |
|---|---|---|
| Emir süresi seçimi | Doğrulayıcı GTC/IOC/FOK/GTX/GTD kabul ediyor. Tek giriş planı ve preflight limit emir için GTC oluşturuyor | Kullanıcı seçimi plan, hazırlık, yürütme ve restart boyunca korunmalı |
| Borsanın trailing emri | Doğrulayıcı TRAILING_STOP_MARKET tanıyor. Grid native_stop kodu watermark’ı botta izleyip STOP_MARKET yeniliyor | Borsa trailing emrinin oluşturma, sorgu, iptal ve dolum yolu ayrı kanıtlanmalı |
| Callback oranı | 0.1 ve 5 kabul edildi. 7.5, 10 ve 20 reddedildi | Güncel resmi şema 0.1–20 aralığı gösteriyor. Demo erişimi ve geçerli ürün koşullarıyla destek sınırı doğrulanmalı |
| Yanıt türü | newOrderRespType=ACK ve RESULT doğrulayıcıda reddedildi | Desteklenecek yanıt tipleri ve sonrasında emir durumunu uzlaştırma davranışı belirlenmeli |
| Pozisyon artırma | SINGLE plan allow_scale_in=true değerini reddediyor. Grid artırımı ayrı uygulama | Kullanıcıya açık miktar artırma talimatı sahiplik, ortalama fiyat ve koruma miktarlarıyla sınanmalı |
| Yön değiştirme | allow_reverse=true plan doğrulamasında reddediliyor | Kapanış, artık miktar ve yeni yön açılışı için kalıcı bir komut akışı gerekli |
| Süreli otomatik iptal | countdownCancelAll adaptör izin listesinde ve incelenen adres referanslarında bulunamadı | Süre kurma, yenileme, kaldırma ve bağlantı kaybı davranışı eklenmeli |
| Tüm emirleri iptal | Native allOpenOrders/algoOpenOrders DELETE yolları bulunamadı. Seçili sahipli emirlerde batch iptal altyapısı var | Talimatın seçili/bot oturumu/sembol/hesap kapsamı tam olarak uygulanmalı |
| Geçmişi topluca sorgulama | userTrades ve income desteği var. allOrders/allAlgoOrders yolları bulunamadı | Saklama sınırları, sayfalama ve terminal emirlerin yerel kayıtlarla uzlaşması kanıtlanmalı |

İlk dört bulgu [order_rules](../../../agentrader/bot/order_rules.py), [plan_v2](../../../agentrader/bot/plan_v2.py), [v2_preflight](../../../agentrader/bot/v2_preflight.py) ve [grid_native_stop](../../../agentrader/bot/grid_native_stop.py) üzerinde incelendi. Yerel parametre deneyleri JSON kanıtına kaydedildi. Önceki coin ölçümündeki geçersiz callback örneği 20 yerine 20.1 olarak düzeltildi. Güncel resmi şemada 20 aralık içindedir ve botun bunu reddetmesi bir destek sınırıdır. Parametrelerin borsada hesaba ve sembole göre kabulü sonraki doğrulama katmanıdır. [Güncel resmi algo emir şeması](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade)

Her işlem talimatında aşağıdaki yaşam döngüsü örnekleri kullanılmalı.

1. Geçerli talimat doğru yöntem, ürün, sembol, yön ve miktarla tamamlanır.
2. Geçersiz kombinasyon anlaşılır nedenle reddedilir. Geçerli bir işlem için destek eksikliği ayrıca görünür olur.
3. Emir kısmen dolduğunda iptal/değiştirme/azaltma yalnız gerçek kalan miktarı etkiler.
4. Yanıt kaybolduğunda istemci kimliği ve borsa sorgusuyla sonuç bulunur.
5. İşlem sırasında süreç kapandığında aynı komut kimliğiyle devam edilir ve ikinci finansal işlem oluşmaz.
6. Aynı talimat tekrarlandığında veya eşzamanlı geldiğinde tanımlanan tekilleştirme uygulanır.
7. Manuel işlem veya başka bot oturumu mevcutsa talimatın hedef kapsamı korunur.
8. Sembol filtresi, bakiye, kaldıraç basamağı veya hesap modu değiştiğinde talimat güncel durumla yeniden değerlendirilir.
9. Sonuç emir, dolum, pozisyon, bakiye ve yerel günlük üzerinden teyit edilir.

Bu dokuz koşul her endpoint’e mekanik biçimde çarpılmamalı. Okuma işlemlerinde sayfalama/veri tutarlılığı, teminat eklemede artımlı işlemin iki kez gönderilmemesi, emir değişikliğinde dolum yarışı gibi işleme özgü koşullar seçilmeli.

Coinler bu işlem sözleşmelerini farklı tick, lot, minimum nominal, maksimum miktar ve kullanılabilir emir türleriyle sınamak için kullanılmalı. Örneğin BTCUSDT’de geçen miktar hesabı düşük fiyatlı veya farklı kontrat çarpanlı bir üründe tekrar doğrulanmalı. Önceki 528 sembollük snapshot ve 8.432 kontrol bu katmanda kullanılabilir. Bunların ölçtüğü alan yerel emir doğrulayıcısıdır.

Spot tarafında OCO/OTO/OTOCO, cancel-replace, pegged ve iceberg işlemleri kendi API sözleşmelerine sahiptir. Margin borçlanma ve geri ödemesi ayrı hesaba ait işlemlerdir. COIN-M kontratları coin cinsi teminat ve kontrat miktarıyla ele alınmalıdır. Mevcut plan şeması demo/binance/USD-M ve USDT sembollerini kabul ediyor. Diğer ürünlerin uçtan uca işlem desteği için ayrıca adaptör ve kabul envanteri gerekiyor. [Resmi Spot belgeleri](https://github.com/binance/binance-spot-api-docs), [Margin borrow/repay](https://developers.binance.com/en/docs/catalog/core-trading-margin-trading/api/rest-api/borrow-repay), [COIN-M işlemleri](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-coin-m-futures/api/rest-api/trade)

Geliştirmeyi kolaylaştıran kaynakların önceliği de bu amaçla güncellendi.

| Resmi kaynak | Bu hedefte kullanımı |
|---|---|
| [Binance Python connector](https://github.com/binance/binance-connector-python) | Ürün bazında güncel istek ve yanıt modellerini karşılaştırma |
| [Binance API Postman](https://github.com/binance/binance-api-postman) | Parametre ve endpoint örneklerini karşılaştırmalı kabul girdisine dönüştürme |
| [Binance CLI](https://github.com/binance/binance-cli) | Kullanıcı talimatlarının komut kapsamını ve argümanlarını karşılaştırma |
| [Binance Spot API docs](https://github.com/binance/binance-spot-api-docs) | Spot emir listeleri, filtreler ve hata koşullarını çıkarma |
| [Binance Skills Hub](https://github.com/binance/binance-skills-hub) | Resmi ürün/komut referanslarının geliştirme iş akışına uygunluğunu inceleme |

Bu turdaki değişiklikler araştırma envanteri, kanıt raporu ve tekrar çalıştırılabilir denetim kodudur. Belirlenen destek açıkları henüz uygulama çekirdeğinde tamamlanmadı. Genel yazılım hatası yaşamama beklentisinin kabul ölçütü, her desteklenen komutun normal giriş yolunda başarı, ret ve toparlanma senaryolarıyla kanıtlanması olarak belirlendi.

Tekrar ölçüm komutu proje kökünde python scripts/research/audit_exchange_operations.py şeklindedir.
