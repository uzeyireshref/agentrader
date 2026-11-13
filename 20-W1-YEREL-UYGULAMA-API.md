# W1 — Yerel uygulama/API temeli

> Güncel not: W2/W3 grafik ve kalıcı çizimler eklendi. Bu belge W1 tesliminin kapsamını korur; güncel kurulum ve kanıtlar [21](21-GRAFIK-VE-KALICI-CIZIMLER.md) içindedir.

Tarih: 9 Kasım 2026 · Durum: uygulandı; çevrimdışı ve gerçek yerel HTTP/restart doğrulaması.

## Teslim edilen

Kendi grafik terminalimize temel olacak isteğe bağlı FastAPI adaptörü ve HTTP'den bağımsız uygulama servisi eklendi. Mevcut CLI, plan v1/v2, emir/risk/yürütme modülleri korunur. Bu paket henüz grafik veya çizim ekranı içermez; W2 sıradadır.

- Anahtarsız, ağ çağrısı yapmayan sağlık ve 95 operasyonluk yerel yetenek kataloğu.
- Kimliği doğrulanmış, temizlenmiş yerel işlem durum özeti. Mevcut execution.sqlite3 yalnız SQLite mode=ro ile okunur; StateStore oluşturulmaz veya borsa sorgulanmaz.
- Ayrı application.sqlite3 üzerinde sürümlü/atomik şema geçişi ve kalıcı komut kuyruğu.
- Yalnız runtime.inspect komutu; API isteği sadece kuyruğa alır. Ayrı yerel işçi çalıştırılınca durum incelemesi yapılır. Emir, ayar, onay veya stop komutları desteklenmez.
- Sunucu/işçi yeniden başlatmasında kayıtlar korunur; aynı kimlikle aynı istek yeni işlem üretmez. Çökmede RUNNING kalan salt okunur inceleme tekrar yapılabilir. Bu tekrar politikası finansal komutlar için kullanılmayacak.
- Tek uygulama işçisi dosya kilidiyle korunur. Finansal yürütücünün mevcut runtime.lock kilidi değiştirilmez; salt okunur işçi onunla birlikte çalışabilir.

## Yerel kurulum ve başlatma

Proje kökünde PowerShell:

~~~powershell
python -m pip install -e ".[web]"
python -m agentrader web serve
~~~

Sunucu yalnız 127.0.0.1:8765 üzerinde çalışır. Sağlık: http://127.0.0.1:8765/api/health . Bu adreste şu an JSON API vardır; grafik arayüzü sonraki pakettir. Ctrl+C sunucuyu durdurur. Port için web serve --port 8766 kullanılabilir. Dış ağa bağlanma, proxy güveni, çoklu worker ve reload seçenekleri bu yerel girişte açılmaz.

Binance anahtarı olmadan ve .env okunmadan başlayabilir. İlk başlangıç yalnız ayrı uygulama veritabanını hazırlar. AGENTRADER_WEB_TOKEN tanımlı değilse özel durum/komut uçları PRIVATE_API_DISABLED döner; genel sağlık ve katalog çalışır.

## Özel uçlar için yerel erişim anahtarı

Bu token Binance anahtarı değildir. Token'ı URL'ye veya komut gövdesine yazmayın; Authorization başlığında kullanın. Aşağıdaki örnek token'ı yalnız mevcut PowerShell oturumunda üretir; ekrana yazdırmaz:

~~~powershell
$env:AGENTRADER_WEB_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
python -m agentrader web serve
~~~

Token sunucu başlarken okunur. Başka terminalde istemci kullanılıyorsa aynı token güvenli biçimde o istemciye sağlanmalıdır. Bu sürüm tek yerel operatör içindir; uzak kullanıcı/Telegram kimlik doğrulaması henüz uygulanmadı. İstemci gövdesinden actor/owner kabul edilmez; kimlik sunucudaki yerel kullanıcıdan türetilir. Token değişimi yeni sunucu başlangıcında geçerli olur; devam eden kuyruğun sahibi aynı yerel kullanıcıdır.

## API sözleşmesi

| Yöntem ve yol | Erişim | Sonuç |
|---|---|---|
| GET /api/health | Yerel genel | LOCAL_READ_ONLY; borsa erişimi NOT_CHECKED |
| GET /api/capabilities | Yerel genel | Belgeli katalog; yazma izni doğrulanmış sayılmaz |
| GET /api/status | Bearer | Yerel oturum özeti, giriş durdurma bayrağı ve işçi gözlemi |
| POST /api/commands | Bearer | runtime.inspect isteği için 202 kuyruğa kabul |
| GET /api/commands/{request_id} | Bearer | Kuyruk veya tamamlanmış sonuç |

Komut gövdesi:

~~~json
{"request_id":"inspect-001","action":"runtime.inspect","payload":{}}
~~~

Kabul hemen yürütme değildir. Aynı kimlik/içerik 200 ve duplicate=true döndürür; mevcut sonuç korunur. Farklı/geçersiz içerik reddedilir. Komut kimliği 1–64 harf/rakam/alt çizgi/tire; gövde en fazla 8192 byte, application/json, tam alan şeması; yinelenen alanlar ve sonlu olmayan JSON sayıları reddedilir.

