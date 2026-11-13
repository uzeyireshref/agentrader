# Grafik etkileşim sözleşmesi

9 Kasım 2026 · B1 tamamlandı. Bu dosya B2–B5 ve çizim görevlerinin uygulayacağı hedef davranışları tanımlar. Hedefler bu tur uygulanmış sayılmaz. Kaynak: mevcut App/DrawingLayer kodu, sabit Lightweight Charts 5.2.1 seçenekleri ve [gerçek App/Chromium ölçümü](../../reports/chart-interaction-baseline-20261109.json).

## Mevcut davranışın ölçümü

`python scripts/measure_chart_interactions.py` kontrollü 300 mum, 1400×1000 viewport, gerçek fare ve wheel olaylarıyla çalışır. Native seçenekler ve mantıksal zaman aralığı okunur. Kullanıcı çalışma alanı/API'sine yazılmaz. Fiziksel trackpad/touch, raster ve çoklu DPR kabulü değildir. 13 gözlem, sıfır yakalanmamış sayfa hatası.

| Davranış | Ölçülen mevcut sonuç | Karar |
| --- | --- | --- |
| Dikey tekerlek | Görünür logical genişlik 116 → 105,36; zoom çalışıyor | B2: imleç odağı ve sınırlar açık kabul koşullarına bağlanacak |
| Sol tuşla boş grafiği sürükleme | from 190 → 172,09; geçmişe kaydırma çalışıyor | B2: korunacak, çizim moduyla çakışma sınanacak |
| Geçmişteyken yeni mum | aralık 172,09–288,09 değişmedi; 300 → 301 mum | Bu davranış korunacak |
| Yatay wheel | Aynı zoom genişliğinde zaman aralığı kayıyor | B2: yatay/dikey ve birleşik delta ayrımı doğrulanacak |
| Son muma dönme | Zoom sonrası aralık yeniden 190–306; yakınlaştırma sıfırlanıyor | B4: son muma gitme ve görünüm sıfırlama ayrılacak |
| Sağ fiyat eksenini sürükleme | autoScale true → false; fiyat koordinatı değişti | B3: manuel/otomatik durum görünür olacak |
| Manuel ölçekten sonra son muma gitme | autoScale false kaldı | B3/B4: son muma gitme manuel ölçeği koruyacak; ayrı sıfırlama otomatiğe döndürecek |
| Fiyat eksenine çift tıklama | autoScale false → true | Korunacak, görünür otomatik ölçek kontrolüyle aynı işlev |
| Zaman eksenine çift tıklama | Motor varsayılan bar aralığına döndü; toolbar dönüşüyle aynı aralık değil | B2/B4: sadece yatay ölçeği sıfırlama olarak açıklanacak |
| Çizim oluşturma modunda wheel | Zoom çalışıyor | Korunacak; ilk nokta UTC/fiyatı viewport değişince değişmeyecek |
| Oluşturma modunda Escape | Taslak/yönerge kapandı; kayıt yok | Korunacak; sürükleme iptalinin bütün yolları C2'de ayrıca sınanacak |

Motor seçenekleri şu an önemli ölçüde varsayılan: touch yatay/dikey drag ve pinch açık, mouse kinetic kapalı, touch kinetic açık, minBarSpacing=0,5, üst bar aralığı sınırı yok, resize sırasında zaman aralığını kilitleme kapalı. Açık seçenek fiziksel cihazda başarılı kullanım kanıtı değildir.

## Uygulanacak davranışlar ve bitiş koşulları

