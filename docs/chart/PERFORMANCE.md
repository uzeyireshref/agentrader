# Grafik performans ölçüm düzeni

D1 — 10 Kasım 2026. Ölçüm aracı: `scripts/measure_chart_performance.py`. Bu düzen headless Chromium üzerinde üretim paketinin rAF callback aralıklarını ölçer. Görünür Windows/GPU FPS veya fiziksel trackpad kabulü değildir.

## Sabit yük ve ortam

- 4.000 deterministik BTCUSDT/15m mum; 200 çizim: yatay, bölge, trend, Fibonacci türlerinden 50’şer adet.
- Sabit arithmetic-v1 veri üretimi; mum/çizim JSON SHA-256 değeri rapora yazılır. Sabit snapshot sonrasında iki saniyede bir aynı sequence ile yalnız tazelik heartbeat’i gönderilir; mum sayısı/verisi değişmez.
- 1400×1000 CSS px, DPR 1; başlangıç logical aralığı 3890–4006, manuel fiyat aralığı 475–520, seçili çizim perf-2. Her koşuda sıfırlama ve 400 ms yerleşme beklemesi aynıdır.
- Vite preview ile mevcut derlenmiş üretim paketi kullanılır. Tüm paket dosyalarının SHA-256 değerleri, tarayıcı sürümü, OS/işlemci/çekirdek ve tarayıcı ortam bilgisi kaydedilir.
- Piyasa/çizim istekleri ve WebSocket izole taklit verilerle karşılanır. Gerçek kullanıcı deposuna yazım veya hesap bağlantısı yapılmaz. Sürükleme Escape ile iptal edilir, tüm fixture’ın değişmediği doğrulanır.

## Tekrarlama

Proje kökünden kısa kurulum doğrulaması:

```powershell
python scripts/measure_chart_performance.py --seconds 10 --runs 1
```

D2 görevi için aynı düzenle üç uzun koşu:

```powershell
python scripts/measure_chart_performance.py --seconds 60 --runs 3
```

Üretim kodu değişmişse önce frontend dizininde `npm.cmd run build` çalıştırılır. Ölçüm paket hash’leri farklıysa sonuçlar aynı paket gibi karşılaştırılmaz. Aynı süreli yeni çalıştırma ilgili JSON raporunu günceller; karşılaştırma için önceki raporu başka adla koru. 10 sn ve 60 sn raporları ayrı dosyalardır.

## Hareket ve geçerlilik

Her iki saniyelik döngü: -120/+120 teker yakınlaştırma, +40/-40 px gerçek fare pan, seçili trend ankrajında +12/-6 px sürükleme ve Escape. Pan hedefi çizimlerin üzerindeki boş alandır. Her wheel/pan’ın aralığı değiştirdiği, sürüklemenin gerçekten başladığı ve iptalin motor kilidini kaldırdığı kontrol edilir. Döngü bitiş zamanları rapora yazılır; otomasyon süresi iki saniyeyi aşarsa izde görünür.

Sekme gizlenirse koşu geçersizdir. rAF kaydında kesinti, kırpılmış örnek, hata, yük/viewport/DPR değişimi veya LIVE dışı durum bulunamaz; en az 30 örnek gerekir. Başlangıç/son yük, görünürlük ve gerçek eylem kontrolleri de geçmelidir. Hata durumunda script başarısız çıkar; sonuç performans kabulü sayılmaz.

D2 hedefi üç ayrı geçerli 60 saniyelik koşunun her birinde p95 ≤33,34 ms; maksimum aralık ve long task sayısı/süresi ayrıca raporlanır. D1’in 10 saniyelik sonucu D2’yi tamamlamaz. Heap başlangıç/son değerleri destekleniyorsa kaydedilir; bellek sızıntısı sonucu değildir. Kaynak yaşam döngüsü D3, uzun oturum/canlı mum değişimi D4 kapsamındadır.


## D2 sonucu — 10 Kasım 2026

Üç geçerli 60 saniyelik koşuda p95 16,7 / 16,7 / 16,8 ms; maksimum kare aralığı 50 / 50 / 33,4 ms. Uzun görev sayısı 1 / 2 / 0, toplam süre 57 / 108 / 0 ms. Her koşuda hata sıfır. [Ayrıntılı kabul kaydı](../../reports/chart-interaction-performance-validation-20261110.json). D2 kontrollü headless rAF kapsamıyla geçti; kaynak tutulması ve uzun oturum henüz kabul edilmedi.


## D3 kaynak ölçümü

```powershell
python scripts/check_chart_resources.py
```

