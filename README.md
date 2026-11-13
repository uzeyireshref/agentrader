> Güncel grafik planı (10 Kasım 2026): [Çekirdek plan v2](docs/chart/PLAN.md). 21 paket, 5 tamamlandı. T03 kalıcı fiyat-zaman cetveli geçti: 735 Python / 161 frontend testi, derleme ve 11 gerçek App/SQLite kontrolü. Sıradaki T04 long/short planlama. [Cetvel kullanımı](docs/chart/RULER.md). B5 ertelenmiş/açık; bot ve emir bağlantısı sonraki kapsamdır.

> Önceki A–E planı: 24/25 tamamlandı; CL01–CL03 kapandı. B5 tamamlanmadı; kullanıcı isteğiyle ertelendi. Güncel sıra için [v2 planını](docs/chart/PLAN.md) izleyin.

> Başvuru: [Aktif plan](docs/chart/PLAN.md), [kabul kapsamı](docs/chart/ACCEPTANCE.md), [sabit aday ve geri dönüş](docs/chart/RELEASE.md). B5 ve genel sürüm kabulü açıktır.

### Önceki geliştirme notları

Aşağıdaki tarihsel test notları güncel tamamlanma sayısı veya kabul kararı değildir.

> Mum/hacim çizimi başarısızken yanlış Canlı etiketi düzeltildi; 109 frontend testi ve derleme geçti. [Kapsam](docs/chart/validation/36-GRAFIK-DURUMU-VE-CIZIM-TOPARLANMASI.md).

> Fiyat hassasiyeti ve eski OHLC gösterimi düzeltildi;102 frontend testi/derleme geçti. [Doğrulama](docs/chart/validation/35-FIYAT-HASSASIYETI-VE-OHLC-DOGRULUGU.md).

> Canlı veri tazeliğinde iki açık düzeltildi; 671 Python testi, izole HTTP/restart ve public canlı veri probe geçti. [Kapsam](docs/chart/validation/34-CANLI-VERI-TAZELIGI-VE-ESITLEME.md).

> Gecikmeli kayıt/coin geçişinde iki yarış hatası yeniden üretilip düzeltildi; 96 frontend testi ve derleme geçti. [Kapsam](docs/chart/validation/33-GECIKMELI-KAYIT-VE-COIN-GECISI-DOGRULUGU.md).

> Kontrollü boşluk ve native seri/imleç referans ekranı eklendi; 86 frontend testi/derleme geçti. Gerçek tarayıcı kontrolü bekliyor. [Kapsam ve görev](docs/chart/validation/31-KONTROLLU-BOSLUK-VE-EKRAN-GOSTERGE-DOGRULUGU.md).

> Masaüstü hizalama testinde ara mum zamanı hatası bulundu; kesirli indeks dönüşümü düzeltildi. 80 frontend testi/derleme geçti; kısa masaüstü tekrar testi bekliyor. [Bulgu ve görev](docs/chart/validation/30-ARA-MUM-HIZALAMA-DUZELTMESI.md).

> Doğruluk turu: isteğe bağlı native motor/SVG hizalama ölçümü eklendi; 75 frontend testi ve derleme geçti. Gerçek masaüstü ölçümü bekliyor. [Kapsam ve görev](docs/chart/validation/29-CIZIM-HIZALAMA-DOGRULAMASI.md).

> Güncel: yerel çizim anahtarı kaldırıldı. 667 Python / 67 frontend testi ve 4.908 bağımsız EMA/RSI değeri geçti. Veri/çizim doğruluğu önceliği sürüyor; Canvas hizalama kabulü açık. [Ayrıntılar](docs/chart/validation/28-ANAHTARSIZ-CIZIM-VE-GOSTERGE-DOGRULUGU.md).

> Kısa performans ölçümü p95 48,70 ms ile hedefi geçmedi. SVG/gösterge yazma optimizasyonu yapıldı; 60 frontend testi/derleme geçti, karşılaştırma bekliyor. [Bulgular ve kısa tekrar testi](docs/chart/validation/27-KARE-GECIKMESI-VE-PERFORMANS-OPTIMIZASYONU.md).

> Güncel kalite turu: 54 frontend testi ve derleme geçti. React iptal senaryoları ile isteğe bağlı 10/60 saniye ölçüm paneli eklendi. [Kapsam ve masaüstü kısa ölçüm görevi](docs/chart/validation/26-KISA-PERFORMANS-VE-ETKILESIM-TESTLERI.md).

> Masaüstü testi kısmen geçti; uzun oturumda hata bulundu. Yeni mum güncellemesi ve 4.000 mum penceresi düzeltildi; 37 frontend testi/derleme geçti. [Bulgular ve tekrar testi](docs/chart/validation/25-MASAUSTU-BULGULARI-VE-YENI-MUM-DUZELTMESI.md).

> Güncel grafik kalite denetimi: 666 Python / 26 frontend testi geçti. Bot bağlantısından önce görsel, yarış ve uzun oturum kabulü bekleniyor. [Denetim ve kabul matrisi](23-GRAFIK-KALITE-DENETIMI-VE-KABUL.md).

> 9 Kasım grafik kalite güncellemesi: 666 Python ve 16 frontend testi geçti. Trend/Fibonacci, EMA/RSI ve mıknatıs eklendi; görsel kabul bekliyor. Güncel ayrıntılar: [kaynak araştırması ve kalite](22-GRAFIK-KAYNAK-ARASTIRMASI-VE-KALITE.md).

# Agentrader

Kendi grafik ve çizim ortamına sahip, Binance USD-M public verilerini kullanan kişisel trading terminali. **Önce web; kendi çizimlerimiz, takip kuralları ve mevcut Python işlem çekirdeği.** TradingView hesabı/Pine/alarm zinciri ana bağımlılık değildir.

9 Kasım 2026: W2 canlı grafik ve W3 kalıcı yatay çizgi/bölge kodlandı. Coin ve zaman dilimi seçimi, mum/hacim, geçmiş yükleme, sürümlü sunucu kaydı, düzenleme, silme ve oturum içi undo/redo mevcut. Bot takibi ve işlem yürütme bu çizimlere henüz bağlı değildir. Görsel masaüstü/mobil ve gerçek sürükleme QA'sı bekliyor; tam kullanıcı kabulü tamamlandı sayılmaz.

| Başvuru | İçerik |
|---|---|
| [21 — Grafik ve kalıcı çizimler](21-GRAFIK-VE-KALICI-CIZIMLER.md) | Güncel kurulum, çizim erişimi ve kanıtlar |
| [02 — Ana plan](02-ASAMALI-GELISTIRME-PLANI.md) | W0–W9 ve kabul ölçütleri |
| [03 — Mimari sözleşme](03-MIMARI-VE-ISLEM-SOZLESMESI.md) | Çizim → strateji → fırsat → yetki/risk → emir |
| [19 — Geçiş tasarımı](19-KENDI-GRAFIK-TERMINALI-VE-GECIS.md) | Kaynak sınırları ve hedef mimari |
| [20 — Yerel API temeli](20-W1-YEREL-UYGULAMA-API.md) | W1 sorgu/komut kuyruğu |
| [07 — Geliştirme durumu](07-GELISTIRME-DURUMU.md) | Mevcut ve bekleyen doğrulamalar |

