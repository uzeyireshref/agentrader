# Canlı araştırma: ölçek, etiket ve saat dilimi

11 Kasım 2026, Asia/Baku. REA03 araştırma eki. Araştırma düzeninde işlev ve görsel durumlar birlikte çalıştırıldı; ürün kodu değiştirilmedi.

Kanıt paketi: reports/rea-chart/rea-evidence-scales-timezone-20261111.json —219 kayıt,72,153,219 byte. Önceki ve başarısız işlemler dahildir; tüm araştırmanın veya ürün testlerinin tamamlanma sayısı değildir.

## Kanıt matrisi

| ID | Uygulanan deney | Kanıt |
| --- | --- | --- |
| S10 | Başlangıç sağ eksen: Auto ve Logarithmic seçili, invert kapalı. Karşılaştırma için yalnız Fib görünür, üç risk çizimi tekil gizlendi | ev_c6e9d2a37d09e950c1b0b6cddc78c2c9e1f1071ba84cbdb711608b81d9029357; ev_d5fe48740859411d576c43798dd6c941febe92f41420be51d47c22a1e881ab57 |
| S11 | Log-Fib açıkken log→lineer Alt+L geçişi; aynı ankrajlarla0.5 seviyesi69282.0→70000.0 | ev_788a03556ade6c757752ae9c5d903d7668069b14b50bac89b871787c4d850025; ev_cb7e4c5f7da98f530aac86a8b646e526e9f9b81582e5e9bccc15680e31e61518; ev_3c1b25983ece9ae19eb7136b8423f264a1d01a39f983107bcbc3767088e58edb |
| S12 | Alt+P yüzde ölçeği; Fib/BB etiketleri yüzdeye döndü. Koordinat formu60000/bar187 ve80000/bar249 olarak kaldı | ev_d2a1e16540ce05030ff6064882713efaf3be3393eff48169001a3b777934190e; ev_79fe386fd3f324165c40c2122bcdcbd9b143395c026c659bbb65278020d36357; ev_818f140f26c5ad4326c778a302518c9303f9dd11369c4ba5e2b0ff87101c2e6b |
| S13 | Indexed to100 uygulandı; örnek Fib etiketleri yüzdelik gösterimin100 fazlası | ev_8066c0dd356026b046959e8efbf1336422812b0b71ad13101b6e502ea2a5b888; ev_f248a73186e6ce7d2039fa95d2f5b1ea8a05b2356f1b3798a93fb3de1e5f1686 |
| S14 | Alt+I indexed görünümü ters çevirdi; eksen küçük değerleri yukarıda, büyükleri aşağıda gösterdi. Tekrar Alt+I ile geri alındı | ev_c502df0cbf71c57348fa4b0f24055db20babf0eec83bdf84eb86ac56ac0cea02; ev_f0ae0e3cb257d11371b56fc9aa7508ea54aac99988f08d4f13b4e07f2ce95b24; ev_1f8b2f37e15ea222f13b9f8f52f4425c27cec982a5a99dd3d5ded431bd9ccf3c |
| S15 | Regular'a dönüldü; Move scale to left çalıştırıldı ve sağa geri getirildi | ev_1f8b2f37e15ea222f13b9f8f52f4425c27cec982a5a99dd3d5ded431bd9ccf3c; ev_aecab78bb24ee54622036c9dac7c9c8a58c603967024526e7083bf0424496fbe; ev_86478334a4253491e05ff3f8f7f43290b2cd80b29db62a55654969bc68dab4dd |
| S16 | Labels alt menüsü incelendi; No overlapping labels kapatılıp yeniden açıldı ve iki ekran kaydı alındı | ev_86478334a4253491e05ff3f8f7f43290b2cd80b29db62a55654969bc68dab4dd; ev_2ba2a2b16bc88abf3f420f6ec038d3601750460ff5c324de3cddf33017d261f4; ev_f185f67641032cf8fbfec6746e43e2339f759057e83de4c7ea316c1b51535638; ev_b3959fd2b438c12e2a9344226f231d590d7ae4b3a5a2293b6ef2597d4882d52f; ev_c96e36a4d3f409a5589df32f3c1a1b524df1f59e2d3471275f6f035889a9a938 |
| S17 | Saat dilimi menüsü;1h grafikte UTC→Dubai/UTC+4 uygulandı, zaman ekseni ve saat yeniden etiketlendi | ev_0c3711df14c5f8c383eed917d28f15e167d0c3aa72a291e0996264b347c84829; ev_0d6aeb728cbf7dba78b70563e33423a812a27ccd0bdda2a822771cf6f54f8332; ev_e0dcb2bb9a6844e298e87c66af3b519340b5ddb286895bc363dc37b464d6c0b0; ev_372894c11fb62abc82b9cf403e0f14e9179dfd937adf53c53d9595f40d0e40af; ev_54096cbefbe4e4f06da622ed50eb722463517597f14e3bfad43ac271a2847fc7 |
| S18 | Zaman imleci kilitlenerek aynı kapalı geçmiş mum UTC+4 veUTC veri penceresinde karşılaştırıldı | ev_13a2bfdca0a60312db18ce8f508def78158758802318e3c180d7d369af6600d7 |
| S19 | Kilitli zaman imleci kapatıldı;1D/log/sağ eksen/UTC geri getirildi; Fib koordinatları yeniden okundu; çizimler global gizlendi, Ctrl+S ve saved durumu görüldü | ev_0c3de7aa0b76ad3b633d019078df59084bf06edae88ac1447b964017c6c99305; ev_94d6eca75bea72bc29f4e8021a7252c1f81f3f95896fc1a63baff2f4d7c484cb; ev_ecef002e65d8d87dae094a0e42ac335d920aea9401b4789adff1522992da00b8 |

