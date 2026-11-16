# Bağımsız Demo kurtarma izleyicisi — 14 Kasım 2026

Ana işlem süreci zorla sonlandırıldığında, daha önce kaydedilmiş grafik planının bekleyen girişini iptal edip dolumunu uzlaştıracak bağımsız süreç eklendi. Bu teslim geliştirme ve izole kabul kapsamındadır: kullanıcı hesabında izleyici başlatılmadı, özel hesap isteği, emir veya onay oluşturulmadı. Gerçek Binance bağlantısı kapalıdır.

## Değişen davranış

Grafik kaynaklı yeni bir demo giriş, bağımsız ve yürütme yeteneği açık kurtarma izleyicisi olmadan artık gönderilemez. Plan incelemesi ve kullanıcı onayı tek başına bu koşulu sağlamaz. Yürütmeden önce ve ilk POST'un hemen öncesinde izleyici tekrar kontrol edilir. Ana izleme süreci çalışırken kurtarma izleyicisi kaybolursa, henüz dolmamış LIMIT girişi iptal edilir. Dolmuş pozisyonun koruması bu giriş kontrolüne bağlı değildir.

İzleyici kendi süreç kilidini tutar; ana motor ise mevcut `data/runtime.lock` kilidini bütün yürütme boyunca tutmaya devam eder. İzleyici bu kilidi zorla kırmaz. Ana süreç ölünce işletim sistemi kilidi bırakır ve izleyici tek yazıcı olarak devralabilir. Ana süreç çalışırken paralel borsa yazıcısı oluşturulmaz.

## Hazır olma kanıtı

İzleyici başlamadan önce Demo saatini ve imzalı hesap yapılandırmasını salt okunur doğrular. Hazır olma kaydı; işlem deposu, kullanıcı, hesap anahtarı kimliği, risk profili, yürütme kilidi, ayrı PID, süreç oluşturulma kimliği ve beş saniyeden yeni kalp atışına bağlıdır. Windows'ta süreç kimliği gerçek kernel oluşturulma zamanıyla doğrulanır; yeniden kullanılan bir PID yeterli değildir.

Durum kaydı ayrıca alan adı ayrılmış HMAC ile imzalanır. Ana motor aynı Demo kimlik bilgileriyle bu imzayı doğrular; aynı API key yanında farklı/eski secret kullanan izleyici girişe izin vermez. Secret dosyaya veya çıktıya yazılmaz. Kilit tutulmayan eski bir durum dosyası, süreç ölse bile henüz beş saniye dolmadı diye geçerli sayılmaz.

Windows'ta okuyucu açıkken atomik dosya değiştirme kısa süre engellenebildiği için, durum dosyası kesilmeden atomik yeniden adlandırma sınırlı süreyle yeniden denenir. Kalıcı hata izleyiciyi hazır göstermeyi durdurur.

## Kurtarma kapsamı

Devralmada önce kalıcı olarak yeni giriş yetkisi iptal edilir ve genel giriş durdurması korunur. Her borsa değişikliğinden önce salt okunur sahiplik/dolum uzlaştırması yapılır.

- Hiç dolmamış kayıtlı LIMIT girişinin kalanı iptal edilir.
- İptal sırasında dolum olmuşsa tekrar okunur, sahipliği doğrulanır ve kayıtlı stop/hedef koruması kurulur.
- Giriş kabul edilmiş fakat ana süreç yanıtı kaydetmeden ölmüşse aynı istemci kimliği borsadan sorgulanır; yeni giriş gönderilmez.
- İlk korumanın yanıtı kaybolmuşsa aynı koruma sorgulanır. Yalnız eksik olan diğer koruma, kendi kalıcı kimliğiyle kurulabilir.
- Stop/hedef aşılmışsa mevcut planın izin verdiği sahipli pozisyon azaltımı yapılabilir; yeni pozisyon açılması engellenir.
- Oturum kaydı oluşmadan ayrılmış rezerv veya kullanılmış giriş hakkı otomatik serbest bırakılmaz. `ORPHAN_*_REVIEW_REQUIRED` durumuyla yeni girişler kapalı tutulur.
- Gönderilip gönderilmediği belirsiz giriş, borsada bulunamadı diye tekrar POST edilmez; rezerv ve durdurma korunur, inceleme gerekir.

