> Tarihsel arşiv: 9 Kasım 2026 yön değişikliğinden önceki metin. Güncel ürün kararı için [aktif hedeflere](../../../01-PROJE-VE-HEDEFLER.md) bakın. İçerik korunmuştur; yerel Markdown bağlantıları arşiv konumuna uyarlanmıştır.

# Kişisel kripto analiz ve işlem sistemi proje taslağı

**Kullanıcı beklentileri, amaç, yapılabilirlik ve geliştirme kapsamı**

Belge tarihi: 6 Kasım 2026 · Sürüm: 1.0 · Proje: agentrader

Bu taslak, projenin hangi ihtiyacı karşılayacağını, kullanıcının nasıl bir deneyim istediğini ve mevcut uygulamanın bu hedefe ne kadar yaklaştığını tanımlar. Geliştiriciye devredilebilecek bir kapsam belgesi ve sonraki geliştirme kararları için ortak başvuru metni olarak kullanılabilir. Yeni işlem açma, risk sınırlarını değiştirme veya gerçek hesaba geçme yetkisi vermez.

## 1 Projenin özü ve ana sonuç

Hedef, kullanıcının TradingView üzerindeki teknik analiz yaklaşımını; kaynakları belli piyasa ve haber verileriyle zenginleştiren, kararını açıklayan, kullanıcı yetkisini denetleyen ve Binance üzerinde belirli planları uygulayan kişisel bir sistem kurmaktır.

Kullanıcı analizden ve karar sürecinden kopmak istememektedir. Sinyalin neden oluştuğunu, hangi verilerin bu fikri desteklediğini, karşı görüşlerin neler olduğunu ve işlem açılırsa ne kadar risk alınacağını görmek istemektedir. Buna karşılık girişten sonra stop, kademeli çıkış ve pozisyon takibi gibi tekrar eden işleri botun yürütmesini istemektedir.

**Genel değerlendirme:** Bu beklentilerin önemli bölümü teknik olarak yapılabilir. Uygun çözüm, TradingView ve Pine ile Python tabanlı analiz, onay, risk ve emir katmanlarının birlikte çalışmasıdır. Bazı beklentiler doğrudan aynı biçimde gerçekleştirilemez: kişisel TradingView hesabındaki bütün elle çizimleri otomatik okumak, kapalı kaynak indikatörlerin iç mantığına erişmek veya Python sisteminin tamamını tek Pine indikatörünün içine taşımak için desteklenmiş bir yol varsayılamaz. Bu noktalar için alarm, açık plan eşleştirmesi ve sayısal seviye girişi kullanılmalıdır.

Mevcut proje, demo emir ve koruma altyapısına sahip bir geliştirme prototipidir. Kullanıcının istediği tam analiz ve kontrol ürününün tamamlandığı anlamına gelmez. Özellikle TradingView bağlantısı, Telegram üzerinden gerçek kullanıcı onayı, zengin piyasa bağlamı, haber ve yapay zekâ katmanları henüz tamamlanmamıştır.

## 2 Kullanıcının istediği sistemin kendi ağzından ifadesi

> TradingView üzerinde kendi analizimi ve çizimlerimi kullanmak istiyorum. Çizgiye bağlı koşul veya indikatör alarmı oluştuğunda bot bundan haberdar olsun. Bana yalnızca al ya da sat demesin; nedenlerini, son günlerdeki hacmi, varsa borsalara giriş ve çıkışları, piyasanın genel durumunu ve ilgili haberleri anlatsın. İşlem uygun bulunmasa bile alarmı ve gerekçesini bana göstersin. Varsayılan olarak yeni işlem benim onayımla açılsın. İstersem belirli giriş, stop ve hedefleri önceden tanımlayıp bu sınırlar içinde otomatik yönetim yetkisi verebileyim. Onayladığım pozisyonun başında sürekli beklemek zorunda kalmayayım. Telefonumdan veya başka cihazdan durumu görebileyim. Sistem gerçek paraya geçmeden önce mümkün olan bütün yönleriyle demoda geliştirilsin ve test edilsin.

Bu ifade bir işlem stratejisinin kesin kurallarını değil, ürünün davranışını tanımlar. Hangi çizginin nasıl seçileceği, kesişmenin hangi anda geçerli sayılacağı, hangi haberlerin önem taşıdığı ve hangi risk değerlerinin kullanılacağı ayrıca tanımlanmalıdır.

## 3 Çözülmek istenen sorunlar

Kullanıcı bugün grafik, haber, hacim ve hesap ekranları arasında gidip gelmek zorundadır. Bir sinyalin genel piyasa koşullarıyla uyumunu değerlendirmek ve bunu her fırsatta aynı disiplinle tekrarlamak güçtür. İşleme girdikten sonra hedeflerin takibi, kısmi kapatma ve stop güncelleme de sürekli dikkat gerektirir.

Proje şu sorunları çözmeyi hedefler:

- Farklı kaynaklardaki verileri aynı olay ve zaman kesiti etrafında toplamak.
- TradingView alarmını kaybetmeden, gerekçeli bir analiz ve plan sürecine dönüştürmek.
- Kullanıcı onayını belirli tutar, stop, hedef ve geçerlilik süresine bağlamak.
- Aynı alarmın veya aynı onayın birden fazla giriş üretmesini önlemek.
- Açık pozisyonu önceden belirlenmiş kurallarla takip etmek.
- Bağlantı koptuğunda veya süreç yeniden başladığında hesabın gerçek durumunu yeniden anlamak.
- Hangi kararın neye dayandığını ve sonrasında ne olduğunu inceleyebilmek.

Başarı yalnızca emir gönderebilmek değildir. Bildirimin ulaşması, kararın anlaşılması, yetkinin korunması ve işlem sonucunun açıklanabilmesi de ürünün parçasıdır.

## 4 Kesinleşmiş tercihler ve açık kararlar

### Kesinleşmiş tercihler

Binance Global USDⓈ-M Futures hedef borsadır. KuCoin alternatif olarak konuşulmuştur, ancak projeyi KuCoin'e taşıma kararı verilmemiştir. İlk geliştirme yerel bilgisayarda, Python tabanlı yürütülmektedir. Gerçek para kullanılmadan önce demo geliştirme ve testleri önceliklidir.

TradingView, kullanıcının teknik analiz ve sinyal üretme ekranı olarak hedeflenmektedir. İlk sürümde ayrıca gelişmiş bir grafik uygulaması geliştirmek zorunlu değildir. Telegram, bildirim ve uzaktan onay için planlanan ilk kanaldır. İleride ayrıntılı rapor paneli eklenebilir.

