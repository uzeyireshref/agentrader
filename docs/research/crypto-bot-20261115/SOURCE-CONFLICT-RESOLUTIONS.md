# Kaynak çelişkilerinin sonuçları

15 Kasım 2026. Eski açık kayıtlarını yeniden sınıflandıran 5–8 turu. Kapama, kanıtlanan bölüm için yapılır. Kalan dış kabul davranışı ayrıca korunur.

| Kimlik | Yeni kanıt / sonuç | Araştırma kararı |
|---|---|---|
| Q-CM-01 | Resmi entegrasyon duyurusu üç yeni DAPI algo işlemi bildiriyor. CLI kaynak kodu eski normal stop seçeneklerini gösterirken -4120 notu da içeriyor. CCXT ek sorgu/iptal yolları uyguluyor | Üç resmi işlem başlangıç 555 envanterine ek liste olarak alındı. CM algo callback ve bütün alanlar için tam resmi şema yok. Uygulama kapısı açık |
| Q-OPT-01 | Resmi schemas sayfası B/P/G/o iç nesnelerini hâlâ ayrıntısız gösteriyor, listenKeyExpired.E string | Zarfın bilinen alanları kaynakla doğrulandı. Tam olay muhasebesi için model/hesap payload kabulü gerekli |
| Q-PM-01 | PM ve Pro general-info farklı host/yapı, Pro/SPAN ayrı sorgu sürümü. PM ping 200 | Ürün/ortam ayrımı karara bağlandı. Gerçek risk/hesap şeması uygunluğu dış kabul kapısı |
| Q-WAL-01 | Eski questionnaire-requirements bağlantısı üzerinden güncel Travel Rule sayfasına erişildi | Önceki belge erişim sorunu giderildi. countryCode, ülke listesi, PII ve accepted/trId ayrımı incelendi. Hesaba özgü gereksinim gelecekte imzalı sorguyla seçilecek |
| Q-WAL-02 | Güncel Wallet asset sayfası fromSymbol/toSymbol alanlarında hâlâ transfer türü enumları gösteriyor. Altındaki notlar bunları yön koşulu olarak açıklıyor | Alan değerini transfer enumundan türetmeme kararı verildi. Gerçek symbol örneği/yanıt kabulü açık |
| Q-DATA-01 | Yeni Demo ortam snapshotı önceki sembol kapsamını koruyor. Son taze mark/filtre çiftinde SXP uyuşmazlığı sürüyor | 62 ölçüm veri koşulu nedeniyle bloklu olarak kapatıldı. Başarılı yürütme sayısına eklenmedi |
| Q-ENV-01 | USD-M Demo, CM Demo, Spot Testnet public metadata ve PM ping doğrulandı | Public erişim sorusu bu kapsamda çözüldü. Private hesap kabulü hâlâ NOT_RUN |
| Q-ENV-02 | Options belgesinin Demo hostu üzerinde /eapi/v1/exchangeInfo 403 | Hata nedenini ürünün desteklenmediği şeklinde yorumlama. Host/ürün/hesap kabulü ayrı kapı |

## Envantere eklenen resmi CM işlemleri

- ADD-CM-001: POST /dapi/v1/algoOrder.
- ADD-CM-002: GET /dapi/v1/openAlgoOrders.
- ADD-CM-003: DELETE /dapi/v1/algoOrder.

Bu üç işlem başlangıç 555 kaydında yok. Böylece araştırma envanteri **555 başlangıç + 3 resmi ek = 558 kayıt** içeriyor. Üç ekte bütün alanların kesinleştiği iddia edilmez. Duyurunun bildirdiği kimlik ve emir ailesi bilgisi kaydedildi.

CCXT kaynak kodunda ayrıca GET /dapi/v1/algoOrder, GET /dapi/v1/allAlgoOrders ve DELETE /dapi/v1/algoOpenOrders görülüyor. Bunlar resmi üç ekle aynı kanıt düzeyinde sayılmadı. Ayrı üç uygulama adayıdır. CCXT'nin kaynak yorumu borsadaki kişisel kabul kanıtı değildir.

## Travel Rule için netleşen davranış

Gereksinim sorgusu anahtara bağlı questionnaireCountryCode döndürüyor. Güncel ülke listesi allowed/blocked ve deposit/withdrawal uygunluğunu ayrıca bildiriyor. Broker çekim yanıtındaki accepted ve trId, tamamlanmış zincir çekimi anlamına gelmez. PII alanları kuruluş/kişi türüne bağlıdır ve günlüklerde ham saklanmamalı. Örnek yanıtta null bulunması zorunlu alanın boş gönderilebileceği anlamına gelmez.

## Öncelik sırası

Yürürlük tarihi belli resmi duyuru ile eski enum çelişiyorsa eski enum güncel destek kanıtı yapılmaz. SDK/Postman uyumu ortak şema üretiminden kaynaklanabilir. Üçüncü taraf kaynak gerçek bir uygulama örneğidir, resmi sözleşme veya bu hesapta kabul kanıtı değildir. Çözülemeyen alanlar açıkça ürün kabul kapısına bağlanır.

Kaynaklar: [CM/UM duyurusu](https://developers.binance.com/en/docs/products/derivatives-trading-coin-futures/Important-CM-UM-Integration-Notice), [Options şemaları](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-options/api/ws-streams/~schemas), [Travel Rule erişim yolu](https://developers.binance.com/docs/wallet/travel-rule/questionnaire-requirements), [Wallet asset](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/asset), sürümlü CLI/CCXT dosyaları repository-assessment.json içinde.
