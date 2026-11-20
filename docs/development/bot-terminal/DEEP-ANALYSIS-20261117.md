# Bot durum analizi ve geliştirme sırası

17 Kasım 2026. İnceleme: bağlı frontend, API, kuyruk, worker, mevcut plan/komut motorları ve izole testler. Bu rapor tam borsa kabulü veya tasarımın bitmiş olduğu iddiası değildir.

## Genel sonuç

Proje artık yalnız prototip değil: gerçek Demo hesap okuması ve mevcut yürütme motoruna bağlı bir kullanıcı akışı var. Buna karşılık müşteri tarafından kendi başına kullanılabilecek tamamlanmış bir terminal seviyesinde değil. En büyük fark yeni işlem yeteneği sayısı değil; kullanıcının doğru planı seçmesi, onaylayacağı kapsamı anlaması, başarısızlığın sebebini görmesi ve geçmişte doğru kaydı bulması.

## Yetenek ve kanıt matrisi

| Alan | Mevcut durum | Kanıt / sınır |
|---|---|---|
| Gerçek Demo hesap okuma | Hesap, pozisyon, normal/algo emirler bağlı | Önceki turda gerçek SNAPSHOT SUCCEEDED; emir kabulü değildir |
| Yeni SINGLE / GRID / NEUTRAL | Taslak → sunucu preflight → süreli review → açık onay | Normal motorlar kullanılır; tüm türlerin gerçek borsa E2E kabulü açık |
| Grafik bağlantısı | Aynı uygulamada geçiş, Long/Short çizim revizyonu doğrulama | Kaynak değişince yeniden aktarım; yeni çizim borsadaki işlemi değiştirmez |
| Pozisyon yönetimi | Artır / azalt / kapat / ters yön | Sahip olunan V2 SINGLE ve ilgili uygunluk sınırları; genel hesap pozisyonuna sahiplik atanmaz |
| Takip stopu | Plan takibi + native trailing yolları | Yerel takip sürekli worker gerektirir; native ve yerel takip aynı kavram değildir |
| Emir iptal / timer | Normal-algo kimlikleri ayrı, koruma kontrolleri mevcut | Timer kira ve heartbeat sınırları var; yeniden başlatmada otomatik yeniden kurma yok |
| Batch | Oluştur / amend / iptal | Üye sonuçları ayrı; farklı semboller, plan yetkisi ve risk profili koşulları var |
| Sorgu / geçmiş / export | Adlandırılmış, sınırlı yollar | Sınırlı snapshot tam geçmiş değildir; export işi tamamlanmış indirme sayılmaz |
| Worker / kurtarma | OS kilidi, kalıcı journal, belirsizlikte durma, kontrollü devam | Worker API'den ayrı başlatılır; sistem yeniden başlatmasında servis garantisi yok |
| AI / diğer ürünler / müşteri yayını | Bu Bot terminalinde teslim edilmedi | Canlı para, diğer ürünler ve AI strateji üretimi kapsam dışı |

## Bulgular

