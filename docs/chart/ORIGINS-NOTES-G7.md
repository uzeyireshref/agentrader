# G7 — Nesne kökeni, manuel koruma ve bağlı notlar

G7, mevcut çizim geometri şemalarını değiştirmeden sunucu aktörü, değiştirilemeyen köken, revizyon izi ve hedefe bağlı uzun not ekler. Otonom bot adaptörü G8 kapsamındadır. Bu uçlar piyasa kanıtı veya emir yetkisi üretmez.

## Aktör ve yetki sınırı

Yerel kullanıcı modu mevcut localhost/Origin güven sınırını korur. Bot modu sunucuda ayrı `AGENTRADER_CHART_BOT_TOKEN` ile etkinleşir. Bu durumda ayrı `AGENTRADER_WEB_TOKEN` da zorunludur; iki anahtar aynı olamaz. Anahtarlar 32–256 güvenli karakter içerir. Bot ve strateji kimlikleri yalnız sunucudaki `AGENTRADER_CHART_BOT_ID` / `AGENTRADER_CHART_STRATEGY_ID` ayarlarından alınır. Varsayılanlar `chart-bot` / `default`; bot anahtarı varsayılan olarak kapalıdır. Ayarlar process environment üzerinden yüklenir; bu paket kullanıcı `.env` dosyasını değiştirmez veya işlem anahtarı yüklemez.

| Aktör | Okuma | Yazma |
| --- | --- | --- |
| Yerel kullanıcı | Kendi owner alanı | Mevcut çizimler; bot modunda kullanıcı Bearer veya HttpOnly eşleştirme çerezi zorunlu |
| Doğrulanmış bot | Aynı owner kapsamındaki manuel/bot nesneleri, notlar, geçmiş, bağlam ve açıkça seçilen UI oturumu | Yalnız kendi bot+strateji kimliğiyle oluşturduğu nesneler ve onların notları |
| Başka owner | Çizim/not bulunamadı | Yetki yok |

Bot kimliği `Authorization: Bearer <ayrı bot anahtarı>` üzerinden doğrulanır. Serbest JSON origin/actor/bot_id/strategy_id alanları kabul edilmez; başlıklardaki aktör iddiaları kullanılmaz. Bot modunda anahtarsız yazma 401 döner. Kullanıcı anahtarı veya kullanıcı çereziyle çalışan yazılım kullanıcı yetkisine sahiptir; aynı işletim sistemi kullanıcısının DB erişimi ve kullanıcı anahtarının ele geçirilmesi bu bot rol sınırının dışındadır. Bot anahtarı kullanıcı oturumu oluşturamaz veya finansal/komut/onay uçlarına erişemez.

`DrawingActor` güvenilen Python servis çağrıları içindir; HTTP bunu doğrulanmış kimlikten üretir. Bot aktörünü seçen servis, `_assert_edit` korumasını her mevcut nesne mutasyonunda transaction içinde uygular. Manuel/legacy nesnede ve farklı bot/stratejide `403 DRAWING_ORIGIN_PROTECTED` döner. Geometri güncelleme, silme/restore, management/stil/kilit ve toplu undo/redo aynı denetimi kullanır. Karma bulk içindeki tek korunan nesne bütün işlemi geri aldırır. Kilit kendi nesnesinde de geometri/not düzenlemesini engeller; mevcut açık kilit çözme işlemi ayrıca revizyon denetimlidir.

Bot için profil/şablon import/restore ve diğer genel yazma yolları HTTP allowlist dışında bırakılır. Aynı sınır `ProfileService` bot aktörünün `_mutation` yolunda da vardır. Yeni kimlikle kopya oluşturmak mümkündür; kopya botun yeni nesnesidir, kaynak manuel nesnenin kimliği/kökeni/notları değişmez. İstemci rastgele geometriyle yeni nesne oluşturabilir; eski kimliğin bot kökenine dönüştürülmesi için bir API yoktur. Origin immutable kalırken kullanıcı bot nesnesini düzenleyebilir; son değişikliği yapan aktör ayrıca kaydedilir.

## Köken ve revizyon izi

Her çizim okumasında şu ek alanlar bulunur:

- `origin`: `schema=drawing-origin/1`, `kind=manual|bot`, `source=legacy|user|bot`, `actor_id`, `bot_id`, `strategy_id`, `created_at`.
- `change`: çizim revizyonu ve sunucunun doğruladığı `updated_by` aktörü. Çizimin `updated_at` alanı korunur.
- `linked_note`: ayrı not kaydı veya `revision=0`, `state=EMPTY`.

`GET /api/drawings/{drawing_id}/history?limit=50&offset=0` revizyon, zaman, silinme ve değişikliği yapan aktör listesini döndürür. Limit 1–100, offset en fazla 1.000.000'dur. Origin owner+nesne kimliğine bağlıdır ve create/bulk/undo/redo/profil stil restore sırasında yeniden yazılmaz. Bot idempotency digest'i sunucu aktörünü de içerir; insanın önceki request ID'sini kullanarak önbellekten başarılı yazım sonucu alınamaz. Mevcut manuel idempotency digest'leri değiştirilmez.

## Bağlı uzun not HTTP sözleşmesi

