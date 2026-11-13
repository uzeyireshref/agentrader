> 10 Kasım E3: [Grafik → bot veri sözleşmesi](docs/chart/BOT-DATA-CONTRACT.md) mevcut wire alanları ile hedef bağ/epoch/tazelik/ondalık kanıtlarını ayırır. Tasarım belgesidir; bot adaptörü veya emir bağlantısı uygulanmadı.

> Grafik mimarisi güncellemesi (9 Kasım): LWC 5.2.1 + series primitive ile olay tabanlı SVG projeksiyonu; resmî sabit commit görev birleştiricisi. Kaynak geometrisi ve revision kayıtları uygulamaya aittir. [Bağımlılık kararı ve sınırlar](22-GRAFIK-KAYNAK-ARASTIRMASI-VE-KALITE.md).

# Agentrader — Mimari ve işlem sözleşmesi

Güncelleme: 9 Kasım 2026 · Durum: onaylanmış ürün yönünün hedef sözleşmesi.

## Ana mimari

Kendi web terminalimiz + Python uygulama/strateji katmanı + mevcut demo yürütme çekirdeği. TradingView/Pine/webhook ana akışın bağımlılığı değildir. Bu belgede yeni modül adları hedef tasarımdır; mevcut/planlanan ayrımı [19 numaralı geçiş tasarımında](19-KENDI-GRAFIK-TERMINALI-VE-GECIS.md) ve [geliştirme durumunda](07-GELISTIRME-DURUMU.md) kayıtlıdır.

Kişisel çizim → takip kuralı → strateji olayı veya bağımsız tarayıcı olayı → açıklanabilir fırsat → somut işlem planı → kullanıcı/yönetim yetkisi → güncel veri/yetenek/sahiplik/ortak risk → kalıcı emir niyeti → borsa → gerçekleşme/koruma/çıkış uzlaştırması → bildirim ve sonuç kaydı.

## Uygulama sınırları

- Frontend grafik, çizim ve raporları gösterir; kullanıcı niyetini API'ye iletir. Binance anahtarı/secret ve borsa yazma yetkisi tarayıcıya verilmez.
- Uygulama API'si sorgular ve kimliği doğrulanmış komutlar sunar. Terminal ve Telegram aynı komut yolunu kullanır. HTTP kabulü emir gerçekleşmesi sayılmaz.
- Piyasa/strateji çalışma döngüsü açık pozisyon yokken de çalışır. Tarayıcı kapanışı bu döngüyü durdurmaz; makine/sunucu kapalıyken yerel bot çalışamaz.
- Hesap için tek yazıcı emir yürütücüsü korunur. API, çizim motoru, tarayıcı, AI veya Telegram ham adaptöre doğrudan yazamaz. Kalıcı komut kabulü borsa yazmasının tamamlandığı anlamına gelmez.
- Backend ilk etapta modüler Python uygulamasıdır. Frontend ayrı istemcidir. Servisleri çoğaltma, veritabanı değiştirme veya mevcut runner'ları topluca yeniden yazma ilk geçişin gereği değildir.

## Alan nesneleri

| Nesne | Sorumluluk | Bağlantı |
|---|---|---|
| Çalışma alanı | Grafik düzeni, sembol ve kullanıcı tercihleri | Sürümlü çizimleri içerir |
| Çizim | Fiyat/zaman geometrisi, ürün ve fiyat kaynağı | Tek başına işlem komutu değildir |
| Strateji tanımı/örneği | Parametreler, çizim bağı veya tarama kaynağı, süre ve davranış | Sürüm ve durum hafızası taşır |
| Piyasa/strateji olayı | Ölçülen temas/kapanış/örüntü ve veri kanıtı | Benzersiz kimlik ve zaman |
| Fırsat | Gerekçeler, karşı bulgular, veri eksikleri ve geçerlilik | Olay/strateji/çizim sürümüne bağlı |
| İşlem planı | Somut yön, giriş, miktar, stop/hedef ve yönetim | Mevcut v1/v2 doğrulamasından geçer |
| Yetki | Plan onayı veya gelecekte sınırlı yönetim kapsamı | Kullanıcı, sürüm, süre ve kapsam |
| Emir/gerçekleşme/oturum | Borsa etkisi ve yönetilen envanter | Mevcut kalıcı kimlik ve sahiplik |

