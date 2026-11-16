# Kaynak ve yürütme sınırı kayıtları

Sonraki inceleme: [5–8 turundaki çelişki sonuçları](SOURCE-CONFLICT-RESOLUTIONS.md). Aşağıdaki tablo önceki tur kaydıdır. Travel Rule belge erişimi sonraki turda düzeldi, ortam soruları daha ayrıntılı sınıflandırıldı.

15 Kasım 2026. Bu kayıtlar kanıtlanmış destek olarak işaretlenmez. Genel eksik etiket yerine hangi kararın belirsiz olduğu ve nasıl çözüleceği belirtilir. Yeni kaynak bulunmadıkça aynı belirsizlik için aynı okuma deneyini tekrar etmek gerekmez.

| Kimlik | Belirsiz davranış | Elde edilen kanıt | Geliştirme etkisi / kapanış yöntemi |
|---|---|---|---|
| Q-CM-01 | Yeni CM algo yollarının tam sözleşmesi ve callback üst sınırı | Entegrasyon duyurusunda normal stop yolunun değişmesi, SDK'da eski normal emir alanları, batch/single sınır farkı | Yeni CM algo desteğine kesin sözleşme atama. Güncel resmi şema veya kontrollü ürün kabulüyle kapat |
| Q-OPT-01 | Options olaylarının bazı iç nesnelerinin tam alan ve tip sözleşmesi | Resmi modeller arşivlendi, önceki sayfa şemaları bazı iç alanları eksik açıklıyor | Parser bilinmeyen alanları destek iddiasına dönüştürmez. Yetkili hesapta olay örneği/model karşılaştırması gerekir |
| Q-PM-01 | PM Pro/SPAN hesap ve risk modelinin gerçek hesap davranışı | PM, Pro ve SPAN farklı yollar/teminat modelleri kullanıyor | Hesap türü keşfi ve ayrı risk/parser kabulü gerekir. PM uniMMR eşikleri Pro/SPAN'a taşınmaz |
| Q-WAL-01 | Yerel kuruluşun Travel Rule soru/kimlik koşulları | SDK request/response alanları alındı. Canlı travel-rule dokümanı iki kez zaman aşımı verdi | Gereksinim sorgusu ve güncel kuruluş şemasıyla uygun yol seçilecek. SDK eşleşmesi kişisel hesap uygunluğunu kanıtlamaz |
| Q-WAL-02 | Wallet transfer fromSymbol/toSymbol şema enum örneği | Resmi sayfa ve koleksiyon transfer türlerini sembol örneği gibi gösteriyor | Bu enumları gerçek symbol olarak göndermemek gerekir. Resmi düzeltme veya hesapta kabul edilebilir örnekle kapat |
| Q-DATA-01 | SXPUSDT mark minimum fiyatın altında | Önceki ve taze halka açık Demo snapshotı aynı uyuşmazlığı veriyor | 62 vaka veri koşulu nedeniyle bloklandı. Güncel tutarlı fiyat/filtre çiftiyle tekrar ölç |
| Q-ENV-01 | Her ürünün demo/test/live hesap uygunluğu | Bu tur dört ürünün public metadata okuması başarılı | Özel hesap ve finansal yürütme gözlemi yapılmadı. 6. araştırma adımında ortam matrisiyle sınırlandırılacak |

SDK/Postman kaynağında 555/555 eşleşme bulundu. Bu iki kaynağın ortak şema ailesinden üretilmesi, yukarıdaki canlı belge ve hesap çelişkilerini çözmez. Yeni işlem duyuruları envanter kapsamını değiştirebilir. Bu tur genel internetin tamamının veya Binance'in bütün hizmet ürünlerinin eksiksiz tarandığı iddiasında bulunmaz.
