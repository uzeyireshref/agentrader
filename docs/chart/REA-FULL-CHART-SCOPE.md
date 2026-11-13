# REA — bütün grafik kapsamı

10 Kasım 2026, kullanıcı düzeltmesi. Önceki araştırma mevcut araçlar ve T04–T14 çekirdeğine fazla daraltılmıştı. Asıl kapsam TradingView grafik ortamını, bizde bulunmayan yetenekler dahil ayrıntılı çözümlemek ve sonra kendi grafiğimiz için yeniden kurulum planı çıkarmaktır. Önceki bulgular geçerlidir; kapsamın tamamlanma kanıtı değildir.

## Araştırmanın ana sırası

1. Grafik ortamının tam yetenek envanteri: her araç grubu açılarak görülen bütün alt araçlar; grafik türleri, göstergeler, menüler, bağlam menüleri, panel ve çalışma alanları. İsimler tahminle doldurulmaz; erişim/abonelik/sürüm sınırı yazılır.
2. Her yeteneğin araştırma fişi: amaç, girişler, geometrisi/hesabı, oluşturma ve düzenleme durumları, ayarlar, görsel durumlar, kalıcılık, kısayol, veri bağımlılığı, hata/sınır durumları, kaynak kanıtı ve bilinmeyenler.
3. Görsel sistemin tam çözümlemesi: yerleşim, ölçüler, renk/tema, tipografi, ikon/çizgi dili, eksen/etiket/grid, menü/dialog/tooltip, nesne seçimi, pane düzeni, ekran boyutu ve DPR davranışı.
4. Kaynak/runtime eşlemesi: elde edilen istemci modülleri, render ve interaction yolları, hesap yardımcıları, kaynak kimliği/hash, veri akışı, olay/kayıt yaşam döngüsü. Sunucu iç işleyişi gözlenmediyse bilinmiyor kalır.
5. Bütün envanterin bizim uygulamaya eşlenmesi: mevcut, kısmi, eksik, veri/motor/altyapı gerektiren. Bu karşılaştırma araştırmanın başlangıç filtresi değildir.
6. Yeni geliştirme programı: tam yetenek haritasından sürümler ve bağımlılıklar çıkarılır. Önceki 21 paket başlangıç envanteridir; kapsam tavanı değildir. Uygulama sırası kalite ve bağımlılıklarla belirlenir.

## Zorunlu inceleme alanları

| Alan | Araştırma kapsamı |
| --- | --- |
| Çizim aileleri | Cursor, çizgi/ray/uzatma, bütün kanal ve pitchfork varyantları, Gann/Fibonacci, pattern/Elliott, tahmin/ölçüm/pozisyon, hacim tabanlı araçlar, geometrik şekiller, fırça/yol, metin/not/etiket/tablo, ikon/sembol ve ilgili alt araçlar. Gerçek menü adları ve erişim kanıtı envantere işlenir. |
| Nesne davranışı | Araç bazlı anchor/tutamak, snap, Shift/Ctrl davranışı, oluşturma, seçme, taşıma, iptal, sayısal edit, stil, görünürlük, kilit, clone/copy, sıralama, gruplama, şablon, undo/redo, kayıt/yenileme. |
| Grafik türleri | Mum ve bütün menüdeki alternatif türler; fiyat üretimi/dönüşümü, veri gereksinimi, boşluk/zaman semantiği, gerçek fiyatla sentetik fiyat ayrımı. |
| Göstergeler | Yerleşik kategorilerin envanteri; parametre/edit/style/pane/timeframe/offset/warmup/reset; hesap ailesi bazında bağımsız doğrulama. Katalog envanteri ile her göstergenin formülünün doğrulanması ayrı durumlar taşır. |
| Fiyat ve zaman | Tüm ölçek modları, ters ölçek, auto/manual/fit, hassasiyet ve label çakışması; interval seçenekleri/custom interval, session/timezone ve crosshair/OHLC ilişkisi. |
| Navigasyon | Fare/klavye/trackpad, zoom/pan/sağ boşluk, canlıya dön/reset, go-to-date/range, fullscreen, arama, tool hotkeys ve focus yönetimi. |
| Pencere/pane | Çoklu grafik/layout düzenleri, karşılaştırılan semboller, senkronizasyon, gösterge pane'leri, boyutlandırma/taşıma; hesap sınırları kaydedilir. |
| Yardımcı paneller | Watchlist, nesne ağacı, data window, gösterge/çizim ayarları ve şablonlar, replay, grafik alarmlarının semantiği; görünürlük ve kalıcılık. |
| Veri/runtime | History, açık/kapalı mum, hacim ve fiyat kaynakları, güncelleme, reconnect/stale/boş veri, performans ve kaynak yaşam döngüsü. |
| Tasarım | Tüm grafik yüzeyinin görsel dili ve her öğenin normal/hover/selected/focus/disabled/loading/error durumları; açık/koyu ve responsive davranışlar. |

Bu alanlar ürünün gerçekten erişilen sürümündeki tam menü/envanterle genişletilir. Liste, henüz incelenmemiş özelliklerin mevcut olduğu veya tamamlandığı iddiası değildir. Sosyal içerik/katalog büyüklüğü ile grafik motorunun yetenekleri ayrı tutulur; kullanıcı için ana hedef grafik ortamıdır.

## Çıktılar ve tamamlanma

- Tam yetenek kataloğu: kimlik, aile, arayüzdeki ad, erişim, kanıt, araştırma durumu, bizim karşılığımız ve bağımlılık.
- Ayrıntılı teknik ve görsel araştırma fişleri; kaynak kanıtı ve tekrarlanabilir örnekler.
- Ortak hesap/geometri/etkileşim/veri/kayıt tasarımı; yeni gereken altyapılar.
- Kapsamlı uygulama yol haritası ve işlevsel/görsel kabul matrisi.

Mevcut REA03 tam kabulü verilmez. REA04 bu geniş envanter tamamlanmadan kesinleşmez. Eski T04 başlangıç sırası bağlayıcı kabul edilmez; yeni yol haritasında yeniden değerlendirilecektir. Önceden tamamlanmış kod ve kanıtlar silinmez. Bu aşamada ürün grafiği değiştirilmez.
