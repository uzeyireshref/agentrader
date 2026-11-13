# UTC ankraj, log sürükleme, üst-zaman hesabı ve kaynak gözlemi

11 Kasım 2026, yaklaşık 02:00–02:27 UTC. REA03 canlı araştırması; ürün uygulaması değildir. Ana referans TradingView REA Araştırma, Chromium 157.0.8103.50. Sayısal/etkileşim ve tasarım aynı turda incelendi. Önceki raporların açık maddeleri aşağıdaki dar kapsamda güncellenir; eski gözlemler silinmez.

Kanıt paketi: reports/rea-chart/rea-evidence-utc-drag-htf-20261111.json — **106 kayıt, 21.183.555 byte**; önceki89 kayıt dahil, bu tur17 yeni kayıt. Paket unknowns=0, bütün araştırmanın eksiksiz olduğu anlamına gelmez. Ordinary-CDP kayıtları ayrı dosyalardır ve REA Evidence diye etiketlenmez. Görseller: reports/rea-chart/utc-drag-htf-visual-manifest-20261111.json; 3 REA +2 ordinary-CDP PNG, hash ve gerçek boyutlarıyla.

## 1. Fib'in kalıcı zamanı ve görünen bar numarası

Önceki FIB-BAR-INDEX-DRIFT-001,187/249→186/248 farkını açık bırakmıştı. tools/rea/capture-layout-anchors.mjs, yalnız gözlenmiş kendi araştırma düzeninin sources yanıtını ve başlangıç fiyat serisinin sayısal sınırlarını süzdü. Açık Page.reload ve değişen loaderId gerçek document yüklemesini doğruladı. Cookie/header/token/auth mesajı, tam layout veya tam mum gövdeleri kaydedilmedi. Bu dar ordinary-CDP gözlemi reports/rea-chart/saved-fib-anchor-source-20261111.json ve current-anchor-and-series-20261111.json içinde; REA koordinat okuyucusu ev_3cb7fdc0ea9b4102fb6768c4149600413c07e3c5036402cc19ea715085188adc ile desteklenir.

İki ayrı güncel sources okumasında aynı7185-byte yanıt özeti SHA256 5ee67a441905ab170acb0c0d62a036f8fca3ec0dfebacad64645cd17a3a0d8e0 ve aynı Fib noktaları bulundu:

| UTC ankraj | time_t (saniye) | offset | fiyat | güncel bar |
| --- | --- | --- | --- | --- |
|2026-07-21 00:00 |1784592000 |0 |60000 |186 |
|2026-09-21 00:00 |1789948800 |0 |80000 |248 |

Başlangıç create_series isteğinde300 mum/1D; timescale_update içinde300 nokta, index0–299, ilk2026-01-16/son2026-11-11 UTC görüldü. Bu kesintisiz günlük örnekte (time_t−1768521600)/86400 tam186/248 verir. **Kalıcı UTC ile pencereye bağlı logical index farklı kavramlardır.**

Eski187/249 kanıtının URL hash zamanı2026-11-10T20:09:25.227Z, güncel gözlem sonraki UTC gündedir. Aynı tarih ankrajları varsayılırsa önceki300 günlük pencerenin başlangıcı15Ocak olur ve farkı açıklar. Ancak önceki raw time_t ve ilk seri sınırı o anda alınmadığından **geçmiş farkın gün dönümü açıklaması çıkarımdır**. Güncel UTC depolama ve mapping doğrulandı; geçmiş iki tarih noktasının eşitliği doğrudan kanıtlanmadı. Fib indeksleri geri yazılmadı.

Aktarım: Anchor.time zaten frontend/src/drawings.ts içinde mevcut. timeToLogical bunu grid'e çeviriyor; T02 yeniden açılmaz. T07/T12/P3 kabulüne history prepend/pencere değişimi ve market bağlamı eklenir.300 mum referansın bu örneğidir, ürün geçmişi limiti değildir. Seanslı/boşluklu grid'de elapsed-day bölmesi kullanılmaz. Hesap kaydı: reports/rea-chart/utc-anchor-window-fixture-20261111.json.

## 2. Gerçek log gövde sürükleme ve doğrudan Undo/Redo

REA doğrudan drag sunmadığı için tools/rea/research-body-drag-cancel.mjs, boş spot BTCUSDT/1D üzerindeki tek geçici trendle normal mouse/key/CDP erişilebilir kontrol yolunu kullandı; sayfa JS'i veya gizli uygulama state'i çağrılmadı. Orijinal perpetual çizimleri sürüklenmedi. Logarithmic eksen işareti REA ev_8e9d81181a5b2c14312e890cddf22008995a978490483f9aa048fc9da2ce7d03 ve PNG ile doğrulandı.

| Nokta | Gövde öncesi fiyat / bar | Gövde sonrası | Doğrudan Redo sonrası |
| --- | --- | --- | --- |
|1 |78821.52 /195 |80460.60 /204 |80460.60 /204 |
|2 |69129.27 /248 |70566.81 /257 |70566.81 /257 |

