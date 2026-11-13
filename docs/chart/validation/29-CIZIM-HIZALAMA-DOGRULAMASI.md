# Çizim hizalamasının sayısal kontrolü

9 Kasım 2026. Öncelik veri/çizim doğruluğu. Bu tur gezinme arayüzü yeniden tasarlanmadı; bot bağlanmadı.

## Eklenen kontrol

?diagnostics=1 URL'sindeki Çizim hizalama kontrolü panelinde Hizalamayı ölç düğmesi var. Ölçüm iki rAF sonrası mevcut DOM/SVG konumlarını okur; sürekli döngü çalıştırmaz.

Referans, çizim üretimindeki timeToLogical fonksiyonunu kullanmaz. Tam mum zamanında motorun native timeToCoordinate çıktısını alır. Ara zamanda mevcut mumlar arasında ayrı doğrusal tarama ve native x noktalarıyla interpolasyon yapar. Yüklü geçmiş dışına extrapolation yapıp geçti demez. Y için native priceToCoordinate, SVG ile ana pane canvas'ının getBoundingClientRect farkı da konumsal başlangıç referansıdır.

Kontroller: trendin iki ucu; bölgenin normalize iki köşesi; yatay çizginin iki kenarı; Fibonacci'nin yedi seviyesinin iki ucu. Beklenen nokta pane dışındaysa skipped; görünür beklenen noktanın SVG öğesi eksik/gizliyse failed. Eşik 1 CSS piksel Öklid uzaklığıdır. Hiç nokta ölçülmezse NOT_MEASURED; yalnız kontrol edilen noktalar geçerse CHECKED_POINTS_PASSED; skipped/unchecked sayıları korunur. Bu etiket bütün çizimlerin veya bütün grafiğin kabulü değildir.

Motor API koordinatları + SVG attributes/DOM başlangıçlarının karşılaştırılmasıdır; Canvas raster'ındaki boyalı piksellerin bağımsız görüntü analizi değildir. Fiyat referansı aynı motorun priceToCoordinate fonksiyonuna bağlıdır. DPR bilgisi raporlanır; fiziksel pixel hedefi olarak sunulmaz. Native time/price API'nin matematiksel doğruluğunu tek başına ispatlamaz.

## Doğrulama

75 frontend testi ve TypeScript/Vite derlemesi geçti. Sekiz yeni test: native exact/gap referansı; 2 CSS px sapmanın yakalanması; canvas/overlay origin farkı; gizli/eksik geometri reddi; geçmiş dışının unchecked olması; ters köşeli bölge; yatay çizgi ve Fibonacci iki uç kontrolü; panel düğmesiyle başarılı ve eksik öğe raporu üretme. jsdom/chart test doubles gerçek raster veya native touch kabulü değildir.

Backend bu tur değişmedi; önceki 667 Python sonucu tekrar koşulmadı. Yeni bundle index-Dnr66BvD.js, CSS index-CbnKi4Zg.css. Anahtarsız yerel çizim akışı sürer.

## Masaüstünde yapılacak kısa doğruluk görevi

> docs/chart/validation/29-CIZIM-HIZALAMA-DOGRULAMASI.md dosyasını oku. Kod değiştirme. Önceki QA veritabanlarının yeni kopyasıyla izole yerel sunucu aç; artık çizimler için anahtar gerekmiyor. ?diagnostics=1 ile index-Dnr66BvD.js paketini doğrula. Yatay, bölge, trend ve Fibonacci test çizimlerini görünür konuma getir. Her değişiklikten sonra Hizalamayı ölç düğmesine basıp ham raporu desteklenen DOM textContent okumasından kaydet: başlangıç, zoom-in/out, yatay pan, fiyat ekseni ölçeği, fiyat/hacim/RSI pane resize, 15m→1h→4h→15m ve geçmiş ekleme. Her türün en az bir görünür referansını ölç; skipped/unchecked noktaları geçti sayma. Ters sırada oluşturulmuş trend/Fibonacci ve iki mum arasındaki UTC ankraj zamanı örneğini de mevcut UI UTC editörüyle dene. Native referansın bulunmadığı veya canvas referansı seçilemediği durumda NOT_MEASURED'i sakla, sonucu başarılı varsayma. En az bir normal ve bir farklı DPR görünümünü araç destekliyorsa uygula; ölçülen boyutu/DPR'yi raporla. Her senaryonun ham JSON'unu reports/desktop-alignment-qa-20261109/ altında ayrı isimle, özeti reports/chart-desktop-alignment-20261109.md içine yaz. Her koşulda checked_points, failed_drawings, max_error_px ve skipped kapsamını belirt; fail varsa ekran kanıtı al ve dönüşümlerin sırasını kaydet. Kullanıcı 8765 sunucusu/verisini değiştirme. İzole sunucuyu sonunda kapat. 30 dakikalık canlı veya 60 saniyelik performans testi tekrarlama.

Bu görev sonrasında G02'nin native motor koordinatlarına karşı sayısal hizalama kapsamı değerlendirilecek. Raster eşleştirme, native dokunma ve ekrandaki gösterge fixture karşılaştırması ayrı açık maddeler olarak kalır.
