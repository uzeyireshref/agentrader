# B5 — Görünür masaüstü ve fiziksel giriş kabul görevi

9 Kasım 2026. Proje: C:/Users/asus/agentrader. Kullanıcı bu dosyadaki testlerin Codex masaüstü proje sohbetinde uygulanmasını istedi. **Üretim kodunu, stilleri, bağımlılıkları ve planın tamamlanma işaretlerini değiştirme.** Test yardımcıları ve kanıtlar yalnız reports/ altında oluşturulabilir. Sorun bulursan yeniden üret, raporla; bu görevde düzeltme yapma.

## Amaç ve başlangıç

B5 KISMİ/AÇIK, 9/25 görev tamamlandı; C1 başlamayacak. Otomatik kanıtlar başarılı: 14 B5 kontrolü, 40 A senaryosu, B2 18/B3 10/B4 13 kontrolleri, 116 frontend testi. Bunları yeniden çalıştırmak görünür/fiziksel kabulün yerine geçmez. 30 dakika performans testi bu görevde istenmiyor.

Güncel beklenen ana bundle: index-CYPASoGC.js. Önce agentrader/web_assets/index.html ve data/development-progress.json ile doğrula. Fark varsa gözlenen bundle'ı kaydet; eski sürüm adına test sonucu yazma. Aşağıdaki dosyaları oku:

- [Aktif plan](../PLAN.md)
- [Etkileşim sözleşmesi](../INTERACTION.md)
- [Otomatik B5 raporu](../../../reports/chart-access-browser-20261109.json)
- [Son doğruluk değerlendirmesi](../../../reports/chart-correctness-after-access-20261109.json)

## Test ortamını izole hazırla

1. Görünür masaüstü Chrome penceresi kullan. Oturumun mevcut Browser/Computer Use becerilerine ve araç güvenlik kurallarına uy. Headless Chromium sonucunu görünür masaüstü diye yazma. Kontrol servisi güvenlik nedeniyle durursa aynı kısıtı başka otomasyonla aşmaya çalışma; kalanları NOT_TESTED olarak kaydet.
2. Kullanıcının 8765 sunucusunu, mevcut sekmelerini ve data/ altındaki uygulama/işlem/market veritabanlarını değiştirme. Sırları/.env dosyasını okuma. Hesap/emir API'sine veya dış mesaj servisine erişme.
3. scripts/check_local_api.py içindeki alt süreç düzenini örnek alarak kendine ait boş bir loopback portunda izole sunucu başlat. Alt sürece özgü ortamda AGENTRADER_WEB_DATABASE, AGENTRADER_CHART_DATABASE, AGENTRADER_EXECUTION_DATABASE yollarını yalnız bu teste ait ayrı dosyalara yönlendir; AGENTRADER_WEB_TOKEN boş olsun. Global ortamı değiştirme. Komut: python -m agentrader web serve --port <seçilen-boş-port>. Yardımcı süreçler Windows'ta gizli başlatılır; görünür olması gereken uygulama test Chrome penceresidir.
4. Ayrı Chrome test sekmesi/profiliyle http://127.0.0.1:<port>/?diagnostics=1 aç. FixtureLab bu görevin ana ekranı değildir; gerçek App ve toolbar test edilecek. Public BTCUSDT/15m verisi yeterlidir; veri erişilemezse bunu ayır, gerekirse mevcut kontrollü test verisini yalnız bu izole sunucuda kullan ve açıkça belirt.
5. Gerekli dört çizimi yalnız izole test deposunda oluştur veya test verisi olarak hazırla. Kaynak olarak scripts/check_chart_access.py geometrileri kullanılabilir. Test sonunda yalnız kendi PID/port/sunucun ve test sekmen üzerinde temizlik yap; kullanıcı Chrome'unu veya başka süreçleri kapatma. Kanıtları silme.

## Donanım ve kanıt kuralı

Windows sürümü, Chrome sürümü, bundle, ekran çözünürlüğü/ölçekleme, window.devicePixelRatio, CSS viewport, giriş aygıtının türü ve testin görünür/headed olup olmadığını kaydet. Fiziksel touch/trackpad varlığını tahmin etme. Enjekte edilmiş mouse/wheel, DevTools mobil emülasyonu veya sentetik PointerEvent gerçek parmak/trackpad kanıtı değildir.

Gerçek fiziksel gesture'ı araç üretemiyorsa yalnız ilgili adımları kullanıcıya kısa ve açık biçimde uygulat; sonucu gözlemle. Donanım/katılım yoksa DEVICE_UNAVAILABLE veya NOT_TESTED yaz. Kullanıcının dokunmatik cihazı olmadığı varsayımıyla testi geçti sayma. Destek kapsamını daraltma kararı bu görevin yetkisinde değildir.

Her test için adımlar, beklenen, gözlenen, durum, kullanılan giriş türü ve kanıt dosyası yaz. Durumlar: PASS, FAIL, NOT_TESTED, DEVICE_UNAVAILABLE. İddia için yeterli kanıt yoksa PASS verme. Görünür ekranlar, gerekirse kısa video ve sayısal hizalama çıktısı kaydet; kişisel sekmeleri/hesap verilerini kanıta alma.

## Uygulanacak kabul adımları

