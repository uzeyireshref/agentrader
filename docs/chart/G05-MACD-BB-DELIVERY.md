# G05 — MACD ve Bollinger Bands

12 Kasım 2026. Tamamlandı; plan 20/27. Sıradaki T11: seanslı ve anchored VWAP.

## Kullanım ve tasarım

Göstergeler menüsü → MACD / Bollinger Bands; Gösterge ayarları ile parametre ve stil kaydı. MACD ayrı lineer panelde mavi çizgi, turuncu sinyal, sıfır referansı ve dört durumlu histogram kullanır. Pozitif artan/azalan ve negatif artan/azalan bar renkleri ayrı ayarlanır; eşit değer artan dalına girer, ilk önceki histogram değeri0'dır. MACD kendi otomatik ölçek/gizleme kontrolüne sahiptir.

Bollinger Bands fiyat panelinde kesikli orta ve düz üst/alt çizgidir. Üç renk ve ortak çizgi kalınlığı kaydedilir. Bant dolgusu bu teslimde yoktur. MACD çizgi/sinyal renkleri, dört histogram rengi ve çizgi kalınlığı da kaydedilir. Açık/koyu tema tokenları, masaüstü1024px form, klavye Escape ve formun görünür kalan kayıt/vazgeç alanı doğrulandı. Yeni göstergeler başlangıçta kapalıdır.

## Sayısal model

MACD: aynı kaynakta hızlı ortalama−yavaş ortalama. Osilatör ortalamaları SMA veya SMA-seed EMA, sinyal ortalaması bağımsız SMA veya SMA-seed EMA seçilebilir. Hızlı periyot yavaştan küçüktür; periyot sınırı1–500. İlk MACD indeksi slow−1; sinyal ve histogram slow+signal−2. MACD hazırken sinyal/histogram warmup'ta ayrı unavailable kalabilir. Histogram=MACD−sinyal. Geçmiş başlangıcı yüklü veri başlangıcıdır; vendor origin seed veya TradingView exact paritesi iddia edilmez.

BB: orta=seçilmiş SMA/EMA(source,period); standart sapma her durumda kayan kaynak örneklerinin kendi aritmetik ortalaması etrafında **popülasyon varyansı** (bölü period) kullanır. Üst/alt=orta±çarpan×sapma. EMA orta seçilmesi sapma merkezini EMA'ya dönüştürmez. Çarpan0.1–10; periyot1–500.

BB kaydırma−100…100 bar yalnız çizim zamanını UTC interval adımlarıyla değiştirir; sayısal değer ve hesap seed'i değişmez. Negatif kaydırma geçmişe taşıdığı için gelecekte hesaplanmış bilgi geçmişte görüntülenebilir; işlem/replay sinyali olarak sunulmaz. Data window kaydırma uyarısını gösterir. Seçili zamanın kaydırılmış aralıkta karşılığı yoksa “Kaydırılmış aralıkta değer yok” yazar; warmup ile karışmaz.

Tüm çıktılar sabit kimliklidir: macd-main:macd/signal/histogram ve bb-main:basis/upper/lower. Data window bu altı çıktıyı ayrı gösterir. Yetersiz geçmiş sıfır değildir. Missing bar/geçersiz UTC grid bütün çıktıları temizler; onarım/revizyon sonrası yeniden hesaplanır. Açık mum uyarısı korunur. Line writer yalnız renk değiştiğinde de histogram güncellemesi gönderir; önceki bar revizyonundan kaynaklanan renk değişimi kaybolmaz.

## Kalıcılık ve yetki

chart-indicators/3 ve `format_version=3` ile yedi kalıcı gösterge nesnesi, params/style ve bağımsız revision kullanılır. Eski üç/beş nesneli kayıt GET sırasında yazılmadan genişletilir; ilk beşin ayarı, RSI hesap sürümü ve revision'ı korunur. V3 kaydedilince eski format1/2 yazması422 ile engellenir. Fiziksel DB migration gerekmez. T09 idempotency, kayıp yanıt retry, conflict/reload ve kesin kayıt yanıtı kontrolü korunur; nested params/style değerleri yapısal olarak karşılaştırılır.

Registry27 araç içerir; MACD/BB yeni indicator türleridir. Display_model VERSIONED_DISPLAY_CALCULATION ve ayrı çıktı isimlerini açıklar. Canonical bot valueAt implementasyonu bu metadata ile açılmaz: computable=false, canonical_queries=[], tracking/order_authority=false. Strateji/replay bağlantısı P4–P7 işidir.

MACD/Bollinger ayarı değişmesi diğer göstergelerin serilerini yeniden kurmaz. BB stil/offset kaydı sırasında MACD manuel ölçeği korunur. MACD kapanınca sahip olduğu iki çizgi, histogram ve boş pane kaldırılır; tekrar açıldığında kalan price/volume/RSI/ATR pane sırası korunur.

## Kabul

- **809 Python testi** geçti. Sekiz yeni grup: bağımsız Decimal ile dört MACD smoothing kombinasyonunun bütün çıktıları; BB popülasyon sapması/EMA orta/offset; parametre ve renk şeması; eski kaydı koruyan v3/idempotency/conflict; gap/revizyon/ayrı warmup; gerçek HTTP ve eski format izolasyonu; paylaşılan fixture güncelliği; display registry'nin bot yetkisi vermemesi.
- **241 frontend testi** geçti.70 ortak fixture:28 MACD smoothing/source ve42 BB basis/source/offset vakası. Dört histogram durumu, renk-only writer güncellemesi, ayrı çıktı kimliği/warmup, gap/onarım, nested stil onayı ve negatif kaydırmada selected-value/warmup ayrımı dahil sekiz yeni test.
- TypeScript ve üretim derlemesi geçti. Ana JS556.97kB, gzip177.03kB. Mevcut500kB uyarısı ve QA01 performans/p95 kabulü açık kalır.
- **24 yeni üretim App tarayıcı kontrolü** geçti: yedi gösterge/on bir native çıktı bütün noktalarda Python eşleşmesi; bağımsız output Data window; kayıp ACK/conflict/reload; tekil visibility ve warmup;50 RSI pane döngüsü boyunca MACD/ATR korunması; grid eksikliğinde temizleme ve onarım/revizyon; RSI sürüm/coin/timeframe/reload/server restart; dört gerçek histogram rengi; BB±offset ve renk/width kaydı; BB değişirken MACD manuel scale; nested MACD stil onayı;20 MACD pane aç/kapa döngüsü ve üç sahipli serinin temizliği;1024px açık/koyu form.
- G02/G03/T08 için **39 ilgili regresyon tarayıcı kontrolü** geçti. Sentetik public market ve izole SQLite kullanıldı; kullanıcı DB'sine test göstergesi yazılmadı. Page error0, dış/hesap/emir çağrısı0. Açık/koyu ekranlar incelendi; fiziksel GPU/touch veya canlı vendor parity kabulü yok.

Kanıt: `reports/chart-g05-validation-20261112.json`, `reports/g05-*.log`, `chart-g05-*.png`, SHA256 manifesti `reports/chart-g05-delivery-20261112.json`. [V3 sözleşmesi](contracts/indicators-v3.json). Eski teslim/sözleşmeler tarihsel olarak korunur.
