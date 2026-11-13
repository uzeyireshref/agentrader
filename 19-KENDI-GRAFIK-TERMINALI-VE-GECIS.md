# Kendi grafik terminali — Karar ve teknik geçiş

Tarih: 9 Kasım 2026 · Karar: kabul edildi · Uygulama: W1 yerel temeli ardından W2/W3 grafik/veri/çizim kodu eklendi; görsel kabul bekliyor. [Güncel durum](21-GRAFIK-VE-KALICI-CIZIMLER.md). [W1 teslimi](20-W1-YEREL-UYGULAMA-API.md).

## Karar ve gerekçe

Kullanıcı çizim başına Pine Script veya harici alarm kurulumuyla uğraşmak istemiyor. Kendi grafiğimizde çizimler veri olarak bize ait olacak; bot aynı geometrileri ve sürümleri doğrudan kullanacak. Web terminali önce geliştirilecek, uygun olduğunda aynı sistem uygulama olarak paketlenecek.

TradingView hesabı, Pine ve alarm/webhook zinciri kaldırılan ana bağımlılıklardır. Grafik kütüphanesi kullanmak mümkündür: Lightweight Charts gibi bir aday yalnız çizim/render altyapısı sağlar; düzenleyici, kalıcı çizimler, strateji ve bot bağlantısı tarafımızdan geliştirilir. Aday seçimi W2'de etkileşim prototipi ve seçilen sürümün lisans/atıf kontrolüyle kesinleşir.

## Mimari görünüm

~~~mermaid
flowchart TD
    UI[Kendi web terminalimiz] --> API[Uygulama API ve komut kabulü]
    API --> DRAW[Sürümlü çizim ve kural deposu]
    FEED[Binance public piyasa verisi] --> DATA[Ortak piyasa veri hattı]
    DATA --> UI
    DATA --> STRAT[Strateji motoru]
    DRAW --> STRAT
    DATA --> SCAN[Bağımsız tarayıcı]
    SCAN --> STRAT
    STRAT --> OPP[Olay ve fırsat kaydı]
    OPP --> PLAN[Somut plan ve tahsis]
    PLAN --> AUTH[Yetki ve bağımsız risk]
    TG[Telegram] --> API
    API --> AUTH
    AUTH --> EXEC[Tek yazıcı mevcut yürütme çekirdeği]
    EXEC --> DEMO[Binance demo]
    DEMO --> REC[Hesap ve emir uzlaştırması]
    REC --> EXEC
    OPP --> OUT[Kalıcı bildirim kuyruğu]
    REC --> OUT
    OUT --> TG
~~~

Bu diyagram hedef mimaridir. API ve uygulama sınırının W1 salt okunur temeli uygulandı. UI, public canlı veri hattı ve çizim deposu W2/W3 kapsamında uygulandı; görsel kabul bekliyor. Strateji, tarayıcı ve tahsis henüz uygulanmadı. Mevcut hesap kullanıcı akışı public piyasa verisinin yerine geçmez.

## Mevcut koddan hedefe geçiş

| Mevcut parça | Yeni sistemde kullanım | Geçiş işi |
|---|---|---|
| market_data.py / market_cli.py | Public geçmiş ve mum deposu | API sorgu sınırı, ortak canlı piyasa hattı ve kalite olayları |
| analysis.py | Sayısal özellikler | Stratejiden ayrılmış, sürümlü özellik girdileri; grafik gösterimi |
| plans.py / plan_v2.py | Somut plan ve yerel yetki | Yeni kaynak bağları için yan tablo; uzaktan komut adaptörü |
| v2_preflight.py / portfolio.py / reservations.py | Ortak risk ve kapasite | Tahsis önerileri aynı bağımsız kontrolden geçer |
| v2_runner.py / grid_runner.py / neutral_runner.py | Yetkili plan yürütme | Tek yazıcı uygulama komutlarından çağrılır; topluca yeniden yazılmaz |
| watchdog.py / plan_execution.py | Mevcut v1 oturumları | Geçişte korunur; yeni oturumlar uygun runner'a açık yönlendirilir |
| account_runtime.py / runtime.py / service_cli.py | Oturum izleme | Genel piyasa/strateji yaşam döngüsünden sorumluluğu ayrılır |
| user_stream.py / order_journal.py | Özel hesap olayları | REST uzlaştırma bariyeri korunur |
| notifications.py | Kalıcı bildirim ve Telegram gönderimi | Fırsat bildirimleri ve ayrı gelen onay adaptörü |
| state.py / locking.py / transport.py | Kalıcı kayıt, kilit, dayanıklılık | Sürümlü geçişler ve tek yürütücü garantisi |

## Önerilen kaynak düzeni

