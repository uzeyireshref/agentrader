# T05 — ışın, çizgi uzatma ve bölge kapsamı

12 Kasım 2026. Tamamlandı; plan10/27, sıradakiT07 çizim yönetimi.

Çizgi araçları menüsünde Işın, Uzatılmış çizgi ve Yatay ışın bulunur. İki noktalı ışının yönünü noktaların sırası belirler. Uzatılmış çizgi iki yöne uzanır; yatay ışın başlangıç zamanından sağa uzanır. Nokta tutamakları ve sayısal form aynı tick politikasını kullanır. Kaydetme, geri al/yinele ve uygulama yeniden açılışı geometriyi korur. Açık/koyu temada mevcut kabuk ve çizim düzeni kullanılır.

Yeni çizgiler chart-line/1, açıkça seçilen bölge kapsamı chart-zone/1 olarak format_version=3 üzerinden kaydedilir. İki nokta arası ve Tüm zamanlar bölge seçenekleri ayrıdır. Eski trend/bölge kayıtlarının anlamı ve revision'ı değişmez. v1/v2 istemciler yeni geometrileri okuyamaz/değiştiremez; liste sonuçları eski uyumlu nesnelerle sınırlıdır.

Kanonik fiyat sorguları exact rational/Decimal kullanır. Eğimli uzatma yalnız doğrulanmış kesintisiz yüklü zaman gridinde hesaplanır ve çizilir. Grid dışı, boşluk veya pozitif olmayan projeksiyon açıkça engellenir; gelecekte henüz yüklenmemiş mumlara sessiz fiyat tahmini yapılmaz. Yatay ışın sabit fiyat ve ileri zaman kapsamındadır. Çizimler emir veya bot yetkisi oluşturmaz.

742 Python testi,176 frontend testi ve üretim derlemesi geçti. check_chart_t05.py gerçek production App, HTTP ve izole SQLite ile10 kontrolü geçti: dört pointer çizimi, yön/kanonik fiyat, yatay kapsam, form ve tutamak düzenleme, geri al/yinele, bölge yükseltme, eski kayıt korunması, boşluk engeli ve server/page restart. G01/G06/G02/G03 toplam55 regresyon kontrolü geçti. Kullanıcı veritabanı kullanılmadı; dış istek ve page error yok. Test tıklamaları motorun çift tıklama eşiğinden ayrı tutuldu.

Kanıt: reports/chart-t05-validation-20261112.json; koyu/açık ekranlar ve source/build SHA256 manifesti reports/chart-t05-delivery-20261112.json. Bunlar fiziksel GPU/touch, uzun canlı ağ kesintisi veya tam TradingView parity kabulü değildir; QA01 kapsamı korunur.
