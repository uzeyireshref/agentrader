# Kimlik doğrulamalı demo plan onayı — 14 Kasım 2026

Grafik çizim düzeltmesinden sonra, mevcut yerel hesap incelemesini arayüzde gösterme ve belirli demo plana süreli kullanıcı onayı verme adımı uygulandı. Bu teslimde gerçek kullanıcı hesabında inceleme, onay veya emir oluşturulmadı. Tarayıcı kabulü geçici veritabanları ve sahte demo hesap adaptörüyle yapıldı.

## Akış ve yetki sınırı

1. Gölge sinyalden kullanıcı seviyeleriyle bir plan önizlemesi oluşturulur.
2. Mevcut `python -m agentrader web review-preview main EVENT_ID PREVIEW_VERSION` komutu, demo hesabını inceler ve yerel `PENDING_APPROVAL` planını hazırlar. Hesap anahtarları tarayıcıya girilmez.
3. Önizleme içindeki **Yerel demo planını incele ve onayla** bölümü açılır. Yerel web erişim anahtarıyla eşleştirilen oturumda tam plan, hesap/risk sonucu, hesap kimliği, son kontrol tarihi ve süre gösterilir. Anahtar yalnız eşleştirme isteğinde kullanılır; JS depolarına yazılmaz. Oturum HttpOnly, SameSite Strict çerezle tutulur.
4. Kullanıcı planı ve hesap kimliğini kontrol ettiğini işaretler, 30/60/120 saniyelik süre seçer ve belirli plana açık onay verir.
5. Ayrı `python -m agentrader web approval-worker` süreci hesabı ve grafik kaynağını yeniden doğrular. Başarılıysa mevcut PlanService üzerinden yalnız aynı plana, hesaba, içerik özetine ve süreye bağlı onay işler. Ekran kuyruk kabulünü, yeniden kontrolü ve onayın kaydedilmesini ayrı gösterir.

Bu ekran ve işçi emir göndermez. Yürütme önceki teslimdeki ayrı, açık `plans run … --execute-demo` adımıdır. Onay işçisi hesap adaptörü GET izin listesiyle sınırlıdır; POST/PUT/DELETE yöntemleri engellidir. Normal W1 `runtime.inspect` kuyruğuna finansal eylem eklenmedi.

## Yapılandırma

Sunucuda mevcut `AGENTRADER_WEB_TOKEN` tanımlanmış olmalıdır. Değer 32–256 güvenli karakterden oluşur; bu yerel erişim anahtarı Binance anahtarı değildir. Onay işçisi ayrıca ve açıkça başlatılır; web sunucusu başlarken otomatik finansal işçi oluşturulmaz.

Çalışan kullanıcı terminalinde özel API kapalı bırakıldı ve onay işçisi başlatılmadı. Çizimler, veri akışı ve gölge takip çalışır. Onay ekranı bu durumda yerel oturumun kapalı olduğunu açıkça gösterir. Onay için hesap incelemesi ve yerel eşleştirme gerekir; eksik kontroller tamamlanmış gibi gösterilmez.

## Kalıcılık ve yeniden deneme

Uygulama deposuna yalnız eklemeli şema 12 eklendi: ayrı onay isteği ve işçi sağlık tabloları. Geçiş öncesi sekiz SQLite deposu çevrimiçi yedeklendi; migration ayrıca önceki uygulama deposunun yedeğini alır. İşlem deposunun şeması bu akış için değiştirilmedi; CLI inceleme özeti kendi kontrol kaydında tutulur.

HTTP süreci işlem deposunu SQLite salt okunur bağlantıyla açar. İşlem planına veya yetki kaydına yazmaz. Onay isteği mevcut kullanıcı kimliği, inceleme özeti, önizleme özeti, plan özeti ve hesap kimliğiyle sınırlıdır. Farklı hesap, eski inceleme, değiştirilmiş içerik, kapalı işçi, süresi dolmuş istek veya kaynak revizyonu yetkilendirmeyi engeller.

Tekrar tıklama/ağ yeniden denemesi aynı istek kimliğini kullanır; başarı tekrar okunduğunda onay süresi uzamaz. Kullanıcı açıkça web onayı verdiğinde işçi yalnız bekleyen planın yerel onay doğrulayıcısını yeniler, düz kimliği saklamadan mevcut PlanService yetki kurallarını uygular. CLI incelemesinde kaybolan kimlik otomatik geri üretilmez.

İşçi çalışırken kesilen istekler sonraki başlangıçta `NEEDS_REVIEW` olur; muhtemelen uygulanmış bir onay otomatik tekrarlanmaz. Arayüzden yerel plan durumu yeniden okunmalıdır. Plan hâlâ onay bekliyorsa yeni açık istek hazırlanabilir; onay zaten işlenmişse yeniden yetkilendirilmez. Onaydan sonra çizim değiştirilmesi yine giriş engeline yol açar; açık pozisyon koruma kuralları önceki teslimdeki gibi kalır.

## Doğrulama ve sonraki kapsam

1072 Python testi, 343 arayüz testi, TypeScript/üretim derlemesi ve 36 izole replay senaryosu geçti. Yeni backend testleri özel API kapısı, oturum/origin, sahiplik, hash/sürüm/hesap bağı, süre sonu, mükerrer istek, işçi kesintisi ve GET dışı yöntem engelini kapsar. Tarayıcıda eşleştirme → tam plan → açık işaretleme → kuyruk → yeniden doğrulama → onay akışı geçici depoda tamamlandı. Anahtarların DOM/depolara sızmadığı ve çizim değişikliğinin onaydan sonra da girişi engellediği doğrulandı.

Raporlar: `reports/chart-approval-ui-validation-20261114.json`, `reports/chart-approval-python-tests-20261114.log`, `reports/chart-approval-frontend-tests-20261114.log`.

Sıradaki kapsam, belirli plana kullanıcı onayıyla kontrollü gerçek Demo uçtan uca kabulü ve sert süreç kesintilerinde bağımsız izleyici/uzlaştırmadır. Henüz gerçek Demo emriyle kabul yapılmadı. Gerçek Binance bağlantısı kapalıdır.
