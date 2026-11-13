> Tarihsel arşiv: 9 Kasım 2026 yön değişikliğinden önceki metin. Güncel ürün kararı için [aktif hedeflere](../../../01-PROJE-VE-HEDEFLER.md) bakın. İçerik korunmuştur; yerel Markdown bağlantıları arşiv konumuna uyarlanmıştır.

# Basitten karmaşığa geliştirme planı

## 6 Kasım 2026 öncelikli işlem altyapısı programı

Yeni kullanıcı talebiyle genel demo işlem yetenekleri grid dahil tamamlanacak.
Önce [yetenek envanteri ve A0–A12 teslim sırası](../../../06-BINANCE-DEMO-YETENEK-ENVANTERI-VE-GELISTIRME-SIRASI.md)
esas alınır. A0 araştırması ve A1 sürümlü katalog/salt okunur keşif uygulaması
tamamlandı. 12 GET kontrolü gerçek demoda geçti; toplam 150 test başarılı.
A2 ortak istek/dayanıklılık katmanı sıradadır. Grid yürütücüsü henüz yoktur.
A1 keşif/kayıt → A2 dayanıklı istek → A3 plan v2/portföy risk → A4 kaldıraç ve
modlar → A5 emir ailesi/yönler → A6 korumalar → A7 olay/uzlaştırma → A8 LONG
grid → A9 gelişmiş grid/planlar → A10 kullanıcı/servis → A11 tamamlayıcı uçlar
→ A12 diğer demo ürünleri. Grid için gerekli alt işler önce teslim edilir.
134 testlik son durum grid yürütücüsünün tamamlandığı anlamına gelmez.

Bu program aşağıdaki analiz/TradingView/Telegram ürün hedeflerini iptal etmez;
önce emir, risk ve strateji yürütme eksiklerini giderir. Her yetenekte belgeli,
adaptör, çevrimdışı, demo doğrulandı ve ürün akışı hazır durumları ayrı tutulur.
Araştırmada hesap veya emir değişimi yapılmadı; sonraki geliştirmeler eski
işlem onaylarını yeni girişler için tekrar kullanamaz.

Her aşama küçük, çalıştırılabilir bir çıktı ve doğrulama raporuyla bitmeli. Önceki aşamanın temel belirsizliği çözülmeden kapsam büyütülmemeli.

Son plan güncellemesi: 5 Kasım 2026. Hedefler [01-PROJE-VE-HEDEFLER.md](../../../01-PROJE-VE-HEDEFLER.md), yetki/işlem sözleşmesi [03-MIMARI-VE-ISLEM-SOZLESMESI.md](../../../03-MIMARI-VE-ISLEM-SOZLESMESI.md) içindedir. Yeni TradingView aşaması 9'dur; önceki değerlendirme ve sunucu aşamaları sırasıyla 10 ve 11'e taşınmıştır.

## Mevcut durum ve yürütme ilkesi

0–1 temel kapsamı çalışıyor. 2–3'ün tek LONG/one-way demo kapsamı, kalıcı kayıtları ve watchdog'u doğrulandı. Aşama 4'ün şema v1, yerel Mod A/B yetkisi, kademeli hedefler ve giriş fiyatına stop taşıması eklendi; bu kapsam o aşamada 86 ağsız testle doğrulandı. Aşama 5 ile toplam 105 teste ulaşıldı. Kanıt ve sınırlar [DOGRULAMA.md](../../../DOGRULAMA.md) içindedir. Yeni plan/kademeli çıkış yolu gerçek demo borsasında henüz onaylanıp yürütülmedi. SHORT/hedge, stop/TP tetiklenerek gerçekleşmesi, Pine/webhook, zengin analiz, Telegram ve canlı hesap kapsamı tamamlanmadı.

