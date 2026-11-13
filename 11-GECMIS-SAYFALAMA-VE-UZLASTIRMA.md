# Gelir ve gerçekleşme geçmişinin eksiksiz okunması

6 Kasım 2026. Tam test kümesi: **386 test başarılı**. Doğrulama yerel ve
sahte borsa üzerindedir; bu çalışmada demo hesabına istek gönderilmedi.

## Uygulanan davranış

`agentrader/history.py` ortak geçmiş okuyucularını içerir. SINGLE ve grid
sahiplik kontrolü, eski watchdog ve günlük zarar kontrolleri bu yolu kullanır.

- Gerçekleşmeler ilk sorguda sabit başlangıç/bitiş zamanı ile okunur.
  Dolu sayfa sonrası `fromId` kullanılır; tarihler aynı isteğe eklenmez.
  Aynı milisaniyedeki 1.000 üzeri gerçekleşme atlanmaz. Sonraki sorgu sırasında
  oluşan, sabit bitişten sonraki kayıtlar bu görünümün içine alınmaz.
- Gelir, komisyon ve fonlama kayıtları dolu sayfalarda zaman aralığı ikiye
  bölünerek yeniden okunur. Dahil başlangıç/bitiş sınırları çakışmaz.
  Tek milisaniye hâlâ doluysa eksiksizlik kanıtlanamaz ve işlem reddedilir.
- Gelir kimliği `incomeType + tranId` ile değerlendirilir. Aynı kayıt ikinci
  kez toplama eklenmez; aynı kimlikte çelişki hata verir.
- Kimlik, zaman, yön, miktar, sonlu gelir tutarı ve istek bütçesi denetlenir.
  Sıra bozukluğu, ilerlemeyen sayfa, ağ hatası veya bütçe aşımında kısmi sonuç
  kullanılarak yeni girişe izin verilmez.
- Yeni v2/grid oturumunun başlangıcı borsa saat farkını içerir.

## Kanıt

Yeni testler yoğun ve aynı milisaniyeye denk gelen kayıtları, sayfa sınırlarını,
istek bütçesini, çelişkili kimlikleri, geçersiz tutarları ve bağlantı hatasını
kapsar. Yürütücü entegrasyon testi 2.000 gerçekleşmeyi uzlaştırır; sonraki sayfaya
yabancı işlem eklenince yeni emir göndermeden kalıcı durdurma kaydı oluşturur.

## Sınırlar ve sıradaki iş

Bu değişiklik gerçek zamanlı WebSocket bağlantısını tamamlamaz. A7'nin sıradaki
işi kullanıcı olaylarının alınması, normalleştirilmesi ve bağlantı kesintisinden
sonra bu REST okuyucularıyla yeniden doğrulanmasıdır. Mevcut altı günlük otomatik
devralma sınırı korunur. Kayıt sayısı artık doğrudan 1.000 ile sınırlı değildir;
API erişimi, saklama süresi ve istek bütçesi sınırları devam eder.

Kaynaklar: [Binance hesap REST belgeleri](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account),
[işlem REST belgeleri](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade).