Varsayılan yeni giriş davranışı kullanıcı onayıdır. Kullanıcı belirli bir planı önceden etkinleştirirse, yalnızca o planın açık sınırları içindeki giriş ve yönetim eylemleri ek onaysız yapılabilir. Botun kendi kendine genel işlem yetkisi kazanması istenmemektedir.

### Henüz kesinleşmeyen kararlar

Canlı sermaye, işlem başına azami kayıp, günlük kayıp sınırı, kaldıraç, teminat türü, nihai coin listesi ve eşzamanlı pozisyon sayısı belirlenmemiştir. AI modeli, haber sağlayıcısı, zincir üstü akış sağlayıcısı, dominans verisinin lisansı, sunucu sağlayıcısı ve TradingView aboneliği de kesinleşmemiştir.

Önceki demo planlarında kullanılan 70 USDT nominal üst sınır, 10 dakikalık giriş onayı ve fiyat toleransı gibi sayılar belirli testlere aittir. Bunlar sürekli strateji kuralı veya gerçek hesap için risk onayı değildir. Konuşmalardaki 10 ya da 100 dolar ifadesi de nominal tutar, teminat veya azami kayıp olarak kendiliğinden yorumlanmamalıdır.

## 5 Beklentilerin yapılabilirlik değerlendirmesi

Durum ifadeleri üç farklı soruyu ayırır: teknik olarak yapılabilir mi, kodda mevcut mu ve ilgili akış demo borsasında doğrulanmış mı? Bu üç sorunun yanıtı her zaman aynı değildir.

| Kullanıcının beklentisi | Yapılabilirlik ve temel koşul | Mevcut durum |
|---|---|---|
| Binance fiyat ve mum verisini okumak | Yapılabilir; ürün ve fiyat türü doğru seçilmelidir | Public veri adaptörü mevcut |
| Haftalık, günlük, 4 saatlik, 1 saatlik ve 15 dakikalık analiz | Yapılabilir; kapanmış mum ve zaman hizası gerekir | Temel göstergeler mevcut |
| Destek, direnç, tepe, dip ve piyasa yapısı analizi | Yapılabilir; nesnel algoritmik tanım gerekir | Geliştirilecek |
| BTC, ETH, dominans ve TOTAL3 bağlamı | Koşullu yapılabilir; tüm veriler Binance'ten gelmez | Sağlayıcı ve modül eksik |
| Son yedi günün günlük hacmi | Yapılabilir; birim ve karşılaştırma açık olmalıdır | Temel rapor mevcut |
| Borsalara varlık giriş ve çıkışları | Koşullu yapılabilir; etiketli zincir üstü veri gerekir | Sağlayıcı seçilmedi |
| Kaynaklı haber özeti | Yapılabilir; lisans, zaman ve güvenilirlik denetimi gerekir | Geliştirilecek |
| AI ile açıklayıcı değerlendirme | Yapılabilir; model sayısal gerçekleri uydurmamalıdır | Entegrasyon yok |
| TradingView alarmını bota iletmek | Webhook ile yapılabilir [K1] | Alıcı ve bağlantı yok |
| Uygun bulunmayan alarmı da kullanıcıya bildirmek | Yapılabilir; bildirim ile işlem yetkisi ayrılır | Hedef sözleşmede var, kanal yok |
| Elle çizilmiş bütün TradingView nesnelerini otomatik okumak | Pine, elle çizim araçlarıyla etkileşemez; genel kişisel çizim API'si varsayılmaz [K2] | Doğrudan desteklenmiyor |
| Elle çizgiye bağlı koşulu kullanmak | Çizim türünün desteklediği alarm ve açık plan eşleştirmesiyle koşullu yapılabilir | Entegrasyon geliştirilecek |
| Fibonacci seviyeleriyle giriş ve çıkış | Sayısal seviyeler veya tanımlı referans noktalarıyla yapılabilir | Genel plan altyapısı var; Fibonacci arayüzü yok |
| Teknik kuralları Pine indikatörüne dönüştürmek | Pine'a uygun teknik bölüm yapılabilir | Script henüz yazılmadı |
| Bütün analiz merkezini tek Pine scriptine taşımak | Mevcut ihtiyaçların tamamı için uygun mimari değildir [K3] | Python ve Pine ayrılmalı |
| Kapalı indikatörü kullanmak | İzinli kullanım ve dışa sunduğu alarm/veri kadar mümkündür | İndikatöre göre doğrulanmalı |
| Kapalı indikatörün iç kodunu veya tüm hesaplarını okumak | Kaynak erişimi olmadan vaat edilemez | Kapsam dışı varsayım |
| Her yeni işlemde kullanıcı onayı | Yapılabilir; kullanıcı ve plan sürümü doğrulanmalıdır | Yerel onay var, Telegram onayı yok |
| Önceden verilen plan yetkisiyle otomatik yönetim | Yapılabilir; süre, tutar ve eylemler sınırlanmalıdır | Yerel Mod B altyapısı var |
| Kısmi kapatma, stop ve son hedef | Yapılabilir; borsa kuralları ve gerçekleşmeler izlenmelidir | Demo altyapısı mevcut |
| İlk hedef sonrası stopu girişe taşımak | Yapılabilir; yeni stop borsada doğrulanmalıdır | Kod ve testler var; düzeltme sonrası tam senaryo henüz kanıtlanmadı |
| Yeniden başlatmada çift işlem olmaması | Yapılabilir; kalıcı kimlik ve sahiplik eşleştirmesi gerekir | Temel demo devralma doğrulandı |
| Telefonda ve farklı cihazlarda kontrol | Telegram veya kimlik denetimli web paneliyle yapılabilir | Henüz uygulanmadı |
| Bilgisayar kapalıyken kesintisiz çalışma | Sürekli açık sunucu ve servis işletimiyle yapılabilir | Sunucu kurulmadı |
| Sabit veya garantili kâr | Güvenilir ürün taahhüdü olarak verilemez | Başarı ölçütü değil |

## 6 TradingView çizimleri ve indikatör konusu

### Elle çizim ile programatik çizim arasındaki fark

Kullanıcının fareyle çizdiği trend çizgisi veya Fibonacci nesnesi, Pine scriptinin oluşturduğu çizgi nesnesiyle aynı şey değildir. TradingView belgeleri Pine'ın arayüzdeki çizim araçlarıyla etkileşemediğini açıkça belirtir. Dolayısıyla indikatörün, kullanıcının bütün çizgilerini kendiliğinden keşfettiği bir tasarım kurulamaz. [K2]