Aşama 4'ün yerel plan/yetki/kademeli yönetim kapsamı kodlandı ve ağsız doğrulandı; gerçek demo senaryosu için somut kullanıcı planı/onayı gereklidir. Yeni sinyal akışı, uzaktan onay/yetkilendirme katmanı tamamlanmadan otomatik girişe bağlanmaz. Eski demo giriş deneyleri açık `--test-only` gerektirir; üretim sinyal yolu değildir. Bu planı kaydetmek yeni emir veya canlı işlem yetkisi vermez.

## 0 — Projeyi ve erişim sınırlarını belirle

Mevcut klasörü incele; varsa kodu ve yerel yönergeleri oku. Yoksa sade Python proje iskeleti oluştur. Yapılandırma, loglama, test ve bağımlılık yönetimini kur. Demo ve canlı ortamları kesin ayır; varsayılanı demo yap. Gizli bilgileri sürüm kontrolüne alma; örnek yapılandırmada yalnızca boş alanlar kullan.

Binance Global / Binance TR ayrımını, hedef Futures ürününü ve hesap modunu belgele. Hesabın Futures erişimi ile anahtarın Futures yetkisini ayrı doğrula. Kullanıcıdan gizli anahtarı sohbete yapıştırmasını isteme. Demo erişimi, canlı hesap uygunluğu yerine geçmez.

Çıktı: çalıştırılabilir iskelet, kurulum açıklaması, erişim kontrol listesi. Gerçek emir gönderilmez.

## 1 — Demo bağlantısı ve yalnızca okuma

Güncel resmî Binance belgelerinden bağlantı adreslerini ve desteklenen Python istemcisini doğrula. Eski endpointleri ezberden kullanma. Demo anahtarıyla kimlik doğrulamasını, sunucu saatini, bakiyeyi, açık emirleri, pozisyonları ve sembol kurallarını sorgula. IP/izin/zaman hatalarını anlaşılır göster. İlk bağlantı prototipi AI gerektirmez.

Çıktı: bağlantı teşhis komutu ve demo hesap durum raporu. Geçiş koşulu: doğru ortamın kullanıldığının ve okuma işlemlerinin çalıştığının doğrulanması.

## 2 — Demo emir araç kutusu

Önce bekleyen limit emri oluştur, sorgula ve iptal et. Ardından demo pozisyon açma, kısmi kapatma ve tam kapatma ekle. Koruyucu stop ve kâr alma emirlerini güncel Futures API'lerine göre uygula; emirlerin kabul edildiğini ve pozisyonla ilişkisini doğrula. Emir kabulü ile gerçekleşmeyi ayır.

Fiyat/miktar adımı, minimum tutar, hesap/pozisyon modu ve izin uyumluluğunu kontrol et. Sayısal emir değerlerinde uygun ondalık hassasiyet kullan.

Çıktı: desteklenen yetenek tablosu ve demo senaryo kayıtları. Canlı işlem açılmaz.

## 3 — Dayanıklı emir ve risk motoru

Durum: SQLite emir niyetleri, tekrar önleme, demo risk profili, tek yürütücü kilidi, yönetilen oturum ve watchdog mevcut. Gerçek demo üzerinde ani süreç sonlandırma, iki ayrı süreçte devralma ve iptal edilmiş stopun tek onarımı doğrulandı. Ağ hatası ve koruma onarılamama davranışı çevrimdışı hata enjeksiyonuyla sınandı. Sürekli sunucu hizmeti henüz kurulmadı; bunlar tüm strateji/hesap modlarının tamamlandığı anlamına gelmez.

İşlem planı şemasını ve durum makinesini uygula. Tekrarlanan isteklerden çift emir oluşmasını önle. Zaman aşımı sonrası körlemesine tekrar gönderme; önce emri sorgula. Kısmi gerçekleşme, bağlantı kopması, yeniden başlatma ve manuel işlem değişikliklerini uzlaştır.

