# Grafik referansı — REA incelemesi

Tarih: 10 Kasım 2026. Bu belge canlı gözlem, istemci kaynak bulgusu, resmî belge ve kendi tasarım kararlarımızı ayırır. Grafik ürün kodu değiştirilmedi.

## Referans kararı

Ana araç/etkileşim referansı **TradingView Supercharts**; veri ve piyasa bağlamı referansı **Binance USD-M**. Mevcut Lightweight Charts motoru bu araştırma sonucunda değiştirilmez. Supercharts ile açık kaynak Lightweight Charts aynı ürün değildir; birinin araçlarını diğerinde hazır varsayamayız.

Ortak ilk koşullar: Chrome 157.0.8103.50, 1280×720, DPR 1, en-US, UTC, boş araştırma profili. Binance BTCUSDT Perp ve TradingView BINANCE:BTCUSDT.P, 1D. Açık mum değerleri farklı zamanlarda alındığından fiyat/hacim eşitliği testi yapılmadı. O/H/L ilk gözlemlerde aynıydı; bunun bütün geçmiş için eşitlik kanıtı olduğu söylenmez.

| Ölçüt | TradingView | Binance Original / gömülü Trading View |
| --- | --- | --- |
| Grafik açılışı | Hesapsız başarılı | Hesapsız başarılı |
| Araç keşfi | Trend, Fib, long/short, ölçüm, anchored VWAP ve yönetim seçenekleri REA accessibility ile okunuyor | Original OHLC/MA/hacim okunuyor; mod değişimi başarılı, gömülü grafik üst sayfa kaydında iframe |
| Tekrarlanabilir erişim | Adlandırılmış butonlar ve menü satırları; Escape ile menü kapanışı gözlendi | Üst sayfa birçok ikon ve etiketsiz img içeriyor; iframe içi kapsam ayrıca gerekir |
| Kaynak incelenebilirliği | www + static.tradingview.com kaynakları yakalandı; hash ve kod konumu korunuyor | Bu tur tam bundle analizi yapılmadı; başarısız veya incelenemez diye sınıflandırılmaz |
| Çizim kullanımı | Long yerleştirme giriş istemiyle durdu; hesaplı test bekliyor | Bu tur çizim oluşturma deneyi yapılmadı |
| Veri ve performans | Aynı kapalı mum fixture/parity ve eşit yük benchmarkı yapılmadı | Aynı kısıt geçerli |

Karar bir genel ürün sıralaması değildir. Bizim T04–T14 araç kapsamımız için erişilen davranış kanıtının niteliğine dayanır. Binance'in iframe yapısı tek başına teknik olarak analiz edilemez olduğu anlamına gelmez.

## Kanıt envanteri

Yerel ayrıntılar `reports/rea-chart/` altındadır. JSON içindeki tam evidence_id ve parametreler asıldır.

| Kayıt | Kanıt |
| --- | --- |
| TradingView ilk açılış, screenshot/accessibility | tradingview-initial.json / .png; ev_cf2fa65db4b2b8fd354d7ecdb0ac8ee168a361473930edb79ef1f3b64267a7c0 |
| Binance Original ilk açılış | binance-initial.json / .png; ev_b138ce054d581b1285ccb798b982eddbdbb8eeaa91c4678a094456980b552453 |
| Forecasting menüsü | ev_d52f78e972477a2433a484a2254cdb169e2897820c3c7a6401d435ccdc91aaa3; tradingview-forecast-menu.json |
| Trend/Fib/interval/magnet/lock/hide menüleri | ev_c3c5451553b3da1943392c9ef0998c6bcf01237e8b1dd537a09eef318e9e5a15 |
| Binance gömülü moda geçiş | ev_6aa4857e8ced4af4bcd414db5c25946a796efcabd16aade7c4a911c485a7e092 |
| Long oluşturma giriş engeli | ev_146a3cc1bef364f35dc108b96d7c84e26d059b7b6a9dce061086626f27a7753d; place-long başarısız, sonraki adımlar çalışmadı |
| REA kısmi bundle taraması | ev_a0f1d8e12a7f0bf44e6471dadbe40ea5f5de09018f10bffef0e03379983f7196 |
| Kaynak metinleriyle pasif yakalama | ev_4dc67afdd4eeec389a4b0a1e17d8697175a0a24f159de5174336d067abea5838; rea-evidence-source-pass.json |

Bundle taraması 45 saniye toplam sınırına ulaştı. Kısmi route envanterinde 368 kaynak, 176 complete ve 192 unavailable kaydı vardır; route parsing sonucu bütün çizim motorunun analizi değildir. Sonraki pasif source yakalaması tamamlandı; MCP'nin 10 MiB yanıt sınırından büyük olduğu için retained evidence 19.1 MB dosyaya aktarıldı. Bu iki kapsam birbirine karıştırılmaz. `source-term-matches.json` içindeki URL/hash/UTF-16 offset ve kısa bağlamlar kaynak bulgularını tekrar bulmak içindir; üretim koduna aktarılacak kaynak değildir.

## Doğrudan gözlenen davranışlar

