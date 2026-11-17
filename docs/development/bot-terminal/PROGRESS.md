# Bot terminali ilerlemesi

17 Kasım 2026. [Plan](PLAN.md) · [Araştırma ve yetenek matrisi](RESEARCH.md).

| Aşama | Durum |
|---|---|
| Kaynak incelemesi ve ilk yetenek matrisi | İlk teslim tamamlandı; ayrıntılı ekran sözleşmeleri devam edecek |
| Tıklanabilir prototip | İlk sürüm eklendi; görsel kullanıcı değerlendirmesi bekliyor |
| Finansal servis entegrasyonu | Yerel Demo API/worker ve bağlı frontend uygulandı; dış borsa kabulü NOT_RUN |
| Uzaktan erişim / müşteri yayını | Başlamadı |

## Yerel Demo entegrasyonu teslimi — 17 Kasım 2026

Çalıştırma, kullanıcı akışı ve kurtarma ayrıntıları: [INTEGRATION.md](INTEGRATION.md).

- Varsayılan Bot ekranı bağlı Demo modudur. Sentetik prototip yalnız `mode=preview` ile açılır. API/worker yapılandırılmadığında örnek hesap verisi gösterilmez.
- Kimlik doğrulamalı, kalıcı `/api/bot` iş kuyruğu eklendi. HTTP katmanı borsa anahtarını yüklemez veya finansal isteği doğrudan göndermez. Finansal işler mevcut motorlara ayrı worker üzerinden devredilir.
- SINGLE/GRID/NEUTRAL taslağı, grafik revizyon kontrolü, authoritative preflight, 60 saniyelik inceleme, tek kullanımlık açık onay ve mevcut risk/rezerv/journal yürütmesi bağlandı. Sunucu profili tarayıcıdan değiştirilemez.
- Hesap/pozisyonlar, normal ve algo emirler, bot oturumları, planlar, borsa komutları, sonuç uzlaştırma, mevcut yönetim işlemleri ve yerel geri bildirim bağlı modda sunulur.
- Plan taslağı yetkisiz kaydedilebilir. Toplu girişte her plan önce ayrı, yalnız yetkilendirme onayı alır; sonra toplu komut ayrıca incelenir/onaylanır. Ters yön taslağı aktif hesapta kayıt edilebilir ve mevcut ters yön komutu kendi preflight/yetki zincirini uygular.
- Worker salt okunur başlar; Demo yürütmesi açık `--execute-demo` gerektirir. OS tek yürütücü kilidi, yeniden başlatmada RUNNING → NEEDS_REVIEW, gönderim belirsizliğinde yeniden POST yapmama ve kalıcı oturum izleme durdurması korunur. Timer kiraları yeniden başlatmada otomatik devralınmaz.
- Eski/bağlamı doğrulanmamış işlem günlüğü yeniden etiketlenmez. Yerel ve müşteri veritabanları ayrı tutulabilir; yerel geliştirme korunur.
- Frontend: **393 test geçti**, 0 hata/skip. Son üretim derlemesi başarılı; mevcut ~749 kB ana grafik bundle uyarısı sürüyor. Bot bağlı mod ayrı ~30 kB chunk olarak yüklenir.
- Hedefli backend: **22 test geçti**. Mevcut pozisyon komutları paketinde **28 test geçti**. Son tam Python regresyonu: **1.671 test geçti**, 0 hata/skip. Aralıklı hedge fixture senaryosu ayrıca 35 kez üst üste geçti. API/ayar kaynakları değiştiği için binding manifesti üreticisiyle ve 36 ağsız replay senaryosuyla kanıtlar yenilendi; güvenlik denetimi gevşetilmedi.
- Tarayıcı erişim ağacında yerel erişim ekranı ve örnek bakiye bulunmaması görüldü. Desteklenen tarayıcı açılışı tekrar `The browser access host is unavailable` ile engellendi. Yeni bağlı modun tam fiziksel tarayıcı etkileşim/scroll/mobil kabulü açık; React testleri bu kabul olarak gösterilmez.
- Plan adaptöründe tarih dönüşümünün mikrosaniyeye yukarı yuvarlanarak sabit Windows saatinde gelecekte oluşturulma zamanı üretmesi düzeltildi; deterministik regresyon testi eklendi.
- Genel koşuda bulunan aralıklı hedge/ters yön test hatası, senkron sahte borsada eski kapanış ve yeni oturumun aynı milisaniyeye düşmesinden kaynaklandı. Testte yeni oturum başlangıcı eski dolum zamanından ayrıldı; üretimin yabancı geçmiş/belirsizlik reddi değiştirilmedi.
- Gerçek Binance Demo emri gönderilmedi; `NOT_RUN`. Müşteri ortamına yayın yapılmadı. Bu belgede önceki prototip bölümleri tarihsel kayıttır.