İşlem başına risk, toplam açık risk, pozisyon sayısı, günlük kayıp ve veri eskiliği sınırlarını yapılandırılabilir yap. Kullanıcı değerleri belirleyene kadar canlı işlem etkinleşmesin. Yeni girişleri durdurma ile açık pozisyonların korunmasını ayrı ele al. Kritik stop hatasında izlenecek çıkış politikasını açıkça tanımlayıp test et.

Çıktı: hata enjeksiyonu testleri ve yeniden başlatma sonrası doğru durum kurtarma.

## 4 — AI olmadan değişken planları çalıştır

Durum: şema v1, yerel `plans` komutları, tek kullanımlık A onayı, B etkinleştirmesi, sembol rezervasyonu, sürüm/süre/iptal denetimi ve risk/watchdog bağlantısı mevcut. Tek LONG/one-way demo MARKET giriş, 1–8 kademeli hedef, kalan miktar yönetimi ve izinli hedef tamamlanınca giriş fiyatına stop taşıma eklendi. Çıkış/stop geçişi ortasında yeniden başlatma ve kısmi fill senaryoları ağsız sınandı; gerçek kullanıcı planı onaylanmadı. Ara hedefler çalışan watchdog'un mark fiyatı kontrollerinde MARKET çıkışla uygulanır; son hedef borsada closePosition yedeğidir. Komisyon dahil net başa baş garanti edilmez. SHORT/hedge, pozisyon artırma, yeniden giriş ve teminat türü reddedilir. Giriş koşulu her `plans run` çağrısında bir kez kontrol edilir; sürekli giriş koşulu işçisi daha sonra eklenir.

Genel plan şeması, sürümleme, durum makinesi ve yetki kayıtlarını oluştur. Mod A yeni girişte kullanıcı onayı ister; Mod B yalnızca kullanıcının belirli sürümü açıkça etkinleştirdiği planı kendi sınırlarında ek onaysız yürütür. İki mod aynı risk/emir altyapısını kullanır.

Ortam, ürün/sözleşme, yön, giriş koşulu, sayısal stop/Fibonacci/hedefler, miktar türü, risk profili, son geçerlilik, çalıştırma sayısı ve izinli yönetim eylemlerini zorunlu kıl. "100 dolar" nominal/teminat/azami kayıp ayrımı yapılmadan plan etkinleşmez. Miktarı bağımsız risk motoru hesaplar.

AI olmadan koşullu giriş, geç/tekrarlı/yetkisiz onay, süre sonu, ret, iptal, plan değişimi, kademeli çıkış, maliyete stop taşıma, tek çalıştırma ve çelişen plan senaryolarını sına. Desteklenmeyen özellik açık nedenle reddedilir. Aynı sembol/pozisyon için çelişen etkin planlar engellenir. Plan iptali girişleri durdurur, açık pozisyonun korumasını kaldırmaz; kapatma ayrı eylemdir.

Geçiş koşulu: Mod A onayı veya Mod B etkinleştirmesi olmadan yeni giriş yok; sürüm/ortam/kapsam uyuşmazlığında yürütme yok; teknik tekrar çift emir üretmez. Onay sonrası güncel fiyat/veri/risk kontrolü zorunludur. Önemli değişiklik yeni yetki ister. Her olası strateji destekleniyor sayılmaz.

## 5 — Piyasa verisi ve temel çoklu zaman dilimi analizi

Durum: ayrı anahtarsız salt okunur canlı adaptör, SQLite mum/rapor deposu, W/D/4H/1H/15M, EMA20/50, Wilder RSI14/ATR14, hacim karşılaştırması ve 7 tamamlanmış UTC gününün taker/toplam hacim raporu eklendi. BTC/ETH için 3010 gerçek mum okundu; beşer zaman dilimi OK ve önbellekten aynı göstergeler/girdi özeti doğrulandı. Toplam 105 ağsız test başarılı. `market report` emir yoluna bağlanmaz; `BEKLE` ilk sürümde işlem stratejisinin kapalı olduğunu belirtir. REST anlık görüntüsü vardır; WebSocket/sürekli yenileme, piyasa yapısı, dominans/akış ve haber/AI henüz yoktur.

