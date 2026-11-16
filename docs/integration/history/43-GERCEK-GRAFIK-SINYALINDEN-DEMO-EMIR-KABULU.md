# Gerçek grafik sinyalinden Demo emir kabulü — 14 Kasım 2026

## Gerçekleşen zincir

Grafik deposundaki yatay çizgi → gerçek kapanmış Demo mumu TOUCH olayı → kalıcı sinyal önizlemesi → gerçek hesap/risk incelemesi → kaynak bağıyla yerel plan yetkilendirmesi → bağımsız kurtarma izleyicisi doğrulaması → Binance Demo LIMIT emri → kontrollü iptal zinciri ilk kez gerçek veriler ve gerçek borsa emriyle doğrulandı.

Kullanıcının mevcut çizimlerine dokunulmadı. Ayrı etiketli bir kalibrasyon çizgisi oluşturuldu: Demo bot bağ testi 5d3d84559d6a. Seviye, çizim anındaki son kapanmış 1 dakikalık Demo mumunun kapanışı + bir native tick: 65290,10 USDT. Bu, kabul testine ait açık bir teknik kuraldır; bağımsız trend/swing/Fibonacci stratejisi değildir.

Mevcut terminalin gerçek ShadowWorker süreci, geçmiş mumu seed edip sinyal üretmeden WATCHING durumuna geçti. Sonraki kapanmış 1 dakikalık mumda gerçek TOUCH kaydedildi. Olayın kapanışı 65297, candle_time 1794670680 ve olay kimliği ccbe0fe61ebf8352a3b2e86a4c4dbb4fa41081e465050b4086fffb8bb2334598. Takip tek olaydan sonra LATCHED / EXPLICIT_REBIND_REQUIRED durumuna geçti; aynı temastan tekrarlı işlem üretilmedi.

Plan kimliği: chart-fd83b72b0485ee2f5b1df95b1dcc06a3. Kaynak analysis_ref shadow-event: ile gerçek olay kimliğine bağlıdır. Çizim revizyonu, tanım hash'i, olay kanıtı, önizleme hash'i, hesap kimliği, risk profili ve yürütme plan digest bağı doğrulandı.

Binance Demo emri 28679896648: BUY LIMIT, 0,0008 BTC, fiyat 65053,20 USDT. Borsa önce ENTRY_PENDING akışında kabul etti; son bağımsız GET CANCELED ve executedQty=0 doğruladı. Bu aşama emir gönderimi/iptali kabulüdür; yeni pozisyon dolumu veya stop/hedef tetiklenmesi olarak değerlendirilmez. Giriş/stop/hedef parametreleri açık teknik test girdileridir.

## Korunan sınırlar

Önceki küçük Demo turlarının aynı sabit 532,69467203 USDT günlük tavanı devralındı; yeni zarar alanı eklenmedi. İşlem başına/toplam açık risk 1 USDT, nominal tavan 60 USDT, tek pozisyon ve 15 saniye hesap tazeliği korundu. Bu önizlemenin nominal bütçesi 52,73 USDT idi. Son günlük zarar 529,95960838 USDT olarak kaldı: bu adımda ek gerçekleşmiş zarar/masraf sıfır.

Ayrı işletim sistemi sürecindeki gerçek guardian (bu koşuda PID 14940) aynı hesap, kullanıcı, DB, runtime kilidi ve risk profiliyle ARMED oldu. Üretim require_guardian kontrolü ve imzalı süreç/kalp atışı kanıtı bypass edilmedi. Yalnız bu operatör testi için başlatıldı; boş hesap ve kapanmış oturum kanıtından sonra durduruldu.

Varsayılan risk-demo.json ve ana terminalin özel hesap/emir API ayarları değiştirilmedi. Ana API 127.0.0.1:8765 ve orijinal ShadowWorker çalışmaya devam etti. Sınırlı risk profilli önizlemeyi üretim local_preview_provider üzerinden sunmak için yalnız GET kabul eden geçici loopback uç noktası kullanıldı. Bu uç noktanın ayrı MarketFeedHub kaynağı da gerçek Demo verisini kullandı. Test bitince uç nokta ve bu ek abonelik kapatıldı; kapsamlı risk profili dosyası silindi. Profil değerleri ve silinen dosyanın hash'i raporda korunur. Ana UI için sürekli alternatif risk politikası veya yeni web işlem yetkisi açılmadı.

