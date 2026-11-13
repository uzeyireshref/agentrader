# İlk sürüm doğrulaması — 3 Kasım 2026

## 9 Kasım 2026 — W2/W3 grafik, veri ve kalıcı çizimler

665 Python ve 9 frontend testi başarılı. Production build başarılı. Gerçek izole localhost HTTP: çizim oluşturma/tekrar/düzenleme/eski sürüm reddi/silme/restore, cookie ve workspace'in restart sonrası korunması geçti. [Tam kanıt](reports/chart-workspace-validation-20261109.json). Public Binance: 504 sözleşme, BTCUSDT 300 mum, LIVE ve geçmiş sayfalama başarılı; [veri kanıtı](reports/chart-live-validation-20261109.json).

Finansal depo/risk profili korundu; hesap isteği veya emir yok. Görsel masaüstü/mobil ve gerçek çizim sürükleme QA henüz doğrulanmadı. W2/W3 tam kabul işaretlenmedi. Kullanım: [21](21-GRAFIK-VE-KALICI-CIZIMLER.md).


## 9 Kasım 2026 — W1 yerel uygulama/API temeli

- İsteğe bağlı FastAPI/Uvicorn adaptörü; HTTP'den bağımsız uygulama sorguları; yalnız localhost başlatma.
- Ayrı application.sqlite3 ve checksum/sürümlü atomik migration. Mevcut execution.sqlite3 yalnız mode=ro ile okunur; anahtarlar veya .env yüklenmez.
- Token doğrulaması, Host/Origin sınırı, sınırlı komut gövdesi ve güvenli hata cevapları. Yalnız runtime.inspect kabul edilir; finansal HTTP komutu yoktur.
- Ayrı tek işçi, kalıcı komut kimliği ve salt okunur çökme kurtarması. Mevcut finansal yürütücü kilidi ve CLI korunur.
- Başlangıç regresyonu 594 test; teslim doğrulaması 37 yeni senaryoyla 631 test, atlanan yok. Gerçek geçici localhost sunucusunda HTTP, ayrı işçi ve restart sonrası tek komut/işleme doğrulandı.
- Kanıt: [web-foundation-validation-20261109.json](reports/web-foundation-validation-20261109.json). Yeniden üretim: python scripts/validate_web_foundation.py . Kullanım: [20-W1-YEREL-UYGULAMA-API.md](20-W1-YEREL-UYGULAMA-API.md).
- İşlem veritabanları ve risk profili doğrulama boyunca değişmedi. Demo yazma/hesap değişikliği/dış mesaj/mevcut izleyici başlatma yok; kontrol sunucusu kapatıldı. Grafik/çizim/piyasa strateji motoru bu paketle tamamlanmış sayılmaz; W2 sırada.


## 9 Kasım 2026 — Kendi grafik yönüne planlama geçişi

Hedefler, W0–W9 geliştirme sırası, mimari ve kullanıcı kabulü yeniden düzenlendi. TradingView/Pine/alarm zinciri ana ürün yolundan çıkarıldı; kendi Binance verili web terminali ana hedef oldu. Mevcut emir/risk/plan çekirdeği ve geçmiş kanıtlar korundu. Önceki hedef belgeleri [arşivde](docs/archive/2026-11-09/README.md).

Bu yalnız planlama teslimidir: grafik/API/strateji uygulaması henüz yoktur. Python regresyonu bu teslimde yeniden çalıştırılmadı; son kayıtlı 594 test 7 Kasım raporuna aittir. Demo emri, hesap ayarı, dış mesaj veya izleyici başlatılmadı. Belge/JSON/bağlantı ve değişmeyen çekirdek kontrollerinin ayrı kaydı: [planning-restructure-20261109.json](reports/planning-restructure-20261109.json). Yeni özellikler için test/demo kanıtı iddia edilmez.


## A1 yetenek ve izin keşfi teslimi — 6 Kasım 2026

- Kullanıcı genel aşamalı geliştirme planını onayladı. A1 uygulandı:
  capabilities.py, capability_cli.py, paket içi sürümlü 95 operasyon kataloğu.
  API istek izinleri allowed_requests() tek kaynağında birleştirildi; yeni
  yazma adresi açılmadı. Yalnız GET /fapi/v1/accountConfig eklendi.
- Offline listeleme Config/.env veya ağ kullanmaz. Public probe da anahtar
  yüklemez. --account açık isteğiyle özel GET kontrolleri çalışır.
- İlk demoda 10/11 kontrol geçti, Account V3'te canTrade yokluğu bulundu.
  Şema düzeltildi; canTrade ayrı accountConfig'den okunur ve yine işlem
  açma yetkisi kanıtı sayılmaz. Eski başarısız kayıt silinmedi.
- Son gerçek demo run_id 563c12a81a1143b68d40b1f0d570d7d0: 12/12 READ_VERIFIED.
  BTCUSDT TRADING, tick .10, lot .0001, minimum nominal 50 USDT.
  One-way, 20x, CROSSED, multiAssetsMargin=true. Açık pozisyon, normal ve
  koşullu emir sayıları 0. Ayarlar değiştirilmedi.
- Kanıt capability_runs tablosuna katalog/anahtar özeti/sembol/zaman ile
  kaydedildi. Eski veya başka anahtarın kanıtı güncel yetki sayılmaz.
  latest komutu bu kapsamda FRESH/STALE/NOT_FOUND döndürür.
- Rapor: reports/capability-probe-20261106.json. Ham yanıtlar ve anahtarlar
  raporlanmaz; sınırlı, şeması doğrulanmış özet saklanır. Hata mesajı içeriği
  rapora taşınmaz; kod ve HTTP durumu tutulur. 429/418/403/451/ağ hatasında
  kalan kontroller durur; onaysız yazma denemesiyle izin keşfi yapılmaz.
- 150 test geçti (önceki 134 + 16 yeni); bütün mevcut testler korunuyor.
  A1 tamamlandı, A2 ve sonraki paketler henüz tamamlanmadı.

