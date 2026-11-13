# Grafik–bot bağlantısı öncesi teknik değerlendirme

13 Kasım 2026. Kaynak kodu, güncel grafik planı ve teslim kayıtlarının statik incelemesi. Hesap okunmadı, emir/bildirim gönderilmedi, kişisel veriler değiştirilmedi. Testlerin bu tur yeniden yürütülmesi süreç başlatma EPERM/Access denied hatası nedeniyle mümkün olmadı. Aşağıdaki test sayıları mevcut teslim raporlarının kanıtıdır; yeni test sonucu değildir.

## Karar

Grafiği bota emir göndermeyen sürekli gözlem modunda bağlamanın zamanı geldi. Alarmı doğrudan emir çağrısına bağlamak için henüz hazır değiliz. İlk entegrasyon, mevcut demo kilidini ve risk profilini değiştirmeyen bir sunucu tarafı olay–kural köprüsü olmalıdır. Grafik araçlarını genişletmenin bitmesini beklemek gerekmiyor.

## Güncel gerçek durum

- docs/chart/PLAN.md: çekirdek grafik planı 27/27 kontrollü masaüstü kapsamında tamamlandı; QA01 teslimi mevcut. Fiziksel/genel kabul ayrı.
- 24 numaralı planın son teslimi: kalıcı fiyat/çizim/gösterge alarmları, çoklu koşul ve zaman dilimi, kapanış ve yaklaşık saniyelik intrabar örnekleme, frekans, takvim ve alarm başına tarayıcı kanalları mevcut. Son kayıt 981 backend/319 frontend testi.
- PriceAlertWorker API sürecinde bağımsız thread olarak feed referansı tutuyor. Tarayıcı kapanınca izleme sürebilir; API/bilgisayar kapanınca sürmez.
- P4 BindingService sürümlü hedef bağı, P5 uygunluk, P6/P7 kalıcı olay/intent ve replay var. Bağlar DISABLED/STOPPED; P6 fake sink ve replay alanıyla sınırlı. Bunlar sürekli çalışan live bot adapter'ı değildir.
- Demo yürütme: SINGLE, yönlü/neutral grid, hedge, koruyucu algo emirleri, kademeli çıkış, break-even/trailing, risk rezervleri, çoklu sembol sahipliği, yeniden uzlaştırma ve belirsiz emir koruması kodda mevcut. Yeni yolların gerçek demo fill/kesinti kanıtı tamamlanmış kabul edilemez.
- Config yalnız demo kabul ediyor; DemoExchange adresi demo-fapi.binance.com; plan v2 demo/binance/USD-M doğruluyor. Gerçek hesap entegrasyonu bu çalışmanın konusu değil.
- README ve 07 numaralı durum belgesi eski başlıklar içeriyor; güncel karar için aktif plan, son 24 numaralı ekler ve kaynak kodu esas alınmalı.

## Bağlantıdan önce çözülmesi gerekenler

### 1. Alarm ve bot bağının farklı yaşam döngüsü

alert_conditions.operand çizim geometrisi veya gösterge ayarının snapshotını saklıyor. Çizim operandı drawing_id/revision bağı taşımıyor. BindingService ise hedef değişince eski bağı durduruyor. İki davranış da kendi bağlamında anlaşılır; otomatik işlemde aynı anlamı taşımıyormuş gibi ele alınamaz.

Yeni bot bağı alarm kimliği/revision/hash, strateji sürümü, hedef kimliği/revision, kaynak bağlamı, başlangıç/bitiş, çalışma modu ve yeniden kurma politikasını saklamalı. İlk sürümde hedef değişikliği yeni girişleri durdursun; açık pozisyonun borsadaki stopu korunmalı. Donmuş alarm seçeneği açık etiketlenmeli. Eski alarm verisi sessizce dönüştürülmemeli.

### 2. Bildirim tercihi işlem yetkisi olamaz

Takvim ve kart/ses/desktop seçenekleri bildirim davranışıdır. İşlem zaman penceresi ayrı bir strateji politikası olmalı. History-only alarm işlem yetkisi vermemeli; tarayıcı bildirimi kapalı diye mevcut pozisyon koruması durmamalı. Mevcut once/takvim semantiği köprü tarafından yeniden yorumlanmamalı.

### 3. Olay kaybı ve tekrar emir engeli

