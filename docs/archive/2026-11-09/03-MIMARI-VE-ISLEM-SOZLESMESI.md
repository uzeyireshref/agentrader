> Tarihsel arşiv: 9 Kasım 2026 yön değişikliğinden önceki metin. Güncel ürün kararı için [aktif hedeflere](../../../01-PROJE-VE-HEDEFLER.md) bakın. İçerik korunmuştur; yerel Markdown bağlantıları arşiv konumuna uyarlanmıştır.

# Mimari ve işlem sözleşmesi

## 6 Kasım 2026 genel yetenek sözleşmesi

API kapsamı ürün, ortam, yöntem, yol, parametre şeması, hesap yetkisi ve
iş akışı durumuyla kaydedilir. Referans:
[güncel envanter](../../../06-BINANCE-DEMO-YETENEK-ENVANTERI-VE-GELISTIRME-SIRASI.md).
Bir uç noktanın adaptörde izinli olması yönetilen strateji desteği değildir.
Secret genel hesap yetkisi değildir; public, API-key ve signed güvenlik türleri
ayrı uygulanır. Demo tüm uçları destekliyor varsayılmaz.

Kaldıraç/teminat/mod değişimleri emirlerden ayrı kalıcı komutlar olacak;
zaman aşımında körlemesine tekrarlanmayacak, mevcut yapılandırma okunacak.
Grid ve çoklu giriş planları yeni şema ve portföy rezervi olmadan eski tek
giriş motoruna zorlanmayacak. Stop sonrası bekleyen alımların yeniden pozisyon
açmasını engellemek zorunlu kabul ölçütüdür. Spot/COIN-M ve özel ürünler ayrı
adaptör/filtre/izin doğrulaması ister. Aşağıdaki v1 kapsamı henüz genişlemiş
işlevlerin uygulanmış olduğu anlamına gelmez.

Son plan güncellemesi: 5 Kasım 2026. Bu belge hedef sözleşmedir; mevcut kodun kapsamı [01-PROJE-VE-HEDEFLER.md](../../../01-PROJE-VE-HEDEFLER.md) ve [DOGRULAMA.md](../../../DOGRULAMA.md) ile sınırlıdır. Plan şeması v1 ve yerel Mod A/B yetkisi tek girişli demo LONG, 1–8 kademeli hedef ve izinli hedef sonrası girişe stop taşıma kapsamıyla uygulandı. Ayrı salt okunur canlı veri adaptörü ve temel çoklu zaman dilimi raporu vardır. TradingView, zengin haber/AI raporu, Telegram, SHORT/hedge ve diğer desteklenmeyen yönetim eylemleri henüz yoktur.

## Temel akış

TradingView çizim/indikatör alarmı → doğrulama ve kalıcı sinyal kaydı → her alarm için bildirim → piyasa/haber verisi → sayısal analiz ve varsa AI yorumu → gerekçeli rapor/plan adayı → şema/yetenek/risk denetimi → kullanıcı yetkisi → güncel koşulları yeniden doğrulama → kalıcı emir niyeti → Binance → gerçekleşme/koruma takibi → sonuç bildirimi ve günlük.

Önceden etkinleştirilmiş Mod B planı kendi kayıtlı koşullarıyla da tetiklenebilir; geçerli yetki ve risk kapısını atlayamaz. AI olmadan hazırlanmış planlar aynı yolu kullanır.

AI katmanı olmadan da emir motoru ve sayısal analiz test edilebilmeli. Tek süreç ve modüler Python paketleriyle başla; başlangıçta mikroservis veya karmaşık dağıtık altyapı kurma.

## Değişmez kurallar

- Her geçerli benzersiz alarm bildirilir; strateji veya risk reddi bildirimi gizlemez.
- Yeni giriş için Mod A sürüme bağlı kullanıcı onayı veya Mod B açık etkinleştirme kaydı gerekir. Alarm tek başına yetki değildir.
- Kullanıcı onayı risk sınırlarını, geçerlilik ve desteklenen yetenekleri aşamaz.
- Girişleri durdurmak, mevcut koruma ve önceden izinli çıkışları durdurmaz.
- Sembol/miktar eşleşmesi tek başına sahiplik kanıtı değildir; fill/emir kimlikleri uzlaştırılır.
- Aynı olay, onay veya plan eyleminden çift emir üretilmez.
- Demo/canlı, spot/Futures, sözleşme, fiyat türü ve veri kaynağı açıkça ayrılır.

