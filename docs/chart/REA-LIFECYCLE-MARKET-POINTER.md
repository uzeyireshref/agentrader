# Geniş canlı tur: veri yaşamı, piyasa kimliği ve uç nokta sürükleme

11 Kasım2026, Asia/Baku. REA03 araştırması; ürün geliştirmesi yapılmadı. Ana sorular: açık/kapanmış mum, yeniden edinme, tarih navigasyonu, fiyat türü, hacim yokluğu ve gerçek pointer hareketi. Menü, veri penceresi ve tasarım durumları aynı deneylerde izlendi.

Kanıt paketi: reports/rea-chart/rea-evidence-lifecycle-market-pointer-20261111.json;89 kayıt/17,134,616 byte. Bu MCP oturumundaki önceki51 kayıt dahildir; bu tur38 kayıt eklendi. Başarısız ve sınır tanımlayan denemeler de kayıttır. Daha eski234 kayıtlık paket ayrı korunur. Sayılar ürün testi veya kapsam tamamlama yüzdesi değildir.

## Sorular ve kapsam sonucu

| Soru | Sonuç | Kalan sınır |
| --- | --- | --- |
| Açık mum ile önceki kapalı satırlar nasıl değişiyor? | Görünür1m örnek doğrulandı | Exchange closed flag/ham event yakalanmadı |
| Tam document yüklenince kapalı veriler aynı mı? |30 ortak satır aynı | Ham precision, tüm geçmiş ve düzeltmeler değil |
| Kesinti sonrası iyileşme? |25sn emülasyon ve geri dönüş gözlendi | Tam WebSocket black-out oluşmadı; stale kabulü kapanmadı |
| Geçmiş bir pencere açılabiliyor mu? |8 ve5 Kasım1m verileri açıldı | Pagination protokolü/üst sınır/gap bütünlüğü bilinmiyor |
| Spot/last/mark birbirine karışıyor mu? | Kimlik, fiyat ve gösterge davranışı ayrıştı | Tüm fiyat türleri ve yarış senaryoları değil |
| Hacim yoksa VWAP ne yapıyor? | Mark verisinde gerçek RE10142 ve boş çıktılar | Sıfır hacimli ama hacmi mevcut seri ayrı açık |
| Uç nokta gerçekten sürüklenebiliyor mu? | Tek geçici trendde koordinat+Undo doğrulandı | Gövde/multi-select/snap/cancel/touch/performance açık |
| Bar numarası kalıcı ankraj mı? | Eski Fib kaydına göre1 farklı gösterim | Sebep ve mutlak UTC ankraj eşitliği bilinmiyor |

## Kanıt defteri

