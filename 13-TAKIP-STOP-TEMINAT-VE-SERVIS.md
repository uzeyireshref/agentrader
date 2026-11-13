# Takip eden stop, yönetilen teminat ve servis altyapısı

> 9 Kasım 2026 plan notu: Bu belge tarihli işlem alt sistemi teslimini ve kanıtlarını korur. Burada geçen TradingView zinciri yeni geliştirme hedefi değildir; yerine kendi grafik/çizim → strateji → onay → işlem yolu geçmiştir. Güncel ürün sırası [02](02-ASAMALI-GELISTIRME-PLANI.md), geçiş tasarımı [19](19-KENDI-GRAFIK-TERMINALI-VE-GECIS.md) içindedir.

6 Kasım 2026. Bu teslim, onaylanan sekiz aşamanın tamamlandığı anlamına gelmez.
Tam test kümesi **466 test**; kanıt yerel/sahte borsa üzerindedir. Bu çalışmada
gerçek demo emri, hesap ayarı, Telegram mesajı veya otomatik görev başlatılmadı.

## 1. Onaylı plana bağlı takip eden stop

Plan v2 `management.trailing` alanı isteğe bağlıdır; yoksa veya `null` ise
kapalıdır. Eski plan içeriği ve özeti değiştirilmez. Örnek yeni plan alanı:

```json
"trailing": {
  "activation_price": "80800",
  "distance_bps": "100",
  "min_step_bps": "10"
}
```

Bu sayılar örnek şemadır; mevcut bir işlemi değiştirmez. 100 bps %1'dir.
Mesafe 1–5000 bps; minimum güncelleme 1 bps ile mesafe arasındadır. Etkinleşme
referans ile son hedef arasındadır. Politika plan özeti ve sürüm onayına dahildir.

SINGLE LONG/SHORT ve one-way/hedge yönetiminde mark fiyatının en iyi görülen
seviyesi kalıcı tutulur. Stop LONG'da aşağı, SHORT'ta yukarı taşınmaz. Fiyat
adımına yuvarlanır; küçük hareketlerde yeniden emir üretilmez. Yeni miktarlı
STOP_MARKET GET ile etkin doğrulanır, pozisyon tekrar eşleştirilir, sonra eski
stop iptal edilir. Kayıp POST/DELETE cevabında aynı mutasyon tekrar gönderilmez.

Kademeli çıkış kalan miktarı değiştirince stop yeniden boyutlanır. Girişe stop
taşıma daha güçlü takip stopunu gevşetmez. Donmuş bekleyen stop geçişi, yeni
fiyat hareketine göre başka emir üretmeden önce tamamlanır.

Bu **bot tarafından güncellenen, borsada duran STOP_MARKET** yöntemidir;
native TRAILING_STOP_MARKET yürütme kanıtı değildir. Bot kapalıyken son doğrulanmış
stop borsada kalır, takip seviyesi ilerlemez. GRID için bu miktarlı politika
şimdilik açıkça reddedilir; değişen toplam envanter için ayrı politika gereklidir.

## 2. Etkin bot pozisyonunda izole teminat

`settings margin-prepare` artık `--session-id SESSION_ID` kabul eder. Bağımsız
komut etkin bot pozisyonunu değiştiremez. Bağlı komut hesap, yerel sahip, plan
sürümü, sembol, positionSide ve ISOLATED moduyla doğrulanır. Koruma/pozisyon
uzlaştırması salt okunur yapılır. Bekleyen normal emir varsa değişiklik reddedilir.

Hazırlanan miktar, süre ve oturum bağı komut özetine dahildir. Uygulama ayrı
`margin-apply COMMAND_ID --digest DIGEST --execute-demo` komutuyla yapılır.
Bu geliştirmede böyle bir gerçek uygulama yapılmadı. MARGIN bütçesi olan planda
teminat eklemesi planın miktarını aşamaz. NOTIONAL bütçesi kaldıraçla çarpılmaz.
Azaltma etkin stop ve likidasyon tamponu kontrolünü korur. Kayıp artımlı POST
cevabı, geçmişte benzer kayıt bulunsa da UNKNOWN kalır ve tekrar gönderilmez.

SINGLE entegrasyonu uçtan uca sahte borsada sınandı. Grid ancak stabil ve
bekleyen normal emirsiz durumda geçebilir; aktif dolum/refill sırasında teminat
değiştirme kapsamı tamamlanmadı. Genel çoklu ürün/çoklu oturum portföyü de kalan iştir.

