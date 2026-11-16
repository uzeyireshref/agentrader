# G1 — Grafik aracı erişim sözleşmesi

15 Kasım 2026. Sözleşme: chart-tool-access/1. Ana registry/contract şemaları /1 kalır; alanlar geriye uyumlu eklenmiştir.

## Keşif

GET /api/chart-tools bütün türleri ve record_variants listesini döndürür. GET /api/chart-tools/{category}/{kind}?record_schema=... tek kayıt şemasını seçer. Bilinmeyen tür/sürüm/şema mevcut BLOCKED_UNSUPPORTED_TOOL hatasıyla 422 verir. Parametre verilmezse önceki şema seçimi korunur; yeni istemciler preferred_write_schema ve record_variants kullanmalıdır. Paralel kanalın varsayılan eski seçimi chart-channel/1, önerilen güncel yazımı chart-channel-family/1'dir. Nesnenin /contract yanıtı gerçek kayıt şemasını seçer.

## Alanların anlamı

- features: metadata_read, text_read, geometry_query, indicator_series, ui_state_read, create, edit, delete için uygulanmış HTTP erişim bayrakları.
- access: aynı özelliklerin IMPLEMENTED / NOT_IMPLEMENTED / NOT_APPLICABLE durumu, gerekçesi, HTTP method ve path şablonu. Bu yollar normal kullanıcı doğrulaması, sahiplik, kilit ve revizyon politikasına tabidir; yeni bot yazma yetkisi vermez.
- record_schema ve format_version: ilgili CRUD isteğinde kullanılacak şema ve minimum format_version sorgu parametresi. Dönen nesnenin stil/yönetim özellikleri daha yeni format gerektirebilir; tüm çizimler için mevcut en güncel sürüm 9 kullanılabilir.
- text_fields: doğrudan okunabilen label/text alanları. related_notes=false; her çizime bağlı uzun notlar G7'de geliştirilecek.
- python_geometry: gerçekten çalışan Python handler, işlemler, required_inputs, required_context ve supported_scales. İsimler calculations.query argümanlarıdır: time UTC saniye; query_price/ratio/tick_size decimal metin; times mum başlangıçları. İstatistiksel hazırlık ve veri tutarlılığı G2 ve sonraki paketlerde ayrıca ele alınacak.
- http_geometry_operations / http_indicator_operations: şu anda boş. Python hesap desteği genel HTTP hesaplama desteği sayılmaz.
- data_requirements ve optional_context: örneğin trend/ray/eski kanal için times+interval; cetvel için tick_size+interval, isteğe bağlı times. Cetvelde grid olmadan mum sayısı UNAVAILABLE olur.
- readable/editable/computable/canonical_queries: önceki kayıt ve Python kütüphanesi anlamlarıyla uyumluluk için korunur. HTTP hesap keşfinde bu eski alanlar kullanılmamalı; registry legacy_flags_scope bunu açıklar.

## Mevcut kapsam

25 çizim varyantı: 14 varyant Python matematiği sunar; 8 kanal ailesi varyantının backend hesabı G4'e kadar kapalıdır; 3 metin aracı matematiksel sorgu sunmaz. LINEAR Python hesapları desteklenir, LOG hesapları reddedilir. Tarayıcının log görüntüleme politikası ayrı scale_policy alanında kalır.

Gösterge metadata_read/edit, chart-indicators/4 yapılandırmasının GET/PUT işlemleridir. Sabit dokuz gösterge yuvası vardır; create/delete ve hesaplanmış indicator_series sunulmaz. enable/disable ve parametre değişimleri edit kapsamındadır. UI oturumu erişimi henüz yoktur. Fibonacci projection NOT_IMPLEMENTED kalır ve uygulanmış hiçbir erişim bayrağı taşımaz.

G2 güncellemesi: salt okunur chart-context ucu artık uygulanmıştır; [G2 sözleşmesi](CHART-CONTEXT-G2.md) geçerlidir. Aşağıdaki liste G1 teslimindeki durumu kaydeder.

G3 güncellemesi: 14 matematiksel kayıt varyantı için geometry_query ve http_geometry_operations artık uygulanmıştır; [G3 sözleşmesi](CHART-QUERIES-G3.md) geçerlidir. Yukarıdaki boş HTTP listesi açıklaması G1 teslimindeki duruma aittir.

G5 güncellemesi: dokuz yapılandırma için indicator_series ve series/latest/at HTTP erişimi açılmıştır; [G5 sözleşmesi](INDICATOR-QUERIES-G5.md) geçerlidir. Gösterge serisi yok açıklamaları G1 teslimindeki duruma aittir.

## Kesinleştirilen sonraki yollar

Aşağıdakiler bu teslimde uygulanmış değildir; access içinde varmış gibi ilan edilmez:

- G2: GET /api/workspaces/{workspace_id}/chart-context
- G3: POST /api/workspaces/{workspace_id}/chart-queries ve POST /api/drawings/{drawing_id}/queries
- G5: POST /api/workspaces/{workspace_id}/indicator-queries
- G6: PUT /api/workspaces/{workspace_id}/ui-sessions/{ui_session_id} ve GET /api/workspaces/{workspace_id}/ui-sessions

Yazma mevcut drawings/drawing-operations yollarında kalır. G2/G3 yanıtları schema_version/context_id, UTC sunucu zamanı, kaynak ve revizyon kimliği, açık hazırlık durumu taşımak üzere plan 46'daki sözleşmeyi izler.

## Kanıt

Yeni test_chart_tool_access.py, 25 varyantın keşfedilen şema/sürümüyle gerçek HTTP CRUD, contract şema seçimi, metin alanları ve ilan edilen Python işlemlerini sınar. LOG reddi, bilinmeyen şema, eski/yeni paralel ayrımı, gerçek OpenAPI handler eşleşmesi, gösterge GET/PUT ve sonuçların bağımsızlığı ayrıca doğrulanır. Hesapların bağımsız sayısal doğruluğu mevcut araç testlerinde korunur; bu test yeni matematik uygulandığı iddiası değildir.
