# Native emir değiştirme ve toplu oluşturma

6 Kasım 2026. Tam test koşusu: 372 test, başarılı. Bu geliştirmede gerçek
demo hesabına emir/ayar yazılmadı ve arka plan izleyicisi başlatılmadı.

## Uygulanan A5 kapsamı

- Native tekli LIMIT değiştirme: PUT `/fapi/v1/order`.
- Native toplu değiştirme: PUT `/fapi/v1/batchOrders`, 1–5 alt emir.
- Native toplu oluşturma: POST `/fapi/v1/batchOrders`, 1–5 normal LIMIT emir.
- Değişiklik geçmişi: GET `/fapi/v1/orderAmendment`.
- Önceki seçili toplu iptal yolu korunur; değiştirilmiş miktar/fiyat zincirini
  de tanıyarak aynı emirleri durdurabilir.

Bu yollar yalnız mevcut, yetkili plan v2 oturumlarına bağlandı. Diğer emir
türleri ve API'nin bütün parametre kombinasyonları tamamlanmış sayılmaz.
İlk native amend kapsamı açık fiyatlı GTC LIMIT'tir; koşullu emirler bu normal
emir uçlarına gönderilmez.

## Yetki ve risk sınırları

Emir toplam miktarı artırılmaz. Yeni toplam, mevcut gerçekleşmeden büyük
olmalıdır; işlem API tarafındaki yarışta bu sınırı aşarsa emir sonlanması ayrıca
uzlaştırılır. SINGLE giriş fiyatı yalnız daha iyi yönde, stop/ilk hedef/tolerans
aralığında değişebilir. SHORT fiyat iyileştirmesinde nominal tutarın artması da
engellenir. Grid fiyatları amend ile değiştirilmez; hücre seviyeleri korunur.
Grid hücresinin bir defalık miktar azaltması, sonraki döngülerin onaylı toplam
grid bütçesini veya tam hücre rezervini değiştirmez.

Hazırlık salt okunurdur. Uygulama kullanıcı/hesap/oturum/plan sürümü/emir
kimliği/fiyat/miktar/geçerlilik süresine bağlı somut komut özeti ister.
Gönderimden önce sahiplik, filtreler, gerçekleşen miktar ve yetki yeniden okunur.
Toplu değişiklikte bütün alt komutlar tek işlemle SUBMITTING ayrılır; alt komut
tek başına gönderilerek grup denetimi aşılamaz.

## Kalıcı revizyon ve belirsiz yanıt

Plan ve ilk oluşturma niyeti değiştirilmez. APPLIED revizyonlar ayrı sırada
tutulur. Runner, iptal ve envanter yolları doğrulanmış güncel parametreleri bu
zincirden okur. Miktar ve gerçekleşme projeksiyonu aynı SQLite işleminde değişir.

modifyId yerel olarak benzersiz üretilir; borsada idempotent tekrar anahtarı
olarak kabul edilmez. PUT yanıtı kaybolursa aynı PUT gönderilmez. Geçmişteki
modifyId, borsa emir kimliği, önceki/sonraki fiyat ve miktar ile güncel GET
sonucu eşleşmeden revizyon APPLIED sayılmaz. Geciken geçmiş ACKNOWLEDGED/UNKNOWN
kalır ve yeni girişleri engeller. Eksik veya bozuk geçmiş doğru varsayılmaz.

Native değişiklik sırasında gerçekleşme artıp emir sonlanırsa, gerçekleşmiş
miktar kaybolmaz; uygulanmamış değişiklik APPLIED ilan edilmez. Gönderilmemiş
taslak iptal edilebilir; gönderilmiş/belirsiz işlem yerel iptal ile temizlenemez.

Emir kimliği aynı görünse bile borsa orderId değişmişse sahiplik reddedilir.
Elle yapılmış fiyat değişikliği doğrulanmış revizyon gibi kabul edilmez.

## Toplu oluşturma ve kısmi sonuçlar

Gridde birden çok hazır hücre varsa en fazla beşer normal LIMIT emir native
gruba alınır. Başlangıç MARKET stoğu bu gruba karıştırılmaz. Tüm kimlikler
gönderimden önce atomik ayrılır. Kapsam/risk, rezervden önce ve son gönderim
öncesinde tekrar doğrulanır; bu sırada yetki/görünüm değişirse hiçbir alt emir
gönderilmez.

HTTP yanıtı bütün alt emirlerin başarılı olduğu anlamına gelmez. Her oluşturma
ayrı GET ile doğrulanır. Bir alt emir reddedilirse ona envanter yazılmaz.
Bulunamayan belirsiz alt emir UNKNOWN kalır, yeni girişler durur ve grup tekrar
POST edilmez. Mevcut kimliklerle yeni kimlikleri karıştırarak grubu yeniden
göndermek de reddedilir. Kısmi ret ve tamamlanmamış üyeler ayrı raporlanır.

## Komutlar

```
python -m agentrader orders amend-prepare SESSION_ID CLIENT_ID --quantity QUANTITY --price PRICE
python -m agentrader orders amend-apply COMMAND_ID --digest DIGEST --execute-demo
python -m agentrader orders amend-reconcile COMMAND_ID
python -m agentrader orders amend-cancel COMMAND_ID --digest DIGEST
python -m agentrader orders batch-amend-prepare SESSION_ID CHANGES.json
python -m agentrader orders batch-amend-apply BATCH_ID --digest DIGEST --execute-demo
python -m agentrader orders batch-amend-reconcile BATCH_ID
python -m agentrader orders batch-amend-cancel BATCH_ID --digest DIGEST
```

Toplu değiştirme dosyası, client_id/quantity/price alanları olan 1–5 nesnelik
JSON listesidir. Komut şablonları bu geliştirmede gerçek hesaba uygulanmadı.
Doğrulanmış yazma sonrasında mevcut yönetim devralınır: grid varsayılan sürekli,
SINGLE bir turdur. --iterations/--interval değiştirilebilir. Salt okunur
reconcile komutu kendiliğinden yeni emir göndermez; yönetimi de devralmak için
ayrıca --execute-demo gerekir. Kontrollü grid çıkışının DRAINING politikası sürer.

## Kanıt ve kalan işler

Testler tekli/toplu PUT, kısmi ret, kayıp PUT/POST, geç gerçekleşme, restart,
geçmişin gecikmesi, yanlış modifyId, bozuk geçmiş, son yetki denetimi, atomik
grup rezervi ve dondurulmuş risk kapasitesini kapsar. CLI yardım yolları çalıştı.
Yeni yollar gerçek Binance demo emirleriyle henüz uçtan uca doğrulanmadı.

WebSocket, geçmiş sayfalama, trailing yürütme, servis/bildirim/uzaktan erişim,
diğer ürünler ve tamamlayıcı API kapsamları hâlâ eksiktir. Bu çalışma A0–A12'nin
tamamlandığı anlamına gelmez.

Kaynak: [Binance resmi USD-M emir belgesi](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade).
