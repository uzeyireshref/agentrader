# P2 — Saat kanıtı ve uzun kesinti

10 Kasım 2026. P2 TAMAMLANDI. 718 Python / 143 frontend testi, TypeScript ve üretim derlemesi, 9 üretim App kontrolü ve gerçek public WebSocket saat kanıtı geçti. Sıradaki P3'tür. Bu paket bot değerlendirme motoru, olay üretimi veya emir yetkisi eklemez.

## Sürümlü politika

chart-time-policy/1: consumer taşıma yaşı en fazla 10.000 ms, upstream veri yaşının belirsizlik dahil üst sınırı en fazla 10.000 ms; saat belirsizliği en fazla 1.000 ms; duvar/monotonic ilerleme farkı en fazla 250 ms. 20.000 ms'den uzun veri kesintisi yeniden snapshot gerektirir. Saat örneği 300.000 ms sonra yenilenir. Örnekten sonraki belirsizlik 100 ppm drift varsayımıyla artırılır. Bu drift ölçülmüş donanım garantisi değil, açık politika varsayımıdır; politika sürümü değiştirilmeden eşikler değiştirilemez.

## Backend

chart_clock.measure_time public /time isteğinin başlangıç/bitiş wall ve monotonic saatlerini ölçer. RTT/2 + 1 ms örnek belirsizliğidir; ölçüm sırasında clock jump, negatif monotonic süre veya belirsizlik sınırı aşımı UNTRUSTED olur. /time cevabının isteğin ölçülen aralığında üretilmesi ve upstream saatinin drift sınırı içinde ilerlemesi varsayılır. Offset, RTT ve belirsizlik chart-clock-sample/1 alanında REST history ile taşınır. Yerel /time sample_id'si kimlik doğrulama imzası değildir.

Örneğin wall/mono koordinatları yalnız aynı backend sürecindeki 128 kayıtla sınırlı registry'de tutulur. Başka süreçten, bilinmeyen veya eksik sample_id CLOCK_UNTRUSTED olur. Ham producer monotonic değerleri JSON'a gönderilmez; consumer bunlardan çıkarma yapmaz. Aktif feed immutable örnek referansını tutar; registry tahliyesi mevcut feed'i değiştirmez.

StreamTiming event_time, producer monotonic veri alım yaşı, upstream yaş üst sınırı, uncertainty ve snapshot bariyerini üretir. Tekrar/eski event ve heartbeat veri yaşını yenilemez. Taze kabul edilen upstream event yaşını yeniler. Yanlış gelecek timestamp, gecikmiş upstream, clock jump/örnek süresi aşımı veya uzun kesinti yeni clock örneği ve REST seed gerektirir; hatayı packet üretiminde gözlemek de bariyeri kalıcılaştırır. Clock düzelmiş gibi görünmesi tek başına bariyeri kaldırmaz.

Gerçek SharedFeed saat kanıtı geçerli olmadan socket verisini tüketmeye başlamaz; kontrollü yeniden deneme/backoff uygular. FeedState tek başına eski/kanıtsız test veya veri girdisini gözlem verisi olarak işleyebilir, fakat timing BLOCKED kalır. Böyle bir girdinin LIVE ham reducer etiketi, zaman kanıtı veya canlı karar uygunluğu değildir. Üretim browser timing kapısını uygular. Eski close_event alanı geçmiş metadata'dır; yeni semantik olay değildir. Kesinti sonrası yakalama close'u güvenilir feed'e uygulanmadan reddedilir; REST seed geçmiş kapanışlarını yeni olay olarak üretmez. P6'dan önce zaten canlı semantik olay üreticisi bulunmaz.

Feed timeout, idle emekliliği ve flush aralıkları monotonic saate geçti. Paketlerde mevcut received_at/observed_at alanları uyumluluk için wall zamanında kaldı; güvenilir yaş hesabında kullanılmaz.

## Tarayıcı

chart-time-proof/1 yalnız üreticinin sürelerini ve upstream event zamanını taşır. applyPacket kendi performance.now ve Date.now alım noktasını kaydeder. checkFreshness producer yaşlarına yalnız yerel monotonic geçen süreyi ekler. Yeni heartbeat taşıma alımını güncelleyebilir; upstream yaşı sıfırlayamaz. Aynı upstream event için yaşın geri gitmesine izin verilmez; dondurulmuş FRESH heartbeat tekrarları da eski veriyi canlandıramaz. Aynı sequence içinde yeni event zamanı taşıyan paket engellenir.

Browser wall-clock jump veya monotonic gerilemesi snapshot'a kadar engelli kalır. Eksik/bozuk/gelecek/çok belirsiz producer kanıtı Canlı etiketi üretmez. Kanıtsız eski sentetik paketler mevcut ekran uyumluluğunu korur; ayrıca gelecek received_at kontrolü eklendi. Bu legacy fallback bir bot saat uygunluğu sağlamaz; üretim feed'i her pakette timing taşır. Sekme uykusundan dönüşte yaş denetimi tekrar yapılır. Yeni epoch ve değişmez kalite/snapshot güvence katmanı P3 kapsamındadır.

## Doğrulama ve çalışan grafik

12 yeni Python testi: ölçüm belirsizliği, iki yönlü wall jump, monotonic gerileme, örnek süresi, eksik/yabancı sample, eski/taze heartbeat, 25 saniyelik kesinti/yakalama close'u, fresh seed ile toparlanma, sticky saat bariyeri, gerçek yerel HTTP/WebSocket ve runtime SharedFeed kanıt zorunluluğu. Önceki dört freshness testinin fake wall ve monotonic saatleri birlikte enjekte edildi; gerçek test bekleme süresi artırılmadı.

7 yeni frontend testi ve üretim App'te 9 kontrollü durum geçişi geçti. Gerçek public bağlantıda timing FRESH görüldü; rapordaki ölçüm upstream yaş üst sınırı yaklaşık 420 ms ve belirsizlik yaklaşık 204 ms'dir. Bu kısa bağlantı gerçek borsa kesintisi/uzun oturum veya fiziksel cihaz testi değildir. 30 dakika performans testi tekrar edilmedi.

Grafik http://127.0.0.1:8765 üzerinde P2 sürümüyle çalışır; sağlık OK, işlem komutları kapalıdır. İlk yenileme girişimi eski sunucu nedeniyle port çakışması verdi; PID'si doğrulanan eski Agentrader süreci durdurularak doğru sürüm başlatıldı. Public history ve WebSocket kontrolleri yalnız piyasa/cache verisini okur/yeniler; hesap/emir veya çizim yazma komutu gönderilmedi.

Kanıt: reports/chart-p2-validation-20261110.json, chart-p2-python-tests-20261110.log, chart-p2-frontend-tests-20261110.log, chart-p2-browser-20261110.json, chart-p2-live-20261110.json. Üretim bundle index-CJ9UseTX.js. Aday02 arşivi ve B5/fiziksel kabul açıkları korunur.
