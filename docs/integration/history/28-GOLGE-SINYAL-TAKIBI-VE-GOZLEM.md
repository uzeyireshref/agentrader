> Güncelleme: [B2 plan önizlemesi ve tamamlanan gözlem sonucu](29-SINYALDEN-PLAN-ONIZLEMESI.md). 30 dakika tamamlandı; kapanış olayı boşluğu nedeniyle kabul geçmedi. Aşağıdaki gözlem devam ediyor ifadeleri tarihsel teslim anını anlatır.

# B1 — Gölge sinyal takibi ve arka plan gözlemi

13 Kasım 2026 · İlk B1 kapsamı uygulandı. Yerel terminal http://127.0.0.1:8765 üzerinde yeni sürümle çalışıyor. Gerçek hesap, grafik kaynaklı emir ve dış bildirim bağlantısı kapalıdır.

## Kullanım

Grafiği yenile. Yatay çizgi veya yatay ışın oluştur. Paneller → Araç / kural bağları penceresinde hedefi, yaklaşma/temas/kapanış geçişi kuralını, yön ve mutlak fiyat toleransını seçip devre dışı tanımı kaydet. Kayıtlı bağdaki Gölge sinyal takibi bölümünden 15 dakika/1 saat/4 saat süre seçerek açıkça başlat. Sonuçlar aynı bölümde kalıcı geçmiş olarak görünür.

Başlangıç verisi sinyal değildir; ilk yeni uygun kapalı mum değerlendirilir. Backend açık kaldığı sürece tarayıcı kapansa da takip sürer. Web sunucusu veya bilgisayar kapalıyken yerel işçi çalışamaz. Makineye otomatik başlangıç görevi kurulmadı. Sonuç; açıklanabilir gözlemdir, işlem planı, kullanıcı işlem onayı veya emir değildir.

İlk eşleşmeden sonra bağ LATCHED olur. Otomatik yeniden giriş/yeniden kurulma yok; yeni takip için açık yeniden bağlama gerekir. Duraklat/devam et TTL'yi uzatmaz; devam sonrası güncel veri başlangıç noktası olur. Aynı start isteğinin tekrarı da süreyi veya checkpoint'i yenilemez. Çizim/kural revizyonu değişince eski takip durur. Göstergeler, Fib, trend, log ölçek, açık mum ve ikinci test/retest stratejileri bu ilk canlı gölge kapsamına alınmadı.

## Uygulama

- Migration10: app_shadow_runs/events/worker; önceki migration checksum'ları korunur. Mevcut uygulama deposunun online yedeği migration öncesinde otomatik alınır.
- Ayrı gölge durumu, binding'in DISABLED tanımını veya bot_capabilities/order_authority alanlarını etkinleştirmez. Yeni DEMO_SHADOW_CLOSED_EXPLICIT_REARM/1 profili closed_candidate kanonik hesabını paylaşır; replay alanı ve sahte teslim tabloları canlı takip diye kullanılmaz. Eski E3/replay kimlikleriyle byte eşitliği iddiası yoktur.
- Olay ve checkpoint tek SQLite transaction'ında, güncel binding/target head'i tekrar doğrulanarak yazılır. Dış teslim olmadığından outbox/emir niyeti üretilmez. Fırsat/plan köprüsü B2 kapsamıdır.
- Sunucunun kaynak/epoch/grid/hash/ondalık/clock uygunluk denetimi geçmeden olay yoktur. HTTP komutu kullanıcıdan piyasa context/proof kabul etmez; ekstra alanlar reddedilir.
- Tek gölge işçisi veritabanına özgü işletim sistemi kilidi kullanır. İkinci API aynı depoya bağlanabilir, ikinci değerlendirici başlatamaz; var olan işçinin kalıcı sağlık kaydını görür. İlk işçi kapanırsa ikinci API otomatik sahipliği devralmaz; bu sürümde yeniden başlatılması gerekir.
- Yeniden başlatma, epoch değişimi, veri boşluğu veya duraklatmadan dönüş geçmiş kapanışı yeni sinyal saymaz. Aynı kapanışın farklı veriyle gelmesi inceleme için takibi durdurur. Saat sıçraması güvenli bekleme üretir; gerekirse sunucu yeniden başlatılarak yeni saat başlangıcı alınır.
- UI hata veya bozuk authority yanıtında önceki hazır durumu saklamaz. Geç gelen komut yanıtı yeni binding revizyonunun görünümünü değiştiremez. Yerel Host/Origin sınırı korunur; finansal HTTP komutu eklenmedi.

