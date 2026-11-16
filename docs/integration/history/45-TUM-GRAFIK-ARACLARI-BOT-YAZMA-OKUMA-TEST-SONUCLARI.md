# Tüm grafik araçları: bot yazma/okuma kabul sonuçları

14 Kasım 2026. Plan 44 önce yazıldı; P0–P5 sırasıyla tamamlandı. Sonuç: **denetim tamamlandı, bot erişim eksikleri açık**. Testler izole depolarda ve sentetik Demo bağlamında çalıştı; hesap/anahtar erişimi ve emir gönderimi yapılmadı. Mevcut kullanıcı çizimleri değiştirilmedi.

## Kanıtlanan davranış

- 22 araç türünün 25 şema varyantında API ile oluşturma, tam UTC/fiyat geri okuma, revizyonlu düzenleme, silme, kalıcılık, sahip/çalışma alanı ayrımı, kilit ve görünürlük geçti.
- 100 tarayıcı koordinat senaryosunun 98'i geçti; 2 regresyon senaryosu beklenen veri gereksinimi nedeniyle engelli. Desteklenen çizimlerde hata en çok 1 CSS piksel; veri sonrası tarih, yeniden yükleme, lineer/log ve sonradan gelen mumlar kontrol edildi.
- 9 gösterge yapılandırması API üzerinden yazılıp okundu. Üç sayısal tarayıcı paketi EMA/RSI/SMA/ATR/MACD/BB/session VWAP/anchored VWAP sonuçlarını bağımsız referanslarla doğruladı.
- 25 güncel etkileşim paketi geçti: düzenleme, kanal ailesi, Fib, magnet, ölçek/görünüm, iki sekme, veri toparlanması, profil/şablon, gölge/önizleme/onay ve alarm ayarları dahil.
- Tam regresyon: **1163 Python + 343 frontend testi geçti**, üretim derlemesi başarılı. Derlemede 500 kB üstü paket uyarısı var.

## Botun gerçekten erişebildiği katmanlar

API test istemcisi botun çağrılarını taklit etti. Bu sonuç, çalışan işlem botunun kendi kendine araç seçip çizim stratejisi yürüttüğünü kanıtlamaz; genel otonom çizim adaptörü/stratejisi henüz yoktur.

Ham koordinatlar, etiketler, desteklenen metinler, seçenekler, stiller ve nesne sözleşmeleri API'den okunabilir. 8 kanal ailesi + 3 açıklama varyantında tam metin alanı vardır; diğer araçlarda kısa etiket kullanılabilir, uzun not için ayrı Note nesnesi gerekir. Desteklenmeyen metin alanı 422 ile reddedildi.

14 varyant için Python kütüphanesinde sayısal çıktı doğrulandı; 11 varyant görsel/metin amaçlıdır ve hesaplama talebi açıkça engellenir. Genel HTTP hesaplama sorgusu yoktur. Ham yatay çizgi fiyatı gibi doğrudan alanlar ayrıca okunabilir. Gösterge ayarları okunur, hesaplanmış gösterge serileri için bot HTTP uç noktası yoktur. Katalogdaki readable bayrağı tek başına bütün bu katmanları anlatmaz.

Regresyon kanalı gerçek mumları kullanır, tıklanan fiyatları fit girdisi saymaz. Mum başlangıcına denk gelmeyen zamanları ham kayıt kabul etse de çizim hesaplanamaz; API hazır olma durumunu henüz bildirmez. Diğer kanallarda türetilen sınır tutamacı ham üçüncü çapa ile aynı uç nokta olmak zorunda değildir. Fibonacci projection yalnız katalog kaydıdır; oluşturma 422 ile reddedilir.

Kaydedilmiş profil/şablon ile anlık ekran aynı şey değildir. İmleç/hover, seçili araç/nesne, zoom/viewport, magnet, undo geçmişi, favoriler, yerel bildirim tercihleri ve anlık tema genel bot API'sinde yayımlanmaz. Tarayıcı testinin bunları görebilmesi sunucu botuna erişim sağlamaz. Duplicate test edildi; genel pano yapıştırma özelliği uygulanmış değildir.

