# Geniş canlı tur: ATR, RSI, VWAP ve zaman aralıkları

11 Kasım2026, Asia/Baku. REA03 araştırması; uygulama geliştirmesi başlamadı. İşlev, menü, sayısal çıktı ve tasarım birlikte incelendi. Geçici ATR/RSI/VWAP sırayla kullanıldı; önceki dört çizim korunup global gizli tutuldu. Tur sonunda BTCUSDT.P/1D/UTC, Volume+BB20/SMA/close/2/offset0 geri getirildi ve saved doğrulandı.

Kanıt paketi: reports/rea-chart/rea-evidence-atr-rsi-vwap-20261111.json; bu MCP oturumunun51 kaydı/10,271,680 byte. Önceki tablo turunun21 kaydı ve başarısız denemeler dahildir. Daha eski234 kayıtlık paket ayrı korunur. Kayıt sayısı araştırma kapsamı veya ürün test sayısı değildir.

## Kanıt matrisi

| ID | Deney | Kanıt |
| --- | --- | --- |
| N20 | Yerleşik ATR14/RMA,32 kapalı günlük mum,31 ardışık güncelleme | ev_43777f59ed97bd711ebc96f85a247895185e33e59265d5c34fd2d3f36eda6c38 |
| N21 | ATR smoothing menüsü/görseli; SMA seçimi ve18 bağımsız pencere | ev_7b81f9a1844b1a27d070824dca0c9389301a07b8a8b80dd695e7d891e7fd3d26; ev_ae7f7b1ae3f6af23ecc7501f768cc5acc003337830c87fe058c526eb813ebc6f |
| N22 | RSI14+SMA14;32 kapanmış mumdan overlay için19 pencere | ev_7d578bd881643420eb52859efd239d606b0251d20d456ca521561ed55af7d5c0 |
| N23 | RSI2; yerel seed ve20 güncellemelik burnin sonrası10 kapanmış mum | ev_d4b807d3d1bb22aa5e9d9d22e015e211ef425e0ee99f21f811abba4b0c7f55b6 |
| N24 | Session/HLC3/standard-deviation VWAP1h; tam10 Kasım seansı ve11 Kasım ilk kapalı saat | ev_3efef42c744c7213055a3cb820af08b98dcd292e46564ae5804144bdf276decc |
| N25 | Saatlik VWAP Inputs ve görsel kayıt | ev_c05e1206bf3665a0f70a038024416824452842a05caf465c369f029c2297e82c |
| N26 | Hide VWAP on1D or Above açık; günlük tablo VWAP sütunları boş, nesne mevcut | ev_248083ab73ac2be5b1ca5676a0b28be39f5fd5f92996a96667abca315317176e |
| N27 | Hide kapalı;1D/Session/HLC3/Percentage/band multiplier2;32 kapalı satır/96 çıktı | ev_858c75e7726dddaaa77b42da6b3c3dc33f6a5b80ab99c4639f2054ccc0f589d1 |
| N28 | Calculation timeframe menüsü Chart/tick/second/minute/hour/day/week/month seçenekleri | ev_34639bc41691aca72241df86f60c90f2dac059e8419147879f922be6877bdfdd |
| N29 | Üst-zaman seçimi timeout; DOM'da1 day seçeneği bulundu ama seçimin uygulandığı doğrulanmadı | ev_56399c0d9f6d1f1bf81ee383b212ae0d759f3cf655669e1a4b7991263814bf19; ev_1917d3400daaef369aedd057830d1c59435eb0a694e97387e8e456f50c8ec8c0 |
| N30 | Geri yüklenen BB Inputs ve son object tree/saved | ev_15f916c895dfbb147ec5bd2d4b0e0ea8e41f699241e1dd694661ab81d32fc738; ev_d9548ddcfd2b6b6c422caa5979ab81c645bfe52d67fee3dca597349651215186 |

## ATR: smoothing iki farklı hesap sözleşmesi

