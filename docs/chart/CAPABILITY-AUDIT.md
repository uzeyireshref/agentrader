# Grafik yetenek denetimi ve önerilen asgari araç seti

**Takip kararı:** Kullanıcı temel araç kapsamını onayladı ve plan yenilendi. Aktif sıra [PLAN.md](PLAN.md), makine okunur karşılık contracts/chart-core-plan-v2.json. Aşağıdaki “öneri/henüz onaylanmadı” ifadeleri denetimin yazıldığı anı anlatır.

10 Kasım 2026. Kapsam: kaynak kod ve proje sözleşmeleri; yeni görünür tarayıcı testi yapılmadı. Tasarım değerlendirmesi ve P2 uygulaması bu tur yapılmadı. Bu bir öneridir; mevcut P2–P7 planı yerine geçirilmiş/onaylanmış yeni bir uygulama planı değildir.

## Sonuç

Grafik güvenilirliği üzerinde çalışılmış, fakat araç kapsamı sınırlı bir web terminalidir. Temel destek/direnç, bölge, trend segmenti ve Fibonacci çizmek; hacim/EMA/RSI görmek için yeterli. Kullanıcının tarif ettiği geniş temel analiz ve botla aynı hesap üzerinden çalışma hedefi için henüz yeterli değil. "Basit" görünmesinin bir kısmı arayüzden, somut bir kısmı eksik işlevlerden geliyor. Daha çok süs veya onlarca gösterge yerine aşağıdaki çekirdek araçları tamamlamak gerekir. 24/25 görev sayısı önceki geliştirme/kabul planına aittir; ürünün gerekli tüm araçlara sahip olduğunun ölçüsü değildir.

## Bugün gerçekten var

- Binance USD-M USDT perpetual katalog, canlı/history mum ve hacim; coin seçimi; 15m/1h/4h/1d/1w.
- OHLC okuma, zoom/pan, otomatik/manuel fiyat ölçeği, son muma dönüş, reset, klavye ve Fullscreen API.
- Yatay çizgi, iki anchor fiyat bölgesi, trend segmenti, sabit seviyeli Fibonacci; seçme, sürükleme/tutamaç, OHLC mıknatıs, isim/fiyat/UTC düzenleme.
- Sunucuda sürümlü kayıt, undo/redo, çatışma/retry ve iki sekme tutarlılığı için kontrollü kanıtlar.
- EMA20/50, RSI14 ve hacim. P1 kesin ondalık OHLC/hacim/tick sidecar; legacy float kesinlik sayılmaz.

B5 masaüstü görünür klavye/tam ekran tekrarının kalan kısmı kullanıcı isteğiyle ertelendi. Dokunmatik kullanıcı onayıyla ayrı açık iş. Otomatik sayısal/raster kanıt, tamamlanmamış görünür kabul yerine geçmez.

## Özellik matrisi

### F01 — Fiyat/zaman ölçüm aracı

Durum: YOK. Öncelik: ÇEKİRDEK.

İki nokta arasında fiyat farkı, yüzde, tick, mum sayısı ve UTC süresi; mum sayısı ile geçen zaman ayrı.

Bot koşulu: Aynı girdiden aynı Decimal sonuç; ekrandaki yuvarlama ayrı.

### F02 — Long/short işlem planı

Durum: GRAFİKTE YOK. Öncelik: ÇEKİRDEK.

Yön, entry/stop/target, R:R, yüzde/tick mesafeleri; isteğe bağlı risk bütçesiyle teorik qty. Ücret/kayma varsayımları açık.

Bot koşulu: Kaydedilmiş plan revision okur. Araç çizmek emir yetkisi veya aktivasyon değildir. Eski yürütme çekirdeği ayrı.

### F03 — Trend uzatma/yatay ray/paralel kanal

Durum: Yalnız yatay çizgi ve iki noktalı trend segmenti. Öncelik: ÇEKİRDEK.

Segment/ray/sağa-sola uzatma açık enum; kanal üçüncü anchor/offset ile tanımlı.

Bot koşulu: Zaman kapsamı ve bar-grid semantiği açık; sonsuz uzatma kendiliğinden varsayılmaz.

### F04 — Çizim yönetimi ve zaman kapsamı

Durum: Kayıt, revision, undo/redo, liste, isim, fiyat/UTC düzenleme VAR; lock/hide/duplicate/visibility politikası YOK. Öncelik: ÇEKİRDEK.

Kilitle, gizle/göster, çoğalt, seçili zaman dilimlerinde görünürlük, zaman sınırlı/sınırsız bölge.

Bot koşulu: Gizleme yalnız görünüm; kilit düzenleme içindir; botu duraklatma ayrı komut. Görünürlük timeframe ile binding timeframe ayrıdır.

### F05 — Ayarlanabilir gösterge altyapısı

