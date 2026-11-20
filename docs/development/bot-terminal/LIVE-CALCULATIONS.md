# Canlı fiyat, kâr/zarar ve likidasyon hesapları

19 Kasım 2026 güncellemesi. Demo USD-M terminali. Bu özellik emir, plan yetkisi veya otomatik işlem oluşturmaz.

## Güncel düzeltme: senaryo ile işlem uygunluğu ayrıldı

Önceki uygulama hesaplama için tam işlem ön kontrolünü zorunlu tutuyordu. Bu yanlıştı: hesap ayarı uyuşmazlığı, minimum lot veya risk reddi hesaplanabilen sayıların da görünmesini engelliyordu. ANALYZE_PLAN artık kısa, salt okunur hesap/fiyat/filtre/basamak görüntüsü toplar; günlük işlem geçmişini ve emir uygunluğu akışını çalıştırmaz. Gerçek PREVIEW_PLAN ve CONFIRM'in güncel hesap, sahiplik, günlük kayıp, filtre ve risk kontrolleri korunur.

Analiz sonucu `SCENARIO` ve `execution_preflight_required=true` taşır. Seçilen kaldıraç/teminat/pozisyon modu hesapla farklıysa yalnız derleme için kullanılan bağımsız kopyada senaryo ayarları kullanılır; borsa veya kayıtlı hesap ayarı değişmez. Tam portföy ve günlük kayıp uygunluğu bu panelin iddiası değildir. Çapraz portföy tam doğrulanmamışsa likidasyon tahmini gösterilmez.

Uygun senaryolarda compiler'ın miktar/risk matematiği kullanılır. Minimum miktar veya diğer işlem koşulları bunu engelliyorsa ayrı gösterge hesabı `theoretical=true` döndürür: lot adımına yuvarlanmış miktar ile teorik miktar ayrı gösterilir. Gridin gösterge boyutu compiler ile aynı bütçe birimlerini kullanır: toplam nominal, teminat+rezerv veya azami kayıp; hücre sayısı ve en olumsuz fiyat hesaba katılır. Bu değerler yürütülebilir emir miktarı değildir. Gerekli basamak/teminat verisi yoksa likidasyon uydurulmaz. Tek işlemde varsayımsal hedef/stop sonuçları gösterilir; gridde tek ve kesin gerçekleşmiş kâr üretilmez.

Uygunluk uyarıları sayıları gizlemez; ayrı bölümde listelenir. Taslak değişince önceki sonuç hemen geçersizleşir. Yeni sonuçtan 5 saniye sonra yenileme denenir; taze sonuç yeni okuma sırasında görünmeye devam eder. Geçici okuma hatası hâlâ taze olan sonucu silmez; 15 saniyeyi aşmış sonuç güncel sayı olarak gösterilmez: güncel değil etiketiyle en fazla 60 saniye korunur, sonra kaldırılır. Bu sayede normal yenileme sırasında panel tamamen boşalmadan son hesap incelenebilir.

Doğrulama: bildirilen BTCUSDT GRID / 10 USDT / 4 hücre / 10x İzole taslağı gerçek Demo okumasında yaklaşık 6,12 saniyede SCENARIO döndü. Model başlangıç teminatı 1 USDT; lota yuvarlanmış toplam miktar 0; teorik toplam miktar yaklaşık 0,00007143 baz varlıktı. Hesap ayarı, fiyat sapması, minimum bütçe ve likidasyon tamponu gibi koşullar ayrıca raporlanır. İzole testte aynı taslağın PREVIEW_PLAN'ı reddedilmeye devam etti; hesap/snapshot değişmedi, emir veya oturum oluşmadı. İlgili 183 backend testi ve 500 frontend testi geçti; üretim derlemesi başarılı.

## Önceki teslim ve model açıklamaları

Aşağıdaki ilk teslim kayıtlarında anlatılan tam ön kontrol yolu artık yalnız işlem önizlemesinin otoritesidir; hesaplama için yukarıdaki senaryo yolu geçerlidir.

## Çalışma yolu

Form tamamlandığında 1,2 saniyelik düzenleme beklemesinden sonra `ANALYZE_PLAN` kuyruğa eklenir. Worker mevcut `make_plan → runner._snapshot → compile_plan` yolunu kullanır. Yeni bir miktar belirleme motoru veya ayrı risk politikası yoktur. Plan sürümü, onay tokenı ve oturum oluşturulmaz; analiz sonucu CONFIRM için kullanılamaz.

