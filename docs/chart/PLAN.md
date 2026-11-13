# Profesyonel grafik geliştirme planı — v3

13 Kasım 2026 — **QA01 kontrollü masaüstü doğrulaması tamamlandı; uygulama planı 27/27.** [Kabul raporu](QA01-ACCEPTANCE.md): 920 Python/278 frontend testi, 18 raster durumu, 20 cleanup döngüsü, beş 60 saniyelik performans koşusu ve 10 temiz restore kontrolü geçti. rAF p95 her koşuda16,8 ms; wheel→frame-swap p95 78,487 ms. Genel sürüm/B5 fiziksel kabul açık; canlı entegrasyon kapalı. Sıradaki iş açık fiziksel kabul maddelerinin gözden geçirilmesi. Aşağıdaki önceki teslim kayıtları tarihseldir.

13 Kasım 2026. **P7 izole replay/kuru çalışma tamamlandı; sıradaki QA01 genel kabul.** [P7 teslimi](P7-ISOLATED-REPLAY-DELIVERY.md):36/36 gerçek senaryo,20 tür/48 sorgu, kalıcı episode/checkpoint, E3 Python/TS kimliği, sınırlı fake delivery ve kaynak doğrulamalı sonuç paneli.920 Python,276 frontend testi, üretim derlemesi,11 yeni ve12 P6 regresyon tarayıcı kontrolü geçti. Canlı entegrasyon kapalı; B5/fiziksel kabul ve QA01 açık.

Bu dosya ve [REA04 uygulama yol haritası](REA04-IMPLEMENTATION-ROADMAP.md) önceki sıra/statülerin üstündedir. Makine sözleşmesi [chart-core-plan-v3.json](contracts/chart-core-plan-v3.json). Eski ayrıntılı T/P tanımları ve araştırma geçmişi [v2 arşivinde](PLAN-v2-research-20261111.md); v2 JSON tarihsel sözleşme olarak korunur.

## Durum

- REA01/REA02 tamamlandı; REA03 sınırlamaları kayıtlı araştırma olarak kapandı; REA04 planı tamamlandı. Tam vendor parity veya bütün QA kabulü iddiası yok.
- Önceden tamamlanmış T01/T02/P2/P3/T03 korunur; G01/G06/G02/G03/G04/G05, T05, T07, T04, T06, T12, T13, T08, T09, T10, T11, T14, P4, P5, P6 ve P7 eklendi. **Güncel uygulama planı27/27**; QA01 kontrollü kapsamda kapandı, fiziksel/genel kabul açık. Eski çekirdek5/21 tarihsel; sayı süre/efor yüzdesi değildir.
- Toplam49 araştırma fixture’ı; bunlar ürün test sayısı değildir. P7 için276 frontend ve920 Python testi geçti;36 senaryo bu Python kapsamının içindedir.
- Yeni araştırma özeti [son birleşik turda](REA-FINAL-NETWORK-DESIGN.md);6 REA kaydı, ayrı native kayıt ve5 hash doğrulanmış görüntü. Önceki kanıt paketleri ayrı korunur.

## G01 — tamamlandı

App.tsx/style.css üzerinde kompakt üst bar, gruplu çizim rail'i, kapatılabilir sağ panel; light/dark surface/text/accent/up/down/error tokenları, tutarlı ikon ve font/focus sistemi. Teknik paneller normal chart alanını sürekli işgal etmez. Mevcut cetvel/çizimler, kanonik hesap, veri tazeliği ve kayıt akışları korunur.

Bitiş:1536/1280/1024 CSS masaüstü, açık/koyu tema, panel açık/kapalı, seçili/hover/focus/disabled/stale durumları; klavye erişimi ve chart resize. G01 ilk tesliminde diğer bütün araç/göstergeler bir kerede uygulanmaz. Tasarım her paketin işlevsel kabulünün parçasıdır.

## Kesin uygulama sırası

