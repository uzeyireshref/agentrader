# Tüm grafik araçları: bot yazma/okuma ve görünüm kabul planı

14 Kasım 2026. Önce bu plan ve makinece okunur envanter kaydedildi; testler aşağıdaki sırayla uygulanacak. Sonuçlar reports/all-chart-tools-20261114/ altında tutulur. Çalışan kullanıcı çalışma alanı, çizimler ve işlem deposu değiştirilmez; hesap/emir/anahtar erişimi yoktur. Aynı üretim API ve arayüzü ayrı SQLite dosyaları ve kesin koordinatlı test mumlarıyla sınanır.

## Envanter ve kapsam

22 çizim türü: horizontal, horizontal_ray, trend, ray, extended_line, zone, ruler, fibonacci, fibonacci_extension, parallel_channel, flat_channel, disjoint_channel, regression_channel, pitchfork, schiff_pitchfork, modified_schiff_pitchfork, inside_pitchfork, long_plan, short_plan, text, note, price_label.

Eski/yeni Fibonacci, bölge ve paralel kanal şemaları ayrı olduğundan toplam 25 çizim varyantı sınanacak. Fibonacci projection yalnız katalogda ilanlıdır; var olmayan bir araç başarılı sayılmayacak. Dokuz gösterge yapılandırması: iki EMA, RSI, SMA, ATR, MACD, Bollinger Bands, session VWAP ve anchored VWAP. Ayrıca aşağıdaki etkileşim ve görünüm özellikleri kapsanır.

## Sıralı paketler

1. P0: Kaynak/envanter, şemalar, mevcut sözleşme ve veri erişim sınırları. Envanter tamamlandı; özellik başarısı anlamına gelmez.
2. P1: Botun API üzerinden 25 varyantı oluşturması; UTC saniye/Decimal fiyat koordinatlarının birebir geri okunması; etiket, Türkçe/Unicode ve çok satırlı notlar; yeni okuyucu ile kalıcılık; sürümlü güncelleme; kilit/gizlilik/stil/zaman dilimi ayarı; eski revizyon, yanlış sahip, silinmiş nesne ve sözleşme/sayısal sorgu sonuçları.
3. P2: Aynı bot/API üretimi nesnelerin gerçek üretim tarayıcısında doğru yerde görünmesi. Koordinat geri dönüşünde en çok 1 CSS px; yüklü veri ve veri sonrası gelecek; yeniden yükleme; veri geldikten sonra UTC kaymaması; lineer/log destek veya açık engel. Regresyon hesabı için gerçek yüklü mum gereksinimi ayrıca kaydedilir.
4. P3: Tüm gösterge ayarlarını API üzerinden yazıp okuma, parametre ve veri bağlamı, görünümde üretilen sayılar, warmup/eksik veri durumları. Gösterge yapılandırmasının okunması ile botun hesaplanmış seri/son değere erişimi ayrı doğrulanır.
5. P4: Çizim seçme/çoklu seçim, taşıma, çapa düzenleme, undo/redo, kopyalama; magnet/tick; not/etiket/kanal metni; hide/lock/stil; Fib oranları ve kapsamları; kanal/pitchfork/regresyon; long/short plan ve cetvel; gösterge/panel/bölme/volume/VWAP; tema ve lineer/log; görünüm/profil/şablon; sembol/zaman dilimi/favori/arama/üst zaman dilimi; pan/zoom/wheel/eksen/reset/son mum; data window; kurallar/alarmlar/zamanlama/bildirim/replay/gölge/önizleme/onay; geçmiş yükleme, reconnect/stale, render recovery; iki sekme/revizyon yarışları ve hatalar. Her başlıkta API bot okuması, tarayıcı görünümü ve yalnız yerel UI durumu ayrılır.
6. P5: Tam Python ve frontend regresyonu, üretim derlemesi, tek tek sonuç/kanıt tablosu ve eksik geliştirme listesi. Üretim kodu değişirse ilgili kabul tekrar edilir.

## Her araç için kabul ölçütü

- Botun verdiği koordinat ile saklanan ve geri dönen koordinat aynı olmalı; sessiz yuvarlama olmamalı. Tick uyarlaması gerekiyorsa açıkça test edilmeli.
- Yazılan etiket, not, metin ve seçenekler silinmeden/bozulmadan okunmalı. HTML metni kod olarak çalışmamalı.
- Bot oluşturduğu nesneyi ID/revizyon ile tekrar bulabilmeli, beklenen değişikliği yapabilmeli; başka sahip/çalışma alanı verisini alamamalı.
- Görsel kontrol, API kaydının varlığından çıkarılmamalı; gerçek çizim izdüşümü ve ters koordinat ölçümü gerekir.
- Veri sonrasındaki tarih ile ekran pikseli doğru eşlenmeli. Matematik için mum gereken araçlarda veri yokken uydurma değer üretilmemeli.
- Hesaplanabilir araçlarda bağımsız sayısal referans; görsel araçlarda ham koordinat/metin okuması ve açık hesaplama engeli bulunmalı.
- Nesne özellikleri, ekranda hesaplanan değerler ve geçici UI durumu farklı sütunlarda raporlanmalı. Botun erişemediği özellik NOT_EXPOSED_TO_BOT olarak açık kalmalı.

## Durum sözlüğü ve kapanış

PASS: ilgili ölçüt güncel testte kanıtlandı. FAIL: beklenen davranış hatalı. EXPECTED_BLOCK: desteklenmeyen işlem açıkça ve doğru engellendi. VISUAL_ONLY: nesne okunuyor fakat matematik yetkisi yok. NOT_EXPOSED_TO_BOT: özellik UI'da var ama bot okuma arayüzü yok. PARTIAL: katmanlardan yalnız bazıları kanıtlı. NOT_RUN: henüz çalıştırılmadı.

Sayı/ekran/kayıt testlerinden biri diğerinin yerine geçmez. Bütün özellikler için tek genel yeşil sonuç yerine ayrı satır ve kanıt verilecek. Otomatik strateji seçimi, kârlılık veya gerçek emir bu planın kapsamında değildir.


## Güncel kapanış

P0–P5 tamamlandı. [Araç bazında sonuçlar ve açık erişim eksikleri](45-TUM-GRAFIK-ARACLARI-BOT-YAZMA-OKUMA-TEST-SONUCLARI.md). Tamamlanan denetim, eksik bot arayüzlerinin uygulandığı anlamına gelmez. Kopyalama kapsamı Duplicate işlemidir; genel pano yapıştırma yoktur.
