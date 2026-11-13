# Grafik tasarım ve yeniden kurulum şartnamesi

10 Kasım 2026. Kullanıcı hedefi: işlevsel doğruluğun yanında TradingView düzeyinde grafik okunabilirliği, araç erişimi ve etkileşim kalitesi. Bu dosya uygulama öncesi tasarımdır; yeni arayüz teslim edildiği anlamına gelmez.

## Ölçülen referans ve kapsam

Araç referansı TradingView Supercharts; market Binance BTCUSDT perpetual LAST. Bizim motorumuz Lightweight Charts ve kendi kanonik hesap/çizim kaydımız olarak korunur. Markalar, hesap/broker özellikleri ve Supercharts kaynakları ürünümüze taşınmaz; yeniden kurulan şey desteklenen davranış ve grafik kalitesidir.

İlk hesapsız ekran: 1280×720, DPR 1. Sonraki görünür tarayıcı: CDP CSS viewport 1536×776; screenshot 1920×970 piksel. Bunlar aynı boyutta karşılaştırma değildir. Oran 1.25'tir; bu oran tek başına işletim sistemi ölçek ayarının ölçümü sayılmaz. Gelecek karşılaştırmalar CSS boyutu/DPR/tema/font/sabit veriyle sabitlenecek.

`reports/rea-chart/tradingview-computed-style.json` salt okunur DOM/CSS CDP ölçümüdür, REA Evidence değildir. Kaynak, kayıt zamanı ve node/selector/bounds içerir. Body için 14px system/Trebuchet/Roboto/Ubuntu font zinciri; ana yatay toolbar örneklerinde 38 CSS px; sol dikey toolbar 52 CSS px, sağ rail 45 CSS px ölçüldü. Legend toolbar örnekleri 13px/24px. Bu sayılar tek ekrandaki gözlemdir, platformun bütün breakpointleri için sabit tasarım tokenı olduğu iddia edilmez.

## Mevcut projede görülen farklar

Kaynak incelemesi: frontend/src/style.css, App.tsx, DrawingLayer.tsx, DrawingPanel.tsx, ruler.ts, indicators.ts, chartNavigation.ts, chartKeyboard.ts.

- Mevcut topbar 76px; ek instrument/context alanları ve çizim paneli dikey alan tüketiyor. Referans grafik ağırlıklı ve daha sıkışık bir araç kabuğuna sahip. İlk düzenleme chart yüzeyinin görünür alanını büyütmeli.
- Mevcut sol watchlist 245px (geniş ekranda 270px); referansta nesne ağacı/watchlist sağda değiştirilebilir panel olarak yer alıyor. Bizde panel kapatılabilir olmalı; sabit iki yan panel zorunlu tutulmamalı.
- Mevcut çizim ikonlarında metin/Unicode ve elle oluşturulan SVG karışıyor. Tek ikon ailesi, sabit optik boyut ve araç grubu açılır menüleri gerekiyor.
- Mevcut OHLC ve çok sayıda yardımcı metin 9–10px. Yeni hiyerarşide kritik fiyat/eksen/araç bilgisi düşük karşıtlıklı küçük yazıya bırakılmayacak.
- Mevcut renkler koyu yüzey, altın vurgu ve yeşil/kırmızı mum ailesinde. Referans incelemesi açık temada da yapıldı. Açık ve koyu tema tokenları ayrı test edilecek; bir renk değişikliği bütün tema kabulü sayılmaz.
- Mevcut draw layer SVG, render motoru Canvas. Referansta alt canvas ve pointer alanı ayrı; bizim hit-test ve görünüm katmanları da tek geometriyi paylaşırken ayrı sorumluluk taşımalı. Alt katmana tıklama zaman aşımı yaşanması, tasarımımızda açık bir etkileşim sahipliği gereksinimidir.

## Yerleşim sözleşmesi

Öncelik sırası: fiyat/zaman grafiği → OHLC/kaynak ve aktif araç → çizim/gösterge ayarları → piyasa listesi → teknik durum. Grafik kapalı veya stale ise bu durum açık görünür.