## Modüller

- exchange: Binance adaptörü; demo/canlı bağlantısı, hesap, emir ve pozisyon sorguları.
- execution: emir yaşam döngüsü, tekrar önleme, uzlaştırma ve koruyucu emir yönetimi.
- watchdog: kayıtlı pozisyon sahipliği, sürekli koruma kontrolü, devralma, onarım ve acil çıkış politikası.
- risk: bağımsız ve modelin aşamayacağı işlem sınırları.
- plans: plan şeması, sürümler, geçerlilik ve desteklenen yetenekler.
- authorization: Mod A tek kullanımlık onaylar, Mod B etkinleştirme kayıtları, kapsam/süre/kullanım sınırı ve iptal.
- signals/webhooks: TradingView kaynak doğrulaması, olay şeması, sembol/plan eşleştirmesi ve kalıcı kuyruk.
- market_data: WebSocket/REST, mum kapanışları, veri bütünlüğü ve kaynak bilgisi.
- analysis: indikatörler, piyasa yapısı, zaman dilimleri ve göreli güç.
- flows: hacim, taker baskısı ve borsalara giriş/çıkış/net akışın birbirinden ayrılmış kaynaklı ölçümleri.
- news: toplama, güvenilirlik bilgileri, tekrar ayıklama ve zaman bilgisi.
- ai: sağlayıcı adaptörü, yapılandırılmış çıktı, maliyet/çağrı kontrolü.
- storage: analiz, veri, plan, emir, gerçekleşme ve olay kayıtları.
- notifications: Telegram ve alarm kanalları.
- reports (gerektiğinde): yetkili kullanıcıya ayrıntı ve cihazlar arası rapor görünümü.
- app/config: çalıştırma, yapılandırma, sağlık kontrolü ve ortam ayrımı.

SQLite mevcut kalıcı altyapıdır. Plan, sinyal, analiz, yetki ve bildirim tabloları sürümlü geçişlerle eklenir; mevcut intents/events/managed_sessions kayıtları korunur. Gerçek ihtiyaç oluşmadan daha ağır veri altyapısı eklenmesin.

Canlı analiz verisi ayrı `data/market.sqlite3` içindeki source/symbol/interval/open_time anahtarlı mum tablosunda saklanır. `PublicMarket` yalnızca sabit canlı hosttaki public time/exchangeInfo/klines GET çağrılarına izin verir; Config/.env veya API anahtarı yüklemez. Demo yürütme adaptörü değişmez. Açık mumlar analize girmez. Mum boşluğu/eskilik/hatalı sayı raporu eksik yapar; uydurma veriyle doldurulmaz. Sabit sunucu kesim zamanı, tam kapanmış girdi anlık görüntüsü, analiz sürümü ve SHA-256 özetiyle yeniden üretilebilir rapor kaydı tutulur. Teknik rapor, plan/onay/emir katmanlarını çağırmaz.

## TradingView ve sinyal sözleşmesi

Pine, TradingView'daki teknik hesaplama/çizim/sinyal bölümüdür; haber/AI ve Binance hesap/emir katmanı değildir. Webhook TradingView → sunucu bildirimidir; kişisel hesap çizimlerini topluca okuyan veya Python/AI sonucunu Pine'a geri gönderen genel bir API değildir. Fibonacci koordinatları otomatik varsayılmaz; sayısal plan girdisi veya açık alarm eşleştirmesi gerekir.

Sinyal en az olay kimliği, kaynak/alarm kimliği, script/ayar sürümü, borsa, piyasa/sözleşme, sembol, zaman dilimi, tetiklenme ve ilgili mum zamanı, olay türü ve varsa plan kimliği/sürümü taşır. Alınma zamanı sunucuda kaydedilir. Bilinmeyen eşleştirme, eski veya stratejiye uymayan geçerli alarm bildirilir ama yürütülmez. Sahte/yetkisiz trafik güvenlik olayıdır; kullanıcıya işlem önerisi sayılmaz.

