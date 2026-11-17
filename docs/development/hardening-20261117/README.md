# Mevcut kodu sağlamlaştırma — 17 Kasım 2026

Bu çalışma yeni strateji, ürün veya finansal yetki eklemez. Güncel kabul kaydı `reports/hardening-20261117/release-validation.json`; test sayıları ve kaynak hashleri bu dosyadan okunmalıdır. Tarihsel exchange-development raporları değiştirilmez.

## Uygulanan paketler

| Paket | Değişiklik | Doğrulama |
|---|---|---|
| H01 | Geçici depolarla büyüme ölçümleri ve tekrarlanabilir kabul komutu | baseline.json, after-data-access.json, indicators.json |
| H02 | Ortak execution bağlam kapısı; namespace'siz eski günlük normal açılışta reddedilir | test_hardening, test_product_discovery |
| H03 | Bot kuyruğu migration 14/15, eski tablo yapısı doğrulaması ve iki sorgu indeksi | test_application_migrations, test_hardening |
| H04 | Anahtarlı emir okumaları; tek bağlantılı liste ve isteğe bağlı özet API | test_hardening, mevcut runner/watchdog testleri |
| H05 | Çizim köken/not/audit verilerinin toplu okunması, SQL sembol filtresi | grafik bağlamı, çizim ve replay testleri |
| H06 | Onay ve ekran tazeliğinin ayrılması; iş/borsa sonuçlarının açık gösterimi; tipli API ve görünürlük kontrollü polling | botLive, botOutcome, visiblePolling testleri |
| H07 | Kullanıcı işi öncesi/sonrası ve geçmiş sayfaları arasında yönetim; sınırlı salt okunur hata toparlanması | test_hardening ve mevcut kesinti testleri |
| H08 | Kapalı gösterge geçmişinin önbelleği; canlı mumda yalnız son çıktı hesaplanır | indicatorCalculator birebir eşdeğerlik testleri |
| H09 | Python, frontend kaynakları ve paketli web çıktısını bağlayan güncel release kapısı | test_release_evidence, verify_local_release |
| H10 | Grafik WebSocket/geçmiş/timer sahipliği ayrı chartMarketSession modülüne taşındı | chartMarketSession: reconnect, sembol değişimi, iptal ve render kurtarma |
| H11 | Gösterge seri oluşturma/yazma/temizleme ayrı useIndicatorLayers hook'una taşındı | indicatorLayers: etkin seriler, ayar değişimi, unmount |
| H12 | Uzun satırlı 14 dosya davranış koruyan biçime getirildi | format-parity.json, frontend regresyonları |
| H13 | Yedi yardımcı diyalog lazy yüklenir; yükleme hatası ana grafiği kapatmaz | deferredPanel: gecikme, vazgeçme, hata sınırı |
| H14 | Geçmişin bittiği bilgisi veri oturumunda da tutulur; sola kaydırma aynı boş/son sayfayı yeniden istemez | chartMarketSession: bitiş, yeni oturum ve geçici hatadan sonra tekrar |
| H15 | Gösterge kaydı önceki ayar okumalarını geçersiz kılar; geç yanıt doğrulanmış yeni sürümü ezmez | indicatorConfigHook: okumanın kayıttan önce ve sonra tamamlanması |
| H16 | Profil yüklenmeden çalışma alanı/araç kaydı, göstergeler hazır olmadan şablon kaydı engellenir | workspaceAvailability: boş/eski profil, toparlanma, bağımsız gösterge yüklemesi |
| H17 | Yeni worker işi öncesinde timer bütçe kapısı; yakın heartbeat/lease halinde açık ret, otomatik tekrar yok | test_timer_admission: sınır, saat geri gidişi, yetki sonu, kapatma yolu |
| H18 | Ardışık kapanan mumda önceki gösterge çıktıları korunur, yalnız yeni çıktı eklenir | indicatorCalculator: kapanış/tick dizileri, iki MACD ve BB çeşidi, sayısal sözleşme |
| H19 | React ve grafik motoru ayrı önbelleklenebilir chunk'lara ayrıldı; 500 kB uyarısı giderildi | bundle-before/after.json, üretim build ve statik chunk grafiği |

## Davranış ve uyumluluk

