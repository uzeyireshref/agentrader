# Grafik çekirdek geliştirme planı — v2 + REA araştırma kapısı

10 Kasım 2026. T01, T02, P2, P3 ve T03 tamamlandı; **sıradaki iş REA03: bütün grafik envanteri ve ayrıntılı işlev/tasarım analizi; uygulama sırası REA04 ile yeniden belirlenecek**. Tarihsel uygulama kanıtı: 735 Python / 161 frontend testi, üretim derlemesi ve 11 gerçek App/HTTP/SQLite cetvel kontrolü. Bu canlı araştırma turunda bu testler tekrar çalıştırılmadı.

## 11 Kasım — güncel araştırma sırası ve kapanış koşulu

**En yeni tur: [gösterge sınırları](REA-INDICATOR-BOUNDARIES.md).** 8 korunmuş inline+13 export=21 bu tura ait REA kaydı; önceki82 ayrı korunur. Toplam47 araştırma fixture’ı. Sentetik self-ratio tabloda32 kapalı günlük satır RSI14=100; mevcut saf ürün fonksiyonu sabit girdide50. RSI1/SMA1 için30 kapalı komşu karşılaştırması14 yükseliş100/16 düşüş0. Length10000 runtime RE10004 ile length3000 boş/hatasız görüntü ayrıldı. Hidden numeric capture başarısız; origin seed/NA/zero volume hâlâ açık. GeçiciRSI kaldırıldı, BTC1D/UTC özgün4 çizim gizli ve kayıtlı. Session-conflict görüldü; Connect kullanılmadı, kesintisiz live kabulü verilmedi.

[Son geniş tur](REA-TRANSITIONS-REVISION-READINESS.md):82 REA kayıt (önceki72 dahil,10 yeni), toplam44 araştırma fixture’ı. Seri5 ve hızlı6 aralık seçiminde eski revizyonun yeni istekten sonra276ms/111ms gelişleri yakalandı. Üç coin geçişinde market görünümü ve çizim restorasyonunun farklı hazırlık anları görüldü. İki yüklü kaynak hash’iyle turnaround decoder ve statik bileşen guard incelendi; ana grafik aktif handler ve bütün ara renderların korunması henüz kanıtlanmadı. Önceki hassas hesap bulguları korunur; ürün testi sayısı değildir.

1. **Kalan veri ve hesap riskleri:** sıradaki geniş tur bağlantı/toparlanma; coin/interval geçişinde geç yanıt gelişi doğrulandı, ara render/async commit, cached source provenansı ve reconnect/catchup kabulü açık. EMA/ATR origin seed/warmup ve RSI NA hâlâ açık; flat display100 / ürün50 farkı artık canlı sentetik örnekle destekleniyor, ürün kararı REA04’te. VWAP zero-volume/DST/HTF seansları açık. Kontrollü platform girdisi yoksa açık sınırlama ve deterministik ürün kabul fixture’ı tanımlanır; aynı başarısız numeric capture sınırsız tekrarlanmaz.
2. **İptal kabulü ve etkileşim sınırları:** iki-trend mixed-lock mouse hareketi doğrulandı. Kontrollü touchStart timeout nedeniyle gerçek pointercancel/lost capture/OS blur hâlâ bilinmiyor; yeni aynı denemeler yerine QA01 rollback/cleanup/history kabulü izlenir. Nested/mixed-tool gruplar, canvas multi-selection, genel snap/hit radius ve gerçek touch ayrı açık kalır.
3. **Performans ve masaüstü tasarım kabulü:** uygulama öncesi referans baseline; ürün geliştirmede QA01 ile ortak workload/cihaz/gerçek viewport-DPR, frame p95 ve tekrarlı cleanup; mevcut15sn resource örneği benchmark/leak kabulü değildir. Dialog/legend/pane/error/focus ve responsive durumları birlikte doğrulanır. Gerçek touch ayrı açıktır.
4. **REA04 konsolidasyonu:** profesyonel temel/ileri/şimdilik gereksiz kapsamı, yeni grafik kabuğu/pane/veri penceresi paketleri ve eski T/P bağımlılıkları tek uygulama sırasına bağlanır. Her TradingView menüsünün taranması şart değildir; önemli açıkların kanıtı veya açık risk/fixture kararı gerekir.

REA03 devam, REA04 taslak; ürün uygulaması başlamadı. Önceki5/21 tamamlanma korunur. Tarihsel uygulama test sayıları bu tur yeniden doğrulanmadı.

## Son kullanıcı kararı — profesyonel ve seçilmiş kapsam

[Profesyonel grafik kapsamı](PROFESSIONAL-CHART-SCOPE.md) önceki kapsam yorumlarının üstündedir: mevcut araçlarla sınırlanmayan geniş araştırma, ardından temel/ileri/şimdilik gereksiz ayrımı. TradingView’deki her özelliği ürüne dahil etme hedefi yoktur. Seçilen profesyonel ihtiyaçlarda ayrıntılı işlev ve tasarım analizi yapılır; REA04 buna göre eski 21 paketi genişletir ve yeniden sıralar.