Durum: Sabit EMA20/50 ve RSI14; hacim VAR. Öncelik: ÇEKİRDEK.

Kalıcı indicator_id/revision, tür/periyot/kaynak/smoothing/anchor, panel/renk ayarı; preset kaydı.

Bot koşulu: Aynı geçmiş, seed/warmup, açık/kapalı mum ve formül sürümüyle referans parity; bugün TS ve eski Python hesapları tek kanonik motor değil.

### F06 — SMA/ATR/VWAP

Durum: Grafikte YOK; eski bağımsız Python analysis.py içinde ATR VAR. Öncelik: ÇEKİRDEKTE ÖNERİLEN HESAP SETİ.

Ayarlı SMA/EMA/RSI; ATR ve seanslı/anchored VWAP. Seans UTC reset ve anchor kuralı açık; mum tabanlı VWAP seçilen fiyat kaynağına bağlı, trade VWAP eşitliği iddia edilmez.

Bot koşulu: ATR smoothing ve warmup; VWAP fiyat/hacim kaynağı, anchor/reset ve eksik veri davranışı sözleşmeli.

### F07 — Zaman dilimleri ve çoklu zaman dilimi bağlamı

Durum: 15m/1h/4h/1d/1w. Öncelik: ÇEKİRDEK.

En az 1m/5m/30m ekleme; 2h/12h ihtiyaca göre. Eşzamanlı çoklu pencere sonraya kalabilir.

Bot koşulu: Kaynak, resample/bucket, kapanmış üst-zaman mumu ve warmup doğrulanır; gelecekteki üst-zaman kapanışı geçmişe sızmaz.

### F08 — Fibonacci ayarları/uzatmaları

Durum: 0–1 arası yedi sabit retracement seviyesi. Öncelik: ÇEKİRDEĞİ TAMAMLAMA.

Seviye listesini ve yönü kaydet; isteğe bağlı extension seviyeleri ve ayrı üç noktalı projection türü.

Bot koşulu: Oranlar Decimal metin, anchor sırası ve pencere açık; extension ile üç noktalı projection aynı araç sayılmaz.

### F09 — Lineer/log ölçek

Durum: Varsayılan lineer; kullanıcıya log modu sunulmuyor. Öncelik: ÇEKİRDEĞİ TAMAMLAMA.

Özellikle geniş fiyat aralığında log görünüm; geometri semantiğiyle birlikte.

Bot koşulu: Yatay/anchor fiyatı korunur; düz trendin lineer fiyat mı log-fiyat interpolasyonu mu olduğu açık sürümlenir. Sadece ekseni değiştirip aynı bot sonucunu varsayma.

### F10 — Kural/uyarı bağı ve replay

Durum: E3/E4 TASARIM; motor YOK. Öncelik: BOT ÖNCESİ ZORUNLU.

Approach/touch/close-cross, direction/tolerance, closed candle profili, rearm ve kalıcı dedup; sonra revision-bound replay.

Bot koşulu: P2–P7 kanıtları tamamlanmalı; UI LIVE tek başına yeterli değil. OHLC ilk dokunma veya stop/target sırası vermez.

### F11 — MACD/Bollinger, metin/dikey işaret, şablonlar

Durum: Grafikte YOK. Öncelik: İKİNCİ DALGA.

Kullanılacak strateji gerektiriyorsa ekle; not/dikey işaret ve workspace preset kullanımını kolaylaştırır.

Bot koşulu: Görsel not talimat değildir; yalnız açıkça desteklenen hesap türleri ve sürümler değerlendirilir.

### F12 — Volume profile/orderflow/footprint/özel script

Durum: Grafikte YOK. Öncelik: ŞİMDİ ZORUNLU DEĞİL.

Hedef strateji gerekçesi ve uygun veri kaynağı oluşunca.

Bot koşulu: Mevcut OHLCV ile gerçek price-level hacim veya işlem sırası uydurulamaz.

## Bot açısından en önemli mimari fark

Bugün çizim nesnesinin veri olarak kaydedilmesi hazırdır; botun canlı olarak okuyup anlamlandırması ve kullanması hazır değildir. DrawingService tracking=NOT_IMPLEMENTED döndürüyor. Görsel tanım, izleme kuralı ve işlem yetkisi ayrı nesnelerdir.

Her araç için sürümlü bir yetenek kaydı gerekir: kind/schema, anchor ve parametreler, piyasa/timeframe kimliği, zaman kapsamı, fiyat kaynağı, formül/grid sürümü, desteklenen sorgular (priceAt, contains, distance, level gibi) ve açık capability listesi. Desteklenmeyen araçta bot BLOCKED_UNSUPPORTED_TOOL vermeli; benzer araca sessiz dönüşüm yapmamalı. Bot "kullanmak" ile çizim oluşturup/değiştirmeyi de kapsayacaksa ayrı owner-scoped komut yetkisi, expected revision, audit ve açık aktivasyon gerekir. Okuma/hesaplama, düzenleme, bildirim ve emir birbirinin yetkisi değildir.

