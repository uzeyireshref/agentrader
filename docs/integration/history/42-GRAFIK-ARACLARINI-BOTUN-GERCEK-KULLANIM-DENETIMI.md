# Grafik araçlarının bot tarafından gerçek kullanım denetimi — 14 Kasım 2026

## Sonuç

Mevcut bot kendi kendine trend çizgisi, Fibonacci veya kanal çizip bunlardan işlem başlatmıyor. Grafik çizim/hakimiyet altyapısı, hesaplama sorguları ve sınırlı grafik-sinyal-plan köprüsü vardır; bunlar çalışan bağımsız bir çizim stratejisi anlamına gelmez. Bu inceleme salt okunurdur: yeni çizim, bağlantı, sinyal, onay veya emir oluşturulmadı.

## Çalışma deposundaki gerçek kanıt

WebSettings.load ile seçilen data/application-demo.sqlite3 ve data/execution.sqlite3 yerel sahip kapsamında salt okunur incelendi. Güncel, silinmemiş çizimler: iki horizontal, iki trend ve bir horizontal_ray. Bunların varlığı bot tarafından üretildiklerinin kanıtı değildir; mevcut şema onları otomatik strateji çıktısı olarak göstermiyor.

Çizim bağlantısı revizyonu: 0. Gölge takip kaydı: 0. Gölge olay: 0. Sinyal plan önizlemesi: 0. Grafik onay isteği: 0. İşlem deposundaki sekiz planın shadow-event: kaynaklı olanı: 0. Son beş plan operator-authorized-demo-acceptance kaynaklı teknik testlerdir. Önceki üç plan rapor kaynaklıdır. Dolayısıyla bu depo kapsamında grafikteki araçlardan üretilmiş gerçek Demo işlem kanıtı yoktur.

## Katmanlara göre yetenek

| Katman | Mevcut durum | Sınır |
|---|---|---|
| Çizim oluşturma/düzenleme | Kullanıcı arayüzü ve DrawingService API mevcut | Piyasa verisinden bağımsız çizim üreten strateji/ajan bulunmadı |
| Trend/ışın/yatay çizgi sorgusu | priceAt, distance hesaplama ve binding kataloğu var | Hesaplama yeteneği otomatik çizim veya işlem değildir |
| Fibonacci / extension | Seviye hesabı ve seçili oran için binding tanımı var | Canlı ShadowTracking profili bu hedefleri kabul etmiyor |
| Eski paralel kanal | Alt/orta/üst sınır ve mesafe sorguları var | Yeni chart-channel-family/1 şemasındaki kanallar ayrı ve display-only |
| Yeni kanal ailesi / pitchfork | Çizim ve kalıcı görsel sözleşme var | BindingService DISPLAY_ONLY_CHANNEL_FAMILY ile engelliyor |
| Canlı gölge sinyal | horizontal/horizontal_ray; approach/touch/close_cross | Açık başlatma, kapanmış Demo mumları ve açık yeniden kurma gerekir; çalışan hesapta kayıt yok |
| Grafik sinyali → plan → emir | Önizleme, hesap incelemesi, yerel onay ve yürütme kodu var | Gerçek kullanım yok; taze kaynak, risk, onay ve bağımsız izleyici kontrolleri korunuyor |
| Otomatik giriş/stop/hedef seçimi | Bu grafik köprüsünde yok | SignalPreviews değerleri açık parametrelerden alıyor |

BindingService tanımındaki write_target=False, edit_target=False, execute_rule=False ve order_authority=False değerleri hedef nesneyi salt okunur tutar. Sonraki ayrı gölge/plan/yürütme katmanları bu tanımdan kendi kendine yetki türetmez.

## Kod dayanakları

- agentrader/chart/chart_bindings.py: _definition, bot_capabilities ve yeni kanal ailesi reddi.
- agentrader/integration/shadow_tracking.py: _supported yalnız horizontal/horizontal_ray kabul eder.
- agentrader/chart/binding_catalog.py: çizim/indikatör sorgularının hesaplama kapsamı.
- agentrader/chart/drawings/channel_family.py: yeni kanalların display-only sözleşmesi.
- agentrader/integration/signal_previews.py: açık giriş/stop/hedef parametrelerinden plan üretimi.
- agentrader/integration/chart_execution.py ve agentrader/bot/v2_runner.py: shadow-event: bağı ve emir öncesi kontroller.
- agentrader/api/drawings.py ve frontend/src/App.tsx: çizimlerin API/kullanıcı etkileşimiyle oluşturulması.

## Öncelikli geliştirme sırası

1. Var olan bir yatay çizgiyi gerçek Demo verisiyle bağlantıya alıp gölge olay → önizleme → hesap incelemesi → plan → bağımsız izleyici → küçük Demo emir zincirini uçtan uca kanıtlamak. Mevcut hesapta sıfır olan bağlantı kayıtları bu adımın henüz uygulanmadığını gösterir.
2. Canlı gölge sinyal profilini trend/ışın, Fibonacci seçili seviyeleri ve hesaplaması doğrulanmış kanal kenarlarına genişletmek. Yeni kanal ailesinin görsel şemasına yalnız yetki bayrağı eklemek yeterli değildir; hesaplama, veri bağlamı ve yeniden oynatma kanıtı gerekir.
3. Botun otomatik çizim üretmesini ayrı bir strateji katmanı olarak geliştirmek: kapalı mumlardan açık swing/anchor kuralları, tekrar üretilebilir geometri, kaynak mum/strateji sürümü, bot üretimi etiketi, idempotent güncelleme ve kullanıcı çizimlerine dokunmama.
4. Otomatik çizimlerden açık koşul ve risk planı üretimini bağlamak; stale/silinmiş/değişmiş geometriyi engellemek. Önce geçmiş veri/gölge testleri, sonra mevcut küçük bütçe ve Demo korumalarıyla gerçek kabul.

Bu maddeler incelemede uygulanmış sayılmaz. Kullanıcının bu mesajı mevcut yetenek ve gerçek kullanımın denetimidir; eksik otomatik strateji varmış gibi gösterilmedi.

## Doğrulama

Hesaplama, Fibonacci, paralel kanal, kanal ailesi, gölge takip, plan önizlemesi ve grafik yürütme alanlarından 82 ilgili test geçti. Bunlar izole testlerdir; bu hesaptaki gerçek grafik kaynaklı emir kanıtının yerine geçmez. Katalog VERIFIED_TRACEABILITY durumunda.

Kanıt: reports/chart-bot-tool-audit-20261114.json. Test günlüğü: reports/chart-bot-tool-audit-tests-20261114.log. İnceleme emir sayısı: 0.
