# Kesin ondalık veri — P1

10 Kasım 2026. P1 uygulandı; bot adaptörü ve P2–P7 uygulanmadı. B5 ertelenmiş/açık; ana plan 24/25. Bu değişiklik geçmiş aday 02 arşivini değiştirmez.

## Veri biçimi

Mevcut candle.open/high/low/close/volume/quote_volume JSON sayıları grafik içindir ve aynı kaldı. Her üretim candle kaydına opsiyonel `exact` yan verisi eklendi:

```json
{"schema":"chart-exact-decimal/1","state":"VERIFIED","provenance":"UPSTREAM_DECIMAL_TEXT","open":"100","high":"110","low":"90","close":"105.000000000000000000001","volume":"10","quote_volume":"1050"}
```

Bu değerler borsadan gelen metinlerden doğrudan Decimal ile doğrulanır, üssüz kanonik metne çevrilir. Normalize sırasında Decimal bağlamıyla yuvarlama yapılmaz. Kaynak metin gösterimi (örneğin trailing zero) değişebilir; sayısal değer kayıpsızdır. Zaman/closed alanları candle üst düzeyinde mevcut birimleriyle kalır. Aynı sidecar history, snapshot, candle ve tail üzerinden taşınır; heartbeat yeni kesin fiyat üretmez.

Katalogdaki mevcut tick_size değişmedi; `market.exact` doğrulanmış kanonik tick_size içerir. Üst düzey `precision` özeti tüm mevcut snapshot mumlarının ve tick'in kesinlik durumunu sayar. VERIFIED yalnız bu dar sayısal koşul içindir; `bot_eligible:false` her zaman korunur. Saat/epoch/grid/revision/dedup kanıtları bununla tamamlanmaz. Provenans güvenilir upstream parser yolunun açıklamasıdır; imza veya kullanıcı tarafından gönderilen DTO'nun doğruluğunun ispatı değildir.

## Eski kayıt ve doğrulama

Ham CandleStore JSON metinlerini zaten korur, migration gerekmez. Float-only eski satırdan kesin fiyat uydurulmaz; exact.state=UNPROVEN ve reason=PRICE_PRECISION_UNPROVEN olur. Mevcut history cache yalnız süreç içindedir; backend yeniden başlatılınca yeniden edinilir. Üretim history SQL cache'den otomatik kesinlik yükseltmesi yapmaz. İleride adapter eski kaydı kullanmak isterse yeniden edinme veya BLOCKED gerekir.

Pozitif/sonlu OHLC, low/open/close/high tutarlılığı ve negatif olmayan hacim denetlenir. Metin boyutu ve mevcut aralık sınırları uygulanır. Float/bool/int girdiler kesin metin kabul edilmez. Feed içinde iki exact hacim mevcutsa karşılaştırma Decimal üzerinden yapılır; float altında kalan hacim azalması da reddedilir. Tick dışı anchor için validate_tick_price hata üretir; sessiz yuvarlama yapmaz. Bu yardımcı henüz bot veya çizim CRUD'una bağlı değildir; grafik çizimlerinin mevcut serbest fiyat davranışı korunur.

## Doğrulama ve sınır

11 yeni test: düşük Decimal precision altında kayıpsız metin, bozuk sayılar/OHLC/hacim, tick bölünebilirliği, ham cache/legacy kayıt, REST cache izolasyonu, feed/tail/snapshot, gerçek localhost HTTP/WebSocket, float altı hacim azalması. 686 Python ve 131 frontend testi geçti. Güncel sözleşme wire kontrolü 21/21 geçti; bu E4'teki 36 runtime senaryosunun çalıştığı anlamına gelmez. İlk tam koşuda yeni WebSocket testinin relative host hatası düzeltildi; ayrıca eski bir WebSocket kapanış CancelledError görülmüştü. Son tam koşu temiz geçti; ilk log korunur.

Tarayıcı görsel/30 dakika testi bu backend yan alanı değişikliği için tekrarlanmadı. Canlı borsa/hesap/emir isteği veya kullanıcı veritabanına yazma yapılmadı. Yeni alanlar nedeniyle yanıt boyutu arttı; büyük yükte performans etkisi bu tur ölçülmedi. Önceki performans paketinin hash eşliği bu backend sürümü için iddia edilmez.

Güncel sıra v2 planındadır: T01 tamamlandı, sırada T02; ardından P2 güvenilir saat ve P3 akış kanıtı gelir. [Aktif plan](PLAN.md).
