# Binance demo yetenek envanteri ve geliştirme sırası

> 9 Kasım 2026: Bu belge A0–A12 işlem altyapısının tarihli envanteri ve teknik alt iş listesidir. Ana ürün sırası artık [02 — Kendi grafik terminali planı](02-ASAMALI-GELISTIRME-PLANI.md) içindeki W0–W9 programıdır. Kendi grafik/çizim altyapısı önceliklidir; aşağıdaki eski durum ve sıra ifadeleri o tarihin kaydıdır. Güncel uygulama durumu [07](07-GELISTIRME-DURUMU.md) içindedir.

Tarih: 6 Kasım 2026 · Durum: A0 ve A1 tamamlandı; A2 ve sonrası sırada · Hesap değiştiren işlem yapılmadı

## 6 Kasım 2026 tarihli geliştirme kaydı

Kullanıcı aşamalı planı onayladı. A1'in sürümlü yetenek kataloğu ve salt
okunur keşif sistemi uygulandı. `capabilities list` anahtar/ağ olmadan 95
operasyonu sunar. `capabilities probe --account` 12 sabit GET kontrolünü
çalıştırır; kayıtlar anahtar özeti, sembol, ortam ve zamana bağlı saklanır.
`capabilities latest --account` aynı anahtar için yerel kanıtı ağsız getirir;
eski kanıtı STALE işaretler. Başarılı GET, yazma yetkisi veya hazır strateji
anlamına gelmez. API izin listesi tek kaynaktan hesaplanır.

Demo denemesinde 12/12 okuma geçti. Account V3'te canTrade bulunmadığı
görüldü; alan yokluğu hata sayılmayacak şekilde düzeltildi. Ayrı resmî
accountConfig okuması eklendi. Adaptörün bu katalogla eşleşen yöntem/adres
sayısı artık 22. Önceki 21 sayısı A0 tarihli incelemeye aittir. 150 test geçti.
Yeni emir/iptal/kaldıraç/teminat/mod değişimi yapılmadı. A2 henüz başlamadı.

## 1 Yeni hedef

Bot, desteklenen demo işlemleri için genel bir işlem ve hesap yönetim altyapısına
dönüşecek. Tek LONG denemesine özel kod yerine, kullanılabilir yetenekleri bilen,
yetkiyi ve borsa kurallarını denetleyen, emirlerin sonucunu takip eden ortak bir
motor geliştirilecek. Grid bu motorun üzerindeki stratejilerden biri olacak.

Bu çalışma önce neyin mümkün olduğunu ve neyin eksik olduğunu listeler.
Listedeki bir işlevin varlığı, o işlevin geliştirilmiş veya kullanıcı hesabında
çalıştırılarak doğrulanmış olduğu anlamına gelmez. Henüz uygulanmamış işlemler
tamamlanmış gibi sunulmayacak.

## 2 API key ve secret hangi yetkiyi verir

API key hesabı ve izinleri tanımlar; secret HMAC imzalama içindir. Yetki;
demo ürününün desteği, hesabın uygunluğu, anahtar izinleri, sembol kuralları,
uygulamanın yetenekleri ve kullanıcı yetkisinin kesişimidir. Secret'ın bulunması
Binance sitesindeki her düğmeye veya bütün ürünlere erişim sağlamaz.

Public piyasa verilerinin bir kısmı anahtarsızdır. Özel hesap verisi ve emirler
ayrı yetkiler ister. Kullanıcı akışı oluşturmak ile imzalı emir göndermek de
aynı güvenlik türü değildir. Bunlar adaptörde ayrı tanımlanacak.

Resmî USD-M genel bilgi sayfası uç noktaların **çoğunun** demo ortamında
kullanılabildiğini söyler; hepsinin çalıştığını garanti etmez. Bu nedenle
her yetenek için demo ve hesap doğrulaması ayrıca tutulacak. [B1]

