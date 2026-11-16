# Uygulama ilerlemesi

15 Kasım 2026. Kullanıcı araştırmaya dayalı planın uygulanmasını yetkilendirdi. Plan: [PLAN.md](PLAN.md).

| Paket | Durum | Kanıt / sınır |
|---|---|---|
| G00 | Plan ve kayıt teslim edildi | F01–F34 bulgularını kapsayan bağımlılık/uyumluluk/kabul planı |
| G01 | YEREL_KABUL_GECTI | Normal V2 SINGLE girişinde ACK/RESULT tercihi. 1271 test geçti. Borsa kabulü yapılmadı |
| G02 | YEREL_KABUL_GECTI | V2 ve mevcut batch/amend yollarında güncel kurallar ve gönderim kontrolü. 1289 test geçti |
| G03 | YEREL_KABUL_GECTI | Genel CLI, üç doğrudan işlem ve yetkili V1 plan journal köprüsü. 1325 test geçti. [Ayrıntılar](G03.md) |
| G04 | YEREL_KABUL_GECTI | SINGLE LIMIT süre/priceMatch/STP, RUN_SINGLE_PLAN genel komutu ve terminal kalan risk payı. 1343 test geçti. [Ayrıntılar](G04.md) |
| G05 | YEREL_KABUL_GECTI | Sahip olunan SINGLE pozisyonunda native trailing create/query/cancel, alt emir muhasebesi ve kurtarma. 1369 test geçti. [Ayrıntılar](G05.md) |
| G06 | YEREL_KABUL_GECTI | Sahip olunan V2 SINGLE pozisyonunda artır/azalt/kapat/ters yöne geçir; bağımsız ek risk ve iki bacaklı yetki. 1397 test geçti. [Ayrıntılar](G06.md) |
| G07–G23 | Bekliyor | Bağımlılıklar ve ürün sözleşme kapıları PLAN.md içinde |

## G01 kullanım

V2 SINGLE planının mevcut entry alanlarına şu isteğe bağlı alan eklenir:

```json
{
  "order_response_type": "RESULT"
}
```

Bu parça bütün plan dosyası değildir. `entry.condition`, fiyat ve diğer mevcut alanlar korunur. Değer ACK veya RESULT olabilir. Alan verilmezse eski davranış ve istek gövdesi korunur.

Normal kullanım mevcut `python -m agentrader plans create plan.json`, `plans show PLAN_ID VERSION`, `plans preflight plan.json` ve yetkili `plans run` zinciridir. Bu teslim grafik arayüzüne yeni seçim kutusu eklemez. GRID/NEUTRAL için tercih desteklenmez, sessizce yok sayılmaz.

## Değişen davranış

Plan doğrulayıcı alanı kabul eder. Preflight `newOrderRespType` olarak çevirir. Runner plan kapsam karşılaştırmasına dahil eder. Kalıcı niyet, onay digest'i ve restart sırasında aynı değer korunur. Yerel order validator normal/algo tekliflerinde ACK/RESULT alanını tanır. Tam native algo kullanıcı komutu bu paketin teslimi değildir.

Minimal ACK yanıtında dolum varsayılmaz. RESULT da bir emrin kesin dolduğu anlamına gelmez. Son durum orijinal kimlikle sorgulanır. Yanıt kaybı ve restart yeni POST üretmez. Migration gerekmedi, eski planlar değiştirilmedi.

## Yerel kabul

- CLI create/show: tercih izole veritabanında görünür.
- Şema: eski plan değişmez, yanlış enum ve GRID kullanımı reddedilir.
- Preflight: market/limit tercihi taşır, risk ve koruma çıktısı aynı kalır.
- Runner: minimal ACK, kaybolan RESULT yanıtı ve restart, bekleyen LIMIT, kayıtlı tercihin değiştirilmesine ret.
- Hedefli şema, CLI, preflight, validator ve runner testleri geçti.
- Tam regresyon: `python -m unittest discover -s tests` → **1271 test, 124.988 saniye, OK**. Önceki 1262 vakaya 9 yeni anlamlı vaka eklendi.
- Testler izole yerel exchange fixtureları ve geçici veritabanları kullanıyor. Borsa üzerinde ACK/RESULT yürütme kabulü bu sonuçtan türetilmiyor.