## 6 Kasım 2026 genel demo yetenek envanteri

Kullanıcının 'önce bütün işlemleri belirle ve sırala' talebiyle resmî USD-M
REST navigasyonu, demo genel bilgisi, WebSocket ve diğer ürün sınırları
incelendi. 95 operasyon başlığı: hesap 21, trade 32, piyasa 34, kullanıcı
akışı 3, convert 4, portföy marjı görünümü 1. Demo adaptörüyle eşleşen
yöntem/yol sayısı 21; bu tamamlanmış iş akışı sayısı değildir.
scripts/build_capability_inventory.py çalıştırıldı; 95 benzersiz kimlik,
kategori sayıları ve yöntemler denetlendi. Dosyalar:
reports/binance-demo-capabilities-20261106.json ve
reports/binance-demo-api-islem-listesi-20261106.md.

Yeni 06 numaralı belge 48 işlev/strateji maddesi, 20 açık yazılım eksikliği ve
A0–A12 teslim sırasını içerir. A0 araştırması tamamlandı; A1 uygulanmadı.
Üretim kodu veya API izin listesi değiştirilmedi. Hesap sorgusu, emir,
iptal, kaldıraç/teminat/mod değişimi yapılmadı. Önceki son test koşusu 134;
bu araştırma yeni borsa test kanıtı olarak gösterilmedi. Kaynak şema/HTML
indirme denemeleri boş yanıt verdi; eksiksiz otomatik OpenAPI çıkarımı iddiası yok.

## Stop tekrar testi: giriş ve koruma doğrulandı — 5 Kasım 2026

`btc-stop-retest-20261104-225620` v1 kullanıcının açık onayıyla yürütüldü.
Tek MARKET BUY, .0008 BTC, borsada FILLED. Gerçek ortalama giriş 80616.10,
nominal 64.492880 USDT; başlangıç stopu 80241.80, hedefler 80999.10/81251.50.
Gerçek stop mesafesi riski .29944 USDT, komisyon/funding/kayma hariç.
STOP_MARKET ve son hedef TAKE_PROFIT_MARKET korumaları doğrulandı.

İlk izleyici PID 31892, Türkçe karar metnini yönlendirilmiş cp1252 çıktıya
yazarken durdu; pozisyon ve borsadaki korumalar etkilenmedi. JSON kayıtları
ASCII Unicode kaçışları kullanacak şekilde düzeltildi; cp1252 regresyon testi
eklendi. Ayrı süreç PID 19192 `--resume-only --restart-after-stop` ile aynı
oturumu devraldı ve iki protected raporu verdi; ikinci giriş yolu yok. Güncel kayıtlar:
`logs/approved-stop-retest-225620-resume.jsonl` ve `.err.log`.

İlk hedef ve stop geçişi henüz bekleniyor. Borsa stopu taşındıktan sonraki
otomatik süreç devri ayrıca `restart_verified` olayıyla doğrulanacak;
bu kayıt o testin tamamlandığı anlamına gelmez. Tam 118 testlik son kontrol
başarılı. Son kontrolde ilk hedef WAITING ve izleyici çalışır durumda.

## Stop taşıma hata düzeltmesi — 5 Kasım 2026

Kesin bulgu: başarısız stop POST'unun ilk hata kodu/HTTP bilgisi saklanmamış;
UNKNOWN niyeti sonraki -2013 sorgularıyla izleyiciyi tekrar eden alarma sokmuş.
İlk gönderimin ret nedeni geçmiş kayıtlardan kesinleştirilemiyor. Aynı anda
ikinci Close-All stop kullanımı olası çakışma kaynağıdır; bu olayda -4130
alındığı kanıtlanmış değildir.

- Gönderim hatası güvenli mesaj, kod ve HTTP durumuyla kalıcı kayda alınıyor.
  Bilinen kesin retler (ör. -4130/-4509) UNKNOWN sayılmıyor. Koruma gönderimi
  kesin reddedilirse sonradan -2013 sorgusuyla ilk hata maskelenmiyor.
- Stop geçişi kalan doğrulanmış miktar için quantity + reduceOnly=true
  kullanıyor. Eski stop yeni stop doğrulanana kadar kalır. Eksik miktar
  koruması reddedilir. Yeniden başlatmada çift çıkış/stop üretilmediği sınandı.
- UNKNOWN algo için -2013, hesap tamamen boş ve tüm açık emir listeleri boş
  olduğunda RESOLVED_FLAT ile sonlandırılabilir. Bu tarihsel gönderimin
  reddedildiği iddiası değildir; aynı POST yeniden gönderilmez. Açık pozisyon,
  herhangi açık emir veya ağ hatasında UNKNOWN korunur.
- `managed-finalize` yalnızca GET ile sahipliği ve tüm emirlerin sonlanmasını
  doğrular; zaten boş oturumu kapatır. Borsaya yeni emir veya iptal göndermez.
- Demo üzerinde pozisyon açmadan quantity/reduceOnly STOP_MARKET biçimi
  kabul edildi ve deneme emri iptal edildi. Close-All denemeleri boş hesapta
  -4509 verdi; bu deneme özgün çakışma nedenini kanıtlamaz.
  Kanıt: `logs/stop-reproduction.json`.
- Orijinal pozisyonun kalanı son hedef algo emriyle kapandı (FINISHED).
  Oturum CLOSED olarak uzlaştırıldı. Son recover --clear-halt sonucu:
  ready=true, issues=[], pozisyon/normal emir/algo emir sayıları 0.
- 116 ağsız test geçti. Bu düzeltmeyle yeni açık pozisyonda hedef sonrası
  stop taşıma uçtan uca tekrar edilmedi; yeni somut plan/onay gerektirir.
- Otomatik denetim `watchdog --execute-demo` komutunu yeni giriş riski
  gerekçesiyle reddetti. Bunun yerine emir göndermeyen `managed-finalize`
  ve salt borsa okuması yapan recover ile uzlaştırma tamamlandı.

