# Borsa işlem yetenekleri geliştirme planı

## Güncel kapsam kararı — 16 Kasım 2026

Güvenilirlik öncelik turu 16 Kasım 2026'da yerelde geçti: **1649 test / 155.096 saniye / OK**, geniş hata kabulünde **290 test / 44.5 saniye / 0 skip**, **128 seed × 100 adım**, ayrıca **36/36 grafik replay**. G13 dolum/ret durum tutarsızlığını giderdi ve tekrarlanabilir hata kabulü ekledi. G22 salt okunur operasyon/WS/kota/toparlanma görünümünü CLI/API'ye bağladı. G23 yalnız mevcut USD-M yazılım kapsamını kapattı. G14–G21 **UYGULANMADI — ERTELENDİ**. Varsayılan yerel günlük **CONTEXT_UNVERIFIED**; kimlik doğrulamalı borsa kabulü **NOT_RUN**. Yeni ürünlere otomatik geçiş yoktur. [Öncelik kararı](PRIORITY-REVIEW.md), [G13](G13.md), [G22](G22.md), [yerel G23 kapanışı](G23.md).

Bu turdaki durumlar: G13/G22 `LOCAL_ACCEPTANCE_PASSED`, G23 `LOCAL_SCOPE_ACCEPTANCE_PASSED`, G14–G21 `DEFERRED_BY_USER_SCOPE` ve `implemented=false`. Tarihsel paket sırası korunur; etkin seçim ve ertelemeler packages.json current_selection içindedir. Yerel kabul finansal çalışma hazırlığı değildir.


Başlangıç: 15 Kasım 2026. Kullanıcı araştırmadan geliştirmeye geçilmesini ve uygulamanın başlamasını istedi. Hedef, stratejisini kullanıcının belirlediği botun borsa talimatlarını doğru hesap, ürün, emir, tutar ve sonuç kapsamında yürütebilmesidir.

Araştırma girdileri: [34 bulgu ailesi](../../research/crypto-bot-20261115/FINAL-GAP-REGISTER.md), [43 talimat ailesi](../../research/crypto-bot-20261115/WORKFLOW-CAPABILITY-REVIEW.md), [558 kayıt ve kaynak sınırları](../../research/crypto-bot-20261115/RESEARCH-CLOSURE-5-8.md). Başlangıçtaki 555 kaydın 39'unda adaptör yolu var, 1'i başka istemcide, 515'inde ürün/yol açığı bulunuyor. Bir adres eklemek tek başına o talimatı tamamlamaz.

## Teslim modeli

Her paket normal kullanıcı girişini, alan sözleşmesini, doğrulamasını, kalıcı niyetini, sonuç teyidini ve gereken toparlanmasını birlikte teslim eder. Başarı, açık ret ve çözülmemiş sonuç kullanıcıya ayrı gösterilir. Eski SINGLE/GRID/NEUTRAL planları korunur. Genel borsa işlemleri strateji sinyali veya zorunlu stop/hedef planı gibi yeniden yorumlanmaz.

Paket durumu `BEKLIYOR`, `UYGULANIYOR`, `YEREL_KABUL_GECTI`, `BORSA_KABULU_GECTI` veya `SOZLESME_KAPISI` olabilir. Yerel test sonucu borsa kabulü anlamına gelmez. Bir paketin alt maddesi bittiğinde bütün F bulgusu kapatılmaz.

## Ortak uygulama sözleşmesi

1. Ürün/ortam/hesap, sembol veya varlık, işlem türü, client/parent/child kimlikleri ve sürüm açık olmalı.
2. Normal komuttan hazırlama/inceleme, mevcut yetki modeline uygun uygulama ve yeniden sorgulama yolu bulunmalı. Genel geliştirme talebi canlı işlem yetkisi sayılmaz.
3. Finansal mutasyon önce kalıcı niyet ve rezerv oluşturur. Belirsiz gönderim körlemesine tekrarlanmaz.
4. Kısmi dolum, iptal/amend yarışı, batch alt sonuçları ve iki muhasebe ayağı gerçek sonuçla uzlaştırılır.
5. Migration eklemeli ve sürümlü yapılır. Eski journal/client kimlikleri veya digestler yeniden yazılmaz. Yeni isteğe bağlı alanlar eski plana otomatik eklenmez.
6. Her değişiklikte ilgili testler, gerekli entegrasyon testleri ve ortak çekirdek değiştiyse tam regresyon çalışır. Kanıt tarihi, kod hashleri ve ortamı kaydedilir.
7. Belirsiz ürün sözleşmesi tahmin edilmez. İlgili paket kapıda beklerken açık USD-M işlerine devam edilebilir.

