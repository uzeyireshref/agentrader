# P3 — Epoch ve değişmez piyasa kanıtı

10 Kasım 2026. P3 TAMAMLANDI. 729 Python / 153 frontend testi, TypeScript/üretim derlemesi, kontrollü üretim App reconnect kontrolleri ve gerçek public snapshot doğrulaması geçti. Son kanıt reports/chart-p3-validation-20261110.json içindedir. Sıradaki T03 fiyat-zaman cetvelidir; P4 yeni araçlar tamamlandıktan sonra gelir.

## Akış ve snapshot bariyeri

Her FeedState ve her başarılı REST seed yeni UUID stream_epoch alır. SharedFeed upstream socket'i yeniden kurduğunda seed de yenilenir. generation/sequence yalnız aynı epoch içinde kıyaslanır. WebSocket göndericisi hem generation hem epoch izler: restart sonrası sayaçlar aynı olsa bile yeni epoch için full snapshot gönderilir. Aynı canlı feed'e yeni browser aboneliği de önce snapshot alır; bu durumda producer epoch aynı kalabilir.

Tarayıcı transport bağlantısına ayrı bir yerel serial verir. Kapanmış bağlantının mesaj/close/error callback'i yeni bağlantıya müdahale edemez. İlk paket veya yeniden bağlantı update'i snapshot bariyerini geçemez. Yeni epoch yalnız doğrulanan snapshot ile alınır. Eski epoch'lar mevcut market/view ömrü boyunca hatırlanıp reddedilir; market bağlamı/uygulama yeniden kurulunca yeni yaşam başlar ve eski callback serial/abort sınırıyla dışarıda kalır. Retired epoch listesi görünüm ömrüyle büyüyen bilinçli replay korumasıdır; sınırsız oturumda sabit bellek iddiası yoktur.

Aynı epoch'ta düşük sayaç reddedilir. Eşit generation/sequence yalnız heartbeat olabilir; veri revision'ını değiştiremez. Büyük sequence atlaması tek başına gap değildir. Eksik delta veya bozuk hash güncel source paketinde görülürse App socket'i kapatıp yeniden full snapshot ister. Tekrar/eski paket bu toparlanmayı tetiklemez. Mevcut tek socket içindeki yeni epoch düşük/eşit generation ile kabul edilmez; gerçek process restart zaten yeni transport/snapshot bariyerinden geçer.

## Değişmez veri kanıtı

chart_evidence.DataEvidence frozen dataclass içinde canonical payload ve proof JSON metni tutar. view/payload okumaları yeni nesne döndürür. Kaynak mum, piyasa, kalite veya döndürülen nesnenin sonradan değiştirilmesi eski kanıtı değiştirmez. Feed seed'de market/quality alanlarını da derin kopyalar. Yakalama feed lock'u altında veri revision'ıyla yapılır. Status/heartbeat/sequence değişimi data_revision veya snapshot hash'ini değiştirmez; kabul edilen gerçek veri ve seed değiştirir.

chart-data-proof/1 şunları taşır: epoch/generation/data_revision, SHA-256 snapshot ve grid hash'i, ilk/son zaman, bar/closed sayıları, actual missing bars, grid validity, kullanılabilir kesintisiz kapanmış mum sayısı, VERIFIED/BLOCKED ve nedenleri. live_eligible/order_authority daima false'tur. Dinamik P2 saat yaşları hash'e katılmaz; ayrı timing kanıtıdır.

Hash girdisi chart-data-snapshot/1: source/environment/product/price_type/symbol/interval, epoch/generation/revision, piyasa metadatası, raporlanan kalite ve kanonik mumlar. OHLC/hacim grafiği sayıları big-endian IEEE-754 hex olarak kodlanır; böylece Python 100.0 ile JS 100 gibi JSON gösterim farkları hash'i bozmaz. Negatif sıfır sıfıra normalize edilir. Exact Decimal sidecar ayrıca kayıpsız metinle hash'e katılır; float altında kalan fiyat değişimi de hash'i değiştirir. Anahtarlar sıralı, UTF-8 JSON kullanılır. Bu fingerprint imza veya kaynak kimlik doğrulaması değildir.

