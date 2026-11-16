# G6 — Geçici ekran oturumu sözleşmesi

Bu köprü tarayıcının bildirdiği ekran durumunu okutur. `authority=CLIENT_REPORTED_UI_NOT_MARKET_EVIDENCE`, `client_time_trusted=false` ve `order_authority=false` her okunabilir oturumda açıktır. G3/G5 hesapları imleci örtük sorgu zamanı olarak kullanmaz. Kalıcı profil/şablon, piyasa snapshot'ı ve UI birbirinden ayrıdır.

## HTTP yüzeyi

- `GET /api/workspaces/{workspace_id}/ui-sessions`: görünür ve kapanmamış oturumların metadata listesi; snapshot veya yayıncı anahtarı içermez. `?policy_only=true` yalnız politikayı verir.
- `GET /api/workspaces/{workspace_id}/ui-sessions/{ui_session_id}`: açıkça seçilen oturum; hazırsa snapshot, aksi halde `UI_UNAVAILABLE`. Gizli ve bulunamayan kimlikler ayırt edilmez.
- `GET /api/workspaces/{workspace_id}/chart-context?symbol=BTCUSDT&interval=15m&ui_session_id=...`: G2 bağlamına isteğe bağlı, bağımsız UI bölümü ekler. Bot sembol/interval parametrelerini açıkça seçmelidir. `ui.market_matches_requested=false` durumunda sekmenin piyasası sorgu piyasası yerine geçirilmez.
- `PUT /api/workspaces/{workspace_id}/ui-sessions/{ui_session_id}`: frontend yayıncısı; `X-UI-Publisher-Key` 32 bayt rastgele anahtarın 64 küçük hex karakteridir. Salt okuyan bot bu anahtara ihtiyaç duymaz. Anahtar yalnız bellekte bulunur; DOM, localStorage ve GET yanıtlarında bulunmaz.

Yapılandırılmış web token'ı varsa bu uçlar ve UI isteyen chart-context mevcut Bearer/HttpOnly eşleştirme çereziyle doğrulanır. Token yoksa mevcut yerel owner sınırı kullanılır; bu mod çok kullanıcılı kimlik doğrulaması sunmaz. Localhost Host ve aynı Origin sınırı korunur. Oturumlar owner + workspace + session ile ayrılır. Politika gerçek `/api/markets` yanıtında `ui_session_bridge` olarak keşfedilir; destek ilan etmeyen eski frontend fixture'ları yayıncıyı başlatmaz.

## Yayın zarfı ve snapshot

`schema_version=chart-ui-session/1`, `server_instance_id`, artan `sequence`, `client_time_ms`, `visibility=visible|hidden`, `client_status=CONNECTED|OFFLINE|CLOSED`, `snapshot` zorunludur. Bilinmeyen alanlar kabul edilmez; istek en fazla 32 KiB'dir. Sunucu başlangıç kimliği eski process paketlerini reddeder. Aynı sequence ve aynı gövde idempotent ACK verir fakat TTL'yi uzatmaz; çakışan veya geriye giden sequence 409 verir.

Snapshot alanları:

| Alan | Anlam |
| --- | --- |
| `market`, `market_data` | Demo kaynak kimliği, sembol/interval, ekrandaki veri status/epoch/generation/sequence; sunucu piyasa kanıtı değildir |
| `viewport` | Logical/time/price aralıkları, CSS boyutları, LINEAR/LOG ve ters fiyat ekseni; henüz oluşmayan aralık null |
| `selection` | Seçili çizim kimlikleri ve araç; owner/workspace/sembol dışı veya silinmiş seçimler okuma sırasında elenir |
| `crosshair` | UTC saniye, decimal fiyat, pane ve gerçek hover mumu; pointer çıkınca veya piyasa değişince temizlenir; sabit imleçte mum güncellemesi güncel kaynaktan alınır |
| `magnet`, `panels`, `indicators` | Mıknatıs, panel/dialog görünürlüğü, pane ağırlıkları, etkin gösterge kimlikleri ve ayar revizyonu |
| `theme`, `favorites`, `notifications` | O sekmedeki tema/favoriler ve yerel in-app/ses/desktop tercihleri, izin ve ses hazırlığı |
| `history` | `can_undo`, `can_redo`, üst undo/redo işleminin hedef kimliği + revizyonu; yığın/geometri içerikleri yoktur |
| `persistent_refs`, `loading` | Bilinen kalıcı revizyonlar ve henüz yüklenmeyen alanlar; kayıtların kendisi G2 alanlarında kalır |

