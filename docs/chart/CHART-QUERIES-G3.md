# G3 — Tekil ve toplu HTTP geometri sorguları

15 Kasım 2026. İstek schema_version=chart-query-request/1; yanıt schema_version=chart-query-response/1, calculation_version=chart-geometry-http/1.

G4 güncellemesi: sekiz kanal/pitchfork varyantı ve bu şemadaki LOG hesapları açılmıştır; [G4 matematik sözleşmesi](CHANNEL-MATH-G4.md) geçerlidir. Aşağıdaki kapalı destek sayıları G3 teslimindeki duruma aittir.

## Uçlar ve istek

POST /api/workspaces/{workspace_id}/chart-queries gövdesi:

~~~json
{
  "schema_version": "chart-query-request/1",
  "context": {"symbol":"BTCUSDT", "interval":"15m"},
  "queries": [{
    "query_id":"q1", "drawing_id":"<nesne kimliği>", "expected_revision":1,
    "operation":"priceAt", "inputs":{"time":1800258300}, "scale":"LINEAR"
  }]
}
~~~

POST /api/drawings/{drawing_id}/queries aynı zarfı kullanır; queries listesi yerine query nesnesi vardır ve query içinde drawing_id bulunmaz. Çalışma alanı ancak owner kapsamındaki nesne okunduktan sonra belirlenir. query_id 1–64 ASCII harf/rakam/alt çizgi/tire olmalı; toplu istekte benzersizdir. expected_revision zorunludur. scale varsayılan LINEAR; başka ölçek şu aşamada UNSUPPORTED_SCALE verir.

context alanında symbol/interval zorunludur. İsteğe bağlı source/environment/product/price_type, required_closed_bars, include_open ve expected_context_id G2 ile aynı anlamdadır. Önceki GET chart-context çıktısına bağlamak için aynı seçimle expected_context_id gönderilir. Kaynak Demo kimliğiyle eşleşmelidir. İstemci mum dizisi, tick_size, serbest geometri veya piyasa kanıtı gönderemez; bunlar sunucunun mevcut feed'inden alınır. Yeni feed, geçmiş indirme veya emir yetkisi başlatılmaz.

## Keşif ve destek

GET /api/chart-tools veya şema seçen tekil keşifte features.geometry_query, access.geometry_query (POST /api/drawings/{drawing_id}/queries), http_batch_query_path ve http_geometry_operations kullanılır. Aynı kind'in eski/yeni kayıt şeması ayrı değerlendirilir.

- Horizontal/horizontal ray: priceAt, distance.
- Trend/ray/extended line: priceAt, distance.
- Eski/yeni zone: contains, distance.
- Eski/yeni Fibonacci ve extension: level.
- Eski chart-channel/1 paralel kanal: boundsAt, contains, distance.
- Ruler: measurement.
- Long/short plan: riskReward.

Toplam 14 kayıt varyantı. Sekiz chart-channel-family/1 varyantının backend matematiği G4'e kadar kapalıdır; genel uç bunlara gerekçeli UNSUPPORTED_OPERATION döndürür. Text/note/price_label içerik/konum okumaları mevcut CRUD/contract/context üzerindedir; matematik işlemi verilmez. Fibonacci projection G9'a kadar uygulanmamış kalır.

priceAt/boundsAt için inputs.time; distance/contains için inputs.time + inputs.query_price; level için inputs.time + inputs.ratio gerekir. measurement/riskReward için inputs={} kullanılır. Fazladan veya eksik girdi reddedilir. time tam sayı UTC saniyedir: milisaniye veya ondalıklı saniye reddedilir. query_price ve ratio en çok 128 karakter decimal metindir; sayısal JSON fiyatı kabul edilmez. Fiyat tick'e yuvarlanmaz.

## Veri hazırlığı ve hesap kapsamı

Çizgi/eski kanal grid hesapları ile cetvel, sunucunun doğrulanmış veri snapshot'ı READY olduğunda çalışır. Varsayılan kapalı mumlar kullanılır; açık mumu kapsayan sorgu için include_open=true açıkça belirtilmelidir. Yüklenmemiş veya kapalı grid dışında kalan zaman GRID_OUT_OF_RANGE ile WAITING_FOR_DATA dönebilir; sahte mum üretilmez.

