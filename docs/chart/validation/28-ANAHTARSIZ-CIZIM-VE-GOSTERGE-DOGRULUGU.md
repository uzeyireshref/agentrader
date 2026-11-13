# Anahtarsız çizim ve gösterge doğruluğu

9 Kasım 2026. Kullanıcı isteğiyle yerel grafik/çizim araçlarının anahtar zorunluluğu kaldırıldı. Doğruluk önceliği korunuyor; gezinme arayüzü yeniden tasarlanmadı.

## Kullanım ve erişim

http://127.0.0.1:8765/ sayfasını yenile. Çalışma alanı ve çizimler otomatik yüklenir; dört araç için anahtar girilmez. Eski eşleşme diyaloğu ile erişimi aç/kapat düğmeleri kaldırıldı. Mevcut çizimler silinmedi; şema değişmedi. Çalışan sunucu güncel API ile aynı portta yeniden başlatıldı.

/api/workspaces ve /api/drawings anahtarsız yerel metadata uçlarıdır; token ayrıca tanımlanmış olsa da araçlar pairing istemez. Localhost Host/Origin, JSON gövde sınırları, owner kapsamı, revision ve idempotency denetimleri korunur. /api/commands ve /api/status ayrı kimlik doğrulama sınırında kalır; token yoksa kapalıdır. /api/session protokolü bu ayrı API için korunmuştur, grafik UI kullanmaz. Gerçek emir/hesap yetkisi eklenmedi.

## Bağımsız gösterge doğruluğu

scripts/generate_indicator_reference.py ağ erişimi yapmadan Python Decimal precision=50 ile ayrı referans üretir. TypeScript gösterge fonksiyonlarını çağırmaz. EMA SMA seed + 2/(n+1), RSI Wilder ortalaması ve flat=50 sözleşmesini kullanır.

Altı 300 mumluk senaryo: sabit, yükselen, düşen, karışık, zaman boşluğu ve son açık mum kapanışı değiştirilmiş dizi. EMA20/EMA50/RSI14 için toplam 4.908 nokta, zamanları ve warmup uzunlukları frontend ile karşılaştırıldı; mutlak 1e-8 toleransında tamamı geçti. [Referans](../../../reports/indicator-reference-20261109.json); test frontend/tests/indicatorReference.test.ts. Aynı seed/geçmiş sözleşmesine ait sayısal kanıttır; gerçek Canvas etiketlerinin fixture'la görsel karşılaştırması veya farklı seed kullanan her platformla eşitlik garantisi değildir.

## Doğrulama

667 Python testi, atlanan test olmadan; izole HTTP/worker/restart ve runtime/risk korunması geçti. 67 frontend testi, TypeScript ve Vite üretim derlemesi geçti. React testi workspace'in anahtarsız açıldığını, çizim kaydedildiğini, /api/session isteği yapılmadığını ve parola alanı render edilmediğini doğrular. API testi token boşken create/read, foreign-Origin reddi ve komut/status kapalılığını sınar. Gerçek kullanıcı çizimine test amaçlı yazma yapılmadı.

Bundle index-3pKhQtuT.js. [Tam backend raporu](../../../reports/chart-workspace-validation-20261109.json).

## Sonraki doğruluk kapısı

Bağımsız Canvas referansına göre ankraj/fiyat/zaman hizalaması; veri boşluğu ve timeframe değişiminde gerçek çizim geometrisi; fixture'ın ekrandaki gösterge değeriyle eşleşmesi. Genel grafik kabulü ve bot bağlantısı hâlâ açık. Kullanım katmanını yeniden tasarlamadan önce bu doğruluk maddelerine devam edeceğiz.
