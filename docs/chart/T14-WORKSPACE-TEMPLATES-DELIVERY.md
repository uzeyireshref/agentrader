# T14 — çalışma alanı ve araç/gösterge şablonları

12 Kasım 2026. Tamamlandı; plan22/27. Sıradaki P4: revision bağlı araç/kural tanımları. Bot bağlantıları ve emir yetkisi bu teslimde açılmaz.

## Kullanım

Üst bardaki **Çalışma alanı** düğmesi;1024px görünümde aynı düğmenin katman simgesi. Pencerede:

- Çalışma alanını kaydet: gerçek pane oranları, hacim paneli görünürlüğü, panel preset'i, tema, LINEAR/LOG fiyat modu ve açık yan panel kaydedilir. Son kayıtları yükle, kayıtlı görünümü ve gösterge/çizim kayıtlarını açıkça yeniden yükler.
- Seçili aracı varsayılan yap: Çizimler panelinde seçilmiş nesnenin renk/kalınlık/çizgi stili ve uygun araç seçenekleri saklanır. Fib oranları ve long/short varsayılan hesap parametreleri desteklenir. Yeni pointer çizimleri bu varsayılanlarla oluşturulur; yeni fiyat/zaman noktalarını kullanır. Kilit/gizleme/interval filtresi/text/anchor kopyalanmaz.
- Yeni şablon kaydet: adlandırılmış, taşınabilir yerleşim/gösterge/araç varsayılanı kaydı. Yeni sürüm kaydet, aynı kimliğin yeni immutable sürümünü ekler. Sürüm seçicisinden eski sürüm okunur ve uygulanır; eski içerik değişmez.
- Seçili sürümü uygula: önizlenen ayarlar mevcut coin/zaman diliminde uygulanır. “Mevcut görünür çizimlere stilleri uygula” isteğe bağlıdır. Kilitli, gizli veya interval filtresinden dolayı görünmeyen çizimler atlanır.

Mevcut çizim geometrileri, anchor'ları, metinleri ve araç hesap parametreleri geri yükleme sırasında değiştirilmez. Toplu mevcut-çizim uygulaması renk/kalınlık/stildir; araç seçenekleri yeni çizimler için varsayılandır. Template, VWAP anchor noktası taşımaz; mevcut çalışma alanının kayıtlı anchor'ı korunur. Sembol/zaman dilimi preset ile değişmez. Manual fiyat aralığı, zoom/visible-range ve şablon silme/export bu teslimde yoktur.

## Kalıcılık ve atomik restore

Migration5 `app_chart_profiles` ve immutable `app_chart_templates` tablolarını ekler. Uygulanmış migration digest'leri değiştirilmez; standart migration yükseltme yedeği alınır. Eski workspace symbol/interval JSON'u ve API'si aynı kalır. Profil revision0 ise başlangıçta eski local tema/fiyat görünümü korunur; daha önce açıkça kaydedilmiş profil reload'da uygulanır.

API: `/api/workspaces/{id}/profile`, `/templates`, `/templates/{template_id}?revision=n`, `/template-restore`. Owner/workspace kapsamlı; strict schema,1–64 karakter ad,40 şablon ve şablon başına100 sürüm sınırı vardır. Request body64KiB ile sınırlıdır. Numeric sürüm sınırı, bilinmeyen alan/authority, geçersiz renk, geometri alanı ve uygunsuz araç seçeneği reddedilir.

Restore BEGIN IMMEDIATE içinde profil, v4 gösterge config ve seçili sembolün çizim stil revision'larını birlikte günceller. Beklenen profil/gösterge revision'ı ve o sembolün **bütün güncel çizim head'leri** eşleşmelidir. Yeni/eksik/eski bir head veya ayar çakışırsa409 ve tam rollback olur; kısmi görünüm/çizim kaydı kalmaz. Kilit ve görünürlük bayrakları korunur. İmmutable şablon sürümü açıkça seçildiği için eski bir sürümün uygulanması geçerlidir.

