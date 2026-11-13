# Kilitli toplu hareket, hassas OHLCV ve gösterge doğrulaması

11 Kasım 2026, yaklaşık10:17–10:52 UTC. REA03 geniş canlı tur; hesap, etkileşim ve tasarım birlikte incelendi. Ürün kodu değiştirilmedi,5/21 tamamlanma korunur; REA04 taslak.

Paket reports/rea-chart/rea-evidence-mixed-precise-indicators-20261111.json: **72 kayıt /11.346.289 byte**; önceki38 kayıt dahil,34 yeni REA kaydı. Önceki106 kayıtlık paket ayrı korunur. Kayıt sayısı tam platform eşitliği demek değildir. Görsel manifest mixed-precise-visual-manifest-20261111.json:18 PNG,10 REA ve8 ordinary-CDP. Ordinary input/akış kayıtları REA Evidence değildir. Son durumda geçici çizimler/göstergeler temizlendi, dört orijinal perpetual çizim gizli ve saved.

## 1. Gerçek iki-nesne gövde sürükleme: kontrol ve mixed lock

Spot BTCUSDT/1D/log üzerinde tek geçici trend çizildi ve Clone edildi. Normal UI formundan her iki nesne ayrı okundu; row0 clone, row1 original. Başlangıç ev_1737c6b1010bad44f96e7e6805845ac9b2bd8e455eb615925961493d642f3bb3.

| Çizim | Başlangıç fiyat/bar çiftleri | İkisi serbest: sonra | Biri kilitli: sonra |
| --- | --- | --- | --- |
|0 clone |81572.22/195 →71541.73/248 |82983.35/204 →72779.35/257 |81572.22/195 →71541.73/248 |
|1 original |78821.52/195 →69129.27/248 |80185.07/204 →70325.16/257 |80185.07/204 →70325.16/257 |

Kontrol: iki nesne Ctrl ile seçildi, original gövdesinden aynı50/−20 CSSpx mouse drag yapıldı. İki nesnenin iki barı da+9; log-price değişimi additive ortak delta değildir. Toolbar Undo move drawing(s); tekUndo ikisini tam başlangıca döndürdü: ev_080ba726d5f8d75f3a59f0829e0e0fd67dedc5c8d5b357363b87d6ebeb640c6e.

Mixed: yalnız row0 kilitlendi, pair tekrar seçildi. Bir Unlock ve bir Lock ikonu ile iki selected sınıfı doğrulandı: ev_bce2e69a0f462d4934864b7fc7b382109f6c277bb9695de0ec8303794ea98b50. Aynı serbest gövdeden aynı drag, kilitli clone'u aynı bıraktı, serbest original'i kontrolle aynı sonuca taşıdı: ev_64d01571be9dc6af34cfdf24562d9c05b87d79bfae5dc1e34ff1e5c9e9db09dd. TekUndo başlangıcı geri getirdi: ev_c824fa598252310d6d9f5f1d7e60ad2df9e71cb5ce1d612cc2ec8f278e85a8de.

İlk kontrol girişinde mutasyon yoktu; uzun hover bilgi kutusu görüntülendi. Bu sonuç kilit engeli veya platformun move yapamadığı şeklinde yorumlanmadı. İmleç uzaklaştırılıp yeniden gövdeye girilerek giriş ayrıldı; başarılı kontrol held-preview/sonraki koordinatla doğrulandı. İlk başarısız kayıt pair-drag-control-attempt1-20261111.json ayrı tutuldu.

Kayıt mixed-body-move-fixture-20261111.json; ordinary pair-drag-control/mixed ve multi-selection-wide-control/mixed JSON/PNG. İki trend/teklogölçek sınırı geçerlidir; nested group, diğer araç türleri, property/coordinate editi veya bütün komutlar için kilit semantiği kanıtlanmadı.

