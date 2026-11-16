# Cüzdan, Convert ve alt hesap araştırması

İnceleme tarihi: 15 Kasım 2026. Sabitlenmiş resmi koleksiyon başlangıç kapsamı Convert 9, Wallet 50, Sub Account 50 olmak üzere 109 işlem. İşlem listesi cross-product-operation-catalog.json içinde OP-0001–OP-0009 ve OP-0456–OP-0555 kimlikleriyle saklanır. Bu sayı güncel bütün API kapsamının tamamlandığı anlamına gelmez.

## Convert sözleşmesi

Resmi işlem sayfası teklif isteme, kabul, durum, geçmiş ve limit emir oluşturma/iptal/sorgulama yollarını içeriyor. Kabul yanıtındaki PROCESS, ACCEPT_SUCCESS, SUCCESS ve FAIL ayrımı korunmalı. walletType birden fazla cüzdan birleşimini destekliyor. Kaynak: [Convert trade](https://developers.binance.com/en/docs/catalog/core-trading-convert/api/rest-api/trade).

Bot için çıkarılan gereksinimler: teklif, emir ve muhasebe kaydının kimliklerini ilişkilendirme, süreli teklifi kabul öncesi değerlendirme, zaman aşımında sonucu sorgulama, cüzdan seçimini kullanıcı talimatında saklama, limit emrin iptal/dolum yarışını uzlaştırma.

## Cüzdan sözleşmesi

Ağ bilgileri ücret, minimum/maksimum tutar, miktar adımı, adres/memo kuralları ve ağın açık olmasını içerir. Çekim geçmişi withdrawOrderId ile aranırken daha dar zaman aralığı gerekir. Kaynak: [Wallet capital](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/capital).

Universal transfer ayrı API izni gerektirir. Isolated yönlerinde kaynak/hedef sembol koşulludur. Geçmiş sorgusu son altı ayla sınırlıdır. Resmi şemada fromSymbol/toSymbol alanlarında transfer türü enumlarının görünmesi belge tutarsızlığı olarak açık tutulur. Kaynak: [Wallet asset](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/asset).

Bot için çıkarılan gereksinimler: varlık ve ağın ayrı kimliği, Decimal tutarlar, transfer yönü ve hesap kimlikleri, gönderim öncesi güncel kısıtlar, yanıt kaybında geçmiş sorgulama, yatırma/çekme/transfer kaydı ile bakiye uzlaştırması. withdrawOrderId desteği tek başına tekrar gönderimin mükerrer işlem üretmeyeceğini kanıtlamaz.

## Alt hesap inceleme kuyruğu

50 koleksiyon kaydı hesap keşfi, ürün etkinleştirme, bakiye/pozisyon sorguları, transfer, pozisyon taşıma ve API anahtarı yönetimi içeriyor. Master, sub-account ve managed account yetkileri ayrı incelenecek. Bu bölüm envanter sınıflandırmasıdır, 50 sözleşmenin ayrıntılı doğrulaması henüz yapılmadı.

## Kabul senaryoları

1. Teklif alınır, kabul öncesi geçerlilik süresi biter.
2. Kabul yanıtı PROCESS olur, sonraki sorgu SUCCESS döner.
3. Kabul isteğinin yanıtı kaybolur, sorgu mevcut dönüşümü bulur.
4. Kaynak cüzdanın kullanılabilir bakiyesi teklif ile kabul arasında değişir.
5. Convert limit iptali sırasında kısmi dolum olur.
6. Aynı coin farklı ağlarda farklı ücret ve minimuma sahiptir.
7. Memo gereken ağda memo eksiktir.
8. Çekim öncesi ağ kapatılır veya tutar adımı değişir.
9. Çekim isteği kabul edilir, HTTP yanıtı kaybolur, geçmişten teyit gerekir.
10. Çekim kimliğiyle geçmiş aranırken zaman aralığı bölünür.
11. Isolated transferinde gerekli kaynak/hedef sembol eksiktir.
12. Universal transfer izni kapalıdır.
13. Transfer sonrası bir hesap bakiyesi güncellenirken diğeri gecikir.
14. Master anahtarı gereken işlem sub-account anahtarıyla çağrılır.
15. Aynı varlık farklı alt hesaplarda aynı yerel rezervasyonu paylaşmaz.
16. Pozisyon taşıma emri kabulünden sonra iki hesabın pozisyonları uzlaştırılır.

Bunlar araştırmadan çıkarılmış kabul tasarımlarıdır. Borsada çalıştırılmış test olarak sayılmaz. Mevcut botun demo/USD-M ürün kapısı nedeniyle bu ürünler kullanılabilir destek olarak işaretlenemez.

## Kalan doğrulamalar

109 satırın alan bazında güncel belge karşılaştırması, Convert limit kısıtları, yatırma/çekme durum tabloları, Travel Rule uygunluk akışı, alt hesap pozisyon taşıma koşulları, ortam erişimi ve ürünlerin bütün hata kodları açık. Hiçbir finansal hareket veya hesap ayarı değişikliği yapılmadı.
