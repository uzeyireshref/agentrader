# REA kanal / pitchfork geometri bulguları

13 Kasım 2026. Salt okunur bağımsız kaynak incelemesi. Bu belge matematiğin yeniden kurulmasını tarif eder; üçüncü taraf uygulama kodu ürün kaynaklarına kopyalanmadı. Canlı tıklama deneyi yapan ana araştırmanın bulgularından ayrı olarak, aşağıdaki sonuçlar yakalanmış istemci kaynağının statik gözlemleridir.

Kanıt: `ev_dc1e281183debc3ab5307552a6200835389a9accbc05f546d6d807b10caba31b`, `reports/rea-chart/channel-family-complete-source-20261113.json`.

## Kaynak kimlikleri

| Araç | TradingView kaynak URL sonu | SHA-256 |
| --- | --- | --- |
| Pitchfork | `line-tool-pitchfork.4148adc2fc68aeb574bc.js` | `b464935d8b11c27cf292d4cfa838105478be3ca153d17a503fc3afd6ef8b53d9` |
| Disjoint | `line-tool-disjoint-channel.a03151e2202571232f1d.js` | `50ddabffac6e0da4b1c991fb0acb5746c9ab3164e45930152f96c63e84af1a45` |
| Flat top/bottom | `line-tool-flat-bottom.bb0c4d99342cf0d38bae.js` | `7d70600e1015538457eecf35d42fda3642ac3500e868cce5edcf176409600a72` |
| Regression | `line-tool-regression-trend.e926ba13376f22ca9a87.js` | `c1eada4db03fa387bc73fae74a2996382c2fd3e9654a5665ad3c9fcab4fe4b22` |

Tam URL öneki `https://static.tradingview.com/static/bundles/`.

## Koordinat sınırı

Aşağıdaki vektör formülleri **ekran koordinatlarında** uygulanıyor. Lineer zaman/fiyat görünümünde aynı affine işlemler mantıksal bar/fiyat uzayında yapılabilir. Log fiyat görünümünde aritmetik fiyat ortalamasıyla ekran ortalaması eşit değildir; buradan genel log-fiyat hesap parity'si çıkarılamaz.

## Pitchfork ailesi

Üç kayıtlı ankraj A, B, C; M=(B+C)/2 ve H=(C−B)/2.

| Varyant | Merkez ışını | Seviye ışınları |
| --- | --- | --- |
| Original | A yönünden M'ye | M±kH noktasından M−A yönüne |
| Schiff | O=(Ax,(Ay+By)/2) yönünden M'ye | M±kH noktasından M−O yönüne |
| Modified Schiff | O=(A+B)/2 yönünden M'ye | M±kH noktasından M−O yönüne |
| Inside | M noktasından C−(A+B)/2 yönüne | M±kH noktasından C−(A+B)/2 yönüne |

Original, B–C bağlantı segmentini gösterir. Schiff ve Modified Schiff, A–B ve B–C segmentlerini gösterir. Inside ayrıca orta(A,B)–C segmentini gösterir; bu finite segment, M'den başlayan merkez ışını ile aynı nesne değildir.

Tüm ışınların yön boyunca uzaması açık. `extendLines=false` başlangıçların gerisine uzatmayı kapatır; true geriye uzatmayı da açar. Adı "Extend lines" olsa da sağ/ileri ışınlar varsayılan durumda zaten uzar. “None” seçeneğini bounded pitchfork olarak yorumlamak TradingView varsayılanıyla eşleşmez.

Default aktif oranlar k=.5 ve k=1. Her oran simetrik iki çizgi üretir. Dokuz yuva var: .25/.382/.5/.618/.75/1/1.5/1.75/2; diğerleri default kapalı. Default dolgu açık, transparency80. Her seviye görünürlük/renk/kalınlık/stil içerir; bunların tek ortak stile indirgenmesi ürünün desteklenen alt kümesi olur.

**İsim tuzağı:** Enum `Schiff=1` istemci sınıfında “Modified Schiff pitchfork” adına gider; `Schiff2=3` ise “Schiff pitchfork” adına gider. Kullanıcıya gösterilen araç adını esas almak gerekir. Yalnız enum adından formül seçilmemeli.

Bağımsız aritmetik örnek: A=(0,100), B=(10,140), C=(20,120). M=(15,130). x=25'te merkez değerleri Original150; Schiff136.666…; Modified Schiff140; Inside130. k=1 ışın başlangıçları B ve C'dir.

## Disjoint channel

Üç ankraj kaydeder. İlk sınır A→B. Diğer sınır D→C' olup C'=(Bx,Cy), D=(Ax,Cy+By−Ay). Üçüncü noktanın x'i görüntüde kullanılmaz. İkinci sınırın eğimi birincinin ters işaretlisidir; gerçek render **paralel kanal değildir**. Kesişen iki sınır ve bow-tie dolgu mümkündür. Resmî yardım metnindeki “parallel” ifadesiyle çelişen bu nokta, canlı şekil ve kaynakla ayrı doğrulanmalıdır.

Dördüncü tutamaç D türetilmiştir; dördüncü bağımsız ankraj değildir. B taşınırken eski (B.price+C.price)/2 orta fiyatı korunur, dolayısıyla C'nin fiyatı ters yönde güncellenir. C taşınması yalnız C fiyatını değiştirir. Türetilmiş D taşınması A zamanını değiştirir; yeni A.price=B.price−(D.price−C.price).

