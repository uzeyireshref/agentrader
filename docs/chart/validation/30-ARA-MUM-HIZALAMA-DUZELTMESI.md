# Ara mum hizalama hatası ve düzeltmesi

9 Kasım 2026. [Masaüstü raporu](../../../reports/chart-desktop-alignment-20261109.md) G02'yi geçirmedi. Orijinal rapor ve ham kanıtlar korunuyor.

## Bulgu

Tam 15m mum zamanları, zoom/pan, fiyat ölçeği, pane resize, history ve ters ankraj kontrollerindeki ölçülen noktalar geçti. 1h/4h ara zamanları ve 15m 21:52 ankrajı başarısız: 1h 57 çizim/max936.496 px; 4h 48/max937.568 px; 21:52 trend ankrajı736.697 px. Eşik 1 CSS px. Skipped/unchecked referanslar kabul edilmedi.

## Kök neden

Kurulu Lightweight Charts 5.2.1 development kaynağında _internal_indexToCoordinate, !isInteger(index) olduğunda 0 döndürüyor. logicalToCoordinate bu metoda doğrudan gider. Bizim UTC→logical dönüşümümüz ara zamanlarda kesirli indeks üretiyor ve DrawingLayer bunu native API'ye doğrudan gönderiyordu. Native çıktı 0 olduğundan noktalar grafiğin sol kenarına düşüyordu. Referans ölçümü native tam zaman koordinatları arasında hesap yaptığı için farkı yakaladı. Önceki test double doğrusal fonksiyonu kesirli indekste de kabul ettiği için bu motor koşulunu modellemiyordu.

## Düzeltme

frontend/src/drawings.ts projectLogical: floor(index) ve floor(index)+1 için iki native tam indeks koordinatı alınır; kesir oranıyla x interpolasyonu yapılır. Tam indekste tek native çağrı korunur. Null/NaN native cevap uydurulmaz. DrawingLayer tüm yatay dışı ankrajları bu yoldan projekte eder. Kaydedilmiş zaman/fiyat/geometri, migration ve sunucu verisi değiştirilmedi. Ölçüm referansı değiştirilmedi.

## Doğrulama

80 frontend testi ve TypeScript/Vite derlemesi geçti. Beş ek test: sıfıra düşen eski davranış ve yalnız tamsayı native çağrılar; tam/negatif/tarih dışı logical konum; eksik/geçersiz koordinat; 15m/1h/4h ara UTC'nin bağımsız referansla eşitliği; gerçek React trend/bölge/Fibonacci ara zaman SVG çıktıları. Chart test double artık kesirli indeks için gerçek motor gibi 0 döndürüyor. Backend değişmedi, Python regresyonu tekrar koşulmadı.

Yeni bundle index-CXICSJmG.js; CSS index-CbnKi4Zg.css. Offline sonuç, masaüstü hizalama kabulü yerine geçmez.

## Masaüstü kısa tekrar görevi

> docs/chart/validation/30-ARA-MUM-HIZALAMA-DUZELTMESI.md dosyasını oku. Kod değiştirme. desktop-alignment-qa-20261109 QA depolarının yeni kopyasıyla izole anahtarsız yerel örneği aç; ?diagnostics=1 ve index-CXICSJmG.js paketini doğrula. 29 numaralı rapordaki dört fixture'ı görünür tut; 15m tam zaman kontrolünden sonra 1h ve 4h'de 15:45/21:45 UTC gibi ara zamanlarda Hizalamayı ölç çalıştır. 15m'ye dön, trend ankrajını 8 Kasım21:52 UTC yap ve tekrar ölç; ters trend/Fibonacci, zoom/pan/fiyat ölçeği/pane resize ve destekleniyorsa DPR1.25 kontrolünü de uygula. Her türün görünür referansını ölç; skipped/unchecked'i geçti sayma. Ham JSON'ları reports/desktop-alignment-retest-20261109/ altında, özeti reports/chart-desktop-alignment-retest-20261109.md içine kaydet. Ölçülen noktalar <=1 CSS px olmalı; FAILED varsa ekrana ve işlem sırasına kanıt ekle. Eski ham verileri değiştirme; mevcut 8765/kullanıcı çizimlerine dokunma. Test kopyasını/sunucusunu görev sonunda kapat. 30 dakika veya performans koşusu yapma.

G02, bu tekrar sonuçlanana kadar FIXED_AWAITING_DESKTOP_RETEST. Bağımsız raster piksel analizi, native touch, kontrollü boşluklu gerçek veri ve ekrandaki gösterge fixture karşılaştırması ayrı açık maddelerdir. Doğruluk önceliği ve bot bağlantısını bekletme kararı sürer.
