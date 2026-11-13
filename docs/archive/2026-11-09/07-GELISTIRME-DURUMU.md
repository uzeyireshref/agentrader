> Tarihsel arşiv: 9 Kasım 2026 yön değişikliğinden önceki metin. Güncel ürün kararı için [aktif hedeflere](../../../01-PROJE-VE-HEDEFLER.md) bakın. İçerik korunmuştur; yerel Markdown bağlantıları arşiv konumuna uyarlanmıştır.

# Geliştirme durumu — 6 Kasım 2026

Kullanıcı A0–A12 geliştirmesini onayladı ve aşama geçişlerinde yeniden soru
sorulmamasını istedi. Geliştirme için tekrar onay gerekmiyor. Bu kayıt,
belirsiz fiyat/miktarla yeni işlem açma veya süresi dolmuş işlem onayını
yenileme yetkisi değildir. Gerçek hesap desteği etkinleştirilmedi.

## Bu geliştirme grubunun sonucu

594 test geçti. Önceki ortak istek kontrolünde Binance demo üzerinde 12/12
salt okunur kontrol geçti. Rapor:
`reports/capability-probe-after-transport-20261106.json`.
Bu çalışmada emir veya hesap ayarı değiştirilmedi. Salt okunur başarı,
bütün yazma operasyonlarının çalıştığı anlamına gelmez. Sonraki v2 boş hesap
kontrolü pozisyon/açık emir bulunduğu için BLOCKED döndü; mevcut işlemlere
dokunulmadı. Kayıt: `reports/v2-snapshot-readonly-20261106.json`.

| Paket | Uygulanan | Kalan |
|---|---|---|
| A0–A1 | 95 operasyon envanteri; sabit salt okunur keşif; süreli ve anahtara bağlı kanıt | Yeni ürünler kendi kanıtlarını gerektirir |
| A2 | Ortak JSON transport, sınırlı GET tekrarı, yazmalarda otomatik tekrar yok; kalıcı host beklemesi; 429/418, Retry-After, 503 ve belirsiz teslim ayrımı | Yeni adaptörler de bu katmandan geçirilir |
| A3 | USDT teminat; SINGLE/grid risk bağlantısı; tam grid rezervi; ayrı SHORT kayıp/nominal fiyatı | Farklı sembollü USD-M çoklu oturum ve ortak SINGLE/grid rezervleri eklendi; çapraz ürün/teminat portföyü ve gerçek demo kanıtı bekliyor |
| A4 | Ayar komutları; izole teminat ADD/REMOVE, geçmiş/cüzdan doğrulaması, belirsiz artımlı işlemin tekrar edilmemesi | Çoklu oturum/grid/neutral teminat entegrasyonu eklendi; diğer ürünler ve demo yazma kanıtı |
| A5 | SINGLE/grid normal emirler; native tekli/toplu amend, toplu oluşturma/iptal; değişiklik zinciri ve alt emir uzlaştırması | Korunan GTC LIMIT kapsamı dışındaki kombinasyonlar; gerçek demo yazma/kesinti kanıtı |
| A6 | Stop/son hedef, kademeli azaltma, gerçek giriş ortalamasına stop taşıma ve kalan miktara yeniden boyutlandırma; GET doğrulaması | SINGLE takip stopu eklendi; grid/native trailing ve gerçek demo yazma kanıtı |
| A7 | Demo kullanıcı WebSocket bağlantısı; normal/koşullu olay normalleştirme; kalıcı REST bariyeri; geçmiş sayfalaması; yeniden bağlantı ve heartbeat | Gerçek fill/iptal/stop olayı ve uzun süreli kesinti demo kanıtı |
| A8 | GridRunner: döngü, kısmi fill/iptal, stop bariyeri, borsa koruması, native alt emir, restart; plan v2/CLI bağlantısı | Gerçek demo yazma, kesinti ve uzun süreli kanıt; WebSocket/servis |
| A9 | LONG/SHORT yönlü ve tek bütçeli hedge neutral grid; aritmetik/geometrik seviyeler | Gerçek demo neutral kanıtı ve kalan gelişmiş politikalar |
| A10 | Sürekli ön plan izleme; kontrollü grid çıkışında DRAINING; açık stop/close komutu | Ön plan servis, sağlık, kontrollü durdurma ve kalıcı Telegram kuyruğu eklendi; otomatik görev kurulumu, uzaktan onay ve rapor erişimi bekliyor |
| A11 | REST gelir ve gerçekleşme sayfalaması | Diğer geçmiş ve tamamlayıcı API kapsamı |
| A12 | Başlanmadı | Diğer ürünler |

## Uygulama sınırları

Plan v2 artık ayrı V2Runner yoluna yönlendirilir. Çalışabilir ilk kapsam:
SINGLE piyasa/LIMIT girişi, kademeli hedef ve break-even; LONG/SHORT ve one-way/hedge.
V2 grid ayrı GridRunner yoluna yönlendirilir. Eski LONG watchdog
v2 oturumunu devralmaz; `plans manage SESSION_ID` kullanılır. Yeni yürütücü
bu turda gerçek demo emri gönderilerek doğrulanmadı; sahte borsa testleri geçti.