Ek borsa adaptörü yalnız kayıtlı oturuma ve kalıcı niyete birebir uyan koruma, azaltma ve iptallere izin verir. Yeni giriş, kaldıraç/teminat değişikliği ve yabancı emir iptali engellenir. Diğer motorların aktif oturumları bu ilk kapsamda otomatik yönetilmez. Kalıcı genel durdurma, izleyici hesabı kapattı diye otomatik kaldırılmaz.

## Yerel komutlar

Salt okunur durum, kimlik bilgisi yüklemeden ve ağ isteği yapmadan okunabilir:

```powershell
python -m agentrader service guardian-status
```

Gözlem modu ve açıkça yetki verilen kurtarma modu ayrı seçeneklerdir:

```powershell
# Demo hesabını okuyabilir; borsaya değişiklik göndermez.
python -m agentrader service guardian

# Yalnız önceden kayıtlı grafik planının kurtarmasını yürütme yeteneğiyle açar.
# Ayrı terminalde, plan yürütülmeden önce başlatılır.
python -m agentrader service guardian --execute-demo
```

Bu teslimde yukarıdaki uzun çalışan komutlar kullanıcı hesabında başlatılmadı. Yalnız `--help` ve `guardian-status` kontrol edildi; gerçek durum `NOT_RUNNING`, giriş hazırlığı `false`. `--database` veya `AGENTRADER_EXECUTION_DATABASE` seçimi işlem motoruyla aynı olmalıdır. Kontrol aralığı 1–2 saniyedir; borsa ve ağ yanıt süresi kurtarma süresine eklenir. Süreç kendi başına plan oluşturmaz, onay vermez veya giriş açmaz.

## Doğrulama

1099 Python testi ve 36 replay senaryosu geçti. Yeni kapsam 18 izleyici/kapsam testi ve 9 gerçek süreç kesintisi testidir. Kesinti testleri iki ayrı Python süreci, gerçek işletim sistemi kilitleri ve yalnız loopback üzerinde paylaşılan sahte borsayla çalışır. Ana süreç rezervden sonra, claim'den sonra, oturum kaydından sonra, gönderimden önce, giriş kabulünden sonra, kısmi dolumda, ilk koruma kabulünde ve korumalar tamamlandıktan sonra zorla öldürülür. Bekleyen ve dolmuş giriş kabulü ayrı senaryolardır.

Testler; ikinci giriş oluşmadığını, koruma kimliklerinin tekrarlanmadığını, kayıtlı riskin belirsizlikte bırakılmadığını, ana süreç kilidi tutarken devralma yapılmadığını ve bilinen dolumların korunduğunu doğruladı. Gerçek Demo özel API veya emir isteği yapılmadı. Arayüz bu adımda değişmedi; önceki 343 arayüz testi kabulü geçerlidir.

Kaynaklar: `agentrader/bot/recovery_guardian.py`, V2 giriş kapıları, `service guardian` komutları ve `tests/test_recovery_process.py`. Rapor: `reports/guardian-python-tests-20261114.log`; ayrı süreç koşusu: `reports/recovery-process-tests-20261114.log`.

## Kalan sınır

Bu koruma, ana süreç kapanırken bağımsız izleyicinin aynı bilgisayarda çalışmaya devam ettiği durumu kapsar. Bilgisayarın tamamen kapanması, bütün süreçlerin öldürülmesi veya ağın/borsanın erişilememesi kesintisiz koruma garantisi sağlamaz. Kilidi tutan ana süreç donarsa ikinci yazıcı oluşturmak için kilit zorla kırılmaz. Kontrol ile POST arasındaki çok kısa süreç kapanma yarışı da dağıtık atomik işlemle ortadan kaldırılmış değildir.

Sıradaki kabul, belirli plana açık kullanıcı onayıyla kontrollü gerçek Demo yürütmesi ve borsa tarafındaki gerçekleşmelerin doğrulanmasıdır. Bu kabul henüz yapılmadı; gerçek ortama geçiş hazır olarak işaretlenmedi.