reports/rea-chart/atr-rma-parity-20261111.json:10 Ekim–10 Kasım arasındaki32 kapalı1D mum. Önceki kapanış bilinen31 mumda TR=max(H−L,abs(H−Cprev),abs(L−Cprev)); RMA14 next=(13*previousATR+TR)/14. Önceki ATR ve çıktı0.1 precision ile okunduğundan tolerans0.05*13/14+0.05=0.0964286.31/31 adım uydu; maksimum fark0.0785715.10 Kasım TR2720, previousATR2291.6, next2322.2.

reports/rea-chart/atr-sma-parity-20261111.json: SMA14 için önceki kapanışsız ilk input mumundan TR türetilmedi.31 TR'den18 tam pencere kuruldu;18/18 sonuç0.05 tolerans içinde.10 Kasım2459.0142857→2459.0. Aynı gün RMA2322.2; smoothing seçimi yalnız çizgi stili değildir.

Bu günlük BTC örneğinde31 TR'nin tamamı high−low'a eşit. Gap dalı ayrışmadı; önceki kapanışın mum aralığı dışında kaldığı bağımsız örnek gerekiyor. RMA ilk seed/warmup, NA, length1/boş geçmiş ve borsa veri düzeltmeleri açık. ATR14/SMA doğrulaması RMA seed'ini doğrulamaz.

## RSI: ana hesap ile RSI üzerindeki MA ayrılır

reports/rea-chart/rsi-overlay-parity-20261111.json: varsayılan RSI14/close yanında görülen RSI-based MA, RSI değerlerinin SMA14'üdür.32 kapalı RSI değerinden19 pencere çıktı;19/19 uydu. RSI ve overlay0.01 precision ile okunduğu için iki katmanın toplam toleransı0.01; maksimum fark0.0064286. Bu, ana RSI14 seed/formülünün bağımsız kabulü değildir.

reports/rea-chart/rsi2-converged-parity-20261111.json: ayarlanabilir periyot2 çalıştırıldı. Yakalanan serinin ilk iki değişiminden yerel SMA gain/loss seed'i oluşturuldu; Wilder RMA alpha1/2 ile devam edildi.20 recursive güncelleme bekletildikten sonra1–10 Kasım arasındaki10 kapalı sonuç0.005 tolerans içinde uydu; maksimum fark0.0037592.10 Kasım hesap13.5219390, ekran13.52.

Bu yakınsama örneğidir: TradingView geçmişinin başlangıcına erişilmedi, gerçek origin seed kanıtı değildir. Varsayılan RSI14 tam parity veya flat/all-up/all-down platform fixture'ı yerine kullanılamaz. Önceki kaynak bulgusu IND-RSI-FLAT (uygulama50 / kaynak down==0 dalı100) açık kalır; sessiz ürün değişikliği yapılmadı.

## Saatlik VWAP: reset, birikim, bant ve belirsizlik

reports/rea-chart/vwap-hourly-consistency-20261111.json.1h/UTC, Session, HLC3, standard-deviation band1. Yakalanan33 satırdan açık11 Kasım01:00 çıkarıldı.9 Kasım17:00'dan başlayan7 satır eksik seans olduğu için birikim karşılaştırmasına katılmadı.10 Kasım00:00–23:00 tam24 saat ve11 Kasım00:00 ilk kapalı saat olmak üzere25 karşılaştırma var.

İki00:00 satırında VWAP=HLC3, upper=lower=VWAP:10 Kasım75135.0;11 Kasım73592.0. Gün içi VWAP=sum(HLC3*volume)/sum(volume), standart sapma bantları hacim ağırlıklı population variance ile tutarlı.10 Kasım23:00 VWAP73889.9; upper74456.1; lower73323.7.