G01, F03 bulgusunun yanıt tercihi alt maddesini kapatır. IOC/FOK/GTX/GTD, priceMatch ve STP'nin genel kullanıcı girişi G04 kapsamında kalır. Eski araştırma raporları tarihsel kanıttır, bu değişiklikle topluca başarılı olarak işaretlenmedi.

Makine tarafından okunabilir paket bağımlılıkları `packages.json`, kod/test hashleri ve doğrulama sonucu `reports/exchange-development-20261115/g01-validation.json` içindedir.

## G02 teslimi — 16 Kasım 2026

[G02 ayrıntıları](G02.md): callback 0.1–20, yönlü PERCENT_PRICE bandı, doğru MARK_PRICE/CONTRACT_PRICE referansı, zaten tetiklenmiş koşullu emir reddi, filtre yapısı/risk kontrolü ve toplam/algo emir kapasitesi uygulandı. SINGLE/GRID/NEUTRAL gönderim, native batch ve normal amend yollarına taze veri kontrolü bağlandı. Gönderim öncesi okuma hatası NOT_SENT olarak ayrılıyor.

Son tam regresyon: **1289 test, 103.395 saniye, OK**. Kayıtlı public veri üzerinde **527 sembolde 32674 vaka uyumlu**, ek **1054 hatalı fiyat/tetik örneği reddedildi**. SXPUSDT için 62 vaka veri uyuşmazlığından çalıştırılmadı. Borsa kabulü yapılmadı. İlk tam koşudaki tek seferlik chart DB değişmezliği hatası, ayrı test grubunda ve sonraki iki tam koşuda tekrarlanmadı; çalışma geçmişi doğrulama kaydında korunuyor.

Sonuç ve hashler `reports/exchange-development-20261115/g02-validation.json` içinde. Tarihsel araştırma raporları değiştirilmedi. V1/legacy yolların ortak komut sistemine aktarılması G03'te, native trailing kullanıcı komutu G05'te kalıyor.

## G03 uygulaması — 16 Kasım 2026

Stratejiden bağımsız `commands context/prepare/show/apply/reconcile/cancel` yolu eklendi. İlk işlemler GET_MARK_PRICE, QUERY_ORDER ve mevcut güvenli ayar servisine bağlı SET_LEVERAGE. Aynı istemci kimliğinde parametre değişikliği reddedilir; kayıtlar ve ayar alt niyeti atomik hazırlanır. Yeni 26 test geçti. Son tam regresyon **1315 test, 112.664 saniye, OK**. İlk koşudaki grafik kanıtı uyuşmazlığı, değişen CLI kaynağına bağlı manifest ve 36/36 replay yeniden üretilerek giderildi. Sonuçlar ve hashler `reports/exchange-development-20261115/g03-validation.json` içinde.

V1 köprüsü tamamlandı: normal `plans run` girişinde eski yetki tüketimi ve ortak komut kaydı aynı transaction içindedir. Eski eylem/oturum kimlikleri ve koruma/risk yolu korunur. Dahili adaptör doğrudan genel apply ile çalıştırılamaz. Kesinti sonrası list/show/reconcile mevcut kayıtları izler; yeni giriş göndermez. Yeni 10 köprü testi geçti. Nihai tam regresyon **1325 test, 103.195 saniye, OK**; önceki 1315 testlik sonuç çekirdeğin tarihsel kabulüdür.

**G03 yerel kabulü geçti; sıradaki paket G04:** TIF/GTD, priceMatch ve STP normal komutları. G04 başlatılmadı. Destek kapsamı ve kullanım [G03.md](G03.md) içinde. Borsada finansal kabul işlemi yapılmadı.

## G04 teslimi — 16 Kasım 2026

