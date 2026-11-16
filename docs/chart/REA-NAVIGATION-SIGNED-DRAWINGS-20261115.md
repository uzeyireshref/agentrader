# Grafik gezinmesi, fiyat ölçeği ve sıfır altındaki çizimler

15 Kasım 2026. Önceki alt-bölge düzeltmesinin görünümü otomatik kaydırması kaldırıldı. Bu teslim, 27 görevli uygulama planının ardından gelen kullanım düzeltmesidir; eski QA01 arşivi yeni derleme için kabul kanıtı değildir.

## REA bulguları ve sınırları

TradingView anonim/geçici Chrome oturumunda gerçek Supercharts yüklendi. REA `ev_4738eecfcb0985d9a090caa32d2970457b6ca1e31dc6f6b2b6a1f1cdcc9f4422`: mum alanı, ayrı eksen ve gezinme kontrolleri gözlendi. `ev_e0a28b62dad2e427a9c18db0abb9f1b5e42dda103d873c39fffef7de1a275fcf`: ayarlar açıldı. `ev_66593ff2152ab46a97a00ade92c2d3afe7e414b1bf8384a3f000ef032acb26f5`: Scales and lines sekmesinde fiyat/zaman oranını kilitleme kapalı, geniş uzaklaştırma kapalı, A/L ölçek kontrolleri ayrı gözlendi. Tam Evidence kayıtları `reports/rea-chart/navigation-*-20261115.json` dosyalarındadır. REA'nın açtığı headless süreçler kapanmıştır; mevcut hesaba giriş, düzen kaydı veya hesap değişikliği yapılmadı.

[Resmî otomatik ölçek açıklaması](https://www.tradingview.com/support/solutions/43000762826-how-to-enable-autoscale/), [Supercharts yapılandırması](https://www.tradingview.com/support/solutions/43000748166-how-to-configure-your-supercharts/) ve [Featuresets](https://www.tradingview.com/charting-library-docs/latest/customization/Featuresets/) ayrı otomatik sığdırma, reset, yatay wheel kaydırma ve wheel zoom davranışlarını destekler. Bu belgeler Supercharts'ın özel kaynak kodunu veya fiziksel cihaz hissinin sayısal eşitliğini kanıtlamaz.

Kullanıcı TradingView'de sıfır altında çizim yapabildiğini bildirdi. Bu turda doğrudan negatif çapalı vendor çiziminin kayıt/form verisi doğrulanmadı; bu bulgu kullanıcı gözlemidir. Canlı ayar incelemesi ve kendi native motor kaynağının incelenmesi, davranış tasarımının dayanağıdır. 1:1 vendor gesture eğrisi veya bütün araçlarda vendor parity iddiası yoktur.

## Neden rahatsızdı, ne değişti?

- Önceki `ensureDrawingViewport` görünür aralığı çizim sırasında yukarı itiyordu. Dosya ve çağrıları kaldırıldı; araç seçimi görünümü değiştirmez.
- Lightweight Charts 5.2.1 native `_internal_startScroll/_internal_scrollTo`, autoScale açıkken dikey panı bırakır. Yeni `chartGestures.ts` boş ana mum alanında gerçek dikey hareket başladığında manuel ölçeğe geçer; basit tıklama bunu yapmaz. Native yatay gezinme korunur.
- Sağ fiyat ekseninde sürükleme, tutulan fiyatın çevresinde sürekli üstel ölçek uygular. 70 CSS piksel aşağı hareket testinde aralık 1,522 kat oldu; zaman aralığı değişmedi. Eksen çift tıklama otomatik sığdırmayı geri getirir. Log ölçekte pozitif aralık korunur.
- Lineer çizim koordinatları sonlu sıfır ve negatif sayıları destekler. Yatay/trend/kanal/Fib/metin geometri yollarında bu alan artık sırf işaret nedeniyle kaybolmaz. Negatif tick yuvarlama işarete simetriktir; sıfır normalize edilir. Yeni mum veya market verisi üretilmez.
- `coordinates.py` ve `snapDrawingPrice/onDrawingTick` yalnız çizim alanına aittir. Genel piyasa `decimal_text`, `snapPrice/onTick` ve long/short plan fiyatları pozitif kalır. Negatif/sıfır çapalı çizim bot uygunluğunda `NON_POSITIVE_DRAWING_NOT_TRADE_ELIGIBLE` ile BLOCKED olur; emir yetkisi vermez.
- Log görünüm sıfır/negatif çapaları matematiksel olarak göstermez; kayıtlar silinmez. Cetvelin sıfır başlangıçtan yüzdesi ve işlem odaklı hesaplar geçersizse hesap sonucu kullanılamaz kalır; bu durum çizim geometrisini otomatik kaydırma gerekçesi değildir.

## Doğrulama

`reports/chart-navigation-signed-20261115.json`: gerçek Chromium pointer girdisi, production App/API ve geçici SQLite ile 6 kontrol geçti: bağımsız eksen zoom'u; çift tık reset; otomatikten manuel dikey pan; görünüm sıçramadan negatif yatay çizgi kaydı; sıfırı geçen trend kaydı; gerçek reload sonrası negatif geometri. Yoğun 199-çizim fixture'ında yalnız boş-alan pan kontrolü sırasında hit katmanı gizlenip geri getirildi. Ayrı çizim noktaları native çift tık penceresinden bağımsız verildi. Test fiziksel trackpad kabulü değildir.

362 frontend testi ve üretim derlemesi geçti. 1.261 Python testi geçti; yeni negatif hedef uygunluk testi dahil geometri/uygunluk grubunda ayrıca 18 test geçti. 36/36 replay senaryosu yeniden çalıştırıldı, kaynak hash'leri ve bağlama kataloğu yeniden üretildi. Güncel sunucuda katalog VERIFIED_TRACEABILITY ve replay VERIFIED_ISOLATED; üç kullanıcı çiziminin yanıt hash'i yeniden başlatma öncesi/sonrası aynı. Kullanıcı çizimleri veya emir depoları test amaçlı değiştirilmedi.

Kanıtlar: `reports/navigation-tests-20261115.log`, `navigation-python-20261115.log`, `navigation-safety-tests-20261115.log`, `navigation-build-20261115.log`, `navigation-p7-20261115.log`, `navigation-preview-health-20261115.json`. Mevcut 500 kB bundle uyarısı sürer. Önceki beş performans koşusu/fiziksel B5 bu değişiklik için tekrarlandı sayılmaz.
