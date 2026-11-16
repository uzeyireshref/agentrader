# Margin hesap, risk, transfer ve akış incelemesi

15 Kasım 2026. 69 kayıtlık Margin envanterinin temel emir/borç araştırmasına ek inceleme. Kaynak parametreleri cross-product-operation-catalog.json içinde OP-0339–OP-0407 kapsamındadır.

| Alan | Araştırma sonucu | Bot etkisi |
|---|---|---|
| Cross ve isolated hesap | Ayrı hesap sorguları, enable/disable ve hesap sınırı işlemleri var | USD-M pozisyon teminatından ayrı bakiye/borç modeli gerekir |
| Risk verisi | Collateral ratio, isolated tier, liability leverage bracket, restricted asset ve liquidation ratio sorguları var | Futures bakım marjı modelinin doğrudan yeniden kullanımı yeterli değil |
| Transfer | Margin başlığında maksimum transfer çıkışı ve geçmiş sorguları var | Yeni transfer oluşturma yolu Wallet/Universal Transfer ile ayrıca eşleştirilmeli |
| Akış | V1/V2 listen-key için başlatma, canlı tutma ve kapatma var | Sürüm ve hesap kapsamı üretim adaptöründe modellenmeli |
| Geçmiş | Capital-flow, faiz, borç, transfer ve dolum geçmişi ayrı | Tek transaction günlüğünde tür ve kimlik kaybı önlenmeli |

## Kabul senaryoları

- M-09 Cross hesap snapshotı — free, locked, borrowed ve interest alanlarını ayrı kaydet, borcu net bakiyeden türetme.
- M-10 Isolated hesap kapsamı — Base ve quote varlıkların borç ve bakiyesini doğru symbol altında tut.
- M-11 Teminat iskonto değişimi — Collateral oranı ve risk basamağı değiştiğinde kullanılabilir tutarı yeniden hesapla.
- M-12 Transfer ön kontrolü — maxTransferable değerini ve hedef hesabı güncel sorgula.
- M-13 Transfer yanıt kaybı — Hareket geçmişi ve bakiye etkisi doğrulanmadan ikinci transfer gönderme.
- M-14 Akış kesintisi — Emir, bakiye ve borç snapshotlarıyla yeniden uzlaştır.
- M-15 Akış sürümü — V1/V2 başlatma, keepalive ve kapatma kapsamını ayrı doğrula.
- M-16 Isolated açma kapatma — Önkoşulları sorgula, sonuç durumunu tekrar oku.
- M-17 Geçmiş sayfalama — Zaman ve ID sınırlarını koru, aynı kayıtları iki kez sayma.
- M-18 Delist ve restricted asset — Yeni işlem uygunluğunu güncel varlık ve sembol bilgisiyle doğrula.

## Kapanış durumu

Hesap/risk/transfer/akış ailelerinin kaynak ve uygulama etkisi incelemesi yapıldı. Bütün 69 endpoint için alan alan resmi sayfa karşılaştırması, WS olay payloadları ve ortam kabulü henüz kapanmadı. Margin paketi ayrıntılı araştırma bakımından kısmi durumdadır. Transfer oluşturma endpoint eşlemesi ve akış olay sözleşmesi sonraki açık maddelerdir.

Kaynaklar [Account](https://developers.binance.com/en/docs/catalog/core-trading-margin-trading/api/rest-api/account), [Transfer](https://developers.binance.com/en/docs/catalog/core-trading-margin-trading/api/rest-api/transfer) ve [User Data Stream](https://developers.binance.com/en/docs/catalog/core-trading-margin-trading/api/rest-api/user-data-stream).

## Transfer ve akış ek bulguları

Transfer oluşturma Wallet koleksiyonunda POST /sapi/v1/asset/transfer ile eşleşti. type, asset, amount ve imzalı zaman alanları var. Isolated yönlerinde fromSymbol/toSymbol koşulları resmi SDK ile doğrulanmalı. Koleksiyondaki örnek değerler doğrudan geçerli sembol varsayılmamalı. Alt hesap universalTransfer ayrı bir yöntem/yol ve hesap yetkisine sahiptir.

Margin WS şemaları userLiabilityChange, balanceUpdate ve executionReport olaylarını listeliyor. Borç değişimi ayrı bir olay ailesidir. Güncel changelog eski stream.binance.com listenKey yolunun kaldırılmasını kaydediyor. Bu nedenle yalnız REST koleksiyonundaki V1/V2 listen-key girdilerine dayanarak güncel WS bağlantısı tasarlamak yeterli olmaz. Güncel listen-token bağlantı sözleşmesi ve olay alanları açık araştırma maddesidir.

[Margin WS şemaları](https://developers.binance.com/en/docs/catalog/core-trading-margin-trading/api/ws-streams/~schemas), [Margin changelog](https://developers.binance.com/en/docs/products/margin-trading/change-log), [resmi Wallet SDK](https://github.com/binance/binance-connector-python/blob/master/clients/wallet/src/binance_sdk_wallet/rest_api/rest_api.py).

## Güncel listen-token sözleşmesi

POST /sapi/v1/userListenToken token oluşturur. isIsolated=true için symbol zorunludur. validity milisaniyedir ve en fazla 24 saattir. WS bağlantısı wss://ws-api.binance.com:443/ws-api/v3 üzerinden userDataStream.subscribe.listenToken yöntemiyle yapılır. Süre dolmadan yeni token alınıp aynı yöntemle abonelik uzatılır. Geçersiz token -1209 döndürür. Süre dolarsa eventStreamTerminated gelir. Bu davranış eski listen-key canlı tutma döngüsünden ayrıdır. Kaynak incelemesindeki bağlantı belirsizliği çözüldü, gerçek ortam ve olayların tüm alanlarına ilişkin kabul bekliyor.

[Resmi listen-token sözleşmesi](https://developers.binance.com/en/docs/products/margin-trading/listen-token-data-stream)
