# Küçük bütçeli Demo işlem kabulü — 14 Kasım 2026

Kullanıcı bu konuşmada günlük güvenlik kuralını değiştirmeyi ve küçük tutarlı Demo özellik testleri için işlem açmayı açıkça yetkilendirdi. Gerçek Binance bağlantısı kapalıdır.

## Risk değişikliğinin kapsamı

Varsayılan risk-demo.json değiştirilmedi. Sadece bu gözetimli, tek seferlik koşuda başlangıçta okunan 529,69467203 USDT günlük zarara 3 USDT ek bütçe tanımlandı: sabit günlük tavan 532,69467203 USDT. Gerçek zarar verisi her motor ön kontrolüne aynen girer; sıfırlanmaz, test içinde tavan yeniden hesaplanıp büyütülmez.

Tek pozisyon, 60 USDT toplam nominal ve işlem başına/toplam açık riskte 1 USDT stop+masraf bütçesi kullanılır. Bunlar öngörülen risk kontrolleridir; stop kayması, fiyat boşluğu veya borsa/ağ hatası nedeniyle kesin zarar garantisi değildir. Test girişleri on dakikalık pencere ve sıralı üç senaryo ile sınırlıdır. Kaldıraç, teminat ve hesap modu değiştirilmez.

Test aracı kalıcı kayıt ve yedek alır; hazır hesap, son durumdaki geçmiş ve gerçek motor risk kontrolü geçmeden giriş durdurmasını kaldırmaz. Her senaryo sonunda yalnız sahipliği doğrulanan giriş iptal edilir, varsa kendi pozisyonu reduceOnly kapatılır ve koruma emirleri motor üzerinden temizlenir. Tur sonunda giriş durdurması geri konur. Bilinmeyen teslimde yeni kimlikle tekrar giriş yoktur.

## Senaryolar ve sınır

Bu tur: LONG LIMIT bekleme/iptal, asgari tutarlı LONG MARKET giriş/stop/hedef/azaltarak kapatma, ardından aynı kapsamda SHORT. Teknik planlar PlanService sürüm/onay/tek kullanımlık giriş ve V2Runner niyet/rezerv/sahiplik denetimlerini kullanır. Bu yetki yalnız açıkça istenen Demo teknik testleri içindir.

Grafik kaynaklı gölge olay/onay/bağımsız izleyici kabulü bu teknik planlardan ayrıdır; grafik bağını taklit eden olay veya sahte kanıt üretilmez. Bu tur grafik uçtan uca kabulü, stop/hedefin fiyatla gerçekten tetiklenmesi, kısmi hedef, break-even, takip stopu, grid, neutral/hedge, çoklu oturum veya gerçek hesap kabulünün tamamlandığı anlamına gelmez. Bunlar ayrı ve küçük bütçeli kabul senaryoları gerektirir. Mevcut çevrimdışı regresyon kapsamı gerçek borsa kanıtının yerine geçmez.

Araç: scripts/bot/run_bounded_demo_acceptance.py. Gerçek koşu raporu: reports/bounded-demo-acceptance-0441916fb777.json. İşlem öncesi yedek: reports/bounded-demo-before-0441916fb777.sqlite3.

Bu araç her açık çağrıda yeni bütçe oluşturabildiğinden otomatik döngüye veya zamanlayıcıya konmamalıdır; mevcut kullanıcı yetkisi sınırsız, gözetimsiz zarar bütçesi değildir. İlk çağrıdan sonra zaman yuvarlaması ve hesap okuma gecikmesi nedeniyle yalnız henüz oluşturulmamış SHORT senaryosu aynı koşu kimliği, başlangıç zarar tavanı ve hesapla devam ettirildi. Geçmişte tamamlanan senaryolar tekrarlanmadı. İlk on dakikalık pencereye, okuma gecikmesi düzeltmesinden sonra bir defaya mahsus beş dakika eklendi; zarar bütçesi artırılmadı. Yeni turdan önce önceki sonuç ve birikimli test zararı incelenmelidir.


## Geliştirmede bulunan sorunlar

