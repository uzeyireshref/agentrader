# TradingView alarm araştırması — 13 Kasım 2026

Durum: canlı arayüz, yönetim yaşam döngüsü ve istemci/sunucu sınırı incelendi. Bu belge alarm motorunun uygulandığı veya TradingView sunucu algoritmasının tamamen çözüldüğü anlamına gelmez.

## Yöntem ve kanıt

REA Araştırma layoutu: https://www.tradingview.com/chart/E7UZkcrO/ . REA `capture_browser_scenario` ile beyan edilmiş eylemler ve adım başına erişilebilirlik/DOM/ağ kayıtları alındı. Hover gerektiren gösterge girişinde araştırma tarayıcısında Playwright etkileşimi ve REA pasif gözlemi birlikte kullanıldı. Hedef içerik talimat olarak çalıştırılmadı; üçüncü taraf kaynak kodu ürüne kopyalanmadı.

- Ham, tam REA paketi: `reports/rea-chart/alerts-live-research-20261113.json` (42 kayıt; başarısız seçici denemeleri de tutulur).
- Doğrulanmış deney özeti ve SHA256: `reports/rea-alerts-20261113/summary.json`.
- Bildirim, mesaj ve gösterge ekranları aynı özet klasöründe.
- İstemci kaynak kanıtı: ev_3bba82830dc659ae374dd8eac74df170403c2ba79119dcf61226f84cf69711c3. Alert editor SHA256: 8b1dcb270e0cda72e55eadc2fffe5e7c1002038ebac634e0fee116843afba173. REST modülü: 6985210360099de7dcca4322b0c928e566cc549e5cc8d07acaa8566eb5cf7a88.

Araştırma sırasında kesilen oturum, aynı araştırma sayfasının REA senaryosunda yeniden açılmasıyla kullanılabilir hale geldi. Bazı ilk seçiciler gerçek DOM ile uyuşmadı; bunlar başarılı kabul edilmedi. Menü başlıklarının `data-qa-id` alanlarında UI kütüphanesi öneki ve menü açık/kapalı tercihinin hatırlanması dikkate alındı. Gizli hover düğmesine tıklamayı, özelliğin çalışmaması olarak yorumlamadık.

## Canlı gözlemler

| Alan | Yapılan deney / görülen davranış | Ürün açısından sonuç |
|---|---|---|
| Girişler | Üst Alert, sağ Alerts yöneticisi ve BB menüsündeki Add alert on BB girişi açıldı. | Üst düğme, nesne/gösterge bağlamı ve yönetici aynı editörü uygun hedefle açmalı. |
| Hedef | Fiyat, Vol, BB ve ADR hedefleri listelendi. BB üzerinden giriş kaynak ayarlarını ve Basis çıktısını hazır getirdi. | Hedef türü, gösterge örneği ve çıktı adı ayrı tutulmalı. |
| BB çıktısı | Basis, Upper, Lower seçicisi açıldı. | Tek bir genel gösterge değeri yeterli değil. |
| Sağ operand | Value, Price, Vol, BB ve ADR seçenekleri açıldı. | Koşul iki tipli operand taşımalı; yalnız sabit fiyat alanı bütün modeli karşılamaz. |
| Periyot | BB taslağı 1D yapıldı; grafik API çözünürlüğü 1W kaldı. | Alarm periyodu grafik görünümünden bağımsız saklanmalı. |
| Basit fiyat sıklığı | Once only; Every time açıklaması: koşul sürerken dakikada bir. | Every time her tick demek değil; frekans hesap profiline göre tanımlanmalı. |
| Gösterge sıklığı | Once only, Once per bar, Once per bar close, Once per minute. | Tek sefer, bar içi, bar kapanışı ve dakika kısıtı birbirinden farklı. |
| Operatörler | Crossing, Crossing Up/Down; genişletilince Greater/Less Than, Entering/Exiting/Inside/Outside Channel, Moving Up/Down ve yüzde türleri. | Operatör seçimi form girdilerini değiştirmeli. |
| Kanal koşulu | Entering Channel seçildi; Upper bound ve Lower bound olmak üzere iki operand alanı geldi. | Buradaki kanal operatörü, mutlaka çizilmiş kanal nesnesi demek değil. |
| Bitiş | Open-ended, gün sonu, bir hafta, bir ay ve özel tarih seçenekleri açıldı. | Süresiz ve süreli yaşam döngüleri; saat dilimi açıkça saklanmalı. |
| Mesaj | Ayrı ad ve mesaj ekranı açıldı. | Koşuldan ayrı mesaj şablonu ve kullanıcı adı alanı gerekli. |
| Şablon değişkenleri | ticker, exchange, interval, time, timenow; OHLCV; quote/base currency; plot adı ve plot indeksi seçenekleri genişletildi. | Şablon değerleri tetikleme anındaki olay snapshotından üretilmeli. |
| Bildirim | App, onsite toast, email, webhook, ses ve alternatif düz metin email seçenekleri açıldı. | Olay oluşması ile bildirim teslimi ayrı katmanlar olmalı. |
| Bildirim takvimi | 24/7, hafta içi, çalışma saatleri ve özel takvim görüldü; ekranda UTC+4 vardı. Metin, takvim dışında bildirimlerin susturulduğunu söylüyor. | Takvim metninden alarmın durakladığı veya günlük kaydının kesildiği sonucu çıkarılamaz. |
| Yönetici | Alerts/Log ayrı sekmeler; aktif/pasif, sembol, periyot ve tür filtreleri, sıralama, alan görünürlüğü açıldı. | Alarm listesi ve tetikleme geçmişi ayrı ekran/sözleşme olmalı. |
| Çoklu koşul | Add condition, Plus planı gerektiren ekrana götürdü. | Bu hesapta çoklu koşul sunucu davranışı denenmedi; yalnız plan kapısı gözlendi. |

