# Grafik durumu ve çizim toparlanması

9 Kasım 2026. Veri ve çizim doğruluğu önceliğinde devam edildi.

Mum/hacim çizimi hata verdiğinde veri sıra numarası ilerlemiş oluyordu. Aynı sıra numaralı heartbeat, çizimi tekrar denemeden durumu LIVE yapabiliyordu. Yeni RenderRecovery, çizim başarısızlığını saklar; sonraki geçerli pakette tam yeniden çizim ister. Yeniden çizim de başarısızsa RENDER_ERROR korunur. Başarılı çizimden sonra paketin gerçek bağlantı durumu gösterilir. Sağlıklı heartbeat gereksiz çizim başlatmaz.

Geçmiş mum yüklemesindeki çizim hataları da aynı toparlanma yoluna bağlandı. Yanlış coin veya eski generation paketi toparlanmayı temizleyemez. Tanımsız durum etiketleri, geçersiz alım zamanları ve zaman bilgisi olmayan LIVE paketleri reddedilir.

## Doğrulama ve sınırlar

109 frontend testi ve TypeScript/Vite üretim derlemesi geçti. Yedi yeni test: kalıcı hata ve tekrarlanan heartbeat; başarılı tam yeniden çizim; sağlıklı heartbeat ve artımlı güncelleme; yanlış market/eski paket; geçmiş çizim hatası; geçersiz zaman; tanımsız durum ve geçerli başlangıç durumu.

Testler kontrollü çizim callback ve paketlerle Node üzerinde çalıştı. Gerçek motorun hata üretmesi veya tam App/tarayıcı arıza senaryosu bu tur yürütülmedi. Toparlanma kapsamı mum ve hacim yazımıdır; ayrı gösterge efektleri için genel hata toparlanması kabulü değildir. Yeni masaüstü testi gerekmiyor. Genel grafik kabulü ve performansın açık kapsamları korunuyor.

Backend değişmedi; önceki 671 Python testi ve public canlı veri probe bu tur tekrarlanmadı. Yeni ana bundle index-CwoQUoEc.js. Bot bağlantısı, hesap/emir işlemi veya kullanıcı çizimlerine test yazımı yapılmadı.