HTTPS alıcısı güncel kaynak doğrulaması, şema/boyut sınırları, hızlı kalıcı kabul ve arka plan kuyruğu uygular. Binance secret Pine/webhook içine konmaz. Yinelenen teslim aynı olay altında saklanır; farklı alarmlar kaybolmaz. Teslimat garantili varsayılmaz; gecikme/kayıp ve alarm günlüğü görünürdür. Kullanıcı çalışan alarmı etkinleştirir; script/ayar sürümü değişince mevcut alarmın kendiliğinden değiştiği varsayılmaz.

## Analiz raporu ve bildirim sözleşmesi

Özet ve ayrıntı aynı analiz sürümüne bağlıdır. Telegram ilk kanaldır; ayrıntı ek mesajlarla veya ileride kimlik denetimli raporla sunulur. Bildirim yetkisi emir yetkisi değildir.

- Kaynak olay, ürün, zaman dilimi, veri zamanı; LONG/SHORT/BEKLE/ENGELLİ sonucu.
- Destekleyen ve karşı çıkan nedenler; görüşü değiştirecek koşullar.
- Son 7 tamamlanmış UTC gününün günlük hacim/karşılaştırma tablosu ve varsa giriş/çıkış/net akış; açık gün ayrı gösterilir.
- Taker baskısı, spot/Futures hacmi ve zincir üstü borsa akışı ayrı alanlardır. Birim, kapsam, kaynak, etiketleme ve gecikme kaydedilir. Hacimden yeni sermaye girişi çıkarılmaz; borsa akışı tüm piyasa akışı sayılmaz.
- W/D/4H/1H/15M bulguları, BTC/ETH/dominans/TOTAL3 ve göreli güç.
- Haber özeti, URL, yayın/olay zamanı ve güvenilirlik bilgisi.
- Plan adayı, giriş/stop/hedefler, tutar türü/miktar, tahmini risk, yetki modu ve son geçerlilik.
- Eksik veri, gecikme ve analiz kesintisi. Kritik eksik girişe engeldir, bildirime değil.

Sayısal veriyi kod/sağlayıcı üretir; AI yorumlar. İlk alındı bildirimi tam analizden önce gönderilebilir. Teslimat kuyruğu, tekrar denemeleri ve hata kayıtları kalıcıdır. Özel hesap verisi herkese açık rapor bağlantısına konmaz.

## İşlem planı

Bir plan, serbest metin değil doğrulanabilir yapılandırılmış veri olmalı. En az şu alanları kapsasın:

- Plan kimliği, sürümü, oluşturma ve son geçerlilik zamanı.
- Kaynak sinyal/analiz ve script/ayar sürümleri; önceki plan sürümü.
- Ortam, ürün, sembol ve beklenen hesap/pozisyon modu.
- Eylem: bekle, giriş, iptal, stop güncelle, kısmi çıkış veya tam çıkış.
- Yön ve giriş koşulu; tetikleyici veri kaynağı.
- Sayısal Fibonacci referansları/seviyeleri veya açık alarm/koşul eşleştirmesi; kapanış şartı ve fiyat toleransı.
- Stop, hedefler ve planı geçersiz kılan koşullar.
- Kullanılacak strateji/risk profili; miktarı bağımsız risk motoru hesaplar.
- Tutar türü: nominal pozisyon, teminat veya azami kayıp; birim, istenen tutar ve kaldıraç tercihi. Bu ayrım yapılmadan miktar varsayılmaz.
- Hedeflerde çıkış payları ve artık miktar politikası; varsa maliyete stop taşıma koşulu.
- Mod A/B; yetkili kullanıcı ve yetki kaydı; kapsam, sürüm, ortam, son geçerlilik ve kullanım sayısı.
- İzinli yönetim eylemleri, yeniden giriş/azami çalıştırma sayısı ve iptal/değişiklik politikası.
- İlgili mevcut pozisyon/emir kimliği ve önceki plan sürümü.
- Analiz zamanı, gerekçeler, veri eksikleri ve kaynak referansları.

Desteklenmeyen eylem, süresi dolmuş veri, yanlış ortam, geçersiz değer, belirsiz pozisyon ilişkisi veya risk ihlali işlemi reddettirmeli. Modelin güven puanı gerçek başarı olasılığı kabul edilmez.

Yön/seviye, hedef payları toplamı, fiyat/miktar adımları, minimum tutar, yetenek ve sürüm ilişkileri denetlenir. İlk plan sürümünde tek çalıştırma ve yeniden girişin kapalı olması önerilen varsayılandır; etkinleştirme özetinde açıkça gösterilir. Sayısal demo test değerleri canlı risk tercihi değildir.

