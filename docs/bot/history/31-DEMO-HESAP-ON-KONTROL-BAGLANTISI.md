# Demo hesap ön kontrol bağlantısı — 13 Kasım 2026

D3 süreklilik gözlemi geçti: `reports/demo-continuity-observation-20261113.json`, 1800,4 saniye, 30 ardışık doğrulanmış kapanış, 7 saat yenileme, sıfır yenileme hatası ve kapanış boşluğu. Bir saniyelik UPSTREAM_STALE dönemi kaydedildi; kabul sınırını aşmadı. Önceki başarısız gözlemler korunuyor. Teslim kaydındaki yedi kaynak SHA-256 değeri güncel dosyalarla eşleşiyor; bu kontrol imzalı süreç başlangıç kanıtı değildir.

## Eklenen adım

B3'ün ilk parçası olan **salt okunur hesap ön kontrolü** yerel CLI üzerinden kullanılabilir:

```powershell
python -m agentrader web preflight-preview WORKSPACE EVENT_ID VERSION
```

Grafikte yeni, geçerli bir gölge olay ve kullanıcı parametreleriyle üretilmiş önizleme gerekir. Yerel sunucu varsayılan 8765 portunda çalışmalıdır; `--port` değiştirilebilir. Önizleme süreleri uzatılmaz ve eski olaylar yeniden canlandırılmaz.

Komut, yerel API'den tam önizleme sürümünü alır; içerik/plan/risk profili hashlerini, Demo kaynağını ve güncel durumunu doğrular. Demo hesap anahtarları yalnız açıkça çalıştırılan CLI sürecinde yüklenir. Hesap erişimi GET izin listesine sarılır: bakiye, hesap modu, kaldıraç/teminat ayarları, açık pozisyon/emirler, günlük kayıp ve sembol kuralları mevcut `collect_flat_snapshot` ve `prepare_single` kontrollerinden geçer. Hesabın boş ve planla uyumlu olması gerekir; ayarlar otomatik değiştirilmez.

Hesap kontrolünden sonra aynı önizleme tekrar okunur. Süre dolması, veri tazeliği kaybı, revizyon değişimi, değiştirilmiş içerik veya farklı sürüm sonucu engeller. Sonuç yalnız terminale yazılır; hesap çıktısı web API'ye ya da uygulama veritabanına eklenmez. CLI hata çıktısı kimlik bilgilerini veya imzalı URL'leri yansıtmaz.

`READY` sadece anlık hesap/risk kontrolünün sonucudur. `execution_eligible=false`, `order_authority=false`, `approval_state=NOT_REQUESTED`. Plan içe aktarma, yetkilendirme, finansal kuyruk, emir veya hesap ayarı isteği oluşturulmaz. Bu geliştirme sırasında gerçek demo hesap sorgusu çalıştırılmadı; testler yalıtılmış hesap verileri kullandı.

## Doğrulama ve kalan kapsam

1036 Python testi geçti. Yedi yeni bağlantı testi: başarılı kontrolde yetki oluşmaması, hesap okuması sırasında süre dolması/revizyon iptali, içerik bozulması, mutasyon yöntemlerinin engellenmesi, hesap kontrolü hatası ve gerçek risk hazırlayıcıyla kaldıraç uyumsuzluğu. Mevcut önizleme ve yürütücü testleri de çalıştırıldı. Frontend değişmedi.

Sıradaki B3 parçası: kimliği doğrulanmış, hesap/plan hash/sürüm/süre ile bağlı kullanıcı onayı ve kalıcı teslim/uzlaştırma. Grafik revizyonunun giriş gönderiminden hemen önce yeniden doğrulanması, tekrar denemede çift emir oluşmaması ve açık pozisyon korumasının iptallerden etkilenmemesi ayrıca sınanacak. Bunlar tamamlanmadan grafik kaynaklı emir bağlantısı açılmayacak. Gerçek Binance bağlantısı bu kapsamda yoktur.