| No | Öncelik | Bulgu ve etkisi | İlgili kaynak | Karar |
|---|---|---|---|---|
| B01 | P1 | Batch ve ters yön seçimi yalnız `plan_id` kullanıyor. Aynı planın birden fazla sürümü varsa seçilen sürüm kesin değil; batch fazladan sürümleri dahil edebilir. Sunucu reddi güvenlik sınırıdır ama kullanıcı seçiminin doğru olması gerekir. | BotLiveCommands.tsx | İlk turda düzelt |
| B02 | P1 | Komut/oturum onayında kapsam ve parametreler çoğunlukla JSON. Hesap geneli iptal, ortak USD-M/COIN-M modu veya pozisyon kapatmanın etkisini okumak zor. | BotLiveReview.tsx | İlk turda insan tarafından okunur özet |
| B03 | P1 | `FRESH` worker hata koduyla birlikte dönebilir. Frontend yalnız FRESH'e bakarsa kilit/depo hatasında yeni iş kuyruğa eklemeye devam eder. | bot_inbox.py, BotConnected.tsx | İlk turda hata ve kuyruk görünürlüğü |
| B04 | P1 | Otomatik SNAPSHOT her yenilemede kalıcı ve tam sonuçlu yeni kayıt oluşturuyor. Büyük hesapta DB büyümesi ve son 100 kayıtta finansal işlemlerin kaybolması riski var. Bu kontroldeki gerçek DB'de 8 snapshot / yaklaşık 30 kB vardı; bugün büyük arıza değil, büyüme problemi. | bot_inbox.py, BotConnected.tsx | İlk turda log filtresi; saklama/özet snapshot tasarımı ayrı tur. Mevcut geçmiş silinmeyecek |
| B05 | P1 | Güvenli hata kodları var fakat preflight nedenleri fazla genel. Bakiye, hesap modu, filtre ve risk reddi aynı kullanıcı mesajına düşüyor. | bot_worker.py, botApi.ts | Alan bazlı, sabit ve hassas veri içermeyen tanı sözleşmesi ayrı tur |
| B06 | P1 | Canlı forma prototipten gelen 90000/88000/94000 gibi sabit fiyatlar taşınıyor. Bunlar güncel fiyat değildir; preflight korusa da kullanıcı niyeti belirsizleşebilir. | App.tsx, botPrototype.ts | Boş yeni plan veya kullanıcı tarafından açıkça istenen grafik/mark aktarımı tasarlanacak; risk parametreleri sessizce değiştirilmez |
| B07 | P2 | Süresi dolmuş veya uygun olmayan planlar yönetim seçiminde ayıklanmıyor; oturum/form uygunluğu çoğunlukla ancak sunucuda anlaşılır hale geliyor. | BotLiveCommands.tsx | İlk turda sürüm ve temel durum filtresi; kalan uygunluk sunucuda |
| B08 | P2 | Yığılmış CSS kuralları aynı sınıfları tekrar tekrar eziyor. Görsel düzeltme maliyeti ve responsive regresyon riski yüksek. | botTerminal.css | Yeni büyük görünüm değişikliğinden önce bağlı stil dosyası/bileşen ayrımı |
| B09 | P2 | BotConnected; auth, polling, hesap, emirler, yönetim ve geçmişi tek bileşende topluyor. Alt bölümler için hata sınırı, liste sayfalama ve sonuç yükleme durumu eksik. | BotConnected.tsx | Parçalama ve odak/klavye turu ayrı geliştirme |
| B10 | P2 | Gelişmiş işlemler fazla teknik: kimlikler elle giriliyor, bazı enumlar kullanıcıya ham gösteriliyor. Formlarda `name`, alan bazlı hata ve etiket/odak iyileştirmesi gerekli. | BotLiveCommands.tsx, BotPlanForm.tsx | Seçiciler ve form erişilebilirliği turu |
| B11 | Yayın engeli | Yerel otomatik giriş yalnız localhost içindir. Müşteri kimliği, yetki/hesap ayrımı, TLS, servis yöneticisi ve dağıtım kabulü yok. | session.py, settings.py, local_bot_environment.py | Yerel çalışma korunarak ayrı yayın aşaması |
| B12 | Kabul açığı | Konsol, dar ekran, bütün review türleri ve dolu/boş/belirsiz durumların bu sürümde tam canlı tarayıcı kabulü yok. DevTools profil çakışması sürüyor; eski ekran görüntüsü yeni kabul sayılmaz. | Testler / browser ortamı | Otomatik testlerden ayrı açık tutulacak |

## Korunacak güvenlik omurgası

- HTTP borsa anahtarı yüklemez; finansal yürütme yalnız ayrı ve açıkça yetkilendirilmiş worker'da olur.
- Onay; review kimliği, digest, hesap, süre, risk profili, plan sürümü ve yeniden preflight'a bağlanır. Çift tıklama aynı review için ikinci yürütme oluşturmaz.
- Belirsiz finansal sonuç yeni POST olarak otomatik tekrarlanmaz. Rezervler doğrulama olmadan serbest bırakılmaz.
- Tutarlar sunucuda Decimal; istemcide fiyat/miktar metinleri korunur. Risk profilini tarayıcı belirlemez.
- Özet iş listesi büyük sonuç gövdelerini okumaz; ayrıntı talebinde bütünlük doğrulanır. Kuyruk başarısı borsa başarısı diye gösterilmez.

## Geliştirme sırası

1. **İlk tur:** kesin sürüm seçimi, okunur review özeti, worker hata/kuyruk durumu, geçmiş filtresi. Finansal çekirdeğin davranışı genişletilmeyecek.
2. **İkinci tur:** yeni plan başlangıç değerleri, alan bazlı tanılar ve işlem uygunluğu; kontrollü snapshot saklama/caching tasarımı. Mevcut finansal journal korunacak.
3. **Üçüncü tur:** CSS/bileşen ayrıştırma; masaüstü, dar ekran, odak ve tam kullanıcı senaryosu kabulü.
4. **Sonraki kapı:** kullanıcı tarafından onaylanan gerçek Demo emir kabul matrisi; ardından ayrı müşteri yayını. İzole test sayısı bu kapıların yerine geçmez.