## Mod A — Sinyal sonrası kullanıcı onayı

Yeni giriş varsayılan olarak onay bekler. Yetkili Telegram kullanıcısı planın belirli sürümünü tek kullanımlık kimlikle onaylar. Kimlik analiz/plan sürümü, ortam, sembol, miktar, stop/hedefler, süre ve kapsama bağlıdır. Sohbette geçen 2 dakika örnektir; gerçek süre/tolerans yapılandırılır.

Onay beklerken yeni pozisyon açılmaz. Yanıt yoksa, ret, süre sonu, yetki iptali veya sürüm değişimi varsa giriş yoktur. Tekrarlı/eski/yetkisiz buton yürütülmez. Onay kullanımı ve emir eylemi kalıcı/atomik kayıtla ilişkilendirilir; yeniden başlatma çift yürütme üretemez.

Onaydan sonra güncel fiyat, veri, plan koşulu, yetenek ve risk yeniden denetlenir. Maddi değişiklik yeni rapor ve onay ister. Stratejik zayıflıkta gerekçe ve yeniden değerlendirme sunulur; sert risk ihlalinde yürütme onayı sunulmaz. Onay risk engelini aşamaz.

## Mod B — Önceden etkinleştirilmiş otomatik plan

Kullanıcı plan özetini görüp belirli sürümü açıkça etkinleştirir. Bu kayıt yalnızca tanımlı ortam/koşul/miktar/süre/çalıştırma sayısı ve izinli giriş-yönetim-çıkış eylemleri için ön yetkidir. Her eylem risk denetiminden geçer ve bildirilir. TradingView alarmı tek başına Mod B yetkisi oluşturmaz.

Kademeli hedef veya maliyete stop taşıma yalnızca tanımlıysa uygulanır. Pozisyon büyütme, yön çevirme, risk artırma veya yeniden giriş etkinleştirilmiş sürümde açıkça izinli değilse yeni yetki ister; teknik destek yoksa izin verilmiş olsa da reddedilir. Bot/AI genel takdir yetkisi almaz veya mod değiştiremez. Değişmiş plan sürümü eski yetkiyi devralamaz.

Plan iptali/süre sonu bekleyen girişleri durdurur; açık pozisyonun koruma ve izinli çıkış yükümlülükleri devam eder. Pozisyon kapatma ayrı komuttur. İki mod aynı hesapta bulunabilir; aynı sembol/pozisyon için tek yönetim sahibi ve çelişmeyen tek etkin yönetim planı gerekir. Koruma onarımı ve önceden izinli risk azaltıcı çıkış tekrar onay beklemez.

## Değişken analiz nasıl uygulanır?

Bugün bir plan koşullu LONG, yarın başka bir plan emir iptali isteyebilir. Altyapı aynı yetenekleri farklı parametrelerle çalıştırır. Yeni analiz mevcut pozisyonu otomatik olarak tersine çevirmemeli; değiştirme politikası açık olmalı.

İlk yetenekler tek giriş, koruyucu emirler ve çıkış olabilir. Çok kademeli giriş, takip eden stop veya hedge ancak adaptör ve test desteği eklendiğinde kullanılabilir. Yeni strateji, mevcut yeteneklerle ifade edilemiyorsa reddedilir ve geliştirme ihtiyacı olarak kaydedilir.

## Durum ve kesintiler

Sinyal: alındı → doğrulandı/tekrar/eski/yetkisiz → bildirim kuyruğu → analiz → raporlandı. Eksik/engelli/bekle sonucu da raporlanır.

Plan: taslak → doğrulandı → Mod A onayı bekliyor / Mod B etkinleştirme bekliyor → yetkili → koşul bekliyor → güncel risk kontrolü → kalıcı gönderim niyeti → emir açık → kısmen gerçekleşti → pozisyon açık/korumalı → kısmi çıkış → kapanıyor → kapandı. Ret, iptal, süre sonu, yetki iptali, giriş durdurması ve belirsiz durumlar ayrı kaydedilir.