1. Üstte kompakt sembol, interval, grafik tipi, göstergeler, undo/redo, çalışma alanı ve görünüm kontrolleri.
2. Solda gruplu çizim rail'i; sık kullanılan araç doğrudan, varyantlar açılır menüde. Toolbar konumu scroll ile kaybolmaz.
3. Ortada ana fiyat pane'i, isteğe bağlı hacim/RSI pane'leri; ayırıcı sürükleme ve pane menüsü.
4. Sağda fiyat ekseni; onun dışında açılıp kapanabilen watchlist/nesne ağacı. Overlay/menü ekseni okunamaz hale getirmemeli.
5. Altta zaman ekseni, aralık kısayolları, timezone ve canlıya dön. Teknik doğrulama panelleri normal kullanım alanını sürekli işgal etmez.
6. Çizim seçilince yakınında stil/kilit/gizle/ayar/çoğalt menüsü; tam sayısal edit ayrı kontrollü panel veya dialog. Seçim değişince eski nesneye yazma yok.

## Görsel dil ve etkileşim durumları

| Alan | Hedef | Kabul kanıtı |
| --- | --- | --- |
| Tipografi | 12–14px temel grafik UI; fiyatlarda tabular sayılar; 1–2 font ailesi | Aynı fixture ve font yükleme sonrası screenshot; eksen etiketleri kırpılmaz |
| Renk | surface/canvas/panel/border/text/muted/accent/up/down/warning/error tokenları | Her iki temada normal/hover/focus/selected/disabled/stale durumları |
| Araçlar | Tek ikon ailesi, belirgin aktif durum, tooltip ve kısayol | Fare ve klavyede aynı araç seçimi; aria-label görünür işlevle eşleşir |
| Grid/eksen | Düşük ağırlıklı grid, net crosshair, doğru tick/UTC formatı | Zoom, DPR, pane resize ve uzun fiyatlarda hizalama |
| Çizim | İnce keskin çizgi, seçiliyken tutamaklar; geniş ama görünmez hit alanı | 1/1.25/2 DPR; tutamak ve gövde ayrımı; üst üste nesne seçimi |
| Etiket | Ölçüm/R:R/fiyat bilgisi; çakışmada yerleşim veya kısa mod | 200 çizim ve sıkışık fiyat ölçeğinde kritik etiket kaybolmaz |
| Paneller | Kenara bağlı, kapatılabilir, kontrollü scroll; durum korunur | 1280/1536/1920 genişlik; panel değişimi chart resize tetikler |
| Dialog | Inputs/Style/Visibility ayrımı, doğru birim ve validation | Numeric edit, Tab/Escape/Enter, focus dönüşü, hatalı giriş |
| Veri durumu | Loading/Live/Stale/Reconnecting/No data/Error ayrımı | Aynı veri kesinti fixturelarında açık durum ve erişilebilir duyuru |
| Hareket | Gereken feedback; sürekli dekoratif animasyon yok | Reduced motion ve boşta CPU/listener kararlılığı |

Bu değerler bizim tasarım hedeflerimizdir; hepsi TradingView'den birebir ölçülmüş kabul edilmez.

## D01–D06 tasarım işleri

Bu altı iş 21 çekirdek pakete ek tasarım izidir; çekirdek tamamlanma sayısını değiştirmez. Şu an hepsi NOT_STARTED; aşağıdaki çıktıların hiçbiri uygulanmış değildir.

| İş | Teslim | Bağımlılık | Bitiş |
| --- | --- | --- | --- |
| D01 | Referans ölçümünden token ve temel kontrol sözleşmesi; açık/koyu renk/typography/icon/grid | REA04 | Belgeli tokenlar, örnek durumlar ve font/lisans kaydı |
| D02 | Grafik odaklı kabuk, gruplu sol araçlar ve sağ nesne/watchlist paneli | D01 | 1280/1536/1920 düzen; chart alanı/resize; mevcut piyasa seçimi regresyonu |
| D03 | Crosshair/OHLC/eksen, pane ve navigasyon görsel kalitesi | D02, T08 | Sabit mum/grid, label collision ve DPR testleri |
| D04 | Çizim tutamak/etiket/menü ve sayısal edit görünümü | D02; ilgili T04–T07/T12 paketi | Her araç için hover/select/drag/lock/hidden/error durumları; geometri parity |
| D05 | Gösterge ayarları, workspace şablonları, dar ekran/fullscreen | D02; T09/T14 | Kalıcı ayar, pane yaşam döngüsü, dar ekran/klavye/scroll kabulü |
| D06 | Görsel regresyon ve kullanıcı kabulü | D03, D04, D05, QA01 kapsamı | Tekrarlanabilir ekran paketi, açık kusur listesi ve kabul kararı |

