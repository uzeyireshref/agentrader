# Demo Bot terminali bağlantısı

17 Kasım 2026. Yerel entegrasyon teslimidir; müşteri sunucusuna dağıtım veya gerçek borsa kabulü değildir.

## Kullanıcı akışı

Varsayılan Bot ekranı artık gerçek Demo bağlantısını kullanır. Grafik ve Bot aynı uygulama ve port üzerindedir: `/?view=bot`. Eski sentetik tasarım yalnız `/?view=bot&mode=preview` adresindedir. Bağlı modda örnek bakiye veya pozisyon kullanılmaz.

1. Web erişim anahtarıyla yerel oturumu açın. Anahtar JavaScript kalıcı depolarına veya URL'ye yazılmaz; oturum httpOnly, SameSite=Strict yerel cookie kullanır.
2. Worker hazır olduğunda **Hesabı yenile** ile hesap, pozisyonlar, normal/algo emirler, sahip olunan oturumlar, planlar ve komutları alın. Görünüm seri sorgulardan oluşur; atomik değildir. 15 saniyeden eski görünümle yeni değişiklik önizlemesi/onayı gönderilmez; hesabı tekrar yenileyin.
3. SINGLE, GRID veya NEUTRAL taslağını doldurun ya da grafikteki Long/Short çizimini aktarın. Çizim kimliği ve revizyonu sunucuda yeniden kontrol edilir. Değişen çizimi yeniden aktarın; elle düzenleme kaynak bağını kaldırır.
4. **Hesapta ön kontrol yap** mevcut borsa filtreleri ve sunucu risk profiliyle planı derler. Bu adım emir göndermez. Önizleme 60 saniye geçerlidir. Checkbox ve ayrı **Demo hesabında uygula** eylemi olmadan yürütme olmaz.
5. Açık onay, hesap/plan/digest/risk/süre ve yeni preflight denetimlerinden sonra mevcut CLI yürütme motoruna devredilir. Browser kapanınca ayrı çalışan worker oturumları izlemeyi sürdürür.
6. **Kayıtlar** bölümünde dış iş durumu ile iç borsa sonucunu ayrı değerlendirin. `SUCCEEDED`, kuyruğun işi işlediği anlamındadır; `APPLIED`, `UNKNOWN`, oturum durumu ve toplu üye sonuçları ayrıca incelenmelidir. HTTP/ACK dolum kanıtı değildir.

Pozisyon artırma/azaltma/kapatma/ters yön, native trailing, hesap ayarları, koruma denetimli iptaller, iptal timer'ı, adlandırılmış sorgular, sınırlı geçmiş ve dışa aktarma mevcut desteklenen komutlara bağlanır. Sunucu risk sınırlarını kullanıcı tarayıcısı belirleyemez. Artırma/azaltma ve native trailing mevcut motorun doğrulanmış SINGLE oturum koşullarına tabidir; genel hesap pozisyonu bot sahipliği sayılmaz.

**Toplu giriş:** İşlem panelinin gelişmiş hazırlığında SINGLE planını önce **Toplu giriş yetkisini incele** ile ayrı onaylayın. Bu onay yalnız kısa süreli plan yetkisi verir; emir göndermez. Her sembol için ayrı yetkili plan hazırlayın, hesabı yenileyin, Yönetim → Toplu plan girişi içinden 1–5 farklı sembollü yetkili planı seçin ve toplu komutu ayrıca onaylayın. Ortak risk profili ve boş hesap/oturumsuz journal koşulları sunucuda denetlenir. Varsayılan risk profili en fazla bir pozisyon destekler; profil değiştirilmeden çoklu giriş reddedilir.

**Ters yön:** Karşı yön SINGLE planını MARKET/IMMEDIATE ve mevcut hesap ayarlarıyla hazırlayıp **Plan taslağını kaydet** seçin. Kayıt onay veya emir oluşturmaz; flat-account preflight yapmaz. Hesabı yenileyip mevcut oturum ve karşı planı Yönetim → Ters yön üzerinden seçin. Ters yön komutu ayrı onayla mevcut kapanış/temizlik/yeni giriş yetki zincirini kullanır. Taslaklar beş dakika içinde sona erer.

**Geri bildirim:** Son 200 kayıt yalnız bu tarayıcıda saklanır; dışa aktarılabilir. Otomatik geliştiriciye gönderim yapılmaz.