## Kullanıcı kapsam düzeltmesi — tam grafik analizi

10 Kasım 2026: araştırma mevcut araçlarımız ve önceki çekirdekle sınırlandırılmayacak. [Bütün grafik kapsamı](REA-FULL-CHART-SCOPE.md) bu planın önceki kapsam/sıra sınırlamalarından üstündür. TradingView grafik ortamındaki bizde bulunmayan araçlar, göstergeler, grafik türleri, paneller, layout/pane, veri/etkileşim ve görsel sistem de ayrıntılı incelenecek. Önce tam yetenek envanteri ve araştırma fişleri, sonra mevcut projeyle eşleme ve yeni yol haritası. Önceki 21 paket korunmuş başlangıçtır; kapsam tavanı ve kesin sonraki sıra değildir.

Tasarım hedefi [görsel şartnamede](REA-DESIGN-SPEC.md) tanımlıdır ve çekirdek teslimlerin parçasıdır. Önceki “tasarım sonraya” kararı kaldırılmıştır. REA03 devam ediyor; REA04 geniş envanter sonrası kesinleşecek. Giriş tamamlandı; REA Araştırma düzeninde long/short ve Fib örnekleri incelendi. Endpoint ve log gövde sürükleme/Undo-Redo sınırlı örneklerde doğrulandı; OHLC snap ve tree Ctrl/mixed seçim sınırlı örneklerde doğrulandı; mixed iki-trend hareketi doğrulandı; gerçek pointercancel, veri sınırları, ortak performans ve seçilmiş envanter kabulü hâlâ açık.

## 10 Kasım 2026 — REA ile referans analizine geçiş

Kullanıcının yeni sırası: REA reposunu indir/kur → Binance veya TradingView grafiklerinden daha iyi incelenebileni seç → ayrıntılı davranış analizi → mevcut grafiğe aktarım planı → sonraki aşamada uygulama. Önceki 5/21 tamamlanma ve kanıtlar korunur. Aşağıdaki dört araştırma işi 21 çekirdek paketten ayrı izlenir; REA01 ve REA02 tamamlandı; REA03 sürüyor, REA04 taslak. T04 ve sonraki uygulama işleri REA04 bitene kadar başlamaz.

| ID | İş ve teslim | Durum / kabul |
| --- | --- | --- |
| REA01 | Resmî morluto/rea kaynağı, commit/hash/lisans kaydı; izole kurulum; CLI help, Codex/skill doctor ve analiz işçisi/MCP çalışma doğrulaması | TAMAMLANDI. Resmî npm 6.8.0, izole Node 22.23.4; CLI, JavaScript analiz işçisi, Codex/skill doctor ve gerçek stdio MCP (229 araç) geçti. Canlı CDP/web bağlantısı sonraki REA02/REA03 turlarında doğrulandı. |
| REA02 | Aynı Binance USD-M sembolü ve zaman diliminde Binance grafik modu ile TradingView grafiğinin karşılaştırmalı incelemesi | TAMAMLANDI. Erişim/araç keşfi ve kaynak görünürlüğü karşılaştırıldı; ana araç referansı TradingView, piyasa/veri bağlamı Binance. Ortak kapalı mum parity ve performans eşitliği doğrulanmadı; seçim bunlara dayanmaz. |
| REA03 | Seçilen referans için aşağıdaki davranış ve hesap matrisi; REA bulguları ve tekrar üretilebilir örnekler | DEVAM EDİYOR. Ayrı araştırma düzeninde sayısal/geometrik ve tasarım envanteri, BB finite-window ve kısmi EMA/ATR/RSI/VWAP araştırması, açık/kapalı mum ve market ayrımı incelendi. UTC ankraj/pencere mapping, tek endpoint ve log gövde/Undo-Redo, BB1D→1h WaitON/OFF doğrulandı. İki-trend mixed hareket, hassas hacimle VWAP ve ATR gap örneği doğrulandı. Gerçek pointercancel, seed/NA/zero volume, race sırasında bütün render/commitlerin korunması ve ortak performans açık; tam vendor parity iddia edilmez. |
| REA04 | Bulgular → mevcut modül → T/P paketi eşlemesi; farklar, bağımlılıklar, kabul fixtureları ve uygulama sırası | TASLAK. Bulgular mevcut modüllere eşlendi; REA03 kabulü sonrası kesinleştirilecek. T04 henüz başlamaz. |

### Referans seçimi ve kanıt toplama

TradingView ana grafik referansı olarak seçildi; ilk aday karşılaştırması REA02 kaydındadır. Binance mevcut USD-M veri kaynağıyla uyumlu karşılaştırma adayıdır. Binance içindeki farklı grafik modları ayrı kaydedilir. Spot/futures, last/mark/index ve mum zamanları eşleşmeden sayısal fark hata sayılmaz. Aynı veri bulunamazsa etkileşim karşılaştırması yapılır; hesap eşitliği iddia edilmez.

