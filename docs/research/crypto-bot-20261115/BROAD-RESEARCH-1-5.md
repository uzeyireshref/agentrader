# 1–5 geniş araştırma turu teslimi

15 Kasım 2026. Kullanıcının talebi üzerine ürün incelemesi, işlem kuralları, bot karşılaştırması, hata/toparlanma ve sembol senaryoları aynı turda ele alındı. Üretim kodu geliştirmesine geçilmedi. Bu teslim sabitlenmiş başlangıç kapsamı ve aşağıda açıkça belirtilen kanıt sınırları içindir.

## Beş başlığın teslimi

| Adım | Yapılan çalışma | Dosya |
|---|---|---|
| 1. Ürün incelemeleri | 10 koleksiyondaki 555 REST işlemi, 83 WS API komutu ve ürün davranış kararları | [Ürün kararları](PRODUCT-CONTRACT-DECISIONS.md), [sözleşme karşılaştırması](DETAILED-CONTRACT-COMPARISON.md) |
| 2. İşlem kuralları | Parametre türü/zorunluluğu, SDK kontrolleri, kaynak koşulları, yanıt tipleri, 2010 model/enum sınıfı, yaşam döngüsü gereksinimleri | [İşlem sözleşmeleri](detailed-operation-contracts.json), [yanıt modelleri](official-response-models.json), [yaşam döngüleri](operation-lifecycle-requirements.json) |
| 3. Bot karşılaştırması | Her REST kaydı için ürün/yol durumu, kaynak satırları ve 43 kullanıcı talimatı ailesinin erişilebilir komut analizi | [Talimat matrisi](WORKFLOW-CAPABILITY-REVIEW.md), [555 işlem denetimi](operation-support-audit.json) |
| 4. Hata/toparlanma | Belirsiz gönderim, kısmi dolum, iptal/amend yarışı, batch, restart, WS ve ortak hesap etkileri | [Hata ve toparlanma](FAILURE-RECOVERY-REVIEW.md) |
| 5. Coin/sembol kapsamı | Dört ürünün public metadata okuması, 3720 plan şeması deneyi, 527 sembolde 32674 validator vakası ve 1054 ek sınır deneyi | [Sembol kapsamı](SYMBOL-SCENARIO-COVERAGE.md) |

## Ölçülen sonuçlar

- Başlangıçtaki 555 REST kaydı resmi SDK'da yöntem/yol ve parametre isimleriyle eşleşti. SDK ve Postman aynı şema ailesini paylaşabileceğinden bağımsız borsa kanıtı sayılmadı.
- Botun 39 adaptör yolu mevcut. 1 yol başka istemcide bulunuyor. 515 kayıtta ürün veya yol desteği bulunamadı. 39 yolun tamamına genel kullanıcı komutu desteği atanmıyor.
- 1262 mevcut test 180.841 saniyede geçti. Katalogdaki 64 bağlı tanık ayrıca geçti. Bunlar birbirinden bağımsız ek 64 özellik olarak toplanamaz.
- 528 aktif USDT perpetual sembolden 527'sinde 62'şer vaka çalıştı. 30039 sonuç referansla uyumlu, 2635 sonuç beş tekrar eden parametre açığını gösteriyor.
- SXPUSDT tutarsız fiyat/filtre verisi nedeniyle ayrı tutuldu. Bu sembol için 62 senaryo çalıştırılmadı.
- Yeni 1054 sınır deneyinde validator, kaydedilen dinamik fiyat bandı dışındaki LIMIT'i ve zaten tetiklenmiş BUY STOP örneğini teklif olarak kabul etti. Sonraki yürütme kapılarının bu emirleri gönderdiği iddia edilmiyor.

## Geliştirmeyi doğrudan etkileyen bulgular

1. Mevcut normal ürün girişi demo USD-M/USDT perpetual ile sınırlı.
2. Spot, Margin, COIN-M, Options, PM/Pro, Convert, Wallet ve Sub Account için ayrı ürün akışı ve muhasebe gerekiyor.
3. IOC/FOK/GTX/GTD, priceMatch ve STP validator düzeyinde mevcut olsa da standart plan bunların genel seçimini sunmuyor.
4. newOrderRespType ACK/RESULT validator tarafından reddediliyor.
5. Trailing callbackRate 7.5/10/20 mevcut yerel sınırın dışında kalıyor.
6. SINGLE için keyfi scale-in, re-entry ve reverse genel talimat desteği yok.
7. Hesap/genel normal-algo iptali ve countdown cancel yollarında eksik var.
8. Native batch oluşturma LIMIT/GTC akışına bağlı.
9. Sabit 125 kaldıraç sınırı hesap/sembol bracket modeline bağlanmalı.
10. Dinamik fiyat bantları, ek sembol risk filtreleri ve zaten tetiklenmiş emir durumları genişletilmeli.
11. UM/CM ortak position mode ve limit bütçesi ürünler arası yönetilmeli.
12. Yeni ürünlerin liste/child, borç, transfer, coin PnL ve prim/uzlaşma yaşam döngüleri mevcut USD-M journal'ına yalnız endpoint ekleyerek tamamlanamaz.

## Tamamlanma sınırı

Bu tur bütün başlangıç satırlarını kaynak sözleşmesi ve bot durumuyla ilişkilendiren geniş bir masa başı/yerel araştırma teslimidir. 555 canlı belge kaydının her alanı bağımsız olarak yeniden okunmuş veya her işlem borsada çalıştırılmış gibi raporlanmaz. Otomatik sözleşme çıkarımı, ürün yorumu, mevcut test ve canlı public metadata ayrı kanıt türleridir. Kaynakta net olmayan ayrıntılar [belirli açık kayıtları](BOUNDED-OPEN-QUESTIONS.md) içinde tutuldu.

Bu nedenle genel araştırma planının bütün kapanış kutuları işaretlenmedi. Özellikle CM algo sözleşmesi çelişkisi, bazı olay şemaları ve hesap uygunluğu kanıtlanmış destek sayılmıyor. Geliştirme başlamadan önce bu sınırlar nihai kapsam kararına bağlanmalı.

Sonraki araştırma başlıkları kullanıcının önceki listesinde 6: ortam farkları/belge çelişkileri, 7: GitHub/araç seçimi, 8: nihai eksik listesi/kapsam denetimidir. Geliştirme planı bunların ardından çıkarılacak.

## Kaynak ve yeniden üretim

Resmi Python SDK commit `6a75e7e5744904380ab0bfbd0bd3433b997010f5`, Postman commit `1856d66cecd544191a01d60cdfbd99900d310547`, Spot belge commit `e5f8489162e79fa1da6d0ea3ded3ce810b3637a0`. Kaynak indirme manifestleri, dosya hashleri, public sorgu zamanları ve kabul edilmemiş deneyler rapor dizinindedir.

Araştırma araçları `scripts/research/build_detailed_contracts.py`, `audit_product_surface.py`, `build_operation_lifecycles.py`, `audit_extended_symbol_scenarios.py`, `audit_filter_boundaries.py` dosyalarındadır. Üretim paketine üçüncü taraf SDK kurulmadı. Finansal mutasyon yapılmadı.