## Çizim ve strateji sözleşmesi

Çizim; drawing_id, revision, workspace_id, symbol, exchange/product, price_source, tür, fiyat/zaman koordinatları, görünürlük kapsamı ve oluşturma/güncelleme zamanlarını taşır. Backend'de doğrulanır ve kaydedilir. Piksel koordinatları doğruluk kaynağı değildir. Yatay çizgi fiyat; bölge fiyat aralığı ve varsa zaman aralığı; trend iki nokta ve segment/ray uzatımı; Fibonacci iki referans ve açık oranlar taşır.

Strateji çizimden ayrı kayıttır. strategy_id/version, instance_id, bağlı çizim revizyonu veya otomatik seviye kaynağı, sembol/zaman dilimi, fiyat kaynağı, kural türü, parametreler, tolerans, süre, cooldown, yeniden kurulma ve yalnız izle/aday üret davranışı taşır. Serbest metin doğrudan çalıştırılabilir kural veya Python kodu olarak kabul edilmez; önce desteklenen şemaya çevrilip doğrulanır.

Etkin kural belirli çizim revizyonuna bağlıdır. Çizim değişikliği yeni revizyon oluşturur; varsayılan olarak eski bağlı takip durur, bekleyen fırsat/henüz yürütülmemiş onay geçersizleşir. Yeniden etkinleştirme yeni revizyona açık bağ oluşturur. Silme geçmişi silmez. Açılmış pozisyonun planı çizim taşındığında kendiliğinden değiştirilmez; korumaları ve izinli çıkışları sürer.

## Veri ve olay zamanı

Her veri/olay kaynak, ortam, ürün, sembol, fiyat türü, olay zamanı, alınma zamanı ve kalite bilgisi taşır. UTC zamanları saklanır; kullanıcı gösterimi Asia/Baku veya açık seçilen saat dilimiyle yapılır. Mevcut mum deposunun UTC hizası korunur.

Son işlem fiyatı, mark fiyatı, endeks ve bid/ask ayrı alanlardır. Grafik/kural hangi kaynakla çalıştığını gösterir; koruyucu emrin workingType değeri ayrıca kaydedilir. Public canlı veri ile demo hesap verisi karıştırılmaz; demo girişinden önce eşzamanlılık/fiyat farkı kontrolü uygulanır.

Piyasa WebSocket hattı ile mevcut özel hesap kullanıcı akışı ayrı adaptörlerdir. Piyasa akışı reconnect, heartbeat, olay tekrarı/sırası ve REST ile geçmiş tamamlama uygular. Kapanmış mum yalnız bir kapanış olayı üretir. Eksik veride ilgili strateji duraklar; geçmiş temas veya fill uydurulmaz. Sonradan bulunan geçmiş olay yeni ve zamanında fırsat gibi yürütülmez. Stratejiye göre daha ince mum/trade verisi gerekir; OHLC içindeki olay sırası varsayılmaz.

Olay kimlikleri ve strateji kontrol noktaları kalıcıdır. Tekrar işlenen olay ikinci fırsat/komut üretmez. Farklı gerçek olaylar cooldown gerekçesiyle görünmez olmaz: ölçüm ve bastırma nedeni kaydedilir. Anlamlı benzersiz tetiklenen kural için işleme uygun/bekle/engelli sonucu raporlanır; her fiyat tick'i bildirim değildir.

## Strateji hafızası ve geçmiş oynatma

İkinci direnç testi gibi kurallar ilk temas, geri çekilme, ayrılma, ikinci temas ve gözlem durumlarını taşır. Temas ayrılığı, tolerans, süre, tepki ölçümü, teyit ve geçersizlik parametreleri açıktır. Yaklaşık %5 örnek değerdir. İkinci temasta düşüş olmaması ancak gözlem penceresi tamamlandıktan sonra değerlendirilebilir.

