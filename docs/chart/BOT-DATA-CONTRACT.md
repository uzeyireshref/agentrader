# Grafik → bot veri sözleşmesi

10 Kasım 2026 — E3. Sürüm `chart-bot-input/1.0-draft`. **Bu bir tasarım sözleşmesidir; bot adaptörü, strateji kaydı, olay üreticisi veya emir bağlantısı uygulanmadı.** [Makine okunur kurallar](contracts/chart-bot-input-v1.json). Mevcut grafik adayı değişmedi; E1/B5 kabul açıkları korunur.

## Kaynak ve kimlik

Bot ileride pikselleri veya DOM’u okumayacak. Çizim kaynağı DrawingService’in kaydedilmiş sürümü, piyasa kaynağı backend’in doğrulanmış feed state’i olacak. Tarayıcı kapanınca çizim tanımı kaybolmaz; ancak bugünkü public feed talep üzerine açılır ve W4 bot worker’ı henüz yoktur. Tarayıcı kapansa da çalışan takip döngüsü hedef mimaridir, mevcut özellik değildir.

Kimlik `(source, environment, product, price_type, symbol, interval)` birlikte doğrulanır. Şu an kaynak `binance_usdm_live_trade_price`, ortam `live_public`, ürün `USD-M`, fiyat `LAST_PRICE`; yalnız katalogdaki USDT perpetual semboller. Mark/index/bid/ask veya demo hesap fiyatı buna sessizce çevrilmez. UI’da coin/zaman dilimi değiştirmek kalıcı bot bağını değiştirmez.

| Mevcut yol | İçerik | Sınır |
| --- | --- | --- |
| GET /api/markets | Piyasa kimliği, katalog ve tick_size | Katalog güncelliği ayrıca gerekir |
| GET /api/candles | Mumlar, server_time/quality ve sayfalama | Geçmiş veri yeni canlı fırsat değildir |
| WS /api/market-stream | Snapshot/update, generation/sequence, kalite ve kaynak | Kalıcı olay kuyruğu veya kesin her-tick akışı değildir |
| GET /api/workspaces/{id}/drawings?symbol=... | Silinmemiş son çizim sürümleri | Çizimde interval yok; takip bağı ayrı tanımlanır |
| GET /api/drawings/{id} | Güncel head, deleted ve revision | Güncelleme zamanı revizyon yerine kullanılamaz |

Yeni alanlar mevcut strict geometry CRUD isteğine eklenmeyecek. Hedef bot bağlamı ayrı, sürümlü bir adapter DTO/kayıt olacak; endpoint veya DB migration bu adımda eklenmedi.

## Zaman, sayı ve mum

`candle.time`, `anchors[].time`, `close_event.time` UTC **saniye** tam sayısıdır; `close_time`, observed_at, received_at, close_event.event_time UTC **milisaniye**dir. drawing.updated_at mevcut backend’de UTC saniye sayısıdır ve kesirli olabilir. close_time bar sonunu, close_event.time bar açılış kimliğini belirtir; birbirine karıştırılmaz. 1w hizası mevcut Pazartesi UTC bucket kuralına uyar; yerel saat gösterimi karar girdisi değildir.

Mum OHLC pozitif/sonlu, low≤open/close≤high, hacimler sonlu/negatif olmayan, zamanlar artan ve tekil olmalı. Kapalı mum açık hale dönemez. Reconnect/history düzeltmesi veri sürümünü etkiler; eski karar kanıtı sonradan değiştirilmez ve geçmiş close yeni canlı karar gibi yürütülmez. Varsayılan değerlendirme yalnız kapalı mumda; açık mum gözlemlenebilir, otomatik kapanış varsayılmaz. OHLC içindeki temasların sırası veya aynı mumda stop/hedef sırası bilinmiş sayılmaz.

Bugünkü mum endpointi OHLC/hacmi JSON number/float olarak sunar. `Decimal(str(float))` orijinal borsa metnini geri getirmez. Hedef adapter kesin ondalık metin/provenance sağlamadan tick hassasiyetine dayanan bot kararına uygun değildir. Çizim anchor fiyatları zaten pozitif ondalık metindir; bilimsel gösterim mevcut parser’da mümkün olabilir. Kanonik hedefte Decimal ile doğrulanıp üssüz metne normalize edilir; binary-float ile yeni doğruluk üretilmez. Eski/API çizimlerinde tick dışı fiyat mümkün olduğundan bot tick kontrolünü yeniden yapar, sessizce yuvarlamaz. Fibonacci türetilmiş seviyeleri emir fiyatı değildir; ara oran hesabı tick’e zorla yuvarlanmaz. Emir yuvarlama ayrı yürütme katmanıdır.

## Akış, epoch ve tazelik

