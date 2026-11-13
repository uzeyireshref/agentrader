# T04 — long/short grafik planlama

12 Kasım 2026. Tamamlandı; plan12/27. Sıradaki T06 paralel kanal.

## Kullanım ve görünüm

Sol rail’de Planlama araçları → Long plan / Short plan; araç aramasından da bulunur. Önce giriş fiyatı, sonra stop fiyatı, ardından hedef fiyatı ve planın bitiş mumu seçilir. Stop tıklamasının zamanı kullanılmaz; stop ve hedef ortak bitiş zamanı taşır. Long için stop < giriş < hedef, short için hedef < giriş < stop zorunludur. Bitiş başlangıçtan sonra olmalıdır. Esc ve kaynak değişimi yarım oluşturmayı temizler.

Grafikte kırmızı risk/yeşil getiri alanı, giriş-stop-hedef etiketleri, brüt ve maliyetli R:R görülür. Başlangıç/giriş, stop ve hedef tutamakları düzenlenebilir; stop/hedef zaman düzenlemesi ortak sağ kenarı taşır. Alanı sürüklemek üç fiyatı ve zamanlarını birlikte kaydırır. Geçersiz seviye sırası veya sıfır risk kaydedilmez. Plan özeti panelin üstündedir; maliyet, risk bütçesi ve fiyat/zaman formu aşağıdadır. Form taslağı anında hesaplanır, yalnız Kaydet ile saklanır. Kaydedilmiş grafik etiketi onaylanmış değerleri gösterir.

T07 kilit, gizleme, zaman dilimi, stil, çoğaltma, çoklu hareket ve transaction geçmişi kullanılır. Kopya yeni kimlik alır; bot aktivasyonu oluşturmaz. Undo/redo ve uygulama/server restart planı ve varsayımları korur. Nesne kategorisi plan’dır; mevcut grid/strategy plan_execution modellerine veya borsa yürütmesine bağlanmaz.

## Exact matematik

E giriş, S stop, T hedef, d long için+1/short için-1; f=fee_bps/10000, s=slippage_bps/10000. Ücret ve kayma ayrı ayrı0–1000 baz puan/yön aralığında, başlangıçta0’dır.1 baz puan=%0,01. Varsayımlar kullanıcı girdisidir; borsa ücret tarifesi değildir.

- Brüt risk=d(E−S), brüt getiri=d(T−E), brüt R:R=getiri/risk.
- Olumsuz dolum varsayımları: Ei=E(1+ds), Si=S(1−ds), Ti=T(1−ds).
- Maliyetli risk=d(Ei−Si)+f(Ei+Si); maliyetli getiri=d(Ti−Ei)−f(Ei+Ti). Kayma ve iki yöndeki ücret açıkça uygulanır.
- Maliyetli R:R=maliyetli getiri/maliyetli risk. Getiri maliyetlerle negatifleşirse negatif sonuç ve açık uyarı gösterilir.
- İsteğe bağlı risk bütçesi B>0 USDT için teorik baz-varlık miktarı q=B/maliyetli risk; giriş tutarı=qEi, hedef PnL=q×maliyetli getiri. B yoksa miktar/tutar/PnL unavailable kalır;0 sayılmaz.

Python Fraction ve TS BigInt rational aynı hesabı uygular; fiyat/tick girişleri mevcut exact politikayı kullanır. Kanonik riskReward sorgusu exact numerator/denominator ve yalnız sonluysa exact decimal verir. Gösterimde yuvarlanan sonlu veya tekrarlı değerlerin başına≈ konur; bu gösterim emir miktarı değildir. Lot/min-notional filtresi, fonlama, marjin, kaldıraç, likidasyon ve gerçek dolum garantisi dahil değildir. Zaman ufku yalnız görsel plan kapsamıdır; fiyatın o zamanda hedefe varacağını ifade etmez.

## Kayıt ve yetki

chart-position/1; üç anchor sırasıyla giriş/stop/hedef ve params={risk_budget,fee_bps,slippage_bps}. Bütçe null veya pozitif decimal text, maliyetler nonnegative decimal text. Format_version=5 kullanılır; v1–v4 listeleri planları dışarıda bırakır, tekil/CRUD ve eski batch yazımı reddedilir. Eski geometri türlerinin anlamı değişmez. Yeni DB migration gerekmez; mevcut JSON revision kaydı kullanılır. Kanonik hash maliyet ve bütçeyi kapsar, eşdeğer decimal yazımları normalize edilir. Sözleşme category=plan ve schema/basis açıkça gösterilir; canlı uygunluk ve emir yetkisi false kalır.

## Kabul ve sınırlar

757 Python testi geçti;7 yeni test bağımsız long/short maliyet örnekleri, sıfır/ters risk, ortak zaman, bütçesiz durum, negatif net hedef, düşük Decimal context hassasiyetinden bağımsız sonuç, hash, kayıt/undo/restart ve v5 izolasyonunu sınar.188 frontend testi geçti;6 yeni test aynı bağımsız sayısal örnekleri, miktar-bütçe eşitliğini, tutamak/form/tick politikası ve yaklaşık gösterimi doğrular. TypeScript ve üretim derlemesi başarılı. Ana JS yaklaşık512kB minified/163kB gzip; mevcut Vite500kB chunk uyarısı sürer. QA01 performans kabulü bu teslimde tamamlanmış sayılmaz.

check_chart_t04.py gerçek production App/HTTP ve izole SQLite ile12 kontrolü geçti: iki yönde üç tıklamalı oluşturma, native koordinatlarla risk kutusu ve üç seviye, exact maliyet/bütçe, sıfır risk reddi, sayısal hedef, gerçek stop tutamağı, undo/redo, bütün plan hareketi, short işaretleri, kopya, kilit/gizleme ve server/page restart. Kontrollü piyasa verisi kullanıldı; kullanıcı veritabanına test planı yazılmadı. Page error0, dış istek0, hesap/emir/commands/session API çağrısı0. T07/T05/G01/G06/G02/G03 toplam77 regresyon tarayıcı kontrolü geçti. Açık/koyu ekranlar incelendi. Bu, tam TradingView paritesi, fiziksel GPU/touch veya canlı işlem kabulü değildir.

Kanıt: reports/chart-t04-validation-20261112.json, chart-t04-dark/light-20261112.png; kaynak/derleme/test SHA256 kayıtları reports/chart-t04-delivery-20261112.json.