Aşağıdaki düzen hedefi gösterir. W1'de application, api ve migrations paketleri uygulandı; kalan alanlar planlıdır. W2/W3 kaynak ve kanıt ayrıntıları 21 numaralı belgede günceldir.

~~~text
frontend/                      React terminali ve grafik/çizim araçları (W2/W3 kodlandı)
agentrader/application/        Salt okunur sorgu/komut/işçi temeli (W1 uygulandı)
agentrader/api/                Yerel FastAPI; istemci olay hattı sonraki paketlerde
agentrader/drawings/           Geometri, revizyon, depo (W3 HTTP doğrulandı)
agentrader/strategies/         Kurallar, durum makineleri, geçmiş oynatma (planlandı)
agentrader/opportunities/      Olay, kanıt, fırsat ve plan bağlantısı (planlandı)
agentrader/scanner/            Seçili evrende strateji çalıştırma (planlandı)
agentrader/allocation/         Tahsis politikaları ve yönetim yetkisi (planlandı)
agentrader/migrations/         Ayrı uygulama deposunda sürümlü geçişler (W1 uygulandı)
agentrader/*.py                Mevcut yürütme/veri/CLI modülleri (korunur)
~~~

Yeni paketler eski modülleri adaptörle kullanır. Mevcut import/CLI girişleri taşınmadan önce davranış ve oturum uyumluluğu kanıtlanır. Mikroservis, Redis veya PostgreSQL ilk teslimin şartı değildir; SQLite ile başlayıp ölçüme göre karar verilir.

## W1 API ve komut sözleşmesi taslağı

Bu tablo hedef API sözleşmesidir. W1'de /api/health, /api/capabilities, /api/status ve yalnız runtime.inspect için /api/commands uygulandı. W2'de /api/markets, /api/candles ve /api/market-stream; W3'te sürümlü çizim/workspace metadatası ve yerel browser session uçları uygulandı. Strateji/fırsat ve işlem onayı sonraki paketlerdir; aşağıdaki tüm hedef uçlar kullanılabilir sayılmaz.

| İşlem | Kaynak örneği | Etki |
|---|---|---|
| Sağlık/veri durumu | GET /api/health | Anahtarsız sağlık ve gecikme |
| Desteklenen ürün/sembol | GET /api/markets | Borsa meta verisi ve yetenek |
| Mum geçmişi | GET /api/candles | Kaynak/sembol/aralık/kesim zamanı |
| Çizimler | GET/POST /api/workspaces/{id}/drawings | Sahiplik ve şema doğrulaması |
| Çizim güncelleme/silme | PATCH/DELETE /api/drawings/{id} | Beklenen revision; eski sürümde çakışma |
| Takip kuralı | POST /api/strategy-instances | Ayrı oluşturma ve etkinleştirme |
| Olay/fırsat | GET /api/opportunities | Kanıt, geçerlilik ve engel nedeni |
| Kullanıcı komutu | POST /api/commands | Benzersiz request_id, kullanıcı, hedef sürüm, eylem |
| Komut sonucu | GET /api/commands/{id} | Kabul, bekleme, uygulama veya hata |
| İstemci güncellemeleri | Sunucudan olay kanalı | Fiyat/veri/kayıt/fırsat/komut durumu |

Aynı request_id ve aynı içerik aynı sonucu döndürür; farklı içerik reddedilir. Kalıcı kabul ile yürütme ayrılır. İşlem öncesi kritik kontroller yürütücüde tekrar yapılır; API onayı geçerli riskin yerine geçmez. Hesap ayrıntıları, çizim ve kural yazmaları kimlik/nesne sahipliği gerektirir. Yerel kullanıcı kimliği uzaktan doğrulanmış Telegram kimliği sayılmaz.

## Çizim ve kural kayıt taslağı

Çizim: drawing_id, revision, workspace_id, owner_id, environment/source, exchange, product, symbol, price_source, type, anchors, style, visible_timeframes, created_at, updated_at, deleted_at. Fiyatlar ondalık metindir; zamanlar açık UTC değerleridir. visible_timeframes gösterim tercihidir; stratejinin değerlendirme zaman dilimi ayrı alanıdır.

Kural: instance_id, strategy_type, strategy_version, revision, drawing_id/drawing_revision veya otomatik seviye referansı, sembol/fiyat kaynağı, değerlendirme zaman dilimi, parametreler, notification_only/opportunity davranışı, expires_at, cooldown ve rearm politikası. Etkinleştirme açık komuttur. Canlı durumda geometri sessizce değiştirilemez.

Durum/checkpoint: instance_id + kural/çizim sürümü, durum adı, son işlenen olay kimliği/zamanı, temas/tepki ölçümleri, son bildirim ve veri bariyeri. Tekrar/restart aynı olaydan ikinci fırsat üretmez.

Plan kökeni yan tablosu: plan_id/version → opportunity_id → event_id → strategy_instance/revision → drawing_id/revision (varsa). Onay ve emir mevcut plan/intent kimlikleriyle ilişkilidir. Mevcut katı plan şemasına doğrulanmamış alan eklenmez.

## Çizim değişikliğinin yaşam döngüsü

Taslak çizim kaydedilebilir; takip ancak bağlı kural etkinleştirilince başlar. Düzenleme yeni revizyon oluşturur ve eski revizyona bağlı izlemeyi durdurur. Henüz yürütülmemiş fırsat/onayların geçersizliği komut yürütücüsünde de denetlenir. Açık oturumun değişmez planı ve koruması korunur. Kullanıcı yeni revizyonun özetini görerek takip bağını yeniden etkinleştirir. Silme tombstone ile geçmiş kanıtı korur; yeni tetik üretmez.

## Dayanıklılık ve veri doğruluğu

- Son fiyat/mark/kapanış seçimi çizimde ve kuralda görünür; farklı fiyatlar sessizce karşılaştırılmaz.
- Veri hattı ortak abonelikleri kullanır; her grafik ve strateji ayrı REST döngüsü açmaz.
- Reconnect sırasında strateji PAUSED_DATA durumuna geçer. Eksik mumlar tamamlanıp zaman/kalite kontrolünden geçince devam eder. Kaçan anlık temas sonradan kesin bilinmiyorsa UNKNOWN_GAP olarak kaydedilir.
- Çizim kaydında beklenen revizyon denetlenir. Başka cihazın değişikliği ezilmez; kayıt başarısızlığı görünürdür.
- API yeniden başlatması ikinci izleyici oluşturmaz. Tarayıcı kapansa da çalışan backend izler; sunucu kapalıysa bot izlemiyor olarak gösterilir.
- Uygulama çevrimdışı önbelleği canlı veri veya geçerli işlem onayı olarak kullanılmaz. Yetki gerektiren komutlar yeniden bağlantıda sessizce gönderilmez.

## Kapsam ve geçiş stratejisi

1. Salt okunur API ve gerçek piyasa grafiği.
2. Kalıcı yatay çizgi/bölge ve yaklaşma/temas; olay/bildirim.
3. Trend/Fibonacci ve durum hafızalı kurallar; geçmiş oynatma.
4. Somut plan ve kimliği doğrulanmış onay; mevcut demo yürütücüye bağlantı.
5. Bağımsız tarayıcı, tahsis ve ayrı otomatik yönetim yetkisi.

Her adım mevcut CLI ile birlikte çalışır. İşlem tabloları/veritabanları temizlenmez; risk limiti yükseltilmez; geçmiş test raporu yeni doğrulama gibi tarihlenmez. Uygulama kodu değişikliklerinde ilgili regresyonlar çalıştırılır. Geri dönüşte eski CLI'nin okuyabildiği kayıtlar korunur; yeni stratejiler durdurulup mevcut pozisyon korumaları yönetilmeye devam eder.

## Teknoloji ve kaynak durumu

React/TypeScript + Lightweight Charts frontend, Python API ve SQLite başlangıç adaylarıdır. W1'de Python API için FastAPI/Uvicorn isteğe bağlı web bağımlılığı olarak seçildi. Frontend ve grafik seçimi W2'de prototiple doğrulanacak. Çizim araçları ve kalıcılık kendi geliştirme kapsamımızdır.

- [Lightweight Charts eklenti modeli](https://tradingview.github.io/lightweight-charts/docs/plugins/intro): özel çizim ve görselleştirme için teknik başlangıç; son uygulama öncesi sürüm/lisans doğrulanır.
- [Telegram Bot API](https://core.telegram.org/bots/api): bildirim ve gelen onay adaptörü için referans.
- [Binance geliştirici belgeleri](https://developers.binance.com/): ürün, ortam ve akış seçimi uygulama sırasında güncel belgelerden doğrulanır.

## Tamamlanma ve kanıt

W0 tasarım ve W1 yerel API temeli tamamlandı. [W1 kanıtı](reports/web-foundation-validation-20261109.json) 631 test ve izole gerçek HTTP/restart kontrolünü içerir. Terminal ve çizim deposu kodlandı; veri/API/kalıcılık doğrulandı, görsel kabul bekliyor. Strateji motoru, tarayıcı ve yönetim yetkisi bayrakları false kalır. Ayrıntılı sıra [02](02-ASAMALI-GELISTIRME-PLANI.md), mimari değişmezler [03](03-MIMARI-VE-ISLEM-SOZLESMESI.md), kullanıcı kabulü [04](04-KULLANICI-BEKLENTILERI-VE-YAPILABILIRLIK-TASLAGI.md) içindedir.