## Geniş frontend turu

### Tasarım revizyonu ve tarayıcı doğrulaması

Kullanıcı geri bildirimi üzerine Bot tasarımı grafik terminalinin tema değişkenleriyle yeniden düzenlendi. Büyük başlık ve her sekmede görünen işlem paneli kaldırıldı; ayrı Yeni işlem görünümü, kapalı gelişmiş ayarlar, dengeli boşluklar ve masaüstü/dar ekran kaydırma düzeni eklendi. Chrome'da sekme geçişleri, aşağı kaydırma, önizleme, modal/Escape, yaklaşık 396 px dar görünüm ve açık/koyu tema doğrudan kontrol edildi. Önceki tarayıcı erişim engeli bu turda aşılmıştır; geçmiş kayıtlar aşağıda tarihsel olarak korunur.

Son kontrol **387 frontend testi / 0 hata / 0 skip** ve başarılı üretim derlemesidir. Gizli grafik UI yayını da durduruldu. Ayrıntılar ve kalan ağ/finansal sınırlar: [DESIGN-REVIEW.md](DESIGN-REVIEW.md).

Kullanıcının tek turda arayüzleri birleştirme isteğiyle [UI-DELIVERY.md](UI-DELIVERY.md) teslimi hazırlandı. SINGLE çoklu hedef/risk/yerel trailing, GRID/NEUTRAL, ayrıntılı pozisyon ve native trailing yaşam döngüsü, emir filtre/değiştir/iptal, batch, hesap/timer/sorgu, kalıcı yerel geri bildirim ve grafik revizyonlu aktarım aynı uygulamaya bağlandı.

Grafik durumu ve Bot sekme durumu görünüm geçişlerinde korunur. Bot sayfası ve modallar kaydırılır; grafik ana alanı gezinme çubuğunun kalan yüksekliğine oturur. Açık/koyu tema ve mobil kuralları eklendi. Bot ayrı lazy modüle ayrıldı (51,54 kB; gzip 14,06 kB). Doğrudan yerel bağlantı: `http://127.0.0.1:5173/?view=bot`.

Doğrulama: **386 frontend testi / 0 hata / 0 skip**; TypeScript/üretim build ve diff biçim kontrolü geçti. React DOM etkileşim testi ağsız prototip onayı, eski önizleme geçersizliği, yerel kayıt ve modal yaşam döngüsünü kapsar. Gerçek tarayıcı görsel kabulü ve finansal backend bağlantısı tamamlanmadı. Eski aşağıdaki adımlar tarihsel ilerleme olarak korunur; güncel kapsam ve sınırlarda UI-DELIVERY.md esas alınır.

## İlk prototip

- Aynı uygulamada Grafik/Bot geçişi ve grafik üzerinde işlem paneli.
- Üst App durumunda tutulan işlem taslağı; mevcut grafik bileşeni görünüm geçişinde kaldırılmaz.
- SINGLE Limit taslağı, yön ve sayı kontrolü, değişiklikte eski önizlemenin kaldırılması, yalnız prototip onayı.
- Sentetik aktif/boş hesap, kısmi dolum, belirsiz sonuç, ret ve bağlantı kesintisi senaryoları.
- Örnek pozisyon/emir listesi, eylem etkileri, gelişmiş yetenek açıklamaları.
- Prototip finansal ağ çağrısı yapmaz. Sunucu, worker, giriş ve borsa ayarları değiştirilmedi.