| Bulgu | Sonuç | Mevcut karşılık / aktarım |
| --- | --- | --- |
| REA-F01 | Forecasting araçlarında Long/Short, Price range, Date range, Date and price range ayrı araçlar | T03 ortak cetvel korunur; kalıcı/ani ölçüm ayrımı açık olmalı |
| REA-F02 | Trendline, Ray, Extended line, Horizontal line/ray ve Parallel channel ayrı seçimler | T05 süre/kapsam özelliği ve T06 üç anchor; tek sınırsız trend gibi modellenmez |
| REA-F03 | Fib retracement ile Trend-based fib extension ayrı araçlar | T12 iki noktalı retracement ve üç noktalı projection ayrı kind |
| REA-F04 | Weak/Strong magnet seçenekleri; Snap to indicators bu oturumda disabled | Mevcut indicators.ts yalnız yeni noktada 10px OHLC snap. Aynı davranış iddiası yok; T07 etkileşim alt işi |
| REA-F05 | Lock drawings / Lock indicators / Lock all ayrı | T07 kilit kapsamı veri modelinde açık; bot yetkisiyle bağlanmaz |
| REA-F06 | Hide drawings / indicators / positions and orders / all ayrı | T07 ve T09 görünürlük ayrı; gizleme silme veya bot deaktivasyonu değildir |
| REA-F07 | 1m/5m/15m/30m ve diğer zamanlar menüde var | T08 çekirdek 1m/5m/30m; menüde görünmek abonelik/veri kabulü değildir |
| REA-F08 | OHLC, hacim, bid/ask ve seçili fiyat ayrı sunuluyor | OhlcReadout.tsx ve LAST_PRICE korunur; spread/mark/index ile karışmaz |
| REA-F09 | Long oluştururken Join for free istemi | Girişsiz placement/drag/settings/save deneyleri doğrulanmadı |

## Kaynak bulguları ve sınırları

REA-S01: drawing-toolbar.d165472c698df8aa7b4a.js içinde magnetEnabled, magnetMode ve magnetSnapsToIndicators ayrı izlenen değerlerdir. Kaynak hash: 941e6f30ee737c5881769988bf32f817910b25380401c0e8abc2005ff305b273. Bu, UI state ayrımını destekler; kesin snap mesafesi ve tie-break algoritması bu bulguyla kanıtlanmaz.

REA-S02: 83073.2ea3ffb84a70aba53e00.js içindeki PositionTool koordinat dönüşümünde entryLevel, stopLevel, profitLevel, qty, startOffset, endOffset alanları görülür. Hash: 5a9f3eecad30549774987dfa772d3a2927fe6d65d2464d6c602802120112acb7. Bu, bir istemci dönüşüm yoludur; çizim CRUD şemasının tamamı veya hesap formülü değildir.

REA-S03: İstemci araç kimliklerinde long/short, ray/extended/horizontal ray, parallel channel ve Fib türleri ayrı adlandırılır. Olay adları Clone ve RiskReward.Reverse gibi aday işlemler içerir. İsim bulunması, erişim veya başarılı çalıştırma kanıtı değildir.

## Resmî belgelerden tamamlanan sözleşme

Bu bölüm runtime PASS değildir. Belgelenmiş özellikler, kendi ürünümüzün kabul adaylarını belirler.

