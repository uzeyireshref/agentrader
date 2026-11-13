# Canlı araştırma: odak, ayar kapanışları ve dar pencere düzeni

11 Kasım2026, Asia/Baku. REA03 eki. Hesaplı araştırma düzenindeki geçici testler ile girişsiz geçici tarayıcı viewport deneyleri ayrı tutulur. Bu tur ürün kodu değiştirilmedi.

Kanıt paketi reports/rea-chart/rea-evidence-focus-responsive-20261111.json:234 kayıt/80,490,167 byte. Önceki turlar ve başarısız denemeler dahildir. Paket büyüklüğü kapsam kabulü veya test sayısı değildir.

## Uygulanmış deneyler

| ID | İşlem ve sonuç | REA kanıtı |
| --- | --- | --- |
| F10 | Fib ve Short geçici kopyaları oluşturuldu, ayrı ad verildi; Short kopyası tek üyeli gruba alındı | ev_4a5e073c1c13027a9ef003ffa25ba3a8681260b28ca27fdc2af2c67adb8a2aad |
| F11 | Fib kopyası seçildiğinde Move to disabled; çok üyeli gruba taşıma doğrulanmadı | ev_add59094d29bb0df17c1ecd3baddebe7ff947d10f692a9159cf4aa9f532ed25c |
| F12 | Grup üzerinde Create group iç içe grup abonelik ekranı açtı; Basic plan sınırı | ev_4cfaacb0707f0f258ecebfb2d41badc7f5a461d8c65117b7cd510f703d09a6a6 |
| F13 | Yükseltme ekranı kapatıldı; geçici grup/Short kopyası ve ayrı Fib kopyası silindi; dört orijinal çizim korundu/global gizlendi | ev_c338ad16ae3fc7ec619dc2d707ad217a0eb297022a88c6bf5f6c11b4d04004d9 |
| F14 | Go to tarih alanında a,/,virgül tuşları; global symbol/indicator/interval dialogu açılmadı. Maskeli tarih alanı önceki geçerli tarihini korudu; Escape dialogu kapattı | ev_b50eaf4b151d70c2d59cec469163bd9edfcd9f807defe1a32c6d097984ea8d8b |
| F15 | BB Length20 alanında30 yazıldı, ArrowUp31 yaptı; grafik önizleme31'e geçti.0+Tab son geçerli31'e geri döndü. Cancel20'ye ve önceki Undo etiketine döndürdü | ev_125972f7d3f9b601d85f726e1093191c837a59b333354289a9f311c03084764b |
| F16 | BB20→25+Tab; Escape dialogu kapattı fakat25 korundu | ev_ac7a3d9f62d42194a194797e6d746ccc7106118b181fd88c088628e65b959116 |
| F17 | Ayrı kontrol:25→26+Tab; X/Close menu sonrası26 korundu. Ardından20+Ok ile açıkça geri getirildi | ev_58d8139d3c08361585958ca3507b6daec56e83a207fa156888753d324112f3cd |
| F18 | Bağlı pencerede1280 viewport isteği: PNG1920×970 kaldı.768 isteği sırasında alınan DOM/CSS ölçümü1536×776. Gerçek dar viewport kabulü verilmedi | ev_9869c6a43facb8f03276b5e5f1a3b3c68b9ec3a0aa0cb65a5ca57435fa611278; ev_7467a570478d48f9876f460d9aaa813447239e9ed4663b14ba380c4bea5b4cd9 |
| F19 | Ayrı, girişsiz, REA-owned geçici tarayıcı:1024×768/DPR1; gerçek1024×768 görüntü | ev_559b08cf4517ed50f35a7cd2199eae831b09bb192e63cdd4e6a1ab497fdede83 |
| F20 | Aynı bağımsız yol:768×900/DPR1; yan panel açık/kapalı ve Canvas dialog görüntüleri | ev_17d408f2020e82f4083279a12b93d325cb22555a62066a435ae8bacbcff49d7a |
| F21 | Aynı bağımsız yol:1280×720/DPR1; yan panel açık/kapalı ve Canvas dialog görüntüleri | ev_112fa6c307c4e7d3cffe5d5611c675d9911ccf0c568fb54287269fd166448f8e |
| F22 | Hesaplı düzende son kontrol: BB20/SMA/close/2, geçici nesneler yok, orijinal dört çizim gizli, UTC ve saved durumu | ev_ee01f601bea0a7bbf70a13956733f48372e4bff1fc5026b75dbc7b195a4a9068 |