## Bağımlılık ve uygulama sırası

Efor aralıkları ilk mühendislik tahminidir, tek kişinin odaklı iş günü içindir. Dış hesap uygunluğu ve borsa kabulü bekleme süresi dahil değildir. Toplanarak takvim taahhüdüne dönüştürülemez.

| Paket | Teslim | Bulgu | Önkoşul | Tahmini efor |
|---|---|---|---|---|
| G00 | Araştırma → plan, kanıt ve ilerleme kaydı | F32 | Yok | 0.5–1 gün |
| G01 | SINGLE normal girişinde ACK/RESULT seçimi | F03 yanıt alt maddesi | G00 | 0.5–1 gün |
| G02 | Güncel USD-M parametre ve filtre doğrulaması | F04, F10, F11, F12 | G01 | 2–4 gün |
| G03 | Genel işlem komutu, niyet ve sonuç sözleşmesi | F01, F02, F28 | G02 | 4–7 gün |
| G04 | TIF/GTD, priceMatch ve STP normal komutları | F03 kalan | G03 | 3–5 gün |
| G05 | Native trailing emir yaşam döngüsü | F05, F04 uçtan uca | G03 | 2–4 gün |
| G06 | Pozisyon artır/azalt/kapat/yön değiştir | F06 | G03, G04 | 4–7 gün |
| G07 | Seçili/sembol/hesap normal-algo iptali ve timer | F07 | G03 | 3–5 gün |
| G08 | Toplu create/amend/cancel çeşitliliği | F08 | G03, G04, G07 | 3–5 gün |
| G09 | Dinamik leverage, hesap ayarları ve UM/CM etkisi | F09, F13 | G03 | 3–5 gün |
| G10 | Eksik REST sorguları ve tam geçmiş | F15, F33, F34 | G03 | 3–6 gün |
| G11 | Ürün/ortam adaptör kaydı ve hesap keşfi | F01, F26 | G03 | 4–7 gün |
| G12 | Ortak rate budget ve WS işlem arabirimi | F14, F25 | G03, G11 | 4–7 gün |
| G13 | Durum makinesi ve hata enjekte eden kabul araçları | F30, F31, F28 | G03 | 3–5 gün, sonra ürünlere ek |
| G14 | Spot normal/SOR/liste/özel emirler | F16 | G04, G07, G11, G13 | 8–14 gün |
| G15 | Margin hesap, borç, faiz ve emir yan etkileri | F17 | G14, G19, G13 | 8–14 gün |
| G16 | COIN-M inverse/teslim ve yeni algo | F18, F19 | G09, G11, G13 + CM sözleşme kapısı | 6–10 gün |
| G17 | Options prim/vade/exercise/MMP/block trade | F20, F27 Options | G11, G13 + olay/ortam kapısı | 8–14 gün |
| G18 | PM/Pro/SPAN birleşik hesap | F21, F27 PM | G15, G16 + hesap kapısı | 8–14 gün |
| G19 | Wallet transfer/dust/deposit/withdraw/Travel Rule | F23, F27 Wallet | G03, G11, G13 | 6–10 gün |
| G20 | Convert teklif/limit ve sonuç muhasebesi | F22 | G03, G11, G19 | 3–5 gün |
| G21 | Master/sub/managed account işlemleri | F24 | G11, G19 + yetki/VIP kapısı | 5–8 gün |
| G22 | İşlem durumu ve operasyon metrikleri | F29 | G03 | 2–4 gün |
| G23 | Nihai çapraz kapsam ve kabul kapanışı | F26, F27, F31, F32, F28 | Seçilen bütün ürün paketleri | 3–5 gün + dış kabul |

G15'in Wallet bağımlılığı nedeniyle G19, G15'ten önce uygulanır. Tablo kimlik sırasıdır, bağımlılık grafiği uygulama sırasını belirler. Mevcut çalışma ağacındaki kullanıcı değişiklikleri korunur.

## Paket ayrıntıları

### G00 — Plan ve kanıt sürümü