| ID / görev | Hedef davranış | Doğrulama |
| --- | --- | --- |
| I01 / B2 | Grafiğin içinde dikey wheel zaman zoom'u yapar. İmleç altındaki logical konum odağı korunur. Sayfa grafiğin dışından normal kayar. | En az üç imleç konumu ve iki zoom yönünde native koordinat farkı ≤1 CSS px; zoom sınırına ulaşma ayrı değerlendirilir. |
| I02 / B2 | Yatay wheel zaman ekseninde pan yapar. Çapraz delta tek gesture içinde iki kez uygulanmaz. | Yatay, dikey ve çapraz delta senaryoları; aynı gesture için tek beklenen değişim. Fiziksel trackpad ayrıca doğrulanır. |
| I03 / B2 | Sol tuşla boş alanı sürüklemek yatay geçmiş gezinmesidir. Fiyat otomatik ölçekteyken veri dışına rastgele dikey kaydırılmaz. | Native zaman aralığı ve fiyat autoScale kontrolü; hareket çizim revision'ı oluşturmaz. |
| I04 / B2 | Zoom sonlu ve kullanılabilir sınırlar içinde kalır. Başlangıç hedefi bar başına 2–50 CSS px; B2'de dar ekran/kısa geçmiş ölçümüne göre gerekçeli ayarlanabilir. | Aşırı wheel, 20 mum ve 4.000 mum; boş/bozuk koordinat yok. Nihai sayılar B2 kanıtına kaydedilir. |
| I05 / B2 | Geçmişe gidildiğinde canlı tick kullanıcıyı son muma çekmez. Eski mum eklenirken aynı UTC bölgesi ekranda kalır. | Geçmiş pan + tick/rollover + prepend; native time koordinatı sapması ≤1 CSS px. |
| I06 / B3 | Fiyat ekseni drag manuel ölçeğe geçirir; otomatik/manuel durum görünür ve klavyeyle erişilir. Otomatiğe dönmek görünür veriyi sığdırır. | Mikro fiyat, büyük fiyat aralığı, negatif olmayan desteklenen fiyatlar, RSI/hacim pane değişimi. |
| I07 / B3 | Fiyat eksenine çift tıklama yalnız ilgili eksenin otomatik ölçeğini açar. Zaman zoom'u, gösterge seçimi ve çizim geometrisi değişmez. | Aralık/seri/çizim karşılaştırması; görünür kontrol ile aynı son durum. |
| I08 / B4 | Son muma git: mevcut yatay zoom genişliğini ve manuel fiyat ölçeğini koruyarak son mumu görünür yapar; yaklaşık 7 bar sağ boşluk bırakır. Yeni mum takibi bu bölgeye dönünce yeniden etkin olur. | Yakın ve uzak zoom, manuel/otomatik fiyat ölçeği, yeni mum; yakınlaştırma genişliği değişmez. |
| I09 / B4 | Görünümü sıfırla: seçili markette yaklaşık son 110 mum ve sağ boşluk; ana fiyat ölçeği otomatik. | Zaman aralığı hedefi [max(0,n−110), n+6]; geçerli kısa geçmişte hata yok. Çizimler, gösterge seçimi, kayıtlar ve kullanıcının pane yükseklikleri korunur. |
| I10 / B2+B4 | Zaman eksenine çift tıklama yalnız bar aralığını varsayılana döndürür; fiyat ölçeğini değiştirmez. Tüm görünümü sıfırlama kontrolünün yerine geçmez. | Önce/sonra barSpacing ve fiyat autoScale karşılaştırılır; ipucu davranışı açıklar. |
| I11 / B2+C2 | Oluşturma modunda wheel/pan gezinmeye devam eder. Taslak ilk noktası UTC/fiyata bağlıdır; gezinme hareketi yanlışlıkla nokta/kayıt üretmez. | İlk nokta→zoom/pan→ikinci nokta; drag sonundaki click ayrımı; Escape taslağı kaydetmez. |
| I12 / C1+C2 | Kayıtlı çizim gövdesi/tutamaç sürüklenirken grafik pan/scale kilitlenir. Bitiş/iptalde önceki seçenekler tam bir kez döner. | Pointer sahipliği, Escape/blur/capture-loss/dışarı bırakma/market geçişi. Testlerde yeni varsayılanlar eski seçenekleri ezmez. |
| I13 / B5 | Resize/tam ekran odağı ve çizim hizasını korur. Normal resize mümkün olduğunca aynı UTC aralığını korur; kendiliğinden son muma gitmez. | 390×844 ve masaüstü, fullscreen giriş/çıkış, native/SVG karşılaştırması. |
| I14 / B5 | Grafik alanı odaktayken klavye alternatifleri: +/− zoom, sağ/sol gezinme, End son muma gitme; sıfırlama ayrıca etiketli düğmeyle erişilir. | Input/select/textarea/contenteditable içinde tuşlar yazmayı bozmaz; görünür focus, düğme etiketleri ve durum bildirimleri. |
| I15 / B5 | Dokunmada yatay grafik pan ve pinch hedeflenir; sayfayı dikey kaydırma grafikte hapsolmamalıdır. | Gerçek cihazda tek/iki pointer davranışı; sentetik wheel fiziksel trackpad/touch yerine sayılmaz. Çizim düzenleme sahipliği korunur. |

## Değişiklik sırası ve korunacak doğruluk

