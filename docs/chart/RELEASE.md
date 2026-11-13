# Grafik sürüm adayı ve geri dönüş

13 Kasım 2026 — **QA01 kontrollü masaüstü doğrulaması tamamlandı; uygulama planı 27/27.** [Kabul raporu](QA01-ACCEPTANCE.md): 920 Python/278 frontend testi, 18 raster durumu, 20 cleanup döngüsü, beş 60 saniyelik performans koşusu ve 10 temiz restore kontrolü geçti. rAF p95 her koşuda16,8 ms; wheel→frame-swap p95 78,487 ms. Genel sürüm/B5 fiziksel kabul açık; canlı entegrasyon kapalı. Sıradaki iş açık fiziksel kabul maddelerinin gözden geçirilmesi. Aşağıdaki önceki teslim kayıtları tarihseldir.

10 Kasım 2026 — E2. Aday kimliği: `chart-candidate-20261110-02`. Durum **geliştirme sürüm adayıdır**; genel sürüm/cihaz kabulü ve B5 açıktır. Bot entegrasyonu veya emir yetkisi vermez. [Kabul sınırları](ACCEPTANCE.md) arşivle birlikte korunur.

## Sabitlenen içerik

`releases/chart-candidate-20261110-02.zip`: Python uygulama kaynağı, derlenmiş web varlıkları, frontend kaynak/lock/testleri, Python testleri, seçili doğrulama araçları/kanıtları ve bu belge. `MANIFEST.json` her dosyanın SHA-256 değerini, sürümleri ve açık kabul durumunu kaydeder. Arşivin SHA-256 değeri ayrı E2 doğrulama raporundadır; kendi checksum’ı manifest içine döngüsel yazılmaz.

`.env`, anahtarlar, kullanıcı SQLite depoları, yerel `data/`, node_modules, .venv ve önbellekler arşivlenmez. Uygulamanın kaynak içindeki `agentrader/data` varsayılan JSON’ları kaynak paketinin parçasıdır; kullanıcı veri deposu değildir. Tarihsel ekran görüntülerinin tümü arşive kopyalanmaz; kök projedeki raporlar korunur. Bu bir wheel/container/masaüstü kurulum paketi veya bütün bağımlılıkları içeren offline kurulum değildir.

Python/Node/npm ve Python dağıtım sürümleri manifestte, frontend bağımlılıkları package-lock.json’da sabittir. `requirements-web-test.lock.txt` mevcut ortamın web/test bağımlılık kapanışını; `requirements-qa.lock.txt` ayrıca browser test araçlarını exact sürümlerle kaydeder. Bunlar bu ortamın snapshot’ıdır; başka işletim sisteminde aynı binary sonucu garanti etmez.

## Doğrulama

Proje kökünden:

```powershell
python scripts/verify_chart_candidate.py releases/chart-candidate-20261110-02.zip
```

Araç arşivi açıp manifestteki tüm dosya hash’lerini denetler; kaynak/anahtar yazmaz. Bozulmuş checksum veya manifest dışı dosya başarısızdır. E2 doğrulaması ayrıca geçici klasöre güvenli çıkarma, oradan izole localhost HTTP/çizim/restart ve yeniden başlatmada aynı bundle kontrolünü uygular.

## Ayrı klasörden çalıştırma

Arşivi örneğin `C:\work\agentrader-candidate` gibi **yeni, boş** bir klasöre çıkar; mevcut projeye veya depolara üzerine açma. Aşağıdaki komutları çıkarılan klasörde çalıştır:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-web-test.lock.txt
$chartState = Join-Path $PWD 'candidate-state'
New-Item -ItemType Directory -Path $chartState -Force | Out-Null
$env:AGENTRADER_WEB_DATABASE = Join-Path $chartState 'application.sqlite3'
$env:AGENTRADER_CHART_DATABASE = Join-Path $chartState 'chart-market.sqlite3'
$env:AGENTRADER_EXECUTION_DATABASE = Join-Path $chartState 'execution.sqlite3'
$env:AGENTRADER_WEB_TOKEN = ''
.\.venv\Scripts\python.exe -m agentrader web serve --port 8876
```

Grafik `http://127.0.0.1:8876/` adresindedir. Port doluysa başka boş yerel port seç. Public borsa okumaları internet ister; açılışta hesap/emir worker’ı başlatılmaz. Public veri ve yerel çizimler için Binance anahtarı veya çizim erişim anahtarı gerekmez. Korunan özel komutlar ayrı kalır. Bu yönergelerde gerçek kullanıcı depoları bağlanmadığı için önceki kişisel çizimlerin görünmesi beklenmez.

Hazır web varlıklarını çalıştırmak için Node/npm gerekmez. Yeniden frontend derlemesi için manifestteki Node/npm sürümleriyle frontend dizininde `npm ci`, `npm test`, `npm run build` kullanılır. Build sonrası manifest doğrulaması değişiklik varsa uyarır; değiştirilmiş ağaç aynı sabit aday değildir. Paket indirme veya başka platformda yeniden derleme bu yerel doğrulamada test edilmiş sayılmaz.

## Geri dönüş

1. Yalnız kendi başlattığın aday sunucusunu terminalinden Ctrl+C ile durdur. Kullanıcının başka sunucusunu topluca kapatma.
2. Mevcut çalışan proje ve veri klasörleri aday denemesinde değişmediği için önceki proje klasöründen önceki sunucuyu tekrar başlatabilirsin.
3. Arşivdeki sabit adaya dönmek için checksum’ı doğrula; yeni boş klasöre yeniden çıkar, ayrı candidate-state ve farklı portla başlat. Dosyaları çalışan kurulumun üzerine kopyalama.
4. Bu E2 geri dönüşü **kod/paket** içindir. Gerçek kullanıcı DB’lerini otomatik taşımaz veya geri sarmaz. Mevcut çizimleri adayla kullanmadan önce uygulama durdurulmuşken tutarlı SQLite yedeği/backup API çıktısı al; canlı WAL veritabanını yalnız .sqlite dosyasını kopyalayarak yedekleme. Depo şeması değişirse ayrıca migration/restore doğrulaması gerekir.

Bu tur canlı kurulum değiştirilmedi; kalıcı kişisel depolar açılmadı. Geçici depodan kayıt ve restart doğrulaması kod adayı geri dönüşünü test eder; kullanıcının canlı DB geri yüklemesi yapılmış gibi sunulmaz.


## CL01–CL04 güncellemesi

02 adayı, önceki01 arşivi korunarak oluşturulur. Tam App gösterge yazım hatasının ekranı düşürmesi giderildi; gösterge grubu hatada tam yeniden çizilir ve heartbeat hata durumunu gizlemez. Sıkışan Fibonacci etiketleri çizgi/geometriyi değiştirmeden seyreltilir. Fiziksel B5/CL04 kullanıcı şu an katılamadığı için ertelendi, geçti sayılmaz. Görünür browser kontrol servisi kullanılamadı; emüle raster kanıtı fiziksel OS/ekran kanıtı değildir.

Önceki D1–D5/30 dakika ölçümleri01 paketine aittir. Yeni paket için etkilenen otomatik kontroller ayrı kaydedilir; eski asset hash eşliği yeni paket için iddia edilmez.01 arşivi önceki kaynak davranışıyla rollback adayıdır; gösterge hatası eski sürümde bulunur. Kullanıcı veritabanları arşivler arasında otomatik taşınmaz.
