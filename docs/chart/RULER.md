# T03 — Fiyat-zaman cetveli

10 Kasım 2026. T03 TAMAMLANDI. Kalıcı cetvel oluşturma, düzenleme, sürükleme/tutamaç, kayıt/reload, undo/redo, 409 ve restart doğrulandı. 735 Python / 161 frontend testi, TypeScript/üretim derlemesi ve 11 gerçek üretim App kontrolü geçti. Sırada T04 long/short planlama vardır.

## Kullanım

Araç çubuğundaki ↔ Fiyat-zaman cetveli seçilir; grafikte iki ayrı nokta tıklanır. Noktaların fiyat farkı, yüzde değişim, tick farkı, yüklenmiş mum sayısı ve UTC süre görülür. Cetvel seçiliyken alt düzenleyicide tam değerler, sayısal fiyat/UTC zamanı ve ad düzenlenebilir. Çizgi veya tutamaç sürüklenebilir; Escape/pointer iptali kaydetmez. Silme, geri al/yinele ve reload mevcut revision mekanizmasını kullanır. Native motorun iki ayrı click olayı gerekir; kontrollü testte çift tıklama eşiği dışında iki tıklama kullanılır.

Fiyat/yüzde/tick farkları ilk anchor'dan ikinciye işaretlidir; zaman ters seçildiyse süre mutlak ve geriye etiketiyle sunulur. Aynı fiyat, aynı zaman ve tek noktada sıfır ölçüm geçerlidir. Başlangıç fiyatı sıfır/negatif olamaz. Sonlu olmayan yüzde/tick kesirleri tam numerator/denominator olarak gösterilir; örneğin 100/3%. Grafik üzerindeki çok uzun özet açık … ile kısalabilir; alt panel tam değeri verir. Sessiz yaklaşık fiyat üretilmez.

Mum sayısı iki zaman arasındaki dahil yüklenmiş bar açılışlarının sayısıdır. Ayrıca logical bar aralığı verilir: düzenli dizide 3 mum / 2 aralık. UTC süre gerçek saniye farkıdır. Örneğin 15m grid'de arada iki bar eksikse 1 saat / 3 yüklenmiş mum / 2 logical aralık ve 2 eksik mum ayrı görünür. Kesirli zamanlarda interval değeri rasyonel olabilir; beklenen eksik bucket sayısı yalnız ölçüm zaman penceresinde hesaplanır. Gerekli geçmiş yoksa bar sayısı tahmin edilmez; fiyat/yüzde/tick ve süre gösterilebilir.

Kalıcı anchor'lar mutlak UTC/fiyat ve sembole bağlıdır; interval kaydedilmez veya workspace'ten bot bağı türetilmez. Seçili timeframe grid'i mum sayısını değiştirir. Kabulte aynı 5 saatlik ölçüm 15m grafikte 21 mum / 20 aralık, 1h grafikte 6 mum / 5 aralık verdi. Market geçişinde başka sembolün ölçümü karışmaz.

## Sürümlü şema ve uyumluluk

Yeni ruler geometry mevcut beş ortak alanın yanında zorunlu schema=chart-ruler/1 taşır. kind=ruler, iki anchor, pozitif kesin ondalık fiyat ve UTC saniye zamanları gerekir. Bilinmeyen/eksik şema ve fazladan alan reddedilir. Ruler fiyatları P1 sonlu/pozitif ve büyüklük sınırlarından geçer; üssüz fiyat metni en fazla 64 karakterdir. Bilimsel gösterim kayıtta açılır; normal fiyatların trailing zero biçimi korunabilir. Eski horizontal/zone/trend/Fib strict alanları ve anlamları değişmedi.

