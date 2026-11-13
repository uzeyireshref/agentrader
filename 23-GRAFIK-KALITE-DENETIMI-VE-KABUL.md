# Grafik kalite denetimi ve kabul — 1. tur

9 Kasım 2026. Yön: grafik kalitesi; bot bağlantısı bu turun kapsamında değil. Otomatik kontroller başarılı, bütün grafik için nihai kabul verilmedi.

## Bulgular ve uygulanan düzeltmeler

- frontend/src/DrawingLayer.tsx:20 — P1, sürüklemenin pointer sahibi yoktu. İkinci dokunuş veya farklı pointer hareketi ilk işlemi etkileyebilirdi. Artık yalnızca birincil sol pointer başlatır; tek sahip bitirebilir, diğer pointer'lar yok sayılır.
- frontend/src/DrawingLayer.tsx:14 — P1, tüm iptal yolları ortak değildi. Escape, blur, pointercancel, lostpointercapture, coin/zaman dilimi değişimi, devre dışı bırakma ve unmount ortak temizliği kullanır. İptal kayıt başlatmaz; capture ve grafik hareket kilidi serbest bırakılır.
- frontend/src/drag.ts:18 — P1, sabit interval saniyesiyle kaydırma, veri boşluklarında yanlış muma taşıyabilirdi. Artık gerçek mum indeks/zaman dönüşümü yapılır. Nokta sırası korunur; tek mum ve geçmiş dışı koordinatlar ele alınır.
- frontend/src/DrawingLayer.tsx:29 — P2, sürüklemeye başladıktan sonra ilk noktaya geri dönüş eşik kontrolünde atlanıyordu. Eşik yalnızca başlangıçta uygulanır.
- frontend/src/types.ts:19 — P1, snapshot yolu kapanmış mumu tekrar açık kabul edebiliyordu. Snapshot da kapanmış-mum korumasını kullanır.
- frontend/src/types.ts:8 — P1, closed alanının tipi ve close_time sınırı doğrulanmıyordu. Güvenli tamsayı, boolean ve zaman sırası kontrolü eklendi; hatalı paket dizileri ve negatif/geçersiz sayaçlar reddedilir.
- frontend/src/types.ts:16 — P2, aynı sıra numaralı heartbeat mum dizisini yeniden oluşturuyor, göstergeleri gereksiz hesaplatıyordu. Artık durum güncellenirken mum dizisi kimliği korunur ve aynı sırayla yeni fiyat sokulamaz.
- frontend/src/DrawingPanel.tsx:10 — P2, sürüklemenin zaman ekseninde klavye alternatifi eksikti. Noktaların UTC zamanı datetime alanından düzenlenebilir; fiyat/zaman alanları zorunlu, yükleme sırasında kaydet/sil kilitli.
- frontend/src/App.tsx:62 — P2, ana içeriğe atlama bağlantısı yoktu. Eklendi; kısa yol artık textarea/select/contenteditable alanlarını bölmez. Çizim seçimi Enter/Space ile yapılabilir, araç yönergeleri status olarak duyurulur.
- frontend/src/style.css:15 — P2, dark form controls, reduced motion ve uzun piyasa listesi için eksikler vardı. color-scheme, azaltılmış hareket, tabular sayılar, içerik görünürlüğü ve dialog scroll containment eklendi. Görsel erişilebilirlik kabulü ayrıca bekler.

P1, doğruluk/etkileşim açısından öncelikli; P2, kullanım/performans düzeltmesi. Bunlar kod incelemesiyle bulunan sorunlardır; tarayıcıda yeniden üretildiği veya tüm DOM olaylarının uçtan uca test edildiği iddia edilmez. DragGuard ve koordinat çekirdeği otomatik test edildi; React event bağlantıları gerçek tarayıcı kontrolünü bekler.

## Doğrulama