PriceAlerts.events son 100 olayı UI için döndürüyor. Köprü bunu periyodik okuyarak kurulmamalı: kuyruk birikmesinde olay kaçabilir. Olay/checkpoint kaydıyla atomik outbox, kalıcı consumer cursor/claim, benzersiz semantic signal kimliği ve execution tarafında benzersiz plan/giriş claim'i gerekli. Uygulama ve execution SQLite depoları arasında tek transaction varmış gibi davranılamaz. Yeniden başlatma/ACK kaybında karşı taraftaki kimlik sorgulanmalı. Transport exactly-once varsayılmamalı; kanıtlanan en fazla bir giriş hedeflenmeli.

### 4. Alarm uygunluğu bot uygunluğundan daha gevşek

PriceAlerts.process temel LIVE/FRESH/OK, kaynak kimliği ve kapanış sürekliliğini denetliyor. P5 ise daha kapsamlı immutable proof, clock, exact provenance, katalog ve revision denetimleri yapıyor. Alarm olayı P5 uygunluğu yerine geçmez. Köprü yeniden doğrulama ve olay anının immutable veri/geometri/formül kanıtını saklamalı. UI LIVE etiketi veya alarm READY durumu tek başına yeterli değildir.

### 5. Grafik fiyatı ile demo yürütme fiyatı

Sinyal kaynağı live_public/LAST_PRICE; yürütme demo ve korumalar MARK_PRICE olabilir. Kaynaklar açık ayrı kimliklerdir. Eski plan_execution.market_guard_check canlı/demo MARK farkını denetliyor; V2Runner/prepare_single giriş yolunda bu eski guard'ın ortak zorunlu kontrol olarak çağrıldığı görülmüyor. Yeni köprü bütün seçilmiş SINGLE/GRID yollarına ortak fiyat eşleştirme ve tazelik bariyeri uygulamalı. LAST→MARK farkı ile live→demo farkı ayrı kaydedilmeli; referans, stop/target yönü ve miktar yürütme öncesi yeniden doğrulanmalı. Fiyat seviyesi sessizce taşınmamalı.

### 6. Gösterge hesaplarının tekrarlanabilirliği

Alarm backend'i series/multi_series/vwap_series kullanıyor; history/seed pencere farkı ekranla sonuç farkı oluşturabilir. Eski analysis.py RSI flat50, yeni sürümlü gösterge modeli flat100 seçeneği içeriyor. Formül adı tek başına yeterli değil: calculation_version, parametre, source, history başlangıcı, warmup, seans/anchor ve as-of zamanı sinyal kanıtına girmeli. P5 gösterge çıktılarını OBSERVE_ONLY tutuyor; alarmdaki gösterge true sonucunu doğrudan trade-eligible yükseltmek ayrı kabul gerektirir.

### 7. Headless işletim ve ölçek

Worker yaklaşık saniyede tüm aktif alarmları değerlendiriyor; feed acquire hatası sessiz geçiliyor ve bir alarmdaki beklenmeyen process hatası turun kalanını kesebiliyor. Bot öncesi alarm başına hata izolasyonu, kapasite/quota, aktif feed ve warmup yönetimi, worker heartbeat, son başarılı değerlendirme, gecikme ve nedenli BLOCKED durumları eklenmeli. Birden fazla API worker başlatıldığında değerlendirme sahipliği/lease açık olmalı. Servis restart/recovery ve güvenli kapanış protokolü gerekli; tarayıcı kapalı testi bilgisayar kapalı çalışma garantisi değildir.

### 8. Finansal API yetkisi ayrı tutulmalı

Bugünkü yerel çizim/alarm API'leri localhost Host/Origin sınırında anahtarsızdır. /api/commands yalnız kimlik doğrulamalı runtime.inspect kabul eder. Buraya doğrudan trade/approve eklenmemeli. Salt okunur hesap görünümü, kuru çalışma ve demo işlem kontrolü ayrı yetki/komut doğrulamasıyla tasarlanmalı. API anahtarı frontend'e taşınmamalı. Halt, yeni girişleri durdurma ve pozisyonu kapatma farklı işlemlerdir.

## Aşamalı uygulama