## 3 Ürün kapsamı

| Ürün veya alan | Bu çalışmadaki durum | İzlenecek yol |
|---|---|---|
| USDⓈ-M Futures demo | Ana kapsam; mevcut bot burada çalışıyor | Önce tam işlem ve koruma altyapısı |
| Spot Demo | Ayrı resmî demo ürünü var | Ayrı adaptör, bakiye, filtre ve emir modeli; mevcut Futures anahtarının erişimi varsayılmayacak [B7] |
| COIN-M | Ayrı sözleşme/teminat hesabı ve güncel mimari geçiş koşulları var | Güncel entegrasyon ve demo uyumluluğu doğrulandıktan sonra ayrı kapsam [B8] |
| Portfolio Margin | USD-M kataloğunda koşullu hesap görünümü var | Demo ve hesap erişimi kanıtlanmadan destekleniyor sayılmayacak |
| Futures Convert | Belgelenmiş dönüşüm işlemleri var | Demo uygunluğu ve varlık kapsamı ayrıca sınanacak |
| Native grid, DCA veya TWAP arayüzleri | Borsa ekranında bulunmaları mevcut anahtarla API erişimini kanıtlamaz | Resmî API varsa ayrı ürün olarak doğrula; yoksa desteklenen temel emirlerle bot stratejisi geliştir |
| Sanal bakiye sıfırlama veya yükleme | Bu incelemede belgelenmiş genel API doğrulanmadı | Tarayıcı içi özel API'ler kullanılmayacak |
| Gerçek para çekme/yatırma, Earn, staking, P2P, copy trading, options | Mevcut Futures demo anahtarının genel yetkisi sayılmaz | İlgili ürüne ait açık belge, demo ve izin kanıtı olmadan kapsam dışında |

İlk teslim, bütün Binance ürünlerinin tamamlandığı iddiası taşımayacak.
USD-M tamamlanma durumu ile Spot/COIN-M genişleme durumu ayrı raporlanacak.

## 4 Envanter sonucu

İncelenen güncel USD-M REST kataloğunda 95 operasyon başlığı sayıldı:

| Kategori | Operasyon sayısı | Ne içerir |
|---|---:|---|
| Hesap | 21 | Bakiye, yapılandırma, komisyon, izin/kısıt, indirme ve risk bilgileri |
| İşlem | 32 | Oluşturma, değiştirme, iptal, kaldıraç, teminat, pozisyon ve geçmiş |
| Piyasa verisi | 34 | Fiyatlar, mumlar, emir defteri, funding ve türev istatistikleri |
| Kullanıcı akışı oturumu | 3 | Akış açma, canlı tutma ve kapatma |
| Convert | 4 | Çiftler, teklif, kabul ve sonuç |
| Portföy marjı görünümü | 1 | Koşullu hesap görünümü |

Bu 95 başlık; 95 aktif demo yetkisi, 95 strateji veya 95 hazır bot komutu
demek değildir. REST dışında WebSocket piyasa/hesap akışları ve WebSocket
API taşıması ayrıca geliştirme kapsamındadır. [B2] [B3] [B4] [B5]

Tam satır listesi: `reports/binance-demo-api-islem-listesi-20261106.md`.
Makine tarafından kullanılabilir kayıt: `reports/binance-demo-capabilities-20261106.json`.
Her satırda kaynak, referans adres, adaptör izni ve demo doğrulama durumu vardır.
95 başlığın A0 incelemesinde 21'i demo adaptörünün izin verdiği yöntem/adreslerle eşleşiyordu;
A1 accountConfig okumasıyla güncel sayı 22'dir.
Bu sayı 21 tamamlanmış iş akışı anlamına gelmez. Bazı piyasa okuma işlevleri
ayrı canlı public adaptörde vardır; demo adaptörüyle karıştırılmamıştır.

