> Güncel grafik planı (10 Kasım 2026): [Çekirdek plan v2](docs/chart/PLAN.md). 21 yeni paket, 0 tamamlandı; sıradaki T01 ortak araç sözleşmesi. Eski A–E planı 24/25 ve B5 ertelenmiş/açık olarak korunur; P1 tamamlandı. Tasarım ve canlı bot bağlantısı sonraki kapsamdır.

> Güncel durum: **24/25 tamamlandı; E5 grafik kapanış sırası onaylandı; CL01 geçti, sırada CL02. B5 tamamlanmadı; kullanıcı isteğiyle ertelendi.** [Plan](docs/chart/PLAN.md).

> Başvuru: [Aktif plan](docs/chart/PLAN.md), [kabul kapsamı](docs/chart/ACCEPTANCE.md), [sabit aday ve geri dönüş](docs/chart/RELEASE.md). B5 ve genel sürüm kabulü açıktır.

### Önceki geliştirme notları

Aşağıdaki tarihsel test notları güncel tamamlanma sayısı veya kabul kararı değildir.

> Mum/hacim çizimi başarısızken yanlış Canlı etiketi düzeltildi; 109 frontend testi ve derleme geçti. [Kapsam](docs/chart/validation/36-GRAFIK-DURUMU-VE-CIZIM-TOPARLANMASI.md).

> Fiyat hassasiyeti ve eski OHLC gösterimi düzeltildi;102 frontend testi/derleme geçti. [Doğrulama](docs/chart/validation/35-FIYAT-HASSASIYETI-VE-OHLC-DOGRULUGU.md).

> Canlı veri tazeliğinde iki açık düzeltildi; 671 Python testi, izole HTTP/restart ve public canlı veri probe geçti. [Kapsam](docs/chart/validation/34-CANLI-VERI-TAZELIGI-VE-ESITLEME.md).

> Gecikmeli kayıt/coin geçişinde iki yarış hatası yeniden üretilip düzeltildi; 96 frontend testi ve derleme geçti. [Kapsam](docs/chart/validation/33-GECIKMELI-KAYIT-VE-COIN-GECISI-DOGRULUGU.md).

> Kontrollü boşluk ve native seri/imleç referans ekranı eklendi; 86 frontend testi/derleme geçti. Gerçek tarayıcı kontrolü bekliyor. [Kapsam ve görev](docs/chart/validation/31-KONTROLLU-BOSLUK-VE-EKRAN-GOSTERGE-DOGRULUGU.md).

> Masaüstü hizalama testinde ara mum zamanı hatası bulundu; kesirli indeks dönüşümü düzeltildi. 80 frontend testi/derleme geçti; kısa masaüstü tekrar testi bekliyor. [Bulgu ve görev](docs/chart/validation/30-ARA-MUM-HIZALAMA-DUZELTMESI.md).

> Doğruluk turu: isteğe bağlı native motor/SVG hizalama ölçümü eklendi; 75 frontend testi ve derleme geçti. Gerçek masaüstü ölçümü bekliyor. [Kapsam ve görev](docs/chart/validation/29-CIZIM-HIZALAMA-DOGRULAMASI.md).

> Güncel: yerel çizim anahtarı kaldırıldı. 667 Python / 67 frontend testi ve 4.908 bağımsız EMA/RSI değeri geçti. Veri/çizim doğruluğu önceliği sürüyor; Canvas hizalama kabulü açık. [Ayrıntılar](docs/chart/validation/28-ANAHTARSIZ-CIZIM-VE-GOSTERGE-DOGRULUGU.md).

> Kısa performans ölçümü p95 48,70 ms ile hedefi geçmedi. SVG/gösterge yazma optimizasyonu yapıldı; 60 frontend testi/derleme geçti, karşılaştırma bekliyor. [Bulgular ve kısa tekrar testi](docs/chart/validation/27-KARE-GECIKMESI-VE-PERFORMANS-OPTIMIZASYONU.md).

