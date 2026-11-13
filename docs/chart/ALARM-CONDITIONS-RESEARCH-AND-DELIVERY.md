# Alarm koşulları ve panel yenilemesi

13 Kasım2026. Kullanıcı isteği: TradingView'e yakın düzgün bir oluşturma paneli, abonelik engeline bağlı olmadan çeşitli koşulların araştırılması ve mevcut grafikte gerçek hesapla çalışması.

## Araştırma kaynakları ve tasarım kararı

Canlı REA gözlemleri önceki `REA-ALERTS-RESEARCH.md` ve `reports/rea-chart/alerts-live-research-20261113.json` altında. Çoklu koşulun ücretli plan kapısı gözlenmişti; bu kez birincil internet kaynaklarıyla koşul modeli ve gösterge çıktıları araştırıldı. Üçüncü taraf kodu veya abonelik erişimi taklit edilmedi; kendi uygulamamızda bağımsız koşul cebiri kuruldu.

- [TradingView çoklu koşullar](https://www.tradingview.com/support/solutions/43000761492-multi-condition-alerts/): beşe kadar koşul, tümünün birlikte sağlanması, aynı sembol ve farklı periyotların desteklendiği model. Bizde en fazla8 koşul ve açık VE/VEYA seçimi var. Bu sayı ve VEYA, ürünümüzün kendi tasarımıdır; TradingView eşitliği iddiası değil.
- [Teknik alarm operatörleri](https://www.tradingview.com/support/solutions/43000763315-getting-started-with-technical-alerts/): kesişme/yön, karşılaştırma, kanal içinde/dışında/giriş/çıkış ve belirli mumlarda mutlak/yüzdesel hareket aileleri. Gösterge ayarlarının alarm oluşturulurken saklanması da belgeleniyor.
- [Alarm yürütme modeli](https://www.tradingview.com/pine-script-docs/concepts/alerts/): mum içi ve mum kapanışı frekansları farklıdır. Mevcut backendimizin kapalı mum kanıtını kullanarak kapanış değerlendirmesini koruduk; UI'ye çalışmayan intrabar seçeneği koymadık.
- [Başka periyotlar ve repainting](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/): onaylanmamış üst-periyot değerleri değişebilir. Karışık periyot birleştirmesi ayrıca zaman hizası/son kesin kapanış sözleşmesi gerektirir. Bu teslimde tüm koşullar tek seçilen alarm periyodunda çalışır.
- [RSI](https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/):0–100 osilatör ve ayarlanabilir eşikler. RSI'nin yalnız fiyat tipi bir seri gibi ele alınamayacağını dikkate alıp imzalı sabit değerleri de kabul eden sayısal operand ekledik.
- [MACD](https://www.tradingview.com/support/solutions/43000502344-moving-average-convergence-divergence-macd-indicator/): MACD/sinyal/histogram ayrı çıktı. İki gösterge çıktısı birbirine veya sıfır gibi sabite karşılaştırılabilir.
- [Bollinger Bands](https://www.tradingview.com/support/solutions/43000501840-bollinger-bands-bb/): orta/üst/alt seriler ayrı operanddır. Kanal koşulunun alt/üst sınırına bunlar atanabilir. Kaydırılmış BB alarm girdisi olarak reddedilir.
- [ATR](https://www.tradingview.com/support/solutions/43000501823-average-true-range-atr/): fiyat yönü değil oynaklık ölçüsüdür. ATR için büyüktür/küçüktür/eşik ve değişim koşulları kullanılabilir; yön sinyali varsayılmadı.

Bu kaynaklar kavramsal dayanak sağlar; TradingView sunucusunun bütün eşitlik/minute/rearm ayrıntılarının tersine mühendislikle kanıtlandığı anlamına gelmez.

## Panel

Oluşturma editörü ve alarm yöneticisi ayrıldı. Başlıkta sembol, Ayarlar/Mesaj sekmeleri, solda alan adı/sağda kontrol düzeni, numaralı koşul satırları, Koşul ekle, VE/VEYA seçimi ve sabit alt eylem çubuğu. Gün sonu/bir hafta/bir ay/süresiz/özel tarih önayarları. Koyu/açık temada mevcut terminal tokenları;600px'te tek sütun. Kaynaklar fiyat/hacim, grafik göstergeleri ve hesaplanabilir çizimler olarak gruplu. Gösterge/çizim snapshotı güncel grafikten farklıysa kayıtlı ayar olarak görünür ve sessizce değiştirilmez.

Mesaj düz metindir; yerel tetikleme geçmişinde görünür. Henüz olmayan webhook/email/ses için çalışıyormuş gibi ayar sunulmadı. Genel tarih alanı tarayıcının yerel saatini ve saat dilimini gösterir; veritabanında UTC epoch saklanır.

## Çalışan kaynaklar

- Piyasa: OHLC, HL2/HLC3/OHLC4, baz hacim ve quote hacim. Native exact decimal değerler kullanılır.
- Mevcut grafik hesapları: iki EMA örneği, SMA, RSI, ATR, MACD üç çıktısı, BB üç çıktısı, sessionVWAP ve geçerli çapa kurulmuş anchoredVWAP. Parametreler, source, calculation_version ve çapa ayarları snapshot olarak kaydedilir. Grafikte sonradan değişen ayarlar alarmı sessizce değiştirmez.
- Çizimler: yatay, yatay ışın, trend, ışın, uzatılmış çizgi, fib oranları ve eski hesaplanabilir paralel kanal sınırları. Snapshot geometri ve mevcut canonical query kullanılır. Çizim kapsamı dışında sonuç gelmezse alarm hesap bekler.
- Yeni channel-family/pitchfork kayıtları DISPLAY_ONLY kaldığı için listelenmez. Bunları piksellerinden rastgele fiyat üretip alarm yetkisine çevirmedik; ekranda bu kapsam belirtilir.

Gösterge hesapları grafikle ortak Python referanslarını kullanır: indicator_config.series/multi_series ve vwap_series. EMA/RSI/ATR seed/warmup sunucunun yüklediği mevcut geçmişten başlar. Grafik elle daha fazla tarih yüklediyse seed farkı olabilir; burada tam-history veya TradingView numeric parity iddiası yok. Feedin499 barlık geçmişine sığmayan warmup veya eksik UTC seans başlangıcı WAITING_CALCULATION üretir.

##17 operatörün kesin yerel sözleşmesi

Karşılaştırmalar son kapanmış mumda L/R operandlarıdır. a=Lönce−Rönce, b=Lşimdi−Rşimdi.

| Aile | Kural |
|---|---|
| Kesişme | a<0≤b veya a>0≥b. Önceki eşitlik tek başına yeni kesişme sayılmaz. |
| Yukarı/aşağı | Yukarı a<0≤b; aşağı a>0≥b. |
| Büyük/küçük/eşit/eşit değil | b>0, b<0, b=0, b≠0. Sayısal tolerans eklenmez. |
| İçinde/dışında | Alt≤L≤üst sınırı içeride; dışarı bunun tersi. |
| Giriş/çıkış | Önceki kapanış dışarıda/şimdi içeride veya tersi. Mum içi yol çıkarılmaz. |
| Mutlak yükseliş/düşüş | Lşimdi−L[N mum önce] ≥ eşik veya negatif değişim≥eşik. |
| Yüzde yükseliş/düşüş |100×değişim/abs(eski değer); eski değer0 ise hesap yok. |
| Ardışık yükseliş/düşüş | SonN adımın her birinde strict artış/azalış; düz adım koşulu bozuyor. |

HareketN1–100; statik hareket eşiği negatif olamaz. Alt>üst statik kanal kayıtta reddedilir; dinamik ters sınır hesap bekletir. VE tüm sonuçlar, VEYA en az biri true. Yetersiz/bozuk kaynak herhangi bir koşulda varsa VEYA için bile olay üretilmez; bilinmeyen değer false kabul edilmez. Snapshot, eşitlik, fiyat türü ve periyot sürümlü `technical-alert/2` tanımında saklanır.

## Runtime ve uyumluluk

Eski tek fiyat tanımları okunur ve motor tarafından aynı sözleşmeyle yürütülür. Editör bunları kayıpsız tek koşula çevirir; kullanıcı kaydetmeden depoda dönüşüm yok. Yeni koşullarda mevcut atomik olay+checkpoint, revision kontrolü, once/bar_close, stop/resume/reseed ve feed sahipliği korunur. Olay kaydı koşul sonuçlarını ve tanım snapshotını da içerir. Gösterge warmup durumu ilk baseline ve sonraki heartbeatlerde doğru WAITING_CALCULATION olarak kalır.

Tek kapanışta bütün koşullar aynı veri penceresinden hesaplanır. Intrabar, çoklu sembol, farklı periyotların birleşimi, otomatik emir, dış teslim ve yeni DISPLAY_ONLY çizim sorguları bu teslimin dışında. Bunlar UI'de etkinmiş gibi gösterilmez.

## Kabul

- tests/test_alert_conditions.py:17 operatör örnekleri, VE/VEYA/bilinmeyen kaynak, bakış penceresi, bütün mevcut gösterge aileleri, iki gösterge kesişmesi, VWAP, trend/fib/eski kanal, exact ondalık farkları, API create/edit409, değişmeyen snapshot, kalıcı olay/dedup ve heartbeat warmup.
- scripts/check_alert_conditions.mts: üretim Chrome'unda fiyat+RSI oluşturma/mesaj, pause/resume, VEYA ve kanal sınırları, yüzdelik lookback, reload, history/delete,600px,açık tema,süre seçimi ve8 koşul sınırı. Kişisel çalışma alanına sıfır test yazımı; API/WebSocket kontrollü fixture.
- Tam backend950 test;306 frontend testi; TypeScript ve üretim derlemesi. Ekranlar reports/alerts-conditions-ui-20261113 altında. Son runtime paket adı ve sunucu doğrulaması teslim sonunda kaydedilir.

Son üretim paketi: index-Cz97NEZV.js. localhost8765 gerçek GET /api/alerts doğrulandı; runtime_error=null, order_authority=false. Kayıtlı kişisel alarmlar test amacıyla oluşturulmadı/değiştirilmedi.


2026-11-13 follow-up: multi-timeframe conditions delivered; see [ALARM-MULTI-TIMEFRAME-DELIVERY.md](ALARM-MULTI-TIMEFRAME-DELIVERY.md). The earlier same-interval scope above describes that delivery snapshot.