Katalogdaki referans yollar uygulamadan önce güncel belgeyle tekrar kontrol
edilecek. Makine şemasını indirme girişimi boş yanıt verdiği için bu dosya
'OpenAPI şemasından eksiksiz otomatik çıkarım' olarak sunulmuyor; resmî
navigasyon başlıklarıyla karşılaştırılmış bir araştırma envanteridir.

## 5 Bot üzerinden sunulacak temel işlevler

### Hesap ve yapılandırma

1. Bakiye, kullanılabilir teminat, başlangıç/bakım marjı ve gerçekleşmemiş sonuç.
2. Pozisyonları, emirleri ve kullanıcı gerçekleşmelerini listeleme.
3. Sembol filtreleri, minimum tutar, fiyat/miktar adımları ve sözleşme durumu.
4. Kullanıcı komisyonları, funding ve gerçekleşmiş net sonuç raporu.
5. Mevcut kaldıraç, teminat ve pozisyon modunu okuma.
6. Desteklenen kaldıraç basamağında ayar yapma ve geri okuyarak doğrulama.
7. CROSSED/ISOLATED seçimi; değişimin mevcut pozisyona etkisini denetleme.
8. İzole teminata ekleme/azaltma ve değişim geçmişi.
9. One-way/hedge seçimi; hesap çapındaki etkiler ve açık emir/pozisyon engelleri.
10. Single-asset/multi-assets durumu ve hesabın desteklediği ölçüde değişimi.
11. Komisyon indirimi tercihleri ve hesap işlem kısıtları.

### Normal emirler ve pozisyon

12. LIMIT ve MARKET alış/satış.
13. LONG açma, azaltma ve kapatma.
14. SHORT açma, azaltma ve kapatma.
15. One-way ve hedge için ayrı positionSide kuralları.
16. Desteklenen kombinasyonlarda GTC, IOC, FOK, GTX ve GTD.
17. Normal emri kimlikle sorgulama; kabul ile gerçekleşmeyi ayırma.
18. Tek, seçili toplu ve sembol kapsamındaki normal emirleri iptal etme.
19. Limit emrin fiyat/miktarını değiştirme; iptal-yeni emir yarışını yönetme.
20. Toplu oluşturma ve değiştirmede her alt emrin sonucunu ayrı değerlendirme.
21. Süreli otomatik normal emir iptali ve iptal zamanlayıcısını izleme.
22. Emir doğrulama endpointiyle gerçek emir açmadan biçim kontrolü.
23. Price-match, self-trade prevention ve daha özel seçeneklerin yetenek matrisi.
24. Kısmi gerçekleşme, kalan iptali, geç gelen fill ve gerçekleşme toplamı takibi.

Her seçenek her emir türü veya hesap moduyla kullanılamaz. Örneğin belgelenmiş
normal emir değiştirme LIMIT kapsamındadır; hedge'de reduceOnly parametresinin
kullanımı one-way ile aynı kabul edilmez. İzinli kombinasyonlar ayrı test edilir.
[B2]

### Koruyucu ve koşullu emirler

25. STOP ve STOP_MARKET.
26. TAKE_PROFIT ve TAKE_PROFIT_MARKET.
27. Desteklenen koşullarla TRAILING_STOP_MARKET.
28. Mark fiyatı ile işlem fiyatı tetikleyicilerinin ayrı seçimi.
29. Desteklenen kombinasyonlarda price protection, close-all ve miktarlı reduce-only.
30. Koşullu emir oluşturma, sorgulama, iptal ve geçmiş inceleme.
31. Stop/TP değiştirme gerektiğinde güvenli yerine koyma; her türde doğrudan amend varsaymama.
32. Kademeli kâr alma, girişe stop taşıma ve onaylı takip eden stop politikası.
33. Bir çıkış gerçekleşince artık geçersiz kardeş emirlerin temizlenmesi.
34. Acil çıkış, yeni girişleri durdurma ve korumayı sürdürme için ayrı komutlar.