Her iki bar+9; fiyat farkları1639.08 ve1437.54. Fiyat çarpanları1.0207948286 ve1.0207949541; iki ondalık gösterim belirsizliğiyle ortak çarpan aralığı [1.0207948079883664,1.02079495680843]. Log gövdede eşit fiyat eklemek bu gözlemi karşılamaz. Bu, renderer dönüşüm uzayında hareket planının T13'e eklenmesini gerektirir; tüm araçlar için formül ispatı değildir.

Toolbar Undo move drawing(s) gösterdi. Ctrl+Z ardından **araya ayar okuyucusu sokmadan** Redo move drawing(s) tıklandı; Redo sonrası koordinatlar gövde sonrasıyla aynı. Önceki rapordaki okuyucu-Cancel sonrası Redo eksikliği bu yeni doğrudan örneği geçersiz kılmaz, eski akış da başarılı sayılmaz.

Aktarım: drag.ts moveGeometry ve DrawingLayer.tsx şu an additive priceDelta taşır. Mevcut lineer çekirdek tamamlanması korunur; log body translation T13 kapsamında ayrı sürümlü davranış/fixture gerektirir. Ham piksel veya UI yuvarlaması botun kesin fiyat kaynağı olmaz.

## 3. Escape sırasında sürükleme ve ürün kararı

Aynı trendin ikinci ucu fare basılıyken taşındı, Escape basıldı, fare bırakıldı. Sonuç ilk nokta80460.60/bar204 sabit, ikinci72966.83/bar267. Escape rollback yapmadı; toolbar Undo change point. REA koordinatları ev_500015b9b6cb2ca263f4f73e1b8ad8d068104d839132a54af8a15470ef9f0a68; sonraki tekUndo ikinci noktayı70566.81/bar257'ye döndürdü: ev_b2d2c1820c36e55619772a20f5fdbd6705c6bd60f066e3cd1994d67e09c86a0a.

Bu olay browser pointercancel, blur, lost capture veya bütün araçlar için iptal kabulü değildir. Bizim DrawingLayer Escape/blur preview rollback içeriyor; referansın keep davranışı otomatik kopyalanmayacak. T07/QA01'de ürünün Escape=iptal kararı açık tanımlanacak; tek history commit ve pointer capture cleanup kabulü doğrulanacak. Tasarım eşdeğer kalite hedefi her referans davranışının birebir taşınması demek değildir.

Ordinary kayıt: reports/rea-chart/trend-body-cancel-20261111.json; türetilmiş hesap: log-body-escape-fixture-20261111.json. Mousefinally bırakıldı, helper error=null. Geçici trend BB-HTF setup ev_e0ca78f0ed60e1d3e896026a40e5717a77c1e8050d06d8d57f690ff569d0fb53 sırasında silindi, sonra perpetual'a dönüldü.

## 4. BB günlük hesap → saatlik grafik: Wait ON/OFF

Önceki üst-zaman seçim engeli çözüldü. reports/rea-chart/select-bb-calculation-timeframe.mjs sadece açık BB Inputs dialog'unun üçüncü combobox'ını normal focus/Enter ile seçer. Hesap1day ve sonra Chart restore başarılı. VWAP için aynı deney henüz yapılmadı.

BINANCE:BTCUSDT.P/1h/UTC; BB20/SMA/close/2/offset0, Calculation1day. Wait ON kanıtı ev_78e0b598c26bdff439794c8cdb86ae93d4145e4b658247257f97ff4754947c34; OFF ev_94c361fb971fa86b4ae4978bfda4350204a2368946d137dcd7f0dbfbdd2894d4. ON33/OFF32 erişilebilir tablo satırı; **31 ortak kapalı saatin OHLC/change/görüntü hacmi aynı**.02:00 açık mum canlı değiştiği için eşitlik karşılaştırmasından çıkarıldı.

| Saat UTC | Wait ON BB Basis/Upper/Lower | Wait OFF |
| --- | --- | --- |
|10Kasım22:00 |∅ /∅ /∅ |78675.1 /83661.3 /73689.0 |
|10Kasım23:00 |78160.8 /82941.1 /73380.4 |78160.8 /82941.1 /73380.4 |
|11Kasım00:00 |boş |78160.8 /82941.1 /73380.4 |
|11Kasım01:00 |boş |78160.8 /82941.1 /73380.4 |
|11Kasım02:00, canlı |boş |77753.8 /82748.3 /72759.2 |

ON örneğinde günlük sonuçlar yalnız gözlenen23:00 kapanış saatlerinde çıktı; geçmiş aralar açıkça∅, yeni gün satırları blank hücrelerdi. OFF geçmiş saatleri son tamamlanmış günlük değerle dolduruyor; canlı02:00'da gelişmekte olan günlük değer var. Nov9/Nov10 günlük sonuçlar önceki bağımsız BB20 kapalı-gün fixturelarıyla aynı görüntü hassasiyetinde eşleşiyor. Bu, bütün tarih yeniden yüklemelerinde repaint yoktur veya tüm HTF'ler aynıdır iddiası değildir. API'nin gap/lookahead seçeneklerine otomatik eşleme yapılmaz.