## Gözlemde bulunan veri toparlanma açığı

İlk arka plan gözlemi yaklaşık 937 saniyede durduruldu. REST yeniden eşitleme sonrası GAP durumunun kalıcılaştığı gözlendi; 15 benzersiz kapanış ve ilk200 olumsuz örnek tarihsel raporda korunur. Bu gözlem başarılı kabul edilmedi: reports/demo-observation-before-gap-fix-20261113.json.

Kod incelemesi, boşluklu REST seed'iyle akış devam ettiğinde kalite bayrağının GAP olarak kalabildiğini gösterdi. SharedFeed artık OK olmayan/eksik grid'li seed'i işlemeye devam etmek yerine mevcut sınırlı geri çekilme döngüsüyle yeniden REST eşitlemesi yapar. Veri uydurulmaz, geçmiş kapanıştan yeni sinyal üretilmez. Bu durum bağımsız regresyon testinde yeniden üretildi ve düzeltildi.

Düzeltilmiş kodla 30 dakikalık yeni gözlem arka planda başlatıldı. Canlı rapor: reports/demo-observation-20261113.json. Süre bitmeden tamamlandı/PASS sayılmaz. Süreli süreç otomatik kapanır; hesap/işlem deposuna erişmez, geçici piyasa deposu kullanır.

Yeni gözlem ölçütü açık: yalnız taze ve doğrulanmış akıştaki kapanışlar sayılır; iç kapanış sırası kesintisiz olmalı, her toparlanma en fazla30 saniye olmalı, 30 dakikada en az29 kapanış görülmeli. Saat örneğinin5 dakikalık yenilenmesi nedeniyle kısa resync tek başına başarısızlık değildir; bütün geçiş/kesinti süreleri korunur. İlk200 olumsuz örnek ayrıntıda tutulur; toplam samples/live_samples ve tüm outage/violation kayıtları özette kalır. Bu kontrollü süre bütçesi genel sürüm veya fiziksel kabulün yerine geçmez. Gerçek upstream kesintisi enjekte edilmedi.

## Doğrulama

- Python tam regresyon1005 test: başarılı. Yeni16 gölge senaryosu ve1 boşluklu seed toparlanma testi dahil. Son kilit yolu düzenlemesi sonrası16 gölge testi ayrıca geçti.
- Frontend326 test ve üretim derlemesi geçti.5 yeni kontrol: kaynak/authority, açık başlatma, hata sonrası temizleme, desteklenmeyen/disabled bağ ve geç komut yanıtı.
- İzole replay36/36 tekrar geçti; kaynak izlenebilirlik ve fixturelar yeniden üretildi.
- Gerçek izole HTTP/üretim frontend/tarayıcı/arka plan işçisi kontrolü geçti: client context enjeksiyonu ve cross-origin komut reddi; UI'den açık başlatma; ilk seed olay üretmiyor; tarayıcı kapanınca veri aboneliği korunuyor; sonraki sentetik kapanışta tek açıklanabilir TOUCH oluşuyor; tekrar olay yok; yeniden açınca geçmiş görünür; execution sentinel hash değişmiyor. Piyasa bu testte donmuş demo fixture'ıdır; gerçek demo temas gerçekleşmesi diye sunulmaz.
- Yerel ana sunucu schema10 ile yeniden başlatıldı; 300 gerçek demo mumu, Canlı etiketi, SHADOW_ONLY ve worker_running=true/order_authority=false doğrulandı. Kullanıcı deposuna test çizimi veya aktif test kuralı eklenmedi.
- Gerçek emir, hesap ayarı ve dış mesaj yok. Bundle500kB uyarısı sürüyor. Uzun gözlem/fiziksel kabul ve B2/B3 açıktır.

Kanıtlar: reports/shadow-python-tests.txt, reports/shadow-frontend-tests.txt, reports/shadow-build.txt, reports/shadow-replay-tests.txt, reports/shadow-tracking-validation-20261113.json, reports/shadow-tracking-ui-20261113.png. Eski SQLite yedek manifesti: reports/demo-transition-20261113/stores-1794585502/manifest.json.

## Sonraki adım

Gözlem sonucunu ayrı değerlendirmeye devam ederken B2 sinyal → somut plan önizlemesi geliştirilebilir. Uzun veri kabulü tamamlanmadan grafik kaynaklı demo emir yolu açılmaz. B2 önizlemesi de tek başına emir yetkisi oluşturmaz.