## Yerelde açma

Mevcut grafik API'si için kökte `python -m agentrader web serve`; frontend klasöründe `npm run dev`. Mevcut grafiğin üstündeki Bot veya İşlem paneli düğmesini kullanın. Bot örnekleri gerçek borsa verisi gerektirmez; grafiğin veri erişimi mevcut kurallarına tabidir.

## Açık işler

Görsel tarayıcı kabulü, tam GRID/NEUTRAL ve gelişmiş işlem formları, çizim fiyat/revizyon aktarımı, kalıcı komut/geri bildirim, gerçek API ve worker entegrasyonu bekliyor. Bu teslim müşteri yayını veya Demo borsa kabulü değildir.

## İkinci prototip adımı

- GRID: alt/üst bant, 2–100 aralık, aritmetik/geometrik dağılım, referans, stop/son hedef ve NOTIONAL/MARGIN/MAX_LOSS bütçesi eklendi.
- NEUTRAL: 2–20 aralık, iç seviye merkez kontrolü, iki global stop ve tamamlayıcı LONG/SHORT payları eklendi. Yön ve tek hedef yerine neutral özeti gösterilir. Hedge gereksinimi açıklanır; hesap modu değiştirilmez.
- SINGLE Limit: GTC/IOC/FOK/GTX/GTD, uyumlu EXPIRE STP seçimleri ve GTD yerel son geçerlilik alanı eklendi. FOK/GTX seçimi önceki STP değerini temizler. Önizleme seçenekleri gösterir; değişiklik eski özeti kaldırır.
- GRID/NEUTRAL özeti, SINGLE miktar alanı yerine gerçek grid bütçesini ve sınırlarını gösterir. Bu hâlâ tarayıcı taslağıdır; yürütülebilir plan değildir.
- Doğrulama: 368 frontend testi geçti; TypeScript ve üretim derlemesi başarılı. İlk derlemedeki JSX kapanış hatası düzeltildi. Bundle boyut uyarısı sürüyor.
- Sınır: sayı hesabı prototip içindir. Backend Decimal/tick/lot/risk ve güncel borsa kontrolleri uygulanmış sayılmaz. Grid kaldıraç, marjin, koşullu başlatma ve döngü yönetim alanları; SINGLE Market/priceMatch ve pozisyon düzenleyicileri bekliyor.
- Tarayıcı görsel kabulü önceki araç engeli nedeniyle hâlâ açık. Bu adımda tarayıcı testi yapılmadı; backend/worker değiştirilmedi.

## Doğrulama

### Beşinci prototip adımı: kaydırma ve pozisyon yönetimi

- Bot sayfası, grafik kabuğunun `height:100dvh;overflow:hidden` kuralı altında taşarak kırpılıyordu. Bot ana görünümüne `flex:1 1 0;min-height:0;overflow-y:auto` eklendi; üst gezinme küçülmez. Grafik ve grafik yan panelinin mevcut kaydırma düzeni korunur.
- Artır/Azalt/Kapat/Tersine çevir/Trailing için eski genel metin kutusu yerine mevcut `useModalDialog` altyapılı, Escape/kapatma ve odağa dönüş destekli ayrı form eklendi. Uzun modal içerikleri de dikey kaydırılır.
- Artırma miktar/fiyat aralığı, azaltma yüzde/miktar, native trailing miktar/aktivasyon/callback/fiyat kaynağı ve reversal karşı plan kimlik/sürüm/digest alanları içerir. Düzenleme eski önizlemeyi düşürür; onay yalnız örnek günlüğe açıklama yazar.
- Doğrulama örnek Long 0,01 BTC, stop 88.000, hedef 94.000 bağlamındadır. Taze hesap, risk profili, gerçek plan varlığı/sahipliği, borsa filtreleri ve yürütme teyidi henüz bağlı değildir.
- 378 frontend testi geçti; TypeScript ve üretim derlemesi başarılı. Bundle uyarısı sürüyor. Tarayıcıda gerçek kaydırma/görsel kontrolü yapılmadı; CSS kök neden düzeltmesi ve otomatik kontroller görsel kabul yerine geçmez.
- Yerel API/worker ve borsa yapılandırmaları değiştirilmedi. Sırada toplu emir düzenleyicileri, çizim aktarımı, kalıcı geri bildirim ve backend entegrasyonu var.

