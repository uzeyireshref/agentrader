# Grafik ve Bot Terminali Uygulama Planı

Tarih: 16 Kasım 2026.
Durum: Frontend ve yerel Demo API/worker entegrasyonu uygulandı. Çalıştırma ve kabul sınırları [INTEGRATION.md](INTEGRATION.md) içinde. Desteklenen tarayıcı bağlantısı kullanılamadığı için yeni bağlı modun tam tarayıcı kabulü açık. Gerçek Demo emir kabulü ve müşteri yayını yapılmadı. Önceki tasarım turu [DESIGN-REVIEW.md](DESIGN-REVIEW.md), ilerleme [PROGRESS.md](PROGRESS.md) içinde.

## Hedef ve çalışma düzeni

Önce yerelde, emir göndermeyen tıklanabilir prototip hazırlanacak. Tasarım değerlendirildikten sonra mevcut bot servislerine bağlanacak; müşteri yayını son aşamada yapılacak.

Grafik, API ve worker bilgisayarda birlikte çalıştırılabilecek. Geliştirmeye başlamak için sunucu veya ücretli servis gerekmeyecek. Yerel ve müşteri ortamlarının ayarları, anahtarları ve veritabanları ayrı tutulacak. Yerel değişiklikler dağıtılana kadar müşteri sürümünü etkilemeyecek. Binance Demo bağlantısı internet gerektirir.

## 1. Araştırma ve yetenek eşleştirmesi

