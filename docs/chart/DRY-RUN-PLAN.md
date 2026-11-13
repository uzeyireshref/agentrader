# Grafik takip kuru çalışma planı

13 Kasım 2026 güncellemesi: [P7 izole yürütme tamamlandı](P7-ISOLATED-REPLAY-DELIVERY.md);36/36 senaryo ve20 tür/48 sorgu kontrolü geçti. Canlı entegrasyon kapalı; QA01/B5/fiziksel kabul açık. Aşağıdaki 10 Kasım taslağı tarihsel plan olarak korunur; güncel yürütme raporu ve açık DR01 amendment teslim belgesindedir.

10 Kasım 2026 — E4, `chart-dry-run/1.0-draft`. **Plan tamamlandı; strateji motoru/bağlantı uygulanmadı ve aşağıdaki senaryolar çalıştırılmadı.** [E3 veri sözleşmesi](BOT-DATA-CONTRACT.md) ve [makine okunur senaryolar](contracts/chart-dry-run-v1.json) birlikte geçerlidir. Tüm fiyat/eşik örnekleri sentetik doğrulama girdisidir, işlem tavsiyesi veya seçilmiş gerçek strateji parametresi değildir.

## İlk entegrasyon sırası

1. Önce E3 adapter kanıtları: exact decimal, epoch, clock/monotonic tazelik, kalite/geçmiş ve revision-bound bağ. Bugünkü LIVE paket bunları tek başına sağlamaz.
2. Yalnız kapalı mum, yaklaşma/temas, kalıcı temas durumu ve yerel gözlem raporu. Kapanış kırılım/retest örnekleri W5 kabul taslağıdır; W4 kapsamı büyütülmez.
3. Uygulama DB’sinde donmuş karar kanıtı, semantik event ve bildirim intent’ini aynı transaction’da yaz; head revision son kez karşılaştır.
4. Kalıcı checkpoint/idempotency ve restart/crash testleri; sonra sahte yerel sink ve kontrollü bildirim hataları.
5. E5 incelemesi/açık kabul işleri sonrası ayrıca izin verilirse gerçek kanal adapter’ı. Bu plan gerçek Telegram ile mesaj gönderme talimatı değildir. Hesap/emir yürütücüsü bağlanmaz.

## Yaklaşma/temas tanımı

Örnek yatay seviye L=100, tick=0.1; yaklaşma=10 tick(1.0), temas=1 tick(0.1), yeniden kurulma=20 tick(2.0). Uygulamada Decimal/rational kullanılır; float epsilon veya gizli yuvarlama yok. Varsayılan FROM_BELOW için yaklaşma: önceki uygun kapalı close bandın dışında, yeni close’un seviyeye uzaklığı ≤1.0 ve >0.1, uzaklık azalıyor; yeni bar temas bandını kesmiyorsa APPROACH. Temas: uygun kapalı mumun [low,high] aralığı [99.9,100.1] ile kesişir ve bağın geliş yönü koşulu önceki uygun gözlemle sağlanır. Aynı mumda TOUCH önceliklidir; ayrıca APPROACH bildirilmez. FROM_ABOVE simetrik ve ayrı parametredir; BOTH istenirse başlangıç yönü ve episode ayrımı açık sürümlenir.

Temas gözlemi mumun kapanışında bilinir; intrabar ilk temas anı veya OHLC sırası uydurulmaz. Açık mumda fiyat bandı görülse de CLOSED_CANDLE profili yalnız OBSERVE_ONLY üretir. Kapanış kırılımında üst banda eşit close kırılım değildir; kapalı close üst bandı kesin aşmalı, önceki kapanış diğer tarafta olmalı. Bu ayrı rule/version ve W5 örneğidir.

## Kalıcı durum ve yeniden kurulma

Lifecycle (DISABLED/ACTIVE/PAUSED_DATA/PAUSED_REVISION/DELETED) ile temas phase’i (ARMED/APPROACH_NOTIFIED/TOUCH_LATCHED) ayrıdır. Onaylı aktivasyon yoksa lifecycle DISABLED. APPROACH_NOTIFIED aynı yaklaşma episode’unda tekrar bildirim üretmez; TOUCH sonrası TOUCH_LATCHED kalır.

