# T07 — çizim yönetimi

12 Kasım 2026. Tamamlandı; plan11/27. Sıradaki T04 long/short planlama.

## Kullanım

Çizimler panelinde seçili nesnenin kilidi, gizle/göster durumu, zaman dilimi kapsamı, rengi, çizgi kalınlığı ve stili kalıcı kaydedilir. Kilit fiyat, ad, tutamak, sürükleme, stil değişimi ve silmeyi engeller; hesaplama ve okunabilirlik devam eder. Kilitliyken gizleme, zaman dilimi seçimi ve kilidi açma kullanılabilir. Görünürlük bot takibi veya emir yetkisi değildir.

Çoğalt yeni kimlik/revision1 oluşturur; geometri ve görünüm korunur, kilit açılır. İzleme/aktivasyon taşınmaz. Kopya gizli bir nesneden oluşturulursa gizli durumunu korur ve listeden seçilebilir. Geri al/yinele aynı kopya kimliğini kullanır.

Listedeki kutularla veya grafikte/listede Shift/Ctrl/Command ile en fazla20 çizim seçilebilir. Seçili çizimlerden birini sürüklemek görünür ve kilitsiz olanları birlikte taşır. Kilitli ve gizli nesneler yerinde kalır. Bir geometri geçersizse kısmi hareket kaydedilmez. Çoklu seçimde tutamak ve toplu özellik formu açılmaz; ad/fiyat/stil düzenlemesi tek nesneyle sınırlıdır. Tek undo/redo bütün hareketi kapsar. Escape/blur/pointer kaybı ve piyasa/zaman dilimi değişimi aktif hareketi iptal eder; kaynak değişiminde seçim temizlenir.

## Kayıt ve uyumluluk

Yeni chart-management/1 özellikleri geometriden ayrı, aynı çizim revision'ında saklanır. Uygulama DB migration3 yalnız uygulama çizim tablosuna varsayılan boş metadata sütunu ekler; önceki kayıtların geometri/revision/zamanı değişmez. Migration öncesi mevcut otomatik SQLite yedeği alınır. Execution DB açılmaz.

Frontend format_version=4 kullanır. v1/v2/v3 listeleri varsayılan dışı yönetim özellikli nesneleri dışarıda bırakır; tekil okuma/yazma eski formatla reddedilir. Eski istemci kilidi/gizlemeyi bilmeden kaydı değiştiremez. Varsayılan özellikli eski çizimler önceki formatta çalışır. Kanonik geometri/hash ve hesap fiyatları görünümden etkilenmez. Nesne sözleşmesi presentation ve edit_state gösterir; hesap yeteneği kilitle kapanmaz.

POST /api/workspaces/{workspace}/drawing-operations?format_version=4 en fazla20 nesneyi tek SQLite transaction'ında revision kontrolüyle kaydeder. Owner, workspace, tek piyasa, benzersiz kimlik, tam özellik şeması ve200 aktif nesne sınırı doğrulanır. Bir409 bütün işlemi geri alır. Başarısız işlem request kaydı bırakmaz. Aynı request_id ve gövdeyle kayıp yanıt tekrarı aynı nesne/revision sonucunu döndürür. Frontend onay gelmeden kayıt başarılı demez; retry aynı isteği kullanır, son kaydı yükleme yerel geçmişi sıfırlar. Piyasa geçişinden sonra gelen yanıt eski nesneleri yeni piyasa listesine/seçimine/geçmişine ekleyemez.

## Doğrulama

-750 Python testi geçti;8 yeni yönetim testi lock/API enforcement, hash ayrımı, tam rollback, idempotency, owner/workspace/piyasa izolasyonu, stil/restart/kopya, grup inverse/redo ve eski v2 DB migration'ını sınar.
-182 frontend testi geçti;6 yeni React/hook testi karma kilitli seçim hareketi, görünürlük/interval, iptal temizliği, kayıp yanıt/tek undo,409 refresh ve geç piyasa yanıtını sınar. TypeScript ve üretim derlemesi geçti. Ana JS yaklaşık505kB/minified,161kB gzip; Vite500kB chunk uyarısı verir. Bu tur performans kabulü veya p95 iyileştirmesi iddia edilmez; QA01 performans işi korunur.
-check_chart_t07.py: gerçek production App/HTTP ve izole SQLite üzerinde12 kontrol geçti. Grafik motoruyla gerçek pointer hareketi, sunucuda commit sonrası bağlantı kesilmesi ve gerçek409 yanıtı kullanıldı. Kontrollü WebSocket verileri kullanıldı; kullanıcı DB'sine test nesnesi yazılmadı. Page error0/dış istek0.
-T05/G01/G06/G02/G03 toplam65 regresyon tarayıcı kontrolü geçti. Açık/koyu yönetim paneli ve çoklu seçim ekranları incelendi. Fiziksel touch/GPU, uzun canlı ağ kesintisi, tüm TradingView özellikleri veya canlı emir sistemi bu kabul değildir.

Kanıt: reports/chart-t07-validation-20261112.json, chart-t07-dark/light/multiselect-20261112.png ve kaynak/derleme/test hashleri içeren chart-t07-delivery-20261112.json.
