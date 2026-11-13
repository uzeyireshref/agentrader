# Canlı araştırma: çizim yönetimi, şablon ve çalışma alanı

11 Kasım 2026 (Asia/Baku). REA03 eki. Bu tur ürün kodunu değiştirmez; önceki beş tamamlanmış çekirdek işin durumunu sıfırlamaz. Grafik tasarımı işlevlerle birlikte incelenmiştir.

Kanıt paketi: reports/rea-chart/rea-evidence-management-workspace-20261111.json —189 kayıt,66,791,840 byte. Paket önceki turları ve başarısız denemeleri de içerir; kayıt sayısı test veya tamamlanmış özellik sayısı değildir.

## Uygulanmış senaryolar ve kanıt

| ID | Uygulanan işlem / sonuç | REA kanıtı |
| --- | --- | --- |
| M10 | Fib Clone; nesne ağacında ikinci Fib ve seçili kopya | ev_fe689d4b271c4f41395836570dee6f1022316bb82fc406c971d9e8d00c881ed4 |
| M11 | Kopya inline Rename ile REA Geçici Fib Kopyası adını aldı; tek üyeli grup oluşturuldu | ev_499cd334043e8431dca1fb3ebd7e3148217592e3a8561af70f034efb8f339e72; ev_b9e96d3cee891a09e4d4a586342a4dce930128dc96a73b517f98fa6ab14c673a |
| M12 | Grup rename, lock ve hide uygulandı; grup ve çocukta Unlock/Show durumları görüldü; Show ile geri getirildi | ev_ac44d6006dbe8e2bec703aeb9391e317d34b93e6b107382f7e7ed1ffa3b4f1e0 |
| M13 | Grup Settings: Style, Displacement, Visibility. Displacement fiyat için +/−/÷/×, bar için +/− kabul ettiğini açıklıyor | ev_92b8b592f05b9bd6e4be33beda801a3ee91d76c4d4165fc8baec82af345bc9e0; ev_787f4f8150d200cd2a0ceb5041ef3c32098904963c0895d0dfcf37ad0a0141f4 |
| M14 | Kopya baseline:62287.1/bar187;83049.5/bar249. Grup formunda fiyat+1000/bar+2 uygulandı;63287.1/189 ve84049.5/251 okundu | ev_33494a78db3875b280609e9d7412c7bb65b13955da911d51f453cd1ab737bba5; ev_8fd1378d4cbdc542b8c36436fde3ab5fe92b559e6d970b944afa3c558a44125f |
| M15 | İlk Undo yalnız barları187/249 yaptı; fiyatlar+1000 kaldı. İkinci Undo baseline fiyatları geri getirdi | ev_8c12fb8ad1f9e417b885199b686ca6a506899840796e571f84de51a80eeddc9d; ev_5639d5daa2d89a8407986713912901ba0da0c9b7e33c6f71ed9e4d91a9d02977 |
| M16 | Kilitli geçici grup silme isteği ayrı confirmation açtı. Onay sonrası grup/kopya kaldırıldı; Undo grubu geri getirdi; Redo tekrar kaldırdı | ev_38883b1e898c3ae9b33088d47080df8f9067dc42af22cd1cb91a43119727bb4e; ev_9cbe553d60411677bf39cd61d11f8f8cddf85cd5bb7ccf8eece16ef1e21211f5; ev_e1f430b3c415d99ae8b81b9fb330d3af27ee478f6f931ed08d431e177dc69c30; ev_11baa05871e219141fe5ae0049792c21e837fdd3645b72f5145910f2e7a0f863 |
| M17 | Send to back Fib'i nesne ağacında BB ve diğer çizimlerin altına taşıdı; Undo ile eski sıra geri getirildi | ev_8569bb9d67fb7e1876a5d21dd61eb20f622bc5476993bf299c445b31ad99ab8e; ev_c7cf425e22b7ad59ba37c7afb4f9284d5d955e3707313998c8e9b43f5c9c9cad |
| M18 | Fib çizim şablonu Save as ile oluşturuldu. Reverse kapatılıp kaydedildi; şablon yeniden uygulanınca Reverse açık oldu. Ankrajlar60000/bar187 ve80000/bar249 kaldı | ev_0080ac6dc5de04590f31840774ae705e2991818197b40eb6e7ab66b61c704b38; ev_d83f9384b45523ea1b81b90cf185459c7f2a9123f2f5f2c8a63df07c7ff9bcba; ev_469e513a9b5265bc90c435880e06180249946a0a9ae696d65a0669c9ca2543a8 |
| M19 | Geçici şablon satırında Remove, sonra confirmation Yes ile silindi. Yeniden yüklemeden sonra Template menüsünde sadece Save as/Apply defaults kaldı | ev_49fe468a5520cc56d79b07c8b56b01de0076fd2246fbbc7a8556f95ead098e41; ev_0bf1f1823419c25504aa908c86d2186e012680ab878e8840cf937c4d4b426951; ev_9a7be074a618ae73848efdebc0b63e9e6b48cf03334b3826e229e7c9db679427 |
| M20 | Canlı kısayol yardımında chart/drawing kapsamı incelendi; Alt+D veri penceresini, Alt+G Go to dialogunu açtı | ev_bfc389517a73a3b438972d0fafe6a266da05f8447ff0484d5e14902527edca90; ev_532494d9ad3fe8663be48c19a9734b6f37db5c0be5311b39f2328285e15bc853 |
| M21 | Virgül Change interval alanını açtı;30+Enter30m; tekrar virgül/D+Enter günlük mum getirdi | ev_3aec7322bfcbb879d2a504b61ce6613e55c29cb9e220ba5abab995cfdf3c42ab; ev_12f9dd7cc8ead274eec99d55207bd56c2c3d4491d0ea7e8fa23aad0e44868a7f |
| M22 | Layout menüsü Save/Autosave/Share/Copy/Rename/Download/New/Open ve recent layout içeriyor. Save uygulandı; All changes saved görüldü | ev_5f04c8b5be4d5877b000d242971681ebad2b4b4d207da65f1fa457085b9e5ac5; ev_1ecfa9c5628afa5eeb56f1aeef1693ab7038116f1a546a76be555373af69524e |
| M23 | Gerçek sayfa navigation/reload sonrası Fib koordinatları, Reverse/log-Fib, dört orijinal çizim ve BB korundu | ev_9a7be074a618ae73848efdebc0b63e9e6b48cf03334b3826e229e7c9db679427 |
| M24 | Reload sonrası Short ve her iki Long Inputs ayrı açıldı; aşağıdaki alanlar tekrar okundu | ev_00a01c6cb88d68f51a5dcb30f7180917c01eec17be075252dac8436ad76d87b2 |
| M25 | Geçici nesneler temizlendi, dört orijinal çizim gizlendi; Ctrl+S sonrası All changes saved | ev_dee2ae511ebc9bd6ef2a1e9bfd5e0d069e5482e5be375e526f4859affdaefd8d; ev_c487e9542c36e9b78dbd9b6fb8c70950057216239c3804b1f06b04ac0d1e15a0 |

