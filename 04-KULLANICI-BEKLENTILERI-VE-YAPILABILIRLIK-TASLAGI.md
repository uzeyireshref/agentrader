# Agentrader — Kullanıcı beklentileri ve ürün kabulü

Güncelleme: 9 Kasım 2026 · Sürüm: 2.0 · Kendi grafik terminali yönü kullanıcı tarafından onaylandı.

## Kullanıcının istediği deneyim

Aşağıdaki ifade konuşmadan çıkarılan ürün özetidir; birebir alıntı değildir:

Kendi uygulamamda Binance coinlerinin grafiğini açayım. Destek, direnç, trend, Fibonacci ve bölgeler çizeyim; her çizim için kod yazmayayım. Bot bunları sayısal olarak bilsin, belirlediğim davranışları takip etsin ve piyasa bağlamıyla değerlendirsin. Ayrıca çizimlerimden bağımsız fırsatlar arasın. İster işlem öncesi onayımı alsın, ister belirlediğim varlık/bütçe/risk sınırlarında otomatik çalışıp bildirsin. Önce kullanışlı bir web uygulaması olsun; ileride uygulama olarak da kullanılabilsin.

## Kesinleşen yön

Kendi grafiğimiz ana çalışma alanıdır. TradingView hesabı/Pine/webhook geliştirmesi ana kapsamdan çıktı. Hazır grafik kütüphanesi üstüne kendi çizim, kayıt ve bot bağlantımızı kurabiliriz. Web sürümü gerçek üründür; sonradan çöpe atılacak maket değildir. Uygulama paketleme ihtiyacı aynı backend ve alan kayıtlarıyla karşılanacak.

Mevcut Python işlem çekirdeği korunur. Kullanıcı çizimleri ile bağımsız tarama aynı fırsat/plan/yetki/risk yoluna bağlanır. Piyasa izleme ekran açık olmasına bağlı olmaz; kesintisiz çalışma için backend'in çalışması gerekir.

## Kullanıcı akışları

### Grafik ve çizim

1. Kullanıcı desteklenen Binance USD-M sözleşmesini ve zaman dilimini seçer.
2. Geçmiş/canlı mumlar veri durumu ve fiyat kaynağıyla gösterilir.
3. Çizim oluşturur, sürükler veya sayısal fiyatını düzenler; sunucu kayıt durumunu görür.
4. Sayfa yeniden açıldığında aynı çalışma alanı/çizimler gelir.
5. Çizime takip kuralı bağlar, özetini görür ve etkinleştirir.

### İzleme ve fırsat

1. Yaklaşma/temas/kapanış gibi koşul ölçülür; olay kalıcı kaydedilir.
2. Bot destekleyen ve karşı bulguları, veri kalitesini ve geçersizlik koşulunu raporlar.
3. Yalnız izle kuralı bildirimde kalır. İşlem adayı kuralı desteklenen somut plan önerebilir.
4. Kullanıcı neden beklediğini veya risk nedeniyle engellendiğini de görebilir.

### Onaylı işlem

Kullanıcı somut plan sürümü, nominal/teminat/risk ayrımı, giriş, stop/hedefler ve süreyi görür. Onay sonrası koşullar tekrar kontrol edilir. Kabul/gerçekleşme/koruma durumları ayrı bildirilir. Ret veya zaman aşımı giriş oluşturmaz. Pozisyon yönetimi mevcut yürütme yetenekleriyle sınırlıdır.

### Gelecek otomatik çalışma

Kullanıcı semboller/stratejiler, yönetim bütçesi, tahsis yöntemi, yön/kaldıraç, risk ve süre sınırlarıyla yönetim yetkisini açıkça etkinleştirir. Bot kapsam içindeki fırsatları karşılaştırıp somut planlar üretir; uygun fırsat yoksa bekler. Yetki iptali girişleri durdurur, açık korumaları kaldırmaz. Bu akış W8 hedefidir; bugün mevcut değildir.

## İkinci direnç testi örneği

İlk testte güçlü geri çekilme, ikinci testte daha zayıf tepki gözlemi isteniyor. Aynı seviye toleransı, ayrı temas koşulu, geri çekilme süresi, ikinci tepki gözlem penceresi ve teyit tanımlanacak. İkinci temasta düşüş olmaması anında bilinen sonuç değildir. Yaklaşık %5 yalnız örnektir. LONG adayı ile yürütülmüş borsa emri ayrı durumlardır.

## Beklentiler ve mevcut durum

