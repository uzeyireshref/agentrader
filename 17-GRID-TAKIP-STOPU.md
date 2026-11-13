# Yönlü grid için bot tarafından izlenen takip stopu

> 9 Kasım 2026 plan notu: Bu belge tarihli işlem alt sistemi teslimini ve kanıtlarını korur. Burada geçen TradingView zinciri yeni geliştirme hedefi değildir; yerine kendi grafik/çizim → strateji → onay → işlem yolu geçmiştir. Güncel ürün sırası [02](02-ASAMALI-GELISTIRME-PLANI.md), geçiş tasarımı [19](19-KENDI-GRAFIK-TERMINALI-VE-GECIS.md) içindedir.

7 Kasım 2026. Uygulama ve sahte borsa testleri tamamlandı; gerçek demo emir
kanıtı bekliyor. Bu teslim bütün gelişmiş grid politikalarını tamamlamaz.

## Politika

Yönlü GRID planı, SINGLE ile aynı isteğe bağlı `management.trailing` alanını
kabul eder: `activation_price`, `distance_bps`, `min_step_bps`. Alan yoksa veya
null ise eski planın davranışı değişmez. Etkinleşme referans ile son hedef
arasında; mesafe 1–5000 bps ve güncelleme aralığı 1–mesafe arasında olmalıdır.
Örnek bir politika: `{"activation_price":"77000","distance_bps":"100","min_step_bps":"10"}`.
Bu örnek işlem önerisi veya yetkisi değildir. Yeni politika plan özetinin parçasıdır;
mevcut onaylanmış plan kendiliğinden değiştirilmez.

Açık envanter varken LONG için görülen en yüksek, SHORT için en düşük mark
fiyatı saklanır. Etkinleşince takip mesafesi bu fiyattan hesaplanır; fiyat adımına
yuvarlanır ve asgari iyileşme gerçekleşince eşik güncellenir. Stop geri gevşemez.
Watermark ve eşik kalıcı oturum kaydında tutulur; yeniden başlatmada sıfırlanmaz.
Politika bütün grid oturumuna aittir; hücre yeniden açıldığında sıfırlanmaz.

## Yürütme ve sınırlar

Bu sürüm botun yönettiği hareketli eşiktir. Borsadaki başlangıç closePosition
stopu ve son hedef korunur; takip eşiği borsaya taşınmaz. Bu nedenle botun
sürekli çalışması ve güncel mark fiyatı alması gerekir. Kapalı olduğu dönemin
tepe/diplerini yeniden kurmaz; kesinti sırasında hareketli çıkış garantisi yoktur.
Yerleşik Binance trailing emri ve native stop değiştirme bu teslimin dışındadır.

Mark eşikten geri dönünce STOPPING kalıcılaştırılır; bekleyen grid emirleri
iptal edilip terminal durumları doğrulanır. İptal sırasında dolum da dahil
borsadan doğrulanan gerçek kalan miktar mevcut kapanış akışıyla kapatılır.
Yeni açılış ve toplu emir gönderim kontrolleri hareketli eşiği de denetler.
Belirsiz kapanış POST'u tekrar gönderilmez; kalıcı kimlikle uzlaştırılır.
DRAINING sırasında mevcut pozisyonun takip yönetimi devam eder.

Salt okunur yönetim borsaya emir göndermez; gözlemi ve stop bariyerini yerel
veritabanına yazabilir. Bütçe, kaldıraç, risk profili veya geçmiş işlem yetkisi
artırılmaz. Neutral gridin iki taraflı takip politikası hâlâ desteklenmez.

## Doğrulama ve kalan işler

13 yeni senaryo: varsayılan kapalı davranış, etkinleşme/geri gevşememe,
minimum güncelleme adımı, sabit native korumanın korunması, LONG/SHORT hedge,
yeniden başlatma, salt okunur stop bariyeri, kısmi azaltmadan kalan miktar,
iptal sırasında dolum, DRAINING, belirsiz kapanış ve gönderim öncesi refill kontrolü.
Tam regresyon kanıtı: `reports/development-validation-20261107.json`.

Kalan kapsam: native/grid stop yenileme, neutral takip politikası, diğer grid
plan politikaları, gerçek demo dolum/kesinti kanıtları; ardından uzaktan kullanıcı
onayı/rapor erişimi, tamamlayıcı API, çapraz ürün portföyü, Spot/COIN-M ve
TradingView zinciri. Bu turda gerçek demo emri veya dış mesaj gönderilmedi.


Sonraki teslimde isteğe bağlı borsa stop yenilemesi eklendi: [18-GRID-BORSA-STOP-YENILEME.md](18-GRID-BORSA-STOP-YENILEME.md). Varsayılan bot-only davranışı korunur.