| ID | Gözlem | Evidence |
| --- | --- | --- |
| L10 |1m ilk tablo, açık01:32 | ev_d19fa497f744f087417fdbe86b536386404b448d5337144ab272171d384c0f9b |
| L11 | Sonraki tablo,01:32 kapanmış,01:33 açık | ev_5109e9029df0a27d285c8cb6d78620e000f2b29744a7a0f090cc9f3a77f5d907 |
| L12 | Ağ emülasyonu sırasında offline uyarısı ve hâlâ Market open/update etiketi | ev_e1c17c173c75cfa3bdc88174194a7f9ee00ec916509181e15190322b840d9a15 |
| L13 | Emülasyon kaldırıldıktan sonra güncellenen tablo | ev_dc1aad0e9c1bba167548f2e22a0ed1153b37702e852170840bfa6ad835961137 |
| L14 |1m kaydedilmiş düzen, reload öncesi tablo | ev_92b65b417d5f1ff44b599e377f0b55847a8fbcaee3c085ade4b1401abe19e628 |
| L15 | Public query değişimiyle document yükleme/frame navigation; reload sonrası tablo | ev_aa88e31770a1f92514cbb90b5c3edfc6ac9cacd2d062cd485553455d81241d24 |
| L16 |8 Kasım1m, tarih imleci kilitli | ev_b27979bd3443b63af64561ca840fc3aa841a3605c74a775e7f5364779cfe2664 |
| L17 | Volume Default→8:37→37.187;1h'de8 seçili olmasına rağmen K kısaltması | ev_c2335dd5d844544859505d0af6a0961c518460c8a0244eeca73eed75a2c0e076; ev_377b836637ac65825f9d1e348088d47faf8e9954eb6ec8b846e8459b7298626a |
| L18 |5 Kasım1m pencere; öncesinde Volume Default geri yüklendi | ev_2a0feaf696d0696e2223689a07a8ee52b4acc796a8d854a4ebfd818f72a39a58 |
| L19 | Spot arama/spot seçimi ve çizimsiz nesne ağacı | ev_93c846a0438bdf6f77acda0903245d0876e560f71700e4b2fe800083d8975d50; ev_88e1c23f0490ec694597e30edfdb221fb6c7aea6c702399a6b1a3aa94c29fc2d |
| L20 | Mark fiyatı: OHLC var, Volume/VWAP hata; ayrıntı ve tablo | ev_6e56b854e500c40f2c2dce8c1628b28b144f3e7735374a2985048fb7b6c50318; ev_a8200ebc1e193fc53780770eaa10062687685041f7da17cdf2a36e6ec4193a22; ev_759a1de8709997ae283287ad4b68cc7d948babe64a3f922846e7185f815fdfd4 |
| L21 | Perpetual'a dönüş; dört orijinal çizim ve hacimli VWAP geri geldi | ev_9e794082005fe42da7c5c3f5dd6cdb95e9b772f50e76766a8dc79ca0f6d518ff |
| L22 | Boş spot1D üzerinde pointer deneyi hazırlığı | ev_f4c9578e26bb2cdf2ffbe2626962d4bfd25e9c7e479d0fd4e7ea88015d3207c8 |
| L23 | Sürükleme sonrası trend koordinatları ve Undo sonrası koordinatlar | ev_13fe35b437a9574cce35bd9e9562c5534e2a6a0e44b0b1abbe72ed82cb205123; ev_3d33bbbb218b3f201cd02d33492b12fede517e79ed7138929ecd28d48c442e22 |
| L24 | Koordinat okuyucusu Cancel sonrası Redo yok; geçici trend silindi | ev_80b64c1efe079fa00466938c8c08c40cbd42a0242bd685e0ce3504f66c739e72; ev_b1036a13e29bd37d2c1c98bf0f3288f077b3b47e84dc7bdec4cc7618ce96b9f0 |
| L25 | Orijinal Fib fiyatları60000/80000, gösterilen barlar186/248 | ev_6209af4d378e47a2947e5bac8958ae493b68dd0a9e8100530cc815c17cff1011 |
| L26 | Fib seçili görsel; ardından BB Inputs ve temiz/saved son durum | ev_21133bf78fab2f592662281ce5db9dd4850383d0b3b580ad1fa5b2570f832599; ev_91b57216ed4c87448dd4f7be4990a741e8e0ee439075385d9c17727debaea7ba; ev_f4c4d99820ab75cbbc03e1bfee7f0875b558aa0a8c686f2e815643045e0e5fc1 |

## Açık mum, kapalı satır ve reload

reports/rea-chart/minute-lifecycle-20261111.json. Açık01:32 satırında O73788.9/H73844.1/L73780.7/C73844.1/Vol89 ve BB73534.6/73817.5/73251.6 okundu. Sonraki01:33 gözleminde aynı01:32 artık O73788.9/H73855.0/L73780.7/C73840.6/Vol189 ve BB73534.4/73816.6/73252.2 oldu. Mum ve ona bağlı gösterge açıkken değişiyor.

İki tablonun en yeni satırları dışlanıp timestamp ile eşleştirildiğinde31 ortak kapanmış satırın9 görünür hücresi birebir aynıydı. Bunlar displayed OHLC/change/rounded-volume/BB çıktılarıdır. Kapanmışlık sonraki mumun gözlenmesinden çıkarıldı; borsanın closed flag'i yakalanmadı.

