# Ortam farkları ve hesap uygunluğu araştırması

15 Kasım 2026. Yalnız public GET gözlemleri yapıldı. Özel hesap, anahtar, işlem veya finansal mutasyon denemesi yapılmadı. Makine tarafından okunabilir sonuç `environment-capability-matrix.json`, gözlem zamanları `reports/crypto-bot-research-20261115/environment-review/public-probes.json` içinde.

## Ürün/ortam matrisi

| Ürün | Gerçek ortam | Test/Demo bulgusu | Sonuç |
|---|---|---|---|
| USD-M | fapi.binance.com | demo-fapi.binance.com belgelenmiş, exchangeInfo 200 | Public erişim doğrulandı. Her endpoint ve hesap kabulü ayrı |
| Spot | api.binance.com | testnet.binance.vision belgelenmiş, exchangeInfo 200 | Testnet yalnız /api. Ürün/filtre eşitliği varsayılmaz |
| COIN-M | dapi.binance.com | demo-dapi.binance.com belgelenmiş, exchangeInfo 200 | Public erişim doğrulandı. CM algo sözleşmesi ayrı sınır |
| Options | eapi.binance.com | Resmi general-info Demo host olarak demo-fapi gösteriyor. /eapi/v1/exchangeInfo burada 403 | Doküman hostu tek başına çalışır ortam kanıtı değil. Hatanın nedeni belirlenmedi |
| Margin | api.binance.com /sapi | Spot Testnet /sapi desteklemiyor | Ayrı doğrulanmış test ortamı yok |
| PM | papi.binance.com | Gerçek ortam public ping 200. İncelenen general-info test ortamı vermiyor | PM hesap uygunluğu doğrulanmadı |
| PM Pro/SPAN | api.binance.com /sapi | İncelenen general-info test ortamı vermiyor | Pro ve SPAN ayrı hesap kabulü gerektirir |
| Convert | api.binance.com /sapi | Spot Testnet /sapi desteklemiyor | USD-M /fapi Convert ayrı işlem ailesidir |
| Wallet | api.binance.com /sapi | Doğrulanmış ayrı test ortamı yok | İzin, ağ, kuruluş ve hesap uygunluğu gerekir |
| Sub Account | api.binance.com /sapi | Doğrulanmış ayrı test ortamı yok | Master/sub/managed/VIP koşulları işlem bazında |

Belgelerde bir ortamın bulunmaması o ortamın kesinlikle olmadığı anlamına gelmez. Yukarıdaki durumlar incelenen kaynak ve gözlemle sınırlıdır. Aynı hesabın ürün erişimi, API anahtarının izni ve ağ erişimi üç ayrı koşuldur.

## Gerçek metadata farkları

Karşılaştırmada sırasız listeler ve aynı sayının farklı ondalık yazımı normalize edildi. Toplamlar bütün metadata kayıtlarıdır, yalnız TRADING sayısı değildir.

| Ürün | Gerçek toplam | Test/Demo toplam | Ortak sembol | Metadata farkı olan ortak sembol |
|---|---:|---:|---:|---:|
| USD-M | 946 | 744 | 707 | 705 |
| Spot | 3742 | 1373 | 1371 | 1371 |
| COIN-M | 30 | 51 | 30 | 30 |

USD-M ortak sembollerde 695 filtre, 615 permissionSets, 137 status ve 1 contractType farkı görüldü. Spotta 1364 filtre ve bütün ortak sembollerde izin/STP listesi farkı var. COIN-M ortak 30 sembolün filtreleri farklı. Bu farklar test verisinin gerçek ortam işlem kuralları yerine kullanılamayacağını gösteriyor. Likidite veya dolum benzerliği ölçülmedi.

## Bota etkisi

Mevcut Config yalnız demo kabul eder ve DemoExchange adresi sabittir. Genel prod desteği için sadece URL değişikliği yeterli değildir. Ortam, ürün, hesap, anahtar izinleri, metadata cache, journal kimliği ve geçmiş kayıtları aynı kapsamda seçilmeli. Demo komutu prod anahtarıyla veya prod metadata Demo rezervleriyle örtük birleştirilmemeli.

Spot Testnet periyodik olarak sıfırlanır. Silinen borsa geçmişi normal iptal/ret kanıtı sayılmamalı. Ortam nesli/reset bilgisiyle yerel journal uyuşmazlığı görünür olmalı. Testnet'teki /api başarısından /sapi Wallet/Margin/Convert kabulü türetilemez.

## Hesap kabul kapıları

- Her ürün için imzalı okuma ile hesap türü ve izinleri keşfetme.
- İşlem öncesi gerekli margin/position/multi-assets/VIP ve bölgesel ürün koşullarını değerlendirme.
- Normal komuttan tek başarı/ret, kaybolan yanıt, tekrar, restart ve uzlaştırma kabulü.
- Yalnız desteklendiği kanıtlanan ortamda finansal mutasyon deneyi. Genel araştırma yetkisi işlem yürütme yetkisi değildir.

Kaynaklar: [USD-M general info](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info), [CM general info](https://developers.binance.com/en/docs/products/derivatives-trading-coin-futures/general-info), [Options general info](https://developers.binance.com/en/docs/products/derivatives-trading-options/general-info), [Spot Test Network](https://testnet.binance.vision/), [PM general info](https://developers.binance.com/en/docs/products/derivatives-trading-portfolio-margin/general-info), [Pro general info](https://developers.binance.com/en/docs/products/derivatives-trading-portfolio-margin-pro/general-info).
