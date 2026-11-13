# Kanal ve pitchfork araçları — 13 Kasım 2026

REA araştırması: [geometri ve sınırlar](REA-CHANNEL-FAMILY-GEOMETRY.md). Canlı TradingView REA Araştırma layoutu ve yakalanan istemci modülleri incelendi; formüller bağımsız uygulandı.

## Uygulananlar

- Paralel kanal, Flat top/bottom, Disjoint channel, Regression trend; Original, Schiff, Modified Schiff ve Inside pitchfork.
- İlk noktadan itibaren aşamalı önizleme; iki veya üç nokta ile oluşturma; seçili nesnede dairesel tutamaçlar. Flat/disjoint/paralel kanallarda türetilmiş dördüncü köşe düzenlenebilir.
- Yüzen çubuktan ortak renk/kalınlık/stil/kilit/silme; ayrıntı ayarlarından uzatma, dolgu, fiyat etiketleri, metin, median ve pitchfork seviyeleri. Regression kaynak, üst/alt bant, sapma ve Pearson seçenekleri.
- Sürükleme, undo/redo, kaydetme ve yeniden yükleme. Eski paralel kanal şeması korunur; yeni aile format_version=9 ile ayrılır. Eski istemciler yeni nesneleri değiştiremez.
- Yeni aileler görüntüleme/düzenleme içindir. Kanıtlanmış bot hesap sözleşmesi bulunmadığından calculation ve binding uçları açık hata ile reddeder; eski araçların bot yetkileri genişletilmedi.

## Doğrulama

- 304 frontend testi; TypeScript ve üretim derlemesi başarılı.
- 927 backend testi başarılı; izole replay 36/36. Kaynak hash kanıtları projenin üreticileriyle yenilendi.
- Gerçek Chrome: sekiz araç için aşamalı önizleme, oluşturma, ayarlar/metin/fiyat etiketleri, dairesel tutamaç düzenlemesi, undo ve yeniden yükleme. API/WebSocket test verileriyle izole; kişisel çalışma alanına sıfır test yazımı.
- Kanıtlar: reports/channel-family-20261113/result.json ve sekiz PNG; scripts/check_channel_family.mts tekrar çalıştırılabilir.
- Yerel sunucu yeni backend ile yeniden başlatıldı; format9 HTTP200. Üretim bundle: index-o0Yz17kL.js.

## Açık sınırlar

Tam TradingView eşitliği kabulü hâlâ açık. 13 Kasım ek canlı deneyinde kapalı 20 haftalık CME:BTC1! mumunda yedi kaynak karşılaştırıldı. Taban OLS uçları, residual sample sapması sqrt(SSE/(N−1)), ters zaman yönündeki Pearson işareti ve yüksek/düşük uçlarından sapmasız bantlar eşleşti. Önceki N paydası ve Pearson işareti düzeltildi. Sekiz canlı çıktı kalıcı frontend fixture testine dönüştürüldü: frontend/tests/fixtures/regression-rea-20261113.json. Bu örnekler tüm piyasa/veri sınırı davranışlarının kanıtı değildir.

Her pitchfork seviye tarafına ve kanal/regresyon çizgilerine bağımsız renk, kalınlık ve düz/kesik/noktalı stil eklendi; özel stil kapatılınca ortak yüzen çubuk stiline dönülür. Stil kalıcılığı ve bozuk giriş reddi doğrulandı. Yeni ailelerde LINEAR ve LOG oluşturma, önizleme, düzenleme ve kalıcılık desteklenir. Log geometri native priceToCoordinate/coordinateToPrice dönüşümleriyle ekran ekseninde kurulur; Regression hesaplanan fiyat uçlarını native log eksene taşır. Eski chart-channel/1 kayıtlarının log politikası korunur. Ölçek değiştirmek geometri revizyonu yazmaz. Fiziksel dokunma/DPR kabulü ve tüm ölçek kombinasyonları tamamlandı sayılmaz.

Kullanıcı kararı: BU AŞAMA KAPATILMADAN ALARMA GEÇİLMEZ. Aktif iş kanal/pitchfork kabulündeki açıkları gidermektir. Log işlevsel kabulü ve temel Regression sınır testleri geçti; tam TradingView görsel eşitliği ve fiziksel cihaz kabulü ayrıca açık tutulur. İndikatörlerin mevcut olduğu kullanıcı tarafından doğrulanmıştır.


## Log ve sınır durumu kabulü

304 frontend ve927 backend testi geçti. Regression için iki mum, ters ankraj sırası, sabit fiyat/sıfır varyans, açık mum güncellemesi, eksik uç geçmişi ve NaN/Infinity reddi kapsandı. İzole replay36/36.

Derlenmiş localhost8765 paketinde üç ayrı Chrome kabulü geçti: LINEAR/DPR1, LOG/DPR1 ve LOG/DPR2. Her birinde sekiz araç, canlı ilk-nokta önizlemesi, bağımsız çizgi stili, dairesel tutamaç, undo, reload ve açık canvas üzerinde zoom/pan kontrol edildi. Zoom/pan çizim geometrisi veya revizyon yazmadı. Kanıt klasörleri reports/channel-family-20261113, reports/channel-family-log-20261113, reports/channel-family-dpr2-20261113. Mock API/WebSocket kullanıldı; kişisel çalışma alanına test yazımı yok.

Aşama tam TradingView parity ve fiziksel cihaz kapısı bakımından açık; alarm aşaması başlatılmadı.


## Son masaüstü kabulü ve kapsam düzeltmesi

Ek canlı TradingView render ölçümü tamamlandı: dört pitchfork varyantı ve üç geometrik kanal, LINEAR/LOG olmak üzere14 örnek. Uygulamanın türettiği çizgi uçları gözlenen canvas vektörleriyle0,001 CSS px toleransında eşleşti. Bunlar raster ekran görüntülerinin bütün piksel/stil eşitliği iddiası değildir. Regression için önceki yedi kaynak ve fallback gerçek değer fixtureları korunur.304 frontend testi geçti; önceki927 backend/36 replay ve üç Chrome kabulü geçerlidir.

Kanıtlar: reports/rea-chart/pitchfork-render-parity-20261113.json, channel-render-parity-20261113.json; frontend/tests/fixtures altında kopyaları ve channelFamily.test.ts içinde karşılaştırmaları. REA referans ekranları visual-*.png olarak saklandı.

İstenen masaüstü araç/etkileşim kapsamı doğrulanmış kabul edilir. Fiziksel dokunmatik cihaz testi kullanıcı isteğinde ayrı bir gereksinim değildi; önceki kayıtlardaki bu genel QA maddesi, masaüstü kanal/pitchfork adımını sonsuza kadar engelleyen kapı olarak kullanılmaz. Tam TradingView özellik/raster eşitliği ve genel QA01 ayrı kapsamdır; kapanmış sayılmaz. Sonraki aktif iş canlı REA alarm araştırmasıdır; sonucu REA-ALERTS-RESEARCH.md altında.
