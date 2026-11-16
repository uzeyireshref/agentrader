# G11 — Gerçek Demo akışında bot stratejisi

`DrawingStrategy`, üretim `ChartBot` adaptörü üzerinden çalışan, emir yetkisi olmayan küçük ve deterministik bir çizim stratejisidir. `closed-ema20-horizontal/1`, her yeni kapalı mumda EMA20'nin kapanış bazlı değerini HTTP gösterge sorgusundan alır. İlk kararda yatay çizgi oluşturur; sonraki mumlarda aynı bot çizgisini günceller. Bu çizgi bir alım/satım sinyali veya kârlılık iddiası değildir.

Strateji yalnız doğrulanmış, FRESH, READY ve kapalı mumları kullanan bağlamdan karar seçer. EMA yapılandırması close/20/EMA_SMA_SEED/hesap sürümü 1 olarak sabittir; değişirse yeni karar reddedilir. Göstergenin görsel açık/kapalı durumu hesap erişiminin koşulu değildir. Çizim fiyatı, HTTP hesap sonucunun decimal temsiline sabitlenir; sonraki geometri hesabı bu fiyatla tam kesir olarak karşılaştırılır. EMA'nın kendisi FLOAT64 hesap temelini korur.

## Kararın kanıtı ve tekrar güvenliği

Her karar; kapalı mum zamanı, kaynak context_id, veri hazırlığı/proof, tüketilen veri hash'i, gösterge girdi hash'i ve gösterge cevabını kaydeder. Çizimin bağlı notunda neden, kaynak kimlikleri ve seçilen fiyat bulunur. `priceAt` HTTP sorgusu çizilen fiyatı tekrar doğrular.

Karar niyeti HTTP yazımından önce ayrı JSON durum dosyasına atomik değiştirme ve fsync ile kaydedilir. Üretim adaptörünün ayrı SQLite günlüğü gerçek HTTP isteklerini tekilleştirir. İşlem anahtarları strateji sürümü, sembol, zaman dilimi ve kapalı mum zamanını içerir. Kaybolan yanıt sonrası aynı niyet aynı anahtarla sürdürülür. Aynı durum dosyası için işletim sistemi kilidi paralel yürütücüyü durdurur; dosya endpoint/aktör/çalışma alanı/pazar/sürüm kapsamına bağlanır.

Veri stale, eksik veya doğrulanmamışsa yeni karar seçilmez ve bekleyen karar için de yeni çizim/not yazımı yapılmaz. Her yazım öncesi veri hazırlığı tekrar okunur. Kaynak kontrolü ile çizim yazımı ayrı HTTP çağrılarıdır; atomik bir piyasa-yazım işlemi iddia edilmez. Bekleyen niyet, canlı veri geri geldiğinde kayıtlı kaynak kararı olarak sürdürülür. Eski bir mum için daha sonra yeni fiyat seçilmez. Bağlamın sorgu sırasında değişmesi HTTP sözleşmesinin reddiyle sonuçlanır ve sonraki çevrim tekrar dener.

## Çalıştırma

Mevcut yerel grafik sunucusunda ayrı bot kimliği ve çalışma alanı gerekir. Binance hesap anahtarı gerekmez. Bot erişim anahtarı `AGENTRADER_CHART_BOT_TOKEN` ortam değişkeninden alınır; komuta, günlüğe veya rapora yazılmaz.

```powershell
python -m agentrader chart-bot --url http://127.0.0.1:8765 --bot-id chart-bot --strategy-id closed-ema20 --workspace strategy-demo --journal data/strategy-adapter.sqlite3 strategy-watch --state data/strategy-state.json --symbol BTCUSDT --interval 1m --seconds 180 --trace reports/strategy-http.jsonl
```

Sunucuda ilgili pazar için gerçek aktif veri aboneliği bulunmalıdır. Salt okunur bağlam uç noktası kendiliğinden abonelik açmaz. Süre 1–600 saniye, sorgulama aralığı 0,5–10 saniyeyle sınırlıdır. Sonuçlar JSONL'dir: APPLIED, NO_CHANGE, PAUSED veya sabit hata koduyla REJECTED/PENDING. İz kaydı gerçek HTTP yöntem/yol/gövde ve yanıt hash'lerini içerir; erişim başlıklarını içermez. Bu dosyalar strateji notlarını içerdiğinden çalışma alanına ait yerel kayıtlar olarak tutulmalıdır.

## Gerçek kabul

`scripts/integration/observe_g11_chart_strategy.py`, anahtarsız gerçek Binance Demo REST ve WebSocket akışını, üretim MarketFeedHub/ChartMarket ile başlatır. Kullanıcının veritabanından ve sunucusundan ayrı bir çalışma alanı, port ve uygulama/piyasa/strateji depoları kullanır. Strateji ayrı `python -m agentrader chart-bot ... strategy-watch` sürecidir; test istemcisinin sentetik çizimleri canlı strateji yerine sayılmaz.

Gözlem önce doğrulanmış salt okunur bağlamı kaydeder. Manuel geometri ve not sentinel'i yanında bot iki farklı kapalı mumda aynı çizgiyi oluşturur/günceller. Gerçek abonelik kontrollü olarak kaldırıldığında stratejinin durduğu doğrulanır. Sunucu ve veri akışı yeniden açılır; aynı kapalı mum ikinci nesne oluşturmaz. Ayrı strateji süreci yeniden başlatılıp sonraki kapalı mumda aynı nesneyle devam eder. Manuel geometri, köken, revizyon ve not birebir korunur.

Sentetik kayıp yanıt ve stale ara aşama testleri gerçek HTTP fixture'ında ayrıca çalışır. Gerçek gözlemde sentetik mum, paket veya FRESH durumu enjekte edilmez. Kontrollü abonelik kesintisi gerçek borsa kesintisi gözlemi değildir. Emir gönderimi, hesap erişimi ve fiziksel UI kabulü bu gözlemin kapsamına girmez. Yeni migration yoktur; mevcut sürüm 13 korunur.

Nihai kanıt: [G11 raporu](../../reports/chart-interface-g11-20261115/README.md). Son kaynaklarla yapılan kabul `live-current/` altındadır; önceki keşif gözlemi nihai kabul yerine kullanılmaz.
