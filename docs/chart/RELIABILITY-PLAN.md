# Grafik verisi güvenilirlik uygulama planı — CL05

13 Kasım 2026 güncellemesi: [P7 izole yürütme tamamlandı](P7-ISOLATED-REPLAY-DELIVERY.md);36/36 senaryo ve20 tür/48 sorgu kontrolü geçti. Canlı entegrasyon kapalı; QA01/B5/fiziksel kabul açık. Aşağıdaki 10 Kasım taslağı tarihsel plan olarak korunur; güncel yürütme raporu ve açık DR01 amendment teslim belgesindedir.

**Güncel sıralama:** [Çekirdek plan v2](PLAN.md) geçerlidir. P1 tamamlandı; önce T01/T02, sonra P2/P3. Bu belgedeki “sıradaki P2” ifadeleri önceki sıra kaydıdır. P2–P7 teknik bitiş koşulları yeni araç kapsamıyla korunur.

10 Kasım 2026. Bu belge uygulanacak işleri sıralar; adaptör veya bot uygulanmadı. Fiziksel CL04/B5 ertelenmiş ve ana plan 24/25 durumundadır. Grafik geliştirme önceliği korunur. Bu plan botun grafiği okuyabilmesi için backend verisinin hangi kanıtları sağlaması gerektiğini somutlaştırır.

## Kaynak incelemesinin sonucu

`chart_market.py` borsa OHLC/hacim metinlerini float yapıyor. `market_feed.py` generation/sequence ve 1000 elemanlı bellek içi closed_keys kullanıyor; bunlar kalıcı olay kimliği değildir. Feed saati duvar saatine bağlı; `freshness.ts` Date.now–received_at farkına bakıyor ve gelecekteki damgayı tek başına reddetmiyor. Bugünkü LIVE, bot için saat/kesinlik güvencesi sağlamaz. DrawingService revision ve BEGIN IMMEDIATE koruması sunuyor; gelecekteki binding/event transaction buna uyumlu tasarlanmalı.

Veri yolu: borsanın kesin metni → doğrulanmış backend snapshot → saat/kalite/epoch kanıtı → kaydedilmiş revision bağı → saf uygunluk kapısı → kalıcı yerel olay. Grafik bu verinin görsel tüketicisidir; bot DOM/piksel veya UI seçimine bağlanmaz.

## Uygulama sırası

### P1 — Kesin piyasa fiyatı ve provenans

Bağımlılık: yok.

Borsa metninden Decimal doğrulanan, üssüz OHLC/hacim ve tick_size DTO; grafik float görünümü ayrı türetilir. Float üzerinden kesin fiyat geri üretilmez. Eski cache provenansı yoksa yeniden edinilir veya engellenir.

Bitiş koşulları:

- DR24: float-only girdi PRICE_PRECISION_UNPROVEN
- Negatif/NaN/sonsuz ve OHLC tutarsızlığı reddedilir
- Tick dışı anchor sessiz yuvarlanmaz; ondalık metin round-trip kayıpsız

### P2 — Saat, upstream yaş ve uzun kesinti

Bağımlılık: P1.

Enjekte edilebilir monotonic/wall clock; upstream event zamanı ve server-time ölçüm aralığından offset/belirsizlik kanıtı. Consumer ve producer monotonic değerleri süreçler arasında doğrudan çıkarılmaz. Heartbeat taşıma yaşını güncelleyebilir, veri yaşını güncelleyemez. 10sn/10sn taslak eşikler ayrı sürümlü politika; belirsizlik limiti koddan önce açıkça seçilir.

Bitiş koşulları:

- DR21/DR22: eski upstream+taze heartbeat engellenir
- İleri/geri wall-clock sıçraması, gelecek timestamp ve eksik saat kanıtı engellenir
- Uzun kesinti/catchup geçmiş close için olay üretmez; taze snapshot ve kanıtla yeniden uygunluk

### P3 — Stream epoch ve değişmez veri kanıtı

Bağımlılık: P1, P2.

Her stream ömrüne yeni epoch; process restart/yeniden edinmede snapshot bariyeri. Immutable snapshot hash, quality, warmup, bar grid ve continuity kanıtı. Sequence atlaması tek başına gap değildir.

Bitiş koşulları:

- DR15/DR17/DR18/DR19/DR23/DR29
- Eski epoch ve tekrar paket state veya olay değiştirmez
- Reconnect snapshot geçmiş kapanışı canlı fırsata dönüştürmez

### P4 — Kalıcı ve varsayılan kapalı çizim bağı

Bağımlılık: P3.

Ayrı binding şeması: owner/workspace/drawing revision, binding/rule version, tam market kimliği, interval, zaman penceresi ve geometry/grid hash. Mevcut strict çizim CRUD alanları değiştirilmez. UI sembol değişimi bağı değiştirmez. Trend yalnız doğrulanmış loaded-bar logical segment üzerinde; eksik grid veya segment dışı extrapolation yok.

Bitiş koşulları:

- DR12/DR13/DR14/DR20/DR25/DR26/DR27
- Düzenleme/silme/undo eski bağı durdurur; açık rebind gerekir
- Boşluklu gridde grafik/Decimal hesap eşleşir; label talimat olarak yorumlanmaz

### P5 — Saf uygunluk kapısı ve nedenli engelleme

Bağımlılık: P4.

Yan etkisiz karar fonksiyonu yalnız BLOCKED, OBSERVE_ONLY veya EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY üretir. Kanıt alanı yoksa güvenli varsayılanla doldurmaz. Bugünkü LIVE tek başına uygunluk değildir. Açık mum varsayılan OBSERVE_ONLY.