Örnek A=(0,100), B=(10,140), C.price=120: D=(0,160), C'=(10,120). Sınırlar x=7.5, fiyat130'da kesişir.

## Flat top/bottom

Üç kayıtlı ankraj. İlk sınır A→B; ikinci sınır (Ax,Cy)→(Bx,Cy). Üçüncü noktanın fiyatı yatay sınırı belirler. Dördüncü görünür tutamaç (Ax,Cy) türetilmiştir.

Üçüncü tutamaç taşınırken B'nin zamanı da taşınan x'e gider. Dördüncü tutamaç taşınırken A'nın zamanı ve C'nin fiyatı değişir. Dolayısıyla yalnız üç kayıtlı noktayı gösterip dördüncü köşeyi düzenlenemez yapmak TradingView'in tam tutamaç davranışı değildir.

Her iki kanal ailesinde sınırların sola/sağa uzatma anahtarları, dolgu, fiyat etiketleri ve ek metin özellikleri bulunur. Kanal çizgilerinin gösterilen fiyat etiketleri kanonik fiyatlardan formatlanır; log görünümde pikselde türetilen D ile fiyat etiketinde türetilen D aynı işlem yolundan gelmez. Log parity ayrıca gerekir.

## Regression trend: bilinenler ve açıklar

Araç iki ankrajlı. Ankrajlar zamana göre sıralanır; yalnız `first bar time` / `last bar time` ve hesap girdileri çalışma hesaplamasına gönderilir. Dönen `baseLine.startPrice/endPrice` ankraj fiyatlarını yeniden yazar. Mouse ile tıklanan Y değerleri hesaplanan tabanı belirleyen girdiler değildir.

İstemci `_trendData` içinde start/end bar indeksleri, baseLine/upLine/downLine başlangıç/bitiş fiyatları ve `pearsons` değerini tüketir. Renderer bu hazır değerleri fiyat ölçeğine çevirir. Sağ uzatma seçeneği var; renderer soldan uzatmaz. Üst/alt çizgi görünürlüğü ayrı `styles.*.display` alanlarındadır. Pearson etiketi aşağı sınırın başlangıcına yerleştirilir.

Yakalanmış `4187.7c81ec49a1ad3b87368a.js` metaverisi: default upper deviation +2, lower deviation −2; her ikisi integer, izin verilen aralık −500…500. Kaynak default close; open/high/low/close/hl2/hlc3/ohlc4 seçenekleri. `use upper/lower diviation` booleandır ve default true. Meta kaynak SHA-256 `c07d36de676b14b4868271129f9c0af482faf73a1f70a2c2bb193d6ceb1dc513`.

**Henüz kanıtlanmayanlar:** OLS eksen yönü ve kesin uç denklemleri; standart sapmanın N, N−1 veya N−2 paydası; residual sapma mı kaynak sapması mı; kapalı/açık mum ve eksik veri davranışı; disabled deviation durumunda bandın hangi hesapla kurulduğu; Pearson'ın tam formülü, işareti/formatı ve sıfır varyans davranışı. Bu hesaplar yakalanan renderer/metaveri paketlerinde yok. “Use deviation” kutusunun sınırı gizlediği çıkarılamaz; görünürlük bağımsız alandadır.

Uygulama kendi açık OLS/sapma sözleşmesini seçebilir, fakat sayısal TradingView parity'si olarak sunmadan önce aynı kapalı mum penceresinde sayısal karşılaştırma gerekir. Bu inceleme seed/stddev/Pearson hakkında çalıştırılmış deney sonucu üretmedi.


## Ek canlı sayısal deney — 13 Kasım

Araştırma grafiğinde API ile disableSave/disableUndo etkin bir geçici Regression trend oluşturuldu; yalnız deney kimliği dwjOyD kaldırıldı. Önceden bulunan Y7GTYB trend çizgisi korundu. Her kaynak değişiminde properties değişmesi yeterli sayılmadı; sunucu hesabının beklenen taban ve üst uçlarını üretmesi beklendi. İlk hızlı okumanın eski _trendData döndürdüğü gözlendi ve o geçici kayıt doğrulanmış sonuçlarla değiştirildi.

Mumlar269..288, CME:BTC1!,1W; yedi OHLC kaynağı. Kaydedilen gerçek taban/üst/alt uçları bağımsız OLS ile1e-6 fiyat toleransında eşleşti. Sapma sqrt(SSE/(N−1)); Pearson soldan sağa indeks korelasyonunun ters işaretlisi. open kaynağı için deviation kapalıyken bant high/low uçlarının tabana maksimum uzaklığı ile eşleşti. Bu ek deney önceki “payda/Pearson/fallback kanıtlanmadı” kaydını bu örnek penceresi için günceller; tüm sınır durumlarının kabulü değildir.

Kanıtlar: reports/rea-chart/regression-live-comparison-20261113.json, regression-fallback-comparison-20261113.json, regression-seven-sources-20261113.json. Aynı veriler ve gerçek çıktılar frontend/tests/fixtures/regression-rea-20261113.json altında tekrarlanabilir sayısal testtir.