Uygulanabilir ilk yol, desteklenen bir çizim veya fiyat koşulu için alarm kurmak ve bu alarmı botta önceden tanımlanmış planla eşleştirmektir. İkinci yol, referans fiyatları ve zamanları indikatör girdilerine sayısal olarak vermektir. Üçüncü yol, scriptin kendi algoritmasıyla referans noktalarını seçip çizgilerini üretmesidir. Son seçenek, kullanıcının elle yaptığı yorumun aynısını otomatik olarak yaptığı anlamına gelmez; algoritma ayrıca tanımlanır.

İki çizginin kesişmesi de somutlaştırılmalıdır: fiyatın bir çizgiyi geçmesi mi, iki indikatör serisinin kesişmesi mi, yoksa iki geometrik çizginin kesişim noktasına zaman olarak gelinmesi mi istenmektedir? Bu koşullar farklıdır. Her biri için ayrı olay türü ve doğrulama örnekleri gerekir.

Alarm mesajının bütün çizim koordinatlarını içerdiği varsayılmamalıdır. Mesajda plan kimliği ve gerekli sayısal alanlar bulunmalı; eksik bilgi varsa bot kullanıcıdan planı tamamlamasını istemelidir.

### Pine ile Python arasında görev paylaşımı

Pine; teknik göstergeler, grafik üzerindeki hesaplanmış çizimler, uygun çoklu zaman dilimi hesapları ve alarm koşulları için kullanılacaktır. Python; dış veri toplama, haber ve AI yorumu, plan oluşturma, kullanıcı yetkisi, hesap verisi, risk denetimi ve Binance emir yönetimi için çalışacaktır.

Pine'ın belgelenmiş veri istekleri belirli veri bağlamlarına yöneliktir. Bunları Python sunucusuna genel HTTP isteği gönderebilen bir istemci gibi tasarlamamak gerekir. Webhook, TradingView'dan dışarıya alarm iletimidir; Python analizinin aynı kanaldan kişisel grafiğe geri yazılması değildir. Bu görev ayrımı, belgelenmiş veri erişim modeline dayanan mimari değerlendirmedir. [K1] [K3]

Botun sonuçlarını TradingView'daki kişisel grafiğe doğrudan çizmek ilk sürümün taahhüdü değildir. Sonuçlar Telegram'da veya ayrı rapor ekranında gösterilebilir. Görsel olarak aynı grafikte görmek vazgeçilmezse, hangi bilgi ve etkileşimlerin desteklenen yöntemlerle gösterilebileceği ayrı bir prototiple kanıtlanmalıdır.

### Kişisel kullanım ve yayınlama

İndikatör önce kişisel kullanım için geliştirilecektir. Daha sonra açık kaynak, kaynak kodu gizli ancak kullanımı açık protected veya erişimi belirli kullanıcılara verilen invite-only yayınlama seçenekleri değerlendirilebilir. Public/private görünürlük ile kod ve kullanım erişimi aynı ayar değildir. Ücretli dağıtım ayrı ürün, destek ve platform kuralları incelemesi gerektirir. [K4]

Bir scriptte alarm koşulu bulunması çalışan alarmı otomatik olarak kurmaz. Kullanıcı alarmı arayüzden etkinleştirir. Script veya girdiler değişince eski alarmın da güncellendiği varsayılamaz; alarm sürümü takip edilmelidir. [K5]

## 7 Kullanıcı deneyimi ve ana iş akışı

Beklenen ana deneyim şu sırayla ilerler:

1. Kullanıcı TradingView'da kendi grafiğini ve desteklenen alarmını hazırlar.
2. Alarm botun HTTPS alıcısına gelir; olay zamanı, sembol ve mesaj biçimi doğrulanır.
3. Geçerli ve benzersiz olay kalıcı kayda alınır; kullanıcıya alındı bildirimi hazırlanır.
4. Piyasa verileri, teknik bağlam ve varsa haber/akış verileri toplanır.
5. Sistem destekleyen bulguları, karşı bulguları ve eksik bilgileri raporlar.
6. Sonuç işlem için uygunsa sayısal bir plan hazırlanır; uygun değilse yine açıklamalı bildirim gönderilir.
7. Mod A'da kullanıcı belirli plan sürümünü onaylar. Mod B'de daha önce etkinleştirilmiş planın yetkisi kontrol edilir.
8. Girişten hemen önce fiyat, süre, risk ve hesap durumu yeniden denetlenir.
9. Tek bir emir eylemi oluşturulur; kabul, gerçekleşme ve koruma ayrı ayrı doğrulanır.
10. Pozisyon izinli kurallarla yönetilir; her önemli değişiklik kullanıcıya bildirilir ve kaydedilir.
11. İşlem kapanınca gerçekleşen sonuç, masraflar, planla farklar ve teknik sorunlar raporlanır.

Webhook alıcısı uzun analizi isteğin içinde bitirmeye çalışmamalıdır. TradingView kısa yanıt süresi ister; olay hızla kaydedilip analiz arka planda yapılmalıdır. Teslimatın her zaman başarılı olacağı varsayılmamalı, alarm günlüğü ve kayıp/gecikme denetimi tasarlanmalıdır. Webhook için iki aşamalı doğrulama gereksinimi de kurulumda dikkate alınır. [K1]

## 8 Kullanıcıya sunulacak analiz raporu

Kullanıcının beklediği onay ekranı yalnızca iki düğmeden oluşmaz. Önce anlaşılır bir özet, ardından istenirse ayrıntılı veri görünümü sunulmalıdır.

| Rapor bölümü | Gösterilecek bilgi | Karar açısından anlamı |
|---|---|---|
| Olay özeti | Hangi alarm, hangi sözleşme, hangi zaman dilimi ve saat | Neye yanıt verildiğini açıklar |
| Genel sonuç | LONG, SHORT, BEKLE veya ENGELLİ | Analiz görüşü ile işlem iznini ayırır |
| Destekleyen nedenler | Trend, yapı, hacim ve ilgili doğrulanmış bulgular | Fikrin dayanağını gösterir |
| Karşı nedenler | Çelişen zaman dilimleri, düşük hacim, haber belirsizliği | Kullanıcıyı tek taraflı değerlendirmeden korur |
| Yedi günlük tablo | Günlük hacim, karşılaştırma ve varsa ayrı akış verileri | Yakın dönemin bağlamını verir |
| Piyasa bağlamı | BTC, ETH, dominans, TOTAL3 ve göreli güç | Tek coinin dışındaki koşulları açıklar |
| Haberler | Kaynak bağlantısı, yayın ve olay zamanı, ilgili varlık | Yorumun doğrulanmasını sağlar |
| Plan | Giriş koşulu, stop, hedefler, paylar ve geçerlilik | Onayın somut kapsamını gösterir |
| Risk | Nominal, teminat bilgisi, tahmini kayıp ve masraf belirsizliği | Ne kadar risk alındığını açıklar |
| Veri durumu | Eksik, eski veya erişilemeyen veri | Bilinmeyen bilgiyi görünür kılar |

