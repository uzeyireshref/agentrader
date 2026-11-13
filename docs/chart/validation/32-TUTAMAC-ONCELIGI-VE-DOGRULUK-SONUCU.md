# Tutamaç önceliği ve doğruluk sonucu

9 Kasım 2026. [Kontrollü fixture raporu](../../../reports/chart-desktop-fixture-20261109.md) incelendi. Altı senaryoda 4.908 sayısal gösterge değeri + 492 warmup null alanı ve dört gerçek crosshair örneği eşleşti. On iki geçerli hizalama ölçümünde dört çizimin 20/20 referansı geçti. Boşluk ankrajının bir logical bar hareketi doğru UTC'yi üretti; reload geometrileri sıfırladı. Bunlar gerçek Chromium renderer'ında **headless** otomasyonla yapıldı; görünür Windows/native touch testi diye sunulmaz. Önceki sayısal kanıtlar korunur.

Varsayılan ölçekte Fibonacci hit-line seçili trend tutamacını örttü. Bu somut etkileşim hatası düzeltildi: seçili çizimin ankrajları ayrı ve son SVG katmanına taşındı. Çizim gövdelerinin sırası değiştirilmedi; seçim sırasında gövde pointer capture hedefi taşınmaz. Tutamaçlar aynı geometry/drag/cancel yolunu kullanır; kayıt şeması ve zaman/fiyat hesapları değişmedi. Cache gövde ile handle gruplarını ayrı anahtarlarla tutar ve seçim değişince temizlenir. Tutamaç yarıçapı 5 CSS px.

88 frontend testi ve derleme geçti. İki yeni React/jsdom testi: çakışan Fibonacci'den sonra seçili trend tutamacının SVG'nin son katmanında olması, yalnız kendi ankrajını düzenlemesi; üst katman ankrajının Escape iptalinde kayıt yapmaması ve hareket kilidini bırakması. jsdom gerçek browser hit-testing yapmaz; kısa Chromium hit-test tekrarı gerekir. Backend değişmedi, Python testleri tekrar çalıştırılmadı.

Yeni ana bundle index-ChTfbwr0.js; lazy FixtureLab-ClM2r020.js.

## Kısa tekrar

> docs/chart/validation/32-TUTAMAC-ONCELIGI-VE-DOGRULUK-SONUCU.md dosyasını oku. Kod değiştirme. FixtureLab URL'sinde yeni bundle'ı doğrula. Varsayılan time_gap ölçeğinde trendi çizginin erişilebilir yerinden seç; fiyat ölçeğini genişletmeden, seçili ilk tutamacın merkezinde gerçek browser elementFromPoint hedefinin trend circle olduğunu doğrula. Tutamacı bir logical bar sağa taşı: yalnız trendin ilk ankrajı değişmeli; Fibonacci/bölge/yatay değişmemeli. Hizalama ölçümünü ve reload sıfırlamasını kontrol et. Sonucu reports/chart-handle-priority-retest-20261109.md dosyasına kaydet. Headless sayısal/hit-test otomasyonu yeterlidir; görünür kullanıcı deneyimi veya native touch kabulü yaptığını iddia etme. Mevcut normal çalışma alanına yazma; uzun performans/dayanıklılık testi yapma.

Genel grafik kabulü kapatılmadı. Raster piksel analizi, native touch ve diğer açık kabul kapsamları ayrı tutulur. Yeni bot veya emir işlemi yok.
