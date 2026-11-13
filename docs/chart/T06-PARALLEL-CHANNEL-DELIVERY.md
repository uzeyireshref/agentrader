# T06 — paralel kanal

12 Kasım 2026. Tamamlandı; plan13/27. Sıradaki T12 ayarlanabilir Fibonacci ve extension.

## Kullanım ve kapsam

Çizgi araçları → Paralel kanal veya araç araması. İlk iki tıklama temel çizgiyi, üçüncü tıklama paralel sınırı belirler. Üçüncü nokta ilk iki noktanın zaman aralığında olmalıdır. Temel noktaların zamanları farklı, kanal genişliği sıfırdan büyük ve iki sınır da pozitif olmalıdır. Aynı fiyatta iki temel nokta yatay kanal oluşturabilir. Ters temel yönü ve sınırın temel çizginin altında olması desteklenir.

Kanal ilk iki noktanın zaman aralığıyla sınırlıdır. İki sınır, kesikli orta çizgi ve saydam dolgu gösterilir. Her anchor bağımsız tutamakla düzenlenir; alanı sürüklemek üçünü birlikte taşır. Geçersiz/kollinear veya üçüncü noktayı aralık dışında bırakan hareket kaydedilmez. Form, tick, T07 kilit/gizleme/stil/zaman dilimi, çoklu seçim, çoğaltma ve grup geçmişi kullanılır. Kanal orta çizgisi ayrım için kesikli kalır.

Panel bitiş zamanındaki alt/orta/üst sınırı ve genişliği gösterir. İsteğe bağlı kontrol fiyatı aynı referans zamanında içeride/dışarıda ve sınıra mesafe verir; kontrol fiyatı kaydedilen geometriyi değiştirmez. Sınıra eşit fiyat içeride sayılır. Boş kontrol fiyatı0 değildir. Bu panel canlı sinyal veya emir oluşturmaz.

## Kesin hesap sözleşmesi

A=(ta,pa), B=(tb,pb), C=(tc,pc). m=(pb−pa)/(tb−ta), temel(t)=pa+m(t−ta), ofset=pc−temel(tc). İkinci sınır=temel+ofset; alt/üst sıralanır, orta=(alt+üst)/2, genişlik=üst−alt. Mesafe=max(alt−p,p−üst,0) fiyat birimindedir; piksel veya dik geometrik mesafe değildir. Üçüncü noktanın sıfır ofseti ve iki uçta pozitif olmayan sınır reddedilir.

Python Fraction ve TS BigInt rational aynı işlemleri kullanır. Grafik yalnız native koordinata dönüştürürken Number kullanır. boundsAt, contains ve distance sorguları açık UTC zamanı, kesintisiz doğrulanmış yüklü grid ve interval ister. Çekirdek yalnız LINEAR fiyat anlamını destekler. Kesintisiz gridde UTC eğimi ile logical-bar eğimi aynıdır; eksik gridde bu eşitlik varsayılmaz. Anchor dışı zaman OUT_OF_SCOPE, veri boşluğu GRID_GAP, yüklü geçmiş dışı anchor GRID_OUT_OF_RANGE olur. Sonuçlar exact numerator/denominator, mümkünse sonlu decimal içerir. Gösterimde yuvarlanan değerler≈ taşır. Kanonik hash grid/interval ve üç anchor'ı kapsar.

Veri geçerliliği projection cache anahtarına eklendi. Anchor koordinatları değişmeden, kanalın dışındaki bir veri boşluğu bütün grid kanıtını geçersiz kılarsa eski SVG ve tutamaklar gizlenir. Veri tamamlandığında tekrar görünür. Aynı güvence mevcut ray projeksiyonlarını da kapsar.

## Kayıt ve uyumluluk

chart-channel/1, kind=parallel_channel, üç anchor. Format_version=6 kullanılır. v1–v5 listeleri kanalı dışarıda bırakır; tekil okuma/yazma/silme ve eski batch yazımı reddedilir. Önceki araçların anlamı değişmez; mevcut JSON revision kaydı kullanıldığı için yeni DB migration gerekmez. Kontrat kategori=drawing, scope=BASE_ANCHOR_BOUNDED ve verified-grid bağlamını açıklar. Tracking aktivasyonu ve emir yetkisi yoktur.

## Kabul

- **764 Python testi** geçti;7 yeni kanal testi exact alt/üst/orta/genişlik, ters yön, negatif ofset, yatay kanal, sınır eşitliği ve fiyat mesafesi, degenerate/negatif sınır reddi, kapsam/grid engelleri, hash/revision/undo/restart ve v6 izolasyonunu kapsar.
- **194 frontend testi** geçti;5 matematik/form/drag testi ve1 React regresyonu eklendi. Native eşlenik6 kanal koordinatı,3 tutamak, anchor'ların dışındaki boşlukta koordinatlar aynı kalırken gizleme ve tekrar görünme sınandı. TypeScript ve üretim derlemesi geçti. Ana JS yaklaşık518kB minified/165kB gzip; mevcut Vite500kB chunk uyarısı sürer. QA01 performans/p95 kabulü bu teslimde kapanmaz.
- **12 gerçek tarayıcı kontrolü** geçti: dört farklı kanal geometrisi, ters yön/paralellik/native orta koordinat, inside/outside/mesafe, sıfır genişlik ve sayısal düzenleme, gerçek üçüncü tutamak, undo/redo, bütün kanal hareketi, boşluk/iyileşme, kilit ve server/page restart. Production App/HTTP ve izole SQLite, kontrollü piyasa verisi kullanıldı; kullanıcı DB'sine test çizimi eklenmedi. Page error0, dış istek0, hesap/emir API çağrısı0.
- T04/T07/T05/G01/G06/G02/G03 **89 regresyon tarayıcı kontrolü** geçti. Açık/koyu ekranlar incelendi. Fiziksel GPU/touch, uzun canlı ağ kesintisi veya tam TradingView paritesi iddiası yoktur.

Kanıt: reports/chart-t06-validation-20261112.json, chart-t06-dark/light-20261112.png; kaynak/derleme/test SHA256 manifesti reports/chart-t06-delivery-20261112.json.
