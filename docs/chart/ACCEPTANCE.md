# Grafik kabul incelemesi

13 Kasım 2026 — **QA01 kontrollü masaüstü doğrulaması tamamlandı; uygulama planı 27/27.** [Kabul raporu](QA01-ACCEPTANCE.md): 920 Python/278 frontend testi, 18 raster durumu, 20 cleanup döngüsü, beş 60 saniyelik performans koşusu ve 10 temiz restore kontrolü geçti. rAF p95 her koşuda16,8 ms; wheel→frame-swap p95 78,487 ms. Genel sürüm/B5 fiziksel kabul açık; canlı entegrasyon kapalı. Sıradaki iş açık fiziksel kabul maddelerinin gözden geçirilmesi. Aşağıdaki önceki teslim kayıtları tarihseldir.

10 Kasım 2026 — E1 tamamlandı. **Genel grafik/sürüm kabulü verilmedi.** Kontrollü doğruluk, çizim ve performans görevlerinin tamamlanması fiziksel kullanım açıklarını kapatmaz. Bot entegrasyonu başlamadı.

## Doğrulanan çalışma kapsamı

Güncel üretim paketi `index-DIUEWtQr.js`. Üretim paketiyle güçlü güncel kanıt Windows 11 / headless Chromium 145 / 1400×1000 / DPR1 ortamındadır: 4.000 mum, 200 çizim, üç 60 saniyelik etkileşim koşusu ve 30 dakika 2 saniyelik yerel gerçek WebSocket oturumu. P95 16,7/16,7/16,8 ms; 61 tam veri/native seri örneği, iki mum sınırı ve iki reconnect geçti. Bunlar gerçek borsa kesintisi veya fiziksel cihaz kabulü değildir.

390×844 dahil responsive ve DPR2 kontrolleri emüle/otomatik kanıttır. Eski görünür masaüstü B5 koşusu farklı paketle yapıldı ve kabul edilmedi. Fiziksel trackpad, native touch, ekran okuyucu, raster/DPR ve diğer tarayıcılar için genel destek ilan edilmiş sayılmaz. Masaüstü paketlemesi henüz bu incelemenin konusu değildir.

## G01–G07 kanıt eşleştirmesi

| Alan | Doğrulanan kapsam | Açık kalan |
| --- | --- | --- |
| G01 Çizim yaşam döngüsü | Dört türde oluşturma/düzenleme/yeniden açma; Seçim, tutamaç sahipliği, gerçek fare sürükleme/Escape/capture kaybı; Blur, hidden, pointercancel ve ikinci pointer için kontrollü/sentetik iptal | R01 |
| G02 Zaman ve fiyat geometrisi | Tick/ondalık ve açık UTC doğrulaması; Boşluk/fractional logical konum, ters Fibonacci ve pane yaşam döngüsü; Native/SVG koordinat kontrolü; emüle viewport/DPR durumları | R02 |
| G03 Kalıcılık ve kayıt yarışları | Gerçek izole FastAPI/SQLite ile silme/undo/redo/reload/restart; Kayıp yanıt sonrası aynı request_id tekrarında tek sürüm; Bağımsız API yazıcısıyla gerçek 409; eski kayıt kazananı ezmez; Kontrollü hook/App market ve bootstrap yarışları | R03 |
| G04 Piyasa verisi ve toparlanma | Eski/tekrar/bozuk paket ve history/canlı veri yarışları; Mum/hacim writer hata toparlanması için native harness; 30 dakika yerel gerçek WebSocket; iki sınır ve iki reconnect; Önceki yalnız public Binance canlı veri probe kanıtı | R04, R05 |
| G05 Göstergeler | Bağımsız Decimal EMA/RSI referansları ve warmup; History/live close/finalization sonrası native değerler; 50 pane döngüsü; D3 10+20 kaynak döngüsü; Ölçülen oturumda post-GC kaynak sayıları sabit | R06 |
| G06 Tarayıcı performansı | 4.000 mum/200 karma çizim; üç geçerli 60 sn p95 koşusu; D1–D4 ile güncel üretim asset hash eşleşmesi; 30 dakika 2 sn oturum ve 61 tam veri/native seri örneği; Heap bütçesi, snapshot farkı ve uzun aralıklar kayıtlı | R06, R07, OBS01 |
| G07 Erişilebilirlik ve mobil kullanım | Klavye zoom/pan/End, görünür odak, skip-link ve input izolasyonu; 390×844 dahil emüle responsive düzen; Headless Fullscreen API giriş/çıkış/red ve koordinat kontrolleri | R01, R02, R07 |

Ayrıntılı dosya bağlantıları, rapor hash’leri ve kapsam durumları [makine okunur incelemede](../../reports/chart-acceptance-review-20261110.json) yer alır.