Hover OHLC/hacimler kaynakta exact decimal metinse aynen korunur; fallback görüntülenen sayının decimal metnidir. UTC saniye ve milisaniye ayrımı doğrulanır; NaN/Infinity, uygunsuz sayılar, fazla alan ve yığın gövdeleri reddedilir. Görünür fiyat aralığı negatif olabilir. Bu değerler işlem matematiğinin kanıtı olarak kullanılamaz.

Undo/redo revizyon özetleri güncel salt okunur SQLite başlıklarıyla karşılaştırılır: `current_revision`, `revision_matches`, `target_deleted` eklenir. Silinen hedef geri almanın hedefi olabilir; bu yüzden geçmiş referansı korunur fakat seçime geri eklenmez. Owner/workspace/sembol dışı geçmiş referansları elenir. Kullanılabilirlik istemci bildirimidir; işlem uygulanırken mevcut revizyon ve yetkiler ayrıca doğrulanır.

## Yaşam döngüsü ve sınırlar

Normal yayın değişime bağlıdır, en sık 500 ms'de bir yapılır; boşta heartbeat 5 saniyedir. Pointer olayları yalnız dirty işareti üretir. Hidden/offline/pagehide bildirimi hız sınırını beklemeden okunabilirliği kaldırabilir. Tarayıcı veya ağ kapanıp bildirim ulaşamazsa son rapor, sunucunun monoton saatine göre 30 saniye sonra `UI_UNAVAILABLE`, `stale=true` olur. Böyle bir kapanışın anlık tespiti garanti edilmez. Gizli sekme heartbeat ile canlı tutulmaz.

Kapanan veya TTL'si dolan oturum yeni paketle canlandırılmaz. Yayıncı yeniden bağlanırken yeni kimlik/anahtar alır. BFCache dönüşü de yeni kimlik başlatır. Süreç yeniden başlayınca yeni epoch keşfedilir. Geçici hatalarda gecikmeli tekrar uygulanır; eski istek yanıtı daha yeni bir gizleme/kapanış sonucunu geçersiz kılamaz.

Depo süreç belleğindedir; migration veya kalıcı UI yazımı yoktur. En fazla 128 oturum gövdesi tutulur. Yeni oturum için kapanmış/süresi dolmuş kayıt çıkarılabilir; çıkarılmış kimlikler sabit 8 KiB Bloom tombstone filtresiyle yeniden canlanmaya karşı korunur. Çakışma yalnız yeni bir kimliği reddedebilir; yayıncı yeni kimlikle tekrar dener. Dolu aktif depoda 429 uygulanır. Uygulama tek sunucu process'i içindir; çok worker'lı dağıtık lease deposu eklenmedi.

`context_id` G2 piyasa/kalıcı içerik kimliğidir; UI heartbeat ile değişmez. `ui_context_id` ayrı rapor sequence'i ve uzlaştırılmış snapshot'tan üretilir. `consistency_scope=INDEPENDENT_TRANSIENT_SESSION_NOT_MARKET_SNAPSHOT` atomik piyasa+UI snapshot garantisi vermediğini açıklar. G7 nesne kökeni/manüel koruma ve G8 gerçek bot adaptörü bu paketin kapsamı dışındadır.

Kabul komutu: `python scripts/integration/check_g6_ui_sessions.py`. Sonuçlar [G6 raporunda](../../reports/chart-interface-g6-20261115/README.md); gerçek üretim App + izole yerel HTTP/SQLite ve sentetik piyasa fixture'ı kullanılır.