## Çoklu seçim ve grup sınırı

REA6.8.0 senaryo click eylemi button/click_count destekliyor; modifier+click/drag desteklemiyor. Press tek bir tuş birleşimini gönderir; ayrı bir click boyunca Ctrl basılı tutma eylemi değildir. Bu tur Ctrl+click yapılmış gibi raporlanmadı. Move to kontrolünün disabled olması gözlendi; bunun bütün platform/hesaplarda grup taşıma desteklenmez anlamına geldiği çıkarılmadı.

İç içe grup denemesi açık plan yükseltme mesajıyla durdu. Yükseltme veya hesap değiştirme yapılmadı. Dolayısıyla çok üyeli/karışık kilitli grup ve nested inheritance açık kalıyor. Geçici grupta yalnız Short kopyası vardı; grup silindiğinde orijinal Short korunmuştur. Fib kopyası ayrıca silindi. Bu kayıt, önceki tek üyeli grup bulgularını geniş çoklu seçim kabulüne dönüştürmez.

## Odak ve sayısal alan

Go to tarih alanında harf,slash ve virgül normal chart arama kısayollarına kaçmadı. Girdi maskesi geçersiz karakterleri kabul etmedi; metnin harf olarak saklanması doğrulanmadı. Tarih alanı bütün düz metin editörlerinin temsilcisi değildir. Contenteditable/metin çizimi, clipboard, IME ve ekran okuyucu negatif akışları açık.

BB numeric inputta ArrowUp alan değerini30→31 yaptı. Chart intervali1D kaldı.0 girilip Tab ile blur edilince min1'e clamp yerine son geçerli31 görüldü; bu yalnız bu alan/akış örneğidir. Geçersiz değerin helper/error/aria bildirimi ayrıca incelenmeli.

Ayarlar canlı önizleme yapıyor: Length31 olduğunda dialog kapanmadan legend ve nesne ağacı31 oldu, Undo etiketi change Length property oldu. Cancel sonrasında20 ve önceki Undo remove Fib retracement etiketi geri geldi. Böylece önizleme ile kaydı kesinleştirme ayrımı somut olarak gözlendi.

## Cancel, Escape ve X aynı davranış değildir

| Yol | Önceki değer | Önizleme | Pencere kapandıktan sonra |
| --- | --- | --- | --- |
| Cancel |20 |31 |20 |
| Escape |20 |25 |25 |
| X/Close menu, ayrı değişiklik |25 |26 |26 |
| Ok ile geri yükleme |26 |20 |20 |

İlk X denemesi zaten25 olan değere25 verdiği için tek başına X semantiğinin kanıtı sayılmadı. Ayrı25→26 denemesi bu belirsizliği giderdi. Bu davranışlar BB Inputs örneğine aittir; tüm çizim/ayar dialoglarına genellenmez.

Bizim üründe Escape'in her zaman Cancel mı yoksa Close mu olduğu açık ürün kararı olmalı. Canlı önizleme varsa Cancel geri alma snapshot'ı, dirty durumu, undo gruplaması ve kapatma yolu bağımsız tanımlanmalı. Referansın kullanıcıyı şaşırtabilecek ayrımı zorunlu olarak kopyalanmamalı. Test bitiminde BB açıkça20'ye geri getirildi ve sonra yeniden açılarak doğrulandı.

## Dar pencere: doğru karşılaştırma yöntemi

Bağlı hesaplı penceredeki viewport isteğine güvenilmedi:1280×720 istenirken PNG1920×970 çıktı. Ek ordinary-CDP DOM/CSS ölçümü1536×776 gördü. Bu ölçüm REA Evidence değildir: reports/rea-chart/tradingview-responsive-active-metrics.json. REA'nın bağımsız environment isteği ile haricî Chrome'un görünür boyutunu eşitlemediği bu oturumda gözlendi; nedenin tamamı çözümlenmedi. Bu görüntüler responsive başarısı diye sunulmaz.