Her bulgu: kimlik, URL/mod/sürüm veya bundle hash, UTC zaman, sembol/product/price source/interval, viewport/DPR, adımlar, girdi, beklenen-gözlenen sonuç, ekran/JSON/REA kanıt yolu, güven ve kısıt alanlarını taşır. REA çıktısı iç uygulamanın eksiksiz kaynağı olarak sunulmaz. Herkese açık istemci davranışı ve edinilebilen istemci kaynakları incelenir; gizli sunucu uygulaması bilinmiyor kalır. Üçüncü taraf kaynak kullanımı ayrıca lisans/provenans kaydı gerektirir.

### Ayrıntılı inceleme matrisi

1. Grafik çekirdeği: mum/OHLC/hacim, crosshair, fiyat hassasiyeti, zaman/UTC, boşluk ve bar indeksleme; zoom/pan/trackpad, auto-fit, sağ boşluk, fiyat ekseni, resize/DPR, lineer/log.
2. Araç etkileşimi: oluştur/seç/tutamak/gövde sürükle, snap/mıknatıs, kilitle/gizle/kopya, Escape/blur/iptal, undo/redo, görünürlük, sayısal edit, kaydet/reload. Her araç için durum geçişleri ve sınır durumları yazılır.
3. Araç hesabı: cetvel fiyat/yüzde/tick/bar/süre; long/short entry-stop-target ve R:R; segment/ray/kanal; Fib ters yön/oran/extension ve log anlamı. Ekran pikseli kanonik fiyat yerine geçmez.
4. Göstergeler: SMA/EMA/RSI/ATR/VWAP için source, seed, warmup, smoothing, açık mum, seans/anchor ve eksik geçmiş. Bilinen kapalı mumlarla bağımsız referans; platform sonucu erişilemiyorsa açık eksik.
5. Veri yaşam döngüsü: history ekleme, açık mum güncellemesi/kapanışı, coin/interval geçişi, reconnect ve stale durumu; yalnız gözlenen istemci davranışı raporlanır.
6. Performans: ortak cihaz/viewport/DPR ve karşılaştırılabilir veri/çizim yüküyle frame p95, bellek, listener/socket ve hata kaydı. Referans yükü kontrol edilemiyorsa eşit benchmark sonucu verilmez.

### Mevcut projeye aktarım

App.tsx ve chartNavigation.ts/chartKeyboard.ts: terminal ve navigasyon; DrawingLayer.tsx/interaction.ts/drag.ts: etkileşim; exactGeometry.ts ve backend kanonik hesap: geometri; ruler.ts: T03; indicators.ts: T09–T11; useDrawings.ts: kalıcılık/409; types.ts/evidence.ts/freshness.ts: veri doğruluğu. Dosya eşlemesi başlangıç envanteridir; REA03 bulgularıyla doğrulanır.

T04–T14 eski bağımlılık başlangıcıdır; kesin uygulama sırası REA04 ile yeniden belirlenecek. Grafik kabuğu/tasarım, pane/scale ve veri penceresi altyapısı yeni sırada açık iş paketleri olmalı. Her pakete bulgu kimliği, fixture, negatif senaryo ve masaüstü kabulü eklenir. T01/T02/P2/P3/T03 yeniden sıfırlanmaz; fark bulunursa ayrı regresyon işi açılır. Bot P4–P7 ve QA01 mevcut sınırlarını korur. Bu araştırma aşamasında grafik ürün kodu değiştirilmez.

