# Proje düzenleme analizi — 15 Kasım 2026

## Bulgular

İnceleme kök dosyaları, Python paketleri, HTTP/uygulama katmanı, frontend, testler, betikler, paket kaynakları ve belge bağlantılarını kapsadı. Depoda düzenlemeden önce de çok sayıda değiştirilmiş ve Git'e eklenmemiş dosya vardı. Bunların içerikleri korunarak çalışıldı; reset, checkout veya commit yapılmadı.

- Kökte 46 numaralı plan/teslim belgesi ve uzun bir geliştirme günlüğü bulunuyordu. Güncel başlangıç bilgileri tarihsel kabul notları arasında kayboluyordu.
- Python paketinin kökünde bot, grafik, entegrasyon, altyapı ve CLI modülleri karışıktı. Alan sınırları dosya önekleriyle anlatılıyor, klasörlerle gösterilmiyordu.
- 142 geliştirme betiği aynı dizindeydi. Bazıları birbirini doğrudan, bazıları modül adıyla, bazıları dinamik dosya adıyla çağırıyordu.
- Kaynak dosyalarını doğrulayan katalog ve replay kayıtlarında yollar ile SHA-256 özetleri bağlıydı. Taşımadan sonra bunların çevrimdışı yeniden üretilmesi gerekiyordu.
- Sürüm paketi üreticileri yalnız scripts kökündeki Python dosyalarını topluyordu. Yeni dizin yapısında yardımcı betikleri eksik paketleyeceklerdi.
- Yerel testlerden kalma iki tmp dizininde yalnız host_limits tablosu içeren limit.sqlite3 dosyaları vardı. İki eski, bağımsız performans probe'u hiçbir aktif komut veya testten çağrılmıyordu. tmp dizinleri tests/test_transport.py içindeki RequestGovernor testlerinin 6 Kasım tarihli kalıntılarıydı; silinmeden önce yerel geri dönüş kopyaları alındı.
- Düzenlemeden önce Demo süreklilik kabulü DEMO_CONTINUITY_ACCEPTANCE_REQUIRED ile kapalıydı. Katalog VERIFIED_TRACEABILITY, replay VERIFIED_ISOLATED durumundaydı. Yeni bir piyasa gözlemi yapılmış gibi kayıt üretilmedi.

## Yapılan düzenleme

| Alan | Konum |
| --- | --- |
| Bot çekirdeği | agentrader/bot |
| Grafik ve çizimler | agentrader/chart, frontend |
| Bot–grafik birleşimi | agentrader/integration |
| Ortak altyapı | agentrader/shared |
| CLI | agentrader/cli |
| HTTP ve uygulama servisleri | agentrader/api, agentrader/application |
| Bot belgeleri/betikleri | docs/bot, scripts/bot |
| Grafik belgeleri/betikleri | docs/chart, scripts/chart |
| Entegrasyon belgeleri/betikleri | docs/integration, scripts/integration |
| Ortak proje belgeleri/bakım | docs/project, scripts/maintenance |

298 dosya taşındı; iki sahipsiz probe kaldırıldı. [Eski → yeni yol haritası](REORGANIZATION-MAP.json) ve [kaldırılan probe listesi](REORGANIZATION-REMOVED.json) kayıtlıdır. Kök README kısa başlangıç rehberine dönüştürüldü; önceki ayrıntılı içerik [geliştirme geçmişinde](DEVELOPMENT-HISTORY.md) korundu. Numaralı belgeler kendi alanlarının history dizinlerine alındı. Bu isim, planların tamamlandığı anlamına gelmez; aktif planların durumu belgelerin içindedir.

Importlar, mock hedefleri, alt süreç modül adları, paketleme betikleri ve kaynak dosyası yolları güncellendi. Dinamik betik çalıştırıcıları tek ve açık alan listesinden dosya buluyor. Yeni paketler setuptools tarafından agentrader* kapsamıyla keşfedilir. JSON kaynakları ve web_assets paket kökündeki mevcut konumlarını korur.

Testler ortak yardımcıları ve unittest keşif sözleşmesini korumak için tests altında tutuldu. Frontend zaten grafik arayüzünün ayrı çalışma alanıdır. API, uygulama ve migration katmanları iki alanın ortak servis sınırlarını korur.

## Korunanlar

.env, risk-demo.json, data içindeki kullanıcı veritabanları, logs, reports kabul kayıtları, releases geri dönüş arşivleri, tools/rea ve yüklü skill dizinleri taşınmadı veya silinmedi. Eski sürüm adaylarının içeriği değiştirilmedi; geri yükleme denetimi eski ve yeni yardımcı modül yollarını destekler. Genel komut girişi python -m agentrader olarak kaldı. Python iç modüllerini doğrudan kullanan harici kodlar yeni alan yollarına geçmelidir.

Düzenlemeden hemen önceki kaynak içerikleri, mevcut kullanıcı değişiklikleri dahil, reports/reorganization/before altında saklandı. Bu yerel kopyalar Git'e eklenmez. Tarihsel kanıtlar güncel kabul gibi yeniden etiketlenmedi.

## Doğrulama

Başlangıç: 1262 Python testi, 362 frontend testi geçti. Düzenleme sonrası da 1262 Python testi ve 362 frontend testi geçti; atlanan test yok. Üretim frontend derlemesi başarılı. 36/36 izole replay senaryosu, 10 gerçek loopback HTTP kontrolü ve 6 gerçek Chromium çizim/navigasyon kontrolü geçti. Wheel üretildi; yeni paketler ve JSON/web kaynakları wheel içinden yüklenerek doğrulandı. Yapı kontrolünde 390 Python dosyası, 1565 yerel import, 654 belge bağlantısı ve 298 taşıma kaydı doğrulandı. Ham kayıtlar reports/reorganization-*.log ve reports/reorganization altında bulunur. Yapı denetimi: python scripts/maintenance/check_project_layout.py. Bu kontrol yerel importların hedeflerini, belge bağlantılarını, taşıma haritasını ve dinamik komut listesini denetler; emir veya ağ isteği göndermez.

## Kalan teknik borç

Grafik arayüzündeki App.tsx ve çizim etkileşim bileşenleri hâlâ büyük; bazı eski kabul betikleri tarihli rapor adlarına bağlı. Bunlar klasör temizliğinden ayrı davranış değişiklikleri gerektirir. Bu çalışmada algoritmalar, strateji, risk sınırları, API adresleri veya onay kuralları yeniden tasarlanmadı. Üretim derlemesindeki büyük JavaScript parçası uyarısı ayrıca ele alınabilir. Fiziksel cihaz kabulü ve gerçek Demo süreklilik gözlemi bu düzenlemenin doğrulama kapsamına dahil değildir.
