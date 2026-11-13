# Mıknatıs, seçim alanı, sürükleme kesintileri ve çoklu seçim

11 Kasım 2026, yaklaşık09:40–10:07 UTC. REA03 canlı araştırması; tasarım, etkileşim ve sayısal sonuçlar aynı turda. Ürün kodu değiştirilmedi. REA04 taslak, önceki5/21 geliştirme işi tamamlanmış olarak korunur.

Kanıt: reports/rea-chart/rea-evidence-snap-selection-interrupt-20261111.json — **38 REA kaydı /3.994.864 byte**. Bu yeni paket önceki106 kaydın tekrarı değildir; önceki paket ayrı korunur. İlk başarısız bağlantı sonrası close_binary cleanup uygulandığından yeni ledger ayrı başladı. Paket unknowns=0, kapsamın bütünüyle çözüldüğü anlamına gelmez.20 PNG/hash: reports/rea-chart/snap-selection-visual-manifest-20261111.json;5 REA ve15 ordinary-CDP ekranı. Ordinary kayıtlar REA Evidence diye sunulmaz.

## Araştırma düzeneği ve başarısız girişler

Araştırma Chrome'u kapanmıştı:9338 endpoint erişilemiyor, ilgili Chrome süreci yoktu. REA doctor Codex/node kaydını healthy verdi; ilgisiz native engine eksikleri bu browser işi için gerekli değildi. Bekleyen cleanup close_binary ile tamamlandı. Mevcut research-visible profili yeniden açıldı; yeni target099F5CC8F421F74508CDF607D28726C8 list_browser_targets ile doğrulandı. Yeniden kurulum veya güvenlik ayarı değişikliği yapılmadı.

Bir TradingView Session disconnected ekranı da görüldü: ev_8589e9baae1aa2b091239b1ceb34757c0999ea55e243ea9df857243c6a4eb54d. UI başka Chrome/cihaz oturumu nedeniyle bağlantıyı kapattığını bildirdi; bunun güvenlik olayı olduğu çıkarılmadı. Bir normal Connect ile devam edildi: ev_5de79f45f2653cbc9e3325ac693d21aa962d021a158ea1a8195dc32bde43d4f8. Kesinti sırasında alınamayan koordinatlar sonuç kabul edilmedi.

İlk otomatik batch'te aynı/eksik koordinat, açılmayan dialog ve gecikmiş cleanup durumları oldu; snap-comparison-attempt1/2/3-20261111.json ve son batch hata kaydı korunur. İmleç/araç yerleşmesi beklemesi eklendi; nihai deneylerde **normal canvas girdisi ordinary-CDP, form okuma ve cleanup REA** olarak ayrıldı. Başarısız örnekler altı doğrulanmış örneğe dahil değildir. Runtime round-trip'lerde yaklaşık5sn beklemeler vardı; kullanıcı gecikmesi/FPS ölçümü değildir.

Sahne: BINANCE:BTCUSDT spot/1D/UTC, Volume+BB20, başlangıçta çizim yok. Orijinal dört perpetual çizimi değiştirilmedi. Desktop canvas CSS1058×667.2, köşe56/42; PNG1920×970. Eksen Logarithmic ve Auto işaretleri ev_0c26668e4b3dbd7dca73874b20a7b6083a3d47b4a73963407008ce3a30ece9ca ile gözlendi. Bu boyutlar touch/responsive veya ürün pixel parity kabulü değildir.

## 1. Aynı mumlar, aynı piksel noktaları, üç mıknatıs modu

Menü ev_c333bc4658ddbdedde2294b9c9d28c30a81f935077b102d71bfd56f6662a3e9c: Weak magnet/Strong magnet; Snap to indicators disabled. Disabled nedeninin plan/başka ayar olduğu kanıtlanmadı; göstergeye snap çalıştı denmez.

İki kapalı spot mumunun görünür Data window değerleri:

| UTC gün / logical bar | O | H | L | C |
| --- | --- | --- | --- | --- |
|3Ekim /260 |84518.00 |85037.63 |84456.02 |84753.56 |
|17Ekim /274 |81615.91 |81770.01 |80819.66 |81491.04 |

