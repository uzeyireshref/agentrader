# G10 — Ortak bot/grafik kabulü

15 Kasım 2026. G0–G9 üretim arayüzü ve çizim adaptörü ortak regresyondan geçti. Bu paket üretim davranışını veya veritabanı şemasını değiştirmez; kabul araçlarını güncel sözleşmelere bağlar ve bütün araçları aynı kanıt matrisinde toplar.

## Kabul kapsamı

- 26 çizim varyantı: eski/yeni bölge, Fibonacci ve kanal şemaları; üç çapalı projeksiyon; çizgi/ışın, cetvel, pozisyon planları ve üç metin aracı.
- Her satırda ham HTTP okuması, metin/not okuması, HTTP matematik, veri hazırlığı, render, UI bağlamı, üretim ChartBot adaptörü ve manuel koruma ayrı alanlardır.
- 23 varyant sayısal HTTP hesabında READY; text/note/price_label için UNSUPPORTED_OPERATION beklenen sonuçtur. Bunlara matematik desteği etiketi verilmez.
- 5 tarayıcı grubu × 52 yüklenmiş/gelecek varyant = 260 senaryo. Normal ve kesirli mum koordinatları, DPR 1/2 ve kesirli DPR 1.25 kapsanır. Kesirli zaman, mum başlangıcından +225 saniyedir; saklanan UTC koordinatı değişmez. Çapa toleransı en çok 1 CSS px; kaydedilen başlangıç çapa hatalarının en büyüğü 0 px.
- Gelecek regresyon kanalı, kaynak mumlar gelmeden çizgi uydurmaz; WAITING_FOR_DATA gösterir, kaynak gelince aynı çapalarla hesaplanır ve yeniden yüklemede korunur. Tampon mum sayısı yapay mumlarla artırılmaz.
- LINEAR/LOG ölçekleri, yeniden yükleme, iki sekme, oturum kimlikleri, gizli/kapanmış sekme, gerçek TTL süresi ve yeniden bağlantı ayrıca doğrulanır. Eski düz eğimli araçların LOG reddi açık ve beklenendir; kanal ailesinin LOG modeli ayrı doğrulanır.

## Sayısal ve adaptör kanıtı

Backend ve frontend ortak, önceden belirlenmiş bağımsız vektörlerle sınanır: `channel-family-g4.json`, gösterge parity fixture'ları ve altı elle hesaplanan `projection-g9.json` vektörü. Tam kesir/decimal sonuçlar birebir karşılaştırılır. İstatistiksel ve log hesaplarında testlerde belgelenen kayan nokta toleransları kullanılır; ekran kabulünün üst sınırı ayrıca 1 CSS px'dir. HTTP fixture testleri ve 62 gösterge tarayıcı kontrolü dokuz gösterge yuvasının hesap/yapılandırma davranışını doğrular.

Üretim ChartBot gerçek izole HTTP sunucusuna bağlanarak 26 varyantı oluşturur, not yazar, taze bağlamdan okur/hesaplar, düzenler, paketler ve temizler. Kayıp yanıt sonrası kalıcı günlük, sunucu/adaptör yeniden başlatma, ayrı CLI süreci ve büyük Unicode paket kontrolü de geçer.

Her varyantta manuel çizim için güncelleme, silme, not yazma/silme ve toplu işlem denenir: adaptörde 130 ret, adaptör ön denetimini atlayan doğrudan HTTP'de 130 adet 403 `DRAWING_ORIGIN_PROTECTED`. Manuel geometri, revizyon, köken ve not değişmez. Manuel paketten kopya yeni bot kimliği alır; temizlik yalnız bu kopyayı siler.

## Test araçlarında giderilen sorunlar

Oturum testinde diğer sekmenin kaydettiği ETH/1h tercihi yeni sekmeye taşınıyordu; fixture artık gerçek UI üzerinden BTC/15m seçtikten sonra o pazara ait sentetik paketi yayınlar. UI durumunun bot erişimine kapalı olduğunu söyleyen eski kontrol beklentileri gerçek oturum HTTP okumalarıyla değiştirildi.

Eski alarm testlerinin sabit 8765 portu yerine geçici portta, geçici veritabanlarıyla sunucu açılır. Eski raporların içerikleri ortak test çalıştırıcısı tarafından korunur. Kanal ailesi testleri de kullanıcı sunucusundan bağımsızdır.

Eski onay UI testi güncelliğini yitirmiş gerçek Demo süreklilik belgesine bağımlıydı. G10 yalnız sentetik UI kabulünde açık `--synthetic-demo-acceptance` seçeneğiyle mevcut test bağımlılığı enjeksiyonunu kullanır. Eksik gerçek kanıtın üretim kapısında reddedildiği ayrıca doğrulanır. Üretim kontrolü, gerçek kabul belgesi veya emir yetkisi değiştirilmez; bu sonuç canlı Demo kabulü değildir.

## Şema ve açık sınırlar

Yeni migration yoktur; mevcut sürüm 13, yedekleme ve eski kayıt kökeni koruma testleri tam Python paketinde geçer. UI bağlamı istemci bildirimidir; piyasa kanıtı veya emir yetkisi sağlamaz. Testler sentetik halka açık piyasa girdileri ve geçici veritabanları kullanır. Gerçek hesap bilgisi veya emir gönderimi kullanılmaz.

G11 kalmıştır: gerçek Demo veri akışında, ayrı çalışma alanında, manuel sentinel nesneleri yanında deterministik stratejinin çalışan bot adaptörünü kullanmasının gözlemi; stale durumda durma ve yeniden başlatmada tekilleştirme. Fiziksel dokunmatik/trackpad veya gerçek borsa kesintisi gözlemi bu raporun iddiası değildir.

Kanıtlar: [G10 raporu](../../reports/chart-interface-g10-20261115/README.md), [araç matrisi](../../reports/chart-interface-g10-20261115/acceptance-matrix.json), [kaynak/derleme ve kanıt kimlikleri](../../reports/chart-interface-g10-20261115/validation.json).
