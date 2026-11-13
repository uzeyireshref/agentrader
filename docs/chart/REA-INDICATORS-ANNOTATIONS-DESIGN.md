# Geniş canlı araştırma: göstergeler, açıklamalar, şablon ve tasarım

10 Kasım 2026. REA03 araştırma eki. Araştırma düzeni: REA Araştırma, BINANCE:BTCUSDT.P. Bu tur ürün uygulaması değildir. Kaynak görünümü ile canlı hesap sonucu, menü keşfi ile uygulanmış davranış ayrı tutulur.

## Araştırma yöntemi ve kanıt

REA ile mevcut hesaplı tarayıcıda tıklama, form düzenleme ve salt okunur yerleşik Pine kaynakları incelendi. Script düzenleme, çalıştırma veya yayınlama yapılmadı. Gösterge sınırı içinde Volume korunarak BB → RSI → ATR → VWAP örnekleri sırayla incelendi; sonrasında BB geri getirildi. İşlemler yalnız araştırma düzenindedir.

Tam paket: reports/rea-chart/rea-evidence-wide-indicators-design.json — 153 retained kayıt, 60,975,888 byte; önceki turları ve başarısız denemeleri de kapsar. Bu sayı tamamlanan özellik sayısı değildir. İşlem bazında step status kontrol edilir.

| ID | İncelenen bölüm | Kanıt |
| --- | --- | --- |
| W01 | Annotation envanteri ve favorites/templates menüsü | ev_1f7afabd3c4261f6587a0aae36c6b2864475bddceff8c035302813b178b288cc |
| W02 | Metin oluşturma; inline editor ve nesne ağacı | ev_3e18e6e3cad3cf9f2deb1db68e35df9fb10cb0c967e4ed3817d7da9c9f0520b5 |
| W03 | Metin ayarları; gerçek çok satırlı metin korundu | ev_ee9de20f4f0af2711255bf122c3573994b581ac597586a5796aee2390397158e |
| W04 | Background/border/wrap uygulandı; boyut listesi incelendi; seçili metin ekranı | ev_55f9904eca4f870b58fb90b2108bc0f376e8ea004b487087a8d220ce5b1144ed; ev_b2e1f328f400d099710283529ee42051073ae6ede71bbc9bba9ef1c109bad092 |
| W05 | Deneme metni silindi; çizimler gizlendi; gösterge şablonu alanları | ev_d9e9d1a153c5d72d2c86af60508e39659e9d6edd06f3bf1a33e2ec67d1f393e7; ev_fa9ddae912b4b31f3049abc8db8e67007190a8616478f4ec25285f6c3fdca808 |
| W06 | Yerleşik BB kaynak formülü ve render offset | ev_d0f41958c28855db8730715e661a457bf8db359efe31d7646c697ff78ef05883; ev_f2c3155e32ce682e93dd6ad6e2adea4281aa0b309e56f2483be3599cf9099bc5 |
| W07 | Yerleşik RSI girdileri/stili/yumuşatma seçenekleri | ev_6f28fd09bb668169572e23234e89e7006e3fa04234581ddd75409a93432cd5e5; ev_d4f23ddee9c8fbb519ae5b7cbb337b973252aa3145fade493d5a165c3d129b6e |
| W08 | RSI kaynak hesabı ve ayrı panel görünümü | ev_906e39a0d8874fc35b6242741a76190a68d9eb60437ac80919b58578c1e79e11; ev_3334eca8a64827e7ebe7d962cfef6383ddc98679bd198e71459eb82c1d332896; ev_0fb93706c38c419a6e3dd968bad084fa7c40d6571e47140d7f96ce66bf4622ad |
| W09 | Yerleşik ATR girdileri ve kaynak | ev_0f68ae83485452028f96f3162c26c85ea1730139cb3706b52e06422ede1b37a8; ev_b60df845f0f6246dbf6baef8c13f2267c701ae4a851b34f197426e1e536705bf; ev_e53dc7cc2f323a5a7bd5010947feb542ae3cf3bf13864bdd2dd78fbf2d73b6e7 |
| W10 | Yerleşik VWAP girdileri, anchor/bant modu/stil | ev_02d47390dc9a21499bff437cf3d2684b8c29f577eb7f420a3f6871c21edf083e; ev_7c100f260489de7147efa6de5d5e57a7c5138b98f025d524563722702d009d0f |
| W11 | VWAP salt okunur kaynak: reset ve bant hesabı | ev_df184bf57dc47c94fafd3ebea5901f0c1f4484dd387bfc366eee10a087cb877d; ev_203900cc4ce406f75e73f58196b63f652015dca44832b8fbcc3c800b5e46ad2a; ev_bc03e5158d471fbfa975011d40b38cb9eeaa2618b042bcaf0b866bf0a3a702ed; ev_697c1cfed13f55e70c47a3d32be182f6cbc10b16de2e4d8cdffeb15b760250f8 |
| W12 | Koyu tema, panel kapalı geniş grafik, ayar dialogu | ev_cc6322cc34ac19c56522102c74b60641889a38afe011f95869850742bff81e98; ev_5cc9026a8b4ff2d52ed64d4e8fa831d13e4aa6f861dffec4b0d4f3ddd6d84628; ev_434ece24976d2341cc1947ec5af64dea27cafc96a4b03795af094f5a786acaa2; ev_99185fd9b23139439b4a6e61b41bc2fc57b4889902187032b40a929e6c8611fd |
| W13 | Açık tema, BTC/1D, Volume+BB geri getirildi; açık save doğrulaması | ev_6dd02833464c642ce96a6e5ae7334d09831483cf39824ff45aae4b0c6b14ef85; ev_0c618b2fafbaed44f22f8102c7407f6841796c5736c1c066f3686658f9abf039 |

