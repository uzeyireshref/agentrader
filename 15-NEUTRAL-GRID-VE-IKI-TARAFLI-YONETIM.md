# Neutral grid ve iki taraflı yönetim

> 9 Kasım 2026 plan notu: Bu belge tarihli işlem alt sistemi teslimini ve kanıtlarını korur. Burada geçen TradingView zinciri yeni geliştirme hedefi değildir; yerine kendi grafik/çizim → strateji → onay → işlem yolu geçmiştir. Güncel ürün sırası [02](02-ASAMALI-GELISTIRME-PLANI.md), geçiş tasarımı [19](19-KENDI-GRAFIK-TERMINALI-VE-GECIS.md) içindedir.

6 Kasım 2026. Durum: uygulandı ve çevrimdışı/sahte borsa testleri geçti.
Gerçek Binance demo emirleriyle doğrulama bekliyor. Bu kayıt yeni işlem yetkisi değildir.

## İşleyiş

Neutral grid, `neutral-v2` yürütücüsünde tek üst plan, tek oturum ve tek toplam
bütçeyle çalışır. Alt bölgede LONG, üst bölgede SHORT hücreleri bulunur.
`long_fraction` ve `short_fraction` pozitif olmalı ve toplamları 1 etmelidir.
İki tarafın bütçesi ayrıca toplam bütçeye eklenmez. NOTIONAL, MARGIN ve MAX_LOSS
hesapları desteklenir; iki tarafın birleşik kaybı işlem kayıp sınırına tabidir.

Plan `strategy: NEUTRAL_GRID`, `direction: NEUTRAL` kullanır. Hedge hesap modu
zorunludur; bot hesap modunu kendiliğinden değiştirmez. Grid alanları:
`lower`, `upper`, `intervals`, `spacing`, `anchor_price`, `long_fraction`,
`short_fraction`. Başlangıç kapsamı 2–20 aralık; ARITHMETIC veya GEOMETRIC.
İç anchor, hesaplanan bir grid seviyesine ve giriş referans fiyatına eşit olmalıdır.
`stop: {lower, upper}` gridin iki dışında zorunludur; `targets: []` kullanılır.

Başlangıçta piyasa emriyle pozisyon kurulmaz. Güncel fiyatın altındaki LONG BUY
ve üstündeki SHORT SELL limit emirleri kullanılır. Gerçekleşen miktar komşu
hücrede kâr alma emrine dönüşür. Kısmi gerçekleşmede kalan açılış emri önce
iptal edilip terminal durumu doğrulanır. Yeni döngü risk ve yetki kontrolünden geçer.

## Sahiplik, koruma ve kesinti

LONG ve SHORT envanteri ayrı izlenir. Net pozisyon sıfır olsa da brüt risk sıfır
sayılmaz. Rezerv iki pozisyon olarak değerlendirilir; varsayılan risk sınırları
artırılmadı. Mevcut `max_positions: 1` profili neutral başlangıcına izin vermez.
Sembol başka oturuma ait olamaz; diğer sembollerdeki oturumlar ortak riske dahildir.

Her açık taraf için borsa üzerinde closePosition stop ve karşı sınırda kapanış
koruması kurulur. Global sınır tetiklenince iki tarafın normal emirleri iptal
edilir; gerçek kalan miktarlar ayrı kapatılır. Koruma alt emri ve belirsiz yanıt
uzlaştırılmadan aynı emir tekrar gönderilmez. Flat tarafın eski korumaları
emekli edilmeden önce açık tarafın korumaları kontrol edilir.

Kâr alma emri botun kendi bekleyen açılışıyla çakışıyorsa önce açılış iptal
edilip borsadan doğrulanır. Limit emirleri ayrıca EXPIRE_BOTH STP kullanır.
Belirsiz POST/DELETE otomatik tekrarlanmaz; kalıcı istemci kimliğiyle sorgulanır.
Süreç yeniden başladığında kayıtlar ve borsa envanteri uzlaştırılır.

DRAINING yeni açılışları durdurur; mevcut pozisyonun koruma ve azaltma yönetimi
sürer. STOPPING iki tarafın temiz kapanışını hedefler. Servisi durdurmak açık
pozisyonların otomatik kapatıldığı anlamına gelmez.

## Kullanım ve kapsam sınırı

`python -m agentrader plans neutral-example --amount 200` açık miktarla örnek
plan üretir. Örnek, işlem onayı değildir. 200 USDT nominal tutar hücre başına
borsa minimumunu karşılamayabilir; bot bunu gidermek için bütçeyi artırmaz.
Mevcut plan ön kontrolü, yetkilendirme ve çalıştırma akışı kullanılır.
`plans stop-neutral` neutral durdurma yolunu sunar; `manage-all` ve `service run-all`
aynı yürütücüyü destekler. Anahtarların veya hesap risk profilinin değiştirilmesi gerekmez.

Bu ilk neutral sürümde native amend/toplu oluşturma, takip eden stop ve aktif
izole teminat yönetimi desteklenmez. Uzun süreli gerçek demo kesinti/dolum
kanıtı, diğer gelişmiş politikalar, çapraz ürün portföyü, uzaktan onay,
Spot/COIN-M ve TradingView ürün zinciri kalan kapsamdır. Geliştirme onayı bu
işler için sürer; yeni demo işlemleri ayrı, geçerli miktar/risk yetkisi gerektirir.

## Doğrulama

Tam regresyon: 541 test geçti; 44 neutral senaryosu dahil. Birleşik bütçe,
asimetrik/geometrik grid, kısmi fill, iki brüt tarafın stopu, yeniden başlatma,
kayıp yanıt, iptal sırasında dolum, koruma alt emri, servis durdurma ve başka
sembollü oturumla sahiplik kontrolü sahte borsada sınandı.
Kanıt: `reports/development-validation-20261106.json`.
Bu turda gerçek demo emri, hesap ayarı değişikliği veya Telegram mesajı gönderilmedi.

Emir alanlarının birincil kaynağı: [Binance USD-M emir belgeleri](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade).


Güncelleme: Aktif neutral izole teminat entegrasyonu sonraki teslimde eklendi.
Bkz. [16-COKLU-OTURUM-TEMINAT-YONETIMI.md](16-COKLU-OTURUM-TEMINAT-YONETIMI.md). Gerçek demo kanıtı bekliyor.
