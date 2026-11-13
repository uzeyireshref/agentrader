# Kısa performans ölçümü ve React etkileşim testleri

9 Kasım 2026. Bu tur: G01 iptal yolları için React DOM testleri ve G06 için kullanıcı tarafından başlatılan ölçüm paneli. Bot bağlantısı yapılmadı.

## Tamamlananlar

Toplam 54 frontend testi ve TypeScript/Vite derlemesi geçti. Önceki 37 teste 17 test eklendi: 8 iptal yolu; başarılı drag, ikinci pointer ve origin'e geri dönüş; dört kare-istatistik sınırı; bilinen scale altında trend/bölge/Fibonacci SVG projeksiyonu; ölçüm panelinin başlat/iptal/unmount temizliği.

İptal yolları: Escape, window blur, pointercancel, lostpointercapture, symbol, interval, disabled ve unmount. Her testte önce sürükleme preview'su oluşturulur; iptalden sonra pointerup gönderilir; kayıt çağrısı oluşmadığı ve orijinal hareket/ölçek ayarlarının tek kez geri geldiği doğrulanır. Tamamlanan drag'da kayıt tam bir kez gider. İkinci pointer ilk gesture'ı bitiremez. Origin'e dönüş ilk fiyatı geri üretir.

Testler jsdom üzerinde gerçek React event handler'larını çalıştırır. Canvas/chart koordinatları, pointer capture ve tarayıcı boyaması test doubles ile temsil edilir. Bunlar işletim sistemi touch girdisi, native capture veya gerçek piksel hizalaması kabulü değildir. Bilinen scale testi beklenen SVG özniteliklerini kontrol eder; gerçek Canvas'a karşı <=1 CSS px ölçümünü kapatmaz.

Geliştirme bağımlılıkları: jsdom 26.1.0 (Node >=18, mevcut Node 22.12 ile uyumlu), @types/jsdom 21.1.7, tsx 4.23.15. Yalnız devDependencies; üretim JS'e eklenmezler. npm kurulumu denetiminde 0 vulnerability döndü. npm test artık TS/TSX testlerini tsx üzerinden çalıştırır. Backend değişmedi; 666 Python testi bu tur tekrar koşulmadı.

## Ölçüm paneli

Yalnız URL'ye ?diagnostics=1 eklenince görünür: http://127.0.0.1:8765/?diagnostics=1 . Normal kullanımda panel mount olmaz; ölçüm başlatılmadıkça yeni bir rAF döngüsü veya performans gözlemcisi kurulmaz.

- 10 sn ön kontrol ve 60 sn ölç: ölçüm sırasında gerçek pan/zoom/çizim hareketleri yapılır.
- requestAnimationFrame aralıklarının örnek sayısı, ortalaması, p95, en yüksek değeri ve 33.34 ms üstü örnek sayısı.
- Destekleniyorsa longtask sayısı/toplam süresi ve non-standard JS heap başlangıç/son görüntüsü. Desteklenmiyorsa null/Desteklenmiyor.
- Sekmenin arka plana geçmesi, yük/sembol/zaman dilimi veya viewport/DPR değişmesi, LIVE dışı durum ve error/unhandledrejection sayaçları. Kesintili/yetersiz/truncated ölçüm kontrollü kabul olarak sunulmaz.
- Ham JSON ekrandaki details içinde okunabilir ve indirilebilir. Script bundle yolu ve başlangıç/bitiş yükü kaydedilir. Veri dış servise gönderilmez.
- İptal ve unmount: timer/rAF, visibility/error dinleyicileri ve observer temizlenir. En fazla 10.000 kare aralığı tutulur; fazla örnek kesilirse rapor usable=false döner.

rAF callback hızı GPU-render FPS değildir. Longtask ölçümü CPU kullanım yüzdesi değildir. performance.memory desteklenmeyebilir ve güvenilir bir leak hükmü vermez; iki heap fotoğrafı bellek sızıntısını dışlamaz. Panel otomatik grafik kabulü vermez.

Kaynaklar: [MDN requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame), [MDN performance.memory sınırları](https://developer.mozilla.org/en-US/docs/Web/API/Performance/memory), [jsdom](https://github.com/jsdom/jsdom).

## Masaüstünde yalnız gerçek ölçüm için görev

> docs/chart/validation/26-KISA-PERFORMANS-VE-ETKILESIM-TESTLERI.md dosyasını oku. Kod değiştirme. Yeni index-cLhmWRyv.js ve index-CbnKi4Zg.css paketini doğrula. Önceki QA veritabanlarının kopyasıyla ayrı bir yerel örnekte 4.000 mum/200 çizim ve EMA/RSI açıkken URL'ye ?diagnostics=1 ekle. 10 saniyelik ön kontrolü başlatıp grafikte pan/zoom yap; panelin tamamlanmasını ve ham JSON'u kaydet. Ardından görünür, sabit boyut/DPR sekmede 60 saniyelik ölçümü başlat; gerçek pan, zoom ve çizim gövdesi taşıma hareketlerini uygula. Panel JSON'unu desteklenen DOM okumasından alıp reports/chart-performance-desktop-20261109.json dosyasına yaz; beklenen değerlerle doldurma. Yük ve sekme koşulları değişmişse koşuyu tekrarla. Longtask/heap null ise ölçülmedi yaz. rAF p95 hedefi <=33.34 ms karşılaştırmasını bildir, GPU FPS veya sızıntı yok hükmü verme. Ayrıca bir ölçümü iptal et ve yeni ölçümün başlayabildiğini gözle. Sonuç ve ekran kanıtı kapsamını reports/chart-performance-desktop-20261109.md içine yaz. Mevcut kullanıcı verileri/8765 ayarlarını değiştirme; test örneğini görev sonunda kapat. 30 dakikalık dayanıklılık testini bu görevde tekrarlama.

Bu tur native dokunma veya tam fiziksel piksel ölçümü yapılmadı. Bunlar ayrı kabul maddeleri olarak açık kalır.