SQLite JSON geometry alanı yeni açık sürümü saklar; eski kayıtları yeniden yazan DB migration yoktur. Yeni frontend liste okumasında format_version=2 seçer. Varsayılan v1 liste yalnız dört eski türü döndürür; böylece eski renderer cetveli Fibonacci gibi yorumlamaz. Cetvel POST'u zorunlu kendi şemasıyla açık yazma niyetidir. Cetvelin show/PATCH/DELETE yolları format_version=2 ister; aksi durumda DRAWING_FORMAT_VERSION_REQUIRED döner. Eski türlerin yolları çalışmaya devam eder. Aynı request_id/idempotency ve expected_revision korunur; undo eski türü dönüştürmez.

Registry'de ruler readable/editable/computable ve measurement sorgusu olarak açıldı; write_schema chart-ruler/1, gerekli bağlam tick_size/loaded_bar_grid/interval'dir. Sözleşme projeksiyonunda origin CHART_RULER_V1 olur. Görünüm timeframe'i işlem veya izleme yetkisi değildir.

## Kesin hesap

Backend drawings.calculations.measure_ruler ve query(...,'measurement',tick_size=...,times=...,interval=...) saf offline işlevlerdir. Frontend ruler.ts aynı sözleşmeyi bağımsız BigInt/rational aritmetik ile uygular. Sonuç chart-ruler-measurement/1; her fiyat/yüzde/tick/aralık exact rational ve mümkünse sonlu decimal taşır. Delta=p1-p0, yüzde=100*delta/p0, tick=delta/tick_size. Tick farkı emir miktarı/fiyatı değildir ve zorla tam sayıya yuvarlanmaz. Log ölçek şu aşamada desteklenmez.

Grid 1–4000 artan/tekil ve doğru interval bucket'ında UTC saniye ister; haftalık hizası Pazartesi UTC'dir. Boş grid geçmiş yok anlamında üst tüketicide null ile sunulur. Aralık dışındaki anchor için GRID_OUT_OF_RANGE ile bar bilgisi UNAVAILABLE; düzensiz sıralama/bucket ve bozuk tick açık hata olur. Boşluklu grid ölçümde GAPPED ve eksik bucket sayısını verir; bu bilgi canlı bot uygunluğu sağlamaz. P2/P3 kanıtı veya P4/P5 yetkisi yerine kullanılmaz; live_eligible/order_authority false kalır.

## Doğrulama

12 bağımsız sabit fixture: yükseliş, ters/düşüş, sabit fiyat, dikey, sıfır nokta, gap, kesirli anchor+gap, eksik/range dışı geçmiş, 2^53 üstü fiyat, micro fiyat ve tekrar eden yüzde. Düşük Decimal context dahil Python/TS sonuçları aynı. 6 yeni Python testi schema/limit, API v1/v2, kayıt/409/undo/restart, timeframe ve negatif girdileri kapsar. 8 yeni frontend testi hesap/panel/drag/cancel/girdi davranışını kapsar.

Gerçek Chromium ve izole FastAPI/SQLite testinde iki tıklama, native tutamaç sürükleme, sayısal edit, undo/redo, delete/undo, ikinci sekmede 409, market ve timeframe geçişi, sayfa/sunucu restart'ı 11 kontrolle geçti. Kullanıcı workspace'i kullanılmadı; test verisi geçici depodadır. İlk harness denemelerinde WebSocket hazır olma beklemesi, sentetik pakette eksik market.tick_size ve çift tıklama aralığı düzeltildi; ilk rapor korundu. Nihai screenshot ayrıca incelendi. Fiziksel trackpad/touch ve 30 dakika performans kabulü tekrar edilmedi.

Kanıt: reports/chart-t03-validation-20261110.json; Python/frontend/build logları; chart-t03-browser-20261110.json ve chart-t03-ruler-20261110.png. Güncel üretim bundle index-CnNqyIFz.js. Önceki aday02 arşivi değişmedi. Canlı hesap/emir/mesaj veya kullanıcı çizim kaydı oluşturulmadı. Çalışan grafik yeni backend sürümündedir; frontend cetvel düğmesini görmek için sayfayı yenilemek gerekir.
