# Sembol çeşitliliği ve geniş senaryo ölçümü

15 Kasım 2026, yeni herkese açık metadata ve fiyat snapshotlarıyla ölçüldü. Hesap anahtarı okunmadı, borsaya emir veya ayar değişikliği gönderilmedi.

## Canlı okuma kapsamı

| Ürün / ortam | Kaynakta toplam | TRADING kayıt | Çeşitlilik |
|---|---:|---:|---|
| USD-M Demo | 744 | 604 | 570 perpetual, 30 TradFi perpetual ve 4 teslimli kontrat |
| Spot gerçek ortam metadata | 3742 | 1372 | 26 quote varlık sınıfı, 794 Margin-uygun sembol |
| COIN-M gerçek ortam metadata | 30 | 30 | 20 perpetual ve 10 çeyreklik kontrat |
| Options gerçek ortam metadata | 1758 | 1714 | 857 CALL, 857 PUT, 6 underlying, 11 vade |

TRADING sembol kaydı farklı varlık sayısı değildir. Aynı varlığın farklı parite ve vadesi ayrı semboldür. Metadata okuması hesap uygunluğunu veya emir kabulünü kanıtlamaz. TradFi kayıtları geniş API metadata gözlemidir, kullanıcının kripto işlem kapsamına otomatik eklenmedi.

Kaynak URL, HTTP sonuçları ve gözlem zamanları `public-observations.json`, ham snapshotlar `official-snapshots`, sayımlar `product-symbol-surface-audit.json` içinde.

## 528 USDT perpetual üzerinde ölçüm

Yeni Demo snapshotında da aktif USDT PERPETUAL sayısı 528. Bunların 527'sinde 62'şer yerel validator senaryosu çalıştı. Toplam 32674 vaka:

- 30039 vaka beklenen referans davranışıyla uyumlu.
- 2635 vaka referans yeteneğin mevcut validator tarafından reddedildiğini gösteriyor.
- 44 farklı tick/lot/emir türü sınıfı temsil edildi.
- SXPUSDT fiyatı 0.00006630, metadata minimum fiyatı 0.0001. Bu sembolün 62 vakası çalıştırılmadı. Hem önceki hem taze snapshotta uyuşmazlık var. Fiyat yapay olarak değiştirilip başarılı test yazılmadı.

2635 sonuç beş tekrar eden yetenek açığıdır: callback 7.5, 10 ve 20, yanıt tipi ACK ve RESULT. Her biri 527 sembolde görüldü. Bunlar 2635 bağımsız yazılım hatası değildir.

## Kombinasyon kapsamı

62 vaka temel long/short market/limit, hedge açılış ve azaltma yönleri, tek yön reduce-only, stop/trailing, GTC/IOC/FOK/GTX/GTD, sekiz priceMatch seçeneğinin iki yönü, dört STP seçeneği, callback sınırları, ACK/RESULT ve geçersiz adım/sayı/alan kombinasyonlarını içerir. Beklenen kabul değerleri araştırma kaynağına veya mevcut yerel sözleşmeye bağlı olarak ayrı etiketlendi.

Bu seçim bütün olası parametrelerin Kartezyen çarpımı değildir. Hesap bakiyesi, izin, rate limit, order count, likidite, hesap modu değişikliği ve gerçek dolum sonuçları için bu çevrimdışı ölçüm yeterli değildir. Bu koşulların senaryoları hata/toparlanma raporuna bağlıdır.

## Ek fiyat ve tetik sınırı deneyi

527 sembolde iki ek deney yapıldı. Toplam 1054 yerel teklif:

1. Kaydedilen PERCENT_PRICE üst bandının dışında fakat PRICE_FILTER aralığında bir LIMIT fiyatı validator tarafından kabul edildi.
2. MARK_PRICE kullanan BUY STOP_MARKET tetik fiyatı güncel markın altında verildiğinde validator teklif üretti.

Bu deneyler validator katmanında dinamik fiyat bandı ve zaten tetiklenmiş stop durumuna ilişkin yerel kontrol açığı gösterir. Sonraki preflight/risk kapılarını atlayıp borsaya emir gönderildiği iddia edilmez. Borsa ret ve tetik sonucu ayrıca yürütme kabulüdür. `filter-boundary-audit.json` tüm girdileri içerir.

## Ürün kapısı ölçümü

Dört üründeki 3720 aktif sembol normal V2 plan şemasına verildi. 541 USD-M sembolü şema aşamasını geçti. 63 USD-M, 1372 Spot, 30 COIN-M ve 1714 Options sembolü reddedildi. Bu sonuç 541 kullanılabilir işlem demek değildir. Sonraki USD-M preflight quoteAsset=USDT ve contractType=PERPETUAL koşullarını da denetliyor. 528 sayısı bu daha dar sembol sınıfına aittir.

## Geliştirmeyi etkileyen filtre sınıfları

USD-M snapshotında PERCENT_PRICE bütün 604 aktif sembolde, POSITION_RISK_CONTROL 526 sembolde görüldü. Spotta NOTIONAL, PERCENT_PRICE_BY_SIDE, TRAILING_DELTA, order lists/amend count ve sıfır MARKET_LOT_SIZE adımı gibi durumlar bulunuyor. COIN-M contractSize ve coin teminat, Options expiry/strike/unit ayrı sınıflardır. USD-M validatorun MIN_NOTIONAL ve doğrusal miktar modeli diğer ürünler için yeterli değildir.

## Yeniden üretim

`python scripts/research/audit_extended_symbol_scenarios.py --fresh`, `python scripts/research/audit_filter_boundaries.py`, `python scripts/research/audit_product_surface.py` komutları kaydedilmiş herkese açık snapshotlar üzerinde çalışır. API anahtarına ihtiyaç duymaz. Taze veri alınması ayrı, salt okuma adımıdır.

Kaynaklar: [USD-M exchangeInfo](https://demo-fapi.binance.com/fapi/v1/exchangeInfo), [Spot exchangeInfo](https://api.binance.com/api/v3/exchangeInfo), [COIN-M exchangeInfo](https://dapi.binance.com/dapi/v1/exchangeInfo), [Options exchangeInfo](https://eapi.binance.com/eapi/v1/exchangeInfo), [USD-M emir kuralları](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade).
