> 10 Kasım E4: [Kuru çalışma kabul planı](docs/chart/DRY-RUN-PLAN.md) ve [E3 veri sözleşmesi](docs/chart/BOT-DATA-CONTRACT.md) hazır. Bunlar planlama çıktısıdır; W4 motoru/bağlantısı uygulanmadı, genel grafik kabulü ve E5 kullanıcı incelemesi açık.

> Güncel: yerel çizim anahtarı kaldırıldı. 667 Python / 67 frontend testi ve 4.908 bağımsız EMA/RSI değeri geçti. Veri/çizim doğruluğu önceliği sürüyor; Canvas hizalama kabulü açık. [Ayrıntılar](docs/chart/validation/28-ANAHTARSIZ-CIZIM-VE-GOSTERGE-DOGRULUGU.md).

> Güncel grafik kalite denetimi: 666 Python / 26 frontend testi geçti. Bot bağlantısından önce görsel, yarış ve uzun oturum kabulü bekleniyor. [Denetim ve kabul matrisi](23-GRAFIK-KALITE-DENETIMI-VE-KABUL.md).

> W2/W3 kalite kapısı (9 Kasım): GitHub kaynak araştırması ve ilk iyileştirmeler tamamlandı. W4 öncesinde masaüstü/mobil çizim etkileşimi ve uzun oturum performans kabulü bekliyor. [Güncel kapsam ve kabul ölçütleri](22-GRAFIK-KAYNAK-ARASTIRMASI-VE-KALITE.md).

# Agentrader — Kendi grafik terminaline geçiş planı

Güncelleme: 9 Kasım 2026 · Ana program: WEB-TERMINAL-W0-W9.

## Planlama kararı

Kullanıcı kendi grafik ve çizim ortamımızla önce web üzerinde ilerlemeyi onayladı. TradingView/Pine/webhook aşaması ana yol haritasından çıkarıldı. Önceki A0–A12 programı mevcut yürütme altyapısının teknik geçmişi ve alt sistem iş listesi olarak korunur; bütün API uçlarını bitirmek grafik tesliminin ön koşulu değildir.

W0 planlama tamamlandı. W1 yerel uygulama/API temeli uygulandı; 631 test ve izole gerçek localhost HTTP/restart kontrolü geçti. [W1 teslim belgesi](20-W1-YEREL-UYGULAMA-API.md). W2 grafik/public veri ve W3 kalıcı çizimler uygulandı; 665 Python, 9 frontend testi ve gerçek HTTP/restart/public veri kontrolleri geçti. W2/W3 görsel etkileşim kabulü bekliyor; W4–W9 henüz uygulanmadı. [Güncel teslim](21-GRAFIK-VE-KALICI-CIZIMLER.md). Paketlerin güncel durumları [data/development-progress.json](data/development-progress.json) içindedir. Geçiş sırasında mevcut CLI, oturumlar, risk profili ve emir kimlikleri korunur.

## Çalışma ilkeleri

Her paket kullanıcı tarafından görülebilen bir çıktı, bağımlılıklar ve kabul kanıtıyla kapanır. TASARLANDI, KODLANDI, ÇEVRİMDIŞI_DOĞRULANDI, DEMO_DOĞRULANDI ve KULLANICI_AKIŞI_HAZIR ayrı kaydedilir. Planlama tamamlanması özelliklerin kodlandığı anlamına gelmez.

Geliştirme için verilmiş onay rutin paket geçişlerinde yeniden istenmez. Belirsiz ürün ayrıntıları mevcut kararlara göre çözülür; sermaye/işlem yetkisi, dış yayın ve gerçek hesap geçişi kendi somut kapsamıyla değerlendirilir. Eski işlem onayları tekrar kullanılmaz.

## W0 — Ürün yönü ve mimariyi yeniden düzenle

Durum: TAMAMLANDI (yalnız planlama).

Çıktı: güncel 01–04, 07 ve 19; README yönlendirmesi; makinece okunur yeni sıra; önceki planların arşivi.