## Grafik uygulamasını çalıştır

~~~powershell
python -m pip install -e ".[web-test]"
Set-Location frontend
npm ci
npm run build
Set-Location ..
python -m agentrader web serve
~~~

Grafik http://127.0.0.1:8765/ adresindedir. Public fiyat için Binance anahtarı gerekmez. Yerel kalıcı çizimler anahtarsızdır; token oluşturma/eşleştirme gerekmez. Korunan özel komutlar ayrıdır. Sabit adayın kurulumu ve geri dönüşü [güncel yönergede](docs/chart/RELEASE.md). Mevcut demo emir araçları aşağıda korunmuştur; finansal HTTP komutu yoktur.

Güncel aday doğrulaması: 675 Python ve 123 frontend testi, üretim derlemesi, arşiv bütünlüğü ve ayrı klasörden izole localhost HTTP/çizim/restart kontrolü geçti. [Aday raporu](reports/chart-candidate-validation-20261110.json). Genel/cihaz kabulü [E1 raporunda](docs/chart/ACCEPTANCE.md) açık; sırada E5 kullanıcı incelemesi vardır. Önceki public canlı veri denemesi tarihsel kanıttır ve bu aday turunda yeniden yapılmadı.

Public canlı piyasa okuması ile Binance USD-M **demo hesap yürütmesi** ayrıdır. Mevcut risk profili ve eski plan yetkileri korunur. Aşağıdaki tarihli CLI bölümleri teknik referanstır; güncel kapsam 07 ve 21'de açıklanır.

## Çalıştırma (PowerShell)

Ek çalışma zamanı bağımlılığı yoktur. Proje klasöründe:

```powershell
python -m agentrader diagnose
```

Sunucu bağlantısı, saat farkı ve BTCUSDT sembol kuralları JSON olarak gösterilir.
Başka sembol için `--symbol ETHUSDT` ekleyin. Başarı çıkış kodu 0, hata 1'dir.
Loglar stderr'e, başarılı rapor stdout'a yazılır. Emir POST çağrıları otomatik tekrar edilmez.

İsteğe bağlı izole ortam ve komut kurulumu:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\agentrader.exe diagnose
```

## Demo hesap kontrolü

1. Binance Futures Demo Trading üzerinden demo API anahtarı oluşturun.
2. `.env.example` dosyasını `.env` adıyla kopyalayın.
3. Demo API key ve secret değerlerini yalnızca bilgisayarınızdaki `.env` içine yazın.
4. Aşağıdaki komutu çalıştırın:

```powershell
python -m agentrader diagnose --account
```

Anahtarları sohbete, kaynak koda veya ekran görüntülerine koymayın. `.env` Git dışında
tutulur. Ortam değişkenleri `.env` değerlerinden önceliklidir. Bu basit `.env`
okuyucusu ANAHTAR=DEĞER satırlarını destekler; değişken genişletmesi yapmaz.
Rapor hesap bakiyesi ve açık pozisyon bilgileri içerdiğinden paylaşmadan önce inceleyin.

Hesap kontrolü bakiye, pozisyon, açık emir sayısı ve hedge/one-way modunu okur.
`can_trade` alanı borsanın bildirdiği hesap alanıdır; emir gönderme yeteneğinin
veya gerçek hesap uygunluğunun kanıtı değildir. Anahtarsız kontrol hesap yetkisini doğrulamaz.
Demo başarısı gerçek Futures erişimi veya hukuki uygunluk anlamına gelmez.

## Test

```powershell
python -m unittest discover -s tests -v
```

Testler ağ kullanmadan ortam kilidini, eksik anahtarları, imzalamayı, endpoint
izin listesini, hata mesajlarında sırların gösterilmemesini ve anahtarsız akışı doğrular.

## Teknik seçim ve kaynaklar

3 Kasım 2026 tarihinde resmî belgelerden demo adresi
`https://demo-fapi.binance.com` olarak doğrulandı. Bu küçük teşhis adaptörü
Python standart kütüphanesiyle REST GET çağrıları yapar; üçüncü taraf SDK kullanmaz.
Binance'ın güncel modüler Python SDK ailesi incelendi; emir araç kutusuna geçerken
SDK seçimi ayrıca değerlendirilecek. Sabit bir endpoint izin listesi ve yönlendirme
engeli kullanılır. HMAC-SHA256 anahtarları desteklenir; RSA/Ed25519 desteklenmez.