Kaldıraç basamakları artık tüm sıra boyunca boşluk, çakışma, sonluluk ve kaldıraç
tutarlılığı bakımından doğrulanır. SINGLE/grid başlangıcında bu ortak seçim
kullanılır. Grid her yeni OPEN/refill öncesinde basamakları yeniden alır; toplam
rezerv nominali güncel kaldıraca ve bakım oranına göre yeniden değerlendirir.
Yeni sınır uygun değilse alış yapılmaz; mevcut durdurma/temizleme yolu çalışır.

## 3. Kalıcı bildirim kuyruğu ve Telegram teslimi

`plans manage SESSION_ID --notify-chat-id CHAT_ID` durum/eylem özetlerini SQLite
kuyruğuna yazar. Bu seçenek kendi başına mesaj göndermez. Rutin aynı durum
mesajları azaltılır. Mesaj kimliği/içerik uyuşmazlığı reddedilir; teslim kirası,
yeniden başlatma, sınırlı tekrar ve kalıcı başarısızlık görünümü bulunur.

```powershell
python -m agentrader notifications status
python -m agentrader notifications deliver --execute-send --limit 10
```

Teslim komutu süreç ortamında `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` ister.
Token komut satırına, günlüğe veya veritabanına yazılmaz. Gönderici yalnız bu
sohbete teslim eder; yanıtın sohbet/message kimliği denetlenir. 429 beklemesi
korunur. En çok sekiz deneme vardır. Telegram belirsiz teslimde idempotency
anahtarı sağlamadığından yeniden deneme aynı bildirimi tekrar gösterebilir;
mesajdaki olay kimliği bunu ilişkilendirir. Bildirim tekrarının işlem yetkisine
etkisi yoktur. Bu aşama Telegram üzerinden uzaktan onay veya TradingView webhook
katmanının tamamlandığı anlamına gelmez.

Kaynak: [Telegram Bot API](https://core.telegram.org/bots/api).

## 4. Sürekli servis ve kontrollü durdurma

```powershell
python -m agentrader service run SESSION_ID --user-stream
python -m agentrader service status SESSION_ID
python -m agentrader service request-stop SESSION_ID
```

`run` mevcut oturumu sürekli izler; varsayılan emir göndermez. `--execute-demo`
mevcut planın yetki/risk sınırlarıyla yönetimi devralır, yeni plan oluşturmaz.
Sağlık kaydı son gözlem zamanını tutar; 90 saniyeden eski kayıt STALE görünür.
Bu, işletim sistemi sürecinin kesin çalıştığına dair kanıt değildir.

`request-stop` yerel plan sahibini doğrular; durdurma isteği ve yeni giriş
iptalini atomik kaydeder. SINGLE bekleyen girişini iptal eder. Grid girişleri
DRAINING yoluyla durdurulur; pozisyon kendiliğinden düzlenmez ve borsa koruması
korunur. Salt okunur izleyici gerçek iptal yapmadıysa durdurma isteğini silmez.

Windows için `scripts/prepare_demo_task.ps1 -SessionId SESSION_ID` yalnız görev
XML'i hazırlar. Varsayılan salt okunurdur; görev kaydetmez/başlatmaz. Oturum
açılışında, sınırlı kullanıcıyla çalışacak tanım üretir; belirsiz borsa hatasında
otomatik mutasyon tekrar döngüsü kurmaz. Betik sözdizimi ve kullanılan cmdlet
parametreleri doğrulandı; gerçek görev kurulum/oturum açılışı testi yapılmadı.
Bilgisayarın açık ve uyanık olması veya ayrı sunucu kurulumu hâlâ gereklidir.

## 5. Doğrulama ve kalan teslimler

`python scripts/validate_development.py` tüm yerel testleri çalıştırıp kanıt
raporunu yeniler. Gerçek demo uçtan uca testine otomatik yeni işlem eklemez.

Kalanlar: grid/native trailing, çoklu oturum ve diğer ürünlerin ortak risk
görünümü, gerçek demo fill/iptal/stop ve uzun süreli kesinti kanıtı, neutral grid
yürütücüsü, uzaktan kullanıcı onayı/rapor erişimi, tamamlayıcı API kapsamı,
Spot/COIN-M adaptörleri ve TradingView → analiz → onay → işlem ürün zinciri.
Bu işler tamamlanmış olarak işaretlenmedi. Gerçek demo yazma kanıtı için geçerli,
somut miktar ve risk sınırları olan yeni işlem yetkisi gereklidir.
