# G8 — Üretim bot grafik adaptörü

`agentrader.integration.chart_bot.ChartBot`, strateji/ajan kodunun kullanacağı gerçek Python adaptörüdür. `python -m agentrader chart-bot` aynı sınıfı kullanan üretim CLI girişidir. Adaptör yalnız resmi yerel HTTP servislerini kullanır; uygulama DB'sini doğrudan değiştirmez, borsa istemcisi oluşturmaz ve emir yetkisi taşımaz. G8 kabulünde test-client CRUD yerine bu sınıf ve ayrı CLI süreci kullanılmıştır. Otonom bir işlem stratejisinin veya canlı Demo hesabının işletilmesi bu kabul değildir.

## Kimlik ve bağlantı

Sunucuda G7'deki ayrı kullanıcı ve bot anahtarları yapılandırılmalıdır. Adaptör token'ı `AGENTRADER_CHART_BOT_TOKEN` üzerinden veya sınıfa açık argümanla alır; CLI token'ı komut satırı argümanı veya görev JSON'u olarak kabul etmez. Bot/strateji kimliği sunucudaki `AGENTRADER_CHART_BOT_ID` ve `AGENTRADER_CHART_STRATEGY_ID` ile eşleşmelidir.

`GET /api/chart-actor`, sunucunun doğruladığı aktörü, namespace'i ve sabit Demo piyasa kimliğini verir. Adaptör ilk işlemden önce bunları doğrular. Namespace bot+strateji kimliğinden türetilir; her adaptör isteğinde `X-Chart-Bot-Namespace` başlığı taşınır. Başlık verilmişse sunucu, token ile doğrulanmış aktörle eşleşmesini zorunlu tutar. Yanlış namespace 403 verir; istemcinin serbest origin/actor JSON'u kullanılmaz. G7'nin başlıksız istemcileri kendi mevcut sunucu aktör korumasıyla uyumlu kalır.

Yalnız `http://127.0.0.1[:port]` ve `http://localhost[:port]` kök URL'leri kabul edilir. Userinfo, query, fragment, uzak host ve alt path reddedilir. Ortam proxy'leri ve HTTP yönlendirmeleri kullanılmaz; Authorization başka hedefe yönlendirilemez. Varsayılan timeout 5 saniye, normal deneme sayısı 2'dir; timeout .1–30 saniye, deneme sayısı 1–3 ile sınırlıdır. İstek en fazla 64 KiB, JSON yanıtı en fazla 4 MiB'dir; HTML, duplicate JSON key, NaN/Infinity ve geçersiz Unicode kabul edilmez.

```python
import os
from pathlib import Path
from agentrader.integration.chart_bot import ChartBot

bot = ChartBot(
    "http://127.0.0.1:8765",
    os.environ["AGENTRADER_CHART_BOT_TOKEN"],
    bot_id="chart-bot", strategy_id="default", workspace_id="main",
    journal=Path("data/chart-bot-journal.sqlite3"),
)
catalog = bot.discover()
context = bot.snapshot("BTCUSDT", "15m")
# geometry stratejinin ürettiği, katalogdaki desteklenen geometri gövdesidir.
item = bot.create("signal-123-create", geometry)
note = bot.save_note("signal-123-note", item["drawing_id"], 0, item["revision"], "Açıklama 🧭\nİkinci satır")
```

Bu örnek çalıştırma talimatıdır; G8 uygulaması gerçek kullanıcı ortamında bu anahtarları oluşturmaz, `.env` dosyasını değiştirmez veya sunucuda bot modunu kendiliğinden açmaz.

## Adaptör yüzeyi