## Kullanıcı onayı sonrası gerçek demo sonucu — 5 Kasım 2026

- `btc-immediate-demo-20261104-221415` v1 için kullanıcının açık onayıyla
  600 saniyelik tek giriş yetkisi kaydedildi. Yetki kapsamında tek MARKET BUY
  emri gönderildi; borsadan tekrar okunan sonuç FILLED.
- BTCUSDT LONG .0008 BTC, gerçek ortalama giriş 80413.30,
  nominal 64.330640 USDT. Stop 79803.50, hedefler 80549.30 / 80797.90.
  Gerçek girişe göre stop mesafesi riski .48784 USDT; komisyon, funding ve
  kayma hariç. Onaylanan nominal/risk/fiyat toleransları aşılmadı.
- STOP_MARKET ve son hedef TAKE_PROFIT_MARKET closePosition emirleri
  borsada doğrulandı. İlk hedef yerel izleyicide .0004 BTC kısmi kapatma,
  tamamlanınca stopu gerçek giriş ortalamasına taşıma olarak bekliyor.
- İlk plan yürütme süreci korumayı kurup MANAGING durumuyla sonlandı.
  Ayrı Python süreci `--resume-only` ile aynı oturumu ve entry kimliğini
  devraldı; yeni süreçte watchdog tekrar protected raporu verdi. Girişten
  itibaren yalnızca bir BUY niyeti ve iki koruma niyeti var; çift giriş yok.
- Kesinti testinde stop/son hedef silinmedi. İzleyici PID 19192 olarak
  arka planda çalışıyor. JSONL: `logs/approved-demo-221415.jsonl`;
  kanıt: `logs/approved-demo-restart-221415.json`.
- Bu kayıt anında hedefler WAITING. Kısmi hedef ve girişe stop taşımanın
  bu yeni pozisyondaki borsa gerçekleşmesi henüz doğrulanmış değildir;
  doğal fiyat hareketi bekleniyor. Çevrimdışı doğrulama: 108 test başarılı.

## Güncel durum — 5 Kasım 2026: dört adımlı demo yönetim testi

1. Fiyat gözlemi kaydı eklendi: beklerken fiyat/tetik farkı ve engellenirken
   neden, ayrı `plan_price_check` olayında tutuluyor. Bekleme kayıtları yetkiyi
   tüketmiyor. Fiyat toleransı reddinde emir gönderilmediği testle doğrulandı.
2. Yeni canlı veri raporu `reports/market-1793830316279-4.json`, durum OK.
   Demo hesap uzlaştırması ready=true; pozisyon/normal emir/algo emir sayısı 0.
   `btc-immediate-demo-20261104-221415` v1, PENDING_APPROVAL olarak hazırlandı.
   Onay sonrası IMMEDIATE giriş; referans 80300.70, nominal üst sınır 70 USDT,
   tahmini .0008 BTC; stop 79803.50; yarım hedefler 80549.30 / 80797.90.
   İlk hedef sonrası stop gerçek giriş ortalamasına tick yuvarlamasıyla taşınır.
   Stop riski yaklaşık .398 USDT, komisyon/funding/kayma hariç. Canlı/demo
   fiyat farkı hazırlıkta 16.78 bps; üst sınır 50 bps. Gönderimde tekrar ölçülür.
3. Kısmi kapatma ve stop taşıma çevrimdışı testleri başarılı; yeni planla
   gerçek demo gerçekleşmesi henüz yok. Belirli planın kullanıcı onayı bekleniyor.
4. IMMEDIATE planla giriş sonrası yeniden açılan SQLite oturumunda aynı
   session/entry kimliği, çift emir olmaması ve ardından kısmi hedef/stop
   yönetimi çevrimdışı doğrulandı. İzleyiciye `--resume-only` eklendi; bu yol
   yalnızca eşleşen mevcut oturumu yönetir, yeni giriş açmaz. Yeni planla ayrı
   süreç üzerinden gerçek demo devralma testi pozisyon açıldıktan sonra yapılacak.

Toplam 108 ağsız test başarılı. Yeni teklif onaylanmadı; yeni emir gönderilmedi.
Önceki koşullu teklif EXPIRED oldu; eski onay yeni plana taşınmadı.

## Canlı veriden demo teklif hazırlığı — 5 Kasım 2026

- Güncel BTC raporu reports/market-1793827020303-3.json: veri OK. Demo hesabı
  salt okunur uzlaştırmada boş ve ready=true. Yeni emir gönderilmedi.
- btc-live-demo-20261105-012017 sürüm 1, Mod A PENDING_APPROVAL olarak kaydedildi.
  Son 15m tepe + tick giriş eşiği, 2 ATR stop ve 1/2 ATR hedeflerinden oluşan
  küçük, tek çalıştırmalık altyapı testidir; strateji kârlılığı doğrulanmadı.
- Giriş öncesi canlı/demo mark fiyat farkı ve eskilik denetimi onaylı planın
  market_guard alanına bağlandı. Farklı sembol, eski fiyat veya aşırı fark girişe engel.
- Toplam 107 ağsız test başarılı. Kullanıcı bu somut planı henüz onaylamadı;
  token yerel yetki kaydına bağlı, secret/hesap anahtarı rapora konmadı.
- İnceleme dosyası reports/proposal-btc-live-demo-20261105-012017.md.

## Canlı veri ve temel analiz — 5 Kasım 2026

- PublicMarket: anahtarsız, sabit canlı hostta yalnızca time/exchangeInfo/klines
  GET uçları. Hesap/emir ve secret/imza parametreleri reddediliyor. Demo emir
  adaptörü değiştirilmedi; market komutu Config/.env yüklemiyor.
- W/D/4H/1H/15M, ayrı SQLite mum deposu ve EMA20/50, Wilder RSI14/ATR14,
  önceki 20 mum hacim karşılaştırması ve 7 tamamlanmış UTC günlük hacim raporu var.