Araştırma kayıtlarını silmeden uygulama başlangıç hashleri alınır. Her paket için değişen normal giriş, test, durum ve kalan kabul kaydedilir. Araştırma doğrulayıcısının eski kod hashine karşı başarısız olması özellik regresyonu sayılmaz. Kabul: bütün F01–F34 bulguları bir pakete bağlı, bağımlılık döngüsü yok, durum raporu ile gerçek test sonucu aynı.

### G01 — Yanıt tercihini normal SINGLE girişine bağla

Örnek: kullanıcı V2 SINGLE planında `entry.order_response_type: RESULT` belirtir. Önceden bilinmeyen plan/validator alanıydı. Hedef: normal `plans create/show/preflight/run` zinciri tercihi `newOrderRespType` olarak taşır, digest ve journal aynı değeri korur. Mevcut `plan_v2.py`, `order_rules.py`, `v2_preflight.py`, `v2_runner.py` kullanılır. GRID/NEUTRAL kapsamı bu pakette genişletilmez ve seçenek sessizce yok sayılmaz.

Uyumluluk: alan yoksa önceki parametre gövdesi ve digest korunur, DB migrationı gerekmez. ACK içeriği minimal olabilir. RESULT dolum garantisi değildir. Yanıt kaybında orijinal kimlikle sorgu yapılır. Kabul: CLI içe alma/gösterme, market/limit hazırlama, geçersiz enum, minimal ACK, bekleyen LIMIT RESULT, restart sonrası tek POST ve hazırlanan alanın değiştirilmesine ret. Borsa kabulü ayrı.

### G02 — Güncel parametreler ve fiyat/filtre kontrolleri

Örnek: geçerli UM callback 10 reddedilmez, kaydedilen fiyat bandı dışındaki LIMIT anlaşılır nedenle durur. `order_rules.py` ortak kurallarına güncel callback aralığı, koşullu zorunluluklar, dinamik fiyat bandı ve risk filtre değerlendirmesi eklenir. MARK_PRICE ile CONTRACT_PRICE karşılaştırması doğru güncel veri kaynağına dayanır, yalnız mark eldeyken contract fiyatı varsayılmaz.

Yeni bağlam alanları preflight ve gönderim öncesi doğrulamaya taşınır. Eksik/eskimiş fiyat veya tanınmayan kısıt başarı sayılmaz. Eski geçerli planların miktar/risk hesapları korunur. Kabul: 62 sembol vakasının yeni beklentileri, callback sınırları, iki yön/tür tetik eşitlikleri, düşük fiyat/tick sınırı, filtre değişimi ve gönderim öncesi fiyat değişimi. Araştırma raporları tarihsel kalır, yeni sonuç ayrı dosyaya yazılır.

G02 uygulama teslimi V2 SINGLE/GRID/NEUTRAL ile native batch create ve normal amend yollarını kapsar. Normal yetkili V1 girişinin ortak komut sistemine köprüsü G03 kapsamındadır. Eski `--test-only` altyapı deneyleri normal kullanıcı girişine dönüştürülmez ve izinleri genişletilmez. Ayrıntılar [G02 tesliminde](G02.md) ve [G03 tesliminde](G03.md) kaydedilir.

### G03 — Genel komut ve kalıcı niyet

Örnek: kullanıcı mevcut strateji planı kurmadan izinli hesaba belirli bir emir veya sorgu talimatı verir. Yeni, sürümlü bir genel komut sözleşmesi tasarlanır. Önerilen alanlar environment/product/account_ref/operation/scope/parameters/client_command_id. Yeni CLI/API hazırlama, uygulama ve uzlaştırma servisleri mevcut sahiplik, locking, journal ve rezervasyon kodunu kullanır.

Eski plan_v2 ve oturum tabloları geriye uyumlu kalır. Genel komut kayıtları yeni ad alanı veya eklemeli tabloda tutulur. Kod dosyaları uygulama sırasında mimariye göre kesinleşir, doğrudan serbest URL gönderme genel kullanıcı arabirimi yapılmaz. Kabul: desteklenen işlem, ret, duplicate, eşzamanlı aynı kimlik, gönderim öncesi/sonrası crash, farklı hesap/üründe aynı sembol ve parametre değişmiş tekrar. Yetki/risk koşulu olmayan genel POST yolu bırakılmaz.