1. Entegrasyon sözleşmesi: alarm/binding/strategy/signal/plan/session kimlik zinciri; kaynak fiyatları; TTL; revision ve rearm; mod/yetki; notification ve trading schedule ayrımı.
2. Shadow worker: gerçek public veriyle sürekli izleme, kalıcı signal outbox, P5 kanıt kontrolü, NO_ORDER sink. Execution deposu ve borsa yazımı sıfır. İlk kapsam: kapanmış mum, yatay çizgi/bölge veya mevcut kanonik kanal, tek sembol, tek basit kural.
3. Plan önizlemesi: sinyalden mevcut v2 plan şemasına adapter; giriş/stop/hedef/bütçe politikası açık, risk nedeni görünür. Olaydan plan üretmek onay değildir. Aynı sinyal aynı planı verir.
4. Paper çalışma: ücret/kayma/funding ve fill modeli; kaçan sinyal/restart/çakışma; aynı mum stop+hedefte bilinmeyen sıra. P7'nin 36 vakası kârlılık backtesti değildir.
5. Kullanıcı onaylı demo SINGLE: yeni uçtan uca kimlik, tazelik, fiyat farkı, risk, giriş–koruma–fill–restart–kapanış kabulü. İlk kapsam grid veya bağımsız iki yön değil.
6. Sonraki: kanala bağlı grid adapter'ı, bant değişimi ve bekleyen emir geçiş protokolü; ancak SINGLE hattı ve demo doğrulaması oturduktan sonra.

## Grafik ve strateji genişletmeleri

Öncelikli ürün ekleri: alarmdan bot kuralı oluştur; çizimde bağlı kural ve revision göster; neden çalışmıyor paneli; signal→plan→session denetim izi; demo salt okunur pozisyon/emir/stop overlay; risk/masraf önizlemesi. Uygulama tarafında kalıcı worker sağlık ekranı.

Kanal: mevcut kanonik kanal lower/middle/upper hesaplıyor. Görsel channel-family/pitchfork türleri alarm/bot hesabında reddediliyor. Önce tek eski kanala konfigüre bant oranları, fiyatAt/boundsAt, zaman kapsamı ve lineer/log semantiği eklenmeli; bütün yeni araçları bota açmak gerekmez.

Mirror: parent çizim/revision ve referans swing/anchor, eğim/ölçek/zaman kapsamı, türetme sürümü ve invalidation politikası olan nesne. Ana çizim değişince sessizce emir/stop taşınmaz.

Daha sonra: confirmed swing (pivot_at ve confirmed_at ayrı), BOS/CHoCH, kanal aday skoru, sahte kırılım/retest, ATR/yüzde toleransı ve rearm. Çok aşamalı düşüş ve adaptif hedge-grid araştırma hipotezidir. Aynı sembolde bağımsız ana SHORT+ara LONG için alt strateji envanteri, birleşik risk ve çıkış önceliği ayrıca tasarlanır; neutral grid bunun otomatik karşılığı değildir.

## Asgari kabul matrisi

- Tarayıcı kapalı izleme ve API restart sonrası devam; servis durduğunda açık durum göstergesi.
- Aynı sinyal yeniden tesliminde bir plan ve en fazla bir demo giriş; iki worker yarışması.
- Alarm/çizim/strateji değişimi, pause/delete/rebind ve kuyruktaki olay yarışları.
- Gap/stale/epoch/saat sapması/warmup yokluğunda yeni giriş yok; geçmiş snapshot kaçırılmış emre dönüşmez.
- Olay→plan→onay→POST arası TTL/revision/fiyat/risk yeniden kontrolü.
- Gösterge için aynı sürüm/kapalı veriyle UI–alarm–bot sonuç ve kaynak kimliği eşleşmesi.
- Bildirim takvimi ve işlem penceresinin bağımsızlığı; bildirim hatası ikinci emir üretmez.
- POST ACK kaybı, kısmi fill, stop reddi, bağlantı kesintisi, manuel emir ve hesap modu çelişkisi.
- Yeni giriş halt sırasında koruma/azaltma yürüyebilir; bilinmeyen sahiplikte otomatik müdahale yok.

## Sonuç

Yeni bot çekirdeği yazmak gerekmiyor. Mevcut demo yürütücüyü yeniden kullanacak sürümlü ve kalıcı bir sinyal/strateji/plan köprüsü gerekiyor. Emir göndermeyen entegrasyon şimdi yapılabilir; demo emir bağlantısı ayrı kabul aşamasıdır. PostgreSQL, Docker, çok kullanıcılı yapı, tüm göstergeler veya tüm pitchfork çeşitlerinin bot hesabı ilk bağlantının önkoşulu değildir.
