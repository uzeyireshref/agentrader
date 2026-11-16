> 14 Kasım 2026 — [Kullanıcı onaylı iki Demo pozisyonu kapatıldı](37-ONAYLI-DEMO-POZISYON-KAPATMA.md): AAVEUSDT 29,8 ve TRUMPUSDT 1000 reduceOnly MARKET satışları FILLED. Ayrı GET kontrolü 0 pozisyon / 0 açık emir doğruladı. Yeni giriş açılmadı; eski durdurma ve uzlaştırma gereksinimi korundu.

# Kontrollü Demo kabul hazırlığı — 14 Kasım 2026

Gerçek Binance bağlantısı açılmadı. Yapılandırılmış Binance USD-M Demo hesabı ilk kez bu geliştirme zincirinde gerçek, salt okunur hesap çağrılarıyla kontrol edildi. Yeni giriş veya mevcut pozisyonlara müdahale yapılmadı.

## Gerçek hesap bulgusu

`positionRisk` ve hesap pozisyon envanteri iki açık one-way pozisyonu doğruladı:

| Sembol | Pozisyon | Miktar |
|---|---|---:|
| AAVEUSDT | LONG / BOTH | 29,8 |
| TRUMPUSDT | LONG / BOTH | 1000 |

Kontrol sırasında açık normal emir ve açık koşullu emir sayısı sıfırdı. Yerel işlem deposunda aktif yönetilen oturum yok; önceki watchdog bağlantı/sahiplik hatasından kalan giriş durdurması ve üç `NEW` durumlu tarihsel niyet kaydı var. Tarihsel `NEW` kayıtları, şu anda borsada üç açık emir olduğu anlamına gelmez; yeniden uzlaştırılmalıdır.

Grafik çalışma alanında yeni gölge olay/önizleme/onay kaydı yok. Uzun veri sürekliliği kabulü geçerli; bağımsız kurtarma izleyicisi çalışmıyor. İlk kontrollü SINGLE kabulü, hesabın pozisyonsuz ve emirsiz olmasını gerektirdiğinden mevcut koşullarda başlamadı. Risk sınırları artırılmadı, eski durdurma kaldırılmadı ve bilinmeyen pozisyonlar otomatik sahiplenilmedi.

Pozisyonların manuel işlem mi, önceki bot testlerinden kalma mı olduğu kullanıcıdan soruldu. Bu sınıflandırma veya bir sonraki geliştirme adımına geçme talimatı, pozisyonları kapatma onayı olarak kullanılmadı.

## Tekrarlanabilir salt okunur kontrol

```powershell
python -m agentrader service acceptance-check
```

Komut altı özel GET ile hesap yapılandırması, pozisyon modu, hesap, pozisyon riski ve normal/koşullu emir envanterini okur. Yerel işlem deposunu salt okunur açar; geçmiş kayıtları değiştirmez. Hesap ile `positionRisk` uyuşmazlığı, mevcut pozisyon/emirler, aktif yerel oturum, giriş durdurması, uzlaştırılmamış niyetler ve veri kabulü sorunlarını ayrı raporlar.

`plan_review_ready=true` yalnız plan incelemesine geçilebileceği anlamına gelir. `execution_ready`, `execution_authorized` ve `order_authority` daima `false` kalır; yeni giriş ayrıca taze plan, kullanıcı onayı ve bağımsız izleyici gerektirir. Hesap okuması başarısızsa pozisyon sayısı sıfır gösterilmez; bilinmiyor (`null`) olarak raporlanır. POST/PUT/DELETE ve `--execute-demo` seçeneği bu komutta yoktur.

Gerçek hesap çalışması `BLOCKED` döndü; bu hata gizlenmedi ve kabul geçti diye kaydedilmedi. Yerel rapor: `reports/demo-acceptance-check-20261114.json`.

## İnceleme için hazırlanan temizlik seçeneği

Mevcut pozisyonları koruma seçeneğinde bu hesapta yeni kabul testi başlamaz. Alternatif kapatma seçeneği için aşağıdaki **yetkisiz taslak** hazırlandı:

| Sembol | İşlem | Miktar | Emir | Kapsam |
|---|---|---:|---|---|
| AAVEUSDT | SELL | 29,8 | MARKET | BOTH, reduceOnly=true |
| TRUMPUSDT | SELL | 1000 | MARKET | BOTH, reduceOnly=true |

Miktarlar ve emir alanları Demo sembol kurallarıyla `REDUCE` rolünde doğrulandı. Piyasa fiyatı gerçekleşme fiyatını garanti etmez. Taslak yalnız iki mevcut pozisyonun kapatılması içindir; yeni giriş, kaldıraç/teminat değişimi veya genel durdurmanın kaldırılması yetkisi içermez. Uygulama düşünülmeden önce hesap, miktarlar, yön ve açık emirler yeniden doğrulanmalı; kapsam değişirse durulmalıdır.

Taslak: `reports/demo-existing-exposure-review-20261114.json`, durum `DRAFT_NOT_AUTHORIZED`, emir/yetki sayısı sıfır. Kullanıcının açık kararından önce bu taslak yürütülmez.

## Doğrulama ve durum

1107 Python testi ve 36 replay senaryosu geçti. Sekiz yeni test; pozisyonsuz hesabın dahi işlem yetkisi vermemesi, mevcut pozisyonların korunması, iki envanterin uyuşmaması, özel okuma hatasında boş hesap varsayılmaması, durdurma/geçmiş/emir engelleri, veri süresi ve mutasyon yöntemlerinin reddini kapsar.

Arayüz değişmedi. Gerçek hesapta sıfır emir isteği, sıfır hesap ayarı değişikliği ve sıfır işlem deposu mutasyonu yapıldı. Kontrollü gerçek Demo yürütme kabulü **tamamlanmadı**; mevcut pozisyonlar hakkında kullanıcı kararı gerekiyor. Gerçek ortam geçişi hazır olarak işaretlenmedi.
