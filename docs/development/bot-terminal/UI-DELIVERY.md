# Grafik ve Bot arayüzü: geniş tur teslimi

Güncel yerel Demo entegrasyonu ve çalıştırma: [INTEGRATION.md](INTEGRATION.md). Aşağıdaki bölüm 16 Kasım prototip tesliminin tarihsel kaydıdır.

16 Kasım 2026. Bu teslim frontend prototipidir. Finansal HTTP adaptörü, gerçek Demo kabulü ve müşteri yayını tamamlandı sayılmaz.

## Kullanım

- Grafik ve API için mevcut yerel başlatma korunur: kökte `python -m agentrader web serve`, frontend klasöründe `npm run dev`.
- Grafik: `http://127.0.0.1:5173/`. Doğrudan Bot: `http://127.0.0.1:5173/?view=bot`.
- Grafik üstünde Bot, İşlem paneli ve seçili pozisyon çizimi için Seçili planı bota aktar düğmeleri vardır.
- Grafik planı aktarmak için Long/Short pozisyon aracıyla oluşturulmuş bir çizimi seçin. Giriş, stop ve hedef decimal metinleri ile workspace/çizim/revizyon referansı kopyalanır. Değişen veya silinen kaynak yeniden aktarılmadan onaylanamaz. Alanları elle düzenlemek kaynak bağlantısını kaldırır; çizim değişmez.

## Birlikte tamamlanan arayüzler

| Alan | Teslim |
|---|---|
| Ortak kabuk | Grafik/Bot/yan panel, grafik durumunu koruma, Bot sekme durumunu koruma, bağımsız kaydırma, mobil ve açık/koyu tema kuralları |
| SINGLE | Market/Limit, koşullu Market başlangıcı, sekiz priceMatch, TIF/GTD/STP, ACK/RESULT, USDT risk bütçesi, 1–8 hedef, kesin pay toplamı, hedef sonrası girişe stop, yerel takip stopu |
| GRID / NEUTRAL | Bant/aralık/dağılım, bütçe, hesap ve başlatma koşulları; neutral merkez/pay/iki stop; yönlü grid yerel/borsada koruma yenileme politikası |
| Pozisyonlar | Artır/azalt/kapat/tersine çevir; native trailing oluştur/sorgula/iptal için kimlikli formlar ve etki özeti; grid oturumu durdurma senaryoları |
| Emirler | Açık/geçmiş, normal/algo filtreleri, seçili emir iptal özeti, normal emir değiştirme; çekirdek korumalarda genel eylemler kapalı |
| Toplu işlemler | Plan referanslı oluştur, normal emir değiştir/iptal, üye ekle/çıkar/seç, sayısal ve kimlik sınırları, üye bazlı önizleme |
| Gelişmiş | Kaldıraç/marjin/ortak modlar, açık USD-M + COIN-M etki kabulü; timer süre/heartbeat/lease ve kimlikli yaşam döngüsü; sorgu/geçmiş taslağı |
| Günlük ve geri bildirim | Son 200 yerel prototip kaydı; tarayıcıda saklama, paylaşılabilir JSON, depolama hatası ve tekrar okuma, dış veri doğrulama |

## Veri ve yürütme sınırı

- Hesap, emir ve pozisyon listeleri sentetiktir. Onay yalnız yerel prototip kaydı üretir; gerçek finansal emir göndermez veya hesap ayarı değiştirmez.
- SINGLE ilk örnek miktarı artık baz varlık miktarı değil plan şemasına uygun USDT bütçesidir. Gerçek miktar backend preflight tarafından hesaplanacak.
- Yerel kayıtlar sunucuya veya geliştiriciye otomatik gönderilmez. Tarayıcı verisi temizlenirse kaybolur. JSON indirmesi kullanıcı tarafından paylaşılabilir; son 200 kayıt tutulur. Bu depolama finansal idempotency/journal değildir.
- Native ve yerel trailing ayrı kontrollerdir. Grid durdurma senaryoları gerçek engine kapanış politikası yerine geçmez. Gösterilen yönetim alanlarının gerçek sahiplik/risk/filtre kontrolleri backend entegrasyonunda zorunludur.
- Sayı kontrolleri taslak deneyimi içindir; tick/lot/Decimal/bakiye/kota/risk ve borsa sonucu teyidi yapılmış sayılmaz.

## Doğrulama

- 386 frontend testi geçti, 0 hata/skip. Yeni birleşik React DOM testi alan değişiminde eski onayı kaldırma, Market özetini, yerel geri bildirim ve komut kaydını, modal aç/kapat akışını ve sıfır prototip ağ isteğini kapsar.
- Grafik aktarım/revizyon, kesin hedef payları, batch kimlik/sayı/scope, timer heartbeat/lease ve native trailing kimlik testleri eklendi.
- TypeScript ve Vite üretim derlemesi başarılı; mevcut büyük grafik bundle uyarısı sürer. Bot arayüzü ayrı lazy modül olarak yüklenir.
- Grafik ve Bot yükseklikleri flex içinde ayrıldı; uzun Bot sayfası ve modallar için scroll alanları düzeltildi. Bu, gerçek tarayıcı görsel kabulünün yerine geçmez.
- Tarayıcı görsel/mobil kabulü açık tutulur. Son denemede Chrome'un yerel grafik erişilebilirlik ağacı okunabildi; ancak tıklama `coordinate input geometry is unavailable` hatası verdi ve klavye ile Bot bağlantısına geçiş doğrulanamadı. Yanlış pencereye ait olabilen ekran görüntüsü görsel kanıt sayılmadı. Python/backend değişmedi; bu tur Python regresyonu veya grafik replay yeniden çalıştırılmadı.

## Sonraki aşama

Görsel kullanıcı değerlendirmesi ve gerçek backend entegrasyonu. `/api/bot` servisleri, yetkilendirme, kalıcı worker, gerçek hesap görünümü, finansal journal ve sunucu erişimi ayrı uygulama aşamasıdır. Yerel geliştirme yolu korunmuştur.