| Aşama | Sıra | Sonuç |
| --- | --- | --- |
|Kabuk ve bağlam|G01 → G06 → G02 → G03|Tasarım temeli, günlük arama/navigasyon, pane/scale altyapısı, Data window/readiness|
|Araç ve çizim yönetimi|T05 → T07 → T04 → T06 → T12 → T13 → G04|Ray/uzatma; yönetim; long/short; kanal; Fib; log; metin/fiyat etiketi|
|Interval ve göstergeler|T08 → T09 → T10 → G05 → T11|Üst-zaman; kalıcı config; SMA/EMA/RSI/ATR; MACD/BB; VWAP|
|Çalışma alanı|T14|Pane/config/style/şablon kaydetme ve restore|
|Bot uyumu|P4 → P5 → P6 → P7|Revision/uygunluk/neden/yerel intent ve izole replay; dış yan etki yok|
|Kabul|QA01|Masaüstü işlev, görsel, veri, cleanup ve performans; restore edilebilir aday|

Altı yeni paket G01 kabuk, G02 pane/scale, G03 Data window/readiness, G04 metin/etiket, G05 MACD/BB, G06 günlük navigasyondur. T/P paketlerinin eski tamamlanması sıfırlanmaz.27 düğümün tüm bağımlılıkları [doğrulama kaydında](../../reports/rea-chart/final-rea04-validation-20261111.json) döngüsüz ve bu sırayla uyumlu.

## Kapsam ve hesap kararları

[Seçilmiş profesyonel kapsam](PROFESSIONAL-CHART-SCOPE.md) geçerlidir. Referans bütün menülerini kopyalama hedefi yoktur. Lightweight Charts ve kendi hesap/geometri/kayıt altyapımız korunur; vendor kodu/marka yüzeyi ürüne taşınmaz. İleri multi-chart/replay/profile ve gerçek touch/mobile ayrı karardır; broker/emir yürütme bu kapsamda değildir.

RSI v2 flat100 T10’da sürümlü model ve açık ayar seçimiyle eklendi; eski kayıtlar ve analysis.py v1 flat50 olarak korunur. Bot/replay sürüm uygunluğu P4–P7 işidir. EMA/ATR origin seed, NA ve VWAP session/zero-volume sözleşmesi deterministik açıklanır; kanıt yokken TradingView exact denmez. Missing/unavailable/error0 değildir. Σvolume0 için VWAP unavailable; önceki pozitif toplama eklenen0-hacim toplamı değiştirmez.

## Açıklar artık kabul işidir

| Açık | Sahip/kapanış |
| --- | --- |
|Mevcut socket üzerinde gerçek blackout/catchup/dedup|G03/QA01; kontrollü yerel fixture/proxy; cold reload deneyi bunun yerine geçmez|
|Origin seed/NA, sıfır hacim/DST/calendar|T10/T11; sürümlü açık hesap politikası ve negatif sayısal fixture|
|Frame/input p95, doğru workload ve cleanup|G01/G02/QA01; bu tur trace0 DrawFrame, ölçüm null; ürün kabulü açık|
|Pointercancel/lost capture ve sonraki gesture|T07/QA01; gerçek input ve history/persistence rollback; touch ayrı|
|Geç yanıt/cached source ve drawing/render readiness|G03; A→B→A, eski epoch ve async completion; boş tree silme değildir|
|1024 dialog/panel ve uzun etiket/price precision|G01/G02/QA01; stabil kendi tasarım fixtureları; transient referans görüntü PASS değildir|

QA01 performans hedefleri ve5 tekrar/20 cleanup çevrimi [REA04](REA04-IMPLEMENTATION-ROADMAP.md) içinde tanımlı. Ölçülemeyen performans kabulü kapanmaz. Her pakette etkilenen test ve üretim derlemesi; gereksiz bütün test tekrarları yok. Kesin fiyat/bot kaynağı UI formatter değildir.

REA’ya geri dönüş: aynı kapalı veri/ayar/precision ile açıklanamayan hesap farkı; stale/çift/kayıp mum; yanlış gesture/history; ölçülmüş bütçe aşımı. Tek soru ve minimal tekrar kanıtıyla araştırma açılır; yeni geniş envanter turu varsayılan değildir.