Örnek bir bildirim şöyle olabilir: “Alarm alındı. Kısa vadeli teknik yapı yükselişi destekliyor; günlük yön ve düşük hacim karşı bulgu oluşturuyor. Akış verisi mevcut değil. Bu nedenle şu anda işlem önerisi yok; alarm izleme listesine alındı.” Bu bir örnek metindir, mevcut piyasa değerlendirmesi değildir.

Uygun bir planda Onayla ve Reddet; uygun bulunmayan olayda Ayrıntıları gör ve Yeniden değerlendir gibi eylemler sunulabilir. Sert risk ihlali bulunan bir plan için sırf kullanıcı isterse işlem açtıran bir düğme bulunmamalıdır. AI'ın ürettiği güven puanı, ölçülüp kalibre edilmedikçe başarı olasılığı olarak gösterilmemelidir.

## 9 Hacim ile para giriş ve çıkışını ayırma

Bu ayrım kullanıcının istediği analiz merkezinin güvenilirliği için önemlidir. İşlem hacmi bir dönemde ne kadar alışveriş yapıldığını gösterir. Taker alış ve satış hacmi, hangi tarafın likiditeyi tüketerek işlem yaptığını ölçer. İkisi de tek başına piyasaya yeni para girdiğini kanıtlamaz.

Borsalara zincir üstü giriş/çıkış ise bilinen borsa adreslerine veya bu adreslerden yapılan varlık transferlerini izler. Bunun için adres etiketleme kalitesi, desteklenen ağlar, transferlerin birimi ve verinin güncellenme süresi bilinmelidir. Borsaya BTC girişi otomatik olarak satış yapılacağı; stablecoin girişi de kesin alım yapılacağı anlamına gelmez.

Bu nedenle raporda şu alanlar ayrı tutulmalıdır: USDT cinsinden işlem hacmi, taker alış/satış hacmi, ilgili varlık biriminde borsa giriş ve çıkışları, hesaplanabiliyorsa açıklanmış yöntemle dolar karşılığı ve net akış. Net akışta işaret kuralı açık yazılmalıdır. Borsanın kendi cüzdanları arasındaki transferler ve sağlayıcı etiket düzeltmeleri yanlış yorum kaynağıdır.

İlk sürümde hacim raporu kullanılabilir; akış verisi sağlanmadan o alan “veri yok” olarak kalmalıdır. Akış sağlayıcısının ücretli olması veya hedef varlıkları kapsamaması halinde özellik maliyet ve kapsam kararı bekler.

## 10 İki farklı işlem yetkisi

### Mod A her yeni girişte onay

Varsayılan moddur. Kullanıcı işlem planını ve gerekçesini görür. Onay; belirli plan sürümü, ortam, sembol, yön, tutar, stop, hedefler, süre ve izinli eylemler için geçerlidir. Genel bir “devam edelim” ifadesi gelecekte oluşabilecek bütün planlara sınırsız yetki olarak kaydedilmez.

Yanıt gelmezse, süre dolarsa veya kullanıcı reddederse giriş yapılmaz. Fiyat önemli ölçüde değişmişse onaydan sonra bile emir açılmayabilir. Bu durumda yeni değerlendirme gerekir; eski onay değişmiş bir plana taşınmaz.

Onaylanan planın stop, kısmi çıkış ve son hedef eylemleri zaten kapsamın içindeyse her hareket için yeniden onay istenmez. Açılmış pozisyonun korunması ile yeni işlem açma yetkisi birbirinden ayrılır.

### Mod B önceden etkinleştirilen sınırlı plan

Kullanıcı giriş koşullarını, miktar veya kayıp bütçesini, stopu, hedefleri, geçerlilik süresini ve izinli yönetimi önceden görür ve etkinleştirir. Belirli koşul oluştuğunda bot bu sınırlar içinde tekrar onay almadan hareket edebilir. Bu da bir onay biçimidir; yalnızca zaman olarak sinyalden önce verilir.

Örneğin kullanıcı sayısal Fibonacci seviyeleriyle bir giriş, iki hedef ve bir stop tanımlayabilir. Bot, etkinleştirilmiş plan destekleniyorsa koşulu izler ve uygular. Kullanıcının çizdiği nesneyi görsel olarak otomatik okuması bu yetkinin ön koşulu değildir; seviyeler plana açıkça aktarılmış olmalıdır.

Pozisyon büyütme, yön değiştirme, yeniden giriş, süre uzatma veya stopu daha fazla risk yaratacak yönde taşıma mevcut test yetkisinin kapsamı değildir. Teknik destek eklenmeden bu eylemler uygulanamaz. Kullanıcı onayı bağımsız risk engelini de kaldırmaz.

## 11 Pozisyon yönetimi nasıl çalışmalı

Bir işlem planının giriş emri borsada kabul edildiğinde iş bitmez. Gerçekleşen miktar, gerçekleşme fiyatı ve koruyucu emirlerin durumu ayrıca okunmalıdır. Kısmi gerçekleşme varsa planlanan tam miktar yerine gerçekten açılan miktar esas alınmalıdır.

Mevcut yaklaşımda başlangıç stopu ve son hedef borsada tutulur. Ara hedefler çalışan yerel izleyicinin mark fiyatını kontrol ettiği turda reduce-only piyasa çıkışıyla uygulanır. Bu nedenle bilgisayar veya izleyici kapalıyken ara hedeflerin izlendiği varsayılamaz. Polling aralarında kısa fiyat temasları da kaçırılabilir. Üretim tasarımında yerel kontrol, WebSocket takibi ve borsada bekleyen kısmi hedef emirleri seçenekleri güvenilirlik ve desteklenen API açısından ayrıca karşılaştırılmalıdır.

İlk hedef sonrası stop giriş fiyatına taşınacaksa, hedefin izin verilen miktarda gerçekten kapandığı doğrulanmalıdır. Ardından kalan miktara uygun yeni stop kurulmalı ve borsada sorgulanmalıdır. Eski stop ancak yeni koruma doğrulandıktan sonra kaldırılmalıdır. Yerel kayıtta stop değerinin değişmiş olması tek başına başarı sayılmaz.

Giriş fiyatına stop taşımak masraflar dahil sıfır zarar garantisi değildir. Komisyon, funding, spread, piyasa emri kayması ve stop tetiklendikten sonraki gerçekleşme fiyatı sonucu değiştirebilir. Nominal pozisyon büyüklüğü ile yatırılan teminat ve stopta beklenen kayıp da farklıdır; kaldıraç bu ayrımı ortadan kaldırmaz.