## Kalan işlerin kapanış koşulları

### R01

Gerçek ikinci dokunma/native touch ve tüm türlerde fiziksel iptal kapsamı. C2 sentetik sinyaller fiziksel kabul değildir.

Kapanış: Uygun gerçek cihazda owning/non-owning pointer, iptal ve dışarı bırakma doğrulanır; ya da destek sınırı E5 incelemesinde açıkça karara bağlanır.

### R02

Görüntü/raster düzeyinde çizgi-mum hizası ve fiziksel DPR/viewport matrisi. Native sayısal 0 px sonuç raster ispatı değildir.

Kapanış: Hedef ekranlarda görüntü ve koordinat kanıtı, kırpılma/örtüşme kontrolü ve ilan edilen tolerans; atlanan ölçümler PASS sayılmaz.

### R03

Güncel sürümde iki gerçek tarayıcı sekmesinin aynı SQLite deposunda eşzamanlı yazım/undo/yenileme akışı. C4 ikinci yazıcı API istemcisidir.

Kapanış: İki izole sekme aynı çizim sürümünü değiştirir; kazanan korunur, kaybeden 409 ile toparlanır; retry/undo mükerrer sürüm ve çapraz market kayıt oluşturmaz.

### R04

Tam App içinde bağımsız gösterge effect/seri yazım hatası enjeksiyonu ve toparlanması. A1 writer harness tüm React fault yolları değildir.

Kapanış: Mum/hacim ve gösterge hata yolları App içinde kontrollü tetiklenir; durum etiketi hatayı gizlemez, başarılı yeniden çizim ve veri/gösterge tutarlılığı doğrulanır.

### R05

Uzamış upstream kesintisi ve sistem saati sapması. UI tazelik kararı Date.now ile sunucu received_at değerini karşılaştırır. D4 yerel stream gerçek Binance outage değildir.

Kapanış: Uzun kesinti/saat sapması için açık güvenilirlik davranışı ve testler; E3 sözleşmesi tazelik güvencesi yoksa botun karar üretmesini engellemelidir.

### R06

Ölçülen döngüler/30 dakika kaynak sayımı ve heap bütçesi geçti. Sınırsız oturum veya mutlak heap platosu doğrulanmadı.

Kapanış: Sürüm notunda doğrulanan yük/süre/ortam sınırı korunur; daha uzun kullanım hedeflenirse ek ölçüm ve artış varsa nesne/retainer analizi gerekir. Sonsuz süre ispatı aranmaz.

### R07

B5 D07 fiziksel trackpad FAIL sonrası düzeltmenin fiziksel tekrarı yok; D03/D05/D06 eksik, D08/D09 cihaz yok. Ekran okuyucu kabulü yapılmadı.

Kapanış: Önceden hazırlanmış kısa B5 tekrarında yalnız açık durumlar sınanır; otomatik yapılabilecek testler kullanıcıya devredilmez. Dokunma/ekran okuyucu için gerçek uygun ortam veya açık destek kararı gerekir.

### OBS01

D4 ilk 31 saniyesinde gözlenen 749,9 ms aralığının kesin nedeni kayıtlı değil. Heap snapshot aynı pencerede; yalnız GC neden oldu denemez.

Kapanış: Kesin atıf gerekirse faz işaretli kısa trace alınır. D2 etkileşim kabulü geçerli kalır; raporlarda sıfır takılma veya kesin GC nedenselliği iddia edilmez.

## B5 neden hâlâ açık?

Önceki görünür koşuda D01/D02/D04 geçti; D03/D05/D06 tamamlanmadı. D07 yatay trackpad hareketinde mum aralığı yaklaşık %17,38 değişti ve FAIL kaydedildi. Sonraki eksen sabitleme düzeltmesi otomatik testlerden geçti; fiziksel tekrar yapılmadığı için bu bulgu kapanmış sayılmaz. D08/D09 için dokunmatik ekran yoktu. Kullanıcının açık talebiyle B5 ertelendi; bu onay B5’i başarılı sayma veya destek kapsamını sessizce daraltma yetkisi değildir.

## Kanıtların güncelliği

Veri/gösterge çekirdeğindeki sekiz dosyanın SHA-256 değeri A5 incelemesiyle aynı. Sonraki App/editor/navigasyon değişikliklerinin C/D kanıtları ayrıca kaydedildi. Bu nedenle önceki doğruluk kanıtları korunur; tüm tarihsel native senaryoların son pakette tekrar koşulduğu iddia edilmez. Güncel asset hash’leri D5 ile aynı. Son doğrulanan frontend sayısı 123; backend 675 önceki kanıttır. E1 bir kanıt/kapsam incelemesidir; testler veya 30 dakika oturumu bu tur tekrar çalıştırılmadı.