Horizontal, horizontal ray, zone, Fibonacci ve plan aritmetiği nesnenin geometrisinden hesaplanır. Veri yok/stale olsa da sonuç READY olabilir; data_consumed=false ve scope=GEOMETRY_NOT_ORDER_ELIGIBILITY bunu açıkça ayırır. Üst readiness mevcut piyasa durumunu aynen gösterir. Kaynak uyuşmazlığı veya bozuk snapshot altında hesap yapılmaz. Geometri sonucu hiçbir zaman emir yetkisi vermez.

Her başarılı sonuç query_id, drawing_id, kullanılan revision/geometry_schema, operation, istenen inputs/scale, result, data_consumed ve kullanıldıysa consumed_range/consumed_data_hash taşır. Üst yanıt market, context_id, data_identity, server_utc, gösterge ayar revizyonu, readiness ve başarı/hata sayısını içerir. Gösterge hesapları bu teslimde açılmaz.

## Sayı anlamı

Mevcut saf hesap handler'ı kullanılır; numerator/denominator tam kesri korur. Sonlu decimal mümkünse decimal alanı da doludur; devreden kesirde decimal=null, tam kesir geçerlidir ve number_encoding bunu belirtir. Risk bütçesi gibi opsiyonel girdiden türeyen tanımsız çıktılar undefined_outputs listesinde açıkça görünür. Cetvelin eksik bar ölçümü mevcut state/reason alanıyla döner. NaN/Infinity, fiyatı gösterim için yuvarlama veya sessiz sıfır başarı eklenmez.

## Hatalar, tutarlılık ve sınırlar

Tekil/toplu aynı servis ve hesap hata kodlarını kullanır. Toplu yanıt HTTP 200 içinde her sonuç için state/http_status/error.code taşır; bir nesnenin hatası diğer sonuçları gizlemez. Tekil uç satırın durum kodunu HTTP durumuna da taşır. Genel istek/bağlam hatası mevcut {error:{code}} zarfını kullanır.

- UNSUPPORTED_OPERATION (422): UNSUPPORTED_QUERY veya UNSUPPORTED_SCALE.
- INVALID_INPUT (422): alanlar, fiyat/zaman/oran, kapsam veya geometri girdisi uygun değil.
- WAITING_FOR_DATA / WARMUP / STALE / SOURCE_MISMATCH (422): gerekçeli veri/bağlam engeli.
- REVISION_CONFLICT (409): DRAWING_REVISION_CONFLICT.
- NOT_FOUND (404): DRAWING_NOT_FOUND; başka owner/workspace ve silinen hedef aynı sınırı izler.
- Genel CONTEXT_CHANGED (409): önceki context_id veya hesap sırasında değişen nesne/veri. Eski hesaplar yeni snapshot'la birleştirilmez; tüm yanıt reddedilir.
- Genel CONTEXT_READ_TIME_LIMIT (503) ve CHART_QUERY_OUTPUT_LIMIT (413).

İstek sınırı tekilde 8192 byte, topluda 65536 byte; toplu liste 1–50 sorgu; toplam sorgu süresi 2 saniye, UTF-8 yanıt sınırı 262144 byte. Gövde okuyucu yinelenen JSON alanlarını ve NaN/Infinity sabitlerini reddeder. Hesaplar event loop'u bekletmemek için worker thread'de çalışır; deadline istek kapsamında kalır.

G2 ile aynı read-only bağlantılar ve owner/local host/origin sınırı kullanılır. Önce tutarlı snapshot alınır, revision bağlı hesaplar yapılır, yanıt dönmeden aynı context_id tekrar doğrulanır. Query nesnesi ilk sayfa dışında olsa da owner kapsamındaki doğrudan head okuması kullanılır; snapshot sayfalama limiti hesap erişimini daraltmaz. Hiçbir sorgu kullanıcı nesnesini, ayarını veya emir deposunu yazmaz.

## Kabul

Gerçek HTTP istemcisi, gerçek FeedState ve izole SQLite ile 14 varyantta tekil/toplu eşitlik, tam kesir referansları, ara UTC, maliyetli risk/ödül, 25 araç için doğru yetenek keşfi, manuel kayıtların byte/hash değişmezliği ve hata/limit/yarış senaryoları sınanır. Bu G3 API kabulüdür; gerçek bot adaptörü ve Demo runtime gözlemi G8/G11 kapsamındadır.
