# Profesyonel grafik — seçilmiş ürün kapsamı

10 Kasım 2026. En son kullanıcı açıklaması: mevcut grafiğimiz ilkel; profesyonel bir grafikte ihtiyaç duyulan işlev ve tasarım kalitesi hedefleniyor. Araştırma mevcut araçlarımızla sınırlanmayacak. TradingView'deki her özellik de ürüne dahil edilmeyecek. Bu belge, REA-FULL-CHART-SCOPE.md içindeki bütün özellikleri uygulama veya her varyantı eşit derinlikte inceleme yorumundan üstündür.

## Seçim yöntemi

Önce geniş referans envanteri; ardından her yetenek için kullanıcı işine katkı, kullanım sıklığı, veri uygunluğu, doğruluk, etkileşim ve bakım maliyeti değerlendirilir. Seçilen özellikler derinlemesine çözülür. İleri/ertelenmiş özellikler karar gerekçesiyle kaydedilir. Mevcut uygulama bir başlangıç envanteridir; hangi ihtiyaçların önemli olduğunun filtresi değildir.

“Temel” aşağıdaki ürün için planlama kararıdır; bütün profesyonellerin kullanması gereken evrensel özellik listesi veya finansal tavsiye değildir. Geliştirme sırası bağımlılık ve doğrulama sonunda REA04'te kesinleşir.

## A — Temel profesyonel grafik ihtiyaçları

| Alan | Hedef kapsam |
| --- | --- |
| Veri doğruluğu | Doğru OHLC/hacim, kaynak ve fiyat türü, hassasiyet/tick, history pagination, açık/kapalı mum, kesinti/reconnect/stale ve coin/interval izolasyonu |
| Grafik ve eksen | Mum ve çizgi görünümü, net crosshair/OHLC, düzenli fiyat/zaman ölçeği, auto/manual/fit, lineer/log, UTC/timezone, pan/zoom/canlıya dön/fullscreen |
| Çizim çekirdeği | Horizontal line/ray, trend/ray/extended line, bölge/rectangle, parallel channel, Fib retracement/temel extension, fiyat-zaman ölçümü, long/short planı, metin/not/price label |
| Çizim yönetimi | Seçme/tutamak/gövde taşıma, snap, iptal, numeric edit, stil, kilit/gizle, clone, katman/nesne ağacı, undo/redo, kalıcılık, interval görünürlüğü |
| Göstergeler | Kalıcı ayar/pane modeli; SMA/EMA, RSI, ATR, MACD, Bollinger Bands ve VWAP aileleri. Parametre/source/seed/warmup/offset/timeframe açıklığı ve bağımsız sayısal referans |
| Günlük kullanım | Sembol arama/watchlist, hızlı interval seçimi, gösterge/araç arama, çalışma alanı/ayar şablonu, anlamlı kısayollar, veri penceresi, gizlenebilir yan paneller |
| Tasarım | Grafik odaklı kompakt kabuk, tutarlı ikon/font/renk/boşluk, okunur fiyatlar, etiket çakışması yönetimi, doğru selected/hover/focus/disabled/stale durumları, açık/koyu tema ve kontrollü pane/dialog |
| Kalite | Geometri/UI/bot hesap eşleşmesi, kayıt yarışları, klavye erişimi, DPR/resize/fullscreen, ölçülmüş etkileşim performansı ve görsel kabul |

MACD/Bollinger ve metin/etiket ihtiyaçları önceki 21 paketlik çekirdeğin dışında kalmıştı; artık kapsam değerlendirmesinde temel ihtiyaçlar arasındadır. Bu, kodlandıkları veya test edildikleri anlamına gelmez. Risk planı hâlâ varsayımsal çizimdir; bu kapsam finansal yürütme yetkisi oluşturmaz.

## B — Kullanım ihtiyacına göre ileri özellikler

Heikin Ashi ve diğer sentetik grafik türleri; çoklu grafik ve sembol/interval/crosshair senkronizasyonu; replay; çizimden koşul/uyarı; volume profile, anchored profile ve gelişmiş hacim araçları; anchored VWAP'ın gelişmiş varyantları; regression channel/pitchfork; daha geniş gösterge kütüphanesi. Her biri kendi veri, doğruluk ve kullanım gerekçesiyle seçilir. Özellikle gerçek orderflow/footprint için OHLCV'nin yeterli olduğu varsayılmaz.

