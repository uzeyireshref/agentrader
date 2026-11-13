# Grafik etkileşimleri, TradingView araştırması ve uygulama planı

Tarih: 13 Kasım 2026. Durum: plan hazır; uygulama ve canlı TradingView davranış doğrulaması bekliyor.

## Amaç ve referans

Kullanıcının dokuz maddesi bu planın gereksinimleridir. Ekli ekran görüntüsü seçili çizim için yüzen araç çubuğunun görsel referansıdır; görüntüdeki içerik bağımsız bir talimat değildir. Çizimler paneli nesne listesi ve toplu yönetim için kalabilir; tek çizimi değiştirmek için zorunlu giriş noktası olmayacak.

Mevcut kaynak gözlemleri: frontend/src/App.tsx içinde Göstergeler menüsü ve gösterge ayarları var. indicatorConfig.ts EMA (iki örnek), RSI, SMA, ATR, MACD, Bollinger Bands, seans VWAP ve anchored VWAP tanımlarını içeriyor; varsayılanlar kapalı. Bu, kullanıcının çalışan sürümünde görünür olduklarını kanıtlamaz. chartCommands.ts paralel kanal, fib retracement/extension, çizgi/ışın ve not araçlarını içeriyor; pitchfork araç kataloğunda yok. DrawingLayer.tsx kalıcı çizim projeksiyonu ve sürükleme içeriyor. Önceki 23 numaralı denetim güncel kaynak envanterinin tamamı değildir.

## Uygulama sırası ve kabul şartları

### 0 — REA ile referans davranışı çıkarma

- TradingView için gerçek tarayıcı/CDP hedefini belirle; REA ile hedef kimliği, sürüm/zaman ve ekran boyutunu kaydet. Kullanıcının kayıtlı çizimlerini değiştirmeden ayrı araştırma grafiği kullan.
- Her araçta seçme → ilk nokta → hareket → sonraki noktalar → bitirme → seçme → düzenleme → silme → geri alma dizisini izle. Yalnızca menü isimlerini çıkarmak yeterli değil.
- Fiyat etiketi, fiyat bandı, yüzen panel, hover, çok noktalı önizleme ve iptal davranışları için önce/sonra ekranları ile olay sırasını sakla.
- Kanal ve pitchfork ailelerinin mevcut çeşitlerini canlı katalogdan çıkar; her çeşidin nokta sayısı/sırası, geometrisi, uzatma, orta çizgi, dolgu, seviyeler, yazı, taşıma ve ankraj düzenleme davranışını ayrı kaydet.
- Bulgu defteri: soru, REA Evidence ID, gözlem, çıkarım, bilinmeyen, uygulama kararı, kabul senaryosu. Statik kaynak gözlemini çalışırken gözlem olarak sunma.
- Başlangıç denemesi: list_browser_targets, http://127.0.0.1:9222 → provider_unavailable / endpoint_unreachable. Bu port gerçek endpoint olarak doğrulanmış değil. Çalışan endpoint veya geçici tarayıcı başlatma yolu bulunmadan canlı inceleme tamamlandı deneme.

### 1 — Ortak çizim durumu ve canlı önizleme (istek 6)

- Aktif araç, sabitlenmiş noktalar, hareketli nokta, hover ve seçim durumlarını birbirinden ayır; geçici geometriyi kalıcı kayıt/undo geçmişine sokma.
- İlk noktadan hemen sonra çizgi mouse ile uzasın. Fib ve bölge araçlarında geçici seviyeler/dolgu görünsün; üç ve daha çok noktalı araçlarda her aşama ayrı önizlensin.
- Escape, araç/sembol/zaman dilimi değişimi, blur ve pointer iptali geçici çizimi temizlesin. Tamamlanınca tek kayıt ve tek undo adımı oluşsun.
- Kabul: ilk tıklama sonrası hareketle görünür geometri; ters yönde çizim; eksen dışına çıkış; iptal; zoom/pan sonrası doğru hizalama; dokunma ve pointer sahipliği.