TOUCH_LATCHED sonrası iki **ayrı ve uygun kapalı** mum sayılır. İkinci veya sonraki mumun bütün fiyat aralığı seviyeden en az 2.0 uzaktaysa yeniden ARMED olur (FROM_BELOW: high≤98). Yeniden kuran bar yeni yaklaşma/temas doğurmaz; ancak sonraki bar yeni episode açabilir. APPROACH_NOTIFIED durumunda tam ayrılma yaklaşma latch’ini sıfırlar. Tekrar paket/catchup/cooldown sırasında uydurulan bar bu sayacı ilerletmez.

Veri kesilince phase silinmez ama lifecycle PAUSED_DATA olur. Resync geçmişi yeni canlı temas veya yeni cooldown barı sayılmaz. Zamanında gözlenemeyen boşluk nedeniyle episode geçmişi belirsizse tazelik/tamlık kanıtı ve açık yeniden kurulma gerekir; gap sonrasında ARMED varsayılmaz. Ölçüm/suppression nedeni kalıcı raporda görünür; sürekli temas ayrı yeni temas gibi bildirilmez. Bağ değişimi/undo yeni revision’da PAUSED_REVISION ve açık rebind gerektirir.

## Geometri ve kimlik

Yatay örnek yukarıdaki seviyeyi kullanır. Bölge finite zaman/fiyat aralığı, trend doğrulanmış logical grid/segment, Fibonacci kaydedilen anchor sırası ve exact oranlarıyla E3’e uyar. Grid yoksa extrapolation veya UTC formülüyle sessiz alternatif hesap yapılmaz. Örnek ters Fibonacci110→100, r=.618 sonucu103.82; bunu otomatik emir tick’ine yuvarlama.

Semantik olay anahtarı E3 bileşenlerinden canonical UTF-8 JSON array (alanların E3 sırası) üzerinden SHA-256 hex olarak tasarlanır; kalıcı event_id 64 karakterdir. Bütün bileşenler string olarak kanonikleştirilir; revision/version/candle_open_time pozitif base10, başında sıfır olmadan ve backend integer’ından kayıpsız çevrilir. JSON planda golden canonical dizi ve hash vardır; Python/TS motor eşitliği gelecekte ayrıca sınanır. Feed sequence/generation, etiket, piksel ve gönderim denemesi event_id’ye katılmaz. Aynı event_id farklı payload digest’iyle gelirse veri bütünlüğü hatasıdır. Ayrı binding/rule version’ları birbirini cooldown/dedup ile bastırmaz.

## Replay ve bildirim

Replay, donmuş aynı girdi/binding/grid/rule sürümü ve aynı karar anında bilinen bilgiyle aynı domain event izini üretmeli. Canlı state/outbox yerine `replay:<run_id>` deposu kullanılır; dış mesaj/emir yoktur. Run ID domain event hash’ini değiştirmez; namespace depolamayı ayırır. History bootstrap değerlendirme geçmişini besleyebilir ama canlı fırsat veya teslim kaydı üretmez. Gelecek veriye/pivot teyidine bakılmaz.

Mevcut NotificationQueue idempotent event_id+numeric Telegram destination, lease ve retry sağlar; yerel sink değildir. enqueue kendi BEGIN IMMEDIATE transaction’ını açtığından uygulama event transaction’ına olduğu gibi gömülemez. Varsayılan CLI execution.sqlite3 açar; kuru çalışma bunu kullanmaz. Hedef: app-scoped event+intent transaction, ardından ayrı bağlantı/uygun store façade üzerinden idempotent kuyruk köprüsü. Eklenecek façade/migration/state işleri bu planda uygulanmış değildir. İki DB’ye ortak atomik commit sözü verilmez.