Hacim K biçiminde yuvarlanmıştır. Burada **tam hassasiyet parity değil, belirsizlik aralığıyla tutarlılık** doğrulandı: her gösterilen hacim için son yazılı ondalığın yarım birimi kullanıldı (2.42K±5,2.4K için konservatif±50). Fiyat kaynağına±0.05, gösterilen çıktıya±0.05 eklendi. Bütün25 satırda VWAP ve iki bant bu aralıklarda. Merkez ağırlıklarla hesaplanan VWAP maksimum farkı0.1358975; en geniş ortalama kabul yarıçapı1.5729213. Geniş yarıçap sebebi az basamaklı hacimdir; hassasiyet0.1'e eşitmiş gibi sunulmaz.

Ağırlık belirsizliği mean için sum(deltaV*abs(price−mean))/(totalV−sum(deltaV)) ile sınırlandı. Bantlar için mean çevresindeki ikinci momentin numerator/denominator aralıkları ve mean hatası ayrı yayıldı. Hesaplar tekrar çalıştırılabilir yardımcıda bulunur. Exact volume, sıfır hacim, vendor-volume hatası, DST/seans takvimi ve event anchors hâlâ açık.

## 1h→1D OHLC eşleştirme ve timeframe provenansı

reports/rea-chart/cross-interval-aggregation-20261111.json.10 Kasımın24 kapalı saatlik mumu ile aynı UTC günün günlük verisi karşılaştırıldı:

| Alan | Saatlikten birleştirme | Günlük referans |
| --- | --- | --- |
| Open |75327.1 |75327.1 |
| High |75411.0 |75411.0 |
| Low |72691.0 |72691.0 |
| Close |73762.9 |73762.9 |

Dört fiyat birebir eşit. Yuvarlanmış saatlik hacim merkezleri162890'a toplamlandı; günlük162.89K. Saatlik belirsizlik toplamı±300 olduğundan exact volume equality sonucu çıkarılmaz. Tek UTC kripto günü; diğer borsalar, eksik mum/gap ve günlük oturum sınırları doğrulanmış değildir.

1h Session VWAP gün sonunda73889.9,1D Session VWAP73955.0. Günlük grafikte reset her mumda gerçekleştiğinden sonuç günlük HLC3'e eşittir; bu65.1 fark otomatik veri hatası değildir. Bar kaynaklı HLC3*volume hesabı, farklı aggregation timeframe ile aynı tick VWAP'ını garanti etmez. Bot veri sözleşmesi display interval, calculation interval, price source, anchor/session, volume unit ve open/closed durumunu tutmalı; yalnız indicator='VWAP' yeterli kimlik değildir.

## Görünürlük ve yüzde bantları

Hide VWAP on1D or Above etkinleştirildiğinde1D tabloda VWAP başlığı/nesnesi durdu ama üç output hücresi boştu. OHLC ve Volume doluydu. Bu boşluk hesap nesnesinin silinmesi veya piyasa verisinin kaybolması değildir. Sıfır değer de değildir. Ürün sunumunda gizli/uygulanamaz/ısınma/eksik veri nedenleri ayrılmalı; boş hücre bot tarafında0'a çevrilmemeli.

Hide kapatılıp Percentage mode ve multiplier2 uygulandı. reports/rea-chart/vwap-percentage-parity-20261111.json içindeki32 kapalı günlük satırda VWAP=HLC3; upper=VWAP*1.02; lower=VWAP*0.98.96/96 çıktı0.05 tolerans içinde; maksimum fark0.048. Bu sonuç günlük reset/source/band-mode sözleşmesini doğrular; intraday ağırlıklı hacim kabulünün yerine geçmez.

## Üst zaman aralığı: incelenen menü, tamamlanmayan davranış

Calculation timeframe menüsü ve Wait for timeframe closes checkbox'u bulundu.1 day girdisinin DOM kimliği de okundu; ancak seçimin Chart→1 day olarak değiştiği doğrulanmadı. Pointer, role/text seçici, odak/klavye ve dialog scroll denemeleri başarılı HTF seçimi üretmedi. Timeout kayıtları tutuldu. Bu araç/oturum sınırlaması; TradingView bu özelliği desteklemiyor sonucu değildir.