OCO benzeri davranış, ilgili ürünün doğrudan atomik desteği doğrulanmadan
'borsada atomik OCO var' diye sunulmaz. Bot tarafından eşlenen emirlerde
eşzamanlı tetiklenme ve iptal yarışı ayrıca ele alınır.

### Veri ve olay takibi

35. İşlem, mark, endeks, premium ve sürekli sözleşme mumları.
36. Son fiyat, en iyi alış/satış, derinlik ve piyasa işlemleri.
37. Funding, açık pozisyon, long/short ve taker baskısı istatistikleri.
38. ADL, zorunlu kapatma ve ilgili risk göstergeleri.
39. Kullanıcı akışından emir, gerçekleşme, bakiye ve yapılandırma olayları.
40. Piyasa akışı, bağlantı yenileme, eksik olay tespiti ve REST ile uzlaştırma.
41. Hesap/emir/gerçekleşme geçmişi, dışa aktarma ve masraflı sonuç raporu.

### Botun geliştireceği stratejiler

42. Aritmetik LONG grid; ilk uygulama önceliği.
43. Geometrik LONG grid.
44. SHORT ve neutral grid; yön ve hesap modu desteğinden sonra.
45. Sınırlı kademeli alım veya DCA; ayrı risk ve tekrar giriş yetkisiyle.
46. Koşula bağlı giriş, Fibonacci planı ve kademeli çıkış.
47. Gerekirse zamanla bölünmüş emir; native TWAP desteğiyle bot emülasyonunu ayırma.
48. Grid durdurma, iptal etme, mevcut envanteri koruyarak durma veya açıkça kapatma.

Strateji modülleri aynı emir/risk/yetki çekirdeğini kullanacak. Bir grid,
sekiz tek seferlik kâr hedefiyle eşdeğer değildir: envanter ve yeniden alım
döngüsü, bekleyen emir rezervi, kısmi fill ve iptal sırası yönetir.

## 6 Bugünkü yazılım eksikleri

| Kimlik | Sorun veya eksik | Yapılacak düzeltme | Öncelik |
|---|---|---|---|
| G01 | API adresinin açık olması iş akışının tamamlanması sanılabiliyor | Yetenek kayıt sistemi ve dört ayrı doğrulama seviyesi | P0 |
| G02 | Demo desteği ve hesap izni ayrı kaydedilmiyor | Salt okunur keşif ve sonrasında kontrollü senaryo kanıtı | P0 |
| G03 | Limit başlıkları ve Retry-After için ortak zamanlayıcı eksik | İstek ağırlığı, geri çekilme ve öncelikli koruma kuyruğu | P0 |
| G04 | Emirler dışındaki ayar değişimleri için kalıcı komut modeli eksik | Kaldıraç/teminat/mod değişimi ve geri okuma kaydı | P0 |
| G05 | Risk modeli ilk küçük, kaldıraçsız nominal deneyine göre dar | Nominal, teminat, rezerv, stop kaybı ve likidasyon denetimini ayır | P1 |
| G06 | Eski demo sınırları yeni strateji isteğiyle karışıyor | Global korumalar ve sürüme bağlı strateji risk profili | P1 |
| G07 | Plan v1 artırma/yeniden giriş/SHORT/hedge kabul etmiyor | Geriye uyumlu plan v2 ve açık destek matrisi | P1 |
| G08 | Normal emir amend, toplu işlem ve ayrıntılı seçenekler yok | Ortak yaşam döngüsüne ekle; alt sonuçları ayrı sakla | P1 |
| G09 | LONG dışı yön ve hedge sahipliği yok | Ürün/sembol/positionSide bazında envanter ve risk | P1 |
| G10 | Bazı koruma davranışları yalnız çevrimdışı doğrulandı | Borsa gerçekleşmeleriyle uçtan uca senaryolar | P1 |
| G11 | Sürekli kullanıcı/piyasa WebSocket katmanı yok | Olay işleme, tekrar/sıra/bağlantı kopma yönetimi | P1 |
| G12 | GridLedger yalnızca çevrimdışı teklif ve kayıt defteri | Gerçek grid yürütücüsü ve portföy uzlaştırması | P1 |
| G13 | Grid stop sonrası bekleyen alışlar yeniden pozisyon açabilir | Yeni giriş kilidi, terminal iptal ve geç fill kapatma politikası | P1 |
| G14 | Tüm bakiye ve veri yaşı girişlerde ortak denetlenmiyor | Ortak güncel hesap görünümü ve emir öncesi kontrol | P1 |
| G15 | Sürekli servis, bildirim ve sağlık görünürlüğü eksik | Otomatik başlangıç, durum ve kesinti bildirimi | P2 |
| G16 | Telegram üzerinden gerçek kullanıcı onayı yok | Kimlik denetimli, sürüme bağlı, tekrar önleyen onay | P2 |
| G17 | Çıkış sonrası net sonuç ve geçmiş raporu dağınık | Fill/komisyon/funding/gerçekleşen sonuç birleştirme | P2 |
| G18 | Spot/COIN-M farklılıkları soyutlanmadı | Ayrı ürün adaptörleri; miktar, teminat ve sembol modeli | P3 |
| G19 | Native ürün ile bot stratejisi ayrımı görünür değil | UI/API/strateji desteğini ayrı ilan et | P0 |
| G20 | Eski plan dosyalarında güncelliğini kaybetmiş durum cümleleri var | Tarihli durum kaynağı ve kanıt bağlantılarını esas al | P0 |

