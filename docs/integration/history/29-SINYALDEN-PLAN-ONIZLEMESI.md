> Sonraki uygulama: [kapanış sürekliliği düzeltmeleri ve yeni gözlem](30-KAPANIS-SUREKLILIGI-VE-SAAT-YENILEME.md). Aşağıdaki başarısız gözlem tarihsel kanıt olarak korunur.

# B2 — Gölge sinyalden sürümlü plan önizlemesi

13 Kasım 2026 · İlk B2 kapsamı uygulandı. Yerel terminal http://127.0.0.1:8765 üzerinde schema11 ile çalışıyor. Emir, plan onayı, risk rezervasyonu veya gerçek hesap bağlantısı açılmadı.

## Kullanım

Paneller → Araç / kural bağları → kayıtlı bağın Gölge sinyal takibi geçmişi → İşlem planı önizlemesi. Yeni ve geçerli bir gölge sinyal üzerinde yönü açıkça seç; giriş, stop, tek hedef, nominal USDT bütçesi, kaldıraç/teminat/pozisyon modu varsayımlarını belirle. Plan önizlemesi oluştur düğmesi yalnız uygulama deposuna taslak kaydeder.

İlk kapsam SINGLE / LIMIT / tek hedef / Mod A plan v2 taslağıdır. İşlem yönü sinyal yönünden otomatik çıkarılmaz; stop/hedef ve bütçe uydurulmaz. Kaldıraç/hesap modu değişmez. Parametreler mevcut katı plan v2 şemasından geçer; metadata ayrı önizleme kaydındadır. PlanService yetkilendirme, execution store veya emir kuyruğuna aktarım yoktur.

Önizleme; miktar, nominal, masraf rezervli tahmini teminat, stop kaybı, hedef sonucu ve net R/R gösterir. Binance Demo public exchangeInfo/tick/lot/minimum nominal ve mark fiyatı doğrulanır. risk-demo.json bağımsız nominal/işlem kaybı sınırları uygulanır. Kullanılabilir bakiye, hesap modu/kaldıracı, portföy ve günlük kayıp, sahiplik ve likidasyon sorgulanmaz; NOT_CHECKED açıkça gösterilir. Gerçek komisyon/fonlama bilinmez. Matematik varsayımı her yönde0.001 komisyon ve5bps kaymadır; fonlama dahil değildir. Gerçek fiyat/kayma/koruma garantisi verilmez. Sinyal LAST_PRICE, koruma varsayımı MARK_PRICE olarak ayrılır.

## Sürüm ve güvenlik davranışı

- Aynı olay + aynı normalize parametreler tek mevcut sürüme döner; süre uzamaz, yeniden hesaplama/ikinci kayıt oluşmaz.
- Maddi parametre değişikliği expected_version ile yeni sürüm oluşturur. Yarışan eski sürüm409 alır. Aynı olayın eşzamanlı iki aynı isteği tek taslak üretir. Önceki sürüm SUPERSEDED olur.
- Gölge olayının kaynağı, bağ revizyonu, hedefi ve dondurulmuş kanıtı doğrulanır. Client context/account/authority alanı veremez. UI yanıtın plan ve bütün kayıt hash'ini bağımsız doğrular; dönen parametreler girilen değerlerle exact decimal karşılaştırılır.
- Olay en fazla300 saniye yaşında olmalı. Önizleme TTL'si30–300 saniye; arayüz1/2/5 dakika sunar. Son süre olay yaşı ve takip süresiyle sınırlıdır. Aynı parametreyle tekrar deneme sona ermiş taslağı yenilemez.
- Çizim/kural değişikliği, risk profili değişikliği, veri uygunluğu kaybı, kaynak veya kayıt bütünlüğü hatası taslağı engeller/geçersizleştirir. Bu kontrol okumada da yapılır. Eski hesaplar tarihsel görülebilir; yürütmeye uygun diye sunulmaz.
- execution_eligible=false, order_authority=false ve approval_state=NOT_REQUESTED bütün yanıtlarda sabittir. PREVIEW_ONLY hesap ve yürütme ön kontrolünün tamamlandığı anlamına gelmez. Bağımsız toplam/günlük risk ve hesap ön kontrolü ileride B3'te yeniden yapılmak zorundadır.
- Migration11 yalnız app_signal_previews ve app_signal_preview_heads ekler; önceki checksum'lar değişmez. Kaynak aday/yedek birlikte geri alınmalıdır; eski yazılım yeni application DB üzerinde çalıştırılmamalıdır. Execution deposu taşınmadı/sıfırlanmadı.