Dolayısıyla HTF mapping, gap/forward-fill, lookahead/repaint ve Wait on/off karşılaştırması **açık**. Checkbox geçici kapatılıp tekrar açıldı; nihai Chart/on ayarı geri yüklenen BB'de okundu. Bu kontrolün etiketi tek başına bot güvenilirliği veya confirmed-bar sözleşmesini kanıtlamaz. Araştırmada daha fazla aynı timeout denemesi yapılmadı; doğrulanabilen sayısal ve görsel bulgular korundu.

## Tasarım ve menü davranışı

- ATR/RSI ayrı pane'de ana zaman eksenini paylaşır; ana fiyat ve gösterge ölçekleri ayrıdır. ATR settings Length/Smoothing/Calculation grupları, sabit Defaults/Cancel/Ok footer'ı ve belirgin fokus halkası gözlendi. Açılır smoothing listesi RMA/SMA/EMA/WMA içerir; bu seçeneklerin yalnız RMA ve SMA hesapları çalıştırıldı.
- RSI Inputs ana length/source ile smoothing length/type'ı ayrı tutar. BB StdDev yalnız ilgili smoothing türünde etkinleşen bağımlı alandır. Divergence çekirdek hesapla aynı zorunlu kapsam değildir.
- VWAP ayarları uzun: Source metni dar kutuda kısalır, Bands Multiplier2/3 kapalıyken numeric alanları disabled, içerik içten kayar ve footer kalır. Ekranda görünen input kısaltması veri kaynağının tam kimliği değildir.
- Veri penceresi ana OHLC, Volume ve göstergeyi ayrı başlıklarda sunar; seans başlangıcında eşit bantlar açıkça okunur. Aynı panelde geçmiş OHLC ile Last day change canlı bağlamı birlikte bulunabilir; önceki kapalı mum fixture'larında bu canlı alan sabit hesap girdisi yapılmadı.
- Görsel referanslar reports/rea-chart/atr-rsi-vwap-visual-manifest-20261111.json. Attached viewport/PNG uyumsuzluğu sürdüğü için yeni responsive/mobile kabulü çıkarılmadı. Scroll/focus/popover etkileşimi ayrı kalite maddesi olmalı.

## Plan ve doğrulama

T09: kalıcı indicator config schema'ya smoothing/source/band mode/offset/anchor/calculation timeframe/visibility ve output-unavailable reason girmeli. T10: ATR RMA/SMA ve RSI overlay örnekleri, seed/warmup/flat kararlarından ayrı kabul. T11: Session VWAP intraday reset, volume precision/provenance ve timeframe farkı. T08: tek günlük24×1h→1D aggregation örneği başlangıç kabulü; HTF confirmed mapping hâlâ açık. T13/QA01: birim/formatter/empty semantics, multi-pane ve uzun dialog odak/scroll davranışı.

Eski5 tamamlanmış görev korunur. Bu araştırma ürünün genişleyen iş kapsamına kabul girdisidir; görevler uygulanmış/tamamlanmış sayılmaz. Veri yaşam döngüsü history pagination/reconnect/stale/request race, pointer/drag/hit testing ve ölçülmüş performans hâlâ gerekli. REA04 nihai plan konsolidasyonu ayrıca yapılacak.

Tekrar hesaplama: tools/rea/verify-indicator-research.mjs, yerel sabit JSON gözlemlerinden sonuçları yeniden hesapladı;31 RMA+18 SMA+19 RSI overlay+10 RSI2+96 VWAP percentage değeri ve4 aggregation alanı geçti,25 VWAP saatlik satırı rounded-volume aralıklarıyla tutarlı. Ürün testleri bu tur çalıştırılmadı. Gözlenen fixture sayısı19'a çıkarıldı; hepsi aynı hassasiyet/güven düzeyinde değildir.