## Bulunan ve düzeltilen uyumsuzluklar

Salt okunur hesap adaptörü üzerinden hesap incelemesi, daha önce eklenen paralel sembol metadata okumalarını korumuyordu. Üç sabit GET için paylaşılan symbol_metadata yardımcı işlevi ve ReadOnlyDemoAccount.read_symbol_metadata eklendi. Ayrı HTTP taşıyıcıları, aynı senkronize saat ve ortak host hız sınırlayıcısı korunur. Genel yazma yetkisi eklenmedi ve tazelik sınırı artırılmadı.

İlk gerçek emirden sonraki test raporlaması, eski kapalı v1 oturumlarında plan_id bulunmadığı için KeyError verdi. Üretim emir akışı ENTRY_PENDING aşamasına ulaşmıştı; finally temizliği emri iptal edip hesabı boş bıraktı. Eski oturumları güvenle atlayıp tam bir v2 plan eşleşmesi arayan chart_session seçimi ve regresyon testi eklendi. Orijinal koşu raporunun STOPPED / KeyError sonucu korundu; başarılıymış gibi yeniden yazılmadı. Yeni emir açılmadı.

Ayrı salt okunur denetim, kalıcı çizim/olay/önizleme/plan/kaynak bağı/niyet zincirinin hash'lerini yeniden hesapladı ve aynı emir kimliğini borsadan tekrar sorguladı. Sonuç VERIFIED, borsa terminal sonucu CANCELED. Böylece test raporlama hatası ile gerçek finansal zincirin doğrulaması ayrı kaydedildi.

## Son durum ve kalan kapsam

Bağımsız son hesap kontrolü: 0 pozisyon, 0 normal emir, 0 koşullu emir; etkin oturum sıfır; 38 niyetin tamamı terminal. Geçmiş uzlaştırması NO_CHANGES verdi. Giriş durdurması yeniden korunuyor. Chart plan CLOSED, gölge koşu LATCHED; sürekli yeni giriş işi bırakılmadı. acceptance-check BLOCKED sonucu bu korunmuş giriş kapısından kaynaklanır.

Bu teslim bir yatay çizginin gerçek kullanımını kanıtlar. Fibonacci/kanal canlı sinyal profili, otomatik swing/trend çizimi, otomatik giriş/stop/hedef stratejisi, grafik arayüzünden finansal onay ve native stop/hedef tetiklenme kabulü bu aşamayla tamamlanmış sayılmaz. Sonraki kapsam canlı kural profilini trend/ışın ve Fibonacci gibi hesaplanabilir hedeflere genişletmektir; yeni görsel kanal ailesi ayrı matematik/doğrulama gerektirir.

## Kanıt dosyaları

- reports/live-chart-entry-5d3d84559d6a.json: değiştirilmeden korunan gerçek koşu ve raporlama hatası.
- reports/live-chart-entry-5d3d84559d6a-evidence.json: bağımsız salt okunur VERIFIED zinciri ve gerçek borsa emri.
- reports/live-chart-entry-final-account-20261114.json: ayrı gerçek hesap GET kontrolü.
- reports/live-chart-entry-final-history-20261114.json: terminal geçmiş kontrolü.
- reports/live-chart-profile-cleanup-20261114.json: geçici risk dosyası temizliği.
- reports/live-chart-entry-replay-20261114.log: 36/36 replay sonucu.
- reports/live-chart-entry-python-tests-20261114.log: tam Python regresyonu.

Son doğrulama: 1158 Python testi ve 36/36 grafik replay senaryosu geçti. Teslim özeti ve kaynak hashleri reports/live-chart-entry-delivery-20261114.json içinde. Ana API sağlık kontrolü OK; özel API ve web işlem komutları kapalı, gerçek gölge işçisi çalışıyor. Guardian süreç/kilit kanıtı test bitiminde geçersizdir; eski lease dosyası STALE / entry_ready=false olarak görünür.