Kalibrasyonda normal trend formu80667.87/bar260 ve71113.56/bar274 verdi: ev_10115bda2c523706893391a9193aba11867488a038cbb877e80eec55a3ffec4f. Bu fiyat/piksel örnekleriyle yakın iki konum türetildi; tahmini OHLC konumundan4 CSSpx dışarı hedeflendi. Canlı auto-scale/raster ve cents yuvarlama nedeniyle **kesin4px snap mesafesi** iddiası yoktur. Aynı konumlar her modda tekrarlandı; far örnekleri aynı X'te daha uzaktaydı.

| Konum / mod | Nokta1 fiyat | Nokta2 fiyat | Barlar |
| --- | --- | --- | --- |
|Yakın /kapalı |85292.13 |80529.63 |260/274 |
|Yakın /zayıf |85037.63 (H) |80819.66 (L) |260/274 |
|Yakın /güçlü |85037.63 (H) |80819.66 (L) |260/274 |
|Uzak /kapalı |66398.38 |87890.97 |260/274 |
|Uzak /zayıf |66398.38 |87890.97 |260/274 |
|Uzak /güçlü |84456.02 (L) |81770.01 (H) |260/274 |

Altı REA koordinat kanıtı sırasıyla:
ev_43fef75af0548f341faef29a87abc4681c298584873db97089021b68946281c5,
ev_6702e7fed334316414f7f63a209bb4b6d6ae3851da33debe35c7f8892c07f36c,
ev_bc2db835b16426992492d5642dae5648484458de6909c889a0e2c9cb8f793285,
ev_f08523a54949a2fdd8ef4cc7ec6c1507ff29911defd2dbb0db99aa63751db95a,
ev_1aaa9d82897e2a8073afceb0bd21e9657e79229dcc505c061ddcdccb8c885ebd,
ev_e80f5a619327a37c58d7d12a9a8847e71255a5be112cc08dac33dd7b5bcc841a.

Yakında weak/strong aynı OHLC'yi, uzakta weak=off serbest fiyatı, strong yine OHLC'yi verdi. Bu örnek bütün threshold'ların veya price/time snap politikasının kanıtı değildir. Barlar zaten aynı X konumuna karşılık geliyordu; zaman mıknatısının yatay yarıçapı ölçülmedi. Aynı mumda eşit uzaklık tie-break, Ctrl geçici magnet, drag sırasında mode değişimi ve gösterge snap açık.

Aktarım T07/T12/T13: **OHLC mıknatısı ile tick-grid fiyat yuvarlama ayrı işlemdir**. frontend/src/drag.ts içindeki snapPrice tick hizası bu yeni yeteneği sağlamaz. Seçilen candle/field, raw pointer fiyatı, snapped aday fiyatı ve son tick politikası ayrılmalı; ekran pikselinden kesin bot fiyatı türetilmemeli. Magnet-off açık durum, Weak/Strong tercihi ve geçici modifier durumu ayrı modellenmeli.

Kayıt: reports/rea-chart/snap-verified-fixture-20261111.json; altı snap-near_*/far_*-20261111.json ve PNG. Mode seçimleri REA setup kayıtlarında, noktalar native helper eylem zamanlarında saklı.

## 2. Gövde hit örnekleri ve tasarım

Tek2px steep trendde gövde ortasının çevresine dik yönde0/4/8/16 CSSpx offset örneklendi. Önce boş alana tıklanıp sonra hedefe gidildi. CSS.getComputedStyleForNode sonucunda canvas cursor0'da pointer;4/8/16'da crosshair.0 PNG'sinde trend seçili, tutamaklar/fiyat etiketleri ve nesne ağacı vurgusu görünür. Görsel çizgiye yakın hedef ile etkileşim hedefinin tasarımı ayrı kabul maddesidir.

reports/rea-chart/trend-hit-probe-20261111.json ve trend-hit-0/8/16 PNG. Kaydedilen data-source span etiketi tek başına seçili sınıf taşımıyor; bununla seçili durum sayısı iddia edilmez. Cursor+ekran birlikte okunur. Bu dört sample kesin hit yarıçapını, endpoint radius'u, tüm eğimleri veya touch hedefini tanımlamaz; raster/auto-scale etkileri ayrıca sınırlamadır.

