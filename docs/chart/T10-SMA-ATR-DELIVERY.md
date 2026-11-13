# T10 — SMA, ATR ve sürümlü EMA/RSI hesap kabulü

12 Kasım 2026. Tamamlandı; plan 19/27. Sıradaki G05: MACD ve Bollinger Bands.

## Kullanım

Göstergeler menüsünde SMA ve ATR açılır; Gösterge ayarları beş bağımsız nesnenin periyot/görünürlük ve uygun fiyat kaynağını kaydeder. SMA fiyat panelinde turuncu çizgi; ATR ayrı, lineer fiyat-birimi panelinde turkuaz çizgidir. ATR kendi otomatik ölçek/gizleme kontrolüne sahiptir; RSI, hacim ve fiyat ölçeklerine karışmaz. Kalıcı ayar/revision/yeniden deneme T09 protokolünü kullanır. Veri penceresi tüm beş çıktıyı aynı kaynak ve periyotla okur.

## Deterministik hesap

- SMA: seçilen kaynağın kayan aritmetik ortalaması; ilk çıktı period−1.
- EMA: ilk periyodun SMA seed'i; alpha=2/(period+1), ilk çıktı period−1. T09 varsayılan EMA sonuçları korunur.
- RSI: ilk period değişimin gain/loss SMA seed'i ve Wilder RMA; ilk çıktı period. Calculation_version=1 düz seride50, version=2 düz seride100. All-up100/all-down0; v2 diğer dalların hesabını değiştirmez.
- ATR: TR=max(high−low, |high−previous close|, |low−previous close|). İlk yüklü barda önceki close bilinmediği için TR=high−low. İlk period TR'nin SMA seed'i, devamında Wilder RMA; ilk çıktı period−1. ATR fiyat birimidir, yüzde değildir. Kaynak OHLC sabittir.

Yüklü geçmiş başlangıcı açık seed anchor'ıdır. Daha eski history eklendiğinde bu başlangıçtan yeniden hesaplanır; gerçek vendor origin seed'i veya TradingView exact paritesi iddia edilmez. Uzun-history yakınsama origin kanıtı sayılmaz. analysis.py yalnız bağımsız referans olarak karşılaştırıldı; eski CLI analiz davranışı değiştirilmedi.

Warmup eksikliği boş çıktı/yetersiz geçmiş olarak görünür; sıfıra çevrilmez. UTC bucket, sıra, süre veya OHLC geçersizliği ve missing bar olduğunda bütün yapılandırılmış çizgi çıktıları temizlenir, Data window neden gösterir. Bir boşluğun üzerinden smoothing zinciri taşınmaz. Grid onarımı ve son mum revizyonu güncel veri üzerinden yeniden hesaplanır. Açık mum değerlerinin güncellenebilir olduğu görünür uyarıdır; kapanmış çıktı gibi bot kaynağına dönüştürülmez.

## Sürüm geçişi ve bot/replay etkisi

`format_version=2` GET/PUT ve chart-indicators/2 beş nesneyi destekler. Fiziksel DB migration gerekmez; T09'un sürümlü JSON tablosu kullanılır. Eski üçlü kayıt v2 okunduğunda yeni SMA/ATR kapalı eklenir; RSI'nin kayıtlı v1 sürümü, period/source/enabled ve revision korunur. GET veritabanına yazmaz. RSI v2'ye geçiş ayar formunda açık seçim ve revision kaydıdır. Yeni çalışma alanının v2 varsayılan RSI'si100 davranışını kullanır.

V2 beşli kayıt kaydedildikten sonra eski format1 okuma/yazması422 ile reddedilir; eski istemci yeni nesneleri veya RSI sürümünü sessizce silemez. Fresh/legacy format1 sözleşmesi önceki üçlü kayıtlar için korunur. İstemci, v2 istek için v1 yanıtı kabul etmez. Kayıt yanıtının alan ve revision doğrulaması devam eder.

Calculation_version gösterge konfigürasyonunun parçasıdır. Eski analysis.py RSI50 davranışı ve eski replay sonuçları sessizce yeniden yorumlanmaz. Strateji/replay bağlama ve version uygunluk denetimi P4–P7 işidir; bu teslimde strategy_engine NOT_IMPLEMENTED, live_eligible/order_authority=false kalır. Canonical bot query registry'sinde gösterge valueAt planı ayrıca korunur; arayüzde çizgi olması işlem yetkisi değildir.

## Kabul

- **801 Python testi** geçti. Yedi yeni grup: explicit legacy→v2 geçişi ve eski client izolasyonu; SMA/ATR her çıktı için bağımsız analysis/aritmetik referans; ATR previous-close gap **511.4 vs high−low511.3**; RSI v1/v2 flat ve seed başlangıcının etkisi; missing bar/onarım/revizyon; v2 HTTP/uygunsuz ATR source/smoothing reddi; paylaşılan v2 fixture güncelliği.
- **233 frontend testi** geçti. Altı yeni test; 29 ortak sayısal fixture ile tüm beş gösterge/yedi uygun kaynak, SMA/ATR seed/warmup, ATR gap, explicit RSI50/100, NaN/grid boşluğu ve onarım/revizyon, v2 şema. Eski v1 fixture ve varsayılan EMA/RSI testleri korunur.
- TypeScript ve üretim derlemesi başarılı. Ana JS547.81kB, gzip174.12kB. Mevcut500kB uyarısı ve QA01 performans kabulü açık.
- **19 üretim App tarayıcı kontrolü** geçti: beş seride her noktada Python eşleşmesi; tekil görünürlük/uzun warmup; kayıt, kayıp onay ve conflict/reload;50 gerçek kalıcı RSI pane döngüsü sırasında ATR'nin bağımsız kalması; timeframe/coin/reload/server restart; missing bar çizgilerinin temizlenmesi; onarım ve açık mum revizyonu; açık mum uyarısı; RSI sürüm seçiminde50/100;1024px açık/koyu form.
- G02/G03/T08 **39 ilgili regresyon tarayıcı kontrolü** geçti. Sentetik piyasa ve izole SQLite kullanıldı; kullanıcı DB'sine test ayarı yazılmadı. Page error0 ve dış/hesap/emir çağrısı0. Ekranlar görsel olarak incelendi. Fiziksel GPU/touch veya canlı vendor hesap paritesi kabulü yok.

Kanıt: `reports/chart-t10-validation-20261112.json`, `reports/t10-*.log`, `chart-t10-*.png`; kaynak/derleme SHA256 manifesti `reports/chart-t10-delivery-20261112.json`. [V2 sözleşme](contracts/indicators-v2.json). T09 ve v1 sözleşmesi tarihsel olarak korunur.