İlk geliştirme evrenini BTC ve bir altcoinle dar tut; coin seçimini yapılandır. Mumları sakla, eksik ve tekrarlı veriyi denetle. EMA, RSI, ATR ve hacim ölçülerini ekle. Haftalık/günlük büyük resmi, 4H/1H yapıyı, 15M giriş koşullarını değerlendir. Başlangıçta sade, açıklanabilir kurallar kullan.

Canlı piyasa analiz verisini demo yürütme verisinden ayrı sakla; spot/perpetual, mark/index/son fiyatı karıştırma. Son 7 tamamlanmış UTC gününün günlük hacim tablosunu, karşılaştırma dönemini ve değişimini üret. Açık gün ayrı işaretlenir. Her özellikte veri zamanı, kaynak, birim ve eksiklik kaydı bulunur.

Tepe/dip algoritmasının ancak sonraki mumlarla doğrulanabilen noktalarını gerçek zamanlı biliniyormuş gibi kullanma. Kapanmamış mumları ayrı işaretle. Çıktı: gerekçeli analiz kayıtları; henüz otomatik strateji devreye alınmaz.

## 6 — Piyasa yapısı ve paralel analiz

Destek/direnç, HH/HL, LH/LL, BOS/CHoCH tanımlarını açık algoritmik kurallarla ekle. Dominans ve TOTAL3 için ayrı sağlayıcı seç; kaynak, kapsam, gecikme ve maliyeti belgele. Eksik veri uydurma. Altcoin/BTC doğrudan bulunmuyorsa zaman hizalı oran türetmenin sınırlamalarını kaydet.

BTC/ETH ve altcoin göreli gücünü birlikte raporla. Korelasyon, funding, open interest ve likidasyon verileri daha sonraki genişletmeler olabilir; eksiksiz veri varmış gibi davranma.

Fibonacci ve çizgi kesişimi/kırılım tanımlarını algoritmik hâle getir. Hacim, taker alıcı/satıcı baskısı ve borsalara varlık giriş/çıkış/net akışını ayrı alanlar yap. Akış sağlayıcısını kapsam, gecikme, maliyet ve borsa adres etiketleme kalitesiyle seç. 7 günlük akış tablosunu birim ve kaynakla sun; veri yoksa eksik işaretle. Hacim yeni para girişi, borsa akışı tüm piyasa sermaye akışı sayılmaz. Çıktı: kaynağı ve sınırları belli, tekrar üretilebilir rapor.

## 7 — Haber ve AI katmanı

Önce haber toplama, zaman damgası, tekrar ayıklama ve kaynak kayıtlarını kur. Ardından sağlayıcıdan bağımsız AI arayüzü ekle. Model haberleri ve hesaplanmış özellikleri yorumlasın; sayısal gerçeklerin kaynağı kod ve veri sağlayıcısı olsun.

Model çıktısı şemaya uymalı. Haber metni içindeki talimatları güvenilmeyen içerik say; araç ve hesap yetkisi verme. Anahtarları, hesap sırlarını ve gereksiz kişisel verileri modele gönderme. Maliyet, çağrı sınırı, önbellek ve servis kesintisi politikası ekle.

Çıktı: kaynaklı analiz ve işlem planı adayları. Model doğrudan emir göndermez.

Rapor kısa özet ve ayrıntılı bölümden oluşur: LONG/SHORT/BEKLE/ENGELLİ sonucu, destekleyen/karşı çıkan nedenler, görüşü değiştiren koşullar, 7 günlük hacim/akış, zaman dilimleri ve piyasa bağlamı, haber özeti/kaynakları, eksik veriler ve plan/risk bilgileri. Kritik veri yoksa giriş engellenir; alarm bildirimi engellenmez. AI kesintisi/eksik veri durumu kullanıcıya açıkça bildirilir.

