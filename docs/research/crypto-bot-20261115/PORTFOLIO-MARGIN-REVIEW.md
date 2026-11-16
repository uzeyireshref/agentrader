# Portfolio Margin hesap ve işlem modeli incelemesi

15 Kasım 2026. Resmi koleksiyonlarda Classic için 102, Pro için 24 kayıt var. Bu tur hesap ve teminat modeli ile işlem yollarının ayrımını inceler.

| Model | Kaynakta görülen yapı | Bot gereksinimi |
|---|---|---|
| Portfolio Margin | papi/v1/account, balance ve UM/CM/Margin alt yolları | Hesap türü ve ürün ayağı istek kimliğinde saklanmalı |
| Portfolio Margin Pro | sapi/v1/portfolio/account, balance ve tiered collateral | Pro hesap risk snapshotı ve teminat basamakları ayrı modellenmeli |
| Pro SPAN | sapi/v2/portfolio/account | V1 yanıt şemasıyla örtük birleştirme yapılmamalı |
| Borç ve negatif bakiye | Faiz, otomatik dönüşüm, repay ve auto-repay switch | Ayar değişikliği ile gerçekleşen finansal hareket ayrı teyit edilmeli |
| Emirler | UM normal/algo, CM normal/conditional, Margin emir ve OCO | Kimlik ve sorgu yolu ürün bacağına bağlı olmalı |

Pro resmi kullanım açıklaması mevcut Cross Margin, USD-M ve COIN-M trading endpointlerinin kullanılabildiğini belirtiyor. Bu nedenle bütün Pro emirlerini papi yoluna zorlayan bir tasarım doğru olmaz. Normal/PM/Pro/SPAN hesap türü açık keşfedilmeli.

Mevcut portfolio.py, USD-M yerel risk değerlendiricisidir. Binance Portfolio Margin ürünü için birleşik teminat, borç, haircut ve hesap statüsü desteği sağlamaz. Mevcut plan_v2 yalnız demo/binance/USD-M kabul ediyor.

## Kabul senaryoları

- Aynı sembol adı farklı hesap türünde doğru adaptöre gider.
- Teminat iskonto basamağı değiştiğinde available ve adjusted equity yeniden değerlendirilir.
- UM ve CM pozisyonları aynı birleşik teminatı iki kez harcamaz.
- Negatif bakiye/otomatik dönüşüm sonrası yerel borç ve bakiye uzlaşır.
- Auto-repay ayarı değişikliği kaybolan yanıt sonrası tekrar sorgulanır.
- PM/Pro/SPAN yanıtları yanlış şema altında başarı sayılmaz.
- Hesap erişimi olmadığı durumda ürün uygunluğu hatası görünür olur.
- Bir ürün bacağının liquidation/close olayı diğer ayağın riskini yeniden hesaplatır.

## Açık kalanlar

126 işlemin alan alan resmi karşılaştırması, güncel uniMMR hesap durum eşikleri, tüm olay payloadları ve hesap/ortam erişimi henüz kapanmadı. Genel risk oranı formülü tek başına ürün desteğini kanıtlamaz.

Kaynaklar [resmi PM API](https://developers.binance.com/en/docs/catalog/advanced-trading-derivatives-trading-portfolio-margin/api/rest-api), [Pro API kullanımı](https://www.binance.com/en/support/faq/detail/1fc7ab7c087644f0b697b53af38a43cf), [teminat oranları](https://www.binance.com/en/support/faq/detail/39adee656e744a249c7e191148e3d7c6).

## Hesap durumları ve kullanılabilir tutar

Resmi account yanıtı NORMAL, MARGIN_CALL, SUPPLY_MARGIN, REDUCE_ONLY, ACTIVE_LIQUIDATION, FORCE_LIQUIDATION, BANKRUPTED durumlarını listeliyor. accountStatus işlem uygunluğunun parçası olmalı. virtualMaxWithdrawAmount USD birimindedir ve belirli varlığın çekilebilir miktarı gibi kullanılamaz. totalAvailableBalance/totalMarginOpenLoss örnek yanıtta boş metin olabildiğinden parser bunları geçerli sıfır olarak kabul etmemeli.

Resmi PM açıklamasında uniMMR 1.05–1.2 aralığında yeni girişin reddedildiği ve azaltıcı emir kabul edildiği, 1.05 ve altında tasfiye başladığı belirtiliyor. Bu eşikler PM ürününe ait tarihli kaynak bulgusudur. Pro/SPAN modeline otomatik taşınmamalı, hesap durumu ve güncel ürün kurallarıyla teyit edilmelidir.

Ek kabul senaryoları boş sayısal alan, USD transfer tavanını varlık miktarına dönüştürme, eşikte eşitlik, REDUCE_ONLY sırasında açılış reddi/azaltma devamı ve hesap durumunun istek öncesi değişmesidir.

[PM account](https://developers.binance.com/en/docs/catalog/advanced-trading-derivatives-trading-portfolio-margin/api/rest-api/account), [uniMMR açıklaması](https://www.binance.com/en/support/faq/detail/4868b2f1aa6c4d08af973328462bb0bd), [PM kullanıcı akışı](https://developers.binance.com/en/docs/products/derivatives-trading-portfolio-margin/user-data-streams).

## Emir kimliği ve olay yaşam döngüsü

UM normal emir, UM algo, CM normal emir, CM conditional ve Margin emirleri ayrı kimlik alanlarıyla izlenmeli. UM algo için algoId/clientAlgoId, CM conditional için strategyId/newClientStrategyId kullanılır. Aynı sayısal kimlik farklı ürün bacağında aynı işlem olarak eşleştirilemez.

Kaynak: [PM trade](https://developers.binance.com/en/docs/catalog/advanced-trading-derivatives-trading-portfolio-margin/api/rest-api/trade).

PM akışı listenKey yenilemesi ve bağlantı yenilemesini ayrı gerektirir. Anahtar 60 dakika, bağlantı 24 saat geçerlidir. -1125 sonrası anahtar yeniden oluşturulur. Hesap olayları değişen pozisyonları taşır, tam portföy görüntüsü sayılmaz. Kaynak: [PM kullanıcı akışı](https://developers.binance.com/en/docs/products/derivatives-trading-portfolio-margin/user-data-streams).

Tasarım kabul senaryoları:

- Kısmi hesap olayı, olayda yer almayan pozisyonu silmez.
- Funding olayı pozisyon verisi taşımadan bakiyeyi güncelleyebilir.
- Bağlantı ve anahtar yenilemesi sırasında kaçan olaylar snapshot ve geçmiş ile uzlaştırılır.
- Margin borç ve açık emir kaybı olayları birleşik hesap riskini yeniden değerlendirir.
- Gecikmiş risk olayı geldiğinde emir uygunluğu güncel hesap sorgusuyla belirlenir.
- Tetiklenen koşullu emir için oluşan alt emir ayrı sorgulanır ve gerçekleşen miktarla uzlaştırılır.

Bu bölüm olay yaşam döngüsü tasarımını ilerletir. 126 işlemin tamamının alan incelemesi ve hesap üzerinde kabulü halen açık durumdadır.
