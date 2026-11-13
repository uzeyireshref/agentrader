> Yeni mum tekrar testi tamamlandı: 30 dakika 14,774 saniye, iki mum geçişi ve yeniden bağlantı gözlemleri geçti; önceki kalıcı hata yeniden görülmedi. FPS/heap ve diğer açık kabul maddeleri kapsam dışı. [Masaüstü tekrar test raporu](../../../reports/chart-desktop-rollover-retest-20261109.md).

# Masaüstü test bulguları ve yeni mum düzeltmesi

9 Kasım 2026. Masaüstü raporu okundu: [orijinal rapor](../../../reports/chart-desktop-acceptance-20261109.md). Orijinal kanıtlar değiştirilmedi.

## Sonuçların değerlendirilmesi

Dört çizim türü oluşturma, uygulanabilen gövde/ankraj taşıma, normal coin/zaman dilimi geçişi, geçmiş yükleme, iki sekmeli revision çakışmasında güncel kaydı koruma, reload/restart kalıcılığı ve otomatik yeniden bağlantı gerçek ekranda gözlendi. EMA/RSI'nin 50 toggle sonunda görünür pane'leri geri geldi. Dar ekran ve fullscreen açılışı için sınırlı görsel kanıt var.

Nihai grafik kabulü yok: 30 dakika 15 saniyelik oturumun ikinci bölümünde Veri alınamadı kalıcı olmuş. Fiyat zamanı ilerlemiş; 4.000 mum/200 çizim kalmış. CPU/FPS/p95/heap ölçülmemiş. Bütün iptal/pointer/dokunma, <=1 piksel hizalama ve sayısal gösterge referansı testleri tamamlanmamış.

## Bulunan kod hatası ve düzeltme

frontend/src/App.tsx eski artımlı çizim yolu her iki seride her mum için update(candle,true) çağırıyordu. Lightweight Charts 5.2.1'in kurulu kaynak kodu, historicalUpdate=true ve zaman noktası henüz yoksa Cannot update non-existing data point when historicalUpdate is true hatası veriyor. [Resmî update sözleşmesi](https://tradingview.github.io/lightweight-charts/docs/api/interfaces/ISeriesApi#update) de bu bayrağı var olan eski noktaları düzeltmek için tanımlar.

Yeni mum zamanı için bu çağrı yanlıştı. Eski kodu temsil eden regresyon, sözleşme hatasını üretir; düzeltilmiş serileme yeni mumları normal update ile ekler, yalnız son mumdan eski mevcut noktaları historical olarak günceller. Hem mum hem hacim aynı yolu kullanır. Orijinal tarayıcı istisnası yakalanmadığından rapordaki olayın kesin stack trace'i budur denmez; hata doğrulanmış, olayla ilişkisi güçlü bir açıklamadır ve yeni ekran testi gerekir.

Ayrıca reducer 4.000 mumda baştan kırparken eski çizim yolu motorun ilk mumunu kaldırmıyordu. Bu, motor indeksi ile çizim indeksinin ayrışmasına ve sınırsız seri büyümesine yol açabilirdi. ChartSeriesWriter, pencerenin ilk zamanı değiştiğinde iki seriyi aynı bounded diziyle yeniler. Kırpılan baştaki mum sayısına göre görünür logical range korunur. Sıradan açık mum güncellemelerinde tam seri setData yapılmaz.

Artımlı güncellemenin bir kısmı hata verirse iki seri de son doğrulanmış reducer dizisiyle yeniden kurulur. Bu da başarısız olursa Grafik güncellenemedi durumu ve Grafiği yeniden eşitle düğmesi gösterilir. Veri/JSON hatası etiketi ayrı kalır. İstisna mesajları veya hassas ağ ayrıntıları kullanıcı arayüzüne basılmaz.

Skip-link hedefindeki main için tabIndex=-1 eklendi; masaüstü raporunda hedef odak kabulü açık olduğundan bu değişiklik de yeniden klavye testi bekler.

## Doğrulama

Toplam 37 frontend testi ve TypeScript/Vite üretim derlemesi geçti. Altı yeni senaryo: eski historical çağrısının hatayı üretmesi; önceki kapanış ile yeni mumun birlikte işlenmesi; mevcut eski mum düzeltmesi; 4.000 mum devri ve indeks kayması; kısmi hata sonrası iki serinin toparlanması; history prepend. Seri sink'i motorun ilgili API koşulunu modeller; bunlar gerçek Canvas/browser testi değildir.

Backend kaynağı değişmedi; önceki 666 Python testi bu tur tekrar koşulmadı. Yeni paket index-O7AuBlIT.js. [Düzeltme doğrulama kaydı](../../../reports/chart-candle-rollover-fix-20261109.json).

## Masaüstünde yalnız test için sonraki görev

> docs/chart/validation/25-MASAUSTU-BULGULARI-VE-YENI-MUM-DUZELTMESI.md dosyasını oku. Kod değiştirmeden yeni index-O7AuBlIT.js paketini yüklediğini doğrula. Mevcut kullanıcı kayıtları yerine önceki izole QA veritabanlarının bir kopyasıyla test örneği aç. 15 dakika zaman diliminde 4.000 mum/200 çizim yükle; EMA/RSI'yi de aç. En az iki yeni mum başlangıcını kapsayan 30 dakika çalıştır. Her sınırın öncesi/sonrası zamanları, durum etiketi, son mum fiyatı ve çizim hizalamasını kaydet. Yeni mum oluşunca hata etiketinde kalmamalı; mum/hacim/çizim penceresi birlikte ilerlemeli. Bağlantıyı test sunucusunu yeniden başlatarak kesip dönmesini gözle. Skip-link Enter sonrası main odağını kontrol et. Sonucu reports/chart-desktop-rollover-retest-20261109.md dosyasına yaz. Ölçülemeyen FPS/heap veya tamamlanamayan senaryoları geçti işaretleme. Mevcut 8765 sunucusunun ayarlarını ve kullanıcı çizimlerini değiştirme.

Kod ve diğer proje işleri VS Code'da kalır. Bu tekrar testi geçmeden sağlıklı uzun oturum kabulü ve genel W2/W3 kabulü kapatılmayacak; bot bağlantısına geçilmeyecek.