Uygulama sınırı: ilk genel CLI işlemleri mark sorgusu, normal emir sorgusu ve mevcut güvenli servise delege edilen kaldıraç ayarıdır. Normal V1 planı, yetkisini tüketen transaction içinde ortak komut journal'ına bağlanır; planın eski onayı, eylem/oturum kimliği ve koruma motoru korunur. Dahili plan adaptörü genel prepare/apply ile yeni giriş gönderemez. HTTP arabirimi veya bütün motorları tek executor'a yeniden yazma bu çekirdek tesliminin kabul ölçütü değildir. Sonuçlar [G03.md](G03.md) ve ilerleme kaydındadır.

### G04 — Süre, fiyat eşleme ve STP

Örnek: `IOC LIMIT` veya `GTD` son geçerlilikli emir. G03 komut şemasından compiler ve executor'a seçenekler taşınır. Mevcut SINGLE/GRID'e yalnız desteklendiği ölçüde köprü eklenir. GTD milisaniye yuvarlaması, sona erme gecikmesi, FOK/IOC kısmi sonuç, GTX ret ve priceMatch/fiyat çakışması değerlendirilir. STP uygunluğu sembol/hesap ve TIF ile bağlanır.

Kabul: emir kaybolduğunda ikinci POST yok, IOC kalan miktar iptali risk rezervini doğru serbest bırakır, FOK gerçekleşmemesi açık sonuçtur, GTD süresi geçen emir yeniden kurulmaz. Eski GTC varsayılanı değişmez. RPI uygunluğu kanıtlanmadan genel seçenek yapılmaz.

G04 yerel kabulü 16 Kasım 2026'da geçti: 1343 test / 107.194 saniye / OK. Teslim SINGLE LIMIT ve genel RUN_SINGLE_PLAN adaptörü üzerindedir. GRID döngüsünün GTC davranışı korunur; desteklenmeyen seçenek sessizce yok sayılmaz. Yeni STP NONE/RPI sunulmaz. Genel adaptör mevcut yetkili planı ve varsayılan RiskLimits sınırlarını kullanır; serbest URL/POST değildir. Kapsam ve fiyat eşleme risk sınırları [G04.md](G04.md) içinde. Sonraki paket G05'tir.

### G05 — Borsanın native trailing emri

Örnek: kullanıcının verdiği activation/callback ile TRAILING_STOP_MARKET oluştur, sorgula ve iptal et. Yerel watermark/stop-replace işlevi korunur, native emir açıkça ayrı işlem olarak sunulur. Algo/child kimliği, aktivasyon ve gerçek dolum muhasebesi journal'a bağlanır. Kabul: aktivasyon yönü, callback sınırı, tetiklenme/iptal yarışı ve restart sırasında native emrin çoğalmaması.

G05 yerel kabulü 16 Kasım 2026'da geçti: **1369 test / 105.421 saniye / OK**. Teslim, mevcut korunmuş V2 SINGLE pozisyonunu azaltan native trailing create/query/cancel komutlarıdır. Yerel trailing ve sabit korumalar korunur. Native parent, normal alt emir ve gerçek işlem geçmişi ayrı izlenir; açık alt emirde rezerv bırakılmaz. Yeni pozisyon açan trailing ve GRID/NEUTRAL bu teslimde sunulmaz. Kapsam ve kanıt [G05.md](G05.md) içinde. Sonraki paket G06'dır.

### G06 — Pozisyon işlemleri

Örnek: sahipliği belirlenmiş pozisyonu artır, %25 azalt veya açık talimatla ters yöne geçir. Yeni işlem derleyicisi gerçek pozisyon/dolum/teminat ve mevcut korumayı birlikte değerlendirir. Reversal iki bağımsız borsa etkisi içerebilir, atomik varsayılmaz. Parent komut ve alt niyetler kullanılır. Kabul: kısmi kapanıştan sonra yeni yön miktarı, hedge yanlış bacak, manuel pozisyon karışması, bütçe artışı, kapanış yanıt kaybı ve ikinci bacağın reddi. Eski SINGLE izinleri kendiliğinden genişlemez.

G06 yerel kabulü 16 Kasım 2026'da geçti: **1397 test / 108.676 saniye / OK**. İlk adaptör sahip olunan V2 SINGLE kapsamındadır. Artırma/azaltma tek hedefli, artırma ilk Close-All korumalı, reversal tek etkin oturum ve ayrı karşı yön SINGLE IMMEDIATE planı gerektirir. Eski SINGLE izinleri değişmez; yeni miktar/fiyat/risk ve ters plan için açık komut digest'i bağımsız yetkidir. Normal CLI, gerçek dolum/pozisyon kanıtı, ek rezerv ve iki bacaklı hata/kurtarma yolu bağlandı. Destek sınırları [G06.md](G06.md) içinde. Sonraki paket G07'dir.