- `GET /api/bot/jobs` eski tam sonuç biçimini korur. `?summary=true` büyük gövdeleri okumaz; `result_loaded=false` gösterir. Tam sonuç mevcut kimlikli ayrıntı uç noktasından doğrulanarak alınır. Özet kayıt bir onay kanıtı değildir.
- Kuyruk başarısı yalnız işin işlendiğini belirtir. UNKNOWN, REJECTED ve FINAL_WITH_ERRORS ana görünümde ayrı etiketlenir. Büyük sonuç ayrıntısı açılınca yüklenir. Migration 15 kısa sonuç durumunu ayrı tabloda saklar; yeniden açılan ekran da belirsiz/kısmi/ret etiketlerini büyük gövdeyi okumadan gösterir.
- Önizleme öncesi hesap tazeliği ve onay sırasında backend ön kontrolü korunur. Ekrandaki eski snapshot, geçerli 60 saniyelik incelemeyi tek başına engellemez.
- Ortak bağlam kapısı yalnız tamamen boş execution deposunu otomatik oluşturur. Başka depolar ve namespace'siz eski günlükler sessizce etiketlenmez. Durum API'leri aynı bağlam kararı verir.
- Eski Bot tabloları mevcut kolon sırası/tür/null/primary-key yapısı doğrulanarak migration 14 tarafından benimsenir. Mevcut kimlikler ve sonuç gövdeleri korunur.
- Salt okunur geçici hata en fazla üç toparlanma denemesi alır. Her denemede mutasyon öncesi salt okunur bariyer gerekir. Belirsiz niyet, iptal, WS, hesap veya finansal komut varsa otomatik devam yoktur. Durum sağlıklı gösterilmez.
- Kalıcı duraklamadan dönüş, web üzerinden ayrı inceleme/onay ve salt okunur uzlaştırma gerektirir. Global halt veya işlem yetkisi temizlenmez.
- Uzun geçmiş toplama, kalıcı sayfa kaydından sonra aynı süreçte yönetim turuna sıra verir. Restart geçmiş işini otomatik tekrar oynatmaz; mevcut NEEDS_REVIEW davranışı korunur. Bu, süreçler arası otomatik devam eden yeni bir kuyruk motoru değildir.
- Tek yazıcı kilidi, Decimal risk hesapları ve belirsiz mutasyonu tekrar göndermeme korunur. Sürmekte olan ağ isteği zorla kesilmez; bu nedenle ağ timeout'u ve tek yönetim turu hâlâ gecikmeye katkıda bulunabilir. Gerçek zaman garantisi verilmez.
- Gösterge kaynakları/config/simge/zaman dilimi veya kapalı geçmiş değişirse önbellek yeniden kurulur. SMA/BB pencere içi toplama sırası ve referans formüller değiştirilmez; tolerans gevşetilmez. Optimizasyon açık mum güncellemelerinde tüm geçmişi yeniden hesaplamayı kaldırır.
- Backend gösterge çıktıları 499 mum bağlam kapasitesini ve seçilen gereksinimin bunu aşıp aşmadığını açıklar. Kaydedilmiş yüksek periyotlar sessizce düşürülmez. Frontend'in yüklenmiş geçmişi ayrı sınırdır.
- Sayısal CPU/SQL ölçümleri tarayıcı FPS'i veya gerçek borsa gecikmesi değildir.

## Eski günlük geçişi

Normal açılışta CONTEXT_UNVERIFIED alındığında kayıt silinmez veya yeniden oluşturulmaz. İnceleme komutu:

```powershell
python scripts/maintenance/attest_execution_context.py --database PATH --owner OWNER --account-ref SHA256 --context usdm-demo
```

Bu komut ağ isteği yapmaz. Hesap referansı API key'in mevcut SHA-256 referansıdır; key/secret komut satırına verilmez. Eski veri kökeni gerçekten doğrulandıktan sonra aynı komuta `--apply-local` eklenebilir. İşlem mevcut tek-yazıcı kilidi ve SQLite yazma kilidi altında doğrular, önce SQLite backup oluşturur, yalnız namespace ekler. Bu yerel kullanıcı beyanıdır; tarihsel borsa kabulü veya hesap erişim kanıtı üretmez. Kullanıcı günlüğüne bu çalışma sırasında uygulanmadı.

## Tekrar doğrulama

```powershell
python scripts/acceptance/run_hardening.py
python scripts/acceptance/verify_local_release.py
```

İlk komut etkilenen binding/replay kanıtlarını üretir, frontend build ve testlerini, tam Python regresyonunu, geniş güvenilirlik paketini ve izole performans ölçümlerini çalıştırır. Kabul boyunca kaynak değişirse rapor üretmez. Başarısız komut başarılı rapor olarak kaydedilmez. Eski kabul raporları güncel sürüm için yeniden etiketlenmez.