G03 sonrasında [G04](G04.md) uygulandı. V2 SINGLE LIMIT planında isteğe bağlı order_options ile GTC/IOC/FOK/GTX/GTD, sekiz priceMatch seçimi ve etkili STP birleşimleri kullanılabilir. RUN_SINGLE_PLAN genel komutu zaten yetkili planı aynı digest ve seçeneklerle mevcut risk/koruma yürütücüsüne bağlar. Eski GTC davranışı ve GRID döngüsü korunur. Genel adaptör varsayılan RiskLimits kullanır; özel profilli plans run yolu korunur.

GTD gecikmesinde terminal durum varsayılmaz; mevcut kimlik iptal/sorgu ile izlenir. IOC kısmi dolumda terminal kalan ve gerçek koruma doğrulanınca yalnız dolmayan miktarın rezerv payı bırakılır. Geç dolum rezervi artırabilir; bozuk kanıt riski serbest bırakmaz. FOK sıfır dolum, GTX ret ve fiyat eşleme kapsamı sonuçta açıkça ayrılır. Belirsiz giriş yeniden gönderilmez.

**Nihai yerel kabul: 1343 test, 107.194 saniye, OK.** Yeni 18 vaka ve normal CLI uçtan uca testi geçti. Borsada finansal işlem yapılmadı. Hashler ve önceki başarılı koşu `reports/exchange-development-20261115/g04-validation.json` içinde.

**Sıradaki paket G05: native trailing emir yaşam döngüsü.** G05 henüz başlatılmadı.

## G05 teslimi — 16 Kasım 2026

G04 sonrasında [G05](G05.md) uygulandı. Genel CLI üzerinde CREATE_NATIVE_TRAILING, QUERY_NATIVE_TRAILING ve CANCEL_NATIVE_TRAILING kullanılabilir. Mevcut korunmuş V2 SINGLE pozisyonuna ve doğru hesap/bacağa bağlanan azaltıcı emirdir; yeni pozisyon yetkisi üretmez. Sabit stop/hedef ve yerel trailing korunur.

Algo, normal alt emir ve gerçek işlem geçmişi ayrı doğrulanır. İptal sırasında dolum gizlenmez. Aynı sayısal ID farklı sembollerde çakışmaz. Kayıp POST/DELETE ve kesinti sonrası yeni gönderim yapılmaz; açık alt emir varken rezerv serbest bırakılmaz. Yeni 26 hedefli vaka ve normal CLI uçtan uca yolu geçti.

**Nihai yerel kabul: 1369 test, 105.421 saniye, OK.** Borsada finansal işlem yapılmadı. Sonuçlar, sınırlar ve hashler `reports/exchange-development-20261115/g05-validation.json` içinde.

**Sıradaki paket G06: pozisyon artırma/azaltma/kapatma/yön değiştirme.** G06 henüz başlatılmadı.

## G06 teslimi — 16 Kasım 2026

G05 sonrasında [G06](G06.md) uygulandı. Genel CLI üzerinde INCREASE_POSITION, REDUCE_POSITION, CLOSE_POSITION ve REVERSE_POSITION eklendi. İlk adaptör sahip olunan V2 SINGLE kapsamındadır; artırma/azaltma tek hedefli, artırma Close-All korumalı, reversal tek etkin oturumludur. Eski allow_scale_in/allow_reverse ve plan/rezerv digest'leri değiştirilmedi; yeni miktar, fiyat, risk veya ters plan ayrı komut yetkisidir.

Artırma yeni fiyat aralığı ve risk sınırlarıyla IOC LIMIT gönderir. Ek risk ve emir niyeti atomik kayıtlıdır. Gerçek nominal daha yüksekse rezerv buna göre tutulur. Yüzde azaltma taze sahip olunan miktarı lot adımına aşağı yuvarlar. Tam kapanışta yalnız sıfır pozisyon ve terminal emirler rezerv bırakır. Reversal eski kapanış/temizlikten sonra karşı planı açık parent digest'ine bağlı yetkilendirir; kısmi kapanış, geri çekilen hedef, ikinci bacak reddi ve kayıp yanıt otomatik yeni giriş üretmez.

**Nihai yerel kabul: 1397 test, 108.676 saniye, OK.** Yeni 28 G06 vakası, normal CLI ve G04/G05 bağlantıları geçti. Borsada finansal işlem yapılmadı. Sonuç, destek sınırları ve hashler `reports/exchange-development-20261115/g06-validation.json` içinde.