1m düzen geçici olarak kaydedildi. İlk aynı-URL yenileme denemesinde tablo görünümü kaldı; bu deneme reload başarısı sayılmadı. Sonra query'ye yalnız public rea_probe değeri eklenerek yeni document navigasyonu çalıştırıldı; frame events ve yeniden oluşan chart UI kaydedildi. Öncesi/sonrasında timestamp ile eşleşen30 ortak kapalı satırın9 hücresi aynı çıktı. Açık satırlar karşılaştırılmadı.31 ve30 karşılaştırma örtüşür;61 benzersiz mum değildir. Probe query tur sonunda kaldırıldı ve esas1D düzen geri kaydedildi.

Ürün gereği: açık mum aynı anahtar altında güncellenir; kapalı mumun kesinlik/kaynak/revision bilgisi farklıdır. History snapshot veya reload/catchup geçmiş kapanışı yeni canlı sinyal gibi üretmemeli. Bu runtime gözlemi bizim P2/P3 uygulamasının kabul testi değildir.

## Ağ kesintisi: offline etiketi tek başına veri kesilmesi değildir

REA6.8 senaryo ortamı offline eylemi sunmuyor. Sınırlı fallback tools/rea/research-network-window.mjs, yalnız seçilen araştırma target'ına25sn Network.emulateNetworkConditions uygulayıp finally içinde normal ağı geri yükledi. OS ağı değişmedi. Ham payload/header/cookie/storage alınmadı. reports/rea-chart/network-offline-window-20261111.json sıradan CDP runtime kaydıdır, REA Evidence değildir; L12/L13 bu pencerenin ayrı REA gözlemleridir.

Offline pencerede8 loading failure,6 WebSocket closure,4 yeni socket denemesi,4 socket error görüldü; ayrıca31 WebSocket frame alındı. Mevcut akışlardan veri gelmeye devam etti.15sn örneğinde offline uyarısı çıktı; Market open/data updates once per second etiketi de kaldı.25sn içinde yeni01:34 mum oluştu. Restore sonrasında2 socket açılışı/11 frame ve güncellenen fiyatlar görüldü.

Sonuç: hata/yeniden bağlanma ve uyarı durumu gözlendi; **tam transport black-out, stale freeze veya kesintiden sonraki tüm catchup doğruluğu kanıtlanmadı**. Market open seans durumudur; fresh market data kanıtı değildir. Bizim UI connected/reconnecting/disconnected/stale/catching-up durumunu upstream veri yaşı ve snapshot kanıtından üretmeli. Uyarı bütün grafiği kapatmadan son doğrulanmış veriyi ve yaşını göstermeli. Bu tur uyarı metni AX'te gözlendi; piksel yerleşimi için bağımsız offline ekran görüntüsü alınmadı.

## Geçmiş penceresi ve canlı bağlam

Go to→8 Kasım00:00/1m çalıştırıldı ve imleç zamanla kilitlendi: O75836.0 H75836.1 L75814.0 C75814.0, ana-seri Vol37.19, Volume göstergesi37, BB75845.3/75894.8/75795.7.5 Kasım isteğinde de eski1m fiyatlar açıldı; örnek imleç00:46: O80781.9 H80782.0 L80700.0 C80700.1, Vol110.92.5 Kasım00:00'ın tam seçildiği iddia edilmez; istenen güne ait pencere/00:46 verisi gözlendi.

İki tarih de açıldığı için varsayılan bir5000-bar veya hesap planı sınırı çıkarılmadı. Backend paging cursor, batch count, tüm continuity/gap ve tarih dışı hata hâlâ açık. Geçmiş mum seçiliyken bid/ask ve Last day change canlı bağlamda kalabiliyor. UI seçili mum ile en son piyasa verisini açık etiketlerle ayırmalı. Tarih navigasyonu aboneliği/bot market kimliğini sessiz değiştirmemeli.

## Hacim gösteriminin hassasiyet sınırı

Volume Default→Precision8 aynı geçmiş mumda37→37.187 gösterdi; ana-serinin Vol37.19 alanı ayrı formatter kullanıyordu. Ancak1h'de8 seçili olduğu yeniden okunmasına rağmen binli hacimler3.71K/2.42K gibi kısalmaya devam etti. Precision8, K formatını tam hacme çevirmedi. Önceki VWAP bounded-volume tutarlılığı exact-volume parity'ye yükseltilmedi. Volume Default açıkça geri getirildi. Kanonik hacim, UI formatter çıktısından veya yalnız precision düğmesinden türetilmemeli.

