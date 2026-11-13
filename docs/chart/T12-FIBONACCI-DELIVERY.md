# T12 — ayarlanabilir Fibonacci ve extension

12 Kasım 2026. Tamamlandı; plan14/27. Sıradaki T13 lineer/log ölçek semantiği.

## Araç ve kullanım

Fibonacci araçları menüsünde Fibonacci ve Fibonacci extension bulunur; hızlı araç araması ve klasik F kısayolu korunur. İkisi iki noktalıdır. Yeni Fibonacci varsayılanları0/0.236/0.382/0.5/0.618/0.786/1; extension varsayılanları0/1/1.272/1.618/2/2.618. Extension üç noktalı projection değildir. Projection ayrı kind olarak DECLARED_ONLY/BLOCKED kalır; menüye uygulanmış araç olarak eklenmez.

Oran ayarlarında2–24 farklı oran kaydedilir; −10 ile10, en fazla12 ondalık basamak. Oranlar noktalı virgül veya yeni satırla ayrılır; ondalık nokta/virgül kabul edilir. Normalizasyon işaret/ön sıfır/son sıfırları sadeleştirir ve sayısal tekrarları reddeder. Oran sırası korunur. Retracement/extension hazır listeleri ve Noktaların yönünü ters çevir düğmesi form taslağını değiştirir; yalnız Kaydet ile saklanır.

Zaman kapsamı İki nokta arası, Sağa uzat veya Tüm zamanlar olarak seçilir. Sağa uzat, iki anchor'ın erken zamanından başlar; anchor yönü değiştirilince de sağ yönü korur. Kapsam hem SVG hem kanonik sorguda aynıdır. Geçmiş veya gelecekte sabit bir seviye göstermek fiyat tahmini değildir.

Grafik oran ve gösterim fiyatını, panel tam exact fiyat metnini gösterir. Sıkışan etiketler gizlenebilir; çizgi, hit-area, saklı oran ve fiyat değişmez. Uzun ondalıklar panelde kesilmez; gerekirse satır bölünür. Etiketler tutamaktan uzaklaştırılır. Pozitif fiyat üretmeyen oran saklanır, panelde açık unavailable olur ve SVG'de sıfıra zorlanarak çizilmez. Diğer geçerli seviyeler kullanılabilir. T07 stil/kilit/gizleme/zaman dilimi, kopya ve çoklu hareket davranışı korunur.

## Legacy ve kayıt sözleşmesi

Eski schema'sız fibonacci kayıtları aynı yedi sabit oran ve anchor anlamıyla kalır. Yalnız ad/fiyat düzenlemek sessiz geçiş yapmaz. Oranları özelleştir açık eylemi ve Kaydet, kaydı chart-fibonacci/1 biçimine yükseltir; undo aynı legacy geometriyi ve yedi çizgiyi geri getirir. Yeni çizimler chart-fibonacci/1 kullanır; kind fibonacci veya fibonacci_extension, levels decimal-text listesi ve time_scope zorunludur. Mevcut JSON revision store kullanılır; yeni DB migration gerekmez.

Frontend format_version=7 kullanır. v1–v6 listeleri yeni Fib geometrilerini dışarıda bırakır; tekil okuma/yazma/silme ve eski batch istemcileri yeni şemaya erişemez. Eski istemci legacy nesneyi yeni şemaya yükseltemez. Genel sözleşme ratios, geometry_schema ve TWO_ANCHOR_PRICE_INTERPOLATION anlamını gösterir. Tracking veya emir yetkisi oluşmaz. Çizim/revision seçimi değişirken önceki form taslağı uygulanamaz: editörün bağlam anahtarı hazırlanmadıysa kaydetme ve ayar kontrolleri kapalı kalır.

## Exact hesap

Seviye fiyatı=P0+(P1−P0)×r. Anchor sırası korunur; yön ters çevrilince aynı oran ters fiyat hareketine uygulanır. Python Fraction ve TS BigInt rational kullanılır; tick veya emir yuvarlaması yapılmaz. Örnek100.25→110.75 için0.236=102.728,1.618=117.239; ters yönde1.618=93.761. Bu değerlerin tick0.25'e oturması gerekmez. Mevcut tick politikası yalnız değiştirilmiş anchor giriş/sürükleme fiyatlarına uygulanır.

Kanonik level sorgusu yalnız kayıtta seçilmiş oranları kabul eder; decimal yazımları normalize edilir. Eski kayıtlar yalnız eski yedi oranı kabul eder. Scope dışı OUT_OF_SCOPE; seçilmemiş oran UNSUPPORTED_RATIO; sıfır/negatif sonuç NON_POSITIVE_LEVEL olur. Kanonik hash şema/kind, normalized oranlar, anchor'lar ve kapsamı kapsar. Sonuçlar exact fraction ve mümkünse exact decimal taşır. Görüntüde yuvarlanırsa≈ kullanılır; panel tam decimal metni gösterir. Henüz yalnız LINEAR anlamı desteklenir; log konusu T13'tür.

## Kabul

- **771 Python testi** geçti;7 yeni test exact extension/ters fiyat, oran normalizasyonu ve tekrar/hassasiyet/sınırları, legacy yedi oran, üç zaman kapsamı, nonpositive seviye ve tick'e yuvarlamama, promote/undo/restart/hash ve v7 API izolasyonunu kapsar.
- **199 frontend testi** geçti;5 yeni test oran parser, bağımsız Decimal referans, legacy/unavailable ayrımı, form/drag konfigürasyon korunması ve sıkışık etiketleri sınar. Mevcut Fibonacci hit-area ve değişmeyen viewport mutation testleri korunur. TypeScript ve üretim derlemesi başarılı. Ana JS yaklaşık524kB minified/167kB gzip; Vite500kB chunk uyarısı sürer. QA01 performans kabulü kapanmaz.
- **13 gerçek tarayıcı kontrolü** geçti: legacy başlangıç, iki gerçek pointer aracı, özel oran/off-tick fiyat, duplicate reddi, üç scope, açık reverse, gerçek tutamak, undo/redo, bütün çizim hareketi, dense label/hit-area, legacy rename/explicit promote/inverse, nonpositive extension ve server/page restart. Production App/HTTP, kontrollü piyasa verisi ve izole SQLite kullanıldı; kullanıcı DB'sine test çizimi yazılmadı. Page error0, dış istek0, hesap/emir API çağrısı0.
- T06/T04/T07/T05/G01/G06/G02/G03 **101 regresyon tarayıcı kontrolü** geçti. Açık/koyu ekranlar incelendi. Bu teslim tam TradingView paritesi, fiziksel GPU/touch veya canlı emir uygunluğu iddiası değildir.

Kanıt: reports/chart-t12-validation-20261112.json, chart-t12-dark/light-20261112.png; kaynak/derleme/test SHA256 manifesti reports/chart-t12-delivery-20261112.json.