Üretim paketi, 4.000 mum/200 yatay çizim, BTC/ETH ve 15m/1h ile 3 ısınma +10 ölçüm +20 tanı döngüsü. Yerel gerçek WebSocket sunucusu kurulur; test sonunda kapanır. Her örnekte iki forced GC ve CDP DOM/listener sayımı; başlangıç/son heap snapshot türü karşılaştırması yapılır. Raw snapshot metinleri diske yığılmaz, tür farkları rapora yazılır. Post-GC heap tarama sınırı max(1 MiB, başlangıcın %5’i), doğrusal eğim sınırı 64 KiB/döngü; monoton artış ayrıca başarısızdır. Bunlar tarama kurallarıdır, genel sızıntısızlık ispatı değildir.

Son koşuda kaynak sayıları sabit kaldı. Heap yaklaşık 1 MB arttı; snapshot farkı çoğunlukla code/runtime kategorisinde, uygulama object/closure/array artışı çok düşük veya sıfır. Heap plato kanıtı yoktur; D4/D5 uzun oturum değerlendirmesine taşındı. [Ayrıntılı inceleme](../../reports/chart-resource-lifecycle-validation-20261110.json).


## D4 uzun oturum düzeni

```powershell
python scripts/check_chart_soak.py --smoke
python scripts/check_chart_soak.py
```

`--smoke` yalnız kısa araç doğrulamasıdır, D4 kabulüne uygun değildir. Parametresiz koşu gerçek monotonic saatle en az 1.800 saniye çalışır. 4.000 mum ve dört türden 50’şer toplam 200 çizim; yerel gerçek WebSocket sunucusu iki saniyede bir açık mumu günceller. Kontrollü piyasa saatinde sınırlar 60. ve 960. saniyelerde, gerçek 900 saniye arayla geçilir. Yeni muma geçerken önceki mum kapanır ve pencere 4.000 mumda tutulur. 300. ve 1.200. saniyelerde bağlantı sunucudan kapatılır; RECONNECTING ve tekrar LIVE gözlenir.

30 saniyede bir istemci mumlarının tam özeti sunucudaki aynı sequence ile karşılaştırılır; native mum/hacim serilerinin her değeri istemci verisiyle eşleşmelidir. JavaScript hata/rejection ve gizlenme sürekli, rAF aralıkları çevrimiçi histogramla izlenir. Beş dakikada bir iki forced GC sonrası bellek/kaynak örneği alınır. Örnek alınırken yeni paket üretimi kısa süre kilitlenir; GC ve native sayaçlar büyük veri serileştirilmeden önce okunur. Bu örnekleme kesintileri D2 etkileşim p95 kıyası değildir. Dinleyici/DOM sabitliği yalnız post-GC örneklerinde değerlendirilir.

Heap tarama bütçesi net artışta max(2 MiB, başlangıcın %20’si); başlangıç/son heap türü karşılaştırması ve ara post-GC eğilimi ayrıca gözden geçirilir. Bütçe tek başına uzun süre sızıntısızlık garantisi değildir. Beklenmeyen hata, kalıcı LIVE dışı durum, veri/native seri farkı, gizlenme, iki mum sınırının veya iki toparlanmanın eksikliği kabulü engeller. Kontrol noktası `reports/chart-soak-progress-20261110.json` çalışırken güncellenir; tamamlanmadan D4 işaretlenmez.


### D4 sonucu

30 dk 2,359 sn gerçek oturum geçti: 61 tam veri/native seri kontrolü, iki mum sınırı ve iki reconnect. Post-GC native kaynak sayıları sabit, hata/rejection/gizlenme yok. Heap artışı +1.771.904 byte ile 2 MiB tarama bütçesi içinde; son beş dakika +14.316 byte. Mutlak plato veya sınırsız süre bellek kabulü değildir. Gözlem/GC içeren koşuda en büyük rAF aralığı 749,9 ms olarak korundu; saf D2 etkileşim kıyasına katılmaz. [Tam inceleme](../../reports/chart-long-session-validation-20261110.json). D5 toplu performans incelemesi bekliyor.


## D5 kapı sonucu

```powershell
python scripts/check_chart_performance_gate.py
```

16 kayıtlı kanıt/güncel paket kontrolü geçti. 123 frontend testi ve üretim derlemesi ayrıca yeniden geçti; hash’ler ölçülen paketle aynı. **Kontrollü headless performans kapısı kapandı**; fiziksel cihaz/genel grafik sürüm kabulü kapanmadı.

749,9 ms D4 outlier’ı ilk 31 saniyelik pencerede; pencere başlangıç heap snapshot’ını da içerir. Kayıt kesin GC nedenselliğini ayırmaz; bu aralık otomatik olarak ürüne veya yalnız ölçüme atfedilmez. D2’nin ayrı p95 kabulü ve D4’ün gözlem maliyeti ayrımı korunur. Heap’in bütçe içinde kalması mutlak plato kanıtı değildir. [D5 incelemesi](../../reports/chart-performance-gate-validation-20261110.json).