Borsa gerçeğini yerel varsayımla karıştırma. Zaman aşımında emrin gerçekleşmediğini varsayma. Yeniden başlatmada borsadaki açık emir/pozisyonlarla kayıtları uzlaştır. Tek hesapta manuel işlemler veya ikinci bot varsa bunu tespit edip tanımlı politikayı uygula.

Olay/eylem kimliği, plan sürümü, yetki, istemci emir kimliği ve fill kayıtları birbirine bağlanır. Kabul gerçekleşme sayılmaz. Kısmi fill kadar pozisyon korunur; kalan giriş miktarı plan politikasına göre yönetilir. Onay/bildirim kaydı emir kaydının yerine geçmez.

## Watchdog ve sahiplik

Kademeli yönetimde hedef miktarları doğrulanan giriş fill'lerinden hesaplanır. Ara paylar lot adımına aşağı yuvarlanır, artık son hedefe gider; minimumu karşılamayan pay için bütçe artırılmaz. Hedef tetiklenmesi, çıkış denemeleri ve stop geçişi mevcut SQLite oturumunda kalıcıdır. Ara hedefler güncel mark fiyatını gören kontrol turunda reduce-only MARKET çıkış gönderir; izleyici kapalıyken çalışmaz. Borsada tam stop ve son hedefte kalan pozisyonu kapatan TAKE_PROFIT_MARKET yedeği tutulur. Kaçırılan fiyat temasının gerçekleştiği varsayılmaz.

Kısmi hedefin açık kalanı önce iptal edilip terminal durum sorgulanır; yalnızca doğrulanan eksik miktar için yeni çıkış mümkündür. Yanıt belirsizse aynı kimlik sorgulanır; kesin ret veya çözülemeyen durum körlemesine yeni deneme üretmez. Tek hedef eyleminde en fazla üç kesin devam denemesi vardır. Tamamlanmış hedef, yeniden başlatmada borsa gerçekleşmeleriyle eşleştirilir; aynı satış tekrar edilmez.

Girişe stop geçişi yalnızca onaylı planın belirttiği hedefin tam miktarı gerçekleşince uygulanır. Yeni stop, ortalama gerçekleşen girişin tick adımına aşağı yuvarlanmış değeridir; komisyon/funding/kayma dahil net sıfır zarar değildir. Geçiş emri doğrulanmış kalan miktar için quantity ve reduceOnly=true kullanır; ikinci bir Close-All stop kurmaz. Yeni stop kabulü, miktarı ve sahipliği doğrulanmadan eski stop kaldırılmaz. Çökme sonrası geçiş kaydı devralınır. Yeni stop kurulamıyorsa eski koruma korunarak sahipliği doğrulanan kalan pozisyonu kapatma politikası uygulanır. Belirsiz gönderim körlemesine tekrarlanmaz; sahiplik doğrulanamıyorsa koruma korunur ve alarm üretilir. Runtime yönetim alanları ve stop geçişi onaylı değişmez plan sürümüyle de doğrulanır. Gönderim hata kodu/HTTP durumu kalıcıdır. Eksik UNKNOWN algo yalnızca -2013 sorgusu, boş pozisyon ve boş tüm açık emir listeleriyle RESOLVED_FLAT olarak uzlaştırılır; bu, tarihsel ret kanıtı veya yeniden gönderim yetkisi değildir.

Kayıtlı oturumun fill/emir geçmişi borsayla eşleştirilir. Manuel işlem aynı net miktara dönse bile sahiplik ihlalidir; bilinmeyen pozisyon otomatik değiştirilmez. Koruma kaybı kesinleşirse tek onarım niyetiyle aynı risk sınırında kurulur; belirsiz yanıt körlemesine yeni emir üretmez.

Koruma doğrulanamaz veya stop aşılırsa yeni girişler durur; sahipliği tekrar doğrulanan pozisyonda reduce-only çıkış politikası uygulanır. Pozisyon sıfır olmadan koruma kaldırılmaz. Ağ yoksa çıkış garanti edilmez; mevcut koruma korunur ve alarm kaydedilir. Bu risk azaltıcı eylemler için ayrıca onay beklenmez.

Mevcut teknik kapsam tek demo LONG/one-way oturumu, 6 günlük otomatik geçmiş penceresi ve 1000 fill üstünde müdahale reddidir. Sürekli izleyici çalışan süreç gerektirir; işletim sistemi servis/otomatik başlangıç ve Telegram alarmı henüz yoktur.