Portföy modeli hesap bakiyesinin doğrulanmış ortak para değerini gerektirir.
Multi-assets hesabında farklı varlıkların adetleri USDT gibi toplanmaz.
Yeni SINGLE yolu kullanılabilir USDT kaydı, teminat uygunluğu ve taze USDTUSD
endeksini ister; USD toplamını endeks/askRate'in büyüğüyle böler ve USDT
bakiyesiyle sınırlar. Diğer varlıkların bakiyeleri kapasiteye eklenmez.
Likidasyon modeli tahmindir; borsanın gerçek likidasyon fiyatı olarak sunulmaz.

`settings prepare/apply/reconcile` somut komut kimliğiyle çalışır. Geliştirme
sırasında bu komutlarla hesap değişikliği yapılmadı. Hesap çapındaki mod
değişimleri, diğer ürünlerin boşluğu doğrulanana kadar engellenir.

`OrderJournal` iç normalleştirilmiş gözlemlerle çalışır. Kullanıcı WebSocket
adaptörü normal/koşullu olayları REST uzlaştırmasına bağlar; olay mesajı tek
başına envantere dolum eklemez veya emir göndermez.
Kümülatif gerçekleşme azalmaz. Aynı olay tekrar işlendiğinde yeni envanter
oluşmaz. İptal sonrası geç gelen fill miktara eklenir; iptal edilen emir
yeniden açık hale gelmez. Bilinmeyen emir sahiplenilmez.

`GridShutdown` borsaya istek göndermez. Stop kaydı kalıcıdır, yeni alış
önerisini engeller. Bilinmeyen/açık emirler terminal hale gelmeden kalan
pozisyonu kapatma önerisi üretmez. Taze hesap verisi, sahiplik, emir defteri
ve pozisyon miktarı uyuşmadan CLOSED sonucu vermez.

Grid kodu somut, yetkili v2 planıyla demo emir gönderebilir. Bu geliştirmede
çalıştırılmadı; gerçek demo yazma doğrulaması henüz yoktur. Kullanıcının
200 USDT toplam nominal bütçesi, grid sayısı, stopu ve bağımsız risk sınırları
değiştirilmedi. Güncel akış ve sınırlar 08-GRID-YURUTME-VE-REZERVASYON.md içindedir.

## Doğrulama ve sonraki çalışma

`python -m unittest discover -s tests -q`: 372 test, başarılı.

Testler timeout ve kayıp yanıtta tek gönderim, 503 varyantları, kalıcı rate
limit, ayar komutlarında tekrar/restart/GET uzlaştırma, kaldıraçlı portföy
senaryoları, yön ve filtre kuralları, iptal–fill yarışı, olay tekrarı,
envanter ayrımı ve stop sonrası yeniden giriş engelini içerir. V2 testleri ayrıca
LONG/SHORT one-way/hedge, kayıp giriş/stop/iptal yanıtı, kısmi giriş/kapanış,
azaltıcı kapanış, koruma temizliği, anahtar/oturum içeriği uyuşmazlığı,
gönderim öncesi fiyat değişimi ve yetki iptali senaryolarını doğrular.

Sonraki testler LIMIT bekleme/süre sonu/stop iptali, LONG/SHORT kademeli
azaltma, kısmi hedef kalanı, kayıp hedef yanıtı, yeni stop doğrulanmadan eski
stopun korunması, hedge stop alanları, sonraki hedefte stop miktarını küçültme
ve sürekli izlemede belirsiz hatanın tekrar edilmemesini de kapsar.

`plans manage SESSION_ID --execute-demo --iterations 0 --interval 5` mevcut
v2 oturumunu kapanışa/kesmeye kadar izler. Yeni oturum kurmaz; onaylı grid
hücreleri için açıcı/yeniden alış emirleri üretebilir. Belirsiz hata
durumunda çıkıp kayıtları korur; koşulsuz yeniden POST yapan hata döngüsü yoktur.
Girişe stop seviyesi gerçek avgPrice üzerinden tick'e LONG için yukarı,
SHORT için aşağı yuvarlanır. Komisyonların telafi edildiği net başabaş fiyatı
olarak sunulmaz. Grid entegrasyonu çevrimdışı test edildi; gerçek demo
doğrulaması ve kalan aşamalar bitmiş değildir.

Kaynaklar: Binance resmi USD-M [hesap](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account),
[piyasa](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data)
ve [emir](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade)
belgeleri 6 Kasım 2026 tarihinde yeniden incelendi.

Sonraki çalışma sırası `data/development-progress.json` içindedir. Kısmi
paketler, yalnız doğrulayıcı veya çevrimdışı defter eklendiği için tamamlandı
sayılmaz. Bütün aşamalar tamamlanmış değildir.

Sonraki A4/A5 kapsamı, teminat belirsizlik politikası, yeni komutlar ve native
toplu iptal kanıtları 09-TEMINAT-VE-TOPLU-IPTAL.md içinde kayıtlıdır. Bu turda
gerçek hesap/demoda yazma isteği veya izleyici başlatma yapılmadı.