**Sıradaki paket G07: seçili/sembol/hesap normal-algo iptali ve timer.** G07 henüz başlatılmadı.

## G07 teslimi — 16 Kasım 2026

G06 sonrasında [G07](G07.md) uygulandı. CANCEL_SELECTED_ORDERS, CANCEL_SYMBOL_ORDERS, CANCEL_ACCOUNT_ORDERS ve SET/REFRESH/DISABLE/QUERY_CANCEL_TIMER genel CLI üzerinden kullanılabilir. İptal önizlemesi gerçek broker kimlikleriyle dondurulur; yabancı kapsamı açıkça seçilir, yönetilen çekirdek korumalar korunur. Dolumlar ve normal alt emirler ayrı izlenir; iptal pozisyon kapatma veya rezerv bırakma sayılmaz. Belirsiz mutasyon tekrar gönderilmez.

Timer worker açıkça başlatılır; sabit lease, kalıcı heartbeat sırası ve restart sonrası tekrar kurmama davranışı vardır. Süre geçmesi uzaktan devre dışı kanıtı değildir. Aktif/belirsiz timer girişleri engeller; doğru sıfır süre ACK'i engeli kaldırır. Mevcut yönetilen oturum/pozisyon/algo bulunan sembolde timer kurulmaz veya yenilenmez.

**Nihai yerel kabul: 1440 test, 120.108 saniye, OK.** 43 yeni hedefli vaka; normal CLI, kayıp cevap, iptal-dolum yarışı, gerçek store restart, bozuk günlük ve heartbeat/lease sınırları geçti. Borsada finansal işlem yapılmadı. Sonuçlar ve hashler `reports/exchange-development-20261115/g07-validation.json` içinde.

**Sıradaki paket G08: toplu create/amend/cancel çeşitliliği.** G08 henüz başlatılmadı.

## G08 teslimi — 16 Kasım 2026

G07 sonrasında [G08](G08.md) uygulandı. BATCH_CREATE_ORDERS, BATCH_AMEND_ORDERS ve BATCH_CANCEL_ORDERS genel komut yolunda hazırdır. Ayrı onaylı SINGLE planlarıyla normal MARKET/LIMIT, beş TIF ve priceMatch/STP seçenekleri toplu oluşturulabilir. Farklı semboller, boş hesap ve açık birleşik risk sınırları gerekir. Plan claim, rezerv ve oturumlar tek transaction ile hazırlanır; ikinci üye hatası bütün grubu geri alır. Eski GRID GTC davranışı korunur.

Amend üyeleri GTC/GTX/GTD açık fiyatlı LIMIT kapsamındadır; risk büyütülmez ve grup onayı üye digest'lerini bağlar. Broker kimliği ve modifyId geçmişi birlikte teyit edilir. Parent/child iptal kesintisi yeni PUT üretmeden toparlanır. Native batch iptal G07'nin sabit hedeflerini ve ortak iptal engellerini kullanır. Eksik üye, kısmi ret, dolum yarışı ve kayıp yanıt bağımsız sonuç verir; FINAL_WITH_ERRORS tam grup başarısı değildir.

**Nihai yerel kabul: 1473 test, 106.993 saniye, OK.** 33 yeni G08 vakası ve mevcut toplu işlem/amend/G07 kontrolleri geçti. İlk tam koşu 1471 test / 107.098 saniye / OK idi; son iki toparlama vakası ve broker kimliği düzeltmesi nihai koşuda doğrulandı. Borsada finansal işlem yapılmadı. Sonuçlar ve hashler `reports/exchange-development-20261115/g08-validation.json` içinde.

**Sıradaki paket G09: dinamik kaldıraç, hesap ayarları ve UM/CM ortak etkileri.** G09 henüz başlatılmadı.

## G09 teslimi — 16 Kasım 2026

