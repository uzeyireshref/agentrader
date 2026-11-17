# Yedi aşamalı sağlamlaştırma planı — güncel eşleştirme

Bu belge tarihsel geliştirme günlüklerinden ayrıdır. H01–H18 uygulama paketleridir; kullanıcının yedi ana aşamasının yerine geçen yeni bir ürün planı değildir. Nihai test sayıları ve kaynak eşleşmesi için `reports/hardening-20261117/release-validation.json` esas alınır. Kaynak değişikliğinden sonra eski rapor güncel kabul sayılmaz.

| Aşama ve alt kapsam | Uygulama / kanıt | Sınır veya karar |
|---|---|---|
| 1 — Mevcut değişiklikleri koruma, başlangıç testleri ve yeni kabul kaydı | baseline-summary.json; run_hardening.py; release-validation.json | Kullanıcı değişiklikleri geri alınmadı; tarihsel kabul raporları yeniden etiketlenmedi. |
| 1 — 100/1000/10000 niyet, 10/100/1000 iş, 10/100/500 çizim, 300/1000/4000 mum | baseline.json, after-data-access.json, indicators.json | Süre, SQL/bağlantı ve yanıt boyutu ölçümleri izole depolarda. Gerçek tarayıcı FPS'i ve gerçek borsa izleme gecikmesi ölçülmüş değildir. Başlangıçta alınmamış bir ölçüm geriye dönük üretilmiş gibi gösterilmez. |
| 2 — CLI/web/durum/kurtarma ortak execution bağlamı, boş/eski depo ayrımı | shared/storage_context.py; test_hardening, test_product_discovery | Namespace'siz mevcut depo normal açılışta reddedilir. |
| 2 — Eski günlük yedekli, açık bağlamlı geçiş | shared/legacy_execution.py; attest_execution_context.py; test_hardening | Kullanıcı günlüğüne uygulanmadı. Yerel beyan gerçek hesap erişim kanıtı değildir. |
| 2 — Bot migration ve yapısal benimseme, owner/state/zaman indeksleri | migration 14/15; test_application_migrations, test_hardening | Mevcut kimlik/gövde korunur; bozuk şema reddedilir. |
| 3 — Anahtarlı/toplu niyet okumaları | execution.py, v2_runner.py, watchdog.py; test_hardening; growth benchmark | Tam geçmiş uzlaştırması için gerekli tarama korunur. |
| 3 — Tek bağlantılı liste, özet mod, doğrulanan ayrı ayrıntı | bot_inbox.py, botApi.ts; test_hardening | Özet büyük gövdeleri okumaz; onay kanıtı değildir. |
| 3 — Gizli sekmede polling yok, görünürlükte yenileme | useVisiblePolling; visiblePolling testleri | Finansal gönderim tekrar mekanizması yok. |
| 4 — Köken/not/audit toplu okuma ve SQL sembol filtresi | chart_context.py, drawings/service.py; grafik ve hardening testleri | Ortak kalıcı cache eklenmedi. Önce/sonra revizyon, silme ve süre kontrolü korunur. |
| 5 — İnceleme süresi, hesap tazeliği ve worker yetkisi ayrımı | BotLiveReview, botReview/botLive testleri | Önizleme öncesi hesap tazeliği ve backend son kontrolü korunur. |
| 5 — İş/finansal sonuç, sır içermeyen hata/korelasyon, tipli API | botOutcome, botApi, bot_inbox; botOutcome ve hardening testleri | UNKNOWN/REJECTED/kısmi sonuç kuyruk başarısı ile karıştırılmaz. |
| 6 — NOT_SENT/READ_FAILED/UNKNOWN ayrımı, sınırlı salt okunur toparlanma | bot_worker.monitor; test_hardening | En fazla üç deneme; mutasyon belirsizliğinde duraklama. |
| 6 — Kalıcı inceleme nedeni, açık resume ve salt okunur bariyer | bot_engine.confirm; test_hardening | Halt ve finansal yetki temizlenmez; belirsiz istek yeniden gönderilmez. |
| 6 — İş öncesi/sonrası yönetim ve geçmiş sayfaları arasında tur | bot_worker, query_commands; test_hardening | Sayfa kalıcı kaydedildikten sonra checkpoint; süreç çökünce RUNNING iş NEEDS_REVIEW olur. Restart'ta otomatik yeniden oynatma eklenmedi. |
| 6 — Yeni iş öncesinde yaklaşan timer, yetki bitişi ve tek yazıcı | timer_job_admission; test_timer_admission; test_cancel_timers | 16 saniyelik ihtiyat payı tek HTTP timeout'una göre seçilmiştir; bütün iş süresinin üst sınırı değildir. Kısa heartbeat'lerde diğer işler açıkça reddedilebilir. Timer sorgusu ve geçerli onayla kapatma yolu korunur. Süresi biten timer otomatik kurulmaz. |
| 7 — Okunabilirlik ve modül ayırma | format-parity.json; chartMarketSession; useIndicatorLayers | Bağlantı, iptal, reconnect, seri oluşturma/temizleme testleri var. App'in bütün sorumluluklarının ayrıldığı iddia edilmez. |
| 7 — Açık mum ve ardışık kapanış önbelleği, düzeltme/ekleme/ayar değişiminde yeniden hesap | indicatorCalculator; indicatorCalculator testleri ve indicators.json | EMA/RSI/ATR/SMA/MACD/BB referansları değiştirilmedi. Satır kontrolü ve çıktı kopyası hâlâ O(n); bütün işlem O(1) değildir. |
| 7 — SMA/Bollinger kayan pencere seçimi | Son pencerenin hesabı ve önceki çıktıların korunması; sayısal karşı örnek testi | Eski toplamdan çıkan değeri çıkarıp yeni değeri ekleyen sürekli toplam kullanılmadı: kayan nokta toplama sırası referanstan ayrılıyor. Planın birebir sonuç ve tolerans gevşetmeme şartı önceliklidir. Tüm geçmişi baştan hesaplama azaltıldı; ilk yükleme pencereleri referans sırasındadır. |
| 7 — Backend/frontend geçmiş sınırları ve operasyon uyumu | indicator_queries.py; test_frontend_operations_match_backend_mutation_contract | Backend kapasitesi 499 mum, frontend en fazla 4000; farklı sınırlar gizlenmez. Eski ayarlar düşürülmez. |
| 7 — CSS temizliği | Bu tur CSS değiştirilmedi | Doğrulanmış yeni tekrar/çakışma olmadan toplu temizlik yapılmaz. |
| Ek sağlamlaştırma — geçmiş bitişi, eski ayar yanıtı, eksik profil | H14–H16; chartMarketSession, indicatorConfigHook, workspaceAvailability | Mevcut planın hata/okuma yükü kapsamındadır; yeni ürün yeteneği değildir. |

