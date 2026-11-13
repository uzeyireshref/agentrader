# T11 — seanslı ve anchored VWAP

12 Kasım 2026. Tamamlandı; plan21/27. Sıradaki T14 çalışma alanı ve araç/gösterge şablonları.

## Kullanım

Göstergeler → Seans VWAP / Anchored VWAP. İkisi de fiyat panelinde, ayrı renk ve kalınlıkla çizilir. Varsayılan kapalıdır. Ayarlarda mum fiyat kaynağı, hesap modu ve stil kaydedilir. Anchored VWAP çapası **Veri paneli → Seçili mumdan Anchored VWAP** veya UTC tarih/saat alanından seçilir. Çapa, seçildiği sembolle birlikte saklanır; başka coinde otomatik bağlanmaz. Çapa mevcut zaman diliminin tam mum başlangıcına uymalıdır; sessiz snapping yapılmaz.

Veri penceresi her VWAP çıktısını ve seçili mumdaki unavailable nedenini ayrı gösterir. UTC seansı, kaydedilmiş sembol/çapa ve fiyat/hacim provenansı görünürdür. Açık mum değerleri güncellenebilirdir. VWAP bantları ve çapa sürükleme aracı bu teslimde yoktur.

## Hesap ve hacim provenansı

**Mum fiyatı × ham base hacmi:** varsayılan HLC3; OPEN/HIGH/LOW/CLOSE/HL2/HLC3/OHLC4 seçilebilir. VWAP=Σ(source×volume)/Σvolume. Tam sayısal kline hacmi kullanılır; K/M olarak kısaltılmış UI etiketleri girdiye dönüşmez. Bu mod bar fiyatı yaklaşımıdır ve farklı aggregation timeframe'lerinde aynı sonuç garanti edilmez.

**Native decimal quote/base oranı:** fiyat kaynağı quote_base olur ve seçimi kilitlenir. Σ(native quote_volume)/Σ(native base volume), Python Fraction ve TypeScript BigInt rasyonelleriyle toplanır. Son oran numerator/denominator olarak korunur; yalnız çizim/formatter sınırında Number'a çevrilir. Sidecar chart-exact-decimal/1, VERIFIED ve UPSTREAM_DECIMAL_TEXT olmalı; decimal metinler, sayısal projeksiyonlar ve sıfır hacim/quote tutarlılığı doğrulanır. Kanıt eksikse HLC3 veya float hacme geri düşülmez.

Her iki mod **mum/kline verisidir; gerçek trade VWAP iddiası yoktur**. Native decimal ratio hesap hassasiyetini korur; eksik, yanlış veya farklı kapsamlı upstream veri doğruluğunu tek başına kanıtlamaz. Canonical bot query, canlı uygunluk ve emir yetkisi açılmaz.

## Reset, çapa ve eksik veri

Seans UTC00:00'da sıfırlanır. İlk yüklü mum seans ortasındaysa eksik toplamdan VWAP üretilmez; tam seans başlangıcı history ile yüklenene veya sonraki UTC00:00'a kadar unavailable'dır. Bir günlük UTC seansına tam bölünen mevcut aralıklar1m…1d desteklenir;1w için açık uygulanamaz nedeni vardır. Günlük HLC3 seansı her barda sıfırlandığı için günlük HLC3'e eşittir; intraday bar VWAP ile aynı trade kapsamı gibi sunulmaz. Hesap zaman dilimi görüntü zaman dilimidir, yeniden örnekleme yapılmaz.

Anchored birikim tam çapa barında başlar; öncesi unavailable'dır. Çapa yüklü geçmişten önceyse eski mumlar yüklenmelidir. Başka sembol/uyumsuz grid/çapasız durumlar açık ayrı nedenlerdir. Çapa sonrası gap birikimi engeller; onarım veya yeni açık çapa seçimi gerekir. Seans modunda gap sonrası tam yeni UTC başlangıcı hesaplanabilir. Önceki tam seans çıktıları korunur.

Σvolume=0 ise değer yoktur,0 fiyat değildir. Pozitif birikime eklenen0-hacimli mum ortalamayı değiştirmez. Native base0/quote>0 veya base>0/quote0 exact modu engeller. Önceki kapanmış mum revizyonu, history prepend ve reconnect aynı ham diziden yeniden hesaplanır; tekrar gelen hacim bir daha toplanmaz.

