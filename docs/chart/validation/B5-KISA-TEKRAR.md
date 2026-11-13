# B5 — Yalnız açık bulguların kısa tekrarı

9 Kasım 2026. Üretim kodunu/stili/bağımlılığı değiştirme. Önce [son masaüstü raporunu](../../../reports/chart-b5-desktop-acceptance-20261109.json) oku. D01/D02/D04 için geçerli önceki kanıtları koru; bütün D01–D09 turunu veya uzun dayanıklılık testini baştan yapma. Rapor tamamlandı fakat B5 kabul edilmedi. Yeni ana bundle index-C7GQBkeB.js; mutlaka gerçekten yüklenen sürümü doğrula.

## Neden tekrar gerekiyor?

D07 fiziksel yatay harekette 20 bar aralığı %17,38 değişti, çaprazda pan+zoom bildirildi. Ham olaylar olmadığı için eski fiziksel koşunun kesin kök nedeni bilinmiyor. Native wheel filtresinde eksen her olayda seçiliyordu; bir trackpad hareketi boyunca değişebilen minör deltalar mod değiştirebiliyordu. Artık 200 ms boşluğa kadar aynı eksen korunur; Ctrl/pinch ayrı zoom hareketi başlatır. Sıfır/geçersiz delta yoksayılır. Eksenin yalnız baştaki yanlış hareketten seçilmesi veya 200 ms'den uzun donanım boşlukları hâlâ gerçek testte değerlendirilmelidir. Otomatik başarı fiziksel başarı sayılmaz.

D06 için AlignmentPanel artık diagnostics=1 ekranında fullscreen panelinin içindedir; ölçüm düğmesi tam ekranda erişilir. Bu normal kullanıcı ekranına tanılama eklemez. D05 OS tam ekranına ilişkin önceki foreground/Alt-Tab karışıklığı ve D03 select tuşu kontrolü de açıktır.

## Hazırlık ve otomasyon

- Önceki B5 görevindeki izolasyonu koru: ayrı port/veritabanları; 8765 kullanıcı alanını değiştirme; hesap/emir/sır erişimi yok. Mevcut test sunucusu kendi izole sürecinse aynı depoyu kullanabilirsin; aksi durumda yeni izole ortam oluştur. Gereksiz rebuild, skill yükleme, araştırma ve paket kurulumu yapma.
- Desteklenen Chrome entegrasyonunu kullan; native Windows kontrolüne yalnız zorunlu görünür pencere/OS gözlemi için ihtiyaç varsa başvur. Bir güvenlik servisi durursa başka otomasyonla o kısıtı aşma.
- Yalnız şu kontrolleri kendin otomatik tamamla: D03 select odak/ok/End izolasyonu; D05 uygulama düğmesiyle gerçek görünür fullscreen ve düğme/Escape çıkışı; D06 normal/fullscreen/çıkışta mevcut ölçüm düğmesinden geçerli hizalama. Kullanıcıya bu adımları tek tek devretme. Pencereyi sabitle; gözlem sırasında Alt-Tab yapıp görüntüyü bozma. Görünür OS sonucu doğrulanamıyorsa belirt, PASS verme.
- D01'i yalnız yeni sürüm/izole URL doğrulaması kadar tekrarla. D02'nin tamamını, tüm göstergelerin 50 turunu, 30 dakika testi ve tüm otomatik regresyonları tekrar çalıştırma. Gerekli kontrol başarısızsa kısa kanıtla dur; aynı hareketi defalarca yaptırma.

## Kullanıcıdan yalnız fiziksel trackpad hareketleri

Bunları otomasyon gerçek fiziksel giriş olarak üretemez. Kullanıcıya önce tek bir kısa açıklama ver; test alanını ve hareket sırasını hazırla. Gerekirse alanda üç etiketli geçici test işareti/yardımcısı yalnız reports/ test ortamında oluştur; üretim arayüzünü değiştirme. Kullanıcıdan en fazla birer yatay, çapraz ve destekleniyorsa pinch hareketi iste. Otomatik dikey wheel kanıtını fiziksel pinch diye sunma. Her hareket için ayrı uzun soru/tekrar turu açma.

Hareketten önce native wheel olaylarını test sekmesinde kaydet: hedef alan, monotonik zaman, deltaX/Y, deltaMode, ctrlKey, isTrusted; ekran/viewport/DPR ve aynı referans mumların koordinatlarını önce/sonra al. Kaydı üretim filtresinden önce capture aşamasında yap, yeniden yönlendirilmiş sentetik olayları fiziksel olaylarla karıştırma. isTrusted tek başına cihaz kanıtı değildir; gerçek kullanıcı katılımını ayrıca yaz. Bu kayıt yalnız test sekmesine ait olsun, genel tarama/klavye kaydı yapma.

1. Kısa yatay hareket: zaman pan'i olmalı; aynı 20 mum arası mesafe ≤1 CSS px değişmeli.
2. Tek kısa çapraz hareket: tek gesture içinde pan/zoom modu değişmemeli. Başlangıç ekseni baskınlığa göre seçilir. Ham olay dizisiyle 200 ms gesture sınırlarını göster.
3. Pinch destekleniyorsa: fiyat ekseni değil zaman zoom'u gözlenebilir; platformun gerçek ctrl/wheel/pinch olay biçimini kaydet. Desteklenmiyorsa açıklamasız PASS verme.

Kullanıcı bilgisayarı yalnız fiziksel hareket anında devralsın; otomatik ölçüm sürerken başka pencereye geçmesin. Toplam fiziksel katılım hedefi bir dakikadan kısa; bu bir performans kabul eşiği değildir. İlk başarısızlıkta trace+geometriyi kaydet, yeni bir uzun döngüye girme.

## Rapor ve bitiş

Kanıtları reports/b5-desktop-20261109/ altında yeni koşu klasörüne; raporu reports/chart-b5-short-retest-20261109.md ve .json yollarına yaz. Eski fiziksel FAIL kaydını silme. Her alt adım için PASS/FAIL/NOT_TESTED/DEVICE_UNAVAILABLE ve kanıt yolu ver. Önceki kanıtın yeniden kullanıldığını açıkça belirt.

Dokunmatik ekran olmadığı kullanıcı tarafından doğrulandı: D08/D09 DEVICE_UNAVAILABLE kalır. Kullanıcı adına dokunmatik desteğini kapsam dışına çıkarma; bunun için ayrıca ürün kapsamı kararı gerekir. B5 ve 9/25 durumunu/C1 başlangıcını değiştirme; sonuç geliştirme sohbetinde değerlendirilecek. Ham trace yoksa fiziksel sorunun kesin çözüldüğünü iddia etme.
