> Tarihsel arşiv: 9 Kasım 2026 yön değişikliğinden önceki metin. Güncel ürün kararı için [aktif hedeflere](../../../01-PROJE-VE-HEDEFLER.md) bakın. İçerik korunmuştur; yerel Markdown bağlantıları arşiv konumuna uyarlanmıştır.

# AI Crypto Trader — Proje ve hedefler

## 6 Kasım 2026 kapsam genişlemesi

Kullanıcı, yalnız tek LONG denemesi değil, Binance demo API'sinin ilgili ürün
ve hesapta gerçekten desteklediği işlemleri bot üzerinden kullanabilmeyi istedi.
Önce yetenek/izin/mevcut kod envanteri, sonra bağımlılıklara göre geliştirme
yapılacak. Yeni ana envanter ve sıra:
[06-BINANCE-DEMO-YETENEK-ENVANTERI-VE-GELISTIRME-SIRASI.md](../../../06-BINANCE-DEMO-YETENEK-ENVANTERI-VE-GELISTIRME-SIRASI.md).
95 USD-M REST başlığı belgede listelidir; hepsinin demoda veya bu anahtarda
çalıştığı iddia edilmez. Grid, Spot ve COIN-M kapsamları ayrı doğrulanır.
Bu kapsam genişlemesi yeni emir, hesap modu değişimi veya canlı işlem izni değildir.
Aşağıdaki eski durum paragrafları tarihsel gelişimi yansıtır; güncel kanıtlar
DOGRULAMA.md ve yeni envanterle birlikte okunmalıdır.

Son plan güncellemesi: 5 Kasım 2026. Bu belge ilk tasarım ile sonraki geliştirme ve karar görüşmelerini birleştirir. Artık çalışan demo kodu vardır; mevcut yetenekler ve henüz geliştirilecek hedefler aşağıda ayrı belirtilmiştir. Teknik kanıtlar [DOGRULAMA.md](../../../DOGRULAMA.md) içindedir.

## Kullanıcının istediği sistem

Python ile geliştirilen, Binance Futures üzerinde otomatik işlem yapabilen kişisel bir kripto analiz ve işlem sistemi. Yalnızca indikatör sinyali üreten bir bot değil; büyük resmi gören, piyasa yapısını ve haberleri birlikte değerlendiren, karar gerekçelerini kaydeden bir sistem hedefleniyor.

Bot şu yeteneklere ulaşmalı:

- Haftalık, günlük, 4 saatlik, 1 saatlik ve 15 dakikalık verileri birlikte incelemek.
- Tepe/dip, destek/direnç, trend, hacim ve kırılım yapılarını hesaplamak.
- BTC/USDT, ETH/USDT, BTC dominansı, USDT dominansı, TOTAL3 ve seçilen coinin USDT/BTC karşısındaki gücünü paralel değerlendirmek.
- Anlık önemli hareketleri izlemek; kapsamlı analizi ilgili mum kapanışlarında yenilemek.
- Haberlerin zamanını, kaynağını, güvenilirliğini, ilgili varlığı ve tekrar olup olmadığını incelemek.
- LONG, SHORT veya BEKLE değerlendirmesi üretmek. Kullanıcının düşündüğü yönü sırf kullanıcı istedi diye onaylamamak.
- Neden işlem açtığını, neden beklediğini ve hangi koşulda görüşünün değişeceğini anlatmak.
- Analizleri, işlem planlarını ve sonuçları saklamak; daha sonra karşılaştırmak.
- Desteklenen işlem planlarını kullanıcı yetkisi ve bağımsız risk sınırları içinde uygulamak.
- Telegram üzerinden durum, analiz ve kontrol sunmak.
- Her geçerli TradingView alarmını, strateji koşulları uygun olsa da olmasa da gerekçesiyle kullanıcıya bildirmek.
- Son 7 tamamlanmış günün günlük hacmini, karşılaştırmasını ve veri bulunuyorsa borsalara varlık giriş/çıkış/net akışını kaynaklarıyla raporlamak.

## TradingView ve indikatör hedefi

Kullanıcı kişisel TradingView hesabında Binance'in ilgili piyasa/sözleşme grafiğini kullanacak. İki kaynak desteklenecek: elle çizilen çizgi/Fibonacci seviyelerine bağlanan desteklenen alarmlar ve geliştirilecek Pine Script indikatörünün teknik sinyalleri.

Teknik analiz, çizimler ve çoklu zaman dilimi kurallarının Pine'a uygun kısmı indikatörde çalışabilir. Haber/AI, hesap, onay, risk ve emir yönetimi Python'da kalır. Pine'ın Python/AI servisinden genel HTTP çağrısıyla canlı sonuç alabildiği varsayılmaz. Webhook TradingView'dan bota bildirim yönündedir.

