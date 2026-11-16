# G9 ürün kararı

Mevcut `chart-fibonacci/1` extension iki çapalıdır: `A + r × (B − A)`. Kod ve mevcut Fibonacci açıklaması üç çapalı projection'ı açıkça ayrı tutar. Bu nedenle projection bir alias değildir; eski extension kaydı dönüştürülmez.

Yeni `chart-fibonacci-projection/1`: A hareket başlangıcı, B hareket sonu, C projeksiyon tabanıdır. Fiyat `C + r × (B − A)`; `basis=PRICE_DELTA` zorunludur. A/B zamanları ve fiyatları farklıdır; C bağımsızdır. Varsayılan oranlar 0, 1, 1.272, 1.618, 2, 2.618; 2–24 benzersiz oran, −10…10 ve en fazla 12 ondalık basamak. Sıfır/negatif hesap fiyatı çizilmez ve sorguda açık engel verir. Lineer/log görünüm aynı aritmetik fiyat seviyelerini gösterir; logaritmik oran formülü çıkarılmaz. HTTP LINEAR/LOG sorguları bu sabit price-delta anlamını korur.

Zaman kapsamı C'den başlar: `right` sağa sınırsız, `bounded` C…C+|B.time−A.time|, `unbounded` bütün zamandır. Bounded uç UTC sınırını aşamaz. Çapalar UTC saniye/decimal fiyat olarak saklanır. Oluşturma üç tıkla, iptal mevcut Escape akışıyla yapılır. Oran/zaman kapsamı, üçüncü çapa, hit/drag, şablon varsayılanları, HTTP/bot ve katalog aynı şemayı kullanır. Yeni kayıt wire format 10 gerektirir; önceki formatlar yeni nesneyi sessizce eski Fib olarak okumaz.

Clipboard paketi `chart-drawing-package/1` sürümlüdür: sabit Demo market kimliği + kaynak symbol/interval + en fazla 20 `{geometry, management, linked_note}` girdisi. Kimlik, revizyon, origin, bot kimliği, takip/binding ve emir yetkisi pakette bulunmaz. Kaynak export'u owner/workspace ve çizim/not revizyonlarını aynı okuma transaction'ında doğrular. Paste tek atomik ve idempotent transaction'da yeni nesne/not kimlikleri üretir; kökeni doğrulanmış aktör belirler. Aynı request ID tekrarında yeni nesne üretilmez; farklı paste niyeti yeni kimlik üretir.

Sembol veya interval farkı açık hatadır; otomatik fiyat/zaman ölçekleme veya sembol değiştirme yapılmaz. Stil/visibility/kilit/interval tercihleri ve uzun not metni korunur; yeni not revizyonu 1'den başlar. Eski Duplicate ayrı kalır. Kullanıcı paste işlemi normal undo/redo girdisidir; undo hedefi arşivler, redo aynı yeni kimliği/not ilişkisini geri getirir. Botun paste'i manuel kaynağa dokunamaz. Tarayıcı clipboard izni yoksa paket metni kopyalanıp yapıştırılabilecek bir dialog sunulur; kalıcı browser storage kullanılmaz.

Paket üst sınırı 512 KiB, not üst sınırı G7'nin 4000 Unicode/16000 UTF-8 bayt sınırıdır. Bilinmeyen alanlar, bozuk geometri/management/not ve taklit origin reddedilir. Şablonlar mevcut ayrı profil/ayar sistemi olarak kalır; projection'ın oran varsayılanını destekler, yeni clipboard paketi şablon veya yetki aktarımı sayılmaz.

## HTTP ve adaptör

- `POST /api/workspaces/{workspace_id}/drawing-packages/export`: `{symbol, interval, targets}`. Her target `drawing_id`, `expected_revision`, `expected_note_revision` içerir. Owner/workspace dışı veya silinmiş hedef okunmaz; eski çizim/not revizyonu 409 verir. Read-only SQLite transaction kullanılır.
- `POST /api/workspaces/{workspace_id}/drawing-packages/paste`: `{request_id, symbol, interval, package}`. Paket içeriği aktör yetkisi taşımaz; en fazla 20 yeni nesne ve notları tek transaction'da oluşturulur. Aktif 200 nesne limiti korunur. Hata bütün paketi geri alır.
- Yeni projection CRUD/bulk/read için `format_version=10` gerekir. Format 1–9 listeleri bu şemayı içermez; eski formatla tekil erişim/yazma açık format hatası verir. Eski Fib/extension şemaları değiştirilmez.
- Geometri sorgusu `level` için açık UTC saniye ve kayıtlı oran gerekir. `LINEAR` ve `LOG` aynı exact price-delta değerini döndürür. Sorgu, piyasa verisi veya işlem yetkisi kanıtı değildir.
- `ChartBot.export_package(symbol, interval, targets)` ve `ChartBot.paste_package(key, symbol, interval, package)` gerçek HTTP uçlarını kullanır. Paste niyeti G8 journal/namespace/request ID mekanizmasında kalıcıdır. Büyük paket için yalnız paste taşıma sınırı 512 KiB + zarf payına açılır; diğer yazma sınırları korunur. CLI `run` action allowlist'i bu iki metodu içerir.

