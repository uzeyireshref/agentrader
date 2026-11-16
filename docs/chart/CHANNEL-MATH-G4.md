# G4 — Kanal/pitchfork matematiği ve regresyon UTC sözleşmesi

15 Kasım 2026. Kayıt şeması chart-channel-family/1 korunur. Hesap sürümü chart-channel-calculation/1. Göç veya kayıt yeniden yazımı yapılmaz.

## Destek ve erişim

Parallel, flat, disjoint, regression, pitchfork, Schiff, modified Schiff ve inside pitchfork artık backend ve mevcut G3 tekil/toplu HTTP uçlarında hesaplanır. İlgili kayıt şemasının katalog geometry_query özelliği açıktır. Toplam 25 çizim varyantının 22 matematiksel varyantı hesaplanabilir; üç metin aracı matematiksel işlem sunmaz. Gösterge serileri, bağlı uzun notlar, bot adaptörü ve Fibonacci projection bu paketle açılmaz.

İşlemler: geometry, priceAt, boundsAt, contains, distance, slope. Dört pitchfork türü ayrıca level sunar. geometry ve slope için inputs={}; priceAt/boundsAt için time; contains/distance için time+query_price; level için time+ratio gerekir. G3 request schema ve nesne expected_revision/context_id kontrolleri aynen geçerlidir. LINEAR ve LOG aile şemasında desteklenir; eski diğer araçların ölçek kısıtları değişmez.

geometry, veri koordinatlarında çizgi uçları (logical ve price), rol, extend/visible bilgisi ve türetilmiş tutamaçları döndürür. Gizlenen median matematiksel olarak hesaplanabilir; görünürlük/kilit hesap veya emir yetkisi değildir. slope, median ve sınır eğimlerini PRICE_PER_BAR veya LOG_PRICE_PER_BAR birimiyle verir. Dikey çizgide slope değeri null+UNDEFINED_VERTICAL; geometry uçları geçerlidir. Tek bir zamandaki fiyat/bant tanımsızsa VERTICAL_GEOMETRY/UNSUPPORTED_OPERATION döner; sahte fiyat üretilmez.

priceAt matematiksel median fiyatıdır. boundsAt alt/üst sınır, median ve fiyat biriminde genişlik verir. LOG'da median dönüşmüş eksenin orta çizgisidir; ham fiyatların aritmetik ortalaması olmak zorunda değildir. contains/distance, o zamandaki sınırlar arasında kalmayı ve fiyat biriminde dış mesafeyi ölçer. Pitchfork level oranı saklanan seviyelerin işaretli karşılığı veya 0 (median) olmalıdır; keyfi yeni seviye türetilmez.

## Veri koordinatı tanımları

x, doğrulanmış intervaldeki mantıksal mum indeksidir. y, LINEAR'da fiyat; regresyon dışındaki LOG hesaplarda doğal log fiyattır. Sonuçta tekrar fiyat uzayına dönülür. Render, drag ve önizleme aynı saf log-fiyat dönüşümünü kullanır; grafik motorunun küçük fiyatlarda viewport’a göre değiştirdiği log ofseti hesap girdisi değildir. Küçük fiyatlı 1.68e−6 türetilmiş köşe ayrıca iki tarafta sınanır. A/B/C ham çapalardır.

- Parallel: C'nin A–B doğrusu üzerindeki karşılığından düşey farkı iki uçta aynı eksen ofseti oluşturur.
- Flat: ilk sınır A–B; diğer sınır C fiyatında yataydır.
- Disjoint: diğer sınırın sol ucu C.y+B.y−A.y, sağ ucu C.y olur.
- Pitchfork: M=(B+C)/2; yön A'dan M'ye.
- Schiff: başlangıç (A.x,(A.y+B.y)/2), yön buradan M'ye.
- Modified Schiff: başlangıç (A+B)/2, yön buradan M'ye.
- Inside: median M'den başlar; yön C−(A+B)/2'dir.

Yan seviye başlangıcı M ± oran×(C−M), yönü aracın median yönüdür. Ham üç çapa ile dört türetilmiş kanal tutamacı birbirine karıştırılmaz. Median/connector görünürlük ayarları modelde visible olarak belirtilir; bağlayıcı çizgiler bounds hesabına sokulmaz.

extend, frontend segment parametrizasyonuyla aynıdır: none 0≤t≤1; left t≤1; right t≥0; both sınırsız. Bu, ters yönlü çapalarda da A→B segment yönünü izler. Sorgu, gerekli sınır çizgilerinin tanımlı olmadığı kapsamda OUT_OF_SCOPE verir. Geometrik projeksiyon geleceğe uzanabilir; mum dizisine sahte kayıt eklenmez.

## Regresyon seçimi ve hazırlığı

Ham çapa UTC saniyeleri ve fiyatları aynen saklanır. İlk iki ham zamanın aynı olması da kaydı değiştirmeden WARMUP olarak değerlendirilebilir. Frontend oluşturma akışı fit fiyatını ham tıklama fiyatının üzerine yazmaz. İki tutamaç fit'ten türetilir; ham çapa fiyatı OLS girdisi değildir.

Her çapa, time ≤ ham zaman ve ham zaman×1000 ≤ close_time koşulunu sağlayan **gerçek** muma eşlenir. Eşleme en yakına yuvarlama değildir. Etkin başlangıçlar effective_anchor_times; ham zamanlar raw_anchor_times olarak yanıtta bulunur. Ters çapa sırası korunur, örnek seçimi kronolojiktir. Aralık iki uç dahil alınır.

