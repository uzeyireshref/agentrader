# İzole teminat ve seçili toplu iptal

6 Kasım 2026. Son koşu: `python -m unittest discover -s tests -q` — 340 test,
başarılı. Bu geliştirmede Binance hesabında emir veya ayar değiştirilmedi.
Yeni yazma yetenekleri sahte borsayla doğrulandı; gerçek demo yazma kanıtı yoktur.

## İzole pozisyon teminatı

`IsolatedMarginCommands` ADD/REMOVE işlemlerini hesap, yerel kullanıcı, sembol,
pozisyon tarafı, tutar ve kısa geçerlilik süresine bağlı bir komut olarak kaydeder.
Hazırlık yalnız okur. Uygulama somut komut kimliği ve özetini ister; bir kere
gönderir. Tekrarlı çağrı veya restart ikinci teminat artırımı/azaltımı üretmez.

Kapsam USD-M USDT, single-asset ve ISOLATED pozisyondur. BOTH/LONG/SHORT hesap
moduyla eşleşmelidir. Aktif bot oturumunun teminatını bağımsız değiştirmez;
bu entegrasyon henüz tamamlanmadı. Bekleyen normal emir, değişmiş pozisyon,
cüzdan veya teminat geçmişi varken hazırlanan komut uygulanmaz.

ADD kullanılabilir USDT'yi denetler. REMOVE sonrası pozitif izole cüzdan,
masraf rezervi ve ihtiyatlı likidasyon tamponu gerekir. Seçili tarafı kapsayan
aktif MARK_PRICE STOP_MARKET koruması borsadan doğrulanır. Model hesabı borsanın
gerçek likidasyon hesabının garantisi değildir. Teminat modu değiştirilmez.

Örnek komut şablonları; bu çalışma sırasında çalıştırılmadı:

```
python -m agentrader settings margin-prepare --symbol SYMBOL --position-side BOTH --action ADD --amount AMOUNT
python -m agentrader settings margin-apply COMMAND_ID --digest DIGEST --execute-demo
python -m agentrader settings margin-reconcile COMMAND_ID
```

Başarılı POST yanıtı, yeni geçmiş kaydı, aynı pozisyon kimliği ve beklenen cüzdan
değişimi birlikte APPLIED sonucunu verir. Geciken geçmiş ACKNOWLEDGED kalır ve
sonraki salt okunur uzlaştırmada tamamlanabilir.

Yanıtı kaybolmuş artımlı işlem UNKNOWN kalır. Belgelenen istek/geçmiş alanlarında
istemci komut kimliği bulunmadığından yalnız benzer bir geçmiş satırı işlemin
bizim isteğimiz olduğunu kanıtlamaz. Aynı tutarı otomatik tekrar göndermek veya
bu kaydı yalnız eşleşen geçmişe bakarak APPLIED saymak yapılmaz. Operatör/borsa
denetimi gerektiren belirsizlik yeni girişleri ve diğer hesap ayarı değişimlerini
engeller; koruyucu azaltma/kapanış yolu bundan dolayı kapatılmaz.

## Seçili toplu normal emir iptali

`OwnedBatchCancel` yalnız sahip olunan, tek sembole ait, en fazla 10 seçili normal
emri native DELETE batchOrders isteğiyle iptal eder. Hesap çapında toplu iptal
yapmaz ve koşullu emirleri bu listeye karıştırmaz.

Gönderimden önce hem grup hem alt emir iptal niyetleri kalıcı ayrılır. Kayıp
yanıt veya restart otomatik ikinci DELETE üretmez. Daha önce yanıtı belirsiz
tekli iptal, yeni gruba alınarak tekrar gönderilemez.

HTTP yanıtındaki bütün alt sonuçların başarılı olduğu varsayılmaz. Her emir
ayrı GET ile sorgulanır; iptal sırasında FILLED olmuş emir de terminal ve gerçek
miktarıyla değerlendirilir. Hâlâ açık alt emir PARTIAL/uzlaştırılmamış kalır.
Grid kalan miktarı kapatmadan önce bütün seçili emirlerin terminal durumunu ister.

Bu yardımcı GridRunner'ın STOPPING ve DRAINING akışına bağlandı. Büyük gruplar
10'luk parçalara ayrılır; tekli/kısmi hücre iptalinin mevcut kalıcı yolu korunur.
Emir oluşturma ve değiştirme batch uçları ile native amend henüz tamamlanmadı.

## Uzun çalışma ve kalan sınırlar

Tam miktarı FILLED olarak doğrulanıp kaydedilmiş grid emri her tur yeniden
borsadan sorgulanmaz. Aktif, kısmi ve belirsiz emirler sorgulanmaya devam eder;
işlem geçmişi ve pozisyonla sahiplik denetimi kaldırılmadı. SQLite emir kimliği
indeksinden doğrudan okuma eklendi.

Mevcut işlem geçmişi yolunda 1000 satır ve otomatik devralmada süre sınırları
sürüyor. Eksik geçmiş doğru varsayılmaz; sayfalama ve WebSocket çalışmaları
kalan paketlerdedir. Bu geliştirme bütün A0–A12 planını tamamlamaz.

Resmi alan ve uç referansı:
[Binance USD-M trade belgesi](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade).