### 2 — Sağ fiyat ekseni ve renkli fiyat aralığı (istek 1, 4, 5)

- Mouse fiyatı çizim öncesinde, çizilirken ve mevcut çizim üzerinde hover sırasında sağ eksende tick hassasiyetiyle görünsün. SVG hit alanı crosshair güncellemesini engellemesin.
- Mouse konumunun fiyatı ile eğimli çizginin aynı zamandaki hesaplanan fiyatını ayrı anlamlar olarak ele al; TradingView gözleminde hangisi gösteriliyorsa uygun etiketi uygula. Yatay çizgi seviyesini sabit göster.
- Seçili/oluşturulan çizimin fiyat sınırlarını kendi rengiyle eksende vurgula; fib ve kanalda gerekli seviyeleri/aralıkları araştırılan davranışa göre göster. Etiket çakışması ve eksen dışı seviyeleri yönet.
- Kabul: tick yuvarlama, hover çıkışı, seçim değişimi, zoom/pan/resize/DPR, fiyat ölçeği değişimi ve indikatör panellerinde doğru fiyat kaynağı. Desteklenmeyen log geometri için açık davranış.

### 3 — Kare hover çerçevelerini kaldırma (istek 3)

- Çizgi, metin ve not çevresindeki dekoratif kare/köşe çerçevelerini hover sırasında kaldır. Nesne ve ankraj etkileşimini uygun mouse imleciyle anlat.
- Gerçek nesne geometrisi olan dikdörtgeni veya notun içerik kutusunu dekoratif çerçeveyle karıştırma. Klavye odağının erişilebilir göstergesi korunsun; resize/ankraj hedeflerinin görünürlük ve kullanımını bu tercihle uyumlu tasarla.
- Kabul: görünmez hit alanları çalışıyor; mouse ile taşıma ve ankraj düzenleme mümkün; not metnine tıklama ve klavye odağı anlaşılır.

### 4 — Seçili çizimin yüzen düzenleme paneli (istek 2)

- Çizim tamamlandığında ve mevcut çizim seçildiğinde ekran görüntüsündeki düzende panel aç: renk, çizgi kalınlığı (px), çizgi tipi, metin/not, araç ayarları, kilit, sil ve ilgili ek seçenekler.
- Mevcut DrawingPanel alanlarını envanterle; çizim türüne uygun olanları bu panelden erişilebilir yap. Ayrıntılı ayarlar küçük popover/dialog ile açılabilir; Çizimler butonuna dönmek zorunlu olmasın.
- Panel mouse hareketinde kaçmasın, ekran dışına taşmasın, çizim seçimini düşürmesin. Kayıt bekleme/hata, kilitli çizim, çoklu seçim ve boş alana tıklama açık tanımlansın.
- Kabul: oluştur → renk/px/not düzenle → kalıcılığı doğrula → sil; yalnızca seçili nesne değişir; geri al/yeniden yap her düzenlemeyi doğru geri yükler.

### 5 — Üst undo/redo ve klavye (istek 9)

- Mevcut geçmiş altyapısını inceleyip üst çubuğa undo/redo ekle. Ctrl/Cmd+Z, Ctrl/Cmd+Shift+Z, Ctrl+Y ve seçili çizime Delete/Backspace desteği; Escape geçici işlemi iptal eder.
- Ekleme, taşıma, ankraj, stil/not düzenleme ve silme geçmiş kapsamına alınsın. Bir sürükleme tek adım; undo sonrası yeni düzenleme redo dalını temizler.
- Input/textarea/contenteditable ve modal açıkken yazı düzenleme kısayollarına müdahale etme. Kaydetme hatası veya eşzamanlı güncellemede geçmiş sunucu durumuyla tutarlı kalsın.
- Kabul: seri undo/redo, çoklu silme, kilitli nesne, başarısız kayıt, sembol değişimi ve formda Delete/Ctrl+Z.

### 6 — Channel ve pitchfork aileleri (istek 2 devamı)