| Beklenti | Uygulama yaklaşımı | Bugünkü durum |
|---|---|---|
| Yerel uygulama/API temeli | Salt okunur durum, katalog ve inceleme kuyruğu | W1 uygulandı; grafik henüz yok |
| Kendi canlı grafiğimiz | Web terminali + Binance piyasa verisi | W2 kodlandı/public veri doğrulandı; görsel kabul bekliyor |
| Çizimlerin doğrudan bot tarafından bilinmesi | Sunucuda sürümlü zaman/fiyat geometrisi | W3 kayıt/API doğrulandı; bot takibi W4'te bağlanacak |
| Her çizimde kod yazmamak | Formlarla desteklenen kural türleri | Planlandı |
| Ekran kapalıyken takip | Sürekli piyasa/strateji döngüsü | Mevcut oturum izleyicisi var; genel tarayıcı yok |
| Temel çoklu zaman dilimi raporu | PublicMarket/CandleStore/analysis | Mevcut; emir üretmez |
| Telegram bildirimi | Kalıcı kuyruk ve gönderici | Kod mevcut; teslim kanıtı bekliyor |
| Uzaktan işlem onayı | Kimliği doğrulanmış ortak komut yolu | Henüz uygulanmadı |
| Demo plan yürütme | Mevcut v1/v2 yürütücüler | Kod ve testler var; yeni yolların demo kanıtları eksik |
| Bağımsız fırsat taraması | Seçili evrende aynı stratejiler | Planlandı |
| Bütçeyle fırsata göre tahsis | Ayrı tahsis katmanı + ortak risk rezervi | Risk rezervi var; tahsis yöneticisi yok |
| Sürekli otomatik yetki | Sürümlü yönetim yetkisi | Planlandı; mevcut Mod B'den ayrı |
| Haber/AI ve performans | Kaynaklı açıklama ve karar ölçümü | Sonraki paketler |

## İlk teslimin kullanıcı kabulü

- BTCUSDT grafiği kaynakla uyumlu mum/fiyat/zaman gösterir; zaman dilimi değişir, geçmiş incelenebilir.
- Çizgi/bölge oluşturma, seçme, taşıma, fiyat düzenleme ve silme rahat çalışır; grafik kaydırmayla çizim sürükleme çakışmaz.
- Çizim zoom/ölçek değişiminde aynı fiyatta kalır; sayfa yeniden açıldığında sunucudan yüklenir.
- Kaydediliyor/kaydedildi/hata ve veri canlı/eski/bağlanıyor durumları anlaşılırdır.
- Etkin kuralın kaynağı, seviyesi, toleransı ve davranışı görünür; silme/değiştirme etkisi açıkça gösterilir.
- Yaklaşma/temas tek bir anlamlı olay oluşturur; tekrar ve restart bildirim fırtınası yaratmaz.
- Tarayıcı kapalıyken çalışan backend izlemeyi sürdürür. Backend kapalıyken devam ettiği izlenimi verilmez.
- Masaüstü çizim kullanımı önce doğrulanır; dar ekranda okunurluk ve temel kontrol korunur. Mobil çizim hareketleri ayrıca kontrol edilir.
- İlk teslim yalnız takip/bildirimdir; demo giriş W6'da ayrı uçtan uca kanıtlanır.

## Sonraki kalite ölçümleri

Grafik etkileşim ve canlı güncelleme gecikmesi, sembol sayısı altında yük, reconnect sonrası boşluk, kayıt çakışması, bildirim teslimi ve fırsat tekrar oranı ölçülür. Hedef cihaz ve yükle sayısal eşikler W2 prototipinde belirlenir; ölçülmemiş hız veya kusursuzluk garantisi verilmez.

Strateji değerlendirmesinde net sonuç yanında masraf/funding/kayma, azami gerileme, veri kapsamı, reddedilen ve işleme dönüşmeyen fırsatlar da gösterilir. Demo emir başarısı strateji kârlılığı değildir.

## Açık ürün kararları ve sınırlar

Coin listesi, gerçek sermaye/risk, tahsis oranları, onay süresi, sunucu, AI/haber sağlayıcısı, masaüstü/mobil paketleme ve nihai grafik kütüphanesi uygulama sırasında somut ihtiyaca göre seçilecek. Sohbet örnekleri otomatik işlem izni değildir. Tam TradingView araç kataloğu, ilk günden native mobil uygulama ve kendiliğinden öğrenip risk artıran bot ilk teslim kapsamı değildir.

Haber/akış/dominans hedefleri korunur; kendi grafik teslimini bekletmez. Kullanıcı onayı risk ihlalini aşamaz. Sırlar tarayıcıya/mesaja taşınmaz. Para çekme ve gerçek hesap etkinleştirmesi bu geliştirme onayına dahil değildir.

## Başvuru

[01 — Hedef](01-PROJE-VE-HEDEFLER.md), [02 — Teslimler](02-ASAMALI-GELISTIRME-PLANI.md), [03 — Sözleşme](03-MIMARI-VE-ISLEM-SOZLESMESI.md), [19 — Teknik geçiş](19-KENDI-GRAFIK-TERMINALI-VE-GECIS.md), [07 — Durum](07-GELISTIRME-DURUMU.md). Önceki taslak [tarihsel arşivde](docs/archive/2026-11-09/README.md) korunur.