- İki çapa aynı muma düşerse (tam aynı UTC dahil): WARMUP / INSUFFICIENT_REGRESSION_SAMPLES; sample_count=1, required_samples=2 ve etkin mum kimlikleri hata ayrıntısında.
- Geçmiş yüklenmemişse, çapa veri boşluğunda veya gelecekteyse: WAITING_FOR_DATA / REGRESSION_HISTORY_REQUIRED; bulunamayan etkin zaman null olarak açıkça belirtilir.
- Seçili aralıkta eksik mum: WAITING_FOR_DATA / GRID_GAP. HTTP ayrıca G2'nin tüm snapshot kalite/saat korumalarını uygular.
- Ham çapa veya mum uydurulmaz. Yeni veri geldiğinde aynı kayıttan yeniden hesap yapılır; reload da aynı ham kaydı okur.

Sorgu zamanı da regresyonda içinde bulunduğu gerçek mumun başlangıcına eşlenir; effective_query_time ayrıca döner. İleri projeksiyon yeni bir regresyon örneği eklemez. API'de gelecekte henüz olmayan sorgu mumu beklenir; grafikte bilinen fit'in extend çizgisi yine uzatılabilir.

HTTP varsayılanı kapalı mumlardır; include_open=true açıkça istenirse açık mum kullanılabilir. Frontend mevcut çizim davranışını koruyarak yüklü açık mumu örnek aralığı kapsıyorsa kullanır. Aynı mum listesi/politikası verildiğinde hesaplar eşleşir; open_candle_used ve sample_count bunu görünür kılar. Sadece açık mum eksik olduğu için HTTP bekliyorsa include_open tercihi sessizce değiştirilmez.

## OLS, sapma, bant ve ölçek

x=0..n−1; y seçilen open/high/low/close/hl2/hlc3/ohlc4 kaynağıdır. En az iki örnek gerekir. Eğim Σ((x−mx)(y−my))/Σ((x−mx)²); kesişim my−eğim×mx. Sapma, residual toplam karesinin n−1'e bölümünün kareköküdür. Etkin üst/alt sapma çarpanları bu değeri kullanır. İlgili sapma seçeneği kapalıysa üstte max(high−fit), altta max(fit−low) ekstrem farkı kullanılır.

Regresyon ham fiyatlarda hesaplanır; log görünüm istatistikleri değiştirmez. Mevcut REA/frontend Pearson gösterimindeki eksi işareti uyumluluk için korunmuştur: pearson=−Σxy/√(ΣxxΣyy); sabit seride 0. Yanıt pearson_convention=NEGATED_PRICE_CORRELATION_COMPATIBILITY ile bunun klasik fiyat korelasyon işareti olmadığını açıklar.

LINEAR geometrik hesaplar tam kesirdir. Regresyon istatistikleri ve LOG dönüşümleri FLOAT64'tür; decimal metin, 16 anlamlı basamak, mutlak 1e−8 ve göreli 1e−10 tolerans ilan edilir. Tolerans sayısal karşılaştırmada max(mutlak, göreli×ölçek) olarak ele alınır. Görsel kabul ayrıca ≤1 CSS px; bağımsız arşiv referanslarında <0.001 CSS px doğrulanır. Fiyat tick'e yuvarlanmaz; NaN/Infinity başarılı sonuç değildir.

## Görünür durum ve sınırlar

Grafik, hesap hazır değilken çizim grubunda data-family-state/data-family-reason ve okunur durum mesajı yayımlar. WARMUP, beklenen veri ve geçersiz veri ayrılır. Veri geldiğinde aynı piksel koordinatlarına dönülse de eski hata cache'i çizimi engellemez. Hazır çizgide data-family-state=READY olur.

Bu matematik desteği binding aktivasyonunu veya emir yetkisini açmaz. Eski binding API'sindeki DISPLAY_ONLY_CHANNEL_FAMILY kodu geriye uyumlu aktivasyon engeli olarak kalır; artık genel matematik eksikliği anlamına gelmez. canonical_hash açık veri/ölçekle aile modelini kapsar; otomatik binding hâlâ sunucuda engellidir. origin/manual koruması, not ilişkileri ve gerçek bot adaptörü sonraki paketlerin konusudur.

## Kanıt ayrımı

Ortak channel-family-g4.json vektörleri iki tarafta bağımsız elle türetilmiş fiyat/bant referanslarını sınar. REA kapalı fiyat örneklerinin eski zamanları düzensiz olduğundan istatistik referans testi açıkça sentetik sürekli gride taşınmıştır; arşiv fiyatları ve beklenen OLS sonuçları değişmez, canlı piyasada mum uydurulmaz. Eski tarihli kabul finalizer'ı tarihsel birleştirici olarak işaretlenir; yeni G4 kanıtları ayrı klasördedir.

API/SQLite ve FeedState testleri, gerçek üretim tarayıcısındaki normal/ara UTC/DPR 2 koordinat grupları, iki eski regresyon engelinin veri sonrası başarıya dönüşmesi, aynı mum/gap mesajları, reload ve pointer/ayar/undo kabulü ayrı kaydedilir. Bu G4 hesap kabulüdür; gerçek bot adaptörü ve Demo runtime gözlemi G8/G11 kapsamındadır.
