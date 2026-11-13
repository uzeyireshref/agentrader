# P7 — İzole replay, 36 senaryo ve entegrasyon kararı

13 Kasım 2026. P7 tamamlandı. 36 E4 senaryosu gerçek uygulama hesap/uygunluk/kayıt koduyla, geçici SQLite deposu, fake clock ve sabit sahte alıcı kullanılarak yürütüldü. Ek olarak 20 registry türünün 48 sorgusu sınandı. Grafik **Paneller → Kuru çalışma sonuçları** üzerinden kaynak sürümü doğrulanmış raporu, beklenen/gözlenen karşılaştırmasını ve kalan kabul kapılarını gösterir.

**Karar: canlı entegrasyon kapalı kalır.** İzole motor kabulü genel ürün kabulü değildir. Son plan işi QA01’dir; B5/fiziksel trackpad/touch/DPR/ekran okuyucu kabulü ve gerçek upstream kesintisi kanıtı otomatik kapanmadı. Kullanıcı incelemesi için bu sınırlar burada ve rapor ekranında görünürdür. Sürekli worker, gerçek kanal, broker/emir/account adapter’ı bağlanmadı.

## Eklenen davranışlar ve yararları

### Sürümlü episode replay profili

CLOSED_EPISODE_REPLAY/1, P6’nın CLOSED_EXPLICIT_REARM/1 profilinden ayrıdır. Mevcut kullanıcı binding’lerinin EXPLICIT politikası değişmez. Yeni profil yalnız internal, açık replay çağrılarıyla çalışır; HTTP üzerinden çalıştırma/aktivasyon endpoint’i yoktur.

Sentetik L100/tick0.1 örneğinde yaklaşma1.0, temas0.1 ve ayrılma2.0’dır; gerçek strateji önerisi değildir. FROM_BELOW/FROM_ABOVE simetriktir. Yaklaşma bandına giriş exact rational hesapla değerlendirilir. Mumun OHLC aralığı temas bandını kesiyorsa TOUCH yaklaşmaya önceliklidir. Süren temas yeni olay üretmez. İki ayrı uygun kapalı mumdan sonra tüm fiyat aralığı yeterince ayrılmışsa phase ARMED olur; yeniden kuran mum olay üretmez, yalnız sonraki mum yeni episode açabilir. Bu, sürekli temasta bildirim yağmasını ve cooldown sırasında yapay olayları engeller.

CLOSE_CONFIRMED_W5 ayrı profile mode’dur; üst/alt temas bandına eşit kapanış kırılım sayılmaz, kesin aşım gerekir. OHLC içi kırılım/retest veya stop/hedef sırası uydurulmaz; INTRABAR_ORDER_UNKNOWN döner. Açık mum eski kapanışı tekrar değerlendirmez.

### Kalıcı checkpoint ve gözlem izi

Migration 8 replay checkpoint/gözlem/policy tablolarını ve ek sahte teslim durumlarını ekler; v1–v7 migration checksum’ları korunur. Event+intent+checkpoint+observation aynı uygulama DB transaction’ında yazılır. Binding/target head’i commit içinde tekrar okunur. Farklı profile hash, binding revision ve replay namespace ayrı state taşır.

Her gözlem phase önce/sonra, episode, lifecycle, epoch/sequence, data/grid hash, tanım/geometri hash’i, uygunluk nedeni ve event/intent sonucu taşır. Hatalı/eski paket checkpoint veya audit’i değiştirmez. Aynı semantik mum farklı payload ile gelirse SEMANTIC_PAYLOAD_CONFLICT olur; önceki olay sessizce düzeltilmez veya ikinci kez gönderilmez.

Restart/epoch değişimi, veri boşluğu ve saat sapması otomatik ARMED üretmez. Snapshot/history ve heartbeat yalnız gözlem/audit sağlar; geçmiş close metadata’sı fırsat değildir. Resync phase’i korur, fakat fresh proof ile açık internal resume gerekir. Sıra numarası atlaması tek başına gap değildir; asıl UTC mum grid’i ve veri kanıtı denetlenir. Bu, bağlantı toparlanırken kaçmış mumlardan yanlış yeni sinyal üretilmesini önler.

### E3 olay kimliği ve izolasyon

P7, E3’teki canonical UTF-8 string array/SHA256 kimliğini uygular. Backend integer’ları kayıpsız base10 string’e çevrilir; leading zero kabul edilmez. Python ve TypeScript aynı golden kimliği üretir. Replay alanı domain ID’ye katılmaz; yerel event_id owner/namespace ile ayrılır. Aynı donmuş iz farklı motor örneklerinde ve replay alanlarında aynı domain kimliklerini verir. P6’nın eski kimlik profili korunur; mevcut kayıtlar yeniden yazılmaz.