Karşılaştırma, mevcut Chrome executable ile REA launch modunda headless/geçici ve girişsiz profile taşındı. Hesap oturumu/çerez/storage kopyalanmadı. Her senaryo bitiminde provider-owned process terminated sonucu döndü. Yeni kurulum veya hesap değişikliği yapılmadı.

| İstenen/PNG boyutu | Profil | Çalıştırılan durum |
| --- | --- | --- |
|1280×720 |Girişsiz/DPR1 |Yan panel açık; kapalı grafik; Canvas dialog |
|1024×768 |Girişsiz/DPR1 |Watchlist açık grafik |
|768×900 |Girişsiz/DPR1 |Yan panel açık; kapalı grafik; Canvas dialog |

Bu deneyler desktop user-agent/mouse ortamıdır.768px gerçek mobil uygulama, touch, sanal klavye, iOS/Android veya ekran rotasyonu kabulü değildir.1024'te yalnız panel açık durum alındığından bütün viewportlarda aynı durum matrisi tamamlanmış değildir.

## Tasarımsal bulgular

-1024px'de watchlist/detay paneli yaklaşık300px yer kaplıyor; kalan grafik belirgin biçimde daralıyor.768px'de paneli kapatmak temel grafik alanını geri kazandırıyor.
- Dar üst araç çubuğunda metinli eylemler ikonlara dönüşüyor veya erişim alanından çekiliyor. Görünen ikonların erişilebilir adı, tooltip ve overflow yolu korunmalı; yalnız ekran görüntüsü işlevlere erişilebilirliği kanıtlamaz.
-1280px Canvas ayarında sol kategori listesi ve sağ içerik var; alt Template/Cancel/Ok bölümü sabit.720px yükseklikte içerik içten kayıyor.
-768px Canvas dialogu yatay alana göre daralıyor; bazı etiketler iki satıra düşüyor. Alt soldaki Template erişimi ellipsis görünümüne dönüyor; Cancel/Ok görünür kalıyor.
- Girişsiz örneklerde onboarding balonu grafiği kapatabiliyor. Bu deneyim bizim temel grafik yüzeyine taşınmamalı; öğretici içerik kapatılabilir ve analizi engellemeyen bir yerde olmalı.
- Geçici profillerin default tema/gösterge/legend tercihleri hesaplı düzenle aynı değil; farklı font/renkleri viewport farkı diye yorumlamak yanlış olur.
- Hesaplı234 kayıtlık paket içindeki başarısız attached viewport görüntüleri ile doğrulanmış anon görüntüler ayrı manifest etiketleri taşımalı.

## Plana aktarım ve kalan iş

1. Focus router: grafik/çizim/metin/modal/form kapsamı; inputtayken chart kısayolu sızıntısını engelleme.
2. Live preview transaction: önceki snapshot, değişiklik gruplama, Cancel rollback, Escape/X/Ok anlamları; dirty/save göstergesi.
3. Numeric validation: min/max, geçersiz/boş girdi, son geçerli değere dönüş, erişilebilir hata bildirimi ve locale ondalığı.
4. Responsive kabuk: panel kapama/overlay politikası, chart minimum kullanılabilir genişliği, overflow araç erişimi, uzun etiket ve sabit modal footer.
5. Grup: gerçek modifier/pointer bağlantısı veya uygun hesap yeteneğiyle multi/mixed/nested kabulünü tamamlamak. Yeni araç kurulumunu bu tur varsaymamak.
6. Touch/IME/clipboard, tüm viewport durum eşitliği, resize sırasında çizim ankrajları ve performans hâlâ açık.

Son hesaplı durum: BTCUSDT.P/1D, Volume+BB20/SMA/close/2, UTC; dört orijinal çizim global gizli. Geçici grup/kopyalar silindi; Settings kapalı, saved görüldü. REA03 açık; geliştirme başlamadı.