## Kapanış ve dış kabul

Yerel kapanış komutları: `python scripts/acceptance/run_hardening.py`, `python scripts/acceptance/verify_local_release.py`, `python scripts/maintenance/check_project_layout.py`, `git diff --check`. Tam Python/frontend, build, 36 replay ve geniş güvenilirlik paketi bu kayda bağlanır. Kimlik, rezerv, kısmi/geç dolum, kayıp yanıt, restart ve timer lease testleri mevcut tam regresyon ve güvenilirlik paketindedir.

Fiziksel tarayıcı/trackpad, gerçek uzun borsa kesintisi ve kimlik doğrulamalı borsa kabulü **açıktır**. Tarayıcı aracı engeli uygulama başarısı sayılmaz. İzole CPU/SQL ölçümü gerçek borsa gecikmesinin yerine geçmez. Yerel kodun doğrulanması finansal işlem yetkisi veya genel yayına hazır olma anlamına gelmez.

Bu nedenle “orijinal plandaki bütün yöntemler ve dış kabuller eksiksiz tamamlandı” denmez. Yerel uygulama değişiklikleri ile sayısal uyumluluk nedeniyle seçilmeyen yöntem ve dış kabul açıkları ayrı raporlanır. H19 ile React/grafik motoru ayrı chunk'lara ayrılarak 500 kB uyarısı giderildi; eşik yükseltilmedi. Ana dosya yaklaşık 643 kB'den 254 kB'ye indi; bütün başlangıç indirmesinin aynı oranda azaldığı iddia edilmez.