G08 sonrasında [G09](G09.md) uygulandı. SET_LEVERAGE güncel hesap/sembol tablosunu bütün basamaklarıyla ve son gönderim sınırında kontrol eder. Plan, portföy, GRID ve sinyal önizlemesindeki sabit 125 varsayımı kaldırıldı; gerçek nominale karşı basamak, stop/likidasyon ve ortak risk kontrolleri korunur. G09 yüksek kaldıraçta yeni bir risk izni üretmez.

SET_MARGIN_TYPE, SET_POSITION_MODE, SET_MULTI_ASSETS_MODE ve SET_FEE_BURN genel komut/CLI yoluna bağlandı. Ortak pozisyon modu scope'u açık USD-M + COIN-M ister. Her iki üründe normal/algo emirler ve pozisyonlar okunur; legacy cross_product_flat_verified bayrağı bunların yerine geçmez. Dar COIN-M GET adaptörü sabit demo host ve ayrı saat ofseti kullanır; DAPI finansal yazmaları kapalıdır. Gönderim kanıtı komut digest'iyle kalıcıdır. Başarı için iki ürünün mod gözlemi de hedefle eşleşmelidir; belirsizlikte tekrar POST yoktur.

**Nihai yerel kabul: 1499 Python testi, 116.486 saniye, OK.** 26 yeni G09 vaka; mevcut ayar, GRID, izole teminat ve önizleme kontrolleri geçti. Arayüzde 5 sinyal önizleme testi ve TypeScript/Vite build geçti. İzole teminatın kayıp yanıttan sonra gerçek store restart ile ikinci kez eklenmediği doğrulandı. Borsada finansal işlem yapılmadı. Sonuçlar, ortam sınırları ve hashler `reports/exchange-development-20261115/g09-validation.json` içinde.

**Sıradaki paket G10: eksik REST sorguları ve tam geçmiş.** G10 henüz başlatılmadı.

## G10 teslimi — 16 Kasım 2026

G09 sonrasında [G10](G10.md) uygulandı. PUBLIC_QUERY, PRIVATE_QUERY, QUERY_HISTORY, CREATE_HISTORY_EXPORT ve QUERY_HISTORY_EXPORT genel komut yolunda hazırdır. 53 sorgu sözleşmesi, hesap çapında çok sembollü pozisyon/emir okumaları, 7 geçmiş ailesi ve 3 export ailesi vardır. Public piyasa istemcisi yeniden kullanılır; sabit demo hostu korunur. Kullanıcı URL, yöntem, imza veya kapsam dışı sembol veremez.

Geçmiş sayfalaması yoğun tek milisaniye ve pencere sınırlarını korur, ID imlecini uygun ad alanında kullanır ve ikinci turla karşılaştırır. Saklama boşluğu ve belgelenmeyen olay/retention kapsamı complete=false kalır; kayıt, istek ve çıktı bütçeleri vardır. Sorgular sahiplik yaratmaz, ret veya rezerv bırakma kanıtı olarak benimsenmez. Mevcut amend yolu 100'den fazla kaydı sayfalayarak ve gerçek modifyId geçmişini teyit ederek uzlaşabilir.

Dışa aktarma işi oluşturan GET'lerin taşıma retry'ı kapalıdır. Kalıcı source digest, hesap, aile ve downloadId bağı korunur. Kayıp yanıt/restart yeni iş oluşturmaz; hazır link dosyanın indirilip doğrulandığı anlamına gelmez. 95 tarihsel katalog kaydı [G10-surface.json](G10-surface.json) içinde gerekçeli eşlendi; 85 izinli adres tam yaşam döngüsü veya gerçek hesap kabulü diye sunulmaz.

**Nihai yerel kabul: 1536 test, 114.173 saniye, OK.** Yeni 36 sorgu/taşıma vakası ve bir amend entegrasyonu; mevcut piyasa, genel komut, batch, geçmiş ve transport testleri geçti. Önceki başarılı koşular 1532 / 114.468 saniye, 1534 / 114.402 saniye ve 1535 / 114.574 saniyedir. Son çıktı ayrıştırma düzeltmesi nihai koşuda doğrulandı. Borsada finansal işlem yapılmadı. Sonuçlar ve kaynak hashleri `reports/exchange-development-20261115/g10-validation.json` içinde.