Uygulama sırası: REA04 → D01 → D02 → T04+D04(long/short) → T05/T06+D04 → T07+D04 → T08+D03 → T09–T11+D05 → T12/T13+D04/D03 → T14+D05 → P4–P7 → QA01+D06. Buradaki + birlikte teslim koşuludur; paralel ajan talimatı değildir.

## Ölçülebilir kabul

- 1280×720, 1536×864 ve 1920×1080 CSS viewport; DPR 1/1.25/2; sabit zaman/mum/çizim/grid/font/tema. İlk görünür tarayıcının 1536×776 çıktısı bu testlerin yerine kullanılmaz.
- Veri fixture'ı ile anchor–native fiyat/zaman hizası hedefi ≤1 CSS px. Bu, tüm resmin referansla aynı olması demek değildir.
- Toolbar/panel boyutlarında kararlaştırılan spec'e tolerans başlangıçta ±2 CSS px. Kaynak ürünün marka/logo/reklamları görsel fark metriğine katılmaz.
- Metin kritik kontrollerde okunur; odak görünür; renk tek durum göstergesi olmaz. Karşıtlık, klavye ve ekran okuyucu kontrolü ayrı raporlanır.
- 4.000 mum/200 çizim için önceki yerel p95 ≤33ms hedefi korunur; yeni ölçüm yapılmadan performans eşitliği söylenmez.
- Görsel iyileştirme kayıt/undo/409/coin geçişi ve kanonik geometri doğruluğunu bozarsa paket tamamlanmaz.
- Mobil dokunmatik kabulü önceki D08/D09'dan ayrı açık kapsam olarak korunur; responsive screenshot dokunmatik kullanım testi değildir.

## Analizden uygulamaya geçiş

Ürün kodundan önce: REA03'te açık deneyler ve erişilemeyen ayrıntılar kayıtlı olacak; REA04, her gereksinimi T/P/D işine ve fixture'a bağlayacak. Bilinmeyen davranışa platformla eşitlik sözü verilmez. Önce desteklenen çekirdekte kalite eşleşmesi, ardından ikinci dalga araçlar gelir. Kullanıcının görsel kalite isteği artık yalnız en sona bırakılmış bir kozmetik iş değildir.

## Eşzamanlı canlı tasarım turu

Metin seçimi/floating toolbar, RSI ayrı paneli, açık/koyu tema ve panel açık/kapalı görünümler aynı işlev araştırmasında kaydedildi. [Detay ve kanıtlar](REA-INDICATORS-ANNOTATIONS-DESIGN.md) W02–W04/W08/W12. Koyu ayar penceresinde CSS viewport1536×776 iken içerik748.4×734.4px, kategori206px, satır40px, font14px/line-height18px; selected600/normal400 görüldü. Ölçüler referans fixture değerleridir, tüm cihazlara sabit hedef değildir. Modal iç scroll + sabit footer, hover ile selection ayrımı ve panel açılışında yeniden çizim kabul kapsamına girer. Renk şeffaflığı hesaplanan düğümden nihai yüzeye yanlış taşınmamalı. Ürün uygulaması ve görsel karşılaştırması henüz yapılmadı.

## Yönetim durumlarının görsel kapsamı

11 Kasım canlı turunda inline rename, grup/çocuk Unlock ve Show ikonları, ortak grup ayarları, katman sırası ve kilitli silme confirmation akışları incelendi. [Ayrıntılar](REA-MANAGEMENT-WORKSPACE.md). Grup durumları AX/DOM kaydıdır; ayrı piksel screenshot kabulü henüz yok. Global gizleme oturum durumu ile tek nesne görünürlüğü görsel olarak ayırt edilmeli. Şablon silme kontrolü hover ile açılıyor; klavye erişimi ve görünür focus bizim kabul şartımız olmalı. Son temiz görüntü reports/rea-chart/tradingview-management-clean-20261111.png.

## Ölçek ve birim durumlarının eşzamanlı görsel araştırması