## Çizgi boşlukları

Pinlenmiş Lightweight Charts5.2.1'in public data() çıktısı whitespace satırlarını çıkarır; renderer geçerli noktalar arasında köprü çizebilir. Yalnız whitespace gönderip gap çizilmiş sayılmadı. VWAP render adaptörü, unavailable bölgenin önündeki noktanın outgoing segmentini şeffaf yapar; yeni geçerli segment normal renginde devam eder. Onarımda renk geri gelir. Motor kaynağı yerel paketten incelendi, bridge/color davranışı test edildi. Hesap noktaları ile render whitespace ayrı tutulur. Sayısal VWAP'a sıfır/sentinel fiyat sokulmaz.

## Kalıcılık ve yetki

chart-indicators/4, `format_version=4`; dokuz kalıcı nesne. İlk yedi ayar/sürüm/revision aynen korunur.3/5/7 kayıt GET'te yazılmadan genişletilir; yeni VWAP'lar kapalıdır. V4 kaydedilince eski format1/2/3 yazması422 ile engellenir. Yeni fiziksel DB migration yoktur. Atomik revision, idempotent request ve kayıt yanıtı doğrulaması korunur.

Registry'de session_vwap/anchored_vwap display model ve source/mode/anchor/display_interval alanları tanımlıdır. Araç sayısı27 kalır; canonical_queries=[], tracking/order_authority=false. Bot/replay bağlamı fiyat kaynağı, ham hacim provenansı, calculation version, sembol, interval, seans/anchor ve open/closed durumunu taşımalıdır; P4–P7 yetki işleri ayrı kalır.

## Kabul

- **820 Python testi** geçti.11 yeni grup: Decimal referanslı günlük reset/birikim; iki modda0 hacim; partial session/gap/history repair; sembol/grid/anchor kapsamı; float projeksiyondan farklı native rational oran; kanıtsız/inconsistent volume reddi; günlük/haftalık ve günler arası anchor; v4 validation/migration/persistence; gerçek HTTP/format izolasyonu; paylaşılan fixture güncelliği; registry yetki sınırı.
- **252 frontend testi** geçti.11 yeni test: **33 ortak fixture** ile kaynak/seans/çapa/gap/zero/exact ratio; projection ötesi rational metinler; session başlangıcı; whitespace writer; quote proof ve sembol kapsamı; strict v4; reconnect/prepend determinismi; motorun outgoing bridge adaptörü; Data window neden/provenans; seçili mumdan anchor eylemi. Önceki bütün testler korunur.
- TypeScript/üretim derlemesi geçti. Ana JS565.32kB, gzip179.84kB. Mevcut500kB uyarısı ve QA01 performans/p95 kabulü açık kalır.
- **19 yeni üretim App tarayıcı kontrolü** geçti: default/çapasız neden; native output parity; seçili UTC mumdan kayıt; America/New_York tarayıcı saatinde UTC formu; off-grid anchor reddi; yeni UTC seansında0 hacim ve başka coine ait anchor; pozitif toplam/yeniden bağlama;0 hacimde ortalamanın korunması; native exact kaynak/provenans; kanıt bozulmasında değer ve bridge kaldırma; onarım; history öncesi çapa; **gerçek pagination ile anchor geçmişinin tamamlanması**; **aynı sayfada WebSocket close/reconnect ve tekrar snapshot**;20 çift-VWAP aç/kapa döngüsü; stil; page reload;1024px açık/koyu form; server restart.
- G02/G03/T08 için **39 ilgili regresyon tarayıcı kontrolü** geçti. Sentetik public piyasa ve izole SQLite kullanıldı; kullanıcı DB'sine test ayarı yazılmadı. Page error0, dış/hesap/emir çağrısı0. Açık/koyu ekranlar incelendi. Fiziksel GPU/touch ve canlı vendor parity kabulü yoktur.

Kanıt: `reports/chart-t11-validation-20261112.json`, `reports/t11-*.log`, `chart-t11-*.png`, SHA256 manifesti `reports/chart-t11-delivery-20261112.json`. [V4 sözleşmesi](contracts/indicators-v4.json). Önceki teslimler tarihsel kalır.