Aynı kurallar geçmiş oynatma ve canlı izlemeye uygulanır. Yalnız karar anında mevcut veri kullanılır; daha sonra teyit edilen pivot o önceki anda biliniyor sayılmaz. Çizim/strateji sürümleri ve girdi özeti sonuçları yeniden üretilebilir kılar. Veri revizyonu eski karar kanıtını değiştirmez.

## Mevcut işlem planı ve yetki

Plan v1/v2 mevcut şemalarıyla çalışır. Plan kimliği/sürümü, demo ürün/sembol/mod, yön, giriş koşulu ve toleransı, sizing türü, stop, hedef payları, yönetim politikası, süre ve yetkili kullanıcı denetlenir. Desteklenmeyen eylem reddedilir. Yeni çizim/strateji/fırsat bağlantıları önce ayrı üstveri tablosunda tutulur; katı şemaya sessiz alan eklenmez. analysis_ref mevcut şemanın izin verdiği biçimde kullanılır.

Mod A belirli somut plan sürümüne tek giriş onayıdır. Ret, yanıt yokluğu, süre sonu veya maddi değişiklik yeni giriş üretmez. Mod B belirli sürümün etkinleştirilmesidir; açık koşul, süre, miktar ve yönetim eylemlerinin dışına çıkamaz. Kademeli giriş/çıkış, yeniden giriş, takip stopu ve yön çevirme yalnız kod desteği ve plan yetkisi kesişiminde mümkündür. Bot kendiliğinden mod değiştiremez.

Gelecekteki yönetim yetkisi ayrı bir modeldir: izinli sembol/strateji sürümleri, bütçe ve tahsis yöntemi, yön/kaldıraç, eşzamanlı pozisyon, işlem/gün/toplam risk, süre, işlem sıklığı ve yeniden giriş sınırları. Her üretilen plan bu yetkiye ve güncel riske bağlanır. Bu model henüz uygulanmış değildir; Mod B'nin veya max_runs değerinin genişletilmesiyle taklit edilmez.

Yetki iptali/süre sonu yeni girişleri durdurur. Açık pozisyonun koruması ve önceden izinli risk azaltıcı çıkışları sürer; kapatma ayrı eylemdir. Mevcut aynı sembolde tek etkin yönetim sahibi kuralı korunur; kişisel strateji ve tarayıcı ayrı sahiplik açamaz.

## Sermaye ve risk

Mevcut RiskLimits, Exposure, portföy değerlendirmesi ve ReservationBook bağımsız risk kapısıdır. Tahsis yöneticisi yalnız bu sınırlar içinde öneri üretir. Kullanıcı onayı, AI puanı veya fırsat önceliği risk kapısını aşamaz.

Yönetim bütçesi, sembol tahsisi, kullanılan teminat, nominal maruziyet, stop riski, masraf payı ve serbest rezerv ayrı tutulur. Bekleyen açıcı emir ve grid yeniden giriş kapasitesi rezervdedir. Çıkışın önerilmesi/iletilmesi rezervi serbest bırakmaz; gerçekleşme ve terminal durum doğrulanır. Eşzamanlı adaylar ortak atomik rezerv üzerinden kapasite alır.

Masraf, funding, kayma ve likidasyon varsayımları açıkça belirtilir. Tahmini likidasyon borsanın gerçek fiyatı olarak sunulmaz. USDT dışı varlıkların adetleri USDT gibi toplanmaz. Mevcut risk-demo.json sayıları ve tek pozisyon varsayılanı değişmez; sohbet örnekleri yeni limit değildir.

## Emir, koruma ve kurtarma değişmezleri