[Ölçek/saat dilimi turu](REA-SCALES-TIMEZONE.md)10 ekranla log/lineer/yüzde/index/invert, sol eksen, çakışma açık/kapalı ve UTC/+4 sunumlarını karşılaştırdı. Görseller reports/rea-chart/scales-visual-manifest-20261111.json içinde kimlik ve hash ile indeksli. Etiket kutusunun çakışma nedeniyle ötelenmesi kanonik fiyat çizgisini taşımamalı; OHLC fiyat, gösterge yüzde gibi karma birimler açık etiketlenmeli. Görünür uzatma etiketinin üst legend ile çakışması referansta da görüldü; bizim kabulde çözülmeli. İlk screenshot turları geçici default viewport kullandığından piksel eşitliği benchmarkı değildir; indexed sonrası1536×776/DPR1.25 açık istendi. Ürün görsel parity testi geliştirme aşamasındadır.

## Doğrulanmış dar pencere kohortu ve modal kapanışları

[Focus/responsive raporu](REA-FOCUS-RESPONSIVE.md): gerçek girişsiz desktop profilde1280×720,1024×768,768×900/DPR1 PNG boyutları doğrulandı;7 görsel reports/rea-chart/responsive-visual-manifest-20261111.json içinde. Bağlı araştırma penceresinin istenen boyuta uymayan görüntüleri ayrı unverified olarak işaretlendi. Dar ekranda panel kapama, toolbar overflow/erişilebilir ad, satıra kayan form etiketleri ve sabit Cancel/Ok footer birlikte tasarlanmalı. Bu touch/mobile veya ürün parity kabulü değildir. Canlı ayarlarda preview/Cancel/Escape/X anlamı yalnız düğme görünümünden anlaşılmaz; ürün davranışı açık tanımlanmalı.

## D07 — Tablo ve veri penceresi birlikte

[Canlı tur](REA-TABLE-NUMERIC-PARITY.md), reports/rea-chart/table-parity-visual-manifest-20261111.json ve table-parity-design-20261111.png referanstır. İki seviyeli kaynak/alan başlığı, tarih satır başlığı, sağa hizalı sayılar, ince hücre ayırıcıları, grafiğe dönüş ve indirme yolu gözlendi. Sağ Data window tek mum ayrıntısını korur. BB sütunları yatay görünür alanın dışında kalabildi: erişilebilirlikte bulunmaları ekrana sığma kabulü değildir. Gelecek offset satırları OHLC boş/gösterge dolu olabilir; bu durum eksik veri veya gelecek fiyatıyla karıştırılmamalı. Loading/empty/error ve open/closed göstergesi ürün kararı olarak tasarlanmalı. Tablo/CSV ikinci aşama kapsam adayı; Data window çekirdek. Attached viewport sınırlaması sürüyor; bu görüntü responsive/mobile kabulü değildir.

## D08 — Gösterge ayarları, pane ve boş çıktı semantiği

[ATR/RSI/VWAP turu](REA-ATR-RSI-VWAP-DATA.md), reports/rea-chart/atr-rsi-vwap-visual-manifest-20261111.json. ATR/RSI ayrı fiyat ölçeğiyle ortak zaman eksenini paylaşır. Ana length/source ile smoothing length/type ayrı gruplardır. VWAP band2/3 kapalıyken alanlar disabled; uzun içerik içten kayar, Defaults/Cancel/Ok footer görünür kalır. Kaynak adı dar kutuda kısalırken tam kimlik erişilebilir olmalı. Focus halkası, scroll konumu ve popover yerleşimi birlikte test edilmeli; bu tur uzun timeframe seçimi tamamlanmadı.

Hide-on1D nesneyi koruyup output hücrelerini boş bırakır. Gizli/uygulanamaz/ısınma/eksik piyasa verisi ayrı durumlar olmalı; sıfıra veya aynı genel hata metnine indirgenmemeli. Data window geçmiş mum verisiyle canlı Last day change alanını birlikte gösterebildiğinden canlı ve seçili-mum bağlamı etiketlenmeli. Session başlangıcında VWAP bantlarının birleşmesi hata görünümü değildir. Yeni PNGler attached desktop referanslarıdır; responsive/mobile kabulü değildir.

## D09 — Veri durumları, fiyat türü ve pointer geri bildirimi