Aktarım: DrawingLayer.tsx görünür shape ile hit-line/handle geometrisini zaten ayırıyor. Yeni kabul, seçili/seçili-değil ve hover durumlarında gerçek hit alanını masaüstünde kontrol etmeli. Referansın dar örneği evrensel ürün hedefi yapılmaz. Hover sırasında chart crosshair önceki konumda kalabildi; ekran crosshair'i tek başına gönderilen mouse koordinatı sayılmaz.

## 3. Grafik dışındaki panelde bırakma

Başlangıç trend:66398.38/bar260 →87890.97/bar274. İkinci tutamak basılıyken sağdaki panel içine sürüklendi. **Ara basılı-fare PNG'si endpoint preview'un hareket ettiğini gösterdi.** Sonuç66398.38/bar260 →75837.70/bar309; Toolbar Undo change point. Tek Ctrl+Z başlangıç koordinatlarını tam geri getirdi.

REA sonrası ev_d64d26e66c2183f5a4c08d587aa77ac7d1132696c431981a131b14e7388484e6; Undo ev_4166a2418724b62a092a48c4670b73a5c58d5ed5272868b815fde803ea82b8a7. Ordinary trend-interrupt-outside-20261111.json, held/final PNG.309, gözlenen başlangıç300-mum penceresinin299 son indeksinden ilerideydi; boş geleceğe ankraj mümkün oldu. Son X'in pane kenarında sınırlandığı olasıdır ama tek örnekten clamp formülü çıkarılmaz.

İlk outside-attempt1'de koordinatlar/history değişmemişti ve held-preview alınmamıştı; gerçekten drag başladığı kanıtlanmadığından rollback davranışı sayılmadı. Ara görüntülü ikinci örnek nihai doğrulanmış sonuçtur.

Bu tarayıcı içindeki **grafik alanı dışı** bırakmadır, OS pencere dışı veya pointercancel değildir. DrawingLayer guard/capture ve restoreInteraction yolları ürün kabulünde sonlanmalı; yeni gesture takılı kalmamalı, tek commit/Undo olmalı. Bu tur backend persistence/reload fixture'ı değildir.

## 4. Basılı sürükleme sırasında sekme değişimi

Aynı başlangıç ikinci noktası grafik içinde taşındı. Helper yalnız kendine ait about:blank sekme oluşturdu, onu aktive etti, araştırma sekmesine döndü, mouseup gönderdi ve oluşturduğu sekmeyi kapattı. Sonuç ikinci83841.73/bar281; ilk nokta aynı. Toolbar Undo change point; tekUndo başlangıç87890.97/bar274'ü geri getirdi.

REA ev_c71d59237dde2ba1b0ff0c3ecc7949f981776e9da9e2ec121d5c98a9d078470b ve ev_cc874ba36831968ea4795e40fdddea84792737dd150daa649609b7e6f6ebf962. Ordinary trend-interrupt-tab-20261111.json; button_released=true, owned_blank_tab_closed=true. Held-preview PNG alındı. Bu **normal sekme değişimidir**; OS blur olayı veya gerçek browser pointercancel alındığı kanıtlanmadı. Referansın keep davranışı ürünün Escape/blur rollback kararı yerine otomatik konmaz.

İki deney tek fixture dosyasında: reports/rea-chart/pointer-interruption-fixture-20261111.json.

## 5. Ctrl çoklu seçim ve karışık kilit

Temp trend Clone ile ikinci geçici nesne oluşturuldu: ev_04d49ed846b4d1ddeaa5db68fafeb0e82ac7917d4a4b7ced70ddf552fa89976d. Normal ilk satır tıklaması1 seçili; Ctrl+ikinci satır tıklaması2 seçili verdi. Visible DOM ancestor selected sınıfları ve iki mavi satır/çizim görseli destekler; ana data-source span'ı tek başına yeterli değildir. İlk DOM örneğinde frontend nodeId yenilenince ancestor zinciri boş kaldı; helper backendNodeId kullanacak şekilde düzeltildi, geçerli kayıt sonrasında alındı.

