# P4 — Revision bağlı araç/kural tanımları

12 Kasım 2026. P4 tamamlandı. Paneller → Araç / kural bağları üzerinden çizim veya gösterge sürümüne bağlı, devre dışı kural tanımı kaydedilebilir. Plan 23/27; sıradaki P5 uygunluk değerlendirmesi ve nedenli engellerdir.

## Davranış

Tanım owner/workspace, hedef kimliği ve revision’ı, hedef snapshot’ı, piyasa/interval/LINEAR bağlamı, dondurulmuş zaman grid’i, sorgu/çıktı, kural, kanıt ve SHA256 parmak izlerini taşır. Varsayılan DISABLED; yalnız DISABLED ve STOPPED durumları bulunur. Kapanmış mum ve açık yeniden bağlama politikası zorunludur. Sayısal parmak izleri Python/JavaScript arasında IEEE754 gösterimiyle eşleşir; hash yetkilendirme imzası değildir.

Düzenleme, silme, undo/redo, toplu işlem ve şablon restore hedef revision’ını değiştirdiğinde eski bağ aynı veritabanı transaction’ında STOPPED olur. Sonraki değişiklikler onu kendiliğinden açmaz. Kullanıcı güncel hedefe açıkça yeniden bağlar. Stil/etiket/kilit/gizleme de revision değiştiriyorsa durdurur; aynı gösterge ayarının değişmeden kaydı başka hedefin bağını durdurmaz. Silinmiş hedef denetim geçmişinde kalır ve geri getirilmeden yeniden bağlanamaz.

Kayıp ACK yeniden denemesi aynı request/binding kimliği ve ilk dondurulmuş grid ile yapılır. Önbellekteki ACK ilk işlemin tarihsel sonucudur; güncel STOPPED başlığını değiştirmez. Arayüz yazma ardından güncel listeyi okur. 409, geç yanıt, coin/interval/ölçek değişimi ve kanıt yenileme hatası kayıt güvenliğini korur. Katalog yüklenemezse kayıt kapanır.

## Kapsam ve sınırlar

Kanıt kataloğu 12 çizim ve 8 gösterge türünü kapsar: yatay/çizgi/ray/uzatılmış çizgi, bölge, iki Fib, kanal, long/short planı, cetvel; EMA/SMA/RSI/ATR/MACD/BB/session ve anchored VWAP. Desteklenen her sorgunun hesap temeli, fixture ve kaynak SHA256 izi vardır. Runtime kaynak değişikliği kataloğu BLOCKED yapar; build_binding_evidence.py ile bilinçli yeniden üretim gerekir. Bu izler veri gerçekliği veya tam TradingView eşitliği kanıtı değildir.

Kanonik PRICE çıktıları gözlem/yaklaşma/dokunma/kapanış geçişi tanımı alabilir. Gösterge ekran değerleri, metrikler, içerme ve hipotetik plan hesapları yalnız gözlem tanımı alır. Metin/etiket ve uygulanmamış Fib projection açıkça desteklenmez. Anchored VWAP kayıtlı, doğru sembole ait anchor gerektirir. LOG tanımı kapalıdır. Yaklaşma toleransı pozitif mutlak fiyat, gözlem ve kapanış geçişi toleransı sıfırdır.

P4 hiçbir kuralı çalıştırmaz. Başlangıç grid’i ve istemci snapshot hash’i yalnız referanstır (CLIENT_REFERENCE_NOT_ELIGIBILITY). Veri tazeliği, origin/clock/session kanıtı ve canlı uygunluk P5 kapsamındadır. Bot tanımı okuyabilir; hedef yazma/düzenleme, çalıştırma ve emir yetkisi kapalıdır. Aktifleştirme endpoint’i bulunmaz.

## Kalıcılık ve doğrulama

Migration 6 immutable bağ revision/head tablolarını ekler; mevcut veritabanı yükseltmesinde normal yedekleme uygulanır. Workspace başına 100 bağ; beklenen kayıt revision’ı 1000’den küçük olmalıdır, durdurma revision’ı 1000 olabilir. Testler izole veritabanı ve sentetik piyasa akışı kullanır.

839 Python ve 263 frontend testi; üretim derlemesi; 16 yeni P4 tarayıcı kontrolü ve 29 G04/T14 regresyon kontrolü geçti. Gerçek form düzenleme, undo/redo, silme/geri getirme, gösterge ayarı, şablon restore, ACK kaybı/yeni mum, 409/yenileme, geç bağlam yanıtı, reload/restart ve 1024 açık/koyu tema kapsandı. Görseller incelendi. Mevcut 500 kB bundle uyarısı sürer; performans kabulü QA01’de açıktır.

Kanıtlar: [tarayıcı raporu](../../reports/chart-p4-validation-20261112.json), [teslim manifesti](../../reports/chart-p4-delivery-20261112.json), [sözleşme](contracts/bindings-v1.json).