- [Resmî genel API ve demo bilgisi](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info)
- [Hesap REST API: V3 hesap ve pozisyon modu](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account)
- [Binance Python connector deposu](https://github.com/binance/binance-connector-python)

## Demo limit emir döngüsü

Önce yalnızca emir önizlemesi:

```powershell
python -m agentrader order-cycle
```

Demo borsasına emir gönderme, sorgulama ve hemen iptal etme:

```powershell
python -m agentrader order-cycle --execute-demo --test-only
```

Bu araç one-way modunda, açık emir/pozisyon bulunmayan hesapta çalışır. BUY LIMIT
fiyatını alış kotasyonunun %2 altında, GTX (post-only) olarak oluşturur. Fiyat ve
miktarı Decimal ile sembol adımlarına uyarlar. Test başına nominal üst sınır
100 USDT'dir; bu yalnızca demo deneyi sınırıdır, canlı risk tercihi değildir.
Kaldıraç ve hesap ayarları değiştirilmez. Kullanılabilir bakiyenin nominal tutarı
karşılaması istenir. GTX daha sonra gerçekleşmeyi önlemez; hızlı fiyat hareketinde
demo pozisyon oluşabilir ve araç bunu başarılı iptal saymaz.

Gönderimden önce kimlik `logs/demo-orders.jsonl` içine kaydedilir. Zaman aşımında
POST tekrarlanmaz; kimlikle sorgulama yapılır. İptal yalnızca oluşturulan emre
uygulanır ve son durum tekrar okunur. Durum belirsizse yeni test başlatmadan
günlükteki kimlikle demo hesabını kontrol edin. Bu komut yalnızca limit deneyi
içindir. Kalıcı CLI kayıtları `recover` ile uzlaştırılır.

Emir sözleşmesi: [Binance Futures Trade API](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade).

## Demo pozisyon yaşam döngüsü

```powershell
python -m agentrader position-cycle
python -m agentrader position-cycle --execute-demo --test-only
```

İlk komut önizleme, ikincisi sanal işlem yapar. Test akışı: küçük MARKET LONG →
STOP_MARKET ve TAKE_PROFIT_MARKET doğrulaması → yarım reduce-only çıkış → tam
reduce-only çıkış → koruyucu emir iptalleri → boş hesap doğrulaması.
Koruyucu emirlerde güncel `/fapi/v1/algoOrder`, MARK_PRICE ve closePosition
kullanılır. Stop/TP kabulü tetiklenerek gerçekleşme testi anlamına gelmez.

One-way mod ve başlangıçta boş hesap gerektirir; kaldıraç değiştirilmez. Tahmini
nominal sınır 100 USDT; market kayması nedeniyle gerçekleşen tutar farklı olabilir.
%2 stop/TP uzaklığı yalnızca kısa demo senaryosunun parametresidir. Canlı risk
tercihi veya strateji değildir. Giriş ile stop kurulması arasında kısa bir
korumasız süre vardır. Koruma doğrulanamazsa finally temizliği reduce-only
kapatma dener; ağ kesintisinde kapanış garanti edilmez.

Gönderim öncesi kimlikler `logs/demo-positions.jsonl` içine yazılıp diske aktarılır.
Belirsiz POST yeniden gönderilmez, emir kimliğiyle sorgulanır. Pozisyon sıfır
olmadan koruma kaldırılmaz. Temizlik başarısızsa `.lock` dosyası bırakılır;
hesabı ve günlüğü inceleyip uzlaştırmadan kilidi silmeyin. İşlem sırasında manuel
işlem veya ikinci bot kullanmayın. Bu kısa deneyin JSONL kilidi otomatik
devralınmaz; çökme/devralma için aşağıdaki yönetilen oturum komutları kullanılır.
SHORT ve hedge senaryoları bu sürümün kapsamı dışındadır.

## Kalıcı kayıt, kurtarma ve demo risk sınırları

CLI üzerinden `--execute-demo` kullanan deneyler artık gönderimden önce
`data/execution.sqlite3` veritabanına benzersiz emir niyeti kaydeder. Aynı
kimlikle yeniden çağrı yeni POST göndermez; borsayı sorgular. Farklı parametreyle
aynı kimliğin kullanımı reddedilir. SQLite FULL senkronizasyon ve tek yürütücü
işletim sistemi kilidi kullanılır. Anahtarlar veritabanına yazılmaz.

```powershell
python -m agentrader recover
python -m agentrader recover --clear-halt
```

`recover` emir göndermeden kayıtları borsayla karşılaştırır. Kısmi gerçekleşme,
belirsiz emir, manuel pozisyon veya açık normal/algo emir varsa girişleri kalıcı
olarak durdurur. Koruyucu emirleri kaldırmaz. `--clear-halt` ancak hiçbir
belirsizlik, açık emir veya pozisyon kalmamışsa durdurmayı kaldırabilir.
Gönderim öncesi süreç çöker ve emir sorgulanamazsa yeniden gönderilmez; manuel
inceleme gerektiren belirsiz durumda kalır. Kurtarma otomatik strateji devamı
veya bilinmeyen pozisyonu otomatik kapatma değildir.

`risk-demo.json` yalnızca demo deneyleri içindir: işlem başına tahmini stop
kaybı 5 USDT, toplam açık risk 10 USDT, günlük kayıp bütçesi 25 USDT, nominal
100 USDT, en fazla 1 pozisyon ve 15 saniye veri yaşı. Bunlar canlı tercih
değildir. Başka demo profil için `--risk-profile DOSYA.json` kullanılabilir.
Bu aşamada mevcut açık risk kesin bilinmiyorsa yeni giriş reddedilir; aynı
anda birden fazla pozisyon yönetilmez. Çıkışlar ve koruma, giriş durdurması
aktifken de gönderilebilir.

Günlük sonuç UTC gün başlangıcından itibaren USDT realized PnL, komisyon ve
funding toplamıyla hesaplanır; negatif gerçekleşmemiş sonuç eklenir. Mevcut
kayıp + yeni stop riski günlük bütçeye sığmalıdır. USDT dışı gelirler veya
1000 kayda ulaşan eksik sayfa durumunda giriş reddedilir. Stop hesabı fiyat
farkı × miktardır; gap/kayma/komisyon nedeniyle gerçek kayıp daha büyük olabilir.
Limit iptal deneyi için kullanılan %2 risk referansı gerçek bir stop emri değildir.

Her yeni deney öncesinde otomatik uzlaştırma yapılır. Eski JSONL günlükleri
SQLite'a aktarılmaz; borsada eski/manuel açık pozisyon yine saptanır ve giriş
engellenir. Kütüphane düzeyindeki ham `DemoExchange` bir adaptördür; güvenlik
akışı için CLI ve `DurableExchange` kullanılmalıdır. Yönetilen oturumlar için
sürekli kontrol ve koruma onarımı aşağıdaki komutlarla çalışır. Otomatik strateji
üretimi veya sunucu servisi kurulumu bu sürümde açılmaz.

[Günlük gelir API sözleşmesi](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account).

## Yönetilen demo pozisyon ve watchdog

```powershell
# Küçük sanal LONG açar, stop/TP kurar ve kalıcı oturum bırakır:
python -m agentrader managed-open --execute-demo --test-only
# Yalnızca gözlem; emir göndermez:
python -m agentrader watchdog
# Tek tur devralma ve gerekiyorsa koruma onarımı:
python -m agentrader watchdog --execute-demo
# Terminalde çalıştığı sürece izler; turlar arasında 5 saniye bekler:
python -m agentrader watchdog --execute-demo --iterations 0 --interval 5
# Sahipliği tekrar doğrulanan pozisyonu kapatır, ardından korumayı temizler:
python -m agentrader managed-close --execute-demo
```

`managed-open` kapandıktan sonra borsadaki stop/TP kalır. Sürekli izleme için
watchdog komutunu çalışır tutun. Ctrl+C izleyiciyi durdurur; pozisyonu kapatmaz.
Uygulama veya bilgisayar kapalıyken kod onarım yapamaz; kabul edilmiş borsa
koruyucu emirleri borsada kalır. Servis/otomatik işletim sistemi başlangıcı kurulmadı.
Bir turun süresi API gecikmesine bağlıdır; interval turlar arasındaki beklemedir.

Her tur pozisyonu, giriş/çıkış emirlerini, stop/TP'yi ve oturum başlangıcından
sonraki işlem geçmişini karşılaştırır. Salt miktar eşleşmesi sahiplik sayılmaz:
bütün fill emir kimlikleri botun giriş/çıkış veya tetiklenmiş algo emrine ait
olmalıdır. Manuel işlem (aynı net miktara dönülse bile), başka pozisyon, bilinmeyen
emir, hedge modu veya eksik geçmişte müdahale yapılmaz; kalıcı giriş durdurması
ve alarm olayı kaydedilir. Açık oturum varken yeni giriş engellenir.

İptal/sona ermesi kesinleşen stop tek bir yeni kimlikle onarılır. Kalıcı onarım
niyeti gönderimden önce yazılır. Yanıt belirsizse aynı kimlikle sorgulanır;
körlemesine yeni POST yapılmaz. Stop/TP `closePosition=true` olduğu için kısmi
pozisyonun kalanını da kapsar. Bekleyen kısmi girişin kalanı önce iptal edilir.
Stop seviyesi aşılmışsa veya koruma doğrulanamıyorsa, sahiplik tekrar doğrulanıp
reduce-only kapatma denenir. Pozisyon sıfır olmadan koruma kaldırılmaz. Ağ veya
sahiplik belirsizliğinde kapanış garanti edilmez; mevcut koruma korunur, girişler
durur. Geçici ağ hatalarında sonraki tur yeniden okumayı dener. Alarm kayıtları
SQLite events tablosundadır; Telegram/harici alarm bağlantısı henüz yoktur.

Otomatik devralma tek LONG/one-way demo oturumu ve en fazla 6 günlük işlem
geçmişiyle sınırlıdır. 1000 fill veya sorgulanamayan geçmişte otomatik müdahale
reddedilir. Önceki `position-cycle` deneylerinin oturumları bu modele otomatik
ithal edilmez. Borsa ile manuel işlemleri atomik kilitlemek mümkün olmadığından
bot çalışırken aynı hesapta manuel işlem yapmayın.

Geliştirici demo kesinti testi (süreç koruma doğrulanınca aniden sonlanır):

```powershell
python -m agentrader managed-open --execute-demo --test-only --crash-after-ready
python scripts/check_demo_restart.py
```

İkinci komut yeni giriş açmadan iki yeni süreçte devralmayı kontrol eder,
yalnızca oturuma ait stopu iptal ederek onarımı sınar ve finally bloğunda
sahipliği doğrulanan pozisyonu kapatır. Sanal pozisyon kısa süre stopsuz kalır;
yalnızca demo hata enjeksiyonu içindir. Son kanıt `logs/restart-test-result.json`.

## Sürümlü planlar ve yerel onay — 5 Kasım 2026

Yeni işlem yolu `plans` komutlarıdır. Plan oluşturmak emir göndermez ve kullanıcı
onayı sayılmaz. Mod A'da `approve`, Mod B'de `activate` ile belirli sürüm yetkilendirilir.
Onay/etkinleştirme tek giriş içindir; açık pozisyonu watchdog korur ve yönetir.

```powershell
# Ağ ve API anahtarı gerektirmeyen örnek oluştur:
python -m agentrader plans example | Set-Content -Encoding utf8 plan.demo.json
# Dosyadaki fiyatları, tutarı, mode ve geçerliliği incele/düzenle.
# Örnek fiyatlar sabittir; güncel piyasa analizi veya işlem önerisi değildir.
python -m agentrader plans create plan.demo.json
python -m agentrader plans show demo-example 1
python -m agentrader plans list
```

`create` yalnızca ilk çıktıda yerel `authorization_token` gösterir. Bu API secret
değildir; yine de onay yetkisi taşıdığı için paylaşmayın. Sonraki `show/list`
çıktılarında token veya hash'i gösterilmez. Kaybedilirse yeni plan sürümü oluşturun.

Planı gerçekten onaylamak istediğinizde, içe aktarma çıktısındaki token ile:

```powershell
# Yalnızca mode=A; 120 saniye bu demo komutunun değiştirilebilir varsayılanıdır:
python -m agentrader plans approve demo-example 1 --token ONAY_KIMLIGI --ttl 120
# mode=B planında bunun yerine (planın son geçerliliğine kadar ön yetki):
python -m agentrader plans activate demo-example 1 --token ONAY_KIMLIGI
# Güncel piyasa/hesap/risk kontrolü ve önizleme; emir yok, yetki tüketilmez:
python -m agentrader plans run demo-example 1
# Yalnızca yetkilendirilmiş sürümü demo borsasında bir kez yürütmek için:
python -m agentrader plans run demo-example 1 --execute-demo
```

Son komut koşullar sağlanırsa sanal pozisyon açıp stop/TP kurar; pozisyonu hemen
kapatmaz. Devamlı koruma için `watchdog --execute-demo --iterations 0`, ayrı
kapatma için `managed-close --execute-demo` kullanılır. Otomatik koşul izleme
işçisi henüz yoktur; `plans run` her çağrıda koşulu bir kez kontrol eder. Koşul
oluşmamışsa `WAITING_CONDITION` döner, yetki tüketilmez. Onay süresi içinde tekrar
çağrılabilir. Kendi terminalimizin strateji olayları, Telegram onayı ve zamanlayıcı daha sonra
ortak uygulama komut katmanı üzerinden bu servise bağlanacak.

```powershell
python -m agentrader plans reject demo-example 1
python -m agentrader plans cancel demo-example 1
```

Ret/iptal yeni girişe engeldir. Açık pozisyonun planını iptal etmek stop/TP'yi
silmez veya pozisyonu kapatmaz; tek giriş yetkisi zaten tüketilmiştir. Yürütme
ayrılmış ama henüz ne emir niyeti ne oturum kaydı oluşmuşsa iptal rezervasyonu
bırakır. Belirsiz gönderim/oturum varsa otomatik yeniden giriş yapılmaz; kayıtlar
uzlaştırılmalıdır. Pozisyon kapandıktan sonra `plans show/list` durumu `CLOSED`+yapar ve sembol rezervasyonunu bırakır.

### Şema ve desteklenen kapsam

- Şema v1: demo Binance USD-M, one-way LONG, tek MARKET giriş ve 1–8 sıralı hedef.
- Giriş: `IMMEDIATE`, `MARK_AT_OR_BELOW` veya `MARK_AT_OR_ABOVE` (mark fiyatı).
  Fiyat toleransı referans fiyata göre baz puandır: 50 bps = %0,5. En fazla %1.
- Tutar: `NOTIONAL` nominal USDT üst sınırı veya `MAX_LOSS` tahmini stop kaybı
  bütçesi. Miktar güncel fiyat ve sembol adımlarına göre aşağı yuvarlanır; borsa
  minimumunu karşılamıyorsa bütçe kendiliğinden artırılmaz. Bağımsız demo risk
  sınırları her iki türde de uygulanır. Teminat tutarı/kaldıraç değişikliği desteklenmez.
- Hedef `fraction` paylarının toplamı `1` olmalıdır; stop/hedef tick adımına
  uymalıdır. `max_runs=1`, artırma/ters yön/yeniden giriş false olmalıdır.
  `break_even_after_target` null veya son hedeften önceki hedefin 1 tabanlı numarasıdır.
- SHORT/hedge, çoklu giriş, pozisyon artırma ve yeniden giriş henüz yürütülmez;
  bu özellikleri isteyen plan içe aktarılırken reddedilir.
- Sayısal değerler JSON metnidir; zamanlar saat dilimli ISO-8601. En fazla 5 gün
  geçerli plan kabul edilir. Çalışan plan yerinde değiştirilemez. Diğer değişiklikler
  aynı plan kimliğiyle sıradaki sürümü gerektirir ve eski onayı geçersiz kılar.

Her plan SQLite'ta içerik özetiyle saklanır; onay kullanıcıya, sürüme ve içeriğe
bağlıdır. Aynı sembolde başka onaylı plan reddedilir. Giriş hakkı gönderimden önce
atomik ayrılır; aynı sürüm tekrar yürütülmez. Onay süresi/fiyat/koşul/risk gönderim
öncesi yeniden doğrulanır. Market gerçekleşmesi yetkili fiyat/tutar sınırını aşarsa
watchdog sahipliği doğrulayıp reduce-only kapanış dener. Kayma nedeniyle önceden
belirtilen kayıp/tutarın tam garanti olduğu iddia edilmez.

Yetkili kişi yerel CLI'da işletim sistemi kullanıcısıdır (`local:kullanıcı`). İlk
plan komutu depoyu bu kullanıcıya bağlar. Bu bir uzak kimlik doğrulama sistemi
değildir; internetten `actor` alanına güvenerek kullanılmamalıdır. Telegram ve
web terminali için uzaktan kimlik denetimli onay henüz eklenmedi.

Eski `order-cycle`, `position-cycle`, `managed-open` giriş deneyleri artık ayrıca
`--test-only` ister. Bu açık geliştirici deneyi bayrağı plan onayının yerine
geçmez ve sinyal/Telegram akışına bağlanmamalıdır. Plan deposu etkinleştikten sonra
yetki guard'ı olmayan normal kalıcı girişler reddedilir. Raw exchange adaptörü
hesap anahtarına sahip yerel geliştirici aracıdır, yetkili ürün giriş noktası değildir.

Yeni tablolar `plan_versions`, `plan_slots`, `plan_actions`; şema geçişi v1 mevcut
emir/olay/oturum kayıtlarını korur. Plan/kademeli yönetim kapsamı o aşamada 86 ağsız testle doğrulandı;
bu aşamada gerçek demo hesabında yeni plan onaylanmadı ve emir gönderilmedi.

## Kademeli çıkış ve giriş fiyatına stop — 5 Kasım 2026

```powershell
python -m agentrader plans example --staged | Set-Content -Encoding utf8 plan.staged.demo.json
```

Örnek 64 USDT nominal üst sınır, %50/%50 iki hedef ve ilk hedef tamamlanınca
stopu gerçekleşen ortalama giriş fiyatına taşıma içerir. Fiyatlar yalnızca sabit
örnektir; güncel piyasa verisiyle gözden geçirilmelidir. Mevcut create →
approve/activate → run akışını kullanır; yeni izin türü veya otomatik onay yoktur.

Önizleme `target_quantities` içinde miktar dağılımını gösterir. Ara sınırlar
kümülatif paya göre lot adımına aşağı yuvarlanır; kalan miktar son hedefe verilir.
Bir pay minimum miktarı karşılamıyorsa bütçe kendiliğinden büyütülmez; plan
reddedilir. Gerçek giriş kısmen dolarsa kalan giriş iptal edilir ve hedefler
doğrulanan gerçekleşmiş miktardan hesaplanır. Bölünemeyen kısmi pozisyonda risk
azaltıcı tam kapatma denenir.

**Ara hedefler watchdog tarafından izlenir.** Güncel mark fiyatı hedefe ulaştığı
kontrol turunda reduce-only MARKET çıkış gönderilir; bunlar borsada bekleyen
ayrı limit TP emirleri değildir. İzleyici kapalıyken ara hedef çıkışı ve stop
taşıma çalışmaz; kaçırılmış fiyat temasının sonradan gerçekleştiği varsayılmaz.
Tam pozisyon için stop ve son hedefte closePosition TAKE_PROFIT_MARKET yedeği
borsada tutulur. Son hedef yedeği tetiklenirse kalan miktarı kapatabilir; ara
hedeflerin ayrıca gerçekleşmiş olduğu iddia edilmez. Market kayması olabilir.

Hedefin tetiklenmesi, her çıkış denemesinin kimliği, gerçekleşen miktar ve stop
geçişi SQLite oturumuna gönderimden önce yazılır. Kayıp yanıtta aynı emir sorgulanır.
Kısmi çıkışın açık kalanı iptal edilip terminal durumu doğrulanmadan yeni çıkış
gönderilmez. Yalnızca eksik miktar için en fazla üç kesin devam denemesi vardır;
belirsiz emir veya kesin ret durumunda körlemesine tekrar yoktur. Hedef bir kez
tetiklenip kısmen gerçekleşmişse, kalan miktar o hedef eyleminin devamı sayılır;
stop seviyesi aşılmışsa risk azaltıcı tam çıkış uygulanır.

`break_even_after_target=1`, ilk hedefin **tam miktarı** doğrulanmadan stopu
değiştirmez. Yeni stop ortalama gerçekleşen giriş fiyatının tick adımına aşağı
yuvarlanmış değeridir; komisyon/funding/kayma dahil net sıfır zarar garantisi
değildir. Önce yeni stop kabulü/sahipliği doğrulanır, sonra eski stop kaldırılır.
Geçiş ortasında çökülürse yeni süreç kayıtları devralır; çift çıkış veya yeni bir
stop kopyası üretmez. Geçiş doğrulanamazsa mevcut koruma kaldırılmadan sahipliği
doğrulanan kalan pozisyonu kapatmayı dener.

Watchdog, yönetim eylemlerini değişmez onaylı plan sürümüyle de karşılaştırır.
Plan iptali veya süresinin dolması açık pozisyonun önceden izinli çıkış/koruma
yükümlülüklerini kaldırmaz. İzleyici devamı ve kapatma komutları önceki gibidir.
Yeni kademeli/stop geçişi senaryoları gerçek demo borsasında henüz test edilmedi;
taklit borsada kısmi fill, ret, yanıt kaybı ve süreç kesintisiyle doğrulandı.

## Canlı piyasa verisi ve temel analiz — 5 Kasım 2026

```powershell
python -m agentrader market report
python -m agentrader market report --symbols BTCUSDT ETHUSDT --bars 300
# Son kayıtlı veri kesim zamanını yalnızca önbellekten tekrar hesapla:
python -m agentrader market report --offline
# Belirli kesim zamanı (saat dilimi zorunlu):
python -m agentrader market report --offline --as-of 2026-11-05T01:10:05.037+04:00
```

Bu yol `.env` veya hesap anahtarı yüklemez. Ayrı `PublicMarket` adaptörü sabit
`https://fapi.binance.com` adresinde yalnızca time/exchangeInfo/klines/premiumIndex GET uçlarını
kabul eder; hesap ve emir uçları, imza ve key parametreleri reddedilir. Bu canlı
veri okuması, gerçek hesap veya canlı işlem desteğinin açılması değildir.

Varsayılan BTCUSDT ve ETHUSDT USDT perpetual sözleşmelerinde 1W/1D/4H/1H/15M,
300 kapanmış mum hedeflenir. `--bars` 60–5000 ve `--symbols` en fazla 10 sembol
alır. REST sayfaları en fazla 499 satırdır; geçmiş geriye doğru sayfalanır.
418/429 veya bölgesel 451 durumunda yeni istek gönderilmez; başka IP/adresle
kısıt aşılmaz. Otomatik ağ tekrarı veya demo verisine sessiz geri dönüş yoktur.

Canlı piyasa verisi `data/market.sqlite3` dosyasındadır; demo emir/pozisyon
deposundan ayrıdır. Anahtar source/symbol/interval/open_time'dır. Yinelenen aynı
satırlar ayıklanır; çelişkili tekrar, OHLC/hacim, zaman hizası ve eksik mum
kontrol edilir. Kapanmış veri revizyonları sayılır. Canlı sorguda sunucu saati
tek veri kesim zamanı olarak sabitlenir; açık mumlar saklanır ama analiz dışıdır.
Hafta UTC pazartesi, gün UTC 00:00 sınırını kullanır. Son beklenen kapanmış mum
eksik/eskiyse veya geçmişte boşluk varsa gösterge alanları boş ve durum INVALID_DATA
olur. En az 51 kapanmış mum gerekir; 300'den kısa geçmiş ayrıca işaretlenir.

Rapor EMA20/EMA50, Wilder RSI14 ve ATR14, ATR yüzdesi ve son kapanmış mumun USDT
hacmini önceki 20 kapanmış mum ortalamasıyla karşılaştırır. EMA ilk dönem SMA'sıyla
başlatılır; RSI ilk 14 farkın ortalaması ardından Wilder yumuşatmasıdır; sabit
fiyatta RSI=50 kabul edilir. ATR ilk mumda high-low, sonra önceki kapanışı da
içeren true range ve Wilder yöntemidir. Sabit pencere/seeding nedeniyle başka
platformlarla küçük farklar olabilir. Trend UP: close > EMA20 > EMA50; DOWN:
close < EMA20 < EMA50; diğer durumlar MIXED. Bunlar giriş sinyali değildir.

Son 7 tamamlanmış UTC gününde toplam USDT hacmi ve taker alış/satış agresifliği,
önceki 7 güne göre toplam değişim verilir. Eksik gün doldurulmaz; karşılaştırma
tam değilse yüzde hesaplanmaz. Bu veriler yeni para girişi veya borsalara zincir
üstü varlık akışı değildir; capital_flows=NOT_AVAILABLE olarak açıkça işaretlenir.

Her çağrı JSON ve Markdown üretir: `reports/market-ZAMAN-RUN_ID.*` ve kolay
erişim için `reports/market-latest.*`. Son dosyalar çevrimdışı rapor çağrısında
da güncellenir; canlı ilk çıktının kalıcı adı korunur. JSON veri kalitesini,
gerekçeleri ve son kapanış zamanlarını; Markdown kısa tablo ve günlük hacmi sunar.
Veri zamanı UTC ve Bakü (+04:00) gösterilir. Tam girdi, SHA-256 özeti ve rapor
ayrı `analysis_runs` tablosunda saklanır. Canlı/önbellek aynı kapanmış girdilerle
aynı göstergeleri ve özeti üretir; sonradan veri revizyonu varsa yeni özet oluşur.

Raporun `BEKLE` değerlendirmesi bu ilk sürümde giriş stratejisinin etkin
olmadığını belirtir. Destek/direnç, pivot/BOS/CHoCH, dominans/TOTAL3, haber/AI,
sermaye akışı ve Telegram sonraki aşamalardır. Hiçbir market komutu plan
etkinleştirmez veya emir göndermez. Veri hatasında rapor INCOMPLETE, çıkış kodu
1'dir; başarılı ve eksiksiz rapor kod 0'dır. WebSocket/sürekli yenileme henüz yoktur.

Doğrulama: 105 ağsız test başarılı; ayrıca canlı BTC/ETH için 3010 mum okundu,
beşer zaman dilimi OK raporlandı. Gerçek önbellek tekrarı aynı göstergeler ve
aynı girdi özetiyle doğrulandı. Bu işlemler hesap/emir anahtarı kullanmadı.

[Resmî Kline/market veri sözleşmesi](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data).

### Canlı veriden hazırlanan demo planında fiyat farkı kontrolü

Plan şema v1'de isteğe bağlı `market_guard` alanı kaynak
`binance_usdm_live_mark`, `max_divergence_bps` (metin, en fazla 100) ve
`max_age_seconds` (1–30) taşır. Bu alan da onaylanan içerik özetine bağlıdır.
Giriş öncesi demo ve canlı mark fiyatları karşılaştırılır; fark veya eskilik
sınırı aşılırsa emir açılmaz. Canlı okuma başarısızsa sessizce kontrol atlanmaz.
Sadece yeni girişe uygulanır; mevcut korumanın yönetimi canlı veri servisine bağımlı yapılmaz.
Bu ek denetimle test toplamı 107'dir. Onay bekleyen somut teklif dosyası
`reports/proposal-btc-live-demo-20261105-012017.md` içindedir; bu tarihsel teklif
koşul gerçekleşmeden süre dolduğu için EXPIRED oldu. Taslak oluşturmak
kullanıcı onayı veya emir gönderimi değildir.

### Fiyat kaydı ve onaylı oturumu devralma

Stop geçişi kalan miktar için `quantity` ve `reduceOnly=true` kullanır;
ilk stop ve son hedef Close-All korumalarıdır. Yeni stop borsada doğrulanmadan
eski stop kaldırılmaz. Gönderim hatalarının kod/HTTP bilgisi niyette ve
`order_submission_failed` olayında tutulur. Ham yanıt/anahtarlar loga basılmaz.

Zaten borsada kapanmış ve tüm emirleri sonlanmış oturumu yalnızca GET ile
sonlandırmak için `python -m agentrader managed-finalize` kullanılır.
Bu komut açık pozisyonu kapatmaz, koruma kurmaz veya iptal etmez.
UNKNOWN algo kaydı ancak -2013 sorgusu, tamamen boş hesap ve boş açık emir
listeleriyle `RESOLVED_FLAT` olabilir; aynı POST tekrar gönderilmez.

Her yetkili plan kontrolünde `plan_price_check` olayı SQLite'a kaydedilir:
demo mark fiyatı, kaynak ve okuma zamanları, koşul, tetik seviyesi, işaretli
fiyat farkı, onay bitişi ve bekleme/koşul sağlandı/engellendi nedeni.
`CONDITION_MET` tek başına emir kabulü değildir; risk ve yetki kontrolü ayrıca sürer.
Kontrol sonuçları izleyicinin JSONL çıktısında da görünür. Bu, aralıksız fiyat
kaydı değildir; REST kontrolleri arasındaki kısa dokunuşlar kaçırılabilir.

Onaylı planı izlemek için `python scripts/watch_approved_demo.py PLAN_ID 1`
kullanılır. Bu betik onay oluşturmaz veya süresini yenilemez.
`--restart-after-stop` açıkça istenen demo kesinti testi içindir. İlk hedef
sonrası stop geçişi APPLIED ve korumalar borsada doğrulanmışsa kontrol noktası
yazılır; yürütücü kilidi bırakıldıktan sonra ayrı süreç `--resume-only` ile
devralır. Farklı PID, aynı oturum/giriş/stop ve tek BUY niyeti doğrulanır.
Başarı `restart_verified` JSONL ve SQLite olayına kaydedilir. Pozisyon hedefe
ulaşmadan kapanırsa bu senaryo başarılı sayılmaz. Windows dosya yönlendirmesinde
Türkçe karakterler JSON kaçışlarıyla kaydedilir; içerik kaybolmaz.
Mevcut eşleşen oturumu yeni giriş açmadan devralmak için aynı komuta
`--resume-only` eklenir. Önce eski izleyici durmalıdır; tek yürütücü kilidi
paralel çalışmayı reddeder. Stop/son hedef emirleri yeniden başlatma testi
için silinmez. Yeniden bağlanırken plan özeti, oturum kimliği ve borsa sahipliği
kontrol edilir. Yerel izleme kesintisinde ara hedefler takip edilemez.

### Kaldıraçlı grid ön kontrolü

`python -m agentrader grid preview data/proposals/btc-grid-user-20261106.json --output reports/grid-preflight-20261106.json`

Bu komut salt okunurdur. 8 aritmetik aralık (9 sınır), toplam nominal bütçe,
emir minimumları ve risk denetimini hesaplar. GridLedger fill temelli kalıcı
simülasyon defteridir; borsaya emir göndermez. 20x kaldıraç adaptörü ve salt
okunur SymbolConfig/LeverageBracket kontrolü eklendi. Tam grid yürütücüsü
henüz tamamlanmadı. 200 USDT nominal/8 grid isteği minimum emir boyutundan
BLOCKED oldu; bütçe veya eski risk sınırları yükseltilmedi.
Ayrıntı: 05-KALDIRACLI-GRID-KAPSAMI.md. Toplam 132 test başarılı.

### A1 yetenek ve izin keşfi

`python -m agentrader capabilities list --category trade`

Anahtar veya ağ kullanmadan sürümlü kataloğu ve gerçek adaptör izinlerini gösterir.

`python -m agentrader capabilities probe --symbol BTCUSDT --account --output reports/capability-probe-latest.json`

12 sabit GET kontrolü yapar, hiçbir emir veya hesap ayarı değiştirmez.
--account verilmezse .env/anahtar yüklenmez ve yalnız public kontroller yapılır.
Ham hesap yanıtı raporlanmaz; anahtarlar yazılmaz. READ_VERIFIED yalnızca
okuma erişimidir; canTrade=true bile emir oluşturma yetkisini kanıtlamaz.

`python -m agentrader capabilities latest --symbol BTCUSDT --account --max-age 300`

Ağsız olarak mevcut anahtarla eşleşen son SQLite kanıtını getirir. Başka
anahtarın veya sembolün kanıtı kullanılmaz; eski kayıt STALE olur. NOT_FOUND,
STALE veya eksik probe sonuçları CLI'dan başarısız çıkış koduyla döner.
Katalog, demo keşfi ve tamamlanmış strateji desteği ayrı durumlardır.
A1'de 12/12 demo okuması ve toplam 150 test doğrulandı. Grid yürütücüsü yoktur.

### Güncel geliştirme durumu

6 Kasım 2026: 218 test başarılı; ortak transport sonrasında 12/12 demo okuması
doğrulandı. A2 uygulandı; A3–A8 için risk, ayar komutları, emir doğrulama,
kalıcı gerçekleşme defteri ve grid durdurma temelleri eklendi. Bunların tamamı
henüz ortak emir/grid yürütücüsüne bağlanmadı. Grid yürütme kapalıdır.
Paket bazında kesin sınırlar ve kalan işler: [07-GELISTIRME-DURUMU.md](07-GELISTIRME-DURUMU.md).

`python -m agentrader settings --help` ayar komutlarını gösterir.
`prepare` borsada değişiklik yapmaz; `apply` yalnız somut, geçerli komutu
bir kez gönderir; `reconcile` yeniden göndermeden okur.

### Plan v2 yürütücüsü — sonraki geliştirme

249 test geçti. V2 SINGLE piyasa girişi (LONG/SHORT, one-way/hedge), tek son
hedef ve stop koruması ayrı kalıcı yürütücüye bağlandı. Kayıp yanıtlar yeniden
POST edilmez. Kısmi giriş kalanı önce iptal edilir; miktar sahip olunan
gerçekleşmelerle doğrulanır. Koruma HTTP yanıtıyla değil GET alanlarıyla doğrulanır.

`python -m agentrader plans preflight PLAN.json` güncel hesap, fiyat, kaldıraç,
basamak ve risk kontrolüdür; emir göndermez, planı yetkilendirmez.

`plans run PLAN_ID VERSION` yetkili planın ön kontrolünü yapar; yalnız
`--execute-demo` ile tek giriş hakkını tüketir. V2 grid, LIMIT, çoklu hedef
ve break-even henüz bu yürütücüye açık değildir.

`python -m agentrader plans manage SESSION_ID` yeni giriş açmadan v2 oturumunu
okur. `--execute-demo` koruma/kapanış/temizleme işlemlerini uygular. Bu komut
tek turdur; arka planda sürekli izleme başlatmaz. Borsada doğrulanan stop/son
hedef emirleri yerel süreç kapansa da borsada tutulur.

Yeni yürütücü için gerçek demo yazma testi henüz yapılmadı. Son boş hesap
kontrolü mevcut pozisyon/emir nedeniyle BLOCKED döndü; hesaba müdahale edilmedi.

### LIMIT, kademeli hedef ve girişe stop güncellemesi

270 test geçti. V2 artık SINGLE LIMIT girişini ve kademeli hedefleri destekler.
Dolmayan LIMIT, onay süresi/plan geçerliliği içinde bekler; süre dolduğunda,
giriş iptal edildiğinde veya stop/son hedef aşıldığında iptal edilir. Kısmi
girişin kalanı iptal edilip gerçekleşen pozisyon yönetilir.

Ara hedefler yalnız onaylanan payı azaltır; kısmi çıkışın kalanı iptal
edilmeden yeni azaltma gönderilmez. Kayıp yanıtlar sorguyla uzlaştırılır.
break_even_after_target sonrasında gerçek giriş ortalaması ve kalan miktarla
yeni stop doğrulanır; sonra önceki stop iptal edilir. Sonraki hedefler kalan
miktarı azaltırsa stop tekrar boyutlandırılır. Bu fiyat komisyon dahil net
başabaş olarak hesaplanmaz.

`python -m agentrader plans manage SESSION_ID --execute-demo --iterations 0 --interval 5`

Mevcut v2 oturumunu sürekli izler; yeni oturum kurmaz. SINGLE varsayılanı tek turdur.
Ctrl+C yerel izlemeyi durdurur; borsadaki korumaları silmez. Belirsiz hata
otomatik yazma tekrarı yerine izlemeyi durdurur. Bu geliştirmede arka planda
izleyici başlatılmadı ve demo hesabında emir değiştirilmedi.

### Grid yürütücüsü ve rezervasyon

312 test geçti. GridRunner plan v2'ye bağlandı: LONG/SHORT, one-way/hedge,
aritmetik/geometrik, kalıcı tam bütçe rezervasyonu, kısmi fill, karşı emir,
tekrar alış, stop/iptal yarışı ve restart. Native koruma alt emirleri de
sahiplik/temizlik denetimine dahildir. Gerçek demo yazma testi henüz yapılmadı.

Grid `plans run --execute-demo` ve `plans manage --execute-demo` için varsayılan
sürekli ön plan izlemedir. Onaylı grid yeni hücre/tekrar alış emirleri üretebilir.
Sınırlı izleme veya Ctrl+C çıkışında yeni açıcı emirleri iptal edip mevcut
pozisyonu korumayla bırakmayı dener. Ağ kesintisinde bu garanti edilemez.

`python -m agentrader plans stop-grid SESSION_ID --execute-demo`

Yeni girişleri durdurur. Mevcut pozisyonu da kapatmak için açıkça
`--close-position` eklenir. Tam sözleşme ve eksikler:
[08-GRID-YURUTME-VE-REZERVASYON.md](08-GRID-YURUTME-VE-REZERVASYON.md).

### İzole teminat ve native toplu iptal

340 test geçti. İzole pozisyona teminat ADD/REMOVE komutları ve gridin
durdurma akışında seçili native toplu iptal eklendi. Teminat yanıtı kaybolursa
aynı artımlı istek tekrar gönderilmez; belirsizlik yeni girişleri engeller.
Toplu iptal başarısı her alt emir için GET ile doğrulanır. Tam gerçekleşmiş
grid emirlerinin gereksiz tekrar sorguları da azaltıldı.

`python -m agentrader settings margin-prepare --help`

Yeni komutlar, sınırlar ve kalan işler:
[09-TEMINAT-VE-TOPLU-IPTAL.md](09-TEMINAT-VE-TOPLU-IPTAL.md).
Bu yazma yeteneklerinin gerçek demo doğrulaması henüz yapılmadı.

### Native amend ve toplu oluşturma/değiştirme

372 test geçti. `orders` komutları mevcut v2 GTC LIMIT emirleri için tekli/toplu
değişiklik hazırlama, uygulama, salt okunur uzlaştırma ve taslak iptali sağlar.
Miktar büyütülmez; SINGLE fiyatı yalnız daha iyi yöne gider; grid seviyeleri
korunur. Özgün niyet yerine doğrulanmış revizyon zinciri okunur.

`python -m agentrader orders --help`

Gridin hazır hücreleri native toplu oluşturma ile en fazla beşer emir halinde
gönderilir. Bütün kimlikler atomik ayrılır; kısmi ret ve belirsiz yanıt ayrı
uzlaştırılır. Aynı PUT/POST kayıp yanıttan sonra yeniden gönderilmez.
Kapsam, komutlar ve eksikler:
[10-NATIVE-EMIR-DEGISTIRME-VE-TOPLU-OLUSTURMA.md](10-NATIVE-EMIR-DEGISTIRME-VE-TOPLU-OLUSTURMA.md).
Bu geliştirmede gerçek demo hesabına yazma yapılmadı.

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

Neutral grid artık tek plan altında iki hedge tarafını ve ortak bütçeyi yönetir. Varsayılan risk limitleri değişmedi. 541 çevrimdışı test geçti; gerçek demo neutral işlemi doğrulanmadı.

Ayrıntı: [15-NEUTRAL-GRID-VE-IKI-TARAFLI-YONETIM.md](15-NEUTRAL-GRID-VE-IKI-TARAFLI-YONETIM.md).


## Aktif teminat teslimi — 6 Kasım 2026

Aktif çoklu oturum, yönlü grid ve neutral taraf için izole teminat entegrasyonu eklendi. Teminat değişiklikleri somut komutla yetkilendirilir; bütçeler otomatik artırılmaz. 560 test geçti; gerçek demo teminat kanıtı bekliyor.

Ayrıntı: [16-COKLU-OTURUM-TEMINAT-YONETIMI.md](16-COKLU-OTURUM-TEMINAT-YONETIMI.md).


## Grid takip stopu — 7 Kasım 2026

Yönlü GRID için isteğe bağlı bot takip stopu eklendi. LONG/SHORT watermark ve eşik kalıcıdır; tetikte yeni girişler durur, gerçek kalan miktar kapanış akışına geçer. Native sabit stop korunur; hareketli eşik bot çalışırken izlenir. Neutral/native takip ve diğer politikalar bekliyor. 13 yeni senaryo dahil 573 test geçti; sonuç doğrulama raporuna kaydedildi. Gerçek demo yazma yapılmadı.

Ayrıntı: [17-GRID-TAKIP-STOPU.md](17-GRID-TAKIP-STOPU.md). Kanıt: `reports/development-validation-20261107.json`.


## Grid borsa stopunu yenileme — 7 Kasım 2026

Yönlü GRID için isteğe bağlı `management.trailing.native_stop: true` eklendi. Yeni close-all stop GET ile doğrulanmadan önceki takip stopu kaldırılmaz; başlangıç sabit koruması tutulur. Eski planlar değişmez. 21 yeni senaryo eklendi; tam regresyon sonucu `reports/development-validation-20261107.json` içinde. Gerçek demo yazma kanıtı bekliyor.

Ayrıntı: [18-GRID-BORSA-STOP-YENILEME.md](18-GRID-BORSA-STOP-YENILEME.md).


## 10 Kasım — CL01–CL03 otomatik kapanış ve CL04 erteleme

CL01 iki gerçek sekmede 13 kontrollü tutarlılık senaryosuyla doğrulandı. CL02 gösterge yazım hatasının uygulamayı kapatması düzeltildi: 15 hata senaryosu ve 12.420 bağımsız sayısal karşılaştırma geçti. CL03 sıkışık Fibonacci etiketleri düzenlendi; 9 ekran/DPR durumunda 243 raster ölçümü geçti (azami 0,844 CSS px). Frontend 127/127 test geçti. Güncel index-z15JopqV.js için üç 60 saniyelik kontrollü performans koşusu geçti; bu, yeni bir 30 dakika veya fiziksel GPU kabulü değildir.

Kullanıcı fiziksel hareketleri şimdi yapamayacağını belirtti. CL04 ertelendi, B5 tamamlanmadı; ana plan 24/25. Bot bağlanmadı. Önceki aday 01 korunur; güncel geliştirme adayı 02 için RELEASE.md ve reports/chart-closure-progress-20261110.json izlenir.
