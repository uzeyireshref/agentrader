# Bot terminali tasarım düzeltmesi ve tarayıcı kontrolü

Güncel yerel Demo entegrasyonu ve çalıştırma: [INTEGRATION.md](INTEGRATION.md). Aşağıdaki bölüm 16 Kasım prototip tesliminin tarihsel kaydıdır.

16 Kasım 2026. Kullanıcı Bot ekranının grafik terminalinden ayrıştığını, karmaşık olduğunu ve üst üste binen alanlar içerdiğini bildirdi. Bu tur mevcut prototipin tasarım ve etkileşim düzeltmesidir; finansal API entegrasyonu değildir.

## Bulunan sorunlar ve yapılan değişiklikler

| Konum | Sorun | Düzeltme |
|---|---|---|
| `frontend/src/botTerminal.css` | Bağımsız koyu/altın palet, tekrarlanan override blokları ve grafik kabuğuyla çakışan düğme/yükseklik kuralları | Tek stil dosyası yeniden düzenlendi; renkler grafik `--surface`, `--canvas`, `--line`, `--text`, `--muted`, `--accent`, `--up`, `--down` değişkenlerinden alınır |
| `frontend/src/BotTerminal.tsx` | Pazarlama sayfası gibi büyük başlık, fazla açıklama ve her sekmede açık işlem formu | Küçük terminal araç çubuğu; özet yalnız genel bakış/pozisyonlarda; ayrı Yeni işlem sekmesi; ilgisiz sekmelerde işlem paneli yok |
| Yerleşim | Sabit ekran içinde içeriğin kırpılması, form/tabloların dar sütunda sıkışması | Masaüstünde içerik ve işlem paneli ayrı kaydırılır; dar ekranda tek sayfa akışı; minmax(0,1fr), min-width:0, tablo içi yatay kaydırma |
| Formlar | Kaldıraç/marjin gibi ikincil alanların ana formu uzatması, kısa ekranlarda gereksiz yükseklik | Hesap/başlatma ayrıntıları kapalı açılır bölümde; hedef/risk ve gelişmiş emirler ayrı; kısa ekran ölçüleri eklendi |
| Pozisyon/grid | Oturum seçim alanları ile özet satırlarının bitişik görünmesi | Form ve özet gruplarına açık dikey aralık eklendi |
| Modal/tema | Sabit farklı palet ve değişken ölçüler | Modal aynı grafik değişkenlerini kullanır; sınırlandırılmış yükseklik, kendi kaydırması ve mevcut modal odak altyapısı korunur |
| `useUiSession.ts` | Bot görünürken gizlenmiş grafik görünür UI gibi yayın yapabiliyordu | Gerçek grafik görünürlüğü yayıncıya aktarılır; gizli bildirimden sonra periyodik yayın durur, dönüşte aynı oturum kimliği korunur |

Referans: [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md). İçerik taşması, etiketler, odak, dar ekran ve tema ilkeleri uygulandı. Resmî TradingView bileşeni veya birebir kopyası kullanıldığı iddia edilmez; projenin mevcut grafik terminali tasarım kaynağıdır.

## Gerçek tarayıcı kontrolleri

Chrome'da mevcut yerel `http://127.0.0.1:5173/?view=bot` sayfası CUA ile kontrol edildi. Önceki geometri sorunu, pencereyi açıkça Raise ederek öne getirip yenileme sonrasında aşılabildi. Gözlem sonuçları:

- Yeni tasarımın yüklenmesi ve masaüstü ekran görüntüsü doğrulandı.
- Genel bakış, Yeni işlem, Pozisyonlar ve Geri bildirim sekmeleri arasında tıklama ile geçiş doğrulandı. Geri bildirim/pozisyon sekmesinde işlem formunun görünmemesi gözlendi.
- Yeni işlem formunda aşağı kaydırılarak son düğmelere erişildi. İşlemi önizle tıklandı; Onay öncesi özet ve GTC/bütçe/stop/hedef alanları ekranda görüldü. Gerçek emir veya finansal onay yapılmadı.
- Azalt formu modal olarak açıldı; alanlar ve sınırlar incelendi; Escape ile modalın kapandığı gözlendi.
- DevTools dock ile yaklaşık 396 px dar görünümde pozisyon ve Yeni işlem ekranları kontrol edildi. Alanlar tek akışta, ikili fiyat grupları sığacak ölçüde; sekme çubuğu kendi içinde kaydırılır. Ekran görüntülerinde alanların birbirini örtmediği gözlendi. Fiziksel mobil cihaz kabulü yapılmadı.
- Grafik/Bot geçişi ve grafik düğmesinden açık temaya geçiş kontrol edildi. Bot açık tema renklerini de grafik değişkenlerinden aldı; başlangıçtaki koyu tema geri getirildi. Son görünüm Bot genel bakışta bırakıldı.