## Aynı varlık, ayrı piyasa ve fiyat türü

Arama aynı ailede spot, futures/perpetual, mark/index/premium türev metriklerini ayırıyor. Spot BTCUSDT'de iki ondalık fiyat ve örnek0.01 bid/ask farkı; perpetual BTCUSDT.P'de bir ondalık ve örnek0.1 farkı görüldü. Bunlar display/quote örnekleridir, bağımsız tick-size spesifikasyonu değildir.

Spotta nesne ağacı Volume+VWAP içeriyordu; perpetual'ın dört çizimi burada yoktu. Perpetual'a dönüşte dört çizim geri geldi; göstergeler kaynak değişimine yeniden hesaplandı. Bu sıralı geçiştir, yarış/late-response kabulü değildir. UI symbol değişirken URL symbol query'si kendiliğinden değişmediği için araştırmada query aynı tutuldu; nihai URL yeniden perpetual ile temizlendi.

reports/rea-chart/price-type-isolation-20261111.json, aynı kapalı1m/01:42:

| Kaynak | O | H | L | C |
| --- | --- | --- | --- | --- |
| BINANCE:BTCUSDT.P |73979.3 |73981.8 |73900.4 |73918.5 |
| BINANCE:BTCUSDT.P_MPRICE |73990.0 |73990.0 |73904.1 |73920.2 |

Aynı tarih/symbol ailesi bu verileri birbirinin yerine kullanılabilir yapmaz. market key; exchange/product/contract/price_type/interval içerir. Mark fiyatının generic buy/sell gösterimi doğrulanmış yürütülebilir quote değildir; canlı emir fiyatı sayılmaz.

## Hacim yokluğu: gerçek gösterge hata örneği

Mark serisinde OHLC geldi; Volume No volume data, VWAP No volume data: RE10142 gösterdi. Data window nesne başlıklarını koruyup çıktıları boş bıraktı. Table view ise yalnız Open/High/Low/Close/Change sütunlarını gösterdi; hatalı Volume/VWAP output sütunlarını tamamen dışarıda bıraktı. Önceki hide-on1D deneyinde sütunlar durup hücreler boş kalmıştı: bu iki UI durumu aynı değildir.

Perpetual'a dönüşte hacim/VWAP sayıları geri geldi. Ürün contract'ında missing vendor volume, zero volume, hidden-by-setting, warmup, stale ve calculation error ayrı nedenler olmalı. Son geçerli başka market VWAP değeri yeni kaynağa taşınmamalı; boş değer0'a çevrilmemeli. Hata ikonu/mesajı chart kullanımını engellemeden ilgili göstergede görünmeli. Sıfır hacmi mevcut ama değeri0 olan seri hâlâ ayrıca test edilmeli.

## Gerçek pointer: tek trend uç noktası ve Undo

REAclick modifiers/drag sunmadığından tools/rea/research-trend-pointer.mjs yalnız boş spot1D üzerinde normal CDP Input.dispatchMouseEvent kullandı; sayfa JS'i enjekte edilmedi. Helper market/canvas/nesne ağacını kontrol etti; diğer dört çizimin bulunduğu perpetual'a giriş göndermedi. İlk salt okunur guard tooltip'i çizim sandığı için giriş yapmadan durdu; gerçek data-source ağacıyla düzeltilip çalıştırıldı.

reports/rea-chart/trend-pointer-probe-20261111.json eylem/konum/zaman ve önce/sonra PNG/hash kaydıdır, REA Evidence değildir. İki canvas tıklaması bir geçici trend oluşturdu; ikinci uç12 adımlı mouse drag ile taşındı. İlgili REA coordinate formları, reports/rea-chart/trend-pointer-fixture-20261111.json:

| Nokta | Drag öncesi (Undo ile okundu) | Drag sonrası |
| --- | --- | --- |
|1 |111927.87 / bar−121 |111927.87 / bar−121 |
|2 |98638.51 / bar−69 |104182.31 / bar−55 |