Request_id/digest idempotency profil, şablon yaratma/sürümleme ve restore'u kapsar. Kayıp ACK sonrası yeni şablon kimliği ve istek kimliği yeniden kullanılır; ikinci şablon veya ikinci restore revision'ı oluşmaz. Belirsiz/başarısız restore'da yeni çizim varsayılanları doğrulanana kadar araç oluşturma engellenir; aynı istekle retry veya son kayıtları yükleme açıktır.

İstemci template read'lerini token/abort ile ayırır. Restore yanıtı symbol/interval/template/version ve aggregate revision'larla doğrulanır. İstek sürerken grafik bağlamı değişirse yanıt yeni grafiğe yayınlanmaz; doğrulanmış kayıtları yeniden yükleme gerekir. Sunucudaki işlem kendi talep edilen sembolüyle sınırlıdır.

## Görünüm yaşam döngüsü

Gösterge sonucu ve profil birlikte istemciye kabul edilir. Pane'ler kurulup sıralandığında kayıtlı gerçek stretch factor'ları uygulanır. Sonraki async seri/panel düzenlemesi bu oranları varsayılana döndürmez. Kullanıcının sonraki native separator değişikliği yerel çalışma oranlarını günceller; explicit pane preset'i seçimi standart oranlara geçer. “Son kayıtları yükle” aynı revision olsa da yeni read sonucunu uygular; kaydedilmemiş tema/oran değişikliğini yanlışlıkla kayıtlı saymaz. Profil nesnesi pane sürükleme sırasında mutasyona uğramaz.

## Yetki

Şablon sadece görüntü/ayar taşır. Tracking, binding, rule, hesap erişimi, bot aktivasyonu ve order_authority alanları kabul edilmez. İşlem importu/komutu yoktur. Fiyat/zaman anchor'ı taşınmadığı gibi eski drawing geometry identity'si yeni coine kopyalanmaz. P4 revision/rule uygunluğu ayrıca uygulanacaktır.

## Kabul

- **828 Python testi** geçti.8 yeni grup: legacy profil/default/restart/idempotency; immutable template version ve anchor sanitization; atomik settings/style restore ve kilit korunması;409 tam rollback; symbol/visibility/interval scope; unknown authority/geometri/uygunsuz seçenek reddi; Fib/position options doğrulaması; gerçek HTTP ve eski workspace uyumluluğu. Çok büyük sürüm sayısı da422 ile reddedilir.
- **257 frontend testi** geçti.5 yeni test: profil/pane schema; seçili stilden güvenli default çıkarma; izinli tool option domain; portable indicator revision/anchor temizliği; template schema/version/yetki sınırı. Mevcut hook regresyonları korundu.
- TypeScript ve üretim derlemesi geçti. Ana JS581.16kB, gzip184.29kB. Mevcut500kB uyarısı ve QA01 performans/p95 kabulü açık.
- **15 yeni production App tarayıcı kontrolü** geçti: gerçek separator oranı ve default kaydı; taşınabilir v1; gerçek pointer çiziminin yeni stili kullanması; immutable v2/v1; atomik toplu restore/geometry/lock/anchor korunması; art arda v2↔v1 pane oranı; BTC kaynaklı ayarın mevcutETH/5m bağlamında yalnız doğru stile uygulanması; concurrent409 rollback; kayıp restore ACK ve yeni-template ACK idempotency; gecikmiş response sırasında coin değişimi ve creation barrier; page reload; aynı revision'a explicit view reload;1024px iki tema erişim/önizleme; server restart.
- G01/G04/T11 **47 regresyon tarayıcı kontrolü** geçti. İzole SQLite/sentetik piyasa kullanıldı; kullanıcı DB'sine test çizimi/preset yazılmadı. Page error0, dış/hesap/emir çağrısı0. Açık/koyu ekranlar incelendi. Fiziksel GPU/touch,4K veya vendor parity kabulü iddia edilmez.

Kanıt: `reports/chart-t14-validation-20261112.json`, `reports/t14-*.log`, `chart-t14-*.png`; SHA256 manifesti `reports/chart-t14-delivery-20261112.json`. [Workspace templates sözleşmesi](contracts/workspace-templates-v1.json).
