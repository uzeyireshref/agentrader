# Bot terminali araştırması ve yetenek eşleştirmesi

16 Kasım 2026. İlk araştırma teslimi; canlı ürünlerin oturum içi davranışı veya görsel birebir karşılaştırması yapılmadı. Resmî ürün belgeleri incelendi. Bu belge borsa kabulü değildir.

## Kaynaklardan çıkan tasarım kararları

| Kaynak | Gözlenen yaklaşım | Projeye uyarlama |
|---|---|---|
| [3Commas terminali](https://help.3commas.io/en/articles/16281054-trading-terminal-overview) | Grafik ve işlem parametre paneli, yön, emir türü, hedef/stop | Grafik yanında açılan işlem paneli; taslak ve önizleme |
| [Bitsgap bot ayrıntıları](https://bitsgap.com/blog/evaluate-your-bots-performance-with-new-bot-details) | Performans/ayarlar, açık emirler/geçmiş, bot eylemleri | Grafik ile ilişkili ayrı Bot görünümü; pozisyon/emir/komut ayrımı. Kaynak 2023 tarihli tarihsel tasarım referansıdır. |
| [Hummingbot oturum yönetimi](https://hummingbot.org/dashboard/instances/) | Oturum metrikleri, gerçekleşmiş/gerçekleşmemiş sonuç, günlükler; farklı durdurma davranışları | Finansal durum ile süreç sağlığını ayır; durdur/iptal/kapat etkisini açıkla |
| [Freqtrade REST API](https://www.freqtrade.io/en/stable/rest-api/) | Yerel API, kimlik doğrulama ve dış erişime ilişkin sınırlar | Yerel varsayılanı koru; uzak erişimi ayrı yapılandırma ve HTTPS ile hazırla |

Bunlar ürün örüntülerinden yapılan tasarım çıkarımlarıdır. Rakiplerin emir türleri, hedef sayıları veya hesap kapsamları Agentrader desteği olarak taşınmaz.

## Mevcut kodla eşleştirme

| İhtiyaç / ekran | Mevcut kaynak | Sınır ve eksik web işi | Kabul senaryosu |
|---|---|---|---|
| SINGLE işlem kurma | `agentrader/bot/plan_v2.py`, `v2_preflight.py`, `single_commands.py` | Yetkili plan ve risk gerekir; prototip yalnız Limit taslağıdır | Yanlış stop/hedef reddi; değişen taslak eski önizlemeyi düşürür |
| GRID / NEUTRAL | Mevcut grid/neutral plan ve runner servisleri | SINGLE formu kullanılamaz; ayrıntılı kurulum ve mevcut izinlerin HTTP köprüsü bekliyor | Tür değişince SINGLE onayı yok |
| Artır/azalt/kapat/tersine çevir | `agentrader/bot/position_commands.py` | Sahip olunan V2 SINGLE; her oturuma genellenmez | Sahiplik, kısmi kapanış, iki bacaklı reversal |
| Native trailing | `agentrader/bot/native_trailing.py` | Yerel trailing'den ayrı; parent/child ve dolum teyidi | İptal/dolum yarışı; kayıp yanıtta tekrar gönderim yok |
| Seçili/sembol/hesap iptali ve timer | `cancel_commands.py`, `cancel_timers.py` | Koruma ve yabancı kapsamı; timer tek başına pozisyon kapatmaz | İptalde açık pozisyon ve rezerv doğru gösterilir |
| Toplu oluştur/değiştir/iptal | `batch_commands.py` | Oluştur 1–5, değiştir 1–5, iptal 1–10; mevcut ek uygunluk sınırları korunur | Kısmi batch sonucu üye bazında |
| Hesap ayarları | `account_commands.py`, `exchange_commands.py` | Ortak mod etkileri ve hesap uygunluğu; public HTTP adaptörü bekliyor | Açık etki önizlemesi, eski bağlam reddi |
| Sorgu/geçmiş/dışa aktarma | `query_commands.py` | İzinli sorgu kataloğu; serbest URL yok | Sayfalama, hata ve eksik sonuç ayrımı |
| Operasyon görünümü | `agentrader/application/operations.py`, `GET /api/operations` | Yerel gözlem; borsa/işlem hazırlığını kanıtlamaz | Eksik bağlam sağlıklı görünmez |
| Finansal HTTP komutları | Mevcut `exchange_commands.py` çekirdeği | `/api/commands` yalnız runtime.inspect; yeni `/api/bot` adaptörü henüz yok | İdempotency, sahiplik, onay digest'i ve restart |
| Grafikten fiyat/çizim aktarımı | `chart_context`, çizim ve onay servisleri | Prototipte yalnız sembol geçişi var; çizim revizyonlu aktarım bekliyor | Çizim değişikliği onaylı taslağı değiştirmez |

## İlk prototip sınırı

Tarayıcı içi sentetik veri, sabit örnek fiyatlar ve bakiye kullanılır. BotTerminal ve botPrototype ağ çağrısı içermez. Gerçek hesap, risk hesaplama, filtre kontrolü ve finansal komut yoktur. Gelişmiş işlemler yetenek açıklamaları ve örnek eylem önizlemeleridir; çalışan finansal kontroller değildir. Yerel oturum günlüğü kalıcı borsa journal'ı değildir.

## Sonraki tasarım çalışması

GRID/NEUTRAL formları, gelişmiş emir seçenekleri, ayrıntılı pozisyon/batch düzenleyicileri, çizimden revizyonlu aktarım, kalıcı geri bildirim ve klavye/odak erişilebilirliği tamamlanacak. Prototip görsel değerlendirmesinden sonra gerçek servis entegrasyonuna geçilecek. İlk araştırma bu açık işleri tamamlandı saymaz.

## İkinci adım kaynak doğrulaması

`plan_v2.py`, `grid_plan.py`, `neutral_plan.py` ve `entry_options.py` doğrudan incelendi. Grid bütçesi baz varlık miktarı değildir; NOTIONAL/MARGIN/MAX_LOSS USDT bütçesidir. GRID başlangıcı LIMIT olamaz ve tek son hedef gerektirir. NEUTRAL hedge gerektirir; hedef listesi boştur, trailing desteklenmez ve merkez tick uyarlanmış iç seviyeye denk gelmelidir. Prototip yalnız yaklaşık seviye kontrolü yapar, derleyicinin yerine geçmez.

Limit STP yalnız GTC/IOC/GTD ile sunulur; FOK/GTX ile gizli eski STP taşınmaz. Yeni formlar ve kalan parametre kapsamı PROGRESS.md içinde ayrılmıştır. İlk tablodaki eksik web işleri gerçek backend entegrasyonu açısından devam eder.