## 12 AI katmanının görevi ve sınırları

AI'ın görevi hesaplanmış bulguları ve kaynaklı haberleri anlaşılır bir değerlendirmeye dönüştürmek, çelişkileri göstermek ve yapılandırılmış plan adayına katkı sağlamaktır. İşlem miktarı, fiyat adımı, gerçekleşen kâr ve hesap bakiyesi gibi gerçekler doğrudan kod ve veri kaynağından gelmelidir.

Haber metni güvenilmeyen dış içerik olarak işlenmelidir. Bir haberin içinde geçen talimat, botun yetkisini veya risk sınırlarını değiştiremez. AI'a borsa secret'ı, imza anahtarı veya gereksiz özel hesap bilgisi verilmemelidir.

Model çıktısı doğrulanabilir bir şemaya uymalıdır. Yorum, veri eksikliği ve kesin gözlem ayrı alanlarda bulunmalıdır. Model servisinin çalışmaması, otomatik olarak “piyasa uygun” sonucu üretmemelidir. AI zorunlu bir karar bileşeniyse yeni giriş durur; yalnızca açıklama bileşeniyse sayısal kuralların ne koşulda çalışmaya devam edebileceği önceden tanımlanır.

İlk sürümde belirli bir AI sağlayıcısına bağımlı olmayan arayüz tercih edilmelidir. Modelin sürümü, kullanılan veriler, maliyet ve yanıt süresi kaydedilmelidir. AI'ın kendi stratejisini izinsiz değiştirmesi veya başarısız sonuçlar sonrasında kendiliğinden daha fazla risk alması istenen kapsamda değildir.

## 13 Önerilen teknik mimari

Başlangıç için modüler tek Python uygulaması yeterlidir. TradingView/Pine dış sinyal ve grafik katmanını; Python uygulaması karar, yetki ve yürütme katmanını oluşturur. Gerçek ihtiyaç doğmadan çok sayıda mikroservis ve karmaşık dağıtık sistem kurulması önerilmez.

| Bileşen | Sorumluluk | İlk teslim ölçütü |
|---|---|---|
| TradingView ve Pine | Teknik koşul, çizim ve alarm | Python ile aynı kurala bağlı doğrulanmış sinyal |
| Webhook alıcısı | Kaynak, şema ve zaman denetimi | Tekrarlı, eski ve hatalı mesajları ayırma |
| Kalıcı olay kuyruğu | Alarmın kaybolmadan işlenmesi | Yeniden başlatmada tamamlanmamış olayın devamı |
| Piyasa verisi | Mum, fiyat türleri ve veri kalitesi | Eski veya eksik veriyle giriş olmaması |
| Analiz motoru | Teknik yapı ve piyasa bağlamı | Tekrar üretilebilir bulgular |
| Haber ve akış adaptörleri | Kaynaklı dış veri | Zaman, kapsam ve eksik bilgilerin kaydı |
| AI yorumlayıcı | Açıklama ve karşı görüş | Şemalı, kaynaklara bağlı çıktı |
| Plan ve yetki | Sürüm, onay, süre ve eylem sınırı | Yetkisiz veya eski onayla giriş olmaması |
| Risk motoru | Miktar ve bağımsız sınırlar | Onayın aşamayacağı sayısal denetim |
| Binance adaptörü | Emir ve hesap işlemleri | Doğru ortam ve desteklenen ürün |
| İzleyici ve uzlaştırma | Sahiplik, koruma, çıkış ve kurtarma | Kesinti sonrasında çift emir olmaması |
| Bildirim ve panel | Kullanıcıya durum ve kontrol | Yetkili kullanıcıya teslim ve kayıt |

SQLite mevcut uygulama için kalıcı kayıt temelidir. Piyasa mumları ile işlem/yetki kayıtları ayrılmıştır. Analiz, sinyal, plan, onay, istemci emir kimliği ve borsa gerçekleşmeleri birbirine bağlanmalıdır. Veri büyüklüğü veya eşzamanlılık gerçekten gerektirirse daha sonra farklı veritabanı değerlendirilebilir.

## 14 Mevcut uygulamanın gerçek durumu

Bu bölüm 6 Kasım 2026 tarihli yerel dosya ve kayıt incelemesine dayanır. Anlık borsa bakiyesi veya fiyat beyanı değildir. Eski plan dosyalarında tarihsel 35, 86 ve 105 test gibi ara durumlar bulunur; en son bu konuşmada tamamlanan test koşusunda 118 test geçmiştir. Test sayısı tek başına strateji başarısı veya üretim güvenilirliği ölçüsü değildir.

### Mevcut olanlar

Python 3.12 tabanlı paket, demo ortamını zorunlu kılan yapılandırma ve Binance demo adaptörü vardır. Kimlik doğrulama, hesap okuma, emir oluşturma, sorgulama, iptal, küçük LONG pozisyon, kısmi kapatma ve tam kapatma için araçlar geliştirilmiştir.

Emir niyetleri, olaylar, plan sürümleri ve yönetilen oturumlar SQLite'ta saklanır. Tek yürütücü kilidi, aynı istemci kimliğini körlemesine yeniden göndermeme, hesap/gerçekleşme eşleştirmesi ve demo risk sınırları mevcuttur. Yerel CLI üzerinden Mod A onayı ve Mod B etkinleştirmesi bulunur. Bunlar henüz Telegram üzerinde uzaktan kimlik doğrulanmış bir ürün akışı değildir.

Public piyasa adaptörü, kapanmış mum verisi, haftalık/günlük/4 saat/1 saat/15 dakika göstergeleri, EMA20/50, RSI14, ATR14, hacim karşılaştırması ve son yedi tamamlanmış günün raporu vardır. Temel rapor otomatik olarak emir üretmez.

### Demo ile öğrenilenler

Gerçek demo bağlantısı ve kullanıcı onaylı küçük pozisyonlar üzerinden giriş, borsada koruma ve kısmi çıkış davranışları gözlenmiştir. Bir pozisyonda ilk hedef sonrası stop taşıma hatası ortaya çıkmış; ilk hata bilgisinin saklanması, ret/belirsiz ayrımı ve kalan miktar için reduce-only stop yaklaşımı düzeltilmiştir. Windows'ta Türkçe karakterin dosyaya yazımı nedeniyle duran izleyici için de regresyon testi eklenmiştir.