## Başlangıç doğrulaması

Bot terminali + hardening + timer admission: **42 test geçti**. Önceki tam frontend paketi **482 test**. İlk tur sonunda güncel sonuçlar aşağıya eklenecek. DevTools bu incelemede `chrome-profile already running` hatası verdi; kullanıcı tarayıcısı kapatılmadı.

## Uygulanan ilk tur ve sonuçlar

- **B01:** Batch ve ters yön seçicileri `plan_id + version` üzerinden kesin sürümü seçer. Batch; kaybolmuş, yetkisiz, aynı sözleşmeyi tekrarlayan veya SINGLE olmayan seçimi reddeder. Ters yön seçicisi kaynak oturumun sözleşmesini ve karşı yönünü gözetir. Sunucu son otoritedir.
- **B02:** Komut onayında işlem adı, hesap/sözleşme kapsamı, tutarlar, seçili plan sürümleri ve hedef emir kimlikleri okunur biçimde gösterilir. Hesap geneli iptal, ortak ürün ayarı, pozisyon kapanışı ve zamanlayıcı etkileri açıklanır. Teknik JSON ayrıntı olarak korunur; süreli açık onay koşulları değişmez.
- **B03:** Hata bildiren FRESH worker yeni otomatik hesap okumaları için hazır sayılmaz. Kuyrukta bekleyen/işlenen talep sayıları ve uzun bekleme süresi gösterilir. Sayaçlar yalnız geçerli sahibin kayıtlarını içerir.
- **B04 kısmi:** Kayıtlar varsayılan olarak otomatik SNAPSHOT kayıtlarını gizler; kullanıcı isterse gösterir. Sunucu filtresi son 100 sınırından önce uygulanır. Hiçbir eski kayıt silinmedi; snapshot saklama/büyüme sorunu henüz çözülmüş sayılmaz.
- **B07 kısmi:** Plan sürümü, temel durum ve strateji uygunluğu ayıklanır. Süre sonu ve tüm hesap uygunluğu kuralları için ilave çalışma gerekir.

Doğrulama: **489/489 frontend testi**, **44/44 ilgili Python testi**, TypeScript kontrolü ve üretim derlemesi başarılı. İşlem geçmişi filtresinin sınırdan önce uygulandığı, kayıtların korunduğu ve kuyruk sayacının sahipler arasında karışmadığı test edildi. Bu tur tam Python deposu testi çalıştırılmadı.

Güncel yerel API yeniden başlatıldı. Gerçek serviste `/api/bot/status` worker FRESH, yürütme kapalı ve boş kuyruk döndü; geçmiş 8 hesap okumasını saklamaya devam ederken işlem filtresi 0 kayıt döndürdü. Bot sayfası HTTP 200. Finansal komut veya emir gönderilmedi.

**Açık kabul:** DevTools profil çakışması tekrarlandı; güncel görünümün masaüstü/dar ekran, kaydırma ve klavye turu bu oturumda doğrulanamadı. HTTP yanıtı ve bileşen testleri görsel kabul yerine sayılmaz. B05/B06/B08–B12 ve B04/B07 kalan işleri yukarıdaki geliştirme sırasındadır.

## DevTools yeniden bağlantısı ve ikinci arayüz turu

DevTools sonraki oturumda başarıyla bağlandı. Yerel gerçek Demo hesabı üzerinden Hesap, Yeni işlem, Emirler, Yönetim, Kayıtlar ve Geri bildirim sekmeleri gezildi. Hesap boş pozisyon/oturum ve emir listeleriyle incelendi; dolu hesap ve finansal onay kabulü bu kontrolün kapsamında tamamlanmış değildir.

Uygulanan düzenlemeler:

- Hesap sekmesindeki ikinci plan formu kaldırıldı; yeni plan Yeni işlem sekmesinde veya grafiğin işlem panelinde hazırlanır.
- Yeni işlem; strateji/sözleşme, giriş/risk ve ileri ayarlar olarak üç anlamsal bölüme ayrıldı. Geniş ekranda üç, orta ekranda iki, telefonda tek sütun kullanılır. İlgili yeni düzen `botConnectedLayout.css` içinde sınırlıdır; mevcut bütün CSS henüz yeniden yapılandırılmadı.
- B06'nın başlangıç değerleri sorunu düzeltildi: canlı taslakta fiyatlar, bütçe, grid bantları ve tetik fiyatı boştur. Prototip örnekleri yalnız `mode=preview` içinde kalır. Grafik aktarımı mevcut kaynak/revizyon kontrolüyle çalışmaya devam eder.
- Yönetimde yüzde/miktar, izole/çapraz ve tetik referansı seçenekleri okunur etiketlerle gösterilir; sunucuya gönderilen enum değerleri korunur.
- Ana form ve yönetim alanlarına anlamlı `name` değerleri eklendi. Tarayıcı simgesi 404 isteği kaldırıldı.