Heap 30 dakikada yaklaşık 1,69 MiB arttı ve 2 MiB tarama bütçesi içinde kaldı; son beş dakika artışı 14.316 byte. Bu mutlak plato/sızıntısızlık ispatı değildir. D4 749,9 ms maksimumunun kesin nedenselliği kayıtlı değildir; sıfır takılma sözü verilmez.

## Sonraki adım

E2: mevcut grafik **sürüm adayını** paket/bağımlılık/hash bilgisi, çalıştırma ve geri dönüş adımlarıyla sabitlemek. Bu, açık maddeleri çözülmüş veya ürünü yayına hazır ilan etmek değildir. E3/E4 bot veri sözleşmesi ve kuru çalışma planını yazar; botu bağlamaz. E5 kullanıcı incelemesi ve sonraki aşama kararıdır. Kalan açıklar ve fiziksel tekrar, genel kabul/bot entegrasyonu öncesinde açıkça ele alınacak.


## CL01 güncellemesi — 10 Kasım 2026

R03 tanımlı iki browser sekmesi/gerçek HTTP-SQLite akışları13 kontrolle kapandı. [Kanıt](../../reports/chart-two-tab-validation-20261110.json). Önceki E1 tablosu inceleme tarihinin kaydıdır; R03’ün güncel durumu bu ek ve kabul matrisidir. Kullanıcı E5 grafik kapanış sırasını onayladı; bot bağlantısı onaylanmadı. R04/CL02 ve diğer açıklar sürer.


## CL02–CL04 güncellemesi — 10 Kasım 2026

Tam App gösterge effect yazım hatası yeniden üretildi ve düzeltildi;15 fault senaryosu/12.420 bağımsız değer kontrolü geçti. [CL02](../../reports/chart-app-fault-recovery-validation-20261110.json). R04 bu tanımlı native yazım/snapshot/update/history kapsamıyla kapandı; keyfi seri oluşturma/cihaz hatalarının tümü ispatlandı denmez.

[CL03 raster matrisi](../../reports/chart-visual-raster-validation-20261110.json)9 durumda243 gerçek boyalı piksel probunu ≤1 CSS px ile geçti;3px kaydırılmış negatif kontrol başarısız sayıldı. Sıkışan Fibonacci metni seyreltilir, seviye çizgisi/fiyatı değişmez. R02’nin kontrollü raster kısmı kapandı; fiziksel ekran/DPR kabulü henüz verilmedi.

Kaynak değişti: App/LineSeriesWriter ve DrawingLayer/Fibonacci label helper. Önceki E1’deki kaynak hash eşliği tarihi kanıttır; yeni LineSeriesWriter için zorunlu rebuild ve fault regresyonları eklendi. Yeni bundle `index-z15JopqV.js`; önceki01 adayı/30 dakika kanıtı kendi eski paketine aittir. 127 frontend testi/derleme başarılı.

CL04 fiziksel tekrar kullanıcı şu anda yapamadığı için ertelendi. Görünür browser host kullanılamadı; yalnız lab ve otomatik telemetry smoke hazırlandı. Smoke dosyaları açıkça otomatik işaretli, fiziksel PASS değildir. B5 D07 eski FAIL ve diğer eksikler korunur; dokunmatik cihaz yokluğu başarıya çevrilmez.


## P2 uygulama güncellemesi — 10 Kasım 2026

P2 tamamlandı: enjekte edilebilir wall/monotonic saat, upstream saat ölçümü ve belirsizlik, heartbeat yaş koruması ve uzun kesinti snapshot bariyeri uygulandı. 718 Python / 143 frontend testi, 9 üretim App kontrolü ve gerçek public saat kanıtı geçti. Önceki Date.now-only/sıradaki P2 açıklamaları tarihsel durumdur. [Güncel kapsam ve sınırlar](CLOCK-RELIABILITY.md). Sırada P3; epoch/immutable kalite kanıtı ve bot motoru henüz uygulanmadı. B5/fiziksel ve gerçek uzun borsa kesintisi kabulü değişmedi.


## P3 uygulama güncellemesi — 10 Kasım 2026

P3 tamamlandı: producer epoch, consumer snapshot/callback bariyeri, immutable snapshot/grid hash ve açık warmup kanıtı uygulandı. 729 Python / 153 frontend testi, kontrollü App reconnect ve iki gerçek public abonelik snapshot kontrolü geçti. Önceki epoch/immutable kanıtın henüz bulunmadığını söyleyen bölümler tarihsel durumdur. [Güncel kapsam](STREAM-EVIDENCE.md). Sıradaki T03; P4–P7, canlı bot, genel/cihaz kabulü ve gerçek uzun borsa kesintisi kanıtı tamamlanmadı.
