# Agentrader — Proje ve hedefler

Güncelleme: 9 Kasım 2026 · Saat dilimi: Asia/Baku · Karar: kullanıcı tarafından onaylandı.

## Ana yön

Agentrader, Binance piyasa verilerini kendi grafik ekranında gösteren, kişisel çizimleri ve stratejileri takip eden, bağımsız fırsat tarayan ve kullanıcı yetkisi içinde işlem yöneten kişisel bir trading platformudur. Önce web uygulaması geliştirilecek; aynı backend ve alan modelleri korunarak daha sonra yüklenebilir web, masaüstü veya mobil uygulama değerlendirilecektir.

**TradingView hesabı, Pine Script ve TradingView alarm/webhook zinciri ana ürün yolundan çıkarılmıştır. Kendi grafik ve çizim altyapımız ürünün temelidir.** Açık kaynak bir grafik kütüphanesi kullanılması, TradingView hesabı veya Pine bağımlılığı anlamına gelmez. Harici sinyal entegrasyonu ancak ileride ayrı bir ihtiyaç olarak ele alınabilir.

## Kullanıcının yapacağı işler

- Binance USD-M Futures sembollerini seçmek, zaman dilimini değiştirmek ve canlı mumları izlemek.
- Kendi grafiğimizde yatay destek/direnç, bölge, trend çizgisi ve Fibonacci oluşturmak; taşımak, düzenlemek, silmek ve çalışma alanını kaydetmek.
- Çizime yaklaşma, temas, kapanışla kırılım, retest veya ikinci test gibi takip kuralları bağlamak; yalnız izle veya işlem adayı üret davranışını seçmek.
- Botun neden fırsat gördüğünü, karşı bulguları, veri eksiklerini, giriş/stop/hedefleri ve riskini görmek.
- Telegram veya uygulamadan somut planı onaylamak/reddetmek; ileride açık bir yönetim yetkisiyle sınırlı otomatik çalışmayı etkinleştirmek.
- Grafik açık olmasa da backend çalışırken takip ve pozisyon yönetiminin sürmesini sağlamak.

## İki fırsat kaynağı, tek işlem yolu

1. Kişisel çizimlere bağlanan sürümlü stratejiler.
2. Kullanıcının seçtiği varlık evreninde aynı strateji altyapısını kullanan bağımsız tarayıcı.

İki kaynak da olay → açıklanabilir fırsat → somut işlem planı → yetki ve bağımsız risk → mevcut yürütücü → borsa uzlaştırması → sonuç akışında birleşir. Çizgiye temas tek başına işlem yetkisi değildir.

## İlk kullanılabilir teslim

BTCUSDT ile başlayan, desteklenen USD-M sembollerini listeleyebilen web grafiği; kapanmış/geçerli geçmiş mumlar ve canlı güncellemeler; yatay çizgi ve bölge; sunucuda kalıcı kayıt; yeniden açmada aynı çizimler; yaklaşma/temas kuralı; tekrarları önlenen olay ve bildirim.

Bu teslim kullanıcı tarafından çizim rahatlığı, veri doğruluğu, kayıt ve gerçek takip davranışı üzerinden değerlendirilecek. İlk teslimde otomatik giriş açılmaz. Ardından trend/Fibonacci ve ikinci direnç testi gibi durum hafızalı kurallar; kimliği doğrulanmış onay ve demo yürütme bağlanır. Tüm TradingView özelliklerinin ilk sürümde eşitlenmesi veya kusursuzluk garantisi kapsam taahhüdü değildir.

## Güncel grafik ve çizim uygulaması

W2 public grafik/veri hattı ve W3 kalıcı çizim kodu eklendi. 665 Python, 9 frontend testi, gerçek localhost kayıt/restart ve public Binance akışı başarılı. Görsel ve gerçek canvas etkileşim kabulü bekliyor. Yeni uygulama durumu ve kurulum için [21](21-GRAFIK-VE-KALICI-CIZIMLER.md) esas alınır. Çizimler henüz bot takibine veya emre bağlı değildir.

## Korunan mevcut çekirdek

Python 3.12+, SQLite, demo USD-M adaptörü, kalıcı emir niyetleri, belirsiz teslim uzlaştırması, sahiplik kontrolü, plan v1/v2, SINGLE/GRID/NEUTRAL_GRID yolları, ortak risk rezervleri, koruma/çıkış yönetimi, hesap kullanıcı akışı ve bildirim kuyruğu korunur. Mevcut CLI komutları geçiş sırasında çalışmaya devam eder. Canlı public piyasa okuması ile demo hesap yürütmesi ayrı kalır.