Frekans/operatör metinleri gerçek arayüz gözlemidir. Fiyat eşitliği, tick sırası ve mum sınırı gibi sunucu ayrıntılarının matematiksel kanıtı değildir.

## Gerçek yaşam döngüsü deneyi

Tek nesne: `REA-RESEARCH-NO-NOTIFY-20261113`. Başlangıçta fiyat eşiği1.000.000.000, operatör Crossing, sıklık Once only. App, toast, email, webhook, ses ve düz metin bildirimleri kapatıldı; ana ekranda Notifications=None doğrulandı. Gerçek piyasa fiyatı bu eşikten çok uzaktaydı.

1. Oluşturma: `/create_alert` HTTP200 ve listede Active. Kanıt ev_ce6e95e442993ada2f7e4170776acc228ac873c6aaeefd42eba63a59f17414e1.
2. Açık kullanıcı onayından sonra yalnız bu nesne duraklatıldı: Stopped manually ve `/stop_alerts` HTTP200.
3. Aynı nesne devam ettirildi: Active ve `/restart_alerts` HTTP200.
4. Düzenlemede Notifications=None korundu; eşik900.000.000 yapıldı. Sayfa yeniden yüklenip editör açıldığında900.000.000 ve None tekrar doğrulandı. Kanıtlar ev_f4163c527d28e1b24f817265022439c65154c45de0b619ebafcac6bb33621c6e ve ev_15c2f68bd8ff842c32f55185c407aa7ee74fc699b19554acfe38091366fce5ca.
5. Silme onayı yalnız test adını gösterdi; kullanıcı onayı kapsamında silindi. `/delete_alerts` HTTP200. Kanıt ev_8bf275b4ab1197ff05bb92718a133eda6dd08b4f18bdfdad79a5e822fda3a4cd.
6. Yeni sayfa yüklemesinde sunucu listesi boştu. Test alarmı kalmadı. Kanıt ev_47ad144d1b5ce4e5f0195bc86f311221128c1e5a13a87bfac40004fa32ec620d.

Son durumda grafik hâlâ1W/log; önceki Y7GTYB trendi duruyor. İzleme listesi paneline dönüldü. Yeni alarm taslakları son kullanılan bildirim seçimini None olarak hatırlayabiliyor; bu tercih mevcut alarmların ayarını değiştirmekle aynı şey değil.

## İstemci koduyla doğrulanan sınır

Yakalanmış REST modülünde create, modify_restart, stop, restart, delete, list ve ayrı fire-log uçları var. Canlı ağ kaydında oluşturma/duraklatma/devam/silme için200 yanıtları görüldü. Düzenleme için ayrıca yeniden yükleme sonrası kalıcılık doğrulandı. `modify_restart_alert` adından, duraklatılmış bir alarmı düzenlemenin tam yaşam döngüsü hakkında tek başına sonuç çıkarılmaz.