- [3Commas](https://help.3commas.io/en/articles/16281054-trading-terminal-overview), [Bitsgap](https://bitsgap.com/blog/evaluate-your-bots-performance-with-new-bot-details), [Hummingbot](https://hummingbot.org/dashboard/instances/) ve [Freqtrade](https://www.freqtrade.io/en/stable/rest-api/) üzerinden işlem kurma, bot yönetimi, sonuç takibi ve uzaktan erişim yaklaşımları incelenecek.
- Her öneri için kullanıcı ihtiyacı, kaynak, mevcut bot desteği, kısıt, eksik API, ekran ve kabul senaryosu kaydedilecek.
- Mevcut USD-M yeteneklerinin tamamı değerlendirilecek; ertelenmiş ürünler ve yalnız dahili/test amaçlı yollar kullanılabilir özellik sayılmayacak.
- Araştırma, tasarım kararları ve uygulama ilerlemesi ayrı belgelerde izlenecek.
- Başlangıç referansları: [borsa geliştirme planı](../exchange-operations-20261115/PLAN.md), [öncelik kararı](../exchange-operations-20261115/PRIORITY-REVIEW.md) ve [grafik–bot ortak arayüzü](../../integration/history/46-BOT-GRAFIK-ORTAK-ARAYUZ-VE-CIZIM-ADAPTORU-GELISTIRME-PLANI.md). Uygulama öncesi güncel kod ve teslimler yeniden doğrulanacak.

## 2. Ortak arayüz ve prototip

- Aynı uygulamada üstten **Grafik / Bot** geçişi olacak.
- Grafik ekranında işlem yan paneli açılacak; bot ekranındaki emir ve pozisyonlardan ilgili grafiğe gidilebilecek.
- Geçişlerde sembol, zaman dilimi, çalışma alanı ve işlem taslağı korunacak.
- Türkçe, mevcut grafikle uyumlu, sade ve şık terminal tasarlanacak. Deneyimli kullanıcı için ayrıntılı kontroller gelişmiş bölümlerde bulunacak.
- Masaüstünde içerik ve işlem paneli birlikte, mobilde tek sütun kullanılacak. Mevcut tema tercihi korunacak.

Bot ekranının bölümleri:

| Bölüm | İşlev |
|---|---|
| Genel bakış | Hesap, aktif oturumlar, açık risk, finansal sonuç ve dikkat gerektiren durumlar |
| Yeni işlem | SINGLE, GRID ve NEUTRAL için mevcut şemalara uygun formlar |
| Pozisyonlar | Koruma emirleri, trailing ve desteklenen artır/azalt/kapat/tersine çevir eylemleri |
| Emirler | Normal/algo emirler, açık/geçmiş kayıtlar, değiştirme, iptal ve toplu işlemler |
| Komut günlüğü | Talep, onay, gönderim, teyit ve kısmi/belirsiz sonuçlar |
| Gelişmiş | Hesap ayarları, iptal timer’ı, geçmiş/dışa aktarma ve operasyon durumu |

Prototip ayrı senaryo verileriyle çalışacak ve “Tasarım önizlemesi” olarak işaretlenecek. Gerçek emir gönderemeyecek. Boş hesap, bekleyen emir, kısmi dolum, ret ve bağlantı kesintisi durumları değerlendirildikten sonra entegrasyona geçilecek.

## 3. Mevcut bota bağlantı

- Mevcut salt okunur `/api/commands` korunacak; finansal işlemler için `/api/bot` altında HTTP adaptörü eklenecek.
- Adaptör, CLI’nin kullandığı mevcut plan, yetkilendirme, risk, komut ve sonuç teyidi servislerine bağlanacak.
- Bağlam/yetenek keşfi, plan oluşturma, preflight, onay, komut hazırlama/uygulama, sorgulama ve uzlaştırma desteklenecek.
- Komut kimliği, hesap kapsamı, plan sürümü ve digest korunacak; tutarlar decimal metin olarak taşınacak.
- Kalıcı worker tarayıcıdan bağımsız çalışacak. Tarayıcı kapanması bot takibini durdurmayacak.

İşlem akışı:

**Taslak → doğrulama → etki/risk önizlemesi → kullanıcı onayı → uygulama → sonuç teyidi**

Grafikten alınan giriş/stop/hedef taslağa çizim revizyonu ve piyasa bağlamıyla aktarılacak. Sonraki çizim değişikliği onaylı işlemi değiştirmeyecek. Değişen parametre veya hesap bağlamı yeniden önizleme ve onay gerektirecek.

ACK veya HTTP başarısı dolum sayılmayacak. Belirsiz sonuç mevcut kimlikle sorgulanacak; körlemesine yeniden emir gönderilmeyecek. Toplu işlemlerin sonuçları üye bazında gösterilecek.

Yönetim eylemleri gerçek destek sınırlarıyla etkinleştirilecek. Pozisyon artırma/azaltma/kapatma/tersine çevirme ve native trailing mevcut adaptörün sahip olunan V2 SINGLE sınırını koruyacak. GRID ve NEUTRAL kendi yürütme ve durdurma davranışlarını koruyacak. Yabancı veya yönetilemeyen pozisyonlarda desteklenmeyen eylemler gerekçesiyle kapalı olacak.

“Yeni girişleri durdur”, “Emirleri iptal et” ve “Pozisyonu kapat” ayrı eylemler olacak.

## 4. Yerel testten müşteri yayınına geçiş

- Yerel geliştirme ve Demo testi mevcut bilgisayarda yapılacak; müşteri sürümü ayrı yapılandırmayla hazırlanacak.
- Mevcut doğrulanmamış işlem günlüğü korunacak. Müşteri için doğrulanmış Demo hesap bağlamıyla ayrılmış depolar oluşturulacak.
- Yayın paketi tek Linux sunucuda HTTPS reverse proxy, API ve worker çalıştıracak şekilde hazırlanacak.
- Kalıcı depolama, süreç yeniden başlatma, tek yürütücü kilidi, yedekleme ve geri yükleme sağlanacak.
- Yerel çalışma varsayılanı korunacak. Uzaktan yayın açık yapılandırma, izinli alan adı/origin ve güvenilen proxy sınırı gerektirecek.
- Tek müşteri için yönetici tarafından oluşturulan giriş kullanılacak; genel kayıt olmayacak. Güvenli oturum, Secure/HttpOnly çerezler, oturum iptali, CSRF ve giriş denemesi sınırı uygulanacak.
- Borsa anahtarları yalnız backend ortamında tutulacak; frontend, geri bildirim ve günlüklerden çıkarılacak.
- Uygulama içi geri bildirim; açıklama, sayfa, sürüm ve isteğe bağlı komut referansıyla kaydedilecek. Kayıtlar geliştiriciye listelenebilir olacak.
- Sunucu ve alan adı müşteri yayını öncesinde sağlanacak; satın alma bu geliştirme çalışmasının parçası olmayacak.

## 5. Kabul ölçütleri ve varsayımlar

- Prototip hiçbir finansal istek göndermez.
- Grafik–Bot geçişi taslağı ve çalışma alanını korur.
- Her desteklenen işlem ailesi yetenek matrisiyle eşleşir.
- Çift tıklama, yenileme, iki sekme, zaman aşımı ve restart mükerrer emir üretmez.
- Kısmi dolum, iptal/dolum yarışı, eski onay ve sahiplik hataları doğru gösterilir.
- Yetkisiz HTTP/WebSocket erişimi, süresi dolmuş oturum ve yanlış origin reddedilir.
- Python/frontend regresyonları, grafik replay, masaüstü/mobil görsel kontroller ve geri yükleme doğrulanır.
- Müşteri testinden önce ayrılmış Binance Demo hesabında ayrıca yetkilendirilmiş emir yaşam döngüsü kabulü yapılır. Yerel testler borsa kabulü yerine geçmez.
- İlk sürüm tek müşteri, tek Demo hesap ve Türkçe arayüz içindir. AI, doğal dil komutları, yeni strateji motoru, gerçek para, yeni ürünler ve çok müşterili yapı kapsam dışındadır.

## Devam noktası

Geniş frontend turu, ayrıntılı işlem/pozisyon/toplu emir/hesap formları ve grafik aktarımıyla teslim edildi. Sonraki adım görsel değerlendirme ve mevcut bot servislerine bağlantıdır. Finansal yürütme başlamadı; ayrıntılı sınırlar UI-DELIVERY.md içinde korunur.