Backend hashlib ve frontend SHA-256 uygulaması bağımsız karşılaştırılır. Frontend implementasyonu ayrıca node:crypto ile 24 padding/Unicode vektörü ve bilinen abc vektörü üzerinden sınandı. Ortak dört fixture complete/gap/precision_unproven/short_history durumlarını içerir. Bu test verisi deterministik sentetik referanstır, canlı borsa verisi diye sunulmaz.

## Grid ve warmup sınırı

2.000 veya 4.000 UI geçmiş mumu tek üretici snapshot'ı gibi ilan edilmez. Producer kanıt penceresi en fazla 499 mumdur; mevcut başlangıç history varsayılanı 300'dür. Frontend history ile birleştirdiği serinin yalnız proof first/last/count penceresini doğrular. Dışarıdaki bağımsız eski history bu kanıta sessizce eklenmez.

UTC bucket/haftalık Pazartesi hizası, artan tekil zaman, close_time birimi, OHLC/hacim, geçmiş barların kapalı olması ve gerçek zaman farkları denetlenir. Upstream kalite OK dese bile actual grid gap BLOCKED olur. Eksik exact fiyat/tick, yanlış piyasa kimliği ve bilinmeyen kalite ayrıca engellenir. Eksik grid UI'da Veri boşluğu, diğer doğrulanamayan veri Veri doğrulanamadı olur; Canlı etiketi verilmez.

require_warmup açık pozitif tam sayı ister. Yalnız açık son bar öncesindeki kesintisiz kapanmış suffix sayılır; mevcut açık bar warmup'a katılmaz. Gereksinim bilinmiyorsa WARMUP_REQUIREMENT_UNSPECIFIED, yetersizse INSUFFICIENT_WARMUP. Başarılı sonuç DATA_PROOF_VERIFIED_NOT_ELIGIBILITY'dir; P1/P2/P3/veri tek başına kural/olay/emir yetkisi değildir. Kural bazlı gösterge warmup/seed modeli T09/P4/P5'te bağlanır.

## Doğrulama ve runtime

11 yeni Python testi: immutable kayıt ve alias izolasyonu, epoch/reseed/restart, aynı sayaçlı gerçek HTTP/WebSocket geçişi, gerçek gap, warmup, kalite/precision/market engeli, sub-float hash değişimi ve idle feed monotonic regresyonu. P2'den kalan iç idle dalında wall-mono çıkarımı da düzeltildi.

10 yeni frontend testi: bağımsız hash, ortak fixture, ilk update bariyeri, sıfırlanan sayaçlar, aynı producer'a yeniden bağlantı, eski epoch reddi (66 geçiş dahil), sequence atlaması, payload/quality/market/hash kurcalama, farklı history penceresi ve durum etiketleri. Üretim App headless Chromium testinde gerçek yerel socket kapatma/açma, bozuk delta sonrası otomatik snapshot ve geçerli yeni revision sınandı. Bu gerçek Binance kesintisi veya process kill testi değildir.

İlk 729 testlik tam koşuda yeni WebSocket testinin kapanışında CancelledError görüldü; ilk log korundu. Endpoint iptal sırasında da hub referansını finally ile bırakacak şekilde düzeltildi; test server close yanıtını bekler. Son 729 testlik koşu temiz geçti (28,262 s). Starlette/httpx deprecation uyarısı mevcut; test hatası değildir.

Gerçek public/localhost kontrolünde iki yeniden abonelik snapshot'ı (300'er mum) hash ve 50 kapanmış mum gereksinimiyle doğrulandı. Bu kısa test upstream outage, P7'nin 36 replay senaryosu veya sonsuz süre kabulü değildir. 30 dakika performans/retention ve fiziksel B5 testleri tekrar edilmedi. Aday02 arşivi korunur.

Grafik http://127.0.0.1:8765 üzerinde güncel backend ile çalışır. Yeni frontend için açık sayfa yenilenmelidir. Hesap/emir/harici mesaj veya kullanıcı çizim yazma isteği gönderilmedi; public piyasa cache'i normal çalışma kapsamında yenilendi. Canlı bot adaptörü ve kalıcı semantik olay motoru henüz yoktur.