Yerel olay geçmişi yeni profilin kimlik bileşenlerinden SHA256’yı tarayıcıda da kontrol eder. Böylece yanlış veya eksik E3 kimlikli yeni replay kaydı geçerli sonuç olarak çizilmez.

### Sınırlı sahte teslim politikası

Sabit SQLite fake sink için CHANNEL_UNCONFIGURED, RETRY_BOUNDED, FAILED ve EXPIRED eklendi. Sentetik policy60sn TTL ve en fazla3 denemedir; Retry-After zamanı fake clock ile sınanır. Erken tekrar denemesi bütçe tüketmez; kalıcı ret veya TTL sonrası fake receipt yoktur. ACK kaybı DELIVERY_UNKNOWN kalır ve otomatik tekrar edilmez. Hedef değişince gönderilmemiş intent CANCELED_SUPERSEDED olur; önceden bilinen teslim geri çağrılmaz. Hiçbir durum gerçek Telegram/hesap/emir çağrısı yapmaz.

### Salt okunur sonuç ekranı

GET /api/replay-validation yalnız önceden yürütülmüş paketlenmiş raporu okur; test çalıştırmaz. Kaynak hash’leri, runtime kanıt manifesti, 36 benzersiz vaka, expected/observed eşitliği ve sıfır yan etki sayaçları doğrulanır. Kaynak değişmişse BLOCKED olur; eski yeşil sonuç gösterilmez. Arayüzde hata, bozuk authority yanıtı, unmount sonrası geç yanıt ve yeniden yükleme eski başarıyı korumaz.

## Gerçek sonuçlar

- 36/36 E4 senaryosu geçti. Her case için given/steps kaynağı, expected/observed, farklar, checkpoint/gözlem/evidence ve yan etki sayaçları raporda bulunur.
- Eski DR01 NOT_IMPLEMENTED beklentisi, adapter artık mevcut olduğu için açık execution amendment ile INVALID_PACKET oldu: yalnız LIVE etiketi ve eksik proof gerçek giriş kapısında reddedilir. Eski taslak JSON değiştirilmedi; düzeltme raporda ve panelde görünürdür.
- 20 araç/gösterge türü,48 sorgu: kanonik PRICE çıktıları query→event yolunda, metrik/boolean/hipotetik/gösterge çıktıları olay üretmeme koşulunda sınandı. Bu tam vendor parity veya bütün göstergelerin canlı strateji desteği değildir.
- 920 Python,276 frontend testi ve üretim derlemesi geçti. P7’ye ait47 Python testi:36 vaka+8 ek replay/registry kontrolü+3 rapor testi. TypeScript ek testleri rapor bütünlüğünü ve E3 golden kimliği doğrular.
- 11 yeni P7 tarayıcı kontrolü ve12 P6 regresyon kontrolü geçti. Rapor/karşılaştırma, yeni profil geçmişi, stale/authority/503/geç yanıt, iki tema,1024/1536, restart ve execution DB byte hash’inin korunması kapsandı. Görseller incelendi.
- Network denemesi0; hesap/emir/dış mesaj/execution-store mutation0; runtime worker başlamadı. Windows subprocess testlerinin çıktı okuyucu thread’leri bot worker’ı değildir. Commit/teslim öncesi-sonrası gerçek os._exit çökme testleri yeniden yürütüldü.

## Açık kabul ve kapsam

R05 için kontrollü tazelik/uzun kesinti, clock jump, epoch/resync ve resume engelleri sınandı; gerçek Binance upstream blackout veya fiziksel sistem saati deneyi yapılmış sayılmaz. B5’in fiziksel trackpad/touch, DPR/raster ve ekran okuyucu açıkları korunur. QA01 güncel ürünün masaüstü işlev/görsel/veri/cleanup/performans ve geri yüklenebilir aday kabulünü tamamlamalıdır. Mevcut500kB bundle uyarısı açıktır. Genel ürün/canlı entegrasyon kabulü otomatik verilmez.

Normal önizleme yalnız raporu ve boş/yerel geçmişi okur; senaryo fixture’ları kullanıcının uygulama/veri/execution deposuna yazılmadı.

[36 senaryo raporu](../../reports/chart-p7-scenarios-20261113.json) · [48 sorgu raporu](../../reports/chart-p7-tool-coverage-20261113.json) · [Tarayıcı kanıtı](../../reports/chart-p7-validation-20261113.json) · [Teslim manifesti](../../reports/chart-p7-delivery-20261113.json)