## Metin ve açıklama araçları

Menü Text/Note/Price note/Pin/Table/Callout/Comment/Price label/Signpost/Flag mark ve Image/Post/Idea içeriyor. Bu keşif, hepsini uygulama kararı değildir. Temel kapsam metin, kısa not ve fiyat etiketi; sosyal içerik ve dekoratif varyantlar kapsam dışıdır.

Text bir canvas tıklamasıyla yaratıldı; doğrudan grafikte Add text alanı açıldı. İki satır, Türkçe karakterler, noktalama ve sayı içeren metin dolduruldu. Escape düzenlemeyi bitirdi; sonraki settings dialogunda içerik korundu. Nesne ağacı başlığı içerik yerine Text olarak kaldı. Bu yüzden içerikten nesne adı türetildiği varsayılmaz.

Text dialogunda Text ve Visibility sekmeleri var. Varsayılan font boyutu14; listede8/10/11/12/14/16/18/20/22/24/28/32/40 görüldü. Background ve Border başlangıçta kapalı, ilgili renk kontrolleri disabled; açılınca etkinleşti. Text wrap açıldı. Ok sonrası seçili metinde mavi sınır ve sağda genişlik tutamağı görüldü. Floating toolbar stil/boyut/ayar/kilit/silme kontrolleri sunuyor.

Bu dialogda Coordinates sekmesi görülmedi. Fiyat/zaman ankrajı ile ekrana sabit metin arasındaki dönüşüm bu turda tamamlanmadı; toolbar simgesinden davranış çıkarılmadı. Wrap tutamağını sürükleme, metin taşması, font değişiminde piksel eşliği ve touch davranışı açık.

Deneme metni ekran/ayar kanıtı alındıktan sonra nesne ağacı menüsünden silindi. Önceki dört geometri örneği sonraki kontroller için saklandı, global olarak gizlendi. Yeni çizim oluşturma turunda global gizleme durumunun görünür duruma geçtiği görüldü; bunun kalıcılık/undo semantiği ayrıca test edilmeli.

## Gösterge hesabı ve görünümünün ayrılması

| Aile | Doğrudan okunan kaynak/ayar | Bizim sözleşmeye etkisi |
| --- | --- | --- |
| BB | basis=seçilen MA(source,length); dev=multiplier×ta.stdev(source,length); upper/lower=basis±dev. Offset plotlara uygulanıyor | Hesap zamanı ile render offset ayrı; basis türü değiştirilince sapma hesabının da MA türüne dönüştüğü varsayılmamalı |
| RSI | change(source); pozitif/negatif farkların RMA ortalaması; down==0 önce100, sonra up==0 ise0; diğerinde100−100/(1+up/down) | RSI'nin iç smoothing'i ile RSI üstüne çizilen SMA/EMA ayrı parametreler |
| ATR | Seçilen RMA/SMA/EMA/WMA, ta.tr(true) serisine uygulanıyor; varsayılan14/RMA | Sadece high-low ortalaması yeterli değil; ilk bar ve önceki close eksikliği bağımsız fixture ister |
| VWAP | Source HLC3; ta.vwap(source,isNewPeriod,1); sapma bant tabanı stdevUpper−vwap, yüzde modunda vwap×0.01 | Seans/reset/volume ve çıktı bantları sürümlü hesap sözleşmesi ister; basit rolling average değildir |