## Sayısal bulgular

### Clone, lock ve grup işlemi

Orijinal Fib60000/80000; Clone sonrasında kopya62287.1/83049.5, barlar187/249 olarak okundu. Bu örnekte Clone tam aynı koordinatlı çoğaltma değildir. Log görünümdeki kaydırmanın kesin algoritması ölçülmedi; sabit fiyat offseti veya her durumda aynı kopya politikası varsayılmaz.

Tek üyeli grup lock/hide durumlarını çocuğa yansıttı. Buna rağmen grup ayarlarından sayısal Displacement yapılabildi. Lock'un yalnız pointer taşımasını mı yoksa hangi işlem türlerini engellediği ayrıca belirlenmeli. Kopyada deneme yapıldı; orijinal geometriler topluca taşınmadı.

Fiyat ve bar displacement aynı formda girildiği halde iki Undo adımı oluştu. Bizim uygulamada bir Apply'ın tek atomik komut olması ürün kararı olarak değerlendirilmeli; referansın bu davranışı körlemesine kopyalanmamalı. Displacement Redo denemesinde ara settings açma/Cancel akışından sonra Redo kontrolü bulunamadı ve timeout oldu; tam displacement redo parity iddiası yok. Ayrı silme Undo/Redo döngüsü ise dialog açılmadan doğrulandı.

Çok üyeli/karışık kilitli grup, iç içe grup, grup çözme ve çoklu seçim modifier davranışı bu tur uygulanmadı. Tek üyeli örnek bütün grup davranışlarına genellenmez.

### Reload sonrası alan karşılaştırması

| Nesne | Hesap / lot / risk / kaldıraç | Entry / target / stop | Tick alanları |
| --- | --- | --- | --- |
| Sayısal Long |10000 /1 /1% /10 |70000 /74000 /68000 |40000 /20000 |
| Sayısal Short |10000 /1 /1% /10 |70000 /66000 /72000 |40000 /20000 |
| İlk varsayılan Long |1000 /1 /25% /10000 |72904.3 /78829.6 /66979.0 |59253 /59253 |

Bunlar hayalî araştırma girdileridir; risk veya kaldıraç önerisi değildir. Önceki girilmiş alanların reload sonrası korunması doğrulandı. Qty/R:R/amount etiketlerinin reload sonrası ayrı render kontrolü, timestamp/uzunluk ankrajları, invalid girdi ve farklı tick/lot sembollerinde parity hâlâ açık.