Tarayıcı kanıtı: 1440×900 masaüstü, 768×1024 orta ekran ve 390×844 mobil emülasyonu. Mobilde altı sekmede sayfa yatay taşması yok. SINGLE/GRID/NEUTRAL geçişlerinde örnek fiyat oluşmadı; ileri bölümler açıldığında ve en alta kaydırıldığında ön kontrol düğmesine erişildi. Tam Bot'ta kaydırma sahibi `.bot-view`; başlık sayfayla kayar. Grafikte 1440 px genişlikte panelin sol sınırı grafik alanının sağ sınırıyla aynı (1070 px); 390 px panelde yatay taşma yok ve alt düğme erişilebilir. Tab ile sözleşme alanına geçiş ve görünür odak çerçevesi doğrulandı. Son yeniden yüklemede konsolda hata/uyarı yok.

**490/490 frontend testi**, TypeScript kontrolü ve üretim derlemesi başarılı. Bu tur backend veya finansal yürütme davranışı değiştirilmedi; finansal emir gönderilmedi. Görsel kabulün bağlantı engeli kalktı; dolu listeler, tüm review türleri, bütün klavye senaryoları ve gerçek Demo emir kabul matrisi hâlâ ayrı kabul işleridir. B05, snapshot saklama/büyümesi ve kapsamlı stil/bileşen sadeleştirmesi sonraki önceliklerdir.

## 18 Kasım: doğrulama ve uygunluk turu

- SINGLE fiyat/bütçe alanlarında, GRID bant/bütçe/aralık alanlarında ve yön/global stop ilişkilerinde alan bazlı hata gösterimi var. Hata metinleri `aria-describedby` ile alana bağlı; ilk hatalı alan odaklanır. Ayrıntılı hedef, trailing ve hesap ayarlarının mevcut doğrulaması özet mesajla korunur. Hatalı taslak; ön kontrol, kayıt ve toplu giriş yetkisi isteği göndermez.
- Kesin EXCHANGE/REJECTED tanısında -2019, -2027, -4061, -1111 ve -4164 için anlaşılır açıklamalar gösterilir. Kaynak: [Binance USD-M hata kodları](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/error-code). Genel ValueError/preflight reddi için neden uydurulmaz; backend'in yapılandırılmış alan bazlı ret sözleşmesi hâlâ açık iştir. UNKNOWN/NOT_SENT/READ_FAILED bu açıklamalarla kesin ret diye sunulmaz; otomatik yeniden gönderim eklenmedi.
- Planın `expires_at` ve toplu giriş yetkisinin `approval_until` sınırları seçimde ve gönderim hazırlığında kontrol edilir. Seçim yetkiyi yenilemez. Yönetimde kapanmış veya SINGLE olmayan oturumlar gösterilmez; tüm ayrıntılı operasyon uygunluğu son olarak sunucuda doğrulanır.
- Dolu tablo deneyi gerçek hesaba yazmayan, ayrı browser context içindeki açıkça işaretli örnek veriyle yapıldı. 390 px ekranda içerik genişliğinin tabloyla büyüyüp kesilmesi bulundu ve düzeltildi: tablo kapsayıcıları 357 px içinde 624/654 px içeriği yatay kaydırabiliyor. Gerçek hesap ekranına örnek veri karıştırılmadı.
- Örnek veriyle PLAN review açıldı: mobilde pencere 358 px, ekran 390 px; onay kutusu metinle aynı satırda 16 px; salt okunur worker onayı kapalı tutuyor. Fixture yalnız SNAPSHOT ve PREVIEW_PLAN istekleri gördü, finansal CONFIRM yapılmadı. Gerçek sayfada boş formun dört alanı işaretlemesi ve giriş fiyatına odaklanması Chrome'da doğrulandı.

