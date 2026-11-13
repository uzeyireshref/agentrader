# Kontrollü boşluk ve ekrandaki gösterge doğruluğu

9 Kasım 2026. Doğruluk aşaması devam ediyor. Önceki ara mum tekrar testindeki 12 geçerli native/SVG ölçüm geçti; bu kapsam tüm grafik kabulü değildir.

## Ayrı doğruluk ekranı

URL: http://127.0.0.1:8765/?diagnostics=1&fixture=1 . İki parametre birlikte verilince canlı App yerine lazy yüklenen FixtureLab açılır. FixtureLab borsa/API/WebSocket bağlantısı açmaz, çizim deposu okumaz/yazmaz. Çizim taşıma yalnız bu ekranın React state'ini değiştirir; sayfa yenilemesiyle sıfırlanır. Normal canlı çalışma alanı ayrı kalır.

Sabit 300 mum ve Python Decimal precision=50 referansı kullanılır. Flat/rising/falling/mixed/time_gap/changed_live_close senaryoları mevcuttur. time_gap senaryosunda 132 ve 133 indeksleri arasında 3 eksik 15m mum bulunur; sahte mum eklenmez. Trendin ilk ankrajı tam bu boşluğun ortasındadır; Fibonacci ters zaman sırasındadır. Dört çizim türü aynı DrawingLayer, native motor ve AlignmentPanel ile gösterilir.

EMA20/EMA50/RSI14 aynı uygulama hesapları ve LineSeriesWriter yoluyla gerçek motor serilerine yazılır. Seri değerlerini doğrula düğmesi hesaplama fonksiyonunun doğrudan çıktısı yerine native series.data() verisini ayrı Python referansıyla karşılaştırır. İmleç tablosu ise gerçek crosshair event.seriesData değerlerini karşılaştırır. Bu iki kanıt birbirinden ayrıdır. Tolerans 1e-8, ısınma null değerleri ayrıca denetlenir.

Son 200 mum düğmesiyle geçmiş kısaltılırsa referans seed'i aynı kalmadığı için gösterge karşılaştırması NOT_COMPARABLE_HISTORY döner. Tam geçmişi yükle, yeniden 300 mumu motor serilerine gönderir ve bağımsız karşılaştırmayı etkinleştirir. Bu laboratuvarın veri hazırlama yoludur; canlı REST pagination testi yerine geçmez. changed_live_close ayrı sabit son-kapanış fixture'ıdır, gerçek canlı packet testi değildir.

## Otomatik doğrulama

86 frontend testi ve TypeScript/Vite derlemesi geçti. Altı yeni test: eksik mum sayısı ve uydurma mum olmaması; boşluk ortasında trend/ters Fibonacci; altı senaryoda tam referans/warmup karşılaştırması; yanlış/eksik değerin reddi; geçmiş öncesi/sonrası boşluk ankrajının native tam indekslerle eşitliği; boşluk üzerinden bir logical bar taşımanın sabit saniye yerine doğru UTC'yi üretmesi. Motor/ekran entegrasyonu gerçek tarayıcı kontrolünü bekler.

Referans JSON'unun lazy test paketine dahil edilmesi için resolveJsonModule açıldı. Normal kullanımda fixture chunk yüklenmez. Backend değişmedi; önceki 667 Python testi bu tur tekrar koşulmadı. Gerçek kullanıcı verisine yazma yapılmadı.

## Masaüstü kısa doğruluk görevi

> docs/chart/validation/31-KONTROLLU-BOSLUK-VE-EKRAN-GOSTERGE-DOGRULUGU.md dosyasını oku. Kod değiştirme. Yerel sunucuda ?diagnostics=1&fixture=1 URL'sini aç; normal canlı çalışma alanını değiştirme. time_gap senaryosunda 300 mum ve üç eksik mum açıklamasını doğrula. Boşluk bölgesine git; Hizalamayı ölç ile dört test çiziminin görünür referanslarını kaydet. Zoom/pan, fiyat ölçeği ve pane resize sonrası yeniden ölç; skipped noktaları geçti sayma. Trendin boşluk ortasındaki ankrajını bir mum sağa taşı; geometri/hizalama raporuyla doğru UTC hareketini gözle. Sayfayı yenileyip sıfırlandığını doğrula. Seri değerlerini doğrula ile her altı senaryoda native serinin 300 zaman noktasını referansla karşılaştır; warmup null'larını koru. time_gap'te 132/133 civarındaki gerçek iki mumun üzerinde imleç gezdir; İmleç referans karşılaştırması alanındaki gerçek seriesData/expected/error/passed değerlerini ayrı örnekler olarak kaydet. mixed ve changed_live_close senaryolarında son mumun imleç değerlerini de karşılaştır; bunu canlı packet testi diye etiketleme. Son 200 mum ile NOT_COMPARABLE_HISTORY'yi, Tam geçmişi yükle ile yeniden geçen tam referansı doğrula. Ham seri/imleç/hizalama raporlarını reports/desktop-fixture-qa-20261109 altında ayrı JSON'lara, özeti reports/chart-desktop-fixture-20261109.md dosyasına yaz. Paket adlarını gerçek DOM'dan kaydet. Hata varsa kanıtla; boş veya eski timestamp'li ölçümü geçti sayma. Kullanıcı çizimlerine veya normal 8765 ayarlarına dokunma. 30 dakika/performance testi yapma.

Bu görev native seri/crosshair ve kontrollü boşluk çizimi için kabul kanıtı sağlayacak. Raster boyalı piksel analizi, native touch ve tüm W2/W3 kabulü ayrıca açık kalır; bot bağlantısı bekler.