- Var olan paralel kanalı yeniden eklemek yerine referansla farklarını gider. TradingView katalog araştırmasından aile kapsamını kesinleştir; paralel/flat top-bottom/disjoint/regression kanalları ile Andrews/Schiff/Modified Schiff/Inside pitchfork adaylarını araştırma listesine al. Bunlar canlı inceleme yapılana kadar doğrulanmış eksiksiz katalog değildir.
- Her araç için tıklama sırası, denklemler, dejenere noktalar, orta/yan çizgiler, seviye oranları, dolgu, uzatma ve ankraj taşıma sözleşmesini yaz. Pitchfork varyantlarının farklı başlangıç/median hesaplarını ayrı doğrula.
- ToolKind, geometri şeması, backend doğrulama/kalıcılık, migration, projeksiyon, hit test, düzenleme, ayarlar ve kural bağlama uyumluluğunu birlikte tamamla.
- Kabul: sabit sayısal örnekler + aynı ankrajlarla TradingView görsel karşılaştırması; tüm nokta aşamalarında önizleme; kaydet/yükle; zoom/pan; log ölçek politikası; undo/redo. Menüde görünmesi tek başına tamamlanma değildir.

### 7 — İndikatör görünürlüğü ve kapsamı (istek 8)

- Çalışan sürümde Göstergeler menüsünü, workspace ayar yüklemesini ve enabled durumunu incele. Kaynakta var olması kullanıcıda çalıştığını kanıtlamaz; eski build/ayar hatası/kapalı gösterge olasılıklarını gerçek çalışma kanıtıyla ayır.
- İlk kapsam mevcut sekiz türü görünür, aranabilir ve ayarlanabilir sunmak; period/source/style/pane, gizleme/silme ve şablon kalıcılığını tamamlamak. Aynı türden birden fazla örnek ihtiyacını değerlendir.
- Hesapların seed, warm-up, mum kapanışı, geçmiş kapsamı ve VWAP seans/çapa kurallarını belgeler ve örnek veriyle doğrula. Görsel sonuç ile botun kullandığı hesap aynı sözleşmeyi paylaşsın.
- Yeni adayları bot kurallarının ihtiyacına göre sırala: Stochastic, ADX/DMI, Supertrend, Donchian/Keltner, Ichimoku, OBV ve MFI. Her birinin önceliği ve veri gereksinimi ayrı kararlaştırılsın; topluca yüzlerce gösterge eklemek başlangıç kapsamı değil.
- Kabul: yükleme/yenileme sonrası ayarlar, çoklu pane yaşam döngüsü, canlı ve kapanmış mum tutarlılığı, yetersiz geçmiş mesajı, sayısal referans ve performans.

### 8 — Alarm araştırması ve bot için alarm motoru (istek 7)

- Mevcut RuleBindings, LocalEventHistory ve backend olay/rule altyapısını uçtan uca izle; mevcut yerel kural olayları ile kalıcı zamanlanmış alarmın farkını belirle. Yokluk nedeni bu inceleme yapılmadan kesin söylenemez.
- TradingView referansı: fiyat/seviye, çizgi/kanal kesişimi, indikatör koşulu; yukarı/aşağı kesme, bölgeye girme/çıkma, tek sefer/her mum/her kapanış, bitiş zamanı, durdur/devam/sil, bildirim ve geçmiş.
- Bot ihtiyacı: tarayıcı kapalıyken backend çalışması, kalıcı tanım ve tetikleme durumu, koşul sürümü/snapshot, kapanmış mum veya intrabar seçimi, yeniden başlatma/reconnect, duplicate önleme ve teslim tekrarları. Veri boşluğu/eskilik durumunda davranış açık olsun.
- Arayüz: üst Alarm düğmesi, fiyat ekseni/çizim/gösterge üzerinden alarm oluşturma; koşul düzenleyici, aktif/pasif/süresi dolmuş listesi ve tetikleme günlüğü.
- Alarm olayı ve bot emir yürütmesini açık sözleşmeyle bağla; mevcut risk doğrulaması ve idempotency korumaları yürütmede de çalışsın. Bu plan gerçek hesaba otomatik emir açmaz.
- Kabul: grafik kapalıyken tetikleme, kapanış sınırı, bir kere tetikleme, restart/reconnect, veri boşluğu, çizim değişince alarm anlamı, bildirim hatası ve aynı olayın iki emre dönüşmemesi.

