# Grafik kaynak araştırması ve kalite iyileştirmesi

Tarih: 9 Kasım 2026. Kapsam: W2/W3 grafik kalitesi. Karar: web öncelikli kendi terminalimiz, Lightweight Charts 5.2.1 üzerinde devam eder. Çizimlerin asıl kaydı ve ileride botun okuyacağı zaman/fiyat geometrisi bize aittir. Grafik motoru, emir yürütme ve strateji motoru ayrı kalır.

## İncelenen GitHub depoları

Yıldız sayısını kalite garantisi olarak kullanmadık. Motor uyumu, lisans, kaynak kodu, etkileşim modeli, kayıt sorumluluğu ve geçiş maliyeti karşılaştırıldı. Commit ve lisans kanıtları [araştırma kaydında](reports/chart-repository-research-20261109.json).

| Depo | Değerlendirme | Projede kullanım |
| --- | --- | --- |
| [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) | Apache-2.0; mevcut v5.2.1 motorumuz; resmî series primitive arayüzü ve örnekleri | Ana motor korundu. Resmî toolkit görev birleştiricisi kaynak olarak eklendi. |
| [KLineChart](https://github.com/klinecharts/KLineChart) | Apache-2.0; yerleşik gösterge/çizim modelleri; Fibonacci overlay kaynağı incelendi | En güçlü alternatif motor. Şimdiki kayıt ve canlı veri entegrasyonunu yeniden taşımayı gerektirdiğinden bu tur eklenmedi. |
| [Eski line-tools](https://github.com/difurious/lightweight-charts-line-tools) | Eski 3.8 motor fork'u; README yeni v5 çekirdeğine yönlendiriyor | Eski fork alınmadı; yeni çekirdek ayrıca incelendi. |
| [line-tools-core](https://github.com/difurious/lightweight-charts-line-tools-core) | MPL-2.0; v5 uyumlu modüler çekirdek; araçlar ayrı paketler; interaction-manager kaynağı incelendi | Koordinat/etkileşim yaklaşımı referans. Bu tur kodu veya bağımlılığı eklenmedi. |
| [lightweight-charts-drawing](https://github.com/deepentropy/lightweight-charts-drawing) | MIT; v5 için geniş araç seti; README'ye göre kayıt ve undo uygulamaya ait | Geniş araç gereksiniminde tekrar değerlendirilecek. Depo test iddiaları bağımsız doğrulanmış sayılmadı. |
| [CandleKit](https://github.com/rohanbeingsocial/candlekit-charts) | MIT; LWC üzerinde framework bağımsız çekirdek, React bağları, gösterge/replay/ölçüm; koordinat yardımcıları incelendi | Replay/ölçüm için referans aday. İkinci bir uygulama çekirdeği eklemek yerine mevcut altyapı korundu. |

Bu çalışma bütün ekosistemi eksiksiz tarama veya adayların performansını eşit koşullarda karşılaştırma iddiası taşımaz. Seçim, mevcut projemize uygunluk kararıdır.

## Gerçekten eklenen kaynak ve uygulama değişiklikleri

Resmî Lightweight Charts deposunun 2e1d5ce9fa0cf2a1fc8d70e0df66237e622e52c8 commit'indeki coalesced-task.ts dosyası değiştirilmeden eklendi. Toolkit paketinin 1.1.0 sürümü npm install sırasında ETARGET verdiği için yayımlanmamış sürüme bağımlılık kurulmadı. Kaynak, LICENSE, NOTICE ve SHA-256 değerleri [vendor kaydında](frontend/src/vendor/lwc-toolkit/provenance.json). Dağıtım lisansları frontend/public/licenses altında bulunur. Diğer adaylardan kaynak kopyalanmadı.

- Sürekli requestAnimationFrame çizim döngüsü kaldırıldı. Series primitive updateAllViews üzerinden gelen bildirimler resmî görev birleştiricisiyle birleştirilir. SVG çizim/hit alanları korunur; bu, bütün çizimleri Canvas'a taşıma değildir.
- Çizim zamanının mum indeksine dönüşümü doğrusal tarama yerine ikili arama yapar. Eski interpolasyon, veri boşluğu ve tarih dışı konum davranışı korunur.
- Trend çizgisi ve Fibonacci, mevcut yatay çizgi/bölgeye eklendi. İki araç da iki noktayla oluşturulur; seçme, sürükleme, nokta taşıma, fiyat düzenleme, silme ve mevcut undo/redo kayıt yolunu kullanır.
- Trend/Fibonacci yönü için nokta sırası sunucuda korunur. Bölgenin mevcut zaman sıralaması değişmez. Eski veritabanı şeması ve çizimler korunur; migration gerekmez.
- Fibonacci: 0, 0.236, 0.382, 0.5, 0.618, 0.786, 1; fiyat düzleminde doğrusal seviyeler, iki nokta arasındaki genişlikte çizilir. 0 ilk, 1 ikinci noktadır. Her platformun fabrika varsayılanıyla aynı olma iddiası yoktur.
- EMA 20/50: SMA başlangıcı ve standart 2/(n+1) katsayısı. RSI 14: Wilder ortalaması, 14 değişim ısınması; sabit seride 50. Göstergeler yalnızca mum dizisi değişince hesaplanır; heartbeat ve boşta karelerde hesap yapılmaz. En fazla 4.000 mumda O(n) yeniden hesaplama; henüz artımlı gösterge önbelleği yoktur.
- Mıknatıs: yeni çizim noktası, seçilen mumun 10 piksel içindeki en yakın O/H/L/C fiyatına oturur. Sürükleme sırasında mıknatıs henüz uygulanmaz. Fiyatlar coin tick size'a yuvarlanır.
- Sürükleme bitişi/iptalinde önceki kaydırma ve ölçek seçenekleri aynen ve bir kez geri yüklenir. Önceki körlemesine true yapma kaldırıldı.
- Gösterge ve mıknatıs seçimleri şimdilik ekran oturumuna aittir; sayfa yenilenince kapanır. Çizimler sunucuya kaydedilir ve mevcut yerel erişim eşleşmesini gerektirir.

## Doğrulama ve ölçüm

- 666 Python testi, atlanan test yok; izole HTTP/worker/yeniden başlatma ve çizim kayıt akışı geçti. Finansal çalışma veritabanı ve risk dosyaları korunmuştur: [rapor](reports/chart-workspace-validation-20261109.json).
- 16 frontend testi ve TypeScript/Vite üretim derlemesi geçti. Testler canlı mum sırası, geçmiş birleştirme, EMA/RSI sayısal örnekleri, mıknatıs, koordinat interpolasyonu, görev birleştirme, boşta tekrar etmeme, detach sonrası iptal ve özel grafik seçeneklerinin korunmasını kapsar.
- 4.000 mum, 200 iki noktalı çizim, örnek başına 40.000 koordinat araması: medyan eski 94.74 ms, yeni 1.65 ms; bu ortamda yaklaşık 57.45 kat. Sonuç toplam render veya FPS değildir. [Ölçüm](reports/chart-projection-benchmark-20261109.json). Tekrar: frontend içinde node --experimental-strip-types scripts/benchmark-chart.ts.
- Tarayıcı erişim host'u kullanılamadığı için masaüstü/mobil görsel ve uçtan uca pointer testleri tamamlanamadı. W2/W3 görsel kabul kapısı açık tutuldu. Bu sonuçlarla hatasızlık veya belirli cihazda 60 FPS garantisi verilemez.

## Sonraki kalite kapısı ve yön

W4 strateji takibinden önce gerçek tarayıcıda: dört çizim türünü oluştur/kaydet/yenile; trend ve Fibonacci yönlerini ters sırayla dene; gövde/ankraj sürükle ve iptal et; zoom/pan/price-scale/pane-resize sonrası hizalamayı doğrula; coin/zaman dilimi değiştirirken eski veri veya çizim karışmadığını gör; EMA/RSI'yi canlı açık mum ve geçmiş ekleme ile kontrol et; 200 çizim/4.000 mumda CPU, frame time, bellek ve bağlantı sayısını ölç; dar ekran/dokunmatik/fullscreen dene. En az 30 dakikalık reconnect ve uzun oturum testi de görsel kabulün parçasıdır. Mevcut SVG hit alanlarının Canvas'a taşınması, ölçüm bu katmanı darboğaz gösterirse yapılır.

Sonra W4, kaydedilmiş çizim revision'ına bağlı yaklaşma/dokunma kuralları ve tekrar önleme ile ilerler. Bot, ekran görüntüsü okumak yerine bu zaman/fiyat geometrisini ve aynı mum verisini kullanacak. Göstergeler henüz bot sinyali üretmez.

Ters mühendislik skill'i bu aşamada gerekmedi; resmî açık kaynak, API ve örnekler yeterli oldu. İleride ihtiyaç oluşursa herkese açık davranışları gözlemleyip test senaryolarına dönüştürürüz; her yeni bağımlılık ayrı kaynak/lisans/uyumluluk değerlendirmesinden geçer.
