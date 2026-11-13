# Gösterge sınırları: sabit seri, periyot1 ve boş/hata durumu

11 Kasım 2026, REA03 geniş tur. Ürün kodu değişmedi. [Önceki tur](REA-TRANSITIONS-REVISION-READINESS.md) ve5/21 uygulama durumu korunur. Bu tur3 fixture eklenerek toplam47 araştırma fixture'ına ulaşıldı.

## Kanıt kapsamı

Araştırma Chrome'u kapalıydı. İlk açılan browser-profile düzeni Chart Not Found döndürdü; önceki kayıtla doğru research-visible profili belirlendi. Doğru düzen/hesap REA ile doğrulandı. Port9339 kullanıldı. Yanlış profildeki sayfaya giriş veya hesap değişikliği yapılmadı.

`reports/rea-chart/indicator-boundaries-early-inline-evidence-20261111.json`8 tam inline REA kaydını korur. Cleanup sonrası `rea-evidence-indicator-boundaries-20261111.json`13 kayıt içerir; birlikte21 benzersiz kayıt, önceki82 ile örtüşme0. Bu sayı bütün tarihsel kayıtların kümülatif toplamı değildir. Cleanup öncesi ve sonrası kanıt ayrı dosyalardadır.

`tools/rea/build-indicator-boundary-research.mjs` kayıtlı tabloları ayrıştırır, kapanmış satırları kontrol eder, mevcut saf ürün fonksiyonlarını kontrollü girdilerle çalıştırır ve manifest/hashleri doğrular. Sonuç `reports/rea-chart/indicator-boundaries-validation-20261111.json`;5 görsel hash doğrulandı. Ürün test paketi/derleme çalıştırılmadı. Kaynak probe'ları gerçek mevcut indicators.ts fonksiyonudur; tarayıcıya kod enjekte edilmedi.

## 1. Sabit fiyat kaynağında RSI14=100

Normal symbol search ile `BINANCE:BTCUSDT.P/BINANCE:BTCUSDT.P` sentetik oranı açıldı. Platform bunu kabul etti;1D/UTC, RSI14/Close, varsayılan SMA14 ve BB20/SMA/Close/2. REA `ev_38c22856771fb7ac98e4dd452baee9a4580dc8615b7dfa06065c94a79612d36d` başlık/OHLC1.0 ve RSI100.00 gösterdi.

Tablo `ev_968b07ad171b4ca5aeb5e8a0aeb609072198a236aadc2ccbfd925cc6be69f975`:33 günlük satır; açık11Kasım çıkarılınca10Ekim–10Kasım arasındaki32 kapalı satır. Hepsinde OHLC1.0, BB basis/upper/lower1.0, RSI ve RSI-based MA100.00. Divergence kapalı sütunlar ∅. Oran grafiğinde hacim pozitif/değişken kaldı; **sabit fiyat sıfır hacim değildir**. Sentetik spread hacmi exchange trade hacmi otoritesi olarak kullanılmaz.

Mevcut frontend/src/indicators.ts rsi fonksiyonuna40 adet sabit close1 ve period14 verilince26 çıktı50 döndü. Bu, kaynakta önceden görülen gain=loss=0→50 politikasını doğrular. Referansın down==0→100 dalıyla artık canlı sentetik gösterim bulgusu da uyumlu. **Ürün değiştirilmedi.** REA04 flat politikası ve bot/gösterge sözleşmesini açık karara bağlamalı; TradingView uyumu hedeflenirse100 adayı fixture ile teslim edilir.

Sınır: oran mathematically x/x olsa da edinilen platform fiyatları UI precision1.0'dır; hidden precision/raw input eşitliği yakalanmadı. Numeric capture için ordinary-CDP Page.navigate zaman aşımı verdi; kayıt yalnız error içeriyor. Platform origin seed, NA skip/reset algoritması, ham exchange verisi ve bütün history için exact parity iddiası yok. Bu, önceki uzun burnin yakınsamasından farklı, canlı sentetik display fixture'ıdır.

## 2. Çok uzun periyot: hata ile çıktı yok ayrı

BTCUSDT.P/1D/UTC üzerinde geçici RSI length10000, Close, SMA14. `ev_95d7b921e10070d976ed745236c14e062ba34920d99723e989a178b201ff51d3`: legend Runtime error RE10004 gösterdi; Data window RSI başlığı kaldı, değer satırı yoktu. Error düğmesine tıklama ek açıklama üretmedi; RE10004'ün iç nedenini veya kesin maksimum periyodu tahmin etmiyoruz.

Length3000'e dönüş `ev_70c6613cab13be584446f2a633e7496b231f9f7288d0403a2d8cbc86ddbb6d74`: aynı Data window'da RSI başlığı mevcut, sayı yok; runtime error düğmesi görünmedi. Yetersiz geçmiş/warmup açıklaması makul çıkarımdır; tam platform geçmiş sayısı/origin ve bütün yükleme anları yakalanmadı. İki durum da **0 değildir**; hata ve henüz kullanılabilir hesap yok semantiği ayrılmalı. Normal length1'e geçişte çıktı geri geldi, gösterge kalıcı bozulmadı.

