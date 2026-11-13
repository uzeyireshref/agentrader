# Canlı araştırma: veri tablosu ve sayısal gösterge doğrulaması

11 Kasım 2026, Asia/Baku. REA03 devam ediyor; ürün kodu değiştirilmedi. Araştırma Chrome profili yeniden açıldı ve mevcut hesap/düzen korundu. Yeni CDP hedefi 88FD717BF52813260755FF7B1F987BEB. Önceki oturumun 234 kayıtlık paketi ayrı kalır; bu oturumun paketi 21 kayıt/3,317,728 byte içerir. Kayıt sayıları kapsam veya test başarısı sayısı değildir.

Kanıt: reports/rea-chart/rea-evidence-table-parity-20261111.json.

## Deneyler

| Kayıt | Gözlem / hesap | Kanıt |
| --- | --- | --- |
| N10 | Yeniden açılan kayıtlı REA Araştırma, BTCUSDT.P/1D, Volume+BB20/SMA/close/2 | ev_0228dd6ab0c8f9f4b74b2399a41cc4db18c0c5013fff841db7f05ef260389f04 |
| N11 | Chart context → Table view: tarih, OHLC, değişim, hacim ve BB çıktıları aynı satırda | ev_bd7d6849a532513041e03af46e46c7f43ba269b0f167de683af16359a576b894 |
| N12 | 10 Ekim–10 Kasım arasındaki32 kapanmış günlük mum; BB20 bağımsız hesap karşılaştırması13/13 satır,39 çıktı | ev_263ac7cb63f33275c8fd99acd4cafc66780cc6b11ea128b12319ad1105205878 |
| N13 | Download data dialogu: chart+indicators CSV, UTC/UNIX timestamp. Download sonrası Basic→Plus yükseltme ekranı; dosya alınmadı | ev_176584e1e862afd6c30e049b2d21b542ed58c29118c489efb48e4b5395fbc6f2; ev_da78c12cc0c472eaf73e3c7442a2ee528c26ca197b84cdb942d27141927af80e |
| N14 | BB5/SMA/close/2, Offset+2: kapanmış kaynak mumlarından28/28 çıktı satırı,84 değer uyumlu | ev_9c6d4f056082a47bc793ffe652ffbdbea2bf93129dca84b53215a78344b1399a |
| N15 | BB20/EMA/close/2, Offset0:31/31 ardışık EMA güncellemesi ve13/13 band satırı uyumlu | ev_1caf65467922fe24605b8bd5b2d044eedef71fb2ab5598d7f4b19db020bef555 |
| N16 | Tablo + veri penceresi görsel kaydı | ev_529c7d3118bd4df20d5706697dacb28b270b231df39db44bb6d6fab33e0f0723 |
| N17 | BB20/SMA/close/2, Offset0 geri getirildi; Ctrl+S sonrasında All changes saved; çizimler global gizli | ev_ffaa2d5e2c7a32d4241c976452834623886353537f76ba29535eeb6ab2c56442 |

## Sonlu pencere hesabı: BB20

Ham araştırma örneği: reports/rea-chart/bb-closed-parity-20261111.json. En yeni11 Kasım mumu açıktı, bütün sabit karşılaştırmalardan çıkarıldı.32 kapanmış mumdan ilk19'u yalnız pencere girdisidir;29 Ekim–10 Kasım arasındaki13 satır karşılaştırıldı. UI fiyat ve çıktı precision0.1; mutlak çıktı toleransı0.05. En büyük fark0.0495153. Bu bir ürün testi veya tam TradingView eşitliği değildir.

Her20 kapanış için basis=ortalama(close), dev=sqrt(sum((close-basis)^2)/20), upper=basis+2*dev, lower=basis-2*dev.39 değerin tamamı tolerans içinde. N−1 ile örneklem standart sapması kullanıldığında üst bant hatası yaklaşık70–132 fiyat birimi oluyor; bu örneklerde N böleni açıkça ayrışıyor.

10 Kasım örneği: basis78160.785→78160.8; upper82941.1468546→82941.1; lower73380.4231454→73380.4. Hacim K olarak kısaltılmıştır; tam hacim olarak kullanılmaz. Serinin tüm geçmişi veya borsa kaynak eşitliği doğrulanmış değildir.

## Offset hesap zamanı değildir

reports/rea-chart/bb-offset-parity-20261111.json. BB length5/offset+2 ile28 kapanmış kaynak mumunun hesapları iki günlük sonraki gösterim satırına uydu.10 Kasım kapanmış kaynak hesabı12 Kasım satırında: basis75111.9, upper76651.0, lower73572.8.12 Kasım OHLC/değişim/hacim hücreleri boş.13 Kasım satırı açık11 Kasım hesabını taşıdığı için sabit doğrulamaya katılmadı.

