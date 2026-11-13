# T02 — Kanonik hesap ve grafik eşleşmesi

10 Kasım 2026. T02 TAMAMLANDI. Saf geometri çekirdeği ve frontend eşleşmesi uygulandı. Canlı karar/izleme ve emir bağlantısı yoktur.

## Kesin sonuç ve sorgular

agentrader/drawings/calculations.py içindeki query saf bir Python işlevidir; HTTP hesap endpointi veya bot adaptörü eklenmedi. Girdi mevcut strict geometry ve açık sorgu bağlamıdır. chart-geometry/1 sonuçları numerator/denominator metni taşır. decimal yalnız sonlu ondalık gösterim varsa doludur; örneğin 310/3 için null olur. Yuvarlanmış sayı kesin fiyat diye sunulmaz. Fraction aritmetiği Decimal ortam hassasiyetinden bağımsızdır. Float fiyat, bool zaman ve milisaniye/saniye karışıklığı reddedilir.

| Tür | Sorgu | Anlam |
| --- | --- | --- |
| horizontal | priceAt, distance | Sabit fiyat, mutlak fiyat mesafesi |
| zone | contains, distance | Dahil sınırlar; içindeyken mesafe sıfır, dışındayken yakın sınıra mesafe |
| trend | priceAt, distance | Anchor aralığında mum logical konumuyla parça doğrusal fiyat; mutlak fiyat mesafesi |
| fibonacci | level | Kaydedilen yön ve yedi sabit oran; tick'e yuvarlama yok |

Her sorgu açık UTC saniye zamanı ister. Zone/trend/Fib sorguları iki anchor arasındaki dahil zaman aralığıyla sınırlıdır. Yatay çizginin geometri zamanı sınırsızdır; takip geçerliliği ileride ayrı bağlanır. Ruler ve risk planı hesapları T03/T04 kapsamındadır. LOG ölçek T13'e kadar UNSUPPORTED_SCALE verir.

## Grid ve hash

logical_position yüklü zaman dizisindeki bilinen boşluklar dahil grafik eşlemesini rasyonel olarak tanımlar; aralık dışında extrapolation yapmaz. Trend query ise verified_grid üzerinden daha dar davranır: 2–4000 artan/tekil UTC saniye barı, desteklenen açık interval, UTC bucket hizası ve eksiksiz adım dizisi gerekir. Haftalık hizalama Pazartesi UTC'dir. Boşluklu görselde fiyat hesaplanabiliyor olması kanonik uygunluk değildir: GRID_GAP, GRID_BUCKET_MISMATCH, INVALID_GRID veya GRID_OUT_OF_RANGE ile engellenir. Bu statik giriş doğrulaması upstream kalite/epoch kanıtının yerini tutmaz; P2/P3 hâlâ gereklidir.

canonical_hash üssüz ondalık normalize geometri, kaynak/ortam/ürün, scale, interval ve grid'i SHA-256 ile bağlar. Label görünüm metnidir, hash'e katılmaz. Anchor sırası korunur; mevcut zone sıralaması eski sözleşmeyle aynıdır. Owner/drawing_id/revision ve kural sürümü hash yerine kullanılamaz; P4 bunları ayrıca bağlayacak. Hash eşliği canlı uygunluk veya kayıt sahipliği kanıtı değildir.

## Grafik ve giriş yolları

frontend/src/exactGeometry.ts BigInt/rasyonel aritmetiği sağlar. Fibonacci seviyeleri kesin anchor metinlerinden hesaplanır ve yalnız priceToCoordinate sınırında Number'a çevrilir. Grafik pikselleri float kalır; buradan yeni kesin bot fiyatı türetilmez.

Yeni nokta ve sürükleme pozitif tick ızgarasına en yakın seviyeyi seçer; tam yarımda yukarı gider. Sürükleme eski anchor'ı önce Number'a çevirmeden yaklaşık fare hareketini ekler. Fare hareketi kesin piyasa verisi değil, kullanıcının yaklaşık koordinat girdisidir. Form ise tick dışı yeni fiyatı reddeder, sessizce yuvarlamaz. İki yol aynı ondalık tick bölünebilirliğini uygular. Eski tick dışı kaydı yalnız yeniden adlandırma davranışı korunur; strict legacy API'nin tarihsel serbest fiyat kabulü değiştirilmedi. Kanonik türetilmiş seviyeler emir tick'ine zorlanmaz.

Fibonacci'de görünmez hit-line'ların yanlış/eksik koordinatları düzeltildi; her görünür seviye kendi tıklama alanıyla aynı konumdadır. ProjectionCache tüm eşleşen elemanları günceller. Görsel extrapolation eski renderer'da korunur; kanonik sorgu bunu kullanmaz.

## Doğrulama ve kapsam

Ortak sabit referans: frontend/tests/fixtures/geometry-parity.json. Sekiz örnek dört türü, ters anchor'ı, kesirli zamanı, micro fiyatı, float altı hassasiyeti ve tekrar eden kesri kapsar. Python ayrıca bağımsız Decimal matrisinde 77 kesin kesir kontrolü, grid/UTC/weekly/scope/hash/negatif senaryoları sınar. TypeScript testleri bu referansı gerçek timeToLogical ve kesin Fibonacci işlevleriyle karşılaştırır; büyük fiyatlarda sürükleme/form tick eşleşmesini doğrular.

Yeni üretim bundle: index-DLB6RP6i.js. scripts/check_chart_t02.py kontrollü sentetik piyasa ile güncel üretim App'ini headless Chromium'da çalıştırır: ters Fib'in yedi seviyesi ve kesirli anchor trendi native koordinatlarla eşleşir; Fib tıklama alanları da kontrol edilir. Bu 8 sayısal kontrol fiziksel ekran/raster kabulü değildir. Screenshot ayrıca incelendi. İlk kontrol seçicisi görünür ve hit çizgisini birlikte seçerek başarısız oldu; ilk rapor korundu, seçici daraltıldı ve hit çizgisi hatası ayrı test/düzeltmeyle kapandı.

Sonuçlar reports/chart-t02-validation-20261110.json içinde kayıtlıdır. 706 Python ve 136 frontend testi ile TypeScript/üretim derlemesi geçti. Kısa 10 saniye / 4.000 mum / 200 karma çizim performans kontrolünde p95 16.799999999999272 ms; 33,34 ms tarama hedefi geçti. Bu kısa ölçüm genel performans kabulü değildir. Önceki aday02 arşivi korunur. Önceki 30 dakika performans kanıtı yeni bundle için tekrar edilmedi; yeni pakette sınırsız oturum/performance/cihaz kabulü iddia edilmez. Kullanıcı DB'sine, gerçek piyasa/hesap/emir endpointlerine yazılmadı.

Registry mevcut dört tür için PURE_OFFLINE_REQUIRES_CONTEXT ve desteklenen sorguları bildirir. Çizim sözleşmesi LIVE_EVALUATION_NOT_IMPLEMENTED nedeniyle BLOCKED kalır; tracking_activation ve order_authority false'tur. Sıradaki paket P2 güvenilir saat ve uzun kesinti davranışıdır.