## Her aşamanın tamamlanma kapısı

Kaynak değişikliği + ilgili anlamlı testler/TypeScript/build + gerçek tarayıcı kabulü + ekran/olay kanıtı + açık kalanların kaydı. Araştırma, uygulama ve doğrulama durumları ayrı tutulur. Önceki denetimin G01–G07 açık maddeleri uygun aşamalara taşınır; kanıt olmadan kapatılmaz.

## Başlangıç kaynakları

- https://www.tradingview.com/support/solutions/43000703396-drawing-tools-available-on-tradingview/ — araç kataloğu.
- https://www.tradingview.com/support/solutions/43000518117-parallel-channel/ — paralel kanal.
- https://www.tradingview.com/support/solutions/43000518141-pitchfork-drawing-tool/ — pitchfork.
- https://www.tradingview.com/support/solutions/43000791609-modified-schiff-pitchfork-drawing-tool/ — modified Schiff.
- https://www.tradingview.com/support/solutions/43000763315-getting-started-with-technical-alerts/ — teknik alarmlar.
- https://www.tradingview.com/support/solutions/43000595315-how-to-set-up-alerts/ — alarm ayarları.
- https://www.tradingview.com/support/solutions/43000548327-will-alerts-work-if-tradingview-is-not-open-on-the-computer/ — sunucuda çalışan alarm davranışı.

Bu kaynaklar başlangıç referansıdır; canlı REA etkileşim incelemesinin yerine geçmez. Bu tur uygulama kodu değiştirilmedi.


## 13 Kasım — REA bağlantısı kuruldu

Kullanıcı indikatörlerin mevcut olduğunu doğruladı; yokluk teşhisi kapsamdan çıktı. Araştırma Chrome profili tools/rea/research-visible üzerinden localhost:9338 CDP bağlantısı kuruldu. REA, REA Araştırma layoutunu doğruladı: https://www.tradingview.com/chart/E7UZkcrO/ . Hedef Chrome157, CME BTC1! haftalık görünüm; piyasa değiştirilmedi.

REA Trend tools senaryosu: ev_49b32a2ea917a8dd3105475d68af40c124d486d6e7f5a8174c1d6ad286edfcbc. Canlı katalog: Parallel channel, Regression trend, Flat top/bottom, Disjoint channel; Pitchfork, Schiff pitchfork, Modified Schiff pitchfork, Inside pitchfork. Menü gözlemi geometri/yerleştirme kabulü değildir. Sonraki iş önizleme, tıklama aşamaları ve yüzen panel davranışı. Kanıt: reports/rea-chart/drawing-tools-menu-20261113.json.


## 13 Kasım — ilk uygulama grubu teslimi

Durum: ilk çizim etkileşim grubu uygulandı ve yerel grafik varlıklarına derlendi. Tüm plan tamamlanmadı.