### G07 — İptal ve timer kapsamı

Örnek: yalnız bu botun seçili emirlerini, belirli sembolün emirlerini veya açık hesap kapsamıyla bütün normal/algo emirlerini iptal et. Allowlist ancak karşılık gelen komut/teyit hazır olduğunda genişler. Countdown cancel heartbeat ve süre bitimi kalıcı izlenir. Kabul: iptal sırasında dolum, yabancı emir kapsamı, normal/algo farkı, timer yenileme hatası ve restart sonrası beklenmedik timer tekrarı olmaması. Mevcut korumalar yanlış kapsamda iptal edilmez.

G07 yerel kabulü 16 Kasım 2026'da geçti: **1440 test / 120.108 saniye / OK**. Genel CLI seçili/sembol/hesap normal-algo iptalinde incelenebilir sabit hedef listesi kullanır; çekirdek korumalar korunur. Countdown için sabit lease, açık worker, kalıcı deneme kaydı ve belirsizlikte yeni giriş engeli eklendi. Timer durum GET'i varsayılmaz; devre dışı ACK gerekir. 43 hedefli test geçti; finansal borsa kabulü yapılmadı. Sınırlar [G07.md](G07.md) ve kabul raporundadır. Sıradaki paket G08'dir.

### G08 — Batch çeşitliliği

Mevcut batch servisleri ve üye kimlikleri kullanılır. Destekli emir türleri ve süreleri ürün limitleriyle genişletilir. Grup onayı üye parametrelerini kapsar. Kabul: kısmi ret, eksik üye yanıtı, yinelenmiş kimlik, dolum-amend yarışı, grup yanıtının kaybı ve restart. Bir üyedeki başarı tüm gruba yazılmaz. Eski LIMIT/GTC grid davranışı korunur.

G08 yerel kabulü 16 Kasım 2026'da geçti: **1473 test / 106.993 saniye / OK**. BATCH_CREATE_ORDERS, BATCH_AMEND_ORDERS ve BATCH_CANCEL_ORDERS normal komut/CLI yoluna bağlandı. Ayrı yetkili, farklı sembollü SINGLE planlarında MARKET/LIMIT ve GTC/IOC/FOK/GTX/GTD, priceMatch/STP desteklenir; ilk adaptör boş hesap ister. Grup claim/rezerv/oturum hazırlığı atomiktir. Açık fiyatlı GTC/GTX/GTD amend, üye digest'leri ve bağımsız modifyId geçmişiyle teyit edilir. Native normal batch iptal G07'nin sabit broker kimliklerini ve ortak tekrar engellerini kullanır. 33 yeni uçtan uca vaka geçti. Destek sınırları [G08.md](G08.md) içinde; finansal borsa kabulü yapılmadı. Sıradaki paket G09'dur.

### G09 — Hesap ayarları

Sabit 125 yerine sembol/hesap leverageBracket üzerinden doğrulama, ortak UM/CM position mode kontrolü ve mod değişiminden etkilenen bütün ürün kayıtları. Mevcut AccountCommands/IsolatedMarginCommands prepare/apply/reconcile akışı kullanılır. Gerekli CM okuma adaptörü G11 öncesi salt okuma ve dar kapsamda eklenebilir. Kabul: bir üründe açık emir varken ortak ayarın reddi, son anda bracket değişimi, ayar yanıtının kaybı ve izole teminatın iki kez eklenmemesi.

G09 yerel kabulü 16 Kasım 2026'da geçti: **1499 Python testi / 116.486 saniye / OK**. Güncel hesap/sembol bracket tablosu gönderim sınırında tekrar doğrulanır; sabit 125 varsayımı giriş ve risk/önizleme katmanlarından kaldırıldı. Ortak SET_POSITION_MODE, USD-M ve COIN-M pozisyon/normal/algo okumalarını gerçek salt okuma demo adaptörüyle gerektirir; çağıranın boolean beyanı kanıt değildir. Etkilenen ürünler ve gönderim kontrolleri kalıcıdır; iki mod teyidi uyuşmadan başarı yoktur. Diğer mevcut ayarlar genel komuta bağlandı. İzole teminat kayıp yanıt/restart sırasında yeniden eklenmez. 26 yeni vaka, 5 arayüz testi ve frontend build geçti. Kapsam ve sınırlar [G09.md](G09.md) içinde. Finansal borsa kabulü yapılmadı. Sıradaki paket G10'dur.