Hesap okuması ve analiz istemcide aynı okuma kapısını paylaşır. Ekran pasif/gizliyken yeni analiz istenmez. Yeni sonuçtan 15 saniye sonra yeniden hesaplama denenir; ağ/toplama süresi buna eklenir. Taslak değişince önceki sonuç anında geçersizleşir. 15 saniyeyi aşan hesaplama değeri veya başarısız bağlantı sonucu güncel sayı olarak gösterilmez. Hesap görünümünün başlama zamanı ve hesaplamanın bitiş zamanı ayrı gösterilir. Hesaplama, tekrar ön kontrol ve açık onayın yerini almaz.

Mark fiyatı ayrıca SNAPSHOT içinde doğrulanır: sembol, pozitif değer ve borsa zamanının yaş sınırı kontrol edilir. Eski/eksik Mark verisi hesap görüntüsünün diğer bölümlerini uydurma fiyatla tamamlamaz. Kullanıcı isterse güncel Mark değerini referansa aktarır; fiyat alanı sessizce değiştirilmez.

## Hesaplar

Tüm işlevsel matematik backend'de Decimal ile yapılır; arayüz yalnız biçimlendirir.

- Miktar, bölünmüş hedef miktarları, nominal üst sınır, başlangıç teminatı ve masraf rezervi gerçek compiler çıktısından alınır. Lot adımı nedeniyle oluşan gerçek hedef bölünmeleri kullanılır.
- Brüt hedef sonucu: her hedef için `yön × hedef miktarı × (hedef fiyatı − giriş)` toplamı.
- Rezerv sonrası hedef sonucu: brüt sonuç eksi motorun iki yön masraf rezervi.
- Stop sonucu: `yön × miktar × (stop − giriş) − rezerv`.
- Brüt fiyat getirisi: `brüt hedef sonucu / (miktar × giriş) × 100`.
- Rezerv sonrası ROE: `rezerv sonrası hedef sonucu / modellenen başlangıç teminatı × 100`.
- Getiri/risk: `rezerv sonrası hedef sonucu / mutlak stop sonucu`.
- Market için giriş hesabında güncel Mark kullanılır; gerçek dolum fiyatı değildir. Limit için planın limit fiyatı kullanılır. priceMatch'in kesin giriş fiyatı bilinmediğinden kesin hedef kârı ve ROE verilmez.

Masraf rezervi mevcut risk motorunun `%0,1 × iki yön` varsayımıdır; kişiye özel gerçek komisyon değildir. Funding dahil değildir. Bu nedenle çıktı “net gerçekleşen kâr” diye adlandırılmaz.

## Likidasyon ve açık pozisyonlar

Yeni planın **tahmini likidasyonu**, mevcut portföy modelindeki risk basamağı ve teminat varsayımlarıyla alınır. Çapraz modda model kullanılabilir teminatı paylaştırır; tahmin borsanın kesin likidasyon motoru değildir. Modelin 0 üretmesi pozitif bir likidasyon seviyesi üretmediğini ifade eder; risksizlik onayı değildir.

Açık pozisyon tablosundaki **borsa likidasyonu** doğrudan V3 `liquidationPrice` alanıdır; modelle değiştirilmez. Pozitif seviye yoksa “—” gösterilir. Likidasyona mesafe LONG için `(Mark − likidasyon)/Mark ×100`, SHORT için `(likidasyon − Mark)/Mark ×100` olarak hesaplanır; işaret korunur. Getiri yüzdesi `unRealizedProfit / positionInitialMargin ×100` kullanır. Borsa teminat alanı eksik/sıfırsa kaldıraç tahmin edilerek yüzde üretilmez.

GRID/NEUTRAL için derlenmiş tam envanter risk/teminat senaryosu gösterilir. Hücrelerin dolum sırasına bağlı kâr tek bir kesin hedef kârına çevrilmez.

## Gerçek çalışma ve test kanıtı

