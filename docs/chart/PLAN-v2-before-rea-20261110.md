# Grafik çekirdek geliştirme planı — v2

10 Kasım 2026. T01, T02, P2, P3 ve T03 tamamlandı; **sıradaki iş T04: long/short planlama**. Güncel kanıt: 735 Python / 161 frontend testi, üretim derlemesi ve 11 gerçek App/HTTP/SQLite cetvel kontrolü geçti.

## Durum ve kapsam

Eski A–E planı [değiştirilmeden arşivlendi](PLAN-v1-20261110.md):24/25 tamamlandı, B5 kullanıcı isteğiyle ertelenmiş/açık. Bu sayı yeni özelliklerin hazır olduğu anlamına gelmez. P1 kesin ondalık taşıması tamamlandı:686 Python/131 frontend/21 wire kontrolü. Bu plan değişikliğinde testler tekrar koşulmadı.

Yeni kapsam **21 iş paketi, 5/21 tamamlandı**; bunlar takvim/süre tahmini değildir. T01/T02 ve P2/P3 mevcut altyapıyı tamamlar; önceki işleri sıfırlamaz. Kullanıcı tarafından onaylanan kabul hedefi masaüstü fare/klavye/trackpad. Gerçek dokunmatik D08/D09 ayrı açık iş, başarılı sayılmaz. Tasarım sonraya bırakılır.

Hedef araçlar: fiyat-zaman cetveli; long/short planı; ray/uzatma/paralel kanal; çizim kilit/gizle/kopya/görünürlük; ayarlanabilir göstergeler ve SMA/EMA/RSI/ATR/VWAP;1m/5m/30m; ayarlı Fibonacci/extension; lineer/log ölçek; çalışma alanı şablonları. MACD/Bollinger ve daha özel araçlar ikinci dalga, bu çekirdeğin zorunlu bitiş koşulu değildir. Botun desteklenen araçları aynı anlam ve hesapla okuyabilmesi çekirdeğin bitiş koşuludur.

## Sıra ve teslimler

| Grup | İzlenecek sıra | Sonuç |
| --- | --- | --- |
| Temel | T01 → T02 → P2 → P3 | Araç sözleşmesi, kanonik hesap, saat/epoch/kalite |
| İlk araçlar | T03 → T04 → T05 → T06 → T07 | Cetvel, risk planı, uzatmalar/kanal, çizim yönetimi |
| Hesap ve bağlam | T08 → T09 → T10 → T11 → T12 → T13 → T14 | Timeframe, göstergeler, VWAP/Fib/log ve şablonlar |
| Bot uyumu | P4 → P5 → P6 → P7 | Revision bağı, uygunluk, kalıcı olay ve izole replay |
| Kabul | QA01 | Güncel masaüstü kabulü ve doğrulanmış yeni aday |

Bu tablo varsayılan tek çalışma sırasıdır; bağımlılık grafiğinde bazı işler daha az bağımlı olabilir. Sırayı değiştirmek için somut ihtiyaç ve kayıt gerekir; otomatik paralel çalışma talimatı değildir.

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