## 30 dakikalık gözlem sonucu — kabul geçmedi

Önceki aşamada başlatılan düzeltilmiş gözlem1800.4 saniyede tamamlandı.29 benzersiz, doğrulanmış canlı1m kapanış olayı kaydedildi. Beş toparlanma penceresi13.1/11.0/19.1/10.1/10.1 saniye;30 saniyelik toparlanma sınırı aşılmadı. Ancak kapanış olayları arasında bir adet1m boşluk bulundu:1794586320 →1794586440;1794586380 kapanış olayı gözlemde yok. CLOSED_EVENT_GAP nedeniyle passed=false.

Bu, bütün grafik mumlarının kaybolduğu veya ağ kesintisinin nedeni kesinleştiği iddiası değildir. Gözlem canlı kapanış olay zincirini ölçer; yeniden eşitleme geçmişi otomatik sinyal olarak yayımlanmaz. Boşluğun yeniden bağlantı/clock yenileme ve olay sürekliliği ile ilişkisi hedefli araştırılmalıdır. Eksik olay geçmişten yeni işlem fırsatı diye üretilerek kabul kapatılmayacak.

Rapor: reports/demo-observation-20261113.json. Süreli gözlem süreci tamamlandı ve kapandı. Önceki GAP'te takılı kalma deneyi reports/demo-observation-before-gap-fix-20261113.json içinde ayrı korunur. D3 kabulü açık/başarısızdır; B3 emir bağlantısı kapalı kalır.

## Doğrulama

-1021 Python testi,331 frontend testi ve üretim derlemesi geçti. Yeni16 backend önizleme testi ve5 frontend kontrolü dahil.36 izole replay senaryosu geçti.500kB bundle uyarısı sürüyor.
- Backend: LONG/SHORT ve hedge taslağı, katı v2 şeması, tekil/eşzamanlı istek, sürüm yarışı, TTL, risk profili/sınırları, lot/tick/minimum nominal, bozuk olay ve taslak, kaynak tazeliği, sahiplik/çalışma alanı ayrımı ve authority alanı reddi.
- Frontend: gerçek Python fixture'ının plan/tam kayıt hash'i, yanlış authority/kaynak/veri reddi, açık kullanıcı girdisi/optimistic version, kontrol edilmemiş hesap sınırlarının gösterimi ve hata sonrası eski başarıyı kaldırma.
- Gerçek izole HTTP/tarayıcı: UI'den gölge başlatma → tarayıcı kapanınca tek olay → yeniden açınca açık parametrelerle v1 önizleme → aynı istekte aynı v1/expiry → değişiklikte v2 → v1 SUPERSEDED → çizim değişince INVALIDATED. Execution sentinel hash değişmedi; hesap/emir/dış mesaj yok. Piyasa ve public metadata bu deneyde dondurulmuş demo fixture'ıdır; gerçek borsada yeni sinyal/işlem gerçekleştiği iddiası yoktur.
- Ana yerel sunucuda300 gerçek demo mumu/Canlı, PREVIEW_ONLY health ve kapalı işlem yetkisi doğrulandı. Kullanıcı çalışma alanına test sinyali veya plan eklenmedi.

Kanıtlar: reports/preview-python-tests.txt, reports/preview-unit-tests.txt, reports/preview-frontend-tests.txt, reports/preview-build.txt, reports/preview-replay-tests.txt, reports/signal-preview-validation-20261113.json ve reports/signal-preview-ui-20261113.png. Yedek manifesti: reports/demo-transition-20261113/stores-1794587458/manifest.json.

## Sonraki öncelik

D3 canlı kapanış olayı boşluğunun hedefli analizi, düzeltme ve yeni kabul gözlemi. B2 ilk kapsamı kullanılabilir; otomatik strateji/sermaye tahsisi, kademeli hedef önizlemesi, grid önizlemesi ve çizimdeki long/short araçlarından parametre aktarma sonraki kapsamdır. D3 kapanmadan B3 grafik kaynaklı demo emir açılmaz; gerçek hesap ayrı ve en son aşamadır.