[Canlı tur](REA-LIFECYCLE-MARKET-POINTER.md), reports/rea-chart/lifecycle-market-pointer-visual-manifest-20261111.json. Offline banner AXte gözlendi; piksel yerleşimi alınmadı. Seans Market open etiketi veri tazeliğini söylemez. Geçmiş mum seçimi, canlı quote ve Last day change aynı ekranda farklı zaman bağlamları taşıyabilir. History navigation latest-bar dönüş yolunu görünür tutar.

Spot/perp/mark arama satırları ürün/fiyat türünü ayırır; ekrandaki ondalık sayısı tick-size otoritesi değildir. Mark serisinde OHLC çalışırken Volume/VWAP legend error controlü ve boş Data window başlıkları, tabloda ise yalnız OHLC/change sütunları görüldü. Üründe eksik hacim/hidden/warmup/stale için açık neden ve yerinde hata tasarlanmalı; son değer yanlış kaynağa taşınmamalı. Precision8 küçük hacimde ayrıntı verir ama K compaction devam eder; görüntü kanonik veri değildir.

Geçici trend selected handles+fiyat etiketleri, endpoint mouse drag ve Undo change point geri bildirimi kaydedildi. Tek nokta değişimi koordinat formuyla doğrulandı; iki ordinary-CDP PNGsi ayrı etiketlendi. Helper round-trip süresi UI latency değildir. Logical barlar negatif olabiliyor ve eski Fib indeksleri1 farklı okundu; kullanıcıya bar konumu gösterilse de persistence timestamp/grid ile tanımlanmalı. Görseller attached desktop örneği, responsive/touch kabulü değil.

## D07–D09 ek: üst-zaman kimliği ve log sürükleme

[UTC/drag/HTF turu](REA-UTC-DRAG-HTF-RESOURCES.md), reports/rea-chart/utc-drag-htf-visual-manifest-20261111.json. Grafik1h ile BB ·1D başlığı farklı hesap aralıklarını görünür ayırıyor; tablo/Data window aynı kimliği korumalı. Timeframe seçimi normal focus/Enter ile doğrulandı, önceki D08 seçim engeli BB için kalktı. WaitON gap/blank, WaitOFF carried/developing değerleri tek sıfır/aynı tazelik olarak sunulmamalı. Ürün etiketi hesap aralığı ve confirmed/developing bağlamını taşımalı.

Log trendde selected handles/fiyat etiketleri ve Undo move drawing(s)/Redo geri bildirimi sayısal hareketle birlikte incelendi. Escape sırasında keep referansta gözlendi; bizim iptal politikamız açık ürün kararıdır.1920×900 ordinary pointer ve1920×970 REA görüntüleri ayrı cohort; pixel/responsive/touch kabulü verilmez.15sn heap/listener gözlemi görsel akıcılık veya frame p95 ölçümü değildir.

## D10 — Mıknatıs ve çoklu seçim geri bildirimi

[Canlı araştırma](REA-SNAP-SELECTION-INTERRUPTIONS.md); reports/rea-chart/snap-selection-visual-manifest-20261111.json içinde20 PNG. Magnet-on göstergesi ile Weak/Strong tercihi ayrılmalı; bilgi bildirimi odak/canvas girdisini ele geçirmemeli. Altı örnekte OHLC snap tick hizasından ayrı görüldü. Yakın/far aday fiyat ve snapped OHLC görsel geri bildirimi tasarlanmalı; kesin bot fiyatı UI metninden üretilmez.

Gövde0px cursor pointer,4/8/16 crosshair tek-cohort örneği; hit shape, görünür2px çizgi ve touch hedefi ayrı kabul. Selected handles, renkli fiyat/zaman etiketleri ve iki mavi tree satırı gözlendi. Aynı çoklu seçimde bir Lock ve bir Unlock ikonu: selection/lock bağımsız durumlar. Ortak toolbar ve context komutlarının hangi nesnelere uygulanacağı ürün sözleşmesinde açık olmalı. Mixed grup drag henüz doğrulanmadı.

Sağ panelde mouseup ve owned-tab geçişi commit/Undo örnekleri, gerçek pointercancel veya OS blur kabulü değildir. Masaüstü1920×970 görüntüler ürün pixel parity, gerçek touch veya frame p95 testi sayılmaz.

## D11 — Hassasiyet, inaktif çıktılar ve zaman bağlamı

