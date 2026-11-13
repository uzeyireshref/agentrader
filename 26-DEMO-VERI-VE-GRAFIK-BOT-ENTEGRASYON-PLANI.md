# Demo veri kaynağı ve grafik–bot entegrasyon planı

13 Kasım 2026 · Durum: PLAN_READY / uygulama başlamadı.

## Bağlayıcı ürün kararı

Grafik, mum geçmişi, göstergeler, alarmlar, strateji değerlendirmesi ve bot yürütmesi Binance USD-M Demo ortamını kullanacak. Gerçek ortama geçiş en son, ayrı kapsam ve yetkilendirmeyle yapılacak. Önceki public gerçek veri + demo işlem önerisinin yerini bu karar alır.

Bu belge yeni entegrasyon iş sırasıdır. docs/chart/PLAN.md içindeki tamamlanmış grafik paketlerini yeniden açmaz; eski fiziksel/genel kabul açıklarını kapatmaz. Kod değiştirme ve emir yürütme, bu plan belgesinin yazılmasıyla gerçekleşmiş sayılmaz. Demo testleri için somut plan/risk/yetki kontrolleri korunur.

## Değişmezler

- Çalışma ortamı yalnız demo; gerçek hesap desteği ve UI ortam değiştirme düğmesi bu kapsamda yok.
- Normal uygulama akışında gerçek public REST/WS kaynağına otomatik fallback yok. Demo erişilemiyorsa açık hata/STALE/GAP ve yeni giriş engeli.
- Public demo piyasa istemcisine hesap anahtarı verilmez. Özel demo hesap erişimi ayrı kalır.
- REST geçmişi, WS güncellemesi, exchangeInfo ve sunucu zamanı aynı doğrulanmış demo ortamına ait olmalı.
- Kaynak/ortam/ürün/sembol/interval/fiyat türü veri, hesap, kayıt ve kanıtta açık olmalı. LAST_PRICE ile MARK_PRICE aynı şey değildir; aynı ortam kullanmak bu farkı kaldırmaz.
- Kaynak kimliği yalnız etiketi değiştirerek yenilenmez. Eski hash, olay, binding ve test raporları tarihsel kayıttır.
- Emir niyeti önce kalıcı; tek hesap yazıcısı; belirsiz gönderimde tekrar POST yok; yeni stop doğrulanmadan eski koruma kaldırılmaz.
- Demo risk profili ve hesap ayarları kendiliğinden değişmez. Çizim veya alarm kaydetmek işlem onayı değildir.

## Başlangıç bulguları

market_data.py gerçek public REST ve SOURCE; market_feed.py gerçek public WS kullanıyor. live_public ve kaynak sabitleri backend geometri/kanıt/alarm/üst-zaman/binding denetimleri ile frontend tür ve kanıt koduna yayılmış durumda. CandleStore kaynakla anahtarlanıyor; application kayıtları da kaynak bağlamı taşıyor veya bağlamın genişletilmesini gerektiriyor. Fiyat alarmları çizim geometrisi kopyası içerebiliyor. P4–P7 revision bağlı izole replay hattı canlı emir hattı değil. HTTP komut kuyruğu yalnız runtime.inspect kabul ediyor.

## Uygulama paketleri

| Paket | Bağımlılık | Teslim | Kabul kapısı |
|---|---|---|---|
| D0 | — | Kaynak envanteri, test/depo yedekleri, demo endpoint ön kontrolü | Mevcut kayıtlar değişmeden korunur; desteklenen demo REST/WS yolları somut kanıtlı |
| D1 | D0 | Demo piyasa adaptörü ve tutarlı kaynak kimliği | İlk açılış, geçmiş, canlı mum, semboller ve üst-zaman yalnız demodan |
| D2 | D1 | Depo/çizim/alarm/binding ayrımı ve geçiş aracı | Gerçek geçmiş veya aktif kural demo bağlamına sızmaz; tekrar çalıştırma güvenli |
| D3 | D2 | Demo veri ve grafik kabulü | Kesinti/restart/kaynak karışması negatif kontrolleri ve gerçek demo public probe geçer |
| B1 | D3 | Ortak canlı kural sözleşmesi ve gölge işçi | Tarayıcı kapalıyken gözlem; kalıcı tekil olay; dış emir yok |
| B2 | B1 | Fırsat → plan v2 önizlemesi ve inceleme paneli | Aynı olay tek plan; revizyon/süre/veri değişikliği onayı geçersizleştirir |
| B3 | B2 | Onaylı SINGLE demo emir bağlantısı | Tek giriş, gerçek fill ve borsadan doğrulanmış koruma/çıkış görünür |
| B4 | B3 | Kesinti kabulü, raporlama ve grid genişletme | Kurtarma ve ortak risk kanıtı; grid ayrı kabul; gerçek ortam kapalı |

Her paket NOT_STARTED durumunda başlar. Sonuç raporu olmadan tamamlandı işaretlenmez. Süre tahmini D0/D1 bulgularından sonra yapılır.

## D0 — envanter ve geri dönüş