Kabul: güncel belgeler kendi grafiğimizi ana kaynak gösterir; TradingView geliştirmesi zorunlu aşama değildir; geçmiş doğrulamalar ve eksikler korunur; doküman bağlantıları/JSON tutarlıdır. Bu paket grafiğin çalıştığı iddiası üretmez.

## W1 — Uygulama sınırı ve çalıştırma düzeni

Durum: UYGULANDI_VE_DOĞRULANDI. [Teslim ve kullanım](20-W1-YEREL-UYGULAMA-API.md). HTTP yalnız runtime.inspect kabul eder; işlem onayı/yürütmesi W6'ya aittir. Genel piyasa hattı W2'de eklenecek.

Bağımlılık: W0.

- Mevcut yürütücüler etrafında ortak uygulama komut/sorgu sınırı kur. Önce salt okunur sağlık, yetenek ve durum sorguları sun.
- Grafik ve Telegram için kimliği doğrulanmış ortak komut kabulü tasarla; tek yazıcı yürütme kilidini koru. HTTP isteği içinde izleyici döngüsü veya borsaya doğrudan POST çalıştırma.
- API, frontend ve arka plan çalışma sorumluluklarını ayır. API yenilenmesi izleyiciyi çoğaltmamalı; pozisyon yokken de piyasa takibi çalışabilmeli.
- Prototip için React/TypeScript ve Python API çerçevesini değerlendir; bağımlılık ve geliştirme komutlarını belgele. Mevcut çekirdeğe zorunlu web bağımlılığı yükleme.
- Veritabanı geçişlerini sürümlü ve tekrar çalıştırılabilir yap; mevcut tabloları ve plan v1/v2 sözleşmelerini koru.

Kabul: anahtarsız yerel başlatma ve sağlık sorgusu; istemci sır içermez; yetkisiz yazma reddi; ikinci yürütücü engeli; yeniden başlatmada mevcut kayıtlar korunur. Başlangıçta yalnız localhost; dış erişim ayrı işletim adımıdır.

## W2 — Binance verili ilk web grafiği

Durum: UYGULANDI_PUBLIC_VERİ_DOĞRULANDI; görsel masaüstü/mobil kabul bekliyor. [Kanıt ve kullanım](21-GRAFIK-VE-KALICI-CIZIMLER.md).

Bağımlılık: W1.

- BTCUSDT ile başla; borsa meta verisinden desteklenen USD-M sözleşmeleri seçilebilir yap. Adı bilinen her coinin otomatik desteklendiğini varsayma.
- Geçmiş mumlar için mevcut PublicMarket/CandleStore altyapısını kullan; piyasa WebSocket hattı, yeniden bağlantı, REST ile boşluk tamamlama ve kalite durumu ekle.
- Mum, hacim, crosshair, fiyat/zaman eksenleri, zoom/pan, geçmişe kaydırma ve zaman dilimi seçimini oluştur. İlk zaman dilimleri 15m/1h/4h/1d/1w; diğerleri veri desteği doğrulandıktan sonra.
- Grafik kütüphanesi için çizim/etkileşim prototipi yap. Lightweight Charts bir adaydır; hazır çizim paketi kabul edilmez. Lisans ve atıf gereksinimlerini seçilen sürümde doğrula.

Kabul: mum zamanı/fiyatı kaynakla eşleşir; açık mum güncellenir, kapanış tek olaydır; sembol değişiminde eski veri karışmaz; kopma ve eskilik görünür; reconnect boşluğu tamamlar; masaüstü ve dar ekranda kullanım kontrol edilir. Demo yürütme ile public canlı veri açık etiketlidir.

## W3 — Kalıcı çizimler ve çalışma alanı

Durum: UYGULANDI_KAYIT_HTTP_DOĞRULANDI; gerçek canvas sürükleme/ölçek ve görsel kabul bekliyor. Çizimlerin bot takibi W4 kapsamıdır.

Bağımlılık: W2.