- Aşama 0: trend ilk/ikinci nokta, hareketli önizleme, sağ eksen etiketleri ve yüzen panel canlı REA ekranlarıyla gözlendi. Kanal/pitchfork ailelerinin ayrıntılı araştırması açık.
- Aşama 1: mevcut araçlar için geçici önizleme katmanı; trend/fib/bölge/kanalda gerçek tarayıcı kabulü geçti. Geçici çizim kaydedilmiyor. Yeni pitchfork araçları bu teslimde yok.
- Aşama 2: mouse fiyatı SVG hover dahil görünür; seçili/hover/oluşturulan çizimin renkli fiyat bandı ve uç etiketleri var; sürükleme bandı canlı güncelleniyor. Karmaşık etiket çakışmalarının TradingView ile bire bir eşitliği ve tüm ölçek/DPR kombinasyonları açık.
- Aşama 3: nesne etrafındaki dikdörtgen odak çerçevesi ve görünür ankraj işaretleri kaldırıldı; hit hedefleri/imleç ve klavye odak çizgi vurgusu korundu.
- Aşama 4: yüzen çubuk renk/px/stil/kilit/silme ve mevcut tüm ayrıntılı ayarlara erişim sunuyor. Not/metin ayarı buradan yapılabiliyor; Çizimler panelini açmak gerekmiyor. Çubuğun taşınması ve TradingView panelindeki alarm işlemi bu teslimde uygulanmadı.
- Aşama 5: üst undo/redo, Ctrl/Cmd+Z, Ctrl/Cmd+Shift+Z, Ctrl+Y ve Delete/Backspace. Metin alanları/modal dışlanır; kilitli çizim silinmez. Undo geçmişi mevcut oturum kapsamını korur.
- Aşama 6: yeni kanal ve pitchfork aileleri bekliyor.
- Aşama 7: kullanıcı indikatörlerin mevcut olduğunu doğruladı; yeni gösterge kapsamı ihtiyaç değerlendirmesi olarak kalır.
- Aşama 8: kalıcı alarm motoru ve bot bağlantısı bekliyor.

Doğrulama: 284 frontend testi; TypeScript; Vite üretim derlemesi; çizim API/depo/yönetim için32 Python testi; derlenmiş localhost:8765 sürümünde13 izole Chrome etkileşim kabulü geçti. Tarayıcı testleri mocked API ile yapıldı, kişisel çizim depolarına yazılmadı. Gerçek dokunmatik cihaz kabulü değildir. Son bundle index-Bpnp9h04.js.

Teslim raporu: docs/chart/DRAWING-INTERACTION-01-DELIVERY.md. Sonraki iş yeni kanal/pitchfork ailelerinin nokta sırası ve geometrisini REA ile araştırmak; ardından bağımsız geometri/kalıcılık/araç entegrasyonu.


### Kullanıcı düzeltmesi — yüzen çubuk ve uç noktaları

Çubuk sürükleme tamamlandı: soldaki noktalı tutamaktan taşıma, grafik sınırları/resize koruması ve ok tuşları. Seçili çizim ve önizlemede dairesel ankrajlar görünür; kare çerçeve yok. Önceki görünür tüm ankraj işaretlerini kaldırma kararı bu kullanıcı isteğiyle düzeltildi.


## 13 Kasım — kanal/pitchfork uygulama ve doğrulama

Sekiz araç uygulandı: paralel, flat, disjoint, regression ve dört pitchfork varyantı. Aşamalı önizleme, türetilmiş köşe düzenleme, ayarlar, metin/fiyat etiketleri, dairesel tutamaç, undo ve kalıcılık doğrulandı. 295 frontend, 926 backend testi; izole replay36/36; TypeScript ve üretim derlemesi geçti. Yerel sunucu format9 ile yenilendi.

Aşama6 temel araç kapsamı teslim edildi; tam TradingView parity kapısı kapatılmadı: regression sayısal karşılaştırma, seviye bazında bağımsız stil, log ölçek ve fiziksel cihaz kabulü açık. Yeni aileler bot hesaplarına bağlanmaz. Ayrıntılı teslim: docs/chart/CHANNEL-FAMILY-DELIVERY.md; araştırma: docs/chart/REA-CHANNEL-FAMILY-GEOMETRY.md. Sonraki ana iş alarm araştırmasıdır.


### Kullanıcı kabul kapısı — bu aşama tamamlanmadan ilerleme yok

Kanal/pitchfork aşaması AKTİF; alarm araştırmasına geçilmez. Önceki temel teslim tam kabul değildir. Ek canlı sayısal deneyde regression N−1 sapma paydası ve ters Pearson işareti bulundu/düzeltildi; yedi kaynak ve sapmasız bant gerçek çıktıları test fixture oldu. Bağımsız seviye/çizgi renk, px ve stil ayarları eklendi.297 frontend ve927 backend testi geçti. Log ölçek, canlı veri/sınır durumları ve fiziksel cihaz kabulündeki açıklar kapatılmadan aşama tamamlandı denmez.


### Log ve sınır durumu kontrolleri