## Hesap geometrisi ve gösterim birimi

Ankrajlar60000/80000, bar187/249; Reverse açık, log-Fib tercihi açık. Log görünümde0.5=69282.0; lineerde0.5=70000.0. Log-Fib tercihi korunurken aktif fiyat ölçeği, etkin interpolasyon yolunu değiştiriyor. Bu yalnız font/etiket dönüşümü değildir.

| Fib oranı | Lineer fiyat | Log-Fib fiyatı |
| --- | --- | --- |
|0 |60000.0 |60000.0 |
|0.236 |64720.0 |64215.0 |
|0.382 |67640.0 |66969.6 |
|0.5 |70000.0 |69282.0 |
|0.618 |72360.0 |71674.3 |
|0.786 |75720.0 |75223.4 |
|1 |80000.0 |80000.0 |

Fiyatlar ekrandaki0.1 precision ile okunmuştur. Önceki kaynak analizindeki log koordinat interpolasyonuna uygun örneklerdir; tüm alanlarda exact rational eşitlik iddiası değildir.

Yüzde ölçeğinde Fib ve BB legend/eksen değerleri dönüşüyor; OHLC alanları fiyat kalıyor. Veri penceresinde de OHLC fiyat, BB çıktıları yüzde görüldü. Aynı pencerede farklı birimler bulunabileceğinden her alanın ölçü birimi açık olmalı; görüntü metni kanonik bot fiyatı olarak parse edilmemeli.

Gösterim örnekleri: Fib0=-20.95% ve index79.05;0.5=-7.78% ve92.22;1=5.39% ve105.39. Bu yuvarlanmış örneklerde index=100+percent. Yüzde referans tabanının seçim algoritması bu tur bağımsız kapalı veriyle çözülmedi. Farklı viewport/visible-range anlarında yüzdeler değişti; mutlak yüzde değerleri sabit algoritma fixture'ı sayılmaz. İlk senaryolar tool default1280×720 geçici viewport kullanıyordu; indexed ve sonraki senaryolarda1536×776/DPR1.25 açık istendi. Ekranlar1920×970. Görüntü durumlarını eşit veri/yük benchmark'ı diye sunmuyoruz.

Invert görüntüyü dikey çeviriyor; Fib oranları, yön tercihi veya kanonik fiyat sırasının değiştirilmesi gerekmiyor. Eksenin sola alınması price plot başlangıcını, legend ve etiket alanlarını kaydırıyor. Grafik ankrajı ekran x/y'siyle tutulursa kayma doğar.

Sola taşıma sonrası DOM eksen kimliği price-axis-A'dan price-axis-Z'ye geçti. Eski seçiciyle geri dönme denemesi timeout oldu; DOM yeniden okunup doğru eksen üzerinden sağa dönüş uygulandı. Bu ürün API sözleşmesi değil, araştırma otomasyonunda kararlı seçici gereksinimidir.

## Etiketlerin tasarımı ve çakışma

