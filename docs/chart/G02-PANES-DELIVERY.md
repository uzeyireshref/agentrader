# G02 — pane ve ölçek altyapısı

11 Kasım2026. G02 tamamlandı; güncel8/27, sıradakiG03 veri penceresi/readiness.

## Teslim

Üstte Paneller menüsü: hacim/RSI göster-gizle, fiyat alanını büyüt ve pane boyutlarını sıfırla. Native ayırıcılar sürüklenebilir. Aynı önayar manuel resize sonrası tekrar uygulanabilir. Düzen oranları görünür oturum içindir; T14 workspace/template kalıcılığı bu teslim değildir.

Fiyat pane0'ı korur. paneLayout.ts opsiyonel pane'leri sabit indeks yerine gerçek seri sahipliğinden çözer. Hacim gizlenince seri görünmez overlay olarak korunur ve boş pane kaldırılır; geri açılınca fiyat→hacim→RSI sırası kurulur. Hacim verisi silinmez; gizle/göster sırasında manuel sayısal ölçek aralığı saklanıp geri uygulanır. Kayıtlı çizim koordinatları veya market bağlantısı bu görünüm değişikliğiyle değişmez.

PaneLegends hacim ve RSI başlığını, o pane'in otomatik/manuel ölçeğini ve gizleme eylemini gerçek DOM pane konumuna bağlar. Observer/rAF yalnız boyut/etkileşim olayında çalışır ve cleanup edilir; sürekli idle loop yok. PriceScaleControl yalnız priceScale arayüzüne bağlı hale getirildi; hacim/RSI ile fiyat ölçekleri ayrı kalır.

EMA overlay ve RSI oluşturma/yazma yaşam döngüleri ayrıldı. EMA açmak RSI instance'ını, manuel ölçeğini veya pane'ini yeniden kurmaz. RSI0–100 hesap alanını kullanır; axis margin'leri nedeniyle eksen etiketlerinin0–100 dışına taşması hesap çıktısı değildir. RSI flat50 veya seed hesabı değiştirilmedi; T10 kararı bekler.

## Kabul

-167 frontend test, TypeScript kontrolü ve üretim derlemesi geçti. Son paket index-BM6SFYZH.js / index-rO-juNNy.css.
- scripts/check_chart_g02.py gerçek üretim App, native motor, kontrollü300 mum ve izole SQLite ile **15 kontrol** geçti; page error0, dış istek0. Kullanıcı DB'si testte kullanılmadı.
- Native separator hareketinde fiyat pane yüksekliği395.2→340 CSS px değişti; native priceToCoordinate ile SVG yatayı ve pane yüksekliği farkı<1 CSS px kaldı.1536/1280/1024, light/dark, DPR1.25/2 ve fullscreen geçişinde aynı hizalama doğrulandı.
- Hacim gizle/göster, RSI indeks kayması, tekrarlı kaldır/ekle sonrası boş/çift pane yok. Hacim300 satırı ve manuel ölçek aralığı geri geldi. Pane kontrolleri tek market bağlantısını ve çizim revision1'i korudu.
- RSI pane'inde crosshair aynı timestamp'teki fiyat OHLC'sini okudu. RSI'a cetvel aracıyla tıklamak fiyat çizimi başlatmadı. Yardımcı ölçeği manuel yapmak fiyat ölçeğini değiştirmedi; EMA toggle RSI manuel durumunu korudu.
- G01'in14 ve G06'nın12 tarayıcı regresyonu geçti. Eski G01 testinin tek-header-menu varsayımı artık Göstergeler disclosure'ına açıkça sınırlandı.

Kanıt reports/chart-g02-validation-20261111.json ve chart-g02-delivery-20261111.json. Ekranlar chart-g02-{1536,1280,1024}-dark.png, chart-g02-1024-light.png, chart-g02-dpr2.png. Görseller kontrollü sentetik piyasadır; live exchange parity, fiziksel GPU/FPS/touch veya QA01 kapanışı değildir.

Yerel uygulama http://127.0.0.1:8765. Açık sekme yenilendiğinde Paneller menüsü ve bağımsız pane kontrolleri görünür.