İlgili alanlar: market_data.py, market_feed.py, chart_market.py, application/settings.py, chart_evidence.py, drawings/{contracts,service,calculations}.py, higher_timeframe.py, chart_bindings.py, binding_eligibility.py, price_alerts.py, alert_{intrabar,timeframes}.py; frontend types/evidence/bindings/higherContextModel ve etkilenen fixturelar.

Mevcut uygulama, market ve execution depoları SQLite uyumlu yedeklenir; WAL varken ham dosya kopyası yeterli sayılmaz. Çalışan eski sunucu/işçiler envantere alınır; aktif demo pozisyon varsa koruma yönetimini kesen geçiş yapılmaz. Kullanıcı sırları rapora yazılmaz. Kaynak aday ve geri dönüş adımları sabitlenir.

Demo REST kökü https://demo-fapi.binance.com; WS kökü wss://demo-fstream.binance.com resmî belgede belirtilir. Kline için tam WS yolu uygulama öncesi güncel resmî stream belgesi ve gerçek el sıkışma/veri probe ile doğrulanır; yalnız host değiştirerek çalışıyor kabul edilmez. time/exchangeInfo/klines/premiumIndex ayrı okunur probe ile kontrol edilir. Desteklenmeyen sembol/interval gerçek kaynaktan tamamlanmaz.

## D1 — bütün veri hattını demo yap

Tek, değişmez ve izin listeli demo piyasa bağlamı oluşturulur. Serbest URL/env üzerinden başka host kabul edilmez. REST istemcisi salt okunur kalır; redirect engeli sürer. WS, REST catchup ve sembol hassasiyetleri aynı bağlamı kullanır. Kaynak kimliği ve şema sürümü backend/frontend için birlikte tanımlanır; önerilen kimlik binance_usdm_demo_trade_price / demo_public, uygulama sözleşmesinde kesinleştirilir.

Sadece string replace yapılmaz: kaynak doğrulayıcıları, hash girdileri, event kimlikleri, geometri şeması ve clock/evidence sözleşmeleri sürümlenir. MarketFeedHub/cache anahtarlarında ortam yer alır veya demo için fiziksel izolasyon kanıtlanır. Eski ve yeni çalışan feed karışmaz. Ortam alanı olmayan işlem üretebilecek kayıtlar varsayılan demo kabul edilmez.

Üst barda Binance Demo · USD-M ve veri fiyat türü görünür. LIVE/Canlı etiketi akış tazeliğini anlatır; gerçek para ortamı anlamına gelmez. Kaynak verisi eksikse gösterge unavailable/warmup olur; uydurma geçmiş veya sıfır değer yok.

## D2 — kayıt geçişi

Demo için ayrı piyasa deposu varsayılanı; eski chart-market.sqlite3 korunur. Demo çalışma alanı ayrılır. Kaynak kimliği ve kayıt sürümü eski gerçek public çizim/alarm/binding/workspace ile çakışmaz. Uygulama deposu migration ile ayrıştırılır veya demo için ayrı depo açılır; seçim D0 envanterine dayanır. Execution deposu taşınmaz/sıfırlanmaz.

Eski çizimler otomatik demo çizimine dönüştürülmez. İsteğe bağlı kopyalama yeni kimlik ve provenance üretir; anchored VWAP/Fib/trend bağlamı yeniden doğrulanır. Kopyalanan kurallar/alarm/binding pasif olur; eski onay ve checkpoint taşınmaz. Eski hesap oturumlarının koruma/çıkışları korunur. Daha sonra geçiş aracını tekrar çalıştırmak çift nesne üretmez. Rollback yeni kayıtları eski sunucuda sessizce yorumlatmaz.

P4–P7 eski rapor/fixtureları değiştirilip yeni kabul gibi sunulmaz; demo sözleşmesiyle etkilenen kanıtlar yeniden üretilir. Kaynak hash'i değişen rapor BLOCKED olmalıdır; testleri yeşil yapmak için bu koruma kaldırılmaz.

## D3 — veri kabul matrisi

- Ağ kaydı: normal demo kullanımında gerçek fapi/fstream hostlarına sıfır istek; hesap/emir/dış mesaj mutasyonu sıfır.
- REST ile WS mum eşleşmesi, kapalı mum tekilliği, exact OHLC/hacim ve tick/lot doğruluğu.
- BTC/ETH veya demo tarafından doğrulanan iki sembol; 1m, 5m, 1h, 1d ve desteklenen üst-zaman hizası. Desteklenmeyen seçim açıkça engellenir.
- Reconnect/catchup/dedup, eski heartbeat, sırası bozuk olay, clock jump, boş/eksik geçmiş ve demo kesintisi.
- Gerçek ortam etiketli payload enjekte edildiğinde frontend ve backend reddeder; eski cache ve çizimden sinyal çıkmaz.
- Gerçek demo public akışında en az 30 dakika ve iki kapalı 1m geçişi; ayrı restore/restart kontrolü. Kontrollü kesinti ile gerçek upstream gözlemi ayrı raporlanır.
- Etkilenen Python/frontend testleri, derleme; kaynak sözleşmesi geniş değiştiği için paket sonunda tam regresyon. Mevcut fiziksel kabul açıkları korunur.