Labels menüsü symbol name/last price/previous day close, high-low, bid-ask, indicator name/value, countdown ve overlap kontrolünü ayrı gösteriyor. Bazı seansla ilgili seçenekler Binance futures bağlamında disabled idi; tüm menü girdileri bizim ürüne taşınmayacak.

No overlapping labels kapalıyken son fiyat etiketi ile yakın BB alt bandı etiketi üst üste geldi ve yeşil etiket okunamaz oldu. Açıldığında ayrı kutular görünür oldu. Bu gözlem kutu yerleşimidir; fiyat çizgisi veya hesap değeri yer değiştiriyor anlamına gelmez. Çakışma çözümünün öncelik sırası, minimum aralık, connector çizgisi ve çoklu pane algoritması ölçülmedi.

Temel ürün ihtiyacı: son fiyat+countdown, gösterge/çizim fiyat etiketleri ve okunur çakışma yönetimi. Yüzde/index/invert ve sol eksen kullanım ihtiyacına göre eklenebilir; hepsi ilk çekirdeğin zorunlu bitiş koşulu yapılmamalı. Lineer/log ise seçilmiş temel kapsamda kalır.

## Sabit mumla saat dilimi kontrolü

1h grafikte normal UI üzerinden Lock vertical cursor line by time seçildi. Aynı geçmiş mum veri penceresinde kilitli kaldı. Dubai(UTC+4)→UTC geçişinde aşağıdaki alanlar gözlendi:

| Alan | UTC+4 görünümü | UTC görünümü |
| --- | --- | --- |
| Tarih |2026-11-07 |2026-11-07 |
| Saat |18:00 |14:00 |
| Open |75903.0 |75903.0 |
| High |75950.1 |75950.1 |
| Low |75895.0 |75895.0 |
| Close |75916.3 |75916.3 |
| Vol |881.64 |881.64 |
| BB Basis |75936.1 |75936.1 |
| BB Upper |76106.5 |76106.5 |
| BB Lower |75765.7 |75765.7 |

Burada Dubai seçildi; menüde Baku görülmedi. UTC+4 ofsetinin bu tarihte eşit olması Dubai IANA bölgesinin Asia/Baku kimliğiyle aynı olduğu anlamına gelmez. Ürün kullanıcının gerçek IANA saat dilimini saklamalı; DST ve tarihsel kural davranışı ayrı fixture ister.

Last day change alanı iki capture arasında değişti; bu alan kilitli tarihsel mumun OHLC'si gibi sabit kabul edilmedi. Açık piyasa fiyatının güncellenmesi ile sabit mumun göstergeleri ayrılmalı. Bu test timezone gösterim değişmezliğidir; Binance API/TradingView ham veri parity'si veya BB'nin bağımsız matematik doğrulaması değildir.

## Kabul işleri ve kalan sınırlar

- Kanonik price/time, scale transform, Fib calculation mode ve output formatter ayrı sürümlü alanlar.
- Ürün/bot aynı ankrajları okumalı; yüzde/index etiketi kanonik fiyatı değiştirmemeli.
- Panel/eksen tarafı/viewport değişiminde anchoring ve hit testing; seçili tutamak ile floating toolbar çakışması; üst legend üzerine çıkan extension etiketleri görsel kabulde ele alınmalı.
- No-overlap açık/kapalı ve son fiyatın gösterge etiketine yaklaşması ayrı görsel fixture.
- Timestamp UTC tutulmalı; timezone yalnız sunum kuralı olmalı. Gün/hafta/seans hesap başlangıcı ayrıca tanımlanmalı.
- yüzde tabanı/visible range algoritması; negatif/sıfır log domain; invert drag; auto/manual/ratio lock; DPR alt piksel; DST/seans sınırı ve bağımsız veri/gösterge parity hâlâ açık.
- Crosshair lock işleminde ilk menü checked idi, tekrar tıklanarak kapatıldı. Tam keyboard/focus ve touch kabulü yapılmadı.

Son durum: BTCUSDT.P/1D/Candles; sağ log ölçek, invert kapalı, UTC, No overlapping labels açık, Volume+BB. Üç risk çizimi ve Fib'in tekil görünürlüğü eski görünür durumuna getirildikten sonra dördü global gizlendi; kaydetme doğrulandı. Fib60000/80000 ve187/249 tekrar okundu. Yeni nesne oluşturulmadı.

REA03 açık. Bu turdaki ekranlar ve sayısal zaman örneği REA04 plan girdisidir; geliştirme başlamadı.