**Sıradaki paket G11: ürün/ortam adaptör kaydı ve hesap keşfi.** G11 henüz başlatılmadı.

## G11 teslimi — 16 Kasım 2026

G11 yerel kabulü 16 Kasım 2026'da geçti: **1573 test / 152.413 saniye / OK**, ayrıca **36/36 grafik replay**. 16 ürün/ortam bağlamı kayıtlıdır; 13 bağlamda salt okunur keşif, üçünde yalnız kapsam kaydı vardır. Demo/production, ürün, anahtar ve public/private keşif kimlikleri ayrıdır. Ayrı keşif veritabanı yürütme günlüğü ve mum veritabanıyla karıştırılamaz. Eski demo account_ref ve sahiplik kimlikleri korunur. Yanlış ürün anahtarı, Spot Testnet SAPI, erişim engeli ve reset sonrası kayıp emrin ret sayılmaması doğrulandı. Üretim finansal yürütmesi açılmadı; kimlik doğrulamalı borsa kabulü yapılmadı. Teslim [G11.md](G11.md), kayıt [G11-registry.json](G11-registry.json). Sıradaki paket G12'dir.

**Sıradaki paket G12: ortak rate budget ve WS işlem arabirimi.** G12 henüz başlatılmadı.

## G12 teslimi — 16 Kasım 2026

G12 yerel kabulü 16 Kasım 2026'da geçti: **1610 test / 119.718 saniye / OK**, ayrıca **36/36 grafik replay**. UM/CM REST ortak IP ve REST/WS ortak emir bütçeleri kalıcı ve atomik rezerve edilir. WS IP havuzu ve REST trade örtüşmesi ayrı modellenir. Bilinen UID olmadan anahtar başına sahte kapasite üretmek yerine bütün yerel anahtarlar muhafazakâr ortak havuzdadır. 429/418, düşük bildirilen limit ve saat geri dönüşü süreç restartında korunur. Commands/orders CLI açık WS seçimiyle altı tekil yönteme bağlanır; request_id ve operasyon kimliği kalıcıdır. Kayıp yanıt veya değiştirilmiş fiyat aynı CID'yi yeniden gönderemez; REST fallback yoktur. Gerçek SINGLE komutu, koruma emirleri ve modifyId geçmişinden amend toparlanması doğrulandı. Özel karakterli WS imzasında SDK/belge ayrımı gönderim öncesi engellenir. Native batch, diğer ürünlerin finansal adaptörleri ve kimlik doğrulamalı borsa kabulü tamamlandı sayılmaz. Teslim [G12.md](G12.md), sözleşmeler [G12-contracts.json](G12-contracts.json). Sıradaki paket G13'tür.

**Sıradaki paket G13: durum makinesi ve hata enjekte eden kabul araçları.** G13 henüz başlatılmadı.

## Güvenilirlik öncelik turu — 16 Kasım 2026

Güvenilirlik öncelik turu 16 Kasım 2026'da yerelde geçti: **1649 test / 155.096 saniye / OK**, geniş hata kabulünde **290 test / 44.5 saniye / 0 skip**, **128 seed × 100 adım**, ayrıca **36/36 grafik replay**. G13 dolum/ret durum tutarsızlığını giderdi ve tekrarlanabilir hata kabulü ekledi. G22 salt okunur operasyon/WS/kota/toparlanma görünümünü CLI/API'ye bağladı. G23 yalnız mevcut USD-M yazılım kapsamını kapattı. G14–G21 **UYGULANMADI — ERTELENDİ**. Varsayılan yerel günlük **CONTEXT_UNVERIFIED**; kimlik doğrulamalı borsa kabulü **NOT_RUN**. Yeni ürünlere otomatik geçiş yoktur. [Öncelik kararı](PRIORITY-REVIEW.md), [G13](G13.md), [G22](G22.md), [yerel G23 kapanışı](G23.md).

**Bu seçimde otomatik sıradaki paket yoktur.** Sekiz ürün paketi açık kullanıcı kapsamı seçimine kadar ertelenmiştir. Yerel günlük kökeni/migration ve gerçek hesap/borsa kabulü ayrı açık engellerdir.