Son tekrar planı `btc-stop-retest-20261104-225620` yerel kayıtta CLOSED durumundadır. Kapanış olayı 5 Kasım 2026 14.38.34 UTC, yani 18.38.34 Bakü saatinde kaydedilmiştir. Bu oturumun hedefleri kayıt üzerinde WAITING kalmış ve stop geçişi oluşmamıştır. Dolayısıyla bu son deneme, düzeltme sonrası ilk hedef → girişe stop taşıma → yeni stopla ayrı süreçte devralma zincirinin başarılı kanıtı değildir. Kapanış sebebi veya net sonuç, yalnızca bu yerel alanlardan çıkarılmamalı; gerektiğinde borsa gerçekleşmeleriyle ayrıca incelenmelidir.

### Henüz olmayanlar

TradingView webhook alıcısı, kendi Pine indikatörümüz, Telegram bildirim/onay sistemi, uzaktan rapor paneli, haber toplama ve AI yorumu yoktur. Piyasa yapısı, dominans, TOTAL3 ve zincir üstü akış katmanları tamamlanmamıştır. Sürekli çalışan sunucu, otomatik servis başlangıcı ve üretim alarm kanalı kurulmamıştır.

Güncel yürütme kapsamı tek demo LONG ve one-way hesap yaklaşımıyla sınırlıdır. SHORT, hedge, pozisyon artırma, çoklu giriş ve diğer gelişmiş emir davranışları mevcutmuş gibi sunulmamalıdır. Canlı işlem adaptörü ve gerçek hesaba geçiş doğrulanmamıştır.

## 15 Demo ortamı neleri tamamlamamızı sağlar

Demo; emir yaşam döngüsünü, sembol kurallarını, kullanıcı onayını, stop ve hedef yönetimini, tekrar önlemeyi, kayıt tutmayı ve kesintiden kurtulmayı sınamak için değerlidir. TradingView alarmı ve Telegram onayı da sisteme bağlanıp demo emir yoluyla uçtan uca test edilebilir. Bu nedenle ürünün büyük bir kısmı gerçek para kullanılmadan geliştirilebilir.

Ancak demo gerçekleşmelerinin canlı spread, derinlik, kayma, yoğunluk ve kesinti davranışını temsil ettiği varsayılamaz. Demo ve gerçek piyasa fiyatları farklılaşabilir. Bu yüzden gerçek piyasa analizi ile demo yürütme ayrı kaynaklar olarak tutulmalı; girişte yaş ve fiyat farkı kontrolü yapılmalıdır.

Strateji kalitesi için ayrıca gerçek tarihsel verilerle geçmiş test ve ayrılmış test dönemi, mümkünse ileriye dönük sanal işlem gerekir. Demo emir testi “emri doğru yönettik mi?” sorusunu; performans değerlendirmesi ise “bu kurallar masraflardan sonra yeterli sonuç üretiyor mu?” sorusunu yanıtlar. İkisi birbiri yerine geçmez.

Takvimde belirli gün sayısının geçmesi veya çok sayıda test dosyasının başarılı olması otomatik canlıya geçiş şartı değildir. Canlı hazırlık için ölçülmüş davranış, kabul ölçütleri, hesap uygunluğu ve ayrı kullanıcı kararı gerekir.

## 16 Geliştirme sırası ve aşama çıkışları

Aşağıdaki sıra mevcut 0–11 aşamalı planı ürün teslimleri halinde toplar. Mevcut ilerlemeyi yok sayıp baştan başlama önerisi değildir.

| Teslim | Yapılacak işler | Sonraki aşamaya geçiş kanıtı |
|---|---|---|
| 1 Emir ve koruma temelini bitir | Stop düzeltmesi, hata kayıtları, demo son durum raporu | İlk hedef, yeni stop, eski stop iptali ve devralma borsayla eşleşir |
| 2 Kullanıcıya durum görünürlüğü | Temel Telegram durumu, teslim kuyruğu, kesinti alarmı | Kullanıcı sohbetten fiyat, pozisyon ve koruma durumunu görür |
| 3 Uzak onayı güvenilir yap | Kullanıcı kimliği, tek kullanımlık sürümlü onay ve iptal | Eski, geç, tekrar veya yetkisiz tıklama giriş açmaz |
| 4 Temel analizi düzenle | Çoklu zaman dilimi, veri yaşı, açık mum ayrımı | Aynı veri ve sürüm aynı raporu üretir |
| 5 Yapı ve veri kapsamını genişlet | Destek/direnç, Fibonacci tanımı, dominans ve akış adaptörleri | Her bulgunun kaynağı ve eksik veri politikası vardır |
| 6 Haber ve AI ekle | Kaynak/zaman denetimi, şemalı yorum ve maliyet sınırı | Kaynaklı açıklama, karşı bulgu ve servis kesintisi testi |
| 7 TradingView bağlantısını kur | Pine teknik koşulları, webhook, sembol ve plan eşleştirmesi | Her geçerli alarm raporlanır; yalnız yetkili plan yürütülür |
| 8 Mod B deneyimini tamamla | Plan oluşturma, etkinleştirme, izleme ve iptal | Bot yalnızca açık ön yetki sınırlarında hareket eder |
| 9 Sürekli işletimi kur | Sunucu, servis, yeniden başlatma, yedek ve izleme | Kullanıcı bilgisayarı kapalıyken kontrollü demo akışı sürer |
| 10 Performansı değerlendir | Masraflı geçmiş test, ayrılmış dönem, ileri test | Sonuçlar önceden belirlenen ölçütlerle raporlanır |
| 11 Canlı hazırlığı değerlendir | Hesap/API uygunluğu ve kullanıcı risk tercihleri | Ayrı canlı izin kaydı ve kontrollü açılış kararı |

Temel bildirim katmanının erken kurulması önerilir. Bunun nedeni mevcut durumda kullanıcının tekrar tekrar “ne durumdayız?” diye sormasıdır. İşlem yönetimi sağlamlaştırılırken durum ve kesinti bilgisinin kullanıcıya ulaşması paralel öncelik olmalıdır. Bu, henüz tamamlanmamış zengin AI raporunun beklenmesini gerektirmez.

## 17 Kabul ölçütleri

Bir özelliğin tamamlandığını söylemek için gözlenebilir bir sonuç tanımlanmalıdır.