- 105 ağsız test başarılı: gösterge başlangıç/hesap örnekleri, açık mum/ileri
  bilgi dışlama, haftalık UTC hizası, boşluk/eskilik/yetersiz veri, tekrar/çelişki,
  sayfalama, kayıt revizyonu, günlük eksik hacim, anahtar yüklememe ve limitte durma.
- Gerçek canlı Binance BTCUSDT/ETHUSDT perpetual verisi okundu: 3010 kayıt,
  beşer zaman dilimi OK. Kesim 2026-11-04 21:10:05.037 UTC = 5 Kasım
  01:10:05.037 Bakü. Rapor: reports/market-1793826605037-1.md ve .json.
- Ayrı çevrimdışı tekrar raporu aynı göstergeleri ve girdi SHA-256 özetini
  verdi: 5c82ea738e677c11d7d653787ea7a1d551e3d76daa924283e783a190e975607e.
- Mumlar ve değişmez analiz girdileri data/market.sqlite3 içinde. Güncel kısa
  yol reports/market-latest.*; canlı/kayıtlı mod raporda açıkça belirtiliyor.
- Bu geliştirmede demo/canlı işlem açılmadı, plan yetkisi kullanılmadı. Raporun
  BEKLE sonucu teknik raporun işlem stratejisine bağlı olmadığını gösterir.
- Hacim yeni para girişi değildir; borsa akışı, dominans/TOTAL3, yapı, haber/AI
  ve sürekli WebSocket izleme henüz yoktur. Kademeli çıkışın gerçek demo testi
  için önceki kullanıcı planı/onayı gereksinimi devam eder.

## Kademeli hedefler ve giriş fiyatına stop — 5 Kasım 2026

- Plan şeması v1 artık 1–8 sıralı hedef, toplamı 1 olan paylar ve son hedeften
  önceki seçili hedef sonrası girişe stop taşıma iznini destekliyor. Tek giriş,
  demo LONG/one-way ve önceki Mod A/B yetki sınırları korunuyor.
- Payların lotlara dağıtımı, son hedefte artık miktar, gerçekleşmiş kısmi girişten
  yeniden dağıtım ve bölünemeyen payların giriş öncesi reddi doğrulandı.
- İlk hedefte yalnızca pay miktarı reduce-only çıkıyor; hedef tamamen
  gerçekleşince gerçek ortalama girişe tick uyumlu stop taşınıyor. Yeni stop
  doğrulanmadan eski stop kaldırılmıyor. Son hedef kalan pozisyonu kapatıyor.
- Toplam 86 ağsız test başarılı. Yeni kapsam: kademeli kapanış, iki hedefi geçen
  fiyat boşluğu, kısmi giriş/çıkış, kayıp yanıt, gönderimden önce/sonra çökme,
  yeni stop kabulü ile eski stop iptali arasında çökme, yeniden başlatmada çift
  satış/stop oluşmaması, başarısız stopta kapanış, fiyat geri dönüşü, yetkisiz
  runtime değişiklik, manuel müdahale, eski veri ve salt okunur kontrol.
- Onaysız/etkinleştirilmemiş plan yürütülemiyor. Yeni kademeli senaryolar
  kullanıcının gerçek demo hesabında test edilmedi; bu geliştirmede borsaya
  yeni emir gönderilmedi. Gerçek demo deneyi için somut plan incelemesi/onayı gerekir.
- Ara hedefler watchdog'un gördüğü güncel mark fiyatıyla MARKET çıkıştır;
  borsada bekleyen ayrı kısmi TP emirleri değildir. İzleyici kapalıyken ara
  hedef ve stop taşıma çalışmaz; borsadaki tam stop ve son hedef yedeği kalır.
  Net komisyon sonrası sıfır kayıp veya hedef fiyattan kesin gerçekleşme garantisi yoktur.
- `plans example --staged` ağsız örnek üretir. SQLite mevcut oturum kayıtlarına
  hedef/stop geçişi ekler; yeni emir akışı aynı kalıcı niyet mekanizmasını kullanır.

## Plan ve yerel yetkilendirme — 5 Kasım 2026

- Şema v1: demo Binance USD-M/one-way LONG, belirli fiyat koşulu, nominal veya
  tahmini azami kayıp bütçesi, stop ve tek tam çıkış hedefi; bir kez çalıştırma.
- Mod A'da belirli içerik/sürüm için tek kullanımlık onay; Mod B'de ayrı açık
  etkinleştirme. Yerel işletim sistemi kullanıcı kimliği depo sahibidir.
- Plan oluşturma onay sayılmaz. Yetkisiz, geç, reddedilmiş, iptal veya değişmiş
  sürüm planı yürütülemez. Onay tekrarları süreyi yenilemez; aynı sembolde çelişen
  etkin plan reddedilir. Önizleme emir göndermez veya giriş hakkını tüketmez.
- Onay sonrası koşul/fiyat/risk ve sembol adımları yeniden kontrol edilir.
  Gönderim niyeti ayrıldıktan sonraki süre sonu da POST'u engeller. Kullanılmış
  giriş hakkı SQLite yeniden açılışında tekrar kullanılmaz.
- Yeni akış mevcut DurableExchange ve Watchdog'a bağlandı. Gerçekleşme fiyatı
  onay kapsamını aşarsa sahipliği doğrulanan pozisyonda reduce-only çıkış denenir.
  Açık planı iptal etmek mevcut korumayı silmez; pozisyon kapatma ayrıdır.
- Toplam 61 ağsız test başarılı. Yerel CLI example/create/approve/show/cancel
  akışı geçici depoda gerçek alt süreçlerle sınandı. Mod A/B yürütmeleri,
  kısmi/çelişkili durumlar ve kapanış eşleştirmesi taklit borsa üzerinde sınandı.
- Bu geliştirmede kullanıcının demo hesabında yeni plan oluşturulmadı,
  onaylanmadı, etkinleştirilmedi veya emir gönderilmedi. Yeni plan yolunun gerçek
  demo borsası testi, kullanıcının somut planı inceleyip onaylamasını gerektirir.