Her çizimin en çok bir mantıksal bağlı uzun notu vardır; notun ayrı `note_id` ve artan revizyonları bulunur. Geometri içindeki mevcut label/text/note/channel text aynen kalır. Not eklemek çizim revizyonunu veya takip kuralını değiştirmez.

| İşlem | Uç ve gövde |
| --- | --- |
| Oku | `GET /api/drawings/{drawing_id}/notes` |
| Eski not revizyonunu oku | `GET /api/drawings/{drawing_id}/notes?revision=1` |
| Kaydet/güncelle | `PUT /api/drawings/{drawing_id}/notes`: `request_id`, `expected_revision`, `expected_drawing_revision`, `text` |
| Mantıksal sil | `DELETE /api/drawings/{drawing_id}/notes`: `request_id`, `expected_revision`, `expected_drawing_revision` |

Örnek gövde:

```json
{"request_id":"note-001","expected_revision":0,"expected_drawing_revision":3,"text":"Uzun açıklama 🧭\nİkinci satır"}
```

İki revizyon da transaction içinde denetlenir. Eski çizim veya not revizyonu 409 döndürür; aynı anda iki yazardan biri kazanır. Aynı request ID + aynı gövde timeout sonrası tekrarlandığında aynı not revizyonu döner; farklı içerik 409 verir. PUT üst sınırı 24 KiB istek, 4000 Unicode code point / 16000 UTF-8 bayt metindir. LF/CR/TAB korunur; diğer C0/DEL ve geçersiz Unicode reddedilir. Bilinmeyen gövde alanları kabul edilmez. Not revizyonu 0–1.000.000.000 ile sınırlıdır.

Yanıtta `target_revision` mevcut hedefi, `saved_target_revision` bu not revizyonu yazılırkenki hedefi gösterir. `updated_by` not yazan aktördür. Not geçmişi ayrı tutulur; çizim undo/redo işlemi notu eski geometriyle yanlışlıkla yeniden yazmaz. Frontend not kaydı yalnız ilişkili metadata'yı yeniler; çizim seçimi, geometri ve undo/redo yığınları korunur. Kayıp yanıt tekrarında aynı request ID kullanılır. Yeni hedef/revizyon geldiyse eski async yanıt yeni taslağın üzerine yazamaz.

Hedef silinirse not `TARGET_ARCHIVED` olur; içerik ve geçmiş salt okunur korunur, düzenleme 403 verir. Kullanıcının yetkili restore işlemi aynı hedef kimliğini canlandırırsa not aynı not revizyonuyla tekrar ACTIVE olabilir. Notun kendisi silinirse `NOTE_DELETED` durumu ve eski içerik revizyon izi için tutulur; bu fiziksel veri silme değildir. Geçmiş endpoint'i de güncel hedefin arşiv durumunu taşır.

G2 `objects` ve G3 başarılı geometri sorguları origin/change/linked_note taşır. Not revizyonu değişince çizim revizyonu aynı kalsa da `context_id` değişir; bağlam öncesi/sonrası kontrolü eski not ile yeni nesne bağlamını birleştirmez. Not metni gösterge veya geometri hesabının girdisi yapılmaz. Katalog linked-note read/write ve history uçlarını yalnız gerçek çizim kayıtları için ilan eder; uygulanmamış araçlar uygulanmış gibi gösterilmez.

## Migration 13 ve geri dönüş

Migration mevcut geometri/revizyon/head/request tablolarını yeniden yazmaz. `app_drawing_origins`, `app_drawing_audit` ve `app_drawing_notes` eklenir. Mevcut her nesne `manual/legacy` ve ilk revizyonun oluşturma zamanı ile backfill edilir; eski her geometri revizyonu legacy manuel aktörle audit alır. Origin için UPDATE/DELETE koruma trigger'ları vardır. Eski metinler dönüştürülmez veya yeni not alanına taşınıp kaybedilmez.

Mevcut sürümlü store yükseltilmeden hemen önce mevcut migration mekanizması SQLite backup API ile `<db>.before-v13-<id>.bak` oluşturur; yazıcılar migration transaction'ı boyunca engellenir. Yeni boş store'da önceki kullanıcı verisi olmadığından bu yedek gerekmez. Migration atomiktir; hata bütün v13 değişikliklerini geri alır. Önceki migration checksum'ları ve Demo store kimliği korumaları devam eder; ayrı kalması gereken legacy store otomatik Demo store olarak benimsenmez.

Geri dönüş yolu izole testte doğrulanmıştır: sunucu/yazıcılar kapatılır, güncel store ayrıca korunur, v13 öncesi yedek çalışma DB'sine kopyalanır ve v12 uyumlu uygulama sürümüyle açılır. Bu işlem v13 sonrasında yapılan değişiklikleri o kopyada geri alır; daha yeni store üzerinde eski migration kodu çalıştırmak geri dönüş değildir ve reddedilir. Gerçek kullanıcı DB'sine bu kabul sırasında migration veya geri yükleme uygulanmadı.

Kabul: `python -m pytest -q tests/test_drawing_origins_notes.py`, `npm test`, `python scripts/integration/check_g7_origins_notes.py`. [G7 teslim raporu](../../reports/chart-interface-g7-20261115/README.md).