Native amend/toplu değiştirme/toplu oluşturma artık 10 numaralı dosyada belgeli.
İlk niyet değişmeden doğrulanmış revizyon kullanılır; miktar artırma ve grid
seviyelerini değiştirme reddedilir. Yeni yolların demo yazma kanıtı henüz yoktur.

## Geçmiş sayfalama güncellemesi

Yoğun gelir ve gerçekleşme geçmişi artık ortak, sınırlı ve eksik veride duran
okuyucularla toplanır. 386 test geçti. WebSocket bağlantısı henüz tamamlanmadı.
Ayrıntı: [11-GECMIS-SAYFALAMA-VE-UZLASTIRMA.md](../../../11-GECMIS-SAYFALAMA-VE-UZLASTIRMA.md).

## Kullanıcı WebSocket güncellemesi

430 test geçti. Gerçek demo bağlantısı, akış kaynağının oluşturulması/süre
yenilemesi ve ping/pong doğrulandı. Emir veya hesap ayarı değiştirilmedi.
Gerçek özel hesap olayı alınmadı; uçtan uca işlem olayı kanıtı bekliyor.
Ayrıntı: [12-KULLANICI-WEBSOCKET-VE-YENIDEN-UZLASTIRMA.md](../../../12-KULLANICI-WEBSOCKET-VE-YENIDEN-UZLASTIRMA.md).

## Takip stopu, yönetilen teminat ve servis teslimi

466 yerel/sahte borsa testi geçti. SINGLE takip stopu, miktar/stop geçiş
zinciri, etkin oturuma bağlı izole teminat komutu, güncel grid basamak kontrolü,
bildirim kuyruğu ve sürekli servis/sağlık/durdurma komutları eklendi.
Bu teslimde demo emri, hesap ayarı, Telegram mesajı veya otomatik görev başlatılmadı.
Sekiz aşamalı planın tamamı henüz bitmedi; kalan kapsam açıkça kayıtlıdır.
Ayrıntı: [13-TAKIP-STOP-TEMINAT-VE-SERVIS.md](../../../13-TAKIP-STOP-TEMINAT-VE-SERVIS.md).

## Çoklu oturum ve ortak risk teslimi

Aynı USD-M demo hesabında farklı sembollü SINGLE/grid oturumları ortak kalıcı
risk rezerviyle birlikte yönetilebilir. Aynı sembol iki plana bölünmez.
497 test geçti; gerçek demo çoklu işlem testi yapılmadı. Risk profili ve mevcut
bütçeler değiştirilmedi. Yeni komutlar: plans run-many/manage-all/reservations/
release-unused ve service run-all. Ayrıntı ve sınırlamalar:
[14-COKLU-OTURUM-VE-ORTAK-RISK.md](../../../14-COKLU-OTURUM-VE-ORTAK-RISK.md).


## Neutral grid teslimi — 6 Kasım 2026

Neutral grid kodu ve 44 yeni senaryo tamamlandı. Toplam 541 test geçti. Neutral gerçek demo yazma kanıtı bekliyor; tüm proje bitmiş değildir.

Ayrıntı: [15-NEUTRAL-GRID-VE-IKI-TARAFLI-YONETIM.md](../../../15-NEUTRAL-GRID-VE-IKI-TARAFLI-YONETIM.md).


## Aktif teminat teslimi — 6 Kasım 2026

Aktif çoklu oturum, yönlü grid ve neutral taraf teminat yönetimi tamamlandı. Toplam 560 test geçti; gerçek demo teminat değişikliği henüz doğrulanmadı.

Ayrıntı: [16-COKLU-OTURUM-TEMINAT-YONETIMI.md](../../../16-COKLU-OTURUM-TEMINAT-YONETIMI.md).


## Grid takip stopu — 7 Kasım 2026

Yönlü GRID için isteğe bağlı bot takip stopu eklendi. LONG/SHORT watermark ve eşik kalıcıdır; tetikte yeni girişler durur, gerçek kalan miktar kapanış akışına geçer. Native sabit stop korunur; hareketli eşik bot çalışırken izlenir. Neutral/native takip ve diğer politikalar bekliyor. 13 yeni senaryo dahil 573 test geçti; sonuç doğrulama raporuna kaydedildi. Gerçek demo yazma yapılmadı.

Ayrıntı: [17-GRID-TAKIP-STOPU.md](../../../17-GRID-TAKIP-STOPU.md). Kanıt: `reports/development-validation-20261107.json`.


## Grid borsa stopunu yenileme — 7 Kasım 2026

Yönlü GRID için isteğe bağlı `management.trailing.native_stop: true` eklendi. Yeni close-all stop GET ile doğrulanmadan önceki takip stopu kaldırılmaz; başlangıç sabit koruması tutulur. Eski planlar değişmez. 21 yeni senaryo eklendi; tam regresyon sonucu `reports/development-validation-20261107.json` içinde. Gerçek demo yazma kanıtı bekliyor.

Ayrıntı: [18-GRID-BORSA-STOP-YENILEME.md](../../../18-GRID-BORSA-STOP-YENILEME.md).
