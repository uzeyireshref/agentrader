# Grafik geliştirme sonuçları ve sonraki aşama kararı

10 Kasım 2026 — E5 incelemesi. **Kullanıcı grafik kapanış sırasını onayladı.** Ana planda 25 görevden 24 tamamlandı; B5 ertelenmiş/açık. Aşağıdaki ilk aday ölçümleri tarihsel E5 incelemesidir; güncel kapanış özeti dosya sonundadır. Planlama adımlarının bitmesi genel grafik kabulü veya bot entegrasyonu onayı değildir.

## Ulaştığımız durum

Kendi web terminalimiz mevcut: Lightweight Charts motoru, uygulamaya ait yatay/bölge/trend/Fibonacci geometrileri, EMA/RSI, coin/zaman dilimi, yakınlaştırma/kaydırma, manuel/otomatik ölçek, klavye, sürümlü kayıt ve undo/redo. TradingView hesabındaki çizimleri botun okumasına bağımlı değiliz; fakat Lightweight Charts kullanıldığı için gerekli atıf/logo ve lisans sınırları korunur.

Aday `chart-candidate-20261110-01`, bundle `index-DIUEWtQr.js`, kaynak/paket/dependency snapshot’ı ve geri dönüş yönergesiyle sabit. E2’de675 Python ve123 frontend testi/derleme yeniden geçti;250 arşiv dosyası, ayrı klasörden20 localhost API kontrolü/restart/statik paket doğrulandı. Bu E5 turunda testler tekrar çalıştırılmadı.

Performansın doğrulanan kapsamı Windows11/headless Chromium145/1400×1000/DPR1.4.000 mum/200 çizimle üç60sn koşuda p95=16,7/16,7/16,8ms. Gerçek30dk2sn kontrollü oturum,61 tam veri/native seri örneği,iki mum geçişi veiki reconnect geçti. Post-GC kaynak sayıları sabit; heap+1.771.904byte,2MiB tarama bütçesi içinde. Bu sınırsız süre sızıntısızlık veya her fiziksel cihazda60FPS garantisi değildir.749,9ms outlier’ın kesin nedeni belirlenmedi; sıfır takılma iddiası yapılmaz.

## Henüz ne tamamlanmadı?

- Fiziksel trackpad yatay davranışı: eski görünür koşu FAIL; sonraki kod düzeltmesi fiziksel tekrar almadı. B5 D03/D05/D06 eksik; dokunmatik D08/D09 için cihaz yok.
- Sayısal native/SVG hizalama güçlü, fakat raster/fiziksel DPR ve ekran okuyucu kapsamı açık.
- Kayıt/409/retry/undo testleri geçti; güncel iki browser sekmesiyle eşzamanlı test tamamlanmadı.
- Tam App bağımsız gösterge hatası ve uzamış upstream kesintisi/saat sapması gibi kapsamlar açık.
- E3 sözleşmesi ve E4’teki36 senaryo tasarım çıktısıdır.19 E3 wire kontrolü ve14 E4 plan denetimi, bot motorunun uygulandığı veya36 senaryonun çalıştığı anlamına gelmez.

Mevcut mum float taşıması, güvenilir upstream saat kanıtı, stream epoch ve kalıcı revision-bound event/dedup gibi E3 gereklilikleri tamamlanmadan bugünkü LIVE grafik verisi bot kararına uygun sayılamaz. Projedeki eski demo yürütme çekirdeği ile grafiğe bağlı yeni bot ayrı kapsamdır; grafik bu çekirdeğe bağlanmadı.

## Önerilen sonraki sıra

| Sıra | Somut iş | Bitiş koşulu |
| --- | --- | --- |
| CL01 | Aynı geçici depoyla iki gerçek browser sekmesinde kayıt/çatışma/undo/retry | Kazanan sürüm korunur, kaybeden toparlanır, tekrar ve market karışması oluşmaz |
| CL02 | Tam App gösterge/mum/hacim hata enjeksiyonu | Durum hatayı gizlemez; tutarlı toparlanma kanıtlanır |
| CL03 | Raster/viewport/DPR ve görünür düzen | Otomatik görüntü/numeric kanıt birlikte değerlendirilir; fiziksel iddialar yalnız gerçek ortamla |
| CL04 | B5’in yalnız açık fiziksel durumlarının kısa tekrarı | Yatay/çapraz/pinch ham olay izi ve mum aralığı; eksik klavye/tam ekran kanıtları |
| CL05 | Bot öncesi E3 güvenilirlik/bağ kanıtlarının uygulanma planı | Eksik kanıtta BLOCKED; sonraki adapter işi ayrıca onaylanır |

Önerim önce grafiğin kalan kabul açıklarını kapatmaktır. Otomatik yapılabilecek işleri kullanıcıya devretmeyeceğiz;30 dakika testini küçük her değişiklikte tekrarlamayacağız. Fiziksel giriş ancak gerekli olduğunda kısa ve hedefli istenir. Dokunmatik cihaz yokluğu başarılı test sayılmaz veya destek kapsamı kullanıcı yerine daraltılmaz.

CL01 ilk somut iştir. Bu sıranın onayı bot/hesap/emir bağlantısı veya dış bildirim gönderimi yetkisi değildir. Sonraki W4 işi ancak açık ön koşullar ve ayrı kullanıcı kararıyla önce izole, yerel kuru çalışma olarak ele alınabilir.

## Karar

Önce CL01→CL04 ile kalan grafik kabul açıklarını kapatma sırasıyla devam edelim mi? Bot bağlantısı ayrı onay ve ön koşullar gerektirmeye devam edecek.

Başvurular: [kabul kapsamı](ACCEPTANCE.md), [sabit aday/geri dönüş](RELEASE.md), [veri sözleşmesi](BOT-DATA-CONTRACT.md), [kuru çalışma senaryoları](DRY-RUN-PLAN.md), [makine okunur inceleme](../../reports/chart-user-review-20261110.json).


## Güncel takip — 10 Kasım 2026

CL01/CL02 tamamlandı; CL03 kontrollü raster kapsamı geçti. Güncel geliştirme adayı 02 ve bundle index-z15JopqV.js. CL04 fiziksel testleri kullanıcı müsait olmadığı için ertelendi, B5 açık. CL05 yalnız uygulama planı olarak tamamlandı: [Güvenilirlik planı](RELIABILITY-PLAN.md). Yedi paket henüz uygulanmadı; ilk somut kod işi P1 kesin ondalık taşımasıdır. Bot entegrasyonu onaylanmadı. Güncel sonuçlar reports/chart-closure-validation-20261110.json içindedir.