- Kademeli hedef/maliyete stop, SHORT/hedge, teminat tutarı ve yeniden giriş
  henüz desteklenmez; bu planlar şema/yetenek denetiminde reddedilir. Koşul
  kontrolü komut başına tek turdur; sürekli koşul işçisi henüz yoktur.
- Telegram/webhook kimlik doğrulaması ve onay arayüzü henüz yoktur. Eski demo
  giriş deneyleri ayrıca --test-only gerektirir; ürün giriş yolu değildir.

## Güncelleme — 4 Kasım 2026

### Dört adım: izleme, devralma, koruma onarımı, demo kesinti testi

1. Sürekli watchdog döngüsü eklendi. Her tur hesap modu, pozisyon, normal/algo
   emirler ve gerçekleşme geçmişi eşleştiriliyor. Geçici ağ hatasında girişler
   duruyor, mevcut koruma korunuyor ve sonraki tur yeniden okuma deneniyor.
2. Yönetilen oturumlar SQLite'a girişten önce kaydediliyor. Aynı miktar yeterli
   sahiplik kanıtı sayılmıyor; tüm fill emir kimlikleri eşleşmeli. Manuel
   işlem, bilinmeyen emir veya miktar uyuşmazlığında otomatik müdahale reddediliyor.
3. Kesin iptal edilen stop bir kez yeniden kuruluyor. closePosition koruması
   kısmi pozisyonun kalanını da kapsıyor. Koruma kurulamama durumunda sahiplik
   yeniden doğrulanıp reduce-only kapatma uygulanıyor (hata enjeksiyonu testinde).
4. Gerçek demo hesabında 0.0008 BTC LONG açıldı, stop/TP kuruldu ve Python
   süreci os._exit ile aniden sonlandırıldı. İki ayrı yeni işletim sistemi
   süreci aynı oturumu yeni giriş/koruyucu emir üretmeden devraldı.

Oturum: agt-02ff5cdf49eb423cb97defa48e0d.
`scripts/check_demo_restart.py` kendi stopunu iptal ederek tek onarımı ve ikinci
kontrolde çift emir oluşmadığını doğruladı. Ardından pozisyon kapandı.
`logs/restart-test-result.json`: position_count=0, open_order_count=0,
open_algo_order_count=0, issues=[], halt_reason=null, ready=true.

35 çevrimdışı test başarılı. Gerçek demo üzerinde ani süreç sonlandırma,
iki ayrı süreçte devralma ve stop kaybı/onarımı sınandı. İnternet kablosu/Wi-Fi
gerçekte kesilmedi; ağ hatası ve koruma kurulamama çevrimdışı enjeksiyonla sınandı.
SHORT/hedge, uzun süreli sunucu hizmeti, Telegram alarmı ve gerçek para kapsam dışı.
İzleyici terminalde çalıştırılır; görev sonunda sürekli arka plan süreci bırakılmadı.

### Önceki geliştirme aşamasının kaydı

### Kalıcı yürütme ve risk altyapısı

- 23 çevrimdışı test başarılı: SQLite yeniden açılışında kayıp gönderim yanıtı,
  gönderim öncesi çökme benzetimi, tek kimlikle çift gönderim engeli, değişen
  parametre reddi, kısmi gerçekleşme ve manuel pozisyonda giriş durdurma,
  durdurma aktifken reduce-only çıkış, risk ihlali ve süreç kilidi kapsandı.
- CLI demo emirleri SQLite'a gönderim öncesi kaydediliyor. Başlangıç ve bitişte
  read-only uzlaştırma yapılıyor. Risk profili risk-demo.json (canlı tercihi değil).
- Yeni altyapıyla demo BTCUSDT 0.0008 BTC açıldı (orderId 28666133155),
  stop/TP doğrulandı; 0.0004 + 0.0004 BTC reduce-only çıkış gerçekleşti.
- Son uzlaştırma: 3 normal emir FILLED, 2 algo emir EXPIRED, pozisyon 0,
  açık normal/algo emir 0, ready=true, halt_reason=null.
- Kesintiler çevrimdışı hata enjeksiyonuyla sınandı; gerçek ağ kesme veya açık
  pozisyondayken işletim sistemi sürecini öldürme testi henüz yapılmadı.
- Kurtarma güvenli biçimde girişleri durdurur ve mevcut korumaya dokunmaz;
  kısmi pozisyonun otomatik koruma onarımı/devralınması ve sürekli watchdog
  henüz yoktur. Tam otonom işlem aşamasına geçilmedi.

### Pozisyon yaşam döngüsü testi

- 12 çevrimdışı test başarılı; giriş yanıtının kaybolması, hatalı koruma sonrası
  acil çıkış, reduce-only çıkışlar ve önizlemenin emir göndermemesi kapsanıyor.
- BTCUSDT demo MARKET BUY 0.0008 BTC gerçekleşti (orderId 28666125998).
  Ortalama giriş 80.396,10 USDT; gerçekleşen nominal tutar 64,31688 USDT.
- STOP_MARKET 78.768,80 ve TAKE_PROFIT_MARKET 81.984,00; MARK_PRICE,
  closePosition=true, SELL/BOTH ve NEW durumları sorgulanarak doğrulandı.
- Reduce-only 0.0004 BTC kısmi çıkış FILLED; kalan pozisyon 0.0004 BTC doğrulandı.
- Kalan 0.0004 BTC reduce-only çıkış FILLED.
- Son pozisyon 0; açık normal ve algo emir sayısı 0. Koruyucu emirlerin son
  durumları CANCELED olarak kaydedildi. logs/demo-positions.jsonl kanıt kaydıdır.
- Koruyucu emirler tetiklenmedi; stop/TP gerçekleşmesi, SHORT, hedge,
  bağlantı kesintisinde otomatik yeniden başlatma henüz demo borsasında test edilmedi.