Bitiş koşulları:

- DR01/DR09/DR11/DR28
- Her gerekli kanıt tek tek çıkarıldığında olay yok ve doğru engel nedeni var
- Uygunluk emir veya hesap yetkisi vermez

### P6 — Kalıcı semantik olay ve yerel intent

Bağımlılık: P5.

İzole test DB migration taslağı; event semantic key unique. Head revision aynı uygulama DB transaction içinde yeniden okunur; event+local intent birlikte commit edilir. Piyasa DB snapshotı donmuş kanıt olarak taşınır, çapraz DB atomiklik iddiası yapılmaz. Request_id semantik olay anahtarı değildir. Replay namespace ayrıdır.

Bitiş koşulları:

- DR16/DR17/DR25/DR30/DR31/DR34/DR35
- İki worker yarışı, commit öncesi/sonrası crash, restart ve tekrar köprüde tek kalıcı event/intent
- Yalnız sahte sink; gerçek kanal yok; DELIVERY_UNKNOWN exactly-once sayılmaz

### P7 — İzole kuru çalışma ve entegrasyon kararı

Bağımlılık: P6.

36 E4 senaryosu gerçek izole motorda fake-clock/sahte sink ile yürütülür; expected/gözlenen ve yan etki sayaçları kaydedilir. Runtime bağlama, sürekli worker ve gerçek kanal ayrı karar gerektirir.

Bitiş koşulları:

- DR01–DR36 gerçekten çalıştırılır; statik kontrol PASS yerine geçmez
- Order/account/external message/execution DB mutation sayaçları sıfır
- B5/fiziksel destek açıkları ve R05 sonucu kullanıcı incelemesine sunulur; otomatik genel kabul verilmez

## Uygulama ve kabul sınırı

İlk kod işi P1 kesin fiyat taşımasıdır; P2 saat/uzun kesinti R05 açığını ele alır. Her paket yalnız kendi testleriyle kapanır; P1 geçmesi tüm hattı hazır yapmaz. Mevcut görsel sayı alanlarını kırmamak için kesin adapter DTO ayrı sürümlenir; sessiz API tipi değişimi yapılmaz. Yeni kaynak değişiklikleri mevcut aday 02 arşivini değiştirmez, gerekli doğrulama sonrası yeni aday çıkarılır.

P1–P6 gelecekte izole uygulanabilir; bu belge bunları uygulanmış saymaz. P7 entegrasyon kararı fiziksel kabulün yerini alamaz. Gerçek bildirim, hesap/emir, mevcut demo yürütme çekirdeğine bağlantı veya sürekli worker bu planlama adımının kapsamı değildir. Ana plan sayısına yeni CL/P işleri eklenmez.

[Makine okunur plan](contracts/chart-reliability-plan-v1.json) · [Veri sözleşmesi](BOT-DATA-CONTRACT.md) · [36 kuru çalışma senaryosu](DRY-RUN-PLAN.md) · [Kabul açıkları](ACCEPTANCE.md)


## P1 güncellemesi

P1 kesin ondalık taşıması uygulandı ve doğrulandı: [ayrıntı](EXACT-DATA.md). Yukarıdaki paketler uygulama sırasıdır; P2–P7 henüz uygulanmadı. Sıradaki iş P2. Bot adaptörü, worker veya entegrasyon yok; B5 açık.


## P2 uygulama güncellemesi — 10 Kasım 2026

P2 tamamlandı: enjekte edilebilir wall/monotonic saat, upstream saat ölçümü ve belirsizlik, heartbeat yaş koruması ve uzun kesinti snapshot bariyeri uygulandı. 718 Python / 143 frontend testi, 9 üretim App kontrolü ve gerçek public saat kanıtı geçti. Önceki Date.now-only/sıradaki P2 açıklamaları tarihsel durumdur. [Güncel kapsam ve sınırlar](CLOCK-RELIABILITY.md). Sırada P3; epoch/immutable kalite kanıtı ve bot motoru henüz uygulanmadı. B5/fiziksel ve gerçek uzun borsa kesintisi kabulü değişmedi.


## P3 uygulama güncellemesi — 10 Kasım 2026

P3 tamamlandı: producer epoch, consumer snapshot/callback bariyeri, immutable snapshot/grid hash ve açık warmup kanıtı uygulandı. 729 Python / 153 frontend testi, kontrollü App reconnect ve iki gerçek public abonelik snapshot kontrolü geçti. Önceki epoch/immutable kanıtın henüz bulunmadığını söyleyen bölümler tarihsel durumdur. [Güncel kapsam](STREAM-EVIDENCE.md). Sıradaki T03; P4–P7, canlı bot, genel/cihaz kabulü ve gerçek uzun borsa kesintisi kanıtı tamamlanmadı.

## 11 Kasım — canlı referans araştırması eki

Tarihsel uygulama sırası üstte korunur; güncel durum PLAN.md/makine planında P2 ve P3 tamamlanmış kaydıdır. [Canlı araştırma](REA-LIFECYCLE-MARKET-POINTER.md) bunu yeniden ürün testi diye doğrulamaz. Market open/offline etiketi freshness kanıtı değildir;25sn ağ emülasyonu residual WebSocket traffic içerdi. Full blackout/stale/catchup/dedup runtime kabulü açık. Aynı kapalı1m satırlar timestamp ile31/30 karşılaştırmada sabitti, ham exchange closed flag edinilmedi. Spot/mark/last kimliği ve missing-volume unavailable nedeni kalite/uygunluk kapısıyla taşınmalı. Eski görevlerin durumunu sessizce değiştirmeden, REA04te gereken yeni kabul ve genişletmeler eklenmeli.