| Metot | Davranış |
| --- | --- |
| `identify()`, `discover()` | Sunucu aktörü/namespace ve gerçek HTTP yetenek kataloğu |
| `snapshot(symbol, interval, ...)` | Açık piyasa seçimiyle G2 bağlamı; isteğe bağlı `ui_session_id`, sayfa ve `expected_context_id` |
| `find_own(symbol, interval)` | Fresh, aynı context_id ile devam eden sayfalardan yalnız kendi bot+strateji nesneleri; restart sonrası journal'a bağımlı olmadan keşif |
| `get(id)`, `notes(id, revision_number=0)`, `history(id, ...)` | Aynı workspace'teki manuel/bot nesnelerinin resmi HTTP okuması |
| `calculate(id, expected_revision, operation, inputs, *, symbol, interval, ...)` | G3 sayısal sorgusu; READY ve engel sonuçlarını aynen taşır |
| `indicator_queries(symbol, interval, queries, ...)` | G5 dokuz gösterge slotunun resmi sorguları |
| `create(key, geometry)` | Yeni bot nesnesi; yeni nesne için beklenen önceki revizyon sıfırdır, resmi POST şeması yeni kimlik/revizyon 1 üretir |
| `update(key, id, expected_revision, geometry)`, `delete(key, id, expected_revision)` | Mevcut nesnede açık revizyonla yazma |
| `save_note(key, id, expected_revision, expected_drawing_revision, text)`, `delete_note(...)` | Not ve çizim revizyonunu birlikte doğrulayan G7 işlemleri |
| `operations(key, operations)` | En fazla 20 create/edit/delete/management işlemini atomik HTTP bulk olarak gönderir; her hedefin revizyonu ayrı belirtilir |
| `resume_pending()` | Aynı endpoint/namespace/workspace journal'ındaki belirsiz niyetleri aynı gövde/request ID ile tekrarlar |

Adaptör yazmadan önce sahipliği fresh HTTP okumasıyla denetler; revizyonu otomatik yükseltmez veya çatışmada yeniden tabanlamaz. Manuel, farklı bot/strateji ve farklı workspace nesnesine yazma reddedilir. Sunucunun transaction içindeki G7 denetimi ayrıca korunur; adaptörü atlayıp HTTP çağrısı yapmak manuel korumayı aşmaz. Kendi nesnesindeki kilit de sunucuda uygulanır.

Sayısal sorgularda sembol/interval ve gerekli sorgu zamanı açık verilir. Hover örtük varsayılan değildir. Kaynak uyuşmazlığı, eski revizyon, eksik veri, WARMUP veya display-only araç sonucu sıfıra/başarıya çevrilmez. Üç annotation varyantının sayısal sorgusu beklenen UNSUPPORTED_OPERATION'dır; ham geometri ve notları okunabilir.

## Kalıcı niyet ve tekrar sözleşmesi

Her yazmada çağıran sabit bir iş anahtarı verir. Anahtar 1–128 karakterdir; whitespace/control ve geçersiz Unicode içeremez. Namespace + workspace + anahtar deterministik, en fazla 64 karakterlik sunucu request ID'sini oluşturur. Beklenen revizyonlar ve tam gövde ağ çağrısından önce ayrı SQLite journal'a kaydedilir. Journal scope'u canonical endpoint, bot namespace ve workspace'i içerir.

| Journal durumu | Anlam |
| --- | --- |
| `PENDING` | Niyet kalıcı; henüz doğrulanmış sonuç yok. Timeout, ulaşım hatası, 429/5xx veya bozuk/uyuşmayan başarılı ACK bu durumda kalır |
| `SUCCEEDED` | Sunucu ACK'si kimlik/workspace/revizyon ve işlem sonucu açısından doğrulanıp kalıcı kaydedildi |
| `REJECTED` | 403/409/423 gibi kesin ret; aynı anahtar tekrarında aynı ret verilir. Yeni revizyonla yeni niyet için yeni anahtar gerekir |

Aynı anahtar + farklı işlem/gövde yerelde `409 OPERATION_KEY_CONFLICT` verir. Sunucunun actor-bound request ID/digest denetimi de ikinci sınırdır. Aynı niyet iki süreçten eşzamanlı gönderilse bile sunucu tek nesne/revizyon üretir. Yanıt alındıktan sonra journal sonucu yazılamazsa hata belirsiz/PENDING olarak bildirilir. Yeni kimlikle otomatik telafi oluşturma yapılmaz.