- Long/Short brüt sonuç, rezerv, ROE, stop ve çok hedef miktar bölünmesi bağımsız sayısal beklentilerle test edildi. Eksik teminat, sıfır likidasyon, priceMatch, grid ve bekleyen koşul durumları kapsandı.
- Engine üzerinden Mark 80000 → 80100 değiştirildiğinde sonuç değişti. Girdi değişmedi; borsa POST'u, plan kaydı ve oturum oluşmadı. Analiz sonucunu CONFIRM etme denemesi reddedildi.
- İstemci testinde taslak değişimi, kopuk bağlantı, pasif görünüm ve paylaşılan okuma kapısı kontrol edildi; istekler yalnız ANALYZE_PLAN idi.
- 499 frontend testi ve üretim derlemesi başarılı. İlgili backend/risk/transport/kota paketindeki 177 test geçti; son eklenen grid/bekleme senaryosuyla saf hesaplama modülündeki 5 test de geçti. Tüm depo Python paketi bu özellik turunda tekrar çalıştırılmadı.
- Gerçek Demo hesabında ETHUSDT, hesabın gerçek kaldıraç/teminat/pozisyon modu ve güncel Mark ile ANALYZE_PLAN READY döndü; miktar 0.014, hedef brüt sonuç pozitif, stop sonucu negatifti. `order_sent=false`, `execution_authorized=false`. Chrome'da otomatik hesaplama sayıları ve değişen fiyat sonuçları görüldü. Gerçek emir veya pozisyon açılmadı.
- Masaüstü 1440 px ve mobil 390 px görünümde panel kontrol edildi. Tam Bot sayfası tek kaydırma sahibi olmaya devam eder. Eski sonuçlar yenilenme sırasında “—” olur. Boş gerçek hesap nedeniyle açık pozisyon metriklerinin dolu veri yolu izole exchange fixture'larıyla doğrulandı; yeni gerçek pozisyon açılarak kabul yapılmadı.

## İstek bütçesi

Canlı denemede bilinmeyen uçlara uygulanan genel 100 ağırlık, hesap okuması ve analiz birlikte çalışırken yerel bütçeyi doldurdu. Yalnız kesin USD-M GET yolları için güncel resmi ağırlıklar sabitlendi: accountConfig 5, positionSide/dual 30, symbolConfig 5, leverageBracket 1, tek sembollü premiumIndex/assetIndex 1; sembolsüz son iki uç 10. Diğer ürünler, bilinmeyen uçlar, mutasyonlar, tavanlar ve cooldown mekanizması değiştirilmedi. Maliyetlerin yöntem/yol kapsamı test edildi. Mevcut bekleme kaydı silinmedi veya kota sıfırlanmadı.

Kaynaklar: [Binance USD-M Market Data](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data), [Account](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account), [Position Information V3](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade).

## Bildirilen veri eskimesi düzeltmesi

Kullanıcının GRID hesaplamasında gördüğü `SNAPSHOT_STALE` incelendi. Hesap/config/emir/fiyat okumalarının seri ağ beklemeleri 15 saniyelik pencereyi tüketiyordu. Gerçek DemoExchange + JsonTransport yolunda bağımsız sabit GET grupları artık en fazla dört eşzamanlı okuma kullanır. Her çağrı ayrı exchange/transport taşır; yalnız config, saat offset'i ve ortak kota yöneticisi paylaşılır. SQLite yürütme store'u iş parçacıklarına verilmez. Sahte transportlar ve özel adaptörler seri yolunu korur. Günlük geçmiş sayfalama ve hesap sahipliği kontrollerinin sırası/koşulları korunur.

Başlangıç zamanı ileri taşınmadı; 15 saniyelik sınır artırılmadı. 16 saniyelik sentetik toplama, son fiyat taze olsa bile `SNAPSHOT_STALE` olarak reddedilmeye devam ediyor. Paralel yolun gerçekten örtüşmesi, dört çağrı sınırı, bağımsız transportlar, ortak governor ve store paylaşılmaması test edildi.

Aynı kayıtlı BTCUSDT GRID taslağı gerçek Demo okumalarıyla 11,829 saniyede `ACCOUNT_SETTINGS_MISMATCH` döndürdü: taslak 10x/ISOLATED, borsa ayarı 20x/CROSSED. Bu bir zaman aşımı değildir ve hesap ayarı otomatik değiştirilmez. GRID hesap modu/teminat, fiyat toleransı/bant ve hücre başına minimum bütçe retleri de ayrı izinli neden kodlarıyla gösterilir; genel hata metnine düşmez. 10 USDT nominal bütçenin hücre minimumlarını sağlamadığı izole durumda özel neden testi eklendi.

Düzeltme sonrası 181 ilgili backend testi, 499 frontend testi ve üretim derlemesi başarılı. Salt okunur worker yeniden başlatıldı. Yeni emir/ayar değişikliği yapılmadı. Gerçek ağ 15 saniyeyi aşarsa eski veri yine kullanılmaz; optimizasyon bunun güvenlik kontrolünü devre dışı bırakmaz.