## 8 — Telegram, tüm alarm bildirimleri ve kullanıcı onayı

Yetkili kullanıcı/sohbet kontrolü, analiz/durum/durdurma komutları, kalıcı bildirim kuyruğu ve tekrar önleme kur. Modül sözleşmesi aşama 4'te belirlenir; temel bildirim prototipi erken yapılabilir. Kısa özetten ayrıntı mesajlarına erişim sun; gerekirse sonraki aşamada kimlik denetimli, cihazlar arası web raporu ekle. Özel hesap bilgilerini herkese açık bağlantıda sunma.

Her geçerli benzersiz alarm strateji/risk sonucu ne olursa olsun bildirilir. İlk alındı bildirimi tam analizden önce gönderilebilir. Uygun/uygun değil/bekle/engelli sonucu ve gerekçesi raporlanır. Teknik kopyalar aynı olay altında tutulur; farklı alarmlar sessizce düşürülmez. Teslim hatası kalıcı kayda alınır ve tekrar denenir.

Mod A'da belirli plan sürümüne tek kullanımlık Onayla/Reddet, uygun olmayan analizde İzle/Yeniden değerlendir sun. Sert risk engelinde yürütme onayı sunma. Yetkisiz, geç, tekrar veya değişmiş sürüm onayı yürütülmez. Yanıt yoksa giriş yok. Onay sonrası taze koşul/risk kontrolü ve maddi değişiklikte yeniden onay uygula.

Mod B'de plan özeti ve açık etkinleştirme/iptal akışı kur. Her emir/koruma/çıkış bildirilir; izinli eylemler için tekrar onay gerekmez. Risk sınırı veya yetki kapsamı aşılamaz. Sinyal, analiz, plan sürümü, yetki, ret, emir ve sonuç kayıtları ilişkilendirilir.

Geçiş koşulu: onay ve bildirim kesintileri, yeniden başlatma, süre sonu ve aynı butona iki kez basma testleri; kullanıcı yetkisi olmadan yeni giriş oluşmaması.

## 9 — TradingView indikatörü ve webhook

Teknik kuralların Pine'a uygun bölümünü indikatöre dönüştür. Çizimler, çoklu zaman dilimi ve sinyal koşullarında Python ile aynı tanım/sürümü kullan; kapanmış mum, repaint ve ileri bilgi kullanımını test et. Kişisel kullanım önceliklidir; open/protected/invite-only yayınlama ve satış ayrı karardır.

Elle çizime bağlı alarm ile indikatör alarmını ayrı kaynaklar olarak destekle. Sembol, borsa, spot/Futures, sözleşme ve zaman dilimi açık eşleştirilir. Kişisel çizimin bütün koordinatları webhookla geliyor varsayılmaz; sayısal plan alanları veya açık alarm/plan eşleştirmesi kullanılır. Pine'ın Python/AI servisine genel HTTP erişimi veya botun kişisel grafiğe doğrudan çizim basması varsayılmaz.

Kullanıcı çalışan alarmı TradingView arayüzünde etkinleştirir. Hesap planı/2FA gereksinimlerini ve script/ayar değişiminde alarmın yeniden kurulma sürecini güncel resmî belgelere göre doğrula. Alarmın script/ayar sürümünü kaydet.

HTTPS webhook alıcısı, kaynak doğrulama, şema/boyut denetimi, kalıcı hızlı kabul/kuyruk ve tekrar-eski olay denetimi kur. Alarm tek başına işlem yetkisi değildir. Tekrarlanan, geciken, sırası değişen ve teslim edilmeyen olayları test et. Secret webhook mesajına konmaz.

Geçiş koşulu: alarm → her durumda bildirim → analiz → Mod A onayı veya geçerli Mod B ön yetkisi → taze risk kontrolü → demo emir/koruma → sonuç bildirimi. Önce yalnızca kayıt/bildirim; onay sistemi doğrulandıktan sonra açıkça etkinleştirilmiş demo yürütme.