ISO mikro saniye yuvarlaması yeni planın oluşturma anını Windows saatinin aynı tikinde çok az gelecekte gösterebiliyordu. Teknik test planının created_at değeri bir saniye önceye yazılarak düzeltildi; plan süresi ve gelecekte plan reddi kuralı korunur. Tekrarlanabilir regresyon testi eklendi.

Seri üç sembol metadatası sorgusu, Demo ağ gecikmesinde tüm hesap görüntüsünün 15 saniyede toplanmasını zorlaştırdı. Gerçek DemoExchange için bu üç bağımsız GET ayrı HTTP taşıyıcılarıyla paralel alınır; sunucu saat farkı ve ortak host hız sınırlayıcısı korunur. Özel adaptörler/taşıyıcılar kendi davranışını korur. Herhangi bir sorgu hatası tüm görüntüyü engeller. Tazelik sınırı artırılmadı. Test aracında yalnız tam olarak bu görüntü-süresi hatası için en fazla üç salt okunur toplama denemesi vardır; diğer hata, belirsiz emir ve mutasyon yeniden denenmez.

Paralel örtüşme, ayrı bağlantı/taşıyıcı, ortak governor ve hata halinde engelleme için iki test; küçük bütçe, sahiplik olmadan azaltmama, sıfır dolumda azaltma göndermeme, zaman yuvarlaması ve sınırlı okuma tekrarı için sekiz test eklendi.


## Gerçek Demo sonucu

Üç senaryo PASSED; üç plan CLOSED. LIMIT giriş NEW görüldükten sonra iptal edildi. LONG 0,0008 BTC, 68266,70 USDT ortalamayla; SHORT 0,0008 BTC, 68130,90 USDT ortalamayla FILLED oldu. Yaklaşık 54,5 USDT nominal büyüklükteki her pozisyonda STOP_MARKET ve TAKE_PROFIT_MARKET borsada NEW olarak doğrulandı; ardından sahipliği kayıtlı reduceOnly kapanış ve koruma temizliği yapıldı. Son motor hesap görüntüsü pozisyonsuz/emirsiz; etkin oturum sıfır ve giriş durdurması geri kondu.

Başlangıç günlük zarar 529,69467203, son günlük zarar 529,75247855 USDT: bu turun net ilave zarar/masrafı 0,05780652 USDT. Bu yalnız bu kısa turun sonucudur; ilerideki işlemler için zarar garantisi değildir.

1146 Python testi ve 36/36 grafik replay senaryosu geçti. Günlük risk kaydı korunmuştur. Yeni bir işlem veya gözetimsiz çalışma açık bırakılmadı.


Bağımsız son GET kontrolü de 0 pozisyon, 0 normal emir ve 0 koşullu emir doğruladı. Son üç koruma/kapanış niyeti terminal yanıtlarıyla yedekli ve atomik uzlaştırıldı; ilk LONG sonrası üç kayıt da aynı şekilde uzlaştırılmıştı. Toplam 29 niyetin tamamı terminal, etkin oturum sıfır. Kanıt: reports/bounded-demo-final-history-20261114.json ve reports/bounded-demo-final-account-20261114.json. Son acceptance-check sonucu bilinçli BLOCKED: giriş durdurması aktif, bağımsız grafik kurtarma izleyicisi çalışmıyor ve taze grafik plan/onayı yok. Bu sonuç hesapta açık risk bulunduğu anlamına gelmez; yeni otomatik giriş yetkisi verilmediğini gösterir.

Kalan kabul sırası: gerçek fiyatla stop/hedef tetiklenmesi; kısmi hedef ve break-even; takip stopu; yönlü grid ve yeniden başlatma; ayrı hedge/neutral senaryosu; ardından taze grafik gölge olayı → önizleme → hesap incelemesi → onay → bağımsız izleyici ile uçtan uca kabul. Her senaryonun borsa kanıtı ve küçük bütçesi ayrı kaydedilmelidir. Bu teslimde bu kalan özellikler gerçek Demo kabulünden geçmiş olarak işaretlenmedi.
