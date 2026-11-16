# G2 — Ortak salt okunur grafik bağlamı

15 Kasım 2026. GET /api/workspaces/{workspace_id}/chart-context. Yanıt schema_version=chart-context/1, calculation_version=chart-context-readiness/1.

## Kaynak ve çalışma alanı

Çizimler, gösterge ayarları ve kaydedilmiş profil mevcut owner/workspace sınırlarıyla okunur. symbol ve interval verilmezse kaydedilmiş workspace tercihi kullanılır; ilk çalışma alanında BTCUSDT/15m varsayılanı vardır. İstenirse açık symbol/interval seçilir. source/environment/product/price_type yalnız mevcut Binance Demo kimliğiyle eşleşebilir; farklı talep 422 SOURCE_MISMATCH üretir. Hub'ın getirdiği kimlik uyuşmazsa 200 yanıtta veri hazırlığı SOURCE_MISMATCH olur ve güvenilir veri kimliği/kanıtı sunulmaz.

Nesnelerin intervali kalıcı geometriye bağlı değildir. object_interval_binding=NOT_BOUND_TO_INTERVAL bunu açıkça bildirir. Aynı sembolün manuel çizimleri başka intervalde de okunabilir; sayısal hesap bundan otomatik olarak türetilmez.

## Yanıt alanları

- market: etkin Demo kaynak/ortam, ürün, fiyat türü, sembol ve interval.
- workspace: kaydedilmiş tercih ve revizyonu; açık sorgu seçimi market alanındadır.
- objects: en güncel ham çizim kayıtları, ID/revizyon, geometri, mevcut label/text ve management. Fiyatlar orijinal decimal metin olarak korunur. Yeni köken/not ilişkisi üretmez.
- indicators: chart-indicators/4 ayarları ve workspace/gösterge revizyonları. Seri veya gösterge son değeri hesaplanmaz.
- persistent_view: kaydedilmiş profil ve revizyonu. Tarayıcının o anki görünümü değildir.
- derived.readiness: sadece veri snapshot hazırlığı. READY strateji uygunluğu veya emir yetkisi değildir.
- data_identity: stream_epoch, generation, sequence, data_revision. Veri yoksa veya kimlik/geçerlik reddedilmişse null.
- ui: UI_UNAVAILABLE; oturum köprüsü G6 kapsamında.
- context_id, server_utc, time_units, consistency, pagination ve order_authority=false.

## Veri hazırlığı

Sunucunun zaten abonelik bulunan MarketFeedHub.binding_context verisi kullanılır. İstek yeni subscription, REST isteği, websocket, geçmiş indirmesi veya mum kaydı başlatmaz. Tarayıcı kapalıysa başka mevcut sunucu tüketicisi varsa veri yine okunabilir; aktif feed yoksa kalıcı nesneler/ayarlar korunur ve WAITING_FOR_DATA/NO_ACTIVE_FEED döner. Bu uç nokta tek başına sürekli piyasa izleme aboneliği değildir.

Veri kimliği karşılaştırılır, mevcut kanıt sunucudaki aynı mumlardan tekrar doğrulanır. Kaynak saat kanıtı ve transport durumu kullanılır; duvar saatinin tek başına fiyat tazeliği kanıtı olduğu varsayılmaz.

- READY: doğrulanmış, kesintisiz, taze snapshot ve istenen sayıda kapalı mum.
- WARMUP: yetersiz ardışık kapalı mum; değer sıfır gibi sunulmaz.
- WAITING_FOR_DATA: aktif feed yok, veri boşluğu, kanıt uyuşmazlığı veya doğrulanmamış veri.
- STALE: transport LIVE değil, saat güvenilmez veya mevcut zaman kanıtı taze değil.
- SOURCE_MISMATCH: veri kimliği istenen bağlamla farklı.
- INVALID_INPUT: sunucu snapshot şekli hesaplamaya uygun değil.

available_count, available_closed_count, warmup_available_closed_bars, required_closed_bars, missing_ranges, last_closed_candle, open_candle_present/open_candle_used, stale, source_clock, proof, consumed_range ve consumed_data_hash ayrı yayımlanır. required_closed_bars varsayılanı 2, sınırı 1–499'dur. Bu sayı gösterge bazında warmup kabulü değildir; gösterge hesap hazırlığı G5'te tanımlanacaktır. Loaded aralıktan önceki geçmiş UNKNOWN_BEFORE_LOADED_RANGE olarak işaretlenir.

include_open=false varsayılanında tüketilen aralık/hash yalnız kapalı mumları kapsar; açık mum durumu yine görünür. include_open=true açık mumu ayrıca dahil eder. proof.snapshot_hash hub'ın bütün yüklü snapshot'ına, consumed_data_hash seçilen alt kümeye aittir. Mum zamanları UTC saniye, sunucu zamanı ISO8601 UTC, saat süreleri milisaniyedir. Mum serisi bu yanıtta indirilmez.

## Tutarlılık ve sınırlar

Uygulama deposu mode=ro/query_only SQLite bağlantısında tek read transaction ile okunur. Feed kopyası farklı depodan geldiği için atomiklik iddia edilmez. Önce/sonra kalıcı revizyonlar (tombstone dahil), ayarlar/profil ve veri kimliği/kanıt/timing durumu karşılaştırılır. Değişimde en çok 3 okuma denemesi; ortak süre bütçesi 2 saniye. Sürekli değişimde 409 CONTEXT_CHANGED; süre aşımında 503 CONTEXT_READ_TIME_LIMIT. Değişken saat yaşları context_id'yi her istekte değiştirmez; stale geçişi ve saat hata durumu değiştirir.

limit varsayılan 100, en çok 200 çizim; offset 0–1000000. Sıra drawing_id'ye göre sabittir. Sayfa devamında expected_context_id zorunludur; ilk yanıttaki context_id aynen taşınır. Context değiştiyse 409 döner, eski sayfayla yeni nesneler sessizce birleştirilmez. Gösterge ayarları dokuz sabit yuva ile sınırlıdır. Yanıt çizim geçmişini veya bütün mum geçmişini döndürmez. İlgili nesne head'leri tutarlılık için taranır; büyük depoda aynı süre bütçesi uygulanır.

Mevcut yerel host/origin politikası uygulanır; bu yerel okumalar tek yapılandırılmış owner adına çalışır. Token gerektiren işlem uçlarına veya başka kullanıcıya erişim açılmaz. Yetki kontrolü gerektiren bot aktörü ayrımı G7 kapsamındadır.

## Örnek kullanım

İlk sayfa: GET /api/workspaces/main/chart-context?symbol=BTCUSDT&interval=15m&limit=100

Devam: aynı seçime offset=100&expected_context_id=<ilk context_id> eklenir. Aynı ID ayrıca sayfalama olmadan önceki snapshot'ın hâlâ geçerli olduğunu kontrol etmek için gönderilebilir.

G2 testi gerçek SQLite ve FeedState ile sentetik veride çalışır; kullanıcı depolarına veya borsaya erişmez. Salt okunurluk byte/hash kontrolü, kaynak/sahip/çalışma alanı sınırı, eksik geçmiş, açık mum, stale/saat hatası, reload/epoch, ayar revizyonu, sayfalama ve değişim yarışları sınanır. Gerçek Demo runtime gözlemi G11'in ayrı kabulüdür.