Kişisel hesap çizimlerini topluca okuyup değiştiren desteklenmiş bir API doğrulanmadı. Alarm bütün çizim koordinatlarını otomatik aktarıyor sayılmaz. Fibonacci planının seviyeleri sayısal olarak girilir veya açık alarm/plan eşleştirmesi kullanılır. Kendi grafik panelimiz ilk sürüm için zorunlu değildir.

İndikatör önce kişisel kullanım içindir. İstenirse daha sonra open/protected/invite-only dağıtım değerlendirilir; satış ayrı kapsamdır. Script alarm koşullarını tanımlar; kullanıcı çalışan alarmı TradingView'da oluşturup etkinleştirir. Hesap planı, 2FA ve webhook yetenekleri kurulumda doğrulanır.

## Bildirim ve açıklanabilir karar

Her geçerli benzersiz alarm raporlanır. Strateji/risk filtresi bildirimi gizlemez. Teknik tekrarlar tek olay altında birleştirilir; farklı gerçek alarmlar kaybolmaz. Sahte/yetkisiz trafik işlem sinyali değil güvenlik olayıdır.

Rapor kısa özet ve ayrıntılı görünüm sunar: LONG/SHORT/BEKLE/ENGELLİ sonucu, destekleyen/karşı çıkan nedenler, görüş değişim koşulu, zaman dilimleri ve piyasa bağlamı, 7 günlük tablo, kaynaklı haber özeti, veri eksikleri ve işlem planı/risk bilgileri. Kritik veri yoksa işlem engellenir; alarm yine bildirilir. İlk alındı bildirimi analizden önce gönderilebilir.

Hacim, taker alıcı/satıcı baskısı ve zincir üstü borsa giriş/çıkışı farklı ölçülerdir. Hacimden yeni para girişi çıkarılmaz; borsa akışı tüm piyasa sermaye akışı gibi sunulmaz. Her ölçüde birim, kaynak, kapsam, dönem ve gecikme belirtilir. Sağlanamayan veri uydurulmaz.

Telegram ilk bildirim/onay kanalıdır. Ayrıntılar ek mesajlarla sunulabilir; gerekirse sonra kimlik denetimli web raporu eklenir. Böyle bir panel telefon/tablet/bilgisayardan erişilebilir tasarlanır; API secret istemciye gönderilmez. Telegram ve rapor paneli henüz uygulanmadı.

## İki ayrı işlem yetkisi

| Mod | Yeni giriş yetkisi | Pozisyon yönetimi |
|---|---|---|
| A — Sinyal sonrası onay (varsayılan) | Kullanıcının raporlanmış plan sürümüne açık onayı gerekir | Onay kapsamındaki koruma ve çıkışlar otomatik uygulanır |
| B — Önceden etkinleştirilen plan | Kullanıcının belirli plan sürümünü açıkça etkinleştirmesi ön yetkidir | Yalnızca tanımlı koşul, süre, miktar ve eylemler içinde ek onaysız yürütülür |

Mod A'da yanıt yoksa, ret veya süre sonu varsa giriş yapılmaz. Onaydan sonra fiyat, veri, plan koşulları ve risk yeniden kontrol edilir. Önemli değişiklik yeni rapor/onay ister. Risk ihlali ve kritik veri eksikliği kullanıcı onayıyla aşılamaz.

Mod B genel takdir yetkisi değildir. Fibonacci girişleri, kademeli hedefler, stop, varsa maliyete stop taşıma, geçerlilik ve çalıştırma sayısı etkinleştirme özetinde tanımlanır. Pozisyon büyütme, yön değiştirme, riski artıran stop değişimi ve yeniden giriş ancak etkinleştirilen sürümde açıkça izinli ve teknik olarak desteklenmişse uygulanabilir; aksi hâlde yeni yetki gerekir. Her hareket bildirilir. AI kendiliğinden mod değiştiremez.

İki mod farklı planlarda paralel kullanılabilir; aynı sembol/pozisyonu etkileyen çelişkili planlar birlikte etkinleştirilmez. Koruma onarımı ve önceden izinli risk azaltıcı çıkışlar ayrıca onay beklemez. Plan iptali bekleyen girişleri durdurur; açık pozisyonun korumasını kaldırmaz. Pozisyon kapatma ayrı açık eylemdir.

## Mevcut uygulama durumu