## Konsol ve doğrulama sınırları

Konsolda üç tarihsel `ui-sessions` 429 kaydı görüldü; kayıtlar JavaScript yerleşim istisnası değildir. Mevcut güvenlik/kota sınırları kaldırılmadı. Gizli grafik yayını düzeltildi ve ayrı regresyonla doğrulandı. Bu, geçmiş 429 kayıtlarının hepsinin tek kök nedeni bulundu veya bütün ağ hataları giderildi anlamına gelmez.

Sonuç: **387 frontend testi, 0 hata, 0 skip**; TypeScript ve Vite üretim derlemesi başarılı. Birleşik React testi ilgisiz sekmelerde işlem paneli/özet olmamasını ve hesap bölümünün başlangıçta kapalı olmasını denetler. Görünürlük regresyonu, Bot açıkken yayın yapılmamasını ve grafiğe dönüşte kimliğin korunmasını doğrular. Büyük grafik bundle uyarısı sürüyor. Finansal backend ve Python kodu değiştirilmedi.


## 17 Kasım — bağlı modun canlı Chrome incelemesi

Computer Use ile gerçek Chrome penceresi incelendi. Hesap, Yeni işlem, Emirler, Yönetim, Kayıtlar ve Geri bildirim bölümleri açıldı. Yönetimde altı kategoriye geçildi. Grafik işlem paneli açıldı ve alt ayarlara kaydırıldı. Finansal onay veya emir gönderilmedi.

Bulunan ve giderilen sorunlar:

- Üstte sabit yığılan hesap/başlık blokları ile ayrı içerik ve ticket scroll alanları kaldırıldı. Tam terminalin tek dikey scroll sahibi `.bot-view`; başlık ve hesap özeti de sayfayla kayar. Chrome ekranında üst alanın kaybolduğu ve alt formun geniş alanda kaldığı görüldü.
- Hesap özeti yalnız Hesap bölümünde gösterilir. Diğer bölümlerde tekrarlanan üst başlık ve açıklamalar kaldırıldı; kayıt/geri bildirimde hesap yenileme uyarısı gösterilmez.
- Tüm satırı kaplayan Grafiğe dön ve Yeni işlem oluştur düğmeleri düzeltildi. Tek yenileme kontrolü kaldı.
- Ticket üç görsel gruba ayrıldı: Strateji ve sözleşme, Giriş ve risk, İleri ayarlar. SINGLE/GRID/NEUTRAL seçenekleri kullanıcıya Türkçe etiketlerle sunulur; sunucu değerleri korunur.
- Yönetim kategorileri, küçük form boşlukları, sınırlı form genişliği, okunabilir etiketler ve Türkçe sayı biçimi uygulandı. Teknik kayıt kimlikleri açılır ayrıntıya taşındı; iş adları/durumları Türkçeleştirildi.
- Grafik panelinin başlığı kısaltıldı; form kendi alanında kayar. Geniş ekranda ana grafik için panel genişliği ayrılır; fiyat grafiği panelin arkasında kalmaz. Alt ayarların ve ön kontrol düğmesinin erişilebilirliği Chrome'da görüldü.
- Tam terminal düğmesi React görünümünü değiştirir; grafik panelindeki taslağı yeniden sayfa yükleyerek kaybetmez.

Tarayıcıda açık olmayan kabul: gerçek dokunmatik/DPR cihazları ve bütün finansal eylemlerin dış borsa kabulü. Gerçek Demo yürütmesi bu tasarım turunda açılmadı.
