# Aktif çoklu oturum teminat yönetimi

> 9 Kasım 2026 plan notu: Bu belge tarihli işlem alt sistemi teslimini ve kanıtlarını korur. Burada geçen TradingView zinciri yeni geliştirme hedefi değildir; yerine kendi grafik/çizim → strateji → onay → işlem yolu geçmiştir. Güncel ürün sırası [02](02-ASAMALI-GELISTIRME-PLANI.md), geçiş tasarımı [19](19-KENDI-GRAFIK-TERMINALI-VE-GECIS.md) içindedir.

6 Kasım 2026. Kod ve çevrimdışı/sahte borsa doğrulaması tamamlandı.
Gerçek demo teminat değişikliği yapılmadı; gerçek borsa kanıtı bekliyor.

## Eklenen kapsam

`IsolatedMarginCommands`, aynı hesaptaki farklı sembollü SINGLE ve yönlü grid
oturumlarıyla çalışır. Neutral gridde LONG ve SHORT cüzdanları ayrı hedeflenir.
Tek hesapta birden fazla oturum bulunması artık tek başına ret sebebi değildir.
Teminat değişikliği ISOLATED ve single-asset hesabıyla sınırlıdır; hesap modu
veya kaldıraç kendiliğinden değiştirilmez. Pozisyon sahipliği bölüştürülmez.

Teminat komutu belirli etkin `session-id`, hesap, plan özeti, sembol ve tarafla
bağlıdır. Çoklu oturumda ve gridlerde bütün hesabın emir/gerçekleşme/pozisyon
sahipliği ve açık tarafların stop koruması doğrulanır. Sahipliği kanıtlanmış
bekleyen grid emirleri korunur; yabancı emirler veya eksik koruma komutu engeller.
Kısmi dolumun iptali, yeni koruma veya çıkış gibi bekleyen yönetim adımı varsa
önce yürütücü o adımı tamamlamalıdır. Teminat hazırlığı emir yönetimini çalıştırmaz.

## Bütçe ve risk

Çoklu oturum ve grid teminat eklemesinde gönderilecek tutar kullanılabilir
USDT'den önceden düşülerek bütün kalıcı risk zarfları yeniden değerlendirilir.
Güncel kaldıraç basamakları, günlük gerçekleşmiş sonuç/masraflar ve negatif
gerçekleşmemiş sonuçlar hesaba katılır. Henüz gerçekleşmemiş kâr ve teminat
azaltmasından beklenen nakit kapasiteye eklenmez. Bu yöntem bilerek ihtiyatlıdır;
mevcut teminatın bir kısmını yeniden rezerv sayarak kullanılabilir kapasiteyi
düşük gösterebilir. Tek eski SINGLE oturumu mevcut denetimleriyle çalışmaya devam eder.

MARGIN planında mevcut izole cüzdan, yeni ekleme ve kalan grid kapasitesi birlikte
plan bütçesini aşamaz. Neutral tarafta yalnız o tarafa ayrılmış bütçe kullanılır.
NOTIONAL bütçe teminat bütçesi diye yeniden yorumlanmaz. Teminat azaltmasında
kalan cüzdan pozisyonun başlangıç teminatını karşılamalı; etkin MARK_PRICE stop
model likidasyonundan önce tamponla çalışmalıdır. Likidasyon hesabı tahmindir.

Diğer oturumun rezervi, emri veya koruması değiştirilmez. Risk limit dosyaları,
mevcut işlem bütçeleri ve geçmiş işlem onayları değiştirilmedi.

## Komut akışı

Önce `settings margin-prepare` ile miktarı, ADD/REMOVE işlemini, sembolü,
`--position-side` ve `--session-id` bağını belirten komut hazırlanır. Hazırlık
borsada yazma yapmaz. Somut komut özeti onaylandığında `margin-apply` bir kez
gönderir; hazırlıktan sonra pozisyon/cüzdan veya risk değişmişse yeniden kontrol
engelleyebilir. `margin-reconcile` geçmişi okuyarak uzlaştırır.

Üç teminat komutu da `--risk-profile DOSYA` kabul eder. Yönetilen oturumlarla
aynı profil seçilmelidir. Seçilmezse varsayılan RiskLimits kullanılır; tek pozisyon
sınırı çoklu/neutral yönetimi engelleyebilir. Profil otomatik genişletilmez.
POST yanıtı kaybolursa eşleşen geçmiş tek başına sahiplik kanıtı sayılmaz;
komut UNKNOWN kalır ve yeniden gönderilmez. Bu aşama otomatik teminat doldurma
politikası oluşturmaz; her değişiklik belirli tutarlı komut yetkisi gerektirir.

## Kanıt ve kalan işler

Tam regresyon: 560 test; yeni teminat dosyasında 19 senaryo. Birden fazla SINGLE,
SINGLE + bekleyen grid, aktif grid, neutral LONG ekleme/SHORT azaltma, MARGIN
bölüşümü, kalan refill rezervi, değişen ortak nakit, basamak ve günlük kayıp,
korumasız/yabancı pozisyon, kısmi dolum bariyeri, kayıp POST ve CLI profil aktarımı
sahte borsada sınandı. Rapor: `reports/development-validation-20261106.json`.

Gerçek demo dolum/teminat/kesinti kanıtı bekliyor. Çapraz ürün/varlık değerleme,
kalan grid politikaları ve trailing, uzaktan onay/rapor erişimi, tamamlayıcı API,
Spot/COIN-M ve TradingView zinciri hâlâ kalan kapsamdır. Tüm proje bitmiş değildir.
Bu turda gerçek emir/teminat değişikliği, dış mesaj veya servis kurulumu yapılmadı.