- Gerçek hesap ve gerçek para kullanılmadı. Bu sonuç strateji performansı ölçümü değildir.

### Önceki limit deneyi kaydı

Sanal bakiye eklendikten sonra kullanılabilir 5.000 USDT API üzerinden doğrulandı.
Gerçek demo limit emir döngüsü başarılı: BTCUSDT BUY LIMIT GTX, 0.0007 BTC,
78.749,00 USDT fiyat; emir kimliği 28666122441. Sorguda NEW, iptal sonrası
CANCELED ve executedQty=0 doğrulandı. Bu testte pozisyon oluşmadı.
Olaylar logs/demo-orders.jsonl dosyasında saklanıyor. 8 çevrimdışı test başarılı.
Bu limit deneyi sırasında stop/TP ve pozisyon kapatma kapsam dışında tutuldu.

### Sanal bakiye eklenmeden önceki tarihsel kayıt

Demo kimlik doğrulaması, hesap okuma, saat eşitleme ve BTCUSDT sembol kuralları
gerçek bağlantıyla başarılı. Hesap one-way modunda; açık emir ve pozisyon yok.
Kullanılabilir demo bakiye 0 USDT. Limit emir döngüsü eklendi; sanal bakiye
eklenmeden gerçek demo emir kabul/sorgu/iptal senaryosu tamamlanamaz.
Önceki aşağıdaki kayıtlar ilk sürümün tarihsel durumudur.

- Python 3.12.6 üzerinde 5 çevrimdışı test başarılı.
- CLI yardım ve hata çıkışları kontrol edildi.
- Demo dışındaki ortamlar reddediliyor; emir endpointi izin listesinde yok.
- Anahtarsız demo bağlantısı denendi; bu yürütme ortamında ağ/TLS hatası alındı.
  Sandbox dışı deneme de aynı sonucu verdi. Sunucu saati ve sembol kuralları
  gerçek bağlantıyla henüz doğrulanamadı.
- Demo API anahtarları henüz sağlanmadığından hesap okuma doğrulanmadı.
- Gerçek hesap erişimi ve emir yetenekleri test edilmedi.

Bir sonraki adım: kullanıcı bilgisayarında `python -m agentrader diagnose`
komutuyla bağlantıyı doğrulamak, ardından yerel demo anahtarlarıyla `--account`
kontrolünü tamamlamak. Bağlantı ve hesap okuması doğrulanmadan emir aşamasına geçilmez.

### 2026-11-05: Kullanıcı onaylı koşullu demo izleme

`btc-live-demo-20261105-012017`, sürüm 1 için kullanıcının açık onayı kaydedildi.
Giriş yetkisi 600 saniye; süre yenilenmez. İlk yürütme kontrolü
`WAITING_CONDITION` döndürdü; bu aşamada emir gönderilmedi.
`scripts/watch_approved_demo.py` tek yürütücü kilidi altında arka planda başlatıldı
(PID 3128). Süre dolana kadar koşulu kontrol eder; gerçekleşirse yalnızca bir giriş
ve mevcut watchdog ile onaylı stop/kademeli hedef yönetimini yürütür.
Güncel sonuç: `logs/approved-demo-012017.jsonl`; hatalar:
`logs/approved-demo-012017.err.log`. Bu kayıt gerçekleşmiş bir giriş veya hedef
başarısı iddiası değildir. Bilgisayar/izleyici kapanırsa yerel ara hedef takibi durur;
borsada başarıyla kurulmuş koruma emirleri ayrıca geçerliliğini sürdürür.

Koşullu demo izleme sonucu: onay süresi dolduğunda plan `EXPIRED` oldu ve
izleyici normal olarak durdu. Giriş koşulu izleme boyunca gerçekleşmedi;
bu plan kapsamında demo giriş emri gönderilmedi. Süre otomatik yenilenmedi.

### Son durum: ilk hedef gerçekleşti, stop taşıma alarmı

İlk hedefin .0004 BTC reduce-only çıkışı COMPLETED; kalan pozisyon .0004 BTC.
Yerel stop geçişi 80413.30 için PENDING. Yeni stop niyeti UNKNOWN; Binance
sorgusu -2013 döndürüyor. Eski 79803.50 stopu ve 80797.90 son hedefi açık
algo emirleri üzerinden aktif doğrulandı. Dolayısıyla girişe stop taşıma
borsada başarılı sayılmaz. Watchdog yeniden sorguluyor, yeni girişler kalıcı
olarak durdurulmuş durumda. Belirsiz POST tekrar gönderilmedi, eski stop silinmedi.

## Stop duzeltmesi sonrasi yeni demo plani — 5 Kasim 2026

Kullanici dort adimlik tekrar testini istedi. Guncel BTC raporu
reports/market-1793832923523-5.json, durum OK. Hesap ready=true;
pozisyon/normal emir/algo emir sayilari 0, halt yok.
Yeni plan btc-stop-retest-20261104-225620 v1 PENDING_APPROVAL olarak kaydedildi.
IMMEDIATE LONG, referans 80746.70; nominal ust sinir 70 USDT; tahmini .0008 BTC
ve 64.59736 USDT nominal. Stop 80241.80; hedefler 80999.10 / 81251.50.
Ilk hedefte .0004 BTC azaltma, ardindan giris ortalamasina reduceOnly stop
ve yeni stop dogrulandiktan sonra eski stop iptali. Stop riski tahmini
.40392 USDT, masraflar haric. Hazirlikta canli/demo farki 4.397 bps.
Gonderimde fiyat/risk/eskilik/fark tekrar denetlenir. Onay sonrasi giris
izni 600 saniye, otomatik yenileme veya yeniden giris yok.
Birinci hedef/stop dogrulaninca ayri surecte resume-only ile ayni oturum,
giris kimligi ve stop korunarak devralma testi yapilacak. Bu test henuz
baslamadi: somut plan onayi bekleniyor, yeni emir gonderilmedi.
Inceleme: reports/proposal-btc-stop-retest-20261104-225620.md.