26 frontend testi, TypeScript kontrolü ve Vite üretim derlemesi geçti. Önceki 16 teste 10 senaryo eklendi: ikinci pointer, tek seferlik iptal, boşluklu zaman dönüşümü, ters yönlü çizim, ankraj sınırları, snapshot kapanış koruması, hatalı paketler, mum bayrakları, heartbeat kimliği ve tek mum geçmişi.

666 Python testi, atlanan test olmadan ve izole HTTP/worker/yeniden başlatma kontrolüyle geçti. Finansal runtime/risk koruması geçti. Backend kaynakları bu tur değiştirilmedi.

[Denetim sonucu](reports/chart-audit-validation-20261109.json) · [Backend/HTTP sonucu](reports/chart-workspace-validation-20261109.json) · [Kabul matrisi](reports/chart-acceptance-matrix-20261109.json)

## Açık kabul grupları

| ID | Grup | Durum |
| --- | --- | --- |
| G01 | Dört çizim türü; sürükleme/iptal/pointer sahipliği | Çekirdek otomatik testleri geçti; gerçek event testi bekliyor |
| G02 | Zoom/pan/ölçek/pane resize/DPR sonrası hizalama | Sayısal dönüşüm geçti; görsel ölçüm bekliyor |
| G03 | Kayıt/yeniden başlatma/çok sekme/oturum süresi | HTTP regresyonu geçti; hook yarış senaryoları bekliyor |
| G04 | Canlı mum/geçmiş/reconnect/geçersiz paket | Otomatik çekirdek geçti; tarayıcı bağlantı kesintisi testi bekliyor |
| G05 | EMA/RSI ve pane yaşam döngüsü | Sayısal fixture'lar geçti; aynı veriyle görsel karşılaştırma ve 50 toggle bekliyor |
| G06 | 4.000 mum/200 çizim; 30 dakika | Gerçek tarayıcı CPU/frame/heap ölçümü yapılmadı |
| G07 | Klavye/mobil/dokunma/fullscreen/azaltılmış hareket | Kod düzeltmeleri yapıldı; gerçek cihaz/ekran okuyucu kontrolü bekliyor |

G06 için başlangıç hedefi: test makinesi/tarayıcı/DPR kaydıyla 60 saniye etkileşimde p95 kare süresi <=33 ms, sıfır işlenmemiş hata; tekrar eden geçişlerde heap/listener/socket sayısının kararlı seviyeye gelmesi. Bunlar ölçülmüş sonuç değil, ilk kabul hedefidir. G02 için <=1 CSS piksel hizalama hedefi ekran görüntüsüyle ölçülmelidir. Önceki koordinat mikrobenchmark'ı FPS veya toplam render performansı yerine kullanılamaz.

Tarayıcı erişim host'u yeniden denendi ve kullanılamadı. Bu yüzden masaüstü/mobil ekran kanıtı ve uzun oturum kabulü açık tutuldu; kusursuz/hatasız/60 FPS sonucu yazılmadı.

## Sonraki iş

Önce gerçek tarayıcı erişimiyle G01/G02/G07; ardından G03 kayıt yarışları ve G05 pane yaşam döngüsü, son olarak G06 uzun oturum profili. useDrawings içinde refresh ile eşzamanlı yükleme ve oturum sona ermesi ayrıca gecikmeli yanıt testleriyle incelenecek; mevcut HTTP 409 testleri React hook yarış testi yerine geçmez.

İncelemede [web-design-guidelines skill'i](C:/Users/asus/.codex/skills/web-design-guidelines/SKILL.md) ve güncel [arayüz kuralları](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) kullanıldı. Grafik yaşam döngüsü [resmî primitive API sözleşmesiyle](https://tradingview.github.io/lightweight-charts/docs/api/interfaces/ISeriesPrimitiveBase) karşılaştırıldı. Bu tur yeni skill veya bağımlılık kurulmasını gerektiren ihtiyaç oluşmadı.
