> Sonraki kullanıcı kararı: Grafik verisi de gerçek ortama geçişe kadar Binance Demo üzerinden alınacak. Önceki public gerçek veri kullanımının sürdürülmesi varsayımı değişmiştir. Uygulama sırası: [26 numaralı plan](26-DEMO-VERI-VE-GRAFIK-BOT-ENTEGRASYON-PLANI.md).

# Binance USD-M demo → gerçek ortam araştırması

Tarih: 13 Kasım 2026 (Asia/Baku).

## Kullanıcı kararı

Geliştirme, grafik bağlantıları ve işlem doğrulamaları Binance USD-M demo üzerinde sürdürülecek. Gerçek hesaba geçiş, gerçek API anahtarı ekleme veya gerçek emir gönderme bu çalışma kapsamında yetkilendirilmedi. Gerçek geçiş en son ayrı bir aşamadır. Public gerçek piyasa verisini anahtarsız okumak, gerçek hesap bağlantısı değildir.

## Sonuç ve kanıt sınırı

Resmî USD-M belgeleri demo ortamında endpointlerin çoğunun kullanılabildiğini belirtir; tüm endpointler için eşitlik garantisi vermez. Aynı ürün/hesap modu kapsamında grafik, strateji, plan, risk, kalıcı niyet ve uzlaştırma çekirdeğini yeniden yazmak beklenmiyor. Geçiş yalnız URL değiştirmek de değildir. Kod değişikliği küçük/orta kapsamlı bir adaptör ve ortam izolasyonu işi olarak öngörülür; gerçek ortam kabulü ayrı ve kapsamlıdır. Bu bir mühendislik değerlendirmesidir, ölçülmüş efor yüzdesi değildir.

Demo FAQ grafik, emir defteri fiyatları ve emir gerçekleşmesinde farklılık olabileceğini açıklar. Demo kârlılığı gerçek getiri kanıtı sayılmaz. Demo ve gerçek ortamın sembol, filtre, kaldıraç, komisyon, funding ve limitlerinin eşit olduğu varsayılmamalıdır; seçilen ortam/hesaptan okunmalıdır.

Bu araştırmada gerçek veya demo özel hesap sorgusu, emir, hesap ayarı değişikliği yapılmadı; kimlik bilgileri okunmadı. Kaynak kod ve resmî web belgeleri incelendi. Testler yeniden çalıştırılmadı.

## Kod bulguları

- agentrader/config.py yalnız demo ortamı kabul ediyor; kilit korunacak.
- agentrader/exchange.py demo REST adresini ve yöntem/endpoint izin listesini sabitliyor. Serbest kullanıcı URL'sine dönüştürülmemeli.
- agentrader/user_stream.py demo özel WebSocket adresini sabitliyor. İleride REST ve özel stream ortamları birlikte doğrulanmalı.
- agentrader/market_data.py gerçek public USD-M verisini anahtarsız okuyor. Grafik verisi ile demo hesap yürütmesi zaten ayrılmış.
- agentrader/plan_v2.py ve plans.py demo ortamını doğruluyor. Demo plan/onaylarının gerçek ortamda kullanılmasına izin verilmemeli.
- agentrader/v2_preflight.py exchangeInfo, hesap modu, sembol ayarı, kaldıraç basamağı, mark fiyatı ve gelir geçmişini dinamik okuyor; taşınabilirlik için güçlü temel.
- v2_preflight.py içinde fee=Decimal('.001'); portfolio.py içinde fee_rate='0.001' bulunuyor. Bunlar rezerv varsayımlarıdır; hesabın gerçek komisyon oranı diye sunulmamalı. Tahmini rezerv ve gerçekleşen komisyon/funding ayrı raporlanmalı.
- v2_runner.py account_ref değerini API key hash'inden türetiyor. Anahtar değişimi hesap kimliğini değiştirir; ileride ortam/ürün/hesap kimliği ile credential kimliği ayrılmalı. Mevcut aktif kayıtlar otomatik yeniden kimliklendirilmemeli.
- capabilities.py kanıtları demo, ürün, sembol ve credential ile sınırlıyor; kayıtlar gerçek ortam için kanıt sayılmamalı.
- Mevcut kalıcı niyet, tek yazıcı, belirsiz POST'u tekrar etmeme, sahiplik, rezervasyon ve koruma mekanizmaları korunmalı.

## Demo içinde geliştirme sırası

1. Grafik olayı → gölge sinyal → v2 plan önizlemesi; emir yok.
2. Sürümlü kural, çizim kopyası/bağı ayrımı, iptal ve süre sonu; tek olaydan tek plan.
3. Aynı fiyat türlerinde public/demo farkı ve yaş denetimi; LAST ile MARK farkını ortam farkı diye ölçmeme.
4. Kullanıcı onaylı tek sembol SINGLE demo işlemi ve grafikte borsadan doğrulanmış durum.
5. Gerçek demo fill, stop/TP tetiklenmesi, kısmi fill/iptal, bağlantı kopması, restart, kayıp yanıt ve manuel müdahale kabulü.
6. Gecikme, kayma, komisyon/funding ve bakiye-reset etkilerini ölçme; yakalanmayan uç durumları offline hata enjeksiyonuyla sınama.
7. Grid/neutral ve çoklu oturum kabulünü ayrı genişletme.

Binance FAQ'da hazır Futures Grid arayüzünün desteklenmemesi, bizim normal emirlerden kurduğumuz özel grid motorunun otomatik olarak kullanılamaz olduğu anlamına gelmez. Kendi motorumuz her kullandığı endpoint ve davranış için demo kanıtı gerektirir. Binance webhook kısıtı da kendi grafik/backend hattımızı zorunlu olarak engellemez.

## İleride gerçek ortama geçiş için ayrı işler

Ayrı hesap/depo/kimlik bilgileri ve açık ortam sınırı; demo onaylarını taşımama; gerçek ortam yetenek/filtre/komisyon doğrulaması; IP kısıtlı en az yetkili anahtar ve para çekme/transfer kapalı yapı; önce salt okunur kabul, sonra kullanıcı ayrıca yetkilendirirse sınırlı gerçek işlem kabulü. Para çekme izni olmaması, işlem yetkisiyle zarar oluşmasını önlemez.

## Resmî kaynaklar

- https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info
- https://www.binance.com/en-NG/learn/binance-demo-trading
- https://www.binance.com/es-AR/learn/binance-demo-trading
- https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data
- https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade
- https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account
- https://www.binance.com/en/support/faq/detail/360002502072

Belgeler erişim tarihindeki durumdur; geçiş zamanında tekrar doğrulanmalıdır.