Generation/sequence FeedState örneğine aittir; süreç/yeniden edinme sonrası yeniden başlayabilir. Her yerel stream ömrü için yeni `stream_epoch` gerekir. Epoch değişince eski sıra numaraları kıyaslanmaz; önce snapshot, kimlik/kalite/continuity doğrulaması gerekir. Aynı epoch’ta eski generation/sequence reddedilir. Eşit çift heartbeat’tir; ikinci veri/karar üretmez. Sequence durum değişiminde de artabilir; sunucu paketleri birleştirebildiği için sayı atlaması tek başına mum boşluğu değildir. Tamlık mum zamanları/quality ve ihtiyaç duyulan geçmişle kanıtlanır.

`close_event` son kapanış metadatasıdır ve sonraki heartbeat/update’larda tekrar gelebilir. Mevcut closed_keys hafızası bounded/in-memory, kalıcı dedup değildir. İleride kalıcı semantik olay kimliği gerekir; packet generation/sequence’e bağlanan id yeniden başlatmada yanlışlıkla tekrar fırsat üretemez. Başlangıç/reconnect snapshot’ı geçmiş close_event taşısa da yeni canlı olay doğurmaz.

Bugünkü UI LIVE/received_at kararı yerel Date.now farkına duyarlıdır. observed_at ve received_at ikisi de backend duvar saati olduğundan tek başına bağımsız saat güvencesi değildir. Güncel paket her normal upstream olayı için upstream event_time veya saat belirsizliği yayınlamaz. Bu açık R05’in bot öncesi çözülmesi gereken kısmıdır.

Karara uygunluk için status LIVE, quality.state OK, missing_bars=0, kuralın warmup geçmişi tam, piyasa kimliği ve çizim head revision eşleşmiş olmalı. Bunlar sağlansa bile aşağıdaki güvenilirlik kanıtları yoksa uygunluk verilmez.

Hedef politika: hem consumer monotonic son taşıma yaşı hem güvenilir upstream olay yaşı denetlenir. Önerilen varsayılan üst sınırlar 10 sn/10 sn; sürümlü kural politikasıdır, bugünkü runtime’a uygulanmış sayılmaz. Mevcut UI 10 sn stale ve backend 20 sn gecikme/stream guard’ı aynı semantik değildir. Heartbeat son upstream veri zamanını ilerletemez. Saat kanıtı yoksa, geleceğe giden damga/saat sıçraması varsa veya belirsizlik bütçesi aşılırsa **BLOCKED_CLOCK_UNTRUSTED**; yalnız UI LIVE olması yetmez.

## Çizim bağı ve geometri anlamı

