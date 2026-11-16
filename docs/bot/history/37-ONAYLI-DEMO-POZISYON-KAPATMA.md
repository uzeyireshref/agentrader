# Onaylı Demo pozisyon kapatma — 14 Kasım 2026

Kullanıcı, önceki bot testlerinden kaldığını belirttiği iki pozisyonun kapatılmasını açıkça onayladı. Yalnız bu iki mevcut Binance USD-M Demo LONG/BOTH pozisyonu, reduceOnly MARKET SELL emirleriyle kapatıldı. Gerçek Binance ortamına bağlantı kurulmadı.

| Sembol | Kapanan miktar | Borsa durumu | Ortalama gerçekleşme fiyatı | Borsa emir kimliği |
|---|---:|---|---:|---:|
| AAVEUSDT | 29,8 | FILLED | 112,0800 USDT | 442311484 |
| TRUMPUSDT | 1000 | FILLED | 1,08900000 USDT | 646732180 |

İki POST gönderildi. Yeni giriş, kaldıraç/teminat değişikliği veya genel giriş durdurmasını kaldırma işlemi yapılmadı. Mevcut hesap anahtarı kimliği önceki inceleme kapsamıyla eşleştirildi; işlemden önce one-way modu, iki pozisyon envanterinin eşleşmesi, tam miktarlar ve açık emir bulunmaması tekrar doğrulandı.

Her emir kendi sabit istemci kimliğiyle kalıcılaştırıldı. Kayıtlı kimlik tekrar kullanılırsa POST tekrarı yerine sorgulama yapılır. Gönderim yanıtı kaybolursa da aynı emir sorgulanır; yeni kimlikle yeniden gönderim yoktur. Sorgulanan borsa kimliği, sembol, yön, miktar, reduceOnly ve tam dolum kontrol edildi. Her azaltmadan sonra pozisyon tekrar okundu.

İşlem deposunun çevrimiçi yedeği, ilk günlük değişikliğinden önce alındı: `reports/demo-approved-reduction-before-20261114.sqlite3`. Ana işlem kilidi bütün uygulama boyunca tutuldu. İnceleme kapsamı değişseydi gönderim engellenecekti; kayıp/belirsiz yanıtlar otomatik yeni POST hakkı vermiyordu.

## Bağımsız son kontrol

Kapatma işleminin kendi son kontrolüne ek olarak `service acceptance-check` yeniden çalıştırıldı. Sonuç: **0 pozisyon, 0 normal açık emir, 0 koşullu açık emir**. Bu son kontrol yalnız GET kullandı ve işlem deposunu değiştirmedi.

Kontrollü yeni giriş kabulü henüz tamamlanmış değildir. Eski watchdog kaynaklı giriş durdurması ve tarihsel niyetlerin uzlaştırılması gereksinimi korunuyor. Bağımsız kurtarma izleyicisi başlatılmadı; yeni grafik sinyali/planı için ayrıca taze önizleme ve açık plan onayı gerekir. Kapatma onayı bu işlemler için genel yetki olarak kullanılmadı.

## Doğrulama ve kayıtlar

İşlem öncesi dört izole güvenlik testi geçti: kapsam dışı yön/miktar/kimlik/mutasyonun engellenmesi, pozisyon değişiminde teslimin durması, kalıcı kimlikle tekrar çağrıda ikinci POST oluşmaması ve kayıp yanıtta sorgulamayla uzlaştırma.

- Kapatma raporu: `reports/demo-approved-reductions-20261114.json`
- Ayrı son kontrol: `reports/demo-acceptance-after-approved-close-20261114.json`
- Kısıtlı uygulama aracı: `scripts/bot/close_approved_demo_positions.py`
- Güvenlik testleri: `tests/test_approved_demo_reductions.py`

Sonraki çalışma, borsadaki geçmiş emirler ile yerel kayıtları uzlaştırıp kalan giriş engellerini değerlendirmektir. Bu teslimde güvenlik durdurması kaldırılmadı.