Sonuç: **497/497 frontend testi**, TypeScript ve üretim derlemesi başarılı; `git diff --check` temiz. Son iki değişiklik CSS kapsamındaydı ve yeniden derlenip Chrome'da doğrulandı. Bu aşamada backend yürütme davranışı değiştirilmedi. Gerçek Demo emir kabulü, dolu bot oturumu senaryoları ve COMMAND/CONTROL review türlerinin tüm görsel varyantları henüz tamamlanmış sayılmaz.

## 18 Kasım: yapılandırılmış backend ret nedenleri

`PreflightRejection(ValueError)` mevcut doğrulama koşullarına sabit, izinli bir neden kodu ekler. SINGLE hesap modu/kaldıraç/teminat uyumsuzluğu, uygun olmayan/dolu hesap, eski görünüm, yetersiz teminat, küçük bütçe, stop/hedef dışındaki fiyat ve fiyat sapması ayrı nedenlerle raporlanır. Ortak portföy değerlendirmesinde nominal, pozisyon sayısı, işlem/toplam/günlük risk ve likidasyon tamponu retleri de kodlanır. Mevcut hata metinleri, Decimal hesaplamaları, eşikler ve kontrol sırası korunur.

Kuyruk sonucu örneği:

```json
{"state":"FAILED","error_code":"BOT_VALIDATION_OR_PREFLIGHT_REJECTED","result":{"diagnostic":{"category":"PREFLIGHT","reason":"ACCOUNT_SETTINGS_MISMATCH","correlation_id":"job-..."}}}
```

Tanı yalnız PREVIEW_PLAN, PREVIEW_PLAN_AUTHORIZATION ve PREVIEW_COMMAND için iletilir. CONFIRM, READ_COMMAND veya RECONCILE aynı istisnayı alırsa mevcut genel tanı korunur; geçmiş finansal adımların teslim durumu hakkında çıkarım yapılmaz. Ham exception metni/bakiye/anahtar aktarılmaz. Genel ValueError, bilinmeyen nedenler ve henüz kodlanmamış kontroller genel reddi kullanmaya devam eder. Arayüz 15 izinli neden için açıklama sunar; hata mesajı kullanıcı talebi sonrasında odaklanır. Otomatik yeniden gönderim eklenmedi.

Doğrulama:

- 498/498 frontend testi, TypeScript ve üretim derlemesi başarılı.
- Gerçek preflight fixture'larıyla hesap modu, hesap ayarı, veri yaşı, teminat ve risk retleri kuyruk sonucuna kadar test edildi; POST ve oturum oluşmadığı doğrulandı. Özel istisna metni sızıntısı ve CONFIRM'in yanlış etiketlenmemesi ayrıca test edildi. Bot terminalindeki 25 test geçti.
- Tam Python taraması 1704 test çalıştırdı: 1700 geçti, çalışan worker kilidiyle çakışan 2 test ve eski replay raporuna bağlı 2 test başarısızdı. Worker kontrollü durduruldu; replay 36/36 izole senaryo ile yeniden üretilerek `replay_validation.json` yenilendi. İlgili batch, product discovery ve chart replay dosyalarındaki 117 test tekrarında tümü geçti. Tam paket ikinci kez çalıştırılmadı.
- 390 px Chrome emülasyonunda, gerçek hesaba yazmayan ayrı context içindeki örnek ret açıklaması ve hata odağı doğrulandı. Fixture yazımları yalnız SNAPSHOT/PREVIEW_PLAN oldu; CONFIRM yok. Test context'i kapatıldı. Gerçek yerel sayfada konsol hatası/uyarısı yok.
- Yerel worker güncel kodla yeniden başlatıldı: FRESH, hata yok, yürütme kapalı. Gerçek emir gönderilmedi.

Kalan kapsam: bütün grid/komut/filtre retlerinin ayrı kodlarla kapsanması, sunucu tanılarının doğrudan ilgili form alanlarına bağlanması, COMMAND/CONTROL görsel kabul varyantları, snapshot saklama politikası ve gerçek Demo emir kabul matrisi.

## Canlı finansal hesaplama teslimi

Mark, derlenmiş plan miktarı/teminatı, hedef kârı, fiyat getirisi, ROE, stop sonucu, getiri/risk ve model likidasyonu için salt okunur ANALYZE_PLAN yolu eklendi. Açık pozisyonlarda borsa likidasyonu ve teminat getirisi gösteriliyor. İşlev sınırları, gerçek Demo denemesi, doğrulama ve istek ağırlığı kaynakları [LIVE-CALCULATIONS.md](LIVE-CALCULATIONS.md) belgesinde. 499 frontend testi, ilgili backend/transport/kota testleri ve üretim derlemesi başarılı; gerçek emir gönderilmedi.
