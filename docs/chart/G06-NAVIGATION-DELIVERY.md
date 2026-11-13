# G06 — günlük navigasyon ve hızlı erişim

11 Kasım 2026. G06 tamamlandı; güncel7/27, sıradakiG02 pane/ölçek altyapısı.

## Kullanım

- Üst bardaki arama veya **Ctrl+K** (macOS Meta+K): hızlı erişim. Semboller, Araçlar ve Zaman dilimleri ayrı kapsamlar. Oklar/Home/End ile sonuç gezme, Enter ile seçim, Escape ile kapatma ve açan kontrole focus dönüşü.
- **Virgül:** desteklenen zaman dilimlerini ara/seç. Yeni interval motoru eklenmedi;1m/5m/30m T08 kapsamındadır. Desteklenmeyen sorgu boş sonuç verir, Enter hiçbir bağlamı değiştirmez.
- **/**: piyasa panelini aç ve aramayı odakla. `BTC / USDT` gibi ayraçlı aramalar normalize edilir; tam sembol/base eşleşmesi öne çıkar.80 sonuç sınırından sonra daha fazla sözleşme yüklenebilir; bütün desteklenen katalog aranır.
- Yıldız ile favori ekle/çıkar; Tümü/Favoriler filtresi; en son kullanılan4 sözleşmeye dönüş. Favoriler ve en fazla8 son kullanılan bu tarayıcının yerel tercihidir; hesaplar arası senkronizasyon veya T14 workspace template teslimi değildir. Bozuk/erişilemeyen storage uygulamayı durdurmaz. Katalogda olmayan eski tercihler çalışır seçenek olarak sunulmaz.
- Grafik odaktayken **V/T/H/B/F/R**: imleç/trend/yatay/bölge/Fib/cetvel. Escape araç seçimi sonrası toolbar odağında da iptal eder. Metin/numeric/select/contenteditable/combobox ve açık modal içinde shell kısayolları devre dışı; IME ve işlenmiş/modifier tuşları korunur. Araç yükleme/kayıt/retry guard'ları klavye ve palette de geçerli.

## Uygulama

ChartCommandDialog native modal ve combobox/listbox ilişkisi kullanır; fullscreen chart panelinin içindedir. Modal100 sonuç gösterir, fazla sonuçta arama daraltma bilgisi verir; panel kataloğu80'lik adımlarla açılır. Sembol/interval seçimi mevcut setter/epoch/history/useDrawings yaşam döngüsüne gider. Favori seçimi market değiştirmez ve stream açmaz. Mevcut server çizim kaydı/kural hesapları değişmedi; RSI flat kararı veya bot yürütmesi bağlanmadı.

chartCommands.ts desteklenen katalog araması, bounded preference okuma ve temizlenebilir keyboard listener'ı içerir. chartTools tek arama/kısayol metadata kaynağıdır. App/UI, terminal.css ve ChartIcon bağlantıları güncellendi; yeni dış bağımlılık yok.

## Kanıt

- **167/167 frontend test**:6 yeni arama/storage/odak/modal/IME/listener temizliği kabulü; mevcut161 kontrol korundu. TypeScript ve üretim derlemesi geçti.
- scripts/check_chart_g06.py: gerçek production App,103 sözleşmeli kontrollü katalog, synthetic stream ve izole SQLite ile **12 kontrol** geçti. Favori marketi değiştirmiyor; panel kapalı Ctrl+K→ETH ve virgül→1h doğru bağlantıyı açıyor; boş sonuç/typing/modal nesting/focus/fullscreen/yenileme kabulü var. Page error0, dış istek0; kullanıcının DB'sine test yazısı yok.
- scripts/check_chart_g01.py **14 kontrol** yeniden geçti: iki tema/üç genişlik, panel resize, kayıt/Undo/Redo/reload ve fullscreen/stale akışları.
-1536/dark,1280/light,1024/light hızlı erişim ekranları kaydedilip görsel incelendi; son CSS çift focus çerçevesini kaldırır, dış arama focus ring'i korunur. Kanıt reports/chart-g06-validation-20261111.json; kaynak/build ve görüntü hashleri chart-g06-delivery-20261111.json.

Bu teslim live exchange sayısal parity, fiziksel GPU/FPS, touch veya QA01 tamamlanması değildir. Yerel uygulama http://127.0.0.1:8765; açık sekme yeni paketi almak için yenilenir.