Mevcut kuyruk PENDING/SENDING/RETRY/DELIVERED/FAILED, en fazla8 deneme ve60sn lease kullanır; backoff ve sağlayıcı retry_after’ı kayıtlıdır. Hedef DELIVERY_UNKNOWN/EXPIRED/CANCELED_SUPERSEDED/CHANNEL_UNCONFIGURED durumları mevcut sınıfta yoktur. Yanıt kaybında sağlayıcı mesajı almış olabilir: tam bir kez teslim garantisi yok; belirsiz sonuç ve retry/uzlaştırma politikası açık görünmelidir. Örnek60sn notification TTL’i sürümlü tasarım parametresidir, bugünkü kuyrukta uygulanmaz. Beklerken çizim sürümü değişirse gönderilmemiş intent iptal edilir; gönderilmiş mesaj geri alınmış sayılmaz. Bildirim emir yetkisi değildir.

## Senaryo matrisi

| ID | Senaryo | Beklenen sonuç özeti |
| --- | --- | --- |
| DR01 | Bugünkü LIVE veri uygunluk ispatı değildir | {"outcome":"BLOCKED","reason":"NOT_IMPLEMENTED","semantic_events":0,"external_messages":0} |
| DR02 | Yaklaşma bandına giriş | {"event":"APPROACH","semantic_events":1,"local_intents":1,"next_phase":"APPROACH_NOTIFIED"} |
| DR03 | Yaklaşma sınırı dahildir | {"event":"APPROACH","distance":"1.0","semantic_events":1} |
| DR04 | Bandın dışı yaklaşma değildir | {"semantic_events":0,"observation":"OUTSIDE_APPROACH"} |
| DR05 | Kapalı OHLC bandı temasla kesişir | {"event":"TOUCH","semantic_events":1,"local_intents":1,"next_phase":"TOUCH_LATCHED"} |
| DR06 | Aynı mumda temas yaklaşmaya önceliklidir | {"event":"TOUCH","semantic_events":1,"approach_events":0} |
| DR07 | Süren temas yeni temas değildir | {"new_semantic_events":0,"reason":"CONTACT_EPISODE_CONTINUES","measurement_reason_recorded":true} |
| DR08 | Ayrılma ve cooldown sonrası yeniden kurulma | {"event_on_rearm_bar":null,"next_episode_event":"APPROACH","new_semantic_events":1} |
| DR09 | Açık mumda varsayılan olay yok | {"outcome":"OBSERVE_ONLY","semantic_events":0} |
| DR10 | Kapanışla kırılım ayrı W5 profili | {"equality_cross_event":0,"strict_cross_event":1,"w4_enabled_by_this_case":false} |
| DR11 | OHLC içi sıra bilinmez | {"outcome":"INTRABAR_ORDER_UNKNOWN","ordered_pattern_events":0} |
| DR12 | Zaman sınırlı bölge | {"outcome":"OUT_OF_SCOPE","semantic_events":0} |
| DR13 | Trend grid kanıtı yok | {"outcome":"BLOCKED","reason":"GRID_OR_GEOMETRY_UNSUPPORTED"} |
| DR14 | Ters Fibonacci ve ondalık seviye | {"level":"103.82","silent_tick_rounding":false} |
| DR15 | Snapshot/history close metadata canlı olay değildir | {"new_live_events":0,"external_messages":0} |
| DR16 | Tekrar paket ve semantik tekrar | {"new_semantic_events":0,"new_delivery_intents":0,"reason":"SEMANTIC_EVENT_ALREADY_RECORDED"} |
| DR17 | Restart epoch ve temas hafızası | {"phase_restored":"TOUCH_LATCHED","historical_live_events":0,"duplicate_intents":0} |
| DR18 | Sequence atlaması tek başına veri boşluğu değildir | {"false_gap":false,"data_validation_still_required":true} |
| DR19 | Eski/bozuk paket kural hafızasını değiştirmez | {"semantic_events":0,"state_mutation":false,"reason":"INVALID_PACKET"} |
| DR20 | Kaynak/sembol/fiyat türü uyuşmazlığı | {"outcome":"BLOCKED","reason":"IDENTITY_MISMATCH"} |
| DR21 | Taze heartbeat eski upstream veriyi canlandıramaz | {"outcome":"BLOCKED","reason":"STALE_INPUT"} |
| DR22 | Saat kanıtı yok veya saat sıçrar | {"outcome":"BLOCKED","reason":"CLOCK_UNTRUSTED"} |
| DR23 | Kalite/gap/warmup eksikliği | {"semantic_events":0,"reasons":["QUALITY_NOT_OK","GAP_OR_INCOMPLETE_WARMUP"]} |
| DR24 | Float fiyat kesinlik kanıtı değildir | {"outcome":"BLOCKED","reason":"PRICE_PRECISION_UNPROVEN"} |
| DR25 | Çizim commit yarışı | {"semantic_events":0,"local_intents":0,"reason":"REVISION_CHANGED"} |
| DR26 | Silinme veya head okunamaması | {"outcome":"BLOCKED","reason":"DRAWING_NOT_FOUND_OR_DELETED"} |
| DR27 | Undo eski yetkiyi canlandırmaz | {"outcome":"BLOCKED","reason":"REVISION_CHANGED","explicit_rebind_required":true} |
| DR28 | LIVE dışı durum ve renderer/fault | {"semantic_events":0,"blocked_statuses_ref":"E3.blocked_statuses"} |
| DR29 | Gecikmiş resync catchup fırsat değildir | {"new_live_events":0,"audit":"HISTORICAL_CATCHUP","resume_requires_fresh_proofs":true} |
| DR30 | Replay aynı domain izi, ayrı yan etki alanı | {"domain_event_ids_identical":true,"external_messages":0,"live_outbox_writes":0,"namespace":"replay:<run_id>"} |
| DR31 | Event+intent atomik; köprü tekrarına dayanıklı | {"lost_domain_events":0,"duplicate_queue_rows":0,"cross_database_atomicity_claim":false} |
| DR32 | Gönderim sonucu belirsiz | {"delivery_state":"DELIVERY_UNKNOWN","exactly_once_delivery_claim":false,"manual_or_policy_reconcile_required":true} |
| DR33 | Kanal yok/429/kalıcı hata/TTL | {"local_receipt_supported":true,"external_messages":0,"outcomes":["CHANNEL_UNCONFIGURED","RETRY_BOUNDED","FAILED","EXPIRED"]} |
| DR34 | Kuyrukta beklerken revision değişir | {"delivery_state":"CANCELED_SUPERSEDED","old_message_sent":false,"already_sent_message_recalled":false} |
| DR35 | Ayrı kural bağı ayrı olaydır | {"semantic_events":2,"cross_binding_suppression":false} |
| DR36 | Emir/hesap yan etkisi yok | {"order_requests":0,"account_requests":0,"external_messages":0,"execution_store_mutations":0,"runtime_worker_started":false} |

Her senaryonun given/steps/expected alanları JSON planda saklıdır. Hepsinin durumu SPECIFIED_NOT_EXECUTED; E4 belge denetimi bu senaryoların çalıştığı anlamına gelmez.

## Gelecekte çalıştırılacak kabul kapısı

Her fixture kaydında rule/binding/çizim revision, kaynak/epoch/sequence, bar-open zamanı, snapshot/grid/geometri hash’i, eligibility nedeni, önceki/sonraki phase, semantik event ID, intent/delivery durumu ve dış etki sayaçları yer almalı. Beklenen tüm event/state/count sonuçları gerçek izole motor testleriyle eşleşmeli; crash/restart ve fake-clock testleri sahte sink ile geçmeli. Hesap/emir isteği, kullanıcı veya execution DB yazımı ve gerçek kanal gönderimi sıfır olmalı.

Uygulama başlamadan E1 açıkları ve E5 kullanıcı incelemesi korunur. E4 yalnız sonraki işin somut planıdır; W4/Uygulama/Bot hazır kabulü değildir.
