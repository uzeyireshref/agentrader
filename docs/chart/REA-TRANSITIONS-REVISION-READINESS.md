# Coin/aralık geçişi, geç veri ve çizim hazırlığı

11 Kasım 2026. REA03 geniş canlı araştırma turu; ürün kodu değiştirilmedi. BTCUSDT.P ve ETHUSDT.P Binance perpetual, 1m/5m/1h; araştırma düzeni REA Araştırma. Tasarım ve veri yaşam döngüsü birlikte incelendi.

## Kanıt ve yöntem

`reports/rea-chart/rea-evidence-transitions-readiness-20261111.json`:82 REA kaydı; önceki72 kayıt dahil,10 yeni. Önceki106 kayıt ayrı korunur. Normal interval menüsü ve symbol search üzerinden ordinary-CDP girdileri ile sınırlı WebSocket gözlemi yapıldı. Bunlar REA Evidence değildir; REA erişilebilirlik/DOM/ekran kayıtları ve seçilmiş statik analiz ayrıca tutulur. Sayfaya JS enjekte edilmedi; ham frame, cookie, header, auth veya gerçek oturum kimliği saklanmadı. Kimlikler chart-session kapsamında aliaslandı. Girdi zamanı/receipt sırası sunucu nedenselliği ve performans ölçümü değildir.

Üç ana kohort: `interval-menu-transition-timeline-20261111.json`, `interval-burst-transition-timeline-20261111.json`, `symbol-transition-timeline-20261111.json` (reports/rea-chart altında). İlk comma-keyboard denemeleri guard hatasıyla durdu; başarılı aralık değişimi sayılmaz. `interval-burst-serialized-attempt-20261111.json` altı başarılı fakat yavaş seçimdir; hızlı kohorta dahil edilmez. Symbol attempt1 bir ETH seçiminden sonra sonuç hazır olmadığı için durdu; ana üç seçimle karıştırılmaz.

## 1. Eski aralığın verisi yeni istekten sonra geliyor

Seri kohortta beş seçim 1m→5m→1h→1m→1h. Aynı session_1/stream_1 üzerinde üçüncü istek 27711ms'de 60 dakika/revision_5. **27987ms/seq36'da önceki 5 dakika/revision_4 için tek fiyat satırı geldi**: yeni istekten276ms sonra. Yeni revision_5 için300 saatlik satır27988ms'de geldi. İlk resolve gözlemden önce olduğu için binding symbol/ref alanları null; BTC bağlamı görünür Canvas'tan ayrı kaydedildi.

Gerçek hızlı kohortta altı seçim 1m→5m→1h→1m→5m→1h; son seçim2546ms, ilk başlangıç35ms. İkinci istek769ms'de 5 dakika/revision_3. **880ms/seq7'de eski 1 dakika/revision_1 için tek satır geldi**:111ms geç. Yeni5m/300 satır1048ms'de geldi. Altı revizyonun her biri için300 satırlık, aralıkla uyumlu60/300/3600sn timestamp adımları görüldü; final BTC/1h ve özgün dört çizim mevcut.

Bu iki ana kohortta iki eski-tag geliş olayı kanıtlandı. Yardımcı yavaş altılı seçimde ayrıca146ms gecikmiş eski-tag örneği var; ana sayıdan ayrı. İlk binding öncesi bilinmeyen revision'lar geç yanıt olarak sayılmadı. **Ağda eski veri görülmesi, eski verinin ekrana bir kare bile çizilmediğini kanıtlamaz.** Zorlanmış ağ gecikmesi, bütün render commitleri veya cross-symbol stale rejection doğrulanmadı.

## 2. Coin hazır, çizimler henüz hazır değil

Ana kohort ETH/1h başlangıcından BTC→ETH→BTC normal arama/seçimidir. Üç seçim334/1383/2502ms'de tamamlandı. BTC resolve ve public symbol kimliği yakalandı; cached ETH resolve gözlem öncesinde olduğundan ikinci binding symbol/ref null bırakıldı. Görünür Canvas ETH'yi doğrular; bu, yakalanmamış wire çözümlemesinin yerine yazılmaz. URL query BTC olarak kaldığı için adres çubuğu güncel coin otoritesi değildir.

599ms snapshot'ında BTC/1h Canvas, BTC fiyat kaynağı, Volume ve BB mevcut; Object tree yalnız3 kaynak içeriyor. Sonraki BTC dönüşü2716ms ve final5248ms snapshot'larında7 kaynak var: aynı3 kaynağa Fib, Short ve iki Long eklenmiş. Bu örnek **market görünümü ile çizim restorasyonunun farklı zamanlarda hazır olabildiğini** gösterir. Aradaki ETH dönüşü nedeniyle tek BTC geçişinin kesin yüklenme süresi veya ağ latency ölçüsü değildir. Geçici boş ağaç, kayıp/silinmiş çizim kanıtı değildir. Sıfır eski-tag symbol olayı bütün race yollarının güvenli olduğu anlamına gelmez.

## 3. Yüklü istemci kaynaklarında turnaround