## Yerelde çalıştırma

### Bu bilgisayardaki hazır bağlantı

Yerel başlatıcı `AGENTRADER_LOCAL_AUTO_LOGIN=1` ayarını kullanır. Bu bilgisayardaki tarayıcı aynı origin üzerinden otomatik httpOnly oturum açar; kullanıcı web anahtarı girmez. Bu açık yerel kolaylık modu genel WebSettings varsayılanında kapalıdır. Müşteri/yayın ortamına taşımayın; o ortamda değeri `0` tutun. API localhost host/origin kontrollerini sürdürür.

Mevcut `.env` Demo kimlik bilgileri kullanılarak API ve salt okunur bot worker başlatıldı; gerçek hesap SNAPSHOT işi SUCCEEDED oldu (17 Kasım 2026). Emir gönderilmedi. Web erişim anahtarı `data/local-web-token.txt` içindedir; dosya ve `.env` Git dışında tutulur. Tarayıcıda yerel oturum açmak için bu ayrı web anahtarını kullanın, borsa anahtarını değil.

Yeniden başlatırken depo kökünde iki ayrı kabukta aşağıdaki komutları kullanabilirsiniz. Aynı süreçlerin ikinci kopyasını başlatmayın:

```powershell
python -m scripts.maintenance.local_bot_environment serve
python -m scripts.maintenance.local_bot_environment bot-worker
```

Bu yerel başlatıcı `.env` içinden yalnız izin verilen web ayarlarını API ortamına taşır; borsa bilgilerini worker mevcut Config yolu üzerinden okur. Başlatıcı yürütme bayrağı kabul etmez. İşlem veritabanı eski dosyayı yeniden etiketlemeden ayrı `data/execution-demo-web.sqlite3` olarak hazırlanır.

Sunucu veya ücretli worker servisi gerekmez. Komutları depo kökünden çalıştırın. API ve worker aynı yerel kullanıcı, uygulama veritabanı ve işlem veritabanı ayarlarını kullanmalıdır. Üretim/müşteri ortamı ayrı ayarlar ve ayrı veri depoları kullanır; yerel geliştirme sürer.

API ve worker kabuklarında ortak ayarlar:

```powershell
$env:AGENTRADER_WEB_TOKEN = '<32-256 karakterli güvenli yerel erişim anahtarı>'
$env:AGENTRADER_BOT_ENABLED = '1'
$env:AGENTRADER_WEB_DATABASE = 'data/application-demo.sqlite3'
$env:AGENTRADER_EXECUTION_DATABASE = 'data/execution-demo-web.sqlite3'
$env:AGENTRADER_BOT_RISK_PROFILE = 'risk-demo.json'
```

Web anahtarı yalnız harf/rakam/alt çizgi/tire içermelidir. Yukarıdaki açıklama metnini gerçek anahtarla değiştirin; anahtarı kaynak koda eklemeyin. `WebSettings` `.env` dosyasını okumaz; bu ayarları süreç ortamından alır.

API:

```powershell
python -m agentrader web serve --port 8765
```

Frontend geliştirme için ayrı kabuk:

```powershell
cd frontend
npm run dev
```

`http://127.0.0.1:5173/?view=bot` adresini açın. Vite `/api` isteklerini aynı origin üzerinden 8765 portuna iletir. Üretim derlemesini API'den yerelde sunmak için önce `frontend` dizininde `npm run build` çalıştırın, sonra API adresini açın. API localhost ile sınırlıdır; bu teslimde internete açılmadı.

Worker kabuğunda ortak ayarlara ek olarak `BINANCE_DEMO_API_KEY` ve `BINANCE_DEMO_API_SECRET` yalnız worker ortamında veya mevcut Config `.env` mekanizmasında bulunmalıdır. Borsa anahtarlarını web formuna girmeyin.

Önce salt okunur worker:

```powershell
python -m agentrader web bot-worker
```

Bu mod hesap okumayı ve önizlemeyi destekler; yürütme onayını reddeder. API worker başlatmaz. Demo yürütmesi kullanıcı tarafından ayrıca başlatılır:

```powershell
python -m agentrader web bot-worker --execute-demo
```

