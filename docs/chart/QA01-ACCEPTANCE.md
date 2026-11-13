# QA01 — kontrollü masaüstü kabulü

13 Kasım 2026. Kontrollü ürün doğrulaması tamamlandı; kaynak adayının restore sonucu ayrı makbuzla doğrulanır. Genel sürüm, fiziksel cihaz/B5 kabulü ve canlı entegrasyon açık kalır. Bu belge TradingView ile tam sayısal veya performans eşitliği iddiası taşımaz.

## Kullanıcıya yansıyan düzeltmeler

- Çizim sürüklenirken sekme gizlenmesi, pencere odağının kaybı veya Escape önizlemeyi bırakır; yarım hareket geçmişe veya veritabanına yazılmaz. Sonraki hareket çalışır.
- Altı diyalog ortak açma/kapatma yaşam döngüsü kullanır. Diyalog DOM'dan ayrılmadan kapatılır, uygun olduğunda odak açan düğmeye döner.
- Ayar pencerelerinde klavyeyle odaklanan kontrol sabit alt düğmelerin arkasında kalmaz; kaydırma pencere içinde tutulur.
- Açık/koyu tema tarayıcının yerel form kontrollerine ve tema rengine de uygulanır. Deneme kimliği alanında otomatik tamamlama/yazım denetimi kapalıdır.
- Paket verisine doğrulama JSON'ları eklendi; aday kaynak, sözleşmeler ve doğrulama araçlarıyla birlikte sabitlenir.

## Ölçülen kapsam

Üretim derlemesiyle 1.000 kapalı + 1 açık mum, 200 çizim/14 tür ve 60 Hz hedefinde beş ayrı en az 60 saniyelik etkileşim koşusu geçti. Her koşunun rAF p95'i 16,8 ms; bütçe 33,34 ms. Native Chrome wheel gecikme izinde 20 örneğin ORIGINAL→FRAME_SWAP p95'i 78,487 ms, en büyüğü 81,107 ms; bütçe 100 ms. rAF callback aralığı GPU FPS değildir; frame swap fiziksel ekran taraması değildir. Ekran görüntüsü kodlama/taşıma süresini de içeren eski ölçüm yalnız tanısaldır.

1536/1280/1024 CSS genişlik × DPR 1/1,25/2 × açık/koyu tema: 18 durum, 108 konum probu geçti. SVG referansı ve native mum fitili en fazla 1 CSS piksel sapma gösterdi; 4 piksel kaydırılmış negatif kontrol reddedildi. Örtüşme etkisini ayırmak için native ve birleşik görüntüler ayrı kaydedildi. DPR CDP üzerinden doğrulandı. Bu emülasyon fiziksel panel kabulü değildir.

İki ısınma ardından 20 kaynak temizleme döngüsü geçti: gösterge aç/kapat, BTC/ETH geçişi, diyalog ve tema değişimi. Bağlı eleman 3800, CDP node 5851, dinleyici 749 olarak sabit kaldı. GC sonrası heap artışı 1.638.016 bayt, 2 MiB tarama bütçesinin altında. Yerel socket bir bağlantıyla çalıştı ve sayfa kapanınca sıfırlandı. Bu sınırlı pencere sınırsız oturumda sızıntı olmayacağını kanıtlamaz.

İlk denemede görülen birikimin heap kökü test aracının bıraktığı ElementHandle'lardı. Tekrarlanan Locator.wait_for yerine handle bırakmayan expect görünürlük kontrolleri kullanıldı; tanı raporu korunur. Diyalog yaşam döngüsü düzeltmesi ayrıca birim testlidir; gözlenen birikimin tek nedeni olarak sunulmaz.

Gerçek yerel WebSocket ve üretim FeedState/P2/P3 zincirinde 7 kontrol geçti: aynı socket açıkken veri kesilmesi STALE üretir; eski heartbeat LIVE durumunu geri getirmez; yeni seed tek başına taze kabul edilmez; taze olay akışı yeniden geçerli kılar; tekrar olay revision/proof değiştirmez. 499 sunucu mumu ve tutulan eski prefix ile 500 benzersiz native mum vardır. Tarihsel close yeniden yerel olay üretmez. Bu kontrollü yerel kesintidir; gerçek Binance kesintisi değildir.

11 işlev kontrolü klavye gezinme/zoom, giriş alanı izolasyonu, skip-link, fullscreen, kesilen sürükleme, sonraki hareket/undo ve 48 Tab adımını kapsar. Pointercancel/blur/hidden girdileri sentetiktir; lost-capture tarayıcı tarafından üretilir. 920 Python ve 278 frontend testi, üretim derlemesi; G03/G06/T07/T14/P4/P7 tarayıcı regresyonları geçti. G06 desteklenmeyen aralık negatif kontrolü artık desteklenen 1m yerine 7m kullanır.

## Aday ve geri yükleme

Kaynak aday: `releases/chart-candidate-20261113-01.zip`. Dosya hash'leri MANIFEST.json içinde, arşiv hash'i dış makbuzdadır. Kullanıcı veritabanı, kimlik bilgisi, node_modules veya kurulu ortam içermez. Sürüm kilitleri mevcut ortamı kaydeder; temiz ağ kurulumu veya her platformda wheel kabulü değildir.

Proje kökünden `python scripts/verify_chart_candidate.py releases/chart-candidate-20261113-01.zip` ile doğrulayın. `python scripts/restore_qa01_candidate.py releases/chart-candidate-20261113-01.zip` yeni geçici köke çıkarır; ayrı depolarla gerçek sunucuyu başlatır, HTTP asset hash'leri, rapor kaynak doğrulaması, kayıt/restart, schema7→8 ve önceki yedeği kontrol eder, değiştirilmiş arşivi reddeder. Kullanıcı veritabanına restore yapmaz. Sonuç: `reports/chart-candidate-20261113-01-restore.json`.

## Açık kabul

B5 D03/D05/D06 fiziksel doğrulama açık; eski fiziksel D07 FAIL yeniden kabul edilmedi. Fiziksel trackpad, native touch, ekran okuyucu, gerçek panel/DPR ve diğer tarayıcılar ayrıca denenmelidir. Derlemede 500 kB üzeri bundle uyarısı sürer; kontrollü performans bütçeleri geçti. Canlı bot adaptörü, hesap/emir yetkisi ve genel sürüm onayı verilmez. Sonraki iş bu açık kabulün gözden geçirilmesidir; tekrarlanabilir uyumsuzluk çıkarsa hedefli REA araştırmasına dönülür.