Bu gelecekte fiyat gözlendiği anlamına gelmez. Çizim zamanı ile hesap kaynak zamanı ayrılmalı; bot sorguları kaydırılmış render satırını geleceğe ait OHLC diye değerlendirmemeli. Takvim boşlukları/seanslı piyasada iki barın iki gün olmadığı ayrıca test edilmeli.

## EMA: güncelleme doğrulandı, başlangıç açık

reports/rea-chart/ema-recurrence-parity-20261111.json. Aynı32 kapalı mumda EMA20 basis okundu. alpha=2/21; next=alpha*close+(1-alpha)*previousEMA. Önceki EMA da0.1 precision ile okunduğu için tolerans0.05*(1-alpha)+0.05=0.0952381.31 güncellemenin tamamı uydu, maksimum fark0.0666667. Bu karşılaştırma ilk EMA seed'ini belirlemez; SMA seed/ilk fiyat seed, warmup, NA ve geçmiş ekleme davranışı hâlâ açık.

BB EMA basis üst/alt bandı, son20 kapanışın aritmetik ortalama çevresindeki population dev'inin EMA basis'e eklenmesi/çıkarılmasıyla13/13 satırda uydu. Yuvarlanmış EMA+çıktı toleransı0.1. Standart sapmayı EMA çevresinde almak eşdeğer varsayılmamalı. Standalone EMA göstergesi ile mevcut ürün implementasyonu henüz karşılaştırılmadı.

## Menü, veri ve tasarım birlikte

Table view, context menüsünden ulaşılabilen ayrı bir analiz yüzeyidir. İki seviyeli başlık veri kaynağını ve OHLC/gösterge sütunlarını gruplar; tarih satır başlığıdır. Sağ Data window tek mum ayrıntısını korur. Grafiğe dönüş, indirme ve chart kimliği görünür. Sayılar hücrelerde sağa hizalıdır; ince çizgiler yoğun veriyi ayırır. BB sütunları ekranda yatay alanın dışına taşabiliyor; erişilebilirlik ağacında bulunmaları görsel olarak ekrana sığdıklarını kanıtlamaz. Yatay gezinme ve sabit başlık/tarih davranışı tam doğrulanmadı.

768/1024 responsive kabulü bu tur yenilenmedi. Attached screenshot1920×970 içinde uygulama daha dar bir alanda kaldı; önceki viewport sınırı sürüyor. Referansın geçici boş tablo satırları async yüklenmeden sonra doldu. Bizim üründe loading/empty/error ayrı durumlar ve açık mum işareti gerekir. Tarih+OHLC+gösterge erişilebilir tablo, hata ayıklama ve sayısal doğrulama için yararlı kapsam adayıdır; tüm ekranı kaplayan tablo ilk çekirdek için otomatik zorunlu değildir.

PageDown grid üzerinde gönderildi ama o adımın yakalamasında satırların değiştiği gösterilemedi; daha sonra imleç eski tarihe geçti. Bu deney başarılı tablo sayfalama veya klavye izolasyonu kabulü değildir. Yeni bir focus/scroll inceleme sorusu olarak kalır. Bazı menu eylemleri async geçişte timeout oldu; sonradan okunan gerçek durumla düzeltildi. Timeout kayıtları başarılı eylem sayılmadı.

## Plana aktarım

1. T09/T10 gösterge işi ve BB kapsam genişletmesi: aynı sabit veriyle finite-window BB golden örnekleri; population variance, basis türü, source, offset, yuvarlama toleransı; recursive EMA seed/warmup ayrı kabul.
2. Veri sözleşmesi: hesap timestamp'i, render offset'i, open/closed durumu ve boş çıktı hücresi farklı alanlar. Compact K hacmi kanonik hacim değildir.
3. Tasarım: okunur Data window çekirdekte; çok mumlu tablo ve CSV ihtiyaca göre ikinci aşama. Görünür sayı formatı, erişilebilir etiket ve kanonik değer farklı temsil katmanlarıdır.
4. Menü/focus: tablo açıkken gezinme kısayollarının grafiğe sızması ayrıca test edilmeli; sadece eylem completed cevabı yetmez.
5. ATR/RSI/VWAP kapalı veri parity, EMA başlangıcı, history/reconnect/stale/symbol-interval yarışları ve pointer/performance hâlâ açık. REA04 nihai plan konsolidasyonu yapılmadı; eski tamamlanmış5 görev korunur.

Son durum: görünür araştırma Chrome açık; BTCUSDT.P/1D, Volume+BB20/SMA/close/2, Offset0/UTC; dört önceki çizim global gizli, geçici yeni çizim yok, saved doğrulandı. Ürün geliştirmesi başlamadı.