- Önce yatay çizgi ve dikdörtgen fiyat bölgesi; oluştur/seç/taşı/düzenle/sil; fiyatı sayısal düzenleme; geri al/yinele ve kayıt göstergesi.
- Ekran pikseli yerine zaman/fiyat koordinatlarını sunucuda sakla. Coin ve çalışma alanı eşleştirmesi ile sürüm denetimli kayıt uygula.
- Çizim silme/değiştirme, bağlı aktif kuralı açık politika ile durdursun; eski fırsat ve onay yeni geometriye taşınmasın.
- Sonraki genişletmede trend çizgisi/ray ve iki noktalı Fibonacci ekle; bunlar ilk yatay takip tesliminin ön koşulu değildir.

Kabul: sayfa/servis yeniden açıldığında aynı çizimler; zoom/zaman dilimi değişiminde doğru fiyat; eski sürümle kaydetme çakışması görünür; kayıt hatasında sessiz veri kaybı yok; silinen çizim yeni olay üretmez. Önce gerçek kullanımla çizim rahatlığını doğrula.

## W4 — Yaklaşma/temas ve ilk kullanılabilir takip

Bağımlılık: W3.

- Çizimden ayrı, sürümlü takip kuralı oluştur: yalnız izle veya fırsat adayı; yön, tolerans, fiyat kaynağı, süre, cooldown ve yeniden kurulma koşulu.
- Yaklaşma/temas olaylarını kalıcı ve tekrar önlemeli işle; yerel olay akışı ve mevcut bildirim kuyruğuna bağla.
- Yapılandırılmış Telegram göndericisiyle teslim durumunu doğrula; teslim hatası grafik üzerinden görünür olsun. Kanal kurulmamışsa yerel bildirim kanıtı ile Telegram eksikliğini ayrı tut.

Kabul: BTC grafiğinde çizim → etkin kural → ölçülmüş olay → bildirim; ekran kapalıyken backend takibi; restart/tekrar olaylarında bildirim fırtınası yok; veri yokken temas uydurulmaz. W2–W4 ilk kullanılabilir grafik/takip teslimidir. Otomatik giriş kapalıdır.

## W5 — Durum hafızalı strateji ve geçmiş oynatma

Bağımlılık: W4.

- Kapanışla kırılım ve retest; ikinci direnç testi için ilk temas/geri çekilme/ikinci yaklaşma/gözlem durumları.
- Temas ayrılığı, gözlem süresi, tolerans, tepki karşılaştırması, geçersizlik ve tekrar tetiklemeyi sayısallaştır.
- Strateji sürümü ve yalnız o anda bilinen veriyle geçmiş oynatma kur; gecikmeli teyit edilen pivotlar teyit zamanında kullanılabilir.

Kabul: ilk ve ikinci temas kanıtları; restart aynı durumdan devam eder; ileri veri kullanılmaz; OHLC içi belirsiz sıra kesinmiş gibi sunulmaz; strateji parametreleri kullanıcı arayüzünden anlaşılır. Yaklaşık %5 örneği sabit zorunlu kural değildir.

## W6 — Fırsat, somut plan, Telegram onayı ve demo yürütme

Bağımlılık: W5; gerekli mevcut yürütme yolu için demo doğrulama hazırlığı.

- Kişisel strateji olayından sürümlü fırsat, açıklama ve desteklenen somut plan üret. Plan derleyicisi mevcut v1/v2 şemasına uymalı; desteklenmeyen eylem reddedilmeli.
- Telegram ve terminal onaylarını aynı kimlik/sürüm/süre/tek kullanım kontrolleriyle işle. UI doğrudan borsa çağırmasın.
- Onay sonrası fiyat, veri, yetki, sahiplik ve ortak risk yeniden denetlensin. Public canlı analiz ile demo yürütme arasındaki fiyat farkı giriş öncesinde kontrol edilsin.
- Önce önizleme/gölge çalışma; sonra somut yetkili demo planıyla giriş, koruma, kısmi/tam çıkış ve kesinti senaryosu.

