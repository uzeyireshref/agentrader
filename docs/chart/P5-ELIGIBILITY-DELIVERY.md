# P5 — Saf uygunluk ve nedenli engel

13 Kasım 2026. P5 tamamlandı. Kayıtlı bağ kartındaki **Uygunluğu kontrol et**, sunucuda açık olan piyasa aboneliğinin kanıtıyla salt okunur, anlık bir sonuç üretir. Sonuç bağı aktifleştirmez, kuralı çalıştırmaz, olay/intent veya emir üretmez. Sıradaki P6 kalıcı semantik olay ve yerel intent paketidir.

## Sonuç sözleşmesi

- BLOCKED: zorunlu kanıt yok, bozuk, eski veya bağlam dışıdır. Tüm başarısız kontrollerin nedenleri birlikte döner.
- OBSERVE_ONLY: gözlem kuralı veya metrik/boolean/hipotetik/ekran göstergesi çıktısıdır. Kanonik işlem sinyali iddiası yoktur.
- EVALUATION_ELIGIBLE_NOT_ORDER_AUTHORITY: kanonik PRICE çıktısı için kapanmış mum kuralının değerlendirme önkoşulları o anda sağlanmıştır. Bağ DISABLED kalır; live_eligible, execute_rule, rule_evaluated ve order_authority false’tur.

Saf evaluate_binding fonksiyonu açık girdilerle deterministiktir; saat okuma, I/O veya mutation yapmaz. Adapter, binding ve hedefi tek uygulama DB read transaction snapshot’ından okur. Piyasa feed’i ayrı, kilitli bellek snapshot’ıdır; iki kaynağın atomik snapshot’ı veya sonraki kullanım için yetki iddiası yoktur. P6 kullanımdan önce güncel head’i yeniden kontrol edecektir.

## Zorunlu kanıtlar

Owner/workspace, immutable tanım hash’i, DISABLED kayıt, hedef tür/kimlik/revision/içerik, yetki sözleşmesi, kaynak/environment/product/price_type/symbol/interval, LINEAR ölçek ve dondurulmuş referans grid/hash denetlenir. Desteklenmeyen kind/query/ratio/formula/scale/grid açık neden üretir. Sorgu descriptor’ı ve hash’li kaynak/fixture kataloğu güncel tanımla eşleşmelidir.

Sunucu yalnız zaten abone olunan feed’den kanıt okur; kontrol yeni feed açmaz, ağ isteği başlatmaz. Kaynak kimliği ve sunucu transport durumu, P3 veri proof’unun satırlardan yeniden hesaplanan tam karşılığı, epoch/generation/data revision, kesintisiz UTC grid ve en az iki kapanmış mum zorunludur. Native ondalık OHLCV/quote-volume ve tick provenance’ı doğrulanır; ekran float’larıyla eşleşme, exact OHLC sıralaması ve hacim/quote tutarlılığı ayrıca denetlenir. İstemci snapshot hash’i yalnız referanstır.

P2 FRESH saat proof’u ve değişmemiş politika, en fazla 10 saniye alım/kaynak yaşı, en fazla 1 saniye belirsizlik gerekir. Kaynak olay zamanı snapshot’ın son mumuyla ve belirsizlik düşülmüş kapanış zamanıyla eşleşir. Reconnect, durmuş akış, eksik saat veya eski veride uygunluk verilmez. Arayüzdeki LIVE, görünür/gizli çizim veya açık gösterge bu kanıtların yerine geçmez.

12 çizim türünün tüm kayıtlı sorguları sınıflandırılır. Sekiz gösterge türü formül sürümü doğrulanarak yalnız gözlemde kalır; warmup ve son kapanmış mumdaki gerçek display çıktısı aranır. EMA/RSI/ATR seed politikası ekran sözleşmesidir; MACD signal warmup ve BB kaydırması gerçek çıktı kontrolüne dahildir. VWAP session/anchor eksikliği veya sıfır toplam hacim unavailable üretir. Ekran hesapları native fiyat sinyaline yükseltilmez.

## Arayüz ve uyumluluk

Sonuç kayıtlı binding revision/hash ve piyasa bağlamıyla eşleşmeden gösterilmez. Kalan kaynak tazeliği kadar, en fazla 10 saniye görünür; istek süresi bu bütçeden düşülür. Kontrol anlıktır; bu süre boyunca sürekli uygunluk garantisi vermez. Bağlam/revision değişimi, parent mutation, sekmenin gizlenmesi, başarısız/bozuk/geç yanıt sonucu temizler. Polling ve aktivasyon kontrolü yoktur. Açık engel nedenleri Türkçedir; kontrol edilen data revision/generation/hash incelenebilir.

Yeni tanım ve katalog metadata’sı SEPARATE_READ_ONLY_P5’tir. Eski immutable NOT_IMPLEMENTED_P5 kayıtları/hash’leri korunur ve okunur; uygunluk ayrı endpoint sonucudur. DB şeması değişmedi (migration 6). Hiçbir uygunluk raporu kalıcı olarak yazılmaz; geçmiş kontrol, güncel yetki kanıtı olarak kullanılmaz.

## Doğrulama

854 Python, 268 frontend testi ve üretim derlemesi geçti. 15 P5 Python test grubu her zorunlu context/saat girdisinin yokluğunu, tüm desteklenen çizim sorgularını, formül/warmup/VWAP/grid sınırlarını, sahteliği, owner/head kontrolünü ve salt okunur HTTP davranışını kapsar. Beş yeni frontend testi yanlış yetki/revision/yanıt, geç bağlam, hata, süre aşımı ve sonucu temizlemeyi kapsar.

11 P5 üretim tarayıcı kontrolü: gerçek eligibility API’siyle uygun fiyat, gözlem göstergesi, saat/eski veri/native sidecar/eksik sunucu feed engeli, süre aşımı, değişmeyen DB kayıtları, hedef edit sonrası STOPPED ve açık/koyu 1024/1536 görsel kontrol. Sentetik sunucu feed’i ve izole SQLite kullanıldı. 16 P4 regresyon kontrolü geçti. Gerçek kullanıcı hesabı, emir veya worker kullanılmadı. Görseller incelendi. Mevcut bundle boyutu uyarısı ve QA01 performans kabulü açıktır.

[Tarayıcı kanıtı](../../reports/chart-p5-validation-20261113.json) · [Teslim manifesti](../../reports/chart-p5-delivery-20261113.json) · [Makine sözleşmesi](contracts/eligibility-v1.json)