- Demo bağlantı/hesap okuma, limit oluşturma-sorgulama-iptal, küçük LONG açma ve kısmi/tam kapatma doğrulandı.
- SQLite kayıtları, tekrar önleme, demo risk sınırları, tek yürütücü kilidi, yönetilen one-way LONG oturumu ve watchdog mevcut.
- 35 çevrimdışı test; gerçek demo süreç kesintisi, iki ayrı süreçte devralma ve iptal edilen stopun tek onarımı doğrulandı. Son senaryo açık emir/pozisyon bırakmadan kapandı; sürekli arka plan servisi kurulmadı.
- Plan şeması v1 ve yerel CLI Mod A onayı/Mod B etkinleştirmesi mevcut. Tek girişli demo LONG, 1–8 kademeli hedef, izin verilmiş hedef sonrası giriş fiyatına stop taşıma, süre/sürüm/çelişki ve kurtarma ağsız testlerle doğrulandı. Yeni plan/kademeli çıkış yolu henüz gerçek demo hesabında onaylanıp yürütülmedi. Ara hedefler çalışan watchdog üzerinden MARKET çıkışla uygulanır; borsada tam stop ve son hedef yedeği tutulur. Net maliyet/komisyon sonrası sıfır zarar garantisi yoktur.
- TradingView/Pine/webhook, zengin analiz, haber/AI ve Telegram onayı henüz geliştirilmedi. Yerel onay, uzaktan kullanıcı kimlik doğrulaması değildir. Eski demo giriş deneyleri ayrıca `--test-only` ister; üretim sinyal yolu değildir.
- Temel canlı piyasa okuma ve analiz eklendi: BTC/ETH için W/D/4H/1H/15M, ayrı SQLite mum deposu, veri bütünlüğü, EMA20/50, RSI14, ATR14 ve 7 günlük hacim raporu. 3010 canlı mum ve önbellekten aynı sonuç doğrulandı; toplam 105 ağsız test başarılı. Bu rapor gerçek piyasa verisi kullanır fakat plan veya emir üretmez. Piyasa yapısı, dominans/akış ve haber/AI aşamaları henüz yoktur.
- SHORT/hedge, stop/TP'nin fiyatla tetiklenerek gerçekleşmesi ve canlı erişim doğrulanmadı. Demo başarıları tüm stratejilerin desteği anlamına gelmez.

## Kesinleşen tercihler

- Önce yerel bilgisayarda geliştirme. VS Code ve Codex kullanılacak.
- İlk öncelik: analiz motorundan önce Binance bağlantısını ve emir yeteneklerini doğrulamak.
- Önce demo ortamında emir akışını test etmek; gerçek hesap erişimini ayrı doğrulamak.
- Paralel piyasa analizi ve hem anlık izleme hem mum kapanışında kapsamlı analiz.
- İleride kesintisiz çalışmak için güvenli bir sunucuya taşınabilir tasarım. Domain zorunlu değil.
- Ürün geliştirme aşamasındadır; planlanan yetenekler uygulanıp doğrulanmadan kullanılabilir sayılmaz.
- Binance Global USD-M Futures ile devam edilecek. KuCoin araştırıldı; geçiş kararı alınmadı.
- Varsayılan akış yeni işlem öncesi onaydır; açıkça etkinleştirilmiş Mod B planları kendi sınırlarında ön yetkiyle yürüyebilir.

## Kesinleşmemiş konular

AI sağlayıcısı/modeli, haber ve dominans veri sağlayıcısı, coin listesi, bütçe, işlem riski, kaldıraç, günlük kayıp limiti ve sunucu sağlayıcısı seçilmedi. Önceki sohbette geçen %0,5 risk, %2 günlük kayıp, 2x kaldıraç, 35/45/20 ağırlıkları yalnızca öneriydi; kullanıcı onayı sayılmaz.

Akış veri sağlayıcısı, onay süreleri/fiyat toleransları ve TradingView hesap/yayınlama tercihi de kesinleşmedi. "10 veya 100 dolar" nominal pozisyon, teminat ya da azami kayıp anlamına gelebilir; plan bu ayrımı zorunlu kılacak. Demo profil sayıları canlı risk onayı değildir. Sohbette geçen 2 dakikalık onay süresi yalnızca örnektir.

Türkiye için Binance Global Futures ve Futures API uygunluğu kesin olarak doğrulanmadı. Binance TR ve Binance Global ayrı değerlendirilmeli. Teknik erişim ile hukuki uygunluk aynı şey değildir. Hesaba özel erişim doğrulanmadan gerçek Futures kullanılabilir varsayılmamalı.

## Başarı tanımı

Önce izlenebilir işlem/koruma altyapısı; her sinyalin gerekçeli bildirimi; kapsamı belli ve sürümlenmiş kullanıcı yetkisi; ardından ölçülebilir analiz kalitesi ve ayrı canlı onayı. Kârlılık garantisi yoktur. Demo emir başarısı strateji kârlılığını veya gerçek hesap yetkisini kanıtlamaz. Takvim tek başına canlıya geçiş ölçütü değildir.
