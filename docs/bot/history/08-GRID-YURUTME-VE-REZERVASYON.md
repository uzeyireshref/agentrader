# Grid yürütme ve bütçe rezervasyonu

6 Kasım 2026 — 312 test başarılı. Bu geliştirmede gerçek demo emri,
hesap ayarı değişikliği veya arka plan izleyicisi başlatılmadı.

## Uygulanan kapsam

GridRunner plan v2 GRID yoluna bağlandı: USD-M perpetual LONG/SHORT,
one-way/hedge, aritmetik/geometrik seviyeler, NOTIONAL/MARGIN/MAX_LOSS bütçesi.
Başlangıçta taze, pozisyonsuz ve emirsiz hesap gerekir. Kaldıraç, teminat ve
pozisyon modu eşleşmelidir; kendiliğinden değiştirilmez. Tek son hedef ve
zorunlu stop kullanılır. Geometrik ara seviyeler tick'e aşağı yuvarlanır;
seviyeler birleşiyorsa grid sayısı değiştirilmeden plan reddedilir.

ReservationBook hesap/plan özetine bağlı tam risk zarfını kalıcı ayırır.
Hücre satışı veya pozisyonun geçici sıfırlanması tekrar alış rezervini bırakmaz.
Rezerv ancak grid durduktan, emirler terminal olduktan ve sıfır pozisyon
borsadan doğrulandıktan sonra bırakılır. Aynı kimlikle farklı rezervasyon veya
bırakılmış rezervi yeniden etkinleştirme reddedilir. Farklı semboller hesap
kapasitesini paylaşır; aynı sembol/yön tek zarf içinde tutulur.

Genel, birden çok aktif oturum ve bütün teminat varlıklarını kullanan portföy
yönetimi tamamlanmış değildir. Yeni yol kullanılabilir USDT ile sınırlıdır.
SHORT stop kaybı ile nominal/masraf rezervi ayrı ihtiyatlı fiyatlardan hesaplanır.
Nominal bütçe kaldıraçla çarpılmaz. Nominal rezervinde bant, stop ve son hedefin
en yüksek fiyatı kullanılır. Risk modeli ayrılan rezervi borsada gerçekten
eklenmiş izole teminat gibi kabul ederek likidasyon hesabını iyileştirmez.

## Emir sözleşmesi

- Başlangıç stoğu tek kalıcı kimlikle alınır. Kısmi başlangıçta kalan iptal
  edilir ve eldeki miktar kapanış akışına alınır; hücreler fazladan açılmaz.
- Hücrede en fazla bir aktif normal emir bulunur. Gerçekleşen açıcı emir,
  yalnız kendi miktarı için azaltıcı karşı emir üretir. SHORT taraflar terstir.
- Kısmi emir kalanı terminal iptal olmadan karşı emir veya yeni alış üretilmez.
  Kısmi azaltma sonrası önce kalan envanter azaltılır; sonra tam hücre yenilenir.
- Kümülatif gerçekleşme, işlem geçmişi ve pozisyon miktarı eşleşmelidir.
  Tekrar/restart çift miktar veya ikinci başlangıç girişi üretmez.
- Stop/son hedef alanları GET ile doğrulanır. Tüketilmiş veya iptal edilmiş
  koruma, fiyat banda dönse bile otomatik yeniden girişe izin vermez.
- Stop/hedef veya bağımsız risk ihlalinde STOPPING kalıcılaştırılır; normal
  emirler iptal edilir, geç gelen gerçekleşmeler ve koşullu emrin bilinen alt
  emri uzlaştırılır. Sonra yalnız sahip olunan kalan miktar kapatılır.
- Onay iptali veya plan süresinin dolması DRAINING üretir: açıcı emirler iptal
  edilir; mevcut azaltıcı emirler ve korumalar sürer. Bu olay tek başına mevcut
  pozisyonu piyasa emriyle kapatmaz.
- Elle iptal edilmiş hedef tekrar kurulmaz. Yeni girişler durur; mevcut
  pozisyonun stop/son hedef koruması sürer. Yabancı işlemler sahiplenilmez.

## Komutlar

`python -m agentrader plans preflight PLAN.json`

Güncel hesapla SINGLE/grid ön kontrolü; emir veya yetki oluşturmaz.

`python -m agentrader plans run PLAN_ID VERSION --execute-demo`

Yalnız önceden yetkilendirilmiş sürümü başlatır. Grid için varsayılan sürekli
ön plan izlemedir; otomatik arka plan servisi kurulmaz.

`python -m agentrader plans manage SESSION_ID --execute-demo`

Yeni oturum/ikinci başlangıç kurmadan devralır; onaylı grid hücreleri için
açıcı/yeniden alış emirlerini yönetebilir. Grid yazma modunda varsayılan sürekli,
salt okunur/SINGLE modunda bir turdur. --iterations 0 sürekli; pozitif sayı
sınırlı turdur. --interval 1–60 saniyedir. Sınırlı izleme sonunda veya Ctrl+C
ile kontrollü çıkışta açıcı emirleri iptal edip pozisyonu korumayla bırakmayı
dener. İptaller doğrulanamazsa başarılı duruş ilan edilmez.

`python -m agentrader plans stop-grid SESSION_ID --execute-demo`

Yeni girişleri durdurur, mevcut pozisyonu korumayla bırakır. Ek
`--close-position` açıkça verilirse iptal → kalan miktarı kapatma → temizlik
seçilir. --execute-demo olmadan yalnız önizlemedir.

## Doğrulama sınırları

Kullanıcının 200 USDT toplam nominal, 73000–78000, 4 grid, 20x ve 74000 stop
tercihleri değiştirilmedi. Bütçe hücre minimumlarına yetmiyorsa plan reddedilir.
Testlerdeki farklı bütçeler yalnız sahte borsa verisidir; hesapta daha büyük
işlem açma yetkisi sayılmaz.

Borsadaki stop bekleyen normal grid emirlerini kendiliğinden topluca iptal
eden bir mekanizma olarak kullanılmaz. Ağ/elektrik kesintisinde yerel iptal
ve geç gerçekleşme takibi çalışamaz; tekrar giriş riski tamamen kalkmış
sayılmaz. WebSocket, servis/bildirim ve kesinti koruması çalışmaları eksiktir.
Belirsiz ağ/yazma hatası koşulsuz POST tekrarı yerine durdurma/uzlaştırma ister.

Yeni grid yürütücüsü gerçek demo emirleriyle henüz uçtan uca doğrulanmadı.
312 test, borsa doğrulamasının ve A0–A12 planının tamamlandığı iddiası değildir.
