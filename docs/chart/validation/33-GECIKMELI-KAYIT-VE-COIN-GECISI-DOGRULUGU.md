# Gecikmeli kayıt ve coin geçişi doğruluğu

9 Kasım 2026. Kontroller bu oturumda React/jsdom + kontrollü gecikmeli fetch yanıtlarıyla yapıldı. Ayrı masaüstü görevi yok. Canlı kullanıcı çizimlerine test yazımı yapılmadı.

## Yeniden üretilen ve düzeltilen hatalar

1. BTC yazması beklerken ETH'ye geçip BTC'ye geri dön. BTC yüklemesi eski revizyonla geciksin. Yazma revizyon2 ile tamamlandıktan sonra gecikmiş okuma revizyon1'i geri getirebiliyordu. Gerçek useDrawings hook testi düzeltme öncesi 1!=2 ile başarısız oldu. Artık aynı coin için yazma tamamlanırken daha eski bir okuma bekliyorsa okuma geçersizleştirilir; yazma bittikten sonra sunucudan güncel snapshot alınır. Bu korumalı yeniden eşitleme normal refresh gibi ekranın undo/redo geçmişini sıfırlar; farklı sekmede yeni veri varsa eski undo ile üzerine yazılmaz. Olağan yazmalar ekstra refresh başlatmaz.
2. İlk workspace isteği gecikirken kullanıcı Sunucudan yenile yapınca, gecikmiş ilk yanıt eski tercihleri geri yükleyebiliyordu. Test düzeltme öncesi beklenmeyen restore çağrısıyla başarısız oldu. Bootstrap artık ayrı LatestRead kapısından geçer; manuel refresh ve unmount bootstrap'ı iptal eder. Eski başarı/hata güncel duruma yayımlanmaz.

LatestRead.pending yalnız en güncel okumayı temsil eder. Eski isteğin finally bloğu yeni isteğin pending durumunu kapatamaz; bu ayrıca test edildi. Sunucu kayıt/revision/idempotency sözleşmeleri değişmedi.

## Test kapsamı

frontend/tests/drawingRaces.test.tsx gerçek hook'u render eder, yanıt sırasını deferred Promise'lerle kontrol eder:

- A→B→A sonrasında ilk A yanıtının reddi.
- Kaybolan yazma yanıtı sonrası aynı request_id ve birebir aynı body ile tekrar deneme.
- Gecikmiş BTC yazmasının ETH listesine karışmaması.
- Başarılı yazma sonrası eski reload'un revizyonu geriye alamaması.
- İlk bootstrap'ın manuel refresh tercihlerini ezmemesi.
- HTTP409 sonrası eski görüntünün korunması, yenilemeyle yeni revizyonun alınması ve eski retry'nin temizlenmesi.
- Unmount sonrası bootstrap'ın tercih restore etmemesi.

Ek LatestRead testi obsolete completion/pending durumunu sınar. Bu sekiz ek senaryoyla toplam96 frontend testi ve TypeScript/Vite üretim derlemesi geçti. Backend değişmedi; önceki667 Python testi bu tur tekrar koşulmadı. Fetch ve DOM test doubles kullanılır; gerçek TCP kopması veya tüm çok-sekmeli tarayıcı davranışları için genel kabul iddiası değildir. Backend idempotency kanıtları önceki API testlerine aittir; buradaki retry testi istemcinin aynı kimliği koruduğunu gösterir.

Yeni ana bundle index-HL1oVn8x.js; lazy FixtureLab-DGTH2RaE.js. Anahtarsız çizim erişimi korunur.

## Önceki tutamaç testi

[Tutamaç Chromium tekrar raporu](../../../reports/chart-handle-priority-retest-20261109.md) geçti: varsayılan ölçekte trend circle gerçek elementFromPoint hedefiydi; yalnız ilk ankraj doğru UTC'ye taşındı; üç hizalama örneği20/20 ve0 CSS px ile geçti. Kapsam headless kontrollü fixture'dır; native touch veya genel kullanıcı deneyimi kabulü değildir.

## Durum

Sayısal gösterge, kontrollü boşluk, native/SVG hizalama ve kayıt yarışlarında somut doğruluk kanıtları birikti. Genel grafik kabulü yine ayrı tutuluyor. Native touch ve bağımsız raster karşılaştırması yapılmış sayılmaz. UX yeniden tasarımı veya bot bağlantısı bu tur başlatılmadı.