Kaynak kimliği REA `ev_8261acdfe6abcba64f536bfc45fd52f7e40703d85e634f8b29d28d1ffbe015c6`; eski edinilmiş tam kaynak hash'i mevcut loaded script ile eşleşti. Seçilmiş iki dosya REA statik analiz `ev_2869676b67f2d1828f5f6d0262d2fcf83e201c8d848d3d322000ca26857b63dc`;2 parse başarılı,0 parse failure. Bağımlılıklar tam seçilmedi; uygulama partial, semantics unknown.

`transition-source-analysis/provenance.json` tam URL/hash/byte ve edinim kaynağını içerir. Decoder76108 SHA256 `6965c050aaa64af07e6877911543a9b5e4b4fd7f643b954eeb897994e3159ed1`: wire `.t` alanını `turnaround` olarak normalize eder; du→data_update ve timescale_update yolları bulunur. Dolayısıyla yakalanan tag revizyon bağlamıdır, bar timestamp'i değildir.

Series-data-source84989 SHA256 `fc514405bfd9f604cfb96ad05148e2a7b43a59da050de84a6ff3e603229b19cf`: Chart.SeriesDataSource sınıfında sembol/resolution değişimi turnaroundCounter artırır; mesajları Promise kuyruğuna alır. data_update öncesi instanceId ve turnaround kontrol edilir. `_checkTurnaround` aynı instance ve **undefined turnaround veya güncel turnaround** kabul eder. Etiket eksikse bu bileşen koşulsuz reddetmez. Sonrasında async unpack ve merge vardır; bütün await sınırlarında tekrar kontrol kanıtı çıkarılmadı.

Bu sınıfın kaynakta/yüklü bundle'da bulunması ana Supercharts grafiğinin aktif dispatch yolunda çalıştığını kanıtlamaz. Runtime call trace/coverage alınmadı; bütün referans grafik için stale rejection iddiası yok. Kaynaklar araştırma içindir; ürün içine vendor kodu kopyalanmadı, lisans izni varsayılmadı.

## 4. Ürün ve tasarım kabulüne aktarım

App.tsx zaten alive/request serial/connectionSerial ve AbortController; useDrawings.ts selection version, serialized reads ve loadedFor korumaları içeriyor. P3 yeniden açılmış veya bug kanıtlanmış değildir. Aşağıdakiler REA04/QA01 için ek kabul hedefidir:

- Market kimliği exchange/product/price source/symbol/interval ve connection/request epoch ile taşınır. Eski epoch verisi veya async hesap sonucu yeni bağlama commit edilmez. İptal tek başına yeterli kabul sayılmaz.
- Market-data, indicator ve drawing readiness ayrı tutulur. Henüz yüklenmeyen tree için “çizim yok” sonucu, otomatik boş kayıt veya silme olayı üretilmez. Çizim düzenleme ilgili kaynağın hazır olmasına bağlanır.
- Header/legend/fiyat ekseni/crosshair/Data window aynı aktif bağlamı gösterir. Eski görüntü tutulursa yükleniyor/eski bağlam açık görünür; yeni başlık altında eski fiyat ve tıklanabilir eski tutamak karışımı oluşmaz. Hareketli açık mum ve kapanmış mum kabulü ayrı kalır.
- Deterministik ürün fixture: A→B→A, ters sırada history/stream/drawing yanıtları, async indicator tamamlanması, bağlantı epoch değişimi, cached resolve ve eksik revision. Her commit sınırında bağlam kontrolü; final kare kadar ara kareler, history ve persistence olayları da değerlendirilir.

Bunlar referansta her biri gözlenmiş davranış olarak sunulmaz; bulgudan türetilmiş ürün kararlarıdır. D12 görsel kabulü yükleme/boş/hata durumunu ve tıklanabilirlik sınırını kapsar. Bu tur pixel parity, responsive veya FPS/frame p95 benchmark değildir.

## Kapanış ve kalan araştırma

Final REA `ev_3a7a1e796832ae9f9d1424a47651ace48fa008042ef92cecc4071a6d90b0f0d7`: BTCUSDT.P/1D/UTC, özgün4 çizim globally hidden, Volume+BB20/SMA/Close/2/offset0/Chart/WaitON; dialog kapalı ve All changes saved. BB formu `ev_df31ce178920fafab424ab1bab68d866247529ad6bc7bd179ce996adb2e54e9c` ile yeniden okundu. Yeni çizim/indikator oluşturulmadı; gözlem bağlantıları kapandı.

Sıradaki araştırma: seed/warmup/NA/zero-volume için kontrollü örnek elde edilebilirliği ve açık risk kararı; gerçek blackout/reconnect/catchup için uygulanabilir kanıt yöntemi; ortak referans performans baseline ve seçilmiş desktop durum matrisi; ardından REA04 konsolidasyonu. Önceki25sn offline deneyinde socket trafiği sürdüğünden tam blackout hâlâ kanıtlanmış değil. REA03 devam, REA04 taslak, uygulama5/21 korunur. Araştırma fixture ve kontrolleri ürün testleri değildir.