T07/QA01 aktarımı: selection set ile editable set ayrı. Çoklu pointer hareketi, seçili kilitli nesneyi taşımamalı; tek gesture/tek history adımıyla değişen nesneler geri alınmalı. Bot bağları, görünürlük ve kilit ayrı kalır. Kaynak rehber [TradingView çoklu taşıma](https://www.tradingview.com/support/solutions/43000682552-how-to-move-multiple-drawing-objects-at-the-same-time/) mouse/klavye/displacement yollarını açıklıyor; bu belge runtime ölçümünün yerine kullanılmadı.

## 2. Pointercancel girişimi: sonuç üretmeyen kontrollü deney

Kalan tek trendde normal CDP touchStart/Move/Cancel ve pointercancel listener breakpoint gözlemi hazırlandı; sayfa JS'i enjekte edilmedi. İlk guard inline Rename textbox'ı yüzünden çizim span'ını bulamadı ve input göndermeden durdu. Escape sonrası source/koordinat doğrulandı. Gerçek denemede ilk Input.dispatchTouchEvent touchStart çağrısı zaman aşımına uğradı; move/cancel aşamasına geçilmedi, listener pause veya held-preview alınmadı. **Reference pointercancel sonucu bilinmiyor.** Fiziksel touch, OS blur veya mouse lost-capture kabulü değildir.

touch-pointercancel-observation-20261111.json ve touch-cancel-cleanup-20261111.json: breakpoint remove, Debugger.disable ve Emulation touch disabled yanıtları alındı. Debugger.resume not paused, touchCancel Must send a TouchStart first yanıtları aktif paused/touch kalmadığını destekledi. Cleanup tamamlandı. Sonradan trend78821.52/195→69129.27/248 aynı okundu ve silindi: ev_b137daab42bd62f060b10b84c899fff875d77bef10a238ab31b353834ecf9770.

Ürün kabul kararı (uygulama değil): pointercancel/lost capture/blur, commit edilmemiş preview'u bırakmalı; pointer sahipliği/capture ve chart interaction lock'u temizlenmeli; iptal yeni history/persistence/bot olayı üretmemeli; sonraki gesture çalışmalı. Tamamlanmış mouseup/persist yanıtı için revision/stale-response sınırı ayrıca test edilmeli. DrawingLayer/drag guard bu yolları kaynakta içeriyor; canlı referans veya ürün testi PASS'i verilmedi. Bu bilinmeyen yeni touch girişlerini sınırsız tekrar etme gerekçesi değildir; QA01'de uygun gerçek input kohortuyla açık kalır.

## 3. Daha hassas fiyat/hacim girdisi

VWAP için perpetual BTCUSDT.P/1h/UTC; Session/HLC3/Standard Deviation/Multiplier1/Offset0/Chart/WaitON formu okundu: ev_4617b9b491eaa958cecf64b5d305943c930c4d7b128eb434ec0be655dcbd89f8. Düzen saved ev_98b6a1acf36fd9b0a0930b2117d4ad2e15b5cf37a1594e56e676abd671a4fbd5.

tools/rea/capture-numeric-study-stream.mjs explicit reload/loader değişimini gözledi; sadece sayısal timestamp/index/OHLCV vektörleri süzüldü. Oturum/auth/headers/cookie/storage/quote ve ham frame saklanmadı. Study name keşfi hesapta kullanılmadı; gösterge numeric vektörleri alınamadı. Bunlar protected-output hassasiyet kanıtı değildir.

precise-volume-study-stream-20261111.json:300 saat,29Ekim23:00–11Kasım10:00 UTC; ardışık3600sn. Son saat açık,299 önceki saat kapanmış bağlamda. İlk29Ekim seansı yalnız23:00 içerdiğinden VWAP reset hesabına başlangıç olarak alınmadı. Gözlenen OHLC değerleri0.1, hacimler0.001 adımda temsil edilebildi; bunlar bu örneğin decimal girdileridir, resmî tick/lot-size otoritesi değildir. Örnek ilk OHLCV:78976.2/78986.8/77868.4/77962.6 ve20163.947 hacim.

REA tablosundaki32 kapalı saatin OHLC'si, aynı timestamp'teki feed OHLC'siyle tam eşleşti. Hacim K sunumu yerine browser-decoded daha ayrıntılı sayılar kullanıldı. Bu, ham exchange trade akışı veya trade-level VWAP değildir; veri revision/vendor farkları ayrıca açıktır.

## 4. VWAP: hacim belirsizliği daraldı,96 çıktı eşleşti

REA33 satırlık tablo ev_f96e42e9be6628407e7b5146e3a5cd911000c1525d5cd62daeca60d2d4a79c85. Açık11Kasım10:00 çıkarıldı,10Kasım02:00–11Kasım09:00 arasındaki32 kapalı saat/96 çıktı karşılaştırıldı.

Bağımsız referansta p=(H+L+C)/3. Fiyat/hacim tamsayı ölçeklere çevrilip BigInt ile Σpv,Σv,Σp²v toplandı; basis ve ağırlıklı population variance rasyonelleri saklandı. Yalnız son gösterim karşılaştırmasında Number/sqrt kullanıldı. UTC00:00 resetinde tam session girdisi olma şartı uygulandı. Formül sıfır hacim için bu tur kabul edilmedi; yakalanan bütün v değerleri pozitifti.

**32/32 satır,96/96 çıktı0.05 toleransında**; maksimum mutlak hata0.04875589315. Çıktı UI0.1 precision ile okundu, bu nedenle sub-display veya hidden precision parity iddiası yok. Örnek11Kasım00:00 basis/upper/lower73592.0/73592.0/73592.0; tek barın HLC3 değeri73592.0333333.9Kasım/10Kasım diğer tam gün girdileri mevcut, ama UI karşılaştırması yalnız belirtilen32 satırdır.

Dosyalar precise-vwap-table-20261111.json, precise-vwap-parity-20261111.json; tools/rea/verify-precise-vwap.mjs. Önceki25 rounded-volume consistency satırı geriye dönük exact'e çevrilmez. Yeni cohort, uncompact browser hacmiyle **yuvarlanmış UI eşitliğidir**. T11: kaynak/anchor/session/grid provenansı ve kanonik hacim display formatter'dan ayrılmalı. Zero-volume/DST/borsa seans takvimi, gerçek trade VWAP ve HTF VWAP hâlâ açık.

## 5. RSI14: uzun geçmiş sonrası varsayılan hesap

Inputs14/Close, smoothing SMA14, Chart/WaitON; Calculate Divergence kapalı: ev_3d8e3907812d80519eb954e81c5d02eccb9267555adbd4a6b6bde576cacea910. Tablo ev_31aacc6b6bcd731964570168260dc9597c9ddb9e980635b6c4f02cef65e52504.

Aynı300 close girdisi; ilk14 değişim SMA gain/loss yerel seed, sonraki Wilder RMA14 güncellemeleri. Karşılaştırılan32 kapalı saat için seed sonrası minimum253 update geçti. RSI ve RSI üzerindeki SMA14 bağımsız hesaplandı. **32/32 satır,64/64 çıktı0.005 toleransında**, maksimum hata0.00492578444. rsi14-hourly-long-burnin-20261111.json; verify-rsi14-hourly.mjs.

Bu uzun-history eşleşmesi, platformun başlangıç seed/NA/warmup algoritmasını belirlemez. Flat/all-up/all-down fixture'ı değildir. Önceki kaynak sözleşmesindeki flat source100/ürün50 farkı hâlâ source-level açık madde; ürün değiştirilmedi.

Tasarım: divergence kapalıyken dört divergence sütunu tabloda kaldı, hücreler boştu. Disabled calculation/empty output gerçek0 veya hata değildir. RSI-based MA ayrı hesap ve ayrı ayar olmalı; erişilebilirlikte sütun varlığı ekrana sığma kabulü değildir.

## 6. ATR14/RMA: sekiz ondalık ve önceki kapanış dalı

Inputs14/RMA/Chart/WaitON ev_5b9e83a9f2f6cde0f1f3f7a904cd4361aa24d8a69fc43b804c079bae234910db. Style Precision8 seçildi; yalnız output formatter ayarıdır, kanonik fiyat/hacim değişmedi. Menü ev_9d7e5c6ab68edeac232f783723ad0491ec895e3daea7457de1c92f111ea9312e.

İki tablo kohortu: son32 kapalı saat ev_011bbf67ef1b2911b917235385198eefec9a6ce4d0e3886d7d4612eeaba57b18 →31 recurrence;4Kasım02:00–6Kasım09:00 ayrı56 kapalı saat ev_6913633c345849b859ee27f14cc65897d2fbcb32fd5a508b818c291cfa1ecab2 →55 recurrence. **86/86** RMA next=(13*previousATR+TR)/14 adımı1e−8 toleransında. Önceki/güncel ATR display belirsizliği toplam üst sınırı yaklaşık9.64e−9;1e−8 kullanıldı. Başlangıç seed kanıtı değildir.

300 fiyat girdisinde bir kapalı mumda Cprev high-low dışında bulundu. Native hover/time eşlemesi stale/locked readout nedeniyle doğrulanamadı; yanlış okumalar kabul edilmedi. Exact Go to tarih+saat, normal chart context ve cursor lock ile üç saat ayrı doğrulandı. İlk05 isteği yanlış10Kasım12:00 okuttu; dışlandı. Cursor lock toggle düzeltilerek doğru05 yeniden alındı.

|9KasımUTC | ATR8 | Kanıt |
| --- | --- | --- |
|04:00 |475.39239196 |ev_21df41776c6970add22c5393e699190d009bd52f88b5992496035b61e4210fc6 |
|05:00 |477.96436396 |ev_7ee17cab5a4f0f12e9b58073ed204fc846f2fb2130575474278e7138981e6057 |
|06:00 |494.22405225 |ev_308c5513bc282a6ab102b9431beffa49d6be153736a3f5212c78c2f55043ffb8 |

05 mumunda Cprev74800.0,H74799.9,L74288.6. H−L511.3 ama gerçek TR511.4. RMA beklenen477.964363962857; UI farkı2.86e−9. Yanlış high-low-only aday477.957221105714; fark−0.007142854286,8dec belirsizliğinin çok üstünde.06'daki normal dal da1.43e−9 farkla uydu. Böylece önceki günlük turda ayrılamayan **gap-sensitive TR dalı tek örnekte ayrıştırıldı**.86 tablo adımı+2 hedef adım88 recurrence kontrolü; diğer göstergelerle sayılar tek benzersiz-mum toplamı diye birleştirilmez.

atr-gap-precise-ui-20261111.json, atr-scrolled-ui-20261111.json, atr-gap-precise-parity-20261111.json; verify-atr-gap-precise.mjs. Çoklu seans/DST/NA/seed, daha büyük gap ve vendor revision hâlâ açık.

## 7. Menü, kaydırma ve tasarım bulguları

Tasarım sayısal deneylerle birlikte ölçüldü: selected iki satır, mixed Lock/Unlock, kilitli çizgide geometri sabitliği; high-precision ayrı ATR ölçeği ve Data window; inactive divergence sütunları; kaynak/chart interval ve gösterge parametreleri. Precision8 uzun etiketleri eksen alanını büyüttü; görüntü genişliği/plot dönüşümü sabit kabul edilmemeli. Kullanıcı ekranında varsayılan okunabilirlik ve araştırma precision'ı ayrı tercih olmalı.

TablePageDown denemesi satır aralığını değiştirmedi; keyboard scroll kabulü verilmedi. Native wheel input timeout oldu, sonuç kabul edilmedi. Normal scrollbar track click eski56 satırı getirdi; scroll yolu çalıştı ama hedef tarih için hassas track konumu veya keyboard erişimi doğrulanmadı. DOM'daki12300px tbody yüksekliği, eksiksiz tarihçe veya tüm satırların render edildiği kanıtı değildir. Cursor lock ile GoTo marker/son crosshair aynı tarih olmak zorunda değildir; veri penceresinin date+time alanı doğrulanmadan gösterge fiyatına bağlanmamalı.

18 PNG1920×970 desktop kohort; no pixel parity/touch/FPS kabulü. Hash'li CSS adları yalnız locator kanıtıdır, tasarım token'ı olarak kopyalanmaz.

## 8. Plan kararı ve son durum

Bu tur mixed pointer hareketini, VWAP volume-display belirsizliğini, varsayılan RSI14 yakınsama örneğini ve ATR gap dalını dar kapsamda kapattı. Sonraki araştırma önceliği veri kaynak/interval geçişinde geç yanıt, seed/NA/zero-volume/seans sözleşmesi kararları ve referans performans baseline. Pointercancel referans sonucu bilinmiyor; ürün rollback/cleanup kabulü QA01'e yazıldı. Sonsuz aynı input denemesi yapılmayacak. REA04 seçilmiş kapsam/dependency/kabul konsolidasyonundan önce tüm TradingView menülerini bitirme şartı yoktur.

Final ev_68c3db2b587928b8c98a4fec91777d7578f2298b92a338a7e9ca3136f08cdd78: BTCUSDT.P/1D/UTC, Volume korunmuş+BB20/SMA/close/2/offset0/Chart/WaitON yeniden okundu. ATR/RSI/VWAP ve iki temp spot trend kaldırıldı; dört orijinal çizim global gizli, dialog kapalı ve All changes saved. Emülasyon/debugger temiz; Ctrl/mouse bırakılmış. Ürün testleri/uygulaması yapılmadı.

Dört yeni araştırma fixture'ı ile toplam40. tools/rea/verify-mixed-precise-research.mjs ve reports/rea-chart/mixed-precise-validation-20261111.json, hesap/cleanup/manifest doğrulamasını tutar. Önceki fixture'lar yeni kanıtlarla geriye dönük kapsam dışı PASS sayılmaz.

Doğrulama sonucu kaydedildi: mixed-precise-validation-20261111.json. Mixed pointer/Undo,300 OHLCV,32 VWAP satırı/96 çıktı,32 RSI satırı/64 çıktı,ATR31+55+2 recurrence,18 PNG hash/boyutu ve son restore durumu kontrol edildi. Önceki snap/selection kohort doğrulayıcısı büyüyen katalogdan bağımsız kimliklerle korunur; ürün testleri çalıştırılmadı.