401 yanlış/eksik token, 503 özel erişim yapılandırılmamış veya yerel depo okunamıyor, 403 farklı Origin, 400 geçersiz Host, 415 yanlış içerik türü, 413 büyük gövde, 422 desteklenmeyen komut, 409 kayıtlı komut bütünlüğü çakışması, 404 bulunamayan kaynak. Ham hatalar, plan token'ları, hesap referansları, emir parametreleri ve halt gerekçesi cevaplara taşınmaz.

Host yalnız localhost/127.0.0.1 olabilir. Origin varsa sunucu adresiyle aynı olmalıdır; CORS açılmaz. W2 frontend geliştirme sunucusu aynı origin API proxy'si kullanmalıdır. Token ve istek gövdeleri access log'a yazılmaz; otomatik /docs ve /openapi.json bu adaptörde kapalıdır.

## Ayrı yerel işçi

Başka bir terminalde, aynı uygulama veritabanı ve yerel kullanıcıyla:

~~~powershell
python -m agentrader web worker --once
python -m agentrader web worker
~~~

İlk komut tek inceleme yapar veya IDLE döner; ikincisi 2 saniye aralıkla komut bekler. --interval 1–10 seçilebilir. İşçi yalnız uygulama kuyruğunu inceler; Binance anahtarı ve web erişim token'ı istemez. Ctrl+C durdurur. API çalışıyor olması işçinin veya piyasa takibinin çalıştığı anlamına gelmez.

Bu işçi piyasa/strateji motoru değildir. W2'de public piyasa hattı, sonraki paketlerde strateji döngüsü eklenecek. HTTP süreci mevcut pozisyon izleyicisini başlatmaz ve çoğaltmaz.

## Depolar ve migration

Varsayılanlar: data/application.sqlite3 yeni uygulama deposu; data/execution.sqlite3 mevcut işlem deposu. AGENTRADER_WEB_DATABASE ve AGENTRADER_EXECUTION_DATABASE ortam değişkenleriyle farklı yollar seçilebilir. Aynı dosyaya/symlink veya hardlink'e işaret eden iki depo reddedilir. Sırlar .env'den okunmaz ve API cevaplarına eklenmez.

~~~powershell
python -m agentrader web migrate
~~~

application.sqlite3 için app_schema_migrations ayrı sürüm ve checksum defteridir. Tek transaction içinde uygulanır; tekrar çalışma veri silmez; başarısız DDL geri alınır; değiştirilmiş/eski kodla açılamayan yeni migration reddedilir. Legacy PRAGMA user_version ve ilgisiz tablolar değiştirilmez. Mevcut işlem deposu migration'a verilmez. Bu teslim bütün eski modüllerin tablo oluşturma kodunu merkezi migration'a taşımamıştır; bunu gerektiren gelecek şema değişiklikleri ayrıca ele alınır.

Yeni boş depo otomatik hazırlanabilir. Gelecekte dolu depoya yeni migration uygulanmadan önce doğrulanmış yedek/geri dönüş prosedürü hazırlanmalıdır. Bu sürümde execution.sqlite3 üzerinde migration yapılmaz.

## Doğrulama

~~~powershell
python -m pip install -e ".[web-test]"
python scripts/validate_web_foundation.py
~~~

Doğrulama tam çevrimdışı/sahte borsa regresyonunu ve geçici depolarla gerçek localhost HTTP kontrolünü çalıştırır. Yerel sunucu kontrol sonunda kapatılır. Kalıcı kullanıcı işlem deposuna, borsa hesabına veya Telegram'a yazılmaz. Rapor: [web-foundation-validation-20261109.json](reports/web-foundation-validation-20261109.json).

Kapsam: migration tekrar/rollback/gelecek sürüm, mevcut kayıtların korunması, yetkisiz erişim/yazma, şema ve gövde sınırları, Host/Origin, komut tekrarı/restart, işçi kilidi, ayrı süreçte finansal yürütücü kilidi, eksik/bozuk yerel depo ve mevcut CLI'nin web bağımlılıkları olmadan çalışması. Gerçek HTTP kontrolünde API restart sonrası tek komut ve tek işleme doğrulanır.

## Sonraki paket

W2: gerçek Binance verili web grafiği, public piyasa WebSocket hattı, sembol/zaman dilimi seçimi ve grafik etkileşimi prototipi. W3–W4'te çizimler ve takip bağlanır. Kimliği doğrulanmış işlem onayı W6; sermaye tahsisi/yönetim yetkisi W7–W8'dir.

## Kaynaklar

- [FastAPI sunucu çalıştırma](https://fastapi.tiangolo.com/deployment/manually/)
- [FastAPI test bağımlılıkları](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [02 — Ana plan](02-ASAMALI-GELISTIRME-PLANI.md)
- [03 — Mimari sözleşme](03-MIMARI-VE-ISLEM-SOZLESMESI.md)
- [19 — Geçiş tasarımı](19-KENDI-GRAFIK-TERMINALI-VE-GECIS.md)