Yeni ailelerde native ekran ekseninde LOG geometri, ilk-nokta önizlemesi, yüzen panel ve tutamaç düzenlemesi eklendi. Eski paralel kanalın kısıtları korundu.302 frontend,927 backend,36/36 replay geçti. LINEAR/DPR1,LOG/DPR1,LOG/DPR2 gerçek Chrome kontrollerinde sekiz araç ve zoom/pan/reload kabulü geçti. Regression iki mum, ters sıra, sabit veri, açık mum güncellemesi, eksik geçmiş ve geçersiz sayısal veri davranışları test edildi. Tam TradingView görsel eşitliği/fiziksel cihaz kabulü açık; kullanıcı koşulu gereği alarm aşamasına geçilmedi.


## Son masaüstü kabulü ve alarm araştırması

Kanal/pitchfork ana masaüstü kapsamı, ek gerçek canvas ölçümleriyle doğrulandı: dört pitchfork ve üç kanalın iki ölçekte14 örneği0,001 CSS px içinde eşleşti. Regression gerçek sayısal fixtureları,304 frontend,927 backend,36/36 replay ve LINEAR/LOG/DPR2 Chrome kabulü mevcut. Genel fiziksel dokunmatik ve tam raster/özellik parity işleri ayrı QA kapsamıdır; istenmeyen yeni bir engel olarak kullanılmaz.

Aktif adım: TradingView alarm araştırması. Menü kataloğunun ötesinde, bildirimleri kapalı tek araştırma alarmı oluşturuldu; açık kullanıcı onayıyla duraklat/devam/düzenle/yeniden yükle/sil akışları ve sunucu yanıtları gözlendi. Test nesnesi silindi ve temiz durum reload ile doğrulandı. Gösterge çıktısı/operand/periyot, frekans farklılıkları, bildirim takvimi, mesaj değişkenleri ve çoklu koşul plan kapısı incelendi. Gerçek koşul tetiklenmesi ve arka plan çalışması bu deneyde doğrulanmadı. Ayrıntılar docs/chart/REA-ALERTS-RESEARCH.md; kanıt özeti reports/rea-alerts-20261113/summary.json. Alarm motoru kodu/canlı bot bağlantısı henüz eklenmedi.


## Alarm ilk uygulama grubu — görünür ekran ve kalıcı fiyat motoru

Üst çubuğa Alarm düğmesi, oluştur/düzenle/duraklat/devam/sil, filtreler ve tetikleme geçmişi eklendi. Backend tarayıcıdan bağımsız feed referansı tutarak kapanmış mum fiyatını izler; kayıtlar ve dedup checkpointi kalıcıdır. Sabit fiyat koşulları, once/her uygun kapanış ve bitiş zamanı mevcut. Yerel sunucu güncellendi.304 frontend, tam934 backend ve son eklenen gerçek arka plan thread senaryosu dahil hedefli8 alarm testi geçti; Chrome kabulü tamam. Teslim docs/chart/ALARMS-01-DELIVERY.md.

Alarm aşaması bütünü AKTİF: gösterge/çizim koşulları, intrabar/dakika profilleri, bildirim kanalları/takvimi ve bot köprüsü açık. Bu teslim tam TradingView alarm eşitliği değildir. Gerçek piyasa tetikleme/uzun kesinti kabulü ayrıca gerekir.


## Alarm paneli ve çoklu koşul teslimi

TradingView referanslı kompakt editör: Ayarlar/Mesaj, numaralı koşullar, VE/VEYA, süre önayarları, ayrı liste/geçmiş, sabit eylem çubuğu. En fazla8 koşul ve17 operatör motoruyla birlikte eklendi. Fiyat/OHLC türevleri/hacim; mevcut gösterge örnekleri ve çıktıları; canonical hesap sözleşmesi olan çizim snapshotları kullanılabilir. Gösterge ayarları alarmda donmuş kalır; yeterli geçmiş/kapsam yoksa WAITING_CALCULATION. Eski fiyat alarmları korunur.