## Stop retest plani onaylandi — 5 Kasim 2026

btc-stop-retest-20261104-225620 v1 icin kullanici acik onay verdi;
600 saniyelik giris yetkisi kaydedildi. Izleyici PID 31892 ile baslatildi:
logs/approved-stop-retest-225620.jsonl / .err.log.
Bu kayitta giris EXECUTING asamasinda; FILLED/koruma sonucu henuz ilan edilmedi.
Izleyiciye --restart-after-stop eklendi. Yalnizca watchdog protected raporu
ve stop_transition=APPLIED sonrasinda oturum/giris/stop/PID kontrol noktasi
kaydedilir, kilit birakilir ve ayri surecte --resume-only baslatilir.
Yeni surecin ilk protected raporunda giris ve stop kimligi, farkli PID ve tek
BUY niyeti dogrulanir; restart_verified olayi yazilir. Hedefe ulasilmaz veya
pozisyon oncesinde kapanirsa bu test basarili sayilmaz.
Mevcut 116 test ve ek yeniden baslatma kimlik/cift giris testi ayri ayri gecti.

## 6 Kasım 2026 kaldıraçlı grid isteği

Kullanıcı 20x LONG, giriş 75725, bant 73000–82500, 8 grid, stop 71000 ve
200 USDT toplam nominal istediğini açıkça belirtti. salt okunur demo ön
kontrolü BTCUSDT minimum yeni alış tutarı 50 USDT, lot .0001, tick .10
buldu. Hesap kaldıraç 20/CROSSED; pozisyon ve açık emir yok. Yeni emir veya
kaldıraç değişimi gönderilmedi. İstek minimum grid alış tutarı ile mevcut
bağımsız risk sınırlarından BLOCKED. Ayrıntı grid-preflight-20261106.json.
Planlama, kaldıraç adaptörü ve kalıcı offline döngü defteri eklendi. Gerçek
borsa grid yürütücüsü henüz tamamlanmadı; bütün grid özelliği tamamlandı
olarak işaretlenmedi. 132 test geçti (14 yeni). Kullanıcının bütçesi 20 ile
çarpılmadı, grid sayısı/stop/risk sınırı kendiliğinden değiştirilmedi.

## 6 Kasım 2026 — A2 ve sonraki paketlerin temelleri

218 test başarılı. Yeni ortak transport üzerinden 12/12 salt okunur demo
kontrolü geçti: reports/capability-probe-after-transport-20261106.json.
Bu geliştirme grubunda emir/ayar değişikliği yapılmadı. A3–A8 tamamlanmış
değildir; risk/plan v2, ayar komut defteri, emir doğrulayıcı, gerçekleşme
projeksiyonu ve grid durdurma bariyeri eklendi. Ayrıntılı kapsam ve eksikler
07-GELISTIRME-DURUMU.md içinde kayıtlıdır.

## Sonraki geliştirme — plan v2 yürütme bağlantısı

249 test geçti. Taze boş hesap/risk görünümü, USDT teminatla sınırlı multi-assets
değerleme, miktar/masraf/drift rezervi, kaldıraç basamağı ve SINGLE LONG/SHORT
yürütücüsü eklendi. One-way/hedge piyasa girişi, tek stop/son hedef, kayıp yanıt,
kısmi giriş/kapanış, iptal yarışı, restart ve yetki iptali sahte borsada doğrulandı.
Gerçek demo emri veya ayar değişikliği bu turda yapılmadı. Gerçek boş hesap
kontrolü mevcut pozisyon/açık emir nedeniyle BLOCKED oldu:
reports/v2-snapshot-readonly-20261106.json. Bu bir başarılı emir testi değildir.
Grid, LIMIT ve v2 kademeli hedef yürütme eksikleri sürüyor.

## LIMIT, kademeli hedef, break-even ve sürekli izleme

Son test koşusu 270 test, başarılı. Önceki LIMIT/kademeli hedef eksikleri
SINGLE v2 yürütücüsünde giderildi. Yeni stop GET ile doğrulanmadan önceki
stop korunur; kalan pozisyon küçüldüğünde yeni stop miktarı da küçülür.
LONG/SHORT, hedge alanları, kısmi hedef/iptal yarışı, kayıp stop/iptal yanıtı,
yanlış stop yanıtında eski korumanın korunması ve TRIGGERING durumunun terminal
sayılmaması test edildi. Sürekli izleme yalnız mevcut oturumu devralır ve
belirsiz hatada tekrar POST yapmadan durur. Bu turda gerçek emir/hesap ayarı
değişikliği veya izleyici başlatma yapılmadı. Grid yürütmesi hâlâ eksiktir.

## Grid, izole teminat ve seçili toplu iptal — güncel doğrulama

Son tam koşu 340 test, başarılı. GridRunner ve rezervasyon kodu 08 dosyasında;
izole teminat ve native toplu iptal kapsamı 09 dosyasında belgeli. Yeni testler
belirsiz artımlı teminatın tekrar edilmemesi, geciken geçmiş, yanlış ACK,
güvenli teminat azaltması, hedge tarafı, kısmi toplu iptal, kayıp DELETE yanıtı,
iptal/fill yarışı ve tamamen gerçekleşmiş emirleri tekrar sorgulamadan devralmayı
doğrular. CLI yardım komutları da çalıştı. Bu çalışmada gerçek demo hesabına
yazma isteği, yeni emir veya arka plan izleyicisi gönderilmedi/başlatılmadı.

## Native amend, toplu değiştirme ve toplu oluşturma

Son tam koşu 372 test, başarılı. Tekli ve toplu native PUT, doğrulanmış
revizyon zinciri, gridde native batch oluşturma, atomik niyet rezervi, kısmi
ret, kayıp yanıt, son yetki/görünüm değişimi, modifyId/geçmiş eşleşmesi,
gerçekleşme yarışı ve restart test edildi. Manuel fiyat değişikliği ve yeniden
kullanılmış istemci kimliği reddedildi. `orders` CLI yardım yolları çalıştı.
Bu geliştirmede gerçek demo emri/ayar değişikliği veya izleyici başlatma yoktur.
Geniş kapsam ve kalan sınırlar 10 numaralı dosyadadır.