## B1 — canlı takip, emir yetkisi yok

Tek kanonik kural/olay sözleşmesi tanımlanır; alarm ve revision bağlı replay motorunun paylaşacağı hesap ve farklı profiller açık olur. İlk canlı kapsam kapalı mum yatay seviye/çizgi: temas, yaklaşma, kapanış kırılımı. Eşitlik/tolerans/yön/rearm/TTL sürümlüdür. Intrabar bildirim doğrudan işlem tetiklemez.

Backend işçisi tarayıcıdan bağımsız, tek sahipli, sağlığı ölçülen ve kalıcı checkpointli çalışır. Event/intent/checkpoint atomik kaydedilir; restart/reconnect geçmiş olayı yeni fırsat yapmaz. Çizime bağlı kural revizyon değişiminde durur; sabit kopya seçeneği ayrı etiketlenir. Gölge olaylar emir API'sine erişemez.

## B2 — plan önizlemesi

Olay → açıklanabilir fırsat → katı plan v2. Miktar, nominal, teminat, stop riski, masraf rezervi, hedefler ve geçerlilik görünür. Olay/çizim/kural/veri/hesap ortam zinciri üstveride kayıtlıdır; katı şemaya sessiz alan eklenmez. Tek semantik olaydan tek plan, tekrar çağrıda aynı sonuç. Süre sonu/revizyon değişimi yeni girişi engeller; açık pozisyon yönetimini bozmaz.

LAST_PRICE sinyalinden MARK_PRICE stopuna geçiş açık gösterilir. Demo LAST–MARK ve plan referans drift kontrolleri ayrı yapılır. Gerçek public fiyat bu sürümün karar girdisi olmaz.

## B3 — yetkili SINGLE demo

İlk kapsam tek sembol/tek oturum, mevcut risk profili, mevcut hesap moduyla uyumlu SINGLE; otomatik kaldıraç/teminat değişimi yok. Onay kullanıcı/hesap/ortam/plan digest/sürüm/süre/tek girişe bağlıdır. Mevcut salt okunur W1 kuyruğuna finansal action eklemek tek başına yeterli değildir: teslim/uzlaştırma modeli ve kimlik doğrulama ayrıca uygulanır.

Mevcut V2Runner, kalıcı niyet, execution_lock ve rezervasyon kullanılır. UI kabul/kuyruk/borsa kabulü/fill/koruma doğrulandı durumlarını ayırır. Stop taşıma beklerken eski doğrulanmış stop gösterilir. Yeni girişleri durdur, kuralı durdur ve pozisyonu kapat ayrı komutlardır. Sırlar frontend'e verilmez.

## B4 — dayanıklılık ve genişletme

Somut demo test planları mevcut yetkilendirme modelinden geçer. LONG/SHORT, stop/TP gerçek tetiklenmesi, kısmi fill/iptal yarışı, kayıp POST yanıtı, süreç çökmesi, ağ kesintisi, manuel emir ve iptal edilen koruma denenir. Senaryoya erişilemeyen demo davranışları NOT_OBSERVED kalır; offline enjeksiyon ayrı kanıttır. Artakalan pozisyon/emir/UNKNOWN niyet yok veya açıkça engelli durum vardır. Kör tekrar ve çift giriş sıfır olmalı.

Masraf rezervi ile gerçek komisyon/funding ayrı raporlanır. API key hash'i ve hesap kimliği ayrımı mevcut oturumları bozmayan migration ile ele alınır. Önce SINGLE kabulü; ardından yönlü grid, neutral ve çoklu oturum ayrı risk ve durdurma testleriyle açılır. Uzun gölge/demo gözleminde en az 24 saatlik worker/stream yenileme ve restart raporu hedeflenir; hata sayıları ve süreler kaydedilir, sadece test adedi başarı ölçütü olmaz.

## Gerçek ortama geçiş — bu planın dışında

Gerçek API anahtarı, gerçek hesap okuma/yazma ve ortam seçimi açılmaz. İleride ayrı plan: hedef hesap yetenek/filtre/komisyon doğrulaması, ayrı depolar ve yetkiler, önce salt okunur kabul, sonra kullanıcı ayrıca yetkilendirirse sınırlı gerçek işlem. Demo kabulü gerçek likidite, kayma veya kârlılığı kanıtlamaz.

## İlk uygulanacak iş

D0 → D1 → D2 → D3. Bu dört kapı kapanmadan grafik kaynaklı demo emir bağlantısı açılmaz. Sonraki adım B1 gölge izleme. Her teslim raporu kaynak sürümü, testler, gerçek ağ gözlemleri, veri/hesap etkileri ve kalan açıkları belirtir.

## Kaynak

- [Resmî USD-M genel bilgiler ve demo adresleri](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info)
- [Demo/gerçek ortam araştırması](25-BINANCE-DEMO-VE-GERCEK-ORTAM-GECIS-ARASTIRMASI.md)
- [Grafik planı](docs/chart/PLAN.md)
- [Mimari sözleşme](03-MIMARI-VE-ISLEM-SOZLESMESI.md)