Grafik renderer'ı koordinat gösterebilir; kanonik hesap motoru Decimal/rational anlamı üretir. Bot ve UI sonuçları aynı sabit test girdileriyle karşılaştırılır. Her ikisini aynı dilde yazmak şart değil; bağımsız uygulamalar varsa parity testleri zorunlu. Mevcut frontend göstergeleri float, eski analysis.py ayrı implementasyon; P1 yalnız taşıma kesinliğini çözdü. Sürüklemede roundPrice(Number(...)) ve Fibonacci'de Number hesabı bulunuyor; bu görüntü/etkileşim hesapları kanonik bot fiyatı gibi kullanılmamalı. Formdan kesin düzenleme daha güçlü olsa da tüm girdi yollarının tick/precision davranışı birlikte ele alınmalı.

Önemli iki geometri sınırı: timeToLogical yüklü aralığın dışında mevcutta görsel extrapolation yapabiliyor; E3 bot sözleşmesi grid kanıtı olmadan bunu reddetmeyi planlıyor. Bu ayrım uygulamada açık hale getirilmeli. Lineer ekrandaki düz trend ile log ekrandaki düz trend aynı fiyat fonksiyonu olmayabilir; log görünümü yalnız kozmetik değişiklik değildir. Bölge bugün iki farklı zaman ve fiyat ister; yatay kanal veya zaman sınırsız zone bu modele kendiliğinden eklenemez.

## Önerdiğim sıra

1. Bu denetimden onaylı asgari özellik/capability matrisi çıkar. Mevcut dört aracı da aynı sözleşmeye dahil et; her yeni araç kayıt/edit/undo/timeframe/parity koşullarıyla tanımlansın.
2. P2–P3 saat, akış ve veri kanıtlarını sürdür; bunlar mevcut ve yeni araçların ortak temelidir.
3. İlk araç paketi: fiyat-zaman cetveli + long/short risk planı; ardından uzatma/ray/kanal ve çizim yönetimi. UI ve kanonik backend hesapları aynı pakette doğrulansın.
4. Kalıcı ayarlı gösterge modeli + SMA/EMA/RSI/ATR/VWAP; gerekli kısa timeframe'ler, Fib ayarları ve log semantiği. Kullanıcı ihtiyacına göre gruplar daha küçük teslimlere ayrılır.
5. P4–P7 revision bağı, uygunluk, kalıcı olay ve izole replay ile araç-bot eşleşmesini gerçekten test et. Bot hesabı/çizim düzenlemesi/bildirim/emir ayrı kapsam ve yetkilerle kalır.
6. Sonra ikinci dalga araçlar ve tasarım; fiziksel kabul açıklarını da yayın kapsamına göre kapat.

Bu sıra "her araç bitmeden veri güvenilirliğine dokunma" anlamına gelmez. Önce ortak sözleşme, ardından veri temeliyle kontrollü araç genişlemesi hedeflenir. Bu tur yalnız denetim kaydedildi; yeni araç uygulanmadı ve P2 başlatılmadı.

## Başarı ölçütü

Her çekirdek araç fareyle çizilebilir, sayısal düzenlenebilir, kaydedilip yeniden açılır, undo/redo ve market geçişinde bozulmaz; bot aynı tanımdan aynı fiyat/seviye/mesafe sonucunu üretir. History/gap/resize/log/reconnect/revision değişiminde anlam değişirse açık sürüm veya BLOCKED sonucu olur. Hatalı/eksik veri uygunmuş gibi sunulmaz. Bu koşulların hepsi sağlanmadan yalnız toolbar ikonu eklenmesi tamamlanma sayılmaz.

## Kaynaklar ve inceleme kanıtı

Kod: frontend/src/drawings.ts, DrawingLayer.tsx, DrawingPanel.tsx, editGeometry.ts, indicators.ts, types.ts, drag.ts; agentrader/drawings/service.py, chart_precision.py, analysis.py. Eski analysis.py ATR varlığı grafikte entegre ATR varlığı anlamına gelmez.

Karşılaştırma yalnız araçların işlevini doğrular; hangilerinin bizim için öncelikli olduğu proje hedefinden yapılan mühendislik değerlendirmesidir:

- [TradingView çizim araçları](https://www.tradingview.com/support/solutions/43000703396-drawing-tools-available-on-tradingview/)
- [Long/short ölçümleri](https://www.tradingview.com/support/solutions/43000475660-how-to-use-long-and-short-position-drawing-tools/)
- [ATR formülü ve smoothing](https://www.tradingview.com/support/solutions/43000501823-average-true-range-atr/)
- [Anchored VWAP](https://www.tradingview.com/support/solutions/43000669764-anchored-vwap-drawing-tool/)
