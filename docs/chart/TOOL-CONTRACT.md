# T01 — Ortak araç sözleşmesi

10 Kasım 2026. Durum: TAMAMLANDI. 697 Python testi geçti; 11 yeni T01 testi dahil. T02 daha sonra tamamlandı; sıradaki P2.

GET /api/chart-tools sürümlü yetenek kaydını sunar. Dört mevcut çizim okunabilir/düzenlenebilir; gelecek çizimler, göstergeler, planlar ve kurallar ayrı kategorilerde listelenir. Sabit mevcut EMA/RSI görüntüsü, yeni sürümlü indicator nesnesinin hazır olduğu anlamına gelmez. Kanonik sorgular boş, izleme ve emir yetkisi kapalıdır. capability bilinmeyen kategori/tür/sürümü BLOCKED_UNSUPPORTED_TOOL ile reddeder.

GET /api/chart-tools/{category}/{kind}?version=1 tek araç yeteneğini döndürür; bilinmeyen kategori/tür/sürüm HTTP 422 ve BLOCKED_UNSUPPORTED_TOOL verir. Kayıt 22 tür tanımlar; yalnız dört mevcut çizimin nesne okuma/düzenleme desteği vardır. computable=false ve canonical_queries=[] tüm türlerde korunur. definition alanındaki anchor sayısı, parametre adları ve planned_queries gelecek uygulamalar için bildirimdir; çalışan hesap veya kabul edilen yazma şeması değildir.

GET /api/drawings/{drawing_id}/contract mevcut owner-scoped show üzerinden chart-tool-contract/1 okuma izdüşümü verir. Kimlik, revision, silinme, anchor sırası ve ondalık metin korunur. Eski kayıtta interval bulunmadığından null ve UNSPECIFIED_LEGACY kullanılır; workspace'in güncel intervalinden tarihsel bağlam uydurulmaz. Yatay çizgi sınırsız, diğer mevcut araçlar anchor aralığıyla sınırlıdır. Fibonacci mevcut yedi oranı taşır. LEGACY_LOGICAL_GRID kanonik fiyat hesabı iddiası değildir.

## Uyumluluk ve göç sınırı

Eski strict CRUD ve SQLite kayıt biçimi aynen korunur. Yeni sözleşme ayrı salt okunur endpoint olduğundan DB migration veya geçmiş revision yeniden yazımı gerekmez. Kayıp yanıtların saklanmış eski sonuçlarına alan eklenmez. Sözleşme nesnesi eski geometry yazma uçlarında geçerli değildir. Gelecekte v2 yazma desteği ayrı açık endpoint, expected_revision ve request_id ile eklenmeli; bilinmeyen alanlar eski geometriye düşürülmemelidir. Yeni araç persistence, gösterge ayarları ve kural aktivasyonu ilgili sonraki paketlerin işidir.

Gizleme görünüm, kilit düzenleme, izleme revision bağlı kural, emir ayrı yetkidir. Bu paket gizleme/kilit işlevi eklemez. Hesap, stream veya emir çağrısı yapmaz.

## Doğrulama

Tam Python regresyonu: **697/697 PASS** (22,379 saniye). T01: 6 sözleşme + 5 API testi; mevcut 19 çizim/API testiyle hedefli toplam 30 kontrol geçti. Tam koşu bu testleri de içerir; sayılar birbirine eklenmez.

Doğrulananlar: 22 türün ayrı kategori ve açık yetenekleri; bilinmeyen tür/sürüm hatası; dört çizimde anchor/ondalık/sıra/zaman kapsamı/Fib oranları; owner izolasyonu; değişmeyen legacy CRUD ve idempotent tekrar; silme/geri yükleme; workspace intervalinden bağ türetilmemesi; sözleşmenin legacy yazma girişinde reddi; dış origin engeli; borsa erişimi ve execution DB oluşturulmaması.

Kanıt: reports/chart-t01-python-tests-20261110.log ve reports/chart-t01-validation-20261110.json. İlk sandbox süreç başlatma engeli izinli çalıştırma yoluyla aşıldı. TestClient bağımlılığında mevcut httpx deprecation uyarısı var; test başarısızlığı yok. Frontend kaynak/asset değişmedi; frontend testleri, build ve fiziksel kabul bu backend sözleşme paketi için tekrar çalıştırılmadı. Canlı ağ/hesap/emir isteği yapılmadı. T02/P2 ve sonraki paketler uygulanmadı.

## T02 sonrası güncel yetenekler

Yukarıdaki boş canonical_queries ve hesap uygulanmadı açıklaması T01 teslim anının kaydıdır. T02 mevcut dört türde PURE_OFFLINE_REQUIRES_CONTEXT, computable=true ve desteklenen sorguları ekledi. Bunlar yalnız saf/offline hesap yeteneğidir; izleme/emir yetkisi değildir. Çizim sözleşmesi LIVE_EVALUATION_NOT_IMPLEMENTED ile BLOCKED kalır. [Güncel hesap sözleşmesi](GEOMETRY.md).

## T03 güncellemesi

Ruler açık chart-ruler/1 şemasıyla kalıcı, okunabilir, düzenlenebilir ve saf measurement hesabına sahip hale geldi. Varsayılan eski liste dört türü korur; modern istemci format_version=2 ile opt-in yapar. Eski kayıtlar değiştirilmedi, DB migration gerekmedi. [Güncel cetvel sözleşmesi](RULER.md).