Tamamlanmış niyet tekrarında journal'daki tarihi ACK dönebilir; yanıttaki `adapter.replayed=true` bunu açıklar. Bu, nesnenin güncel halinin kanıtı değildir: güncel çizim/not için `get` veya fresh `snapshot` kullanılmalıdır. Sunucunun `duplicate` alanı sunucudaki tekrarı, `adapter.replayed` yerel cache tekrarını anlatır. Bütün adapter metadata'sında emir yetkisi false'tur.

Restart toparlanması aynı journal ve aynı canonical endpoint ile yapılır. Endpoint/workspace/namespace değişirse eski PENDING işlemler başka hedefe otomatik taşınmaz. Sunucu DB'si değiştirilmişse eski ACK'ler güncel nesneler varsayılmaz. `resume_pending` ilk hatada durur; önce tamamlanan niyetler SUCCEEDED kaldığından sonraki tekrar onları yeniden yazmaz. Kör workspace silme veya manuel nesne temizleme metodu yoktur; temizlik açık bot kimlikleri ve güncel beklenen revizyonlarla yapılır.

Journal `application_id` ve sürüm işaretiyle ayrı bir dosyadır. Uygulama/işlem DB'si yanlışlıkla journal olarak verildiğinde değişiklik yapmadan reddedilir. FULL synchronous ve SQLite transaction'ları kullanılır. Token/Authorization otomatik journal'a yazılmaz; niyet gövdeleri ve sonuçları saklanır. Tamamlanmış niyetler idempotency için korunur; otomatik journal budama eklenmedi.

## CLI

```powershell
python -m agentrader chart-bot --journal data/chart-bot-journal.sqlite3 identity
python -m agentrader chart-bot --journal data/chart-bot-journal.sqlite3 discover
python -m agentrader chart-bot --journal data/chart-bot-journal.sqlite3 snapshot BTCUSDT 15m
python -m agentrader chart-bot --journal data/chart-bot-journal.sqlite3 own BTCUSDT 15m
python -m agentrader chart-bot --journal data/chart-bot-journal.sqlite3 run task.json
python -m agentrader chart-bot --journal data/chart-bot-journal.sqlite3 resume
```

`run` dosyası yalnız `action` ve `arguments` alanlarını içerir. Action allowlist'i yukarıdaki çizim/not/hesap okuma-yazma metotlarıdır; keyfî URL, komut, hesap veya emir çağrısı yoktur. Örneğin not görevi:

```json
{"action":"save_note","arguments":{"key":"signal-123-note","drawing_id":"explicit-owned-id","expected_revision":0,"expected_drawing_revision":1,"text":"Açıklama"}}
```

CLI çıkışları: başarı 0, kesin ret 1, belirsiz/PENDING 2. Başarılı bir sorgu çağrısının üst `SUCCEEDED` durumu HTTP/adaptör çağrısının tamamlandığını anlatır; matematiksel kullanılabilirlik için her `results[].state` ayrıca kontrol edilmelidir. Hata çıktısı yalnız yapılandırılmış kod ve HTTP status taşır; token veya Authorization yazdırılmaz. `Config.load()` / borsa hesabı hazırlığına girilmeden ayrı chart-bot alt komutuna yönlendirilir.

## Kabul kapsamı

`python scripts/integration/check_g8_chart_bot.py`: gerçek üretim adaptörü + ayrı CLI süreci, gerçek loopback HTTP/SQLite ve üretim frontend. Açık sentetik fixture donmuş saatle 300 mum sunar; piyasa network/subscription oluşturma yolu kapalıdır. 25 varyant create/not/fresh snapshot/edit; 22 READY + 3 beklenen display-only engeli; commit sonrası yanıtı taşıma sınırında düşürme, gerçek sunucu restart, pending resume, namespace/source/manuel koruma ve yalnız bot nesnelerini temizleme kontrol edilir. Kullanıcı undo kullanılabilirliği ve manuel nesne/not/profil/workspace hashleri önce/sonra eşleşir.

Bu paket G3/G4/G5'in bağımsız matematik kabulünün yerine geçmez. Adaptörün gerçekten o HTTP yollarını kullandığını ve sonuç/engel bilgisini taşıdığını kanıtlar; çizimlerin bütün piksel projeksiyonunu yeniden test etmiş gibi sunulmaz. [G8 raporu](../../reports/chart-interface-g8-20261115/README.md).