> Güncel kalite turu: 54 frontend testi ve derleme geçti. React iptal senaryoları ile isteğe bağlı 10/60 saniye ölçüm paneli eklendi. [Kapsam ve masaüstü kısa ölçüm görevi](docs/chart/validation/26-KISA-PERFORMANS-VE-ETKILESIM-TESTLERI.md).

> Yeni mum tekrar testi tamamlandı: 30 dakika 14,774 saniye, iki mum geçişi ve yeniden bağlantı gözlemleri geçti; önceki kalıcı hata yeniden görülmedi. FPS/heap ve diğer açık kabul maddeleri kapsam dışı. [Masaüstü tekrar test raporu](reports/chart-desktop-rollover-retest-20261109.md).

> Masaüstü testi kısmen geçti; uzun oturumda hata bulundu. Yeni mum güncellemesi ve 4.000 mum penceresi düzeltildi; 37 frontend testi/derleme geçti. [Bulgular ve tekrar testi](docs/chart/validation/25-MASAUSTU-BULGULARI-VE-YENI-MUM-DUZELTMESI.md).

> Güncel grafik kalite denetimi: 666 Python / 26 frontend testi geçti. Bot bağlantısından önce görsel, yarış ve uzun oturum kabulü bekleniyor. [Denetim ve kabul matrisi](23-GRAFIK-KALITE-DENETIMI-VE-KABUL.md).

> 9 Kasım grafik kalite güncellemesi: 666 Python ve 16 frontend testi geçti. Trend/Fibonacci, EMA/RSI ve mıknatıs eklendi; görsel kabul bekliyor. Güncel ayrıntılar: [kaynak araştırması ve kalite](22-GRAFIK-KAYNAK-ARASTIRMASI-VE-KALITE.md).

# Agentrader — Geliştirme durumu

Güncelleme: 9 Kasım 2026 · Ana program: WEB-TERMINAL-W0-W9.

## Güncel ürün kararı

Kendi Binance verili grafik ve çizim terminalimiz önce web üzerinde geliştirilecek. TradingView/Pine/webhook ana geliştirme yolundan çıkarıldı. Mevcut Python emir/risk/plan çekirdeği korunacak. Kullanıcı bu yön ve plan düzenlemesini onayladı; geliştirme paketleri için tekrar genel onay beklenmez.

## W2/W3 uygulaması

Kendi React web grafiği, paylaşılan public piyasa akışı ve sunucuda sürümlü çizimler eklendi. Yatay çizgi/bölge, sayısal düzenleme, taşıma, silme, undo/redo; cookie ile yerel eşleştirme ve çalışma alanı kaydı mevcut. Kullanım [21](21-GRAFIK-VE-KALICI-CIZIMLER.md).

665 Python ve 9 frontend testi; izole gerçek localhost HTTP/restart; public Binance 504 sözleşme, BTCUSDT 300 mum ve LIVE akış başarılı. Finansal depo/risk profili değişmedi. Görsel masaüstü/mobil ve gerçek canvas etkileşim QA'sı doğrulanmadı; W2/W3 tam kabul işaretlenmedi. Son tam kabul paketi W1 olarak korunur.

## Önceki W1 teslimi

Yerel uygulama/API temeli eklendi: ağsız sağlık/yetenek sorgusu, kimliği doğrulanmış salt okunur yerel durum, ayrı uygulama deposu ve sürümlü migration, runtime.inspect kuyruğu ve ayrı tek işçi. Mevcut CLI için web bağımlılığı zorunlu değildir. [Kurulum ve kullanım](20-W1-YEREL-UYGULAMA-API.md).

631 test (37 yeni) ve geçici depolarla gerçek localhost HTTP/restart kontrolü geçti. İşlem veritabanları ve risk profili doğrulama sırasında değişmedi. Emir, hesap ayarı, Telegram mesajı veya mevcut pozisyon izleyicisi başlatılmadı; kontrol sunucuları kapatıldı.