### G10 — Sorgu ve geçmiş

55 eksik USD-M yolun sorgu/hesap/veri grupları kullanıcı talimatı ve uygun saklama penceresiyle tamamlanır. `history.py`, `history_reconciliation.py` ve public market istemcisi yeniden kullanılır. Emir/algo/order amendment, force orders, gelir ve indirilebilir geçmiş kimlikleri ayrılır. Kabul: yoğun tek milisaniye, pencere sınırı, arada eklenen kayıt, eski kaydın yokluğu ve tam olmadığı bilinen sonucun tam raporlanmaması. Trading Schedule/TradFi gibi kapsam dışı işlemler gerekçeli tutulur.

G10 yerel kabulü 16 Kasım 2026'da geçti: **1536 test / 114.173 saniye / OK**. Normal komut/CLI yoluna 53 adlandırılmış sorgu, 7 geçmiş ailesi ve 3 dışa aktarma ailesi bağlandı. Sayfalama sabit zaman sınırı, ID veya daralan zaman penceresi, toplam bütçe ve ikinci okuma karşılaştırması kullanır. Saklama boşluğu, tek milisaniye doygunluğu ve değişen kayıt tam geçmiş sayılmaz. Mevcut amend yaşam döngüsünün 100 kayıt engeli sayfalama ile giderildi. İş oluşturan GET tek gönderimlidir; downloadId hesap/aileye bağlıdır ve hazır URL dosya tamamlığı sayılmaz. 36 yeni sorgu/taşıma testi ve bir amend entegrasyonu geçti. Kapsam [G10.md](G10.md), 95 kaydın gerekçeli dağılımı [G10-surface.json](G10-surface.json) içinde. Katalogdaki 10 kapsam dışı veya diğer pakete ait adres ayrı tutuldu; finansal borsa kabulü yapılmadı. Sıradaki paket G11'dir.

### G11 — Ürün/ortam ve hesap keşfi

Ortam hostları, API ailesi, izin ve hesap modeli registry'ye alınır. Mevcut demo Config geriye uyumlu kalır. Anahtar bilgileri günlük/komut çıktısında gösterilmez. Üretim desteği bu paketin otomatik sonucu değildir. Migration mevcut account_ref sahipliğini değiştirmez. Kabul: Demo/prod cache ve journal ayrımı, yanlış ürün anahtarı, Spot Testnet /sapi reddi, Options 403'ün doğru belirsizlik sonucu ve Testnet reset sonrası kayıp geçmişin ret sayılmaması.

G11 yerel kabulü 16 Kasım 2026'da geçti: **1573 test / 152.413 saniye / OK**, ayrıca **36/36 grafik replay**. 16 ürün/ortam bağlamı kayıtlıdır; 13 bağlamda salt okunur keşif, üçünde yalnız kapsam kaydı vardır. Demo/production, ürün, anahtar ve public/private keşif kimlikleri ayrıdır. Ayrı keşif veritabanı yürütme günlüğü ve mum veritabanıyla karıştırılamaz. Eski demo account_ref ve sahiplik kimlikleri korunur. Yanlış ürün anahtarı, Spot Testnet SAPI, erişim engeli ve reset sonrası kayıp emrin ret sayılmaması doğrulandı. Üretim finansal yürütmesi açılmadı; kimlik doğrulamalı borsa kabulü yapılmadı. Teslim [G11.md](G11.md), kayıt [G11-registry.json](G11-registry.json). Sıradaki paket G12'dir.

### G12 — Limit bütçesi ve WS komutları

RequestGovernor üzerine ürünün gerçek IP/UID/order bütçesi ve UM/CM ortak havuz bağlamı eklenir. WS API istek kimliği, imza, zaman ve sonuç korelasyonu REST journal'a eşdeğer semantik taşır. Passive user stream mevcut görevini korur. Kabul: iki hostta eşzamanlı bütçe tüketimi, 429/418 kalıcı cooldown, WS yanıt kaybı/kopma ve aynı niyetin REST'e kör fallback ile tekrar gönderilmemesi.