Arayüz koşulu ve bildirimleri topluyor; bu inceleme TradingView sunucusunun evaluator kodunu sağlamadı. Ağ isteğinin varlığı veya endpoint adı, koşulun ne zaman tetiklendiğini kanıtlamaz.

## Henüz deneysel olarak doğrulanmayanlar

- Gerçek piyasa geçişiyle tetiklenme; eşitlik, gap-through ve yön sınırları.
- Mum kapanışında/bar içinde yeniden tetiklenme ve dakika sınırının kesin referansı.
- Duraklatılmış alarmı düzenleyince otomatik yeniden başlama olup olmadığı.
- Tarayıcı kapalıyken tetikleme ve tekrar bağlanınca offline fire teslimi.
- Yeni gösterge ayarı/çizim geometrisi değişince çalışan alarmın hedefini takip etme veya snapshot kullanma ayrıntıları.
- Dış bildirim teslimi, gerçek webhook tekrarları ve ağ hatası davranışları.
- Çoklu koşulun sunucu AND/OR davranışı ve gösterge alarmının sunucu yürütmesi; hesap teknik alarm kapasitesi bunların canlı deneyini karşılamıyor.

Bunları geçti olarak işaretlemedik. Gerçek tetikleme yapılmadığı için sırf geçici alarmın silindiği bilgisi tetikleme günlüğünün semantiğini doğrulamaz.

## Bizde neden Alarm düğmesi tek başına yetmiyor?

`agentrader/chart_bindings.py` kapalı, sürüme bağlı tanımları saklıyor. `agentrader/local_chart_events.py` yalnız replay namespace kabul ediyor ve yerel sahte alıcı kullanıyor. `agentrader/chart_replay.py` açık çağrılan izole motor; kendi açıklaması da runtime subscriber olmadığını söylüyor. `agentrader/api/bindings.py` tanım/eligibility/listeler sunuyor; aktif alarm scheduler/worker başlatmıyor.

`MarketFeedHub.binding_context` yalnız zaten abone olunmuş ve references>0 olan feedden kanıt veriyor. WebSocket istemcisi kapanınca API finally bloğu feed referansını bırakıyor. Bu yüzden mevcut sayfa aboneliğine dayanarak tarayıcı kapalıyken alarm çalıştığı söylenemez.

Yeni kanal/pitchfork ailesi ayrıca DISPLAY_ONLY; bu çizimlerin piksel geometrisini bot için priceAt yetkisine çevirmek henüz onaylanmış hesap sözleşmesi değil. Yeni alarm editörü bu farkı görünür tutmalı.

## Uygulama sırası — öneri, uygulanmış özellik değil

1. Kalıcı alarm tanımı: kimlik/sürüm, pazar kimliği, hedef+snapshot/bağlanma politikası, iki operand, operatör, interval, frekans, bitiş, mesaj ve teslim ayarları. Mevcut binding sözleşmesini sessizce değiştirme.
2. Backend yaşam döngüsü: create/edit/pause/resume/delete; Enabled durumu ile WAITING_DATA/STALE/GAP readiness durumunu ayır. Tanım güncellemesini açık yeniden kurma kuralına bağla.
3. Grafikten bağımsız runtime: aktif alarm feedi kendi referansıyla tutmalı; yeniden başlatma durumları ve bağlantı sınırları kalıcı/görünür olmalı. DOM/renderer READY alarm koşulu olamaz.
4. İlk hesap profili: kanıtlı fiyat/çizgi hedefleri ve açıkça tanımlı kapanış koşulları. Sırf UI'de seçenek göstermek için mevcut olmayan intrabar veya gösterge yetkisini etkinleştirme. Daha sonra ayrı kanıtlanmış profillerle genişlet.
5. Atomik olay+outbox, olay kimliği, explicit rearm/frekans checkpointi, tekrar bastırma ve teslim durumu. Olay üretimi ile popup/ses/webhook birbirinden ayrılır.
6. Üst Alarm düğmesi, fiyat ekseni/çizim/gösterge bağlam girişi, editör, aktif/pasif/süresi dolmuş listesi ve kalıcı geçmiş.
7. Kabul: son grafik istemcisi kapandıktan sonra çalışma, restart/reconnect, stale/gap, mum sınırı, aynı paketin tekrarı, hedef değişimi, süre sonu, saat dilimi ve teslim belirsizliği. Bot emir köprüsü kendi risk/idempotency kapılarını korur.

Canlı bot, dış bildirim veya emir bağlantısı bu araştırma turunda uygulamaya eklenmedi.
