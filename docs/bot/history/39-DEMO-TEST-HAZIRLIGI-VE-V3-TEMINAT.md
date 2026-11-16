# Demo test hazırlığı ve V3 teminat doğrulaması — 14 Kasım 2026

Önceki geçmiş uzlaştırması başarılıdır. Bu adımda gerçek Binance bağlantısı açılmadı. Demo hesap salt okunur kontrol edildi; yeni emir, plan onayı, hesap ayarı değişikliği veya durdurma kaldırma yapılmadı.

## Bulgu ve düzeltme

V3 account yanıtının USDT varlığında marginAvailable alanı yoktur. Uygunluk, alan hesapta bulunmadığında exchangeInfo varlık metadatasından doğrulanır. Hesapta açık bir ret varsa diğer kaynak bunu geçersiz kılamaz; eksik veya çelişkili kanıt engellenir.

Multi Assets kullanılabilir bakiye diğer teminatları da içerebildiği için yalnız doğrulanmış USDT kapasitesi kullanılır: walletBalance + min(unrealizedProfit, 0) - initialMargin. Sonuç ayrıca varlığın availableBalance değeri ve endeksle muhafazakâr çevrilmiş genel tavanla sınırlıdır. Pozitif gerçekleşmemiş kâr kapasiteyi büyütmez. Grid ve neutral risk yenilemeleri de aynı sözleşmeyi kullanır.

Salt okunur hesap adaptörleri senkronize sunucu saat farkını korur. Günlük gerçekleşmiş zarar penceresi ve UTC gün geçişi bu saatle hesaplanır.

Resmî sözleşmeler: [Account Information V3](https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Account-Information-V3), [Exchange Information](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information), [Multi Assets Mode Asset Index](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Multi-Assets-Mode-Asset-Index).

## Hazırlık komutu ve güncel sonuç

`python -m agentrader service prepare-demo-test --symbol BTCUSDT --direction LONG`

Yön açıkça verilmelidir. Bu komut emir göndermez, onay vermez veya durdurmayı kaldırmaz. Hesap, veri kabulü, yerel geçmiş ve risk koşullarını denetleyip teknik giriş parametreleri taslağı üretir. Doğrudan yürütülebilir v2 plan dışa aktarmaz; grafik gölge olayı → açık önizleme parametreleri → hesap incelemesi → plana özel onay → bağımsız izleyici zinciri korunur.

14 Kasım gözleminde hesap pozisyonsuz ve emirsiz, 20 yerel emir kaydının tümü son durumdadır. Doğrulanmış USDT teminatı 4445,47513045 USDT. Günlük gerçekleşmiş Demo zararı 529,69467203 USDT, profil sınırı 25 USDT olduğundan sonuç BLOCKED / DAILY_LOSS_LIMIT_EXCEEDED. Eski pozisyon kapatmalarının zararı risk hesabından çıkarılmadı; sınır yükseltilmedi.

BTCUSDT için 54,93 USDT bütçeli LIMIT bekleme/iptal teknik taslağı üretildi. Bu bir işlem önerisi veya kullanıcı onayı değildir. GTC limit emir dolabilir; dolmayacağı varsayılmaz. Risk engeli nedeniyle yürütme miktarı hesaplanmadı. Fiyatlar eskir; ileride taze veri ve yeni ön kontrol gerekir.

Sonraki UTC gün penceresi 15 Kasım 2026 00:00 UTC, Bakü saatiyle 04:00'te başlar. Bu saat otomatik izin veya çalıştırma anlamına gelmez. Günlük zarar, hesap, veri kaynağı, risk ve izleyici yeniden doğrulanmadan giriş durdurması kaldırılmamalıdır. Ayrı izleyici çalışmıyor; özel web API kapalıdır.

## Doğrulama ve kanıt

1136 Python testi ve 36/36 grafik replay senaryosu geçti. Yeni 12 test V3 teminat sözleşmesini, sunucu saatiyle UTC penceresini, iki yönlü taslakları, limit ihlallerini ve yetki üretmeme davranışını doğruladı. Arayüz bu adımda değiştirilmedi.

- `reports/demo-test-candidate-20261114.json`: gerçek salt okunur hazırlık sonucu.
- `reports/demo-preparation-fixed-snapshot-20261114.json`: düzeltilmiş hesap anlık görüntüsü.
- `reports/demo-test-preparation-python-tests-20261114.log`: tam Python regresyonu.
- `reports/demo-test-preparation-replay-20261114.log`: grafik tekrar doğrulaması.

Sıradaki emirli kabul, günlük risk engeli kalkıp yeni kontroller geçtikten ve somut plana özel kullanıcı onayı alındıktan sonra yapılabilir. Beklerken geliştirme ve çevrimdışı testler sürdürülebilir.