Kurulum kanıtı: [REA durum kaydı](../../reports/chart-rea-setup-20261110.json). Kaynak: [resmî REA](https://github.com/morluto/rea), yerel kurulum belgesi tools/rea/docs/getting-started/installation.md. Süreç başlatma engeli yetkili çalıştırmayla aşıldı; izole Node/npm ve REA kurulumu doğrulandı. Codex kaydı ve skill kuruldu; açık sohbetin MCP araçlarını yüklemesi yeniden başlatma gerektirir, CLI hazırdır. REA02 için CDP tarayıcı bağlantısı ve canlı web probe ayrıca doğrulanacak. Native sağlayıcı eksikleri statik JavaScript analizini engellemez. Canlı REA araçları yeniden başlatma sonrası bu oturumda kullanılabildi. İlk ters mühendislik turu ve sınırları [referans raporunda](REA-REFERENCE-ANALYSIS.md); tam REA03 kabulü açık. Bu plan düzenlemesinde uygulama testleri çalıştırılmadı; eski test sayıları tarihsel kanıttır.

## Durum ve kapsam

Eski A–E planı [değiştirilmeden arşivlendi](PLAN-v1-20261110.md):24/25 tamamlandı, B5 kullanıcı isteğiyle ertelenmiş/açık. Bu sayı yeni özelliklerin hazır olduğu anlamına gelmez. P1 kesin ondalık taşıması tamamlandı:686 Python/131 frontend/21 wire kontrolü. Bu plan değişikliğinde testler tekrar koşulmadı.

Yeni kapsam **21 iş paketi, 5/21 tamamlandı**; bunlar takvim/süre tahmini değildir. T01/T02 ve P2/P3 mevcut altyapıyı tamamlar; önceki işleri sıfırlamaz. Kullanıcı tarafından onaylanan kabul hedefi masaüstü fare/klavye/trackpad. Gerçek dokunmatik D08/D09 ayrı açık iş, başarılı sayılmaz. Tasarım işlevsel kaliteyle birlikte teslim edilecek; geniş kapsam düzeltmesi üstündür.

Hedef araçlar: fiyat-zaman cetveli; long/short planı; ray/uzatma/paralel kanal; çizim kilit/gizle/kopya/görünürlük; ayarlanabilir göstergeler ve SMA/EMA/RSI/ATR/VWAP;1m/5m/30m; ayarlı Fibonacci/extension; lineer/log ölçek; çalışma alanı şablonları. Güncel profesyonel kapsamda MACD/Bollinger ve metin/etiket temel ihtiyaçlara alındı; eski 21 paket bu ek işleri içermediğinden toplam ve sıra REA04 içinde yeniden sürümlenecek. Daha özel araçlar koşullu ileri kapsamdır. Botun desteklenen araçları aynı anlam ve hesapla okuyabilmesi çekirdeğin bitiş koşuludur.

## Sıra ve teslimler

| Grup | İzlenecek sıra | Sonuç |
| --- | --- | --- |
| Temel | T01 → T02 → P2 → P3 | Araç sözleşmesi, kanonik hesap, saat/epoch/kalite |
| İlk araçlar | T03 → T04 → T05 → T06 → T07 | Cetvel, risk planı, uzatmalar/kanal, çizim yönetimi |
| Hesap ve bağlam | T08 → T09 → T10 → T11 → T12 → T13 → T14 | Timeframe, göstergeler, VWAP/Fib/log ve şablonlar |
| Bot uyumu | P4 → P5 → P6 → P7 | Revision bağı, uygunluk, kalıcı olay ve izole replay |
| Kabul | QA01 | Güncel masaüstü kabulü ve doğrulanmış yeni aday |

REA01 → REA02 → REA03 → REA04 kapısından sonra bu tablo varsayılan tek uygulama sırasıdır; bağımlılık grafiğinde bazı işler daha az bağımlı olabilir. Sırayı değiştirmek için somut ihtiyaç ve kayıt gerekir; otomatik paralel çalışma talimatı değildir.

## T01 — Ortak araç sözleşmesi ve yetenek kaydı

Durum: TAMAMLANDI; 22 tür için yetenek kaydı, mevcut dört çizimin sürümlü okuma sözleşmesi ve 11 yeni test dahil 697 Python testi geçti. [Kapsam](TOOL-CONTRACT.md). Bağımlılıklar: P1.

Mevcut dört çizim dahil kind/schema/version, anchors/params, source/product/price_type/symbol/interval, zaman kapsamı ve sorgu capabilities; çizim, gösterge, kural ve plan nesneleri ayrılır. Eski strict CRUD için açık yeni sürüm/migration ve backward compatibility planı.

Bitiş koşulları:

- Her çekirdek araç için okunabilir/hesaplanabilir/düzenlenebilir yetenekler açık
- Gizleme, kilit, izleme aktivasyonu ve emir yetkisi birbirinden ayrı
- Desteklenmeyen araç açık hata/BLOCKED verir; eski kayda sessiz anlam değişimi yok

## T02 — Kanonik hesap ve grafik eşleşmesi

Durum: TAMAMLANDI. [Kesin geometri ve kanıt](GEOMETRY.md). Bağımlılıklar: T01.

Decimal/rational geometri ve ölçüm çekirdeği; TS görüntü hesaplarıyla parity fixtures. Grid boşlukları, lineer/log semantiği, canonical hash ve sürükleme/tick girdi yolları tanımlanır.

Bitiş koşulları:

- Yatay/bölge/trend/Fib sonuçları bağımsız referansla eşleşir
- Float gösterimden kesin bot fiyatı türetilmez; form ve drag aynı tick politikasına uyar
- History/grid eksikliği, aralık dışı sorgu ve zaman birimleri test edilir

## P2 — Güvenilir saat ve uzun kesinti

Durum: TAMAMLANDI. [Saat kanıtı ve doğrulama](CLOCK-RELIABILITY.md). Bağımlılıklar: T01.

Mevcut reliability P2: monotonic taşıma yaşı, upstream saat/uncertainty kanıtı, future stamp ve wall-clock jump davranışı.

Bitiş koşulları:

- Taze heartbeat eski upstream veriyi uygun göstermez
- İleri/geri saat sıçraması veya eksik kanıt engellenir
- Uzun kesinti/catchup canlı fırsat üretmez; eşikler sürümlü

## P3 — Epoch ve değişmez piyasa kanıtı

Durum: TAMAMLANDI. [Akış ve immutable veri kanıtı](STREAM-EVIDENCE.md). Bağımlılıklar: P2.

Mevcut reliability P3: stream epoch, snapshot/grid/quality/warmup/continuity kanıtı.

Bitiş koşulları:

- Restart/reconnect snapshot bariyeri
- Tekrar/eski paket ve eksik geçmiş uygunluk üretmez
- Sequence atlaması tek başına veri boşluğu sayılmaz

## T03 — Fiyat/zaman cetveli

Durum: TAMAMLANDI. [Cetvel kapsamı ve doğrulama](RULER.md). Bağımlılıklar: T02.

Fiyat, yüzde, tick, bar sayısı ve gerçek UTC süre ölçümü; sıfır/düşen fiyat yönü ve sonuç sunumu.

Bitiş koşulları:

- Boşluklu grafikte bar sayısı ile süre ayrı hesaplanır
- UI ve kanonik sonuçlar eşleşir; uç değerlerde sessiz yuvarlama yok
- Kalıcı ölçüm seçeneği varsa kayıt/edit/undo/reload doğrulanır

## T04 — Long/short planlama

Durum: BEKLİYOR. Bağımlılıklar: T03.

Entry/stop/hedef ve R:R; opsiyonel risk bütçesi/teorik qty, ücret/kayma varsayımları. Plan emir değildir.

Bitiş koşulları:

- Long/short seviye sırası ve sıfır risk reddi
- Decimal mesafeler ve maliyet dahil/hariç sonuçlar açık
- Plan kaydı/edit/undo/reload; hiçbir hesap/emir API çağrısı yok

## T05 — Ray ve çizgi uzatma

Durum: BEKLİYOR. Bağımlılıklar: T02.

Trend segment/ray/bilateral uzatma, horizontal ray; sonlu/sınırsız zone zaman kapsamı sürümlü.

Bitiş koşulları:

- Başlangıç/son sınırları ve ters anchor doğru
- UI/bot priceAt/contains aynı; eksik grid sessiz extrapolation üretmez
- Eski segment/bölge kayıtları önceki anlamıyla açılır

## T06 — Paralel kanal

Durum: BEKLİYOR. Bağımlılıklar: T05.

Üç anchor veya açık offset ile paralel kanal, orta çizgi ve sınır sorguları.

Bitiş koşulları:

- Paralellik, ters yön ve degenerate geometri testleri
- İçeride/dışarıda/mesafe hesapları aynı referansa uyar
- Tutamak/drag/edit/kayıt/undo/reload doğrulanır

## T07 — Çizim yönetimi

Durum: BEKLİYOR. Bağımlılıklar: T01, T05.

Kilitle, gizle/göster, çoğalt, timeframe görünürlüğü, kalıcı özellikler ve çoklu çizim seçimi ihtiyacının sınırı.

Bitiş koşulları:

- Kilit yalnız edit engeller; hide bot bağını değiştirmez
- Kopya yeni kimlik alır, bot aktivasyonu taşınmaz
- 409/retry/undo/market geçişleri ve farklı timeframe görünümü doğrulanır

## T08 — Zaman dilimleri ve üst-zaman bağlamı

Durum: BEKLİYOR. Bağımlılıklar: P3, T02.

1m/5m/30m ekle; mevcut15m/1h/4h/1d/1w korunur. Üst-zaman kapalı mum bağlamı; çoklu pencere zorunlu değil.

Bitiş koşulları:

- Backend/frontend interval listesi ve UTC bucket tutarlı
- Pagination/warmup/reconnect her yeni intervalde doğru
- Üst-zaman kapanışı erken okunmaz; kaynak/resample provenansı açık

## T09 — Kalıcı ayarlanabilir gösterge modeli

Durum: BEKLİYOR. Bağımlılıklar: T01, T02.

indicator_id/revision, period/source/smoothing/anchor/pane ve workspace ayar kaydı.

Bitiş koşulları:

- EMA/RSI mevcut sonuçları korunur
- UI ve backend bağımsız referans/seed/warmup parity
- Ayar/coin/timeframe/reload ve 50 pane döngüsü regresyonu

## T10 — SMA ve ATR; ayarlı EMA/RSI

Durum: BEKLİYOR. Bağımlılıklar: T09, T08.

SMA ve ATR ekle; mevcut EMA/RSI modeline ayarlar bağla. Eski analysis.py yeniden kullanımı ancak parity sonrası.

Bitiş koşulları:

- SMA/EMA/RSI/ATR bağımsız referans değerleri
- ATR smoothing ve seed açık; açık mum ve warmup eksikliği işaretli
- Eksik bar/veri revizyonu sonrası sonuç güncelliği doğru

## T11 — Seanslı ve anchored VWAP

Durum: BEKLİYOR. Bağımlılıklar: T09, T08.

UTC seans reset ve kaydedilmiş anchor; fiyat/hacim kaynağı ve bar tabanlı hesap tanımı.

Bitiş koşulları:

- Sıfır hacim/anchor öncesi/eksik geçmiş davranışı
- Reset/anchor/reconnect/history sonrası aynı sonuç
- Mum VWAP gerçek trade VWAP olarak sunulmaz; mümkünse exact quote/base seçimi açık

## T12 — Ayarlanabilir Fibonacci ve extension

Durum: BEKLİYOR. Bağımlılıklar: T02, T07.

Kalıcı Decimal oran listesi, ters anchor, seçilmiş extension seviyeleri ve zaman kapsamı; üç noktalı projection ayrı kind olarak sınırlandırılır.

Bitiş koşulları:

- Eski yedi seviyeli kayıt göçü/gösterimi korunur
- Seviye sonuçları Decimal referansla eşleşir
- Tick emir yuvarlaması yapılmaz; sıkışık etiket/drag/undo regresyonu

## T13 — Lineer/log ölçek semantiği

Durum: BEKLİYOR. Bağımlılıklar: T02, T05, T06, T12.

Log görünüm ve trend/channel/Fib anlamı açık sürüm ile; görüntü ve fiyat fonksiyonu birbirine karışmaz.

Bitiş koşulları:

- Ölçek değişiminde anchor fiyatları korunur
- Düz ekran çizgisi ile bot priceAt eşleşir veya desteklenmeyen kombinasyon BLOCKED
- Scale/reload/zoom/raster ve geometry parity testleri

## T14 — Çalışma alanı ve araç şablonları

Durum: BEKLİYOR. Bağımlılıklar: T07, T09, T12.

Araç/gösterge varsayılanları ve workspace preset kaydı; çizim/indicator ayarları toplu geri yükleme.

Bitiş koşulları:

- Şablon bot aktivasyonu veya işlem yetkisi taşımaz
- Market/timeframe geçişinde yanlış kaydı yüklemez
- Version/restore/409 ve eski workspace uyumluluğu

## P4 — Revision bağlı araç/kural tanımları

Durum: BEKLİYOR. Bağımlılıklar: P3, T04, T06, T08, T10, T11, T12, T13, T14.

Mevcut reliability P4 genişleyen araç registry kapsamıyla: binding varsayılan DISABLED, owner/revision/rule/interval/grid/hash.

Bitiş koşulları:

- Edit/delete/undo eski bağı durdurur; açık rebind
- Her desteklenen araç query/parity kanıtı taşır
- Bot yazma/düzenleme capability ayrı; emir yetkisi yok

## P5 — Saf uygunluk ve nedenli engel

Durum: BEKLİYOR. Bağımlılıklar: P4.

Eksik kanıtta BLOCKED; OBSERVE_ONLY/EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY sonuçları.

Bitiş koşulları:

- Her zorunlu kanıtın yokluğuna negatif test
- UI LIVE veya çizim görünürlüğü aktivasyon değildir
- Desteklenmeyen kind/formula/scale/grid açık engel

## P6 — Kalıcı semantik olay/yerel intent

Durum: BEKLİYOR. Bağımlılıklar: P5.

Mevcut reliability P6: transaction head recheck, semantic unique key, replay namespace, crash/restart.

Bitiş koşulları:

- Event+intent atomik ve kalıcı dedup
- Ayrı DB atomik snapshot iddiası yok
- Sahte sink; gerçek mesaj/hesap/emir/worker aktivasyonu yok

## P7 — İzole replay/kuru çalışma

Durum: BEKLİYOR. Bağımlılıklar: P6.

Mevcut36 E4 senaryosunu gerçekten yürüt; yeni araçlara registryde açıkça desteklenen ek senaryolar.

Bitiş koşulları:

- 36 senaryo ve araç bazlı ek parity testleri sonuç sayılarıyla
- Fake clock/restart/revision yarışı tekrar edilebilir
- Canlı fırsat/history ayrımı; dış yan etki sayaçları sıfır

## QA01 — Masaüstü grafik kabulü ve yeni aday

Durum: BEKLİYOR. Bağımlılıklar: T03, T04, T05, T06, T07, T08, T09, T10, T11, T12, T13, T14, P7.

Genişleyen çekirdek kapsamı regression/raster/performans ve gerekli görünür klavye/fullscreen kabulü; restore edilebilir yeni aday.

Bitiş koşulları:

- Ertelenmiş B5 masaüstü D03/D05/D06 kapanır veya açık kalır; dokunmatik ayrı iş
- Değişiklik etkisine göre ölçüm; her küçük değişiklikte30dk tekrar yok
- Yeni aday hash/restore ve kaynak kanıtı; bot/live order/notification ayrı sonraki karar

## Her araç için ortak tamamlanma kuralı

Araç yalnız ikon/render eklendiğinde tamamlanmaz: kimlik/schema sürümü, kanonik hesap ve UI parity, oluşturma/sayısal edit/drag, kayıt/reload/undo/409, market/timeframe davranışı ve gereken negatif testler birlikte teslim edilir. Bot desteklemiyorsa capability açıkça bunu söyler; benzer araca sessiz dönüşüm yok. Kullanılmayan geçmiş veya birden çok kaynaktan gelen veri provenansı gizlenmez.

Görsel gizleme botu durdurmaz; kilitleme işlem yetkisi değildir. Çizim planı, kural aktivasyonu, botun çizim düzenleme yetkisi, bildirim ve emir ayrı kapsamdır. P4–P7 önce izole yerel değerlendirme kapsamıdır; canlı worker, dış mesaj, hesap/emir veya eski demo yürütme çekirdeğine bağlantı bu planla yetkilendirilmez.

Mevcut reliability P2–P7 tanımları korunur, fakat uygulama sırası ve genişleyen araç bağımlılıklarında bu v2 planı üstündür. E3/E4 senaryoları tasarım kanıtı olarak korunur; çalıştırılmadan runtime PASS sayılmaz. B5 erteleme kaldırılmış değildir; QA01'de görünür kabul yeniden ele alınır. Yeni aday ancak kaynak ve kanıt sürümü eşleştiğinde paketlenir; aday02 korunur.

## Bağlantılar

[Makine okunur plan](contracts/chart-core-plan-v2.json) · [Yetenek denetimi](CAPABILITY-AUDIT.md) · [Veri güvenilirliği ayrıntıları](RELIABILITY-PLAN.md) · [Bot sözleşmesi](BOT-DATA-CONTRACT.md) · [P1](EXACT-DATA.md) · [Kabul kapsamı](ACCEPTANCE.md)


## Son canlı araştırma kontrol noktası

REA03 devam ediyor. Navigasyon/sembol turunda interval ile range preset ayrımı, Go to, çizgi fiyat kaynakları ve BTC/ETH çizim izolasyonu incelendi. Araştırma çizimleri silinmeden gizlendi; BTC/1D görünümü kaydedildi. Ayrıntılar ve doğrulanmayan durumlar REA-REFERENCE-ANALYSIS.md içindeki REA-N01–N07 kayıtlarında. Uygulama kodu değiştirilmedi.

## Geniş canlı tur kontrol noktası

REA03 içinde metin oluştur/edit/style/silme, gösterge şablonu kapsam alanları, yerleşik BB/RSI/ATR/VWAP kaynak/girdi/stil, RSI paneli ve açık/koyu tasarım durumları birlikte incelendi. [Detaylı araştırma ve fixturelar](REA-INDICATORS-ANNOTATIONS-DESIGN.md) REA04 girdisidir. IND-RSI-FLAT için mevcut uygulamanın50 sonucu ile yerleşik kaynağın100 dalı arasında uyumluluk kararı gerekiyor; ürün kodu sessizce değiştirilmez. Numeric parity/drag/reload açık; REA03 tamamlandı sayılmıyor.

## 11 Kasım 2026 — yönetim ve kalıcılık canlı turu

[Tur raporu](REA-MANAGEMENT-WORKSPACE.md) ve [gözlenen fixturelar](contracts/rea-observed-fixtures-v1.json) REA04 girdisidir. T07 gruplama/katman/lock semantiğiyle genişletilmeli; T14 çizim-gösterge-layout şablonlarını ayrı tutmalı. Grup fiyat+bar Apply işlemindeki iki Undo adımı referans davranışıdır; bizim atomik işlem kararı açık verilmeli. Belirli Fib ve Long/Short alanlarında gerçek reload doğrulandı; tam render/timestamp/yarış kabulü kapanmadı. Global gizleme bu reload deneyinde kalıcı değildi; oturum tercihi ile nesne görünürlüğü ayrılmalı. REA03 araştırması sürüyor; ürün geliştirmesi başlamadı.

## 11 Kasım — ölçek ve zaman sunumu kabul girdileri

[Ölçek/saat dilimi raporu](REA-SCALES-TIMEZONE.md) temel lineer/log geometri ve etiket/birim sözleşmesini ayrıntılandırır. T12/T13 içinde kanonik ankraj, log-Fib hesabı ve gösterim formatterı ayrı tutulmalı. Yüzde/index/invert/sol eksen uygulanan referans kabiliyetleridir; çekirdek bitiş şartına otomatik eklenmez. Etiket çakışma çözümü ve timezone gösterim değişmezliği temel kaliteye dahildir. UTC+4→UTC sabit kapalı mum örneği contracts/rea-observed-fixtures-v1.json içine eklendi. DST/seans, yüzde tabanı, pointer ve performans açık; REA03 tamamlanmış sayılmaz.

## 11 Kasım — focus, canlı önizleme ve responsive kabulü

[Tur raporu](REA-FOCUS-RESPONSIVE.md) ve contracts/rea-observed-fixtures-v1.json içine3 örnek eklendi. BB referansında Cancel geri alırken Escape/X değişikliği koruyor; bizim ürün bu kapanış yollarını açık karar ve transaction/undo tasarımıyla ele almalı. Date input odağında global harf/slash/virgül kısayolu sızıntısı bu örnekte görülmedi; tüm editör kabulü değildir. Bağlı tarayıcı dar viewport iddiası geri çekildi; ayrı girişsiz desktop launch senaryolarında1280/1024/768 PNG boyutları doğrulandı. Çoklu seçim/mixed lock ve nested grup açık: mevcut REA click modifier/drag sunmuyor, nested denemesi Basic-plan yükseltme ekranında durdu. Bu sınırlar için yeni izin/kurulum/yükseltme varsayılmadı. REA03 sürüyor.

## 11 Kasım — veri tablosu ve bağımsız sayısal karşılaştırma

[Tur raporu](REA-TABLE-NUMERIC-PARITY.md):32 kapalı günlük mumdan BB20 için13/13 satır (39 değer), BB5/offset+2 için28/28 satır (84 değer), EMA20 basis için31/31 ardışık güncelleme ekran hassasiyeti içinde uyuştu. Bunlar araştırma fixturelarıdır; ürün kabulü veya EMA seed/warmup doğrulaması değildir. T09/T10 ve BB kapsam genişletmesi için population variance, source/basis, offset ve formatter toleransı ayrı kabul maddeleri olmalı. T08/T13 veri sözleşmesi hesap zamanı ile render zamanını ayırmalı; geleceğe kaydırılmış gösterge satırında OHLC boş kalabilmeli. Menü/tasarım araştırması sürüyor: Data window temel, çok mumlu tablo/CSV ihtiyaca göre sonraki kapsam adayı. CSV mevcut hesapta plan yükseltme ekranında durdu, dosya alınmadı.11 gözlenen fixture var; tamamlanmış5 görev korunuyor. RSI/ATR/VWAP sayısal parity, veri yaşam döngüsü, pointer ve performans açık; REA03 sürüyor, ürün geliştirmesi başlamadı.

## 11 Kasım — ATR/RSI/VWAP ve aggregation kabul girdileri

[Geniş tur raporu](REA-ATR-RSI-VWAP-DATA.md) ve19 araştırma fixtureı REA04 girdisidir. ATR14/RMA31 güncelleme, ATR14/SMA18 pencere, RSI üzerindeki SMA14 için19 pencere, RSI2 için20 burnin sonrası10 çıktı, VWAP1D percentage2 için32 satır/96 değer doğrulandı. Saatlik VWAP25 kapalı satırda rounded-volume belirsizlik aralıklarıyla tutarlı; exact-volume parity değildir. Tek UTC günün24 saatlik OHLC birleştirmesi günlükle birebir uyuştu.

T09/T10 ana indicator/smoothing/overlay ve seed/warmup ayrımını; T11 hesap timeframe/source/anchor/volume provenansını ve boş çıktı nedenlerini; T08 aggregation ile üst-zaman confirmed mapping ayrımını ele almalı. Günlük ve saatlik Session/HLC3 VWAP farklı olabilir; yalnız VWAP adı veri kimliği değildir. Hide-on1D örneğinde nesne korunurken çıktılar boş kaldı; boş değer0 değildir. Üst-zaman seçim akışı tamamlanmadığından Wait-for-timeframe-closes on/off, lookahead/gap/forward-fill kabulü açık. Veri yaşam döngüsü/reconnect/stale/yarış, pointer ve performans araştırması sürüyor. Aynı5 görev tamamlanmış kalır; ürün geliştirmesi veya nihai REA04 planı bu tur tamamlanmadı.

## 11 Kasım — veri yaşamı, fiyat türü ve gerçek uç nokta sürükleme

[Geniş tur raporu](REA-LIFECYCLE-MARKET-POINTER.md) ve27 araştırma fixtureı REA04 girdisidir. Açık1m mum değişirken31 önceki kapalı satır, document navigasyonu öncesi/sonrası30 ortak kapalı satır aynı kaldı; karşılaştırmalar örtüşür. Offline25sn emülasyon geri yüklendi ama31 socket frame geldiği için tam blackout/stale freeze kabulü açık. Market-open göstergesi freshness kanıtı değildir. Tarih navigasyonunda5/8 Kasım1m pencereleri açıldı; hard-limit/pagination algoritması çıkarılmadı.

Spot/perpetual/mark fiyatı ayrı kimlik ve OHLC üretiyor. Mark serisinde OHLC var/hacim yok: Volume hata, VWAP RE10142; Data window boş nesne başlıklarını korurken Table view hata veren output sütunlarını dışarıda bırakıyor. T09/T11 ve P2/P3 tasarım girdileri; missing/zero/hidden/warmup/stale ayrı nedenler olmalı. Volume Precision8 küçük değerleri37→37.187 açtı ama K kısaltması kalıyor; exact VWAP volume parity hâlâ açık.

REA drag sunmadığından sınırlı sıradan-CDP fallback ile boş spot grafiğinde bir geçici trend uç noktası sürüklendi: nokta1 aynı, nokta2 fiyat+5543.80/bar+14; Undo eski noktaya döndü. T07/T12/T13 pointer kabulü kısmen somutlaştı; bodydrag/snap/cancel/multi/touch/perf açık. Geçici trend silindi. Orijinal Fib fiyatları60000/80000 kaldı ama gösterilen barlar önceki187/249 yerine186/248: sebep/UTC ankraj eşitliği açık, indekslere düzeltme yazılmadı. Kalıcı ankraj yalnız UI logical index olamaz. Eski5 tamamlanmış iş korunuyor. REA03 sürüyor; uygulama ve REA04 nihai plan konsolidasyonu başlamadı.
