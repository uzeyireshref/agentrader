# Tarayıcı erişimi ve masaüstü grafik testi

9 Kasım 2026. Kullanıcı kararı: yalnızca gerçek grafik testleri masaüstü uygulamasında; kod ve diğer proje çalışmaları VS Code'da sürer.

## Teşhis

CUA uygulama envanteri çalışıyor, tarayıcı listesi boş ve Browser host unavailable hatası dönüyor. Etkin Codex sürecinin üst süreci Code.exe: bu oturum IDE uzantısında. Masaüstü uygulaması yüklü ve süreçleri açık; yalnızca uygulamayı yeniden başlatmak bu IDE turuna browser sağlayıcısı kazandırmaz.

[Resmî Browser belgesi](https://learn.chatgpt.com/docs/browser), yerleşik tarayıcının IDE/CLI'da bulunmadığını, masaüstü uygulamasında kullanılabildiğini belirtir. Bu tur sağlayıcı onarılmış gibi işaretlenmedi. Ayar, güvenlik izni veya özel host protokolü değiştirilmedi. [Teşhis kaydı](../../../reports/browser-access-diagnosis-20261109.json).

## Masaüstünde gönderilecek görev

Aşağıdaki metni masaüstü uygulamasında C:\Users\asus\agentrader projesini açtıktan sonra gönder:

> Yalnızca gerçek grafik kabul testlerini yürüt. Proje kaynak kodlarını değiştirme; hata ve ölçümleri raporla. Önce 23-GRAFIK-KALITE-DENETIMI-VE-KABUL.md ve reports/chart-acceptance-matrix-20261109.json dosyalarını oku. Browser envanterini kontrol et; http://127.0.0.1:8765 grafiğini aç. G01/G02/G05/G07 senaryolarını gerçek ekranda dene: dört çizim türü, ankraj/gövde sürükleme, başlangıç noktasına geri dönüş, Escape/blur/capture kaybı, coin ve zaman dilimi geçişi, zoom/pan, fiyat ve pane ölçekleri, EMA/RSI aç-kapat, klavye UTC düzenleme, dar ekran ve tam ekran. G03 için iki sekmede aynı çizim revision çakışmasını gözle. Çizim kaydı yerel erişim gerektiriyorsa mevcut 21 numaralı kurulum belgesine uy; erişimi sessizce kaldırma, kullanıcı verisini temizleme veya gerçek çizimleri topluca değiştirme. Gerekirse ayrı geçici test veritabanlarıyla izole yerel test örneği kullan. Hesap/emir işlemi yapma. Ardından G06 için 4.000 mum/200 test çizimiyle performansı ve 30 dakikalık oturumu ölç. Ölçüm aracı yoksa FPS/heap sonucunu doğrulanmadı yaz. Test edilen sürümün bundle adını, ekran boyutunu, browser/DPR bilgisini, adım/adım beklenen ve gözlenen sonucu kaydet. Ekran kanıtlarını desteklenen araçla alabiliyorsan proje reports altında kaydet. Raporu reports/chart-desktop-acceptance-20261109.md dosyasına yaz; yalnızca gerçekten test edilen kontrolleri geçti işaretle. Kod düzeltmeleri ve diğer proje işleri VS Code tarafında devam edecek.

Tarayıcı masaüstünde de görünmüyorsa resmî [Browser extension sorun giderme](https://learn.chatgpt.com/docs/chrome-extension) adımlarını kontrol et. Oturum/izin veya uygulama arayüzü engellerini açıkça kaydet; görsel kabulü geçme.

## Burada tamamlanan ek kalite işi

frontend/src/latestRead.ts, yalnızca en yeni okumanın sonucunu veya hatasını yayımlamasını sağlar. useDrawings ilk yükleme ve yenileme aynı kapıyı kullanır; sembol değişimi/unmount/eşleşme kapanışında eski okumalar geçersizleşir. Refresh, URL'deki sembolü başlangıçta sabitler ve bekleyen preference zincirini bekler; workspace ve çizimleri birlikte yayımlar. Mutasyon sürerken yeni refresh başlatılmaz.

Beş gecikmeli Promise testi: eski ilk yüklemenin yeni refresh'i ezmesi, A→B→A dönüşünde eski A yanıtı, eski hata, dispose sonrası yanıt, güncel hata ve tekrar deneme. Toplam 31 frontend testi ve TypeScript/Vite derlemesi geçti. Bunlar okuma koordinatörünün testleridir; React hook'un bütün yaşam döngüsü veya gerçek çok sekmeli etkileşim testi olarak sunulmaz. Backend bu tur değiştirilmedi; önceki 666 test sonucu geçerlidir, bu tur yeniden çalıştırılmadı.

Açık kalanlar: React hook yarışlarının uçtan uca doğrulaması, oturum süresi akışı, gerçek ekran hizalaması/dokunma ve uzun oturum ölçümü. Bot bağlantısı kalite kabulüne kadar bekler.