1. B2: wheel/pan/zoom seçeneklerini açık hale getir; odağı, sınırları ve history prepend konumunu doğrula. Çizim oluşturmayla gesture çakışması varsa önce gider.
2. B3: fiyat ölçeği durumunu ve otomatiğe dönüşü görünür kıl; mikro fiyat ve pane testleri.
3. B4: mevcut tek dönüş düğmesini iki ayrı anlama ayır; son mum dönüşü zoom'u korusun, sıfırlama varsayılan görünümü geri getirsin.
4. B5: boyut/fullscreen/klavye/mobil ve uygun ortamda fiziksel dokunma kabulü.

Her değişiklikte A5'in etkilenen doğruluk kanıtları yeniden açılır. UTC/fiyat geometrisi, mum kapanışı, veri tazeliği ve kayıt sürümü korunur. Bu sözleşme ek gösterge, yeni çizim türü veya bot bağlantısı talimatı değildir. Açık kabul kapsamları PLAN.md içindeki R01–R07 ile birlikte izlenir.

## B2 uygulama durumu

B2 tamamlandı: I01–I05, I10 ve I11'in kontrollü masaüstü fare/wheel kapsamı [18 kontrolde](../../reports/chart-navigation-browser-20261109.json) geçti. 2–50 CSS px bar aralığı korundu; 20/4.000 mumda doğrulandı. Çapraz delta baskın eksende bir kez işlenir, eşitlikte dikey eksen seçilir. Grafik üstündeki SVG çizim alanından wheel motor köküne yönlendirilir; drag kilidi korunur. Bu tablo fiziksel trackpad, native touch veya tüm viewport/DPR kabulünü kapatmaz. B3–B5 ve C görevlerinin hedefleri henüz uygulanmış sayılmaz.

## B3 uygulama durumu

I06–I07 ana mum fiyat ölçeğinde uygulandı. Görünür Otomatik/Manuel düğmesi, native eksen sürükleme ve çift tıklamayla eşitlenir; Enter/Space destekler. Düğme yalnız fiyat autoScale seçeneğini değiştirir. Coin/timeframe/yeniden eşitleme bağlamı yeni otomatik ölçekle başlar; aynı markette gösterge pane değişimi manuel seçimi korur. [10 kontrollü tarayıcı kontrolü](../../reports/chart-price-scale-browser-20261109.json) geçti. RSI/hacim ölçekleri ve B4'ün görünüm sıfırlama ayrımı ayrıca kalır.

## B4 uygulama durumu

I08–I09 uygulandı: Güncel mumlara dön native sağ offset'e giderken zoom'u ve fiyat modunu korur; ayrı Görünümü sıfırla yaklaşık son 110 mum/sağ boşluk ve otomatik fiyat ölçeğine döner. Her ikisi boş veride kapalıdır; Enter/Space ile çalışır. Native sınırlar dar ve güçlü zoom'lu görünümde son mumun görünür kalmasını sağlar. Göstergeler, veri, çizimler ve pane yükseklikleri reset sırasında korunur. [13 kontrollü tarayıcı kontrolü](../../reports/chart-view-actions-browser-20261109.json) geçti. B5'in fiziksel/erişilebilirlik kapsamı ayrıca açıktır.

## B5 otomatik uygulama durumu

I13–I14 controlled Chromium kapsamıyla uygulandı: aynı zaman görünümünü koruyan resize; toolbar içeren fullscreen; odaklı +/−, oklar ve End; görünür focus; input koruması. Mobil düzen, durum metinleri ve emüle DPR2 sayısal hizalama [14 kontrolde](../../reports/chart-access-browser-20261109.json) geçti. I15 için vertTouchDrag=false ayarlandı; fiziksel scroll/pinch/ikinci dokunuş geçerliliği doğrulanmadı. Görünür işletim sistemi tam ekranı, native touch, fiziksel trackpad ve raster kabulü E1 öncesi açık kalır. B5 tamamlandı işareti bu otomatik kapsamla sınırlıdır.


## B5 fiziksel gesture incelemesi

Tek olayda baskın eksen kuralı, tek fiziksel hareketteki ardışık olayların eksen değiştirmesine izin veriyordu. Artık 200 ms duraklamaya kadar gesture ekseni korunur; Ctrl/pinch geçişi ayrı gesture başlatır. Otomatik çok olaylı testler geçti; D07 fiziksel kabulü hâlâ FAIL/yeniden test bekliyor. [Kısa tekrar](validation/B5-KISA-TEKRAR.md).
