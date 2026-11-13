> 9 Kasım grafik kalite güncellemesi: 666 Python ve 16 frontend testi geçti. Trend/Fibonacci, EMA/RSI ve mıknatıs eklendi; görsel kabul bekliyor. Güncel ayrıntılar: [kaynak araştırması ve kalite](22-GRAFIK-KAYNAK-ARASTIRMASI-VE-KALITE.md).

# W2/W3 — Canlı grafik ve kalıcı çizimler

Tarih: 9 Kasım 2026 · Durum: kodlandı; veri/API/kalıcılık testleri geçti. Görsel tarayıcı ve gerçek sürükleme QA'sı henüz doğrulanmadı.

## Mevcut ürün

Kendi React/TypeScript terminalimiz, yerel Python API'den Binance USD-M public verisi alır. Coin arama/seçme, 15m/1h/4h/1d/1w, mum/hacim, crosshair, zoom/pan, geçmiş yükleme ve güncel mumlara dönüş mevcut. Tarayıcı doğrudan Binance'e bağlanmaz; aynı sembol/zaman dilimi bir API sürecinde paylaşılan feed kullanır. Eski, tekrar eden ve yanlış bağlamlı olaylar reddedilir; kopmada REST ile yeniden eşitleme yapılır. Son iki mum birlikte taşınarak kapanışın bir sonraki mumla aynı ekran güncellemesine denk gelmesi korunur.

Yatay çizgi ve iki köşeli fiyat bölgesi sayısal zaman/fiyat koordinatlarıyla sunucuda saklanır. Seçme, sürükleme, bölge köşelerini değiştirme, sayısal fiyat/ad düzenleme, silme ve oturum içi geri al/yinele arayüzü eklendi. Çizimler sembole bağlıdır; zaman dilimi değişse de aynı mutlak zamanı/fiyatı temsil eder.

Çizimlerin bot takibi veya emir etkisi henüz yoktur. Yaklaşma/temas kuralları W4'tür. Trend çizgisi ve Fibonacci sonraki çizim genişletmeleridir.

## Başlatma

Proje kökünde önce bağımlılık ve derleme:

~~~powershell
python -m pip install -e ".[web-test]"
Set-Location frontend
npm ci
npm run build
Set-Location ..
python -m agentrader web serve
~~~

Grafik: http://127.0.0.1:8765/ . Sadece public grafik için Binance anahtarı veya web token gerekmez. Frontend çıktıları agentrader/web_assets içine derlenir; Python sunucusu aynı origin üzerinde bunları ve API'yi sunar. Düzenleme geliştirmesinde frontend içinden npm run dev kullanılabilir; /api ve WebSocket aynı-origin yerel proxy'den geçer.

## Kalıcı çizim erişimi

Yerel grafik ve çizimler için anahtar/eşleşme gerekmez. Sunucuyu başlatıp grafiği aç; çizimler otomatik yüklenir. Host/Origin ve revision denetimleri korunur. Ayrı komut/status API kimlik doğrulaması çizimlerden bağımsızdır. [Güncel kapsam](docs/chart/validation/28-ANAHTARSIZ-CIZIM-VE-GOSTERGE-DOGRULUGU.md).

## Kayıt davranışı

- Çizim oluşturma/düzenleme/silme sunucu tarafından onaylandığında Kaydedildi gösterilir.
- Her değişiklik yeni revizyondur. Eski revizyonla yazma 409 döndürür; daha yeni veri ezilmez.
- Aynı request_id ve içerik tek kayıt üretir; bağlantı hatasında Aynı kaydı tekrar dene aynı kimliği kullanır.
- Son kaydı yükle sunucudaki güncel çizimleri alır ve yerel undo/redo geçmişini sıfırlar.
- Silme tombstone revizyonudur; geri alma yeni bir restore revizyonu oluşturur. Sayfa yeniden açıldığında çizimler ve son coin/zaman dilimi korunur; undo/redo yığını yalnız mevcut ekran oturumundadır.
- Çizimler yüklenmeden düzenleme başlatılmaz. Sembol değişimi sırasında geciken eski yanıt yeni grafiği ezmez.
- Fiyatlar ondalık metin, zamanlar UTC saniyesi olarak saklanır. Ekran pikseli doğruluk kaynağı değildir.

## Depolar ve geçiş

application.sqlite3 şema v2: çalışma alanları, değişmez çizim revizyonları, güncel revizyon başları ve tekrar önleme kayıtları. V1'den yükseltmede önce tutarlı before-v2-*.bak yedeği alınır; bekleyen inceleme komutları korunur. Finansal işlem deposu değiştirilmez.

Public grafik verisi ayrı data/chart-market.sqlite3 içindedir; CandleStore altyapısı yeniden kullanılır. Eski analiz deposu market.sqlite3 ve execution.sqlite3 ayrıdır. AGENTRADER_CHART_DATABASE grafik deposunu seçer. Anahtarlar bu depoya konmaz.

## Doğrulama ve kanıt

- [Tam doğrulama](reports/chart-workspace-validation-20261109.json): 665 Python testi, atlanan yok; gerçek izole localhost HTTP kontrolü geçti. Çizim create/tekrar/update/çakışma/delete/restore, cookie ve çalışma alanının sunucu restart'ında korunması doğrulandı.
- Frontend: 9 Node/TypeScript testi geçti; production derlemesi başarılı. Sembol/zaman dilimi ayrımı, kapanış sırası, reconnect/history birleştirme, zaman projeksiyonu ve .25 gibi tick hassasiyeti kapsandı.
- [Gerçek public veri kontrolü](reports/chart-live-validation-20261109.json): 504 desteklenen sözleşme, BTCUSDT 300 mum, LIVE akış ve geçmiş sayfalama başarılı. Hesap isteği ve emir yok.
- Görsel masaüstü/mobil QA, gerçek canvas üzerinde sürükleme/ölçek ve iki köşeli çizim etkileşimi otomatik tarayıcıyla henüz doğrulanmadı. Kodlanmış özellik ile bu kabul kanıtı ayrı tutulur; W2/W3 tam kullanıcı kabulü bu kontrolü bekler.

~~~powershell
python scripts/validate_chart_workspace.py
python scripts/check_chart_feed.py
Set-Location frontend
npm test
npm run build
~~~

İlk komut çevrimdışı regresyon ve izole yerel HTTP'dir; ikinci komut açıkça public Binance ağına çıkar. Hiçbiri emir veya hesap mutasyonu yapmaz. Mevcut risk profili korunur.

## İşletim sınırları

Piyasa akışı ekran abonelikleriyle talep üzerine açılır; boşta kalan abonelik yaklaşık 60 saniye tutulur. Bu aşamada çizimler kendi başına kalıcı strateji aboneliği açmaz. W4'te etkin kuralların bağımsız backend yaşam döngüsüne bağlanması gerekir. Bir API sürecinde en çok 8 feed ve feed başına 16 istemci vardır. Verinin gecikmesi/GAP/reconnect durumu görünür; kaçan temas veya fill uydurulmaz.

Lightweight Charts 5.2.1 kullanılır; kütüphane logosu/bağlantısı ve LICENSE/NOTICE dosyaları korunmuştur. Bu kullanım TradingView hesabı/Pine/alarm bağımlılığı oluşturmaz.

## Sonraki teslim

Önce W2/W3 görsel kabul kontrolü; ardından W4 yaklaşma/temas, tekrar önleme ve bildirim. Mevcut çizim revizyonlarına bağlanan kurallar çizim taşındığında eski sürümle sessizce çalışmamalıdır.