### RSI farkı: bağımsız fixture gerektiren somut aday

Mevcut frontend/src/indicators.ts, ortalama kazanç ve kayıp ikisi sıfırsa50 üretiyor. İncelenen yerleşik RSI kaynak dal sırası down==0 için100 döndürüyor; up==down==0 halinde bu dal önce seçilir. Bu, **kaynak sözleşmesi farkıdır**. TradingView'e sabit fiyatlı aynı OHLCV fixture'ı verilerek canlı sayısal karşılaştırma henüz yapılmadı. Eski kayıtların anlamı sessiz değiştirilmemeli; REA04'te uyumluluk tercihi ve sürüm kararı açık olmalı. Ürün kodu bu tur değiştirilmedi.

RSI panelinde ana mor çizgi yanında varsayılan SMA14,70/50/30 seviyeleri, arka plan ve overbought/oversold gradient fill var. Smoothing seçenekleri None/SMA/SMA+Bollinger/EMA/RMA/WMA/VWMA. Calculate Divergence varsayılan kapalı; temel RSI için zorunlu değil. Bütün varyantlar ilk teslim şartı yapılmamalı.

ATR default14/RMA; Chart hesap intervali ve Wait for timeframe closes açık. Length ve smoothing ayrı. İlk bar için ta.tr(true) çağrısı kaynakta görülüyor; fonksiyonun runtime seed/NA sözleşmesi yalnız bu çağrıdan tamamıyla kanıtlanmaz.

### VWAP kapsamı

Anchor seçenekleri Session/Week/Month/Quarter/Year/Decade/Century/Earnings/Dividends/Splits. Kaynakta Session→timeframe.change(D), Week→W, Month→M, Quarter→3M, Year→12M; veri başlangıcında önceki source NA ise reset var. Bu eşleme doğrudan kaynak gözlemidir; tam seans takvimi ve timezone sözleşmesini tek başına kanıtlamaz.

Hide on1D+ varsayılan kapalı. Bands mode Standard Deviation/Percentage; ilk bant çarpanı1 açık,2 ve3 kapalı/disabled alanlı. Stil VWAP, üst/alt bant ve dolgu; standart precision/status line/axis label kontrolleri. Günlük Session görünümünde üç çıktının aynı sayıyı göstermesi gözlendi; bu değer, intraday hacim ağırlıklı gün içi VWAP ile eşdeğer sayılmamalı. Vendor hacmi yoksa kaynakta runtime error yolu var; bizim ürün açık unavailable durumu göstermeli.

Kripto üründe temel Session/Week/Month başlangıçları ve açık timezone; event anchor/decade/century zorunlu değil. Anchored VWAP tıklama geometrisi ayrı ileri özellik olarak kalır.

## Gösterge şablonu

Favorites ile Templates ayrı sekmeler. Save indicator template dialogu ad, opsiyonel Remember Symbol ve Remember Interval seçeneklerini ve Saved indicators listesini gösteriyor. Boş adda Save disabled. Bu tur yeni şablon oluşturulmadı; dialog Cancel ile kapatıldı.

Gösterge şablonu; çizim stil şablonu; çalışma alanı layout kaydı farklı nesneler olarak tasarlanmalı. Gösterge şablonunun sembol veya intervali değiştirmesi açık tercihe bağlı olmalı. Kullanıcının mevcut çizimlerine sessizce uygulanmamalı. Template overwrite/rename/reload henüz çalıştırılmadı.

## Tasarım eşzamanlı araştırıldı