Bu liste görülen açık eksiklerin envanteridir; yazılımda başka hata olmadığı
garantisi değildir. Her geliştirme yeni hata senaryoları ve kabul ölçütleriyle
doğrulanacaktır.

## 7 Doğrulama seviyeleri

Her özellik aşağıdaki seviyelerde ayrı ayrı işaretlenecek:

1. **Belgeli:** Güncel resmî API'de tanımlanmış.
2. **Adaptör:** İstek, şema, sayı hassasiyeti ve hata modeli kodlanmış.
3. **Çevrimdışı:** Olumlu/olumsuz ve kesinti testleri geçmiş.
4. **Demo doğrulandı:** İlgili hesap ve sembolde kontrollü senaryo kanıtı var.
5. **Ürün akışı hazır:** Yetki, risk, kayıt, kullanıcı komutu ve izleme birlikte çalışıyor.

Ek durumlar: `DEMO_DESTEGI_BELIRSIZ`, `IZIN_EKSIK`, `FILTE_ENGELI`,
`RISK_ENGELI`, `HESAP_ONKOSULU`, `YAZILIM_EKSIK`, `EMIR_SONUCU_BELIRSIZ`.
Böylece bir minimum tutar hatası yazılım arızasıyla, anahtar izni eksikliği de
API'nin hiç bulunmamasıyla karıştırılmayacak. Bilinen API hataları bütün borsa
hatalarını otomatik tekrar eden bir döngüye sokmayacak. [B1]

## 8 Geliştirme ve teslim sırası