| ID | Uygulama | Geçiş koşulu |
| --- | --- | --- |
| D01 | Görünür Chrome'da test URL/bundle ve dört çizimi doğrula. | Test penceresi ve grafik görünür; doğru sürüm; başlangıç kanıtı mevcut. |
| D02 | Farklı pencere boyutlarında yeniden boyutlandır; en az normal/geniş ve dar görünümü incele. 390×844 yalnız emülasyonla yapılırsa bunu açıkça yaz. | Toolbar kontrolleri ulaşılır, sayfada istenmeyen yatay taşma yok, mum/çizim görünümü bozulmaz. |
| D03 | Grafik alanına Tab ile gel. +/−, ←/→ ve End kullan; sonra input/select/editör alanına odaklanıp ilgili tuşları kullan. | Odak görünür; yalnız grafik odaktayken gezinir; yazı/form davranışı bozulmaz. Tab/Shift+Tab ile alan terk edilebilir. |
| D04 | Klavyeyle Grafiğe geç bağlantısını ve Ölçek / Güncel mumlara dön / Görünümü sıfırla kontrollerini çalıştır. | Adlar anlaşılır; manuel/otomatik durum tutarlı; son mum dönüşü zoom'u korur; reset veriyi/çizimleri silmez. |
| D05 | Gerçek pencere üzerinde uygulamanın tam ekran düğmesiyle gir; toolbar ve çıkış düğmesini incele; düğmeyle çık. | Gerçek OS/Chrome tam ekranı görünür; çıkış kontrolü erişilir; dönüşte odak kaybolmaz, aralık ve çizim hizası korunur. F11 bu uygulama Fullscreen API testinin yerine geçmez. |
| D06 | Tam ekrana yeniden gir ve Escape ile çık; resize, RSI aç/kapat, dar/geniş geçişlerinde hizalama ölç. | Escape çıkışı çalışır, kontroller tekrar kullanılabilir; en az normal/tam ekran/çıkış sonrası geçerli hizalama ≤1 CSS px. NOT_MEASURED/atlanan noktalar PASS sayılmaz. Sayısal hizalama raster kabulü diye sunulmaz; görsel kırpılma ayrıca gözlenir. |
| D07 | Fiziksel trackpad ile yatay, dikey ve çapraz gezinme; destekleniyorsa pinch. | Dikey hareket öngörülebilir zoom, yatay pan; çapraz hareket istemsiz iki işlem yapmaz; kontrolsüz sıçrama yok. Fiziksel pinch platformun verdiği gerçek olayla kaydedilir. |
| D08 | Gerçek dokunmatik ekranda boş grafik üzerinde yatay pan, dikey sayfa scroll'u ve iki parmak pinch. | Sayfa dikey kaydırılabilir, yatay grafik gezinmesi/pinch kullanılabilir; grafik sayfayı hapsetmez; istemsiz çizim kaydı yok. |
| D09 | Dokunmatik ortamda bir çizimi/tutamacı taşırken ikinci parmak ekle, ardından bırak/iptal et. | Yalnız sahip pointer çizimi değiştirir; diğer çizimler değişmez; iptal kayıt bırakmaz; gezinme kilidi geri açılır. Yalnız izole depo kullanılacak. |

D07–D09 fiziksel donanım gerektirir. Görünür mouse/klavye kontrolleri başarılı olsa bile bu üç adımın yokluğu tam B5 kabulü değildir. Raster, ekran okuyucu ve genel G01–G07 kabulü için bu görevin kapsamadığı maddeler ayrıca açık kalır.

## Rapor ve bitirme

- İnsan raporu: reports/chart-b5-desktop-acceptance-20261109.md
- Makine kaydı: reports/chart-b5-desktop-acceptance-20261109.json
- Kanıt klasörü: reports/b5-desktop-20261109/ (her koşu için yeni alt klasör; eski kanıtları ezme).
- Bu yollar zaten varsa önce oku; yeni koşuyu ekle, eski bulguları silme. Yanındaki JSON taslağı yalnız başlangıç şemasıdır, test sonucu değildir.

Raporda D01–D09 ayrı durumlarla bulunmalı. full_b5_accepted yalnız bütün zorunlu adımlar somut kanıtla PASS ise true olabilir. Aksi durumda false, next_task B5 kalır. Plan/progress tamamlanma sayısını veya C1 başlangıcını değiştirme; sonucu bu geliştirme sohbetinde değerlendireceğiz. Son mesajında görünür masaüstünde yapılanlar, fiziksel cihazda yapılanlar, yapılamayanlar ve rapor yolları açıkça ayrı olsun.


## Yeni masaüstü turunda yeniden deneme

Kullanıcı yeniden deneme istedi. Önceki raporu oku; önceki NOT_TESTED sonuçlarını silme ve yeni koşu klasörü aç. Yerel 8765 servisinin kapalı olduğu görüldü, geliştirme sohbetinde yeniden başlatıldı; ana sayfa ve /api/health HTTP200, statik bundle index-CYPASoGC.js doğrulandı. Bu yalnız HTTP hazırlık kontrolüdür; görünür/fiziksel test yerine geçmez. Sunucuya erişilemiyorsa önce yalnız sağlık kontrolü yap ve sonucu bildir; kullanıcının çalışan sunucusunu durdurma.

Yeni turda mevcut Computer Use/Browser güvenlik kurallarını yeniden uygula. Önceki durdurmanın kalktığını varsayma. Chrome URL'si güvenilir biçimde doğrulanamıyor ve servis duruyorsa yeni pencere, alternatif sürücü/otomasyon veya ayar değişikliğiyle etrafından dolaşma; kalan testleri NOT_TESTED kaydet. Kullanıcıdan güvenilir test sayfasını elle açması istenebilir; bu da araç güvenlik kontrolünün yerine geçmez. Hizmet düzeldiyse yalnız yukarıdaki izole test ortamında D01–D09'a devam et.

Fiziksel trackpad kullanıcı tarafından var diye doğrulandı; hareketleri test sırasında kendisi uygulayabilir. Trackpad cihaz varlığı D07 başarısı değildir. Dokunmatik ekran varlığı hâlâ bilinmiyor; D08/D09 için ayrıca gerçek donanım gerekir. B5 tam kabulü kapanmadan C1'e geçme; üretim kodunu değiştirme.
