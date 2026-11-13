# Alarm — ilk uygulama grubu

13 Kasım2026. Yerel uygulama http://127.0.0.1:8765 . Üst çubukta Göstergeler yanında Alarm düğmesi var. Son paket index-CKqY7Fns.js.

## Çalışan kapsam

Kalıcı sabit fiyat alarmları; seçilen Binance USD-M son fiyat verisinin kapanmış mumları. Kesişme, yukarı/aşağı kesişme ve üzerinde/altında koşulları. Kesişme: önceki kapanış strict karşı taraftayken yeni kapanış seviyeye ulaşır/geçer; above/below strict karşılaştırmadır. Bir kere veya her uygun mum kapanışı; isteğe bağlı bitiş, ad ve düz metin mesaj.

Oluştur/düzenle/duraklat/devam/sil, revision conflict koruması, aktif/duraklatılmış/tetiklenmiş/süresi dolmuş listeleri ve kalıcı son100 tetikleme kaydı. Silinen alarmın geçmişi korunur. Düzenle ve devam işlemi yeni baseline alır; eski mumları geriye dönük tetiklemez.

Backend worker aktif alarmın feed referansını kendi tutar. Grafik istemcisi gerektirmez; sunucu süreci kapanırsa izleme durur. Restart, epoch değişimi, stale veri dönüşü ve atlanmış kapanış sonrası baseline yeniden kurulur; gap içindeki kaçırılmış olaylar üretilmez. LIVE, FRESH, qualityOK, doğru pazar kimliği ve verified exact kapanış gerekir. Güncel veri yoksa WAITING_DATA gösterilir. Kaynak edinme başarısızlığı izlemeyi etkinmiş gibi READY yapmaz.

Olay ve son işlenen kapanış aynı SQLite transactionında kaydedilir. Kimlik owner/alert/revision/candle_time üzerinden üretilir; aynı kapanışın tekrarında ikinci olay yok. Tek sefer alarmı TRIGGERED olur. Depo uygulama veritabanıdır; execution deposuna yazılmaz. Replay motorunun namespace/otorite sınırları değiştirilmedi.

## Doğrulama

- Tam backend934 test geçti; son eklenen bağımsız gerçek worker-thread testi dahil alarm hedefli8 test geçti. Ek thread testi hiçbir HTTP/grafik istemcisi olmadan sentetik kapanışla olay üretti ve referansları bırakıp kapandı.
-304 frontend testi, TypeScript ve Vite üretim derlemesi geçti; mevcut500kB chunk uyarısı sürüyor.
- Gerçek Chrome/üretim bundle: üst düğme, create, doğru koşul kaydı, revisionlı pause/resume, fiyat edit, boş geçmiş, delete ve modal cleanup geçti. reports/alerts-ui-20261113/result.json; ekran PNG aynı klasörde. Test API/WebSocket verileri izole, kullanıcı çalışma alanına test yazımı yok.
- Gerçek TestClient API: create/pause/restart/conflict/edit/delete ve execution DB oluşmaması. Saf motor: dedup, owner izolasyonu, kalıcılık, expiry, stale/epoch/gap reseed, once, bozuk giriş.
- Yerel sunucu güncellendi; gerçek GET /api/alerts price-alerts/1 döndürüyor, runtime_error=null, order_authority=false. Gerçek piyasada fiyat tetiklenmesi/uzun kesinti testi yapılmış sayılmaz.

## Açık kapsam — alarm aşaması bütünü tamamlanmadı

İlk sürüm yalnız kapanmış mum ve sabit fiyat. Gösterge/çizim operandı, mum içi/per-minute sıklık, bildirim takvimi, popup/ses/webhook/email, mesaj placeholderları ve bot emir köprüsü henüz yok. Tetikleme şu an kalıcı yerel geçmişe gider; harici teslim yapılmaz. Yeni DISPLAY_ONLY kanal/pitchfork araçlarına hesap yetkisi verilmedi. Bunlar REA-ALERTS-RESEARCH.md planına göre sonraki uygulama gruplarıdır.