| Paket | Kapsam | Geçiş koşulu |
|---|---|---|
| A0 | Bu yetenek envanteri ve kaynak/sürüm kaydı | 95 REST başlığı, stratejiler ve ürün sınırları ayrı listeli |
| A1 | Yetenek keşfi, sürümlü kayıt ve salt okunur hesap araçları | Her komutta ortam/ürün/izin/önkoşul sonucu |
| A2 | Ortak istek ve dayanıklılık katmanı | Hata, timeout, istek limiti ve belirsiz sonuç senaryoları |
| A3 | Plan v2 ve kaldıraçlı portföy risk modeli | Nominal/teminat/kayıp ayrımı; pending emir rezervi; açık yetki kapsamı |
| A4 | Kaldıraç, teminat ve hesap modu yönetimi | Değişim geri okunur; başarısızlıkta işlem açılmaz |
| A5 | Normal emir ailesi, LONG/SHORT ve amend/toplu işlemler | Tam/kısmi fill, iptal yarışı, tekrar ve restart kanıtı |
| A6 | Koşullu emirler ve koruma paketi | Stop/TP/trailing ve temiz kapanış; miktar/positionSide uyumu |
| A7 | Kullanıcı/piyasa olay akışı ve uzlaştırma | Kaçan/tekrarlı/sırası bozuk olaylar doğru sonuçlanır |
| A8 | Gerçek LONG grid yürütücüsü | Başlangıç → fill → karşı emir → tekrar alım → stop/temizleme → restart |
| A9 | Gelişmiş grid ve planlar | Geometrik/SHORT/neutral yalnız desteklenen modlarda çalışır |
| A10 | Kullanıcı komutları, bildirim ve servis | Durum ve hata görünür; kimlik denetimi ve sürekli çalışma |
| A11 | Tamamlayıcı hesap/geçmiş/veri ve koşullu ürünler | Her desteklenen operasyon kanıtlanır veya gerekçeli erişilemez işaretlenir |
| A12 | Spot, COIN-M ve diğer doğrulanmış demo ürünleri | Ürün başına ayrı adaptör/filtre/risk ve test matrisi |

Bu sırada A3–A7'nin grid için gerekli alt bölümleri önce bitirilir. Bütün
geçmiş indirme ve nadir veri uçlarının bitmesi gridin ilk teslimini bekletmez.
Ancak risk, koruma, sahiplik ve iptal güvenliği atlanarak grid etkinleştirilmez.

## 9 Grid için kesin tamamlanma ölçütleri

- Başlangıç envanteri ile bekleyen alışların toplam bütçesi onaylı sınırdadır.
- Stop ve hedef tutarları gerçek gerçekleşmiş miktardan hesaplanır.
- Her hücrenin alış/azaltıcı satış döngüsü ayrı kimliklidir; çift satış veya açığa dönüş yoktur.
- Kısmi fill, kalan iptali ve geç gelen fill envanterde doğru görünür.
- Stop tetiklendiğinde önce yeni alış üretimi kesilir; bekleyen alışlar iptal edilir ve terminal durum okunur.
- İptal sırasında gerçekleşen alım varsa yeniden açık kalan miktar tanımlı çıkış politikasıyla kapatılır.
- Pozisyon kapandıktan sonra eski grid emri yeniden giriş açmaz.
- Ağ kesintisinde borsa korumasının ne yaptığı ve yerel takibin neyi yapamadığı raporlanır.
- Yeniden başlatılan süreç aynı emirleri/pozisyonu devralır; kayıp yanıtı yeni POST ile tekrar etmez.
- Manuel veya başka bota ait işlem görünürse sahiplik otomatik varsayılmaz.
- Bütçe, kaldıraç, teminat modu, miktar adımı ve minimum tutar açıkça raporlanır.
- Bant içinde stop kullanılacaksa alt alışların iptal politikası test edilir; bu kullanıcının son isteğinde özellikle gereklidir.

Güncel kullanıcı örneği 73000–78000, 4 aralık ve 74000 stop içerir. Bu bir
regresyon senaryosudur. 200 USDT nominal bütçenin minimum emirlerle uyuşmaması
ayrı parametre engelidir; yazılım borsa minimumlarını ortadan kaldıramaz.
Bu envanter çalışması o işlemi açma veya bütçeyi yükseltme yetkisi değildir.

## 10 Yapılmayacak yanlış kısayollar

API izin listesi bütün yolları kabul edecek şekilde açılmayacak. Her yeni
yetenek yöntem, yol, parametre ve kapsam denetimiyle eklenecek. Hesap modları
uygunluğu doğrulanmadan değiştirilmez. Test emir endpointinin başarılı olması
emrin gerçek demo defterinde dolduğunu veya korumanın çalıştığını kanıtlamaz.

