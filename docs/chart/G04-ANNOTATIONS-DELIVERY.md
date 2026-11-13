# G04 — metin, not ve bağlı fiyat etiketi

12 Kasım 2026. Tamamlandı; plan16/27. Sıradaki T08 zaman dilimleri ve üst-zaman bağlamı.

## Kullanım

Sol rail’de Açıklama araçları → Metin / Not / Fiyat etiketi veya araç araması. Grafik odaktayken A/N/P kısayolları aynı araçları seçer. Bir fiyat/mum noktasına tıklamak tek anchor'lı nesne oluşturur ve Çizimler panelini açar. Metin/not editörü panelin başında yer alır; Metni kaydet, bütün form taslağını kayıt protokolüyle saklar. Sayısal fiyat/zaman ve ad düzenlemesi için mevcut form da kullanılabilir. Metin alanında A/N/P yazmak araç değiştirmez.

Metin hafif arka planla, not kart/bağlantı çizgisiyle, fiyat etiketi isteğe bağlı başlık ve kayıtlı anchor fiyatıyla gösterilir. Fiyat etiketi son piyasa fiyatını takip etmez; bağlı noktadaki exact fiyatı gösterir. Başlık metni fiyat alanını değiştirmez. Kartın gerçek hit alanından veya tek anchor tutamağından taşıma, zaman/fiyatı mevcut tick politikasıyla değiştirir; gövde korunur. Undo/redo, kopya ve server/page restart gövde, anchor ve özellikleri korur.

T07 kilit/gizleme/zaman dilimi ve renk/stil yönetimi kullanılır. Kilit gövde/fiyat düzenlemesini, taşıma ve silmeyi engeller; gizleme ve kilidi açma ayrı kalır. Kopya yeni, kilitsiz kimlik alır; gizli durumunu koruyabilir. T13 gereği log görünümde açıklama anchor'ı native fiyat koordinatına yansır, kayıt değişmez; pointer taşıma kapalı, sayısal form kullanılabilir.

## Metin ve yerleşim

Text/note en fazla8 satır, toplam1000 Unicode karakter ve satır başına256 karakter kabul eder. Fiyat etiketi başlığı isteğe bağlıdır; tek kayıt satırı ve80 karakterle sınırlıdır. CRLF/CR, LF'ye normalize edilir; NUL ve desteklenmeyen kontrol karakterleri reddedilir. Frontend karakter sayımı backend Unicode kod noktası sayımıyla uyumludur; emoji UTF16 uzunluğundan dolayı yanlışlıkla iki karakter sayılmaz.

Gövde plain text olarak SVG tspan/textContent ile yazılır; HTML/Markdown çalıştırılmaz. Unicode, emoji, açık satır sonu ve yazılmış markup metin olarak korunur. Canvas ölçümüyle grafikte satır sarılır. En fazla12 görsel satır veya pane'in izin verdiği daha az satır çizilir; kalan bölüm… ile belirtilir. Tam gövde kayıtta, editörde, SVG title ve erişilebilir isimde kalır. Bir glyph'in surrogate çifti kesilmez.

Kutular anchor'a yakın konumlanır ve görünen pane içine sığdırılır; bağlantı çizgisi gerçek anchor'ı gösterir. Anchor görünür alanın dışındaysa kart gizlenir; köşeye sabitlenip yanlış bir konum izlenimi verilmez. Yeniden görünür alana gelince gövde korunarak çizilir. Metin yerleşimi gövde/fiyat/kullanılabilir boyut anahtarıyla önbelleğe alınır; her pan frame'inde uzun not yeniden ölçülmez. Font/boyut bu sürümde12px Arial olarak sabittir.

## Sözleşme ve yetki sınırı

chart-annotation/1; kind=text/note/price_label, tek UTC/decimal-price anchor, text ve kısa label. Format_version=8 kullanılır; v1–v7 listeleri açıklamaları dışarıda bırakır ve eski istemciler tekil okuma/yazma/silme veya batch değişimi yapamaz. Yeni DB migration gerekmez; mevcut JSON revision store kullanılır. Eski araçların anlamı korunur.

Registry25 araç içerir;3 yeni nesne annotation kategorisindedir. Readable/editable=true, computable=false, canonical_queries=[], calculation_state=DISPLAY_ONLY. Tracking activation ve order authority=false. Kontrat UTC_PRICE_ANCHOR, ANCHOR_POINT, NOT_BOUND_TO_INTERVAL ve DISPLAY_ONLY bot kullanımını açıklar. price_label bilgi amaçlıdır; yatay seviye/rule nesnesine dönüşmez. Canonical query/hash işlemleri DISPLAY_ONLY_ANNOTATION ile engellenir. Piyasa/anchor görüntü koordinatı, otomatik işlem fiyat hesabı sayılmaz.

## Kabul

- **782 Python testi** geçti;7 yeni test Unicode/satır normalizasyonu, markup korunması, limit/schema/tek anchor, salt görsel registry/query sınırı, revision/undo/kopya/restart, kilit ve v8 read/write/delete/batch izolasyonunu kapsar.
- **214 frontend testi** geçti;8 yeni test Unicode sınırı, sarma/kısaltma ve gövde korunması, exact fiyat etiketi, tek nokta form/drag, üç güvenli SVG glyph/hit alanı ve ekran dışı anchor davranışını sınar. TypeScript/üretim derlemesi başarılı. Ana JS yaklaşık533kB minified/169kB gzip; mevcut Vite500kB chunk uyarısı sürer. QA01 performans/p95 işi kapanmaz.
- **14 gerçek production App tarayıcı kontrolü** geçti: üç gerçek tek tıklama, çok satırlı Unicode ve markup'ın çalışmaması, uzun gövde/truncation/title,9.satır reddi, caption/anchor ayrımı, kart hit testi, tek fiyat tutamağı, undo/redo, üç kısayol ve editör key guard, kilit/gizle, kopya ve açık bot yetki sınırı, log native koordinat ve server/page restart.
- T13/T12/T06/T04/T07/T05/G01/G06/G02/G03 **128 regresyon tarayıcı kontrolü** geçti. Kontrollü piyasa verisi ve izole SQLite kullanıldı; kullanıcı DB'sine test çizimi yazılmadı. Page error0, dış istek0, hesap/emir API çağrısı0. Açık/koyu ürün ekranları incelendi. Fiziksel touch/GPU veya tam TradingView annotation paritesi iddiası yoktur.

Kanıt: reports/chart-g04-validation-20261112.json, chart-g04-dark/light-20261112.png; kaynak/derleme/test SHA256 manifesti reports/chart-g04-delivery-20261112.json.
