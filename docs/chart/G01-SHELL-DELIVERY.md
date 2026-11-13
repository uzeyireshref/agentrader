# G01 — yeni grafik kabuğu

11 Kasım 2026. İlk profesyonel grafik uygulama paketi tamamlandı. Kompakt45px header,44px gruplu çizim rail'i, kapatılabilir sağ piyasa/çizim paneli,40px panel rail'i ve25px durum çubuğu. Grafik mevcut panellerle776px viewport'ta673px yüksekliğe ulaşıyor;1024px genişlikte yan panel kapanınca264 CSS px alan geri kazanılıyor.

App.tsx içindeki stream/epoch, history/paint recovery, creation guards ve useDrawings akışı korunarak render kabuğu değiştirildi. Tema mevcut chart instance'ına applyOptions ile uygulanır; chart/market bağlantısı yeniden kurulmaz. Tema tercihi storage erişilebiliyorsa yerelde korunur. İkonlar ChartIcon, disclosures ShellMenu içinde; native klavye/focus/Escape davranışı var. Desteklenmeyen gelecek araçlar işlevsiz buton olarak eklenmedi.

Piyasa listesi sağ panele, mevcut DrawingPanel aynı yöneticiyle diğer sekmeye taşındı. Panel saklanırken yönetici ve çizimler korunur. Grafik nesnesi seçimi otomatik panel resize tetiklemez. `/` kapalı piyasa panelini açar ve aramayı odaklar. Mevcut aralık/gösterge/cetvel/çizim/ölçek/tam ekran kontrolleri çalışır. G06'nın daha geniş navigasyon kabulü, G02 pane ve G03 Data window bu teslim değildir.

Açık/koyu tema tokenları canvas/grid/axis/crosshair ile arayüzde birlikte uygulanır; disabled/focus/selected/loading/stale görünümü korunur. Teknik hizalama/perf panelleri yalnız diagnostics=1 ile görünür. Ürün hesapları, RSI flat50 ve diğer T10 kararları değiştirilmedi. Broker/emir/bot yürütmesi bağlanmadı.

## Doğrulama

- Frontend161/161 test geçti; TypeScript kontrolü ve üretim derlemesi geçti. Son JS index-DMe-D6JO.js, CSS index-AGrNkzLm.css.
- scripts/check_chart_g01.py: gerçek production App, kontrollü300 mum WebSocket, izole SQLite;14 kontrol geçti, page error0, dış istek0. Kullanıcının DB'si testte kullanılmadı.
-1536/1280/1024 CSS viewport, DPR1.25, iki temada6 ekran; yatay document taşması yok. Panel/tema/resize sırasında market socket aynı kaldı. İlk panel kapanışında boş40px sütun bulundu ve düzeltildi.
- Gerçek numeric edit74100→74125.25 SQLite'a yazıldı; Undo/Redo, reload ve aynı çizim kimliği korundu. Gruplu trend seçimi/Escape, disclosure focus dönüşü, arama filtresi, fullscreen ve loading/stale durumları geçti.

Kanıt reports/chart-g01-validation-20261111.json; ekranlar reports/chart-g01-{1536,1280,1024}-{dark,light}.png ve chart-g01-final.png. Performans/FPS, fiziksel GPU, gerçek touch/mobile ve bütün QA01 kabulü bu paketle tamamlanmış sayılmaz. Yeni paket testleri bunları geçerli ölçümle ayrıca doğrular.

Güncel durum6/27; sonraki G06. Önceki araştırma/v2 kanıtları tarihsel olarak korunur. Yerel inceleme adresi http://127.0.0.1:8765.