## API ve güvenlik sınırları

Botun yürütme yetkisi = hesap uygunluğu ∩ anahtar izinleri ∩ resmî API yetenekleri ∩ desteklenen plan ∩ kullanıcı yetkisi ∩ risk kontrolleri. Canlı ortam ayrıca açık canlıya geçiş yetkisi ister. API secret imzalama içindir; tam hesap yetkisi değildir. Para çekme kapsam dışıdır. Güncel CLI yalnızca demo adresine bağlanır. `plans` giriş yolu yerel onay kapısından geçer; Telegram/webhook üzerinden üretim onayı henüz yoktur. Eski demo giriş deneyleri açık `--test-only` ister ve ürün akışına bağlanmaz.

Yerel yetkili kimlik `local:işletim_sistemi_kullanıcısı`dır. SQLite'a şema geçişi v1 ile eklenen `plan_versions`, `plan_slots`, `plan_actions` tabloları içerik özeti, onay, sembol rezervasyonu ve tek giriş hakkını saklar. Mevcut kayıtlar korunur. Kullanıcı onayı bir sunucuya gönderilen güvenilmeyen `actor` alanından türetilemez; uzak kimlik doğrulama sonraki katmanın sorumluluğudur. Kütüphane adaptörü ve açık test araçları ayrı geliştirici yetkisidir.

Anahtarları kod, Git, log, ekran görüntüsü veya model girdilerine koyma. Demo/canlı anahtarlarını ayır. IP kısıtı, en az yetki ve anahtar döndürme yaklaşımı kullan. Limit uyarılarında bekle; kısıtlamaları aşmak için IP değiştirme. Güncel endpoint, emir türü ve rate limitlerini resmî belgelerden doğrula; sabit eski sayılara dayanma.

Secret Pine, webhook, Telegram veya istemci tarayıcısına gönderilmez. Telegram callbackleri yetkili kullanıcı/sohbet ve tek kullanımlık kayıtla doğrulanır. Rapor erişimi kimlik denetimlidir. Canlı analiz verisiyle demo emir fiyatı farklılaşabilir; tolerans/eskilik kontrol edilir, demo sonuçları canlı performans sayılmaz.

## Referans başlangıçları

- Binance resmî geliştirici belgeleri: https://developers.binance.com/en/docs/introduction
- Binance API ürünleri ve demo bilgisi: https://www.binance.com/en/binance-api
- API anahtarı kurulumu: https://www.binance.com/en/support/faq/detail/360002502072
- Futures hesap açma ve uygunluk: https://www.binance.com/en/support/faq/detail/360033772992
- TradingView çizim/teknik alarmları: https://www.tradingview.com/support/solutions/43000763315-getting-started-with-technical-alerts/
- Webhook: https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/
- Pine alarm koşulları ve sınırları: https://www.tradingview.com/pine-script-docs/faq/alerts/
- Pine veri erişimi: https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/
- Script yayınlama: https://www.tradingview.com/pine-script-docs/writing/publishing/

Bağlantılar tasarım referansıdır; güncel sayfa, hesap, plan, yayınlama ve API koşulları uygulama/kurulum sırasında yeniden doğrulanmalıdır.

## Kullanıcı akışı ve yeniden uzlaştırma — 6 Kasım 2026

Demo kullanıcı WebSocket bağlantısı mevcut SINGLE/grid yönetimine eklendi.
Olay → kalıcı bekleme işareti → REST kimlik/dolum/sahiplik doğrulaması →
işareti kaldırma → mevcut onay/risk kontrolleriyle yönetim sırası uygulanır.
Yeniden bağlantı yeni işlem yetkisi vermez; belirsiz emir tekrar gönderilmez.
430 test geçti. Gerçek demo bağlantısı ve ping/pong doğrulandı; gerçek
fill/iptal/stop olayı ve uzun süreli kesinti kanıtı henüz tamamlanmadı.
Ayrıntı: [12-KULLANICI-WEBSOCKET-VE-YENIDEN-UZLASTIRMA.md](../../../12-KULLANICI-WEBSOCKET-VE-YENIDEN-UZLASTIRMA.md).

## Takip stopu, teminat ve servis — 6 Kasım 2026