Hedef bağda workspace/drawing_id/**drawing_revision**, binding_id/version, rule_id/version, piyasa kimliği ve **interval** açıkça saklanır. DrawingService tüm timeframe’lerde aynı sembol çizimini döndürebilir; takip timeframe’i bundan türetilmez. label yalnız görüntü metnidir, kod/kural/işlem talimatı değildir. Çizim tek başına kuralı etkinleştirmez; varsayılan bağ DISABLED’dır.

Çizim değişince yeni revision oluşur ve eski bağ durur. Silme/tombstone, head okunamaması, 409 veya binding revizyonu uyuşmazlığında karar üretilmez. Undo aynı geometriyi getirse bile yeni revision’dır; eski yetkiyi yeniden canlandırmaz. Yeniden bağ açık seçimle yapılır. Açık pozisyon koruması çizim değişti diye kaldırılmaz veya değiştirilmez.

| Tür | Bot için varsayılan yorum |
| --- | --- |
| horizontal | Tek anchor fiyatı; zaman sınırsız çizgi olabilir ama binding geçerlilik penceresi ayrıca zorunlu |
| zone | İki zaman arasındaki kapalı pencere ve min/max fiyat aralığı; geleceğe sonsuz bölge varsayılmaz |
| trend | Yalnız iki anchor arasındaki segment; otomatik ray/uzatma yok |
| fibonacci | Kaydedilen anchor sırası korunur; `p0+(p1−p0)×r`, r=0/0.236/0.382/0.5/0.618/0.786/1; zaman kapsamı açık seçilir, sessiz uzatma yok |

Mevcut grafik eşit bar aralıklı logical x eksenini kullanır. Trendde boşluk varken saf UTC doğrusal formül farklı sonuç verebilir. Hedef default `LOADED_BAR_LOGICAL_PIECEWISE_V1`: sabit doğrulanmış bar grid’inde t’nin yeri mevcut timeToLogical eşlemesiyle belirlenir; `p=p0+(p1−p0)×(L(t)−L(t0))/(L(t1)−L(t0))`. Grid kanıtı/hash’i bağın geometrik bağlamına eklenir. Gerekli grid yok/eksik/değişmişse veya sorgu segment dışında ise BLOCKED/OUT_OF_SCOPE; son bar aralığını uydurarak extrapolation yapılmaz. Düzenli ve eksiksiz aralıkta UTC ve logical oran aynı olabilir; bunu boşluklu grafiğe genelleme. UTC_LINEAR veya ray istenirse ayrı açık semantik sürümü ve grafik/bot eşleşme testi gerekir. Çizim şeklinin ne anlama geldiği pikselden çıkarılmaz.

## Değerlendirme ve olay kaydı

Güvenilir adapter gelecekte şu kanıtların **tamamını** sağlamalı: kesin ondalık veri, stream epoch, monotonic taşıma yaşı, upstream saat güvencesi, eksiksiz quality snapshot, sürüme bağlı kural/geometri, güncel head kontrolü ve kalıcı dedup. Bunların eksikliği bugün NOT_IMPLEMENTED/BLOCKED sonucudur; boş alanlara iyi varsayılan doldurulmaz.

Değerlendirme girdisi immutable piyasa/mum snapshot özeti, bar-grid/geometri hash’i, drawing/binding/rule revision, epoch ve freshness/quality kanıtını taşır. Gelecekte semantik olay kalıcı yazılmadan aynı uygulama DB transaction’ında çizim head revision yeniden karşılaştırılır; uyuşmazsa event commit olmaz. Piyasa ve uygulama DB’leri ayrı olduğundan otomatik çapraz-DB atomic snapshot varmış gibi davranılmaz. Üretilen kanıt donmuş snapshot’tır; sonraki yürütme ayrıca güncelliği/yetkiyi denetler.

Kapalı mum varsayılanı için kalıcı olay anahtarı: kaynak+ortam+ürün+fiyat türü+sembol+interval+workspace+drawing_id/revision+binding_id/version+rule_id/version+event_kind+candle_open_time. Sequence/generation/label/piksel anahtarın parçası değildir. Aynı mumda çoklu intrabar temas gerekiyorsa daha ince veri/ayrı occurrence kimliği tasarlanır; bu varsayılanı zorlayarak çoklu temas uydurulmaz. Request_id HTTP yazma idempotency’si içindir; strateji olayı dedup anahtarı değildir.

Sonuçlar: BLOCKED (nedenli), OBSERVE_ONLY veya EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY. Hiçbiri borsa emri/yetki değildir. Bu E3 sözleşmesi mevcut bot runtime’ı veya trade permission oluşturmaz. E4 bu kuralları kuru çalışma/replay/bildirim örneklerine çevirecek; E5 incelemesi ve açık kabul işleri tamamlanmadan entegrasyon başlamaz.


E4 devamı: [kuru çalışma planı](DRY-RUN-PLAN.md),36 tanımlı senaryo ve beklenen durum/bildirim sonuçlarını içerir; motor uygulaması veya gerçek gönderim değildir.


## P1 uygulama güncellemesi — 10 Kasım 2026

Önceki float-only taşıma açıklaması eski adayın durumudur. Güncel backend, mevcut grafik sayıları yanında chart-exact-decimal/1 sidecar taşır; ayrıntılar [EXACT-DATA.md](EXACT-DATA.md). Kesinlik kanıtı eksik satırlar UNPROVEN kalır. Bot adaptörü uygulanmadı; P2–P7 şartları ve BLOCKED kuralları sürer.


## P2 uygulama güncellemesi — 10 Kasım 2026

P2 tamamlandı: enjekte edilebilir wall/monotonic saat, upstream saat ölçümü ve belirsizlik, heartbeat yaş koruması ve uzun kesinti snapshot bariyeri uygulandı. 718 Python / 143 frontend testi, 9 üretim App kontrolü ve gerçek public saat kanıtı geçti. Önceki Date.now-only/sıradaki P2 açıklamaları tarihsel durumdur. [Güncel kapsam ve sınırlar](CLOCK-RELIABILITY.md). Sırada P3; epoch/immutable kalite kanıtı ve bot motoru henüz uygulanmadı. B5/fiziksel ve gerçek uzun borsa kesintisi kabulü değişmedi.


## P3 uygulama güncellemesi — 10 Kasım 2026

P3 tamamlandı: producer epoch, consumer snapshot/callback bariyeri, immutable snapshot/grid hash ve açık warmup kanıtı uygulandı. 729 Python / 153 frontend testi, kontrollü App reconnect ve iki gerçek public abonelik snapshot kontrolü geçti. Önceki epoch/immutable kanıtın henüz bulunmadığını söyleyen bölümler tarihsel durumdur. [Güncel kapsam](STREAM-EVIDENCE.md). Sıradaki T03; P4–P7, canlı bot, genel/cihaz kabulü ve gerçek uzun borsa kesintisi kanıtı tamamlanmadı.