### Dördüncü prototip adımı: Market ve priceMatch

- SINGLE için Market/Limit seçimi ve sekiz mevcut priceMatch yöntemi eklendi. Market ve priceMatch seçildiğinde fiyat alanı risk referansı olarak adlandırılır; dolum/sabit fiyat garantisi verilmez.
- Market veya GRID/NEUTRAL'e geçiş Limit seçeneklerini taslaktan kaldırır. Limit'e dönmek eski GTD/STP/priceMatch değerlerini geri getirmez. Tür geçişleri ortak `updateBotDraft` fonksiyonunda uygulanır.
- Onay özeti ayrı bileşene taşındı. Market'te süre/STP gösterilmez; priceMatch'te sabit fiyat gönderilmeyeceği ve seçilen yöntem açıklanır.
- 374 frontend testi geçti, 0 hata/skip. Yeni testler tür geçişlerinde seçenek temizliğini, sekiz yöntemde risk referansını ve gerçek render edilen özet metinlerini kapsar. TypeScript/üretim derlemesi ve diff biçim kontrolü geçti. Bundle uyarısı sürüyor.
- Bu adım borsa isteği veya yürütülebilir plan üretmez. SINGLE miktar alanının gerçek plan bütçesine dönüşümü entegrasyon öncesinde netleştirilecek; sayısal taslak kontrolü backend preflight yerine geçmez.
- Sıradaki işler: ayrıntılı pozisyon yönetimi, batch düzenleyicileri, çizim aktarımı, kalıcı geri bildirim ve API/worker bağlantısı. Görsel tarayıcı kabulü açık; önceki tarayıcı erişim engeli bu adımda yeniden denenmedi.

### Üçüncü prototip adımı: hesap ve başlatma

- Kaldıraç, ISOLATED/CROSSED marjin, one-way/hedge pozisyon modu ve 0–100 bps (sıfır hariç) sapma toleransı eklendi. Varsayılanlar örnek taslak değerleridir; hesap gözlemi değildir.
- GRID/NEUTRAL için IMMEDIATE, MARK_AT_OR_BELOW ve MARK_AT_OR_ABOVE başlatmaları, koşula bağlı tetik alanı ve stop sınırı kontrolleri eklendi.
- NEUTRAL türüne geçiş taslağı hedge moduna alır; gerçek hesap modu değiştirilmez. SINGLE'a dönüş koşulu IMMEDIATE yapar; bu ekrandaki SINGLE hâlâ Limit prototipidir.
- Onay özetine kaldıraç, marjin, hesap modu, sapma ve grid başlatma koşulu eklendi. Alan değişikliği eski önizlemeyi düşürür.
- 370 frontend testi geçti, 0 hata/skip. TypeScript ve üretim derlemesi başarılı; bundle boyut uyarısı sürüyor. `git diff --check` geçti (CRLF bilgilendirmesi var).
- Finansal servis, worker ve yerel çalıştırma yapılandırması değişmedi. Görsel kabul hâlâ açık. Market/priceMatch, ayrıntılı pozisyon/batch yönetimi, çizim aktarımı ve API entegrasyonu bekliyor. Grid döngü izni yalnız açıklanır; taslak yetki üretmez.

### İlk prototip doğrulaması

- `npm test`: 365 test geçti, 0 hata, 0 skip. Üç yeni test; hatalı miktar/fiyat, yönle uyumsuz stop/hedef ve GRID/NEUTRAL'in SINGLE onayını kullanamamasını kapsar.
- `npm run build`: TypeScript ve Vite üretim derlemesi başarılı. 500 kB üstü bundle uyarısı var; derleme hatası değildir.
- Backend değişmedi; Python regresyonları bu teslimde çalıştırılmadı.
- Tarayıcıda görsel ve tam etkileşim kabulü yapılmadı; test sonuçları bu kabulün yerine geçmez.