SINGLE için plan onayına bağlı, varsayılan kapalı takip stopu eklendi.
Stop yalnız sıkılaşır; yeni koruma doğrulanmadan eskisi kaldırılmaz.
Aktif bot pozisyonunda izole teminat komutları oturum/plan sürümüne bağlandı.
Grid yeniden girişte güncel kaldıraç basamaklarını kontrol eder.
Kalıcı bildirim kuyruğu, Telegram göndericisi, sürekli servis, sağlık ve
kontrollü durdurma komutları eklendi. Gerçek mesaj veya otomatik görev başlatılmadı.
466 test geçti; gerçek demo yazma kanıtı ve kalan ürün kapsamı tamamlanmadı.
[13-TAKIP-STOP-TEMINAT-VE-SERVIS.md](../../../13-TAKIP-STOP-TEMINAT-VE-SERVIS.md).

## Çoklu oturum sahipliği ve ortak risk — 6 Kasım 2026

Aynı USD-M demo hesabında farklı sembollü v2 SINGLE/grid planları birlikte
çalışır. Emirler plan/hesap/niyet ve sembolle birlikte borsa kimliğiyle doğrulanır.
Bekleyen emirler ve refill dahil tam risk rezervleri ortak hesap sınırlarından
geçer. Kapanışta yalnız ilgili oturumun rezervi atomik bırakılır; eş oturumun
emirleri korunur. run-many ortak ön kontrol, manage-all/run-all tek süreçli
yönetim sağlar. 497 test geçti; gerçek demo işlemi veya profil/bütçe değişikliği
yapılmadı. Kalan kapsam ve kullanım:
[14-COKLU-OTURUM-VE-ORTAK-RISK.md](../../../14-COKLU-OTURUM-VE-ORTAK-RISK.md).


## Neutral grid teslimi — 6 Kasım 2026

NeutralGridRunner tek üst plan/oturum, iki positionSide ve bir risk rezervi kullanır. Hedge zorunludur. Açılış LIMIT, kapanış gerçekleşen miktara bağlıdır; global stop iki brüt tarafı kapatır. Belirsiz emirler kalıcı kimlikle uzlaştırılır. Bildirim işlem yetkisi oluşturmaz.

Ayrıntı: [15-NEUTRAL-GRID-VE-IKI-TARAFLI-YONETIM.md](../../../15-NEUTRAL-GRID-VE-IKI-TARAFLI-YONETIM.md).


## Aktif teminat teslimi — 6 Kasım 2026

İzole teminat komutları hedef oturuma bağlıdır. Çoklu oturum/grid sahipliği ve tüm açık tarafların stopları doğrulanır. Ekleme sonrası varsayımsal kullanılabilir USDT ile ortak kalıcı risk zarfları değerlendirilir. MARGIN bütçesi kalan refill kapasitesini içerir. Belirsiz artımlı POST tekrar edilmez.

Ayrıntı: [16-COKLU-OTURUM-TEMINAT-YONETIMI.md](../../../16-COKLU-OTURUM-TEMINAT-YONETIMI.md).


## Grid takip stopu — 7 Kasım 2026

Yönlü GRID için isteğe bağlı bot takip stopu eklendi. LONG/SHORT watermark ve eşik kalıcıdır; tetikte yeni girişler durur, gerçek kalan miktar kapanış akışına geçer. Native sabit stop korunur; hareketli eşik bot çalışırken izlenir. Neutral/native takip ve diğer politikalar bekliyor. 13 yeni senaryo dahil 573 test geçti; sonuç doğrulama raporuna kaydedildi. Gerçek demo yazma yapılmadı.

Ayrıntı: [17-GRID-TAKIP-STOPU.md](../../../17-GRID-TAKIP-STOPU.md). Kanıt: `reports/development-validation-20261107.json`.


## Grid borsa stopunu yenileme — 7 Kasım 2026

Yönlü GRID için isteğe bağlı `management.trailing.native_stop: true` eklendi. Yeni close-all stop GET ile doğrulanmadan önceki takip stopu kaldırılmaz; başlangıç sabit koruması tutulur. Eski planlar değişmez. 21 yeni senaryo eklendi; tam regresyon sonucu `reports/development-validation-20261107.json` içinde. Gerçek demo yazma kanıtı bekliyor.

Ayrıntı: [18-GRID-BORSA-STOP-YENILEME.md](../../../18-GRID-BORSA-STOP-YENILEME.md).