- Gönderim niyeti borsa isteğinden önce kalıcıdır. Belirsiz POST körlemesine tekrarlanmaz; aynı kimlikle sorgulanır ve uzlaştırılır. Kabul edilmiş emir gerçekleşmiş sayılmaz.
- İstemci kimliği farklı parametrelerle tekrar kullanılamaz. Restart aynı oturumu/eylemi devralır; yeni giriş üretmez.
- Sahiplik sembol ve net miktarla kanıtlanmaz; emir/fill/geçmiş kimlikleri eşleştirilir. Bilinmeyen veya manuel pozisyon otomatik sahiplenilmez.
- Gerçekleşen miktar korunur. Yeni stop GET ile doğrulanmadan eski stop kaldırılmaz. Giriş fiyatına taşınan stop komisyon/funding sonrası sıfır kayıp garantisi değildir.
- Kısmi fill/iptal ve geç gelen fill uzlaştırılır. Stop sonrası bekleyen açıcılar terminal doğrulanmadan yeniden pozisyon açamaz. Grid stop/drain/close politikaları 08 ve 15–18'deki uygulama sınırlarıyla korunur.
- Giriş durdurması koruma/izinli çıkışı engellemez. Koruma onarımı yalnız sahipliği doğrulanmış miktarda ve mevcut yetki içinde yapılır. Ağ kesintisinde çıkış garanti edilmez; mevcut borsa koruması korunur ve durum bildirilir.
- Hesap ayarları ve teminat değişiklikleri ayrı kalıcı komutlardır; belirsiz artımlı işlemler otomatik tekrarlanmaz. API uç yeteneği strateji desteği kanıtı değildir.

## Bildirim ve rapor

NotificationQueue/TelegramSender mevcut temelidir; kimliği doğrulanmış uzaktan onay henüz yoktur. Gelen komutlarda kullanıcı/sohbet, olay/plan/sürüm, süre ve tekrar kullanım denetlenir. Terminal ve Telegram aynı komut kimliğini paylaşır. Telegram teslimi belirsizse bildirim tekrarı mümkün olabilir; bu ikinci emir üretmemelidir.

Fırsat raporu kaynak, çizim/strateji sürümü, veri zamanı ve kalite, destekleyen/karşı nedenler, geçersizlik, plan/risk, yetki durumu ve teslim bilgisini gösterir. Hacim/taker/zincir üstü akış ayrılır. Eksik veri uydurulmaz. Her tick yerine anlamlı durum değişiklikleri bildirilir; engellenen gerçek kural tetiklenmeleri gerekçesiyle görünürdür.

## Depolama, erişim ve geçiş

Mevcut execution.sqlite3 ve market.sqlite3 korunur. Yeni alan tabloları sürümlü migration ile eklenir; ilgili modüllerde dağınık CREATE TABLE işlemleri geçişte envantere alınır. Plan/intents/events/session kayıtları yeniden kimliklendirilmez. Şema değişimi öncesinde doğrulanmış yedek ve geri dönüş yolu gerekir.

Başlangıç yerel web erişimidir. Çizim ve kural yazmaları dahil kimlik doğrulama/nesne sahipliği uygulanır; dış erişimde TLS ve oturum/CSRF/origin politikaları işletim planına dahildir. Sırlar frontend, Telegram, log veya rapora gönderilmez. Mevcut yürütme yalnız demo; public canlı piyasa okuması gerçek hesap desteği değildir. Para çekme kapsam dışıdır.

## Ayrıntı ve kanıtlar

[19 — Geçiş tasarımı](19-KENDI-GRAFIK-TERMINALI-VE-GECIS.md), [02 — Teslim sırası](02-ASAMALI-GELISTIRME-PLANI.md), [07 — Güncel durum](07-GELISTIRME-DURUMU.md), [06 — Yetenek envanteri](06-BINANCE-DEMO-YETENEK-ENVANTERI-VE-GELISTIRME-SIRASI.md), [DOGRULAMA — Tarihli kanıtlar](DOGRULAMA.md). Önceki sözleşmenin tarihsel ayrıntıları [arşivde](docs/archive/2026-11-09/README.md) korunur; yeni ürün yönüne üstün gelmez.