W0'da hedef/plan/sözleşme belgeleri güncellenmiş, önceki metinler [arşive](docs/archive/2026-11-09/README.md) alınmıştı. W1 uygulama teslimidir; grafik, çizim ve strateji motoru henüz yoktur.

## Yeni program

| Paket | Durum | Sonuç |
|---|---|---|
| W0 | PLANNING_COMPLETE | Ürün yönü ve sözleşmeler güncellendi |
| W1 | IMPLEMENTED_OFFLINE_AND_LOCAL_HTTP_VERIFIED | Yerel API, salt okunur komut kuyruğu, işçi ve migration |
| W2 | IMPLEMENTED_PUBLIC_LIVE_VERIFIED_PENDING_VISUAL_QA | Web grafik/public veri; görsel kabul bekliyor |
| W3 | IMPLEMENTED_HTTP_PERSISTENCE_VERIFIED_PENDING_VISUAL_QA | Kalıcı çizimler ve workspace; etkileşim QA bekliyor |
| W4 | NOT_STARTED | Yaklaşma/temas, olay ve bildirim; ilk kullanılabilir takip |
| W5 | NOT_STARTED | İkinci test, kırılım/retest ve geçmiş oynatma |
| W6 | NOT_STARTED | Fırsat/plan, uzaktan onay ve uçtan uca demo |
| W7 | NOT_STARTED | Bağımsız tarayıcı ve sermaye tahsisi |
| W8 | NOT_STARTED | Sınırlı otomatik yönetim yetkisi |
| W9 | NOT_STARTED | İleri analiz, işletim ve uygulama paketleme |

## Korunan işlem altyapısı

| Alan | Mevcut | Kalan kanıt veya kapsam |
|---|---|---|
| A0–A2 | 95 operasyon envanteri, salt okunur keşif, ortak dayanıklı transport | Yeni adaptörler aynı kontrolleri kullanmalı |
| A3 | Farklı sembollü USD-M çoklu oturum ve ortak SINGLE/grid rezervleri | Gerçek çoklu oturum demo; çapraz ürün/varlık kapsamı |
| A4 | Hesap ayar komutları ve yönetilen izole teminat | Yeni teminat yollarının demo yazma kanıtı |
| A5 | Korunan native amend, toplu oluşturma/değiştirme/iptal | Gerçek demo yazma/kesinti; desteklenmeyen kombinasyonlar |
| A6 | SINGLE kademeli çıkış, girişe stop ve takip | Yeni yolların gerçek demo kanıtı |
| A7 | Özel hesap WebSocket normalleştirme, REST bariyeri, sayfalama | Gerçek fill/iptal/stop olayı ve uzun kesinti |
| A8–A9 | Yönlü/neutral grid; bot takibi ve isteğe bağlı borsa stop yenileme | Gerçek demo, neutral takip ve kalan politikalar |
| A10 | Ön plan servis, sağlık/durdurma, kalıcı kuyruk ve Telegram göndericisi | Uzaktan onay, teslim kanıtı, otomatik görev/rapor erişimi |
| A11 | Gelir ve gerçekleşme REST sayfalaması | Diğer tamamlayıcı iş akışları |
| A12 | Başlanmadı | Spot/COIN-M ve diğer ürünler; ilk grafik tesliminin koşulu değil |

A paketleri tamamlandı diye yeniden etiketlenmedi. Eski durumlar data/development-progress.json içindeki execution_backlog kaydında korunur. 05–18 numaralı belgeler işlem altyapısının tarihli kapsamını açıklar; yeni ürün sırasının yerine geçmez.

## Doğrulama sınırı

