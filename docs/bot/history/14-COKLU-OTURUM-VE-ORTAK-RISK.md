# Çoklu oturum sahipliği ve ortak risk

6 Kasım 2026. Aynı Binance USD-M demo hesabında **farklı sembollerdeki v2 SINGLE
ve grid planları** birlikte çalışabilir. Tam yerel test kümesi: **497 test**.
Bu geliştirmede gerçek demo emri, ayar değişikliği veya dış bildirim gönderilmedi.

## Sahiplik sınırı

Her oturum kendi plan sürümü/özeti, yerel sahibi, API hesap özeti ve kalıcı emir
niyetleriyle doğrulanır. Emir sahipliği yalnız istemci kimliği önekinden çıkarılmaz.
Borsa emir kimliği sembolle birlikte değerlendirilir; BTC ve ETH aynı sayısal
orderId'yi kullansa da birbirinin işlemi kabul edilmez. Tetiklenen stop/TP alt
emirleri bağlı algo kaydı üzerinden tanınır.

Hesaptaki pozisyonlar, gerçekleşmeler ve açık emirler bütün etkin oturumlarla
eşleştirilir. Yabancı/manual emir veya eşleşmeyen miktar varsa bot sahiplenmez;
yürütme inceleme durumuna geçer. Mevcut sahiplik, durum ve miktar kontrolleri
korunur. Veri toplama mevcut tazelik süresini aşarsa görünüm kullanılmaz.

Bu ilk kapsamda aynı sembol iki ayrı plana bölünmez. Hesap pozisyon modu ortak
olmalıdır. One-way ve hedge desteklenir; örneğin BTC LONG ile ETH SHORT ayrı
planlar olabilir. BTC LONG/SHORT'u iki bağımsız oturuma bölmek ve neutral grid
bu teslimin dışında kalır. Manuel pozisyonlarla eşzamanlı, seçici çalışma da
tamamlanmış sayılmaz: bilinmeyen pozisyon mevcut güvenli durdurmayı tetikler.

## Ortak risk rezervi

SINGLE de grid gibi kalıcı `ReservationBook` kullanır. Her planın tam onaylı
maruziyeti ayrılır; bekleyen LIMIT henüz dolmasa bile bütçesi hesaba katılır.
Kısmi çıkış, takip stopu veya bekleyen azaltma rezervi erkenden serbest bırakmaz.
Grid bütün refill kapasitesini ayırmaya devam eder.

Yeni giriş ve grid refill sırasında toplam nominal, pozisyon sayısı, stop/masraf
riski, günlük sonuç ve kullanılabilir teminat denetlenir. Eş oturumların güncel
kaldıraç basamakları da kontrol edilir. Yeni girişte açık eş pozisyonun etkin
stop koruması gerekir. Gerçekleşmemiş USDT zararı günlük görünümde hesaba katılır;
pozitif gerçekleşmemiş sonuçla ek kapasite yaratılmaz. İzole pozisyonun gerçek
cüzdanı en az mevcut miktarın başlangıç teminatını karşılamalıdır.

Hesabın kullanılabilir USDT tutarına kullanılmış teminat otomatik eklenmez; tam
rezervlerle birlikte muhafazakâr hesap yapılır. Bu yöntem bazı geçerli fırsatları
da reddedebilir. Risk sınırları otomatik artırılmaz. `RiskLimits` varsayılan
`max_positions=1` sınırı ikinci oturumu engellemeye devam eder. Kullanıcının
`risk-demo.json` dosyası veya mevcut plan bütçeleri bu çalışmada değiştirilmedi.

Bir plan kapanırken yalnız kendi emirleri temizlenir. Diğer planın pozisyonu,
korumaları ve rezervi korunur. Sıfır miktar/terminal emir kanıtından sonra oturum
kapanışı ile rezervin serbest bırakılması tek SQLite işleminde kaydedilir.

## Kullanım

Her plan önceden kendi sürümüne ait `approve` veya `activate` ile yetkilendirilmiş
olmalıdır. Aşağıdaki kimlikler örnektir; bu komutlar geliştirme sırasında gerçek
hesapta çalıştırılmadı.