## 10 — Strateji ve uçtan uca değerlendirme

Geçmiş test, ayrılmış test dönemi ve walk-forward değerlendirme oluştur. Gerçek piyasa verisi üzerinde sanal işlemleri demo emir testinden ayrı yürüt. Komisyon, funding, spread, kayma ve veri gecikmesini hesaba kat. Net getiri, drawdown, beklenti, profit factor ve piyasa rejimlerine göre sonuçları raporla. Basit referans stratejiyle karşılaştır.

Model/parametre değişikliklerini sürümle; canlıda kontrolsüz kendini değiştirme uygulanmaz. 45 veya 90 gün geçmesi başarı kanıtı değildir.

Webhook/veri gecikmesi ve insan onayı bekleme etkisini hesaba kat. Mod A/B yetki sınırları, her alarmın bildirimi, ret/bekle/işleme dönüşmeyen sinyaller ve plan iptallerini ölç. Pine, Python ve AI sürümlerini rapora bağla. Demo emir testi ile gerçek piyasa verisindeki sanal strateji performansını karıştırma.

## 11 — Sunucu ve kontrollü canlıya hazırlık

Yerelde doğrulanan uygulamayı güvenli, sürekli çalışan sunucuya taşı. Domain zorunlu değil. Sabit çıkış IP'si, anahtar erişim sınırları, özel yönetim bağlantısı, yedekleme, alarm, zaman senkronizasyonu ve otomatik yeniden başlatma kur.

Webhookun internetten erişilebilir HTTPS adresi gereksinimini ayrıca çöz; yerel test adresi ile sürekli sunucuyu ayır. Domain/sertifika tercihi bu teknik gereksinime göre yapılır. Kullanıcı cihazları Telegram veya kimlik denetimli rapor paneline bağlanır; Binance secret tarayıcıya gönderilmez. Watchdog ve bildirim işçileri için servis/otomatik başlangıç ve gerçek alarm kanalı kur.

Canlıya geçiş için hesap/API uygunluğu, kullanıcı tarafından belirlenmiş risk sınırları, geçerli test sonuçları ve ayrı açık canlı işlem onayı gerekir. Bu doküman gerçek para işlemi başlatma yetkisi değildir. Sunucuya geçmek coğrafi kısıtları aşma yöntemi olarak kullanılmaz.

Canlıya geçişte Mod A ve Mod B yetki kontrolleri de doğrulanmalıdır. Demo planının etkinleştirilmesi canlı ortamı açmaz; canlı risk/kaldıraç/tutar kararları ayrıca alınır.

## Kullanıcı akışı ve yeniden uzlaştırma — 6 Kasım 2026

Demo kullanıcı WebSocket bağlantısı mevcut SINGLE/grid yönetimine eklendi.
Olay → kalıcı bekleme işareti → REST kimlik/dolum/sahiplik doğrulaması →
işareti kaldırma → mevcut onay/risk kontrolleriyle yönetim sırası uygulanır.
Yeniden bağlantı yeni işlem yetkisi vermez; belirsiz emir tekrar gönderilmez.
430 test geçti. Gerçek demo bağlantısı ve ping/pong doğrulandı; gerçek
fill/iptal/stop olayı ve uzun süreli kesinti kanıtı henüz tamamlanmadı.
Ayrıntı: [12-KULLANICI-WEBSOCKET-VE-YENIDEN-UZLASTIRMA.md](../../../12-KULLANICI-WEBSOCKET-VE-YENIDEN-UZLASTIRMA.md).

## Takip stopu, teminat ve servis — 6 Kasım 2026

