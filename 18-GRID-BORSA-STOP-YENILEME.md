# Yönlü gridin borsa stopunu yenileme

> 9 Kasım 2026 plan notu: Bu belge tarihli işlem alt sistemi teslimini ve kanıtlarını korur. Burada geçen TradingView zinciri yeni geliştirme hedefi değildir; yerine kendi grafik/çizim → strateji → onay → işlem yolu geçmiştir. Güncel ürün sırası [02](02-ASAMALI-GELISTIRME-PLANI.md), geçiş tasarımı [19](19-KENDI-GRAFIK-TERMINALI-VE-GECIS.md) içindedir.

7 Kasım 2026. Uygulama ve sahte borsa testleri tamamlandı. Gerçek demo emir
doğrulaması bekliyor. Bu teslim Binance TRAILING_STOP_MARKET emri değildir.

## Onaylı plan ve mevcut planların davranışı

Yönlü GRID planındaki `management.trailing` nesnesi isteğe bağlı boolean
`native_stop` alanını kabul eder. Varsayılan false'tur. Örnek:

```json
{"activation_price":"77000","distance_bps":"100","min_step_bps":"10","native_stop":true}
```

Örnek yeni işlem yetkisi veya fiyat önerisi değildir. Alan plan özetine dahildir;
eski onaylar kullanılmaz, mevcut plan kendiliğinden değiştirilmez. SINGLE ve
neutral grid için bu alan desteklenmez. Önceki bot takip eşiği çalışmaya devam eder.

## Geçiş akışı

Bot yeni tepe/dip gözleminden takip eşiğini hesaplar. Açık envanter ve gönderim
öncesi güncel fiyat doğrulanınca bu eşikte closePosition STOP_MARKET emri kurar.
Emir miktar içermez; uygun LONG SELL veya SHORT BUY tarafını kapatır. Dolayısıyla
gridin kısmi çıkışlarında korunacak miktarın yeniden yazılması gerekmez.

Yeni korumanın kimliği, seviyesi, tarafı, MARK_PRICE ve close-all alanları GET ile
doğrulanır. Hesap sahipliği tekrar denetlenir. Daha önceki takip stopu ancak bu
doğrulamadan sonra iptal edilir; iptal terminal ve alt emirsiz doğrulanmalıdır.
Başlangıçtaki sabit stop ve son hedef ayrıca korunur. En fazla bir bekleyen
geçiş vardır; yeni watermark bekleyen emrin parametrelerini değiştirmez.

Geçişler PREPARED → VERIFIED → APPLIED olarak kalıcıdır. İstemci kimliği nesle
bağlıdır; belirsiz POST yalnız aynı kimlikle sorgulanır. DELETE için kalıcı
iptal kaydı tutulur; yanıt kaybolursa aynı iptal tekrar gönderilmez. Yönetim
hatasında mevcut durdurma bariyeri uygulanır; otomatik girişe devam edilmez.

Emekli stop ancak kayıtlı geçiş ve iptal komutuyla, CANCELED ve alt emirsizse
beklenen terminal kabul edilir. Son stopun haricen iptali, reddi veya tetiklenmesi
gridi STOPPING'e geçirir. Çoklu oturum sahipliği bütün stop nesillerini kapsar.
Normal emirler iptal edilir; tetiklenen alt emir kısmen dolmuşsa kalan alt emir
önce iptal edilir. Pozisyon yeniden doğrulanıp yalnız gerçek artık miktar
kapatılır. TRIGGERING/TRIGGERED olup alt emir kimliği henüz yoksa piyasa kapanışı
gönderilmez; uzlaştırma beklenir. Tam dolmuş native kapanış ikinci kez kapatılmaz.

## Çalışma ve kesinti sınırı

Bot kapandığında borsa son doğrulanmış sabit seviyeyi tutar. Yeni fiyat tepelerine
göre stopun ilerlemesi için bot çalışmalıdır. Bu davranış borsanın bağımsız
TRAILING_STOP_MARKET politikasıyla aynı değildir. Borsa stopu tetiklenmesi bekleyen
grid açılış emirlerini kendiliğinden iptal etmez; kesintiden sonra geç dolum
olabilir ve bot bunları uzlaştırmalıdır. Kesintisiz kapanış garantisi verilmez.
Başlangıç koruması ayrıca tutulduğu için birden fazla stop kaydı görülebilir.

Read-only yönetim `GRID_STOP_MOVE_REQUIRED` döndürür; API yazması yapmaz. Normal
izleme `GRID_STOP_MOVED` geçişini ve daha sonra grid yönetimini sürdürür.
Bütçe, kaldıraç, risk profili ve mevcut işlem onayları değiştirilmedi.

## Kanıt ve kalan kapsam

21 yeni sahte borsa senaryosu: ilk/sonraki stop, doğrulamadan önce iptal etmeme,
read-only, kayıp POST/DELETE, restart, hatalı koruma alanı, kesin ret, geçiş
sırasında artan watermark, fiyat boşluğu, LONG/SHORT hedge, harici iptal,
tetiklenen alt emrin tam/kısmi gerçekleşmesi ve kimlik bekleme; farklı sembollü
oturumda sahiplik ve bağımsız kapanış. Tam regresyon raporu:
`reports/development-validation-20261107.json`.

Gerçek demo yazma/dolum/kesinti kanıtı, neutral takip politikası, kalan grid
plan politikaları, uzaktan kimlik denetimli onay ve rapor erişimi, diğer API
iş akışları, çapraz ürün portföyü, Spot/COIN-M ve TradingView zinciri bekliyor.
Bu turda gerçek demo emri, hesap ayarı veya dış mesaj gönderilmedi.

API alanları: [Binance USD-M emir belgeleri](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade).

Amend akışı da ilerletilmiş grid stopunu kontrol eder; emir değiştirerek takip eşiği atlanamaz. Geçersiz takip nesnesi ve native flag türü plan doğrulamasında reddedilir.