- [Long aracı](https://www.tradingview.com/support/solutions/43000517002-long-position-drawing-tool/): entry/stop/hedef, risk/miktar ve görünüm ayarları. T04 ilk teslimi ayrı plan nesnesi ve salt teorik hesap olmalı; gerçek hesap bilgisi gerektirmemeli.
- [Long/short hesap açıklaması](https://www.tradingview.com/support/solutions/43000475660-how-to-use-long-and-short-position-drawing-tools/): yönlü fiyat mesafesi, R:R ve risk temelli qty. Lot/point-value/leverage seçenekleri ayrıca anlamlandırılmadan USD-M miktar hesabına taşınmaz.
- [Fib](https://www.tradingview.com/support/solutions/43000518158-fibonacci-retracement-drawing-tool/): özel oran, reverse, uzatma ve timeframe görünürlüğü. Log tabanlı seviye hesabı görüntü ölçeğinden ayrı seçenek; T12/T13'te ayrı sürümlü alan gerekir.
- [VWAP](https://www.tradingview.com/support/solutions/43000502018-volume-weighted-average-price-vwap/): seçilen bar fiyatı×hacim toplamı/hacim toplamı, reset/anchor ve kaynak ayarı. Mum VWAP ile trade VWAP ayrı isimlendirilir.
- [Anchored VWAP](https://www.tradingview.com/support/solutions/43000669764-anchored-vwap-drawing-tool/): kullanıcı başlangıç barını seçer; bu başlangıç, mouse Y fiyatına sabit yatay çizgi değildir.

## Kendi yeniden kurulumumuz için hesap kararları

Bu formüller ürün tasarımıdır; henüz TradingView ekranıyla sayısal parity sonucu değildir.

T04: side=long için stop<entry<target, short için target<entry<stop. Risk mesafesi abs(entry-stop), ödül mesafesi abs(target-entry), R:R=ödül/risk. Sıfır veya yanlış yön reddedilir. Tüm kesin fiyatlar decimal string; çizim pikseli yalnız giriş/görüntü dönüşümüdür. Ücret/kayma hem stop hem target senaryosunda ayrı varsayım sürümüyle gösterilir. Qty varsa USD-M base qty, risk bütçesi ve varsayımsal maliyet modeli açık olmalı. Emir step/min-notional doğrulaması veya yürütme yetkisi vermez.

T05/T06: fiyat fonksiyonu bar mantıksal ekseniyle tanımlanacaksa grid kimliği taşır; gerçek zamanla tanımlanacaksa UTC semantiği açık olur. İkisi sessizce birbirine dönüşmez. Sınırsız ray bile eksik veri uygunluğunu aşmaz. Kanal iki sınır ve orta çizgiyi aynı kanonik hesap üzerinden üretir.

T12/T13: mevcut first+(second-first)*ratio anlamı korunur. Referanstaki 0/1 yönünün aynı olduğu varsayılmaz; açık reverse/orientation eşlemesi gerekir. Log görünümden dolayı kaydedilmiş fiyatlar değişmez. Log geometri yalnız pozitif fiyatlarda; desteklenmeyen bot sorgusu BLOCKED.

T09–T11: source/period/seed/smoothing/warmup/anchor/reset/timezone veri sözleşmesinin parçası. Mevcut EMA SMA seed ve RSI Wilder davranışı regresyon fixturelarıyla korunur. 50 sabit RSI seçimi ile başka platformun tanımsız/null davranışı eşit kabul edilmez.

## Hesaplı deneyler — ikinci tur

Kullanıcı ayrı araştırma düzenini oluşturma ve deneme çizimlerini kaydetme iznini açıkça verdi. İlk hesabın bir kayıtlı düzen sınırı nedeniyle ek düzen oluşturulamadı. Kullanıcı diğer hesabına kendisi giriş yaptı. Bu hesapta açılan yeni düzen **REA Araştırma**, URL: https://www.tradingview.com/chart/E7UZkcrO/ . Önceki hesabın Adsız düzenine deneme çizimleri kaydedilmedi. Bu tur hesap/emir/broker işlevi kullanılmadı; bütün sayılar varsayımsal çizim girdileridir.

| Bulgu | Girdi ve gözlenen çıktı | Kanıt |
| --- | --- | --- |
| REA-F10 | Long: account=10000, risk=%1, lot=1, leverage=10, entry=70000, stop=68000, target=74000. Qty=0.05, R:R=2; hedef amount=10200, stop amount=9900; tick uzaklıkları 40000/20000 | ev_5fa0e0a59f8d74ef992d56f285241256dc30cf3be509a15c8731b0577102267f + sonraki screenshot |
| REA-F11 | Short: entry=70000, stop=72000, target=66000; aynı risk/lot/leverage. Qty=0.05, R:R=2; yeşil hedef aşağıda, kırmızı stop yukarıda | ev_cba8618fa73ec64e6e6f6f2a5754b20eeb218ffb86facba4ef48295be9a732db + sonraki screenshot |
| REA-F12 | Long ayarları Inputs/Style/Visibility olarak ayrılır. 12 font-size; compact/always-show-stats, price labels, ayrı stop/target renkleri; interval aralıkları ayarlanabilir | F10 kaydının style ve visibility adımları |
| REA-F13 | All changes saved gözlendi; tam reload sonrası sembolsüz URL SPX açtı. Aynı URL'ye BTCUSDT.P açık sorgusuyla dönünce iki long nesnesi yeniden listelendi | ev_3a5774801aeb767c47498243ca20f604afe22890bce997e462a287971afbf023 ve ev_18f304f398cf1f31b3d16568d51a93ee339d98bb32232bced2804e83d8c5cf75 |
| REA-F14 | Fib oluşturmanın iki farklı canvas noktası kullanıcı tarafından seçildi. Nesne ağacından ayarları REA açtı. İlk fiyat/bar girdileri 66754.7/187 ve 87261.4/249 idi; sonra yalnız fiyatlar 60000/80000 yapıldı | ev_70cd7f1d80d899efc57b721a680166a0d4717afacc9961c98fbe73467832d0b3 |
| REA-F15 | Reverse kapalı lineer Fib: 0=80000, .236=75280, .382=72360, .5=70000, .618=67640, .786=64280, 1=60000. Bizim first+(second-first)*ratio sözleşmemizin tersi | ev_1076c311be4c5f46db72c09a34f1e3a9385e4ad9c949806431d8509edb72ee89 + screenshot |
| REA-F16 | Reverse açılınca 0=60000, .236=64720, .382=67640, .5=70000, .618=72360, .786=75720, 1=80000 | ev_0d2b20c3e9c0e2fc9b0d4b4ed371b524cc041f0e0fccdeaab366f4528946384c + screenshot |
| REA-F17 | Lineer görünümde log-Fib seçeneği disabled; log görünümde seçilebilir. Reverse açık, log-Fib açık: .5=69282.0, .382=66969.6, .618=71674.3. 60000/80000 ankraj fiyatları korunur | ev_91547283d112c582a0d2cb0f00c5b9a34ef77e3f2c0628a107a32665c0733d5d + screenshot |
| REA-F18 | Fib ayarında 24 oran yuvası; bu oturumda 11 enabled, 13 disabled görüldü. Extend left ve right ayrı menuitemcheckbox; default Don't extend | ev_2d80bf4b3a3888f0053fb2cddc6cacade4149b1f7ec90fc17dbc6b422ebf132c ve F15 |
| REA-F19 | Nesne ağacı üst üste nesneyi seçme ve dialog açma yolu sunar. Ortak canvas merkezini çift tıklamak başka nesneyi seçebildi; nesne kimliğinin görünür olması gerekir | Short denemesindeki önceki Long dialog ile doğru Short dialog ayrımı; tam kayıtlar aşağıdaki evidence paketinde |

Kalıcı dosya: `reports/rea-chart/rea-evidence-authenticated-final.json` — 59 REA kaydı, 43.9 MB. Bu paket eski ve başarısız denemeleri de içerir; her kaydın step status alanı kontrol edilir. Click timeout bazen dialog açıldıktan sonra döndü; timeout PASS'e çevrilmedi, sonraki bağımsız screenshot/inspection ile gerçekleşen durum belgelendi. Tekrar oluşturma nedeniyle araştırma düzeninde iki long örneği vardır; bunu tek nesne reload testi diye sunmuyoruz. F13 yalnız iki nesnenin geri geldiğini gösterir; bütün sayısal alanların reload parity'si henüz ayrı doğrulanmadı.

## Doğrudan incelenen hesap ve render kaynakları

Hesaplı araçlar kullanıldıktan sonra REA'nın pasif kaynak yakalamasında 376 script kaydı görüldü. `ev_bc22b67613e214b18b47122923b2ffb65b9238355d549076780897de98b6c95d` kaydı tam metinleri retained evidence'a korur. MCP yanıtı 10 MiB sınırını aştığı için dosyaya export edildi; kaynak sonucu kesilmiş değildir. Bu kaynak yakalama 376 scriptin bütün algoritmalarının analiz edildiği anlamına gelmez.

- **REA-S04:** line-tool-risk-reward.0148670f19691994081e.js; SHA256 a0dd0e391d8e990cb7c6388e2db777ffea46853a14d422d97433702eff62c997. Tek base tool, long/short alt türleri, özellik modelleri, ayrı pane renderer ve fiyat ekseni view'leri görüldü. Qty yeniden hesabı risk temelli ve kaldıraç temelli sınırın minimumunu alıyor. Varsayılan account=1000/risk=25%/leverage=10000 değerleri bu kaynağın varsayılanlarıdır; bizim risk tercihimiz değildir ve kopyalanmayacak.
- **REA-S05:** Aynı paket, qty/risk/hesap/lot değişimlerini yeniden hesaplayan ayrı yollar ve tarihi mumlardan actual-entry/close-point arayan mantık içeriyor. Ekrandaki Closed PnL etiketi gerçekleşmiş hesap işlemi değildir. Aynı mumda stop+hedef sıralaması ve bütün veri boşluğu durumları bu tur çalıştırılmadı; bot backtest sözleşmesine kopyalanmaz.
- **REA-S06:** line-tool-fib-retracement.c0c93d67c8c5d88e7a1a.js; SHA256 6063dcab243cd7d922c67a8f5773cdaecccdc2ef351bb34a837f1873c027d4af. Reverse ankraj fiyatlarının hangi yönden okunacağını seçer. Log-Fib ancak fiyat ölçeği log ve ilgili seçenek açıkken etkinleşir. Seviye render'ı fiyatı ve piksel koordinatını ayrı üretir.
- **REA-S07:** 79097.303b2bf0ba8030264823.js; SHA256 522475513c70e6afd2720e25321c894c2d9ae01b195580da2b5437ee0a28aab1. fibLevelPrice lineerde fiyat aralığını, log seçeneğinde fiyat ölçeği koordinat dönüşümünü kullanır. Lineer/log sonuçlarını tek formül veya tek görüntü ayarı saymak yanlış olur.

Kaynak konumları ve kısa bağlamlar `auth-source-matches.json` / `calculation-source-snippets.json` içinde. Üretim koduna üçüncü taraf uygulama kodu kopyalanmadı; kendi sözleşmemiz ve bağımsız hesaplarımız kullanılacak.

## Tasarım ve uygulamaya etkisi

[Tasarım şartnamesi](REA-DESIGN-SPEC.md) D01–D06 işleriyle görsel kaliteyi çekirdek teslimlere bağlar. T04'te doğrulanan iki sayısal örnek fixture olur. T12'de default referans yönü için açık orientation/reverse alanı gerekir; eski first=0 kayıtları göçte tersine çevrilmez. T13'te log hesap geometrisi, görüntü ölçeği ve sayısal tolerans ayrı sürümlenir. Log interpolasyonun irrasyonel sonucu exact rational gibi etiketlenmez.

## Kalan doğrulamalar

Serbest drag/pointercancel/magnet mesafesi; invalid/zero risk ve diğer miktar sınırları; tam sayısal reload/undo/çok sekme; ray/kanalın iki/üç farklı noktada platform parity'si; ortak kapalı mumlarla EMA/RSI/ATR/VWAP parity; reconnect/history senaryoları ve eşit yük frame/heap ölçümü açık. Responsive 768px denemesi masaüstü CDP emülasyonudur; gerçek dokunmatik/mobil kabulü değildir. REA03 tam kabulü bu açık maddeler nedeniyle verilmedi. REA04 plan eşlemesi kullanılabilir taslaktır; bütün platform eşitliği veya yeni grafik uygulaması hazır değildir.


## Canlı tur: gösterge panelleri, ayarlar ve veri penceresi (10 Kasım 2026)

Bu tur REA üzerinden hesaplı araştırma düzeninde yapıldı. MACD yerleşik gösterge olarak eklendi, ayrı panel ve ayarları incelendi; ardından iki gösterge sınırı içinde BB incelemesine yer açmak için araştırma MACD örneği kaldırıldı. Ürün kodu değişmedi.

| Bulgu | Doğrudan gözlem | REA kanıtı |
| --- | --- | --- |
| REA-I01 | MACD: close, fast 12, slow 26, signal 9; oscillator ve signal için bağımsız EMA/SMA; Chart hesap zaman dilimi ve kapanış bekleme seçeneği | ev_e2f6cff4a3c208c58586b48175af54abf847e8529b558aa99812dcf172d6c7b0 |
| REA-I02 | Style: dört histogram rengi, MACD/signal/zero, precision, eksen ve status line değerleri; interval görünürlüğü | ev_0af51a29df2dc01066d41ba2e54f3a2a651d0edef500d50ee18067c35aa999df |
| REA-I03 | Gösterge menüsü: görsel sıra, görünürlük, Move to, Pin to scale, kopyalama/gizleme/silme/ayar. Move to alt menüsünde Existing pane above görüldü; taşıma uygulanmadı | ev_c0d212733abe8ca3f9a5e2fea2f27ad9e3992515801a8ec9bc7a9eaec4927b11; ev_1e045b20c8873923e14048ba1fca38282b5f59bbae0f2b053270f4624d7ef982 |
| REA-I04 | Salt okunur yerleşik Pine kaynağı UI üzerinden açıldı: fastMA-slowMA=MACD, MA(MACD,signalLength)=signal, MACD-signal=histogram. Seçilen MA türü EMA/SMA fonksiyonuna gider | ev_732822b9290626c222dedccb356eb626a2b4d8da4ca2c867d20803ee7febdd87; ev_38a6710e110cf7ddcd033df0b402e38ca2dd5697bb84e0d02ef63c7245bd9c45 |
| REA-I05 | Histogramın dört rengi: hist>=0 ve önceki değerden büyükse koyu yeşil; diğer pozitif durumda açık yeşil; negatifte önceki değerden büyükse açık kırmızı, diğerinde koyu kırmızı. Eşitlik ayrı durumdur | I04 ile aynı kaynak görünümü |
| REA-I06 | Yerleşik BB kimliği STD;Bollinger_Bands. Length20, basisSMA, sourceClose, StdDev2, offset0, Chart timeframe; MA seçenekleri SMA/EMA/SMMA(RMA)/WMA/VWMA. Style üç çizgi+background ve output labels içerir | ev_35362aace66f0ed7bf1a7254c986ce5d037b7164aea6bb62d33ba1e809e8e5e8; ev_ac954020c75e7e86f4d4b5dda400c9947d7c178044a3bd02a4638cff693d8b5a |
| REA-I07 | Veri penceresi seçilen barın tarih/OHLC/change/volume ve göstergelerin adlandırılmış çıktılarını ayrı gösterir. Legend ve veri penceresi tarihsel bara bağlıyken sağ eksen son değer etiketlerini göstermeyi sürdürebilir | ev_55dea4f246c9f36d2231d086f67c12614a525e6acc6d2aaef9fcf26357fcfe43; ev_b10b713a443d70521f8a9621d55fb61c5310d44cade24f9f7193a9cba06da9ff |
| REA-V01 | Symbol: candle body/border/wick ayrı, önceki kapanışa göre renk, precision/timezone. Status line: title/market status/chart values/bar change ve indicator titles/inputs/values ayrı | ev_26c0af659429dcd556aed363b909e89fbffd8fbc146658699beff35213ef3382; ev_d7363a351bfaf22c2a65923614d7f93c0406b7b784893fa8c212c70645018a44 |
| REA-V02 | Canvas: solid background, yatay/dikey grid, pane separators, crosshair, scale text12, hover navigation/pane buttons; top10%, bottom8%, right10bar boşluğu bu düzende görüldü | ev_d7363a351bfaf22c2a65923614d7f93c0406b7b784893fa8c212c70645018a44 |
| REA-V03 | Scale: çakışmayan etiketler, countdown, sembol/indicator/high-low/bid-ask görünürlük seçenekleri; time format ve interval değişiminde sol kenarı koruma. Eksen menüsü Auto/ratio lock/chart-only/invert/regular/percent/index100/log/left scale içerir | V02; ev_4e22e7770da3503a4e52c04c04c6570a4e8943ecaed3ef70f6de7035ebba5c12 |

**Uygulamaya aktarım:** Gösterge tanımı (girdi/hesap/çıktı) ile instance görünümü (pane/scale/style/visibility) ayrılmalı. Seçilen bar değerleri ile son bar değerleri UI'da açık ayrılmalı. MACD histogramı dört durumlu olmalı. BB için basis MA ve standart sapma hesap yöntemi aynı şey sayılmamalı; seed/warmup ve population/sample sapma henüz bağımsız mum fixture'ıyla doğrulanmadı. Platforma özgü tüm MA türleri ilk teslimde zorunlu değildir; desteklenen alt küme açık belirtilmeli.

**Deneme düzeltmesi:** Bollinger aramasında asenkron topluluk sonuçları nedeniyle bir topluluk göstergesi yanlışlıkla eklendi (ev_7d1aef...). Hemen Undo ile kaldırıldı (ev_c5c563...); bu göstergenin sonuçları yerleşik BB bulgusu sayılmadı. Ardından DOM'da STD kimliği doğrulanıp doğru yerleşik BB eklendi. Genel metin seçicisi yerine standart gösterge kimliği kullanılmalı.

**Sınırlar:** MA seed/NA davranışı, aynı kapalı OHLCV kümesiyle sayısal parity, pane resize/drag ve özel zaman dilimi hesapları henüz doğrulanmadı. Menü seçeneğini görmek, o işlevin bütün durumlarını test etmek değildir. Ayar incelemesi Cancel ile kapatıldı. Araştırma düzeninde Volume+yerleşik BB ve önceki çizimler duruyor; onboarding görsel engeli normal kapatma kontrolüyle kaldırıldı.

Kalıcı kanıt paketi: reports/rea-chart/rea-evidence-indicators-settings-live.json (93 kayıt, 49,185,420 byte); sonraki temiz ekran kaydı ayrıca son export'a dahil edilir.

## Canlı tur: çizim yönetimi

REA-M01: Nesne ağacından Fib sağ menüsü; template, visual order, interval visibility, group, clone, copy, rename, lock/hide/remove, go-to ve settings gözlendi (ev_d8129aee2d573ca939ac15f979ecf6215848e17861f2d9dfb3480ea4e28bf126).

REA-M02: Lock uygulandı; nesne ağacı ve menü Unlock durumuna geçti (ev_9109adff84a8470e186a99d829fa51cd07681f5361328611fb64e84ad56737d8). Sonra Unlock uygulandı. Bu, kilitli nesneyi pointer ile sürükleyememe testinin yerine geçmez.

REA-M03: Hide uygulandı; nesne ağaçta kaldı ve Show kontrolüne geçti (ev_0cf88bfefc95cabc342c903203d9bdb960da9a21c07a1176793b370f3c9e6dfa). Show ile geri getirildi. Interval visibility alt menüsü current and above/below/only/all seçenekleri içeriyor (ev_4a27a1eb65141cb43e2bde20e9cda9e186752084c6a2e6b0a57529e0cb9aeec7); interval filtresi değiştirilmedi.

Temiz tasarım referansı: reports/rea-chart/tradingview-bb-data-window.png. Seçilen geçmiş mum, BB seçim işaretleri, son değer etiketleri ve katman yoğunluğu birlikte görülebilir. Son kanıt paketi 99 kayıt / 49,609,040 byte içerir.


## Canlı tur: sade grafik, navigasyon ve sembol izolasyonu

- **REA-N01 — Çizimleri sadeleştirme:** Hide all drawings uygulandı; kontrol Show all drawings/pressed oldu. Volume ve BB legendleri kaldı, dört çizim nesne ağacında korundu. ev_6984d3fb1a4b6857435498fdf4783765015cc3c7518b6a5452336ad137db70a6. Son BTC görünümünde tekrar gizlendi ve Save sonrası All changes saved doğrulandı: ev_6a23e62f1374d9b1ae73db2588b7257cc712b3ec0b1323be0a698e35575dca24. Silme uygulanmadı; daha sonraki geometri kontrolleri için örnekler korunuyor.
- **REA-N02 — Interval menüsü ve geçiş:** Tick/seconds/minutes/hours/days/ranges grupları ve favorites kontrolleri görüldü. 1D mumdan 5m muma geçiş uygulandı; Volume/BB instance girdileri ve BTC çizim listesi korundu. ev_6984d3...; ev_63a59c55d9cc21552d4e42d6e25eb1ffa7816f8d5572658f73322c7d81a083c5. Tick/saniye bütün planlarda çalışır iddiası yok.
- **REA-N03 — Tarihe git:** Go to dialogu Date ve Custom range sekmeleri, tarih ve saat alanları sunuyor. 5m görünümde 2026-11-09 tarihi uygulandı; sonrasında Reset chart view ve Scroll to the most recent bar kontrolleri görüldü. Custom range iki tarih+saat alanıyla incelendi fakat aralık uygulanmadı. ev_c07ac4ab8bcfb6ffcecfb3fe4ee562a95813f048e893ea20d80e3e99a253c387. Son muma dön tıklaması timeout döndü (ev_46cf3a...); bu eylem başarılı kabul edilmedi. Tarihin tam ekran konumu ayrıca piksel fixture'ıyla doğrulanmadı.
- **REA-N04 — Görünüm aralığı mum intervali değildir:** Alt çubuktaki 1D (1 day in 1 minute intervals) çalıştırıldı; üst interval 1m, daha sonra chart legend intervali 1 oldu. Hemen sonraki capture'da üst 1m iken legend kısa süre 5 kaldı; settle sonrası eşitlendi. Bu geçişin toplam süresi ölçülmedi. ev_f8e93a1caa3c8d09cd0eef5629cf1a2dce3c4f0f9b2cedb3198c3d39c6329248.
- **REA-N05 — Çizgi tipi:** Candles→Line→Candles uygulandı. Line ayarı Close kaynağı ve Gradient stilini gösterdi; kaynak menüsünde O/H/L/C, HL2, HLC3, OHLC4 görüldü. Kaynak değiştirilmedi; mum/veri hesap eşitliği testi değildir. ev_51dd961775245921c840bb3afd7d9ccc0a6890acaf2ab6d474b6ac3825a53682; ev_4fe1fdc191d2f0ff05d9374ed368770be460c9585d6b37de03a5bc0300ea8470.
- **REA-N06 — Sembol izolasyonu:** Aramada spot/swap/derivative metrics ve borsa kimlikleri ayrılıyor. DOM'daki BINANCE:ETHUSDT.P satırı seçildi. ETH nesne ağacında yalnız Volume+BB vardı; BTC çizimleri yoktu. BB girdileri20/SMA/close/2 kaldı, Volume birimi ETH oldu. ev_5e9c65df8d5374095e438288b70076434abf6871394194c274ddd3d21e6e66bf; ev_0b57d03c27f24e23d2e8724d0452ef0516ce3a65d19ada4db6fc6c86e82bfeed.
- **REA-N07 — Geri dönüş ve test yöntemi sınırı:** Sembol seçimi adresin symbol query'sini kendiliğinden değiştirmedi. Sonraki scenario'da query'yi ETH yapmak tam navigation/reload oluşturdu ve undo geçmişi kayboldu; Undo change symbol timeout oldu. Bu yüzden undo kalıcılığı veya kesintisiz BTC→ETH→BTC state parity iddiası yok. Sonra arama UI'sıyla BTC'ye dönüldü; dört BTC çizimi geri görüldü, günlük interval ve gösterge ayarları yüklendi. ev_096c59b6c11d7021c82d018694107c90325f7a930f77f6f614703435c55fb128; ev_659f4b0054047d9c74383198b29b5293bba804598ec04d98fbeec522487a5d26. Son durum BTC/1D/Candles, araştırma çizimleri gizli ve kaydedilmiş.

**Plan gereksinimleri:** range preset ve candle interval ayrı alanlar; sembol anahtarı exchange/product/price type dahil olmalı; eski sembolün geç gelen sonuçları yeni grafiğe uygulanmamalı. Gösterge instance tercihleri ile sembole bağlı çizimler ayrı kapsamda tutulmalı. Geçişte başlık/veri/gösterge uyumu sağlanana kadar loading/epoch bariyeri kullanılmalı. Son gözlem bir gereksinim çıkarımıdır; TradingView sunucu mimarisi iddiası değildir.

Kanıt: reports/rea-chart/rea-evidence-navigation-symbols-live.json, 116 kayıt / 52,058,786 byte. REA'nın unknowns=0 metadata sayısı araştırmadaki açık soruların kapandığı anlamına gelmez. Drag/pointercancel, bağımsız kapalı mum gösterge parity, reconnect/history ve eşit yük performans hâlâ açık.

## Geniş canlı tur: metin, göstergeler, şablon ve iki tema

[Detaylı tur raporu](REA-INDICATORS-ANNOTATIONS-DESIGN.md) W01–W13 kanıtlarını ve kabul fixturelarını içerir. Metin oluşturma/stil/silme, şablon kapsam alanları, BB/RSI/ATR/VWAP yerleşik kaynakları ve girdileri, RSI paneli, koyu tema/panel kapalı görünüm ve dialog ölçümleri birlikte incelendi. RSI sabit seri dalında mevcut50 ile kaynak100 arasında somut sözleşme farkı bulundu; ortak platform fixture henüz yok. Tam paket reports/rea-chart/rea-evidence-wide-indicators-design.json:153 kayıt. Açık tema ve Volume+BB geri getirildi, çizimler gizli ve save doğrulandı. REA03 hâlâ devam ediyor.

## 11 Kasım: yönetim, şablon ve gerçek reload kontrolü

[Yönetim/çalışma alanı raporu](REA-MANAGEMENT-WORKSPACE.md) M10–M25 ile clone/rename/group/lock/hide, sayısal displacement ve iki Undo adımı, kilitli silme confirmation ve Undo/Redo, katman sırası, çizim şablonu save/apply/delete, klavye ve gerçek navigation reload kanıtlarını içerir. Fib ankraj/Reverse/log-Fib ve sayısal Long/Short input alanlarının reload kabulü artık gözlendi; önceki genel sayısal reload eksikliği bu belirli alanlar için daraltılır. Render etiketleri/timestamp/çok sekme/drag hâlâ açık. Tek üyeli grup bütün grup davranışı değildir. Makinece okunabilir örnekler contracts/rea-observed-fixtures-v1.json içinde.

## 11 Kasım: ölçek, etiket ve saat dilimi geniş turu

[Detaylı rapor](REA-SCALES-TIMEZONE.md) S10–S19: log/lineer/yüzde/index/invert, eksen sola/sağa, etiket çakışma açık/kapalı ve sabit1h mumla UTC+4→UTC karşılaştırması. Fib koordinatları korunurken log orta69282.0/lineer70000.0; yüzde formunda kanonik60000/80000. Sabit2026-11-07 mumu18:00→14:00; OHLCV ve BB çıktıları aynı. Bu timezone invariantı bağımsız gösterge matematik parity kabulü değildir.10 ekran kaydı ve2 ek fixture saklandı; yüzde referans tabanı/DST/log domain açık.

## 11 Kasım: odak, kapatma semantiği ve gerçek dar pencere turu

[Detaylı rapor](REA-FOCUS-RESPONSIVE.md) F10–F22. BB canlı önizlemesinde Cancel rollback, Escape/X keep davranışları ve numeric input fallback gözlendi. Bağlı viewport isteği doğrulanamadığı için responsive kabulü verilmedi; ayrı girişsiz REA launch profillerinde gerçek1280/1024/768 boyutlarıyla7 ekran doğrulandı. Grup/multi-select: modifier click araç desteği ve nested Basic-plan sınırı nedeniyle açık; geçici nesneler temizlendi. Görsel manifest reports/rea-chart/responsive-visual-manifest-20261111.json.

## 11 Kasım — tablo görünümü ve sayısal araştırma turu

[Veri tablosu ve numeric parity raporu](REA-TABLE-NUMERIC-PARITY.md) menü, tasarım ve hesap doğruluğunu birlikte genişletir. Kanıt paketi reports/rea-chart/rea-evidence-table-parity-20261111.json bu yeni REA oturumunun21 kaydını içerir; önceki234 kayıtlık paket ayrı korunur. BB20 finite-window13 satır; BB5/offset+2 28 satır; EMA20 recurrence31 adım doğrulandı. EMA ilk seed/NA/warmup, RSI/ATR/VWAP platform parity açık. CSV plan kapısı nedeniyle alınmadı. Ürün kodu değiştirilmedi.

## 11 Kasım — ATR/RSI/VWAP, hesap aralığı ve veri sunumu

[Detaylı tur](REA-ATR-RSI-VWAP-DATA.md) N20–N30 kayıtlarını, bağımsız araştırma hesaplarını ve sınırlamaları içerir. Paket reports/rea-chart/rea-evidence-atr-rsi-vwap-20261111.json,51 kayıt; önceki21 kayıt dahildir, eski234 kayıt ayrı korunur. Menü/tasarım araştırması smoothing, bağımlı alanlar, uzun dialog, günlük gizleme ve üst-zaman menüsüyle genişledi. HTF seçimi tamamlanmadı; on/off davranışı bilinmiyor.19 fixture farklı kanıt sınıfları taşır; hepsi exact parity değildir. Yeniden hesaplama tools/rea/verify-indicator-research.mjs ile yapıldı. Son durumda geçici göstergeler kaldırıldı, Volume+BB20 ve dört gizli çizim korundu, saved görüldü.

## 11 Kasım — veri akışı ve pointer geniş turu

[REA-LIFECYCLE-MARKET-POINTER](REA-LIFECYCLE-MARKET-POINTER.md), L10–L26. Paket89 kayıt; önceki51 dahil. Açık/kapalı/reload örnekleri,25sn partial offline/restore, iki eski1m pencere, Volume precision sınırı, spot/perp/mark ve gerçek VWAP hacim-yok hatası kaydedildi. Ordinary-CDP pointer fallback + REA koordinat okumasıyla tek endpoint ve Undo doğrulandı; helper kaydı REA Evidence diye sunulmuyor. Orijinal Fib bar-index farkı açık soru.27 fixture kanıt sınıflarıyla korunuyor; ürün testleri/uygulama yapılmadı.

## 11 Kasım — UTC ankraj, log gövde, HTF ve kaynak turu

[Detaylı rapor](REA-UTC-DRAG-HTF-RESOURCES.md).106 kayıtlık paket önceki89 kaydı içerir;17 yeni REA kaydı ve ayrı ordinary-CDP gözlemleri. Kalıcı Fib UTC ve güncel300-mum mapping doğrulandı; önceki gün indeks farkı açıklaması çıkarım. Log gövde hareketi/doğrudan Undo-Redo ve Escape-keep örneği eklendi. BB1D→1h seçim engeli aşıldı, WaitON/OFF31 ortak kapalı OHLCV satırı ve farklı output mapping kaydedildi.15sn resource sayacı FPS/leak benchmarkı değildir.31 araştırma fixture’ı; PLAN üst durum/sırası güncellendi, ürün uygulaması başlamadı.

## 11 Kasım — OHLC mıknatıs ve etkileşim geniş turu

[REA-SNAP-SELECTION-INTERRUPTIONS](REA-SNAP-SELECTION-INTERRUPTIONS.md):38 yeni REA kaydı ayrı paket, önceki106 korunur. Altı fixed-position weak/strong/off örneği;0/4/8/16 cursor örnekleri; held-preview ile panel dışı bırakma ve sekme geçişi/tekUndo; iki tree öğesinde Ctrl seçimi ve karışık kilit.20 PNG hash’li manifest; toplam36 araştırma fixture’ı. Gerçek pointercancel/OS blur ve mixed grup hareketi hâlâ açık. Geçici iki çizim/boş sekme temiz, dört perpetual çizimi gizli ve saved; ürün kodu değişmedi.

## 11 Kasım — mixed hareket ve hassas gösterge turu

[Detaylı rapor](REA-MIXED-PRECISE-INDICATORS.md):72 kayıt önceki38’i içerir,34 yeni. İki trend kontrol+mixed-lock pointer hareketi/tekUndo;300 sayısal OHLCV ile VWAP32/96 ve RSI14 uzun-burnin32/64; ATR8 precision31+55 tablo ve2 hedef recurrence, previous-close gap ayrışması. TouchStart timeout sonucu pointercancel bilinmiyor, cleanup tamamlandı.18 PNG hash manifesti ve40 araştırma fixture’ı; ürün kodu/testleri değişmedi.


## 11 Kasım — Geç revizyon ve bağımsız çizim hazırlığı

Daha yeni [gösterge sınırı turu](REA-INDICATOR-BOUNDARIES.md):8 inline+13 export olmak üzere21 ayrı REA kaydı, toplam47 fixture. Sentetik x/x grafikte32 kapalı günlük satırda RSI14 display100, mevcut ürünün sabit-girdi fonksiyonunda50; hidden numeric capture başarısız olduğundan exact internal parity iddiası yok. RSI1 için30 kapalı komşu karşılaştırması14 yükseliş100/16 düşüş0. Büyük periyotta runtime error ile boş çıktı ayrı kaydedildi. GeçiciRSI kaldırıldı ve düzen kaydedildi. Origin seed/NA/zero-volume açık; ürün değişmedi.

[Canlı geçiş ve kaynak analizi](REA-TRANSITIONS-REVISION-READINESS.md):82 kayıt, önceki72 dahil10 yeni; toplam44 fixture. Seri5/hızlı6 aralık seçimi, üç coin seçimi; iki eski-tag geliş olayı. Ağ geliş kanıtı ile ekranda stale rejection kanıtı ayrıdır. Market görünümü çizim restorasyonundan önce hazır olabilir. Yüklü hash-matched decoder ve SeriesDataSource statik guard seçilerek incelendi; ana grafik runtime dispatch ve missing-tag güvenliği genellenmedi. PLAN ve D12 güncellendi; ürün uygulaması başlamadı.


## REA04 kesinleşti — geniş araştırma kapanışı

11 Kasım kullanıcı kararıyla [birleşik son tur](REA-FINAL-NETWORK-DESIGN.md) ve [kesin geliştirme planı](REA04-IMPLEMENTATION-ROADMAP.md) tamamlandı.49 araştırma fixture; yeni6 REA kaydı ayrı. Offline cold reload hata sayfası ve online300 günlük snapshot gözlendi; warm catchup/dedup kanıtlanmadı. Gerçek üç viewport boyutu ölçüldü; transient plot ve0 DrawFrame nedeniyle stable responsive/perf kabulü yok. Açıklar G/T/QA sahiplerine taşındı. Araştırma bounded kapandı, ürün QA kapanmadı. Güncel plan5/27, sonraki G01; eski5/21 tarihsel. Somut geliştirme sorunu hedefli REA dönüşü tetikler.