- **Yetki:** Onaysız, süresi dolmuş veya değiştirilmiş planla yeni giriş açılamaz.
- **Tekrarsız yürütme:** Aynı alarm, onay veya yeniden başlatma ikinci giriş üretmez.
- **Gerçekleşme:** Emir kabulü ile fill ayrılır; hedef gerçekleşmesi borsadaki miktarla doğrulanır.
- **Koruma:** Stop yalnız yerel kayıtta değil, borsada doğru miktar ve tetik fiyatıyla aktiftir.
- **Stop geçişi:** İlk hedef tam miktarda kapanır; yeni stop kabul edilir; eski stop bundan sonra kaldırılır.
- **Devralma:** Yeni süreç aynı oturum, giriş ve stopu benimser; bilinmeyen manuel işlemi sahiplenmez.
- **Bildirim:** Geçerli uygun olmayan alarm da gerekçesiyle görünür; teslim hatası kaybolmaz.
- **Veri kalitesi:** Kritik veri eski veya eksikse yeni giriş engellenir; eksik alan uydurulmaz.
- **Rapor:** Kullanıcı planın nedenini, karşı bulguları ve tahmini riskini görebilir.
- **Güvenlik:** Secret rapor, Pine, webhook, Telegram veya istemci ekranına taşınmaz.
- **Kesinti:** İnternet yokken hangi eylemlerin durduğu ve hangi borsa emirlerinin kaldığı açıktır.
- **Performans:** Kâr, zarar ve kayıp serileri komisyon/funding/kaymayla değerlendirilir.

Bu ölçütlerin bir bölümü birim testi, bir bölümü hata enjeksiyonu, bir bölümü gerçek demo hesabında senaryo testi gerektirir. Sadece bir test katmanının başarısı diğerlerinin yerini tutmaz.

## 18 Kesintisiz çalışma ve cihazlardan erişim

İstenen sürekli izleme için botun çalışma süreci sürekli açık kalmalıdır. Kullanıcının bilgisayarı yerine sunucu kullanılabilir. Telefon ve bilgisayar bu sunucuya Telegram veya kimlik denetimli panel üzerinden bağlanır; borsa secret'ı cihazlara dağıtılmaz.

Sunucu kurulumu yalnızca bir Python dosyasını arka planda çalıştırmak değildir. Servisin otomatik başlaması, tek yürütücü kilidi, bağlantı hatası politikası, sağlık kontrolü, disk/log sınırı, saat eşitleme, yedekleme ve yeniden kurulum testi de gerekir. İkinci bir aktif sunucu kurmak çift emir riskini büyütebilir; yedek sunucunun devralma yetkisi ayrıca tasarlanmalıdır.

TradingView alarmının platform tarafında çalışması ile bizim analiz ve emir sunucumuzun çalışması farklı konulardır. Webhook alıcısı ve pozisyon yöneticisi erişilemiyorsa bütün zincirin çalıştığı kabul edilmez. Bildirim kanalı da aynı arızadan etkilenebileceği için kritik kesintilerde alternatif uyarı yöntemi değerlendirilebilir.

## 19 Maliyet ve kaynak yaklaşımı

Kesin aylık fiyat bu taslakta taahhüt edilmemektedir. Önceki görüşmedeki yaklaşık 10–20 dolar sunucu bütçesi, küçük bir başlangıç kurulumuna ilişkin tahmindi; bütün ürünün toplam maliyeti değildir. Satın alma öncesi güncel fiyat ve gereksinimler tekrar incelenmelidir.

| Maliyet kalemi | Maliyeti belirleyen unsur | Planlama yaklaşımı |
|---|---|---|
| Sunucu | Bellek, CPU, bölge, çalışma süresi ve yedekleme | Küçük demo ile başlayıp ölçerek büyüt |
| TradingView | Alarm/webhook ihtiyaçları ve yayınlama biçimi | Hesabın gereken özelliklerini satın almadan doğrula |
| AI | Model, girdi/çıktı hacmi, haber sayısı ve çağrı sıklığı | Çağrı bütçesi, önbellek ve günlük sınır koy |
| Haber | Lisans, kaynak sayısı ve tarihsel erişim | Kaynak gereksinimini önce daralt |
| Akış ve piyasa bağlamı | Kapsanan varlık/borsa/ağ ve gecikme | Veri kalitesini maliyetle birlikte karşılaştır |
| Depolama ve yedek | Mum, olay, haber ve rapor tutma süresi | Saklama ve arşiv politikasını belirle |
| İşlem masrafları | Komisyon, funding, spread ve kayma | Altyapı faturasından ayrı performansa dahil et |
| Bakım | API değişiklikleri, izleme ve hata giderme | Sürekli işletim sorumluluğunu tanımla |

Başlangıçta pahalı veri abonelikleri ve AI çağrıları yerine sağlam emir/onay/bildirim akışını bitirmek daha verimli olabilir. Ne kadar coin ve zaman diliminin ne sıklıkta analiz edileceği belli olmadan güvenilir toplam maliyet hesaplanamaz.

## 20 Temel riskler ve kapsam dışında bırakılan varsayımlar

En büyük teknik riskler; veri kaynakları arasındaki farklar, ağ kesintileri, emir yanıtının belirsiz kalması, kullanıcı onayı beklerken fiyat değişmesi, yerel stop kaydının borsa gerçeğinden kopması ve aynı hesapta manuel müdahaledir. Bunlar kayıt, yeniden sorgulama, sahiplik denetimi ve açık hata politikalarıyla yönetilmelidir.

Analiz tarafında aşırı uyum, repaint, gelecekte bilinecek tepe/dibi geçmişte biliniyormuş gibi kullanma, haberin geç gelmesi ve AI'ın desteklenmeyen kesinlik üretmesi risktir. Çok sayıda gösterge veya veri kaynağı eklemek bu sorunları kendiliğinden çözmez.

Kapsam dışında kalan veya ayrıca karar gerektiren konular şunlardır: kullanıcı izni olmadan gerçek para ile işlem; para çekme; sınırsız hesap yetkisi; garanti kâr; kapalı kaynak indikatörün koduna izinsiz erişim; özel çizimlerin belgelenmemiş yöntemlerle topluca okunmasının vaat edilmesi; başka kullanıcıların parasını yöneten ticari hizmet; izinsiz strateji veya risk değişikliği.

Gerçek hesaba geçerken ürün ve hesap erişimi ayrıca doğrulanmalıdır. Demo erişimi, Binance sitesinin açılması veya API'nin cevap vermesi tek başına canlı Futures kullanım uygunluğu değildir. Türkiye/Binance Global/Binance TR gibi konularda güncel hesap ve ürün koşulları ayrı değerlendirme konusudur; bu belge hukuki uygunluk tespiti yapmaz.

## 21 Bir sonraki somut çalışma paketi

Öncelik, daha fazla demo pozisyon açmak değil, açık kalan test iddiasını ve kullanıcı görünürlüğünü tamamlamaktır. Son oturum kapanmıştır; hedef sonrası stop taşıma zinciri bu tekrar oturumunda kanıtlanmadığı için başarılı sayılmamalıdır.

Önerilen çalışma paketi şudur:

1. Son demo oturumunun borsa gerçekleşmelerini okuyarak kapanış nedeni, miktarlar ve net masrafları raporla. Bu işlem yeni giriş gerektirmez.
2. Stop taşıma senaryosunu kontrollü simülasyonla tam olarak doğrula; ağ/ret/yanıt kaybı ve yeniden başlatma örneklerini raporla.
3. Gerçek demo doğrulaması gerekiyorsa yeni somut planı kullanıcıya sun. Hedef oluşmadı diye seviyeleri veya riski kendiliğinden değiştirme.
4. İlk hedef, yeni reduce-only stop ve eski stop iptali borsada eşleşince ayrı süreçte devralma kanıtını kaydet.
5. Temel Telegram durum ve kesinti bildirimini kur; kullanıcının yalnızca sohbetten manuel sorguya bağımlı kalmasını azalt.
6. Uzaktan kimlik doğrulanmış onayı tamamla; ardından TradingView'dan önce yalnızca bildirim, sonra yetkili demo yürütme akışını bağla.

Bu çalışma paketi, önceki yetkileri yeni işlemlere taşımaz. Taslağın hazırlanması sırasında işlem açma, stop değiştirme veya izleyiciye müdahale yapılmamıştır.

## 22 Karara bağlanacak sorular

Geliştirmeyi sürdürürken her sorunun aynı anda yanıtlanması gerekmez. Ancak ilgili özelliğe başlanmadan önce şu kararlar kayıt altına alınmalıdır:

- İlk stratejide tam olarak hangi çizgi, kesişme ve mum kapanışı kuralı kullanılacak?
- İlk ürün yalnız LONG mu olacak, SHORT desteği hangi aşamada eklenecek?
- “100 dolar” nominal tutar mı, teminat mı, azami kayıp mı demek?
- Hangi zaman dilimi bağlayıcı, hangisi yalnız bağlam sağlayıcı olacak?
- Kritik veri eksikliğinde hangi kararlar duracak, hangi raporlar yine gönderilecek?
- Onay ne kadar süre geçerli olacak; hangi fiyat değişimi yeniden onay gerektirecek?
- Mod B planları ne kadar süre, kaç giriş ve hangi yönetim eylemleriyle çalışacak?
- Ara hedefler borsada mı bekleyecek, yerel izleyiciyle mi yönetilecek?
- Kullanıcı manuel işlem yaptığında bot duracak mı, yeni bir uzlaştırma akışı mı isteyecek?
- İlk haber, akış ve dominans sağlayıcıları hangileri olacak; aylık veri bütçesi nedir?
- Telefon erişiminde Telegram yeterli mi, ilk sürümde ayrıntılı panel de gerekli mi?
- Canlıya geçişin kabul edilebilir kayıp, kesinti ve performans ölçütleri nelerdir?

## 23 Başarı tanımı

Projenin hedeflenen ilk kullanılabilir sürümü; kullanıcının TradingView alarmını alabilen, her geçerli alarmı gerekçesiyle bildiren, kaynaklı temel analiz sunan, yeni girişte yetkiyi doğrulayan ve onaylı demo pozisyonu dayanıklı biçimde yönetebilen sistemdir.

Tam hedef sürümde buna zengin piyasa bağlamı, haber/AI, açıkça tanımlanmış akış verisi, Mod B deneyimi, cihazlar arası erişim, sürekli sunucu işletimi ve ölçülmüş strateji değerlendirmesi eklenir. Gerçek hesap desteği bu aşamaların doğal veya otomatik sonucu değildir; ayrıca tasarlanıp onaylanır.

Kullanıcı açısından aranan sonuç, bir alarm geldiğinde “Neden bu karar verildi, hangi bilgimiz eksik, neye izin verdim, şu an hesabımda ne oluyor ve sistem durursa ne olacak?” sorularının anlaşılır cevaplarını alabilmektir.

## 24 Kaynaklar ve izlenebilirlik

### Yerel proje kaynakları

- `01-PROJE-VE-HEDEFLER.md`: Kullanıcı hedefleri ve önceki tercihlerin kaydı.
- `02-ASAMALI-GELISTIRME-PLANI.md`: Aşamalı geliştirme planı; bazı durum paragrafları tarihsel ara aşamaları anlatır.
- `03-MIMARI-VE-ISLEM-SOZLESMESI.md`: Plan, kullanıcı yetkisi, risk ve yürütme sözleşmesi.
- `DOGRULAMA.md`: Demo senaryoları, hata bulguları ve test geçmişi.
- `agentrader/`: Mevcut Python uygulaması; özellikle plans, plan_execution, execution, watchdog, management, market_data ve market_cli modülleri.
- `scripts/watch_approved_demo.py`: Yerel izleme ve stop sonrası ayrı süreçte devralma yardımcısı.
- `tests/`: Çevrimdışı davranış ve hata senaryoları.
- `data/execution.sqlite3` ile ilgili JSONL kayıtları: Bu belgede belirtilen son oturumun yerel durum kanıtı. Gizli anahtarlar belgeye aktarılmamıştır.

### Resmî dış kaynaklar

Teknik platform sınırları 6 Kasım 2026 tarihinde aşağıdaki resmî TradingView belgeleriyle kontrol edilmiştir. Platform özellikleri ve abonelik koşulları kurulumdan önce yeniden doğrulanmalıdır.

- **[K1] TradingView webhook yapılandırması:** https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/ — Dış uygulamaya alarm iletimi, kısa yanıt süresi, 2FA ve teslimat sınırlamaları.
- **[K2] Pine çizgiler ve kutular:** https://www.tradingview.com/pine-script-docs/visuals/lines-and-boxes/ — Script nesneleri ile kullanıcı çizim araçlarının ayrılığı.
- **[K3] Pine diğer zaman dilimleri ve veri:** https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/ — Belgelenmiş veri erişim modeli; Python/Pine görev ayrımının dayanağı.
- **[K4] Pine script yayınlama:** https://www.tradingview.com/pine-script-docs/writing/publishing/ — Public/private ve open/protected/invite-only ayrımları.
- **[K5] Pine alarm soruları:** https://www.tradingview.com/pine-script-docs/faq/alerts/ — Çalışan alarmın kullanıcı tarafından oluşturulması ve script/girdi değişikliklerinin mevcut alarma kendiliğinden yansımaması.

Belgedeki örnek bildirimler, önerilen aşama çıkışları ve henüz seçilmemiş sağlayıcı mimarisi tasarım önerisidir. Bunlar tamamlanmış özellik veya kullanıcı tarafından belirlenmiş nihai risk tercihi olarak yorumlanmamalıdır.
