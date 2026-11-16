> Bu yaklaşım geri alındı: görünümü zorla kaydırıyordu. Güncel çözüm [REA-NAVIGATION-SIGNED-DRAWINGS-20261115.md](REA-NAVIGATION-SIGNED-DRAWINGS-20261115.md). Aşağıdaki kayıt tarihseldir.

# Ana mum alanının alt bölgesinde kaybolan çizimler

15 Kasım 2026. Açık Chrome grafiğinde BTCUSDT haftalık/manuel lineer ölçek gözlendi: ana fiyat alanının altı 0 ve -40.000 fiyatlarını kapsıyordu. Oluşturma ve hareket sözleşmesi pozitif fiyat gerektirir; ortak önizleme bu bölgede null ürettiğinden tüm araçlar kayboluyordu. Hacim paneliyle ilgili değildir.

`frontend/src/drawingViewport.ts` gerçek alt pikselin fiyatını denetler. Çizim aracı etkinleştirildiğinde veya kayıtlı çizim sürüklemesi başlarken, alt kenar tick'in altındaysa lineer görünür aralığı aynı genişlikle yukarı taşır. Zoom aralığı korunur, otomatik ölçek açılmaz. Normal pozitif aralık, log/yüzde/index ölçekleri değiştirilmez. Negatif fiyatlı kayıt yaratma izni verilmez; kullanıcı çizim sırasında dikey görünümün yukarı kaydığını görebilir. Çizim kapalıyken serbest gezinme davranışı korunur.

İki birim testi: margin içeren alt piksel düzeltmesi/kararlılık ve geçerli veya lineer olmayan ölçeklerin korunması. Native grafik regresyonu `scripts/chart/probe_bottom.py`: negatif alt kenar yeniden üretildi, H aracı gerçek grafik odağında etkinleştirildi, düzelmiş alt fiyat ve %20/%70/%90/%98 yüksekliklerde fiyat etiketi/SVG çizgi koordinatı doğrulandı. İzole geçici SQLite ve sentetik feed; kullanıcı kayıtları değiştirilmedi.

362 frontend testi ve üretim derlemesi geçti. Kanıtlar `reports/drawing-bottom-tests-20261115.log`, `reports/drawing-bottom-build-20261115.log`, `reports/drawing-bottom-browser-20261115.log`. Önceki QA01 arşivi dondurulmuş eski adaydır; bu değişiklik için beş performans koşusunun veya fiziksel B5'in tekrarlandığı iddia edilmez.