Fib60000/80000; bar187/249; Reverse açık, log-Fib açık korundu. Şablon silinmesi reload sonrası doğrulandı. Bu, tüm şablon türleri veya çok sekmeli kayıt yarışı kabulü değildir.

Global Hide all drawings yeniden yüklemede görünür duruma döndü. Sonrasında çizimler tekrar gizlendi. Dolayısıyla “save olduysa global gizleme de kalıcıdır” varsayımı yapılmamalı; oturum sunum durumu ile kaydedilmiş nesne görünürlüğü ayrılmalı.

## Tasarım ve klavye sonuçları

- Nesne adı inline input ile düzenleniyor; kullanıcı içeriği ile tool kind ayrı kalabiliyor. Clone, group ve template isimleri ayrı kimlikler taşımalı.
- Grup/çocuk kilit ve göz ikonları birlikte okunabilir olmalı. Global gizleme ile tek nesne/grup gizleme farklı durumlar; yalnız sol araç çubuğu ikonu yeterli açıklama olmayabilir.
- Katman ağacı sırası render sırasıyla ilişkili. Sıra değişimi kanonik hesap sonucunu değiştirmemeli.
- Group Settings tek bir Fib dialogu değil; Style/Displacement/Visibility sekmeleriyle ortak özellik arayüzü.
- Kilitli çizimleri silme ve şablon silme ayrı confirmations gösteriyor. Bu tur Don't show again seçilmedi. Bizde yıkıcı grup işleminin etki kapsamı ve geri alma imkânı görünür olmalı.
- Şablon satırındaki Remove yalnız satır üzerine gelince ortaya çıkıyor; ilk doğrudan tıklama timeout oldu. REA'da hover eylemi yok. Normal UI üzerinden satıra orta tuş tıklaması ile pointer satıra taşındı, kontrol görünür oldu ve Remove tıklandı. Bu bir API/state müdahalesi değildir. Orta tuş bazı çizimlerde silme kısayolu olabileceğinden bu yöntem yalnız şablon menüsü satırında kullanıldı.
- Canlı yardımda Ctrl+Z/Y/S, Alt+D/G/L/P/I, araç kısayolları ve selection'a bağlı ok tuşları listeleniyor. Yalnız M20–M21 ve Ctrl+S bu tur fiilen çalıştırıldı; tüm kısayollar test edildi denmez.
- Grafik, çizim, modal ve metin alanı için ayrı odak kapsamı gerekir. Tek tuşla sembol/interval araması; çizim seçiliyken ok tuşuyla taşıma; modaldayken Escape; inputtayken normal metin girişi birbirine karışmamalı. Metin odak izolasyonu negatif senaryosu henüz uygulanmadı.

Temiz son görünüm: reports/rea-chart/tradingview-management-clean-20261111.png. Grup kilit/gizli durumları AX/DOM kanıtlarında kayıtlıdır; bu tur bu durumlara ayrı piksel screenshot alınmadı. Daha önceki metin/pane/iki tema görselleri tasarım şartnamesine bağlı kalır.

## Plana aktarılacak kabul işleri

| İş | Gereken kabul |
| --- | --- |
| T07 yönetim | İsim/kind ayrımı; clone offset politikası; group lock/hide; katman sırası; etki kapsamı belli silme ve Undo/Redo; mixed/nested group testleri |
| T02/T05/T06 geometri | Grup taşıması her ankrajda aynı tanımlı fiyat/bar dönüşümünü uygular; log view ekran offseti ile kanonik offset ayrılır |
| T14 ve geniş çalışma alanı paketi | Çizim/gösterge/layout şablonu ayrı; çizim şablonu koordinatları taşımaz; apply/cancel/rename/delete ve reload; global visibility oturum tercihi ayrı |
| Navigasyon/klavye | Öncelikli focus scope; metin alanında kısayol sızıntısı yok; interval parse ve cancel; undo action label doğru |
| Kalıcılık | Sayısal Long/Short/Fib reload fixtureları; çok sekme/409 ve yarış hâlâ zorunlu |
| Tasarım | Inline rename, child/group icons, selection/disabled, katman ağacı ve destructive confirmation; sadece normal chart screenshot kabul değildir |

## Kalan sınırlar

Serbest pointer drag/pointercancel, hit testing, snap mesafesi, karışık/çok üyeli grup, negatif/çarpan displacement, tam displacement redo, bağımsız OHLCV gösterge parity ve EMA seed, geçmiş/reconnect ve eşit yük performansı tamamlanmadı. Hesaplı Long/Short/Fib için belirli alanların reload kabulü artık gözlenmiş durumda; önceki raporlardaki genel “sayısal reload açık” ifadesi bu alanlar için bu kayıtla daraltılır.

Kaynak/kayıt/plan dosyaları dışında ürün kodu değiştirilmedi. REA03 araştırması açık kalır; REA04 seçilmiş profesyonel grafik yol haritasını bu sonuçlarla genişletmeli.
