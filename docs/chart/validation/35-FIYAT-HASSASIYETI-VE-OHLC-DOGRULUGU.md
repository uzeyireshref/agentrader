# Fiyat hassasiyeti ve OHLC doğruluğu

9 Kasım 2026. Bu tur veri gösteriminin doğruluğu incelendi; zoom/menü tasarımı değiştirilmedi.

## Bulgular ve değişiklikler

- Eski crosshair etiketi bütün coinlerde dört ondalık gösteriyordu. Örneğin 0.00000013, 0.0000 olabiliyordu. Yeni OhlcReadout, coin tick_size hassasiyetini (mevcut destek sınırı12 basamak) kullanır; aynı format içinde OHLC değerlerini gösterir. Tick bilinmiyor/geçersiz veya fiyat NaN/Infinity ise uydurma değer basmaz.
- İmleç mumdan ayrıldığında veya whitespace üzerinde olduğunda önceki OHLC bırakılıyordu. Artık Mum seçilmedi · UTC gösterilir.
- Coin/zaman dilimi değişiminde etiket yeni DOM/abonelikle başlar; eski callback yeni etiketi yazamaz. Native crosshair verisi, seçili ekranın mumuyla aynı zaman/OHLC değilse gösterilmez. Eşleşme için sıralı mumlarda ikili arama yapılır.
- Sabit imleçte mum verisi değişirse etiket güncel değeri alır; aynı coin yeniden eşitlenirken veri boşalırsa temizlenir.
- Enstrüman başlığı, view.symbol/view.interval seçili coin/zaman dilimiyle uyuşmadan eski son fiyat/yüksek/düşük/hacim göstermez.

Grafik motorunun fiyatları, kayıtlı ondalık geometri ve işlem verileri değiştirilmedi. Eski OHLC dinleyicisi kaldırıldı; yeni bileşen unsubscribe temizliğini yapar. Hareket başına React state güncellemesi yok; yalnız metin gerçekten değişince DOM etiketi yazılır.

## Doğrulama

102 frontend testi ve TypeScript/Vite üretim derlemesi geçti. Altı yeni test: sekiz basamaklı mikro fiyat; quarter/whole tick ve geçersiz değer; imleç çıkışı/whitespace temizliği; coin/timeframe remount ve listener temizliği; aynı timestamp'li eski coin verisinin reddi; sabit imleç verisinin güncellenmesi ve resync temizliği. React/jsdom ve kontrollü motor olayları kullanıldı; fiziksel ekran/native touch kabulü yapılmadı. Header guard küçük mantıksal değişikliktir, bu tur tam App/native browser senaryosu çalıştırılmadı.

Backend bu tur değişmedi; önceki671 Python testi ve public canlı probe yeniden çalıştırılmadı. Yeni ana bundle index-CI3fr0vQ.js; lazy FixtureLab-w_HOad2W.js. Kullanıcı çizimlerine test amaçlı yazma yapılmadı.

Genel grafik kabulü ayrı kalır. Önceki native/SVG, kontrollü boşluk, gösterge ve kayıt yarışı kanıtları kendi kapsamlarında geçerlidir. Bu tur için yeni masaüstü görevi yok.
