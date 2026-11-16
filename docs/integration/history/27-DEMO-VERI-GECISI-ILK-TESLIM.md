> Sonraki teslim: [B1 gölge sinyal takibi ve arka plan gözlemi](28-GOLGE-SINYAL-TAKIBI-VE-GOZLEM.md). Aşağıdaki ilk veri geçişi kaydı tarihseldir.

# Demo veri geçişi — ilk uygulama teslimi

13 Kasım 2026. D0/D1/D2 ilk kapsamı uygulandı; D3 kısa ağ/HTTP/masaüstü kabulü doğrulandı. 30 dakika kesintisiz gözlem ve geniş fiziksel kabul henüz tamamlandı sayılmaz. B1–B4 sinyal/plan/emir entegrasyonu henüz açılmadı.

## Değişiklikler

- REST geçmişi, exchangeInfo, sunucu saati ve public mark sorguları demo-fapi üzerinden; kline WS demo-fstream /market/ws üzerinden.
- market_environment.py tek sabit demo bağlamıdır. Serbest host/gerçek ortam seçici veya gerçek kaynağa fallback eklenmedi.
- Grafik, kaynak kanıtı, hesap/geometri çıktısı, üst-zaman, binding uygunluğu ve alarm kontrolleri demo kaynak kimliğine geçirildi. Python/TypeScript parity fixtureları yeniden üretildi; paketlenmiş replay kaydı yeni kaynak hash'leriyle gerçek test çalıştırılarak yenilendi. Tarihsel raporlar yeni başarı diye etiketlenmedi.
- Varsayılan uygulama deposu data/application-demo.sqlite3; grafik mum deposu data/chart-market-demo.sqlite3; CLI analiz deposu data/market-demo.sqlite3. Execution deposu değişmedi.
- Yeni uygulama deposu kalıcı kaynak işareti taşır. İşaretsiz ve içinde kullanıcı verisi olan eski uygulama deposu reddedilir; eski aktif alarmlar otomatik taşınmaz. Eski çizimler silinmedi; yeni demo çalışma alanı başlangıçta boştur. İsteğe bağlı çizim kopyalama aracı bu teslimde yok.
- UI Binance Demo USD-M gösterir. Katalog/geçmiş/WS kaynak kimlikleri tüketim öncesi denetlenir; yanlış ortam yeni mum olarak kabul edilmez.
- Eski v1 canlı/demo market_guard içeren planların yeni girişi ağ çağrısından önce engellenir; demo fiyatının kendisiyle karşılaştırılıp canlı karşılaştırma başarılı sanılması önlenir. Mevcut pozisyon koruması değişmez.
- Eski /health piyasa akışı NOT_IMPLEMENTED alanı yerine demo kaynak/ortamı ve DEMO_ON_DEMAND raporlanır; strateji/emir yürütme hâlâ kapalı.

## Doğrulama

- Python tam regresyon: 988 test, başarılı; frontend: 321 test, başarılı; üretim derlemesi başarılı. 500 kB bundle uyarısı sürüyor.
- İzole replay 36/36; kaynak ve kayıt değişikliği gerçek emir yetkisi üretmedi.
- Demo REST 4 endpoint ve gerçek kline WS el sıkışma/veri kontrolü geçti; hesap/emir isteği yok.
- İzole HTTP kabulünde BTCUSDT/ETHUSDT × 1m/5m/1h/1d geçmişi kaynak ve kaliteyle doğrulandı; desteklenmeyen interval ve finansal komut reddedildi.
- Gerçek tarayıcıda demo etiketi, sıfırdan büyük mum sayısı ve Canlı durumu kontrol edilir; görsel reports/demo-transition-ui-20261113.png.
- Gerçek yerel WS üzerinden demo public akışı; en az iki ayrı 1m kapanışı. Ağ adresleri demo hostlarıyla sınırlandı. Tam süre ve sonuç reports/demo-transition-validation-20261113.json içindedir.
- İzole uygulama yeniden başlatma/işaret kontrolü ve execution sentinel byte hash'inin değişmemesi doğrulandı. Bu sentinel deneyi gerçek hesap uzlaştırması veya gerçek demo özel akış testi değildir.
- 6 mevcut SQLite deposu online backup ile yedeklendi ve integrity_check geçti. Manifest: reports/demo-transition-20261113/stores-1794583882/manifest.json. Kaynak depolara yazma yapılmadı. Sonrasında yalnız yeni demo uygulama/mum depoları normal kullanımda oluşur.

## Açık işler

D3 için planlanan 30 dakikalık kesintisiz gözlem, uzun kesinti/gerçek upstream kanıtı ve genel/fiziksel kabul açık. Bu kısa teslim 30 dakika veya 24 saatlik kabul diye sunulmaz. Eski cihaz kabulü değişmez. Sonraki uygulama kapısı D3 kalan veri kabulü; ardından B1 gölge takip ve B2 plan önizlemesi. Grafik kaynaklı emir, yeni hesap ayarı, bildirim gönderimi ve gerçek hesap bağlantısı açılmadı.

## Çalıştırma ve geri dönüş

Yeni çalıştırma: python -m agentrader web serve. Varsayılan demo çalışma alanı otomatik hazırlanır. AGENTRADER_WEB_DATABASE eski kullanıcı verili depoya işaret ediyorsa güvenli biçimde başlangıç reddedilir; eski depoyu demo diye işaretleyerek aşmayın. Ayrı yeni bir demo yolu kullanın.

Geri dönüşte eski kaynak adayı ve eski uygulama/grafik depoları birlikte kullanılmalı; yeni demo deposu eski gerçek-public yazılımla açılmamalı. Aktif execution oturumları kopyalanmaz veya sıfırlanmaz. Yerel sunucu yeni demo sürümüyle 127.0.0.1:8765 üzerinde yeniden başlatıldı; 300 mum, demo kaynak kimliği ve Canlı durumu gerçek tarayıcıda doğrulandı. Makbuz: reports/demo-running-terminal-20261113.json. Kaynak değişiklikleri commit edilmedi.

[Plan](26-DEMO-VERI-VE-GRAFIK-BOT-ENTEGRASYON-PLANI.md)