Birincil internet araştırması ve matematik: docs/chart/ALARM-CONDITIONS-RESEARCH-AND-DELIVERY.md.950 backend,306 frontend, TypeScript/build ve8 Chrome kabul grubu geçti. Koyu/açık tema ve600px görselleri incelendi. Son bundle index-Cz97NEZV.js, yerel sunucu güncellendi; GET /api/alerts runtime_error=null/order_authority=false. Testler kullanıcı çalışma alanına yazmadı.

Aktif alarm planındaki kalanlar: karışık periyot hizalama, intrabar/dakika profilleri, bildirim kanalları/takvimi ve mesaj değişkenleri, DISPLAY_ONLY aileler için ayrı kanıtlı hesap sözleşmesi, gerçek piyasa uzun kesinti kabulü ve bot köprüsü. Bu teslim gösterilmeyen yetkileri etkinleştirmez.


## Alarm follow-ups — 2026-11-13

Multi-timeframe conditions delivered: docs/chart/ALARM-MULTI-TIMEFRAME-DELIVERY.md.

Browser notification delivery delivered: application cards and unread count, browser-wide sound/desktop preferences, permission and audio activation, persisted receipt dedup with Web Locks, and visible failure states. Full frontend311; backend alarm29;11 notification browser acceptance groups plus existing condition acceptance passed. Production index-D2PRm3DF.js verified at localhost8765. Details and limitations: docs/chart/ALARM-NOTIFICATIONS-DELIVERY.md.

Alarm stage remains active for intrabar/frequency profiles, per-alarm notification schedule, closed-browser external delivery and bot integration. Browser notification preferences in this delivery are global to the browser and require an open application tab.


## Alarm sampled-live frequency delivery — 2026-11-13

REA price/BB frequency menus observed and editor draft dismissed without creating an alarm. Separate evaluation timing selector added: confirmed close retains legacy behavior; sampled intrabar supports once, once per base candle and rolling60second limit. V4 contract, atomic event/checkpoint, restart-persistent suppression, as-of confirmed higher timeframes and forming indicator evaluation implemented. This samples latest feed about once per second; it is not every exchange tick or proven TradingView server parity.

Final13 targeted live tests,967 full backend regression (before two added targeted tests),312 frontend,36/36 chart evidence checks,7 new plus11 existing browser groups passed. Local production index-DnWt9qhF.js. Details: docs/chart/ALARM-FREQUENCIES-DELIVERY.md.

Remaining alarm work: notification schedule/time zone, per-alarm delivery options, closed-browser external delivery and bot integration.


## Per-alert notification schedule — 2026-11-13

Delivered:24/7, weekday/workday/custom windows, IANA timezone, overnight/start-day ownership, DST handling, permanent per-event mute decision, muted history and smart single-use lifecycle. Separate Takvim editor tab and manager summary added. Monitoring remains active; muted events do not produce browser cards, sound, desktop or unread badge and never replay later. Existing alert schemas remain readable; schedule is a versioned optional field.

REA draft custom night range observed, discarded without creating/applying an alarm; original24/7 default verified retained. Full978 backend /315 frontend tests;8 calendar,7 frequency,11 notification browser groups passed. Production index-D4BFG9TI.js verified. Details: docs/chart/ALARM-SCHEDULE-DELIVERY.md.

Next agreed step: per-alarm channel preferences (current sound/desktop preferences are browser-wide). Bot integration remains after that.


## Per-alert channel preferences — 2026-11-13

Delivered: Kanallar editor tab, inheritance or independent card/sound/desktop selection, history-only mode, strict optional policy on all alert definition versions, immutable event-policy snapshots, and independent batch filtering for each delivery channel. Recorded schedule decision and current browser master preferences/permissions remain upper bounds. Older alarms retain inheritance.

981 backend /319 frontend tests passed;7 channel and8 calendar Chrome acceptance groups passed. Production index-D8UGb9zW.js verified. Detailed delivery and limitations: docs/chart/ALARM-CHANNELS-DELIVERY.md.

Next agreed phase: bot rule-system integration in no-order test mode, with event dedup and lifecycle controls.
