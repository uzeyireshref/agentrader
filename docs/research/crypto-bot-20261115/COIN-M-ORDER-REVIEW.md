# COIN-M emir sözleşmesi incelemesi

15 Kasım 2026.

| Konu | Resmi sözleşme | Uygulama gereksinimi |
|---|---|---|
| Miktar | quantity kontrat sayısıdır | Base coin miktarı ile kontrat adedi ayrı tutulmalı |
| Pozisyon modu | BOTH veya hedge LONG/SHORT | Yön ve hedef bacak birlikte doğrulanmalı |
| Reduce-only | Hedge ve closePosition ile gönderilemez | Ürün ve hesap moduna bağlı doğrulama gerekir |
| Koşullu emir geçişi | CM migration sonrasında normal order stop türlerinde -4120 döndürür, algoOrder yolu gerekir | Sembol/hesap geçiş durumu ve güncel algo sözleşmesi incelenmeli |
| Amend | Geçiş sonrasında price ve quantity birlikte zorunlu | Tek alan değiştirme talimatı mevcut diğer alanı doğrulayarak tamamlanmalı |
| Kısmi dolum amend | Yeni toplam miktar executedQty değerinden küçük/eşitse emir iptal olabilir | Amend cevabı emir durumuyla teyit edilmeli |
| GTX amend | Yeni fiyat anlık eşleşecekse iptal olabilir | Ret ve iptal durumları farklı ele alınmalı |

Kabul senaryoları kontrat miktarı dönüşümü, hedge yanlış bacak reddi, kısmi dolumda amend iptali, GTX fiyat değişimi, migration -4120, kaybolan algo yanıtı ve terminal emir uzlaştırması olarak belirlendi. Bunlar henüz borsada yürütülmedi.

Mevcut bot planı USD-M/USDT ile sınırlı olduğundan COIN-M için normal üretim komutu bulunmuyor. Ayrıntılı algo, hesap ve uzlaşma incelemesi devam ediyor.

[Resmi COIN-M işlem belgeleri](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-coin-m-futures/api/rest-api/trade)

## Hesap ve kontrat verisi incelemesi

exchangeInfo contractSize, marginAsset, quoteAsset, contractType, deliveryDate ve contractStatus alanlarını sağlar. pricePrecision/quantityPrecision yerine tickSize/stepSize filtreleri kullanılmalıdır. Teslimli kontratta funding geçmişinin boş dönmesi belgelenmiştir. Funding periyodu ayrıca fundingInfo üzerinden alınmalıdır.

Mevcut risk.py kaybı abs(entry-stop)*quantity ve nominali entry*quantity ile hesaplıyor. Bu doğrusal model COIN-M kontrat adedi ve coin teminatına doğrudan uygulanamaz. Birim ve kontrat çarpanı yeni ürün sözleşmesinde zorunlu olmalıdır.

## Kaynak uyuşmazlıkları

COIN-M normal ve batch emir sayfaları migration sonrası stop türlerinin algoOrder yoluna taşındığını belirtiyor. Aynı sayfanın enum listeleri eski türleri hâlâ içeriyor. Batch callback alanında 4, tek emir açıklamasında 10 üst sınırı görülüyor. Bu alanlar hesap geçiş durumuna göre güncel algo sözleşmesi ve entegrasyon duyurusuyla çözümlenmeden tek ortak sınır olarak uygulanmamalı.

[COIN-M market data](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-coin-m-futures/api/rest-api/market-data), [hesap belgeleri](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-coin-m-futures/api/rest-api/account), [mimari geçiş duyurusu](https://developers.binance.com/en/docs/products/derivatives-trading-coin-futures/Important-CM-UM-Integration-Notice).

## Geçiş ve uzlaşma araştırmasının devamı

Mimari entegrasyon duyurusu genel geçişin 24–30 Haziran 2026 aralığında yapıldığını bildiriyor. Ancak koşullu emirlerin normal endpointte reddi için ayrı, gecikmeli yürürlük açıklaması var. Bu iki tarih tek geçiş anı olarak ele alınmamalıdır. UM ve CM positionSide ayarı ile limit havuzları ortak. Mod değiştirmeden önce her iki üründeki açık emir ve pozisyonlar kontrol edilmelidir. Anlık POST/PUT/DELETE yanıtlarından avgPrice/cumBase/cumQuote kaldırılmış olabilir, dolum sorgu yolundan teyit edilmelidir.

Teslimli kontratta vade öncesi son 10 dakika yeni pozisyon açılışı kısıtlanır. Açık pozisyonlar uzlaşma fiyatıyla kapatılır, sonuç ve uzlaşma ücreti coin cinsi hesapta teyit edilmelidir. Bot, vade sonunda sıfır pozisyon görmesini kendi gönderdiği kapanış emriyle karıştırmamalıdır.

Kabul senaryoları ortak UM/CM mod değişikliği reddi, ortak rate-limit tüketimi, eksik ACK dolum alanları, vade öncesi açılış reddi, uzlaşma sonrası bakiye/PnL/ücret eşlemesi ve yeni kontrat kimliğinin ayrılmasıyla genişletildi.

[Entegrasyon duyurusu](https://developers.binance.com/en/docs/products/derivatives-trading-coin-futures/Important-CM-UM-Integration-Notice), [resmi teslim ve uzlaşma açıklaması](https://www.binance.com/en-NG/support/faq/detail/a3401595e1734084959c61491bc0dbe3).

Durum, temel ürün farkları ve uzlaşma davranışı kaynaklı belgelendi. Algo parametre sınırları ve hesap/ortam bazında gözlem hâlâ açık.

## Algo sınırı karşılaştırması sonucu

Resmi SDK arama sonuçları normal emir için eski callback açıklamasını taşıyor. Bu, yeni algo endpoint sınırını tek başına doğrulamıyor. Doküman ve SDK arasındaki bu konu çözümlenmiş kabul edilmedi. Araştırma açık sorusu olarak korunuyor, ürün desteği için hesap/ortam teyidi gerekir.