İki worker'ı birlikte çalıştırmayın. Bir kerelik işleme için `--once`, tur aralığı için `--interval 1` (1–10 saniye) vardır. Mevcut CLI ile aynı OS yürütücü kilidi kullanılır. Sürekli takip gereken oturumlarda worker açık kalmalıdır; işletim sistemi servis yöneticisiyle müşteri ortamına kurulum bu teslimin parçası değildir.

Eski `data/execution.sqlite3` günlüğünün Demo bağlamı doğrulanmamış olabilir. Otomatik yeniden bağlanmaz: `EXECUTION_CONTEXT_UNVERIFIED` veya `EXECUTION_CONTEXT_MISMATCH` döner. Yeni, ayrılmış Demo store kullanın; eski dosyayı silmeyin veya ad alanını elle değiştirmeyin.

## Kesinti ve teyit

- Her talep sabit iş kimliğiyle saklanır. Değişen içerikle aynı kimlik reddedilir; aynı önizleme için birden çok browser onayı aynı işe dönüşür.
- Kayıp HTTP yanıtı otomatik yeni POST üretmez. Worker başlarken yarım `RUNNING` işler `NEEDS_REVIEW` olur; otomatik tekrar gönderilmez. Eski önizlemenin süresi dolarsa yeni önizleme gerekir.
- Borsa komutları mevcut `command_id` ile uzlaştırılır. Plan yürütmesinde oturum ve plan kimliklerini inceleyin. `UNKNOWN` veya kesinti sonrası aynı işlemi yeni kimlikle tekrarlamayın. Belirsiz emir/rezerv çözümü mevcut CLI kurtarma araçlarına tabidir.
- İzleme hatası ilgili oturumu kalıcı `bot_monitor_paused` durumuna alır. Arayüz bunu gösterir; worker yeniden başlatılması kör yeniden deneme başlatmaz. CLI ile inceleyin; otomatik devam/rezerv serbest bırakma yoktur.
- Timer heartbeat yalnız bu worker sürecinde açıkça kurulan timer'lar için çalışır. Yeniden başlatma timer'ı otomatik devralmaz. Kira uzatılmaz; REFRESH mevcut kira içinde tek heartbeat'tir. Worker durması borsadaki geri sayımı durdurmaz; geniş timer'ın açık pozisyon/koruma uygunluğu sunucuda denetlenir.
- Varsayılan profil demo deney sınırıdır; kullanıcıya özel risk tavsiyesi değildir. Gerçek para, diğer borsa ürünleri ve AI strateji üretimi bu entegrasyonda açılmadı.

## Kabul durumu

İzole backend ve React testleri; tek kullanımlık onay, değişen preflight, yetkisiz erişim, eski journal, kayıp yanıt, yeniden başlatma, salt okunur worker, plan taslağı/yetkilendirme ve tam bağlı form etkileşimini kapsar. `tests/test_bot_terminal.py` ve `frontend/tests/botLive.test.tsx` kullanılır.

Tarayıcı erişim ağacı, bağlı modun yapılandırılmamış oturum ekranını gösterdi ve örnek bakiyelerin bulunmadığı doğrulandı. Desteklenen tarayıcı açılışı tekrar denendi; Computer Use `The browser access host is unavailable` döndürdü. Fiziksel görünüm, scroll, mobil ve bağlı hesap etkileşimlerinin yeni modda tam tarayıcı kabulü **açık**; React etkileşim testleri bunun yerine geçmez. Gerçek Binance Demo emri ve dış borsa kabulü **NOT_RUN**. Kullanıcı onaylı Demo kabul turu ve müşteri dağıtımı ayrı aşamalardır.

### Son otomatik doğrulama — 17 Kasım 2026

- `python -m unittest discover -s tests`: **1.671 test**, OK.
- `npm test`: **393 test**, 0 hata/skip.
- `npm run build`: TypeScript ve üretim derlemesi başarılı; mevcut ana grafik bundle boyut uyarısı sürüyor.
- `git diff --check`: başarılı; Windows satır sonu bilgilendirmeleri var.
- Hedefli bot entegrasyonu 22 test; mevcut pozisyon komutları 28 test. Senkron hedge fixture sınırı ayrıca 35 tekrar geçti.
- İlgili kaynak manifesti üreticisiyle yenilendi; 36 ağsız replay senaryosu geçti. Hiçbir gerçek borsa emri gönderilmedi.
