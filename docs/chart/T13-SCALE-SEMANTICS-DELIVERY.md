# T13 — lineer/log görünüm semantiği

12 Kasım 2026. Tamamlandı; plan15/27. Sıradaki G04 metin/not/fiyat etiketi.

## Kullanıcı davranışı

Alt bardaki Fiyat ekseni türü Lineer/Logaritmik seçer. Bu bir görüntüleme tercihidir; geometri türü, anchor fiyatı/zamanı, oran listesi, maliyet varsayımı, canonical hash veya çizim revision'ı değişmez. Görünüm tercihi browser-local chart-view/1 olarak agentrader.chartView anahtarında saklanır; reload sırasında tanınan sürüm yeniden uygulanır. Geçersiz/bilinmeyen kayıt lineere döner. Sunucuya veya başka tarayıcıya senkronizasyon iddiası yoktur.

Tür değişiminde görünür mumlar native autoscale ile yeniden sığdırılır. Önceki manuel dikey aralık taşınmaz; kullanıcı geçişten sonra yine manuel fiyat ölçeğine geçebilir. Zaman eksenindeki zoom/range korunur. Hacim ve RSI normal ölçektedir; sonradan açılan/yeniden taşınan pane'ler de açıkça mode0 alır. EMA verisi değiştirilmez; fiyat pane'inde aynı log dönüşümle gösterilir.

Log görünümde yatay çizgi/yatay ışın, bölge, Fibonacci/extension, pozisyon planının seviye ve alanları, cetvelin uç nokta ölçümü desteklenir. Fibonacci mevcut aritmetik fiyat formülünü korur:100→400 için0.5 seviyesi250'dir,200 değildir. Cetvelin diyagonali yalnız iki uç arasındaki görsel ölçüm kılavuzudur; ara zamanlar için priceAt fonksiyonu sunmaz.

## Açık BLOCKED sınırı

Trend, ray, extended_line ve parallel_channel log görünümde gizlenir; kayıtlar silinmez. Liste Logda engelli gösterir, seçili nesne açıklaması BLOCKED nedenini belirtir. Rail, kısayol ve komut araması bu araçları logda etkinleştiremez. Geometri formu ve çizim tutamakları kapanır; görünürlük/kilit gibi yönetim bilgileri ayrı kalır. Lineere dönünce aynı geometri yeniden görünür.

Log görünümde bütün çizimlerde pointer sürüklemesi kapalıdır; desteklenen sabit fiyat araçları listeden seçilip sayısal formda düzenlenebilir ve grafiğe yeni noktalarla yerleştirilebilir. Bu, logda toplu hareketin çarpımsal mı toplamsal mı olacağını sessizce seçmeyi önler. Aktif hareket ölçek değişiminde iptal edilir, chart interaction kilidi bırakılır. Native mod ve React görünüm durumu ayrı kontrol edilir; geçişte eski bir render izin vermez. Bilinmeyen gelecek araçlar logda varsayılan destekli sayılmaz.

Bu teslim yeni logaritmik trend/kanal fiyat fonksiyonu veya geometrik Fibonacci sürümü üretmez. T13 kabulündeki desteklenmeyen birleşimin açık BLOCKED olması yolu uygulanmıştır. Böyle bir hesap istenirse ayrı geometri şeması, hassasiyet ve kanonik sorgu sürümüyle eklenmelidir; mevcut kayıtların anlamı değiştirilmez.

## Kanonik sözleşme ve native motor

chart-scale-policy/1 registry/capability alanı geometry_scale=LINEAR, log görüntü desteği veya BLOCKED_STRAIGHT_SLOPE ve log_geometry_query=BLOCKED_UNSUPPORTED_SCALE bildirir. Native görünüm ile query/canonical_hash scale parametresi aynı şey değildir. Kanonik API'ye scale=LOG gönderilirse UNSUPPORTED_SCALE alınır; log görünümü seçmek kanonik LINEAR sorgusunu gizlice loga çeviremez. Tracking/emir yetkisi eklenmez. Geometri/kayıt biçimi v7 olarak kalır; DB veya drawing migration yoktur.

Kurulu Lightweight Charts motorunun PriceScaleApi.setVisibleRange ve mode geçişi kaynakta ve gerçek runtime'da incelendi. Özelleştirilmiş fiyat aralığını log moduna ham fiyat aralığı olarak tekrar geçirmek anlamsız büyüklük/Infinity üretebiliyor; yalnız mode değiştirip eski custom aralığı taşımak da güvenli değil. Private log formülünü kopyalamak veya vendor kodunu değiştirmek yerine desteklenen applyOptions({mode,autoScale:true}) kullanılır. Bu nedenle otomatik sığdırma geçişin açık ürün davranışıdır. Yeni pane'lerin global right-scale varsayılanından log miras alması da her hacim/RSI pane'ini mode0 başlatarak önlenir.

## Kabul

- **775 Python testi** geçti;4 yeni test sürümlü görünüm politikası, log kanonik sorgu reddi, anchor/hash/revision/restart değişmezliği ve yetki sınırını doğrular.
- **206 frontend testi** geçti;7 yeni test view tercihi/bozuk sürüm, destek matrisi, native autoscale geçişi, negatif manuel aralığın taşınmaması, logda gizle/geri getir, pointer edit engeli ve aktif sürükleme iptalini kapsar. TypeScript/üretim derlemesi geçti. Ana JS yaklaşık527kB minified/167kB gzip; mevcut Vite500kB chunk uyarısı sürer. QA01 performans/p95 işi kapanmaz.
- **14 gerçek production App tarayıcı kontrolü** geçti. Native mode/range, dört eğimli türün engeli, rail/search, Fibonacci250/200 ayrımı, yatay/bölge/cetvel/plan native fiyat koordinatları, pointer edit yokluğu, zaman zoom'u, EMA/RSI/hacim izolasyonu, autoscale roundtrip, browser-local reload ve lineere dönüşte tüm kayıtların aynılığı sınandı.
- PNG raster testi üç görüntüde fiyat250 için gerçek mor çizgi piksellerini native koordinat çevresinde aradı. Lineer koyu ve log koyuda803, log açıkta994 eşleşen piksel bulundu; hata1 fiziksel pikselin altında, DPR1.25. Bu yalnız DOM attribute karşılaştırması değildir. Tam raster/GPU performans veya bütün araç matrisinin raster kabulü iddiası yoktur.
- T12/T06/T04/T07/T05/G01/G06/G02/G03 **114 regresyon tarayıcı kontrolü** geçti. Page error0, dış istek0, hesap/emir API çağrısı0. Testler kontrollü piyasa verisi ve izole SQLite kullanır; kullanıcı DB'sine test çizimi yazılmaz. Açık/koyu ürün ekranları incelendi.

Kanıt: reports/chart-t13-validation-20261112.json; chart-t13-linear-dark/log-dark/log-light-20261112.png. Kaynak/derleme/test/native engine SHA256 kayıtları reports/chart-t13-delivery-20261112.json.
