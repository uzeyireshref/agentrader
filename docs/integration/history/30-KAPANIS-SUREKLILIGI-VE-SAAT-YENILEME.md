# Kapanış sürekliliği ve bağlantıyı kesmeden saat yenileme

13 Kasım 2026 · D3 düzeltme adayı uygulandı; yeni30 dakikalık kabul arka planda sürüyor. Demo veri kaynağı değişmedi. Grafik kaynaklı emir, gerçek hesap ve dış mesaj yetkisi kapalı.

## Bulgular

Önceki1800.4 saniyelik gözlemde29 kapanış ve bir1m kapanış olayı boşluğu kaydedilmişti. Aynı raporun927.8–946.8 saniye penceresinde durum RECONNECTING, clock nedeni CLOCK_UNTRUSTED ve mum kalite bilgisi OK/missing_bars0 idi. Kodda saat örneği300000ms sonunda sona eriyor; bu durum WebSocket kapanışı ve REST seed'ine yol açıyordu. Geçmiş seed'i yeni sinyal üretmemesi için kapanışları yalnız closed_keys içine alıyordu. Böylece planlı saat yenilemesi kapanış sınırına denk gelince canlı kapanış zinciri kesilebiliyordu. Eski başarısız rapor korunur; demo fiyatlarının gerçek piyasadan farklı olması bu kusurun nedeni değildir.

Birleşik grafik/saat/gölge testinde ikinci kusur yeniden üretildi: kapanış çerçevesi zaman belirsizliği sınırını henüz aşmadığında CLOSED_TIME_UNPROVEN üretiliyor, gölge motoru bunu genel veri arızası gibi reseed işaretliyordu. Sonraki gerçek güncellemede bu kapanış başlangıç noktası sayılıp atlanabiliyordu.

## Düzeltmeler

- Saat kanıtı sona ermeden, dört dakika civarında ayrı bir public demo zaman sorgusuyla yenilenir. Sorgu ayrı thread'de çalışır; WS tüketimini veya geçmiş kilidini bekletmez. Ek kaynak yalnız demo /fapi/v1/time GET'tir; anahtar veya hesap gerektirmez.
- Yeni örnek aynı süreçte ölçülmüş, daha yeni, düşük belirsizlikli ve önceki saat tahmininin belirsizlik aralığıyla uyumlu olmalıdır. Epoch, generation, mumlar, data_revision, son alınma zamanı ve son kapanış değişmez. Kalp atışı veya saat sorgusu veri tazeliği yerine geçmez.
- Freshness/clock politika sınırları gevşetilmedi. Saat sıçraması, uzun kesinti, expired örnek, uyumsuz ölçüm veya resnapshot bariyeri saat yenilemeyle temizlenemez. Başarısız yenilemede eski geçerli kanıt kalır; sonunda güvenilirlik kaybolursa normal güvenli yeniden eşitleme uygulanır. Gecikmiş eski epoch sonucu veya durdurma sonrası sonuç uygulanmaz.
- Gerçek kesintide REST'ten bulunan kapanışlar ayrı RECOVERED_CLOSE / origin=REST_RESYNC / signal_eligible=false tanı kayıtları olur. Live close_event'e çevrilmez ve emir fırsatı değildir. Feed belleğinde en fazla1000 kayıt tutulur; gözlem raporu bunları ayrı kalıcı alana yazar. Bu, bütün piyasa olaylarının süreçler arası kalıcı günlüğü iddiası değildir.
- Gölge motorda yalnız CLOSED_TIME_UNPROVEN beklemesinde önceki değerlendirilen mum korunur. Sonraki doğrulanmış canlı örnek kapanışı bir kez değerlendirebilir. Kaynak, epoch, gerçek saat/veri hataları ve boşluklarda önceki reseed davranışı korunur. Geçmiş kapanış yeni sinyal yapılmaz.
- Paket tanı alanları clock_renewals, clock_renewal_failures ve son yeniden bağlantı nedenini taşır. Kaynak izlenebilirlik manifestine canlı gölge motoru ve public grafik adaptörü de eklendi.

## Doğrulama

1029 Python tam regresyon testi,331 frontend testi,36 izole replay senaryosu başarılı. Üretim frontend kaynakları değişmedi; mevcut derleme gerçek tarayıcıyla doğrulandı.

Yeni8 regresyon kontrolü:

1. 11 dakikalık deterministik akışta iki saat yenilemesi; epoch değişmeden11 ardışık1m kapanışı, REST geçmişi tekrar yüklenmeden.
2. Saat sorgusu beklerken WS kapanışının işlenmesi.
3. Yabancı/uyumsuz örneğin reddi ve eski güven süresinin uzamaması.
4. Wall-clock sıçraması ve snapshot bariyerinin korunması.
5. Eski epoch için geciken sonucun reddi.
6. REST kapanışlarının ayrı, tekrarsız ve sinyale uygun olmayan kaydı.
7. Durdurma sonrası sonucun uygulanmaması.
8. Üç saat yenilemesi boyunca gerçek FeedState → veri kanıtı → binding uygunluğu → ShadowTracking zinciri; kapanış belirsizliğinde checkpoint korunması ve sonraki gerçek güncellemede tek TOUCH.

Gerçek demo REST/WS + izole HTTP/tarayıcı kabulü: BTC/ETH ×1m/5m/1h/1d geçmiş,300 görünür mum/Canlı, iki gerçek1m kapanışı, sadece demo ağ adresleri ve execution sentinel'in değişmemesi geçti. İzole gölge tarayıcı/arka plan işçisi kabulü tekrar geçti. Bu kısa deneyler30 dakikalık kabulün yerine geçmez.

## Devam eden gözlem

reports/demo-continuity-observation-20261113.json yeni adayın canlı raporudur. Önceki reports/demo-observation-20261113.json ve before-gap-fix kaydı değiştirilmedi. Yeni süreç kendi geçici piyasa deposunu kullanır; hesap veya execution deposunu açmaz ve1800 saniyede otomatik biter.

Kabul ölçütü aynı kalır: canlı doğrulanmış kapanışlar arasında boşluk olmamalı, toparlanma penceresi30 saniyeyi aşmamalı,30 dakikada en az29 kapanış görülmeli. RECOVERED_CLOSE kayıtları canlı kapanış sayısına katılmaz; bir boşluğu geçmiş olayla doldurup PASS üretmek yoktur. RUNNING/passed=null kabul tamamlanmadı demektir. İlk gerçek gözlemde iki saat yenilemesi, yeniden bağlantı olmadan kaydedildi; tam sonuç henüz bekleniyor.

Ana terminal http://127.0.0.1:8765 yeni backend ile yeniden başlatıldı. Tarayıcı kapalıyken gölge motoru backend açık olduğu sürece çalışır; gerçek demo veya gerçek para emri gönderilmedi. D3 kapanmadan B3 açılmaz. Kaynak değişiklikleri commit edilmedi.

## Kanıtlar

reports/continuity-python-tests.txt, reports/continuity-frontend-tests.txt, reports/continuity-unit-tests.txt, reports/continuity-replay-tests.txt, reports/continuity-http-validation-output.txt, reports/continuity-shadow-validation-output.txt ve reports/demo-continuity-observation-20261113.json.

[Önceki gözlem ve B2 teslimi](29-SINYALDEN-PLAN-ONIZLEMESI.md) · [Ana entegrasyon planı](26-DEMO-VERI-VE-GRAFIK-BOT-ENTEGRASYON-PLANI.md)
