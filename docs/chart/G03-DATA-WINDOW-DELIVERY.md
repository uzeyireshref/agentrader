# G03 — veri penceresi ve bağımsız hazırlık durumları

12 Kasım2026. G03 tamamlandı; durum9/27, sıradakiT05 ray/çizgi uzatma. Test kohortu dosyaları başlangıç tarihi20261111 adıyla korunur; teslim manifesti20261112'dir.

## Kullanım ve sözleşme

Sağ rail'deki Veri penceresi veya sağ paneldeki Veri sekmesi; sembol/interval/kaynak, UTC mum zamanı, açık/kapalı mum, OHLC/baz hacim/USDT hacim ve etkin EMA20/50–RSI14 çıktıları. Son mum, İmleci izle ve Sabitle ayrı seçim modlarıdır. İmleç seçimi panelde Sabitle'ye ulaşılabilmesi için chart dışına çıkıldığında korunur; grafik içindeki boşluğa geçilirse geçerli seçim yoktur. Sabitlenen timestamp yeni canlı mumları takip etmez, aynı açık mumun güncellenen değerini takip eder. Yüklü geçmişten düşerse sessiz son-mum fallback'i yoktur.

Piyasa, göstergeler, çizimler ve geçmiş hazırlığı bağımsız gösterilir. PiyasaLIVE iken çizim read'i hâlâ beklenebilir. Çizim read hatası yüklenemedi, gerçek boş tamamlanmış read0 çizim hazırdır. Sayısal0, kapalı gösterge, yetersiz geçmiş, veri bekleme ve render hatası farklıdır. Kaynak ayrıntısıLAST_PRICE/UTC ve mevcut veri kanıtını gösterir; transportLIVE tek başına “doğrulanmış veri” etiketi değildir.

Sembol/interval renderında aktif bağlam anında türetilir; eski başlık/fiyat/çizim kombinasyonu gösterilmez. Eski veriyi taşıyan chart host yeni mumlar gelene kadar gizlenir. DataWindow context key'i seçim ve subscriber'ı sıfırlar; kaldırılmış listener'ın kuyruğa alınmış olayı canlı component'e yazamaz. Native crosshair OHLC'si ilgili timestamp'teki kaynak OHLC ile eşleşmeden seçilmez.

Stale/reconnect/gap durumunda son alınan değerler açık uyarıyla sunulur. Gerçek render error'da sayısal okuma ve çizim etkileşimi kapanır; başarılı repaint sonrası geri döner. BoşLIVE snapshot “Mum verisi yok” görünümüne çevrilir. Backend epoch/sequence, freshness, kanonik hesap ve kayıt protokolleri değiştirilmedi. Çizim görünümü yalnız yüklenmiş doğru sembolün nesnelerini kullanır; loading boş liste sayılmaz.

## Kabul

- **173/173 frontend test**, TypeScript ve üretim derlemesi geçti.6 yeni model/component testi; sıfır/unavailable, boşLIVE/blocked proof, eski context, pointer exit/pin, queued callback, warmup/stale/renderError ayrımı var.
- scripts/check_chart_g03.py: gerçek production App, kontrollü WebSocket/read sırası ve izole SQLite ile **14 kontrol** geçti. Piyasa hazır/çizim beklemesi, açık-kapalı mum,0 hacim, pin/latest, aynı bağlamlı gösterge, stale uyarısı, yanlış sembollü packet ve A→B→A geç çizim yanıtı sınandı.
- Read503→açık retry→ready ve history503 sonrası mevcut mumun korunması doğrulandı. Native candle setData/update testte kontrollü olarak hata verdi: RENDER_ERROR, sayısal kapanış/EMA unavailable; yöntemler geri alınıp başarılı repaint ile değerler döndü. Bu, yalnız sahte UI status gösterimi değildir.
- Boş yeni1h snapshot ve10 mum warmup sayısal0'a dönüşmedi. İki genişlik/iki tema ekranı kaydedilip incelendi. Page error0, dış istek0. Seed çizim revision'ları1 olarak kaldı; kullanıcı DB'si testte kullanılmadı.
- G01/G06/G02 **41 regresyon tarayıcı kontrolü** geçti:14+12+15. Testler fiziksel GPU/touch, live exchange parity veya uzun ağ blackout/catchup QA01 kabulü değildir; bu açıklar yerinde durur.

Kanıt reports/chart-g03-validation-20261111.json ve chart-g03-delivery-20261112.json; source/build/görsel hashleri manifestte. Yeni modüller DataWindow.tsx/chartReadiness.ts; App, DrawingPanel, ChartIcon ve terminal.css güncellendi. Yerel uygulama http://127.0.0.1:8765, açık sekme yenilenir.
