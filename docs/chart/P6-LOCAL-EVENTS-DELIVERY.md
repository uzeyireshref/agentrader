# P6 — Kalıcı semantik olay ve yerel intent

13 Kasım 2026. P6 tamamlandı. Replay alanında üretilen yerel domain olayı, yerel teslim intent’i ve phase aynı uygulama veritabanı transaction’ında kalıcılaştırılır. Grafikte **Paneller → Yerel olay geçmişi** salt okunur denetim ekranıdır. Üretim feed’ine olay üreticisi bağlanmadı; sürekli worker, gerçek kanal, hesap veya emir aktivasyonu yoktur. Sıradaki P7 izole kuru çalışma ve entegrasyon kararıdır.

## Kalıcı köprü

Migration 7, local event/intent/phase ve SQLite fake receipt tablolarını ekler. Mevcut uygulama DB yükseltmesi normal migration yedeğini alır; önceki migration checksum’ları değiştirilmez. Execution DB’ye migration veya yazma yapılmaz.

Hazırlanan girdide binding revision/hash ve donmuş context taşınır. Commit BEGIN IMMEDIATE içinde güncel binding ve hedef head’ini yeniden okur; DISABLED durum, revision/hash ve P5 uygunluğu tekrar doğrulanır. Kilit bekleme süresi alım/kaynak yaşına eklenir, saat sapması ve belirsizlik denetlenir. Eski kanıt veya edit/delete/undo/rebind yarışı yeni olay oluşturmaz. Uygulama DB snapshot’ı ile donmuş piyasa kanıtı iki ayrı kaynaktır; çapraz DB atomiklik iddiası yoktur.

Semantik unique key owner/workspace, binding/rule/target revision kimliği, market/query, kapanmış mum zamanı, olay türü/yönü ve episode’dan türetilir. Request_id, stream epoch/generation, data revision, snapshot hash veya taşıma sıra numarası olay anahtarı değildir. Domain kimliği replay alanından bağımsızdır; yerel event_id namespace ile ayrılır. Aynı domain izi iki replay alanında aynı domain ID ve farklı yerel kayıt üretir. Düzeltilmiş veri aynı semantik olay için ikinci intent veya geçmiş kanıtın üzerine yazma oluşturmaz.

Event, PENDING_FAKE intent ve kalıcı phase birlikte commit edilir. Tekrar köprü, restart veya iki eşzamanlı kayıtçı tek kalıcı çift bırakır. Commit öncesi çökme üç kaydı da geri alır; commit sonrası ACK kaybı kalıcı çifti kaybetmez. Başka binding ayrı olaydır. Yeni mum veya restart latch’i temizlemez; P4 EXPLICIT yeniden bağlama politikası korunur.

## Sürümlü yerel olay profili

CLOSED_EXPLICIT_REARM/1 yalnız kanonik çizim PRICE sorgularını ve kapanmış mumları kullanır. P5 OBSERVE_ONLY/BLOCKED sonucu olay üretmez. Exact decimal/rational hesap yapılır; float epsilon veya sessiz yuvarlama yoktur.

Her mumun seviye sorgusu o mumun UTC başlangıç timestamp’inde değerlendirilir. TOUCH: güncel kapanmış mumun low/high aralığı tolerans bandıyla kesişir; önceki kapanış bandın dışındadır. APPROACH: aynı taraftaki önceki kapanış yaklaşma bandının dışındayken yeni kapanış bandın içine girer ve uzaklık azalır; seviye teması veya seviyenin diğer yanına gap yaklaşma sayılmaz. CLOSE_CROSS: önceki kapanış seviyenin karşı tarafında veya üzerinde eşitken yeni kapanış kesin olarak diğer tarafa geçer. ABOVE/BELOW geliş yönünü filtreler; ANY hesaplanan yönü saklar. Çizgi/Fib/kanal kendi query zaman kapsamı dışında extrapolate edilmez.