G12 yerel kabulü 16 Kasım 2026'da geçti: **1610 test / 119.718 saniye / OK**, ayrıca **36/36 grafik replay**. UM/CM REST ortak IP ve REST/WS ortak emir bütçeleri kalıcı ve atomik rezerve edilir. WS IP havuzu ve REST trade örtüşmesi ayrı modellenir. Bilinen UID olmadan anahtar başına sahte kapasite üretmek yerine bütün yerel anahtarlar muhafazakâr ortak havuzdadır. 429/418, düşük bildirilen limit ve saat geri dönüşü süreç restartında korunur. Commands/orders CLI açık WS seçimiyle altı tekil yönteme bağlanır; request_id ve operasyon kimliği kalıcıdır. Kayıp yanıt veya değiştirilmiş fiyat aynı CID'yi yeniden gönderemez; REST fallback yoktur. Gerçek SINGLE komutu, koruma emirleri ve modifyId geçmişinden amend toparlanması doğrulandı. Özel karakterli WS imzasında SDK/belge ayrımı gönderim öncesi engellenir. Native batch, diğer ürünlerin finansal adaptörleri ve kimlik doğrulamalı borsa kabulü tamamlandı sayılmaz. Teslim [G12.md](G12.md), sözleşmeler [G12-contracts.json](G12-contracts.json). Sıradaki paket G13'tür.

### G13 — Kabul araçları ve durum makinesi

Mevcut izole fixtures ve process crash testleri temel alınır. Hypothesis gerektiği yerde geliştirme bağımlılığı olarak eklenir, yalnız dil sözdizimini tekrar test etmek için kullanılmaz. Temel invariantlar: kimlik başına en fazla kanıtlı tek gönderim, muhasebe miktarı gerçek dolumla eşit, belirsiz rezerv erken serbest değil, yanlış hesapta işlem yok. SXP veri koşulu test başarısı gibi düzeltilmez. Kabul: yeniden üretilebilir seed, hata izi ve başarısız örneğin küçültülebilmesi.

G13 teslimi: [G13.md](G13.md). Model kaynaklı ret/dolum düzeltmesi, bounded küçültme ve normal CLI/gerçek crash kabulü yerelde geçti; F31 veri kapısı ve native order/test yolu açık kapsamdır.

### G14 — Spot

48 başlangıç sözleşmesi normal/SOR emir, cancel-replace, keep-priority amend, OCO/OTO/OTOCO/OPO/OPOCO, iceberg/pegged/trailing ve hesap/geçmiş gruplarına bölünür. Baz/quote miktar, STP izinleri, komisyon ve parent/child muhasebesi yeni ürün adaptöründe tutulur. Kabul: cancel başarılı/new order ret, OPO pending miktar ve ücret, SOR allocation, sıfır market step ve kullanıcı aboneliği sonrası recovery. G11 ortam ayrımı ve G13 süreç testleri olmadan ürün tamamlandı sayılmaz.

### G15 — Margin

69 başlangıç sözleşmesi cross/isolated hesap, debt/interest, borrow/repay, sideEffectType, emir listeleri, risk ve özel işlem gruplarıyla uygulanır. Borrow ile emir ayrı veya borsanın otomatik yan etkisi olabilir. Account-wide pending işlem sıralaması gerekir. Kabul: -3007, sessiz auto-repay başarısızlığı, faiz değişimi, izole yanlış sembol, transfer sonrası gecikme ve borcun yanlışlıkla sıfır sayılmaması. Eski futures isolated margin ile karıştırılmaz.

### G16 — COIN-M

64 başlangıç ve üç resmi ek yol ayrı kayıtlarla uygulanır. ContractSize, kontrat miktarı, inverse coin PnL, funding ve teslim sonu muhasebesi eklenir. **Kapı:** CM algo'nun tam alanları/sınırları veya açık sınırları olan kontrollü kabul kanıtı. CCXT kaynaklı üç aday resmi kabul yerine geçmez. Kabul: kontrat/coin dönüşümü, CM/UM ortak mod, GTX amend iptali, yeni algo/child kimliği, vade kapanışı ve coin komisyonu.

### G17 — Options

44 başlangıç işleminde normal/batch LIMIT, pozisyon/prim/exercise, MMP/kill-switch ve block-trade alt teslimleri ayrı yapılır. **Kapı:** belgelenmiş ortam/hesap erişimi ve gerekli iç olay şemaları. Bilinmeyen object gövdesi yanlış doldurulmaz. Kabul: CALL/PUT, unit/strike/expiry, premium ve fee, exercise sonucu, MMP freeze/reset, heartbeat kaybı ve block trade uzatma/iptal yarışı.