Aktarım T08/T09/P4: chart_interval ve calculation_interval ayrı; hesap mumunun UTC başlangıç/bitişi, confirmed/developing durumu, kaynağı ve gösterim fill politikası veri sözleşmesinde bulunmalı. Doldurulmuş eski değer yeni hesap/kapanış sayılmamalı. OFF botun kapanmış günlük değer şartını gevşetmez. Null/∅/hidden/missing farklı anlam taşıyabilir; neden taşınmalı. Kayıt: reports/rea-chart/bb-htf-wait-fixture-20261111.json.

## 5. Tasarım aynı turda

D07/D08/D09 genişledi. Legend ve tablo başlığı grafik1h iken **BB ·1D** gösteriyor; hesap bağlamı başlıkta görünür olmalı. Timeframe dropdown'u mouse yanında klavye/focus ile erişilebilir olmalı; seçili değer, Wait checkbox ve gruplu ayarlar birlikte okunmalı. D07 tabloda sağ Data window kalıyor, kaynak/alan başlıkları ayrılıyor, sayılar sağa hizalı; alt yatay alan taşması önceki sınır olmaya devam ediyor. Bu PNG'de ilk saatler ve BB üç sütunu görünür, tüm veri satırları aynı anda ekranda değildir.

Trend selected handles/fiyat etiketleri, log eksen işareti, Undo/Redo fiil adları ve Escape sonucu sayısal kanıtla birlikte kaydedildi. Pointer cohort gerçekCSS1536×720, PNG1920×900; REA ek görüntüler1920×970. Farklı boyutlar karıştırılarak pixel parity veya responsive kabulü verilmez. Gerçek touch ayrıca açık.

## 6. Kaynak ölçümü ve performans sınırı

reports/rea-chart/quiet-resource-window-20261111.json,15 saniye girdisiz spot1D/Volume+BB20/tekseçili trend sahnesi. CSS viewport1536×720, scale1/zoom1.0. REA durum ev_0002ac265b33b340f68cb6e905cb71b7fd607009056e795180eedae6a2bb3859.

| Zaman | JS heap used byte | DOM nodes | JS listeners |
| --- | --- | --- | --- |
|0sn |71264652 |4405 |5900 |
|5sn |70491212 |4408 |5900 |
|15sn |71552916 |4426 |5900 |

Heap düşüp yükseldi; zorunluGC yok. Renderer40documents saydı; platform/ads/detached document içerir,40 grafik sekmesi değildir. Body helper öncesi/sonrası sayaçları ayar dialog/history açılışlarını da içerir.15sn veya tek gesture **leak yok/var** sonucuna yetmez. CDP round-trip süreleri UI latency değildir. Frame p95/FPS ölçülmedi, bizim ürünle ortak workload benchmark yapılmadı.

QA01 için kabul tasarımı: gerçek viewport/DPR ve cihaz; sabit veri/çizim/pane yükü; ısınma; ayrı input/frame timing; tekrarlı mount/edit/unmount; son cleanup sonrası karşılaştırılabilir resource kohortu; hata/socket/listener takibi. Referansın heap/node sayısı ürün hedefi yapılmaz.

## 7. Sıralama, aktarım ve son durum

Araştırma sırası PLAN.md üstünde güncellendi: kalanpointer snap/hit/cancel/mixed seçim → hesap/veri sınırları ve request race → ortak performans/masaüstü tasarım durumları → REA04 seçilmiş uygulama planının konsolidasyonu. Platforma kontrollü sabit seri yüklenemeyen seed/flat senaryolarında iddia daraltılacak; sonsuz menü taraması bitiş şartı olmayacak. EMA/ATR başlangıç seed, exact VWAP volume, gerçektouch, tam offline ve race hâlâ açık.

Son durum ev_139a7f566384bb9c597c6d6da36abb38911a02a99ddd214c44661349b03efed1 ve ev_b635e959b8732afdacecc6408be42f10700b4400652c3552d19d0970e7f6ad5b: BTCUSDT.P/1D/UTC, Volume Default korunmuş, BB20/SMA/close/2/offset0/**Chart/WaitON** gerçek reload sonrası Inputs ile tekrar doğrulandı. Dört orijinal çizim global gizli, spot geçici trend silinmiş; probe query kaldırıldı; dialog kapalı ve All changes saved. Hiçbir product dosyası değiştirilmedi; uygulama testleri bu araştırmada çalıştırılmadı.5/21 tamamlanma korunur; REA03 devam, REA04 taslak.

Yeniden hesaplama/doğrulama: tools/rea/verify-utc-drag-htf-research.mjs.31 araştırma fixture'ı ürün testlerinin PASS sayısı değildir.

Doğrulama sonucu: reports/rea-chart/utc-drag-htf-validation-20261111.json. İki UTC mapping, ortak log çarpan aralığı, doğrudan Redo, Escape sonrası Undo,31 kapalı OHLCV satırı, günlük BB karşılığı,5 PNG hash/boyutu ve son Chart/WaitON/saved durumu yeniden kontrol edildi. Bu araştırma doğrulamasıdır; ürün testleri çalıştırılmadı.