```powershell
# Yalnız ortak ön kontrol: emir, claim veya risk rezervi oluşturmaz.
python -m agentrader plans run-many --plan BTC_PLAN:1 --plan ETH_PLAN:1

# Adı açıkça belirtilen yetkili planları başlatıp tek yürütücüde yönetir.
python -m agentrader plans run-many --plan BTC_PLAN:1 --plan ETH_PLAN:1 --execute-demo --iterations 0

# Yeni giriş hakkı oluşturmaz; kayıtlı oturumları devralır.
python -m agentrader plans manage-all --execute-demo --iterations 0
python -m agentrader service run-all --execute-demo

# Yerel risk kayıtları; ağ isteği yapmaz.
python -m agentrader plans reservations
```

`--risk-profile FILE` ile açıkça seçilen profil kullanılır. Çoklu başlatma önce
bütün adayları ve ortak bütçeyi kontrol eder. Sonra her giriş kendi güncel fiyat,
yetki ve risk kontrolünden geçer. Binance çoklu sembol işlemlerini tek atomik
işlem olarak yürütmez: sonraki giriş hata verirse önceki açılışlar kalabilir.
`PARTIAL_START_REVIEW_REQUIRED` açılanları ve başarısız planı gösterir; belirsiz
giriş yeniden POST edilmez. Kaydedilmiş oturumlar ve mevcut borsa korumaları
korunur; inceleme sonrası `manage-all` ile devralınır.

Çoklu izleme tek işlem motoru/süreç kilidi altında sırayla çalışır. Her oturumun
sağlık kaydı ve durdurma isteği ayrıdır. Bir oturum servis tarafından durdurulunca
aynı döngü onu kendiliğinden yeniden başlatmaz; diğer oturumlar izlenebilir.
Sonlu veya Ctrl+C ile biten yürütmede gridler DRAINING yoluna alınır, pozisyon
kendiliğinden düzlenmez. Belirsiz finansal hata otomatik mutasyon tekrarına
çevrilmez. Hesap çapındaki mevcut halt politikası yeni girişleri engellemeye
devam eder; risk azaltma ve koruma onarımı ayrı kurallarla yürür.

`manage-all`/`run-all` bu teslimde REST tabanlıdır. Tek oturumun `--user-stream`
yolu korunur; hesap çapında WebSocket uyandırma bu teslimde eklenmedi.

## Yeniden başlatma ve eski kayıtlar

Kalıcı rezervler yeniden başlatmada korunur. Eski SINGLE oturumunda risk zarfı
yoksa tek oturum yönetimi devam edebilir; başka plan açmak için bu oturuma
kendiliğinden yeni bütçe/sahiplik atanmaz. Önce mevcut oturum kapatılır.

Rezerv ayrıldıktan sonra, plan claim edilmeden süreç kapanırsa rezerv kapasiteyi
korur. `plans reservations` bunu `has_session=false` ile gösterebilir. Yalnız
hesap sahipliği doğrulandıktan ve hiçbir giriş hakkı/oturum oluşmadığı kanıtlandıktan
sonra aşağıdaki komut kullanılabilir:

```powershell
python -m agentrader plans release-unused RESERVATION_ID
```

Bu işlem kullanılmamış plan yetkisini de iptal eder; rezerv ve plan değişimi
atomiktir. UNKNOWN/SUBMITTING veya oturumu/giriş hakkı olan finansal işlemi bu
yolla çözülmüş saymaz ve hiçbir borsa emri göndermez.

## Test kanıtı ve kalan kapsam

Yeni 31 senaryo; iki SINGLE, SINGLE+grid, iki grid, farklı sembollerde hedge
LONG/SHORT, izole cüzdan, bütçe/pozisyon/günlük zarar sınırı, gerçekleşmemiş zarar,
yabancı emir/pozisyon, çakışan sayısal orderId, değiştirilmiş stop/risk kaydı,
yeniden başlatma, tek oturumu kapatma/durdurma, kısmi çoklu başlatma, belirsiz
yanıt ve kullanılmamış rezerv kurtarmasını kapsar. Tüm 497 test geçti.

Gerçek demo üzerinde çoklu açılış/fill/stop/kesinti henüz doğrulanmadı. Genel
çapraz ürün/teminat portföyü, aynı sembolde birden fazla plan, neutral grid,
çoklu oturumda aktif teminat değişimi ve uzaktan plan ekleme/kontrol kuyruğu
kalan iştir. Tek süreç kilidi nedeniyle izleyici çalışırken ayrı bir CLI
yürütücüsüyle yeni plan açılmaz; önceden yetkilendirilmiş planlar `run-many`
ile birlikte başlatılır. Servis durdurma istekleri ayrı kontrol kaydıyla alınır.
