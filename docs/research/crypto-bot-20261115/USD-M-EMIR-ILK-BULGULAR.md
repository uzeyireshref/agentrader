# USD-M emir araştırması — ilk bulgular

15 Kasım 2026. Araştırma sürüyor. Bu kayıt resmi işlem belgesi, mevcut kod ve yerel testlerle sınırlıdır.

| Talimat | Resmi kaynak ve mevcut durum | Sonraki doğrulama |
|---|---|---|
| IOC/FOK/GTX/GTD limit girişi | order_rules doğruluyor, v2_preflight.py:252 girişte GTC kuruyor. | Normal plan sözleşmesinden seçim ve tüm yürütme zinciri incelenmeli. |
| Takip emri callback 7.5–20 | Resmi algo şemasında 0.1–20 aralığı var. order_rules.py:97 üst sınırı 5. | Demo ürün ve hesap kabulü doğrulanmalı. |
| ACK veya RESULT yanıt türü | Yerel doğrulayıcı alanı reddediyor. | Normal ve algo endpoint farkı ve sonuç yönetimi araştırılmalı. |
| Toplu limit oluşturma | batch_create.py:67 LIMIT/GTC ve pozitif fiyatla sınırlıyor. | Diğer belgeli kombinasyonlar ve kısmi sonuçlar incelenmeli. |
| Toplu değiştirme | Resmi endpoint en fazla 5 emir listeliyor. orders komutu mevcut oturum için prepare/apply akışı sunuyor. | Alan, kısmi dolum ve karışık sonuçların gerçek komut kanıtı çıkarılmalı. |
| Tek pozisyon artırma veya ters yön | plan_v2.py SINGLE için scale-in ve reverse değerlerini reddediyor. | Kullanıcı talimatı ve güvenli sonuç akışı tasarlanmalı. |

Koşullu emirlerin resmi yolu STOP, STOP_MARKET, TAKE_PROFIT, TAKE_PROFIT_MARKET ve TRAILING_STOP_MARKET türlerini listeliyor. [Binance USD-M işlem belgeleri](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade)

Yerel denetim 95 kayıt için 39 izinli adaptör yöntemi/yolu, ayrı istemcide 1 adres ve taranan kaynakta bulunmayan 55 adres saptadı. Bu değerler uçtan uca işlem desteği sayısı değildir. 12 order_rules regresyonu geçti. Borsa üzerinde yeni kabul testi yapılmadı. [Denetim kaydı](../../../reports/crypto-bot-research-20261115/exchange-operation-audit.json)