## REST geçmiş sayfalaması

Gelir/komisyon/fonlama geçmişi zaman aralıklarıyla, gerçekleşmeler işlem kimliğiyle
sayfalanır. Yoğun geçmişte eksik risk veya sahiplik görünümü kullanılmaz.
386 test geçti; bu çalışmada demo hesabına istek gönderilmedi.
Ayrıntı: [11-GECMIS-SAYFALAMA-VE-UZLASTIRMA.md](11-GECMIS-SAYFALAMA-VE-UZLASTIRMA.md).

## Kullanıcı akışı ve yeniden uzlaştırma — 6 Kasım 2026

Demo kullanıcı WebSocket bağlantısı mevcut SINGLE/grid yönetimine eklendi.
Olay → kalıcı bekleme işareti → REST kimlik/dolum/sahiplik doğrulaması →
işareti kaldırma → mevcut onay/risk kontrolleriyle yönetim sırası uygulanır.
Yeniden bağlantı yeni işlem yetkisi vermez; belirsiz emir tekrar gönderilmez.
430 test geçti. Gerçek demo bağlantısı ve ping/pong doğrulandı; gerçek
fill/iptal/stop olayı ve uzun süreli kesinti kanıtı henüz tamamlanmadı.
Ayrıntı: [12-KULLANICI-WEBSOCKET-VE-YENIDEN-UZLASTIRMA.md](12-KULLANICI-WEBSOCKET-VE-YENIDEN-UZLASTIRMA.md).

## Takip stopu, teminat ve servis — 6 Kasım 2026

SINGLE için plan onayına bağlı, varsayılan kapalı takip stopu eklendi.
Stop yalnız sıkılaşır; yeni koruma doğrulanmadan eskisi kaldırılmaz.
Aktif bot pozisyonunda izole teminat komutları oturum/plan sürümüne bağlandı.
Grid yeniden girişte güncel kaldıraç basamaklarını kontrol eder.
Kalıcı bildirim kuyruğu, Telegram göndericisi, sürekli servis, sağlık ve
kontrollü durdurma komutları eklendi. Gerçek mesaj veya otomatik görev başlatılmadı.
466 test geçti; gerçek demo yazma kanıtı ve kalan ürün kapsamı tamamlanmadı.
[13-TAKIP-STOP-TEMINAT-VE-SERVIS.md](13-TAKIP-STOP-TEMINAT-VE-SERVIS.md).

## Çoklu oturum sahipliği ve ortak risk — 6 Kasım 2026

Aynı USD-M demo hesabında farklı sembollü v2 SINGLE/grid planları birlikte
çalışır. Emirler plan/hesap/niyet ve sembolle birlikte borsa kimliğiyle doğrulanır.
Bekleyen emirler ve refill dahil tam risk rezervleri ortak hesap sınırlarından
geçer. Kapanışta yalnız ilgili oturumun rezervi atomik bırakılır; eş oturumun
emirleri korunur. run-many ortak ön kontrol, manage-all/run-all tek süreçli
yönetim sağlar. 497 test geçti; gerçek demo işlemi veya profil/bütçe değişikliği
yapılmadı. Kalan kapsam ve kullanım:
[14-COKLU-OTURUM-VE-ORTAK-RISK.md](14-COKLU-OTURUM-VE-ORTAK-RISK.md).


## Neutral grid teslimi — 6 Kasım 2026

Tam regresyon 541 test: başarılı. 44 neutral senaryosu dahil; kayıp yanıt, kısmi gerçekleşme, brüt iki taraflı stop, yeniden başlatma ve sahiplik sahte borsada sınandı. Gerçek demo yazma, Telegram gönderimi ve görev kurulumu bu turda yapılmadı.

Ayrıntı: [15-NEUTRAL-GRID-VE-IKI-TARAFLI-YONETIM.md](15-NEUTRAL-GRID-VE-IKI-TARAFLI-YONETIM.md).


## Aktif teminat teslimi — 6 Kasım 2026

560 test geçti; yeni dosyada 19 çoklu oturum/grid/neutral teminat senaryosu bulunuyor. CLI risk profili aktarımı da sınandı. Gerçek demo yazma veya dış mesaj yapılmadı.

Ayrıntı: [16-COKLU-OTURUM-TEMINAT-YONETIMI.md](16-COKLU-OTURUM-TEMINAT-YONETIMI.md).


## Grid takip stopu — 7 Kasım 2026

Yönlü GRID için isteğe bağlı bot takip stopu eklendi. LONG/SHORT watermark ve eşik kalıcıdır; tetikte yeni girişler durur, gerçek kalan miktar kapanış akışına geçer. Native sabit stop korunur; hareketli eşik bot çalışırken izlenir. Neutral/native takip ve diğer politikalar bekliyor. 13 yeni senaryo dahil 573 test geçti; sonuç doğrulama raporuna kaydedildi. Gerçek demo yazma yapılmadı.

Ayrıntı: [17-GRID-TAKIP-STOPU.md](17-GRID-TAKIP-STOPU.md). Kanıt: `reports/development-validation-20261107.json`.


## Grid borsa stopunu yenileme — 7 Kasım 2026

Yönlü GRID için isteğe bağlı `management.trailing.native_stop: true` eklendi. Yeni close-all stop GET ile doğrulanmadan önceki takip stopu kaldırılmaz; başlangıç sabit koruması tutulur. Eski planlar değişmez. 21 yeni senaryo eklendi; tam regresyon sonucu `reports/development-validation-20261107.json` içinde. Gerçek demo yazma kanıtı bekliyor.

Ayrıntı: [18-GRID-BORSA-STOP-YENILEME.md](18-GRID-BORSA-STOP-YENILEME.md).
