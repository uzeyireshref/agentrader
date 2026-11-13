# Canlı veri tazeliği ve eşitleme

9 Kasım 2026. Veri doğruluğu önceliğinde, açık soketin mutlaka güncel veri anlamına gelmediği durumlar test edildi. Bu tur masaüstüne görev aktarılmadı.

## Yeniden üretilen hatalar

1. Tazelik kontrolü yalnız socket.receive() timeout/None döndüğünde çalışıyordu. Sürekli eski/tekrarlanan frame gelirse kabul edilen mum güncellenmese bile yeniden bağlantı başlamıyordu. Kontrollü testte bir bağlantıda kaldı; beklenen ikinci bağlantı ve force REST seed oluşmadı.
2. Olay zamanı son kabul edilenden büyük olsa bile olay çok gecikmiş olabiliyordu. Bu paket received_at zamanını yenileyip durumu LIVE yapabiliyordu. Kontrollü testte 30 saniye gecikmiş olay reddedilmedi.

## Düzeltme

SharedFeed artık her receive dönüşünde, frame None olsa da olmasa da son kabul edilen veri tazeliğini kontrol eder. Mevcut 20 saniyelik eşik korunur; eşik aşılınca soket kapanır, RECONNECTING ve force=True REST eşitlemesi uygulanır. Duplicate trafik watchdog'u atlayamaz.

FeedState.seed sırasında REST server_time ile yerel clock başlangıcı birlikte kaydedilir. Yeni olayın E zamanı, bu borsa zamanına eklenen geçen süreyle karşılaştırılır; 20 saniyeden fazla gecikmiş olay mum/sequence/received_at/close_event değiştirmeden yeniden eşitleme ister. Yerel epoch ile borsa epoch'unun aynı olduğu varsayılmaz. Burada geçen süre mevcut enjekte edilen clock üzerinden ölçülür; işletim sistemi saat sıçramaları ayrıca modellenmedi. İleri tarihli olay sınırı bu turun kapsamı değildir.

Önceki duplicate/out-of-order ve closed-bar koruması devam eder. Kapanış atlanması veya eksik mum normal tek-bar append yoluyla örtülmez; mevcut REST resync davranışı korunur. Tarihsel kapanışlar yeni canlı sinyal olarak üretilmez.

## Doğrulama

Yeni dört deterministik test: kesintisiz duplicate akışının iki bağlantı/iki force REST seed üretmesi ve soketleri kapatması; artan fakat gecikmiş olayın state'i tazelememesi; kısa jitter sonrası güncel olayın çalışması; yerel ve borsa epoch farklıyken doğru kabul. İlk ikisi düzeltme öncesi başarısız, sonrası başarılı oldu. Kontrollü clock/soket doubles kullanıldı; uzun süre gerçek paket bozulması enjekte edilmiş kabul edilmez.

671 Python testi, atlanan test yok; izole HTTP/worker/restart ve mevcut execution/risk korunması geçti. [Tam rapor](../../../reports/chart-workspace-validation-20261109.json).

[Gerçek public probe](../../../reports/chart-live-validation-20261109.json): 504 desteklenen piyasa, 300 BTCUSDT/15m mumu, LIVE ve geçmiş pagination geçti. Hesap isteği0, emir0. Bu kısa kontrol uzun oturum garantisi veya bütün piyasalarda gecikme ölçümü değildir. Frontend kodu bu tur değişmedi; önceki96 frontend testi yeniden koşulmadı.

Ana yerel sunucu kimliği kontrol edilerek yeni Python koduyla aynı8765 portunda yeniden başlatıldı. Anahtarsız yerel çizimler sürer; kullanıcı çizimleri temizlenmedi. Şema veya işlem yetkisi değişmedi.

Genel grafik kabulü kapatılmadı. Native touch/görünür kullanım ve raster piksel kapsamları, bu veri akışı testinden ayrı tutulur. Bot bağlantısı yapılmadı.