1. Text seçimi: sınırlı mavi kutu, bir genişlik tutamağı, yüzen araç çubuğu; nesne ağacında seçili satır. Seçim görünümü ile çizimin kayıtlı rengi ayrı.
2. RSI paneli: fiyat panelinden ayrı ölçek ve legend; yatay zaman hizası;70/50/30 çizgileri ve katmanlı dolgular. Sağ kenar etiketlerinin çakışma durumu ayrıca kabul edilmeli.
3. Panel kapalı grafik: chart daha geniş, görünür tarih/bar sayısı değişiyor; grafik koordinatları ekran pikseliyle saklanmamalı.
4. Koyu tema: gerçek UI theme-dark doğrulandı. Grafik bu oturumda siyah canvas; dialog ve yüzeyler farklı koyu tonlar. Bunlar bu düzenin gözlemleridir, tüm TradingView varsayılan paleti diye sunulmaz.
5. Ayar dialogu: sol kategori listesi, sağ kayan içerik ve altta sabit Template/Cancel/Ok bölümü; içerik yüksekliği ekrana sığmazsa iç scroll var. Selected ile hover farklı font weight/arka plan durumu taşıyor.

Salt okunur DOM/CSS ölçümü (REA dışında ordinary CDP): reports/rea-chart/tradingview-dark-dialog-computed-style.json,50 kayıt. CSS viewport1536×776, ekran görüntüsü1920×970 (1.25 oran). Dialog içerik boyutu748.4×734.4CSSpx, kategori listesi206px, kategori satırı40px,14px yazı/18px line-height; selected weight600, normal400. Selected beyaz/#222 arka plan; normal metin rgb184. Dialog düğümünün transparent background'u nihai görsel yüzey rengi sayılmaz. Bu ölçüler başka viewport/OS için otomatik hedef değildir.

Referans ekranları: reports/rea-chart/tradingview-text-selected.png; tradingview-rsi-pane.png; tradingview-dark-wide.png; tradingview-dark-settings.png. Uygulamada bunlar işlevsel durumlarla beraber görsel kabul fixture'larına dönüşür. Tasarım en sona bırakılmaz.

## REA04'e girecek kabul örnekleri

| Fixture | Kabul kapsamı | Durum |
| --- | --- | --- |
| IND-RSI-FLAT | Sabit close; up/down sıfır dalı ve ilk geçerli bar;50/100 uyumluluk kararı | Kaynak farkı bulundu, platform fixture açık |
| IND-RSI-TREND | Yükselen/düşen seri, reset/warmup; RSI ile smoothingMA çıktılarının ayrımı | Açık |
| IND-BB-OFFSET | Aynı kapalı OHLCV; basisMA ve population/sample sapma, offset±n | Formül okundu; numeric parity açık |
| IND-ATR-GAP | Önceki close'a gap; ilkbar/eksikclose ve smoothing türleri | Kaynak okundu; numeric parity açık |
| IND-VWAP-RESET | Gece/seans/hafta sınırı, timezone, sıfır/eksikvolume,1D kaynak farkı | Reset kaynağı okundu; bağımsız fixture açık |
| TXT-MULTILINE | Unicode, newline, wrap/background/border, seçili kutu ve cleanup | Canlı oluştur/edit/style/silme gözlendi; drag/reload açık |
| TPL-SCOPE | Gösterge şablonu, remember symbol/interval kapalı/açık, overwrite/cancel | Alanlar/Cancel gözlendi; apply/reload açık |
| VIS-PANE-THEME | Açık/koyu; panel açık/kapalı; modal scroll/footer; selected/hover | Ekran/CSS kaydı alındı; ürün karşılaştırması geliştirmede |

## Son durum ve açık sınırlar

Açık tema geri getirildi. BTC/1D/Candles; Volume+yerleşik BB geri getirildi. Metin denemesi silindi, önceki dört araştırma çizimi gizli. All changes saved doğrulandı. Kaynak editörü ve ayar dialogları kapalı.

Pointer drag/pointercancel/touch, pane resize, bağımsız kapalı mum sayısal parity, EMA seed/NA, template apply/reload, reconnect/history ve eşit yük performans ölçümü tamamlanmadı. Hash navigation bazı dropdownları kapatıyor; devam eylemlerinde mevcut durum yeniden okunmalı. Timeout işlemleri PASS sayılmadı. REA03 açık kalır; tüm TradingView eşitliği iddia edilmez.
