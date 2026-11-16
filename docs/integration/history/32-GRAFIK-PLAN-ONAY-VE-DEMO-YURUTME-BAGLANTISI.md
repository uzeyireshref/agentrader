# Grafik planı → yerel onay → Demo yürütme — 13 Kasım 2026

B3'ün yerel CLI bağlantısı uygulandı. Grafik sinyalinin önizlemesi, mevcut PlanService onayı ve V2Runner yürütmesine kalıcı kaynak bağıyla taşınabiliyor. Web API ve grafik arayüzü finansal komut kabul etmiyor. Bu teslim sırasında kullanıcı hesabında plan oluşturulmadı, onay verilmedi, özel hesap isteği veya emir gönderilmedi; yürütme denemeleri yalıtılmış sahte borsada yapıldı.

## Kullanım sınırı

Yeni ve geçerli bir gölge sinyal için önizleme oluşturulduktan sonra:

```powershell
python -m agentrader web review-preview main EVENT_ID PREVIEW_VERSION
```

Bu komut D3 kabul kaydını ve gözlemlenen yedi kaynak dosyasının özetini kontrol eder. Güncel önizlemeyi ve demo hesabını salt okunur inceler; hesap hazır ve çalışma zamanı boşsa işlem deposunda `PENDING_APPROVAL` planı oluşturur. Tam plan, hesap/risk sonucu ve bir kez gösterilen yerel onay kimliğini terminale döndürür. Komut kendi başına onay veya emir üretmez.

Kullanıcının dönen **tam planı** inceleyip ayrı ayrı vereceği komutlar:

```powershell
python -m agentrader plans approve PLAN_ID 1 --token TOKEN --ttl 120
python -m agentrader plans run PLAN_ID 1 --execute-demo --interval 2
```

Bu komutlar geliştirme sırasında çalıştırılmadı. Grafik planlarında `run` varsayılan olarak sürekli izler; belirli `--iterations` verilirse normal çıkışta kalan giriş durdurulur. Sonradan devralma için mevcut `plans manage SESSION_ID --execute-demo` kullanılır; yeni giriş oluşturmaz. Normal Ctrl+C çıkışı bekleyen girişi iptal edip dolumları kontrol eder. Dolmuş pozisyonu kapatma yetkisi vermez; mevcut stop/hedef korumalarını korur.

`AGENTRADER_EXECUTION_DATABASE` verilmişse hem web önizleme aktarımı hem plans komutları aynı seçili depoyu kullanır. Tüm yerel finansal işlemler mevcut `execution_lock` kilidini kullanır. Varsayılan `data/execution.sqlite3` değişmedi. Web süreci demo hesap anahtarlarını yüklemez.

## Kalıcı kaynak ve onay bağı

Önizleme sürümü, olay kimliği, çalışma alanı, önizleme/plan özeti, hesap anahtarının SHA-256 kimliği, kullanıcı, risk profili, Demo ortamı ve son kullanım zamanı birlikte kaydedilir. Gizli anahtar veya düz onay kimliği bu kaynak kaydına yazılmaz. PlanService kendi mevcut hashli onay kimliği ve kullanıcı/süre/tek giriş kapsamını korur.

Önizleme sürümleri yürütme planı sürümleriyle karıştırılmaz: aynı semantik olay tek bir `chart-…`, sürüm 1 yürütme planına dönüşür. Örneğin olayın önizleme sürümü 2 ilk kez incelenirse, yürütme sürümü 1 olur; kaynak kaydı önizleme sürümü 2'ye bağlı kalır. Plan kimliği ve sürüm dışında işlem alanları değiştirilmez; iki plan özeti ayrı tutulur.

Aynı aktarım tekrar çağrıldığında yeni plan veya yeni onay kimliği üretilmez. Aynı olayın başka önizlemesiyle ikinci yürütme oluşturulmaz. Yanıt/kimlik kaybolursa mevcut plan iptal edilip yeni olay kullanılmalıdır. Kaynak bağı plan kaydından önce kalıcılaştırılır; çökme en fazla yetkisiz artık kayıt bırakır. Otomatik yetkilendirme veya kayıp kimliği yenileme yoktur.

## Gönderim ve yeniden başlama

Mevcut V2Runner, sıradan `plans run`, `manage` ve yeniden başlama yollarında da grafik kaynağını tanır. Onay öncesinde, giriş açılırken ve POST'tan hemen önce güncel önizleme tekrar okunur. Kaynak, revizyon, süre, risk profili veya hesap kimliği değişirse yeni giriş reddedilir. Son kaynak okumasından sonra yetki ve hesap görünümünün tazeliği tekrar kontrol edilir. Bu kontrol ağ ve veritabanı arasında dağıtık atomik işlem değildir; kontrol ile borsa kabulü arasındaki çok kısa değişim yarışı tamamen ortadan kalkmaz.

Kalıcı istemci emir kimliği, risk rezervi, niyet kaydı ve belirsiz yanıtta yalnız sorgulama davranışı mevcut yürütücüden kullanılır. Yeniden başlama yeni giriş göndermez. Kaynak bağı kaybolmuş grafik planları, başka bir komut yolundan içe aktarılmış olsalar da yeni giriş yapamaz.

Bekleyen ve hiç dolmamış LIMIT girişinin kaynağı geçersizleşir veya yerel veri sunucusu kaybolursa giriş iptal edilir. İptal sırasında oluşan dolum yeniden okunur ve korumaya alınır. Dolmuş pozisyonun stop/hedef yönetimi önizleme süresinin dolmasına veya grafik kaynağının erişilememesine bağlı değildir.

## Kabul ve kalan işler

1057 Python testi geçti; 20 yeni grafik yürütme/yerel taşıma/kabul kapısı testi ve seçili işlem deposunun CLI ile ortak kullanımı doğrulandı. `git diff --check` temiz. Frontend değişmedi; bu adımda yeniden frontend derlemesi yapılmadı. Teslim özeti: `reports/chart-execution-delivery-20261113.json`.

Yeni bağlantı testleri; mükerrer aktarım, sürüm eşleştirmesi, hesap/risk/içerik değişimi, kayıp kaynak kaydı, POST öncesi süre sonu, süreç yeniden başlatma, belirsiz emir yanıtı, bekleyen LIMIT iptali, iptal sırasında dolum ve pozisyon korumasını kapsar. Gerçek loopback HTTP denemeleri doğru olay/sürüm istemini, proxy dışlamasını ve yönlendirmelerin izlenmediğini doğrular. Kaynak gözlemi kabul kapısı, bozuk/eksik raporu, kapanış boşluğunu, uzun kesintiyi ve değişmiş kaynak dosyasını reddeder.

Bu teslim otomatik arka plan işlem servisi veya web onay ekranı değildir. Sıradaki parça kimliği doğrulanmış arayüz üzerinden plan inceleme/onay ve durum uzlaştırmasıdır. Ardından kullanıcının belirli plana açık onayıyla kontrollü gerçek Demo uçtan uca kabulü yapılmalıdır. Gerçek Binance bağlantısı kapalı kalır.

Önemli çalışma sınırı: stop/hedef emirleri dolum tespitinden sonra kuruluyor. Sürecin zorla öldürülmesi veya bilgisayarın kapanması, bekleyen LIMIT sonradan dolarsa kesintisiz koruma garantisi sağlamaz; yönetimin yeniden devralınması gerekir. Normal çıkış temizliği bu sert kesintinin yerine geçmez. Gerçek ortama geçişten önce bağımsız izleyici ve bu kesinti senaryosu ayrıca tamamlanmalıdır.
