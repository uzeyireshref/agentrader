# Kare gecikmesi bulgusu ve ilk performans optimizasyonu

9 Kasım 2026. [Orijinal masaüstü ölçümü](../../../reports/chart-performance-desktop-20261109.md) ve [ham JSON](../../../reports/chart-performance-desktop-20261109.json) değişmeden korundu.

## Ölçüm kararı

4.000 mum/200 çizim ve EMA/RSI açık, görünür sabit viewport altında 60.013 saniyelik kullanılabilir koşuda p95 rAF aralığı 48.70 ms çıktı; 33.34 ms hedefi geçmedi. 3.830 örnek, 457 adet 33.34 ms üstü aralık, 108 longtask/7.029 ms longtask süresi, sıfır error/unhandledrejection kaydı vardı. Yük/viewport/sekme koşulları değişmedi. Ortalama callback hızı kabul hedefi yerine kullanılmadı.

JS heap iki fotoğrafta 26.214.243 → 51.528.127 byte. Bu, tek başına leak kanıtı değildir; GC ve nesne yaşam döngüsü ayrıca incelenmelidir. rAF GPU FPS, longtask da CPU yüzdesi değildir. Ölçüm paneli gerçek ekranda çalıştı; performans hedefi sağlanmadı.

## Uygulanan değişiklikler

1. DrawingLayer/ProjectionCache: çizim grup ve öğe sorguları mevcut SVG yapısı için önbellekte tutulur. Pane boyutu/ankraj projeksiyonu değişmemişse koordinat yazımı atlanır; değişenlerde yalnız farklı attribute değerleri yazılır. Çizim listesi veya seçim değişince cache temizlenir; yeniden oluşan ankraj handle'ları eski DOM referansını kullanmaz. Unmount'ta cache bırakılır. DOM mutation testinde aynı görünüm için 20 invalidation sıfır attribute mutasyonu üretir.
2. LineSeriesWriter: gösterge sonuçları değişmediyse motora çağrı yapılmaz. Yalnız son bir/iki nokta değiştiğinde update kullanılır; yeni zaman normal append, mevcut eski nokta historical update alır. History prepend, pencere kayması veya daha geniş yeniden hesaplamada tam setData uygulanır. Artımlı yazma hata verirse son hesaplanan veriyle yeniden kurulur. Böylece açık mum tick'lerinde üç gösterge için tüm seri/time-scale rebuild yolu kaldırılır.

EMA/RSI matematiği bu tur değiştirilmedi; hâlâ en çok 4.000 mum üzerinde hesaplanır. React çizim ağacının yeniden render'ı ve gerçek pan sırasında değişen tüm projeksiyonların maliyeti devam eder. Bunlar ölçülmüş CPU profiliyle kesinleştirilmiş tek kök nedenler olarak sunulmaz; kaynakta doğrulanan gereksiz işlem yollarıdır. Yeni p95 ölçülmeden hızlanma yüzdesi veya hedef geçti sonucu verilmez.

## Doğrulama

60 frontend testi ve TypeScript/Vite derlemesi geçti. Altı ek test: açık mumda tek gösterge update'i; aynı değerde sıfır motor çağrısı; geçmiş nokta/yeni zaman bayrakları; history/rolling/recalculation/clear serisi eşitliği; unchanged SVG mutation=0; seçim sonrası ankraj cache'inin yenilenmesi. React iptal/pointer ve önceki mum devri testleri de geçti. Backend bu tur değişmedi ve Python regresyonu tekrar koşulmadı.

Yeni bundle index-BAW3mKcg.js, CSS index-CbnKi4Zg.css. [Optimizasyon kaydı](../../../reports/chart-performance-optimization-20261109.json).

## Masaüstü karşılaştırma görevi — yalnız kısa test

> docs/chart/validation/27-KARE-GECIKMESI-VE-PERFORMANS-OPTIMIZASYONU.md dosyasını oku. Kod değiştirme. Önceki izole test depolarının yeni bir kopyasıyla ayrı sunucuda ?diagnostics=1 grafiğini aç. Gerçek bundle'ın index-BAW3mKcg.js olduğunu doğrula. Önceki ölçümle aynı 1440x1000 ve yaklaşık DPR1, BTCUSDT/15m, 4.000 mum, 200 çizim, EMA20/50 ve RSI14 açık yükünü kur. 10 saniye ön kontrol ve bir geçerli 60 saniye ana koşu yap; pan/zoom ile test çizimi taşıma hareketlerini benzer biçimde uygula. Kullanılabilir fakat hedefi geçmeyen koşuyu daha iyi sonuç seçmek için silme/tekrarlama. Önceki 48.70 ms p95, 108 longtask/7029 ms değerleriyle karşılaştır; koşullar veya girdi temposu farklıysa bunu yaz. Panelin ham ana JSON'unu reports/chart-performance-after-optimization-20261109.json, karşılaştırma ve ekran kapsamını reports/chart-performance-after-optimization-20261109.md içine kaydet. Eski raporları değiştirme. GPU FPS, CPU yüzdesi veya leak yok sonucu verme. Mevcut 8765 sunucusuna/kullanıcı kayıtlarına dokunma; test sunucusunu kapat. 30 dakikalık testi tekrarlama.

G06 performans kabulü yeni ölçüme kadar açık. Native dokunma ve bağımsız Canvas hizalama kabulü de açık kalır. Bot bağlantısı bekler.
