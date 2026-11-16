# Son mumdan sonraki alana çizim — 14 Kasım 2026

Sorunun iki ortak nedeni vardı. `App.tsx` çizim tıklamasında grafik motorunun `event.time` alanını zorunlu tutuyordu; bu alan son gerçek mumun sağında boş geliyor. `DrawingInteraction` da imlecin altında mutlaka mevcut bir mum satırı arıyordu. Dolayısıyla önizleme ve çizim başlangıcı/tamamlanması bütün araçlarda engelleniyordu. Ek olarak bazı ışın/kanal gösterimleri çapa noktalarını yüklü veri aralığıyla sınırlıyor ve ışınları son mumda kırpıyordu.

## Uygulanan düzeltme

`drawingTimeAt`, ekranın mantıksal bar koordinatını seçili zaman dilimine göre UTC çizim zamanına çevirir. Yüklü aralıkta gerçek satırın zamanını kullanır; sağdaki/solundaki boş alanda aynı periyotta takvim adımları hesaplar. Haftalık çizim Pazartesi hizasını korur. Son iki veri satırı arasında boşluk varsa bu boşluk gelecekteki periyoda dönüştürülmez.

Tıklama ve önizleme aynı dönüşümü kullanır. Gerçek mum bulunmayan alanda OHLC mıknatısı fiyatı değiştirmez. Çizimi sürüklerken ters dönüşüm de aynı periyodu kullanır; yeni mum gelmesi veya eski tarih yüklenmesi kayıtlı UTC çapalarını değiştirmez.

Işınlar görünür panel sınırına kadar çizilir. Görsel projeksiyonun kapsamı ile hesaplama/veri kanıtının kapsamı ayrıldı: gelecekte bir çizim çapası oluşturmak, mevcut olmayan mumları botun veri kanıtına eklemez. Grafik mum/indikatör/veri deposuna sahte satır eklenmez. Backend hesaplamalarının mevcut aralık, boşluk ve tazelik kontrolleri korunur.

Regresyon kanalı gerçek mumlar üzerinde hesaplanır; verisiz iki gelecekteki noktadan regresyon uydurulmaz. Mevcut mumlardan hesaplanan kanal, mevcut sağa uzatma seçeneğiyle geleceğe yansıtılabilir. Cetvelin fiyat/zaman geometrisi gelecekte kullanılabilir; gerçekleşmiş mum sayısı kanıtı mevcut veriyle sınırlıdır.

## Doğrulama

Üretim arayüzü ve geçici SQLite üzerinde gerçek fareyle 21 araç son mumdan sonraki alanda oluşturuldu: yatay/trend çizgileri, ışınlar, Fibonacci araçları, geometrik kanallar, dört Pitchfork, bölge, cetvel, açıklamalar ve long/short planları. Trend, Fibonacci ve paralel kanalın gelecek çapaları ayrıca sürüklenip kaydedildi. Sayfa yenilemesi, gerçek mumların çizim tarihine yetişmesi ve ışının panel sınırına uzanması doğrulandı. Tarayıcı hatası, dış kaynak veya hesap/emir isteği yok.

Kaynaklar: `frontend/src/drawingTime.ts`, çizim etkileşim/projeksiyon modülleri, `frontend/tests/drawingTime.test.ts`, `scripts/chart/check_future_drawings.py`.

Rapor: `reports/future-drawings-validation-20261113.json` (test ilk oluşturulurken verilen dosya adı korunmuştur; son çalışma 14 Kasım). Çalışan yerel terminal güncel üretim derlemesini sunuyor. Açık sayfada yenileme yeterlidir.