### G18 — PM/Pro/SPAN

126 başlangıç işleminde PM, Pro ve SPAN parser/risk hesapları ayrılır. UM normal/algo, CM conditional ve Margin kimlikleri doğru hesap yoluna gider. **Kapı:** hesap modeli ve risk şeması kabulü. PM uniMMR eşikleri Pro/SPAN'a taşınmaz. Kabul: haircut basamağı, boş sayısal alan, USD transfer tavanı/coin ayrımı, bir bacağın tasfiyesi ve negatif bakiye/repay sonucu. Mevcut portfolio.py USD-M işlevi korunur.

### G19 — Wallet

50 başlangıç işleminde varlık/izin/ücret, transfer/dust, deposit/withdraw ve Travel Rule alt grupları yapılır. Hareket niyeti, iki hesap ayağı, ücret, ağ, adres/tag, hassas PII ve geçmiş kimliği ayrı tutulur. **Kapı:** fromSymbol/toSymbol çelişkisine karşı gerçek sembol kabulü ve hesaba özgü Travel Rule gereksinimi. Kabul: lost reply, yetersiz fee, kapalı ağ, yanlış memo, bir ayağın gecikmesi, soru/PII retleri ve accepted ile completed ayrımı.

### G20 — Convert

9 /sapi sözleşmesi teklif, kabul, limit ve sonuç süreciyle eklenir. Futures /fapi Convert ayrı ürün yoludur. Kabul: teklif süre aşımı, kaynak/hedef miktar, wallet birleşimi, PROCESS/ACCEPT_SUCCESS/SUCCESS/FAIL ayrımı, limit iptal/dolum yarışı ve tekrarlanan kabul talimatında mükerrer hareket olmaması.

### G21 — Alt hesap

50 sözleşme master/sub/managed keşfi, ürün etkinleştirme, API key/IP/izin yönetimi, transfer ve position move alt gruplarıyla eklenir. **Kapı:** ilgili master/VIP/ürün izinleri. Hassas anahtar yanıtı loga yazılmaz. Kabul: kaynak/hedef hesap karışması, VIP7–9/cross/mark koşulları, 10 pozisyon sınırı, karışık UM/OPTION reddi ve iki hesabın gecikmeli uzlaşması.

### G22 — Görünür durum ve gözlem

Komutun hazırlanması, gönderimi, belirsizliği, sorgusu ve kesin sonucu CLI/API'de aynı anlamı taşır. UNKNOWN sayısı, recovery gecikmesi, WS kesintisi, limit beklemesi ve kısmi batch sonucu ölçülür. Prometheus adaydır, günlükler mevcut journal yerine geçmez. Kabul: hassas veri içermeyen ölçüm, yanlış başarı bildirimi olmaması, restart sonrası açık işlerin görünmesi.

G22 teslimi: [G22.md](G22.md). Owner/context kontrollü salt okunur CLI/API ve sayısal metrikler yerelde geçti; eski günlük doğrulanmış sayılmadı.

### G23 — Nihai kabul ve kapanış

558 resmi kayıt, üç uygulama adayı, 83 WS komutu ve 43 talimat ailesi nihai kapsam kararına bağlanır. Seçilen ürünlerin alan kombinasyonları ve normal kullanıcı yolları üzerinde yerel/entegrasyon/borsa kanıtı ayrı hesaplanır. Her bulgu kapalı, belirli destek sınırında veya gerekçeli kapsam dışında olmalı. Kalan kritik bilinmeyen varken bütün borsa işlemleri destekleniyor iddiası verilmez. İnternetin tamamı veya Binance'in diğer Earn/C2C/Web3 hizmetleri bu planın tamamlanma ölçütüne örtük eklenmez.

G23 güncel teslimi: [G23.md](G23.md). Bu aşama mevcut USD-M için yerel kapsam kapanışıdır; orijinal bütün ürün ve dış hesap kabulünü tamamlamaz.

## Tarihsel ilk uygulama kaydı

İlk uygulama G01. Kullanıcı artık V2 SINGLE planında isteğe bağlı `entry.order_response_type` ile ACK/RESULT seçebilir. Eski plan ve kayıtlara varsayılan alan eklenmez. Detay ve test sonuçları [ilerleme kaydında](PROGRESS.md). Sonraki paket G02, ardından genel komut G03'tür. Hiçbir dış hesapta finansal deney bu geliştirme turunun parçası olarak yürütülmez.