[Mixed/hassas gösterge turu](REA-MIXED-PRECISE-INDICATORS.md), reports/rea-chart/mixed-precise-visual-manifest-20261111.json. Mixed pointer hareketinde kilitli çizimin konumu ve seçili görünümü korunur; serbest çizim değişir, tekUndo ikisini başlangıç durumunda tutar. Ortak toolbar etki alanı editable nesnelerle açıklanmalı. İlk uzun-hover bilgi kutulu giriş başarısızdı; hover kartı hit/drag alanını beklenmedik kapatmamalı.

Precision8 ATR eksen etiketlerini büyüttü ve plot alanı değişti; fiyat dönüşümünde sabit eksen genişliği varsayılmaz. Kullanıcı varsayılan okunabilirlik ve ayrıntılı sayısal inceleme ayrı tercih. RSI divergence kapalıyken4 output sütunu boş kaldı; disabled/inactive sıfıra çevrilmez. GoTo marker, kilitli crosshair ve Data window tarih+saat birlikte okunmalı; istenen tarih gerçek veri bağlamının kanıtı değildir.

TablePageDown satırları taşımadı, keyboard scroll kabulü verilmedi. Scrollbar track eski56 satırı getirdi; hedefleme/klavye erişimi açık.18 desktop PNG responsive/touch/performance parity sayılmaz.


## D12 — Coin/aralık geçişinde bağlam ve hazırlık

D13 devamı [gösterge sınırları raporundadır](REA-INDICATOR-BOUNDARIES.md): numeric0/100, unavailable/warmup, inactive, missing_source, runtime_error ve stale ayrı görsel/veri durumlarıdır. Length10000 RE10004 ile length3000 boş/hatasız legend/Data window karşılaştırıldı; ikisinde de ad ve ayar korunur, boş çıktı0'a çevrilmez. Self-ratio flat RSI100 ile ürün50 farkı açık hesap kararıdır; formatter farkı değildir. reports/rea-chart/indicator-boundaries-visual-manifest-20261111.json içindeki5 hash doğrulanmış görüntü durum referansıdır, pixel/responsive/performance kabulü değildir. Session-disconnected bildirimi kapanmış mumun seçili verisini canlı quote ile karıştırmama gereğini gösterir; Connect sonrası toparlanma bu tur doğrulanmadı.

[Geçiş turu](REA-TRANSITIONS-REVISION-READINESS.md), reports/rea-chart/transitions-visual-manifest-20261111.json. İki kohortta eski revizyon verisi yeni istek sonrası geldi; coin dönüşünde yeni BTC Canvas ve fiyat kaynağı varken çizimler henüz listelenmedi. Bu, son ekranın doğruluğundan ayrı ara durum kabulüdür.

Ürün kararı: market/indicator/drawing readiness ayrı; yüklenmeyen çizim ağacı boş kayıt/silme anlamı taşımaz. Header, legend, fiyat ekseni, crosshair ve veri penceresi aynı aktif bağlamda tutulur. Tutulan eski görüntü için bağlam ve yükleme açık görünür; eski tutamaklar yeni markete yazamaz. Placeholder ve hata durumları panel boyutunu/odağı gereksiz sıçratmaz. Referansın bütün ara kareleri veya aktif guard yolu doğrulanmadı; bu metin türetilmiş tasarım kabulüdür. Final BTC1D/UTC, dört çizim gizli ve kayıtlı. Pixel/FPS/responsive eşitliği iddia edilmez.


## D14 — Araştırmadan ürün kabulüne

[Son tur](REA-FINAL-NETWORK-DESIGN.md) gerçek CSS1536/1280/1024 genişliklerini doğruladı;1024 transient boş plot, stabil responsive kabulü değildir. Trace0 DrawFrame olduğundan frame p95/FPS yok. [REA04](REA04-IMPLEMENTATION-ROADMAP.md) ile G01/G02/G03 ve QA01 sahipliği kesinleşti; tasarım uygulamada her işle birlikte teslim edilir. Kapalı panel/plot önceliği, aynı market/revision header–legend–Data window, warmup/error/0 ayrımı, gerçek viewport/DPR ve durum doğrulamalı performans ölçümü zorunlu. D01–D06 tasarım izleri bu yeni paketlere bağlıdır; yeni tamamlanmış ürün işi değildir. Makine planı contracts/chart-core-plan-v3.json.