## Sonraki geliştirme sırası

1. Bot için salt okunur ortak grafik bağlamı: nesneler, kaynak/UTC/revizyon, hesaplama hazır olma durumu; kalıcı ve anlık durum açık ayrılmalı.
2. Türetilmiş çizim değerleri ve gösterge serileri için kaynak kanıtı/warmup içeren sorgular. Görsel araçlara yalnız bayrak değiştirerek işlem yetkisi verilmemeli.
3. Genel bot çizim adaptörü: bot kökeni/nesne alanı, idempotency ve manuel çizimleri koruma. Aynı yerel sahip içinde manuel/bot kökeni henüz ayrılmıyor.
4. Katalog/şema keşfini ve regresyon giriş koşullarını tutarlı hale getirme; ardından ayrı otonom strateji kabulü.

## Araç bazında sonuçlar

API sütunu oluşturma/okuma/düzenleme/silmeyi kapsar. Sayısal sütun Python kütüphanesidir; HTTP hesaplama erişimi bütün satırlarda eksiktir.

| Varyant | API | Not erişimi | Python sayısal işlem | Tarayıcı senaryoları |
|---|---|---|---|---|
| horizontal | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| zone-legacy | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| zone-v1 | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| trend | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| fib-legacy | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| fib-v1 | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| ruler | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| horizontal_ray | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| ray | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| extended_line | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| parallel-legacy | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| family-parallel_channel | PASS | FULL_TEXT_FIELD | EXPECTED_BLOCK | PASS: 4 |
| family-flat_channel | PASS | FULL_TEXT_FIELD | EXPECTED_BLOCK | PASS: 4 |
| family-disjoint_channel | PASS | FULL_TEXT_FIELD | EXPECTED_BLOCK | PASS: 4 |
| family-regression_channel | PASS | FULL_TEXT_FIELD | EXPECTED_BLOCK | PASS: 2, EXPECTED_BLOCK: 2 |
| family-pitchfork | PASS | FULL_TEXT_FIELD | EXPECTED_BLOCK | PASS: 4 |
| family-schiff_pitchfork | PASS | FULL_TEXT_FIELD | EXPECTED_BLOCK | PASS: 4 |
| family-modified_schiff_pitchfork | PASS | FULL_TEXT_FIELD | EXPECTED_BLOCK | PASS: 4 |
| family-inside_pitchfork | PASS | FULL_TEXT_FIELD | EXPECTED_BLOCK | PASS: 4 |
| fib-extension | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| long_plan | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| short_plan | PASS | LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT | PASS | PASS: 4 |
| text | PASS | FULL_TEXT_FIELD | EXPECTED_BLOCK | PASS: 4 |
| note | PASS | FULL_TEXT_FIELD | EXPECTED_BLOCK | PASS: 4 |
| price_label | PASS | FULL_TEXT_FIELD | EXPECTED_BLOCK | PASS: 4 |

## Kanıt dosyaları ve kapsam sınırı

[Makine okunur matris](../../../reports/all-chart-tools-20261114/capability-matrix.json), [plan](44-TUM-GRAFIK-ARACLARI-BOT-YAZMA-OKUMA-TEST-PLANI.md), P1/P2/P3/P4/P5 raporları ve ekran görüntüleri `reports/all-chart-tools-20261114/` altındadır. Eski E3 tasarım prototipi ve eski toolbar kanal yolu güncel kabul yerine kullanılmadı; ham sonuçları korundu, yerlerine güncel sözleşme ve eski/yeni şema testleri kondu. Bu, eski prototiplerin geçtiği iddiası değildir. Test fikstürleri güncel Demo veri zarfına uyarlandı; eksik hassasiyet veya açık bozuk kanıt güvenilir seviyeye yükseltilmedi. Bu tur üretim uygulama kodu değiştirilmedi.