SINGLE için plan onayına bağlı, varsayılan kapalı takip stopu eklendi.
Stop yalnız sıkılaşır; yeni koruma doğrulanmadan eskisi kaldırılmaz.
Aktif bot pozisyonunda izole teminat komutları oturum/plan sürümüne bağlandı.
Grid yeniden girişte güncel kaldıraç basamaklarını kontrol eder.
Kalıcı bildirim kuyruğu, Telegram göndericisi, sürekli servis, sağlık ve
kontrollü durdurma komutları eklendi. Gerçek mesaj veya otomatik görev başlatılmadı.
466 test geçti; gerçek demo yazma kanıtı ve kalan ürün kapsamı tamamlanmadı.
[13-TAKIP-STOP-TEMINAT-VE-SERVIS.md](../../../13-TAKIP-STOP-TEMINAT-VE-SERVIS.md).

## Çoklu oturum sahipliği ve ortak risk — 6 Kasım 2026

Aynı USD-M demo hesabında farklı sembollü v2 SINGLE/grid planları birlikte
çalışır. Emirler plan/hesap/niyet ve sembolle birlikte borsa kimliğiyle doğrulanır.
Bekleyen emirler ve refill dahil tam risk rezervleri ortak hesap sınırlarından
geçer. Kapanışta yalnız ilgili oturumun rezervi atomik bırakılır; eş oturumun
emirleri korunur. run-many ortak ön kontrol, manage-all/run-all tek süreçli
yönetim sağlar. 497 test geçti; gerçek demo işlemi veya profil/bütçe değişikliği
yapılmadı. Kalan kapsam ve kullanım:
[14-COKLU-OTURUM-VE-ORTAK-RISK.md](../../../14-COKLU-OTURUM-VE-ORTAK-RISK.md).


## Neutral grid teslimi — 6 Kasım 2026

Gelişmiş grid aşamasında neutral yürütücü ve ortak iki taraflı bütçe tamamlandı. Gerçek demo kanıtı ve kalan politikalar bekliyor. Diğer aşamalar bütünüyle tamamlanmış sayılmaz; geliştirme için yeniden onay gerekmiyor.

Ayrıntı: [15-NEUTRAL-GRID-VE-IKI-TARAFLI-YONETIM.md](../../../15-NEUTRAL-GRID-VE-IKI-TARAFLI-YONETIM.md).


## Aktif teminat teslimi — 6 Kasım 2026

Portföy ve teminat aşamasında aktif USD-M çoklu oturum, yönlü grid ve neutral teminat entegrasyonu tamamlandı. Çapraz ürün değerleme, kalan grid politikaları ve gerçek demo kanıtları bekliyor.

Ayrıntı: [16-COKLU-OTURUM-TEMINAT-YONETIMI.md](../../../16-COKLU-OTURUM-TEMINAT-YONETIMI.md).


## Grid takip stopu — 7 Kasım 2026

Yönlü GRID için isteğe bağlı bot takip stopu eklendi. LONG/SHORT watermark ve eşik kalıcıdır; tetikte yeni girişler durur, gerçek kalan miktar kapanış akışına geçer. Native sabit stop korunur; hareketli eşik bot çalışırken izlenir. Neutral/native takip ve diğer politikalar bekliyor. 13 yeni senaryo dahil 573 test geçti; sonuç doğrulama raporuna kaydedildi. Gerçek demo yazma yapılmadı.

Ayrıntı: [17-GRID-TAKIP-STOPU.md](../../../17-GRID-TAKIP-STOPU.md). Kanıt: `reports/development-validation-20261107.json`.


## Grid borsa stopunu yenileme — 7 Kasım 2026

Yönlü GRID için isteğe bağlı `management.trailing.native_stop: true` eklendi. Yeni close-all stop GET ile doğrulanmadan önceki takip stopu kaldırılmaz; başlangıç sabit koruması tutulur. Eski planlar değişmez. 21 yeni senaryo eklendi; tam regresyon sonucu `reports/development-validation-20261107.json` içinde. Gerçek demo yazma kanıtı bekliyor.

Ayrıntı: [18-GRID-BORSA-STOP-YENILEME.md](../../../18-GRID-BORSA-STOP-YENILEME.md).