Kabul: ret/yanıtsızlık/süre sonu/yetkisiz/tekrar onay giriş üretmez; plan veya çizim değişikliği eski onayı geçersiz kılar; belirsiz POST tekrar edilmez; fill ve koruma borsadan doğrulanır. Gerçek para kullanılmaz.

## W7 — Bağımsız tarama ve sermaye tahsisi

Bağımlılık: W6.

- Aynı stratejileri seçili sembollerde çizim gerektirmeden çalıştır; otomatik bulunan seviyenin kaynağını sakla.
- Fırsatları ölçülebilir koşullarla sırala; puanı başarı olasılığı olarak sunma. Kişisel ve tarama fırsatlarını kaynak etiketleriyle aynı kuyruğa al.
- Önce kullanıcı tanımlı sabit tahsis ve boşta bakiye; bütçe/teminat/nominal/azami kayıp ayrımı; mevcut ortak risk rezervine bağlanma.
- Aynı sembolde tek etkin yönetim sahibi kısıtını koru; çelişen adayları sırala/beklet/reddet, ayrı planlarla sahipliği bölme.

Kabul: eşzamanlı adaylar kapasiteyi iki kez kullanamaz; minimum emir ve masraflar denetlenir; fırsat yoksa bütçe bekler; farklı semboller bağımsız izlenir. Varsayılan demo profilinin tek pozisyon sınırı kendiliğinden yükseltilmez.

## W8 — Sınırlı otomatik portföy çalışma yetkisi

Bağımlılık: W7 ve yeni yetki modeli doğrulaması.

- Mevcut Mod A/B'ye dokunmadan ayrı yönetim yetkisi tanımla: sembol, strateji/sürüm, bütçe, yön/kaldıraç, risk, süre, sıklık ve yeniden giriş sınırları.
- Yeni somut planları üst yetkiye bağla; her emirde geçerli kapsamı tekrar doğrula. Karma modda otomatik ve onaylı kapsam açık olsun.
- Yetki iptali yeni girişleri durdursun; açık pozisyonların koruma/izinli çıkışları sürsün. AI yetkiyi genişletemesin.

Kabul: önce gölge çalışma, sonra somut sınırlı demo yetkisi; bütçe ve yetki ihlalinde giriş yok; yapılan ve engellenen kararlar açıklanır; restart ve iptal yarışları testlidir. Yalnız şema süresini uzatmak bu paketin tamamlandığı anlamına gelmez.

## W9 — İleri analiz, işletim ve uygulama paketleme

Bağımlılık: ilgili temel akışlar.

Kaynaklı haber/AI, dominans/göreli güç/OI/funding, performans ölçümü, çoklu grafik, gelişmiş çizimler, güvenli sunucu işletimi ve yedekleme; web terminalinin PWA/masaüstü/mobil olarak paketlenmesi. Daha büyük depolama veya ek borsa ürünleri ancak somut ihtiyaca göre.

Kabul: ölçülmüş kullanım/performance hedefleri, kaynak/gecikme/maliyet görünürlüğü; kurulum/yeniden başlatma/yedekten dönüş kanıtı. PWA önbelleği eski fiyatı canlı gibi veya çevrimdışı onayı geçerli gibi göstermez. Canlı işlem ayrı hazırlık ve yetkilendirme kararıdır.

## Paralel korunacak işlem altyapısı işleri

A3–A11'in eksik demo kanıtları ve koruma kusurları ilgili W paketinin ihtiyaç duyduğu ölçüde ele alınır. Mevcut açık oturumların korunması önceliklidir. Gelişmiş grid politikaları, çapraz ürün portföyü, Spot/COIN-M ve kullanılmayan API uçları ilk terminal teslimini bekletmez. Geçmiş paket durumları makine kaydında execution_backlog altında korunur.

## Sonraki somut iş

W2/W3 görsel masaüstü/mobil, çizim sürükleme/ölçek ve kullanım kabulü. Grafik ve kalıcı çizim kodu ile veri/API doğrulamaları tamamlandı. Ardından W4 yaklaşma/temas ve bildirim bağlanacak.