GET olmak işlemin tamamen etkisiz olduğu anlamına gelmeyebilir: geçmiş
indirme görevi başlatan işlemler ve kaynak tüketen uçlar ayrı ele alınır.
API key/secret rapora veya bir genel HTTP aracına aktarılmaz. Gerçek hesap
adreslerine veya para çekme kapsamına otomatik genişleme yapılmaz.

Demo borsasına yeni emir gönderen testler rastgele fiyat/miktarla otomatik
çalıştırılmayacak. Önce çevrimdışı ve read-only kontroller; sonra mevcut
kullanıcı yetkisinin kapsadığı somut demo senaryoları kullanılacak.

## 11 Kaynaklar ve inceleme sınırı

- [B1] https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info
- [B2] https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade
- [B3] https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account
- [B4] https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data
- [B5] https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/user-data-streams
- [B6] https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/websocket-api-general-info
- [B7] https://developers.binance.com/en/docs/products/spot/demo-mode/general-info
- [B8] https://developers.binance.com/en/docs/products/derivatives-trading-coin-futures/Important-CM-UM-Integration-Notice
- [B9] https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/convert

Yerel inceleme: exchange.py, plans.py, execution.py, risk.py, watchdog.py,
grid.py, grid_cli.py, market_data.py, doğrulama ve önceki plan dosyaları.
Son tamamlanan test koşusu 134 testtir; bu araştırmada üretim kodu
değiştirilmediği için testler tekrar çalıştırılmadı. Katalog üretim betiği
95 benzersiz kimlik ve kategori sayılarını denetleyerek çalıştırıldı.

İncelemede hesap sorgusu, emir gönderimi, emir iptali, kaldıraç/teminat/mod
değişimi veya izleyici müdahalesi yapılmadı. Bütün yeni operasyonların bu
anahtarla demo üzerinde çalıştığı iddiası yoktur. İlk uygulama paketi A1'dir;
ilgili yetenekler doğrulanmadan sonraki paketler tamamlandı sayılmaz.

## 12 Güncel uygulama kaydı

6 Kasım 2026 sonraki geliştirmesinde A2 ortak istek katmanı uygulandı.
A3–A8 için çevrimdışı risk/plan v2, kalıcı ayar komutları, emir doğrulama,
gerçekleşme defteri ve grid durdurma bariyeri eklendi. 218 test geçti;
ortak transport üzerinden 12/12 salt okunur demo kontrolü doğrulandı.
Bu geliştirme grubunda emir veya hesap ayarı değiştirilmedi.
Paketlerin kalan işleri ve yürütme sınırları 07-GELISTIRME-DURUMU.md ve
data/development-progress.json içinde kayıtlıdır. Gerçek grid yürütme
kapalı; A3–A8 kısmi, A9–A12 henüz başlanmadı. Aşama geçişlerinde kullanıcıdan
yeniden geliştirme onayı istenmeyecek.

Sonraki uygulama kaydı: 249 test başarılı. A3 taze boş hesap görünümü ve
USDT teminatla sınırlı multi-assets değerlemesiyle SINGLE yürütücüye bağlandı.
A5/A6 için LONG/SHORT, one-way/hedge piyasa girişi, tek stop/son hedef,
kayıp yanıt uzlaştırması ve yeniden başlatma uygulandı. Yeni v2 yürütücüsü
gerçek demo emriyle henüz doğrulanmadı; sahte borsa senaryoları geçti.
USDTUSD demo endeksi salt okunur doğrulandı; boş hesap ön kontrolü mevcut
pozisyon/emir nedeniyle engellendi. Grid/LIMIT/kademeli hedef ve genel
portföy rezervasyonu tamamlanmış değildir. Güncel kanıtlar 07 dosyasındadır.