Son tam doğrulama: 9 Kasım 2026, 665 Python ve 9 frontend testi; atlanan yok. İzole gerçek HTTP/restart, çizim revizyonları ve workspace oturumu başarılı. Kanıt: [chart-workspace-validation-20261109.json](reports/chart-workspace-validation-20261109.json). [Public veri denemesi](reports/chart-live-validation-20261109.json) de başarılı. W1'in 631 testlik raporu tarihsel referanstır.

Gerçek yerel HTTP kontrolü: anahtarsız başlangıç, özel erişim/Origin sınırı, finansal komut reddi, kabulün yalnız kuyruğa yazması, ayrı işçi, restart sonrası tek komut/tek işleme ve işlem deposu oluşturmama. Yerel API kontrolü borsa demo yazma kanıtı değildir.

Önceki 12/12 salt okunur kontrol, kullanıcı WebSocket bağlantısı ve BLOCKED_ACCOUNT_NOT_FLAT snapshot kendi tarih/hesap kapsamıyla korunur. Bugünkü borsa hesabı okunmadı; yeni demo yazma doğrulaması yapılmadı. [7 Kasım regresyon raporu](reports/development-validation-20261107.json) tarihsel referanstır.

W0 belge/JSON kontrolü [planning-restructure-20261109.json](reports/planning-restructure-20261109.json) içinde ayrı tutulur; uygulama test kanıtı değildir.

## Mevcut önemli kısıtlar

- API public grafik ve kimlik doğrulamalı çizim metadatası ile runtime.inspect sunar. Strateji motoru yoktur; çizimler kendi başına takip/emir başlatmaz. Görsel etkileşim kabulü bekliyor.
- Mevcut kullanıcı WebSocket'i özel hesap/emir akışıdır; canlı grafik veri hattı değildir.
- Portföy risk değerlendirmesi mevcuttur; fırsat seçip sermaye dağıtan yönetici henüz yoktur.
- Mod A/B somut plan sürümlerine bağlıdır; sürekli yeni plan üretme yönetim yetkisi henüz yoktur.
- Çoklu oturum farklı sembollerle sınırlıdır. Aynı sembol ayrı planlar arasında bölünmez; varsayılan risk profilinin tek pozisyon sınırı korunur.
- Çalışan ön plan izleyicisi sürekli kurulu sunucu servisi değildir. Mevcut pozisyon yokken genel fırsat taraması henüz çalışmaz.
- Gerçek hesap desteği etkin değildir. Yeni geliştirme yönü yeni işlem veya hesap ayarı yetkisi vermez.

## Sonraki iş

[02 numaralı plandaki](02-ASAMALI-GELISTIRME-PLANI.md) W2/W3 görsel kabulü; ardından W4 yaklaşma/temas ve bildirim. Ayrıntılı kaynak eşleştirmesi ve çizim/kural tasarımı [19 numaralı belgede](19-KENDI-GRAFIK-TERMINALI-VE-GECIS.md).


## 10 Kasım — CL01–CL03 otomatik kapanış ve CL04 erteleme

CL01 iki gerçek sekmede 13 kontrollü tutarlılık senaryosuyla doğrulandı. CL02 gösterge yazım hatasının uygulamayı kapatması düzeltildi: 15 hata senaryosu ve 12.420 bağımsız sayısal karşılaştırma geçti. CL03 sıkışık Fibonacci etiketleri düzenlendi; 9 ekran/DPR durumunda 243 raster ölçümü geçti (azami 0,844 CSS px). Frontend 127/127 test geçti. Güncel index-z15JopqV.js için üç 60 saniyelik kontrollü performans koşusu geçti; bu, yeni bir 30 dakika veya fiziksel GPU kabulü değildir.

Kullanıcı fiziksel hareketleri şimdi yapamayacağını belirtti. CL04 ertelendi, B5 tamamlanmadı; ana plan 24/25. Bot bağlanmadı. Önceki aday 01 korunur; güncel geliştirme adayı 02 için RELEASE.md ve reports/chart-closure-progress-20261110.json izlenir.