W1 yerel API, kimliği doğrulanmış salt okunur durum ve kalıcı inceleme kuyruğu eklendi; [teslim belgesi](20-W1-YEREL-UYGULAMA-API.md). W1 tesliminde 631 test geçmişti; güncel W2/W3 doğrulaması 665 Python + 9 frontend testi ve public veri kontrolünü içerir. Bu sayı grafik terminalinin tamamlandığı veya yeni yürütme yollarının gerçek demoda doğrulandığı anlamına gelmez. Güncel durum [07-GELISTIRME-DURUMU.md](07-GELISTIRME-DURUMU.md), kanıtlar [DOGRULAMA.md](DOGRULAMA.md) içindedir.

## Yetki ve sermaye hedefi

- Mod A: somut plan sürümüne işlem öncesi onay.
- Mod B: önceden etkinleştirilmiş somut planın açık koşulları içinde yürütme.
- Gelecek yönetim yetkisi: seçili semboller/stratejiler, bütçe, kaldıraç, risk, süre ve yeniden giriş sınırları içinde yeni planlar üretme ve yürütme. Henüz uygulanmadı; mevcut Mod B bunun yerine geçmez.

Sermaye tahsisi ile teminat, pozisyon nominali ve azami kayıp ayrı alanlardır. Kullanıcı sabit paylar belirleyebilir; daha sonra açık yetkiyle fırsata göre tahsis eklenebilir. Bütçe ayrılması hemen işlem açılması demek değildir. Sohbetteki 100 USD, AAVE/SOL/POL ve yaklaşık %5 tepki örnekleri işlem talimatı veya onaylanmış risk parametresi değildir.

## Sonraki ürün yetenekleri

Çoklu zaman dilimi piyasa yapısı, göreli güç, uygun kaynaklarla dominans/TOTAL3, likidite/OI/funding, kaynaklı haber ve AI açıklaması; karar ve performans geçmişi. Hacim, taker baskısı ve zincir üstü borsa akışı ayrı ölçüler olarak sunulur. AI sayısal gerçeğin, riskin ve kullanıcı yetkisinin yerine geçmez. Öğrenme önce ölçüm ve inceleme demektir; otomatik kural/risk değişikliği değildir.

## Kesinleşen ve açık kalan tercihler

Kesin: kendi grafik ortamımız, önce web, Binance USD-M önceliği, Python çekirdeğini koruma, çizimlerin sunucuda sayısal kaydı, Telegram, iki fırsat kaynağı ve demo üzerinden ilerleme.

Açık: grafik kütüphanesi ve frontend/backend çerçevesinin prototip sonucu nihai seçimi; telefon ve masaüstü paketleme; haber/AI sağlayıcıları; sunucu; varlık listesi; gerçek sermaye, kaldıraç ve risk değerleri. React/TypeScript ve Lightweight Charts başlangıç adaylarıdır; mevcut bağımlılıklara kurulmuş sayılmaz.

Web önce yerel çalışabilir; ilk aşamada halka açık yayın veya hosting gerekmez. Bilgisayar kapalıyken çalışmak için sürekli açık bir sunucu ve işletim kurulumu gerekir.

## Belge düzeni

- [02 — Ana geliştirme sırası](02-ASAMALI-GELISTIRME-PLANI.md)
- [03 — Mimari ve işlem sözleşmesi](03-MIMARI-VE-ISLEM-SOZLESMESI.md)
- [04 — Kullanıcı akışları ve kabul ölçütleri](04-KULLANICI-BEKLENTILERI-VE-YAPILABILIRLIK-TASLAGI.md)
- [19 — Grafik terminali ve geçiş tasarımı](19-KENDI-GRAFIK-TERMINALI-VE-GECIS.md)
- [06 — İşlem yetenek envanteri](06-BINANCE-DEMO-YETENEK-ENVANTERI-VE-GELISTIRME-SIRASI.md): alt sistem referansı; ana teslim sırası değildir.

Önceki hedef ve planların bağlamı [tarihsel arşivde](docs/archive/2026-11-09/README.md) korunur. Yeni yön için 01–04 ve 19 esas alınır; geçmiş kanıtlar tarihleriyle geçerlidir.