## C — Şimdilik ürün hedefi olmayan özellikler

Sosyal paylaşım/akış, topluluk/marketplace ve editör yayıncılığı; reklam/abonelik/marka yüzeyleri; broker/order ticket entegrasyonu; bütün Gann/Elliott/harmonik/dekoratif araç varyantları; bütün topluluk scriptlerini veya yüzlerce özel göstergeyi kopyalamak. Bunların arayüzde bulunması araştırma envanterine girebilir, uygulama zorunluluğu oluşturmaz. Gerçek kullanım ihtiyacı doğarsa kapsam yeniden değerlendirilir.

## Önce çözülmesi gereken ürün sorunları

1. Grafik alanını daraltan kabuk ve sürekli yardımcı paneller; küçük ve düşük karşıtlıklı kritik metinler.
2. Parçalı araç erişimi, ikon dili ve ayar/nesne yönetimi; seçim ve hata durumlarının belirsizliği.
3. Eksik araç/gösterge ayarları ve profesyonel kullanım için gereken yeni yetenekler.
4. Mevcut kesin hesap/kayıt/veri güvenilirliği çalışmalarını koruyarak grafik ile ayar/etiket/ekseni tek tutarlı sistem haline getirmek.

[Referans bulguları](REA-REFERENCE-ANALYSIS.md), [tasarım şartnamesi](REA-DESIGN-SPEC.md) ve yeni geniş envanter bu sorunlara çözüm üretecek. Görsel kalite en sona bırakılan kozmetik paket değildir. Önce analiz ve plan; sonra seçilen işlevlerle birlikte tasarım uygulaması.

## Sayısal ve görsel kabul eki —11 Kasım geniş gösterge turu

[ATR/RSI/VWAP araştırması](REA-ATR-RSI-VWAP-DATA.md): gösterge kimliği; source, length, smoothing, calculation interval, anchor/session, offset ve volume provenansıyla birlikte tanımlanmalı. Ana gösterge ile üstündeki smoothing overlay ayrı çıktılardır. Session/1h VWAP ile Session/1D VWAP tek veriymiş gibi kullanılamaz. Data window ve ayar akışları işlevle aynı anda tasarlanmalı; boş çıktı nedenleri, disabled bağımlı inputlar, uzun modal scroll/focus ve fiyat/gösterge pane ölçekleri kapsam dahilinde. Fullscreen tablo/CSV veya bütün üst-zaman seçenekleri bu gözlemle otomatik zorunlu yapılmaz. Sayısal fixturelar finite-window/recurrence/convergence/rounded-volume-consistency olarak ayrı sınıflanır; araştırma sonucu ürün kabulü değildir.

## Veri yaşamı ve etkileşim kabul eki —11 Kasım

[Yaşam döngüsü/piyasa/pointer turu](REA-LIFECYCLE-MARKET-POINTER.md): profesyonel çekirdekte açık/kapalı/history/catchup, market status ve data freshness ayrı olmalı. Market kimliği last/mark/spot/contract ayrımını taşır; referansın tüm derivative-metric ürünleri ilk çekirdeğe eklenmez. Hacmi olmayan ama OHLCsi olan kaynakta VWAP nedenli unavailable verir. Hata, gizleme ve sıfır veri farklıdır.

İlk gerçek endpoint-drag/Undo örneği alındı; body/multi/cancel/snap ve ölçülmüş performans henüz açık. UI bar indeksleri persistence kimliği değildir; eski Fib okuyucusundaki1 indeks farkı UTC ankraj karşılaştırması olmadan kapatılamaz. Bütün referans özelliklerini araştırmanın bitiş koşulu yapmak yerine bu kalan veri/ankraj/pointer soruları REA04te karşılığı olan iş ve kabul maddelerine bağlanmalı.


## REA04 uygulama kapsamı kesinleşti

11 Kasım2026: [REA04](REA04-IMPLEMENTATION-ROADMAP.md) temel kapsamı altı yeni G paketiyle eski çekirdeğe bağladı; toplam27 paket,5 tamamlanmış. Geniş araştırma sınırlamaları ve hedefli geri dönüş politikasıyla kapandı. İlk iş G01 kabuk; MACD/BB ve metin/etiket temel kapsam olarak G05/G04, günlük erişim G06. Koşullu ileri ve kapsam dışı aileler bu belgedeki ayrımı korur. Yeni ürün uygulaması henüz başlamadı.