Adaptör yeni projection için format 10 seçer; önceki araçların yazma URL'leri ve dolayısıyla G8 niyet digest'leri korunur. Önceden kaydedilmiş format-9 pending niyetleri geçerli kalır; fresh GET format 10 kullanır. Paket bir piyasa kanıtı veya imzalı origin aktarımı değildir. Kullanıcı içeriğini düzenlemek mümkündür; sunucu yine yalnız yeni kimlik üretir ve kökeni doğrulanmış aktörden belirler.

## Arayüz ve geçmiş

Fibonacci menüsü ve araç araması yeni üç tıklı aracı içerir. C çapasının hareketi A/B'yi değiştirmez; A/B ters çevirme C tabanını korur. Log görünümde çapa sürükleme fiyat koordinatlarıyla yapılır. Oran/pozitif fiyat, zaman aralığı ve çapa doğrulaması uygulanır. Şablon varsayılanı yeni projection oranlarını ve desteklenen stili uygular; zorunlu basis/schema değişmez.

Kopyala ve Yapıştır kontrolleri sürümlü JSON dialogunu açar. Yerel clipboard API'si kullanıcı niyetiyle denenir; izin yoksa metin seçme/elle yapıştırma alternatifi bulunur. Farklı interval/sembol için grafik seçimi açıkça değiştirilmelidir. Bozuk paket sunucuya yazılmaz. Paste yanıtı kaybolursa aynı kayıt yeniden denenir; yeni request ID üretilerek belirsiz işlem çoğaltılmaz. Kesin doğrulama hatasında metin düzeltilebilir.

Undo/redo mevcut çizim işlemi zincirini kullanır. Not, geometri yığınına gömülüp eski metinle yeniden yazılmaz; yeni nesne silinip canlandırıldığında aynı not ilişkisi korunur. Kopyalanan kilit/visibility korunur; kilitli nesnenin undo/delete işlemi de mevcut sunucu kilit denetimine tabidir. Duplicate ve şablon ayrı mevcut işlemler olarak kalır.

## Doğrulama

Altı bağımsız elle belirlenmiş fiyat vektörü Python Fraction ve frontend BigInt sonuçlarını sınar. Backend paket testleri 26 varyantı 4000 Unicode karakterlik notla taşır; geçersiz kaynak/kimlik/şema, eski revizyon, atomiklik ve manuel koruma test edilir. Gerçek adaptör matrisi 26 varyantta not, fresh snapshot, sayısal sorgu, edit, export/paste ve yalnız bot temizliğini gerçekleştirir; 64 KiB üstü Unicode paket ayrıca taşınır.

Gerçek tarayıcı kabulü DPR 1 ve 2'de üç tıklı oluşturma, lineer/log seviyeler ve üç çapa için en çok 1 CSS px, C başlangıcı/bounded uç, native clipboard, bozuk paket/interval reddi, kayıp paste yanıtı, undo/redo, yeniden paste, projection varsayılanları ve reload'u kapsar. Native grafik testinde click ile double-click ayrımı için mevcut kabul betiklerindeki gibi tıklar arasında yeterli aralık bırakılır. Bütün veriler izoledir; canlı Demo hesabı veya emir çalıştırılmaz.

Migration eklenmedi: yeni geometri JSON'u mevcut revizyon tablosunda, yeni notlar mevcut G7 not tablosunda saklanır. Önceki kullanıcı değişiklikleri ve kabul raporları korunur. [G9 teslim raporu](../../reports/chart-interface-g9-20261115/README.md). G10 ortak geniş regresyon ve G11 Demo runtime kabulü ayrı paketlerdir.