Fiziksel tarayıcı/trackpad ve gerçek Binance Demo kabulü bu otomatik kabulün parçası değildir; NOT_RUN olarak açık tutulur. İkinci turda yardımcı diyaloglar ihtiyaç anında yüklenerek ana grafik bundle yaklaşık 753 kB’den 642 kB’ye indirildi. 500 kB uyarısı hâlâ sürüyor; eşik yükseltilerek gizlenmedi.

## Kabul sırasında bulunan fixture yarışı

Guardian alt süreç testi lease dosyasını doğrudan oluşturduğu için okuyucu dosyayı boşken görebiliyordu. Üretimin mevcut atomik replace_lease yöntemi test yazıcısında da kullanıldı; guardian kabulü veya imza/kimlik kontrolleri gevşetilmedi. Başarısız kabul denemesinde önceki başarılı rapor güncel sonuç olarak bırakılmaz; önceki rapor ayrı isimle korunur.

## İkinci sağlamlaştırma turu

Grafik verisinin bağlantı ve geçmiş yükleme yaşam döngüsü App içinden çıkarıldı. Her oturum kendi WebSocket bağlantısını, reconnect zamanlayıcısını, tazelik zamanlayıcısını ve AbortController'ını sahiplenir. Oturum kapandıktan sonra gelen yanıtlar ve eski socket callback'leri etkisizdir. Geçmiş yüklemesi sırasında gelen canlı mumlar korunur; yanlış kaynak/sembol yanıtı reddedilir. Grafik viewport kaydırması yalnız başarılı çizimden sonra uygulanır.

Gösterge serilerinin kaynak sahipliği ve önbelleği useIndicatorLayers içinde kalır. Pane düzeni App'te, veri taşıması chartMarketSession'da kalır. Seri oluşturma ve temizleme sırası korunmuştur; hesap formülleri değiştirilmemiştir. Biçimlendirme uyumu kaydı yalnız biçimlendirme adımını karşılaştırır; modül ayırma ve lazy yükleme değişikliklerinin kabulü ayrı davranış testlerine dayanır.

Alerts, ReplayValidation, LocalEventHistory, RuleBindings, DrawingClipboard, WorkspaceTemplates ve IndicatorSettings ilk grafik açılışında yüklenmez. Panel yüklenirken vazgeçilebilir. Panel kodu yüklenemezse hata sınırı grafiği ve taslağı korur; kullanıcı paneli kapatabilir. Lazy hata önbelleği temizlenmiş gibi davranılmaz; yeniden deneme için sayfa yenileme mesajı gösterilir.

Başlangıç ana JS çıktısı yaklaşık 753 kB / gzip 235 kB iken 642 kB / gzip 202 kB oldu. Bu, başlangıç ana chunk karşılaştırmasıdır; tüm isteğe bağlı paneller açıldığında toplam indirilen kodun aynı oranda azaldığı veya FPS artışı olduğu iddia edilmez. Yeni çalışma zamanı bağımlılığı eklenmedi. Biçimlendirme için sabit Prettier 3.6.2 yalnız araç olarak kullanıldı.

## Geçmiş yükleme isteklerinin sonlandırılması

Eski kod `hasMore` bilgisini yalnız React düğmesine aktarıyordu. Görünür aralık aboneliği doğrudan `loadOlder` çağırdığı için geçmiş bitse bile sola kaydırma aynı sayfayı tekrar okuyabiliyordu. Oturum artık başarılı son/boş/ilerlemeyen sayfadan sonra hem düğmeyi hem doğrudan yükleme çağrılarını durdurur. Başarısız istek bitiş sayılmaz; kullanıcı yeniden deneyebilir. Yeni sembol/zaman dilimi oturumu kendi bitiş bilgisini sıfırdan oluşturur. Mevcut 4000 mum sınırı değişmez.

## Gösterge ayarlarında okuma/kayıt sırası

Aynı render üzerinden yeniden yükleme ve kayıt başladığında eski GET yanıtı kayıt sonrasında da yayınlanabiliyordu. Gösterge kaydı artık önceki okuma seri numarasını geçersiz kılar; yalnız doğrulanmış PUT yanıtı yeni ayarları ve hazır durumunu yayınlar. Revizyon, içerik doğrulaması, istek kimliğinin tekrar kullanım kuralı ve 409 davranışı korunur. Geciktirilmiş GET yanıtının PUT yanıtından önce ve sonra tamamlandığı iki React testi eski kaydın geri gelmediğini doğrular. Hook ayrıca okunabilir biçime getirildi; yeni bağımlılık eklenmedi.