## 3. RSI1: kapanmış mumlarda yükseliş100, düşüş0

RSI length1/Close, smoothing SMA length1; Chart/WaitON. Formdaki checkbox, numeric input olarak sayılmadı; ilk yanlış input-index girişimi durdu ve uygulanmayan adımlar başarısız kaldı. İlk canvas context menüsü görünür Short çizimini seçtiği için Table view yoktu; çizimler gizlendikten sonra grafik tablo menüsü açıldı. Bu başarısız denemeler başarılı kohorta eklenmedi.

`ev_81e0b93c33b4460bc522db162e8ae1253f5f628a0326799742c73a5e21e719b2`:32 tablo satırı. Açık11Kasım ve görünür daha eski komşusu olmayan son satır karşılaştırmadan çıkarıldı.30 kapalı close-to-previous-close karşılaştırması:14 yükseliş RSI100.00,16 düşüş RSI0.00; SMA1 aynı değer. Örnek10Kasım close73762.9, önceki75327.0→RSI0;9Kasım75327.0, önceki74823.5→RSI100.

Bu, period1 uç dal kabulüdür; RSI14 tümü yükselen/düşen history ve origin seed kanıtı değildir. Mevcut fonksiyon ayrıca14'ten az close değişimiyle RSI14,14'ten az close ile EMA14 çıktısı üretmedi; bunlar yalnız ürünün bugünkü saf hesap davranışıdır, platform warmup eşitliği değildir.

## 4. Tasarım ve veri durum sözleşmesi

REA04 önerisi: sayısal0, sayısal100, unavailable/warmup, inactive, runtime_error, missing_source, stale ayrı durumlar olmalı. Null/∅/atlanmış çıktı sütunu0'a çevrilmez. Gösterge adı ve ayarı hata/boş durumda da korunur; hata durumu okunabilir açıklama ve düzeltilebilir ayarla erişilebilir olur. Runtime vendor kodu bizim kullanıcıya gösterilen nihai açıklama yerine geçmez. Bot sayısal olmayan output'u eşiğe sokmaz; unavailable reason ve kaynak/revision taşır. Farklı precision, sıfır olmayanı sıfır sanma gerekçesi değildir.

Origin seed/warmup için ilk gerçek veri kaynağına erişilmeden kesin parity kapanmaz. Zero-volume kabulü ayrıca bir seansın ilk hacmi0, arada0 hacim, bütünü0 hacim, missing/null hacim ve negatif/geçersiz hacmi ayrı kontrollü senaryolarla kapsamalı. Bu tur canlı sıfır-hacim fixture'ı elde edilmedi; daha önceki missing-volume RE10142 onun yerine geçmez. Eksik girdiyi sessiz0 ile doldurmak önerilmez. Bu kararlar ürün kabul önerisidir; her biri referansta gözlendi diye sunulmaz.

## 5. Kesinti ve temizlik

Numeric kayıt sırasında renderer yanıt vermedi; REA20sn ve sonra desteklenen30sn handshake denemeleri timeout/cleanup_incomplete döndürdü. Her seferinde close_binary ile kaynak temizliği tamamlandı. Native kontrol No dialog is showing ve AX timeout verdi. Yalnız araştırma sekmesi normal CDP close ile kapatılıp aynı saved düzen açıldı; BTC/1D, özgün4 çizim ve BB geri geldi. Hidden numeric capture başarısız kaldı; yeni aynı deney tekrarlanmadı.

Daha sonra platform Session disconnected / başka browser-device oturumu bildirdi (`ev_abf411a00c3cb5efe811612a582906326f80eb3453086c2a2858dd6240053676`). Connect'e basılmadı. Bu, kontrollü ağ blackout/reconnect/catchup deneyi değildir; bildirim kapatılarak normal cleanup tamamlandı.

Final `ev_220421aff08e4fa41e89c1e2336ec0b73a8663744b2c0b81287f89a69647c770`: seçilmiş geçici RSI Delete ile kaldırıldı, Undo remove RSI kaydı göründü; BTCUSDT.P/1D/UTC, Volume+BB20, özgün Fib/Short/iki Long mevcut ve globally hidden; All changes saved. BB ayarları değiştirilmedi. Table view kapalı; kalıcı RSI kalmadı. Veri oturumunun kesintisiz güncelliği kabul edilmedi.

Sıradaki geniş tur bağlantı/toparlanma kanıtı ve performans/tasarım baseline; seed/NA/zero-volume erişilemeyen kısımlar açık risk ve deterministik ürün kabulüne taşınır. Bu tur araştırma gate'ini veya ürün5/21 durumunu tamamlamaz.