İlk çizim Lock edildi: ev_a55f7f31d60f7603e986de9a07a53efa235d1e8841cf7f6fb8d2fb5fd6fe7ccd. Aynı Ctrl seçimi yine iki seçili öğe verdi. REA ev_2fcf2d8f2fb82f35544533b8f5c83a68d76a08eac81ca7b5bdc5cb89e76515a1 ilk aşamasında bir Unlock ve bir Lock ikonu aynı anda gözlendi; seçim sınıfları iki öğede. **Kilitli nesne seçilebilir; kilit ve seçim ayrı boyutlardır.** Context menü Rename gibi tek nesne komutlarını göstermeyen çoklu menüye geçti; bu menüde Unlock vardı.

Ordinary multi-selection-unlocked/mixed-20261111.json ve PNG. Modifier finally bırakıldı. Bu test **nesne ağacında iki trend seçimi** içindir; canvas Ctrl-selection, marquee, mixed group drag, alignment/displacement, grup hiyerarşisi veya klavye shift-range kabulü değildir. Kilitli/serbest çiftin birlikte taşınması hâlâ açık. Basic-plan nested group sınırı kalkmadı; yeni hesap yükseltme yapılmadı.

Temizlikte çoklu menüden Unlock, sonra Delete uygulandı; iki geçici çizim birlikte kalktı, spot kaynak ağacı yalnız BTCUSDT/Volume/BB3 öğeye döndü: ev_c4f0507013218583d71e4a3e7ce0a649e437a75c5eeb23b61c6a87f4b9d2434b.

## 6. Tasarım aktarımı, açıklar ve son durum

D09–D10 görsel gereksinimleri: magnet açık durumu/tercihi ve geçici yardım bildirimi, seçilebilir cursor, selected handles, aynı renkli fiyat-zaman etiketleri, iki mavi tree satırı, bağımsız lock/unlock ikonları ve ortak command toolbar. Kontroller odak/klavye erişimiyle tasarlanmalı; hash'li sınıf adları ürün tasarım token'ı olarak kopyalanmaz. Magnet-on bilgi bildirimi deney sırasında görünür oldu; modal/tooltip odak ve canvas girdisini yanlış ele geçirmemeli.

Ürün eşlemesi: DrawingLayer.tsx pointer capture/guard/preview/Escape+blur; drag.ts tick snapping ve bir pointer sahibi; interaction.ts chart etkileşimini geri verme; useDrawings.ts command/persistence/revision. Bunlar kaynak incelemesidir, TradingView iç uygulamasının kaynak çözümü değildir. Yeni araç/multi-selection/semantic OHLC snap planı T07/T12/T13 ve QA01'de sürümlenecek; tamamlanmış T02 sıfırlanmayacak.

Açıklar: gerçek pointercancel/lost capture/OS blur; mixed-lock group drag; yatay snap/tie-break/modifier/indicator snap; endpoint hit matrisi; farklı DPI/zoom/touch. Sonraki geniş tur bunları sınırlı kabul kararlarına bağlayıp seed/volume/seans ve veri request race araştırmasına geçmeli. Performans framep95/matched workload ve REA04 konsolidasyonu ayrıca açık; bu30dakikalık etkileşim turu performans testi değildir.

Nihai ev_202e27b8ba361c9a358e7960b53b99bff54c4e9ab658484d1a33c974a90ee628: BTCUSDT.P/1D/UTC, Volume korunmuş; BB20/SMA/close/2/offset0/Chart/WaitON formu yeniden okundu. Dört orijinal çizim global gizli; geçici spot çizimleri ve helper boş sekmesi temiz; magnet kapalı, Ctrl/mouse bırakılmış, dialog kapalı, All changes saved. Tüm bot/işlem yetkileri değişmeden kaldı; ürün uygulaması yapılmadı.

Yeniden hesaplama: tools/rea/verify-snap-selection-research.mjs; çıktı reports/rea-chart/snap-selection-validation-20261111.json. Toplam36 araştırma fixture'ı; ürün testlerinin PASS sayısı değildir.

Doğrulama tamamlandı:6 snap case,4 cursor sample,2 interruption/Undo çifti,1→2 tree seçimleri (serbest ve mixed lock),20 PNG hash/boyutu, spot3-kaynak temizliği ve son Chart/WaitON/saved durumu kontrol edildi. Önceki UTC/log/HTF doğrulayıcı global fixture sayısına değil kendi kohort kimliklerine bağlandı; yeni bulgular eski kanıtları sıfırlamaz.