İlk replay episode’u explicit olarak ARMED başlar; olaydan sonra TOUCH_LATCHED, APPROACH_NOTIFIED veya CROSS_LATCHED kalıcıdır. Bu profil otomatik cooldown/rearm, intrabar yol veya vendor parity iddiası taşımaz. Eski DRY-RUN-PLAN’daki daha geniş otomatik cooldown profili ve bütün 36 DR senaryosunun gerçek motorda yürütülmesi P7’de sürümlenip değerlendirilmelidir; P6 bunların genel kabulü değildir. Canlı tarihsel seed/catchup olay üreticisi yoktur.

## Sabit sahte alıcı

Teslim yalnız açık internal test çağrısıyla yapılır; arka plan döngüsü yoktur. PENDING_FAKE → IN_FLIGHT_FAKE claim’i transaction ile tektir. Gönderimden önce revision tekrar kontrol edilir; bu kontrol ve kalıcı fake receipt aynı transaction’dadır. Hedef kuyruktayken veya claim’den sonra değişirse CANCELED_SUPERSEDED olur, fake receipt oluşmaz. Bilinen sahte teslim DELIVERED_FAKE’tir; sonradan değişen hedef daha önce kaydedilmiş receipt’i geri çağırmaz.

Commit sonrası alındı bilgisi kaybolursa veya claim/send sırasında süreç ölürse sonuç belirsizdir. Açık recovery IN_FLIGHT_FAKE’ı DELIVERY_UNKNOWN yapar; otomatik yeniden gönderim yoktur. Bir fake receipt bulunması, bilinmeyen teslimi gerçek kanal için exactly-once saydırmaz. Gerçek teslim alıcısı veya adapter eklentisi bulunmaz; SQLite fake sink sabittir.

## Arayüz ve API

GET /api/workspaces/{workspace_id}/local-events yalnız owner/workspace ve replay:<run_id> alanındaki son 1–100 kaydı okur (ekranda 50). Live namespace reddedilir. Event üretme/dispatch/recovery için HTTP endpoint yoktur. Panelde namespace filtresi, durum, UTC mum zamanı, bağ sürümü, deneme sayısı, domain/local ID ve kanıt SHA256 görülür. Belirsiz teslim kırmızı ve açık açıklamalıdır. Boş alan, hata veya geç eski alan yanıtı önceki başarıyı yeni alana taşımaz. Açık/koyu tema ve 1024/1536 görünümü incelendi.

Normal önizlemede izole test kayıtları bulunmaz; boş geçmiş beklenen durumdur. Deneme kayıtları yalnız testlerin geçici DB’sinde oluşturuldu.

## Doğrulama

873 Python ve 272 frontend testi; üretim derlemesi geçti. 19 P6 Python test grubu atomiklik, semantik dedup, iki kayıtçı/teslimci yarışı, revision yarışları, ayrı bağ/namespace, latch/rebind, saat bekleme, saf kural semantiği, salt okunur HTTP ve gerçek subprocess os._exit çökmesini kapsar. Çökmeler commit öncesi/sonrası, delivery claim ve fake-send sonrası denenir. Dört frontend testi malformed/authority yanıtlarını, belirsiz teslimi, hata sonrası temizlemeyi ve unmount sonrası geç yanıtı doğrular.

12 P6 üretim tarayıcı kontrolü ve 11 P5 regresyon kontrolü geçti. Kalıcı beş intent durumu, namespace, boş/hatalı/geç yanıt, iki tema, salt okunur istekler, restart ve execution DB byte hash’inin değişmemesi doğrulandı. Gerçek mesaj/account/order/execution yazma sıfırdır. Mevcut 500 kB bundle uyarısı ve QA01 performans kabulü açıktır.

[Tarayıcı kanıtı](../../reports/chart-p6-validation-20261113.json) · [Teslim manifesti](../../reports/chart-p6-delivery-20261113.json) · [Makine sözleşmesi](contracts/local-events-v1.json)