İlk nokta aynı; ikinci fiyat+5543.80/bar+14. Toolbar Undo change point gösterdi. Cancel ile düzenlenmeden kapatılan formdan sonra Ctrl+Z ikinci noktayı eski değerine döndürdü. Sonraki coordinate-reader Cancel akışından sonra Redo düğmesi görünmedi; doğrudan Undo/Redo çiftinin başarısı iddia edilmez. Geçici trend seçilip Delete ile kaldırıldı, spot nesne ağacı eski3 kaynağa döndü.

Pointer yardımcısının ölçülen drawn→dragged süresi yaklaşık64sn idi; CDP/araç round-trip/backpressure içerir, kullanıcı FPS/drag latency benchmark'ı değildir. Gövde sürükleme, endpoint hit radius, magnet/tick politikası, pointercancel, dışarıda bırakma, çoklu seçim ve touch açık. REA'nın doğrudan drag desteği hâlâ yok; sınırlı fallback bir örnek için çalıştı.

## Fib bar indeksinde yeni belirsizlik

Önceki FIB-TEMPLATE-RELOAD-001,60000/80000 ve bar187/249 kaydetmişti (ev_9a7be074a618ae73848efdebc0b63e9e6b48cf03334b3826e229e7c9db679427, önceki yönetim/ölçek paketlerinde). Bu tur fiyatlar aynıyken form186/248 gösterdi. Fib'e numeric edit veya pointer hareketi uygulanmadı; yalnız koordinat okuyucusu ve görünürlük kullanıldı. Seçili görselde log midpoint69282.0 da önceki fiyat örneğiyle aynı.

Bu gözlem tek başına çizimin mutlak tarihlerinin kaydığını veya kaymadığını kanıtlamaz. UTC anchors önceki kayıtla karşılaştırılmadı; index origin/history/day-boundary sebebi çözülmedi. Bar numaraları geri187/249'a yazılarak düzeltme yapılmadı; böyle bir işlem tarih ankrajını yanlış değiştirebilirdi. Negatif barlar da spot trend formunda görüldü. Ürün kalıcı kimliği render/logical index'e bağlamamalı; timestamp+market+grid provenansı ve history prepend dönüşümü açık olmalı. Bu bir açık araştırma fixture'ıdır, PASS kabulü değildir.

## Plana aktarım ve temizlik

P2/P3: status ile freshness ayrımı, bounded outage'ın kanıt sınırı, catchup/dedup/snapshot barrier; önceki tamamlanmış işler korunur, bu runtime turuyla yeniden PASS verilmez. T08/T09/T11: market/price_type/calculation interval ve missing-volume nedenleri. T07/T12/T13: logical index ile timestamp ayrımı, endpoint drag tek undo işlemi, coordinate-reader'ın undo geçmişi etkisi. QA01: temporary object cleanup, cross-market isolation ve nonblocking error/empty durumları; gerçek performans ve geniş pointer matrisi açık.

Son durum L26: BTCUSDT.P/1D/UTC, Volume Default +BB20/SMA/close/2/offset0/Chart/Wait-on; dört orijinal çizim global gizli, geçici spot trend silindi, VWAP kaldırıldı, probe query temizlendi, modal kapalı ve All changes saved. Fib fiyatları yeniden okundu; bar-index farkı yukarıda açık bırakıldı. Araştırma doğrulaması tools/rea/verify-lifecycle-research.mjs ile yeniden üretildi; ürün testleri çalıştırılmadı. REA03 sürüyor; REA04 nihai plan konsolidasyonu ve ürün uygulaması yapılmadı.

## Sonraki turun sınırlı çözümü

[UTC/drag/HTF raporu](REA-UTC-DRAG-HTF-RESOURCES.md), önceki açık soruları daralttı: güncel Fib time_t ve300-gün penceresi186/248’i tam açıklıyor; eski raw UTC kaydı yok, tarihsel gün dönümü açıklaması çıkarım. Tek log gövde ve doğrudan Undo/Redo başarılı; Escape-keep gözlendi, pointercancel hâlâ açık. BB günlük hesap/saatlik grafikte WaitON/OFF artık doğrulandı. Bu ek eski turdaki gözlemleri veya limitleri geriye dönük PASS yapmaz.
